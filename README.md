# OpenGewasKaart

Interactive map showing BRP Gewaspercelen (agricultural crop parcels) across the Netherlands.

**Stack:** Django + Django REST Framework (backend) · Angular + Angular Material + MapLibre GL (frontend) · tippecanoe + tileserver-gl (vector tiles)

## Data source

- **Gewaspercelen** — [Basisregistratie Gewaspercelen (BRP)](https://service.pdok.nl/rvo/gewaspercelen/atom/basisregistratie_gewaspercelen_brp.xml) via PDOK (RVO). Annual datasets with crop type per parcel, reference date 15 May.

## Setup

### Prerequisites

- Python 3.12+
- Node.js (for the Angular frontend)
- [GDAL](https://gdal.org/) with `ogr2ogr` (for data ingestion)
- [tippecanoe](https://github.com/felt/tippecanoe) v2.80+ (for MBTiles export)
- Docker (for tileserver-gl)

Install tippecanoe:

```bash
git clone https://github.com/felt/tippecanoe.git
cd tippecanoe
make -j
sudo make install
```

### Backend

```bash
virtualenv --python=python3.12 env
source env/bin/activate
pip install -r requirements.txt
cp config/settings_local.py.example config/settings_local.py
# Edit config/settings_local.py — set SECRET_KEY
python manage.py migrate
python manage.py runserver
```

The API runs on http://localhost:8000.

### Ingesting BRP Gewaspercelen data

Ingest a bbox subset from the PDOK GeoPackage for a given year (RD New / EPSG:28992 coordinates):

```bash
python manage.py ingest_gewaspercelen \
  --year 2025 \
  --bbox 155000 463000 157000 465000
```

This example bbox covers a small area northeast of Amersfoort. The command reads the remote GeoPackage via GDAL's `/vsicurl/` driver (no full multi-GB download), reprojects geometry to WGS84, and stores it as GeoJSON text in the database. Re-running the same command is idempotent (duplicates are skipped).

### Export to MBTiles

Export the database to GeoJSON and convert to MBTiles for tileserver-gl:

```bash
python manage.py export_to_mbtiles
```

Useful options:

- `--year 2025` — export a single reference year
- `--bbox netherlands` or `--bbox min_lon,min_lat,max_lon,max_lat` — limit export area
- `--output path` — MBTiles output (default: `data/gewaspercelen.mbtiles`)
- `--geojson-output path` — intermediate GeoJSON (default: `data/gewaspercelen.geojson`)
- `--min-zoom`, `--max-zoom` — zoom range (default 8–16)
- `--layer-name` — layer name in MBTiles (default: `percelen`)
- `--force` — overwrite existing file

Requires tippecanoe v2.80 or newer installed.

### Tileserver

Put MBTiles in `data/` and run tileserver-gl:

```bash
docker compose up
```

Tiles: http://localhost:8080/  
TileJSON: http://localhost:8080/data/gewaspercelen.json

### Frontend

```bash
cd client
npm install
npm start
```

The Angular dev server runs on http://localhost:4200 and proxies:

- `/api` → Django backend on port 8000
- `/tiles` → tileserver-gl on port 8080

## Map behaviour

- Parcels are rendered from vector tiles (MBTiles via tileserver-gl), not raw GeoJSON.
- Fill color is based on crop `category` (see `client/src/app/crop-colors.ts`).
- Click a parcel to highlight it and load full details from `GET /api/percelen/<id>/`.
- Tile feature properties include `id`, `jaar`, `gewascode`, `gewas`, `category`, and `status` so client-side filtering can be added later with `map.setFilter()` without re-tiling.

## Development workflow

1. Ingest data for your test area.
2. Export to MBTiles: `python manage.py export_to_mbtiles --force`
3. Start tileserver: `docker compose up`
4. Start backend: `python manage.py runserver`
5. Start frontend: `cd client && npm start`
