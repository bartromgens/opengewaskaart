import hashlib
import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from django.core.management.base import CommandError
from django.db import transaction

from api.management.gewaspercelen_source import default_source_url
from api.models import Gewasperceel

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
GPKG_LAYER = "brp_gewas"


@dataclass(frozen=True)
class IngestResult:
    fetched: int
    created: int
    skipped: int


def require_rd_bbox(
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
) -> tuple[float, float, float, float]:
    if xmin >= xmax or ymin >= ymax:
        raise CommandError("Invalid bbox: xmin must be < xmax and ymin must be < ymax.")
    return xmin, ymin, xmax, ymax


def require_gpkg_path(gpkg_path: str | Path) -> Path:
    path = Path(gpkg_path)
    if not path.is_file():
        raise CommandError(f"GeoPackage not found: {path}")
    return path


def compute_geometry_hash(properties: dict, geometry: dict) -> str:
    hash_properties = {k: v for k, v in properties.items() if k != "area_m2"}
    payload = json.dumps(
        {"properties": hash_properties, "geometry": geometry},
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

    area_raw = properties.get("area_m2")
    area_m2 = float(area_raw) if area_raw is not None else None

    return Gewasperceel(
        jaar=properties["jaar"],
        gewascode=properties["gewascode"],
        gewas=properties["gewas"],
        category=properties["category"],
        status=properties["status"],
        area_m2=area_m2,
        geometry=json.dumps(geometry, separators=(",", ":")),
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        geometry_hash=compute_geometry_hash(properties, geometry),
    )


def resolve_ogr_source(gpkg_path: Path | None, source_url: str) -> str:
    if gpkg_path is not None:
        return str(gpkg_path)
    return f"/vsicurl/{source_url}"


def fetch_features(
    *,
    gpkg_path: Path | None,
    source_url: str,
    bbox: tuple[float, float, float, float],
    timeout: int,
    tmp_path: Path,
) -> list[dict]:
    xmin, ymin, xmax, ymax = bbox
    # ST_Area on geom in source CRS (EPSG:28992); result in m². -spat filters in RD.
    select_sql = "SELECT *, ST_Area(geom) AS area_m2 FROM brp_gewas"
    command = [
        "ogr2ogr",
        "-f",
        "GeoJSON",
        str(tmp_path),
        resolve_ogr_source(gpkg_path, source_url),
        GPKG_LAYER,
        "-sql",
        select_sql,
        "-dialect",
        "SQLite",
        "-spat",
        str(xmin),
        str(ymin),
        str(xmax),
        str(ymax),
        "-spat_srs",
        "EPSG:28992",
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
    if features:
        logger.info("Fetched %d features from GeoPackage.", len(features))
    else:
        logger.warning("No features returned for the given bbox.")
    return features


def persist_features(features: list[dict]) -> int:
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


def ingest_parcels(
    *,
    year: int,
    bbox: tuple[float, float, float, float],
    gpkg_path: str | Path | None = None,
    source_url: str | None = None,
    timeout: int = 300,
) -> IngestResult:
    xmin, ymin, xmax, ymax = require_rd_bbox(*bbox)
    resolved_gpkg = require_gpkg_path(gpkg_path) if gpkg_path else None
    resolved_source_url = source_url or default_source_url(year)

    logger.info(
        "Starting ingest: year=%s bbox=(%s, %s, %s, %s) source=%s gpkg=%s",
        year,
        xmin,
        ymin,
        xmax,
        ymax,
        resolved_gpkg or resolved_source_url,
        resolved_gpkg is not None,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "features.geojson"
        features = fetch_features(
            gpkg_path=resolved_gpkg,
            source_url=resolved_source_url,
            bbox=(xmin, ymin, xmax, ymax),
            timeout=timeout,
            tmp_path=tmp_path,
        )
        created = persist_features(features)

    skipped = len(features) - created
    logger.info(
        "Ingestion complete: fetched=%d created=%d skipped=%d",
        len(features),
        created,
        skipped,
    )
    return IngestResult(fetched=len(features), created=created, skipped=skipped)
