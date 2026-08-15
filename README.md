# OpenGewasKaart

Interactive map showing BRP Gewaspercelen (agricultural crop parcels) across the Netherlands.

**Stack:** Django + Django REST Framework (backend) · Angular + Angular Material + MapLibre GL (frontend) · tippecanoe + tileserver-gl (vector tiles)

## Data source

- **Gewaspercelen** — [Basisregistratie Gewaspercelen (BRP)](https://service.pdok.nl/rvo/gewaspercelen/atom/basisregistratie_gewaspercelen_brp.xml) via PDOK (RVO). Annual datasets with crop type per parcel, reference date 15 May.

## Prerequisites

- Python 3.12+
- Node.js (for the Angular frontend)
- [GDAL](https://gdal.org/) with `ogr2ogr` (for data ingestion)
- [tippecanoe](https://github.com/felt/tippecanoe) v2.80+ (for MBTiles export)
- Docker (for tileserver-gl)

Tippecanoe is looked up on the system `PATH` by default (see `TIPPECANOE_PATH` in [`config/settings.py`](config/settings.py)). Set `TIPPECANOE_PATH` in `config/settings_local.py` if tippecanoe isn't on your `PATH`.

## Setup (first time)

```bash
# Backend
virtualenv --python=python3.12 env
source env/bin/activate
pip install -r requirements.txt
cp config/settings_local.py.example config/settings_local.py
# Edit config/settings_local.py — set SECRET_KEY
python manage.py migrate

# Frontend
cd client
npm install
cd ..
```

## Run development environment

You need three processes running — use separate terminals:

**Terminal 1 — Django API** (http://localhost:8000)

```bash
source env/bin/activate
python manage.py runserver
```

**Terminal 2 — tileserver-gl** (http://localhost:8080)

```bash
docker compose up
```

**Terminal 3 — Angular frontend** (http://localhost:4200)

```bash
cd client
npm start
```

Open http://localhost:4200 in your browser. The frontend proxies `/api` to Django; vector tiles are loaded directly from tileserver on port 8080.

| Service      | URL                                      |
|--------------|------------------------------------------|
| Frontend     | http://localhost:4200                    |
| Django API   | http://localhost:8000/api/               |
| Tileserver   | http://localhost:8080/                   |
| TileJSON     | http://localhost:8080/data/gewaspercelen.json |

After changing parcel data, re-export MBTiles and restart tileserver (or `docker compose restart`) to see updates on the map.

## Management commands

### `ingest_gewaspercelen` — load parcels into the database

Reads a bbox subset from the PDOK GeoPackage for a given year. Coordinates are **RD New (EPSG:28992)**: `xmin ymin xmax ymax`.

```bash
python manage.py ingest_gewaspercelen \
  --year 2025 \
  --bbox 155000 463000 157000 465000
```

This example covers a small area northeast of Amersfoort. Without `--gpkg`, the command streams the remote GeoPackage via GDAL's `/vsicurl/` driver (no full multi-GB download). That works well for small dev areas, but large bboxes are slow over HTTP because GeoPackage spatial indexing only performs well on a local file. Re-running is idempotent (duplicates are skipped).

For larger areas, download the GeoPackage once and pass `--gpkg`:

```bash
python manage.py ingest_gewaspercelen \
  --year 2025 \
  --gpkg data/gpkg/brpgewaspercelen_definitief_2025.gpkg \
  --bbox 114241 429919 171506 479588
```

### `download_gewaspercelen_gpkg` — download the annual GeoPackage

Downloads the ~2.9 GB PDOK GeoPackage to `data/gpkg/` (skipped if the file already exists with matching size):

```bash
python manage.py download_gewaspercelen_gpkg --year 2025
```

Use `--force` to re-download.

### `ingest_gewaspercelen_grid` — ingest the full Netherlands

Splits the Netherlands into a grid of 25 km cells and ingests each cell from a local GeoPackage. Failed cells are logged and can be retried individually. Re-running the full grid is safe (duplicates are skipped).

```bash
python manage.py download_gewaspercelen_gpkg --year 2025
python manage.py ingest_gewaspercelen_grid \
  --year 2025 \
  --gpkg data/gpkg/brpgewaspercelen_definitief_2025.gpkg
```

This is a long-running batch job (likely 30–90 minutes depending on hardware). Run it in `tmux`, `screen`, or with `nohup`. Progress is written to `log/management.log`.

Useful options:

- `--cell-size 25000` — grid cell size in meters (default: 25000)
- `--bbox xmin ymin xmax ymax` — limit to a sub-region in RD New coordinates
- `--timeout 120` — per-cell ogr2ogr timeout in seconds

### `export_to_mbtiles` — generate vector tiles for the map

Exports database rows to GeoJSON and converts to MBTiles with tippecanoe. Output goes to `data/gewaspercelen.mbtiles` for tileserver-gl.

```bash
python manage.py export_to_mbtiles --force
```

Useful options:

- `--year 2025` — export a single reference year
- `--bbox netherlands` or `--bbox min_lon,min_lat,max_lon,max_lat` — limit export area (WGS84)
- `--force` — overwrite existing MBTiles file

Requires tippecanoe v2.80 or newer.

## Typical workflow

**Small dev area**

1. **Ingest** parcel data for your area (`ingest_gewaspercelen`)
2. **Export** to MBTiles (`export_to_mbtiles --force`)
3. **Start** tileserver, Django, and Angular (see above)
4. **Browse** the map at http://localhost:4200

**Full Netherlands**

1. **Download** the annual GeoPackage (`download_gewaspercelen_gpkg`)
2. **Ingest** in grid cells (`ingest_gewaspercelen_grid`)
3. **Export** to MBTiles (`export_to_mbtiles --force --bbox netherlands`)
4. **Start** services and browse the map

When you ingest new data or change the export area, repeat the ingest and export steps and restart tileserver.

## Map behaviour

- Parcels are rendered from vector tiles (MBTiles via tileserver-gl), not raw GeoJSON.
- Fill color is based on crop `category` (see `client/src/app/crop-colors.ts`).
- Click a parcel to highlight it and load details from `GET /api/percelen/<id>/`.
- Tile feature properties include `id`, `jaar`, `gewascode`, `gewas`, `category`, and `status` so client-side filtering can be added later with `map.setFilter()` without re-tiling.
