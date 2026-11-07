"""Helpers for gewascode → gebruik lookups (from GewasGebruik table)."""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache

from api.models import GewasGebruik

GEBRUIK_MAP_CACHE_KEY = "gebruik_by_gewascode"
GEBRUIK_CODES_CACHE_KEY = "gewas_gebruik_classified_codes"


def invalidate_gebruik_caches() -> None:
    cache.delete(GEBRUIK_MAP_CACHE_KEY)
    cache.delete(GEBRUIK_CODES_CACHE_KEY)


def gebruik_by_gewascode() -> dict[int, str]:
    cached = cache.get(GEBRUIK_MAP_CACHE_KEY)
    if cached is not None:
        return cached
    data = dict(GewasGebruik.objects.values_list("gewascode", "gebruik"))
    cache.set(GEBRUIK_MAP_CACHE_KEY, data, settings.SUMMARY_CACHE_SECONDS)
    return data


def gewas_gebruik_classified_codes() -> set[int]:
    cached = cache.get(GEBRUIK_CODES_CACHE_KEY)
    if cached is not None:
        return cached
    codes = set(GewasGebruik.objects.values_list("gewascode", flat=True))
    cache.set(GEBRUIK_CODES_CACHE_KEY, codes, settings.SUMMARY_CACHE_SECONDS)
    return codes
