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

### Frontend

```bash
cd client
npm install
npm start
```

The Angular dev server runs on http://localhost:4200 and proxies `/api` requests to the Django backend on port 8000.
