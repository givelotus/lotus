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

	"sync"
	"vase.givelotus.org/server/initializers"
	"vase.givelotus.org/server/notifications"
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

type registrationHooks struct {
	Validate func(UserInfo) error
	Remove   func(context.Context, UserInfo) error
}

func newRouter(save func(context.Context, UserInfo) error, hooks ...registrationHooks) http.Handler {
	var hook registrationHooks
	if len(hooks) > 0 {
		hook = hooks[0]
	}
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
		if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 16*1024)).Decode(&info); err != nil {
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
		if hook.Validate != nil {
			if err := hook.Validate(info); err != nil {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid notification registration"})
				return
			}
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
	if hook.Remove != nil {
		mux.HandleFunc("POST /notifications/unregister", func(w http.ResponseWriter, r *http.Request) {
			var info UserInfo
			if json.NewDecoder(http.MaxBytesReader(w, r.Body, 16*1024)).Decode(&info) != nil || strings.TrimSpace(info.PushToken) == "" || strings.TrimSpace(info.Address) == "" {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "PushToken and Address are required"})
				return
			}
			ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
			defer cancel()
			if err := hook.Remove(ctx, info); err != nil {
				writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "Unable to unregister notifications"})
				return
			}
			w.WriteHeader(http.StatusNoContent)
		})
	}
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
	workerCtx, stopWorkers := context.WithCancel(ctx)
	var workers sync.WaitGroup
	defer func() { stopWorkers(); workers.Wait() }()
	var notifier *notifications.Service
	if os.Getenv("VASE_NOTIFICATIONS") == "fcm" {
		if pool.Config().MaxConns < 2 {
			return errors.New("notifications require at least two database pool connections")
		}
		provider, err := notifications.NewFCM(workerCtx, os.Getenv("FCM_PROJECT_ID"), os.Getenv("FCM_CREDENTIALS_FILE"))
		if err != nil {
			return err
		}
		notifier, err = notifications.New(notifications.PGStore{Pool: pool}, provider, os.Getenv("CHRONIK_URL"))
		if err != nil {
			return err
		}
		// A session advisory lock prevents duplicate workers across server replicas.
		lock, err := pool.Acquire(ctx)
		if err != nil {
			return err
		}
		defer func() {
			stopWorkers()
			workers.Wait()
			closeCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_ = lock.Hijack().Close(closeCtx)
		}()
		var acquired bool
		if err := lock.QueryRow(ctx, "SELECT pg_try_advisory_lock(8964001)").Scan(&acquired); err != nil {
			return err
		}
		if !acquired {
			return errors.New("another notification worker owns this database")
		}
		if _, err := (notifications.PGStore{Pool: pool}).Registrations(ctx); err != nil {
			return err
		}
		if _, err := pool.Exec(ctx, "SELECT 1 FROM notification_outbox LIMIT 0"); err != nil {
			return errors.New("notification schema is unavailable; run the migration")
		}
		workers.Add(1)
		go func() {
			defer workers.Done()
			tick := time.NewTicker(10 * time.Second)
			defer tick.Stop()
			for {
				select {
				case <-workerCtx.Done():
					return
				case <-tick.C:
					checkCtx, cancel := context.WithTimeout(workerCtx, 5*time.Second)
					err := lock.Conn().Ping(checkCtx)
					cancel()
					if err != nil {
						log.Print("notification ownership connection lost; stopping server")
						stopWorkers()
						return
					}
				}
			}
		}()
		ctx = workerCtx
		workers.Add(1)
		go func() { defer workers.Done(); notifier.Run(workerCtx) }()
	} else if os.Getenv("VASE_NOTIFICATIONS") != "" {
		return errors.New("unsupported notification provider")
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	server := &http.Server{
		Addr: ":" + port,
		Handler: newRouter(func(ctx context.Context, info UserInfo) error {
			if err := storage.SaveUserInfo(ctx, pool, info); err != nil {
				return err
			}
			if notifier != nil {
				notifier.Changed()
			}
			return nil
		}, registrationHooks{
			Validate: func(info UserInfo) error {
				if notifier == nil {
					return nil
				}
				_, err := notifications.Script(info.Address)
				return err
			},
			Remove: func(ctx context.Context, info UserInfo) error {
				if err := storage.RemoveNotificationRegistration(ctx, pool, info); err != nil {
					return err
				}
				if notifier != nil {
					notifier.Changed()
				}
				return nil
			},
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
