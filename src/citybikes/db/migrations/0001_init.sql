PRAGMA user_version=1;

CREATE TABLE IF NOT EXISTS networks (
    tag TEXT PRIMARY KEY,
    name TEXT,
    latitude REAL,
    longitude REAL,
    meta BLOB,
    stations BLOB DEFAULT '[]',
    created DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated DATETIME DEFAULT CURRENT_TIMESTAMP
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS stations (
    hash TEXT PRIMARY KEY,
    name TEXT,
    latitude REAL,
    longitude REAL,
    stat BLOB,
    network_tag TEXT
) WITHOUT ROWID;

CREATE TRIGGER IF NOT EXISTS update_network AFTER UPDATE ON networks
BEGIN
    UPDATE networks
    SET updated = CURRENT_TIMESTAMP
    WHERE tag = OLD.tag
    ;
END;
