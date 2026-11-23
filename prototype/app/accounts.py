"""Client registration and own-profile persistence."""
from .auth import hash_password
from .errors import BusinessError


def register(db, username, password, display_name):
    password_hash = hash_password(password)
    with db.transaction(write=True) as conn:
        # Legacy usernames keep their original spelling. Check new ones under the write lock.
        if conn.execute("SELECT 1 FROM users WHERE username COLLATE NOCASE = ?", (username,)).fetchone():
            raise BusinessError(409, "username_taken")
        conn.execute(
            "INSERT INTO users(username,password_hash,role,display_name) VALUES (?,?,'client',?)",
            (username, password_hash, display_name),
        )


def profile(db, user):
    with db.transaction() as conn:
        display_name = conn.execute("SELECT display_name FROM users WHERE id=?", (user["id"],)).fetchone()[0]
    return {**user, "display_name": display_name or user["username"]}


def update_display_name(db, user, display_name):
    with db.transaction(write=True) as conn:
        conn.execute("UPDATE users SET display_name=? WHERE id=?", (display_name, user["id"]))
    return {**user, "display_name": display_name}
