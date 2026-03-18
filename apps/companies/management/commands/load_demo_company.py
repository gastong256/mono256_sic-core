from django.core.management.base import BaseCommand, CommandError
from requests import RequestException
from rest_framework.exceptions import ValidationError

from config.exceptions import ConflictError

from apps.companies.demo_import import (
    build_demo_url,
    import_demo_company,
    load_demo_source_from_file,
    load_demo_source_from_url,
)


class Command(BaseCommand):
    help = (
        "Load one demo company from a file or URL using the canonical opening_entry + "
        "logical_exercises format. Safe to run multiple times: identical content is "
        "detected via SHA-256 and will not be imported twice. Invalid demo payloads are "
        "skipped with a warning."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--file", type=str, help="Path to the demo JSON file.")
        parser.add_argument("--url", type=str, help="Full URL to the demo JSON file.")
        parser.add_argument(
            "--r2-base-url",
            type=str,
            help="Base public or signed URL for the R2 bucket/custom domain.",
        )
        parser.add_argument(
            "--r2-key",
            type=str,
            default="demo.json",
            help="Object key to fetch from the R2 base URL (default: demo.json).",
        )
        parser.add_argument(
            "--owner-username",
            type=str,
            default="demo_owner",
            help="Username of the admin user that will own imported demo companies.",
        )
        parser.add_argument(
            "--publish",
            dest="publish",
            action="store_true",
            help="Force the imported demo to be globally published.",
        )
        parser.add_argument(
            "--no-publish",
            dest="publish",
            action="store_false",
            help="Force the imported demo to be globally unpublished.",
        )
        parser.set_defaults(publish=None)

    def handle(self, *args, **options) -> None:
        file_path = options.get("file")
        url = options.get("url")
        r2_base_url = options.get("r2_base_url")
        r2_key = options.get("r2_key") or "demo.json"

        selected_sources = [bool(file_path), bool(url), bool(r2_base_url)]
        if sum(selected_sources) != 1:
            raise CommandError("Provide exactly one source: --file, --url, or --r2-base-url.")

        try:
            if file_path:
                source = load_demo_source_from_file(file_path=file_path)
            elif url:
                source = load_demo_source_from_url(url=url)
            else:
                source = load_demo_source_from_url(
                    url=build_demo_url(base_url=r2_base_url, key=r2_key)
                )
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc
        except (ValueError, RequestException) as exc:
            raise CommandError(f"Unable to load demo payload: {exc}") from exc

        try:
            company, created = import_demo_company(
                source=source,
                owner_username=options["owner_username"],
                publish_override=options.get("publish"),
            )
        except (ValidationError, ConflictError) as exc:
            self.stdout.write(
                self.style.WARNING(
                    "Demo payload is not compatible with the current backend rules. "
                    f"Skipping import. Details: {exc}"
                )
            )
            return

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    "Demo imported successfully: "
                    f"id={company.id} slug={company.demo_slug} sha256={company.demo_content_sha256}"
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                "An identical demo already exists. "
                f"Skipping import for company id={company.id} slug={company.demo_slug}."
            )
        )
