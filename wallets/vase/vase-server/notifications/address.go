package notifications

import (
	"bytes"
	"crypto/sha256"
	"errors"
	"math/big"
	"strings"
)

// Script decodes mainnet XAddresses, including the historical length-prefixed checksum.
// XAddress payloads contain the complete locking script, not a public-key hash.
func Script(address string) ([]byte, error) {
	const alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
	bad := errors.New("invalid mainnet Lotus XAddress")
	if !strings.HasPrefix(address, "lotus_") || len(address) > 200 {
		return nil, bad
	}
	encoded := address[6:]
	n := new(big.Int)
	for _, r := range encoded {
		i := strings.IndexRune(alphabet, r)
		if i < 0 {
			return nil, bad
		}
		n.Mul(n, big.NewInt(58))
		n.Add(n, big.NewInt(int64(i)))
	}
	raw := n.Bytes()
	for _, r := range encoded {
		if r != '1' {
			break
		}
		raw = append([]byte{0}, raw...)
	}
	if len(raw) < 6 || raw[0] != 0 {
		return nil, bad
	}
	payload := raw[1 : len(raw)-4]
	check := raw[len(raw)-4:]
	modern := sha256.Sum256(append([]byte("lotus_\x00"), payload...))
	legacy := sha256.Sum256(append([]byte{5, 'l', 'o', 't', 'u', 's', '_', 0, byte(len(payload))}, payload...))
	if !bytes.Equal(check, modern[:4]) && !bytes.Equal(check, legacy[:4]) {
		return nil, bad
	}
	return payload, nil
}

func subscription(script []byte) (string, []byte) {
	if len(script) == 25 && bytes.Equal(script[:3], []byte{0x76, 0xa9, 0x14}) && bytes.Equal(script[23:], []byte{0x88, 0xac}) {
		return "p2pkh", script[3:23]
	}
	if len(script) == 23 && script[0] == 0xa9 && script[1] == 0x14 && script[22] == 0x87 {
		return "p2sh", script[2:22]
	}
	if (len(script) == 35 && script[0] == 0x21 || len(script) == 67 && script[0] == 0x41) && script[len(script)-1] == 0xac {
		return "p2pk", script[1 : len(script)-1]
	}
	if (len(script) == 36 || len(script) == 69 && script[36] == 0x20) && bytes.Equal(script[:3], []byte{0x62, 0x51, 0x21}) {
		return "p2tr", script[3:36]
	}
	return "other", script
}
