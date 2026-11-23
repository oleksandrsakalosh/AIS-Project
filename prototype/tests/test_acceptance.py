from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import sqlite3
from threading import Barrier, Event

import pytest

from app.auth import COOKIE
from app.db import stamp
from app.main import create_app
from app.seed import initialize
from conftest import book, code, count


def test_SC_P01_login_credentials_and_session_rotation(demo):
    browser = demo.client()
    old_cookie = browser.cookies.get(COOKIE)
    assert browser.get("/session").json()["user"] is None
    for username in ("anna", "does-not-exist"):
        code(browser.post("/login", json={"username": username, "password": "wrong"}), 401, "invalid_credentials")
    response = browser.post("/login", json={"username": "anna", "password": "Demo123!"})
    assert response.json()["user"] == {"id": 1, "username": "anna", "role": "client"}
    assert browser.cookies.get(COOKIE) != old_cookie
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
    stranger = demo.client()
    stranger.cookies.set(COOKIE, old_cookie, domain="testserver.local", path="/")
    code(stranger.get("/reservations"), 401, "unauthorized")
    with demo.db.transaction() as conn:
        stored = conn.execute("SELECT password_hash FROM users WHERE id=1").fetchone()[0]
        assert stored.startswith("scrypt$") and "Demo123!" not in stored
        assert not conn.execute("SELECT 1 FROM sessions WHERE token_hash=?", (browser.cookies.get(COOKIE),)).fetchone()


def test_SC_P02_schedule_projection_and_trainer_read_access(demo):
    anna, boris, trainer = demo.client("anna"), demo.client("boris"), demo.client("trener")
    items = {row["id_treningu"]: row for row in anna.get("/trainings").json()["items"]}
    assert (items[1]["kapacita"], items[1]["obsadene"], items[1]["volne_miesta"]) == (3, 1, 2)
    assert items[1]["moja_rezervacia_id"] is None
    assert boris.get("/trainings").json()["items"] != []
    assert next(row for row in boris.get("/trainings").json()["items"] if row["id_treningu"] == 1)["moja_rezervacia_id"] == 1
    assert all(row["moja_rezervacia_id"] is None for row in trainer.get("/trainings").json()["items"])
    assert set(items[1]) == {"id_treningu","aktivita","trener","priestor","starts_at","ends_at","kapacita","obsadene","volne_miesta","moja_rezervacia_id"}
    assert "password" not in anna.get("/trainings").text and "username" not in anna.get("/trainings").text


def test_SC_P03_booking_persists_and_membership_need_not_cover_training(demo):
    anna = demo.client("anna")
    with demo.db.transaction(write=True) as conn:
        conn.execute("UPDATE memberships SET valid_until=? WHERE user_id=1", (stamp(demo.now+timedelta(hours=1)),))
    response = book(anna)
    assert response.status_code == 201
    assert response.json()["stav"] == "confirmed"
    assert count(demo) == 2
    assert anna.get("/reservations").json()["items"][0]["id_rezervacie"] == response.json()["id_rezervacie"]


def test_SC_P04_full_training_has_no_mutation(demo):
    code(book(demo.client("anna"), 3), 409, "capacity_full")
    assert count(demo, 3) == 1


@pytest.mark.parametrize("state", ["absent", "pending", "expired", "not-yet-valid"])
def test_SC_P05_inactive_membership(demo, state):
    anna = demo.client("anna")
    with demo.db.transaction(write=True) as conn:
        if state == "absent":
            conn.execute("DELETE FROM memberships WHERE user_id=1")
        elif state == "not-yet-valid":
            conn.execute("UPDATE memberships SET valid_from=? WHERE user_id=1", (stamp(demo.now+timedelta(hours=1)),))
        else:
            conn.execute("UPDATE memberships SET status=? WHERE user_id=1", (state,))
    view = anna.get("/memberships/current").json()["membership"]
    assert view is None if state == "absent" else view["stav"] == ("pending" if state == "not-yet-valid" else state)
    code(book(anna), 403, "membership_inactive")
    assert count(demo) == 1


@pytest.mark.parametrize("offset,allowed,effective", [(-1,False,"pending"),(0,True,"active"),(3599999999,True,"active"),(3600000000,False,"expired")])
def test_SC_P05_validity_boundaries(demo, offset, allowed, effective):
    with demo.db.transaction(write=True) as conn:
        conn.execute("UPDATE memberships SET valid_from=?,valid_until=? WHERE user_id=1",
                     (stamp(demo.now),stamp(demo.now+timedelta(hours=1))))
    demo.clock.set(demo.now+timedelta(microseconds=offset))
    anna = demo.client("anna")
    assert anna.get("/memberships/current").json()["membership"]["stav"] == effective
    response = book(anna)
    if allowed:
        assert response.status_code == 201
    else:
        code(response, 403, "membership_inactive")


def test_SC_P06_duplicate_precedes_full_and_inactive_membership(demo):
    anna = demo.client("anna")
    assert book(anna, 2).status_code == 201
    code(book(anna, 2), 409, "duplicate_reservation")
    with demo.db.transaction(write=True) as conn:
        conn.execute("UPDATE memberships SET status='expired' WHERE user_id=1")
    code(book(anna, 2), 409, "duplicate_reservation")
    assert count(demo, 2) == 1


def test_SC_P07_SC_P08_cancel_history_and_repeat_after_start(demo):
    anna = demo.client("anna")
    with demo.db.transaction(write=True) as conn:
        conn.execute("UPDATE trainings SET starts_at=?,ends_at=? WHERE id=1", (stamp(demo.now+timedelta(minutes=1)),stamp(demo.now+timedelta(hours=1))))
    reservation_id = book(anna).json()["id_rezervacie"]
    cancelled = anna.delete(f"/reservations/{reservation_id}")
    assert cancelled.status_code == 200 and count(demo) == 1
    assert anna.delete(f"/reservations/{reservation_id}").json() == cancelled.json()
    demo.clock.set(demo.now+timedelta(minutes=2))
    assert anna.delete(f"/reservations/{reservation_id}").json() == cancelled.json()
    history = anna.get("/reservations").json()["items"]
    assert history[0]["stav"] == "cancelled" and history[0]["cancelled_at"]
    assert count(demo) == 1


def test_SC_P09_rebooking_delayed_post_and_old_delete(demo):
    anna = demo.client("anna")
    old_id = book(anna, 2).json()["id_rezervacie"]
    assert anna.delete(f"/reservations/{old_id}").status_code == 200
    # Identical delayed replay is intentionally indistinguishable from an intentional new booking.
    new_id = book(anna, 2).json()["id_rezervacie"]
    assert new_id != old_id
    assert anna.delete(f"/reservations/{old_id}").status_code == 200
    assert count(demo, 2) == 1
    assert {row["id_rezervacie"]: row["stav"] for row in anna.get("/reservations").json()["items"]} == {old_id:"cancelled",new_id:"confirmed"}


def test_SC_P10_ownership_scoping_and_missing_ids(demo):
    anna = demo.client("anna")
    assert book(anna).status_code == 201
    own = anna.get("/reservations?id_klienta=2").json()["items"]
    assert len(own) == 1 and own[0]["id_rezervacie"] not in (1,2,3)
    for reservation_id in (1,999999):
        code(anna.delete(f"/reservations/{reservation_id}"), 404, "reservation_not_found")
    code(book(anna, 999999), 404, "training_not_found")
    assert count(demo) == 2


def test_SC_P11_browser_identity_and_role_are_not_authentication(demo):
    anna = demo.client("anna")
    code(book(anna, user=2), 403, "client_mismatch")
    assert count(demo) == 1
    anonymous = demo.client()
    anonymous.cookies.set(COOKIE, '{"id":1,"role":"client"}', domain="testserver.local", path="/")
    code(book(anonymous), 401, "unauthorized")


@pytest.mark.parametrize("method,path", [("GET","/trainings"),("GET","/memberships/current"),("GET","/reservations"),("POST","/reservations"),("DELETE","/reservations/not-an-id")])
def test_SC_P12_authentication_precedes_invalid_input_and_csrf(demo, method, path):
    browser = demo.client()
    response = browser.request(method, path, content="not json", headers={"X-CSRF-Token":"wrong"})
    code(response, 401, "unauthorized")


@pytest.mark.parametrize("method,path", [("GET","/memberships/current"),("GET","/reservations"),("POST","/reservations"),("DELETE","/reservations/not-an-id")])
def test_SC_P12_trainer_role_precedes_csrf_and_validation(demo, method, path):
    trainer = demo.client("trener")
    code(trainer.request(method, path, content="not json", headers={"X-CSRF-Token":"wrong"}), 403, "forbidden")
    assert trainer.get("/trainings").status_code == 200


@pytest.mark.parametrize("offset", [0,-1])
def test_SC_P13_training_start_boundary_precedes_duplicate(demo, offset):
    anna = demo.client("anna")
    reservation_id = book(anna).json()["id_rezervacie"]
    with demo.db.transaction(write=True) as conn:
        conn.execute("UPDATE trainings SET starts_at=? WHERE id=1", (stamp(demo.now+timedelta(seconds=offset)),))
    code(book(anna), 409, "training_started")
    code(anna.delete(f"/reservations/{reservation_id}"), 409, "training_started")
    code(book(anna, 4), 409, "training_started")
    assert count(demo) == 2


def simultaneous(*operations):
    barrier = Barrier(len(operations))
    def run(operation):
        barrier.wait(timeout=5)
        return operation()
    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        futures = [pool.submit(run, operation) for operation in operations]
        return [future.result(timeout=10) for future in futures]


@pytest.mark.parametrize("attempt", range(3))
def test_SC_P14_final_seat_real_concurrent_requests(demo, attempt):
    anna, boris = demo.client("anna"), demo.client("boris")
    responses = simultaneous(lambda: book(anna, 2), lambda: book(boris, 2, 2))
    assert sorted(response.status_code for response in responses) == [201,409]
    code(next(response for response in responses if response.status_code == 409),409,"capacity_full")
    assert count(demo, 2) == 1


def test_SC_P14_same_client_and_simultaneous_cancellation(demo):
    anna1, anna2 = demo.client("anna"), demo.client("anna")
    responses = simultaneous(lambda: book(anna1,2), lambda: book(anna2,2))
    assert sorted(response.status_code for response in responses) == [201,409]
    code(next(response for response in responses if response.status_code == 409),409,"duplicate_reservation")
    reservation_id = next(response for response in responses if response.status_code == 201).json()["id_rezervacie"]
    responses = simultaneous(lambda: anna1.delete(f"/reservations/{reservation_id}"), lambda: anna2.delete(f"/reservations/{reservation_id}"))
    assert [response.status_code for response in responses] == [200,200]
    assert count(demo, 2) == 0


def test_SC_P14_create_cancel_race_preserves_capacity(demo):
    anna, boris = demo.client("anna"), demo.client("boris")
    created, cancelled = simultaneous(lambda: book(anna,3), lambda: boris.delete("/reservations/2"))
    assert cancelled.status_code == 200
    assert created.status_code in (201,409)
    if created.status_code == 409:
        code(created,409,"capacity_full")
    assert count(demo, 3) == (1 if created.status_code == 201 else 0)


@pytest.mark.parametrize("boundary", ["membership", "training", "cancel"])
@pytest.mark.parametrize("wait_mode", ["wait", "retry"])
def test_SC_P14_fresh_clock_after_lock_wait_and_retry(demo, monkeypatch, boundary, wait_mode):
    anna = demo.client("anna")
    reservation_id = book(anna).json()["id_rezervacie"] if boundary == "cancel" else None
    with demo.db.transaction(write=True) as conn:
        if boundary == "membership":
            conn.execute("UPDATE memberships SET valid_until=? WHERE user_id=1", (stamp(demo.now+timedelta(seconds=10)),))
        else:
            conn.execute("UPDATE trainings SET starts_at=? WHERE id=1", (stamp(demo.now+timedelta(seconds=10)),))
    waiting, retrying = Event(), Event()
    attempts = []
    class ObservedConnection(sqlite3.Connection):
        def execute(self, sql, parameters=()):
            if sql == "BEGIN IMMEDIATE":
                attempts.append(True)
                waiting.set()
                if len(attempts) >= 2:
                    retrying.set()
            return super().execute(sql, parameters)
    def observed_connect():
        conn = sqlite3.connect(demo.path, timeout=0.01 if wait_mode == "retry" else 1, factory=ObservedConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    monkeypatch.setattr(demo.db, "connect", observed_connect)
    blocker = sqlite3.connect(demo.path)
    blocker.execute("BEGIN IMMEDIATE")
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(lambda: anna.delete(f"/reservations/{reservation_id}") if boundary == "cancel" else book(anna))
            try:
                assert waiting.wait(5), "Request never attempted the write lock"
                if wait_mode == "retry":
                    assert retrying.wait(5), "Request did not retry a real SQLITE_BUSY"
                demo.clock.set(demo.now+timedelta(seconds=20))
            finally:
                blocker.rollback()
            response = future.result(timeout=10)
    finally:
        blocker.close()
    code(response, 403 if boundary == "membership" else 409, "membership_inactive" if boundary == "membership" else "training_started")
    assert count(demo) == (2 if boundary == "cancel" else 1)


def test_SC_P15_application_reopen_uses_same_persistent_database(demo):
    anna = demo.client("anna")
    reservation_id = book(anna,2).json()["id_rezervacie"]
    reopened = create_app(demo.path, clock=demo.clock)
    fresh = demo.client("anna", application=reopened)
    assert fresh.get("/reservations").json()["items"][0]["id_rezervacie"] == reservation_id
    assert next(row for row in fresh.get("/trainings").json()["items"] if row["id_treningu"] == 2)["volne_miesta"] == 0


def test_SC_P16_csrf_precedes_malformed_body_and_path(demo):
    anna, boris = demo.client("anna"), demo.client("boris")
    for token in ("", "invalid", boris.headers["X-CSRF-Token"]):
        code(anna.post("/reservations", content="not json", headers={"X-CSRF-Token":token}),403,"csrf_invalid")
        code(anna.delete("/reservations/not-an-id", headers={"X-CSRF-Token":token}),403,"csrf_invalid")
    assert anna.post("/reservations", content="not json").status_code == 422
    for invalid in (0,-1,True,"1",1.5,None):
        response = anna.post("/reservations", json={"id_klienta":1,"id_treningu":invalid})
        assert response.status_code == 422 and "detail" in response.json()
    assert anna.delete("/reservations/0").status_code == 422
    assert anna.delete("/reservations/not-an-id").status_code == 422
    assert anna.post("/reservations", json={"id_klienta":1,"id_treningu":1,"role":"trainer"}).status_code == 422
    assert count(demo) == 1


def test_SC_P16_login_logout_csrf_expiry_and_repeated_logout(demo):
    anonymous = demo.client()
    code(anonymous.post("/login", content="not json", headers={"X-CSRF-Token":"bad"}),403,"csrf_invalid")
    anna = demo.client("anna")
    code(anna.post("/logout", headers={"X-CSRF-Token":"bad"}),403,"csrf_invalid")
    assert anna.post("/logout").status_code == 204
    code(anna.get("/reservations"),401,"unauthorized")
    session = anna.get("/session").json()
    assert session["user"] is None
    assert anna.post("/logout", headers={"X-CSRF-Token":session["csrf_token"]}).status_code == 204
    expiring = demo.client("anna")
    demo.clock.set(demo.now+timedelta(days=1))
    code(expiring.get("/reservations"),401,"unauthorized")


def test_SC_P17_expired_owner_can_cancel_but_not_book(demo):
    cyril = demo.client("cyril")
    assert cyril.delete("/reservations/3").status_code == 200
    assert count(demo,5) == 0
    code(book(cyril,5,3),403,"membership_inactive")


def test_SC_P18_storage_failure_rolls_back_insert_and_is_sanitized(demo):
    anna = demo.client("anna")
    with demo.db.transaction(write=True) as conn:
        conn.execute("CREATE TRIGGER injected_failure AFTER INSERT ON reservations BEGIN SELECT RAISE(FAIL,'sensitive internal disk detail'); END")
    response = book(anna)
    code(response,500,"internal_error")
    assert "sensitive" not in response.text and count(demo) == 1
    assert anna.get("/reservations").json()["items"] == []


def test_SC_P18_unavailable_storage_does_not_create_an_empty_database(demo, tmp_path):
    missing_path = tmp_path / "missing.sqlite3"
    unavailable = create_app(missing_path)
    from fastapi.testclient import TestClient
    with TestClient(unavailable, raise_server_exceptions=False) as browser:
        code(browser.get("/health"),503,"storage_unavailable")
    assert not missing_path.exists()


def test_SC_P19_initialization_preserves_data_and_explicit_reset_restores_fixtures(demo):
    anna = demo.client("anna")
    assert book(anna,2).status_code == 201
    assert initialize(demo.path,now=demo.now+timedelta(days=10)) is False
    assert count(demo,2) == 1
    with demo.db.transaction() as conn:
        assert conn.execute("SELECT value FROM metadata WHERE key='seeded_at'").fetchone()[0] == stamp(demo.now)
    assert initialize(demo.path,reset=True,now=demo.now) is True
    assert count(demo,2) == 0
    with demo.db.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM reservations").fetchone()[0] == 3


def test_SC_P19_reset_refuses_an_unrelated_database(tmp_path):
    path = tmp_path / "unrelated.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE precious (value TEXT)")
        conn.execute("INSERT INTO precious VALUES ('keep')")
    with pytest.raises(ValueError,match="not owned"):
        initialize(path,reset=True)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT value FROM precious").fetchone()[0] == "keep"


def test_SC_P20_html_auth_pages_and_contract_metadata(demo):
    anonymous = demo.client()
    assert anonymous.get("/schedule",follow_redirects=False).status_code == 303
    anna, trainer = demo.client("anna"), demo.client("trener")
    assert 'lang="sk"' in anna.get("/schedule").text
    assert 'id="reservations"' in anna.get("/my-reservations").text
    assert 'href="/my-reservations"' not in trainer.get("/schedule").text
    assert trainer.get("/my-reservations",follow_redirects=False).headers["location"] == "/staff"
    document = anna.get("/openapi.json").json()
    assert document["info"]["version"] == "0.3.0"
    assert set(document["paths"]) == {
        "/health", "/session", "/login", "/logout", "/trainings", "/memberships/current",
        "/reservations", "/reservations/{id_rezervacie}", "/api/admin/accounts",
        "/api/admin/accounts/{account_id}/role", "/api/admin/accounts/{account_id}/status",
        "/api/admin/catalog/{kind}", "/api/admin/catalog/{kind}/{entry_id}/name",
        "/api/admin/catalog/{kind}/{entry_id}/status", "/api/admin/catalog/trainers/{entry_id}/account",
    }
    assert document["components"]["schemas"]["SessionUser"]["properties"]["role"]["enum"] == [
        "client", "trainer", "reception", "admin"
    ]
