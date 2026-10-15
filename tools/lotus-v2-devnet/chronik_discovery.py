"""Bounded confirmed Payment discovery. HTTP supplies candidates, never authority."""
from dataclasses import dataclass
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Iterable, Any


class DiscoveryError(ValueError):
    pass


class RetryDiscovery(DiscoveryError):
    pass


def hash32(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise DiscoveryError("native wire-order lowercase 32-byte hex required")
    return value


def uint(value, bits=64, decimal=True):
    if decimal:
        if not isinstance(value, str) or not re.fullmatch(r"0|[1-9][0-9]*", value):
            raise DiscoveryError("canonical decimal string required")
        value = int(value)
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise DiscoveryError("unsigned integer outside range")
    return value


@dataclass(frozen=True)
class Snapshot:
    chain_id: str
    profile_id: str
    tip: str
    height: int

    @classmethod
    def parse(cls, row):
        return cls(hash32(row["chain_id"]), hash32(row["profile_id"]),
                   hash32(row["tip"]), uint(row["height"]))


@dataclass(frozen=True, order=True)
class Outpoint:
    txid: str
    index: int


@dataclass(frozen=True)
class Candidate:
    outpoint: Outpoint
    value: int
    token_id: str
    branches: tuple
    flags: int
    paths: tuple


@dataclass(frozen=True)
class Discovery:
    snapshot: Snapshot
    generation: int
    candidates: tuple


class HttpTransport:
    """Only public JSON enters this transport. Redirects are forbidden."""
    def __init__(self, base_url, timeout=5, response_cap=256 * 1024):
        url = urllib.parse.urlsplit(base_url)
        if (url.scheme not in ("http", "https") or not url.hostname or
                url.username or url.password or url.query or url.fragment):
            raise DiscoveryError("invalid public Chronik URL")
        if not 0 < timeout <= 30 or not 1 <= response_cap <= 256 * 1024:
            raise DiscoveryError("invalid transport bounds")
        self.base = base_url.rstrip("/")
        self.timeout, self.cap = timeout, response_cap
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        self.opener = urllib.request.build_opener(NoRedirect())

    def __call__(self, path, payload):
        data = None if payload is None else json.dumps(payload).encode()
        if data is not None and len(data) > 32 * 1024:
            raise DiscoveryError("request bound exceeded")
        request = urllib.request.Request(self.base + path, data=data,
                                         headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(self.cap + 1)
        except urllib.error.HTTPError as error:
            error.close()
            if error.code in (409, 503):
                raise RetryDiscovery("Chronik snapshot unavailable") from error
            raise DiscoveryError("Chronik HTTP failure: " + str(error.code)) from error
        except (OSError, TimeoutError) as error:
            raise DiscoveryError("Chronik transport failed") from error
        if len(raw) > self.cap:
            raise DiscoveryError("response bound exceeded")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise DiscoveryError("duplicate JSON key")
                result[key] = value
            return result
        try:
            return json.loads(raw, object_pairs_hook=unique)
        except (ValueError, UnicodeError) as error:
            raise DiscoveryError("invalid JSON response") from error


class Client:
    def __init__(self, transport, chain_id, profile_id, *, page_size=100,
                 max_pages=100, retries=2):
        self.transport = transport
        self.binding = hash32(chain_id), hash32(profile_id)
        if (type(page_size) is not int or not 1 <= page_size <= 100 or
                type(max_pages) is not int or not 1 <= max_pages <= 10000 or
                type(retries) is not int or not 0 <= retries <= 10):
            raise DiscoveryError("invalid discovery bounds")
        self.page_size, self.max_pages, self.retries = page_size, max_pages, retries

    def _envelope(self, row):
        if type(row.get("version")) is not int or row["version"] != 2 or row.get("confirmed_only") is not True:
            raise DiscoveryError("confirmed V2 API required")
        snapshot = Snapshot.parse(row["snapshot"])
        if (snapshot.chain_id, snapshot.profile_id) != self.binding:
            raise DiscoveryError("chain/profile mismatch")
        return snapshot, uint(row["generation"])

    def discover(self, payment_roots: Iterable[str]) -> Discovery:
        roots = tuple(sorted({hash32(root) for root in payment_roots}))
        if not 1 <= len(roots) <= 256:
            raise DiscoveryError("one to 256 wallet Payment roots required")
        for attempt in range(self.retries + 1):
            try:
                return self._scan(roots)
            except RetryDiscovery:
                if attempt == self.retries:
                    raise DiscoveryError("discovery retry budget exhausted")
            except (KeyError, TypeError, AttributeError) as error:
                raise DiscoveryError("malformed Chronik response") from error

    def _scan(self, roots):
        status = self.transport("/v2/status", None)
        stamp = self._envelope(status)
        if status.get("ready") is not True:
            raise RetryDiscovery("index not ready")
        if status.get("pool_indexed") is not False:
            raise DiscoveryError("unexpected pool API contract")
        found, cursors, cursor = {}, set(), None
        for _ in range(self.max_pages):
            page = self.transport("/v2/branches/utxos", {
                "any_branch": roots, "page_size": self.page_size, "cursor": cursor})
            if self._envelope(page) != stamp:
                raise RetryDiscovery("snapshot/generation changed")
            rows = page["outputs"]
            if not isinstance(rows, list) or len(rows) > self.page_size:
                raise DiscoveryError("invalid page size")
            for match in rows:
                row = match["record"]
                branches = row["branches"]
                if not isinstance(branches, list) or not 1 <= len(branches) <= 256:
                    raise DiscoveryError("invalid output branches")
                branches = tuple(hash32(root) for root in branches)
                if not set(roots).intersection(branches) or row["spend"] is not None:
                    raise DiscoveryError("output does not match unspent Payment filter")
                op = Outpoint(hash32(row["txid"]), uint(row["out_idx"], 32, False))
                creation = row["creation"]
                if hash32(creation["txid"]) != op.txid or uint(creation["height"]) > stamp[0].height:
                    raise DiscoveryError("invalid creation location")
                hash32(creation["block_id"])
                hash32(creation["txhash"])
                uint(creation["tx_index"], 32, False)
                paths = row["paths"]
                if not isinstance(paths, list) or len(paths) > 256:
                    raise DiscoveryError("invalid paths")
                paths = tuple(tuple(uint(i, 8, False) for i in path) for path in paths)
                if any(len(path) > 256 for path in paths):
                    raise DiscoveryError("path limit exceeded")
                coin = Candidate(op, uint(row["value"]), hash32(row["token_id"]),
                                 branches, uint(row["flags"], 8, False), paths)
                if op in found and found[op] != coin:
                    raise DiscoveryError("conflicting duplicate outpoint")
                found[op] = coin
            cursor = page["cursor"]
            if cursor is None:
                # Fence even empty results and last-page transitions.
                final = self.transport("/v2/status", None)
                if self._envelope(final) != stamp or final.get("ready") is not True:
                    raise RetryDiscovery("snapshot changed at completion")
                return Discovery(*stamp, tuple(found[key] for key in sorted(found)))
            if not isinstance(cursor, str) or not re.fullmatch(r"[0-9a-f]{348}", cursor) or cursor in cursors:
                raise DiscoveryError("invalid or repeated cursor")
            cursors.add(cursor)
        raise DiscoveryError("page budget exhausted; no partial discovery returned")


def discover_and_reconcile(client: Client, payment_roots: Iterable[str],
                           native_track: Callable[[Outpoint], Any],
                           native_reconcile: Callable[[], Any]):
    """Adapters call native encrypted-wallet track/reconcile; never import HTTP coins.

    native_track(Outpoint) MUST call PaymentEngine::TrackFunding, which obtains
    and verifies authoritative walletcontext, ownership and anchor recheck before
    persisting. Exceptions stop the operation. Tracking is idempotent; a failed
    later track may leave earlier verified outpoints tracked. native_reconcile()
    MUST call PaymentEngine::Reconcile; its result alone determines spendability.
    """
    discovery = client.discover(payment_roots)
    for candidate in discovery.candidates:
        native_track(candidate.outpoint)
    return discovery, native_reconcile()
