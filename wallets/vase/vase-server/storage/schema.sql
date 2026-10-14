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
