# Lock-removal audit summary

Five independent source reviews of the lock-removal series, 2026-11-01. Nothing was
built or run, so "confirmed" means traced in code, not reproduced. Reproduce each
finding with a failing test before fixing it. The series isn't in the pins, except
where noted.

Don't publish these reports until the findings below are fixed: they describe
remotely triggerable bugs.

## Verdicts

| Verdict | Commits |
|---|---|
| pass | `952db7eb9e` `96b3326973` `a5b4951884` `703a07c21e` `f8ace4160c` `d9e932b64f` `2be6acfcc7` |
| fix | `da31264727` `77d48070c8` `d650d95bfb` `9e484521d6` `39c96054f6` `4ff6454942` `447c4aac77` `0cb9f3933b` `40de4ece63` `5e21887803` `e7054d87a7` `6eb8e0c15a` `6a1406992b` |
| hold | `ac31d9dc2d` `b033646c60` `e91e089f30` `b8f43cdb8b` `2deccfdbf7` `f66e475bc1` `52e34975f9` `9cfddf4d37` `7dc7be76bb` |

## Critical and high findings

| Finding | Commit | Effect | Report |
|---|---|---|---|
| X1: batch admission omits `CheckSpentCoin` and the expiry check | **Already in the V2 pin** | A v7 tx with an attacker's key can occupy a victim's P2PKH coin in the mempool | `validation-concurrency.md` |
| V7 `out.value` >= 2^63 decodes negative and re-serializes as 0 | **Root cause `8eed51051f` is in the V2 pin**; `39c96054f6` makes the retained bytes differ | Identity collision, censorship until the next tip, block delay | `wire-payloads.md` |
| B1: `existsWithinReadSection` called with no RCU lock | `b033646c60` | One unauthenticated tx aborts the node | `radix-indices.md` |
| M1: `mapNextTx` nodes are never pruned or counted | `ac31d9dc2d` | Permanent growth on normal traffic, invisible to `-maxmempool` | `radix-indices.md` |
| Lock-order cycle between `m_recent_rejects_mutex` and `cs_main` | `e91e089f30` | One rejected tx, two more and an INV can hang the node | `net-processing.md` |
| Batches of 128+ skip `TransactionAddedToMempool` | `b8f43cdb8b` | Wallets miss transactions | `net-processing.md` |
| A1: in-flight INVSHORT is dropped with no re-request | `2deccfdbf7` | Transactions can be lost to relay | `admission-limits.md` |
| A2, C1, C2, C3, D1: limits raised without compensating bounds | `2deccfdbf7` to `9cfddf4d37` | 2 peers fill the queue; about 3.5 GiB of filters at 1000 inbound; long `cs_main` holds; stalled reconciliation; 2 s stalls per tx | `admission-limits.md` |

## Landing rules

- Fix X1 and the V7 value decode first, in V2, with tests through `ProcessRawTxBatch` and the decoder. Both are in the pin.
- Shared-tier limits stay at the values in `73ed9c43ed`. Stock ABC peers can exploit the
  raised limits, so any higher value needs a per-peer byte limit and a measured reason.
- `pass` commits land first, then `fix` commits with their fixes folded in. Commits that
  depend on a `hold` wait for it.
- A `hold` commit lands only after its findings are fixed and it has been re-audited.
  Hunks the reports passed can be split out earlier.
- Almost none of these commits add tests. Each landed commit needs a test that fails
  without it.
