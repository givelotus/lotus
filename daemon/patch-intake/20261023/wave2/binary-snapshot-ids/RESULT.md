# Shared binary snapshot IDs candidate

Committed `6428d42250cbdd6b5b78a8c1b97941505c497aef` on `fec2cab9ce9d8f2ba2bb451ce2bdcdc3a7897830`; tree `c0a4b7779d6df01e532d2b48ea29ddd4893a24aa`. Candidate is not integrated, pushed or native-adapted.

Internal snapshot dependency/child edges now store TxId directly. Capture preserves unique sorted graph links; mining joins binary keys; RPC converts at JSON output and preserves public strings/order. Historical snapshots now check exact edge identity. One graph fixture covers multi-input parent dedup, parent/child RPC ordering opposed to raw-byte order, and fallback mining identity/order/fees/sigchecks with a blocked high-fee child.

Release Ninja bitcoind, bitcoin-cli and test_bitcoin build passed. Seven focused suites passed 72 cases/23202 assertions; mempool_packages.py passed. Zero warnings in changed files. Four inherited metrics.cpp warnings are documented by exact source-blob identity and full baseline log. Original first fixture failures are preserved; only test setup was repaired (minimum transaction sizes and pre-addition chain publication), with assertions strengthened.

No benchmark claim. Native override work is separate. REST functional requires wallet and was unavailable with required wallet-OFF flags. Exact source/config/binary hashes, commands and gate results are in DELIVERY.json. source.bundle verifies with prerequisite `fec2cab9ce9d8f2ba2bb451ce2bdcdc3a7897830`; source.patch, source.diff and source-files.tar.gz preserve the delivery. Both existing C6 and new build artifacts remain. No owned processes remain.
