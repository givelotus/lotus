# Bitcoin Core patches

Pinned base and acceptance target: Bitcoin Core `f13ae519de94394314cd63a27924b0998ac65d45` (also verified against latest master `cce32b16874e85e8a00cfa1a2190f0b6f4dcaf66`).

These patches are split into a clean 3-commit stack suitable for upstream review:

| File | Actual change | Status |
|---|---|---|
| `01-dbwrapper-backend-interface.patch` | Pure refactor in `src/dbwrapper.{h,cpp}` abstracting `CDBWrapper`'s `m_db_context`, `CDBBatch::WriteBatchImpl`, and `CDBIterator::IteratorImpl` behind polymorphic adaptor interfaces (`DBContext`, `WriteBatchImpl`, `IteratorImpl`) implemented by `LevelDBContext` | Zero new dependencies and zero behavior changes. Compiles and passes all `dbwrapper_tests` standalone. |
| `02-vendor-libmdbx.patch` | Vendors unmodified upstream amalgamated `libmdbx` v0.14.4 (`src/libmdbx/{LICENSE,mdbx.h,mdbx-internals.h,mdbx.c}`) | Pure upstream vendor commit (`git subtree` / amalgamated distribution). |
| `03-dbwrapper-libmdbx-backend.patch` | Adds `cmake/libmdbx.cmake`, `MdbxContext` in `src/dbwrapper.cpp`, `-dbbackend=leveldb\|mdbx` startup flag (default: `leveldb`) in `src/init.cpp`, non-destructive bidirectional LevelDB $\leftrightarrow$ `libmdbx` migration (`leveldb.bak/` and `mdbx.bak/`), `HasKeyStartingWith` support for both backends, and `mdbx_backend_and_migration` unit test in `src/test/dbwrapper_tests.cpp` | Allocates the concrete backend adaptor once on `CDBWrapper` initialization with zero per-operation config lookups. Passes `test_bitcoin -t dbwrapper_tests,txindex_tests` and live `bitcoind -regtest` round-trip migration (`leveldb` $\to$ `mdbx` $\to$ `leveldb`). |
