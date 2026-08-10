# Tariq.lb Production Deployment Guide

## Deployment-Readiness Audit

Current production-ready pieces:

- Flask uses an application factory: `app:create_app()`.
- WSGI entry point is now available at `wsgi:application`.
- Admin auth uses Werkzeug password hashes when `ADMIN_PASSWORD_HASH` is set.
- CSRF protection covers admin login, uploads, feedback, status updates, deletes, and retry detection.
- Upload validation checks extension, browser MIME type, real image content, pixel count, and size.
- Uploaded filenames are generated UUIDs rather than trusting browser filenames.
- YOLO model loading is cached and reused.
- The public map excludes resolved/rejected reports.
- Basic rate limiting and security headers are implemented.

Important production gaps addressed in this pass:

- Added `DATABASE_URL` support for PostgreSQL.
- Added fail-fast production validation for secrets, database, upload persistence, secure cookies, and model presence.
- Added `/healthz` for hosting health checks.
- Added clean HTML/JSON error handling.
- Added Flask-Migrate wiring.
- Added production WSGI, Gunicorn, Render, and GitHub Actions files.
- Changed the default detection integration from self-HTTP to in-process detection to avoid one-worker WSGI deadlocks.

Remaining production decisions:

- Use Render persistent disk for `static/uploads` or move uploads to object storage later.
- Configure real domain DNS and HTTPS before enabling public launch.
- Set real secret values in the hosting provider; never commit them.

## Recommended Hosting Platform

Primary recommendation: Render.

Why Render fits this project:

- Native Python web services and Gunicorn support.
- Managed PostgreSQL.
- Persistent disks for uploaded images.
- HTTPS and custom domain support.
- Health check support.
- Simpler than operating a VM while still giving enough RAM/CPU for CPU-only YOLO inference.

For the smoothest public production launch, use at least a paid web service
plan with persistent upload storage. The included `render.yaml` is set to a
free demo deployment so it does not require a credit card.

## Required Environment Variables

Set these in production:

```text
APP_ENV=production
FLASK_ENV=production
SECRET_KEY=<long random secret>
DATABASE_URL=<managed PostgreSQL URL>
ADMIN_USERNAME=<admin username>
ADMIN_PASSWORD_HASH=<Werkzeug password hash>
AUTO_CREATE_DATABASE=false
MODEL_PATH=models/road_damage_v3.pt
DETECTION_API_URL=internal
DETECTION_PRELOAD_MODEL=1
UPLOAD_FOLDER=static/uploads
ANNOTATED_FOLDER=static/uploads/annotated
PERSISTENT_UPLOADS_CONFIRMED=true
ALLOW_EPHEMERAL_UPLOADS=false
SESSION_COOKIE_SECURE=1
TRUST_PROXY_HEADERS=1
PREFERRED_URL_SCHEME=https
```

Generate an admin password hash locally:

```powershell
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('replace-this-password'))"
```

When deploying with the included `render.yaml`, Render automatically:

- creates and injects `DATABASE_URL`
- generates `SECRET_KEY`
- sets `ADMIN_USERNAME=tariq.lb@admin2026`
- uses free Render web and Postgres plans
- places the web service and database in the same Render region
- sets `ALLOW_EPHEMERAL_UPLOADS=true`
- sets `AUTO_CREATE_DATABASE=1` so the demo database starts without manual migration commands
- sets `DETECTION_API_URL=disabled` so report submission cannot crash the
  free instance by loading YOLO/PyTorch

You only need to paste `ADMIN_PASSWORD_HASH` during the first Blueprint deploy.

For a launch where AI detection runs online, upgrade the web service memory
and set `DETECTION_API_URL=internal`.

## Database

Local development may continue using SQLite.

Production should use PostgreSQL through `DATABASE_URL`. On Render Free,
Postgres is useful for demos, but it expires after 30 days.

Migration commands after deployment setup:

```bash
flask --app wsgi:application db init
flask --app wsgi:application db migrate -m "initial schema"
flask --app wsgi:application db upgrade
```

For the free Render demo Blueprint, `AUTO_CREATE_DATABASE=1` is enabled so the
site starts without manual database commands. For long-term production, turn it
off and run migrations instead of relying on `db.create_all()`.

## Upload Persistence

The app stores user uploads in:

```text
static/uploads
static/uploads/annotated
```

The free Render Blueprint does not mount a persistent disk, so uploaded image
files can be lost after a redeploy/restart. The database can still store report
records. For real public launch, add a persistent disk or use S3-compatible
object storage or Cloudinary and set `PERSISTENT_UPLOADS_CONFIRMED=true`.

## Production Startup Command

```bash
gunicorn "wsgi:application" --config gunicorn.conf.py
```

Do not use:

```bash
python run.py
```

for production hosting.

## Render Deployment Steps

1. Push `main` to GitHub.
2. In Render, create a Blueprint from this repository.
3. Confirm `render.yaml` creates:
   - one web service
   - one PostgreSQL database
4. Add the secret value for:
   - `ADMIN_PASSWORD_HASH`
5. Deploy.
6. Run database migrations.
7. Open `/healthz` and confirm:

```json
{"status":"ok","database":"ok"}
```

## DNS and Domain

For a real domain such as `tariqlb.com`:

1. Add the custom domain in Render.
2. Configure DNS records as Render instructs.
3. Choose one canonical domain, for example `https://www.tariqlb.com`.
4. Redirect the alternate domain to the canonical domain.
5. Keep HTTPS enabled.
6. Do not hardcode localhost URLs in production environment variables.

## Backup Strategy

PostgreSQL:

- Enable scheduled Render database backups.
- Before major releases, export a manual backup with `pg_dump`.

Uploads:

- Use Render persistent disk snapshots if available.
- Periodically copy `static/uploads` to durable off-platform storage.
- If the project grows, migrate uploads to object storage with versioning.

Restore plan:

1. Restore PostgreSQL backup.
2. Restore uploaded image directory.
3. Redeploy the latest known-good GitHub commit.
4. Verify `/healthz`, `/map`, `/upload`, and `/admin/dashboard`.

## Monitoring

Minimum monitoring:

- Render health checks on `/healthz`.
- Render logs for startup, login failures, report submissions, and detection failures.
- Alert on repeated 500s or health-check failures.

Recommended next step:

- Add Sentry for exception monitoring before a public launch with real users.

## Pre-Launch Checklist

- [ ] `APP_ENV=production`
- [ ] `DEBUG` is off
- [ ] `SECRET_KEY` is strong and private
- [ ] `ADMIN_PASSWORD_HASH` is set
- [ ] Admin password is not the demo password
- [ ] PostgreSQL `DATABASE_URL` is configured
- [ ] Migrations have been run
- [ ] Persistent upload storage is mounted
- [ ] `MODEL_PATH` exists in the deployed filesystem
- [ ] `/healthz` returns ok
- [ ] `/upload` accepts valid JPG/PNG files
- [ ] `/map` shows only active public reports
- [ ] `/admin/login` works over HTTPS
- [ ] Delete/status update actions require login and CSRF
- [ ] Domain and HTTPS are configured
- [ ] Backups are scheduled
