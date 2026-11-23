from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.seed import initialize


class Clock:
    def __init__(self, now):
        self.value = now

    def __call__(self):
        return self.value

    def set(self, value):
        self.value = value


@pytest.fixture
def demo(tmp_path):
    now = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)
    clock = Clock(now)
    path = tmp_path / "booking.sqlite3"
    initialize(path, now=now)
    app = create_app(path, clock=clock)
    clients = []

    def client(username=None, application=None):
        browser = TestClient(application or app, raise_server_exceptions=False)
        clients.append(browser)
        session = browser.get("/session")
        assert session.status_code == 200
        browser.headers["X-CSRF-Token"] = session.json()["csrf_token"]
        if username:
            response = browser.post("/login", json={"username": username, "password": "Demo123!"})
            assert response.status_code == 200, response.text
            browser.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        return browser

    yield SimpleNamespace(path=path, now=now, clock=clock, app=app, db=app.state.db, client=client)
    for browser in clients:
        browser.close()


def code(response, status, expected):
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == expected


def book(client, training=1, user=1):
    return client.post("/reservations", json={"id_klienta": user, "id_treningu": training})


def count(demo, training=1):
    with demo.db.transaction() as conn:
        return conn.execute("SELECT COUNT(*) FROM reservations WHERE training_id=? AND status='confirmed'", (training,)).fetchone()[0]


def remove_inc03_schema(conn):
    """Restore the legacy catalog schema in a disposable migration fixture."""
    remove_inc04_schema(conn)
    conn.execute("DROP TABLE catalog_creates")
    conn.execute("DROP INDEX one_trainer_per_account")
    conn.execute("ALTER TABLE trainers DROP COLUMN account_id")
    for table in ("trainers", "activities", "rooms"):
        conn.execute(f"ALTER TABLE {table} DROP COLUMN status")
        conn.execute(f"ALTER TABLE {table} DROP COLUMN version")


def remove_inc04_schema(conn):
    conn.execute("DROP TABLE training_creates")
    conn.execute("DROP INDEX training_by_trainer")
    conn.execute("DROP INDEX training_by_room")
    conn.execute("ALTER TABLE trainings DROP COLUMN version")
