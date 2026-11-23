"""R-02 booking service. All mutation-dependent checks share the write lock."""
from .auth import authorize
from .db import instant, stamp
from .errors import BusinessError
from .membership import effective_state, get_membership


def check_training(training, now):
    if instant(training["starts_at"]) <= now:
        raise BusinessError(409, "training_started")


def check_membership(membership, now):
    if membership is None or effective_state(membership, now) != "active":
        raise BusinessError(403, "membership_inactive")


def create_reservation(db, cookie, requested_client_id, training_id):
    with db.transaction(write=True) as conn:
        user_id = authorize(conn, cookie, db.clock(), "client")["id"]
        if requested_client_id != user_id:
            raise BusinessError(403, "client_mismatch")
        training = conn.execute("SELECT * FROM trainings WHERE id=?", (training_id,)).fetchone()
        if training is None:
            raise BusinessError(404, "training_not_found")
        check_training(training, db.clock())
        if conn.execute("SELECT 1 FROM reservations WHERE user_id=? AND training_id=? AND status='confirmed'",
                        (user_id, training_id)).fetchone():
            raise BusinessError(409, "duplicate_reservation")
        membership = get_membership(conn, user_id)
        check_membership(membership, db.clock())
        count = conn.execute("SELECT COUNT(*) FROM reservations WHERE training_id=? AND status='confirmed'",
                             (training_id,)).fetchone()[0]
        if count >= training["capacity"]:
            raise BusinessError(409, "capacity_full")
        # Fresh after lock acquisition/retries and reads, immediately before write/commit.
        now = db.clock()
        check_training(training, now)
        check_membership(membership, now)
        cursor = conn.execute("INSERT INTO reservations(user_id,training_id,status,created_at) VALUES (?,?,'confirmed',?)",
                              (user_id, training_id, stamp(now)))
        result = {"id_rezervacie": cursor.lastrowid, "stav": "confirmed"}
    return result


def cancel_reservation(db, cookie, reservation_id):
    with db.transaction(write=True) as conn:
        user_id = authorize(conn, cookie, db.clock(), "client")["id"]
        row = conn.execute("SELECT r.*, t.starts_at FROM reservations r JOIN trainings t ON t.id=r.training_id "
                           "WHERE r.id=? AND r.user_id=?", (reservation_id, user_id)).fetchone()
        if row is None:
            raise BusinessError(404, "reservation_not_found")
        if row["status"] == "cancelled":
            return {"id_rezervacie": reservation_id, "stav": "cancelled"}
        now = db.clock()
        check_training(row, now)
        conn.execute("UPDATE reservations SET status='cancelled',cancelled_at=? WHERE id=? AND user_id=? AND status='confirmed'",
                     (stamp(now), reservation_id, user_id))
    return {"id_rezervacie": reservation_id, "stav": "cancelled"}
