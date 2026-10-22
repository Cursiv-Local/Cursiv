-- Additive website-only migration. No visitor/event rows or personal identifiers.
CREATE TABLE IF NOT EXISTS download_analytics_cache (
  id TEXT PRIMARY KEY,
  payload TEXT,
  updated_at INTEGER NOT NULL DEFAULT 0,
  retry_at INTEGER NOT NULL DEFAULT 0,
  lease_until INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'empty'
);

CREATE TABLE IF NOT EXISTS download_click_totals (
  button TEXT PRIMARY KEY CHECK (button IN ('windows', 'mac')),
  count INTEGER NOT NULL DEFAULT 0,
  started_day TEXT NOT NULL
);
