# Native mining command and signed-payment process check

`daemon/tests/check-v2-native-mining.py` exercises two actual development-node
processes with the native bounded `mineblock` command. It fetches the connected
blocks actually produced by the native implementation through bounded `readblock`
chunks and independently runs Python complete-block validation on those exact
bytes. It compares authoritative roots and monetary bytes, confirms native
coinbase TxId/index/value, checks ordered ordinary transaction preservation,
propagation, coin/proof results and persisted restart. It supplies no acceptance,
coin-lookup or mining callbacks to the node.

The first gate uses a public fixture scalar 3 for actual BIP340 signatures through
the independent reference signing implementation. Its message derives from the
native-mined funding coin after independent full-block validation. The compiler
binds the existing Payment source to the corresponding public key. The node
receives signed full transaction bytes, never a private key or supplied digest.
This is explicitly a fixture signer, not an encrypted wallet/user workflow.

The older SQLite pilot helper opens indexed-V2 storage while the live development
node uses V4 recovery/candidate storage. Stopping the process does not make those
profiles compatible. This check never invokes that helper, opens a live LevelDB
from another process, migrates/resets storage or claims wallet integration. A
proper coherent V4 wallet-context/provider packet is a separate prerequisite for
the final interactive wallet flow.

Build the compiler package first (`npm ci --ignore-scripts && npm run build`).
Use the reference Python environment with blake3 and coincurve. After root approves
an exact binary/source/hash, run explicitly from the monorepo root:

```sh
/private/tmp/lotus-v2-compiler-review-venv/bin/python \
  daemon/tests/check-v2-native-mining.py \
  --daemon /path/to/approved/lotusd \
  --daemon-source <full-native-commit> \
  --expected-daemon-sha256 <approved-binary-hash> \
  --build-command 'exact configure/build command and log' \
  --manifest /path/to/explicit-manifest.json \
  --reference-package tools/lotus-v2-reference \
  --reference-source <full-reference-commit> \
  --compiler tools/lotus-v2-compiler --compiler-source <full-compiler-commit> \
  --network-magic 31435769 --receive-limit 2097152 \
  --output /tmp/new-native-mining-run
```

The magic is the existing dispatcher fixture magic, not a network allocation.
Every issuance, target, spacing, maturity and resource value comes from the
explicit caller manifest. The pilot's 100000 atom coinbase claim cap and 1000 atom
ordinary fee are transaction choices, not protocol/network defaults. Supported
manifests have empty pruned genesis, no supplied field hints, matching ordinary
and monetary dust limits, and maturity 2–16. No mainnet or reserved/default ports
are used. Both nodes bind `127.0.0.1:0`; the reused transparent relay delays actual
peer chunks by 50ms with bounded queues/backpressure and exact-handle cleanup.

The exact producer request contains all fields:

```json
{"id":"caller-id","command":"mineblock","expected_parent":"<64 hex>","time":1792022520,"max_claim":"100000","coinbase_output":"<canonical native Output hex with value zero>","coinbase_data":null,"transactions":[],"start_nonce":"0","max_attempts":256}
```

A found response must remain `accepted:false`, `pending_validation:true` and
`retained_authenticated:true`, retaining the parent authority in that response.
Only subsequent quiescent native status proves normal validation/receipt
publication. Nonce, block ID and confirmed coinbase fields are checked against
the independently decoded actual block, not reconstructed from response claims.
The check reads 97-byte chunks deliberately spanning header/transaction boundaries,
checks offsets/constant total/EOF and saves the exact assembled body. It also
checks the empty exact-end EOF response. The miner does not echo a full block.

Funding and maturity blocks are mined natively. A valid signature spending the
immature funding is initially refused; after actual maturity blocks the same
signed transaction is natively assembled/mined and normally accepted/propagated.
Independent Python validates every produced block, root and monetary transition.
The spent funding and created recipient coin frames must match that independent
ledger on both stores; their proof paths must agree. Node B restarts into the
same quiescent persisted tip/root/money.

Negative gates cover missing/duplicate/unknown fields, malformed and uppercase
hex, noncanonical/overflowing decimal u64, overflowing time, Boolean attempt
count, attempt cap 257, nonzero destination, destination/data/count/aggregate byte
quotas, stale parent, immature funding, malformed signed transaction and invalid
signature. Error classes are checked: malformed scalar/encoding is invalid_request;
well-formed local quotas are capacity_refused; transaction failures are
invalid_transactions; stale parent remains stale_parent. Zero attempts must
return nonce_exhausted with unchanged next nonce and no authoritative mutation.
At u64 maximum, either a found nonce must be exactly that maximum and pass normal
validation, or exhaustion must return null next_nonce. Wrapping to zero fails.

Before/after projections include authoritative tip/root/money/profile, invalid-root
count and fetch epoch. These observations establish unchanged exposed state and
no new durable invalidity fact; they do not independently prove every raw KV row
unchanged. The native assembler/storage unit gates cover stronger raw-state
properties. The test does not turn producer errors into permanent block invalidity
or infer acceptance from a pending response.

The output must be new. Exact binary/compiler-module/input hashes, source pins,
build command, compiled source/artifact, signed public-fixture transaction bytes,
produced blocks, raw JSONL stdin/stdout/stderr, typed negative responses, peer relay
traffic statistics and cleanup results remain for review. Existing failures are
never reset or regenerated. Early dependency/setup failures can leave only the
copied manifest; there are no node processes at that point. All process handles
and relay sockets/threads are owned and cleaned by the reused local-node harness.

## Observed execution

Root approved native source `3a8b8dcaaa68b095ec2b22611f82e2f4bf29ea37`, binary
`/private/tmp/lotus-v2-daemon-runtime-staging-20261015/build/src/lotusd`, SHA256
`fdffaaf226fab90220d2c8571cbafb7b675d40db6fe1035014d795c1bf870b34`.
Build: `cmake --build build --target lotusd -j6`; log
`/private/tmp/lotus-v2-native-mine-command-final-build.log`.
Reference/compiler source was monorepo
`fa9ff11e65366a731be7da27ba4b519a038718a9`.

The real two-process gate passed at
`/private/tmp/lotus-v2-native-mining-venv-20261015`. A fresh strengthened run at
`/private/tmp/lotus-v2-native-mining-chunked-20261015` passed actual multi-offset
retrieval: 242/242/450 byte blocks required 3/3/5 chunks. Heights 1/2/3 were mined
at nonces 0/2/1, each with confirmed 100000 atom coinbase output. Height three
included the unchanged signed Payment and independent invocation cost 50181.
Twenty-one typed negative gates passed; maximum-u64 nonce exhaustion returned
null, and zero attempts returned next_nonce zero without exposed state changes.
All node starts, including B restart, exited zero with no cleanup errors.
The initial system Python attempt lacked coincurve and failed before launching
any node; its partial manifest remains at
`/private/tmp/lotus-v2-native-mining-first-20261015`.

These results establish bounded native production and real peer acceptance for
the explicit fixture profile and public-fixture signer. They do not establish
an encrypted user-wallet flow, transaction relay/mempool, autonomous mining,
a usable testnet or public-network readiness.
