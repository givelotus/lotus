package main

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestUserInfoRejectsInvalidRequests(t *testing.T) {
	gin.SetMode(gin.TestMode)
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
	gin.SetMode(gin.TestMode)
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
	gin.SetMode(gin.TestMode)
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
