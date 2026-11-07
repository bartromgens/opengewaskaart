from django.core.management.base import BaseCommand

from api.summaries import warm_all_national_summaries


class Command(BaseCommand):
    help = "Pre-compute and cache national gewassen, gebruik, and category summaries."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--jaar",
            type=int,
            default=None,
            help="Optional jaar filter (default: all years in the database).",
        )

    def handle(self, *args, **options) -> None:
        jaar = options.get("jaar")
        jaar_param = str(jaar) if jaar is not None else None
        warm_all_national_summaries(jaar_param)
        self.stdout.write(self.style.SUCCESS("Summary caches warmed."))
