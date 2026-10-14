// Copyright (c) 2026 The Lotus developers
// Distributed under the MIT software license.
// Adapters for operation counts of the actual corrected addTxs method.
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iostream>
#include <memory>
#include <queue>
#include <set>
#include <unordered_map>
#include <utility>
#include <vector>
static size_t edgesWalked = 0, hashCalls = 0, comparisons = 0;
using TxId = int;
struct SaltedTxIdHasher {
    size_t operator()(TxId id) const { ++hashCalls; return std::hash<int>{}(id); }
};
struct CTransaction {
    TxId id;
    bool valid = true;
    const TxId &GetId() const { return id; }
};
struct CFeeRate {
    int64_t perK;
    bool operator<(CFeeRate other) const { return perK < other.perK; }
};
struct PoolEntry;
using CTxMemPoolEntryRef = std::shared_ptr<PoolEntry>;
struct ParentRange {
    std::set<CTxMemPoolEntryRef> values;
    size_t size() const { return values.size(); }
    struct Iterator {
        std::set<CTxMemPoolEntryRef>::const_iterator position;
        const CTxMemPoolEntryRef &operator*() const { return *position; }
        Iterator &operator++() { ++edgesWalked; ++position; return *this; }
        bool operator!=(Iterator other) const { return position != other.position; }
    };
    Iterator begin() const { return {values.begin()}; }
    Iterator end() const { return {values.end()}; }
};
struct PoolEntry {
    CTransaction tx;
    int64_t fee;
    ParentRange parents;
    const CTransaction &GetTx() const { return tx; }
    const ParentRange &GetMemPoolParentsConst() const { return parents; }
    CFeeRate GetModifiedFeeRate() const { return {1000 * fee / 200}; }
    size_t GetTxSize() const { return 200; }
    int64_t GetSigChecks() const { return 1; }
};
struct CompareTxMemPoolEntryByModifiedFeeRate {
    bool operator()(const CTxMemPoolEntryRef &a, const CTxMemPoolEntryRef &b) const {
        ++comparisons;
        if (a->GetModifiedFeeRate().perK != b->GetModifiedFeeRate().perK)
            return a->GetModifiedFeeRate().perK > b->GetModifiedFeeRate().perK;
        return a->tx.id < b->tx.id;
    }
};
struct entry_id {};
struct CTxMemPool {
    struct Map {
        std::vector<CTxMemPoolEntryRef> entries;
        size_t size() const { return entries.size(); }
        template<class Tag> const auto &get() const { return entries; }
    } mapTx;
    void add(std::vector<int> parents = {}, int64_t fee = 1000) {
        const auto id = static_cast<int>(mapTx.entries.size());
        auto entry = std::make_shared<PoolEntry>();
        entry->tx.id = id;
        entry->fee = fee;
        for (int parent : parents) entry->parents.values.insert(mapTx.entries.at(parent));
        mapTx.entries.push_back(entry);
    }
};
struct Fitter {
    uint64_t size = 1000, sigChecks = 100;
    bool isBelowBlockMinFeeRate(CFeeRate fee) const { return fee.perK < 1000; }
    bool testTxFits(uint64_t txSize, int64_t checks) const {
        return size + txSize < 1000000000 && sigChecks + checks < 1000000000;
    }
    uint64_t getMaxGeneratedBlockSize() const { return 1000000000; }
    uint64_t nBlockSize = 1000;
};
struct BlockAssembler {
    Fitter blockFitter;
    std::vector<int> included;
    std::vector<bool> present;
    size_t checks = 0;
    bool CheckTx(const CTransaction &tx) { ++checks; return tx.valid; }
    void AddToBlock(const CTxMemPoolEntryRef &entry) {
        for (const auto &parent : entry->parents.values) assert(present.at(parent->tx.id));
        assert(!present.at(entry->tx.id));
        present[entry->tx.id] = true;
        included.push_back(entry->tx.id);
        blockFitter.size += entry->GetTxSize();
        blockFitter.nBlockSize = blockFitter.size;
        blockFitter.sigChecks += entry->GetSigChecks();
    }
    void addTxs(const CTxMemPool &mempool);
};
// INSERT_CANDIDATE_METHOD
static void run(const char *name, CTxMemPool &pool, size_t edges) {
    edgesWalked = hashCalls = comparisons = 0;
    BlockAssembler miner;
    miner.present.resize(pool.mapTx.size());
    miner.addTxs(pool);
    const size_t count = pool.mapTx.size();
    assert(miner.included.size() == count);
    assert(miner.checks == count);
    assert(edgesWalked == edges);
    assert(hashCalls < 10 * (count + edges));
    const auto logBound = static_cast<size_t>(std::ceil(std::log2(count + 1)));
    assert(comparisons <= 6 * count * logBound);
    std::cout << name << ": n=" << count << " m=" << edges
              << " edge-walks=" << edgesWalked << " checks=" << miner.checks
              << " hash-calls=" << hashCalls << " heap-comparisons=" << comparisons << '\n';
}
int main() {
    CTxMemPool chain;
    chain.add();
    for (int i = 1; i < 10000; ++i) chain.add({i - 1});
    run("chain", chain, 9999);
    CTxMemPool diamonds;
    diamonds.add(); diamonds.add({0}); diamonds.add({0});
    for (int layer = 0; layer < 5000; ++layer) {
        int last = static_cast<int>(diamonds.mapTx.size()) - 1;
        diamonds.add({last - 1, last}); diamonds.add({last - 1, last});
    }
    run("layered-diamonds", diamonds, 20002);
    CTxMemPool fanout;
    fanout.add();
    for (int i = 1; i < 10000; ++i) fanout.add({0}, 1000 + (i * 7919) % 10000);
    run("wide-fanout", fanout, 9999);
    CTxMemPool repeated;
    repeated.add();
    for (int i = 1; i < 10000; ++i) repeated.add({i - 1, i - 1});
    run("repeated-parent-inputs", repeated, 9999);
}
