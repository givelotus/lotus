"""Independent controller tests with purpose-built local fake processes.

These children exercise process/FD/socketpair transport only. They are neither
nodes nor wallets and provide no consensus, cryptographic or SQLite evidence.
Run discovery with LOTUS_V2_CONTROLLER_SOURCE pointing to the independently
owned controller.py until root integrates it. Failure fixtures are preserved.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve()
LIMITS = {
    "deadline_ms": 2000,
    "max_line_bytes": 32768,
    "max_wallet_bytes": 32768,
    "max_events": 3,
    "max_blocks": 4,
    "max_batches": 8,
}
TXID = "11" * 32
TXHASH = "22" * 32


def load_controller():
    source = Path(
        os.environ.get(
            "LOTUS_V2_CONTROLLER_SOURCE", HERE.parent.parent / "controller.py"
        )
    )
    spec = importlib.util.spec_from_file_location(
        "lotus_v2_devnet_controller_under_test", source
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def record(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a") as stream:
        stream.write(json.dumps(value, separators=(",", ":")) + "\n")


def emit(value):
    sys.stdout.buffer.write(json.dumps(value, separators=(",", ":")).encode() + b"\n")
    sys.stdout.buffer.flush()


def fake_node(mode, report):
    """No listener: readiness endpoints are inert fake metadata."""
    ready = {
        "event": "ready",
        "listen": {"address": "127.0.0.1", "port": 42001},
        "chain_id": "00" * 32,
        "genesis_id": "33" * 32,
        "profile_digest": "44" * 32,
    }
    record(
        report,
        {
            "kind": "node-start",
            "pid": os.getpid(),
            "argv": sys.argv,
            "env_secret_marker": any(
                "controller-fake-secret" in v or "private-test-passphrase" in v
                for v in os.environ.values()
            ),
        },
    )
    if mode == "no-ready":
        time.sleep(30)
        return
    ready.update(tip_known=True, reopen_required=False)
    if len(sys.argv) >= 8:
        home = Path(sys.argv[-2])
        # Native node startup supports reopening an existing home; the controller
        # decides whether a fresh launch or explicit resume may use it.
        home.mkdir(mode=0o700, parents=False, exist_ok=True)
        ready["listen"]["port"] += int(home.name.endswith("right"))
    emit(ready)
    if mode == "duplicate-ready":
        emit(ready)
    if mode == "ignore-stop":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    for line in sys.stdin.buffer:
        request = json.loads(line)
        record(report, {"kind": "node-request", "request": request})
        ident = request["id"]
        if request["command"] == "stop" and mode != "ignore-stop":
            emit({"id": ident, "ok": True})
            return
        if mode in ("silent", "ignore-stop"):
            continue
        if mode == "trickle":
            for byte in b'{"unfinished":':
                os.write(1, bytes([byte]))
                time.sleep(0.01)
            continue
        if mode == "oversized":
            os.write(1, b"x" * (LIMITS["max_line_bytes"] + 1))
            continue
        if mode == "duplicate-key":
            os.write(
                1,
                (
                    '{"id":%s,"id":%s,"ok":true}\n'
                    % (json.dumps(ident), json.dumps(ident))
                ).encode(),
            )
            continue
        if mode == "bool-id":
            emit({"id": True, "ok": True})
            continue
        if mode == "wrong-ok":
            emit({"id": ident, "ok": "true"})
            continue
        if mode == "non-object":
            emit([ident])
            continue
        if mode == "truncated":
            os.write(1, b'{"id":')
            return
        if mode == "nonfinite":
            os.write(
                1, ('{"id":%s,"ok":true,"value":NaN}\n' % json.dumps(ident)).encode()
            )
            continue
        if mode.startswith("response-cap-") and request["command"] == "walletcontext":
            response = {"id": "walletcontext-1", "ok": True, "padding": ""}
            size = int(mode.rsplit("-", 1)[1])
            response["padding"] = "x" * (
                size - 1 - len(json.dumps(response, separators=(",", ":")))
            )
            response["id"] = ident
            emit(response)
            continue
        if mode == "late-ids":
            emit({"id": "not-this-request", "ok": True, "unexpected": True})
        for height in range(5):
            emit(
                {
                    "event": "tip",
                    "height": height,
                    "tip": "%064x" % height,
                    "ignored_payload": "not retained",
                }
            )
        response = {
            "id": ident,
            "ok": True,
            "command": request["command"],
            "echo": request,
        }
        if request["command"] == "status":
            response.update(
                tip_known=True,
                reopen_required=False,
                tip="66" * 32,
                pending_journal=False,
                pending_receipt=False,
                pending_propagation=False,
                execution_paused=False,
            )
        if request["command"] == "walletcontext":
            response["context"] = {
                "fixture": "fake-transport-only",
                "tip": request.get("tip"),
                "outpoint": request.get("outpoint"),
            }
        emit(response)
        if mode == "late-ids":
            emit(response)  # duplicate stale response must never match a new id
    if mode == "ignore-stop":
        while True:
            time.sleep(1)


def read_line(sock, cap=32768):
    data = bytearray()
    while b"\n" not in data:
        chunk = sock.recv(min(4096, cap + 1 - len(data)))
        if not chunk or len(data) >= cap:
            raise RuntimeError("fake helper response framing")
        data.extend(chunk)
    line, _, tail = data.partition(b"\n")
    if tail:
        raise RuntimeError("fake helper extra response frame")
    return json.loads(line)


def fake_wallet(mode, report, native_argv):
    """Implements only the native CLI transport shape, never wallet semantics."""
    command = native_argv[2]
    flags = {
        value.split("=", 1)[0]: value.split("=", 1)[1] for value in native_argv[3:]
    }
    public_raw = sys.stdin.buffer.read()
    public = json.loads(public_raw)
    secret = b""
    if "--passphrase-fd" in flags:
        fd = int(flags["--passphrase-fd"])
        while True:
            chunk = os.read(fd, 4097 - len(secret))
            if not chunk:
                break
            secret += chunk
            if len(secret) > 4096:
                raise RuntimeError("fake secret cap")
        os.close(fd)
    record(
        report,
        {
            "kind": "wallet-start",
            "pid": os.getpid(),
            "argv": native_argv,
            "env_secret_marker": any(
                "controller-fake-secret" in v or "private-test-passphrase" in v
                for v in os.environ.values()
            ),
            "command": command,
            "public": public,
            "secret_len": len(secret),
            "secret_sha256": hashlib.sha256(secret).hexdigest(),
        },
    )
    home = Path(native_argv[1])
    pending_path = home / "fake-pending.json"
    if (
        mode
        in (
            "lost-sign",
            "sign-close-stdout",
            "sign-timeout",
            "sign-setup",
            "sign-interrupt",
        )
        and command in ("sign", "pay")
    ):
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(pending_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump({"txid": TXID, "txhash": TXHASH, "wire": "010203"}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        record(
            report, {"kind": "durable-export-fixture", "txid": TXID, "wire": "010203"}
        )
        if mode == "sign-interrupt":
            # Signal only the direct parent that created this isolated fake.
            parent_pid = os.getppid()
            if parent_pid <= 1:
                raise RuntimeError("fake parent vanished")
            os.kill(parent_pid, signal.SIGINT)
            time.sleep(30)
            return 9
        if mode == "sign-setup":
            emit({"result": "setup_error"})
            return 1
        if mode == "sign-close-stdout":
            os.close(1)
            time.sleep(30)
            return 9
        if mode == "sign-timeout":
            time.sleep(30)
            return 9
        return 9  # no stdout: controller must report OutcomeUnknown, no retry
    if mode == "pay-accepted" and command in ("sign", "pay"):
        value = {"txid": TXID, "txhash": TXHASH, "wire": "010203", "digest": "33" * 32}
        pending_path.write_text(json.dumps(value))
        emit({"result": "success", "submission": "accepted", **value})
        return 0
    if mode == "pay-inconclusive" and command == "pay":
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        value = {"txid": TXID, "txhash": TXHASH, "wire": "010203", "digest": "33" * 32}
        pending_path.write_text(json.dumps(value))
        emit({"result": "inconclusive", "error": "submission response lost", **value})
        return 2
    if mode == "silent":
        time.sleep(30)
        return 9
    if mode == "pay-inconclusive" and command in ("status", "broadcast"):
        value = json.loads(pending_path.read_text())
        emit({"result": "success", "txid": value["txid"], "txhash": value["txhash"],
              **({"state": "unknown"} if command == "status" else {"submission": "accepted", "missing": []})})
        return 0
    channel = socket.socket(fileno=int(flags["--node-fd"]))
    channel.settimeout(2)
    if mode in ("route", "lost-sign") and command not in ("pending", "export"):
        for n, outpoint in enumerate((None, {"txid": TXID, "index": 7}), 1):
            request = {
                "id": "walletcontext-" + str(n),
                "command": "walletcontext",
                "tip": None,
                "outpoint": outpoint,
            }
            if command == "broadcast":
                request = {"id": "wallettransaction-" + str(n),
                           "command": "submittransaction", "wire": "ab",
                           "expected_tip": TXID}
            elif command == "status":
                request = {"id": "wallettransaction-" + str(n),
                           "command": "transactionstatus", "txid": TXID,
                           "txhash": TXHASH, "wire": "ab"}
            channel.sendall(json.dumps(request, separators=(",", ":")).encode() + b"\n")
            response = read_line(channel)
            if (
                response.get("id") != request["id"]
                or response.get("ok") is not True
                or "event" in response
            ):
                raise RuntimeError("fake private ID/event routing")
            record(
                report,
                {"kind": "wallet-context", "request": request, "response": response},
            )
    elif mode.startswith("private-"):
        request = {
            "id": "walletcontext-1",
            "command": "walletcontext",
            "tip": None,
            "outpoint": None,
        }
        raw = json.dumps(request).encode() + b"\n"
        if mode == "private-bool-id":
            request["id"] = True
            raw = json.dumps(request).encode() + b"\n"
        if mode == "private-command":
            request["command"] = "sign"
            raw = json.dumps(request).encode() + b"\n"
        if mode == "private-extra":
            request["secret"] = "not a secret"
            raw = json.dumps(request).encode() + b"\n"
        if mode == "private-truncated":
            raw = raw[:-1]
        if mode == "private-oversized":
            raw = b"x" * (LIMITS["max_line_bytes"] + 1)
        if mode == "private-coalesced":
            raw += raw
        if mode.startswith("private-cap-"):
            target = int(mode.rsplit("-", 1)[1])
            raw = json.dumps(request, separators=(",", ":")).encode()
            raw += b" " * (target - len(raw) - 1) + b"\n"
        if mode == "private-exact-no-newline":
            raw = b"x" * LIMITS["max_line_bytes"]
        channel.sendall(raw)
        if mode == "private-truncated":
            channel.shutdown(socket.SHUT_WR)
        response = read_line(channel)
        if mode == "private-cap-1024":
            record(
                report,
                {"kind": "private-boundary", "size": len(raw), "response": response},
            )
        else:
            raise RuntimeError("malformed private input unexpectedly serviced")
    channel.close()
    if command == "pending":
        emit(
            {
                "result": "success",
                "pending": (
                    [json.loads(pending_path.read_text())["txid"]]
                    if pending_path.exists()
                    else []
                ),
            }
        )
    elif command == "export":
        exported = json.loads(pending_path.read_text())
        emit({"result": "success", **exported})
    elif mode == "public-oversized":
        os.write(1, b"x" * (LIMITS["max_wallet_bytes"] + 1))
    elif mode == "public-duplicate":
        os.write(1, b'{"result":"success","result":"success"}')
    elif mode == "public-extra-document":
        os.write(1, b'{"result":"success"}{}')
    else:
        if command == "create":
            home.mkdir(mode=0o700, parents=True, exist_ok=False)
        emit(
            {
                "result": "success",
                "transport_fixture": True,
                "public_key": "55" * 32,
                "payment_policy_registered": True,
                "payment_output_hex": "00",
                "payment_output": {
                    "value": "0",
                    "flags": 0,
                    "branches": ["88" * 32],
                    "paths": [[0]],
                },
                "coins": [],
            }
        )
    return 0


class ControllerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load_controller()

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="lotus-v2-controller-test-")).resolve()
        self.report = self.root / "public-report.jsonl"
        self.nodes = []

    def tearDown(self):
        for node in reversed(self.nodes):
            node.stop(time.monotonic() + 0.1)
        result = self._outcome.result
        failed = any(
            case is self or getattr(case, "test_case", None) is self
            for case, _ in result.failures + result.errors
        )
        if failed:
            print("preserved fake-process fixture:", self.root, file=sys.stderr)
        else:
            shutil.rmtree(self.root)

    def node(self, mode="normal"):
        node = self.api.NodeProcess(
            "fixture",
            [sys.executable, "-u", str(HERE), "--fake-node", mode, str(self.report)],
            dict(LIMITS),
        )
        self.nodes.append(node)
        node.start()
        node.wait_ready(time.monotonic() + 2)
        return node

    def events(self):
        return (
            [json.loads(line) for line in self.report.read_text().splitlines()]
            if self.report.exists()
            else []
        )

    def wallet(self, node, mode="route"):
        executable = self.root / ("wallet-" + mode)
        executable.write_text(
            "#!"
            + sys.executable
            + "\nimport runpy,sys\nsys.argv="
            + repr([str(HERE), "--fake-wallet", mode, str(self.report)])
            + "+sys.argv[1:]\nrunpy.run_path("
            + repr(str(HERE))
            + ",run_name='__main__')\n"
        )
        executable.chmod(0o700)
        return self.api.WalletProcess(
            executable,
            self.root / "public-manifest.json",
            self.root / "wallet-home",
            node,
            dict(LIMITS),
        )


class NodeTransportTests(ControllerCase):
    def test_unique_ids_and_interleaved_bounded_events(self):
        node = self.node("late-ids")
        first = node.request(
            {"command": "status", "id": "caller-chosen"}, time.monotonic() + 1
        )
        second = node.request({"command": "status"}, time.monotonic() + 1)
        self.assertNotEqual(first["id"], "caller-chosen")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(second["echo"]["id"], second["id"])
        self.assertEqual(len(node.events), LIMITS["max_events"])
        self.assertTrue(all("ignored_payload" not in event for event in node.events))

    def test_malformed_frames_and_typed_responses_fail(self):
        for mode in (
            "oversized",
            "duplicate-key",
            "bool-id",
            "wrong-ok",
            "non-object",
            "truncated",
            "nonfinite",
        ):
            with self.subTest(mode=mode):
                node = self.node(mode)
                with self.assertRaises(self.api.ControllerError):
                    node.request({"command": "status"}, time.monotonic() + 0.3)
                node.stop(time.monotonic() + 0.05)
                self.assertIsNotNone(node.process.poll())

    def test_absolute_deadline_does_not_extend_for_trickle(self):
        node = self.node("trickle")
        started = time.monotonic()
        with self.assertRaises(self.api.ControllerError) as error:
            node.request({"command": "status"}, started + 0.04)
        self.assertEqual(error.exception.code, "timeout")
        self.assertLess(time.monotonic() - started, 1.0)

    def test_outbound_capacity_refuses_before_child_receives(self):
        node = self.node()
        with self.assertRaises(self.api.ControllerError) as error:
            node.request(
                {"command": "status", "body": "x" * LIMITS["max_line_bytes"]},
                time.monotonic() + 1,
            )
        self.assertEqual(error.exception.code, "capacity_refused")
        self.assertFalse(any(item["kind"] == "node-request" for item in self.events()))

    def test_stop_reaps_noncooperative_process_and_closes_streams(self):
        node = self.node("ignore-stop")
        process = node.process
        started = time.monotonic()
        node.stop(started + 0.03)
        self.assertLess(time.monotonic() - started, 2)
        self.assertIsNotNone(process.poll())
        self.assertTrue(
            all(
                stream.closed
                for stream in (process.stdin, process.stdout, process.stderr)
            )
        )
        node.stop(time.monotonic() + 0.03)

    def test_readiness_deadline_and_duplicate_ready(self):
        node = self.api.NodeProcess(
            "no-ready",
            [
                sys.executable,
                "-u",
                str(HERE),
                "--fake-node",
                "no-ready",
                str(self.report),
            ],
            dict(LIMITS),
        )
        self.nodes.append(node)
        node.start()
        with self.assertRaises(self.api.ControllerError) as error:
            node.wait_ready(time.monotonic() + 0.1)
        self.assertEqual(error.exception.code, "timeout")
        with self.assertRaises(self.api.ControllerError) as error:
            duplicate = self.node("duplicate-ready")
            duplicate.request({"command": "status"}, time.monotonic() + 1)
        self.assertEqual(error.exception.code, "protocol_error")

    def test_stop_baseexception_still_reaps_and_closes(self):
        for exception in (KeyboardInterrupt, SystemExit):
            with self.subTest(exception=exception.__name__):
                node = self.node("ignore-stop")
                process = node.process
                with mock.patch.object(node, "request", side_effect=exception):
                    with self.assertRaises(exception):
                        node.stop(time.monotonic() + 0.1)
                self.assertIsNotNone(process.poll())
                self.assertTrue(
                    all(
                        stream.closed
                        for stream in (process.stdin, process.stdout, process.stderr)
                    )
                )


class WalletTransportTests(ControllerCase):
    def test_socketpair_id_rewrite_event_filter_and_secret_fd(self):
        node = self.node("late-ids")
        wallet = self.wallet(node)
        secret = bytearray(b"controller-fake-secret\x00with-newline\n")
        expected = hashlib.sha256(secret).hexdigest()
        expected_len = len(secret)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = wallet.invoke(
                "create", {"public": "request"}, secret, time.monotonic() + 2
            )
        self.assertEqual(result["result"], "success")
        self.assertFalse(any(secret))
        records = self.events()
        child = next(item for item in records if item["kind"] == "wallet-start")
        self.assertEqual(child["secret_sha256"], expected)
        self.assertEqual(child["secret_len"], expected_len)
        self.assertFalse(child["env_secret_marker"])
        self.assertEqual(child["public"], {"public": "request"})
        private = [item for item in records if item["kind"] == "wallet-context"]
        self.assertEqual(len(private), 2)
        for item in private:
            self.assertEqual(item["request"]["id"], item["response"]["id"])
            self.assertNotIn("event", item["response"])
            self.assertNotEqual(item["request"]["id"], item["response"]["echo"]["id"])
        marker = b"controller-fake-secret"
        self.assertNotIn(marker, self.report.read_bytes())
        self.assertNotIn(marker.decode(), captured.getvalue())

    def test_private_transaction_provider_routing(self):
        node = self.node("normal")
        wallet = self.wallet(node, "route")
        for command in ("broadcast", "status"):
            result = wallet.invoke(command, {"txid": TXID})
            self.assertEqual(result["result"], "success")
        routed = [item["request"]["command"] for item in self.events()
                  if item["kind"] == "node-request"]
        self.assertEqual(routed, ["submittransaction", "submittransaction",
                                  "transactionstatus", "transactionstatus"])

    def test_private_and_public_frame_failures(self):
        node = self.node()
        for mode in (
            "private-bool-id",
            "private-command",
            "private-extra",
            "private-truncated",
            "private-oversized",
            "private-coalesced",
            "public-oversized",
            "public-duplicate",
            "public-extra-document",
        ):
            with self.subTest(mode=mode):
                wallet = self.wallet(node, mode)
                with self.assertRaises(self.api.ControllerError) as error:
                    wallet.invoke("info", {}, None, time.monotonic() + 2)
                self.assertNotEqual(
                    error.exception.code,
                    "timeout",
                    "must actually reach malformed-frame gate",
                )

    def test_post_persist_sign_faults_are_unknown_and_recover_without_resigning(self):
        node = self.node()
        for mode in ("lost-sign", "sign-close-stdout", "sign-timeout", "sign-setup"):
            with self.subTest(mode=mode):
                wallet = self.wallet(node, mode)
                wallet.home = str(self.root / ("home-" + mode))
                secret = bytearray(b"private-test-passphrase")
                before = len(self.events())
                with self.assertRaises(self.api.ControllerError) as error:
                    wallet.invoke(
                        "sign",
                        {"plan": "fake-public-plan"},
                        secret,
                        time.monotonic() + 2,
                    )
                self.assertEqual(error.exception.code, "outcome_unknown")
                self.assertFalse(any(secret))
                records = self.events()[before:]
                self.assertEqual(
                    [x["command"] for x in records if x["kind"] == "wallet-start"],
                    ["sign"],
                )
                self.assertTrue((Path(wallet.home) / "fake-pending.json").is_file())
                # A new wrapper/child reopens persisted fake state, proving the
                # controller recovers bytes without trusting lost sign stdout.
                reopened = self.api.WalletProcess(
                    wallet.executable, wallet.manifest, wallet.home, node, dict(LIMITS)
                )
                pending = reopened.invoke("pending", {}, None, time.monotonic() + 1)
                exported = reopened.invoke(
                    "export",
                    {"txid": TXID, "max_bytes": 1024},
                    None,
                    time.monotonic() + 1,
                )
                self.assertEqual(pending["pending"], [TXID])
                self.assertEqual(
                    (exported["wire"], exported["txid"], exported["txhash"]),
                    ("010203", TXID, TXHASH),
                )
                self.assertEqual(
                    [
                        x["command"]
                        for x in self.events()[before:]
                        if x["kind"] == "wallet-start"
                    ],
                    ["sign", "pending", "export"],
                )

    def test_private_frame_exact_limits_include_newline(self):
        node = self.node()
        wallet = self.wallet(node, "private-cap-1024")
        self.assertEqual(
            wallet.invoke("info", {}, None, time.monotonic() + 2)["result"], "success"
        )
        self.assertEqual(
            next(x for x in self.events() if x["kind"] == "private-boundary")["size"],
            1024,
        )
        for mode in ("private-cap-1025", "private-exact-no-newline"):
            with self.subTest(mode=mode):
                with self.assertRaises(self.api.ControllerError) as error:
                    self.wallet(node, mode).invoke(
                        "info", {}, None, time.monotonic() + 2
                    )
                self.assertEqual(error.exception.code, "protocol_error")

    def test_private_response_exact_limits_include_newline(self):
        for size in (32768, 32769):
            with self.subTest(size=size):
                node = self.node("response-cap-" + str(size))
                node.limits["max_line_bytes"] = 65536
                wallet = self.wallet(node, "private-cap-1024")
                if size == 32768:
                    self.assertEqual(
                        wallet.invoke("info", {}, None, time.monotonic() + 2)["result"],
                        "success",
                    )
                else:
                    with self.assertRaises(self.api.ControllerError) as error:
                        wallet.invoke("info", {}, None, time.monotonic() + 2)
                    self.assertEqual(error.exception.code, "capacity_refused")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--fake-node":
        fake_node(sys.argv[2], sys.argv[3])
    elif len(sys.argv) > 1 and sys.argv[1] == "--fake-wallet":
        raise SystemExit(fake_wallet(sys.argv[2], sys.argv[3], sys.argv[4:]))
    else:
        unittest.main()
