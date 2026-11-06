"""
Seed rules for BRP gewascode → veevoer/voedsel/gemengd/niet_voedsel/onbekend.

Used by migrations and tests. The migration only creates rows that are missing
(get_or_create) so manual admin edits are preserved.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from api.models import GewasGebruik

if TYPE_CHECKING:
    from django.db.models import QuerySet

G = GewasGebruik

# --- Explicit gewascode → gebruik (high-volume and ambiguous cases) ---

EXPLICIT_GEBRUIK: dict[int, str] = {
    # Aardappelen
    2014: G.GEBRUIK_VOEDSEL,
    2015: G.GEBRUIK_VOEDSEL,
    2016: G.GEBRUIK_VOEDSEL,
    2017: G.GEBRUIK_GEMENGD,
    2025: G.GEBRUIK_NIET_VOEDSEL,
    # Granen / korrel (geen eindgebruik in BRP → gemengd)
    233: G.GEBRUIK_GEMENGD,
    234: G.GEBRUIK_GEMENGD,
    235: G.GEBRUIK_GEMENGD,
    236: G.GEBRUIK_GEMENGD,
    238: G.GEBRUIK_GEMENGD,
    314: G.GEBRUIK_GEMENGD,
    7130: G.GEBRUIK_GEMENGD,
    7129: G.GEBRUIK_GEMENGD,
    7131: G.GEBRUIK_GEMENGD,
    2652: G.GEBRUIK_GEMENGD,
    382: G.GEBRUIK_GEMENGD,
    670: G.GEBRUIK_GEMENGD,
    6636: G.GEBRUIK_GEMENGD,
    3510: G.GEBRUIK_GEMENGD,
    381: G.GEBRUIK_GEMENGD,
    1022: G.GEBRUIK_GEMENGD,
    247: G.GEBRUIK_GEMENGD,
    246: G.GEBRUIK_GEMENGD,
    636: G.GEBRUIK_GEMENGD,
    1927: G.GEBRUIK_GEMENGD,
    7124: G.GEBRUIK_GEMENGD,
    1922: G.GEBRUIK_GEMENGD,
    1923: G.GEBRUIK_GEMENGD,
    # Bieten
    256: G.GEBRUIK_VOEDSEL,
    257: G.GEBRUIK_VEEVOER,
    # Mais
    259: G.GEBRUIK_VEEVOER,
    316: G.GEBRUIK_GEMENGD,
    317: G.GEBRUIK_VEEVOER,
    814: G.GEBRUIK_VOEDSEL,
    1935: G.GEBRUIK_VEEVOER,
    2032: G.GEBRUIK_NIET_VOEDSEL,
    # Grasland
    265: G.GEBRUIK_VEEVOER,
    266: G.GEBRUIK_VEEVOER,
    331: G.GEBRUIK_VEEVOER,
    332: G.GEBRUIK_NIET_VOEDSEL,
    1926: G.GEBRUIK_GEMENGD,
    3805: G.GEBRUIK_NIET_VOEDSEL,
    # Voeder / peul
    258: G.GEBRUIK_VEEVOER,
    803: G.GEBRUIK_VEEVOER,
    802: G.GEBRUIK_GEMENGD,
    800: G.GEBRUIK_VEEVOER,
    801: G.GEBRUIK_GEMENGD,
    657: G.GEBRUIK_VEEVOER,
    311: G.GEBRUIK_GEMENGD,
    308: G.GEBRUIK_GEMENGD,
    242: G.GEBRUIK_GEMENGD,
    241: G.GEBRUIK_GEMENGD,
    7121: G.GEBRUIK_GEMENGD,
    7137: G.GEBRUIK_GEMENGD,
    665: G.GEBRUIK_GEMENGD,
    663: G.GEBRUIK_GEMENGD,
    666: G.GEBRUIK_GEMENGD,
    854: G.GEBRUIK_VOEDSEL,
    853: G.GEBRUIK_GEMENGD,
    244: G.GEBRUIK_VOEDSEL,
    3519: G.GEBRUIK_VEEVOER,
    516: G.GEBRUIK_NIET_VOEDSEL,
    # Braak / tijdelijk
    3802: G.GEBRUIK_NIET_VOEDSEL,
    3801: G.GEBRUIK_NIET_VOEDSEL,
    2300: G.GEBRUIK_NIET_VOEDSEL,
    6798: G.GEBRUIK_NIET_VOEDSEL,
    6794: G.GEBRUIK_NIET_VOEDSEL,
    # Natuur / overige niet voedselketen
    335: G.GEBRUIK_NIET_VOEDSEL,
    1936: G.GEBRUIK_NIET_VOEDSEL,
    6522: G.GEBRUIK_NIET_VOEDSEL,
    662: G.GEBRUIK_NIET_VOEDSEL,
    3055: G.GEBRUIK_NIET_VOEDSEL,
    794: G.GEBRUIK_NIET_VOEDSEL,
    7127: G.GEBRUIK_NIET_VOEDSEL,
}


def _normalize(s: str) -> str:
    return s.lower()


def classify_gewas(gewascode: int, gewas: str, category: str) -> str:
    """Return a GEBRUIK_* string for a parcel row."""
    if gewascode in EXPLICIT_GEBRUIK:
        return EXPLICIT_GEBRUIK[gewascode]

    g = _normalize(gewas)
    cat = _normalize(category)

    if cat == "grasland":
        return G.GEBRUIK_VEEVOER
    if cat == "braakland":
        return G.GEBRUIK_NIET_VOEDSEL
    if cat == "natuurterrein":
        return G.GEBRUIK_NIET_VOEDSEL
    if cat == "overige" and ("bos" in g or g.startswith("bos ")):
        return G.GEBRUIK_NIET_VOEDSEL

    niet_patterns = (
        "bloembollen",
        "bloemkwekerijgewassen",
        "bloemkwekerij",
        "vermeerdering",
        "wachtbed",
        "pot- en containerveld",
        "zaden en opkweekmateriaal",
        "droogbloemen",
        "hennep, vezel",
        "vlas, vezel",
        "miscanthus",
        "mais, energie",
        "groenbemesting",
        "vanggewas",
        "graszaad",
        "industriegras",
        "tijdelijk onbeteelde",
        "onbeteelde grond",
        "teeltverbod",
        "gewasresten (mulching)",
        "natuurterreinen",
        "sierteelt",
        "sierconiferen",
        "sierheesters",
        "laanbomen",
        "parkbomen",
        "buxus",
        "ericaceae",
        "planten, open grond",
        "planten, pot-",
        "boomgaard",
        "wilgenhakhout",
        "lisdodde",
        "rietland",
        "riet in",
        "voedselbos",
        "karwijzaad",
        "kanariezaad",
        "groene braak",
    )
    for p in niet_patterns:
        if p in g:
            return G.GEBRUIK_NIET_VOEDSEL

    if "grasland" in g:
        return G.GEBRUIK_VEEVOER
    if "voeder" in g:
        return G.GEBRUIK_VEEVOER
    if "silage" in g or "kolvensilage" in g:
        return G.GEBRUIK_VEEVOER
    if "groenvoedergewas" in g:
        return G.GEBRUIK_VEEVOER
    if "mais" in g or "maïs" in g:
        if "suiker" in g:
            return G.GEBRUIK_VOEDSEL
        if "energie" in g:
            return G.GEBRUIK_NIET_VOEDSEL
        return G.GEBRUIK_VEEVOER
    if "luzerne" in g:
        return G.GEBRUIK_VEEVOER
    if "drachtplanten" in g:
        return G.GEBRUIK_VEEVOER

    if "aardappel" in g or "aardappelen" in g:
        return G.GEBRUIK_VOEDSEL
    if "suikerbiet" in g:
        return G.GEBRUIK_VOEDSEL
    if g.startswith("uien"):
        return G.GEBRUIK_VOEDSEL
    if "consumptie" in g:
        return G.GEBRUIK_VOEDSEL
    voedsel_cues = (
        "asperges",
        "bonen",
        "erwten",
        "groente",
        "kool",
        "sla",
        "spinazie",
        "wortel",
        "peen",
        "prei",
        "tomat",
        "komkommer",
        "paprika",
        "meloen",
        "aardbei",
        "framboos",
        "besse",
        "kersen",
        "pruimen",
        "appels",
        "wijndruiven",
        "pompoen",
        "knoflook",
        "pastinaak",
        "schorseneren",
        "rabarber",
        "peren",
    )
    for cue in voedsel_cues:
        if cue in g:
            return G.GEBRUIK_VOEDSEL

    if any(
        x in g
        for x in (
            "tarwe",
            "gerst",
            "haver",
            "rogge",
            "triticale",
            "spelt",
            "boekweit",
            "teff",
        )
    ):
        return G.GEBRUIK_GEMENGD
    if "korrel" in g and "mais" not in g:
        return G.GEBRUIK_GEMENGD

    return G.GEBRUIK_ONBEKEND


def seed_gewas_gebruik_from_queryset(
    qs: QuerySet,
    GewasGebruikModel=None,
) -> int:
    """
    Insert GewasGebruik rows for distinct (gewascode, gewas) in qs via get_or_create.
    Returns number of rows created (not updated).

    Pass GewasGebruikModel from apps.get_model() inside data migrations.
    """
    GG = GewasGebruikModel or GewasGebruik

    distinct = qs.values_list("gewascode", "gewas", "category").distinct()
    created_count = 0
    for gewascode, gewas, category in distinct:
        gebruik = classify_gewas(int(gewascode), str(gewas), str(category))
        _obj, created = GG.objects.get_or_create(
            gewascode=int(gewascode),
            defaults={
                "gebruik": gebruik,
                "toelichting": "",
            },
        )
        if created:
            created_count += 1
    return created_count
