import re
import subprocess
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from api.management.bbox import BBOX_ARGUMENT_HELP
from api.management.utils import find_executable, resolve_executable_path

VersionTuple = Tuple[int, int, int]
TIPPECANOE_VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")

TIPPECANOE_NOT_FOUND_MESSAGE = (
    "tippecanoe is not installed or not in PATH.\n"
    "Install it:\n"
    "  Ubuntu/Debian: sudo apt-get install tippecanoe\n"
    "  macOS: brew install tippecanoe\n"
    "  Or build from source: https://github.com/felt/tippecanoe"
)

MBTILES_CONVERSION_OPTION_KEYS = (
    "min_zoom",
    "max_zoom",
    "layer_name",
    "force",
    "maximum_tile_bytes",
    "low_detail",
    "minimum_detail",
    "simplification",
    "no_coalesce",
    "no_drop_smallest",
    "bbox",
    "tippecanoe",
)


def format_version(version: VersionTuple) -> str:
    return f"{version[0]}.{version[1]}.{version[2]}"


def parse_tippecanoe_version(version_text: str) -> VersionTuple | None:
    match = TIPPECANOE_VERSION_PATTERN.search(version_text)
    if not match:
        return None
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3) or 0),
    )


def get_tippecanoe_version(tippecanoe_path: str) -> VersionTuple:
    try:
        result = subprocess.run(
            [tippecanoe_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CommandError(
            f"Failed to run tippecanoe version check at {tippecanoe_path}: {exc}"
        ) from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise CommandError(
            f"tippecanoe --version failed at {tippecanoe_path}"
            + (f": {stderr}" if stderr else "")
        )

    version_text = (result.stdout or result.stderr or "").strip()
    version = parse_tippecanoe_version(version_text)
    if version is None:
        raise CommandError(
            f"Could not parse tippecanoe version from output: {version_text!r}"
        )
    return version


def ensure_min_tippecanoe_version(
    tippecanoe_path: str,
    min_version: VersionTuple,
) -> str:
    version = get_tippecanoe_version(tippecanoe_path)
    if version < min_version:
        raise CommandError(
            f"tippecanoe {format_version(version)} found at {tippecanoe_path}, "
            f"but version {format_version(min_version)} or newer is required."
        )
    return format_version(version)


def default_tippecanoe_search_paths() -> list[str]:
    paths: list[str] = []
    configured = getattr(settings, "TIPPECANOE_PATH", None)
    if configured:
        paths.append(configured)
    paths.extend(
        [
            "/usr/local/bin/tippecanoe",
            "/usr/bin/tippecanoe",
            "/opt/homebrew/bin/tippecanoe",
        ]
    )
    return paths


def resolve_tippecanoe_path(tippecanoe_option: Optional[str] = None) -> str:
    configured = tippecanoe_option or getattr(settings, "TIPPECANOE_PATH", None)
    if configured:
        tippecanoe_path = resolve_executable_path(configured)
        if not Path(tippecanoe_path).exists():
            raise CommandError(f"tippecanoe not found at: {tippecanoe_path}")
        return tippecanoe_path

    return find_executable(
        "tippecanoe",
        default_tippecanoe_search_paths(),
        TIPPECANOE_NOT_FOUND_MESSAGE,
    )


def add_mbtiles_conversion_arguments(parser) -> None:
    parser.add_argument(
        "--min-zoom",
        type=int,
        default=getattr(settings, "VECTOR_TILE_MIN_ZOOM", 8),
        help=f"Minimum zoom level (default: {getattr(settings, 'VECTOR_TILE_MIN_ZOOM', 8)})",
    )
    parser.add_argument(
        "--max-zoom",
        type=int,
        default=getattr(settings, "VECTOR_TILE_MAX_ZOOM", 16),
        help=f"Maximum zoom level (default: {getattr(settings, 'VECTOR_TILE_MAX_ZOOM', 16)})",
    )
    parser.add_argument(
        "--layer-name",
        type=str,
        default="percelen",
        help="Layer name in MBTiles (default: percelen)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file if it exists",
    )
    parser.add_argument(
        "--maximum-tile-bytes",
        type=int,
        default=300_000,
        metavar="BYTES",
        help="Max size per tile in bytes (default: 300000).",
    )
    parser.add_argument(
        "--low-detail",
        type=int,
        default=12,
        metavar="DETAIL",
        help="Detail at zoom levels below max zoom (default: 12).",
    )
    parser.add_argument(
        "--minimum-detail",
        type=int,
        default=6,
        metavar="DETAIL",
        help="Minimum detail when a tile exceeds size limit (default: 6).",
    )
    parser.add_argument(
        "--simplification",
        type=float,
        default=30.0,
        metavar="SCALE",
        help="Simplification scale multiplier (default: 30.0).",
    )
    parser.add_argument(
        "--no-coalesce",
        action="store_true",
        help="Use --drop-densest-as-needed instead of --coalesce-densest-as-needed.",
    )
    parser.add_argument(
        "--no-drop-smallest",
        action="store_true",
        help="Don't use --drop-smallest-as-needed.",
    )
    parser.add_argument(
        "--bbox",
        type=str,
        default=None,
        help=BBOX_ARGUMENT_HELP,
    )
    parser.add_argument(
        "--tippecanoe",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to tippecanoe executable (default: from settings or PATH)",
    )


def mbtiles_conversion_kwargs(options: dict[str, Any]) -> dict[str, Any]:
    return {key: options[key] for key in MBTILES_CONVERSION_OPTION_KEYS if key in options}


def build_tippecanoe_command(
    *,
    tippecanoe_path: str,
    input_path: Path,
    output_path: Path,
    layer_name: str,
    min_zoom: int,
    max_zoom: int,
    maximum_tile_bytes: int,
    low_detail: int,
    minimum_detail: int,
    simplification: float,
    coalesce: bool,
    drop_smallest: bool,
    bbox: Optional[Tuple[float, float, float, float]],
    force: bool,
) -> list[str]:
    tippecanoe_cmd = [
        tippecanoe_path,
        "--output",
        str(output_path),
        "--layer",
        layer_name,
        "--minimum-zoom",
        str(min_zoom),
        "--maximum-zoom",
        str(max_zoom),
        "--maximum-tile-bytes",
        str(maximum_tile_bytes),
        "--low-detail",
        str(low_detail),
        "--minimum-detail",
        str(minimum_detail),
        "--use-attribute-for-id=id",
    ]

    if simplification != 1.0:
        tippecanoe_cmd.extend(["--simplification", str(simplification)])

    if coalesce:
        tippecanoe_cmd.append("--coalesce-densest-as-needed")
    else:
        tippecanoe_cmd.append("--drop-densest-as-needed")

    if drop_smallest:
        tippecanoe_cmd.append("--drop-smallest-as-needed")

    if bbox:
        min_lon, min_lat, max_lon, max_lat = bbox
        tippecanoe_cmd.extend(
            ["--clip-bounding-box", f"{min_lon},{min_lat},{max_lon},{max_lat}"]
        )

    tippecanoe_cmd.extend(
        [
            "--extend-zooms-if-still-dropping",
            str(input_path),
        ]
    )

    if force:
        tippecanoe_cmd.insert(-1, "--force")

    return tippecanoe_cmd


def run_tippecanoe(command: Iterable[str], stdout) -> None:
    try:
        with subprocess.Popen(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ) as proc:
            assert proc.stdout is not None
            for line in proc.stdout:
                stdout.write(line.rstrip())
            proc.wait()
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, list(command))
    except subprocess.CalledProcessError as exc:
        raise CommandError(f"tippecanoe failed with exit code {exc.returncode}") from exc
    except FileNotFoundError as exc:
        raise CommandError(TIPPECANOE_NOT_FOUND_MESSAGE) from exc


def prepare_tippecanoe(
    command: BaseCommand,
    tippecanoe_option: Optional[str],
) -> tuple[str, str]:
    tippecanoe_path = resolve_tippecanoe_path(tippecanoe_option)
    min_version = getattr(settings, "TIPPECANOE_MIN_VERSION", (2, 80, 0))
    tippecanoe_version = ensure_min_tippecanoe_version(tippecanoe_path, min_version)
    command.stdout.write(
        f"Using tippecanoe {tippecanoe_version} ({tippecanoe_path})"
    )
    return tippecanoe_path, tippecanoe_version
