import json
import logging
import math
from pathlib import Path
from typing import Iterable, Optional

from django.conf import settings
from django.core.management.base import BaseCommand
from shapely import set_precision, to_geojson
from shapely.errors import GEOSException
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

from api.brp_constants import EXCLUDED_MBTILES_CATEGORIES
from api.management.bbox import (
    BBOX_ARGUMENT_HELP,
    REGION_BBOXES,
    filter_queryset_by_bbox,
    require_bbox,
)
from api.models import Gewasperceel

logger = logging.getLogger(__name__)

DEFAULT_CELL_SIZE = 0.25  # degrees
# All distances are in degrees (WGS84). 0.0001 degrees is roughly 7-11 m.
DEFAULT_CLOSE_DISTANCE = 0.0004
DEFAULT_SIMPLIFY_TOLERANCE = 0.0003
DEFAULT_MIN_AREA = 2e-7  # ~ 1.5 ha; smaller dissolved pieces are dropped


def _polygons(geometry: BaseGeometry) -> list[Polygon]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    if hasattr(geometry, "geoms"):
        result: list[Polygon] = []
        for part in geometry.geoms:
            result.extend(_polygons(part))
        return result
    return []


def dissolve_geometries(
    geometries: Iterable[BaseGeometry],
    *,
    close_distance: float = DEFAULT_CLOSE_DISTANCE,
    simplify_tolerance: float = DEFAULT_SIMPLIFY_TOLERANCE,
    min_area: float = DEFAULT_MIN_AREA,
) -> Optional[BaseGeometry]:
    """Merge parcels into few large shapes.

    Parcels are slightly buffered so that neighbours separated by a ditch or
    road merge, unioned, then shrunk back (a morphological closing). Tiny
    results and tiny holes are dropped; they would be invisible at overview zooms.
    """
    prepared = []
    for geometry in geometries:
        if geometry.is_empty:
            continue
        if not geometry.is_valid:
            # BRP data contains self-intersecting rings that make GEOS ops fail.
            geometry = make_valid(geometry)
            if geometry.is_empty:
                continue
        simplified = geometry.simplify(simplify_tolerance, preserve_topology=True)
        if simplified.is_empty:
            continue
        prepared.append(simplified.buffer(close_distance, quad_segs=2, join_style="mitre"))

    if not prepared:
        return None

    merged = unary_union(prepared).buffer(-close_distance, quad_segs=2, join_style="mitre")
    merged = merged.simplify(simplify_tolerance, preserve_topology=True)

    pieces: list[Polygon] = []
    for polygon in _polygons(merged):
        if polygon.area < min_area:
            continue
        holes = [ring for ring in polygon.interiors if Polygon(ring).area >= min_area]
        pieces.append(Polygon(polygon.exterior, holes))

    if not pieces:
        return None

    result: BaseGeometry = pieces[0] if len(pieces) == 1 else MultiPolygon(pieces)
    if not result.is_valid:
        # Dropping holes/simplifying can leave self-touching rings behind.
        pieces = [
            polygon
            for polygon in _polygons(make_valid(result))
            if polygon.area >= min_area
        ]
        if not pieces:
            return None
        result = pieces[0] if len(pieces) == 1 else MultiPolygon(pieces)
    return result


class Command(BaseCommand):
    help = (
        "Export a dissolved (merged per crop) GeoJSON for low-zoom overview tiles. "
        "Parcels are merged per grid cell and gewascode, which keeps overview tiles "
        "small without dropping parcels."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--output",
            type=str,
            default=str(settings.BASE_DIR / "data" / "gewaspercelen_overview.geojson"),
            help="Output file path (default: data/gewaspercelen_overview.geojson)",
        )
        parser.add_argument("--year", type=int, default=None, help="Filter to a single year.")
        parser.add_argument("--bbox", type=str, default=None, help=BBOX_ARGUMENT_HELP)
        parser.add_argument(
            "--cell-size",
            type=float,
            default=DEFAULT_CELL_SIZE,
            help=f"Grid cell size in degrees (default: {DEFAULT_CELL_SIZE}).",
        )
        parser.add_argument(
            "--close-distance",
            type=float,
            default=DEFAULT_CLOSE_DISTANCE,
            help=(
                "Gaps up to twice this distance (degrees) between same-crop parcels "
                f"are closed (default: {DEFAULT_CLOSE_DISTANCE})."
            ),
        )
        parser.add_argument(
            "--simplify-tolerance",
            type=float,
            default=DEFAULT_SIMPLIFY_TOLERANCE,
            help=f"Simplify tolerance in degrees (default: {DEFAULT_SIMPLIFY_TOLERANCE}).",
        )
        parser.add_argument(
            "--min-area",
            type=float,
            default=DEFAULT_MIN_AREA,
            help=(
                "Drop dissolved pieces and holes smaller than this area in square "
                f"degrees (default: {DEFAULT_MIN_AREA})."
            ),
        )

    def handle(self, *args, **options) -> None:
        output_path = Path(options["output"])
        year = options.get("year")
        bbox = require_bbox(options.get("bbox")) or REGION_BBOXES["netherlands"]
        cell_size = options["cell_size"]
        dissolve_kwargs = {
            "close_distance": options["close_distance"],
            "simplify_tolerance": options["simplify_tolerance"],
            "min_area": options["min_area"],
        }

        base = Gewasperceel.objects.all()
        if EXCLUDED_MBTILES_CATEGORIES:
            base = base.exclude(category__in=EXCLUDED_MBTILES_CATEGORIES)
        if year is not None:
            base = base.filter(jaar=year)
        base = filter_queryset_by_bbox(base, bbox)

        min_lon, min_lat, max_lon, max_lat = bbox
        cols = math.ceil((max_lon - min_lon) / cell_size)
        rows = math.ceil((max_lat - min_lat) / cell_size)
        total_cells = cols * rows

        self.stdout.write(
            f"Dissolving parcels into {output_path} ({total_cells} cells of {cell_size} deg)..."
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        features_written = 0
        parcels_seen = 0
        cell_index = 0
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write('{\n  "type": "FeatureCollection",\n  "features": [\n')
            first = True

            for col in range(cols):
                x0 = min_lon + col * cell_size
                x1 = x0 + cell_size
                for row in range(rows):
                    cell_index += 1
                    y0 = min_lat + row * cell_size
                    y1 = y0 + cell_size

                    # Each parcel belongs to exactly one cell: the one holding its min corner.
                    queryset = base.filter(
                        min_lon__gte=x0, min_lon__lt=x1, min_lat__gte=y0, min_lat__lt=y1
                    ).only("gewascode", "gewas", "geometry")

                    groups: dict[int, tuple[str, list[BaseGeometry]]] = {}
                    for parcel in queryset.iterator(chunk_size=5000):
                        parcels_seen += 1
                        entry = groups.setdefault(parcel.gewascode, (parcel.gewas, []))
                        entry[1].append(shape(json.loads(parcel.geometry)))

                    for gewascode, (gewas, geometries) in groups.items():
                        dissolved = dissolve_geometries(geometries, **dissolve_kwargs)
                        if dissolved is None:
                            continue
                        try:
                            dissolved = set_precision(dissolved, 1e-6)
                        except GEOSException:
                            # Coordinate rounding is only a size optimisation.
                            logger.warning(
                                "set_precision failed for gewascode=%s in cell %d; "
                                "writing unrounded geometry.",
                                gewascode,
                                cell_index,
                            )
                        feature = {
                            "type": "Feature",
                            "properties": {"gewascode": gewascode, "gewas": gewas},
                            "geometry": json.loads(to_geojson(dissolved)),
                        }
                        if not first:
                            handle.write(",\n")
                        first = False
                        handle.write("    ")
                        handle.write(
                            json.dumps(feature, ensure_ascii=False, separators=(",", ":"))
                        )
                        features_written += 1

                    if groups:
                        self.stdout.write(
                            f"  cell {cell_index}/{total_cells}: "
                            f"{parcels_seen} parcels -> {features_written} features"
                        )

            handle.write("\n  ]\n}\n")

        logger.info(
            "Overview export complete: %d parcels -> %d features in %s",
            parcels_seen,
            features_written,
            output_path.absolute(),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Overview export complete: {parcels_seen} parcels -> "
                f"{features_written} features ({output_path.absolute()})"
            )
        )
