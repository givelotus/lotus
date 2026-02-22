# Lotus

Lotus is a trust-minimized peer-to-peer monetary protocol. Monetary policy is governed by proof-of-work mining difficulty as a live, adversarially-revealed signal — no committees, no oracles, no central bank.

This monorepo contains all components of the Lotus ecosystem.

## Structure

```
daemon/         — Lotus node daemon (eCash upstream + Lotus patchset)
  patches/      — Lotus-specific patches applied on top of eCash
sdk/
  typescript/   — TypeScript SDK for wallet and application development
  dart/         — Dart SDK for mobile wallet development
  rust/         — Rust libraries for blockchain interaction
wallets/
  vase/         — Mobile reference wallet (Dart/Flutter)
  stamp/        — CashWeb-based desktop wallet
indexer/        — Blockchain indexer
miner/          — GPU mining software
cashweb/        — Peer-to-peer encrypted messaging protocol
docs/           — Documentation
```

## Research

The theoretical foundation for Lotus is published at [givelotus.github.io](https://givelotus.github.io). Three preprints cover proof-of-work as monetary signal, adaptive monetary policy via feedback control, and spam prevention via burn-to-speak messaging.

## Support

Lotus is funded by its community. If you believe mathematics should govern money instead of committees, consider supporting development at [patreon.com/c/givelotus](https://www.patreon.com/c/givelotus).
