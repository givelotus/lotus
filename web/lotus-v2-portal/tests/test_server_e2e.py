#!/usr/bin/env python3
"""
Python Unit & Integration Tests for `web/lotus-v2-portal/server.py`
"""

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import server  # noqa: E402


class TestLotusV2PortalServer(unittest.TestCase):
    def test_p04_vectors_in_python_blake3(self) -> None:
        chain_id = bytes(range(32))
        header = bytes.fromhex(
            "202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f"
            "ffff001d0605040302010f0e0d0c0b0a0908020000008877665544332211"
            "00ffeeddccbbaa99404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f"
            "606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f"
        )
        body_hash, work_hash, block_id = server.lotus_v2_hashes(header, chain_id)
        self.assertEqual(
            body_hash.hex(),
            "1704e11edcbc47eb829d210ac1affb606dd4021c82305e07a028962456efec3d",
        )
        self.assertEqual(
            work_hash.hex(),
            "56c49269bcb4709b42d48312a382badc0906162e5bd6e49aac48a7096288ffd1",
        )
        self.assertEqual(
            block_id.hex(),
            "fbe9243579627fc3a41043c80395d33a8a01b91a9b86b6c6e629530595c83370",
        )

    def test_forbidden_ports_rejected(self) -> None:
        for port in (10604, 10605, 8331):
            with self.assertRaises(ValueError):
                server.create_server("127.0.0.1", port)

    def test_http_sse_and_invalid_share_rejection(self) -> None:
        httpd = server.create_server("127.0.0.1", 37225)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base_url = "http://127.0.0.1:37225"
        try:
            # 1. Fetch SSE job
            with urllib.request.urlopen(f"{base_url}/pool/jobs?worker=sub:py@lotus.org&once=1") as resp:
                self.assertEqual(resp.status, 200)
                text = resp.read().decode("utf-8")
                self.assertIn("event: job", text)
                data_line = [ln for ln in text.splitlines() if ln.startswith("data:")][0]
                job = json.loads(data_line[5:].strip())
                self.assertEqual(job["protocol"], "v2")

            # 2. Submit a valid share by finding a nonce meeting target
            header = bytearray.fromhex(job["header"])
            chain_id = bytes.fromhex(job["chain_id"])
            target = bytes.fromhex(job["target"])
            winning_nonce = None
            for nonce in range(10000):
                header[42:50] = nonce.to_bytes(8, "little")
                _, _, bid = server.lotus_v2_hashes(bytes(header), chain_id)
                if server.meets_target(bid, target):
                    winning_nonce = nonce
                    break
            self.assertIsNotNone(winning_nonce)

            req = urllib.request.Request(
                f"{base_url}/pool/submit",
                data=json.dumps(
                    {
                        "protocol": "v2",
                        "job_id": job["job_id"],
                        "worker": "sub:py@lotus.org",
                        "nonce": winning_nonce,
                        "header": bytes(header).hex(),
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                body = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(body["accepted"])
                self.assertTrue(body["subscription_unlocked"])
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
