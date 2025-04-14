PRAGMA user_version=3;

-- add column of entity ids
ALTER TABLE networks ADD COLUMN vehicles BLOB DEFAULT '[]';
-- add entity table
CREATE TABLE IF NOT EXISTS vehicles (
    hash TEXT PRIMARY KEY,
    latitude REAL,
    longitude REAL,
    kind TEXT,
    stat BLOB,
    network_tag TEXT
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS idx_network_tag ON vehicles(network_tag);
