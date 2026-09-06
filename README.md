# UFIT Motion

A multi-organization platform for running a K-8 physical education program across school
districts. Coaches record sessions, incidents and assessments from their phones.
Administrators and principals see compliance and student growth across every school.

Designed and built by Jahleel Heath, April to May 2026. 22,557 lines of Python.
Flask 3.1 and PostgreSQL on Supabase in production, deployed on Render.

## This repository is the demo build

It is a snapshot published so the work can be inspected and clicked. It runs on SQLite and
seeds its own fabricated data on every boot. **No real student record exists in this repo or
on the demo instance.** That is enforced by configuration, not by memory: `render-demo.yaml`
never sets `DATABASE_URL`, so `app/database.py` falls back to SQLite and re-seeds on cold
boot. A public demo of a FERPA-scoped product must not be one environment variable away from
carrying FERPA data.

## Demo logins

The app creates these itself on first boot:

| Role      | Email                |
|-----------|----------------------|
| Principal | principal@demo.com   |
| Coach     | coach@demo.com       |
| Parent    | parent@demo.com      |
| Staff     | staff@demo.com       |
| Assistant | assistant@demo.com   |

Password is set via `UFIT_SEED_PASSWORD`.

## What is worth looking at

- `migrations/supabase/step5_rls.sql` — 157 row-level security policies across all 32 tables.
  Six `SECURITY DEFINER` helpers exist so policies do not recursively evaluate RLS on the
  users table. `anon` is denied everywhere. The org boundary is validated by database join,
  never trusted from a token claim.
- `app/database.py` — a dual-backend abstraction over SQLite and Postgres. Rewrites `?` to
  `%s`, injects `RETURNING <pk>` from a 34-table primary key map so `lastrowid` behaves the
  same on both, and ships a quote-aware statement splitter because psycopg3 has no
  `executescript`. Sets `prepare_threshold = None` because Supabase's transaction-mode
  pooler rejects server-side prepared statements.
- `app/routes/auth_routes.py` — a module-level dummy hash is verified on both the no-such-user
  and pending-invite paths, so login timing cannot be used to discover which accounts exist.
- `app/routes/shared_routes.py` — inbound webhooks verified with `hmac.compare_digest`, and
  the handler returns 503 refusing every request when the secret is unset, so an
  unconfigured environment cannot be used to create schools.
- `app/routes/_helpers.py` — `audit()` deliberately does not commit, so the audit row and the
  business write land in one transaction. A missing audit entry is a FERPA violation.
- `tests/` — 8,960 lines across 22 files against 11,442 lines of application code.
- `render.yaml` — the comments explain why the gunicorn timeout is 120 seconds and why one
  worker with four threads.

## Local run

    pip install -r requirements.txt
    UFIT_SECRET_KEY=local-only UFIT_SEED_PASSWORD=pick-one DB_PATH=/tmp/ufit.db \
      gunicorn wsgi:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:8000

Leave `DATABASE_URL` unset and it runs on SQLite and seeds itself.


## One click deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/jahleelheath/ufit-motion-demo)

The root `render.yaml` is the demo blueprint and never sets `DATABASE_URL`.
The production blueprint is kept as `render-production.yaml`.
Set `UFIT_SEED_PASSWORD` in the Render dashboard after the first deploy.
