"""Helpers for gewascode → gebruik lookups (from GewasGebruik table)."""

from __future__ import annotations

from api.models import GewasGebruik


def gebruik_by_gewascode() -> dict[int, str]:
    """gewascode → gebruik string for all rows in GewasGebruik."""
    return dict(GewasGebruik.objects.values_list("gewascode", "gebruik"))
