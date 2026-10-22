#!/bin/sh
set -eu
: "${ROOT_RUNTIME_LEASE:?Held until root confirms archive/compiler drain}"
export LOTUS_TEST_SOURCE=/Users/shammah/repos/lotus-v2-repaired-source
export BITCOIND=/Users/shammah/repos/lotus-v2-optimizations/daemon/.local-artifact-archive/bin/527/lotusd
export SEALED_PROOF_OUTPUT=/Users/shammah/repos/lotus-v2-optimizations/benchmark-results/20261022/native527-dedicated-network500k-v1/block-confirmation/canary-result.json
exec /usr/local/bin/python3 /Users/shammah/repos/lotus-v2-optimizations/benchmark-results/20261022/native527-dedicated-network500k-v1/block-confirmation/sealed_relay_correctness.py --configfile=/Users/shammah/repos/lotus-v2-optimizations/benchmark-results/20261022/native527-dedicated-network500k-v1/block-confirmation/relocated-config.ini --tmpdir=/Users/shammah/repos/lotus-v2-optimizations/daemon/.local-artifact-archive/benchmark-tmp/confirmed-canary --portseed=631 --timeout-factor=1
