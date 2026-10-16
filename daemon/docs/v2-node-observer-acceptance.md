# Native Avalanche observer process validation

The Chronik-enabled daemon at source `7808120ec6a7087df9b506c6e16c7fc7d771c05c` built successfully and passed the actual node process harness on 2026-10-15. Binary SHA256: `d0e821e8686e56c60b8c41a6d1fa4410b0b66a464b0065f2ff89b4d38f38ba5d`.

The harness uses fresh homes and ephemeral loopback ports. Checks include two observer peers, disabled/enabled storage-profile refusal, minimum-height and freshness initial-download gates, malformed private credentials, and requested genesis/unknown-block policy observations. Disabled observations omit policy flags. All temporary nodes were cleaned and the harness exited zero.

Public command/event traces, input hashes and the result are retained in [evidence](evidence/v2-node-observer-7808120ec6). Reproduce with `src/lotus_v2/node_avalanche_test/check_node.py --node BINARY --manifest DEVELOPMENT_MANIFEST --evidence NEW_DIRECTORY --binary-source EXACT_COMMIT` from the stated native source.

These observer checks do not prove funded quorum, finality, parking, conflicting-fork recovery or separate-machine operation. Those remain separate acceptance gates. The build retains macOS dependency deployment-target warnings; this run does not establish portability. This source is ahead of the maintained mailbox series through patch 260 and requires complete replay before series integration.
