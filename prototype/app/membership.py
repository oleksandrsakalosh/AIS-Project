"""Read-only membership meaning; no activation or payment lifecycle."""
from .db import instant


def effective_state(membership, now):
    if now < instant(membership["valid_from"]):
        return "pending"
    if now >= instant(membership["valid_until"]):
        return "expired"
    return membership["status"]


def get_membership(conn, user_id):
    return conn.execute("SELECT * FROM memberships WHERE user_id=?", (user_id,)).fetchone()


def membership_view(conn, user_id, now):
    row = get_membership(conn, user_id)
    if row is None:
        return None
    return {"id_clenstva": row["id"], "typ": row["kind"], "stav": effective_state(row, now),
            "valid_from": row["valid_from"], "valid_until": row["valid_until"]}
