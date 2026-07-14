# Deployment Guide

This app ships ready for local development out of the box (zero
configuration required). This guide covers what changes for a real
deployment.

## 1. Set Environment Variables

Copy `.env.example` to `.env` (or set real environment variables on
your host - whichever your platform supports) and set at minimum:

```bash
APP_ENV=production
SECRET_KEY=<a long random value>
```

Generate a strong `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**The app will refuse to start** if `APP_ENV=production` and
`SECRET_KEY` is still the development placeholder - this is a
deliberate safety check in `app.py`, not a bug.

## 2. Choose a Database

The default is a local SQLite file - fine for a single-admin,
low-to-moderate traffic deployment (this app was designed for exactly
that use case). If you need a different database, set:

```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

(Requires installing the matching driver, e.g. `psycopg2-binary`, and
adding it to `requirements.txt` - not included by default since the
project ships SQLite-first.)

## 3. Install a Production WSGI Server

Flask's built-in development server (`python app.py`) is **not**
suitable for production - it's single-threaded and not hardened
against real traffic. Use Gunicorn (Linux/macOS) or Waitress
(Windows):

```bash
pip install gunicorn
gunicorn "app:create_app()" --bind 0.0.0.0:8000 --workers 3
```

or

```bash
pip install waitress
waitress-serve --port=8000 "app:create_app()"
```

## 4. Put a Reverse Proxy in Front (recommended)

Run Nginx (or your platform's equivalent) in front of Gunicorn/Waitress
to terminate HTTPS, serve static files efficiently, and add basic
request limits. A minimal Nginx example:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.example;

    location /static/ {
        alias /path/to/cyber_training_portal/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

With `ProductionConfig` active, session cookies are already marked
`Secure` (HTTPS-only) - make sure HTTPS is actually terminated
somewhere in front of the app, or logins will silently fail to persist.

## 5. File Storage & Backups

- `uploads/certificates/` must be on **persistent
  storage** that survives deploys/restarts - don't deploy to an
  ephemeral filesystem (e.g. some container platforms wipe local disk
  on every deploy) without mounting a persistent volume.
- `database/backups/` accumulates timestamped backups every time an
  admin clicks "Backup" in Settings, or a database restore happens (a
  pre-restore safety backup). Set up an external cron job / platform
  scheduler to periodically copy these off-server (S3, another disk,
  etc.) - this app does not do that automatically.

## 6. Logging

In any environment other than `development`/`testing`, logs are
written to `logs/app.log` with automatic rotation (1 MB per file, 5
backups kept - see `app.py`). Point your platform's log shipper at
this file, or watch it directly:

```bash
tail -f logs/app.log
```

## 7. Multi-Worker Note on Login Throttling

`utils/security.py`'s login-throttle counter is stored in the Python
process's memory. This is fine for a single-worker deployment. If you
run **multiple** Gunicorn workers (`--workers 3` or more), each worker
has its own independent counter, so the effective lockout threshold is
roughly `MAX_FAILED_ATTEMPTS × worker_count` rather than a single
global limit. For most deployments of this app's scale that's an
acceptable trade-off; if you need a hard global limit across many
workers, replace the in-memory dict in `utils/security.py` with a
shared store (e.g. Redis) - the function signatures
(`record_failed_login`, `is_locked_out`, `clear_failed_logins`) are
designed to be swapped without touching `routes/auth.py`.

## 8. Pre-Launch Checklist

- [ ] `.env` created with a real `SECRET_KEY` and `APP_ENV=production`
- [ ] Default admin password changed from `admin123`
- [ ] HTTPS is terminated somewhere in front of the app
- [ ] `uploads/` and `database/` are on persistent storage
- [ ] A backup schedule is in place for `database/`
- [ ] `pytest` passes locally before deploying
- [ ] Running behind Gunicorn/Waitress, not `python app.py`
