PRAGMA foreign_keys=ON;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('client','trainer','reception','admin')),
    display_name TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version BETWEEN 1 AND 9007199254740991)
);
CREATE TABLE memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
    kind TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','pending','expired')),
    valid_from TEXT NOT NULL,
    valid_until TEXT NOT NULL CHECK (valid_until > valid_from)
);
CREATE TABLE activities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version BETWEEN 1 AND 9007199254740991)
);
CREATE TABLE trainers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version BETWEEN 1 AND 9007199254740991),
    account_id INTEGER REFERENCES users(id)
);
CREATE UNIQUE INDEX one_trainer_per_account ON trainers(account_id) WHERE account_id IS NOT NULL;
CREATE TABLE rooms (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
    version INTEGER NOT NULL DEFAULT 1 CHECK (version BETWEEN 1 AND 9007199254740991)
);
CREATE TABLE catalog_creates (
    admin_account_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL CHECK (kind IN ('trainers','activities','rooms')),
    request_id TEXT NOT NULL,
    entry_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    PRIMARY KEY (admin_account_id, kind, request_id)
);
CREATE TABLE trainings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL REFERENCES activities(id),
    trainer_id INTEGER NOT NULL REFERENCES trainers(id),
    room_id INTEGER NOT NULL REFERENCES rooms(id),
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL CHECK (ends_at > starts_at),
    capacity INTEGER NOT NULL CHECK (capacity > 0)
);
CREATE TABLE reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    training_id INTEGER NOT NULL REFERENCES trainings(id),
    status TEXT NOT NULL CHECK (status IN ('confirmed','cancelled')),
    created_at TEXT NOT NULL,
    cancelled_at TEXT,
    CHECK ((status='confirmed' AND cancelled_at IS NULL) OR (status='cancelled' AND cancelled_at IS NOT NULL))
);
CREATE UNIQUE INDEX one_confirmed_booking ON reservations(user_id,training_id) WHERE status='confirmed';
CREATE INDEX confirmed_occupancy ON reservations(training_id,status);
CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    csrf_hash TEXT NOT NULL,
    csrf_token TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
