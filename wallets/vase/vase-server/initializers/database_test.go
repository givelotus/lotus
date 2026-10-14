package initializers

import (
	"context"
	"strings"
	"testing"
)

func TestDatabaseConfigurationRejectsMissingOrInvalidDSNWithoutLeakingSecrets(t *testing.T) {
	for _, dsn := range []string{"", "password='private credential"} {
		t.Setenv("DB_STRING", dsn)
		pool, err := ConnectToDB(context.Background())
		if err == nil || pool != nil {
			t.Fatal("invalid configuration was accepted")
		}
		if strings.Contains(err.Error(), "private credential") {
			t.Fatal("configuration error leaked credentials")
		}
	}
}
