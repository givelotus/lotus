package main

import (
	"context"
	"log"
	"time"

	"vase.givelotus.org/server/initializers"
	"vase.givelotus.org/server/storage"
)

func main() {
	if err := initializers.LoadEnvVariables(); err != nil {
		log.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	pool, err := initializers.ConnectToDB(ctx)
	if err != nil {
		log.Fatal(err)
	}
	defer pool.Close()
	if err := storage.Migrate(ctx, pool); err != nil {
		// Do not log database details or connection strings.
		log.Fatal("database migration failed")
	}
}
