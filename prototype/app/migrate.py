"""Explicit, in-place upgrade for existing local demo databases."""
import argparse
from pathlib import Path

from .db import Database, DEFAULT_DB


SCHEMA_VERSION = "0.3.0"


def upgrade(path=DEFAULT_DB):
    with Database(path).transaction(write=True, rebuild_tables=True) as conn:
        metadata = {}
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata'").fetchone():
            metadata = dict(conn.execute("SELECT key,value FROM metadata").fetchall())
        if metadata.get("application") != "POC-BOOKING":
            raise ValueError("Refusing to upgrade a database not owned by this demo")
        version = metadata.get("schema_version")
        if version == SCHEMA_VERSION:
            return False
        if version not in ("0.1.1", "0.2.0"):
            raise ValueError(f"Unsupported demo schema version: {version}")
        if version == "0.1.1":
            conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
        old_sequence = conn.execute("SELECT seq FROM sqlite_sequence WHERE name='users'").fetchone()
        conn.execute("""
            CREATE TABLE users_inc02 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('client','trainer','reception','admin')),
                display_name TEXT,
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
                version INTEGER NOT NULL DEFAULT 1 CHECK (version BETWEEN 1 AND 9007199254740991)
            )
        """)
        conn.execute("""
            INSERT INTO users_inc02 (id,username,password_hash,role,display_name)
            SELECT id,username,password_hash,role,display_name FROM users
        """)
        conn.execute("DROP TABLE users")
        conn.execute("ALTER TABLE users_inc02 RENAME TO users")
        if old_sequence is not None:
            conn.execute("DELETE FROM sqlite_sequence WHERE name='users'")
            conn.execute("INSERT INTO sqlite_sequence(name,seq) VALUES ('users',?)", (old_sequence["seq"],))
        conn.execute("UPDATE metadata SET value=? WHERE key='schema_version'", (SCHEMA_VERSION,))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    print("Demo database upgraded." if upgrade(args.db) else "Demo database is already current.")


if __name__ == "__main__":
    main()
