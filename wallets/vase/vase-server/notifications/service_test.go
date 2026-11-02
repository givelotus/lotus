package notifications

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"math/big"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/coder/websocket"
	"google.golang.org/protobuf/proto"
	pb "vase.givelotus.org/server/notifications/chronikpb"
)

type memoryStore struct {
	mu     sync.Mutex
	regs   []Registration
	queued map[string]Delivery
	sends  int
}

func (m *memoryStore) Registrations(context.Context) ([]Registration, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return append([]Registration(nil), m.regs...), nil
}
func (m *memoryStore) Enqueue(_ context.Context, regs []Registration, id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, r := range regs {
		key := r.Token + r.Address + id
		m.queued[key] = Delivery{Token: r.Token, Address: r.Address, TxID: id}
	}
	return nil
}
func (m *memoryStore) Next(context.Context) (*Delivery, error)            { return nil, nil }
func (m *memoryStore) Finish(context.Context, Delivery, bool, bool) error { return nil }

type fakeProvider struct{}

func (fakeProvider) Send(context.Context, Delivery) (bool, error) { return false, nil }
func waitFor(t *testing.T, fn func() bool) {
	t.Helper()
	until := time.Now().Add(5 * time.Second)
	for time.Now().Before(until) {
		if fn() {
			return
		}
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatal("condition not reached")
}

func TestSubscriptionsReconnectRouteAndCancel(t *testing.T) {
	script := []byte{0x51}
	store := &memoryStore{regs: []Registration{{"dummy-a", "dummy-address", script}, {"dummy-b", "dummy-address", script}}, queued: map[string]Delivery{}}
	var sessions atomic.Int32
	var subs atomic.Int32
	var unsubs atomic.Int32
	txid := bytes.Repeat([]byte{7}, 32)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/tx/") {
			raw, _ := proto.Marshal(&pb.Tx{Outputs: []*pb.TxOutput{{OutputScript: script}}})
			w.Write(raw)
			return
		}
		conn, err := websocket.Accept(w, r, nil)
		if err != nil {
			return
		}
		defer conn.CloseNow()
		session := sessions.Add(1)
		for {
			_, raw, err := conn.Read(r.Context())
			if err != nil {
				return
			}
			var sub pb.WsSub
			if proto.Unmarshal(raw, &sub) != nil {
				return
			}
			if sub.IsUnsub {
				unsubs.Add(1)
				continue
			}
			subs.Add(1)
			event, _ := proto.Marshal(&pb.WsMsg{MsgType: &pb.WsMsg_Tx{Tx: &pb.MsgTx{Txid: txid}}})
			conn.Write(r.Context(), websocket.MessageBinary, event)
			conn.Write(r.Context(), websocket.MessageBinary, event)
			if session == 1 {
				return
			}
		}
	}))
	defer server.Close()
	service, _ := New(store, fakeProvider{}, server.URL)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	done := make(chan struct{})
	go func() { service.Run(ctx); close(done) }()
	waitFor(t, func() bool { return sessions.Load() >= 2 && subs.Load() >= 2 })
	waitFor(t, func() bool { store.mu.Lock(); defer store.mu.Unlock(); return len(store.queued) == 2 })
	store.mu.Lock()
	store.regs = nil
	store.mu.Unlock()
	service.Changed()
	waitFor(t, func() bool { return unsubs.Load() == 1 })
	cancel()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("workers did not stop")
	}
	if subs.Load() != 2 {
		t.Fatalf("expected one shared script per session, got %d", subs.Load())
	}
}

func TestFCMAcceptanceAndFailure(t *testing.T) {
	for _, tc := range []struct {
		status            int
		body              string
		permanent, failed bool
	}{{200, `{"name":"projects/test/messages/123"}`, false, false}, {200, `{}`, false, true}, {404, `{"error":{"details":[{"errorCode":"UNREGISTERED"}]}}`, true, true}, {401, `{}`, false, true}, {429, `{}`, false, true}} {
		t.Run(fmt.Sprint(tc.status, tc.body), func(t *testing.T) {
			srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				var body map[string]any
				if json.NewDecoder(r.Body).Decode(&body) != nil {
					t.Error("invalid JSON")
				}
				message := body["message"].(map[string]any)
				if message["token"] != "dummy-token" {
					t.Error("wrong target")
				}
				if strings.Contains(fmt.Sprint(body), "private-address") {
					t.Error("address leaked to provider")
				}
				w.WriteHeader(tc.status)
				w.Write([]byte(tc.body))
			}))
			defer srv.Close()
			f := FCM{Client: srv.Client(), Endpoint: srv.URL}
			permanent, err := f.Send(context.Background(), Delivery{Token: "dummy-token", Address: "private-address", TxID: "dummy-txid"})
			if permanent != tc.permanent || (err != nil) != tc.failed {
				t.Fatalf("got permanent=%v err=%v", permanent, err)
			}
		})
	}
	if _, err := NewFCM(context.Background(), "", ""); err == nil {
		t.Fatal("missing credentials accepted")
	}
}

func encodeAddress(script []byte, legacy bool) string {
	preimage := append([]byte("lotus_\x00"), script...)
	if legacy {
		preimage = append([]byte{5, 'l', 'o', 't', 'u', 's', '_', 0, byte(len(script))}, script...)
	}
	sum := sha256.Sum256(preimage)
	raw := append(append([]byte{0}, script...), sum[:4]...)
	n := new(big.Int).SetBytes(raw)
	alphabet := "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
	encoded := ""
	base := big.NewInt(58)
	for n.Sign() > 0 {
		rem := new(big.Int)
		n.QuoRem(n, base, rem)
		encoded = string(alphabet[rem.Int64()]) + encoded
	}
	for _, b := range raw {
		if b != 0 {
			break
		}
		encoded = "1" + encoded
	}
	return "lotus_" + encoded
}
func TestMainnetAddressChecksumsAndScript(t *testing.T) {
	script := append([]byte{0x76, 0xa9, 0x14}, bytes.Repeat([]byte{3}, 20)...)
	script = append(script, 0x88, 0xac)
	for _, legacy := range []bool{false, true} {
		address := encodeAddress(script, legacy)
		decoded, err := Script(address)
		if err != nil || !bytes.Equal(script, decoded) {
			t.Fatal(err)
		}
		kind, payload := subscription(decoded)
		if kind != "p2pkh" || len(payload) != 20 {
			t.Fatal("wrong subscription")
		}
		if _, err := Script(address[:len(address)-1] + "0"); err == nil {
			t.Fatal("invalid checksum accepted")
		}
	}
	for _, bad := range []string{"lotus_", "lotusR1234", "bitcoin_1234", strings.Repeat("a", 201)} {
		if _, err := Script(bad); err == nil {
			t.Fatal("bad address accepted")
		}
	}
}

func TestLotusTaprootAndPublicKeySubscriptions(t *testing.T) {
	key := bytes.Repeat([]byte{2}, 33)
	script := append([]byte{0x62, 0x51, 0x21}, key...)
	for _, candidate := range [][]byte{script, append(append(append([]byte(nil), script...), 0x20), make([]byte, 32)...)} {
		kind, payload := subscription(candidate)
		if kind != "p2tr" || !bytes.Equal(payload, key) {
			t.Fatal("Taproot must subscribe by commitment key")
		}
	}
	p2pk := append(append([]byte{0x21}, key...), 0xac)
	kind, payload := subscription(p2pk)
	if kind != "p2pk" || !bytes.Equal(payload, key) {
		t.Fatal("P2PK must subscribe by public key")
	}
}

type deliveryStore struct {
	memoryStore
	pending  bool
	accepted bool
}

func (s *deliveryStore) Next(context.Context) (*Delivery, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.pending {
		return nil, nil
	}
	return &Delivery{ID: 1, Token: "dummy-token"}, nil
}
func (s *deliveryStore) Finish(_ context.Context, _ Delivery, success, permanent bool) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.pending = false
	s.accepted = success
	return nil
}
func TestDeliveryWorkerRecordsAcceptanceAndStops(t *testing.T) {
	store := &deliveryStore{pending: true}
	service, _ := New(store, fakeProvider{}, "http://127.0.0.1:1")
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() { service.deliver(ctx); close(done) }()
	waitFor(t, func() bool { store.mu.Lock(); defer store.mu.Unlock(); return store.accepted })
	cancel()
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("delivery worker did not stop")
	}
}
