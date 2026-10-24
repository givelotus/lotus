# Lotus Documentation

- **[Lotus V2 Specification & Dual-Lens Architecture Overview (`lotus-v2/README.md`)](lotus-v2/README.md)** — Start here for the **Why, How, and What** of Lotus V2, with split explanations for everyday users & product builders alongside senior protocol engineers.
- **[Interactive HTML Specification Site (`lotus-v2/site/index.html`)](lotus-v2/site/index.html)** — Rendered multi-page HTML book with an interactive **Split / Everyday / Protocol Engineer** audience-lens toggle, KaTeX math, and Mermaid diagrams (regenerate anytime with `python3 docs/lotus-v2/tools/render_html.py`).
- **[Header History Merkle Tree (`lotus-v2/header-history-tree.md`)](lotus-v2/header-history-tree.md)** — Binary carry-chain `HeaderHistoryFrontier`, `MonetaryState::history_root`, and $O(\log H)$ historical header inclusion proofs.

For the V1 mainnet daemon, see the [build and run guide](../daemon/README.md). The repository [README](../README.md) describes its components and release downloads.

The files under `specs/` and the 2021 running/mining guides are historical protocol and operational references. Use current daemon instructions when running a node.

[Architecture decisions](architecture-decisions.md) describes the current component layout.
