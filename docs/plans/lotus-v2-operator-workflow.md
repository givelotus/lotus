# Private V2 operator workflow: implementation contract

Design against monorepo `45faac3d` and native `c0ddb9cf30` (2026-10-15).
This is a proposal, not evidence of separate-machine deployment. Implement in
an isolated development checkout; preserve production homes and release assets.

## Scope and ownership

One controller implementation owner changes `tools/lotus-v2-devnet/controller.py`,
`devnet.py`, `config.schema.json`, and controller tests (including new test files).
The runbook owner changes `tools/lotus-v2-devnet/SETUP.md` and its operator examples;
coordinate any README edits. This design owns only this document. No native,
compiler, consensus, P2P, explorer API or credential-provisioning changes are needed.
Existing native Avalanche provisioning and quorum requirements still apply.

Each machine runs its own foreground controller and owns its local node and wallet
children. Operators copy public descriptors between machines and configure explicit
private numeric P2P endpoints. Use stable nonzero listener ports across machines;
`connect_to` remains a convenience for nodes in one controller. Remote mining,
SSH automation, live-process attachment, public deployment and QUIC are outside
this increment.

## Existing behavior and gaps

`wallet pay` already signs, persists and submits without mining; `wallet sign`,
`broadcast`, `status`, `pending` and `export` already support staged recovery.
Only the top-level `pay ... --mine-to ...` combines payment with local mining.
Both payment paths currently resolve recipients through a local wallet. Native
`info` supplies a public key, chain/genesis/profile identity and registered Payment
output. `_compile(public_key)` already derives the sole Payment root. Chronik
wallet discovery already finds received outpoints and native reconciliation checks
them against the local node. No secret belongs in HTTP requests or descriptors.

Controller startup currently requires a new directory, saves incomplete resume
metadata, and forgets wallet-to-node bindings. Its network allowlist rejects native
`chronik_bind` and `avalanche`; the JSON schema also omits supported node `chronik`.

## Configuration contract

Keep config schema 1 and existing hashes. Extend the exact network allowlist with
optional non-null fields matching native parsing:

- `chronik_bind`: numeric socket string (`127.0.0.1:PORT` or `[::1]:PORT`), port
  1..65535 for this operator workflow. Reject DNS and malformed/trailing input.
- `avalanche`: exact `{credentials, initial_download}`. Credentials are null
  (observer) or an absolute local path. `initial_download` is exactly
  `{minimum_height, maximum_tip_age_seconds}`, uint32 and positive uint32.
  Reject bool-as-integer, unknown fields, and explicit null optional objects.

Keep these fields in the effective network file passed to the native child.
Check credential file type/ownership/private permissions through the native
loader; do not read, copy, log or transmit its contents in controller code.
Enabling Avalanche changes the native storage profile and is forbidden on resume.
Add the existing node `chronik` discovery-binding shape to `config.schema.json`
with the same endpoint/identity constraints as `discovery_endpoint`. Document
network schema separately if needed; it is a pinned external JSON file.

`--check` remains read-only. Tests must show ordinary old configs still work,
new fields reach the child unchanged, and invalid/unknown fields fail closed.

## Explicit clean resume

CLI: `devnet.py --config CONFIG --session SESSION --resume`. Default launch still
requires a nonexistent session. `--resume --check` validates persisted metadata
and paths without starting children or modifying files; it cannot promise future
exclusive access. No attach/reset/adopt switch is added.

First increment accepts only sessions created by the new controller and cleanly
stopped by it. Old schema-1 session records, partial startup, controller crashes,
uncertain child cleanup and live sessions are refused with preserved files and a
specific error. This supports orderly restart; crash recovery is a separate gate.

Persist a versioned schema-2 `session.json` with: canonical session path,
manifest/daemon/wallet-client pins, compiler directory and Node path plus hashes
of Node, compiler entry and Payment source, complete normalized configuration
(including node home mappings, network pins and discovery bindings), observed
chain/genesis/profile identity, and wallet-to-node map. Persist lifecycle
`starting|running|stopped` and a monotonically increasing run generation. Bind
all config fields on resume; no silent executable, policy, endpoint, identity or
home migration. Compiler hashes have the existing limited coverage; they do not
claim a complete dependency-tree commitment.

Use an exclusive nonblocking OS file lock on a fixed session lock file, held until
all launched children are reaped. Never unlink that lock file. Create/open metadata
and lock paths without following symlinks; reject symlinks in the session, managed
homes and managed-file path components, paths escaping the session, non-owned
files/directories and unsafe writable permissions. Reject aliases before resolving
away evidence of a symlink. Reserve controller filenames in node-home validation.
Check all persisted metadata and pins before opening any existing node home.

Under the lock, durably replace `stopped` with `starting` before launching any
child; use temp-file + rename + file/directory fsync for metadata updates. A
failure or abrupt death leaves a non-resumable state. Start fresh child processes
against only recorded homes; ready events must match persisted chain/genesis/
profile and configured listeners before marking `running`. Cleanup acts only on
Popen handles created in this invocation, never recorded PIDs or discovered
processes. Mark `stopped` only after every owned child has exited and been reaped
and cleanup has no uncertainty. Release lock last. Failure never deletes homes.

Persist wallet/node bindings atomically before create can leave a wallet behind;
validate existing wallets via public `info` on resume. Unknown/orphan wallet
homes are not silently adopted. Incomplete registration can use existing explicit
`wallet register`. Restore bindings exactly, including nondefault nodes.
Persist effective network files per generation, so ephemeral `connect_to`
listeners can be rebuilt without overwriting historical inputs. The original
pinned network inputs must remain identical. Fixed cross-host ports stay fixed.

## Public recipient commands

```text
recipient export bob --output /absolute/new/bob-recipient.json
recipient import bob-remote --file /absolute/received/bob-recipient.json
wallet prepare alice --to-recipient bob-remote --amount 10000 --fee 1000
wallet pay alice --to-recipient bob-remote --amount 10000 --fee 1000
```

The new option is mutually exclusive with existing `--to LOCAL_WALLET` for
`wallet prepare|sign|pay`; exactly one is required. Keep top-level `pay --mine-to`
restricted to local wallets, because it performs local receive tracking and mining.

Descriptor schema 1 has exactly `schema`, `kind` (`lotus-v2-payment-recipient`),
`chain_id`, `genesis_id`, `profile_digest`, `public_key`, and `payment_output`.
The public key is the existing 32-byte x-only lowercase hex. Output is exactly
`{flags:0,value:"0",branches:[ROOT],paths:[[0]]}`. Identity fields/root are
32-byte lowercase hex. No script, amounts, URLs, file paths, credentials, wallet
names, keys, or passphrases are accepted as additional descriptor fields.

Export calls local native `info`, verifies registered Payment and current identity,
recompiles the public key and checks the exact output/root. Write to a new regular
file only (exclusive create; no overwrite/symlink), mode 0600, with fsync. Return
its path and SHA256 fingerprint. Import reads at most 16 KiB from a regular file,
rejects duplicate JSON keys/deep or malformed structures, validates exact shape,
identity and canonical output, and recompiles the public key to compare its root.
Compilation uses the existing bounded subprocess API and operation deadline.
This verifies Payment semantics; the operator must authenticate the descriptor
fingerprint with the intended recipient out of band.

Store validated imports at `session/public/recipients/ALIAS.json`; alias follows
existing wallet-name grammar but uses a separate namespace. Refuse alias overwrite.
On resume/use revalidate descriptors and compiled roots; imported contents cannot
select a compiler or executable. At signing time derive output amount solely from
`--amount`; native wallet validation remains the final canonical-output check.
Never invoke or create a local recipient wallet for `--to-recipient`.

## Payment, receive and finality sequence

1. Receiver starts its local configured node/controller, creates/registers its
   wallet, exports the descriptor and shares only that public file/fingerprint.
2. Sender imports it and runs `wallet pay ... --to-recipient ...`. Return existing
   native submission and txid/wire result. Accepted/duplicate means submission,
   not confirmation or finality. Preserve existing unknown-signing-outcome recovery;
   never sign again automatically after a timeout.
3. Independent miner uses existing local `mine` commands. P2P relays transactions
   and blocks. The sender does not launch or control the remote miner.
4. Receiver runs `wallet reconcile bob` with its explicit local Chronik binding.
   Discovery plus native reconciliation determines receipts; no sender-driven
   remote `track` request or secret HTTP endpoint is needed. Sender uses existing
   `wallet status alice TXID`; rebroadcast uses the same stored transaction.
5. Operators inspect existing native/Chronik block observations and Avalanche
   readiness/quorum evidence for that block. Wallet `confirmed` does not imply
   `finalized`. Missing observations are unavailable, never synthesized finality.
6. Clean `stop`, then explicit `--resume`, retains wallet history and same homes.
   Reconcile after restart and after an induced pre-finality reorg. A reorg must
   clear stale inclusion/receipt claims through existing native/discovery behavior.

## Required acceptance tests and evidence boundaries

Controller unit tests cover new config validation and schema agreement; resume
success with multiple wallet/node bindings; competing controller lock rejection;
identity/config/binary/compiler drift; symlink/path/permission attacks; missing,
old, partial and non-stopped sessions; startup/cleanup failures leaving no false
stopped marker; and no signaling of foreign processes. Resume must preserve
wallet/node bytes on preflight refusal and never reset or silently create a
missing recorded home.

Descriptor tests cover export/import roundtrip, restart persistence, wrong identity,
root/key/output tampering, extra secret fields, malformed/bounded JSON, file and
alias collision, and no passphrase prompt before validation succeeds. Payment
tests assert imported recipients require no local receiver and no mining request;
broadcast/unknown-outcome handling preserves the original transaction.

Run the native controller lifecycle with two independent sessions connected by
explicit private P2P endpoints: public descriptor transfer, payment, independent
mining, receiver discovery, clean stop/resume, and reconciliation after reorg.
Record actual block finality separately using existing Avalanche provisioning and
observations. Same-host sessions are a useful gate but do not establish separate-
machine operation. The release owner must execute the runbook on separate hosts
and record identities, exact builds, tx/block IDs, restart/reorg results and actual
finality before declaring that user goal complete. No proof of finality is implied
by configuration acceptance or by the local wallet/explorer gate alone.
