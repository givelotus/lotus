// Copyright (c) 2026 The Lotus developers
// Distributed under the MIT software license.
// Test adapters only. The runner inserts the candidate's actual entry struct
// and addTxs method at the markers below, without rewriting their logic.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <functional>
#include <iostream>
#include <memory>
#include <optional>
#include <stack>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
struct Amount {
    int64_t n = 0;
    Amount() = default;
    Amount(int64_t value) : n(value) {}
    static Amount zero() { return {}; }
    Amount &operator+=(Amount other) { n += other.n; return *this; }
    int64_t operator/(Amount other) const { return n / other.n; }
};
const Amount SATOSHI{1};
using TxId = int;
using SaltedTxIdHasher = std::hash<TxId>;
struct OutPoint { TxId id; const TxId &GetTxId() const { return id; } };
struct Input { OutPoint prevout; };
struct CTransaction {
    TxId id;
    std::vector<Input> vin;
    bool valid = true;
    const TxId &GetId() const { return id; }
};
using CTransactionRef = std::shared_ptr<const CTransaction>;
struct PoolEntry {
    CTransactionRef tx;
    Amount fee;
    size_t size;
    int64_t sigChecks;
    CTransactionRef GetSharedTx() const { return tx; }
    Amount GetFee() const { return fee; }
    Amount GetModifiedFee() const { return fee; }
    size_t GetTxSize() const { return size; }
    int64_t GetSigChecks() const { return sigChecks; }
};
struct entry_id {};
struct CTxMemPool {
    struct Map {
        std::vector<std::shared_ptr<PoolEntry>> entries;
        size_t size() const { return entries.size(); }
        template <class Tag> const auto &get() const { return entries; }
    } mapTx;
    std::optional<const PoolEntry *> GetIter(TxId id) const {
        for (const auto &entry : mapTx.entries) {
            if (entry->tx->id == id) return entry.get();
        }
        return std::nullopt;
    }
    void add(int id, std::vector<int> parents, int64_t fee,
             size_t size = 200, int64_t sigChecks = 1) {
        auto tx = std::make_shared<CTransaction>();
        tx->id = id;
        for (int parent : parents) tx->vin.push_back({{parent}});
        mapTx.entries.push_back(std::make_shared<PoolEntry>(
            PoolEntry{tx, fee, size, sigChecks}));
    }
};
struct CFeeRate {
    int64_t perK;
    CFeeRate(Amount fee, size_t size) : perK(size ? 1000 * fee.n / size : 0) {}
};
struct Fitter {
    uint64_t nBlockSize = 1000; // upstream coinbase reservation
    uint64_t nBlockSigChecks = 100;
    uint64_t maxSize = 1000000;
    uint64_t maxSigChecks = 1000000;
    int64_t minFeePerK = 1000;
    bool testTxFits(uint64_t size, int64_t sigChecks) const {
        // Same strict inequalities as pinned src/node/blockfitter.cpp.
        return nBlockSize + size < maxSize &&
               nBlockSigChecks + sigChecks < maxSigChecks;
    }
    bool isBelowBlockMinFeeRate(const CFeeRate &fee) const {
        return fee.perK < minFeePerK;
    }
};
// INSERT_CANDIDATE_ENTRY
struct BlockAssembler {
    Fitter blockFitter;
    std::vector<int> included;
    size_t checks = 0;
    bool CheckTx(const CTransaction &tx) { ++checks; return tx.valid; }
    void AddToBlock(const PoolEntry &entry) {
        included.push_back(entry.tx->id);
        blockFitter.nBlockSize += entry.size;
        blockFitter.nBlockSigChecks += entry.sigChecks;
    }
    void addTxs(const CTxMemPool &mempool);
};
// INSERT_CANDIDATE_METHOD
int main() {
    {
        CTxMemPool pool;
        pool.add(1, {}, 2000);
        pool.add(2, {1}, 1000);
        BlockAssembler miner;
        miner.blockFitter.maxSize = 1401;
        miner.addTxs(pool);
        assert(miner.included == std::vector<int>{1});
        assert(miner.blockFitter.testTxFits(200, 1));
        std::cout << "CONFIRMED size regression: child fits, but only parent selected\n";
    }
    {
        CTxMemPool pool;
        pool.add(1, {}, 2000);
        pool.add(2, {1}, 1000);
        BlockAssembler miner;
        miner.blockFitter.maxSigChecks = 103;
        miner.addTxs(pool);
        assert(miner.included == std::vector<int>{1});
        assert(miner.blockFitter.testTxFits(200, 1));
        std::cout << "CONFIRMED sigchecks regression: child fits, but only parent selected\n";
    }
    {
        CTxMemPool pool;
        pool.add(1, {}, 0);
        pool.add(2, {1}, 10000);
        BlockAssembler miner;
        miner.addTxs(pool);
        assert(miner.included.empty());
        std::cout << "CONFIRMED package-fee limitation: paying child does not rescue parent\n";
    }
    {
        CTxMemPool pool;
        pool.add(1, {}, 10000);
        pool.add(2, {1}, 0);
        BlockAssembler miner;
        miner.addTxs(pool);
        assert((miner.included == std::vector<int>{1, 2}));
        std::cout << "CONFIRMED fee regression: already-mined parent subsidizes free child\n";
    }
    {
        CTxMemPool pool;
        pool.add(1, {}, 1000);
        pool.add(2, {1}, 1000);
        pool.add(3, {1}, 1000);
        pool.add(4, {2, 3}, 1000);
        std::vector<CBlockTemplateEntry> entries;
        for (const auto &entry : pool.mapTx.entries)
            entries.emplace_back(entry->tx, entry->fee, entry->fee,
                                 entry->size, entry->sigChecks);
        entries[1].AccountForParent(entries[0]);
        entries[2].AccountForParent(entries[0]);
        entries[3].AccountForParent(entries[1]);
        entries[3].AccountForParent(entries[2]);
        assert(entries[3].packageSize == 1000); // actual unique total 800
        assert(entries[3].packageFees.n == 5000); // actual unique total 4000
        assert(entries[3].packageSigChecks == 5); // actual unique total 4
        std::cout << "CONFIRMED diamond accounting: 5 entries charged for 4 unique txs\n";
    }
    {
        // Distinct outputs of one parent may occur twice in vin. Inputs here
        // model only their parent TxIds, exactly what the candidate reads.
        CTxMemPool pool;
        pool.add(1, {}, 1000);
        for (int id = 2; id <= 17; ++id)
            pool.add(id, {id - 1, id - 1}, 1000 * id);
        BlockAssembler miner;
        miner.addTxs(pool);
        assert(miner.included.size() == 17);
        assert(miner.checks == 17);
        std::cout << "CONTROL repeated-parent chain: 17 txs, 17 checks end to end; "
                     "no reachable exponential DFS demonstrated\n";
    }
    {
        // Independent paid transactions: verify fitting and fee adapters.
        CTxMemPool pool;
        pool.add(1, {}, 0);
        pool.add(2, {}, 1000);
        pool.add(3, {}, 2000);
        BlockAssembler miner;
        miner.blockFitter.maxSize = 1401;
        miner.addTxs(pool);
        assert((miner.included == std::vector<int>{3, 2}));
        assert(miner.blockFitter.nBlockSize == 1400);
        std::cout << "CONTROL independent fee selection and block-size limit pass\n";
    }
}
