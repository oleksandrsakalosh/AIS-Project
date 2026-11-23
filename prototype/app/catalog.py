"""Administrator catalog commands and the trainer-account association."""
from unicodedata import normalize

from .auth import authorize
from .errors import BusinessError
from .models import normalize_catalog_name
from .schedule import CATALOG_REFERENCES, has_future_training


def table_name(kind):
    # Only these application-owned identifiers may enter a SQL statement.
    if kind not in CATALOG_REFERENCES:
        raise BusinessError(422, "validation")
    return kind


def list_entries(db, cookie, kind):
    table = table_name(kind)
    with db.transaction() as conn:
        authorize(conn, cookie, db.clock(), "admin")
        return [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY id")]


def name_key(name):
    return normalize("NFC", normalize_catalog_name(name).casefold())


def require_available_name(conn, table, name, excluding_id=None):
    if table == "trainers":
        return
    key = name_key(name)
    for row in conn.execute(f"SELECT id,name FROM {table}"):
        if row["id"] != excluding_id and name_key(row["name"]) == key:
            raise BusinessError(409, "catalog_name_taken")


def create_entry(db, cookie, kind, data):
    table = table_name(kind)
    with db.transaction(write=True) as conn:
        actor = authorize(conn, cookie, db.clock(), "admin")
        scope = (actor["id"], kind, data.request_id)
        receipt = conn.execute(
            "SELECT entry_id,name FROM catalog_creates WHERE admin_account_id=? AND kind=? AND request_id=?",
            scope,
        ).fetchone()
        if receipt is not None:
            if receipt["name"] != data.name:
                raise BusinessError(409, "create_request_conflict")
            entry_id = receipt["entry_id"]
        else:
            require_available_name(conn, table, data.name)
            entry_id = conn.execute(f"INSERT INTO {table}(name) VALUES (?)", (data.name,)).lastrowid
            conn.execute(
                "INSERT INTO catalog_creates(admin_account_id,kind,request_id,entry_id,name) VALUES (?,?,?,?,?)",
                (*scope, entry_id, data.name),
            )
        entry = {"id": entry_id, "name": data.name, "status": "active", "version": 1}
        if kind == "trainers":
            entry["account_id"] = None
        return entry


def current_entry(conn, table, entry_id, version):
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (entry_id,)).fetchone()
    if row is None:
        raise BusinessError(404, "catalog_entry_not_found")
    if row["version"] != version:
        raise BusinessError(409, "catalog_entry_changed")
    return dict(row)


def rename_entry(db, cookie, kind, entry_id, data):
    table = table_name(kind)
    with db.transaction(write=True) as conn:
        authorize(conn, cookie, db.clock(), "admin")
        entry = current_entry(conn, table, entry_id, data.expected_version)
        if normalize_catalog_name(entry["name"]) == data.name:
            return entry
        require_available_name(conn, table, data.name, excluding_id=entry_id)
        conn.execute(f"UPDATE {table} SET name=?,version=version+1 WHERE id=?", (data.name, entry_id))
        return {**entry, "name": data.name, "version": entry["version"] + 1}


def deactivate_entry(db, cookie, kind, entry_id, data):
    table = table_name(kind)
    with db.transaction(write=True) as conn:
        authorize(conn, cookie, db.clock(), "admin")
        entry = current_entry(conn, table, entry_id, data.expected_version)
        if entry["status"] == "inactive":
            return entry
        if has_future_training(conn, kind, entry_id, db.clock()):
            raise BusinessError(409, "future_training_reference")
        conn.execute(f"UPDATE {table} SET status='inactive',version=version+1 WHERE id=?", (entry_id,))
        return {**entry, "status": "inactive", "version": entry["version"] + 1}


def require_linkable_account(conn, account_id):
    account = conn.execute("SELECT role,status FROM users WHERE id=?", (account_id,)).fetchone()
    if account is None:
        raise BusinessError(404, "account_not_found")
    if account["role"] != "trainer" or account["status"] != "active":
        raise BusinessError(409, "trainer_account_ineligible")
    if conn.execute("SELECT 1 FROM trainers WHERE account_id=?", (account_id,)).fetchone():
        raise BusinessError(409, "trainer_account_already_linked")


def change_trainer_link(db, cookie, entry_id, data):
    with db.transaction(write=True) as conn:
        authorize(conn, cookie, db.clock(), "admin")
        entry = current_entry(conn, "trainers", entry_id, data.expected_version)
        account_id = data.account_id
        if entry["account_id"] == account_id:
            return entry
        if account_id is not None and entry["status"] == "inactive":
            raise BusinessError(409, "catalog_entry_inactive")
        if entry["account_id"] is not None and has_future_training(conn, "trainers", entry_id, db.clock()):
            raise BusinessError(409, "future_training_assignment")
        if account_id is not None:
            require_linkable_account(conn, account_id)
        conn.execute("UPDATE trainers SET account_id=?,version=version+1 WHERE id=?", (account_id, entry_id))
        return {**entry, "account_id": account_id, "version": entry["version"] + 1}
