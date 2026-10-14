# Component licenses

This monorepo combines components with their existing licenses. This document maps the license files; it does not assign a new license to the repository or change any component's terms. Source-file notices and dependency licenses remain applicable.

| Component | Existing license file | Notes |
| --- | --- | --- |
| GPU miner (`miner/`) | [MIT license](miner/LICENSE) | Retains the Logos Foundation copyright notice. |
| Rust SDK (`sdk/rust/`) | [MIT license](sdk/rust/LICENSE) | Retains the Logos Foundation copyright notice. |
| Dart SDK (`sdk/dart/`) | [MIT license and attribution](sdk/dart/lib/LICENSE) | Retains the listed Lotus and upstream authors' notices. |
| Vase wallet and server (`wallets/vase/`) | [GNU GPL version 3](wallets/vase/LICENSE) | The embedded Dart library also retains its [own MIT license and attribution](wallets/vase/vase-client/lib/lotus/LICENSE). |
| Daemon built from upstream Bitcoin ABC and Lotus patches (`daemon/`) | Upstream `COPYING` and source-file notices | Setup fetches the pinned upstream source into the ignored workspace. Its `COPYING` file is available at `daemon/workspace-v1/COPYING` after V1 setup and accompanies daemon release archives. Retain dependency notices when distributing bundled libraries. |

The patch series preserves upstream source notices. The map above does not establish a blanket license for documentation, build scripts, or other files without an existing notice. Consult the applicable files for their terms.
