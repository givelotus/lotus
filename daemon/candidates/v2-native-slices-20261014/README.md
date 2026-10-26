# Lotus V2 native slices — REVIEW

This is a self-contained, review-only 15-mailbox series on Bitcoin ABC `1fb7db17c176cdea8a2c60d887891589382ee4e3`, starting with the reviewed V2 foundation 000–008 and appending native topics 009–014. It does not change the selectable V2 series, base pin, production workspace, node, or release. `manifest.json` records the exact base, every source commit and intermediate tree, patch SHA-256, and provenance.

The new topics add typed branch/indexed/ordered commitments (009), a scalar collapsed sparse UTXO reference model and fixed monetary-state commitment (010), bounded transaction and coinbase framing (011), complete input bytes in identities (012), signing hash domains (013), and identity/signing modes (014). Topic 010 also enforces `MAX_COIN_BYTES = 868` and tests a valid maximal 812-byte output inside an 868-byte Coin; that correction is folded into the sparse topic and identified in the manifest. Original source authors and author dates are retained. Patches 000–008 are byte-identical to the foundation candidate.

## Exact replay

Apply the files listed in `series` with `git am --keep-non-patch` to an isolated checkout of the recorded ABC base. A separate fresh clone `/tmp/lotus-v2-native-mailbox-replay` did so successfully; all 15 resulting intermediate trees matched `manifest.json`, including final tree `7374d7fad27c6ad8c68352ef605efc03ee5553d1`. The integrated development source is `/tmp/lotus-v2-native-slice-review` at commit `283ded8c6d8c80bb22c10c10613f10f67c823d8a`. `git diff 3c5cfc0d4..HEAD --check` passed.

## Native validation

On the integrated source, Debug and Release configurations each passed:

```sh
cmake -S . -B <build> -G Ninja -DCMAKE_BUILD_TYPE=<Debug|Release> -DBUILD_CHRONIK=OFF -DBUILD_QT=OFF
cmake --build <build> --target check-lotus-v2-header check-lotus-v2-commitment check-lotus-v2-sparse-state -j 6
cmake -S src/lotus_v2/output_test -B <output-build> -G Ninja -DCMAKE_BUILD_TYPE=<Debug|Release>
cmake --build <output-build> -j 4
ctest --test-dir <output-build> --output-on-failure
cmake -S src/lotus_v2/signing_test -B <signing-build> -G Ninja -DCMAKE_BUILD_TYPE=<Debug|Release> -DLOTUS_SECP_LIBRARY=<built ABC libsecp256k1.a>
cmake --build <signing-build> -j 4
ctest --test-dir <signing-build> --output-on-failure
```

The root targets reported header, commitment, and sparse-state vector/boundary passes in both configurations. Output and transaction standalone CTests passed 2/2 in each configuration; signing standalone CTest passed 1/1 in each. Signing used the existing ABC secp256k1 static library from the foundation build, with the same source base. All test checks in these slices are active in Release.

The integrated Debug `test_bitcoin` target also built from this source, and `--run_test=miner_tests --log_level=error --color_output=no` passed all six cases.

## Review boundaries

These are isolated candidate primitives. The sparse set recomputes roots from all coins and is not a persistent chainstate. The transaction, commitment, sparse, and signing modules are not wired into daemon consensus or network behavior; signing currently has only a standalone test target and external secp library path. No full valid V2 block, live-node sync, economic calibration, or independent multi-implementation consensus conformance is claimed. The source and specification remain candidates for review.
