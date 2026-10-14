// Package storage persists the existing Vase tables using explicit PostgreSQL SQL.
package storage

import (
	"context"
	"errors"
	"strconv"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type UserInfo struct {
	PushToken string   `json:"PushToken"`
	Longitude *float32 `json:"Longitude"`
	Latitude  *float32 `json:"Latitude"`
	Address   string   `json:"Address"`
}

// ErrDeletedRecord preserves the old GORM Save rejection of soft-deleted keys.
var ErrDeletedRecord = errors.New("cannot update a soft-deleted record")

func SaveUserInfo(ctx context.Context, pool *pgxpool.Pool, info UserInfo) error {
	return pgx.BeginFunc(ctx, pool, func(tx pgx.Tx) error {
		now := time.Now().UTC()
		result, err := tx.Exec(ctx, `
			INSERT INTO users (push_token, created_at, updated_at) VALUES ($1, $2, $2)
			ON CONFLICT (push_token) DO UPDATE SET updated_at = EXCLUDED.updated_at
			WHERE users.deleted_at IS NULL`, info.PushToken, now)
		if err != nil {
			return err
		}
		if result.RowsAffected() != 1 {
			return ErrDeletedRecord
		}
		if _, err := tx.Exec(ctx, `
			INSERT INTO locations (push_token, longitude, latitude, address, created_at, updated_at)
			VALUES ($1, $2::numeric, $3::numeric, $4, $5, $5)`, info.PushToken,
			strconv.FormatFloat(float64(*info.Longitude), 'f', -1, 32),
			strconv.FormatFloat(float64(*info.Latitude), 'f', -1, 32), info.Address, now); err != nil {
			return err
		}
		result, err = tx.Exec(ctx, `
			INSERT INTO addresses (type, push_token, address, created_at, updated_at)
			VALUES ('XPI', $1, $2, $3, $3)
			ON CONFLICT (push_token, address) DO UPDATE
			SET type = EXCLUDED.type, updated_at = EXCLUDED.updated_at
			WHERE addresses.deleted_at IS NULL`, info.PushToken, info.Address, now)
		if err != nil {
			return err
		}
		if result.RowsAffected() != 1 {
			return ErrDeletedRecord
		}
		return nil
	})
}
