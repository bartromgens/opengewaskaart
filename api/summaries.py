from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, QuerySet, Sum

from api.brp_constants import EXCLUDED_MBTILES_CATEGORIES
from api.gebruik import gebruik_by_gewascode
from api.management.bbox import (
    bbox_cache_key_part,
    filter_queryset_by_bbox,
    parse_bbox,
    prepare_summary_bbox,
)
from api.models import GewasGebruik, Gewasperceel

GEWASSEN_SUMMARY_LIMIT_MAX = 50


def national_http_cache_headers() -> dict[str, str]:
    max_age = getattr(settings, "NATIONAL_HTTP_CACHE_SECONDS", 300)
    return {"Cache-Control": f"public, max-age={max_age}"}


def parse_jaar_param(jaar_param: str | None) -> int | None:
    if jaar_param is None:
        return None
    return int(jaar_param)


def gewassen_base_queryset(jaar: int | None) -> QuerySet[Gewasperceel]:
    queryset = Gewasperceel.objects.exclude(category__in=EXCLUDED_MBTILES_CATEGORIES)
    if jaar is not None:
        queryset = queryset.filter(jaar=jaar)
    return queryset


def fetch_gewassen_summary_rows(
    *,
    jaar_param: str | None,
    limit: int | None,
    bbox_param: str | None,
    gewas_codes: list[int] | None,
) -> tuple[list[dict[str, Any]], bool]:
    """
    Aggregate gewas rows for the API. Second value is True when the response
    is a national (no bbox) summary suitable for HTTP caching.
    """
    jaar = None if jaar_param is None else parse_jaar_param(jaar_param)
    queryset = gewassen_base_queryset(jaar)

    bbox: tuple[float, float, float, float] | None = None
    cache_aggregation = True
    if bbox_param is not None and bbox_param.strip() != "":
        parsed = parse_bbox(bbox_param.strip())
        if parsed is None:
            raise ValueError("invalid_bbox")
        bbox, cache_aggregation = prepare_summary_bbox(parsed)
        queryset = filter_queryset_by_bbox(queryset, bbox)

    if gewas_codes:
        queryset = queryset.filter(gewascode__in=gewas_codes)

    order_by = "-area_m2" if bbox is not None else "-parcel_count"
    aggregation = queryset.values("gewascode", "gewas", "category").annotate(
        parcel_count=Count("id"), area_m2=Sum("area_m2")
    ).order_by(order_by)

    is_national = bbox is None
    rows: list[dict[str, Any]]
    if is_national or cache_aggregation:
        limit_key = str(limit) if limit is not None else ""
        bbox_key = bbox_cache_key_part(bbox) if bbox is not None else ""
        gewas_key = ",".join(str(c) for c in gewas_codes) if gewas_codes else ""
        cache_key = (
            f"gewassen_summary:{jaar_param}:{limit_key}:{bbox_key}:"
            f"{gewas_key}:{order_by}"
        )
        cached_rows = cache.get(cache_key)
        if cached_rows is None:
            rows_qs = aggregation[:limit] if limit is not None else aggregation
            cached_rows = list(rows_qs)
            cache.set(cache_key, cached_rows, settings.SUMMARY_CACHE_SECONDS)
        rows = cached_rows
    else:
        rows_qs = aggregation[:limit] if limit is not None else aggregation
        rows = list(rows_qs)

    return rows, is_national


def warm_gewassen_summary(
    *,
    jaar_param: str | None = None,
    limit: int | None = None,
) -> None:
    fetch_gewassen_summary_rows(
        jaar_param=jaar_param,
        limit=limit,
        bbox_param=None,
        gewas_codes=None,
    )


def fetch_categorieen_summary_rows(jaar_param: str | None) -> list[dict[str, Any]]:
    jaar = None if jaar_param is None else parse_jaar_param(jaar_param)
    cache_key = f"categorieen_summary:{jaar_param}"
    cached_rows = cache.get(cache_key)
    if cached_rows is not None:
        return cached_rows

    queryset = gewassen_base_queryset(jaar)
    rows = list(
        queryset.values("category")
        .annotate(parcel_count=Count("id"), area_m2=Sum("area_m2"))
        .order_by("-parcel_count")
    )
    cache.set(cache_key, rows, settings.SUMMARY_CACHE_SECONDS)
    return rows


def fetch_gebruik_summary_rows(jaar_param: str | None) -> list[dict[str, Any]]:
    cache_key = f"gebruik_totals:{jaar_param}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Roll up the national gewas summary. Grouping by gewascode alone makes
    # SQLite use the non-covering gewascode index and read every geometry.
    rows, _is_national = fetch_gewassen_summary_rows(
        jaar_param=jaar_param,
        limit=None,
        bbox_param=None,
        gewas_codes=None,
    )
    gebruik_map = gebruik_by_gewascode()

    parcels: dict[str, int] = defaultdict(int)
    areas: dict[str, float] = defaultdict(float)
    for row in rows:
        code = int(row["gewascode"])
        g = gebruik_map.get(code, GewasGebruik.GEBRUIK_ONBEKEND)
        parcels[g] += row["parcel_count"]
        am = row["area_m2"]
        if am is not None:
            areas[g] += float(am)

    order = (
        GewasGebruik.GEBRUIK_VEEVOER,
        GewasGebruik.GEBRUIK_VOEDSEL,
        GewasGebruik.GEBRUIK_GEMENGD,
        GewasGebruik.GEBRUIK_NIET_VOEDSEL,
        GewasGebruik.GEBRUIK_ONBEKEND,
    )
    seen = set(order)
    out: list[dict[str, Any]] = []
    for g in order:
        pc = parcels.get(g, 0)
        am2 = areas.get(g, 0.0)
        out.append(
            {
                "gebruik": g,
                "parcel_count": pc,
                "area_m2": am2 if am2 > 0 else None,
            }
        )
    for g in sorted(set(parcels) | set(areas)):
        if g in seen:
            continue
        pc = parcels.get(g, 0)
        am2 = areas.get(g, 0.0)
        out.append(
            {
                "gebruik": g,
                "parcel_count": pc,
                "area_m2": am2 if am2 > 0 else None,
            }
        )
    cache.set(cache_key, out, settings.SUMMARY_CACHE_SECONDS)
    return out


def warm_all_national_summaries(jaar_param: str | None = None) -> None:
    warm_gewassen_summary(jaar_param=jaar_param, limit=8)
    warm_gewassen_summary(jaar_param=jaar_param, limit=None)
    fetch_gebruik_summary_rows(jaar_param)
    fetch_categorieen_summary_rows(jaar_param)
