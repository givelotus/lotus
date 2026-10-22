# Pure MR06 causal-owner prefix transform

Import `transform.py` and call `transform(files)` with a dictionary of source paths to bytes or strings. Keep `payload.json` beside it. The function returns a new dictionary, preserves byte/string types and unrelated files, performs no Git/cache/ref/worktree writes, and is idempotent. It changes only the six paths named in payload.json.

Production starts at **recovered-relay-0004 / global265**, current canonical owner `56443331da6c8658581fd324a89dfcf4248610e7`. The capability envelope, feature enum, peer feature field and options used there already exist. Before that owner the function is a no-op. It removes local-only opt-in, adds the explicit high-bandwidth format capability, gates direct sealed and body relay, and preserves ordinary peers' paths.

The earliest negotiation helper has no continuous-reconciliation option: its transformed helper does not mention that future option. Later helpers preserve the existing reconciliation selection. Before `-txrelaypushhb` exists, the pre-existing implementation pushes bodies by default; the transform preserves that historical local willingness while adding explicit remote capability. Once the option appears, its local willingness is retained. Epoch maintenance remains controlled by the existing short-ID option, so a private-only feature does not introduce a new relay-index workload.

The ordinary-announcement sealed path is a later native addition. Its new local-willingness guard enters only when `is_hb_sealed_peer` is present. Native header adaptations remain unchanged.

The existing sealed-header integration test is changed at the negotiation owner because all its helpers exist there. Four additional/default-body negotiation tests enter with their actual required option at `6e267760894deaee6fff36fc2749f433f2d5528e` (the txrelaypushhb owner). No later option, pure-native transaction format or future harness API is imported into an earlier prefix.

`prefix-ledger.json` records **all257 original prefixes**, from owner265 through canonical521 `a60bba6facc924cdf43c34dc881805bb114fe373`. Every transformation succeeded, every second application was identical, and the six endpoint blobs are byte-identical to isolated candidate `e724205aec`. This is source/prefix evidence, not 257 builds or runtime tests.

N1 reported all six affected MR06 cases passing on its combined `2b61` source/tree `2b4`; its actual before control preserves three expected failing assertions. Its complete fifteen-case gate also passes. N1 owns raw receipts and combined integration. This module neither modifies that lane nor claims a complete stock-ABC daemon-pair/Chronik-enabled build.
