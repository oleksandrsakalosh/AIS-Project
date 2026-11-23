import sqlite3

import pytest

from app.auth import verify_password
from app.main import create_app
from app.migrate import upgrade
from conftest import book, code, count, remove_inc03_schema
from test_acceptance import simultaneous


SIGNUP = "/api/account/registration"
PROFILE = "/api/account/profile"
CLIENT = {"username": "eva.demo", "password": "Fictional pass phrase", "display_name": "Eva Nová"}


def login(browser, credentials=CLIENT):
    response = browser.post("/login", json={key: credentials[key] for key in ("username", "password")})
    assert response.status_code == 200
    browser.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()["user"]


def test_SC_C01_SC_C06_registration_is_account_only(demo):
    browser = demo.client()
    response = browser.post(SIGNUP, json={**CLIENT, "display_name": "  Eva Nová  "})
    assert response.status_code == 201 and response.json() == {"username": CLIENT["username"]}
    assert browser.get("/session").json()["user"] is None
    code(browser.get("/trainings"), 401, "unauthorized")

    user = login(browser)
    assert user["role"] == "client"
    assert browser.get(PROFILE).json() == {**user, "display_name": CLIENT["display_name"]}
    assert browser.get("/trainings").json()["items"]
    assert browser.get("/reservations").json() == {"items": []}
    assert browser.get("/memberships/current").json() == {"membership": None}
    code(book(browser, user=user["id"]), 403, "membership_inactive")
    assert count(demo) == 1
    with demo.db.transaction() as conn:
        password_hash = conn.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()[0]
        assert password_hash.startswith("scrypt$") and CLIENT["password"] not in password_hash
        assert verify_password(CLIENT["password"], password_hash)
        assert conn.execute("SELECT COUNT(*) FROM memberships").fetchone()[0] == 4


def test_SC_C02_own_name_survives_reopen_and_repeat(demo):
    anna = demo.client("anna")
    before = anna.get(PROFILE).json()
    assert before == {"id": 1, "username": "anna", "role": "client", "display_name": "anna"}
    expected = {**before, "display_name": "Anna Živá"}
    for _ in range(2):
        updated = anna.put(PROFILE, json={"display_name": " Anna Živá "})
        assert updated.status_code == 200 and updated.json() == expected
    reopened = create_app(demo.path, clock=demo.clock)
    assert demo.client("anna", application=reopened).get(PROFILE).json() == expected
    assert demo.client("boris", application=reopened).get(PROFILE).json()["display_name"] == "boris"


def test_SC_C03_duplicate_signup_preserves_identity_and_credentials(demo):
    first = demo.client()
    second = demo.client()
    with demo.db.transaction(write=True) as conn:
        conn.execute("UPDATE users SET username='Anna' WHERE id=1")
    code(first.post(SIGNUP, json={**CLIENT, "username": "anna"}), 409, "username_taken")
    responses = simultaneous(lambda: first.post(SIGNUP, json=CLIENT), lambda: second.post(SIGNUP, json=CLIENT))
    assert sorted(response.status_code for response in responses) == [201, 409]
    code(second.post(SIGNUP, json={**CLIENT, "display_name": "Changed", "password": "different-secret"}),
         409, "username_taken")
    assert login(first)["username"] == CLIENT["username"]
    assert first.get(PROFILE).json()["display_name"] == CLIENT["display_name"]
    with demo.db.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE username=?", (CLIENT["username"],)).fetchone()[0] == 1


@pytest.mark.parametrize("override", [
    {"role": "trainer"}, {"id": 2}, {"membership": "active"},
    {"username": "Eva"}, {"username": "eva\n"}, {"password": "too-short"},
    {"display_name": "  "}, {"display_name": "Eva\tNová"}, {"display_name": "A" * 81},
])
def test_SC_C04_invalid_signup_does_not_echo_values(demo, override):
    browser = demo.client()
    response = browser.post(SIGNUP, json={**CLIENT, **override})
    code(response, 422, "validation")
    assert "input" not in response.text and CLIENT["password"] not in response.text
    with demo.db.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 5


def test_SC_C04_SC_C05_csrf_role_and_ownership_precedence(demo):
    anon = demo.client()
    anna = demo.client("anna")
    trainer = demo.client("trener")
    bad_csrf = {"X-CSRF-Token": "wrong"}
    code(anon.post(SIGNUP, content="not JSON", headers=bad_csrf), 403, "csrf_invalid")
    code(anon.post(SIGNUP, content='{"password":"unparsed-secret"', headers=anon.headers), 422, "validation")
    code(anna.post(SIGNUP, content="not JSON", headers=bad_csrf), 403, "already_signed_in")
    code(anon.get(PROFILE), 401, "unauthorized")
    code(anon.put(PROFILE, content="not JSON", headers=bad_csrf), 401, "unauthorized")
    code(trainer.get(PROFILE), 403, "forbidden")
    code(trainer.put(PROFILE, content="not JSON", headers=bad_csrf), 403, "forbidden")
    code(anna.put(PROFILE, content="not JSON", headers=bad_csrf), 403, "csrf_invalid")
    code(anna.put(PROFILE, json={"display_name": "Changed", "id": 2}), 422, "validation")
    assert anna.get(PROFILE + "?id=2").json()["id"] == 1
    assert anna.get(PROFILE).json()["display_name"] == "anna"
    assert demo.client("boris").get(PROFILE).json()["display_name"] == "boris"


def test_SC_C07_write_failures_rollback_and_a_committed_signup_can_be_recovered(demo):
    anon, anna = demo.client(), demo.client("anna")
    with demo.db.transaction(write=True) as conn:
        conn.execute("CREATE TRIGGER fail_signup AFTER INSERT ON users BEGIN SELECT RAISE(FAIL,'private detail'); END")
        conn.execute("CREATE TRIGGER fail_profile AFTER UPDATE OF display_name ON users BEGIN SELECT RAISE(FAIL,'private detail'); END")
    for response in (anon.post(SIGNUP, json=CLIENT), anna.put(PROFILE, json={"display_name": "New name"})):
        code(response, 500, "internal_error")
        assert "private" not in response.text
    assert anna.get(PROFILE).json()["display_name"] == "anna"
    with demo.db.transaction(write=True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE username=?", (CLIENT["username"],)).fetchone()[0] == 0
        conn.execute("DROP TRIGGER fail_signup")
    # Discard the successful response and use the ordinary login flow to recover.
    anon.post(SIGNUP, json=CLIENT)
    assert login(anon)["username"] == CLIENT["username"]
    with demo.db.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE username=?", (CLIENT["username"],)).fetchone()[0] == 1


def test_SC_C08_upgrade_preserves_sessions_and_booking_history(demo):
    anna = demo.client("anna")
    trainer = demo.client("trener")
    reserved = book(anna).json()["id_rezervacie"]
    with demo.db.transaction(write=True) as conn:
        remove_inc03_schema(conn)
        conn.execute("ALTER TABLE users DROP COLUMN display_name")
        conn.execute("UPDATE metadata SET value='0.1.1' WHERE key='schema_version'")
    assert upgrade(demo.path) is True
    assert upgrade(demo.path) is False

    reopened = create_app(demo.path, clock=demo.clock)
    restored = demo.client(application=reopened)
    restored.cookies.update(anna.cookies)
    restored.headers["X-CSRF-Token"] = anna.headers["X-CSRF-Token"]
    assert restored.get(PROFILE).json()["display_name"] == "anna"
    assert restored.get("/reservations").json()["items"][0]["id_rezervacie"] == reserved
    assert restored.delete(f"/reservations/{reserved}").json()["stav"] == "cancelled"
    assert book(restored).status_code == 201
    assert demo.client("anna", application=reopened).get(PROFILE).status_code == 200

    restored_trainer = demo.client(application=reopened)
    restored_trainer.cookies.update(trainer.cookies)
    assert restored_trainer.get("/trainings").status_code == 200
    code(restored_trainer.get(PROFILE), 403, "forbidden")


def test_upgrade_refuses_unrelated_storage(tmp_path):
    path = tmp_path / "unrelated.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE other (id INTEGER)")
    with pytest.raises(ValueError, match="not owned"):
        upgrade(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT name FROM sqlite_master").fetchall() == [("other",)]


def test_SC_C09_page_navigation_respects_role(demo):
    anonymous, anna, trainer = demo.client(), demo.client("anna"), demo.client("trener")
    assert 'href="/register"' in anonymous.get("/login").text
    assert 'id="registration-form"' in anonymous.get("/register").text
    assert anonymous.get("/profile", follow_redirects=False).headers["location"] == "/login"
    assert anna.get("/register", follow_redirects=False).headers["location"] == "/schedule"
    assert 'aria-current="page">Môj profil' in anna.get("/profile").text
    assert trainer.get("/profile", follow_redirects=False).headers["location"] == "/staff"
    assert 'href="/profile"' not in trainer.get("/schedule").text
