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


def current_session(db, cookie):
    if not cookie or len(cookie) > 128:
        return None
    with db.transaction() as conn:
        row = conn.execute(
            "SELECT s.*, u.id AS uid, u.username, u.role FROM sessions s "
            "LEFT JOIN users u ON u.id=s.user_id WHERE s.token_hash=?", (digest(cookie),)
        ).fetchone()
        if row is None or instant(row["expires_at"]) <= db.clock():
            return None
        return dict(row)


def user_summary(session):
    if session is None or session["uid"] is None:
        return None
    return {"id": session["uid"], "username": session["username"], "role": session["role"]}


def create_session(db, response, user_id=None, replace=None):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with db.transaction(write=True) as conn:
        now = db.clock()
        conn.execute("DELETE FROM sessions WHERE expires_at<=?", (stamp(now),))
        if replace:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (replace,))
        conn.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", (
            digest(token), user_id, digest(csrf), csrf, stamp(now + timedelta(seconds=SESSION_SECONDS))
        ))
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict", secure=False, path="/")
    return csrf


def valid_csrf(session, token):
    return bool(session and token and len(token) <= 128 and hmac.compare_digest(session["csrf_hash"], digest(token)))


def authenticate(db, username, password):
    with db.transaction() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    valid = verify_password(password, user["password_hash"] if user else DUMMY_HASH)
    if user is None or not valid:
        raise BusinessError(401, "invalid_credentials")
    return {"id": user["id"], "username": user["username"], "role": user["role"]}
