package notifications

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"time"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
)

type Provider interface {
	Send(context.Context, Delivery) (permanent bool, err error)
}
type FCM struct {
	Client   *http.Client
	Endpoint string
}

func NewFCM(ctx context.Context, project, credentials string) (*FCM, error) {
	if project == "" || credentials == "" {
		return nil, errors.New("FCM project and service-account credential path are required")
	}
	raw, err := os.ReadFile(credentials)
	if err != nil {
		return nil, errors.New("unable to read FCM credentials")
	}
	config, err := google.JWTConfigFromJSON(raw, "https://www.googleapis.com/auth/firebase.messaging")
	if err != nil || config.Email == "" || len(config.PrivateKey) == 0 || config.TokenURL == "" {
		return nil, errors.New("invalid FCM service-account credentials")
	}
	// Token acquisition uses the service lifecycle context; requests also carry their own deadlines.
	tokenCtx := context.WithValue(ctx, oauth2.HTTPClient, &http.Client{Timeout: 15 * time.Second})
	return &FCM{Client: &http.Client{Transport: &oauth2.Transport{Source: config.TokenSource(tokenCtx)}, Timeout: 20 * time.Second}, Endpoint: "https://fcm.googleapis.com/v1/projects/" + url.PathEscape(project) + "/messages:send"}, nil
}
func (f *FCM) Send(ctx context.Context, d Delivery) (bool, error) {
	body, _ := json.Marshal(map[string]any{"message": map[string]any{"token": d.Token, "notification": map[string]string{"title": "Lotus wallet activity", "body": "Open Vase to refresh your wallet."}, "data": map[string]string{"txid": d.TxID, "event_id": fmt.Sprint(d.ID)}}})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, f.Endpoint, bytes.NewReader(body))
	if err != nil {
		return false, err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := f.Client.Do(req)
	if err != nil {
		return false, errors.New("push transport failed")
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(io.LimitReader(resp.Body, 65537))
	if err != nil {
		return false, errors.New("push response failed")
	}
	if resp.StatusCode == 200 {
		var accepted struct {
			Name string `json:"name"`
		}
		if json.Unmarshal(raw, &accepted) != nil || accepted.Name == "" {
			return false, errors.New("invalid push acceptance response")
		}
		return false, nil
	}
	// Only explicit FCM token invalidation is terminal; auth/config failures remain retriable.
	var failure struct {
		Error struct {
			Details []struct {
				Code string `json:"errorCode"`
			} `json:"details"`
		} `json:"error"`
	}
	_ = json.Unmarshal(raw, &failure)
	for _, detail := range failure.Error.Details {
		if detail.Code == "UNREGISTERED" {
			return true, errors.New("push token unregistered")
		}
	}
	return false, fmt.Errorf("push rejected (HTTP %d)", resp.StatusCode)
}
