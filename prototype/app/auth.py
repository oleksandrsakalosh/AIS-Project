"""Opaque, database-backed sessions; browser identity/roles are never trusted."""
from datetime import timedelta
import hashlib
import hmac
import secrets

from .db import stamp, instant
from .errors import BusinessError

COOKIE = "poc_session"
SESSION_SECONDS = 24 * 60 * 60


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password):
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return "scrypt$" + salt.hex() + "$" + key.hex()


def verify_password(password, encoded):
    _, salt, expected = encoded.split("$")
    key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return hmac.compare_digest(key.hex(), expected)


# Same password work for unknown users, without logging or storing the raw password.
DUMMY_HASH = hash_password(secrets.token_urlsafe(24))


def session_context(conn, cookie, now):
    if not cookie or len(cookie) > 128:
        return None
    row = conn.execute(
        "SELECT s.*, u.id AS uid, u.username, u.role FROM sessions s "
        "LEFT JOIN users u ON u.id=s.user_id WHERE s.token_hash=? "
        "AND (s.user_id IS NULL OR u.status='active')", (digest(cookie),)
    ).fetchone()
    return row if row is not None and instant(row["expires_at"]) > now else None


def current_session(db, cookie):
    with db.transaction() as conn:
        return session_context(conn, cookie, db.clock())


def user_summary(session):
    if session is None or session["uid"] is None:
        return None
    return {"id": session["uid"], "username": session["username"], "role": session["role"]}


def require_access(session, role=None):
    user = user_summary(session)
    if user is None:
        raise BusinessError(401, "unauthorized")
    if role is not None and user["role"] != role:
        raise BusinessError(403, "forbidden")
    return user


def authorize(conn, cookie, now, role=None):
    return require_access(session_context(conn, cookie, now), role)


def start_session(conn, now, user_id=None, replace=None):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    conn.execute("DELETE FROM sessions WHERE expires_at<=?", (stamp(now),))
    if replace:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (replace,))
    conn.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", (
        digest(token), user_id, digest(csrf), csrf, stamp(now + timedelta(seconds=SESSION_SECONDS))
    ))
    return token, csrf


def set_session_cookie(response, token):
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict", secure=False, path="/")


def valid_csrf(session, token):
    return bool(session and token and len(token) <= 128 and hmac.compare_digest(session["csrf_hash"], digest(token)))


def require_csrf(session, token):
    if not valid_csrf(session, token):
        raise BusinessError(403, "csrf_invalid")


def login(db, cookie, csrf, username, password):
    with db.transaction() as conn:
        original = conn.execute("SELECT password_hash FROM users WHERE username=?", (username,)).fetchone()
    password_hash = original["password_hash"] if original else DUMMY_HASH
    valid = verify_password(password, password_hash)
    with db.transaction(write=True) as conn:
        now = db.clock()
        context = session_context(conn, cookie, now)
        require_csrf(context, csrf)
        user = conn.execute(
            "SELECT id, username, role, password_hash FROM users WHERE username=? AND status='active'",
            (username,),
        ).fetchone()
        if not valid or original is None or user is None or user["password_hash"] != password_hash:
            raise BusinessError(401, "invalid_credentials")
        token, csrf = start_session(conn, now, user["id"], context["token_hash"])
        summary = {key: user[key] for key in ("id", "username", "role")}
    return summary, token, csrf
