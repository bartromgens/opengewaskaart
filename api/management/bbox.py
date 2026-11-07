import math
from typing import Optional, Tuple

from django.core.management.base import CommandError

BBOX_CACHE_ROUND_DEG = 0.05
VIEWPORT_CACHE_MIN_SPAN_DEG = 0.5

REGION_BBOXES: dict[str, Tuple[float, float, float, float]] = {
    "netherlands": (3.2, 50.75, 7.2, 53.7),
    # Utrecht province (WGS84); use with export_to_mbtiles --bbox utrecht for dev.
    "utrecht": (4.792, 51.858, 5.627, 52.302),
    # Small test area around Gouda (~27 x 28 km).
    "gouda": (4.55, 51.90, 4.95, 52.15),
    # Test area from Deventer to Hengelo (~60 x 55 km), covers the 52.25N / 6.45E
    # overview cell edges where crop-colour dominance artefacts showed up.
    "deventer": (5.9, 52.0, 6.8, 52.5),
}

BBOX_ARGUMENT_HELP = (
    f"Bounding box filter. Either a region name ({', '.join(REGION_BBOXES)}) "
    "or coordinates as min_lon,min_lat,max_lon,max_lat"
)


def parse_bbox(bbox_str: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    if not bbox_str:
        return None

    lower = bbox_str.lower().strip()
    if lower in REGION_BBOXES:
        return REGION_BBOXES[lower]

    try:
        coords = [float(value) for value in bbox_str.split(",")]
        if len(coords) == 4:
            return coords[0], coords[1], coords[2], coords[3]
    except ValueError:
        pass

    return None


def require_bbox(
    bbox_str: Optional[str],
) -> Optional[Tuple[float, float, float, float]]:
    if not bbox_str:
        return None

    bbox = parse_bbox(bbox_str)
    if bbox is None:
        raise CommandError(
            f"Invalid bbox: {bbox_str}. Use a region name or "
            "min_lon,min_lat,max_lon,max_lat"
        )
    return bbox


def filter_queryset_by_bbox(queryset, bbox: Tuple[float, float, float, float]):
    min_lon, min_lat, max_lon, max_lat = bbox
    return queryset.filter(
        min_lon__lte=max_lon,
        max_lon__gte=min_lon,
        min_lat__lte=max_lat,
        max_lat__gte=min_lat,
    )


def round_bbox(
    bbox: Tuple[float, float, float, float],
    step: float = BBOX_CACHE_ROUND_DEG,
) -> Tuple[float, float, float, float]:
    min_lon, min_lat, max_lon, max_lat = bbox

    def floor_coord(value: float) -> float:
        return math.floor(value / step) * step

    def ceil_coord(value: float) -> float:
        return math.ceil(value / step) * step

    return (
        floor_coord(min_lon),
        floor_coord(min_lat),
        ceil_coord(max_lon),
        ceil_coord(max_lat),
    )


def parse_gewas_codes_param(raw: Optional[str]) -> tuple[Optional[list[int]], bool]:
    if raw is None or raw.strip() == "":
        return None, True
    codes: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            codes.append(int(part))
        except ValueError:
            return None, False
    if not codes:
        return None, True
    return codes, True


def bbox_spans(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    min_lon, min_lat, max_lon, max_lat = bbox
    return max_lon - min_lon, max_lat - min_lat


def is_small_viewport_bbox(bbox: Tuple[float, float, float, float]) -> bool:
    lon_span, lat_span = bbox_spans(bbox)
    return (
        lon_span < VIEWPORT_CACHE_MIN_SPAN_DEG
        and lat_span < VIEWPORT_CACHE_MIN_SPAN_DEG
    )


def prepare_summary_bbox(
    parsed: Tuple[float, float, float, float],
) -> Tuple[Tuple[float, float, float, float], bool]:
    """Return query bbox and whether Django cache may store the aggregation."""
    if is_small_viewport_bbox(parsed):
        return parsed, False
    return round_bbox(parsed), True


def bbox_cache_key_part(bbox: Tuple[float, float, float, float]) -> str:
    return ",".join(f"{v:.4f}" for v in bbox)
