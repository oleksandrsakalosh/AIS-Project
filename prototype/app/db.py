"""SQLite storage boundaries. Application services share one transaction."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import time

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "runtime" / "booking.sqlite3"


def utc_now():
    return datetime.now(timezone.utc)


def stamp(value):
    if value.tzinfo is None:
        raise ValueError("An aware UTC clock is required")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Database:
    def __init__(self, path=DEFAULT_DB, clock=utc_now, lock_timeout=5.0):
        self.path = Path(path).resolve()
        self.clock = clock
        self.lock_timeout = lock_timeout

    def connect(self):
        # mode=rw prevents an accidental empty database after a path/configuration error.
        connection = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=0.05)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @contextmanager
    def transaction(self, write=False, *, rebuild_tables=False):
        connection = self.connect()
        try:
            if rebuild_tables:
                # SQLite requires this before BEGIN. Check every reference before commit.
                connection.execute("PRAGMA foreign_keys=OFF")
            deadline = time.monotonic() + self.lock_timeout
            while True:
                try:
                    connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                    break
                except sqlite3.OperationalError as exc:
                    if getattr(exc, "sqlite_errorcode", None) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                        raise
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.01)
            yield connection
            if rebuild_tables and connection.execute("PRAGMA foreign_key_check").fetchone():
                raise sqlite3.IntegrityError("Foreign key check failed during migration")
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
