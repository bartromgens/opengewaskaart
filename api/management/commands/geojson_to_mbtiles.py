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
    build_tile_join_command,
    build_tippecanoe_command,
    prepare_tippecanoe,
    resolve_tile_join_path,
    run_tippecanoe,
)

logger = logging.getLogger(__name__)

# Only what the map needs for colouring; dropping the rest (notably `id`) lets
# tippecanoe merge neighbouring parcels with identical attributes.
OVERVIEW_ATTRIBUTES = ("gewascode", "gewas")


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

        def detail_command(
            *, out: Path, zoom_min: int, force_overwrite: bool
        ) -> list[str]:
            return build_tippecanoe_command(
                tippecanoe_path=tippecanoe_path,
                input_path=input_path,
                output_path=out,
                layer_name=options["layer_name"],
                min_zoom=zoom_min,
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
                force=force_overwrite,
            )

        # Zoom tiers, lowest first:
        #   dissolved: z[min_zoom .. dissolved_max_zoom] from the pre-merged GeoJSON
        #   overview:  next zooms up to overview_max_zoom, coalesced from the full GeoJSON
        #   detail:    everything above, one polygon per parcel
        dissolved_max_zoom = options["dissolved_max_zoom"]
        overview_input = Path(options["overview_input"])
        use_dissolved = dissolved_max_zoom > 0 and min_zoom <= dissolved_max_zoom < max_zoom
        if use_dissolved and not overview_input.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Dissolved GeoJSON {overview_input} not found; skipping dissolved tier "
                    "(run export_overview_geojson)."
                )
            )
            use_dissolved = False

        overview_max_zoom = options["overview_max_zoom"]
        overview_start = dissolved_max_zoom + 1 if use_dissolved else min_zoom
        use_overview = (
            overview_max_zoom > 0 and overview_start <= overview_max_zoom < max_zoom
        )

        detail_start = min_zoom
        if use_overview:
            detail_start = overview_max_zoom + 1
        elif use_dissolved:
            detail_start = dissolved_max_zoom + 1

        if not use_overview and not use_dissolved:
            run_tippecanoe(
                detail_command(out=output_path, zoom_min=min_zoom, force_overwrite=force),
                self.stdout,
            )
        else:
            stem = output_path.stem
            dissolved_path = output_path.with_name(stem + ".dissolved.mbtiles")
            overview_path = output_path.with_name(stem + ".overview.mbtiles")
            detail_path = output_path.with_name(stem + ".detail.mbtiles")
            partials: list[Path] = []
            tile_join_path = resolve_tile_join_path(tippecanoe_path)

            self.stdout.write(
                f"Zoom tiers: dissolved {min_zoom}-{dissolved_max_zoom if use_dissolved else '-'}, "
                f"overview {overview_start if use_overview else '-'}-"
                f"{overview_max_zoom if use_overview else '-'}, "
                f"detailed {detail_start}-{max_zoom}"
            )

            if use_dissolved:
                self.stdout.write("Building dissolved tiles...")
                run_tippecanoe(
                    build_tippecanoe_command(
                        tippecanoe_path=tippecanoe_path,
                        input_path=overview_input,
                        output_path=dissolved_path,
                        layer_name=options["layer_name"],
                        min_zoom=min_zoom,
                        max_zoom=dissolved_max_zoom,
                        maximum_tile_bytes=options["maximum_tile_bytes"],
                        maximum_tile_features=options["maximum_tile_features"],
                        full_detail=options["low_detail"],
                        low_detail=options["low_detail"],
                        minimum_detail=options["minimum_detail"],
                        simplification=options["overview_simplification"],
                        coalesce_densest=False,
                        drop_densest=False,
                        drop_smallest=True,
                        drop_fraction=False,
                        include_attributes=OVERVIEW_ATTRIBUTES,
                        use_feature_id=False,
                        preserve_input_order=True,
                        bbox=bbox,
                        force=True,
                    ),
                    self.stdout,
                )
                partials.append(dissolved_path)

        if use_overview:
            self.stdout.write("Building overview tiles...")
            run_tippecanoe(
                build_tippecanoe_command(
                    tippecanoe_path=tippecanoe_path,
                    input_path=input_path,
                    output_path=overview_path,
                    layer_name=options["layer_name"],
                    min_zoom=overview_start,
                    max_zoom=overview_max_zoom,
                    maximum_tile_bytes=options["maximum_tile_bytes"],
                    maximum_tile_features=options["maximum_tile_features"],
                    full_detail=options["low_detail"],
                    low_detail=options["low_detail"],
                    minimum_detail=options["minimum_detail"],
                    simplification=options["overview_simplification"],
                    coalesce_densest=False,
                    drop_densest=False,
                    # Last resort only; coalescing handles most of the load.
                    drop_smallest=True,
                    drop_fraction=False,
                    coalesce=True,
                    coalesce_smallest=True,
                    detect_shared_borders=True,
                    include_attributes=OVERVIEW_ATTRIBUTES,
                    use_feature_id=False,
                    bbox=bbox,
                    force=True,
                ),
                self.stdout,
            )
            partials.append(overview_path)

        if use_overview or use_dissolved:
            self.stdout.write("Building detailed tiles...")
            run_tippecanoe(
                detail_command(
                    out=detail_path, zoom_min=detail_start, force_overwrite=True
                ),
                self.stdout,
            )
            partials.append(detail_path)

            self.stdout.write("Joining tiers...")
            run_tippecanoe(
                build_tile_join_command(
                    tile_join_path=tile_join_path,
                    output_path=output_path,
                    input_paths=partials,
                    force=force,
                ),
                self.stdout,
            )
            for partial in partials:
                partial.unlink(missing_ok=True)

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
