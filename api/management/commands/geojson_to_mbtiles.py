import logging
from pathlib import Path
from typing import Optional, Tuple

import ijson
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from api.management.bbox import require_bbox
from api.management.tippecanoe import (
    add_mbtiles_conversion_arguments,
    build_tippecanoe_command,
    prepare_tippecanoe,
    run_tippecanoe,
)

logger = logging.getLogger(__name__)


def validate_geojson_has_features(input_path: Path) -> None:
    """Stream-parse GeoJSON and fail fast if the file is invalid or empty."""
    try:
        with input_path.open("rb") as handle:
            for _ in ijson.items(handle, "features.item"):
                return
    except ijson.JSONError as exc:
        raise CommandError(f"Invalid GeoJSON file: {exc}") from exc
    except OSError as exc:
        raise CommandError(f"Error reading GeoJSON file: {exc}") from exc

    raise CommandError("GeoJSON file contains no features")


class Command(BaseCommand):
    help = "Convert Gewaspercelen GeoJSON to MBTiles format for tileserver-gl."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--input",
            type=str,
            default=str(settings.BASE_DIR / "data" / "gewaspercelen.geojson"),
            help="Input GeoJSON file path (default: data/gewaspercelen.geojson)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=str(settings.BASE_DIR / "data" / "gewaspercelen.mbtiles"),
            help="Output MBTiles file path (default: data/gewaspercelen.mbtiles)",
        )
        parser.add_argument(
            "--skip-input-validation",
            action="store_true",
            help="Skip GeoJSON validation (e.g. when the file was just exported).",
        )
        add_mbtiles_conversion_arguments(parser)

    def handle(self, *args, **options) -> None:
        input_path = Path(options["input"])
        output_path = Path(options["output"])
        force = options["force"]
        bbox_str = options.get("bbox")

        tippecanoe_path, _ = prepare_tippecanoe(self, options.get("tippecanoe"))
        bbox: Optional[Tuple[float, float, float, float]] = require_bbox(bbox_str)
        if bbox:
            logger.info("Clipping to bounding box: %s", bbox)
            self.stdout.write(f"Clipping to bounding box: {bbox}")

        if output_path.exists() and not force:
            raise CommandError(
                f"Output file {output_path} already exists. Use --force to overwrite."
            )

        if not input_path.exists():
            logger.info("Input file %s not found, exporting GeoJSON from database.", input_path)
            self.stdout.write(
                f"Input file {input_path} not found, exporting GeoJSON from database..."
            )
            try:
                call_command("export_gewaspercelen_geojson", output=str(input_path))
            except Exception as exc:
                logger.exception("Failed to export GeoJSON: %s", exc)
                raise CommandError(f"Failed to export GeoJSON: {exc}") from exc
            options["skip_input_validation"] = True

        if not input_path.exists():
            raise CommandError(f"Input file {input_path} does not exist")

        if not options["skip_input_validation"]:
            self.stdout.write(f"Validating GeoJSON input: {input_path}...")
            validate_geojson_has_features(input_path)
            logger.info("GeoJSON input validated: %s", input_path)
            self.stdout.write("GeoJSON input validated")

        min_zoom = options["min_zoom"]
        max_zoom = options["max_zoom"]
        logger.info(
            "Converting to MBTiles: input=%s output=%s zoom=%s-%s",
            input_path,
            output_path,
            min_zoom,
            max_zoom,
        )
        self.stdout.write(f"Converting to MBTiles (zoom {min_zoom}-{max_zoom})...")
        self.stdout.write(f"Output: {output_path.absolute()}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        tippecanoe_cmd = build_tippecanoe_command(
            tippecanoe_path=tippecanoe_path,
            input_path=input_path,
            output_path=output_path,
            layer_name=options["layer_name"],
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            maximum_tile_bytes=options["maximum_tile_bytes"],
            maximum_tile_features=options["maximum_tile_features"],
            full_detail=options["full_detail"],
            low_detail=options["low_detail"],
            minimum_detail=options["minimum_detail"],
            simplification=options["simplification"],
            coalesce_densest=options["coalesce_densest_as_needed"],
            drop_densest=options["drop_densest_as_needed"],
            drop_smallest=options["drop_smallest_as_needed"],
            drop_fraction=options["drop_fraction_as_needed"],
            limit_tile_feature_count=options["limit_tile_feature_count"],
            bbox=bbox,
            force=force,
        )
        run_tippecanoe(tippecanoe_cmd, self.stdout)

        file_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(
            "Conversion complete: %s (%.2f MB).",
            output_path.absolute(),
            file_size,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"\nConversion complete: {output_path.absolute()} ({file_size:.2f} MB)"
            )
        )
