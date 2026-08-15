import logging

from django.core.management.base import BaseCommand, CommandError

from api.management.gewaspercelen_ingest import ingest_parcels, require_gpkg_path
from api.management.gewaspercelen_source import (
    add_source_url_argument,
    add_year_argument,
    default_source_url,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Ingest BRP Gewaspercelen parcels from a PDOK GeoPackage into the database."
    )

    def add_arguments(self, parser) -> None:
        add_year_argument(parser)
        parser.add_argument(
            "--bbox",
            nargs=4,
            type=float,
            metavar=("XMIN", "YMIN", "XMAX", "YMAX"),
            required=True,
            help="Bounding box in EPSG:28992 (RD New) coordinates.",
        )
        parser.add_argument(
            "--gpkg",
            type=str,
            default=None,
            help="Path to a local GeoPackage file (recommended for large areas).",
        )
        add_source_url_argument(parser)
        parser.add_argument(
            "--timeout",
            type=int,
            default=300,
            help="Timeout in seconds for the ogr2ogr subprocess (default: 300).",
        )

    def handle(self, *args, **options) -> None:
        year = options["year"]
        bbox = tuple(options["bbox"])
        gpkg_path = options.get("gpkg")
        source_url = options["source_url"]
        timeout = options["timeout"]

        source_label = (
            str(require_gpkg_path(gpkg_path))
            if gpkg_path
            else (source_url or default_source_url(year))
        )
        self.stdout.write(
            f"Fetching year {year} from {source_label} "
            f"for bbox {bbox}..."
        )

        try:
            result = ingest_parcels(
                year=year,
                bbox=bbox,
                gpkg_path=gpkg_path,
                source_url=source_url,
                timeout=timeout,
            )
        except CommandError:
            raise
        except Exception as exc:
            logger.exception("ingest_gewaspercelen failed: %s", exc)
            raise CommandError(str(exc)) from exc

        if result.fetched == 0:
            self.stdout.write(
                self.style.WARNING("No features returned for the given bbox.")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Ingestion complete: {result.fetched} fetched, "
                f"{result.created} created, {result.skipped} skipped as duplicates."
            )
        )
