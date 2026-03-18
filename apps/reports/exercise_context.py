from apps.closing.selectors import ReportExerciseContext, serialize_logical_exercise


def build_report_exercise_metadata(*, context: ReportExerciseContext) -> dict:
    return {
        "requested_date_from": (
            str(context.requested_from) if context.requested_from is not None else None
        ),
        "requested_date_to": str(context.requested_to),
        "active_exercise": (
            serialize_logical_exercise(context.active_exercise)
            if context.active_exercise is not None
            else None
        ),
        "previous_exercises": [
            serialize_logical_exercise(exercise) for exercise in context.previous_exercises
        ],
    }


def build_report_exercise_cache_parts(*, context: ReportExerciseContext) -> dict[str, str]:
    return {
        "exercise_id": (
            context.active_exercise.exercise_id if context.active_exercise is not None else "none"
        )
    }


def attach_report_exercise_metadata(*, report: dict, context: ReportExerciseContext) -> dict:
    return {
        **report,
        **build_report_exercise_metadata(context=context),
    }
