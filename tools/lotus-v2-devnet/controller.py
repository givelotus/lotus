"""Private, foreground orchestration for explicitly configured isolated V2 nodes.

This module is not a wallet, transaction codec, consensus implementation or RPC
server. Native processes own validation, encrypted keys and wallet persistence.
"""

from __future__ import annotations

import collections
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import queue
import re
import select
import selectors
import shlex
import signal
import socket
import subprocess
import threading
import time
import uuid


class ControllerError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class SigningInterrupted(BaseException):
    """An interrupted signing attempt whose durable result is unknown."""

    code = "outcome_unknown"


def terminate_owned(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=0.5)


def require(condition, message, code="invalid"):
    if not condition:
        raise ControllerError(code, message)


def exact(value, keys):
    require(
        isinstance(value, dict) and set(value) == set(keys), "unexpected object fields"
    )


def integer(value, low, high):
    require(
        type(value) is int and low <= value <= high, "integer outside configured range"
    )
    return value


def hexadecimal(value, size=32):
    require(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % (2 * size), value),
        "canonical lowercase hex required",
    )
    return value


def endpoint(value, listen=False):
    exact(value, ("address", "port"))
    require(isinstance(value["address"], str), "numeric IP address required")
    address = ipaddress.ip_address(value["address"])
    require(str(address) == value["address"], "canonical numeric IP address required")
    require(not address.is_multicast and (listen or not address.is_unspecified),
            "unicast endpoint required")
    integer(value["port"], 0 if listen else 1, 65535)


def decimal(value):
    require(
        isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]*", value),
        "canonical decimal u64 required",
    )
    require(int(value) <= (1 << 64) - 1, "decimal exceeds u64")
    return value


def decode_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON field", "protocol_error")
            result[key] = value
        return result

    try:
        return json.loads(
            data,
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("nonfinite JSON")
            ),
        )
    except ControllerError:
        raise
    except (ValueError, UnicodeError) as error:
        raise ControllerError("protocol_error", "invalid JSON") from error


def encode_json(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=False).encode("utf8")


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise ControllerError("timeout", "operation deadline expired")
    return value


def send_fd(fd, data, deadline):
    view = memoryview(data)
    while view:
        remaining(deadline)
        try:
            count = os.write(fd, view)
            require(count > 0, "private channel closed", "transport_error")
            view = view[count:]
        except BlockingIOError:
            select.select([], [fd], [], remaining(deadline))
        except (BrokenPipeError, OSError) as error:
            raise ControllerError(
                "transport_error", "private channel write failed"
            ) from error


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_config(path):
    """Validate explicit inputs without creating homes or starting processes."""
    path = Path(path).resolve()
    require(path.stat().st_size <= 65536, "configuration too large")
    config = decode_json(path.read_bytes())
    exact(
        config,
        (
            "schema",
            "manifest",
            "daemon",
            "wallet_client",
            "compiler",
            "limits",
            "nodes",
        ),
    )
    require(
        type(config["schema"]) is int and config["schema"] == 1, "configuration schema"
    )
    for name in ("manifest", "daemon", "wallet_client"):
        pinned = config[name]
        exact(pinned, ("path", "sha256"))
        hexadecimal(pinned["sha256"])
        source = Path(pinned["path"])
        source = (
            (path.parent / source).resolve()
            if not source.is_absolute()
            else source.resolve()
        )
        require(
            source.is_file() and sha256_file(source) == pinned["sha256"],
            name + " pin mismatch",
        )
        if name != "manifest":
            require(os.access(source, os.X_OK), name + " must be executable")
        pinned["path"] = str(source)
    exact(config["compiler"], ("directory", "node"))
    for key in ("directory", "node"):
        source = Path(config["compiler"][key])
        config["compiler"][key] = str(
            (path.parent / source).resolve()
            if not source.is_absolute()
            else source.resolve()
        )
    compiler = Path(config["compiler"]["directory"])
    require(
        (compiler / "dist/generic.js").is_file()
        and (compiler / "examples/gallery/payment.lotus").is_file(),
        "build the shared compiler first",
    )
    require(
        os.access(config["compiler"]["node"], os.X_OK),
        "explicit node executable required",
    )
    limits = config["limits"]
    exact(
        limits,
        (
            "deadline_ms",
            "max_line_bytes",
            "max_wallet_bytes",
            "max_events",
            "max_blocks",
            "max_batches",
        ),
    )
    for key, low, high in (
        ("deadline_ms", 1, 60000),
        ("max_line_bytes", 32768, 8388608),
        ("max_wallet_bytes", 1024, 4194304),
        ("max_events", 1, 256),
        ("max_blocks", 1, 256),
        ("max_batches", 1, 4096),
    ):
        integer(limits[key], low, high)
    require(
        isinstance(config["nodes"], list) and 1 <= len(config["nodes"]) <= 8,
        "one to eight explicit nodes required",
    )
    names, homes, magic = set(), [], None
    for node in config["nodes"]:
        exact(node, ("name", "home", "network", "connect_to"))
        require(
            isinstance(node["name"], str)
            and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", node["name"]),
            "node name",
        )
        require(node["name"] not in names, "duplicate node name")
        home = Path(node["home"])
        require(
            not home.is_absolute()
            and home.parts
            and all(part not in (".", "..") for part in home.parts),
            "home must be beneath new session",
        )
        require(
            home.parts[0] not in ("wallets", "public", "network", "session.json"),
            "home uses controller namespace",
        )
        require(
            all(
                home != other
                and home not in other.parents
                and other not in home.parents
                for other in homes
            ),
            "overlapping homes",
        )
        homes.append(home)
        require(
            isinstance(node["connect_to"], list)
            and len(set(node["connect_to"])) == len(node["connect_to"])
            and all(peer in names for peer in node["connect_to"]),
            "links must name earlier nodes",
        )
        pinned = node["network"]
        exact(pinned, ("path", "sha256"))
        hexadecimal(pinned["sha256"])
        source = Path(pinned["path"])
        source = (
            (path.parent / source).resolve()
            if not source.is_absolute()
            else source.resolve()
        )
        require(
            source.is_file()
            and source.stat().st_size <= 65536
            and sha256_file(source) == pinned["sha256"],
            "network pin mismatch",
        )
        network = decode_json(source.read_bytes())
        exact(
            network,
            ("schema", "magic", "listen", "connect", "receive_limit", "local_policy"),
        )
        require(
            type(network["schema"]) is int
            and network["schema"] == 1
            and network["local_policy"] == "bounded-local-v1",
            "network schema/policy",
        )
        exact(network["listen"], ("address", "port"))
        endpoint(network["listen"], listen=True)
        require(isinstance(network["connect"], list) and len(network["connect"]) <= 64,
                "bounded explicit peer endpoints required")
        for peer in network["connect"]:
            endpoint(peer)
        hexadecimal(network["magic"], 4)
        require(
            magic is None or magic == network["magic"],
            "network magic differs between nodes",
        )
        magic = network["magic"]
        integer(network["receive_limit"], 1, 0xFFFFFFFF)
        pinned["path"] = str(source)
        node["resolved_network"] = network
        names.add(node["name"])
    return config


def load_config(path):
    """Validate configuration without process or filesystem mutations."""
    try:
        return _load_config(path)
    except ControllerError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise ControllerError(
            "invalid", "invalid configuration: " + str(error)
        ) from error


class NodeProcess:
    """Own one JSONL child; background draining continues while the REPL waits."""

    def __init__(self, name, argv, limits):
        self.name, self.argv, self.limits = name, list(argv), limits
        self.process = None
        self.events = collections.deque(maxlen=limits["max_events"])
        self.ready = None
        self.failure = None
        self.stderr_tail = bytearray()
        self._pending = {}
        self._mutex = threading.Lock()
        self._serial = threading.Lock()
        self._wake = threading.Condition(self._mutex)
        self._thread = None
        self._closing = False

    def start(self):
        require(self.process is None, "node already started")
        self.process = subprocess.Popen(
            self.argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            start_new_session=True,
        )
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            os.set_blocking(stream.fileno(), False)
        self._thread = threading.Thread(
            target=self._pump, name="node-" + self.name, daemon=True
        )
        self._thread.start()

    def _fail(self, error):
        with self._wake:
            self.failure = error
            for reply in self._pending.values():
                reply.put(error)
            self._pending.clear()
            self._wake.notify_all()

    def _pump(self):
        selector = selectors.DefaultSelector()
        buffer = bytearray()
        try:
            selector.register(self.process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(self.process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                for key, _ in selector.select(0.1):
                    cap = (
                        self.limits["max_line_bytes"] + 1 - len(buffer)
                        if key.data == "stdout"
                        else 65536
                    )
                    require(cap > 0, "node JSONL frame exceeds cap", "protocol_error")
                    data = os.read(key.fd, min(65536, cap))
                    if not data:
                        selector.unregister(key.fileobj)
                        if key.data == "stdout":
                            require(
                                not buffer,
                                "truncated node JSONL frame",
                                "protocol_error",
                            )
                            if not self._closing:
                                raise ControllerError(
                                    "transport_error", "node stdout closed"
                                )
                        continue
                    if key.data == "stderr":
                        self.stderr_tail.extend(data)
                        del self.stderr_tail[:-8192]
                        continue
                    buffer.extend(data)
                    while b"\n" in buffer:
                        line, _, tail = buffer.partition(b"\n")
                        buffer = bytearray(tail)
                        require(
                            line and len(line) <= self.limits["max_line_bytes"],
                            "node JSONL frame length",
                            "protocol_error",
                        )
                        value = decode_json(line)
                        require(
                            isinstance(value, dict),
                            "node JSON object required",
                            "protocol_error",
                        )
                        with self._wake:
                            if "id" in value:
                                require(
                                    isinstance(value["id"], str)
                                    and type(value.get("ok")) is bool,
                                    "node response schema",
                                    "protocol_error",
                                )
                                reply = self._pending.pop(value["id"], None)
                                if reply is not None:
                                    reply.put(value)
                            else:
                                require(
                                    isinstance(value.get("event"), str)
                                    and 0 < len(value["event"]) <= 64,
                                    "node event schema",
                                    "protocol_error",
                                )
                                if "tip" in value:
                                    hexadecimal(value["tip"])
                                if "height" in value:
                                    integer(value["height"], 0, (1 << 64) - 1)
                                for field in ("tip_known", "reopen_required"):
                                    if field in value:
                                        require(
                                            type(value[field]) is bool,
                                            "node event flag",
                                            "protocol_error",
                                        )
                                # Keep bounded event summaries rather than arbitrary body echoes.
                                summary = {
                                    k: value[k]
                                    for k in (
                                        "event",
                                        "tip",
                                        "height",
                                        "tip_known",
                                        "reopen_required",
                                    )
                                    if k in value
                                }
                                self.events.append(summary)
                                if value["event"] == "ready":
                                    require(
                                        self.ready is None,
                                        "duplicate ready event",
                                        "protocol_error",
                                    )
                                    self.ready = value
                            self._wake.notify_all()
        except Exception as error:
            self._fail(
                error
                if isinstance(error, ControllerError)
                else ControllerError("transport_error", "node reader failed")
            )
        finally:
            selector.close()

    def wait_ready(self, deadline):
        with self._wake:
            while self.ready is None:
                if self.failure:
                    raise self.failure
                self._wake.wait(remaining(deadline))
            if self.failure:
                raise self.failure
            return dict(self.ready)

    def request(self, payload, deadline):
        require(
            isinstance(payload, dict) and isinstance(payload.get("command"), str),
            "node command required",
        )
        require(self.process is not None, "node not started")
        require(
            self._serial.acquire(timeout=remaining(deadline)),
            "node request busy",
            "timeout",
        )
        ident = "ctl-" + uuid.uuid4().hex
        reply = queue.Queue(maxsize=1)
        try:
            with self._mutex:
                if self.failure:
                    raise self.failure
                self._pending[ident] = reply
            request = dict(payload, id=ident)
            data = encode_json(request) + b"\n"
            require(
                len(data) - 1 <= self.limits["max_line_bytes"],
                "node request frame capacity",
                "capacity_refused",
            )
            send_fd(self.process.stdin.fileno(), data, deadline)
            try:
                value = reply.get(timeout=remaining(deadline))
            except queue.Empty as error:
                raise ControllerError(
                    "timeout", "node response deadline expired"
                ) from error
            if isinstance(value, Exception):
                raise value
            return value
        finally:
            with self._mutex:
                self._pending.pop(ident, None)
            self._serial.release()

    def stop(self, deadline):
        if self.process is None:
            return
        self._closing = True
        failure = None
        try:
            if self.process.poll() is None:
                if not self.process.stdin.closed:
                    try:
                        self.request({"command": "stop"}, deadline)
                    except Exception:
                        pass
                    self.process.stdin.close()
                try:
                    self.process.wait(timeout=max(0.01, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    pass
        except BaseException as error:
            failure = error
        finally:
            # EOF/stream closure alone does not terminate a noncooperative child.
            # Always attempt bounded termination/reaping, even when graceful
            # shutdown was interrupted by a signal or SystemExit.
            try:
                if self.process.poll() is None:
                    terminate_owned(self.process)
            except BaseException as error:
                if failure is None:
                    failure = error
            finally:
                for stream in (
                    self.process.stdin,
                    self.process.stdout,
                    self.process.stderr,
                ):
                    if stream and not stream.closed:
                        try:
                            stream.close()
                        except OSError:
                            pass
                if self._thread:
                    self._thread.join(timeout=0.5)
        if failure is not None:
            raise failure


class WalletProcess:
    """One native wallet operation; only walletcontext crosses its private FD."""

    def __init__(self, executable, manifest, home, node, limits):
        self.executable, self.manifest, self.home = (
            str(executable),
            str(manifest),
            str(home),
        )
        self.node, self.limits = node, limits

    @staticmethod
    def _validate_provider_request(request):
        require(isinstance(request, dict), "wallet provider object", "protocol_error")
        command = request.get("command")
        shapes = {
            "walletcontext": ("id", "command", "tip", "outpoint"),
            "submittransaction": ("id", "command", "wire", "expected_tip"),
            "transactionstatus": ("id", "command", "txid", "txhash", "wire"),
        }
        require(command in shapes, "wallet private command", "protocol_error")
        exact(request, shapes[command])
        require(isinstance(request["id"], str) and
                re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", request["id"]),
                "wallet private id", "protocol_error")
        for field in ("tip", "expected_tip", "txid", "txhash"):
            if field in request and request[field] is not None:
                hexadecimal(request[field])
        if "wire" in request:
            require(isinstance(request["wire"], str) and
                    re.fullmatch(r"(?:[0-9a-f]{2})+", request["wire"]) and
                    len(request["wire"]) <= 2 * 1048576,
                    "wallet wire capacity/encoding", "protocol_error")
        if request.get("outpoint") is not None:
            exact(request["outpoint"], ("txid", "index"))
            hexadecimal(request["outpoint"]["txid"])
            integer(request["outpoint"]["index"], 0, 0xFFFFFFFF)

    def invoke(self, command, publicrequest, passphrase=None, deadline=None):
        try:
            return self._invoke(command, publicrequest, passphrase, deadline)
        finally:
            if isinstance(passphrase, bytearray):
                passphrase[:] = b"\0" * len(passphrase)

    def _invoke(self, command, publicrequest, passphrase=None, deadline=None):
        require(
            command
            in (
                "create",
                "register",
                "track",
                "reconcile",
                "prepare",
                "sign",
                "abandon",
                "info",
                "pending",
                "export",
                "pay",
                "broadcast",
                "status",
            ),
            "wallet command",
        )
        deadline = (
            deadline
            if deadline is not None
            else time.monotonic() + self.limits["deadline_ms"] / 1000
        )
        require(isinstance(publicrequest, dict), "public wallet object required")
        data = encode_json(publicrequest)
        require(
            len(data) <= min(1048576, self.limits["max_wallet_bytes"]),
            "wallet request capacity",
            "capacity_refused",
        )
        require(
            passphrase is None
            or isinstance(passphrase, bytearray)
            and 0 < len(passphrase) <= 4096,
            "bounded mutable passphrase required",
        )
        parent, child = socket.socketpair()
        secret_read = secret_write = None
        process = None
        selector = selectors.DefaultSelector()
        output, errors, private = bytearray(), bytearray(), bytearray()
        try:
            timeout = max(1, min(60000, int(remaining(deadline) * 1000)))
            argv = [
                self.executable,
                self.manifest,
                self.home,
                command,
                "--node-fd=" + str(child.fileno()),
                "--timeout-ms=" + str(timeout),
            ]
            passed = [child.fileno()]
            if passphrase is not None:
                secret_read, secret_write = os.pipe()
                argv.append("--passphrase-fd=" + str(secret_read))
                passed.append(secret_read)
            process = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                pass_fds=tuple(passed),
                bufsize=0,
                start_new_session=True,
            )
            child.close()
            if secret_read is not None:
                os.close(secret_read)
                secret_read = None
                os.set_blocking(secret_write, False)
                send_fd(secret_write, passphrase, deadline)
                os.close(secret_write)
                secret_write = None
            if passphrase is not None:
                passphrase[:] = b"\0" * len(passphrase)
            parent.setblocking(False)
            for stream in (process.stdin, process.stdout, process.stderr):
                os.set_blocking(stream.fileno(), False)
            send_fd(process.stdin.fileno(), data, deadline)
            process.stdin.close()
            selector.register(parent, selectors.EVENT_READ, "private")
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                for key, _ in selector.select(remaining(deadline)):
                    target = (
                        private
                        if key.data == "private"
                        else output if key.data == "stdout" else errors
                    )
                    cap = (
                        min(2098176, self.limits["max_line_bytes"])
                        if key.data == "private"
                        else (
                            self.limits["max_wallet_bytes"]
                            if key.data == "stdout"
                            else 8192
                        )
                    )
                    if key.data == "stderr":
                        chunk = os.read(key.fd, 4096)
                    else:
                        require(
                            len(target) <= cap,
                            "wallet channel frame capacity",
                            "protocol_error",
                        )
                        chunk = os.read(key.fd, min(4096, cap + 1 - len(target)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        if key.data == "private":
                            require(
                                not private,
                                "truncated wallet private frame",
                                "protocol_error",
                            )
                        continue
                    target.extend(chunk)
                    if key.data == "stderr":
                        del errors[:-8192]
                        continue
                    require(
                        len(target) <= cap, "wallet output capacity", "protocol_error"
                    )
                    if key.data == "private":
                        require(
                            len(private) < cap or b"\n" in private,
                            "wallet private frame capacity",
                            "protocol_error",
                        )
                    if key.data == "private" and b"\n" in private:
                        line, _, tail = private.partition(b"\n")
                        require(
                            not tail and len(line) + 1 <= cap,
                            "wallet private framing",
                            "protocol_error",
                        )
                        private.clear()
                        request = decode_json(line)
                        self._validate_provider_request(request)
                        if request["command"] == "walletcontext":
                            require(len(line) + 1 <= 1024, "wallet context request capacity", "protocol_error")
                        response = self.node.request(
                            {k: v for k, v in request.items() if k != "id"}, deadline
                        )
                        response = dict(response, id=request["id"])
                        encoded = encode_json(response)
                        require(
                            len(encoded) + 1 <= 32768,
                            "wallet context response capacity",
                            "capacity_refused",
                        )
                        send_fd(parent.fileno(), encoded + b"\n", deadline)
            code = process.wait(timeout=remaining(deadline))
            value = decode_json(output)
            require(
                isinstance(value, dict) and isinstance(value.get("result"), str),
                "wallet public result schema",
                "protocol_error",
            )
            if command in ("sign", "pay") and value["result"] in (
                "setup_error",
                "storage_error",
                "outcome_unknown",
            ):
                raise ControllerError(
                    "outcome_unknown",
                    "signing outcome requires pending/export recovery",
                )
            if command in ("sign", "pay") and value["result"] == "success":
                for field in ("txid", "txhash", "digest"):
                    hexadecimal(value.get(field))
                require(
                    isinstance(value.get("wire"), str)
                    and re.fullmatch(r"(?:[0-9a-f]{2})+", value["wire"]),
                    "signed wire result schema",
                    "protocol_error",
                )
            expected = (
                0
                if value["result"] == "success"
                else (
                    1
                    if value["result"] == "setup_error"
                    else 4 if value["result"] == "storage_error" else 2
                )
            )
            require(
                code == expected, "wallet result/exit mismatch", "wallet_process_error"
            )
            return value
        except BaseException as error:
            if command in ("sign", "pay") and process is not None:
                if isinstance(error, (KeyboardInterrupt, SystemExit)):
                    raise SigningInterrupted(
                        "sign outcome unknown; recover using wallet pending/export before any retry"
                    ) from error
                raise ControllerError(
                    "outcome_unknown",
                    "sign result unavailable; use wallet pending/export, never blindly resign or abandon",
                ) from error
            if isinstance(error, (ControllerError, KeyboardInterrupt, SystemExit)):
                raise
            raise ControllerError(
                "transport_error", "wallet operation unavailable"
            ) from error
        finally:
            if passphrase is not None:
                passphrase[:] = b"\0" * len(passphrase)
            selector.close()
            parent.close()
            child.close()
            for fd in (secret_read, secret_write):
                if fd is not None:
                    os.close(fd)
            if process is not None:
                if process.poll() is None:
                    terminate_owned(process)
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream and not stream.closed:
                        stream.close()


class Controller:
    def __init__(self, config, session, secret_prompt=None):
        self.config, self.session = config, Path(session).resolve()
        self.nodes = {}
        self.wallet_nodes = {}
        self.secret_prompt = secret_prompt
        self.started = False
        self.closed = False
        self.cleanup_errors = []

    def deadline(self):
        return time.monotonic() + self.config["limits"]["deadline_ms"] / 1000

    def start(self):
        require(
            not self.started and not self.closed, "controller already started/closed"
        )
        # No existing session, resume/reset or arbitrary external home is allowed.
        self.session.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.started = True
        try:
            for name in ("manifest", "daemon", "wallet_client"):
                pinned = self.config[name]
                require(
                    sha256_file(pinned["path"]) == pinned["sha256"],
                    name + " changed before launch",
                )
            (self.session / "network").mkdir(mode=0o700)
            (self.session / "wallets").mkdir(mode=0o700)
            (self.session / "public").mkdir(mode=0o700)
            identity = None
            for item in self.config["nodes"]:
                home = self.session / item["home"]
                home.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                require(not home.exists(), "node home already exists")
                network = dict(item["resolved_network"])
                network["connect"] = list(network["connect"]) + [
                    self.nodes[name].ready["listen"] for name in item["connect_to"]
                ]
                for peer in network["connect"]:
                    endpoint(peer)
                network_path = self.session / "network" / (item["name"] + ".json")
                self._write_new(network_path, encode_json(network) + b"\n")
                node = NodeProcess(
                    item["name"],
                    [
                        self.config["daemon"]["path"],
                        "-lotusv2node",
                        self.config["manifest"]["path"],
                        str(home),
                        str(network_path),
                    ],
                    self.config["limits"],
                )
                self.nodes[item["name"]] = node
                node.start()
                ready = node.wait_ready(self.deadline())
                require(
                    ready.get("tip_known") is True
                    and ready.get("reopen_required") is False,
                    "node startup has no authoritative tip",
                    "inconclusive",
                )
                exact(ready.get("listen"), ("address", "port"))
                endpoint(ready["listen"], listen=True)
                integer(ready["listen"]["port"], 1, 65535)
                require(ready["listen"]["address"] == network["listen"]["address"]
                        and (network["listen"]["port"] == 0 or
                             ready["listen"]["port"] == network["listen"]["port"]),
                        "node listener differs from configured endpoint")
                observed = tuple(
                    hexadecimal(ready.get(field))
                    for field in ("chain_id", "genesis_id", "profile_digest")
                )
                require(
                    identity is None or identity == observed,
                    "node profile identities differ",
                )
                identity = observed
            self._write_new(
                self.session / "session.json",
                encode_json(
                    {
                        "schema": 1,
                        "manifest": self.config["manifest"],
                        "daemon": self.config["daemon"],
                        "wallet_client": self.config["wallet_client"],
                        "compiler": self.config["compiler"],
                        "compiler_sha256": sha256_file(
                            Path(self.config["compiler"]["directory"])
                            / "dist/generic.js"
                        ),
                        "payment_source_sha256": sha256_file(
                            Path(self.config["compiler"]["directory"])
                            / "examples/gallery/payment.lotus"
                        ),
                        "identity": identity,
                        "nodes": [
                            {"name": name, "listen": node.ready["listen"]}
                            for name, node in self.nodes.items()
                        ],
                    }
                )
                + b"\n",
            )
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _write_new(path, data):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def close(self):
        if self.closed and not self.cleanup_errors:
            return
        self.closed = True
        self.cleanup_errors = []
        for node in reversed(list(self.nodes.values())):
            try:
                node.stop(
                    time.monotonic()
                    + min(2, self.config["limits"]["deadline_ms"] / 1000)
                )
            except BaseException as error:
                self.cleanup_errors.append(
                    {"node": node.name, "error": type(error).__name__}
                )
        # Preserve evidence and encrypted homes, including partially created ones.

    def _node(self, name=None):
        if name is None:
            name = self.config["nodes"][0]["name"]
        require(name in self.nodes, "unknown node")
        return self.nodes[name]

    def _wallet(self, name):
        require(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", name), "wallet name")
        home = self.session / "wallets" / name
        require(
            home.resolve() == home and not home.is_symlink(),
            "wallet home symlink or namespace escape",
        )
        node = self._node(self.wallet_nodes.get(name))
        return WalletProcess(
            self.config["wallet_client"]["path"],
            self.config["manifest"]["path"],
            home,
            node,
            self.config["limits"],
        )

    def _invoke(self, name, command, request, deadline, secret=False):
        wallet = self._wallet(name)
        require(
            command == "create" or Path(wallet.home).is_dir(),
            "wallet home missing; create explicitly first",
        )
        password = None
        try:
            if secret:
                require(
                    self.secret_prompt is not None,
                    "private terminal secret prompt unavailable",
                )
                password = self.secret_prompt(name, command)
            # Recheck after an injected prompt/callback as well as before asking.
            home = Path(wallet.home)
            require(
                home.resolve() == home and not home.is_symlink(),
                "wallet home symlink or namespace escape",
            )
            require(
                command == "create" or Path(wallet.home).is_dir(),
                "wallet home disappeared",
            )
            value = wallet.invoke(command, request, password, deadline)
            if value["result"] != "success":
                raise ControllerError(
                    value["result"],
                    value.get("error", "native wallet operation failed"),
                )
            return value
        finally:
            if isinstance(password, bytearray):
                password[:] = b"\0" * len(password)

    def _compile(self, owner, deadline):
        hexadecimal(owner)
        compiler = self.config["compiler"]
        argv = [
            compiler["node"],
            str(Path(__file__).with_name("compile-payment.mjs")),
            compiler["directory"],
        ]
        # Public input/output only. Pipe reads are explicitly capped before accumulation.
        process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            start_new_session=True,
        )
        selector = selectors.DefaultSelector()
        output, errors = bytearray(), bytearray()
        try:
            for stream in (process.stdin, process.stdout, process.stderr):
                os.set_blocking(stream.fileno(), False)
            send_fd(process.stdin.fileno(), encode_json({"owner": owner}), deadline)
            process.stdin.close()
            selector.register(process.stdout, selectors.EVENT_READ, output)
            selector.register(process.stderr, selectors.EVENT_READ, errors)
            while selector.get_map():
                for key, _ in selector.select(remaining(deadline)):
                    target = key.data
                    chunk = os.read(key.fd, min(4096, 65537 - len(target)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    target.extend(chunk)
                    require(
                        len(target) <= 65536,
                        "compiler output capacity",
                        "capacity_refused",
                    )
            require(
                process.wait(timeout=remaining(deadline)) == 0,
                "shared Payment compiler failed",
            )
            value = decode_json(output)
            exact(value, ("script", "proof", "root"))
            require(
                isinstance(value["script"], str)
                and re.fullmatch(r"(?:[0-9a-f]{2})+", value["script"]),
                "compiler script encoding",
            )
            require(
                value["proof"] == [],
                "native wallet supports sole compiled Payment method",
            )
            hexadecimal(value["root"])
            return value
        finally:
            selector.close()
            if process.poll() is None:
                terminate_owned(process)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream and not stream.closed:
                    stream.close()

    def _status(self, node, deadline):
        value = node.request({"command": "status"}, deadline)
        require(
            value.get("ok") is True
            and value.get("tip_known") is True
            and value.get("reopen_required") is False,
            "authoritative node status unavailable",
            "inconclusive",
        )
        require(
            not value.get("pending_journal")
            and not value.get("pending_receipt")
            and not value.get("pending_propagation")
            and not value.get("execution_paused"),
            "node recovery/receipt/propagation/execution fence",
            "inconclusive",
        )
        hexadecimal(value.get("tip"))
        return value

    def _wait_active(self, node, block, deadline):
        hexadecimal(block)
        while True:
            value = node.request(
                {"command": "blockstatus", "block_id": block}, deadline
            )
            require(value.get("ok") is True, "block status unavailable", "inconclusive")
            require(
                not value.get("deterministic_invalid"),
                "native validator rejected block",
                "invalid",
            )
            if (
                value.get("is_active_tip") is True
                and value.get("tip_known") is True
                and not value.get("reopen_required")
                and not value.get("execution_paused")
                and not value.get("pending_journal")
                and not value.get("pending_receipt")
                and not value.get("pending_propagation")
            ):
                return value
            time.sleep(min(0.02, remaining(deadline)))

    def _wait_pending(self, node, txid, deadline):
        # Observe peer relay at the mining node; never inject wallet wire there.
        while True:
            value = node.request({"command": "transactionstatus", "txid": hexadecimal(txid)}, deadline)
            require(value.get("ok") is True, "transaction status unavailable", "inconclusive")
            if value.get("state") in ("pending", "confirmed"):
                return value
            require(value.get("state") != "conflicted", "transaction conflicted", "conflicted")
            time.sleep(min(0.02, remaining(deadline)))

    def _mine(self, name, claim, clock, batches, transactions, deadline):
        require(not transactions, "minepool accepts no injected transactions")
        info = self._invoke(name, "info", {}, deadline)
        require(
            info.get("payment_policy_registered") is True,
            "register compiled Payment first",
        )
        output = info.get("payment_output_hex")
        require(
            isinstance(output, str) and re.fullmatch(r"(?:[0-9a-f]{2})+", output),
            "native canonical destination unavailable",
        )
        node = self._wallet(name).node
        status = self._status(node, deadline)
        when = (
            int(time.time())
            if clock == "now"
            else integer(int(clock), 0, (1 << 48) - 1)
        )
        request = {
            "command": "minepool",
            "expected_parent": status["tip"],
            "time": when,
            "max_claim": decimal(claim),
            "coinbase_output": output,
            "coinbase_data": None,
            "start_nonce": "0",
            "max_attempts": 256,
        }
        for _ in range(batches):
            result = node.request(request, deadline)
            require(
                result.get("ok") is True,
                result.get("error", "native mining refused"),
                result.get("result", "inconclusive"),
            )
            if result.get("found") is True:
                block = result.get("block_id")
                self._wait_active(node, block, deadline)
                tracked = {
                    "prev_txid": hexadecimal(result.get("coinbase_txid")),
                    "prev_index": integer(result.get("coinbase_index"), 0, 0xFFFFFFFF),
                }
                self._invoke(name, "track", tracked, deadline)
                return result
            require(
                result.get("found") is False and result.get("next_nonce") is not None,
                "nonce range exhausted",
                "nonce_exhausted",
            )
            request["start_nonce"] = decimal(result["next_nonce"])
        raise ControllerError(
            "nonce_exhausted", "explicit nonce batch budget exhausted"
        )

    def execute(self, line):
        """Execute one public REPL command; no hidden retry of sign or abandon."""
        signing_wallet = None
        try:
            require(
                self.started and not self.closed, "controller not running", "closed"
            )
            words = shlex.split(line)
            require(words, "command required")
            deadline = self.deadline()
            if words == ["stop"]:
                self.close()
                return {
                    "ok": not self.cleanup_errors,
                    "result": (
                        "cleanup_incomplete" if self.cleanup_errors else "stopped"
                    ),
                    "cleanup_errors": self.cleanup_errors,
                }
            if words[0] in ("status", "inspect"):
                require(len(words) <= 2, "status [node]")
                selected = (
                    [self._node(words[1])]
                    if len(words) == 2
                    else list(self.nodes.values())
                )
                result = {
                    node.name: node.request({"command": "status"}, deadline)
                    for node in selected
                }
                return {"ok": True, "result": "status", "nodes": result}
            if words[0] == "wallet":
                require(len(words) >= 3, "wallet COMMAND NAME")
                command, name = words[1:3]
                require(
                    command
                    in (
                        "create",
                        "register",
                        "info",
                        "reconcile",
                        "pending",
                        "export",
                        "abandon",
                        "prepare",
                        "sign",
                        "pay",
                        "broadcast",
                        "status",
                    ),
                    "wallet command",
                )
                wallet = self._wallet(name)
                if command == "create":
                    require(len(words) in (3, 5), "wallet create NAME [--node NODE]")
                    require(
                        not Path(wallet.home).exists(), "wallet home already exists"
                    )
                    if len(words) == 5:
                        require(
                            words[3] == "--node", "wallet create NAME [--node NODE]"
                        )
                        self._node(words[4])
                        self.wallet_nodes[name] = words[4]
                    value = self._invoke(name, "create", {}, deadline, True)
                    compiled = self._compile(value["public_key"], deadline)
                    self._invoke(name, "register", compiled, deadline)
                    self._write_new(
                        self.session / "public" / (name + "-payment.json"),
                        encode_json(compiled) + b"\n",
                    )
                elif command == "register":
                    require(len(words) == 3, "wallet register NAME")
                    info = self._invoke(name, "info", {}, deadline)
                    value = self._invoke(
                        name,
                        "register",
                        self._compile(info["public_key"], deadline),
                        deadline,
                    )
                elif command in ("info", "reconcile", "pending"):
                    require(len(words) == 3, "wallet " + command + " NAME")
                    value = self._invoke(name, command, {}, deadline)
                elif command in ("export", "abandon", "broadcast", "status"):
                    require(len(words) == 4, "wallet " + command + " NAME TXID")
                    request = {"txid": hexadecimal(words[3])}
                    if command == "export":
                        request["max_bytes"] = 1048576
                    value = self._invoke(name, command, request, deadline)
                    if command == "export":
                        self._save_wire(value)
                else:
                    options = self._options(words[3:], ("to", "amount", "fee"))
                    info = self._invoke(options["to"], "info", {}, deadline)
                    require(
                        info.get("payment_policy_registered") is True,
                        "recipient compiled Payment not registered",
                    )
                    recipient = dict(
                        info["payment_output"], value=decimal(options["amount"])
                    )
                    if command in ("sign", "pay"):
                        signing_wallet = name
                    value = self._invoke(
                        name,
                        command,
                        {"recipient": recipient, "fee": decimal(options["fee"])},
                        deadline,
                        command in ("sign", "pay"),
                    )
                    if command in ("sign", "pay"):
                        self._save_wire(value)
                return {
                    "ok": True,
                    "result": "wallet",
                    "operation": command,
                    "wallet": name,
                    "data": value,
                }
            if words[0] in ("fund", "mine", "mature"):
                return self._mining_command(words, deadline)
            if words[0] == "pay":
                require(
                    len(words) >= 2,
                    "pay FROM --to TO --amount N --fee N --mine-to MINER --claim N --time now|SECONDS --batches N",
                )
                options = self._options(
                    words[2:],
                    ("to", "amount", "fee", "mine-to", "claim", "time", "batches"),
                )
                info = self._invoke(options["to"], "info", {}, deadline)
                require(
                    info.get("payment_policy_registered") is True,
                    "recipient compiled Payment not registered",
                )
                recipient = dict(
                    info["payment_output"], value=decimal(options["amount"])
                )
                signing_wallet = words[1]
                signed = self._invoke(
                    words[1],
                    "pay",
                    {"recipient": recipient, "fee": decimal(options["fee"])},
                    deadline,
                    True,
                )
                self._save_wire(signed)
                require(signed.get("submission") in ("accepted", "duplicate"),
                        "native transaction submission refused", signed.get("submission", "inconclusive"))
                mining_node = self._wallet(options["mine-to"]).node
                self._wait_pending(mining_node, signed["txid"], deadline)
                mined = self._mine(
                    options["mine-to"],
                    options["claim"],
                    options["time"],
                    self._batches(options["batches"]),
                    [],
                    deadline,
                )
                # Only this native PaymentEngine's output ordering is assumed.
                recipient_node = self._wallet(options["to"]).node
                self._wait_active(recipient_node, mined["block_id"], deadline)
                self._invoke(
                    options["to"],
                    "track",
                    {"prev_txid": hexadecimal(signed["txid"]), "prev_index": 0},
                    deadline,
                )
                self._wait_active(self._wallet(words[1]).node, mined["block_id"], deadline)
                receiver = self._invoke(options["to"], "reconcile", {}, deadline)
                sender = self._invoke(words[1], "reconcile", {}, deadline)
                history = self._invoke(words[1], "status", {"txid": signed["txid"]}, deadline)
                require(history.get("state") == "confirmed" and history.get("block_id") == mined["block_id"],
                        "wallet confirmation history unavailable", "inconclusive")
                return {
                    "ok": True,
                    "result": "paid",
                    "signed": signed,
                    "transaction_status": history,
                    "mined": mined,
                    "sender": sender,
                    "receiver": receiver,
                }
            raise ControllerError("invalid", "unknown command")
        except SigningInterrupted as error:
            error.recovery_note = (
                self._recovery_note(signing_wallet)
                if signing_wallet is not None
                else None
            )
            raise
        except ControllerError as error:
            result = {"ok": False, "result": error.code, "error": str(error)}
            if error.code == "outcome_unknown" and signing_wallet is not None:
                result["recovery_note"] = self._recovery_note(signing_wallet)
                result["recovery"] = [
                    "wallet pending " + signing_wallet,
                    "wallet export " + signing_wallet + " TXID",
                ]
            return result
        except (ValueError, KeyError, TypeError, OSError) as error:
            return {"ok": False, "result": "invalid", "error": str(error)}

    def _recovery_note(self, wallet):
        # Public bounded facts only; never infer a txid that was not received.
        note = {
            "schema": 1,
            "result": "outcome_unknown",
            "wallet": wallet,
            "automatic_retry": False,
            "recovery": [
                "wallet pending " + wallet,
                "wallet export " + wallet + " TXID",
                "wallet reconcile " + wallet,
            ],
        }
        path = (
            self.session
            / "public"
            / (wallet + "-sign-unknown-" + uuid.uuid4().hex + ".json")
        )
        try:
            self._write_new(path, encode_json(note) + b"\n")
            return str(path)
        except OSError:
            # Preserve unknown classification even if the filesystem cannot
            # persist the recovery note. No automatic retry follows.
            return None

    @staticmethod
    def _options(words, required):
        require(len(words) % 2 == 0, "options require values")
        result = {}
        for key, value in zip(words[::2], words[1::2]):
            require(
                key.startswith("--") and key[2:] not in result,
                "unknown or duplicate option",
            )
            result[key[2:]] = value
        require(
            set(result) == set(required),
            "required options: " + ", ".join("--" + key for key in required),
        )
        return result

    def _batches(self, value):
        return integer(int(value), 1, self.config["limits"]["max_batches"])

    def _save_wire(self, value):
        txid = hexadecimal(value["txid"])
        wire = value["wire"]
        require(
            isinstance(wire, str)
            and re.fullmatch(r"(?:[0-9a-f]{2})+", wire)
            and len(wire) <= 2 * 1048576,
            "native signed wire encoding/capacity",
        )
        path = self.session / "public" / (txid + ".json")
        encoded = encode_json(value) + b"\n"
        if path.exists():
            existing = decode_json(path.read_bytes())
            require(
                all(
                    existing.get(field) == value.get(field)
                    for field in ("txid", "txhash", "wire")
                ),
                "exported wire changed for txid",
            )
        else:
            self._write_new(path, encoded)

    def _mining_command(self, words, deadline):
        command = words[0]
        require(len(words) >= 2, command + " requires destination/count")
        if command == "fund":
            name, count = words[1], 1
            options = self._options(words[2:], ("claim", "time", "batches"))
        elif command == "mine":
            count = integer(int(words[1]), 1, self.config["limits"]["max_blocks"])
            options = self._options(words[2:], ("to", "claim", "time", "batches"))
            name = options["to"]
        else:
            name = words[1]
            options = self._options(
                words[2:], ("max-blocks", "claim", "time", "batches")
            )
            count = integer(
                int(options["max-blocks"]), 1, self.config["limits"]["max_blocks"]
            )
        batches = self._batches(options["batches"])
        mined = []
        targets = set()
        if command == "mature":
            initial = self._invoke(name, "reconcile", {}, deadline)
            targets = {
                (coin["prev_txid"], str(coin["prev_index"]))
                for coin in initial.get("coins", [])
                if coin.get("present") is True and coin.get("mature") is False
            }
        for _ in range(count):
            if command == "mature":
                reconciled = self._invoke(name, "reconcile", {}, deadline)
                immature = any(
                    (coin["prev_txid"], str(coin["prev_index"])) in targets
                    and coin.get("present") is True
                    and coin.get("mature") is False
                    for coin in reconciled.get("coins", [])
                )
                if not immature:
                    return {
                        "ok": True,
                        "result": "mature",
                        "mined": mined,
                        "wallet": reconciled,
                    }
            mined.append(
                self._mine(
                    name, options["claim"], options["time"], batches, [], deadline
                )
            )
        reconciled = self._invoke(name, "reconcile", {}, deadline)
        immature = any(
            (coin["prev_txid"], str(coin["prev_index"])) in targets
            and coin.get("present") is True
            and coin.get("mature") is False
            for coin in reconciled.get("coins", [])
        )
        return {
            "ok": True,
            "result": (
                "mined"
                if command != "mature"
                else "maturity_budget_exhausted" if immature else "mature"
            ),
            "mined": mined,
            "wallet": reconciled,
        }
