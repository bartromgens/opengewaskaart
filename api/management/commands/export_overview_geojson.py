import json
import logging
import math
import multiprocessing
import os
from pathlib import Path
from typing import Callable, Iterable, Optional

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from shapely import from_geojson, set_precision, to_geojson
from shapely.errors import GEOSException
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree
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
    exclude: Optional[Callable[[BaseGeometry], Optional[BaseGeometry]]] = None,
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
    # Closing and hole-filling must not paint over parcels of other crops;
    # otherwise overlapping crop polygons are resolved by draw order and
    # whole cells flip to one colour. `exclude` only returns the foreign
    # parcels that actually touch `result`, which keeps the difference cheap.
    to_remove = exclude(result) if exclude is not None else None
    if to_remove is not None and not to_remove.is_empty:
        try:
            result = result.difference(to_remove)
        except GEOSException:
            result = make_valid(result).difference(make_valid(to_remove))
        pieces = [p for p in _polygons(result) if p.area >= min_area]
        if not pieces:
            return None
        result = pieces[0] if len(pieces) == 1 else MultiPolygon(pieces)
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
        parser.add_argument(
            "--workers",
            type=int,
            default=os.cpu_count() or 1,
            help="Parallel worker processes, one grid cell each (default: CPU count).",
        )

    def handle(self, *args, **options) -> None:
        output_path = Path(options["output"])
        year = options.get("year")
        bbox = require_bbox(options.get("bbox")) or REGION_BBOXES["netherlands"]
        cell_size = options["cell_size"]
        workers = max(1, options["workers"])
        dissolve_kwargs = {
            "close_distance": options["close_distance"],
            "simplify_tolerance": options["simplify_tolerance"],
            "min_area": options["min_area"],
        }

        min_lon, min_lat, max_lon, max_lat = bbox
        cols = math.ceil((max_lon - min_lon) / cell_size)
        rows = math.ceil((max_lat - min_lat) / cell_size)
        total_cells = cols * rows

        self.stdout.write(
            f"Dissolving parcels into {output_path} ({total_cells} cells of {cell_size} deg, "
            f"{workers} worker(s))..."
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        tasks = []
        for col in range(cols):
            for row in range(rows):
                x0 = min_lon + col * cell_size
                y0 = min_lat + row * cell_size
                tasks.append(
                    (
                        len(tasks) + 1,
                        (x0, x0 + cell_size, y0, y0 + cell_size),
                        year,
                        bbox,
                        dissolve_kwargs,
                    )
                )

        parcels_seen = 0
        cell_features: list[tuple[int, float, str]] = []
        pool = None
        if workers > 1:
            # Each worker must open its own database connection.
            connections.close_all()
            pool = multiprocessing.get_context("fork").Pool(workers)
            results = pool.imap(_process_cell, tasks)
        else:
            results = map(_process_cell, tasks)

        try:
            for cell_index, (parcel_count, features) in enumerate(results, start=1):
                parcels_seen += parcel_count
                cell_features.extend(features)
                if parcel_count:
                    self.stdout.write(
                        f"  cell {cell_index}/{total_cells}: "
                        f"{parcels_seen} parcels -> {len(cell_features)} features"
                    )
        finally:
            if pool is not None:
                pool.terminate()
                pool.join()

        # Features of overlapping crops are drawn in tile order. tippecanoe keeps
        # input order with --preserve-input-order, so write them in one global
        # crop order. The last drawn crop wins where crops mix inside a pixel, so the
        # largest crop (grassland) goes last and stays dominant when zoomed out;
        # smaller crops only show where they are dense. Per-cell orders would make
        # whole cells look dominated by whichever crop happened to be drawn last.
        area_per_crop: dict[int, float] = {}
        for code, area, _ in cell_features:
            area_per_crop[code] = area_per_crop.get(code, 0.0) + area
        rank = {
            code: index
            for index, code in enumerate(
                sorted(area_per_crop, key=lambda c: (area_per_crop[c], c))
            )
        }
        cell_features.sort(key=lambda item: rank[item[0]])

        features_written = len(cell_features)
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write('{\n  "type": "FeatureCollection",\n  "features": [\n')
            for index, (_, _, line) in enumerate(cell_features):
                if index:
                    handle.write(",\n")
                handle.write("    ")
                handle.write(line)
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


def _process_cell(task) -> tuple[int, list[tuple[int, float, str]]]:
    """Dissolve one grid cell; returns (parcel count, serialized features)."""
    cell_index, (x0, x1, y0, y1), year, bbox, dissolve_kwargs = task

    base = Gewasperceel.objects.all()
    if EXCLUDED_MBTILES_CATEGORIES:
        base = base.exclude(category__in=EXCLUDED_MBTILES_CATEGORIES)
    if year is not None:
        base = base.filter(jaar=year)
    base = filter_queryset_by_bbox(base, bbox)

    # Each parcel belongs to exactly one cell: the one holding its min corner.
    queryset = base.filter(
        min_lon__gte=x0, min_lon__lt=x1, min_lat__gte=y0, min_lat__lt=y1
    ).only("gewascode", "gewas", "geometry")

    names: dict[int, str] = {}
    raw: dict[int, list[str]] = {}
    parcel_count = 0
    for parcel in queryset.iterator(chunk_size=5000):
        parcel_count += 1
        names.setdefault(parcel.gewascode, parcel.gewas)
        raw.setdefault(parcel.gewascode, []).append(parcel.geometry)
    if not raw:
        return 0, []

    # Parse all geometries of a crop in one vectorised call.
    groups: dict[int, list[BaseGeometry]] = {
        code: list(from_geojson(np.array(strings, dtype=object)))
        for code, strings in raw.items()
    }
    del raw

    # Footprints of all parcels, to keep a crop's dissolved polygon from
    # covering parcels of other crops.
    all_geoms: list[BaseGeometry] = []
    all_codes: list[int] = []
    tree: Optional[STRtree] = None
    if len(groups) > 1:
        for code, geometries in groups.items():
            for g in geometries:
                if g.is_empty:
                    continue
                all_geoms.append(g if g.is_valid else make_valid(g))
                all_codes.append(code)
        tree = STRtree(all_geoms)

    def make_exclude(code: int):
        def exclude(region: BaseGeometry) -> Optional[BaseGeometry]:
            hits = tree.query(region, predicate="intersects")
            foreign = [all_geoms[i] for i in hits if all_codes[i] != code]
            return unary_union(foreign) if foreign else None

        return exclude

    dissolved_groups = []
    for code, geometries in groups.items():
        dissolved = dissolve_geometries(
            geometries,
            exclude=make_exclude(code) if tree else None,
            **dissolve_kwargs,
        )
        if dissolved is not None:
            dissolved_groups.append((code, names[code], dissolved))

    # Large areas first so small crops are drawn on top.
    dissolved_groups.sort(key=lambda item: item[2].area, reverse=True)

    lines: list[tuple[int, float, str]] = []
    for code, gewas, dissolved in dissolved_groups:
        area = dissolved.area
        try:
            dissolved = set_precision(dissolved, 1e-6)
        except GEOSException:
            # Coordinate rounding is only a size optimisation.
            logger.warning(
                "set_precision failed for gewascode=%s in cell %d; "
                "writing unrounded geometry.",
                code,
                cell_index,
            )
        feature = {
            "type": "Feature",
            "properties": {"gewascode": code, "gewas": gewas},
            "geometry": json.loads(to_geojson(dissolved)),
        }
        lines.append(
            (code, area, json.dumps(feature, ensure_ascii=False, separators=(",", ":")))
        )
    return parcel_count, lines
