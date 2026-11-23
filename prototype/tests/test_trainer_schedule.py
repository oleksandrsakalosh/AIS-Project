from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta
from itertools import count
from threading import Event
from uuid import uuid4

import pytest

from app.db import instant, stamp
from app.main import create_app
from app.migrate import SCHEMA_VERSION, upgrade
from app.seed import initialize
from conftest import book, code, remove_inc04_schema
from test_admin import admin, edit as edit_account, find, parallel, provision, sign_in
from test_catalog import change, items


PATH = "/api/trainer/schedule"
PAGE = "/staff/training-schedule"


def link(demo, admin, trainer_id, username):
    row = next(trainer for trainer in items(admin, "trainers") if trainer["id"] == trainer_id)
    response = change(admin, "trainers", row, "account", account_id=find(admin, username)["id"])
    assert response.status_code == 200, response.text
    return demo.client(username) if username == "trener" else sign_in(demo, username)


@pytest.fixture
def trainer(demo, admin):
    return link(demo, admin, 1, "trener")


def payload(demo, *, days=6, hours=0, room=1, capacity=3, seconds=0):
    start = demo.now + timedelta(days=days, hours=hours, seconds=seconds)
    return {"activity_id": 1, "room_id": room, "capacity": capacity, "starts_at": stamp(start),
            "ends_at": stamp(start + timedelta(hours=1)), "request_id": str(uuid4())}


def publish(trainer, data):
    response = trainer.post(PATH, json=data)
    assert response.status_code == 201, response.text
    return response.json()


def get_schedule(trainer):
    response = trainer.get(PATH)
    assert response.status_code == 200, response.text
    return response.json()


def update(trainer, training, **fields):
    data = {key: training[key] for key in ("activity_id", "room_id", "capacity", "starts_at", "ends_at")}
    return trainer.put(f"{PATH}/{training['id_treningu']}",
                       json={**data, "expected_version": training["version"], **fields})


def race_in_order(demo, monkeypatch, first, second):
    """Hold the first connection's write lock until the second request tries to write."""
    locked, attempted = Event(), Event()
    sequence = count()
    transaction = demo.db.transaction

    @contextmanager
    def gated(*, write=False, **kwargs):
        turn = next(sequence) if write else None
        if turn == 1:
            attempted.set()
        with transaction(write=write, **kwargs) as conn:
            if turn == 0:
                locked.set()
                assert attempted.wait(5), "second request never reached the write boundary"
            yield conn

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(demo.db, "transaction", gated)
        leading = pool.submit(first)
        assert locked.wait(5)
        trailing = pool.submit(second)
        return leading.result(timeout=10), trailing.result(timeout=10)


def test_SC_S01_link_access_scope_and_redirects(demo, admin):
    unlinked = demo.client("trener")
    assert provision(admin, "desk.reception", "reception").status_code == 201
    for browser, destination, status, error in [
        (demo.client(), "/login", 401, "unauthorized"),
        (demo.client("anna"), "/schedule", 403, "forbidden"),
        (admin, "/staff", 403, "forbidden"),
        (sign_in(demo, "desk.reception"), "/staff", 403, "forbidden"),
        (unlinked, None, 403, "trainer_link_required"),
    ]:
        page = browser.get(PAGE, follow_redirects=False)
        if destination:
            assert page.status_code == 303 and page.headers["location"] == destination
        else:
            assert page.status_code == 200 and 'lang="sk"' in page.text
            assert browser.get("/trainings").status_code == 200
        code(browser.put(f"{PATH}/malformed", content="{", headers={"X-CSRF-Token": "bad"}), status, error)
    trainer = link(demo, admin, 1, "trener")
    snapshot = get_schedule(trainer)
    assert snapshot == get_schedule(trainer)
    assert snapshot["trainer"]["id"] == 1
    assert [training["id_treningu"] for training in snapshot["items"]] == [1, 3, 5]
    assert trainer.get("/trainings").status_code == 200
    assert "reservations" not in snapshot["items"][0] and "moja_rezervacia_id" not in snapshot["items"][0]
    for training_id in (2, 999):
        code(update(trainer, {**snapshot["items"][0], "id_treningu": training_id}), 404, "training_not_found")
    demo.clock.set(demo.now + timedelta(days=2))
    code(trainer.get(PATH), 401, "unauthorized")


def test_SC_S02_publish_edit_and_validation(demo, trainer):
    request = payload(demo, seconds=23)
    training = publish(trainer, request)
    changed = update(trainer, training, room_id=2, activity_id=2, capacity=7,
                     starts_at=stamp(demo.now + timedelta(days=6, hours=2)))
    code(changed, 422, "validation")
    changed = update(trainer, training, room_id=2, activity_id=2, capacity=7,
                     starts_at=stamp(demo.now + timedelta(days=6, hours=2)),
                     ends_at=stamp(demo.now + timedelta(days=6, hours=3)))
    assert changed.status_code == 200, changed.text
    assert changed.json()["version"] == 2 and changed.json()["room_id"] == 2
    assert demo.client("anna").get("/trainings").json()["items"][-1]["kapacita"] == 7
    for malformed in [{"capacity": 0}, {"capacity": 2.5}, {"capacity": True}, {"capacity": "3"},
                      {"trainer_id": 2}, {"starts_at": "2027-02-30T10:00:00Z"},
                      {"activity_id": 2**53}, {"starts_at": request["ends_at"]}]:
        code(trainer.post(PATH, json={**request, **malformed}), 422, "validation")
    for body in (b"{", b'{"x":"\xff"}'):
        headers = {"Content-Type": "application/json"}
        code(trainer.post(PATH, content=body, headers=headers), 422, "validation")
        code(trainer.post(PATH, content=body, headers={**headers, "X-CSRF-Token": "bad"}), 403, "csrf_invalid")
    code(trainer.put(f"{PATH}/99999999999999999999", json={
        **{key: changed.json()[key] for key in ("starts_at", "ends_at", "room_id", "activity_id", "capacity")},
        "expected_version": 1,
    }), 422, "validation")
    code(trainer.post(PATH, json=payload(demo, days=0)), 409, "training_start_not_future")
    code(update(trainer, changed.json(), starts_at=stamp(demo.now)), 409, "training_start_not_future")
    demo.clock.set(instant(changed.json()["starts_at"]))
    trainer = demo.client("trener")
    code(update(trainer, changed.json()), 409, "training_started")


def test_SC_S02_queued_create_crosses_start(demo, trainer, monkeypatch):
    request = payload(demo, days=0, seconds=1)
    transaction = demo.db.transaction

    @contextmanager
    def after_wait(*, write=False):
        with transaction(write=write) as conn:
            if write:
                demo.clock.set(instant(request["starts_at"]))
            yield conn

    monkeypatch.setattr(demo.db, "transaction", after_wait)
    code(trainer.post(PATH, json=request), 409, "training_start_not_future")


def test_SC_S03_allocation_and_legacy_overlap(demo, admin, trainer):
    assert provision(admin, "other.trainer", "trainer").status_code == 201
    other = link(demo, admin, 2, "other.trainer")
    first = publish(trainer, payload(demo))
    publish(trainer, payload(demo, hours=1))
    publish(other, payload(demo, room=2))
    code(trainer.post(PATH, json=payload(demo, room=2)), 409, "trainer_overlap")
    code(other.post(PATH, json=payload(demo, hours=1)), 409, "room_overlap")
    with demo.db.transaction(write=True) as conn:
        conn.execute("UPDATE trainings SET starts_at=?, ends_at=? WHERE id=2", (first["starts_at"], first["ends_at"]))
    assert update(trainer, first, capacity=5).status_code == 200
    updated = next(row for row in get_schedule(trainer)["items"] if row["id_treningu"] == first["id_treningu"])
    assert update(trainer, updated, starts_at=payload(demo, hours=3)["starts_at"],
                  ends_at=payload(demo, hours=3)["ends_at"]).status_code == 200
    demo.clock.set(demo.now + timedelta(days=6, hours=1, minutes=15))
    trainer = demo.client("trener")
    code(trainer.post(PATH, json=payload(demo, hours=1.5)), 409, "trainer_overlap")


def test_SC_S04_history_lock_and_capacity(demo, trainer):
    training = publish(trainer, payload(demo))
    anna, boris = demo.client("anna"), demo.client("boris")
    first = book(anna, training["id_treningu"])
    second = book(boris, training["id_treningu"], user=2)
    assert first.status_code == second.status_code == 201
    code(update(trainer, training, capacity=1), 409, "capacity_below_occupancy")
    code(update(trainer, training, activity_id=2, capacity=1), 409, "training_details_locked")
    updated = update(trainer, training, capacity=2).json()
    assert updated["obsadene"] == 2 and updated["volne_miesta"] == 0 and updated["has_reservation_history"]
    for client, reservation in ((anna, first), (boris, second)):
        assert client.delete(f"/reservations/{reservation.json()['id_rezervacie']}").status_code == 200
    code(update(trainer, updated, room_id=2), 409, "training_details_locked")
    after = update(trainer, updated, capacity=1).json()
    assert after["has_reservation_history"] and after["volne_miesta"] == 1
    assert anna.get("/reservations").json()["items"][0]["stav"] == "cancelled"


@pytest.mark.parametrize("booking_first", [False, True])
@pytest.mark.parametrize("move", [False, True])
def test_SC_S05_booking_contends_with_scheduling(demo, trainer, monkeypatch, booking_first, move):
    training = publish(trainer, payload(demo, capacity=2))
    anna, boris = demo.client("anna"), demo.client("boris")
    if not move:
        assert book(anna, training["id_treningu"]).status_code == 201
    reserve = lambda: book(boris, training["id_treningu"], 2)
    save = lambda: update(trainer, training, **({"room_id": 2} if move else {"capacity": 1}))
    if booking_first:
        booked, edited = race_in_order(demo, monkeypatch, reserve, save)
        assert booked.status_code == 201
        code(edited, 409, "training_details_locked" if move else "capacity_below_occupancy")
    else:
        edited, booked = race_in_order(demo, monkeypatch, save, reserve)
        assert edited.status_code == 200
        if move:
            assert booked.status_code == 201
        else:
            code(booked, 409, "capacity_full")
    view = next(x for x in get_schedule(trainer)["items"] if x["id_treningu"] == training["id_treningu"])
    assert view["obsadene"] <= view["capacity"]
    if move:
        assert boris.get("/reservations").json()["items"][0]["training"]["priestor"] == (
            training["priestor"] if booking_first else edited.json()["priestor"])


def test_SC_S05_cancellation_does_not_unlock_details(demo, trainer, monkeypatch):
    training = publish(trainer, payload(demo, capacity=2))
    anna, boris = demo.client("anna"), demo.client("boris")
    reservation = book(anna, training["id_treningu"]).json()["id_rezervacie"]
    assert book(boris, training["id_treningu"], 2).status_code == 201
    cancelled, reduced = race_in_order(demo, monkeypatch,
        lambda: anna.delete(f"/reservations/{reservation}"), lambda: update(trainer, training, capacity=1))
    assert cancelled.status_code == reduced.status_code == 200
    remaining = boris.get("/reservations").json()["items"][0]["id_rezervacie"]
    refused, last_cancelled = race_in_order(demo, monkeypatch,
        lambda: update(trainer, reduced.json(), room_id=2), lambda: boris.delete(f"/reservations/{remaining}"))
    code(refused, 409, "training_details_locked")
    assert last_cancelled.status_code == 200
    code(update(trainer, reduced.json(), room_id=2), 409, "training_details_locked")


def test_SC_S06_receipts_versions_and_relink(demo, admin, trainer):
    second_session = demo.client("trener")
    data = payload(demo)
    first, second = parallel(lambda: trainer.post(PATH, json=data), lambda: second_session.post(PATH, json=data))
    assert first.status_code == second.status_code == 201 and first.json() == second.json()
    row = first.json()
    assert update(trainer, row).json() == row
    responses = parallel(lambda: update(trainer, row, capacity=4), lambda: update(second_session, row, capacity=5))
    assert sorted(response.status_code for response in responses) == [200, 409]
    code(next(response for response in responses if response.status_code == 409), 409, "training_changed")
    assert publish(trainer, {**data, "starts_at": data["starts_at"].replace(".000000", "")}) == row
    code(trainer.post(PATH, json={**data, "capacity": 9}), 409, "create_request_conflict")
    code(trainer.post(PATH, json={**data, "request_id": str(uuid4())}), 409, "trainer_overlap")
    demo.clock.set(instant(row["starts_at"]))
    trainer = demo.client("trener")
    assert publish(trainer, data) == row
    admin = sign_in(demo, "first.admin")
    row1 = items(admin, "trainers")[0]
    assert change(admin, "trainers", row1, "account", account_id=None).status_code == 200
    trainer = link(demo, admin, 2, "trener")
    assert get_schedule(trainer)["items"] == []
    code(trainer.post(PATH, json=data), 409, "create_request_conflict")


@pytest.mark.parametrize("resource", ["trainer", "room"])
def test_SC_S06_edit_races_create_for_same_allocation(demo, admin, trainer, resource):
    original = publish(trainer, payload(demo))
    competing_trainer = demo.client("trener")
    if resource == "room":
        assert provision(admin, "other.trainer", "trainer").status_code == 201
        competing_trainer = link(demo, admin, 2, "other.trainer")
    allocation = payload(demo, hours=3)
    edited, created = parallel(
        lambda: update(trainer, original, starts_at=allocation["starts_at"], ends_at=allocation["ends_at"]),
        lambda: competing_trainer.post(PATH, json=allocation),
    )
    assert sorted([edited.status_code, created.status_code]) in ([200, 409], [201, 409])
    code(edited if edited.status_code == 409 else created, 409, resource + "_overlap")
    schedule = trainer.get("/trainings").json()["items"]
    assert sum(row["starts_at"] == allocation["starts_at"] for row in schedule) == 1


@pytest.mark.parametrize("kind,field", [("rooms", "room_id"), ("activities", "activity_id")])
@pytest.mark.parametrize("publish_first", [False, True])
def test_SC_S07_catalog_deactivation_race(demo, admin, trainer, monkeypatch, kind, field, publish_first):
    label = "room" if kind == "rooms" else "activity"
    entry = admin.post(f"/api/admin/catalog/{kind}", json={"name": "New option", "request_id": str(uuid4())}).json()
    code(trainer.post(PATH, json={**payload(demo), field: 999}), 404, label + "_not_found")
    data = {**payload(demo), field: entry["id"]}
    create = lambda: trainer.post(PATH, json=data)
    deactivate = lambda: change(admin, kind, entry, "status", status="inactive")
    if publish_first:
        created, blocked = race_in_order(demo, monkeypatch, create, deactivate)
        assert created.status_code == 201
        code(blocked, 409, "future_training_reference")
        assert update(trainer, created.json(), **{field: 1}).status_code == 200
        assert deactivate().status_code == 200
    else:
        deactivated, blocked = race_in_order(demo, monkeypatch, deactivate, create)
        assert deactivated.status_code == 200
        code(blocked, 409, label + "_inactive")
    assert entry["id"] not in [x["id"] for x in get_schedule(trainer)[kind]]


@pytest.mark.parametrize("operation", ["unlink", "record", "status", "role"])
@pytest.mark.parametrize("publish_first", [False, True])
def test_SC_S07_first_assignment_guards(demo, admin, monkeypatch, operation, publish_first):
    assert provision(admin, "new.trainer", "trainer").status_code == 201
    row = admin.post("/api/admin/catalog/trainers", json={"name": "Nový tréner", "request_id": str(uuid4())}).json()
    trainer = link(demo, admin, row["id"], "new.trainer")
    row = items(admin, "trainers")[-1]
    account = find(admin, "new.trainer")
    changes = {
        "unlink": lambda: change(admin, "trainers", row, "account", account_id=None),
        "record": lambda: change(admin, "trainers", row, "status", status="inactive"),
        "status": lambda: edit_account(admin, account, status="disabled"),
        "role": lambda: edit_account(admin, account, role="reception"),
    }
    create = lambda: trainer.post(PATH, json=payload(demo))
    if publish_first:
        created, blocked = race_in_order(demo, monkeypatch, create, changes[operation])
        assert created.status_code == 201
        code(blocked, 409, "future_training_reference" if operation == "record" else "future_training_assignment")
    else:
        changed, blocked = race_in_order(demo, monkeypatch, changes[operation], create)
        assert changed.status_code == 200
        if operation in ("unlink", "record"):
            code(blocked, 403, "trainer_link_required")
        else:
            code(blocked, 401, "unauthorized")


def test_SC_S08_rollback_and_lock_exhaustion(demo, trainer):
    data = payload(demo)
    with demo.db.transaction(write=True) as conn:
        conn.execute("CREATE TRIGGER reject_training_receipt BEFORE INSERT ON training_creates "
                     "BEGIN SELECT RAISE(ABORT, 'private'); END")
    failure = trainer.post(PATH, json=data)
    code(failure, 500, "internal_error")
    assert "private" not in failure.text
    assert [x["id_treningu"] for x in get_schedule(trainer)["items"]] == [1, 3, 5]
    with demo.db.transaction(write=True) as conn:
        assert conn.execute("SELECT count(*) FROM training_creates").fetchone()[0] == 0
        conn.execute("DROP TRIGGER reject_training_receipt")
    demo.db.lock_timeout = 0
    with demo.db.transaction(write=True):
        code(trainer.post(PATH, json=data), 503, "storage_unavailable")
    assert publish(trainer, data)["version"] == 1


def test_SC_S10_upgrade_preserves_links_receipts_on_restart_and_resets(demo, trainer):
    with demo.db.transaction(write=True) as conn:
        remove_inc04_schema(conn)
        conn.execute("UPDATE metadata SET value='0.4.0' WHERE key='schema_version'")
        conn.execute("UPDATE trainings SET starts_at=(SELECT starts_at FROM trainings WHERE id=1), "
                     "ends_at=(SELECT ends_at FROM trainings WHERE id=1) WHERE id=2")
    assert upgrade(demo.path) and not upgrade(demo.path)
    before = get_schedule(trainer)
    assert before["items"][0]["has_reservation_history"] and before["items"][0]["version"] == 1
    request = payload(demo)
    saved = publish(trainer, request)
    assert update(trainer, saved, capacity=4).status_code == 200
    reopened = demo.client("trener", application=create_app(demo.path, demo.clock))
    assert publish(reopened, request) == saved
    assert get_schedule(reopened)["items"][-1]["version"] == 2
    assert not initialize(demo.path, now=demo.now)
    assert initialize(demo.path, reset=True, now=demo.now)
    code(demo.client("trener").get(PATH), 403, "trainer_link_required")


def test_SC_S10_migration_rolls_back_overcapacity(demo):
    with demo.db.transaction(write=True) as conn:
        remove_inc04_schema(conn)
        conn.execute("UPDATE metadata SET value='0.4.0' WHERE key='schema_version'")
        conn.execute("INSERT INTO reservations(user_id, training_id, status, created_at) VALUES (1,3,'confirmed',?)",
                     (stamp(demo.now),))
    with pytest.raises(ValueError, match="occupancy"):
        upgrade(demo.path)
    with demo.db.transaction() as conn:
        assert conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] == "0.4.0"
        assert "version" not in [row["name"] for row in conn.execute("PRAGMA table_info(trainings)")]
        assert SCHEMA_VERSION == "0.5.0"


@pytest.mark.parametrize("schema_version", ["0.4.0", SCHEMA_VERSION])
def test_SC_S10_migration_rejects_unsafe_capacity_without_changing_data(demo, schema_version):
    with demo.db.transaction(write=True) as conn:
        if schema_version == "0.4.0":
            remove_inc04_schema(conn)
            conn.execute("UPDATE metadata SET value=? WHERE key='schema_version'", (schema_version,))
        conn.execute("UPDATE trainings SET capacity=? WHERE id=1", (9_007_199_254_740_992,))
        before = list(conn.iterdump())
    with pytest.raises(ValueError, match=r"Training 1 capacity .*9007199254740991"):
        upgrade(demo.path)
    with demo.db.transaction() as conn:
        assert list(conn.iterdump()) == before


def test_SC_S10_maximum_editor_capacity_survives_upgrade(demo, trainer):
    maximum = 9_007_199_254_740_991
    with demo.db.transaction(write=True) as conn:
        remove_inc04_schema(conn)
        conn.execute("UPDATE metadata SET value='0.4.0' WHERE key='schema_version'")
        conn.execute("UPDATE trainings SET capacity=? WHERE id=1", (maximum,))
    assert upgrade(demo.path) and not upgrade(demo.path)
    row = next(item for item in get_schedule(trainer)["items"] if item["id_treningu"] == 1)
    assert row["capacity"] == maximum
    assert row["volne_miesta"] == maximum - row["obsadene"]
