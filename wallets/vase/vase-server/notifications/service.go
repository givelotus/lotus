// Package notifications observes Chronik wallet activity and durably queues push attempts.
package notifications

import (
	"context"
	"encoding/hex"
	"errors"
	"io"
	"log"
	"math/rand/v2"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/coder/websocket"
	"google.golang.org/protobuf/proto"
	pb "vase.givelotus.org/server/notifications/chronikpb"
)

type Service struct {
	Store    Store
	Provider Provider
	URL      string // HTTP(S) Chronik base URL, without /ws
	HTTP     *http.Client
	wake     chan struct{}
	once     sync.Once
}

func New(store Store, provider Provider, endpoint string) (*Service, error) {
	u, err := url.Parse(endpoint)
	if err != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Host == "" || u.User != nil || u.RawQuery != "" || u.Fragment != "" {
		return nil, errors.New("invalid Chronik HTTP base URL")
	}
	return &Service{Store: store, Provider: provider, URL: strings.TrimRight(endpoint, "/"), HTTP: &http.Client{Timeout: 15 * time.Second}, wake: make(chan struct{}, 1)}, nil
}
func (s *Service) Changed() {
	select {
	case s.wake <- struct{}{}:
	default:
	}
}

// Run blocks until cancellation and joins both workers. Each instance may run once.
func (s *Service) Run(ctx context.Context) {
	s.once.Do(func() {
		var wg sync.WaitGroup
		wg.Add(2)
		go func() { defer wg.Done(); s.observe(ctx) }()
		go func() { defer wg.Done(); s.deliver(ctx) }()
		wg.Wait()
	})
}
func pause(ctx context.Context, d time.Duration) bool {
	t := time.NewTimer(d)
	defer t.Stop()
	select {
	case <-ctx.Done():
		return false
	case <-t.C:
		return true
	}
}
func (s *Service) observe(ctx context.Context) {
	backoff := time.Second
	for ctx.Err() == nil {
		started := time.Now()
		err := s.session(ctx)
		if ctx.Err() != nil {
			return
		}
		if err != nil {
			log.Print("Chronik notification session interrupted; retrying")
		}
		if time.Since(started) > time.Minute {
			backoff = time.Second
		}
		if !pause(ctx, backoff+time.Duration(rand.Int64N(int64(backoff)/2+1))) {
			return
		}
		backoff = min(backoff*2, time.Minute)
	}
}
func (s *Service) session(ctx context.Context) error {
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	endpoint := strings.Replace(strings.Replace(s.URL, "https://", "wss://", 1), "http://", "ws://", 1) + "/ws"
	dialCtx, stop := context.WithTimeout(ctx, 15*time.Second)
	conn, _, err := websocket.Dial(dialCtx, endpoint, nil)
	stop()
	if err != nil {
		return err
	}
	defer conn.CloseNow()
	conn.SetReadLimit(64 * 1024)
	type frame struct {
		body []byte
		err  error
	}
	incoming := make(chan frame, 1)
	done := make(chan struct{})
	go func() {
		defer close(done)
		for {
			kind, body, err := conn.Read(ctx)
			if err == nil && kind != websocket.MessageBinary {
				err = errors.New("nonbinary Chronik message")
			}
			select {
			case incoming <- frame{body, err}:
			case <-ctx.Done():
				return
			}
			if err != nil {
				return
			}
		}
	}()
	// Cancel before joining the reader on every exit.
	defer func() { cancel(); _ = conn.CloseNow(); <-done }()
	current := map[string]Registration{}
	var regs []Registration
	reconcile := func() error {
		fresh, err := s.Store.Registrations(ctx)
		if err != nil {
			return err
		}
		desired := map[string]Registration{}
		for _, r := range fresh {
			kind, payload := subscription(r.Script)
			desired[kind+":"+string(payload)] = r
		}
		send := func(r Registration, unsub bool) error {
			kind, payload := subscription(r.Script)
			body, err := proto.Marshal(&pb.WsSub{IsUnsub: unsub, SubType: &pb.WsSub_Script{Script: &pb.WsSubScript{ScriptType: kind, Payload: payload}}})
			if err != nil {
				return err
			}
			writeCtx, stop := context.WithTimeout(ctx, 10*time.Second)
			defer stop()
			return conn.Write(writeCtx, websocket.MessageBinary, body)
		}
		for key, r := range current {
			if _, ok := desired[key]; !ok {
				if err := send(r, true); err != nil {
					return err
				}
			}
		}
		for key, r := range desired {
			if _, ok := current[key]; !ok {
				if err := send(r, false); err != nil {
					return err
				}
			}
		}
		regs = fresh
		current = desired
		return nil
	}
	if err := reconcile(); err != nil {
		return err
	}
	poll := time.NewTicker(5 * time.Second)
	defer poll.Stop()
	heartbeat := time.NewTicker(30 * time.Second)
	defer heartbeat.Stop()
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-s.wake:
			if err := reconcile(); err != nil {
				return err
			}
		case <-poll.C:
			if err := reconcile(); err != nil {
				return err
			}
		case <-heartbeat.C:
			pingCtx, stop := context.WithTimeout(ctx, 10*time.Second)
			err := conn.Ping(pingCtx)
			stop()
			if err != nil {
				return err
			}
		case frame := <-incoming:
			if frame.err != nil {
				return frame.err
			}
			var msg pb.WsMsg
			if err := proto.Unmarshal(frame.body, &msg); err != nil {
				return err
			}
			if msg.GetError() != nil {
				return errors.New("Chronik rejected subscription")
			}
			event := msg.GetTx()
			if event == nil {
				continue
			}
			if event.MsgType != pb.TxMsgType_TX_ADDED_TO_MEMPOOL && event.MsgType != pb.TxMsgType_TX_CONFIRMED {
				continue
			}
			if len(event.Txid) != 32 {
				return errors.New("invalid Chronik txid")
			}
			txid := append([]byte(nil), event.Txid...)
			for i, j := 0, len(txid)-1; i < j; i, j = i+1, j-1 {
				txid[i], txid[j] = txid[j], txid[i]
			}
			id := hex.EncodeToString(txid)
			if err := s.activity(ctx, regs, id); err != nil {
				return err
			}
		}
	}
}
func (s *Service) activity(ctx context.Context, regs []Registration, id string) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, s.URL+"/tx/"+id, nil)
	if err != nil {
		return err
	}
	resp, err := s.HTTP.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return errors.New("Chronik transaction lookup failed")
	}
	body, err := io.ReadAll(io.LimitReader(resp.Body, 8*1024*1024+1))
	if err != nil {
		return err
	}
	if len(body) > 8*1024*1024 {
		return errors.New("Chronik transaction exceeds limit")
	}
	var tx pb.Tx
	if err := proto.Unmarshal(body, &tx); err != nil {
		return err
	}
	// Index once; matching cost stays linear in transaction scripts plus registrations.
	affected := make(map[string]struct{}, len(tx.Inputs)+len(tx.Outputs))
	for _, in := range tx.Inputs {
		affected[string(in.OutputScript)] = struct{}{}
	}
	for _, out := range tx.Outputs {
		affected[string(out.OutputScript)] = struct{}{}
	}
	var targets []Registration
	for _, r := range regs {
		if _, ok := affected[string(r.Script)]; ok {
			targets = append(targets, r)
		}
	}
	return s.Store.Enqueue(ctx, targets, id)
}
func (s *Service) deliver(ctx context.Context) {
	for ctx.Err() == nil {
		attemptCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
		d, err := s.Store.Next(attemptCtx)
		if err == nil && d != nil {
			permanent, sendErr := s.Provider.Send(attemptCtx, *d)
			err = s.Store.Finish(attemptCtx, *d, sendErr == nil, permanent)
		}
		cancel()
		if err != nil {
			log.Print("notification outbox operation failed; retrying")
		}
		if d == nil || err != nil {
			if !pause(ctx, time.Second) {
				return
			}
		}
	}
}
