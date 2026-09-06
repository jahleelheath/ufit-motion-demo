# UFIT Motion

A multi-organization platform for running a K-8 physical education program across school
districts. Coaches record sessions, incidents and assessments from their phones.
Administrators and principals see compliance and student growth across every school.

Designed and built by Jahleel Heath, April to May 2026. 22,557 lines of Python.
Flask 3.1 and PostgreSQL on Supabase in production, deployed on Render.

## This repository is the demo build

It is a snapshot published so the work can be inspected and clicked. It runs on SQLite with
fabricated seed data. **No real student record exists in this repo or on the demo instance.**
That is enforced by configuration, not by memory: the root `render.yaml` never sets
`DATABASE_URL`, so `app/database.py` takes the SQLite path. A public demo of a FERPA-scoped
product must not be one environment variable away from carrying FERPA data.

Seeding is idempotent, so it populates once and then leaves the database alone, which is the
correct behaviour for a real deployment. The cost on a long-lived demo is that dates go stale
and the dashboard starts advertising an assessment window that closed weeks ago. So under
`DEMO_MODE`, and only when `DATABASE_URL` is absent, `_refresh_demo_dates()` re-anchors those
windows on every boot. Both guards are tested, including the one that matters: it refuses to
rewrite anything when a real database is configured.

## Demo logins

The login page carries a bar with one-click sign in, ordered so you see the widest
surface first. No password to ask anyone for.

| # | Role       | Email                | What it opens |
|---|------------|----------------------|---------------|
| 1 | Admin      | admin@ufit.com       | every school, analytics, audit log |
| 2 | Head Coach | coach@demo.com       | log sessions, assessments, incidents |
| 3 | Principal  | principal@demo.com   | one school, compliance and growth |
| 4 | Parent     | parent@demo.com      | one child, read only |

Also seeded: `staff@demo.com`, `assistant@demo.com`, `ceo@demo.com`.
All share `UFIT_SEED_PASSWORD`.

That bar prints a working password into the page, which is fine here and nowhere else.
`app/__init__.py` refuses to render it whenever `DATABASE_URL` is set, because that is
the variable selecting the Postgres backend holding real records. The guard is covered
by `tests/test_demo_mode.py`, including the case that actually matters: `DEMO_MODE=true`
against a real database renders nothing and leaks nothing.

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
- `tests/` — 9,095 lines across 23 files against 11,467 lines of application code.
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
