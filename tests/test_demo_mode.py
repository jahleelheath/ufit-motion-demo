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
