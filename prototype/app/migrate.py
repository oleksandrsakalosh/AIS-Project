"""Explicit, in-place upgrade for existing local demo databases."""
import argparse
from pathlib import Path

from .db import Database, DEFAULT_DB


SCHEMA_VERSION = "0.2.0"


def upgrade(path=DEFAULT_DB):
    with Database(path).transaction(write=True) as conn:
        metadata = {}
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata'").fetchone():
            metadata = dict(conn.execute("SELECT key,value FROM metadata").fetchall())
        if metadata.get("application") != "POC-BOOKING":
            raise ValueError("Refusing to upgrade a database not owned by this demo")
        version = metadata.get("schema_version")
        if version == SCHEMA_VERSION:
            return False
        if version != "0.1.1":
            raise ValueError(f"Unsupported demo schema version: {version}")
        conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
        conn.execute("UPDATE metadata SET value=? WHERE key='schema_version'", (SCHEMA_VERSION,))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    print("Demo database upgraded." if upgrade(args.db) else "Demo database is already current.")


if __name__ == "__main__":
    main()
