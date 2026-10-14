package main

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"vase.givelotus.org/server/initializers"
	"vase.givelotus.org/server/storage"
)

type UserInfo = storage.UserInfo

func writeJSON(w http.ResponseWriter, status int, value any) {
	body, err := json.Marshal(value)
	if err != nil {
		http.Error(w, "Unable to encode response", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_, _ = w.Write(body)
}

func newRouter(save func(context.Context, UserInfo) error) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/userinfo", func(w http.ResponseWriter, r *http.Request) {
		// Gin's previous default returned 404 rather than 405 for other methods.
		if r.Method != http.MethodPost {
			http.NotFound(w, r)
			return
		}
		defer func() {
			if recover() != nil {
				log.Print("request handler failed")
				w.WriteHeader(http.StatusInternalServerError)
			}
		}()
		var info UserInfo
		// Preserve ShouldBindJSON behavior: unknown fields, missing Content-Type,
		// and data following the first JSON object are accepted as before.
		if err := json.NewDecoder(r.Body).Decode(&info); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid user information"})
			return
		}
		if strings.TrimSpace(info.PushToken) == "" || strings.TrimSpace(info.Address) == "" ||
			info.Longitude == nil || info.Latitude == nil ||
			*info.Longitude < -180 || *info.Longitude > 180 ||
			*info.Latitude < -90 || *info.Latitude > 90 {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "PushToken, Address, and valid coordinates are required"})
			return
		}
		ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
		defer cancel()
		if err := save(ctx, info); err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "Unable to save user information"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]UserInfo{"info": info})
	})
	mux.HandleFunc("/userinfo/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost && r.URL.Path == "/userinfo/" {
			http.Redirect(w, r, "/userinfo", http.StatusTemporaryRedirect)
			return
		}
		http.NotFound(w, r)
	})
	return mux
}

func run(ctx context.Context) error {
	if err := initializers.LoadEnvVariables(); err != nil {
		return err
	}
	startup, cancel := context.WithTimeout(ctx, 5*time.Second)
	pool, err := initializers.ConnectToDB(startup)
	cancel()
	if err != nil {
		return err
	}
	defer pool.Close()
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	server := &http.Server{
		Addr: ":" + port,
		Handler: newRouter(func(ctx context.Context, info UserInfo) error {
			return storage.SaveUserInfo(ctx, pool, info)
		}),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	finished := make(chan struct{})
	shutdown := make(chan error, 1)
	go func() {
		select {
		case <-ctx.Done():
			grace, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			shutdown <- server.Shutdown(grace)
		case <-finished:
		}
	}()
	err = server.ListenAndServe()
	close(finished)
	if errors.Is(err, http.ErrServerClosed) {
		if err := <-shutdown; err != nil {
			_ = server.Close()
			return errors.New("HTTP shutdown failed")
		}
		return nil
	}
	return errors.New("HTTP server failed to listen")
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	if err := run(ctx); err != nil {
		log.Fatal(err)
	}
}
