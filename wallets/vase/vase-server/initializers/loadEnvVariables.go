package initializers

import (
	"errors"
	"os"

	"github.com/joho/godotenv"
)

func LoadEnvVariables() error {
	// Production can supply environment variables directly, without a .env file.
	if err := godotenv.Load(); err != nil && !errors.Is(err, os.ErrNotExist) {
		return errors.New("failed to load environment configuration")
	}
	return nil
}
