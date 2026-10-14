package initializers

import (
	"context"
	"errors"
	"os"

	"github.com/jackc/pgx/v5/pgxpool"
)

func ConnectToDB(ctx context.Context) (*pgxpool.Pool, error) {
	dsn := os.Getenv("DB_STRING")
	if dsn == "" {
		return nil, errors.New("DB_STRING is required")
	}
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, errors.New("invalid database configuration")
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		// Connection errors can contain credentials from a DSN; keep logs generic.
		return nil, errors.New("failed to connect to database")
	}
	return pool, nil
}
