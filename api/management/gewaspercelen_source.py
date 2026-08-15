from pathlib import Path

from django.conf import settings

GPKG_FILENAME = "brpgewaspercelen_definitief_{year}.gpkg"
DEFAULT_SOURCE_URL = (
    "https://service.pdok.nl/rvo/gewaspercelen/atom/downloads/" + GPKG_FILENAME
)

# RD New bbox covering the Netherlands (EPSG:28992).
NETHERLANDS_RD_BBOX: tuple[float, float, float, float] = (
    0,
    300000,
    280000,
    625000,
)

YEAR_ARGUMENT_HELP = "Reference year of the dataset (e.g. 2025)."


def default_source_url(year: int) -> str:
    return DEFAULT_SOURCE_URL.format(year=year)


def default_gpkg_path(year: int) -> Path:
    return settings.BASE_DIR / "data" / "gpkg" / GPKG_FILENAME.format(year=year)


def add_year_argument(parser) -> None:
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help=YEAR_ARGUMENT_HELP,
    )


def add_source_url_argument(parser) -> None:
    parser.add_argument(
        "--source-url",
        type=str,
        default=None,
        help="Override the PDOK GeoPackage URL.",
    )
