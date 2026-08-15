from typing import Iterator


def iter_grid_cells(
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
    cell_size: float,
) -> Iterator[tuple[float, float, float, float]]:
    if cell_size <= 0:
        raise ValueError("cell_size must be positive")

    y = ymin
    while y < ymax:
        y_end = min(y + cell_size, ymax)
        x = xmin
        while x < xmax:
            x_end = min(x + cell_size, xmax)
            yield x, y, x_end, y_end
            x = x_end
        y = y_end
