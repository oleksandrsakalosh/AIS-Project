from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier, Event
import sqlite3

import pytest

from app import accounts, auth, booking
from app.bootstrap_admin import bootstrap, main as bootstrap_main
from app.db import instant
from app.errors import BusinessError
from app.main import create_app
from app.migrate import SCHEMA_VERSION, upgrade
from app.models import RegistrationInput
from app.seed import initialize
from conftest import book, code, count, remove_inc03_schema
from test_accounts import login


ADMIN = "/api/admin/accounts"
SIGNUP = "/api/account/registration"
PROFILE = "/api/account/profile"
PASSWORD = "FictionalStaff42!"


def credentials(username):
    return {"username": username, "display_name": username.title(), "password": PASSWORD}


def sign_in(demo, username):
    browser = demo.client()
    login(browser, credentials(username))
    return browser


@pytest.fixture
def admin(demo):
    bootstrap(demo.path, RegistrationInput(**credentials("first.admin")))
    return sign_in(demo, "first.admin")


def provision(admin, username, role):
    return admin.post(ADMIN, json={**credentials(username), "role": role})


def edit(admin, account, **change):
    field, = change
    return admin.put(f"{ADMIN}/{account['id']}/{field}", json={**change, "expected_version": account["version"]})


def find(admin, username):
    return next(account for account in admin.get(ADMIN).json()["items"] if account["username"] == username)


def parallel(*calls):
    start = Barrier(len(calls))

    def invoke(call):
        start.wait(timeout=5)
        return call()

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        jobs = [pool.submit(invoke, call) for call in calls]
        return [job.result(timeout=10) for job in jobs]


def test_SC_A01_cli_bootstrap_validates_and_preserves_identity(demo, monkeypatch, capsys, tmp_path):
    def run_cli(path, username):
        answers = iter((username, "Local administrator"))
        monkeypatch.setattr("builtins.input", lambda _: next(answers))
        monkeypatch.setattr("app.bootstrap_admin.getpass", lambda _: PASSWORD)
        monkeypatch.setattr("sys.argv", ["bootstrap_admin", "--db", str(path)])
        result = bootstrap_main()
        output = capsys.readouterr()
        assert PASSWORD not in output.out + output.err
        return result, output

    for username, message in [("x", "Invalid username"), ("anna", "already in use")]:
        result, output = run_cli(demo.path, username)
        assert result == 1 and message in output.err
    assert run_cli(tmp_path / "missing.sqlite3", "staff.admin")[0] == 1
    other = tmp_path / "other.sqlite3"
    with sqlite3.connect(other) as conn:
        conn.execute("CREATE TABLE unrelated(id)")
    assert run_cli(other, "staff.admin")[0] == 1
    result, output = run_cli(demo.path, "staff.admin")
    assert result == 0 and output.out == "Administrator created: staff.admin\n"
    assert run_cli(demo.path, "next.admin")[0] == 1
    assert sign_in(demo, "staff.admin").get(ADMIN).status_code == 200
    assert demo.client("anna").get("/session").json()["user"]["role"] == "client"


def test_SC_A01_concurrent_bootstrap(demo):
    def attempt(name):
        try:
            return bootstrap(demo.path, RegistrationInput(**credentials(name)))["role"]
        except BusinessError as exc:
            return exc.code

    assert sorted(parallel(lambda: attempt("first.admin"), lambda: attempt("other.admin"))) == [
        "admin", "administrator_exists"
    ]


def test_SC_A02_A10_visibility_and_error_order(demo, admin):
    visitor, client, trainer = demo.client(), demo.client("anna"), demo.client("trener")
    assert provision(admin, "front.desk", "reception").status_code == 201
    reception = sign_in(demo, "front.desk")
    for browser, redirect in [(visitor, "/login"), (client, "/schedule"), (trainer, "/staff"), (reception, "/staff")]:
        assert browser.get("/admin/accounts", follow_redirects=False).headers["location"] == redirect
        response = browser.get(ADMIN)
        code(response, 401 if browser is visitor else 403, "unauthorized" if browser is visitor else "forbidden")
        assert "display_name" not in response.text
    read = admin.get(ADMIN)
    assert read.headers["cache-control"] == "no-store"
    assert admin.get(ADMIN).json() == read.json()
    assert find(admin, "anna") == dict(id=1, username="anna", display_name="anna", role="client", status="active", version=1)
    for staff in (trainer, reception, admin):
        schedule = staff.get("/trainings").json()["items"]
        assert next(item for item in schedule if item["id_treningu"] == 1)["obsadene"] == 1
        assert all(item["moja_rezervacia_id"] is None and "participants" not in item for item in schedule)
        for path in (PROFILE, "/memberships/current", "/reservations"):
            code(staff.get(path), 403, "forbidden")
        assert staff.get("/register", follow_redirects=False).headers["location"] == "/staff"
    assert "admin/accounts" not in reception.get("/staff").text
    assert "Spravovať účty" in admin.get("/staff").text
    bad_url = ADMIN + "/NaN/status"
    for browser, status, expected in ((visitor, 401, "unauthorized"), (client, 403, "forbidden"),
                                       (admin, 403, "csrf_invalid")):
        code(browser.put(bad_url, content="broken", headers={"X-CSRF-Token": "bad"}), status, expected)
    for invalid in ("+1", "0", "1.1", "9007199254740992"):
        code(admin.put(f"{ADMIN}/{invalid}/status", json={"status": "disabled", "expected_version": 1}), 422, "validation")
    for version in (1.0, True, "1", 0, 9007199254740992):
        code(admin.put(f"{ADMIN}/1/status", json={"status": "disabled", "expected_version": version}), 422, "validation")
    code(admin.post(ADMIN, content="broken", headers={"Content-Type": "application/json"}), 422, "validation")
    login_error = visitor.post("/login", json={"username": "first.admin", "password": PASSWORD * 25})
    assert login_error.status_code == 422 and "detail" in login_error.json()
    assert PASSWORD not in login_error.text


def test_SC_A03_provisioning_and_shared_username_uniqueness(demo, admin):
    for role in ("trainer", "reception", "admin"):
        response = provision(admin, "new." + role, role)
        assert response.status_code == 201
        assert response.json()["role"] == role
        assert PASSWORD not in response.text
        assert sign_in(demo, "new." + role).get("/session").json()["user"]["role"] == role
    code(provision(admin, "client.new", "client"), 422, "validation")
    code(admin.post(ADMIN, json={**credentials("another"), "role": "trainer", "id": 1}), 422, "validation")
    with demo.db.transaction(write=True) as conn:
        conn.execute("UPDATE users SET username='Anna' WHERE id=1")
    code(provision(admin, "anna", "trainer"), 409, "username_taken")
    reception = find(admin, "new.reception")
    assert edit(admin, reception, status="disabled").status_code == 200
    code(provision(admin, reception["username"], "trainer"), 409, "username_taken")
    anonymous = demo.client()
    results = parallel(lambda: anonymous.post(SIGNUP, json=credentials("shared")),
                       lambda: provision(admin, "shared", "trainer"))
    assert sorted(result.status_code for result in results) == [201, 409]
    code(next(result for result in results if result.status_code == 409), 409, "username_taken")


def test_SC_A04_A05_disable_preserves_client_history_and_rejects_future_seats(demo, admin):
    cyril, second = demo.client("cyril"), demo.client("cyril")
    target = find(admin, "cyril")
    code(edit(admin, target, status="disabled"), 409, "future_reservation")
    reservations = cyril.get("/reservations").json()["items"]
    seat = reservations[0]["id_rezervacie"]
    assert cyril.delete(f"/reservations/{seat}").status_code == 200
    history = cyril.get("/reservations").json()
    response = edit(admin, target, status="disabled")
    assert response.json() == {**target, "status": "disabled", "version": 2}
    for old in (cyril, second):
        code(old.get(PROFILE), 401, "unauthorized")
        code(old.post("/logout"), 403, "csrf_invalid")
    guest = demo.client()
    disabled = guest.post("/login", json={"username": "cyril", "password": "Demo123!"})
    unknown = guest.post("/login", json={"username": "nobody", "password": "Demo123!"})
    code(disabled, 401, "invalid_credentials")
    assert disabled.json() == unknown.json()
    assert edit(admin, response.json(), status="active").json() == {**target, "version": 3}
    code(second.get(PROFILE), 401, "unauthorized")
    assert second.get("/session").json()["user"] is None
    assert demo.client("cyril").get("/reservations").json() == history
    assert demo.client("cyril").get("/memberships/current").json()["membership"]["stav"] == "expired"
    boris = find(admin, "boris")
    with demo.db.transaction() as conn:
        latest = conn.execute("SELECT starts_at FROM trainings WHERE id=3").fetchone()[0]
    demo.clock.set(instant(latest))
    assert edit(sign_in(demo, "first.admin"), boris, status="disabled").status_code == 200


def test_SC_A06_last_admin_and_simultaneous_reductions(demo, admin):
    first = find(admin, "first.admin")
    for change in ({"status": "disabled"}, {"role": "trainer"}):
        code(edit(admin, first, **change), 409, "last_active_admin")
    second = provision(admin, "second.admin", "admin").json()
    disabled = edit(admin, second, status="disabled").json()
    code(edit(admin, first, role="trainer"), 409, "last_active_admin")
    second = edit(admin, disabled, status="active").json()
    another = sign_in(demo, "second.admin")
    results = parallel(lambda: edit(admin, first, status="disabled"),
                       lambda: edit(another, second, role="reception"))
    assert sorted(response.status_code for response in results) == [200, 409]
    code(next(response for response in results if response.status_code == 409), 409, "last_active_admin")
    winner = admin if results[0].status_code == 200 else another
    code(winner.get(ADMIN), 401, "unauthorized")


@pytest.mark.parametrize("module, name, request_kind", [
    (booking, "create_reservation", "booking"),
    (booking, "cancel_reservation", "cancel"),
    (accounts, "update_display_name", "profile"),
])
def test_SC_A07_revoked_requests_waiting_at_the_write_boundary(demo, admin, monkeypatch, module, name, request_kind):
    anna = demo.client("anna")
    with demo.db.transaction(write=True) as conn:
        conn.execute("INSERT INTO reservations(user_id,training_id,status,created_at) "
                     "SELECT 1,id,'confirmed',starts_at FROM trainings WHERE id=4")
        past_id = conn.execute("SELECT max(id) FROM reservations").fetchone()[0]
    actions = {"booking": lambda: book(anna, training=2),
               "cancel": lambda: anna.delete(f"/reservations/{past_id}"),
               "profile": lambda: anna.put(PROFILE, json={"display_name": "New name"})}
    reached, release = Event(), Event()
    original = getattr(module, name)

    def pause(*args, **kwargs):
        reached.set()
        assert release.wait(timeout=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, name, pause)
    with ThreadPoolExecutor() as pool:
        task = pool.submit(actions[request_kind])
        try:
            assert reached.wait(timeout=5)
            assert edit(admin, find(admin, "anna"), status="disabled").status_code == 200
        finally:
            release.set()
        code(task.result(timeout=5), 401, "unauthorized")
    assert count(demo, 2) == 0
    assert find(admin, "anna")["display_name"] == "anna"


def test_SC_A07_booking_and_cancellation_commit_before_disable(demo, admin, monkeypatch):
    anna = demo.client("anna")
    target = find(admin, "anna")
    reached, release = Event(), Event()
    original = accounts.change_account

    def pause(*args, **kwargs):
        reached.set()
        assert release.wait(timeout=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(accounts, "change_account", pause)
    with ThreadPoolExecutor() as pool:
        first = pool.submit(edit, admin, target, status="disabled")
        try:
            assert reached.wait(timeout=5)
            seat = book(anna, training=2).json()["id_rezervacie"]
        finally:
            release.set()
        code(first.result(timeout=5), 409, "future_reservation")
        reached.clear()
        release.clear()
        second = pool.submit(edit, admin, target, status="disabled")
        try:
            assert reached.wait(timeout=5)
            assert anna.delete(f"/reservations/{seat}").status_code == 200
        finally:
            release.set()
        assert second.result(timeout=5).status_code == 200
    assert count(demo, 2) == 0


def test_SC_A08_role_changes_and_revocation(demo, admin):
    trainer = demo.client("trener")
    target = find(admin, "trener")
    role = edit(admin, target, role="reception").json()
    assert role == {**target, "role": "reception", "version": 2}
    code(trainer.get("/trainings"), 401, "unauthorized")
    code(trainer.post("/login", json={"username": "trener", "password": "Demo123!"}), 403, "csrf_invalid")
    reception = demo.client("trener")
    assert reception.get("/session").json()["user"]["role"] == "reception"
    code(reception.get(ADMIN), 403, "forbidden")
    code(edit(admin, find(admin, "anna"), role="trainer"), 409, "client_role_fixed")
    disabled = edit(admin, role, status="disabled").json()
    assert edit(admin, disabled, role="trainer").json()["status"] == "disabled"
    other = provision(admin, "second.admin", "admin").json()
    another = sign_in(demo, other["username"])
    assert edit(another, find(admin, "first.admin"), role="reception").status_code == 200
    code(admin.get(ADMIN), 401, "unauthorized")
    code(sign_in(demo, "first.admin").get(ADMIN), 403, "forbidden")


def test_SC_A08_login_racing_disable_checks_current_state(demo, admin, monkeypatch):
    guest = demo.client()
    reached, release = Event(), Event()
    original = auth.verify_password

    def pause(*args):
        reached.set()
        assert release.wait(timeout=5)
        return original(*args)

    monkeypatch.setattr(auth, "verify_password", pause)
    with ThreadPoolExecutor() as pool:
        task = pool.submit(guest.post, "/login", json={"username": "anna", "password": "Demo123!"})
        try:
            assert reached.wait(timeout=5)
            assert edit(admin, find(admin, "anna"), status="disabled").status_code == 200
        finally:
            release.set()
        code(task.result(timeout=5), 401, "invalid_credentials")
    assert guest.get("/session").json()["user"] is None


def test_SC_A09_stale_versions_noop_and_atomic_failures(demo, admin):
    trainer = demo.client("trener")
    target = find(admin, "trener")
    assert edit(admin, target, status="active").json() == target
    assert trainer.get("/trainings").status_code == 200
    code(edit(admin, {**target, "id": 999}, status="disabled"), 404, "account_not_found")
    with demo.db.transaction(write=True) as conn:
        conn.execute("CREATE TRIGGER reject_revoke AFTER DELETE ON sessions "
                     "BEGIN SELECT RAISE(FAIL, 'private failure'); END")
        conn.execute("CREATE TRIGGER reject_create AFTER INSERT ON users "
                     "BEGIN SELECT RAISE(FAIL, 'private failure'); END")
    for response in (edit(admin, target, status="disabled"), provision(admin, "fail.staff", "trainer")):
        code(response, 500, "internal_error")
        assert "private failure" not in response.text
    assert find(admin, "trener") == target and trainer.get("/trainings").status_code == 200
    assert all(item["username"] != "fail.staff" for item in admin.get(ADMIN).json()["items"])
    with demo.db.transaction(write=True) as conn:
        conn.execute("DROP TRIGGER reject_revoke")
        conn.execute("DROP TRIGGER reject_create")
    other = sign_in(demo, provision(admin, "second.admin", "admin").json()["username"])
    results = parallel(lambda: edit(admin, target, status="disabled"), lambda: edit(other, target, role="reception"))
    assert sorted(response.status_code for response in results) == [200, 409]
    code(next(response for response in results if response.status_code == 409), 409, "account_changed")
    assert find(admin, "trener")["version"] == 2


def test_SC_A11_migration_and_reset(demo, tmp_path):
    anna = demo.client("anna")
    assert anna.put(PROFILE, json={"display_name": "Anna NOVA"}).status_code == 200
    seat = book(anna, training=2).json()["id_rezervacie"]
    schema = (Path(__file__).parents[1] / "app" / "schema.sql").read_text(encoding="utf-8")
    legacy_users = schema[schema.index("CREATE TABLE users"):schema.index("CREATE TABLE memberships")]
    legacy_users = legacy_users[:legacy_users.index("    status TEXT")].rstrip().removesuffix(",") + "\n);"
    legacy_users = legacy_users.replace("'client','trainer','reception','admin'", "'client','trainer'")
    with closing(sqlite3.connect(demo.path)) as source:
        with closing(sqlite3.connect(tmp_path / "legacy.sqlite3")) as legacy:
            source.backup(legacy)
    path = tmp_path / "legacy.sqlite3"
    with closing(sqlite3.connect(path)) as conn, conn:
        remove_inc03_schema(conn)
        rows = conn.execute("SELECT id, username, password_hash, role, display_name FROM users").fetchall()
        conn.execute("DROP TABLE users")
        conn.execute(legacy_users)
        conn.executemany("INSERT INTO users VALUES (?,?,?,?,?)", rows)
        conn.execute("UPDATE metadata SET value='0.2.0' WHERE key='schema_version'")
        conn.execute("UPDATE sqlite_sequence SET seq=50 WHERE name='users'")
    assert upgrade(path) and not upgrade(path)
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone() == (SCHEMA_VERSION,)
        assert conn.execute("SELECT id,username,password_hash,role,display_name FROM users").fetchall() == rows
    restored = demo.client(application=create_app(path, clock=demo.clock))
    restored.cookies.update(anna.cookies)
    assert restored.get(PROFILE).json()["display_name"] == "Anna NOVA"
    assert restored.get("/reservations").json()["items"][0]["id_rezervacie"] == seat
    assert bootstrap(path, RegistrationInput(**credentials("first.admin")))["id"] == 51
    assert not initialize(path, now=demo.now)
    assert initialize(path, reset=True, now=demo.now)
    assert bootstrap(path, RegistrationInput(**credentials("first.admin")))["id"] == 6


def test_SC_A11_failed_upgrade_rolls_back(demo):
    with closing(sqlite3.connect(demo.path)) as conn, conn:
        remove_inc03_schema(conn)
        conn.execute("ALTER TABLE users DROP COLUMN display_name")
        conn.execute("UPDATE metadata SET value='0.1.1' WHERE key='schema_version'")
        conn.execute("UPDATE reservations SET user_id=999 WHERE id=1")
    with pytest.raises(sqlite3.IntegrityError, match="Foreign key check"):
        upgrade(demo.path)
    with closing(sqlite3.connect(demo.path)) as conn:
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone() == ("0.1.1",)
        assert "display_name" not in {row[1] for row in conn.execute("PRAGMA table_info(users)")}
