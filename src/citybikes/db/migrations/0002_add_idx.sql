PRAGMA user_version=2;

-- index station network_tag
CREATE INDEX IF NOT EXISTS idx_network_tag ON stations(network_tag);
