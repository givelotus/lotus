# Retention cap and reviewed pipeline folds

| Check | Result | Adoption |
|---|---|---|
| Native retained-body cap tree49082823 | 1,207 cases /31,466,445 assertions pass | Candidate; not timed |
| Shared/native fold endpoints | Shared projected5c0d8301; native exactly49082823 | Pure source preservation verified |
| Modified shared owner268 | Compiles after timer placement repair | Gate fails inherited16-body-push fixture; not waived |
| Final shared/native boundary gates | 1,024 shared and1,207 native cases PASS | No promotion: owner268 fixture/ownership issue remains |

The measured21.9% all-peer improvement belongs to earlier64176c73/tree4b78888f. No timing is claimed for retained-budget/folded tree49082823. The budget reserves serialized bytes across decoded compact responses in addition to primary queue accounting. Credits stay alive through peer disconnect and release after held bodies are destroyed; if no reservation fits, the already-decoded response follows existing serial admission. This bounds additional serialized retention, not exact RSS of every allocation or every other protocol buffer.

Six temporary fixes are folded into three existing source owners: shared admission268, native consensus fixture, native snapshot signature preparation. Two additional timing-placement adapters move a timestamp and timer constructor out of owner268 into the later metrics owner that declares the timer. Both final endpoints remain exact through that move.531 final commits,378 shared plus153 native; all532 prior source owners and all six fixup diffs accounted in PIPELINE-FINAL-COMPOSED-OWNERSHIP.json. No mailbox edits, original-ref pruning, new worktrees, active source pin/main/master/tag changes.

Final review refs: sharedb14362f31c6c46fd10a1eb5a9d2c29362f6fa315; nativeb466fdd221427e9d60a01f6b36db6b7943ff579d. Verified incremental bundles and closure prerequisites are recorded in PIPELINE-FOLD-PRESERVATION.json. All old source refs are retained.

Owner-prefix verification exposed an additional pre-existing problem: the relay-tick test simulates only a local private-handler flag while production at that stage requires a real negotiated feature. The late shared RPC owner later removes explicit negotiation checks and their regression tests; native first consensus restores them. PRIVATE-RELAY-OWNERSHIP-REVIEW.md is the next reviewed repair plan, with exact source rollback diffs saved. It intentionally restores shared behavior and preserves the native endpoint; it must not be hidden as a pure shared reorder. Promotion remains withheld until affected prefix gates and both endpoints pass with the correct ownership.

Raw terminal evidence: evidence-pipeline-retention-v1.tar.gz with verified byte manifest. Live endpoint gate logs remain outside this archive until finished. Prior RPC admission and all-peer measurements are in NATIVE-PEER-PIPELINE-REPORT.md and evidence-peer-pipeline-v1.tar.gz. No block processing/finality result is claimed.
