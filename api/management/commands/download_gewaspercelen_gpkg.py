import logging
import urllib.error
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from api.management.gewaspercelen_source import (
    add_source_url_argument,
    add_year_argument,
    default_gpkg_path,
    default_source_url,
)

logger = logging.getLogger(__name__)

PROGRESS_INTERVAL_BYTES = 100 * 1024 * 1024
CHUNK_SIZE = 8 * 1024 * 1024


def fetch_remote_content_length(url: str) -> int | None:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is None:
                return None
            return int(content_length)
    except (urllib.error.URLError, ValueError) as exc:
        raise CommandError(f"Failed to fetch remote file metadata: {exc}") from exc


def download_file(url: str, output_path: Path, stdout) -> None:
    request = urllib.request.Request(url, method="GET")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".part")

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content_length = response.headers.get("Content-Length")
            total_bytes = int(content_length) if content_length else None
            downloaded = 0
            last_logged = 0

            with temp_path.open("wb") as handle:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    handle.write(chunk)
                    downloaded += len(chunk)

                    if downloaded - last_logged >= PROGRESS_INTERVAL_BYTES:
                        last_logged = downloaded
                        if total_bytes:
                            pct = 100 * downloaded / total_bytes
                            message = (
                                f"Downloaded {downloaded / (1024 * 1024):.0f} MB "
                                f"({pct:.1f}%)..."
                            )
                        else:
                            message = f"Downloaded {downloaded / (1024 * 1024):.0f} MB..."
                        stdout.write(message)
                        logger.info(message)

        temp_path.replace(output_path)
    except urllib.error.URLError as exc:
        temp_path.unlink(missing_ok=True)
        raise CommandError(f"Download failed: {exc}") from exc


class Command(BaseCommand):
    help = "Download the PDOK BRP Gewaspercelen GeoPackage for a reference year."

    def add_arguments(self, parser) -> None:
        add_year_argument(parser)
        add_source_url_argument(parser)
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help=(
                "Output file path "
                "(default: data/gpkg/brpgewaspercelen_definitief_<year>.gpkg)."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-download even if the local file already exists.",
        )

    def handle(self, *args, **options) -> None:
        year = options["year"]
        source_url = options["source_url"] or default_source_url(year)
        output_path = Path(options["output"] or default_gpkg_path(year))
        force = options["force"]

        logger.info(
            "Starting GPKG download: year=%s output=%s source=%s force=%s",
            year,
            output_path,
            source_url,
            force,
        )
        self.stdout.write(f"Source: {source_url}")
        self.stdout.write(f"Output: {output_path}")

        remote_size = fetch_remote_content_length(source_url)
        if remote_size is not None:
            self.stdout.write(f"Remote size: {remote_size / (1024 * 1024):.1f} MB")

        if not force and output_path.exists():
            local_size = output_path.stat().st_size
            if remote_size is not None and local_size == remote_size:
                message = (
                    f"Local file already exists with matching size "
                    f"({local_size / (1024 * 1024):.1f} MB). Skipping download."
                )
                logger.info(message)
                self.stdout.write(self.style.SUCCESS(message))
                return
            if remote_size is None:
                message = (
                    f"Local file already exists ({local_size / (1024 * 1024):.1f} MB) "
                    "and remote size is unknown. Use --force to re-download."
                )
                logger.info(message)
                self.stdout.write(self.style.SUCCESS(message))
                return

        self.stdout.write("Downloading GeoPackage...")
        download_file(source_url, output_path, self.stdout)

        final_size = output_path.stat().st_size
        if remote_size is not None and final_size != remote_size:
            output_path.unlink(missing_ok=True)
            raise CommandError(
                f"Download incomplete: expected {remote_size} bytes, got {final_size}."
            )

        message = f"Download complete: {output_path} ({final_size / (1024 * 1024):.1f} MB)"
        logger.info(message)
        self.stdout.write(self.style.SUCCESS(message))
