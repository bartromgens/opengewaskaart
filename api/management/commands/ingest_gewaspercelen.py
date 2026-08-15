import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import Gewasperceel

DEFAULT_SOURCE_URL = (
    "https://service.pdok.nl/rvo/gewaspercelen/atom/downloads/"
    "brpgewaspercelen_definitief_{year}.gpkg"
)
BATCH_SIZE = 500


def default_source_url(year: int) -> str:
    return DEFAULT_SOURCE_URL.format(year=year)


def compute_geometry_hash(properties: dict, geometry: dict) -> str:
    payload = json.dumps(
        {"properties": properties, "geometry": geometry},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def compute_bbox(geometry: dict) -> tuple[float, float, float, float]:
    coordinates = geometry.get("coordinates")
    if not coordinates:
        raise ValueError(f"Geometry type {geometry.get('type')} has no coordinates")

    min_lon = float("inf")
    min_lat = float("inf")
    max_lon = float("-inf")
    max_lat = float("-inf")

    def visit(point: list[float]) -> None:
        nonlocal min_lon, min_lat, max_lon, max_lat
        lon, lat = point[0], point[1]
        min_lon = min(min_lon, lon)
        min_lat = min(min_lat, lat)
        max_lon = max(max_lon, lon)
        max_lat = max(max_lat, lat)

    def walk(node) -> None:
        if isinstance(node[0], (int, float)):
            visit(node)
            return
        for child in node:
            walk(child)

    walk(coordinates)
    return min_lon, min_lat, max_lon, max_lat


def feature_to_model(feature: dict) -> Gewasperceel:
    properties = feature["properties"]
    geometry = feature["geometry"]
    min_lon, min_lat, max_lon, max_lat = compute_bbox(geometry)

    return Gewasperceel(
        jaar=properties["jaar"],
        gewascode=properties["gewascode"],
        gewas=properties["gewas"],
        category=properties["category"],
        status=properties["status"],
        geometry=json.dumps(geometry, separators=(",", ":")),
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        geometry_hash=compute_geometry_hash(properties, geometry),
    )


class Command(BaseCommand):
    help = (
        "Ingest BRP Gewaspercelen parcels from a PDOK GeoPackage into the database."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="Reference year of the dataset (e.g. 2025).",
        )
        parser.add_argument(
            "--bbox",
            nargs=4,
            type=float,
            metavar=("XMIN", "YMIN", "XMAX", "YMAX"),
            required=True,
            help="Bounding box in EPSG:28992 (RD New) coordinates.",
        )
        parser.add_argument(
            "--source-url",
            type=str,
            default=None,
            help="Override the PDOK GeoPackage URL.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=300,
            help="Timeout in seconds for the ogr2ogr subprocess (default: 300).",
        )

    def handle(self, *args, **options) -> None:
        year = options["year"]
        xmin, ymin, xmax, ymax = options["bbox"]
        source_url = options["source_url"] or default_source_url(year)
        timeout = options["timeout"]

        if xmin >= xmax or ymin >= ymax:
            raise CommandError("Invalid bbox: xmin must be < xmax and ymin must be < ymax.")

        self.stdout.write(
            f"Fetching year {year} from {source_url} "
            f"for bbox ({xmin}, {ymin}, {xmax}, {ymax})..."
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "features.geojson"
            features = self._fetch_features(
                source_url=source_url,
                tmp_path=tmp_path,
                bbox=(xmin, ymin, xmax, ymax),
                timeout=timeout,
            )
            created = self._persist_features(features)

        skipped = len(features) - created
        self.stdout.write(
            self.style.SUCCESS(
                f"Ingestion complete: {len(features)} fetched, "
                f"{created} created, {skipped} skipped as duplicates."
            )
        )

    def _fetch_features(
        self,
        source_url: str,
        tmp_path: Path,
        bbox: tuple[float, float, float, float],
        timeout: int,
    ) -> list[dict]:
        xmin, ymin, xmax, ymax = bbox
        vsicurl_source = f"/vsicurl/{source_url}"

        command = [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            str(tmp_path),
            vsicurl_source,
            "brp_gewas",
            "-spat",
            str(xmin),
            str(ymin),
            str(xmax),
            str(ymax),
            "-t_srs",
            "EPSG:4326",
            "-dim",
            "XY",
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise CommandError(
                f"ogr2ogr timed out after {timeout} seconds."
            ) from exc
        except FileNotFoundError as exc:
            raise CommandError(
                "ogr2ogr was not found. Install GDAL (ogr2ogr) and try again."
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr.strip() or "No stderr output."
            raise CommandError(f"ogr2ogr failed (exit {result.returncode}): {stderr}")

        try:
            payload = json.loads(tmp_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Failed to parse GeoJSON output: {exc}") from exc

        features = payload.get("features", [])
        if not features:
            self.stdout.write(
                self.style.WARNING("No features returned for the given bbox.")
            )
        return features

    def _persist_features(self, features: list[dict]) -> int:
        before_count = Gewasperceel.objects.count()

        with transaction.atomic():
            for start in range(0, len(features), BATCH_SIZE):
                batch = features[start : start + BATCH_SIZE]
                models = [feature_to_model(feature) for feature in batch]
                Gewasperceel.objects.bulk_create(
                    models,
                    ignore_conflicts=True,
                )

        return Gewasperceel.objects.count() - before_count
