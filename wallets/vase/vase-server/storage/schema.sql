-- Additive bootstrap for new installations. Existing tables/data are not altered.
-- PostGIS is retained for future nearby-user queries; never update an existing extension here.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS users (
    push_token text PRIMARY KEY,
    created_at timestamptz,
    updated_at timestamptz,
    deleted_at timestamptz
);
CREATE TABLE IF NOT EXISTS addresses (
    type text DEFAULT 'XPI',
    push_token text NOT NULL,
    address text NOT NULL,
    created_at timestamptz,
    updated_at timestamptz,
    deleted_at timestamptz,
    PRIMARY KEY (push_token, address),
    CONSTRAINT fk_users_addresses FOREIGN KEY (push_token) REFERENCES users(push_token)
);
CREATE TABLE IF NOT EXISTS locations (
    id bigserial PRIMARY KEY,
    push_token text,
    longitude numeric,
    latitude numeric,
    address text,
    created_at timestamptz,
    updated_at timestamptz,
    deleted_at timestamptz,
    CONSTRAINT fk_users_location FOREIGN KEY (push_token) REFERENCES users(push_token)
);
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users (deleted_at);
CREATE INDEX IF NOT EXISTS idx_addresses_deleted_at ON addresses (deleted_at);
CREATE INDEX IF NOT EXISTS idx_locations_deleted_at ON locations (deleted_at);
CREATE INDEX IF NOT EXISTS idx_locations_push_token ON locations (push_token);

-- Durable notification attempts; accepted means provider acceptance, not device delivery.
CREATE TABLE IF NOT EXISTS notification_outbox (
 id bigserial PRIMARY KEY,
 push_token text NOT NULL,
 address text NOT NULL,
 txid text NOT NULL,
 attempts integer NOT NULL DEFAULT 0,
 next_attempt_at timestamptz NOT NULL DEFAULT now(),
 created_at timestamptz NOT NULL DEFAULT now(),
 completed_at timestamptz,
 accepted boolean NOT NULL DEFAULT false,
 UNIQUE(push_token,address,txid)
);
CREATE INDEX IF NOT EXISTS notification_pending ON notification_outbox(next_attempt_at,id) WHERE completed_at IS NULL;
