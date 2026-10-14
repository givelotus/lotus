# Context: bitcoinsuite-chronik-client (+ chronik-client TS)

## Boundary

**Inside**: HTTP + WebSocket client for the Chronik blockchain indexer API. Rust crate and TypeScript npm package.

**Outside**: Core blockchain types, error infrastructure, the Chronik server itself.

## Dependencies

### bitcoinsuite-chronik-client (Rust)

| Dependency | Type | Purpose |
|---|---|---|
| `bitcoinsuite-core` | Runtime | Bytes, Sha256d |
| `bitcoinsuite-error` | Runtime | ErrorMeta, Result, WrapErr |
| `reqwest` | Runtime | HTTP client |
| `prost` | Build (via build.rs) | Protobuf code generation |
| `thiserror` | Runtime | Error derive |
| `tokio` | Dev | Async test support |
| `serde` | Dev | JSON test support |

### chronik-client (TypeScript)

| Dependency | Type | Purpose |
|---|---|---|
| `axios` | Runtime | HTTP requests |
| `ws` / `isomorphic-ws` | Runtime | WebSocket client |
| `protobufjs` | Runtime | Protobuf decoding |

## Module Structure

```
bitcoinsuite-chronik-client/
├── build.rs          Compile chronik.proto via prost
├── proto/chronik.proto  Protobuf schema for Chronik API
├── src/lib.rs        ChronikClient (Rust), ScriptEndpoint, PluginEndpoint, error types
└── tests/test_chronik_client.rs  Integration tests (need running Chronik)

chronik-client/ (TypeScript)
├── index.ts          ChronikClient (JS), types, WS subscription manager
├── chronik.ts        Protobuf-generated TypeScript types
├── hex.ts            Hex encoding utilities
├── test/test.ts      Mocha tests
├── package.json      npm config, scripts, dependencies
├── tsconfig.json     TypeScript config
├── typedoc.json      Documentation config
└── .eslintrc.js      Lint rules
```

## Key Invariants

1. **Two separate clients** — The Rust client (`bitcoinsuite-chronik-client`) and TypeScript client (`chronik-client`) are independent implementations. This update validates the Rust client only; inherited TypeScript API/schema parity is not guaranteed.
2. **URL must not end with '/'** — Both clients enforce this at construction time. Trailing slash = error.
3. **HTTP + WebSocket** — Chronik provides REST endpoints for querying (blocks, txs, scripts) and WebSocket for real-time subscription (address tx notifications).
4. **Protobuf wire format** — The Rust client compiles the validated daemon protobuf via prost; the inherited TypeScript client uses its own schema.
5. **Script endpoint patterns** — REST endpoints follow pattern: `/script/:script_type/:script_payload`.
6. **Plugin support** — Chronik supports plugins with custom endpoints: `/plugin/:plugin_name/:payload`.

## Key Contracts

### Rust

| Contract | Type | Description |
|---|---|---|
| `ChronikClient` | struct: `new(url)`, `script()`, `plugin()`, `broadcast_tx()`, `subscribe()` | Main client class |
| `ScriptEndpoint` | builder: `utxos()`, `history()`, `slp()` etc. | Script query builder |
| `PluginEndpoint` | builder: `get()`, `post()` | Plugin query builder |
| `ScriptType` | enum: `Other`, `P2pk`, `P2pkh`, `P2sh`, `P2trCommitment`, `P2trState` | Script type for endpoints |
| `ChronikClientError` | enum with `#[critical()]` severity | Error types |

### TypeScript

| Contract | Type | Description |
|---|---|---|
| `ChronikClient` | class: `constructor(url)`, `script(type, payload)`, `plugin(name, payload)`, `broadcastTx(rawTx)`, WsSubscription | Main client class |
| `ScriptType` | type union: `"other" \| "p2pk" \| "p2pkh" \| "p2sh"` | Script type literal |
| `Tx` / `Block` / `ScriptUtxo` | TS interfaces matching protobuf messages | API response types |

## Lotus Rust protocol checks

`ScriptType::P2tr` queries a 33-byte commitment via `/script/p2tr/…`; stateful and stateless outputs share that key. The former commitment/state names are deprecated aliases, not independent indexes. `ChronikClient::block_header(height)` returns the complete 160-byte Lotus header. The current daemon protobuf adds unsigned transaction versions and broadcast finalization options (default timeout 0).

Public captured responses decode offline and are compared to the core RPC transaction fixtures. The opt-in `LOTUS_CHRONIK_URL` test reads real headers, block/transaction responses, raw transactions, and Taproot UTXOs without broadcasting. See the SDK README for commands and coverage.
