-- Cursiv web database (Cloudflare D1).
-- Same five tables as cursiv_engine/web/db.py, plus demo_sessions for the demo chat's
-- rate limit (the Python server kept that in memory, which reset on every restart).
--   Local:  npx wrangler d1 execute cursiv --local  --file schema.sql
--   Live:   npx wrangler d1 execute cursiv --remote --file schema.sql

CREATE TABLE IF NOT EXISTS users (
  id        TEXT PRIMARY KEY,
  username  TEXT UNIQUE NOT NULL,
  pw_hash   TEXT NOT NULL,
  created   TEXT NOT NULL,
  device_id TEXT
);
CREATE INDEX IF NOT EXISTS users_device ON users (device_id);

CREATE TABLE IF NOT EXISTS posts (
  id        TEXT PRIMARY KEY,
  user_id   TEXT NOT NULL,
  username  TEXT NOT NULL,
  text      TEXT NOT NULL,
  source    TEXT NOT NULL DEFAULT 'broadcast',
  timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS posts_time ON posts (timestamp);
CREATE INDEX IF NOT EXISTS posts_user_time ON posts (user_id, timestamp);

CREATE TABLE IF NOT EXISTS fleet_nodes (
  machine_id   TEXT PRIMARY KEY,
  machine_name TEXT NOT NULL,
  username     TEXT NOT NULL,
  version      TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'idle',
  ip_hint      TEXT,
  last_seen    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fleet_tokens (
  id          TEXT PRIMARY KEY,
  token_hash  TEXT NOT NULL UNIQUE,
  label       TEXT NOT NULL,
  added_by    TEXT NOT NULL,
  added_at    TEXT NOT NULL,
  active      INTEGER NOT NULL DEFAULT 1
);

-- salt = AES-GCM IV, hmac_tag = "aes-gcm-v2" (GCM carries its own tag inside the ciphertext).
CREATE TABLE IF NOT EXISTS sealed_letters (
  id            TEXT PRIMARY KEY,
  from_user_id  TEXT NOT NULL,
  from_username TEXT NOT NULL,
  to_username   TEXT NOT NULL,
  salt          TEXT NOT NULL,
  ciphertext    TEXT NOT NULL,
  hmac_tag      TEXT NOT NULL,
  created       TEXT NOT NULL,
  read_at       TEXT
);
CREATE INDEX IF NOT EXISTS letters_to ON sealed_letters (to_username, created);
CREATE INDEX IF NOT EXISTS letters_from ON sealed_letters (from_user_id, created);

-- One row per visitor IP: demo message count for the current hour + Guardian score.
CREATE TABLE IF NOT EXISTS demo_sessions (
  ip           TEXT PRIMARY KEY,
  count        INTEGER NOT NULL DEFAULT 0,
  window_start INTEGER NOT NULL,
  guard_score  REAL NOT NULL DEFAULT 0
);

-- One row per UTC day: total demo replies, so the free AI tier can't be drained.
CREATE TABLE IF NOT EXISTS demo_daily (
  day   TEXT PRIMARY KEY,
  count INTEGER NOT NULL DEFAULT 0
);

-- Cursiv Cloud (desktop app's free backup AI): messages per visitor IP per UTC day,
-- and the site-wide total per day.
CREATE TABLE IF NOT EXISTS cloud_usage (
  day   TEXT NOT NULL,
  ip    TEXT NOT NULL,
  count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, ip)
);
CREATE TABLE IF NOT EXISTS cloud_daily (
  day   TEXT PRIMARY KEY,
  count INTEGER NOT NULL DEFAULT 0
);

-- Problem reports sent from the desktop app ("Send problem report").
-- Read them with:  npx wrangler d1 execute cursiv --remote --command "SELECT id, created, version, note FROM reports ORDER BY created DESC LIMIT 20"
CREATE TABLE IF NOT EXISTS reports (
  id         TEXT PRIMARY KEY,
  created    TEXT NOT NULL,
  ip_hash    TEXT NOT NULL,
  install_id TEXT,
  version    TEXT,
  os         TEXT,
  note       TEXT,
  logs       TEXT
);
CREATE INDEX IF NOT EXISTS reports_ip_day ON reports (ip_hash, created);

-- Phone app ↔ desktop: a "space" is one person's shared conversation.
-- The desktop creates it, shows a 6-digit pairing code, the phone joins with it.
CREATE TABLE IF NOT EXISTS spaces (
  id          TEXT PRIMARY KEY,
  created     TEXT NOT NULL
);
-- Each paired device (the desktop, her phone, ...) has its own token for the same space.
CREATE TABLE IF NOT EXISTS space_devices (
  token_hash  TEXT PRIMARY KEY,
  space_id    TEXT NOT NULL,
  device      TEXT NOT NULL,          -- 'desktop' | 'phone'
  created     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pair_codes (
  code      TEXT PRIMARY KEY,
  space_id  TEXT NOT NULL,
  expires   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS space_messages (
  id          TEXT PRIMARY KEY,
  space_id    TEXT NOT NULL,
  created     TEXT NOT NULL,
  role        TEXT NOT NULL,          -- 'user' | 'assistant'
  source      TEXT NOT NULL,          -- 'phone' | 'desktop' | 'ai'
  text        TEXT NOT NULL,
  image       TEXT,                   -- base64 JPEG/PNG (resized on the phone), optional
  image_mime  TEXT
);
CREATE INDEX IF NOT EXISTS space_messages_by_space ON space_messages (space_id, created);

-- Per-person memory for the phone app: a short summary of the person's memories,
-- uploaded by their linked computer (only while "share memories with the phone" is on).
CREATE TABLE IF NOT EXISTS space_memory (
  space_id  TEXT PRIMARY KEY,
  person    TEXT,
  digest    TEXT NOT NULL,
  updated   TEXT NOT NULL
);

-- Website download analytics; identical to the additive analytics-schema.sql migration.
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
