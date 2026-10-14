package main

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestUserInfoRejectsInvalidRequests(t *testing.T) {
	bodies := []string{
		``,
		`{`,
		`null`,
		`[]`,
		`{}`,
		`{"PushToken":"token","Address":"address","Latitude":0}`,
		`{"PushToken":"token","Address":"address","Longitude":0,"Latitude":null}`,
		`{"PushToken":" ","Address":"address","Longitude":0,"Latitude":0}`,
		`{"PushToken":"token","Address":" ","Longitude":0,"Latitude":0}`,
		`{"PushToken":"token","Address":"address","Longitude":181,"Latitude":0}`,
		`{"PushToken":"token","Address":"address","Longitude":-181,"Latitude":0}`,
		`{"PushToken":"token","Address":"address","Longitude":0,"Latitude":91}`,
		`{"PushToken":"token","Address":"address","Longitude":0,"Latitude":-91}`,
		`{"PushToken":"token","Address":"address","Longitude":"0","Latitude":0}`,
	}
	for _, body := range bodies {
		t.Run(body, func(t *testing.T) {
			router := newRouter(func(context.Context, UserInfo) error {
				t.Fatal("invalid request reached persistence")
				return nil
			})
			response := httptest.NewRecorder()
			router.ServeHTTP(response, httptest.NewRequest(http.MethodPost, "/userinfo", strings.NewReader(body)))
			if response.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, body = %s", response.Code, response.Body.String())
			}
		})
	}
}

func TestUserInfoSavesAndEchoesValidCoordinates(t *testing.T) {
	for _, coordinates := range []string{`"Longitude":0,"Latitude":0`, `"Longitude":-180,"Latitude":90`, `"Longitude":180,"Latitude":-90`} {
		t.Run(coordinates, func(t *testing.T) {
			body := `{"PushToken":"token","Address":"address",` + coordinates + `}`
			var saved UserInfo
			called := false
			router := newRouter(func(ctx context.Context, info UserInfo) error {
				if ctx == nil {
					t.Fatal("missing request context")
				}
				called, saved = true, info
				return nil
			})
			response := httptest.NewRecorder()
			router.ServeHTTP(response, httptest.NewRequest(http.MethodPost, "/userinfo", strings.NewReader(body)))
			if response.Code != http.StatusOK || !called {
				t.Fatalf("status = %d, saved = %v", response.Code, called)
			}
			var decoded struct {
				Info UserInfo `json:"info"`
			}
			if err := json.Unmarshal(response.Body.Bytes(), &decoded); err != nil {
				t.Fatal(err)
			}
			if decoded.Info.PushToken != saved.PushToken || decoded.Info.Address != saved.Address ||
				*decoded.Info.Longitude != *saved.Longitude || *decoded.Info.Latitude != *saved.Latitude {
				t.Fatalf("response does not match saved request: %s", response.Body.String())
			}
		})
	}
}

func TestUserInfoReportsPersistenceFailure(t *testing.T) {
	router := newRouter(func(context.Context, UserInfo) error {
		return errors.New("private database connection details")
	})
	response := httptest.NewRecorder()
	body := `{"PushToken":"token","Address":"address","Longitude":0,"Latitude":0}`
	router.ServeHTTP(response, httptest.NewRequest(http.MethodPost, "/userinfo", strings.NewReader(body)))
	if response.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d", response.Code)
	}
	if strings.Contains(response.Body.String(), "private database") {
		t.Fatal("response exposed database error")
	}
}

func TestUserInfoCompatibility(t *testing.T) {
	body := `{"PushToken":"token","Address":"address","Longitude":0,"Latitude":0,"Unknown":"accepted"} {"trailing":"accepted"}`
	for _, contentType := range []string{"", "application/json", "text/plain"} {
		t.Run(contentType, func(t *testing.T) {
			key := struct{}{}
			ctx, cancel := context.WithCancel(context.WithValue(context.Background(), key, "request-value"))
			cancel()
			router := newRouter(func(got context.Context, info UserInfo) error {
				if got.Value(key) != "request-value" || !errors.Is(got.Err(), context.Canceled) {
					t.Fatal("request context was not propagated")
				}
				return nil
			})
			request := httptest.NewRequest(http.MethodPost, "/userinfo", strings.NewReader(body)).WithContext(ctx)
			request.Header.Set("Content-Type", contentType)
			response := httptest.NewRecorder()
			router.ServeHTTP(response, request)
			if response.Code != http.StatusOK {
				t.Fatalf("legacy JSON binding behavior changed: %d %s", response.Code, response.Body.String())
			}
			if response.Header().Get("Content-Type") != "application/json; charset=utf-8" {
				t.Fatal("unexpected JSON response content type")
			}
			if response.Header().Get("Access-Control-Allow-Origin") != "" {
				t.Fatal("CORS policy changed")
			}
		})
	}
}

func TestRouterMethodAndPathCompatibility(t *testing.T) {
	router := newRouter(func(context.Context, UserInfo) error {
		t.Fatal("unrecognized route reached persistence")
		return nil
	})
	for _, tc := range []struct {
		method, path string
		status       int
	}{
		{http.MethodGet, "/userinfo", http.StatusNotFound},
		{http.MethodOptions, "/userinfo", http.StatusNotFound},
		{http.MethodPost, "/missing", http.StatusNotFound},
		{http.MethodPost, "/userinfo/", http.StatusTemporaryRedirect},
		{http.MethodPost, "/userinfo/nested", http.StatusNotFound},
	} {
		response := httptest.NewRecorder()
		router.ServeHTTP(response, httptest.NewRequest(tc.method, tc.path, nil))
		if response.Code != tc.status {
			t.Fatalf("%s %s status = %d, expected %d", tc.method, tc.path, response.Code, tc.status)
		}
	}
}

func TestRouterRecoversPersistencePanic(t *testing.T) {
	router := newRouter(func(context.Context, UserInfo) error { panic("private persistence details") })
	response := httptest.NewRecorder()
	body := `{"PushToken":"token","Address":"address","Longitude":0,"Latitude":0}`
	router.ServeHTTP(response, httptest.NewRequest(http.MethodPost, "/userinfo", strings.NewReader(body)))
	if response.Code != http.StatusInternalServerError || strings.Contains(response.Body.String(), "private") {
		t.Fatalf("unexpected panic response: %d %s", response.Code, response.Body.String())
	}
}
