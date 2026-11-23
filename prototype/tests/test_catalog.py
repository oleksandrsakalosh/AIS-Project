from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import uuid4
import sqlite3

import pytest

from app import accounts, catalog
from app.db import stamp
from app.main import create_app
from app.migrate import SCHEMA_VERSION, upgrade
from app.seed import initialize
from conftest import book, code, remove_inc03_schema
from test_admin import admin, edit, find, parallel, provision, sign_in


CATALOG = "/api/admin/catalog"
KINDS = ("trainers", "activities", "rooms")


def create(browser, kind, name, key=None):
    return browser.post(f"{CATALOG}/{kind}", json={"name": name, "request_id": key or str(uuid4())})


def change(browser, kind, entry, field, **values):
    return browser.put(f"{CATALOG}/{kind}/{entry['id']}/{field}",
                       json={**values, "expected_version": entry["version"]})


def items(browser, kind):
    response = browser.get(f"{CATALOG}/{kind}")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()["items"]


def test_SC_CAT01_08_catalog_access_and_error_order(demo, admin):
    assert provision(admin, "front.desk", "reception").status_code == 201
    for browser, location, status, error in (
        (demo.client(), "/login", 401, "unauthorized"),
        (demo.client("anna"), "/schedule", 403, "forbidden"),
        (demo.client("trener"), "/staff", 403, "forbidden"),
        (sign_in(demo, "front.desk"), "/staff", 403, "forbidden"),
    ):
        page = browser.get("/admin/catalog", follow_redirects=False)
        assert page.status_code == 303 and page.headers["location"] == location
        code(browser.get(f"{CATALOG}/missing"), status, error)
        for method, path in (("POST", "/rooms"), ("PUT", "/rooms/bad/name"),
                             ("PUT", "/rooms/bad/status"), ("PUT", "/trainers/bad/account")):
            code(browser.request(method, CATALOG + path, content="{", headers={"X-CSRF-Token": "bad"}), status, error)
    assert 'href="/admin/catalog"' in admin.get("/staff").text
    assert 'lang="sk"' in admin.get("/admin/catalog").text
    code(admin.put(f"{CATALOG}/trainers/bad/account", content="{", headers={"X-CSRF-Token": "bad"}), 403, "csrf_invalid")
    invalid = admin.put(f"{CATALOG}/trainers/bad/account", json={"unexpected": "secret fixture"})
    code(invalid, 422, "validation")
    assert "secret fixture" not in invalid.text
    code(admin.post(f"{CATALOG}/rooms", content="{}"), 422, "validation")
    code(admin.get(f"{CATALOG}/missing"), 422, "validation")
    for kind in KINDS:
        rows = items(admin, kind)
        assert rows == items(admin, kind)
        assert [row["id"] for row in rows] == sorted(row["id"] for row in rows)
        keys = {"id", "name", "status", "version"}
        assert all(row.keys() == (keys | {"account_id"} if kind == "trainers" else keys) for row in rows)


@pytest.mark.parametrize("method,suffix", (("POST", "/rooms"), ("PUT", "/rooms/1/name")))
def test_SC_CAT08_invalid_utf8_uses_catalog_validation(demo, admin, method, suffix):
    invalid = b'{"name":"\xff","request_id":"a855853d-8874-4d29-b28d-d5ee7ad31d3f"}'
    headers = {"Content-Type": "application/json"}
    path = CATALOG + suffix
    before = items(admin, "rooms")
    code(demo.client().request(method, path, content=invalid, headers=headers), 401, "unauthorized")
    code(demo.client("trener").request(method, path, content=invalid, headers=headers), 403, "forbidden")
    code(admin.request(method, path, content=invalid, headers={**headers, "X-CSRF-Token": "bad"}), 403, "csrf_invalid")
    response = admin.request(method, path, content=invalid, headers=headers)
    assert response.status_code == 422, response.text
    assert response.json() == {"error": {"code": "validation", "message": "validation"}}
    assert items(admin, "rooms") == before


def test_SC_CAT03_unchanged_migrated_label_preserves_legacy_collision(demo, admin):
    legacy_name = "  Sa\u0301la  "
    with demo.db.transaction(write=True) as conn:
        remove_inc03_schema(conn)
        conn.execute("UPDATE metadata SET value='0.3.0' WHERE key='schema_version'")
        conn.executemany("INSERT INTO rooms(id,name) VALUES (?,?)", ((10, legacy_name), (11, "Sála")))
    assert upgrade(demo.path)
    before = items(admin, "rooms")
    entry = next(room for room in before if room["id"] == 10)
    for name in (legacy_name, "Sála"):
        response = change(admin, "rooms", entry, "name", name=name)
        assert response.status_code == 200, response.text
        assert response.json() == entry
    code(change(admin, "rooms", entry, "name", name="SÁLA"), 409, "catalog_name_taken")
    assert items(admin, "rooms") == before
    renamed = change(admin, "rooms", entry, "name", name="Malá sála")
    assert renamed.status_code == 200
    assert renamed.json() == {**entry, "name": "Malá sála", "version": 2}


@pytest.mark.parametrize("kind", KINDS)
def test_SC_CAT02_03_04_create_rename_deactivate_and_replay(admin, kind):
    key = str(uuid4())
    original = create(admin, kind, "  Šport : Aktivita  ", key)
    assert original.status_code == 201, original.text
    entry = original.json()
    assert (entry["version"], entry["status"], entry["name"]) == (1, "active", "Šport : Aktivita")
    assert create(admin, kind, entry["name"], key).json() == entry
    code(create(admin, kind, "Other", key), 409, "create_request_conflict")
    assert change(admin, kind, entry, "name", name=entry["name"]).json() == entry
    renamed = change(admin, kind, entry, "name", name="Šport II").json()
    assert renamed["version"] == 2 and renamed["id"] == entry["id"]
    code(change(admin, kind, entry, "name", name="Šport II"), 409, "catalog_entry_changed")
    code(change(admin, kind, {**renamed, "id": 999}, "name", name="Názov"), 404, "catalog_entry_not_found")
    inactive = change(admin, kind, renamed, "status", status="inactive").json()
    assert inactive["version"] == 3 and inactive["status"] == "inactive"
    assert change(admin, kind, inactive, "status", status="inactive").json() == inactive
    code(change(admin, kind, inactive, "status", status="active"), 422, "validation")
    assert create(admin, kind, "Šport : Aktivita", key).json() == entry
    assert inactive in items(admin, kind)
    if kind == "trainers":
        assert create(admin, kind, "Šport II").json()["id"] != entry["id"]
    else:
        code(create(admin, kind, " šPORT II "), 409, "catalog_name_taken")
        other = create(admin, kind, "Odlišný názov").json()
        code(change(admin, kind, other, "name", name="Šport II"), 409, "catalog_name_taken")
    assert change(admin, kind, inactive, "name", name="Oprava").json()["status"] == "inactive"
    for name in ("  ", "\tBad", "😀" * 81):
        code(create(admin, kind, name), 422, "validation")
    code(create(admin, kind, "Test", key.upper()), 422, "validation")


def test_SC_CAT04_future_reference_includes_empty_and_cancelled_bookings(demo, admin, monkeypatch):
    boris = demo.client("boris")
    booking = next(row for row in boris.get("/reservations").json()["items"] if row["id_treningu"] == 1)
    assert boris.delete(f"/reservations/{booking['id_rezervacie']}").status_code == 200
    for kind in KINDS:
        code(change(admin, kind, {"id": 1, "version": 1}, "status", status="inactive"), 409, "future_training_reference")
    code(change(admin, "activities", {"id": 2, "version": 1}, "status", status="inactive"), 409, "future_training_reference")
    start = demo.now + timedelta(minutes=1)
    arrived = Event()
    original = catalog.deactivate_entry

    def mark_arrival(*args):
        arrived.set()
        return original(*args)

    monkeypatch.setattr(catalog, "deactivate_entry", mark_arrival)
    with demo.db.transaction(write=True) as conn:
        conn.execute("UPDATE trainings SET starts_at=? WHERE id=1", (stamp(start),))
    with ThreadPoolExecutor(max_workers=1) as pool:
        with demo.db.transaction(write=True):
            request = pool.submit(change, admin, "activities", {"id": 1, "version": 1}, "status", status="inactive")
            assert arrived.wait(timeout=5)
            demo.clock.set(start)
        response = request.result(timeout=5)
        assert response.status_code == 200 and response.json()["status"] == "inactive", response.text
    assert demo.client("anna").get("/trainings").json()["items"]


def test_SC_CAT05_06_link_lifecycle_and_account_guard(demo, admin):
    trainer = find(admin, "trener")
    other = provision(admin, "new.trainer", "trainer").json()
    receptionist = provision(admin, "front.desk", "reception").json()
    first, second = items(admin, "trainers")
    assert first["account_id"] is None and second["account_id"] is None
    code(change(admin, "trainers", first, "account", account_id=999), 404, "account_not_found")
    code(change(admin, "trainers", first, "account", account_id=receptionist["id"]), 409, "trainer_account_ineligible")
    trainer_session = demo.client("trener")
    linked = change(admin, "trainers", first, "account", account_id=trainer["id"]).json()
    assert linked["version"] == 2 and linked["account_id"] == trainer["id"]
    assert change(admin, "trainers", linked, "account", account_id=trainer["id"]).json() == linked
    code(change(admin, "trainers", first, "account", account_id=trainer["id"]), 409, "catalog_entry_changed")
    code(change(admin, "trainers", second, "account", account_id=trainer["id"]), 409, "trainer_account_already_linked")
    for new_id in (None, other["id"]):
        code(change(admin, "trainers", linked, "account", account_id=new_id), 409, "future_training_assignment")
    for fields in ({"status": "disabled"}, {"role": "reception"}):
        code(edit(admin, trainer, **fields), 409, "future_training_assignment")
    assert trainer_session.get("/trainings").status_code == 200
    assert find(admin, "trener") == trainer
    demo.clock.set(demo.now + timedelta(days=4))
    admin = sign_in(demo, "first.admin")
    trainer_session = demo.client("trener")
    disabled = edit(admin, trainer, status="disabled").json()
    assert disabled["version"] == 2, disabled
    code(trainer_session.get("/trainings"), 401, "unauthorized")
    assert items(admin, "trainers")[0] == linked
    code(change(admin, "trainers", second, "account", account_id=trainer["id"]), 409, "trainer_account_ineligible")
    demoted = edit(admin, disabled, role="reception").json()
    assert demoted["role"] == "reception"
    replaced = change(admin, "trainers", linked, "account", account_id=other["id"]).json()
    inactive = change(admin, "trainers", replaced, "status", status="inactive").json()
    assert inactive["account_id"] == other["id"]
    code(change(admin, "trainers", inactive, "account", account_id=trainer["id"]), 409, "catalog_entry_inactive")
    assert change(admin, "trainers", inactive, "account", account_id=None).json()["account_id"] is None


@pytest.mark.parametrize("account_change", ({"status": "disabled"}, {"role": "reception"}))
@pytest.mark.parametrize("link_first", (True, False))
def test_SC_CAT07_link_races_account_change(demo, admin, monkeypatch, account_change, link_first):
    trainer = find(admin, "trener")
    first = items(admin, "trainers")[0]
    second_admin = sign_in(demo, "first.admin")
    both_arrive = Event()
    first_commits = Event()

    def first_write(original):
        def perform(*args, **kwargs):
            assert both_arrive.wait(timeout=5)
            try:
                return original(*args, **kwargs)
            finally:
                first_commits.set()
        return perform

    def second_write(original):
        def perform(*args, **kwargs):
            both_arrive.set()
            assert first_commits.wait(timeout=5)
            return original(*args, **kwargs)
        return perform

    link_wrapper, account_wrapper = (first_write, second_write) if link_first else (second_write, first_write)
    monkeypatch.setattr(catalog, "change_trainer_link", link_wrapper(catalog.change_trainer_link))
    monkeypatch.setattr(accounts, "change_account", account_wrapper(accounts.change_account))
    linked, changed = parallel(
        lambda: change(admin, "trainers", first, "account", account_id=trainer["id"]),
        lambda: edit(second_admin, trainer, **account_change),
    )
    if link_first:
        assert linked.status_code == 200
        code(changed, 409, "future_training_assignment")
        assert items(admin, "trainers")[0]["account_id"] == trainer["id"]
    else:
        assert changed.status_code == 200
        code(linked, 409, "trainer_account_ineligible")
        assert items(admin, "trainers")[0]["account_id"] is None


def test_SC_CAT07_concurrent_create_version_and_account_claim(demo, admin):
    another = sign_in(demo, "first.admin")
    key = str(uuid4())
    results = parallel(lambda: create(admin, "rooms", "Sála C", key), lambda: create(another, "rooms", "Sála C", key))
    room = results[0].json()
    assert all(response.status_code == 201 and response.json() == room for response in results)
    results = parallel(lambda: create(admin, "activities", "Nová aktivita"), lambda: create(another, "activities", "NOVÁ AKTIVITA"))
    assert sorted(response.status_code for response in results) == [201, 409]
    results = parallel(lambda: change(admin, "rooms", room, "name", name="Sála D"),
                       lambda: change(another, "rooms", room, "status", status="inactive"))
    assert sorted(response.status_code for response in results) == [200, 409]
    one, two = items(admin, "trainers")
    account_id = find(admin, "trener")["id"]
    results = parallel(lambda: change(admin, "trainers", one, "account", account_id=account_id),
                       lambda: change(another, "trainers", two, "account", account_id=account_id))
    assert sorted(response.status_code for response in results) == [200, 409]
    assert sum(row["account_id"] == account_id for row in items(admin, "trainers")) == 1


def test_SC_CAT07_08_rollback_and_queued_revocation(demo, admin, monkeypatch):
    with demo.db.transaction(write=True) as conn:
        conn.execute("CREATE TRIGGER refuse_receipt BEFORE INSERT ON catalog_creates "
                     "BEGIN SELECT RAISE(ABORT, 'private fixture'); END")
    error = create(admin, "rooms", "Sála C")
    code(error, 500, "internal_error")
    assert "private fixture" not in error.text and len(items(admin, "rooms")) == 2
    with demo.db.transaction(write=True) as conn:
        conn.execute("DROP TRIGGER refuse_receipt")
    assert provision(admin, "second.admin", "admin").status_code == 201
    second = sign_in(demo, "second.admin")
    create_entry = catalog.create_entry

    def revoke_first(*args):
        assert edit(second, find(second, "first.admin"), role="reception").status_code == 200
        return create_entry(*args)

    monkeypatch.setattr(catalog, "create_entry", revoke_first)
    code(create(admin, "rooms", "Sála C"), 401, "unauthorized")
    assert len(items(second, "rooms")) == 2


def test_SC_CAT09_live_labels_keep_booking_identity(demo, admin):
    anna = demo.client("anna")
    reservation_id = book(anna).json()["id_rezervacie"]
    activity = items(admin, "activities")[0]
    replacement = change(admin, "activities", activity, "name", name="Opravený názov").json()
    history = anna.get("/reservations").json()["items"][0]
    assert history["id_rezervacie"] == reservation_id and history["stav"] == "confirmed"
    assert history["training"]["aktivita"] == replacement["name"]
    assert anna.delete(f"/reservations/{reservation_id}").status_code == 200
    demo.clock.set(demo.now + timedelta(days=1))
    admin = sign_in(demo, "first.admin")
    assert change(admin, "activities", replacement, "status", status="inactive").status_code == 200
    history = demo.client("anna").get("/reservations").json()["items"][0]
    assert history["stav"] == "cancelled" and history["training"]["aktivita"] == replacement["name"]
    staff = demo.client("trener").get("/trainings").json()["items"]
    assert all(row["moja_rezervacia_id"] is None for row in staff)


def test_SC_CAT11_upgrade_seed_and_restart(demo, admin, tmp_path):
    with demo.db.transaction(write=True) as conn:
        remove_inc03_schema(conn)
        conn.execute("UPDATE metadata SET value='0.3.0' WHERE key='schema_version'")
        accounts_before = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        trainings_before = conn.execute("SELECT * FROM trainings ORDER BY id").fetchall()
    assert upgrade(demo.path) and not upgrade(demo.path)
    with demo.db.transaction() as conn:
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == SCHEMA_VERSION
        assert conn.execute("SELECT * FROM users ORDER BY id").fetchall() == accounts_before
        assert conn.execute("SELECT * FROM trainings ORDER BY id").fetchall() == trainings_before
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    trainer = items(admin, "trainers")[0]
    assert trainer["status"] == "active" and trainer["version"] == 1 and trainer["account_id"] is None
    key = str(uuid4())
    room = create(admin, "rooms", "Nová telocvičňa", key).json()
    inactive = change(admin, "rooms", room, "status", status="inactive").json()
    linked = change(admin, "trainers", trainer, "account", account_id=find(admin, "trener")["id"]).json()
    restarted = demo.client(application=create_app(demo.path, clock=demo.clock))
    restarted.cookies.update(admin.cookies)
    restarted.headers["X-CSRF-Token"] = admin.headers["X-CSRF-Token"]
    assert not initialize(demo.path, now=demo.now) and not upgrade(demo.path)
    assert inactive in items(restarted, "rooms") and linked in items(restarted, "trainers")
    assert create(restarted, "rooms", room["name"], key).json() == room
    with pytest.raises(sqlite3.OperationalError):
        upgrade(tmp_path / "missing.sqlite3")
    assert initialize(demo.path, reset=True, now=demo.now)
    with demo.db.transaction() as conn:
        assert conn.execute("SELECT count(*) FROM catalog_creates").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM trainers WHERE account_id IS NOT NULL").fetchone()[0] == 0
