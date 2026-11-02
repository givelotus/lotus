package notifications

import (
	"context"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type Registration struct {
	Token, Address string
	Script         []byte
}
type Delivery struct {
	ID                   int64
	Token, Address, TxID string
	Attempts             int
}
type Store interface {
	Registrations(context.Context) ([]Registration, error)
	Enqueue(context.Context, []Registration, string) error
	Next(context.Context) (*Delivery, error)
	Finish(context.Context, Delivery, bool, bool) error
}
type PGStore struct{ Pool *pgxpool.Pool }

func (s PGStore) Registrations(ctx context.Context) ([]Registration, error) {
	rows, err := s.Pool.Query(ctx, `SELECT a.push_token,a.address FROM addresses a JOIN users u USING(push_token) WHERE a.deleted_at IS NULL AND u.deleted_at IS NULL AND a.type='XPI' ORDER BY a.push_token,a.address LIMIT 10001`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Registration
	count := 0
	for rows.Next() {
		count++
		if count > 10000 {
			return nil, errors.New("notification registration capacity exceeded")
		}
		var r Registration
		if err := rows.Scan(&r.Token, &r.Address); err != nil {
			return nil, err
		}
		if r.Script, err = Script(r.Address); err == nil {
			out = append(out, r)
		}
	}
	return out, rows.Err()
}
func (s PGStore) Enqueue(ctx context.Context, regs []Registration, txid string) error {
	return pgx.BeginFunc(ctx, s.Pool, func(tx pgx.Tx) error {
		// Serializes queue capacity checks even if a future producer is added.
		if _, err := tx.Exec(ctx, `SELECT pg_advisory_xact_lock(8964002)`); err != nil {
			return err
		}
		var count int
		if err := tx.QueryRow(ctx, `SELECT count(*) FROM notification_outbox `).Scan(&count); err != nil {
			return err
		}
		if count+len(regs) > 100000 {
			return errors.New("notification outbox capacity exceeded")
		}
		for _, r := range regs {
			if _, err := tx.Exec(ctx, `INSERT INTO notification_outbox(push_token,address,txid) VALUES($1,$2,$3) ON CONFLICT DO NOTHING`, r.Token, r.Address, txid); err != nil {
				return err
			}
		}
		return nil
	})
}
func (s PGStore) Next(ctx context.Context) (*Delivery, error) {
	// Seven-day retention bounds dedupe storage; expired/terminal rows are pruned in batches.
	if _, err := s.Pool.Exec(ctx, `DELETE FROM notification_outbox WHERE id IN (SELECT id FROM notification_outbox WHERE created_at < now()-interval '7 days' LIMIT 1000)`); err != nil {
		return nil, err
	}
	var d Delivery
	err := s.Pool.QueryRow(ctx, `SELECT o.id,o.push_token,o.address,o.txid,o.attempts FROM notification_outbox o JOIN addresses a ON a.push_token=o.push_token AND a.address=o.address JOIN users u ON u.push_token=a.push_token WHERE o.completed_at IS NULL AND o.created_at >= now()-interval '7 days' AND o.next_attempt_at<=now() AND a.deleted_at IS NULL AND u.deleted_at IS NULL ORDER BY o.id LIMIT 1`).Scan(&d.ID, &d.Token, &d.Address, &d.TxID, &d.Attempts)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	return &d, err
}
func (s PGStore) Finish(ctx context.Context, d Delivery, success, permanent bool) error {
	delay := time.Second * time.Duration(1<<min(d.Attempts+1, 12))
	_, err := s.Pool.Exec(ctx, `UPDATE notification_outbox SET attempts=attempts+1,next_attempt_at=now()+$2::interval,completed_at=CASE WHEN $3 OR attempts>=11 THEN now() ELSE NULL END,accepted=$4 WHERE id=$1`, d.ID, delay.String(), success || permanent, success)
	return err
}
