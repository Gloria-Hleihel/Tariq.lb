# Tariq.lb - Smart Road Damage Detection & Mapping Platform

**Roads. Solutions. Progress.**

Tariq.lb is a smart web application that helps citizens report potholes,
cracks, and other road hazards across Lebanon. Users upload a road photo,
confirm the location, and the system analyzes the image using YOLOv8, estimates
severity, and places active reports on an interactive map for faster review.

## Features

- Upload road photos to report damage
- Automatic road damage detection using YOLOv8
- Severity scoring: Low, Medium, High, Critical
- GPS extraction from image EXIF metadata
- Manual location selection using an interactive map
- Lebanese city and village search
- Interactive Leaflet live map with severity-based markers
- Admin dashboard for reviewing and managing reports
- Admin map view for managing reports geographically
- Live, Under Review, and Done report sections
- Completed reports are hidden from the public map but kept in admin records
- Contact and feedback form for user messages
- FAQ and support modals

## Tech Stack

| Area | Tools |
|---|---|
| Frontend | HTML, CSS, JavaScript, Leaflet.js, Jinja2 |
| Backend | Python 3.12, Flask, Flask-SQLAlchemy, Gunicorn |
| AI/ML | YOLOv8, Ultralytics |
| Database | SQLite locally, PostgreSQL for production |
| Utilities | Pillow, Werkzeug |

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Gloria-Hleihel/TechTalks-Tariq.lb.git
cd TechTalks-Tariq.lb
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Activate it on Mac/Linux:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add or verify the YOLO model

The app uses the v3 fine-tuned model by default:

```text
models/road_damage_v3.pt
```

To use another model locally:

```bash
set DETECTION_MODEL_PATH=C:\path\to\your\model.pt
```

### 5. Seed the database

```bash
python scripts/seed.py
```

### 6. Run the app locally

```bash
python run.py
```

Open:

```text
http://127.0.0.1:5000
```

## Admin Panel

Admin login page:

```text
http://127.0.0.1:5000/admin/login
```

Default local credentials:

```text
Username: admin
Password: changeme
```

Do not use the defaults for public deployment. Production requires a strong
`SECRET_KEY` and `ADMIN_PASSWORD_HASH`.

## Environment Variables

Common settings:

| Variable | Purpose |
|---|---|
| `APP_ENV=production` | Enables production safety checks |
| `SECRET_KEY` | Required strong Flask session secret |
| `DATABASE_URL` | Production PostgreSQL connection string |
| `ADMIN_USERNAME` | Admin login username |
| `ADMIN_PASSWORD_HASH` | Hashed admin password |
| `UPLOAD_FOLDER` | Persistent upload directory in production |
| `PERSISTENT_UPLOADS_CONFIRMED=true` | Confirms uploads are stored persistently |
| `MODEL_PATH` | YOLO weights path |
| `DETECTION_MODEL_PATH` | YOLO weights path used by detector |
| `DETECTION_API_URL=internal` | Runs AI inference inside Flask |
| `DETECTION_API_TOKEN` | Protects detection endpoints in production |
| `DETECTION_PRELOAD_MODEL=true` | Warms the YOLO model at startup |
| `SESSION_COOKIE_SECURE=true` | Sends cookies only over HTTPS |

See `.env.example` for placeholders.

## Testing

```bash
python -m pytest tests
```

## Production Deployment

Production deployment uses:

- `wsgi.py` as the WSGI entrypoint
- `gunicorn.conf.py` for Gunicorn
- `render.yaml` for the recommended Render setup
- Flask-Migrate/Alembic migrations in `migrations/`
- `/healthz` as the health check endpoint

Production startup command:

```bash
flask --app wsgi:application db upgrade && gunicorn "wsgi:application" --config gunicorn.conf.py
```

Read the full deployment guide before launching:

```text
docs/deployment.md
```

## Database

The database includes:

- `reports` - submitted road damage reports
- `detections` - AI detection results linked to reports
- `feedback_messages` - contact and support messages from users

Full schema documentation:

```text
docs/schema.md
```

## Map Severity Colors

- Green - Low
- Yellow - Medium
- Orange - High
- Red - Critical

## Documentation

- Deployment Guide: `docs/deployment.md`
- Production Readiness Audit: `docs/production_readiness_audit.md`
- Database Schema: `docs/schema.md`
- API Documentation: `docs/api.md`
- DB Integrity Check: `docs/db_integrity_check.md`

## Troubleshooting

### Port 5000 already in use

```bash
flask run --port 3001
```

### No module named ultralytics

Activate the virtual environment, then run:

```bash
pip install -r requirements.txt
```

### Model file not found

Make sure this file exists:

```text
models/road_damage_v3.pt
```

### First detection is slow

The first detection can be slower because the YOLO model loads into memory.
For a smoother demo:

```bash
set DETECTION_PRELOAD_MODEL=1
python run.py
```

### Map pins do not appear

Check that reports have valid latitude and longitude values. Completed reports
are intentionally hidden from the public live map.

### Map tiles do not load

Check your internet connection because map tiles load from online providers.

## Notes

This project can run locally for development and university submission. For a
real public launch, use a production host with enough memory for YOLOv8,
PostgreSQL through `DATABASE_URL`, persistent upload storage, HTTPS, and real
secrets configured in the hosting dashboard.

## Project Structure

```text
TechTalks-Tariq.lb/
|-- app/
|   |-- admin/
|   |-- detection/
|   |-- reports/
|   `-- utils/
|-- docs/
|-- migrations/
|-- models/
|   `-- road_damage_v3.pt
|-- scripts/
|-- static/
|-- templates/
|-- tests/
|-- config.py
|-- models.py
|-- requirements.txt
|-- run.py
|-- wsgi.py
|-- gunicorn.conf.py
`-- render.yaml
```
