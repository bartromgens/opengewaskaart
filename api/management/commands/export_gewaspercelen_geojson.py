import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from api.brp_constants import EXCLUDED_MBTILES_CATEGORIES
from api.management.bbox import BBOX_ARGUMENT_HELP, filter_queryset_by_bbox, require_bbox
from api.models import Gewasperceel

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000


def feature_from_row(row: Gewasperceel) -> dict:
    return {
        "type": "Feature",
        "id": row.id,
        "properties": {
            "id": row.id,
            "jaar": row.jaar,
            "gewascode": row.gewascode,
            "gewas": row.gewas,
            "category": row.category,
            "status": row.status,
        },
        "geometry": json.loads(row.geometry),
    }


class Command(BaseCommand):
    help = "Export Gewaspercelen rows to GeoJSON for vector tile generation."

    def add_arguments(self, parser) -> None:
        default_out = settings.BASE_DIR / "data" / "gewaspercelen.geojson"
        parser.add_argument(
            "--output",
            type=str,
            default=str(default_out),
            help="Output file path (default: data/gewaspercelen.geojson)",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Filter to a single reference year.",
        )
        parser.add_argument(
            "--bbox",
            type=str,
            default=None,
            help=BBOX_ARGUMENT_HELP,
        )

    def handle(self, *args, **options) -> None:
        output_path = Path(options["output"])
        year = options.get("year")
        bbox_str = options.get("bbox")
        bbox = require_bbox(bbox_str)

        queryset = Gewasperceel.objects.all().order_by("id")
        if EXCLUDED_MBTILES_CATEGORIES:
            queryset = queryset.exclude(category__in=EXCLUDED_MBTILES_CATEGORIES)
            self.stdout.write(
                f"Excluding categories: {', '.join(EXCLUDED_MBTILES_CATEGORIES)}"
            )
        if year is not None:
            queryset = queryset.filter(jaar=year)
        if bbox:
            queryset = filter_queryset_by_bbox(queryset, bbox)
            self.stdout.write(f"Filtering to bbox: {bbox}")
        if year is not None:
            self.stdout.write(f"Filtering to year: {year}")

        total_count = queryset.count()
        if total_count == 0:
            logger.warning("No gewaspercelen found in database.")
            self.stdout.write(self.style.WARNING("No gewaspercelen found in database"))
            return

        logger.info(
            "Exporting %d parcels to %s (year=%s bbox=%s excluded=%s).",
            total_count,
            output_path,
            year,
            bbox,
            EXCLUDED_MBTILES_CATEGORIES,
        )
        self.stdout.write(f"Exporting {total_count} parcels to {output_path}...")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        processed = 0
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write('{\n  "type": "FeatureCollection",\n  "features": [\n')
            first = True

            for row in queryset.only(
                "id",
                "jaar",
                "gewascode",
                "gewas",
                "category",
                "status",
                "geometry",
            ).iterator(chunk_size=BATCH_SIZE):
                feature = feature_from_row(row)
                if not first:
                    handle.write(",\n")
                first = False
                handle.write("    ")
                handle.write(json.dumps(feature, ensure_ascii=False, separators=(",", ":")))

                processed += 1
                if processed % 10000 == 0:
                    pct = 100 * processed / total_count
                    self.stdout.write(f"  Processed {processed}/{total_count} ({pct:.1f}%)...")

            handle.write("\n  ]\n}\n")

        logger.info(
            "Export complete: %d features written to %s.",
            processed,
            output_path.absolute(),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Export complete: {processed} features written to {output_path.absolute()}"
            )
        )
