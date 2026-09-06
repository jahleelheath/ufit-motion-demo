"""The demo credential bar prints a working password onto the login page.

That is acceptable on the public demo instance, which holds only seeded data, and
unacceptable anywhere else. DATABASE_URL is what selects the Postgres backend that
holds real student records, so it is the signal the guard keys on. These tests exist
because the failure mode is silent: a stray env var on the wrong service would put a
live password on a page serving FERPA data, and nothing would look broken.
"""

import os
import pytest

from app import create_app


def _client(monkeypatch, tmp_path, **env):
    for k in ("DEMO_MODE", "DATABASE_URL", "UFIT_SEED_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("UFIT_SECRET_KEY", "test-only")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "demo.db"))
    monkeypatch.setenv("UFIT_APP_ROOT", os.getcwd())
    return create_app().test_client()


def test_demo_bar_renders_without_a_real_database(monkeypatch, tmp_path):
    c = _client(monkeypatch, tmp_path, DEMO_MODE="true", UFIT_SEED_PASSWORD="pw-for-test")
    html = c.get("/login").get_data(as_text=True)
    assert "demo-bar" in html
    assert "pw-for-test" in html


def test_demo_bar_refuses_when_database_url_is_set(monkeypatch, tmp_path):
    """The one that matters. DEMO_MODE is ignored against a real database."""
    c = _client(
        monkeypatch,
        tmp_path,
        DEMO_MODE="true",
        UFIT_SEED_PASSWORD="must-not-appear",
        DATABASE_URL="postgresql://u:p@example.invalid:5432/db",
    )
    html = c.get("/login").get_data(as_text=True)
    assert "demo-bar" not in html
    assert "must-not-appear" not in html


def test_demo_bar_absent_by_default(monkeypatch, tmp_path):
    c = _client(monkeypatch, tmp_path, UFIT_SEED_PASSWORD="pw-for-test")
    html = c.get("/login").get_data(as_text=True)
    assert "demo-bar" not in html
    assert "pw-for-test" not in html


@pytest.mark.parametrize("value", ["false", "0", "no", "", "TRUEISH"])
def test_demo_bar_only_on_for_explicit_truthy_values(monkeypatch, tmp_path, value):
    c = _client(monkeypatch, tmp_path, DEMO_MODE=value, UFIT_SEED_PASSWORD="pw-for-test")
    html = c.get("/login").get_data(as_text=True)
    assert "demo-bar" not in html


def test_roles_are_listed_most_capable_first(monkeypatch, tmp_path):
    """A founder clicking through should see the widest surface first."""
    c = _client(monkeypatch, tmp_path, DEMO_MODE="true", UFIT_SEED_PASSWORD="pw-for-test")
    html = c.get("/login").get_data(as_text=True)
    order = ["admin@ufit.com", "coach@demo.com", "principal@demo.com", "parent@demo.com"]
    positions = [html.index(e) for e in order]
    assert positions == sorted(positions)


def test_each_role_button_carries_the_portal_the_api_expects(monkeypatch, tmp_path):
    """The login API takes {email, password, portal} and 400s on a mismatch.

    Filling only the credentials sends whichever portal happened to be selected,
    which failed silently for every role on the first deployed build. Each button
    must carry the portal key that matches its account.
    """
    c = _client(monkeypatch, tmp_path, DEMO_MODE="true", UFIT_SEED_PASSWORD="pw-for-test")
    html = c.get("/login").get_data(as_text=True)
    expected = {
        "admin@ufit.com": "admin",
        "coach@demo.com": "coach",
        "principal@demo.com": "org",   # principals sign in through the Organization portal
        "parent@demo.com": "parent",
    }
    for email, portal in expected.items():
        needle = f'data-demo-email="{email}" data-demo-portal="{portal}"'
        assert needle in html, f"{email} must post portal={portal}"


def test_role_switch_clears_the_session_first(monkeypatch, tmp_path):
    """Clicking a role while already signed in must log out before signing in.

    The session survives a client-side route change, so without this the SPA just
    re-renders the current dashboard and the click appears to do nothing. Found by
    clicking Admin while signed in as the head coach on the deployed instance.
    """
    c = _client(monkeypatch, tmp_path, DEMO_MODE="true", UFIT_SEED_PASSWORD="pw-for-test")
    html = c.get("/login").get_data(as_text=True)
    # Use the SPA's own logout, which clears in-memory state and re-renders the
    # login form. Posting to /api/auth/logout directly left the SPA holding a
    # stale session and the click silently did nothing.
    assert "_doLogout" in html
    assert "whenLoginReady" in html


def test_seeded_assessment_window_status_matches_its_dates(monkeypatch, tmp_path):
    """An 'active' window whose end date has passed is a visible contradiction.

    The demo re-seeds on every cold boot, so windows are anchored relative to
    today. The mid-year window was previously seeded ending four days ago while
    still marked active, and the coach dashboard advertised it as the active
    window. Caught by reading the deployed dashboard, not by any existing test.
    """
    import datetime

    from app.database import get_db

    c = _client(monkeypatch, tmp_path, DEMO_MODE="true", UFIT_SEED_PASSWORD="pw-for-test")
    today = datetime.date.today()
    with c.application.app_context():
        db = get_db()
        rows = db.execute(
            "SELECT window_name, end_date, status FROM assessment_windows"
        ).fetchall()

    assert rows, "the demo seed must create assessment windows"
    for row in rows:
        name, end_date, status = row["window_name"], row["end_date"], row["status"]
        end = datetime.date.fromisoformat(str(end_date)[:10])
        if status == "active":
            assert end >= today, f"{name} is active but ended {end}"
        if status == "closed":
            assert end < today, f"{name} is closed but ends {end}"


def test_stale_demo_dates_are_repaired_on_boot(monkeypatch, tmp_path):
    """A long-lived demo instance must not advertise a window that already closed.

    init_db is idempotent by design, so a database seeded once keeps its original
    dates forever. On a demo that is the first thing a visitor sees. The refresh
    step re-anchors the windows on every boot.
    """
    import datetime

    from app.database import get_db

    db_path = tmp_path / "demo.db"
    c = _client(monkeypatch, tmp_path, DEMO_MODE="true", UFIT_SEED_PASSWORD="pw")
    with c.application.app_context():
        db = get_db()
        db.execute(
            "UPDATE assessment_windows SET end_date = ? WHERE status = 'active'",
            ("2020-01-01",),
        )
        db.commit()

    # Boot again against the same database, exactly as a restart would.
    c2 = _client(monkeypatch, tmp_path, DEMO_MODE="true", UFIT_SEED_PASSWORD="pw")
    with c2.application.app_context():
        rows = get_db().execute(
            "SELECT end_date FROM assessment_windows WHERE status = 'active'"
        ).fetchall()

    assert rows
    today = datetime.date.today()
    for row in rows:
        assert datetime.date.fromisoformat(str(row["end_date"])[:10]) >= today


def test_date_refresh_refuses_against_a_real_database(monkeypatch, tmp_path):
    """The refresh writes rows, so it must never run against real records."""
    from app.database import get_db
    from app.seeds import _refresh_demo_dates

    c = _client(monkeypatch, tmp_path, DEMO_MODE="true", UFIT_SEED_PASSWORD="pw")
    with c.application.app_context():
        db = get_db()
        db.execute(
            "UPDATE assessment_windows SET end_date = ? WHERE status = 'active'",
            ("2020-01-01",),
        )
        db.commit()
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@example.invalid:5432/db")
        _refresh_demo_dates(db)
        row = db.execute(
            "SELECT end_date FROM assessment_windows WHERE status = 'active'"
        ).fetchone()

    assert str(row["end_date"])[:10] == "2020-01-01", "must not rewrite a real database"
