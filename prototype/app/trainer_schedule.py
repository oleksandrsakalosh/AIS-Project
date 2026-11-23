"""Trainer-owned scheduling commands on the shared booking transaction."""
import json

from . import auth
from .db import instant
from .errors import BusinessError


EDITOR_SELECT = """
SELECT t.id AS id_treningu, t.trainer_id, tr.name AS trener, t.activity_id,
       a.name AS aktivita, t.room_id, room.name AS priestor, t.starts_at, t.ends_at,
       t.capacity, t.version,
       (SELECT COUNT(*) FROM reservations r WHERE r.training_id=t.id AND r.status='confirmed') AS obsadene,
       EXISTS(SELECT 1 FROM reservations r WHERE r.training_id=t.id) AS has_reservation_history
FROM trainings t JOIN trainers tr ON tr.id=t.trainer_id
JOIN activities a ON a.id=t.activity_id JOIN rooms room ON room.id=t.room_id
"""


def access(conn, cookie, now):
    context = auth.session_context(conn, cookie, now)
    user = auth.require_access(context, "trainer")
    trainer = conn.execute("SELECT id,name FROM trainers WHERE account_id=? AND status='active'",
                           (user["id"],)).fetchone()
    if trainer is None:
        raise BusinessError(403, "trainer_link_required")
    return context, user, trainer


def item(row):
    result = dict(row)
    result["has_reservation_history"] = bool(result["has_reservation_history"])
    result["volne_miesta"] = result["capacity"] - result["obsadene"]
    return result


def editor_row(conn, training_id, trainer_id):
    row = conn.execute(EDITOR_SELECT + " WHERE t.id=? AND t.trainer_id=?", (training_id, trainer_id)).fetchone()
    if row is None:
        raise BusinessError(404, "training_not_found")
    return row


def snapshot(db, cookie):
    with db.transaction() as conn:
        now = db.clock()
        _, _, trainer = access(conn, cookie, now)
        rows = conn.execute(EDITOR_SELECT + " WHERE t.trainer_id=?", (trainer["id"],))
        future = [item(row) for row in rows if instant(row["starts_at"]) > now]
        future.sort(key=lambda row: (instant(row["starts_at"]), row["id_treningu"]))
        return {
            "trainer": dict(trainer),
            "activities": [dict(row) for row in conn.execute(
                "SELECT id,name FROM activities WHERE status='active' ORDER BY id")],
            "rooms": [dict(row) for row in conn.execute(
                "SELECT id,name FROM rooms WHERE status='active' ORDER BY id")],
            "items": future,
        }


def require_future(starts_at, now, code="training_start_not_future"):
    if instant(starts_at) <= now:
        raise BusinessError(409, code)


def require_catalog_choices(conn, data):
    for table, label, entry_id in (("activities", "activity", data.activity_id), ("rooms", "room", data.room_id)):
        entry = conn.execute(f"SELECT status FROM {table} WHERE id=?", (entry_id,)).fetchone()
        if entry is None:
            raise BusinessError(404, label + "_not_found")
        if entry["status"] != "active":
            raise BusinessError(409, label + "_inactive")


def require_allocation(conn, trainer_id, data, existing_id=0):
    start, end = instant(data.starts_at), instant(data.ends_at)
    rows = conn.execute(
        "SELECT trainer_id, room_id, starts_at, ends_at FROM trainings "
        "WHERE id!=? AND (trainer_id=? OR room_id=?)", (existing_id, trainer_id, data.room_id))
    room_overlap = False
    for row in rows:
        if start < instant(row["ends_at"]) and instant(row["starts_at"]) < end:
            if row["trainer_id"] == trainer_id:
                raise BusinessError(409, "trainer_overlap")
            room_overlap = True
    if room_overlap:
        raise BusinessError(409, "room_overlap")


def create(db, cookie, csrf, data):
    with db.transaction(write=True) as conn:
        now = db.clock()
        context, actor, trainer = access(conn, cookie, now)
        auth.require_csrf(context, csrf)
        scope = (actor["id"], data.request_id)
        fields = json.dumps(data.model_dump(exclude={"request_id"}), sort_keys=True)
        receipt = conn.execute("SELECT trainer_id,fields,response FROM training_creates "
                               "WHERE account_id=? AND request_id=?", scope).fetchone()
        if receipt:
            if receipt["trainer_id"] != trainer["id"] or receipt["fields"] != fields:
                raise BusinessError(409, "create_request_conflict")
            return json.loads(receipt["response"])
        require_future(data.starts_at, now)
        require_catalog_choices(conn, data)
        require_allocation(conn, trainer["id"], data)
        require_future(data.starts_at, db.clock())
        training_id = conn.execute(
            "INSERT INTO trainings(activity_id,trainer_id,room_id,starts_at,ends_at,capacity) VALUES (?,?,?,?,?,?)",
            (data.activity_id, trainer["id"], data.room_id, data.starts_at, data.ends_at, data.capacity)
        ).lastrowid
        response = item(editor_row(conn, training_id, trainer["id"]))
        conn.execute("INSERT INTO training_creates(account_id,request_id,trainer_id,training_id,fields,response) "
                     "VALUES (?,?,?,?,?,?)", (*scope, trainer["id"], training_id, fields, json.dumps(response)))
        return response


def edit(db, cookie, csrf, training_id, data):
    with db.transaction(write=True) as conn:
        now = db.clock()
        context, _, trainer = access(conn, cookie, now)
        auth.require_csrf(context, csrf)
        current = editor_row(conn, training_id, trainer["id"])
        if current["version"] != data.expected_version:
            raise BusinessError(409, "training_changed")
        require_future(current["starts_at"], now, "training_started")
        interval_changed = (instant(current["starts_at"]) != instant(data.starts_at)
                            or instant(current["ends_at"]) != instant(data.ends_at))
        moved = interval_changed or current["room_id"] != data.room_id
        details_changed = moved or current["activity_id"] != data.activity_id
        if details_changed and current["has_reservation_history"]:
            raise BusinessError(409, "training_details_locked")
        require_future(data.starts_at, now)
        require_catalog_choices(conn, data)
        if data.capacity < current["obsadene"]:
            raise BusinessError(409, "capacity_below_occupancy")
        if moved:
            require_allocation(conn, trainer["id"], data, existing_id=training_id)
        now = db.clock()
        require_future(current["starts_at"], now, "training_started")
        require_future(data.starts_at, now)
        if not details_changed and current["capacity"] == data.capacity:
            return item(current)
        conn.execute("UPDATE trainings SET activity_id=?,room_id=?,starts_at=?,ends_at=?,capacity=?,version=version+1 "
                     "WHERE id=?", (data.activity_id, data.room_id,
                                    data.starts_at if interval_changed else current["starts_at"],
                                    data.ends_at if interval_changed else current["ends_at"],
                                    data.capacity, training_id))
        return item(editor_row(conn, training_id, trainer["id"]))
