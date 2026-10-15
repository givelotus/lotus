# lotusd-v11.6.1

Distributor build from https://github.com/Bitcoin-ABC/bitcoin-abc.git commit `8c67fe1e85a602204a2ce65aa3b643469c2c3a1d`.
Upstream native version: `0.34.1`; built native version: `11.6.1`.
Distributor patch revision: `1`; profile: `maintained`; channel: `mainnet-maintained`.
Explicit features: `registry defaults`.
Source tree: `68c74f713877577520223330af8441d4bf1431d2`.
The in-process Chronik indexer is compiled in; run the documented runtime enable option.

This is a givelotus distribution, not an official upstream release.
Build and regtest checks do not establish full mainnet synchronization or complete consensus parity.
No production deployment or container-registry push is performed.

On x86-64 Linux, the release also includes a Debian package and an RPM built
from the exact Guix-verified daemon archive. The `.deb` is smoke-tested on
Ubuntu 24.04 and Debian 12; the `.rpm` is smoke-tested on Fedora 44. These
packages install `lotusd` and `lotus-cli` under `/usr/bin` and documentation
under `/usr/share`; they do not install a service or create, migrate, or remove
node data. For example, install the `.deb` with `apt install ./lotusd_*_amd64.deb`
or the RPM with `dnf install ./lotusd-*.rpm`.
