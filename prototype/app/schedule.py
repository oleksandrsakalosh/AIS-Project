"""Schedule projections expose counts and only the signed-in client's booking ID."""
from .db import instant

CATALOG_REFERENCES = {"activities": "activity_id", "trainers": "trainer_id", "rooms": "room_id"}

TRAINING_SELECT = """
SELECT t.id AS id_treningu, a.name AS aktivita, tr.name AS trener, room.name AS priestor,
       t.starts_at, t.ends_at, t.capacity AS kapacita,
       (SELECT COUNT(*) FROM reservations r WHERE r.training_id=t.id AND r.status='confirmed') AS obsadene,
       (SELECT r.id FROM reservations r WHERE r.training_id=t.id AND r.status='confirmed'
          AND r.user_id=?) AS moja_rezervacia_id
FROM trainings t JOIN activities a ON a.id=t.activity_id
JOIN trainers tr ON tr.id=t.trainer_id JOIN rooms room ON room.id=t.room_id
"""


def has_future_training(conn, kind, entry_id, now):
    column = CATALOG_REFERENCES[kind]
    rows = conn.execute(f"SELECT starts_at FROM trainings WHERE {column}=?", (entry_id,))
    return any(instant(row["starts_at"]) > now for row in rows)


def project(row):
    result = dict(row)
    result["volne_miesta"] = result["kapacita"] - result["obsadene"]
    return result


def trainings(conn, user_id):
    return [project(row) for row in conn.execute(TRAINING_SELECT + " ORDER BY t.starts_at,t.id", (user_id,))]


def reservation_history(conn, user_id):
    rows = conn.execute("SELECT * FROM reservations WHERE user_id=? ORDER BY created_at DESC,id DESC", (user_id,)).fetchall()
    schedule = {row["id_treningu"]: row for row in trainings(conn, user_id)}
    return [{"id_rezervacie": row["id"], "id_treningu": row["training_id"], "stav": row["status"],
             "created_at": row["created_at"], "cancelled_at": row["cancelled_at"],
             "training": schedule[row["training_id"]]} for row in rows]
