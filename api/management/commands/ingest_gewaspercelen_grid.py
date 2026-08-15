import logging

from django.core.management.base import BaseCommand, CommandError

from api.management.grid import iter_grid_cells
from api.management.gewaspercelen_ingest import ingest_parcels, require_gpkg_path, require_rd_bbox
from api.management.gewaspercelen_source import NETHERLANDS_RD_BBOX, add_year_argument

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Ingest BRP Gewaspercelen from a local GeoPackage by splitting the area "
        "into a grid of smaller bounding boxes."
    )

    def add_arguments(self, parser) -> None:
        add_year_argument(parser)
        parser.add_argument(
            "--gpkg",
            type=str,
            required=True,
            help="Path to a local GeoPackage file.",
        )
        parser.add_argument(
            "--bbox",
            nargs=4,
            type=float,
            metavar=("XMIN", "YMIN", "XMAX", "YMAX"),
            default=NETHERLANDS_RD_BBOX,
            help=(
                "Overall bounding box in EPSG:28992 (RD New) coordinates "
                f"(default: {NETHERLANDS_RD_BBOX})."
            ),
        )
        parser.add_argument(
            "--cell-size",
            type=float,
            default=25000,
            help="Grid cell size in meters (default: 25000).",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=120,
            help="Timeout in seconds for each cell ingest (default: 120).",
        )

    def handle(self, *args, **options) -> None:
        year = options["year"]
        gpkg_path = require_gpkg_path(options["gpkg"])
        xmin, ymin, xmax, ymax = require_rd_bbox(*options["bbox"])
        cell_size = options["cell_size"]
        timeout = options["timeout"]

        if cell_size <= 0:
            raise CommandError("Invalid cell-size: must be positive.")

        cells = list(iter_grid_cells(xmin, ymin, xmax, ymax, cell_size))
        total_cells = len(cells)

        logger.info(
            "Starting grid ingest: year=%s gpkg=%s cells=%d cell_size=%s bbox=(%s, %s, %s, %s)",
            year,
            gpkg_path,
            total_cells,
            cell_size,
            xmin,
            ymin,
            xmax,
            ymax,
        )
        self.stdout.write(
            f"Ingesting year {year} from {gpkg_path} "
            f"in {total_cells} cells ({cell_size:.0f} m)..."
        )

        failed_cells: list[tuple[tuple[float, float, float, float], str]] = []
        total_fetched = 0
        total_created = 0
        total_skipped = 0

        for index, cell in enumerate(cells, start=1):
            cell_label = f"cell {index}/{total_cells} {cell}"
            self.stdout.write(f"Processing {cell_label}...")
            logger.info("Processing %s", cell_label)

            try:
                result = ingest_parcels(
                    year=year,
                    bbox=cell,
                    gpkg_path=gpkg_path,
                    timeout=timeout,
                )
            except CommandError as exc:
                error_message = str(exc)
                failed_cells.append((cell, error_message))
                logger.error("Failed %s: %s", cell_label, error_message)
                self.stdout.write(self.style.ERROR(f"Failed {cell_label}: {error_message}"))
                continue

            total_fetched += result.fetched
            total_created += result.created
            total_skipped += result.skipped

            summary = (
                f"Completed {cell_label}: fetched={result.fetched} created={result.created} "
                f"skipped={result.skipped} (running totals: fetched={total_fetched} "
                f"created={total_created} skipped={total_skipped})"
            )
            logger.info(summary)
            self.stdout.write(summary)

        self.stdout.write("")
        if failed_cells:
            self.stdout.write(
                self.style.ERROR(
                    f"Grid ingest finished with {len(failed_cells)} failed cell(s)."
                )
            )
            for cell, error_message in failed_cells:
                self.stdout.write(
                    self.style.ERROR(
                        f"  {cell}: {error_message}"
                    )
                )
            logger.error(
                "Grid ingest finished with %d failed cell(s).",
                len(failed_cells),
            )
        else:
            message = (
                f"Grid ingest complete: {total_cells} cells, "
                f"{total_fetched} fetched, {total_created} created, "
                f"{total_skipped} skipped."
            )
            logger.info(message)
            self.stdout.write(self.style.SUCCESS(message))
