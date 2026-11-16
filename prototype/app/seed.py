"""Explicit CLI initialization/reset; never invoked automatically by the server."""
import argparse
from datetime import timedelta
from pathlib import Path
import sqlite3

from .auth import hash_password
from .db import DEFAULT_DB, utc_now, stamp


def initialize(path=DEFAULT_DB, *, reset=False, now=None):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = now or utc_now()
    connection = sqlite3.connect(path)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables and not reset:
            return False
        if reset and tables:
            # Refuse destructive reset of anything except our recognizable demo database.
            if "metadata" not in tables or connection.execute("SELECT value FROM metadata WHERE key='application'").fetchone() != ("POC-BOOKING",):
                raise ValueError("Refusing to reset a database not owned by this demo")
            connection.execute("PRAGMA foreign_keys=OFF")
            for table in ("sessions", "reservations", "trainings", "memberships", "users", "activities", "trainers", "rooms", "metadata"):
                connection.execute(f'DROP TABLE IF EXISTS "{table}"')  # fixed internal names only
            connection.commit()
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript((Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8"))
        connection.execute("INSERT INTO metadata VALUES ('application','POC-BOOKING')")
        connection.execute("INSERT INTO metadata VALUES ('seeded_at',?)", (stamp(now),))
        connection.execute("INSERT INTO metadata VALUES ('schema_version','0.1.1')")
        password_hash = hash_password("Demo123!")
        connection.executemany("INSERT INTO users(id,username,password_hash,role) VALUES (?,?,?,?)", [
            (1, "anna", password_hash, "client"), (2, "boris", password_hash, "client"),
            (3, "cyril", password_hash, "client"), (4, "dana", password_hash, "client"),
            (5, "trener", password_hash, "trainer")])
        for user_id, status, start, end in [(1,"active",-7,30),(2,"active",-7,30),(3,"expired",-30,-1),(4,"pending",-1,30)]:
            connection.execute("INSERT INTO memberships(user_id,kind,status,valid_from,valid_until) VALUES (?,'Mesačné členstvo',?,?,?)",
                               (user_id, status, stamp(now+timedelta(days=start)), stamp(now+timedelta(days=end))))
        connection.executemany("INSERT INTO activities VALUES (?,?)", [(1,"Funkčný tréning"),(2,"Joga a mobilita"),(3,"Kruhový tréning"),(4,"Ranný strečing"),(5,"Zdravý chrbát")])
        connection.executemany("INSERT INTO trainers VALUES (?,?)", [(1,"Marek Novák"),(2,"Lucia Kováčová")])
        connection.executemany("INSERT INTO rooms VALUES (?,?)", [(1,"Sála A"),(2,"Štúdio B")])
        for tid, days, capacity in [(1,1,3),(2,2,1),(3,3,1),(4,-1,8),(5,4,2)]:
            start = now + timedelta(days=days)
            connection.execute("INSERT INTO trainings VALUES (?,?,?,?,?,?,?)", (tid,tid,1 if tid%2 else 2,1 if tid%2 else 2,stamp(start),stamp(start+timedelta(hours=1)),capacity))
        for user_id, training_id, created in [(2,1,now-timedelta(hours=2)),(2,3,now-timedelta(hours=2)),(3,5,now-timedelta(days=2))]:
            connection.execute("INSERT INTO reservations(user_id,training_id,status,created_at) VALUES (?,?,'confirmed',?)", (user_id,training_id,stamp(created)))
        connection.commit()
        return True
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description="Initialize the fictional local booking demo. Stop the server before reset.")
    parser.add_argument("--reset-demo", action="store_true", help="Explicitly recreate this demo database's fixtures")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Database path (default: prototype/runtime/booking.sqlite3)")
    args = parser.parse_args()
    changed = initialize(args.db, reset=args.reset_demo)
    print("Demo initialized: " + str(args.db.resolve()) if changed else "Existing database preserved; initialization made no changes.")


if __name__ == "__main__":
    main()
