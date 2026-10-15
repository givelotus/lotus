# Isolated Lotus V2 playground

This foreground controller keeps explicitly configured development nodes alive
while you create encrypted native wallets, compile/register Payment policies,
mine, fund, mature and pay. It provides no public RPC, wallet cryptography,
transaction codec, consensus implementation or direct database access.

## Prerequisites and reproducibility

Use a reviewed Lotus V2 development checkout and its exact tested `lotusd` and
`lotus-v2-wallet-client` binaries. The wallet executable must implement private-FD
`walletcontext`, `pending` and `export`. An ordinary V1 daemon is insufficient.
Do not point this tool at a running production process or existing chain home.

Build the shared compiler from the same checkout using its committed lockfile:

```sh
cd tools/lotus-v2-compiler
npm ci
npm run build
```

Python 3.10 or later and the compiler's supported Node.js version are required.
The controller uses only Python's standard library. Native build instructions
and their validation evidence belong to the corresponding reviewed native
packet; this controller does not fetch, patch or build native code.

You supply the complete manifest, network files, binaries and SHA256 pins.
`config.schema.json` is the exact configuration shape. Paths in configuration
resolve relative to that configuration file. `compiler.node` names an executable
path, not a shell command or a PATH lookup. `compiler.directory` contains the
built shared compiler and `examples/gallery/payment.lotus`.

Each pinned object is `{ "path": "...", "sha256": "64 lowercase hex" }`.
Required top-level fields are:

- `schema`: `1`.
- `manifest`, `daemon`, `wallet_client`: pinned files.
- `compiler`: `{ "directory": "...", "node": "..." }`.
- `limits`: explicit `deadline_ms`, `max_line_bytes`, `max_wallet_bytes`,
  `max_events`, `max_blocks`, `max_batches` within the published schema.
- `nodes`: ordered entries `{ "name", "home", "network", "connect_to" }`.

`home` is a relative path beneath the **new** session directory. Homes must not
overlap or use controller namespaces. `network` is a pinned network JSON file
with the native node's exact schema, explicit magic and receive limit. Its
listener must be a numeric loopback address with port `0`; `connect` must be
empty. No seeds, endpoints, chain parameters or network magic are generated.
`connect_to` explicitly names earlier entries. The controller replaces the
empty connection list with those nodes' reported ephemeral endpoints and saves
the effective network files. For two nodes, the second can name the first;
that accepted connection carries traffic in both directions. This packet does
not support cyclic startup dependencies or external/fixed-port connections.

Wallet homes are checked within the canonical session namespace before and
after prompting, with symlinks/escapes refused. This does not eliminate
adversarial concurrent filesystem replacement.

The manifest is shared by all nodes and wallets. Reported chain/genesis/profile
identities must match. File pins are checked during configuration validation and
again before launch. This detects accidental changes, not adversarial executable
replacement. The compiler adapter imports public `compileContract` from the
shared `dist/generic.js` and compiles the canonical gallery Payment source for
the native wallet's public key. The native wallet verifies the supported policy;
no script bytecode is assembled in Python or this adapter.

See [SETUP.md](SETUP.md) for the separately maintained offline preparation of
the existing tested profile. Its explicit fixtures are not controller defaults;
preparation does not start nodes.

## Start

```sh
python3 tools/lotus-v2-devnet/devnet.py --config /absolute/config.json --session /absolute/NEW-session
```

The session's parent must exist; the session itself must not exist. There is no
implicit resume, reset, deletion, migration or reuse of an existing wallet/home.
For a side-effect-free pin/configuration check, add `--check` (the supplied
`--session` remains unused). Actual node execution requires explicitly approved
binary pins in the testing/review workflow.

The controller prints public JSON results. Node stdout is continuously drained
in a background reader while the prompt waits. Wallet commands are sequential;
the native wallet remains the only owner of encrypted keys and reservations.

## Commands

Arguments with spaces can be shell-quoted; no command is passed to a shell.
All amounts/fees/claims use canonical unsigned decimal u64 strings. `SECONDS`
is a u48 integer. `--time now` samples the wall clock; the node independently
checks MTP and all clock eligibility. The controller does not force future
timestamps or bypass a native refusal. `--batches` authorizes that many local
nonce searches of at most 256 attempts each, without wrapping.

```text
status [NODE]
inspect [NODE]
wallet create NAME [--node NODE]
wallet register NAME
wallet info NAME
wallet reconcile NAME
wallet pending NAME
wallet export NAME TXID
wallet abandon NAME TXID
wallet prepare FROM --to TO --amount AMOUNT --fee FEE
wallet sign FROM --to TO --amount AMOUNT --fee FEE
fund NAME --claim CLAIM --time now|SECONDS --batches N
mine COUNT --to NAME --claim CLAIM --time now|SECONDS --batches N
mature NAME --max-blocks N --claim CLAIM --time now|SECONDS --batches N
pay FROM --to TO --amount AMOUNT --fee FEE --mine-to MINER --claim CLAIM --time now|SECONDS --batches N
stop
```

`wallet create` creates a new native wallet, then compiles/registers its Payment
policy. If compilation/registration fails after creation, use `wallet register`
to retry registration; do not create that home again. Public Payment artifacts
are saved beneath `public/`. The first configured node is the default wallet
provider; `--node` binds a new wallet to another configured live node.

`fund` mines a coinbase to the registered policy and tracks its native-reported
outpoint. `mature` follows the initially immature tracked outpoints through
native reconciliation, ignoring new coinbases produced by the maturity work.
It stops at its block/deadline budget and reports whether more work is needed.
Claims are explicit policy caps; native monetary validation determines the
actual payout. `mine`/`fund` do not invent issuance or create a prefunded UTXO.

`prepare` does not sign. `sign` signs/reserves exactly once and saves the native
exported wire. `pay` signs once, mines that exact wire, waits for authoritative
acceptance, tracks recipient output zero and reconciles both wallets. Output
zero is a convention of this native PaymentEngine only; arbitrary imported
transactions do not inherit it. Native signing automatically tracks wallet-owned
change. There is no mempool or standalone transaction broadcast: another wallet
can observe the payment only after the complete block is accepted/synchronized.

A found nonce or retained candidate is **not acceptance**. Funding/payment waits
for authoritative `blockstatus.is_active_tip`, without recovery/receipt/
propagation fences. The receiving wallet's provider must observe the accepted
block before its tracking/reconciliation step. Operational failures stop the
command and leave nodes/homes intact; they do not mark a transaction invalid.

## Lost signing results and explicit recovery

The controller attempts to persist and fsync a bounded public recovery note on
an unknown signing outcome, including interruption/SystemExit during signing.
Interruption reports `outcome_unknown` before owned-process shutdown. If note
persistence fails, the result remains unknown and reports a null note path.

A signing timeout, crashed helper, malformed/lost stdout, generic setup failure
or storage ambiguity is `outcome_unknown`. The native SQLite commit may already
have reserved/exported a transaction. The controller never automatically
re-signs or abandons it. Recover explicitly:

```text
wallet pending NAME
wallet export NAME CANONICAL_TXID
wallet reconcile NAME
```

`pending` lists persisted outgoing transaction IDs. `export` retrieves the
canonical, native-validated persisted wire without unlocking, signing or releasing
its reservation. It saves the public artifact beneath `public/`. Signing and
export may return different metadata envelopes; the immutable txid/txhash/wire
must agree. `wallet abandon` is an explicit user decision and is never an error
cleanup action. A failure after a successful sign during mining also leaves the
signed artifact/reservation available. Do not blindly issue a second payment.

## Secrets, bounds and shutdown

Secret operations require an interactive terminal. Passphrases are prompted
without echo, confirmed on create, UTF-8 encoded and sent as exact bytes through
a dedicated EOF-framed pipe (no appended newline). They never enter argv,
environment, public JSON, logs or files. The mutable transport buffer is cleared;
Python/terminal/runtime copies are not a secure-memory guarantee. The native
client owns secret cleansing and encrypted persistence. Noninteractive tests
must inject a bounded `bytearray` prompt rather than embed secrets in commands.

The native client's other private socketpair permits only exact bounded
`walletcontext` JSONL. IDs are correlated through unique controller IDs and
mapped back; node events never enter the wallet channel. Requests are at most
1024 bytes, responses at most 32768 bytes. Public wallet stdin is at most 1 MiB;
its stdout is limited by `max_wallet_bytes` (native output can require up to
4 MiB for reconciliation). Configuring a smaller output budget can make a
successful signing result unavailable; the same recovery rules apply.

Each user operation uses one absolute monotonic deadline, including broker I/O,
compilation, mining and reconciliation. Timeouts are not reset per chunk.
Process stdin/stdout and compiler output are bounded; event summaries use a
bounded deque, stderr retains only a bounded tail, and mining counts/batches are
explicit. These are logical work/payload bounds, not total RSS or native VM/
LevelDB/kernel allocator claims. Signed artifacts and encrypted wallet databases
can grow across explicit user operations; no automatic pruning is promised.

`stop`, terminal EOF, Ctrl-C and termination signals close private channels,
request node shutdown and reap only controller-owned process groups. An
unresponsive owned process is terminated, then killed after a bounded grace
period. Existing external processes are never signaled. Homes and public
artifacts are preserved, including incomplete operations. `session.json` records
binary/manifest pins, compiler entry/source hashes and observed identities;
effective network configurations record the chosen ephemeral endpoints.

## Test and promotion gates

`tests/test_controller.py` and `tests/test_interactive_flow.py` are independently
owned. Fake-process tests exercise real pipes/socketpairs, interleaved events,
strict frames/IDs, absolute deadlines, private secret transport, process cleanup,
fresh-directory refusal, lost signing results and pending/export recovery.
Real-node tests require separately approved exact binaries/manifest and new
isolated homes. Required evidence is two live isolated nodes completing native
wallet create/register, funding, immature refusal/maturity, signed payment,
authoritative synchronization and reconciliation, followed by complete owned
process cleanup. Passing fake-process tests alone does not establish that flow.
