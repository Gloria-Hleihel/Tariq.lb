# Tariq.lb Production Deployment Guide

This guide prepares Tariq.lb for public hosting without changing the product
flow, AI model, reports, map, or admin dashboard.

## Recommended Platform

Use Render with:

- A paid web service with at least 2 GB RAM.
- Managed PostgreSQL.
- A persistent disk mounted for uploads.

The YOLOv8/PyTorch model can exceed free-instance memory during report
submission. A free instance may boot, but it is not reliable for public AI
inference.

## Required Environment Variables

Set these in the hosting provider dashboard. Do not commit real values.

```text
APP_ENV=production
FLASK_ENV=production
SECRET_KEY=<strong random secret>
DATABASE_URL=<postgres connection string>
ADMIN_USERNAME=<admin username>
ADMIN_PASSWORD_HASH=<werkzeug password hash>
MODEL_PATH=models/road_damage_v3.pt
DETECTION_MODEL_PATH=models/road_damage_v3.pt
DETECTION_API_URL=internal
DETECTION_API_TOKEN=<random internal token>
DETECTION_API_REQUIRE_TOKEN=true
DETECTION_PRELOAD_MODEL=true
UPLOAD_FOLDER=/var/data/tariq-lb/uploads
ANNOTATED_FOLDER=/var/data/tariq-lb/uploads/annotated
PERSISTENT_UPLOADS_CONFIRMED=true
AUTO_CREATE_DATABASE=false
SESSION_COOKIE_SECURE=true
TRUST_PROXY_HEADERS=true
TRUSTED_PROXY_COUNT=1
WEB_CONCURRENCY=1
GUNICORN_THREADS=2
```

Generate a password hash locally:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('REPLACE_WITH_ADMIN_PASSWORD'))"
```

## Production Startup Command

```bash
flask --app wsgi:application db upgrade && gunicorn "wsgi:application" --config gunicorn.conf.py
```

The Flask development server is only for local development:

```bash
python run.py
```

## Database Migrations

Migration support is enabled with Flask-Migrate.

Local migration commands:

```bash
flask --app wsgi:application db migrate -m "Describe schema change"
flask --app wsgi:application db upgrade
```

Production deploys should run:

```bash
flask --app wsgi:application db upgrade
```

## Upload Persistence

Production uploads must not live in ephemeral container storage. The Render
blueprint mounts:

```text
/var/data/tariq-lb/uploads
```

Set:

```text
UPLOAD_FOLDER=/var/data/tariq-lb/uploads
ANNOTATED_FOLDER=/var/data/tariq-lb/uploads/annotated
PERSISTENT_UPLOADS_CONFIRMED=true
```

For a larger launch, move uploaded images to object storage such as S3,
Cloudflare R2, Backblaze B2, or Cloudinary.

## AI Model

The deployed model path is:

```text
models/road_damage_v3.pt
```

The model is loaded once and reused. Production runs CPU inference unless the
host provides GPU support. Keep one Gunicorn worker unless the server has enough
RAM for multiple PyTorch model copies.

## Health Check

Render should use:

```text
/healthz
```

The health check confirms Flask and database connectivity only. It does not run
YOLO inference.

## DNS and HTTPS

After the web service is live:

1. Add the custom domain in Render.
2. Add the DNS record shown by Render at your domain registrar.
3. Wait for DNS propagation.
4. Confirm HTTPS is active.
5. Choose one canonical domain, such as `tariqlb.com`.
6. Redirect `www.tariqlb.com` to the canonical domain or the opposite.

Do not hardcode localhost URLs in production.

## Backup Strategy

Database:

- Enable scheduled PostgreSQL backups in the hosting provider.
- Export a manual backup before migrations or major releases.

Uploads:

- Back up the persistent upload disk regularly.
- For production launch, prefer object storage with versioning enabled.

Restore procedure:

1. Restore the PostgreSQL backup.
2. Restore uploaded images and annotated images.
3. Deploy the same Git commit.
4. Run `flask --app wsgi:application db upgrade`.
5. Verify `/healthz`, `/`, `/upload`, `/map`, and `/admin/login`.

## Monitoring

Minimum launch monitoring:

- Hosting uptime checks against `/healthz`.
- Application logs for failed logins, upload failures, and detection failures.
- Database storage usage.
- Persistent disk usage.
- Memory usage during report submission.

## Pre-Launch Checklist

- Tests pass with `python -m pytest tests`.
- Production secrets are set in the host dashboard.
- `ADMIN_PASSWORD_HASH` is used, not a plaintext password.
- PostgreSQL is connected through `DATABASE_URL`.
- Uploads are stored on persistent storage.
- `/healthz` returns `{"status":"ok"}`.
- Admin login works with the real credentials.
- Report upload works with a real image.
- Detection completes without memory restart.
- Public map hides resolved/rejected/completed reports.
- Delete report asks for confirmation and removes images.
- HTTPS is active.

## Remaining Production Limitation

This repository is ready to deploy on a suitable paid instance. It is not safe to
claim full public production readiness on a 512 MB free instance because YOLOv8
and PyTorch can exceed memory during inference.
