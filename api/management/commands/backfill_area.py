import json
import logging

from django.core.management.base import BaseCommand

from api.models import Gewasperceel

logger = logging.getLogger(__name__)


def _area_m2_rd(geometry_json: str, transformer) -> float:
    """Planar area in m² (RD). Reuse one *transformer* for all rows — building it per row is very slow."""
    from shapely.geometry import shape
    from shapely.ops import transform

    geom = shape(json.loads(geometry_json))
    geom_rd = transform(transformer.transform, geom)
    return float(geom_rd.area)


class Command(BaseCommand):
    help = (
        "Compute area_m2 from stored WGS84 geometries (RD planar area in m²). "
        "For rows already ingested without ST_Area from ogr2ogr."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Only update rows for this jaar.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=2000,
            help="Rows per bulk_update batch (default 2000).",
        )

    def handle(self, *args, **options) -> None:
        year = options["year"]
        batch_size = max(1, int(options["batch_size"]))

        qs = Gewasperceel.objects.filter(area_m2__isnull=True).only("id", "geometry")
        if year is not None:
            qs = qs.filter(jaar=year)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No rows need area backfill."))
            return

        from pyproj import Transformer

        # One transformer for the whole run; creating Transformer.from_crs per row dominated runtime.
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)

        self.stdout.write(f"Backfilling area_m2 for {total} rows...")
        updated = 0
        batch: list[Gewasperceel] = []

        for row in qs.iterator(chunk_size=batch_size):
            try:
                row.area_m2 = _area_m2_rd(row.geometry, transformer)
            except Exception:
                logger.exception("Failed area for id=%s", row.pk)
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                Gewasperceel.objects.bulk_update(batch, ["area_m2"])
                updated += len(batch)
                pct = 100.0 * updated / total
                self.stdout.write(
                    f"  Progress: {updated}/{total} ({pct:.1f}%)"
                )
                batch.clear()

        if batch:
            Gewasperceel.objects.bulk_update(batch, ["area_m2"])
            updated += len(batch)

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete: {updated}/{total} rows updated (100%)."
            )
        )
