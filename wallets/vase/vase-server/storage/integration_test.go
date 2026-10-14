package storage

import (
	"context"
	_ "embed"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

//go:embed testdata/legacy_schema.sql
var legacySchema string

// Integration tests create their own cluster and never accept a database DSN.
// PostgreSQL binaries may be supplied via VASE_TEST_POSTGRES_BIN or PATH.
func isolatedPostgres(t *testing.T) *pgxpool.Pool {
	t.Helper()
	bin := os.Getenv("VASE_TEST_POSTGRES_BIN")
	if bin == "" {
		path, err := exec.LookPath("initdb")
		if err != nil {
			t.Skip("PostgreSQL initdb/pg_ctl are required for isolated integration tests")
		}
		bin = filepath.Dir(path)
	}
	if os.Geteuid() == 0 {
		t.Skip("initdb cannot run as root")
	}
	dir, err := os.MkdirTemp("", "vase-pg-")
	if err != nil {
		t.Fatal(err)
	}
	// macOS's default temporary paths can exceed Unix socket path limits.
	socket, err := os.MkdirTemp("/tmp", "vase-pg-socket-")
	if err != nil {
		_ = os.RemoveAll(dir)
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.RemoveAll(dir); _ = os.RemoveAll(socket) })
	run := func(name string, args ...string) {
		t.Helper()
		if out, err := exec.Command(filepath.Join(bin, name), args...).CombinedOutput(); err != nil {
			t.Fatalf("isolated PostgreSQL %s failed: %v\n%s", name, err, out)
		}
	}
	data := filepath.Join(dir, "data")
	run("initdb", "-D", data, "-U", "vase_test", "--auth=trust", "--encoding=UTF8", "--no-locale")
	// The cluster listens only on its own Unix socket, with no TCP port exposed.
	run("pg_ctl", "-D", data, "-l", filepath.Join(dir, "postgres.log"), "-o", "-h '' -k "+socket, "-w", "start")
	t.Cleanup(func() {
		if out, err := exec.Command(filepath.Join(bin, "pg_ctl"), "-D", data, "-m", "fast", "-w", "stop").CombinedOutput(); err != nil {
			t.Errorf("isolated PostgreSQL shutdown failed: %v\n%s", err, out)
		}
	})
	pool, err := pgxpool.New(context.Background(), "host="+socket+" user=vase_test dbname=postgres sslmode=disable")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	if err := pool.Ping(context.Background()); err != nil {
		t.Fatal(err)
	}
	return pool
}

func schemaColumns(t *testing.T, pool *pgxpool.Pool) []string {
	t.Helper()
	rows, err := pool.Query(context.Background(), `SELECT table_name, column_name, data_type, is_nullable,
		COALESCE(column_default,'') FROM information_schema.columns
		WHERE table_schema='public' AND table_name IN ('users','addresses','locations')
		ORDER BY table_name, ordinal_position`)
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	var result []string
	for rows.Next() {
		var table, column, kind, nullable, value string
		if err := rows.Scan(&table, &column, &kind, &nullable, &value); err != nil {
			t.Fatal(err)
		}
		result = append(result, strings.Join([]string{table, column, kind, nullable, value}, "|"))
	}
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
	return result
}

func TestPostgresPersistenceCompatibility(t *testing.T) {
	admin := isolatedPostgres(t)
	ctx := context.Background()
	for _, legacy := range []bool{false, true} {
		t.Run(fmt.Sprintf("legacy_GORM_schema_%v", legacy), func(t *testing.T) {
			db := "vase_fixture_" + strconv.FormatBool(legacy)
			if _, err := admin.Exec(ctx, "CREATE DATABASE "+db); err != nil {
				t.Fatal(err)
			}
			config := admin.Config()
			config.ConnConfig.Database = db
			pool, err := pgxpool.NewWithConfig(ctx, config)
			if err != nil {
				t.Fatal(err)
			}
			defer pool.Close()
			var before []string
			if legacy {
				if _, err := pool.Exec(ctx, legacySchema); err != nil {
					t.Fatal(err)
				}
				before = schemaColumns(t, pool)
			}
			if err := Migrate(ctx, pool); err != nil {
				t.Fatal(err)
			}
			if err := Migrate(ctx, pool); err != nil {
				t.Fatal(err)
			}
			if legacy && !reflect.DeepEqual(before, schemaColumns(t, pool)) {
				t.Fatal("migration changed legacy columns/defaults")
			}
			var postgis string
			if err := pool.QueryRow(ctx, "SELECT postgis_lib_version()").Scan(&postgis); err != nil {
				t.Fatal(err)
			}
			t.Logf("actual PostGIS extension: %s", postgis)
			created := time.Date(2000, 1, 2, 3, 4, 5, 0, time.UTC)
			if _, err := pool.Exec(ctx, `INSERT INTO users(push_token,created_at,updated_at) VALUES('existing',$1,$1);
			`, created); err != nil {
				t.Fatal(err)
			}
			if _, err := pool.Exec(ctx, `INSERT INTO addresses(type,push_token,address,created_at,updated_at)
			VALUES('OLD','existing','address',$1,$1)`, created); err != nil {
				t.Fatal(err)
			}
			if _, err := pool.Exec(ctx, `INSERT INTO locations(id,push_token,longitude,latitude,address,created_at,updated_at)
			VALUES(42,'existing',1,2,'historical',$1,$1)`, created); err != nil {
				t.Fatal(err)
			}
			if _, err := pool.Exec(ctx, `SELECT setval('locations_id_seq',42)`); err != nil {
				t.Fatal(err)
			}
			if err := Migrate(ctx, pool); err != nil {
				t.Fatal(err)
			}
			lon, lat := float32(12.345), float32(-45.678)
			info := UserInfo{PushToken: "existing", Address: "address", Longitude: &lon, Latitude: &lat}
			for i := 0; i < 2; i++ {
				if err := SaveUserInfo(ctx, pool, info); err != nil {
					t.Fatal(err)
				}
			}
			var users, addresses, locations int
			if err := pool.QueryRow(ctx, `SELECT (SELECT count(*) FROM users),(SELECT count(*) FROM addresses),(SELECT count(*) FROM locations)`).Scan(&users, &addresses, &locations); err != nil {
				t.Fatal(err)
			}
			if users != 1 || addresses != 1 || locations != 3 {
				t.Fatalf("counts after repeated POST: %d %d %d", users, addresses, locations)
			}
			var userCreated, addressCreated, updated time.Time
			var addressType string
			if err := pool.QueryRow(ctx, `SELECT u.created_at,a.created_at,u.updated_at,a.type FROM users u JOIN addresses a USING(push_token)`).Scan(&userCreated, &addressCreated, &updated, &addressType); err != nil {
				t.Fatal(err)
			}
			if !userCreated.Equal(created) || !addressCreated.Equal(created) || !updated.After(created) || addressType != "XPI" {
				t.Fatal("existing timestamps or address upsert incorrect")
			}
			var longitude, latitude string
			var newestID int64
			if err := pool.QueryRow(ctx, `SELECT id,longitude::text,latitude::text FROM locations ORDER BY id DESC LIMIT 1`).Scan(&newestID, &longitude, &latitude); err != nil {
				t.Fatal(err)
			}
			if newestID != 44 || longitude != "12.345" || latitude != "-45.678" {
				t.Fatalf("location/sequence mismatch: %d %s %s", newestID, longitude, latitude)
			}
			// The third write fails; the new user and location must both roll back.
			if _, err := pool.Exec(ctx, `ALTER TABLE addresses ADD CONSTRAINT fixture_reject CHECK (address <> 'reject')`); err != nil {
				t.Fatal(err)
			}
			bad := info
			bad.PushToken = "rollback"
			bad.Address = "reject"
			if err := SaveUserInfo(ctx, pool, bad); err == nil {
				t.Fatal("expected third-write failure")
			}
			var count int
			if err := pool.QueryRow(ctx, `SELECT (SELECT count(*) FROM users WHERE push_token='rollback')+(SELECT count(*) FROM locations WHERE push_token='rollback')`).Scan(&count); err != nil || count != 0 {
				t.Fatalf("partial persistence: %d %v", count, err)
			}
			for _, table := range []string{"addresses", "users"} {
				if _, err := pool.Exec(ctx, "UPDATE "+table+" SET deleted_at=now() WHERE push_token='existing'"); err != nil {
					t.Fatal(err)
				}
				if err := SaveUserInfo(ctx, pool, info); !errors.Is(err, ErrDeletedRecord) {
					t.Fatalf("soft-deleted %s was not rejected: %v", table, err)
				}
				if err := pool.QueryRow(ctx, `SELECT count(*) FROM locations`).Scan(&count); err != nil || count != 3 {
					t.Fatalf("soft-delete rejection did not roll back: %d %v", count, err)
				}
				if _, err := pool.Exec(ctx, "UPDATE "+table+" SET deleted_at=NULL WHERE push_token='existing'"); err != nil {
					t.Fatal(err)
				}
			}
			cancelled, cancel := context.WithCancel(ctx)
			cancel()
			if err := SaveUserInfo(cancelled, pool, info); err == nil {
				t.Fatal("cancelled request persisted")
			}
		})
	}
}
