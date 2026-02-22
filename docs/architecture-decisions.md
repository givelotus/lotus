# Architecture Decisions & Open Questions

## Target Deployment Stack

Goal: minimize operational complexity so community members can actually run nodes.

```
lotusd      — blockchain node + embedded indexer
cashwebd    — unified messaging daemon (keyserver + relay + broadcast merged)
postgres    — persistent structured data
redis(?)    — ephemeral high-throughput data (message queues, routing state)
```

## Open Questions

### Data Layer for cashwebd
- Postgres handles persistent structured data (keys, metadata, accounts)
- High-throughput ephemeral data (message queues, routing state) needs a separate store
- Redis is operationally simple but not good for non-ephemeral data
- ScyllaDB and MongoDB are options but may be overkill at current scale
- **Decision deferred:** Need to inspect existing Rust daemon code to understand actual storage patterns before committing to a data layer

### cashwebd Consolidation
- Current state: separate keyserver, relay, and broadcast daemons (unfinished contractor work)
- Target: single `cashwebd` binary with one config, one database connection
- Shared connection pool, shared auth, shared crypto primitives across all three functions
- **Decision deferred:** Need to audit existing Rust code before merging

### Indexer
- Chronik was paid for ($20K) and then pulled into eCash daemon in a way that dropped Lotus support
- Options: fork Chronik back out, extend Fulcrum, or build new indexer on bitcoinsuite
- Preference: embed indexer in lotusd to reduce daemon count
- **Decision deferred:** Depends on lotusd codebase analysis

## Decided

### Monorepo
- Single `lotus` monorepo at github.com/givelotus/lotus
- All components live here: daemon, SDKs, wallets, cashweb daemons, specs, docs
- Reduces fragmentation across givelotus, StampChat, and LotusiaStewardship orgs

### Daemon Strategy
- Track eCash upstream via git rebase (not patchset files, not a frozen fork)
- Lotus-specific changes kept as clean atomic commits on top of eCash tag
- Pull upstream security fixes selectively rather than full rebases
- Redenomination conflicts isolated to chainparams / constants layer

### Chain Parameters
- Runtime flag approach (not compile-time) for chain-specific constants
- Extends existing CChainParams pattern already in eCash codebase
- Allows full test suite to run against Lotus binary with Lotus params
