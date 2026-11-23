"""Create the first administrator for an initialized local demo database."""

import argparse
from getpass import GetPassWarning, getpass
from pathlib import Path
import sqlite3
import sys
import warnings

from pydantic import ValidationError

from .accounts import insert_account
from .auth import hash_password
from .db import Database, DEFAULT_DB
from .errors import BusinessError
from .migrate import SCHEMA_VERSION
from .models import RegistrationInput


def bootstrap(path, data):
    encoded = hash_password(data.password)
    with Database(path).transaction(write=True) as conn:
        metadata = {}
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata'").fetchone():
            metadata = dict(conn.execute("SELECT key,value FROM metadata").fetchall())
        if metadata.get("application") != "POC-BOOKING" or metadata.get("schema_version") != SCHEMA_VERSION:
            raise BusinessError(409, "unsupported_database")
        if conn.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1").fetchone():
            raise BusinessError(409, "administrator_exists")
        return insert_account(conn, data.username, encoded, data.display_name, "admin")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    path = parser.parse_args().db
    if not path.is_file():
        print("Initialize the local database before bootstrapping an administrator.", file=sys.stderr)
        return 1
    try:
        username = input("Administrator username: ")
        display_name = input("Display name: ")
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            password = getpass("Password: ")
        data = RegistrationInput(username=username, display_name=display_name, password=password)
        account = bootstrap(path, data)
    except (EOFError, KeyboardInterrupt, GetPassWarning):
        print("Bootstrap cancelled. Use an interactive terminal with hidden password input.", file=sys.stderr)
    except ValidationError:
        print("Invalid username, display name or password. Check the documented field rules.", file=sys.stderr)
    except BusinessError as exc:
        messages = {
            "unsupported_database": "Select an initialized local demo database at the current schema version.",
            "administrator_exists": "An administrator account already exists.",
            "username_taken": "That username is already in use.",
        }
        print(messages[exc.code], file=sys.stderr)
    except sqlite3.DatabaseError:
        print("The local database is unavailable or could not be updated.", file=sys.stderr)
    else:
        print(f"Administrator created: {account['username']}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
