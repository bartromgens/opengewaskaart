import logging
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from api.management.bbox import require_bbox
from api.management.tippecanoe import (
    add_mbtiles_conversion_arguments,
    mbtiles_conversion_kwargs,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Export Gewaspercelen to GeoJSON and convert to MBTiles format."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--geojson-output",
            type=str,
            default=str(settings.BASE_DIR / "data" / "gewaspercelen.geojson"),
            help="Intermediate GeoJSON file path (default: data/gewaspercelen.geojson)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=str(settings.BASE_DIR / "data" / "gewaspercelen.mbtiles"),
            help="Output MBTiles file path (default: data/gewaspercelen.mbtiles)",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Filter export to a single reference year.",
        )
        add_mbtiles_conversion_arguments(parser)

    def handle(self, *args, **options) -> None:
        geojson_output = options["geojson_output"]
        mbtiles_output = options["output"]
        year = options.get("year")
        bbox_str = options.get("bbox")

        require_bbox(bbox_str)
        geojson_path = Path(geojson_output)

        logger.info(
            "Starting export_to_mbtiles: geojson=%s mbtiles=%s year=%s bbox=%s",
            geojson_output,
            mbtiles_output,
            year,
            bbox_str,
        )

        self.stdout.write("=" * 60)
        self.stdout.write("Step 1: Exporting GeoJSON from database")
        self.stdout.write("=" * 60)

        try:
            export_kwargs = {"output": str(geojson_path)}
            if year is not None:
                export_kwargs["year"] = year
            if bbox_str:
                export_kwargs["bbox"] = bbox_str
            call_command("export_gewaspercelen_geojson", **export_kwargs)
        except Exception as exc:
            logger.exception("Failed to export GeoJSON: %s", exc)
            raise CommandError(f"Failed to export GeoJSON: {exc}") from exc

        if not geojson_path.exists():
            raise CommandError("GeoJSON export failed - file was not created")

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("Step 2: Converting GeoJSON to MBTiles")
        self.stdout.write("=" * 60)

        try:
            mbtiles_kwargs = {
                "input": str(geojson_path),
                "output": mbtiles_output,
                **mbtiles_conversion_kwargs(options),
            }
            call_command("geojson_to_mbtiles", **mbtiles_kwargs)
        except Exception as exc:
            logger.exception("Failed to convert to MBTiles: %s", exc)
            raise CommandError(f"Failed to convert to MBTiles: {exc}") from exc

        logger.info(
            "Export and conversion complete: mbtiles=%s geojson=%s",
            Path(mbtiles_output).absolute(),
            geojson_path.absolute(),
        )
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("Export and conversion complete!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"MBTiles output: {Path(mbtiles_output).absolute()}")
        self.stdout.write(f"GeoJSON output: {geojson_path.absolute()}")
