import datetime
from dataclasses import dataclass

from apps.common.cache import safe_cache_get, safe_cache_set
from apps.reports.cache import report_cache_version
from config.exceptions import ConflictError
from apps.closing.models import ClosingSnapshot
from apps.companies.models import Company
from apps.journal.models import JournalEntry

_LOGICAL_EXERCISES_CACHE_TTL = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class LogicalExercise:
    exercise_id: str
    exercise_index: int
    opening_entry_id: int
    opening_source_type: str
    start_date: datetime.date
    closing_entry_id: int | None
    closing_date: datetime.date | None
    snapshot_id: int | None
    status: str

    @property
    def end_date(self) -> datetime.date | None:
        return self.closing_date


@dataclass(frozen=True)
class ReportExerciseContext:
    requested_from: datetime.date | None
    requested_to: datetime.date
    active_exercise: LogicalExercise | None
    previous_exercises: tuple[LogicalExercise, ...]
    visible_from: datetime.date | None
    visible_to: datetime.date
    computed_from: datetime.date | None
    computed_to: datetime.date


def _logical_exercises_cache_key(*, company_id: int) -> str:
    version = report_cache_version(company_id=company_id)
    return f"closing:company:{company_id}:logical-exercises:v{version}"


def _serialize_exercise(exercise: LogicalExercise) -> dict:
    return {
        "exercise_id": exercise.exercise_id,
        "exercise_index": exercise.exercise_index,
        "opening_entry_id": exercise.opening_entry_id,
        "opening_source_type": exercise.opening_source_type,
        "start_date": exercise.start_date.isoformat(),
        "closing_entry_id": exercise.closing_entry_id,
        "closing_date": exercise.closing_date.isoformat() if exercise.closing_date else None,
        "snapshot_id": exercise.snapshot_id,
        "status": exercise.status,
    }


def _deserialize_exercise(data: dict) -> LogicalExercise:
    return LogicalExercise(
        exercise_id=str(data["exercise_id"]),
        exercise_index=int(data["exercise_index"]),
        opening_entry_id=int(data["opening_entry_id"]),
        opening_source_type=str(data["opening_source_type"]),
        start_date=datetime.date.fromisoformat(data["start_date"]),
        closing_entry_id=(
            int(data["closing_entry_id"]) if data.get("closing_entry_id") is not None else None
        ),
        closing_date=(
            datetime.date.fromisoformat(data["closing_date"])
            if data.get("closing_date") is not None
            else None
        ),
        snapshot_id=int(data["snapshot_id"]) if data.get("snapshot_id") is not None else None,
        status=str(data["status"]),
    )


def _exercise_id_for(entry: JournalEntry) -> str:
    prefix = "opening" if entry.source_type == JournalEntry.SourceType.OPENING else "reopening"
    return f"{prefix}:{entry.id}"


def _build_logical_exercises(company: Company) -> list[LogicalExercise]:
    boundary_entries = list(
        company.journal_entries.filter(
            source_type__in=[
                JournalEntry.SourceType.OPENING,
                JournalEntry.SourceType.REOPENING,
                JournalEntry.SourceType.PATRIMONIAL_CLOSING,
            ]
        ).order_by("date", "entry_number")
    )
    snapshots_by_closing_entry_id = {
        snapshot.patrimonial_closing_entry_id: snapshot.id
        for snapshot in ClosingSnapshot.objects.filter(company=company)
    }

    exercises: list[LogicalExercise] = []
    current_opening_entry: JournalEntry | None = None
    seen_opening = False

    for entry in boundary_entries:
        if entry.source_type == JournalEntry.SourceType.OPENING:
            if seen_opening or current_opening_entry is not None or exercises:
                raise ConflictError("The company has an invalid logical exercise chain.")
            seen_opening = True
            current_opening_entry = entry
            continue

        if entry.source_type == JournalEntry.SourceType.REOPENING:
            if not seen_opening or current_opening_entry is not None:
                raise ConflictError("The company has an invalid logical exercise chain.")
            current_opening_entry = entry
            continue

        if current_opening_entry is None:
            raise ConflictError("The company has an invalid logical exercise chain.")

        exercises.append(
            LogicalExercise(
                exercise_id=_exercise_id_for(current_opening_entry),
                exercise_index=len(exercises) + 1,
                opening_entry_id=current_opening_entry.id,
                opening_source_type=current_opening_entry.source_type,
                start_date=current_opening_entry.date,
                closing_entry_id=entry.id,
                closing_date=entry.date,
                snapshot_id=snapshots_by_closing_entry_id.get(entry.id),
                status="closed",
            )
        )
        current_opening_entry = None

    if current_opening_entry is not None:
        exercises.append(
            LogicalExercise(
                exercise_id=_exercise_id_for(current_opening_entry),
                exercise_index=len(exercises) + 1,
                opening_entry_id=current_opening_entry.id,
                opening_source_type=current_opening_entry.source_type,
                start_date=current_opening_entry.date,
                closing_entry_id=None,
                closing_date=None,
                snapshot_id=None,
                status="open",
            )
        )

    if company.journal_entries.exists() and not exercises:
        raise ConflictError(
            "The company has accounting entries but no valid logical exercise chain."
        )

    return exercises


def list_logical_exercises(*, company: Company) -> list[LogicalExercise]:
    key = _logical_exercises_cache_key(company_id=company.id)
    cached = safe_cache_get(key)
    if isinstance(cached, list):
        return [_deserialize_exercise(item) for item in cached]

    exercises = _build_logical_exercises(company)
    safe_cache_set(
        key,
        [_serialize_exercise(exercise) for exercise in exercises],
        timeout=_LOGICAL_EXERCISES_CACHE_TTL,
    )
    return exercises


def serialize_logical_exercise(exercise: LogicalExercise) -> dict:
    return _serialize_exercise(exercise)


def get_current_logical_exercise(*, company: Company) -> LogicalExercise | None:
    exercises = list_logical_exercises(company=company)
    for exercise in reversed(exercises):
        if exercise.status == "open":
            return exercise
    return exercises[-1] if exercises else None


def resolve_report_exercise_context(
    *,
    company: Company,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
) -> ReportExerciseContext:
    actual_to = date_to or datetime.date.today()
    exercises = list_logical_exercises(company=company)
    if not exercises:
        return ReportExerciseContext(
            requested_from=date_from,
            requested_to=actual_to,
            active_exercise=None,
            previous_exercises=(),
            visible_from=date_from,
            visible_to=actual_to,
            computed_from=date_from,
            computed_to=actual_to,
        )

    requested_from = date_from or exercises[0].start_date
    intersected = [
        exercise
        for exercise in exercises
        if exercise.start_date <= actual_to and (exercise.end_date or actual_to) >= requested_from
    ]
    if not intersected:
        return ReportExerciseContext(
            requested_from=date_from,
            requested_to=actual_to,
            active_exercise=None,
            previous_exercises=(),
            visible_from=requested_from,
            visible_to=actual_to,
            computed_from=requested_from,
            computed_to=actual_to,
        )

    active_exercise = intersected[-1]
    visible_from = max(active_exercise.start_date, requested_from)
    previous_exercises = tuple(reversed(intersected[:-1]))
    return ReportExerciseContext(
        requested_from=date_from,
        requested_to=actual_to,
        active_exercise=active_exercise,
        previous_exercises=previous_exercises,
        visible_from=visible_from,
        visible_to=actual_to,
        computed_from=active_exercise.start_date,
        computed_to=actual_to,
    )


def get_latest_snapshot(*, company: Company) -> ClosingSnapshot | None:
    return company.closing_snapshots.order_by("-closing_date", "-id").first()


def get_snapshot(*, company: Company, snapshot_id: int) -> ClosingSnapshot:
    return company.closing_snapshots.get(pk=snapshot_id)
