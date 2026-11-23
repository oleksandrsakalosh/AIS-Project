"""Client and staff account persistence."""
from .auth import authorize, hash_password
from .db import instant
from .errors import BusinessError


def insert_account(conn, username, password_hash, display_name, role):
    if conn.execute("SELECT 1 FROM users WHERE username COLLATE NOCASE = ?", (username,)).fetchone():
        raise BusinessError(409, "username_taken")
    cursor = conn.execute(
        "INSERT INTO users(username,password_hash,role,display_name) VALUES (?,?,?,?)",
        (username, password_hash, role, display_name),
    )
    return account_view(conn.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone())


def register(db, username, password, display_name):
    encoded = hash_password(password)
    with db.transaction(write=True) as conn:
        insert_account(conn, username, encoded, display_name, "client")


def profile(db, cookie):
    with db.transaction() as conn:
        user = authorize(conn, cookie, db.clock(), "client")
        display_name = conn.execute("SELECT display_name FROM users WHERE id=?", (user["id"],)).fetchone()[0]
    return {**user, "display_name": display_name or user["username"]}


def update_display_name(db, cookie, display_name):
    with db.transaction(write=True) as conn:
        user = authorize(conn, cookie, db.clock(), "client")
        conn.execute("UPDATE users SET display_name=? WHERE id=?", (display_name, user["id"]))
    return {**user, "display_name": display_name}


def account_view(row):
    view = {key: row[key] for key in ("id", "username", "display_name", "role", "status", "version")}
    view["display_name"] = view["display_name"] or view["username"]
    return view


def list_accounts(db, cookie):
    with db.transaction() as conn:
        authorize(conn, cookie, db.clock(), "admin")
        return [account_view(row) for row in conn.execute("SELECT * FROM users ORDER BY id")]


def provision_staff(db, cookie, data):
    encoded = hash_password(data.password)
    with db.transaction(write=True) as conn:
        authorize(conn, cookie, db.clock(), "admin")
        return insert_account(conn, data.username, encoded, data.display_name, data.role)


def change_account(db, cookie, account_id, expected_version, *, status=None, role=None):
    with db.transaction(write=True) as conn:
        authorize(conn, cookie, db.clock(), "admin")
        row = conn.execute("SELECT * FROM users WHERE id=?", (account_id,)).fetchone()
        if row is None:
            raise BusinessError(404, "account_not_found")
        if row["version"] != expected_version:
            raise BusinessError(409, "account_changed")
        if role is not None and row["role"] == "client":
            raise BusinessError(409, "client_role_fixed")
        new_status = status or row["status"]
        new_role = role or row["role"]
        disabling = row["status"] == "active" and new_status == "disabled"
        role_changed = new_role != row["role"]
        if not role_changed and new_status == row["status"]:
            return account_view(row)
        if row["role"] == "admin" and row["status"] == "active" and (disabling or role_changed):
            other_admin = conn.execute(
                "SELECT 1 FROM users WHERE role='admin' AND status='active' AND id<>? LIMIT 1", (account_id,)
            ).fetchone()
            if other_admin is None:
                raise BusinessError(409, "last_active_admin")
        if disabling and row["role"] == "client":
            starts = conn.execute(
                "SELECT t.starts_at FROM reservations r JOIN trainings t ON t.id=r.training_id "
                "WHERE r.user_id=? AND r.status='confirmed'", (account_id,)
            ).fetchall()
            now = db.clock()
            if any(instant(training["starts_at"]) > now for training in starts):
                raise BusinessError(409, "future_reservation")

        # INC-03 adds explicit trainer links and the corresponding future assignment guard.
        conn.execute("UPDATE users SET status=?,role=?,version=version+1 WHERE id=?",
                     (new_status, new_role, account_id))
        if disabling or role_changed:
            conn.execute("DELETE FROM sessions WHERE user_id=?", (account_id,))
        return account_view(conn.execute("SELECT * FROM users WHERE id=?", (account_id,)).fetchone())
