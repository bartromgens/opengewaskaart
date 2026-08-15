# OpenGewasKaart

Interactive map showing BRP Gewaspercelen (agricultural crop parcels) across the Netherlands.

**Stack:** Django + Django REST Framework (backend) · Angular + Angular Material + MapLibre GL (frontend)

## Data source

- **Gewaspercelen** — [Basisregistratie Gewaspercelen (BRP)](https://service.pdok.nl/rvo/gewaspercelen/atom/basisregistratie_gewaspercelen_brp.xml) via PDOK (RVO). Annual datasets with crop type per parcel, reference date 15 May.

## Setup

### Prerequisites

- Python 3.12+
- Node.js (for the Angular frontend)

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

Requires [GDAL](https://gdal.org/) with `ogr2ogr` available on your `PATH`.

Ingest a bbox subset from the PDOK GeoPackage for a given year (RD New / EPSG:28992 coordinates):

```bash
python manage.py ingest_gewaspercelen \
  --year 2025 \
  --bbox 155000 463000 157000 465000
```

This example bbox covers a small area northeast of Amersfoort. The command reads the remote GeoPackage via GDAL's `/vsicurl/` driver (no full multi-GB download), reprojects geometry to WGS84, and stores it as GeoJSON text in the database. Re-running the same command is idempotent (duplicates are skipped).

Full nationwide and multi-year ingestion can be added once this pipeline is validated.

### Frontend

```bash
cd client
npm install
npm start
```

The Angular dev server runs on http://localhost:4200 and proxies `/api` requests to the Django backend on port 8000.
