from typing import Optional, Tuple

from django.core.management.base import CommandError

REGION_BBOXES: dict[str, Tuple[float, float, float, float]] = {
    "netherlands": (3.2, 50.75, 7.2, 53.7),
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
