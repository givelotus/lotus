"""Controller command integration and explicitly gated real two-node acceptance.

Default tests use transport-only fake executables, no TCP listeners/SQLite/VM.
Real acceptance runs only with LOTUS_V2_APPROVED_INTERACTIVE pointing to a
root-approved JSON specification containing config, preserved evidence path,
exact daemon/wallet/manifest SHA256s and public command parameters. Secrets
are generated in memory and passed only through the controller's private FD.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
import unittest
from unittest import mock

from test_controller import (
    ControllerCase,
    HERE,
    LIMITS,
    TXID,
    TXHASH,
    load_controller,
    record,
)


def pinned(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def executable(path, body):
    path.write_text("#!" + sys.executable + "\n" + body)
    path.chmod(0o700)
    return path


class CommandFlowTests(ControllerCase):
    def make_controller(self, wallet_mode="route", secret_prompt=None):
        daemon = executable(
            self.root / "fake-daemon",
            "import runpy,sys\nsys.argv="
            + repr([str(HERE), "--fake-node", "normal", str(self.report)])
            + "+sys.argv[1:]\nrunpy.run_path("
            + repr(str(HERE))
            + ",run_name='__main__')\n",
        )
        wallet = executable(
            self.root / "fake-wallet",
            "import runpy,sys\nsys.argv="
            + repr([str(HERE), "--fake-wallet", wallet_mode, str(self.report)])
            + "+sys.argv[1:]\nrunpy.run_path("
            + repr(str(HERE))
            + ",run_name='__main__')\n",
        )
        compiler = self.root / "compiler"
        (compiler / "dist").mkdir(parents=True)
        (compiler / "examples/gallery").mkdir(parents=True)
        (compiler / "dist/generic.js").write_text("// inert fake compiler fixture\n")
        (compiler / "examples/gallery/payment.lotus").write_text(
            "// inert fake Payment fixture\n"
        )
        compiler_node = executable(
            self.root / "fake-compiler",
            'import json,sys\njson.load(sys.stdin)\nprint(json.dumps({"script":"4e","proof":[],"root":"'
            + "88" * 32
            + '"}))\n',
        )
        manifest = self.root / "fake-manifest.json"
        manifest.write_text('{"scope":"opaque fake transport fixture"}')
        network = self.root / "fake-network.json"
        network.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "magic": "11223344",
                    "listen": {"address": "127.0.0.1", "port": 0},
                    "connect": [],
                    "receive_limit": 4096,
                    "local_policy": "bounded-local-v1",
                }
            )
        )
        config = {
            "schema": 1,
            "daemon": pinned(daemon),
            "wallet_client": pinned(wallet),
            "manifest": pinned(manifest),
            "compiler": {"directory": str(compiler), "node": str(compiler_node)},
            "limits": dict(LIMITS),
            "nodes": [
                {
                    "name": name,
                    "home": "nodes/" + name,
                    "network": pinned(network),
                    "connect_to": [] if name == "left" else ["left"],
                }
                for name in ("left", "right")
            ],
        }
        config_path = self.root / "config.json"
        config_path.write_text(json.dumps(config))
        normalized = self.api.load_config(config_path)
        controller = self.api.Controller(
            normalized,
            self.root / "session",
            secret_prompt=secret_prompt
            or (lambda *_: bytearray(b"controller-fake-secret")),
        )
        controller.start()
        self.nodes.extend(controller.nodes.values())
        self.addCleanup(controller.close)
        return controller, config_path

    def test_explicit_manual_private_endpoints_validate(self):
        _, config_path = self.make_controller()
        config = json.loads(config_path.read_text())
        network_path = Path(config["nodes"][0]["network"]["path"])
        network = json.loads(network_path.read_text())
        network["listen"] = {"address": "0.0.0.0", "port": 29001}
        network["connect"] = [{"address": "192.0.2.10", "port": 29002},
                              {"address": "2001:db8::1", "port": 29003}]
        network_path.write_text(json.dumps(network))
        for node in config["nodes"]:
            node["network"] = pinned(network_path)
        config_path.write_text(json.dumps(config))
        normalized = self.api.load_config(config_path)
        self.assertEqual(normalized["nodes"][0]["resolved_network"], network)
        for bad in ({"address": "node.example", "port": 29002},
                    {"address": "0.0.0.0", "port": 29002},
                    {"address": "192.0.2.10", "port": 0}):
            with self.assertRaises((self.api.ControllerError, ValueError)):
                self.api.endpoint(bad)

    def create_wallets(self, controller):
        for name, node in (("alice", "left"), ("bob", "right")):
            answer = controller.execute("wallet create " + name + " --node " + node)
            self.assertTrue(answer["ok"], answer)

    def test_config_fresh_session_links_and_public_wallet_commands(self):
        controller, path = self.make_controller()
        self.create_wallets(controller)
        self.assertTrue(controller.execute("status")["ok"])
        network = json.loads((controller.session / "network/right.json").read_text())
        self.assertEqual(network["connect"], [controller.nodes["left"].ready["listen"]])
        for name in ("alice", "bob"):
            self.assertTrue(
                (controller.session / "public" / (name + "-payment.json")).is_file()
            )
            self.assertTrue(controller.execute("wallet reconcile " + name)["ok"])
        before = self.events()
        second = self.api.Controller(self.api.load_config(path), controller.session)
        with self.assertRaises((FileExistsError, self.api.ControllerError)):
            second.start()
        self.assertEqual(self.events(), before)
        self.assertFalse(second.nodes)
        for file in controller.session.rglob("*"):
            if file.is_file():
                self.assertNotIn(b"controller-fake-secret", file.read_bytes())
        self.assertFalse(any(x.get("env_secret_marker") for x in self.events()))

    def test_postpersist_pay_unknown_stops_then_explicit_recovery(self):
        controller, _ = self.make_controller("lost-sign")
        self.create_wallets(controller)
        before = len(self.events())
        answer = controller.execute(
            "pay alice --to bob --amount 10 --fee 1 --mine-to alice --claim 100 --time now --batches 1"
        )
        self.assertEqual(answer["result"], "outcome_unknown")
        note = json.loads(Path(answer["recovery_note"]).read_text())
        self.assertFalse(note["automatic_retry"])
        self.assertNotIn("txid", note)
        records = self.events()[before:]
        self.assertEqual(
            [x["command"] for x in records if x["kind"] == "wallet-start"],
            ["info", "pay"],
        )
        self.assertFalse(
            any(
                x["kind"] == "node-request" and x["request"]["command"] in ("mineblock", "minepool")
                for x in records
            )
        )
        self.assertEqual(
            controller.execute("wallet pending alice")["data"]["pending"], [TXID]
        )
        exported = controller.execute("wallet export alice " + TXID)
        self.assertTrue(exported["ok"], exported)
        self.assertEqual(exported["data"]["wire"], "010203")
        self.assertEqual(
            json.loads((controller.session / "public" / (TXID + ".json")).read_text())[
                "txhash"
            ],
            TXHASH,
        )
        self.assertEqual(
            [
                x["command"]
                for x in self.events()[before:]
                if x["kind"] == "wallet-start"
            ],
            ["info", "pay", "pending", "export"],
        )

    def test_interrupted_persisted_sign_note_and_recovery(self):
        controller, _ = self.make_controller("sign-interrupt")
        self.create_wallets(controller)
        before = len(self.events())
        with self.assertRaises(self.api.SigningInterrupted) as interrupted:
            controller.execute("wallet sign alice --to bob --amount 10 --fee 1")
        self.assertEqual(interrupted.exception.code, "outcome_unknown")
        note = json.loads(Path(interrupted.exception.recovery_note).read_text())
        self.assertEqual(note["wallet"], "alice")
        self.assertFalse(note["automatic_retry"])
        self.assertEqual(
            controller.execute("wallet pending alice")["data"]["pending"], [TXID]
        )
        self.assertTrue(controller.execute("wallet export alice " + TXID)["ok"])
        self.assertEqual(
            [
                x["command"]
                for x in self.events()[before:]
                if x["kind"] == "wallet-start"
            ],
            ["info", "sign", "pending", "export"],
        )
        pid = next(
            x["pid"]
            for x in self.events()[before:]
            if x["kind"] == "wallet-start" and x["command"] == "sign"
        )
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_close_continues_after_baseexception_and_allows_retry(self):
        controller, _ = self.make_controller()
        right, left = controller.nodes["right"], controller.nodes["left"]
        with mock.patch.object(right, "request", side_effect=KeyboardInterrupt):
            controller.close()
        self.assertEqual(
            controller.cleanup_errors, [{"node": "right", "error": "KeyboardInterrupt"}]
        )
        for node in (right, left):
            self.assertIsNotNone(node.process.poll())
            self.assertTrue(
                all(
                    s.closed
                    for s in (
                        node.process.stdin,
                        node.process.stdout,
                        node.process.stderr,
                    )
                )
            )
        controller.close()
        self.assertEqual(controller.cleanup_errors, [])

    def test_prompt_home_disappearance_wipes_secret_and_does_not_spawn(self):
        returned = []
        controller, _ = self.make_controller()
        self.create_wallets(controller)
        home = controller.session / "wallets/alice"

        def prompt(*_):
            home.rename(home.with_name("alice-original"))
            value = bytearray(b"private-test-passphrase")
            returned.append(value)
            return value

        controller.secret_prompt = prompt
        before = len(self.events())
        answer = controller.execute("wallet sign alice --to bob --amount 10 --fee 1")
        self.assertFalse(answer["ok"])
        self.assertFalse(any(returned[0]))
        self.assertEqual(
            [
                x["command"]
                for x in self.events()[before:]
                if x["kind"] == "wallet-start"
            ],
            ["info"],
        )
        controller.secret_prompt = lambda *_: self.fail(
            "must refuse missing home before prompting"
        )
        self.assertFalse(
            controller.execute("wallet sign alice --to bob --amount 10 --fee 1")["ok"]
        )

    def test_prompt_symlink_home_escape_is_refused(self):
        controller, _ = self.make_controller()
        self.create_wallets(controller)
        outside = self.root / "outside-home"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_bytes(b"unchanged")
        home = controller.session / "wallets/alice"
        returned = []

        def prompt(*_):
            home.rename(home.with_name("alice-original"))
            home.symlink_to(outside, target_is_directory=True)
            value = bytearray(b"private-test-passphrase")
            returned.append(value)
            return value

        controller.secret_prompt = prompt
        before = len(self.events())
        answer = controller.execute("wallet sign alice --to bob --amount 10 --fee 1")
        self.assertFalse(answer["ok"])
        self.assertFalse(any(returned[0]))
        self.assertEqual(
            [
                x["command"]
                for x in self.events()[before:]
                if x["kind"] == "wallet-start"
            ],
            ["info"],
        )
        self.assertEqual(sentinel.read_bytes(), b"unchanged")
        self.assertEqual(sorted(x.name for x in outside.iterdir()), ["sentinel"])


@unittest.skipUnless(
    os.environ.get("LOTUS_V2_APPROVED_INTERACTIVE"),
    "real nodes require explicit root-approved pinned specification",
)
class ApprovedNativeFlowTests(unittest.TestCase):
    def test_two_node_compiled_payment_and_restart(self):
        api = load_controller()
        spec_path = Path(os.environ["LOTUS_V2_APPROVED_INTERACTIVE"]).resolve()
        spec = json.loads(spec_path.read_text())
        self.assertIs(spec["approved"], True)
        self.assertEqual(
            set(spec),
            {
                "approved",
                "config",
                "pins",
                "evidence",
                "claim",
                "amount",
                "fee",
                "batches",
            },
        )
        config = api.load_config(spec["config"])
        for name in ("daemon", "wallet_client", "manifest"):
            self.assertEqual(config[name]["sha256"], spec["pins"][name])
            self.assertEqual(api.sha256_file(config[name]["path"]), spec["pins"][name])
        self.assertEqual([item["name"] for item in config["nodes"]], ["left", "right"])
        root = Path(spec["evidence"]).resolve()
        root.mkdir(mode=0o700, parents=False, exist_ok=False)
        report = root / "public-evidence.jsonl"
        secret = bytearray(secrets.token_urlsafe(48).encode("ascii"))
        issued = []

        def prompt(*_):
            value = bytearray(secret)
            issued.append(value)
            return value

        record(
            report,
            {
                "kind": "sources",
                "controller": pinned(Path(api.__file__)),
                "tests": [pinned(Path(__file__)), pinned(HERE)],
                "specification": pinned(spec_path),
                "config": pinned(Path(spec["config"])),
            },
        )
        controller = api.Controller(config, root / "session", secret_prompt=prompt)
        reopened = []
        native_request = api.NodeProcess.request
        popen = api.subprocess.Popen

        def request(node, payload, deadline):
            record(
                report, {"kind": "node-request", "node": node.name, "request": payload}
            )
            response = native_request(node, payload, deadline)
            record(
                report,
                {
                    "kind": "node-response",
                    "node": node.name,
                    "response": response,
                    "events": list(node.events),
                },
            )
            return response

        def launch(argv, *args, **kwargs):
            self.assertFalse(any(secret.decode() in str(value) for value in argv))
            self.assertFalse(
                any(secret.decode() in value for value in os.environ.values())
            )
            record(
                report,
                {
                    "kind": "process",
                    "argv": [str(value) for value in argv],
                    "pass_fds": list(kwargs.get("pass_fds", ())),
                },
            )
            return popen(argv, *args, **kwargs)

        def execute(line):
            response = controller.execute(line)
            record(report, {"kind": "controller", "line": line, "response": response})
            self.assertTrue(response["ok"], response)
            return response

        def synced(nodes, expected):
            deadline = time.monotonic() + config["limits"]["deadline_ms"] / 1000
            while True:
                values = [
                    node.request({"command": "status"}, deadline) for node in nodes
                ]
                if all(
                    value.get("tip") == expected
                    and value.get("tip_known") is True
                    and value.get("reopen_required") is False
                    and not any(
                        value.get(field)
                        for field in (
                            "pending_journal",
                            "pending_receipt",
                            "pending_propagation",
                            "execution_paused",
                        )
                    )
                    for value in values
                ):
                    return values
                self.assertGreater(deadline - time.monotonic(), 0, values)
                time.sleep(0.02)

        manifest = json.loads(Path(config["manifest"]["path"]).read_text())

        def next_time():
            status = controller.nodes["left"].request(
                {"command": "status"}, controller.deadline()
            )
            return (
                manifest["header"]["time"]
                + (status["height"] + 2) * manifest["header"]["spacing"]
            )

        try:
            with mock.patch.object(
                api.NodeProcess, "request", request
            ), mock.patch.object(api.subprocess, "Popen", launch):
                controller.start()
                for name, node in (("alice", "left"), ("bob", "right")):
                    execute("wallet create " + name + " --node " + node)
                owners = {
                    name: execute("wallet info " + name)["data"]["public_key"]
                    for name in ("alice", "bob")
                }
                self.assertNotEqual(owners["alice"], owners["bob"])
                execute(
                    "fund alice --claim "
                    + spec["claim"]
                    + " --time "
                    + str(next_time())
                    + " --batches "
                    + str(spec["batches"])
                )
                tip = controller.nodes["left"].request(
                    {"command": "status"}, controller.deadline()
                )["tip"]
                synced(list(controller.nodes.values()), tip)
                premature = controller.execute(
                    "wallet prepare alice --to bob --amount "
                    + spec["amount"]
                    + " --fee "
                    + spec["fee"]
                )
                record(
                    report, {"kind": "immature-payment-refusal", "response": premature}
                )
                self.assertFalse(premature["ok"], premature)
                self.assertEqual(premature["result"], "insufficient_funds", premature)
                self.assertEqual(execute("wallet pending alice")["data"]["pending"], [])
                mature = execute(
                    "mature alice --max-blocks "
                    + str(manifest["coinbase_maturity"] + 1)
                    + " --claim "
                    + spec["claim"]
                    + " --time "
                    + str(next_time())
                    + " --batches "
                    + str(spec["batches"])
                )
                self.assertEqual(mature["result"], "mature", mature)
                tip = controller.nodes["left"].request(
                    {"command": "status"}, controller.deadline()
                )["tip"]
                synced(list(controller.nodes.values()), tip)
                paid = execute(
                    "pay alice --to bob --amount "
                    + spec["amount"]
                    + " --fee "
                    + spec["fee"]
                    + " --mine-to alice --claim "
                    + spec["claim"]
                    + " --time "
                    + str(next_time())
                    + " --batches "
                    + str(spec["batches"])
                )
                signed = paid["signed"]
                tip = controller.nodes["left"].request(
                    {"command": "status"}, controller.deadline()
                )["tip"]
                synced(list(controller.nodes.values()), tip)
                receiver = execute("wallet reconcile bob")["data"]
                sender = execute("wallet reconcile alice")["data"]
                self.assertTrue(
                    any(
                        coin["prev_txid"] == signed["txid"]
                        and int(coin["prev_index"]) == 0
                        and coin.get("present") is True
                        and int(coin["value"]) == int(spec["amount"])
                        for coin in receiver["coins"]
                    ),
                    receiver,
                )
                spent = [
                    coin
                    for coin in sender["coins"]
                    if coin.get("present") is False and coin.get("reserved") is True
                ]
                self.assertEqual(len(spent), 1, sender)
                pending = execute("wallet pending alice")["data"]
                self.assertIsInstance(pending["pending"], list)
                exported = execute("wallet export alice " + signed["txid"])["data"]
                self.assertEqual(
                    tuple(exported[key] for key in ("wire", "txid", "txhash")),
                    tuple(signed[key] for key in ("wire", "txid", "txhash")),
                )
                before = execute("status")["nodes"]
                controller.close()
                self.assertFalse(controller.cleanup_errors)
                for node in controller.nodes.values():
                    self.assertIsNotNone(node.process.poll())
                # Reopen these newly owned homes only. New ephemeral listeners
                # and a new explicit link file replace stale endpoint metadata.
                for name in ("left", "right"):
                    previous = controller.nodes[name]
                    argv = list(previous.argv)
                    network = json.loads(Path(argv[-1]).read_text())
                    network["connect"] = (
                        [] if name == "left" else [reopened[0].ready["listen"]]
                    )
                    path = root / (name + "-restart-network.json")
                    api.Controller._write_new(path, api.encode_json(network) + b"\n")
                    argv[-1] = str(path)
                    node = api.NodeProcess(name + "-reopened", argv, config["limits"])
                    reopened.append(node)
                    node.start()
                    node.wait_ready(
                        time.monotonic() + config["limits"]["deadline_ms"] / 1000
                    )
                after = synced(reopened, tip)
                self.assertEqual(
                    [value["height"] for value in after],
                    [before["left"]["height"], before["right"]["height"]],
                )
                for name, node in zip(("alice", "bob"), reopened):
                    wallet = api.WalletProcess(
                        config["wallet_client"]["path"],
                        config["manifest"]["path"],
                        controller.session / "wallets" / name,
                        node,
                        config["limits"],
                    )
                    info = wallet.invoke(
                        "info",
                        {},
                        None,
                        time.monotonic() + config["limits"]["deadline_ms"] / 1000,
                    )
                    record(
                        report,
                        {"kind": "reopened-wallet", "wallet": name, "info": info},
                    )
                    self.assertEqual(info["public_key"], owners[name])
                    self.assertTrue(info["payment_policy_registered"])
                    reconciled = wallet.invoke(
                        "reconcile",
                        {},
                        None,
                        time.monotonic() + config["limits"]["deadline_ms"] / 1000,
                    )
                    record(
                        report,
                        {
                            "kind": "reopened-reconcile",
                            "wallet": name,
                            "response": reconciled,
                        },
                    )
                    if name == "alice":
                        exported_again = wallet.invoke(
                            "export",
                            {"txid": signed["txid"], "max_bytes": 1048576},
                            None,
                            time.monotonic() + config["limits"]["deadline_ms"] / 1000,
                        )
                        record(
                            report,
                            {"kind": "reopened-export", "response": exported_again},
                        )
                        self.assertEqual(
                            tuple(
                                exported_again[key]
                                for key in ("wire", "txid", "txhash")
                            ),
                            tuple(signed[key] for key in ("wire", "txid", "txhash")),
                        )
                        self.assertTrue(
                            any(
                                coin["prev_txid"] == spent[0]["prev_txid"]
                                and coin.get("present") is False
                                for coin in reconciled["coins"]
                            )
                        )
                    if name == "bob":
                        self.assertTrue(
                            any(
                                coin["prev_txid"] == signed["txid"]
                                and coin.get("present") is True
                                for coin in reconciled["coins"]
                            )
                        )
                record(
                    report,
                    {
                        "kind": "completed",
                        "utxo_root": after[0]["utxo_root"],
                        "state_root": after[0]["state_root"],
                        "height": after[0]["height"],
                        "tip": tip,
                        "txid": signed["txid"],
                        "txhash": signed["txhash"],
                        "pins": spec["pins"],
                    },
                )
        finally:
            for node in reversed(reopened):
                node.stop(time.monotonic() + 2)
            controller.close()
            record(
                report,
                {
                    "kind": "cleanup",
                    "controller_errors": controller.cleanup_errors,
                    "processes": [
                        dict(
                            node=node.name,
                            pid=node.process.pid,
                            returncode=node.process.poll(),
                            streams_closed=all(
                                stream.closed
                                for stream in (
                                    node.process.stdin,
                                    node.process.stdout,
                                    node.process.stderr,
                                )
                            ),
                        )
                        for node in [*controller.nodes.values(), *reopened]
                        if node.process is not None
                    ],
                },
            )
            # Preserve every real fixture, including failures and encrypted homes.
            try:
                for value in issued:
                    self.assertFalse(any(value), "callback-owned secret was not wiped")
                for path in root.rglob("*"):
                    if path.is_file():
                        self.assertNotIn(bytes(secret), path.read_bytes(), str(path))
            finally:
                secret[:] = b"\0" * len(secret)
                print("preserved approved native fixture:", root, file=sys.stderr)


class PrivatePaymentContractTests(unittest.TestCase):
    def test_provider_allows_only_bounded_transaction_commands(self):
        api = load_controller()
        for request in (
            {"id": "wallettransaction-1", "command": "submittransaction", "wire": "ab", "expected_tip": TXID},
            {"id": "wallettransaction-2", "command": "transactionstatus", "txid": TXID, "txhash": TXHASH, "wire": "ab"},
        ):
            api.WalletProcess._validate_provider_request(request)
            with self.assertRaises(api.ControllerError):
                api.WalletProcess._validate_provider_request(dict(request, secret="forbidden"))

    def test_mining_selects_pool_without_supplied_wire(self):
        api = load_controller()
        ctl = api.Controller({"limits": LIMITS}, "/unused")
        node = mock.Mock()
        node.request.return_value = {"ok": True, "found": True, "block_id": TXID,
                                     "coinbase_txid": TXHASH, "coinbase_index": 0}
        ctl._wallet = mock.Mock(return_value=mock.Mock(node=node))
        ctl._invoke = mock.Mock(return_value={"payment_policy_registered": True, "payment_output_hex": "ab"})
        ctl._status = mock.Mock(return_value={"tip": TXID})
        ctl._wait_active = mock.Mock()
        ctl._mine("miner", "1", "123", 1, [], time.monotonic() + 1)
        request = node.request.call_args.args[0]
        self.assertEqual(request["command"], "minepool")
        self.assertNotIn("transactions", request)
        self.assertNotIn("wire", request)
        with self.assertRaises(api.ControllerError):
            ctl._mine("miner", "1", "123", 1, ["ab"], time.monotonic() + 1)

    def test_pay_uses_persisted_wallet_then_observed_relay(self):
        api = load_controller()
        ctl = api.Controller({"limits": LIMITS}, "/unused")
        ctl.started = True
        miner = mock.Mock(name="C")
        wallets = {name: mock.Mock(node=mock.Mock(name=node))
                   for name, node in (("alice", "A"), ("bob", "B"))}
        wallets["miner"] = mock.Mock(node=miner)
        ctl._wallet = mock.Mock(side_effect=wallets.__getitem__)
        signed = {"txid": TXID, "txhash": TXHASH, "wire": "ab", "submission": "accepted"}
        def invoke(name, command, request, deadline, secret=False):
            if command == "info":
                return {"payment_policy_registered": True, "payment_output": {"value": "0"}}
            if command == "pay":
                self.assertEqual(name, "alice")
                self.assertTrue(secret)
                return signed
            if command == "status":
                return {"state": "confirmed", "block_id": TXHASH}
            return {}
        ctl._invoke = mock.Mock(side_effect=invoke)
        ctl._save_wire = mock.Mock()
        ctl._wait_pending = mock.Mock()
        ctl._wait_active = mock.Mock()
        ctl._mine = mock.Mock(return_value={"block_id": TXHASH})
        answer = ctl.execute("pay alice --to bob --amount 10 --fee 1 --mine-to miner --claim 1 --time 123 --batches 1")
        self.assertTrue(answer["ok"], answer)
        self.assertEqual(answer["transaction_status"]["state"], "confirmed")
        self.assertEqual(ctl._wait_pending.call_args.args[:2], (miner, TXID))
        self.assertEqual(ctl._mine.call_args.args[4], [])
        self.assertNotIn("sign", [call.args[1] for call in ctl._invoke.call_args_list])
