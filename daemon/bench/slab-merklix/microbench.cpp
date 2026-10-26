// Copyright (c) 2026 The Lotus developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.
//
// Microbenchmarks: legacy TxOverlayArena / legacy full-recon snapshot build
// versus the slab Merklix tree (lotus_v2/tx_merklix). Links the build's
// static libraries; no node, network or disk. Prints one JSON object per
// measurement. These are microbenchmarks, not end-to-end node results.

#include <lotus_v2/commitment.h>
#include <lotus_v2/mempool_overlay.h>
#include <lotus_v2/minhash.h>
#include <lotus_v2/tx_merklix.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <memory>
#include <new>
#include <random>
#include <string>
#include <thread>
#include <vector>

using namespace lotus::v2;
namespace txm = lotus::v2::txmerklix;

// ---------------------------------------------------------------------------
// Heap allocation counter (all operator new calls in this process).
static std::atomic<uint64_t> g_allocs{0};
void *operator new(size_t n) {
    g_allocs.fetch_add(1, std::memory_order_relaxed);
    if (void *p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void *operator new[](size_t n) { return ::operator new(n); }
void *operator new(size_t n, std::align_val_t a) {
    g_allocs.fetch_add(1, std::memory_order_relaxed);
    void *p = nullptr;
    if (posix_memalign(&p, std::max<size_t>(size_t(a), sizeof(void *)), n ? n : 1) == 0) return p;
    throw std::bad_alloc();
}
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete(void *p, size_t) noexcept { std::free(p); }
void operator delete[](void *p, size_t) noexcept { std::free(p); }
void operator delete(void *p, std::align_val_t) noexcept { std::free(p); }
void operator delete(void *p, size_t, std::align_val_t) noexcept { std::free(p); }

namespace {
using Clock = std::chrono::steady_clock;
double Ms(Clock::time_point a, Clock::time_point b) {
    return std::chrono::duration<double, std::milli>(b - a).count();
}
Hash Rand(std::mt19937_64 &rng) {
    Hash h;
    for (size_t i = 0; i < 32; i += 8) {
        const uint64_t v = rng();
        for (size_t j = 0; j < 8; ++j) h[i + j] = uint8_t(v >> (8 * j));
    }
    return h;
}
uint64_t Stat(const std::atomic<uint64_t> &a) { return a.load(); }

// Faithful copy of the replaced full-recon capture build (canonical 527,
// net/full_mempool_reconciliation.cpp): copy items + refs, sort in canonical
// bit order, build the compressed trie and hash every node eagerly.
struct LegacyRecon {
    struct Item { Hash id, hash; std::shared_ptr<const void> tx; };
    struct Node {
        size_t begin, end;
        uint32_t left{0}, right{0};
        uint16_t split{256};
        Hash digest{};
    };
    std::vector<Item> items;
    std::vector<Node> nodes;
    static bool Bit(const Hash &id, unsigned bit) { return (id[bit / 8] >> (bit % 8)) & 1; }
    static bool Less(const Hash &a, const Hash &b) {
        for (unsigned i = 0; i < 256; ++i)
            if (Bit(a, i) != Bit(b, i)) return !Bit(a, i);
        return false;
    }
    Hash NodeAt(uint32_t index, unsigned depth) const {
        const auto &node = nodes[index];
        Hash d = node.digest;
        if (node.end - node.begin == 1) return d;
        for (unsigned s = node.split; s > depth; --s) {
            d = Bit(items[node.begin].id, s - 1) ? txm::BranchDigest(s - 1, txm::EmptyDigest(), d)
                                                 : txm::BranchDigest(s - 1, d, txm::EmptyDigest());
        }
        return d;
    }
    uint32_t Build(size_t begin, size_t end) {
        const uint32_t index = uint32_t(nodes.size());
        nodes.push_back(Node{begin, end});
        if (end - begin == 1) {
            nodes[index].digest = txm::LeafDigest(items[begin].id, items[begin].hash);
            return index;
        }
        unsigned split = 0;
        while (Bit(items[begin].id, split) == Bit(items[end - 1].id, split)) ++split;
        const auto middle = std::partition_point(items.begin() + begin, items.begin() + end,
                                                 [&](const Item &i) { return !Bit(i.id, split); });
        const size_t offset = size_t(middle - items.begin());
        const uint32_t l = Build(begin, offset), r = Build(offset, end);
        nodes[index].left = l;
        nodes[index].right = r;
        nodes[index].split = uint16_t(split);
        nodes[index].digest = txm::BranchDigest(split, NodeAt(l, split + 1), NodeAt(r, split + 1));
        return index;
    }
    LegacyRecon(const std::vector<Item> &source) {
        items.reserve(source.size());
        nodes.reserve(source.size() * 2);
        for (const auto &i : source) items.push_back(i); // ref copies (under locks in production)
        std::sort(items.begin(), items.end(), [](const Item &a, const Item &b) { return Less(a.id, b.id); });
        if (!items.empty()) Build(0, items.size());
    }
    Hash Root() const { return items.empty() ? txm::EmptyDigest() : NodeAt(0, 0); }
    size_t Bytes() const { return items.capacity() * sizeof(Item) + nodes.capacity() * sizeof(Node); }
};

void Emit(const std::string &json) { std::printf("%s\n", json.c_str()); std::fflush(stdout); }
std::string F(double v) { char b[64]; std::snprintf(b, sizeof b, "%.4f", v); return b; }
std::string U(uint64_t v) { return std::to_string(v); }

void Run(size_t n, unsigned seed) {
    std::mt19937_64 rng(seed);
    std::vector<std::pair<Hash, Hash>> members(n);
    for (auto &[id, h] : members) { id = Rand(rng); h = Rand(rng); }
    auto payload = std::make_shared<int>(0);
    const std::string N = "\"n\":" + U(n);

    // A. Populate by individual inserts (admission-style), unshared.
    TxOverlayArena arena;
    uint32_t aroot = TxOverlayArena::kNullIdx;
    uint64_t a0 = g_allocs;
    auto t0 = Clock::now();
    for (const auto &[id, h] : members) aroot = arena.InsertTxLeaf(aroot, id, h);
    auto t1 = Clock::now();
    const uint64_t arena_allocs = g_allocs - a0;
    Emit("{\"phase\":\"populate\",\"impl\":\"legacy_arena\"," + N + ",\"ms\":" + F(Ms(t0, t1)) +
         ",\"ns_per_op\":" + F(Ms(t0, t1) * 1e6 / n) + ",\"heap_allocs\":" + U(arena_allocs) +
         ",\"retained_bytes\":" + U(arena.ArenaNodeCount() * sizeof(TxOverlayNode)) + "}");

    txm::Tree tree;
    const uint64_t leaf0 = Stat(txm::Stats().leaf_allocs), br0 = Stat(txm::Stats().branch_allocs);
    a0 = g_allocs;
    t0 = Clock::now();
    for (const auto &[id, h] : members) tree.Insert(id, h, payload, 400);
    t1 = Clock::now();
    Emit("{\"phase\":\"populate\",\"impl\":\"slab_tree\"," + N + ",\"ms\":" + F(Ms(t0, t1)) +
         ",\"ns_per_op\":" + F(Ms(t0, t1) * 1e6 / n) + ",\"heap_allocs\":" + U(g_allocs - a0) +
         ",\"node_allocs\":" + U(Stat(txm::Stats().leaf_allocs) - leaf0 + Stat(txm::Stats().branch_allocs) - br0) +
         ",\"retained_bytes\":" + U(tree.GetStore()->RetainedBytes()) + "}");

    // B. First full commitment of an all-dirty version.
    t0 = Clock::now();
    const Hash aroot_digest = arena.SubtreeARoot(aroot);
    t1 = Clock::now();
    Emit("{\"phase\":\"first_commitment\",\"impl\":\"legacy_arena\"," + N + ",\"ms\":" + F(Ms(t0, t1)) + "}");
    const uint64_t h0 = Stat(txm::Stats().node_hashes);
    t0 = Clock::now();
    const Hash troot = tree.RootDigest();
    t1 = Clock::now();
    Emit("{\"phase\":\"first_commitment\",\"impl\":\"slab_tree\"," + N + ",\"ms\":" + F(Ms(t0, t1)) +
         ",\"node_hashes\":" + U(Stat(txm::Stats().node_hashes) - h0) +
         ",\"equal_roots\":" + (troot == aroot_digest ? "true" : "false") + "}");

    // C. Reconciliation snapshot capture (+ first root) for the same membership.
    std::vector<LegacyRecon::Item> source;
    source.reserve(n);
    for (const auto &[id, h] : members) source.push_back({id, h, payload});
    a0 = g_allocs;
    t0 = Clock::now();
    LegacyRecon legacy(source);
    const Hash lroot = legacy.Root();
    t1 = Clock::now();
    Emit("{\"phase\":\"capture_and_root\",\"impl\":\"legacy_recon_rebuild\"," + N + ",\"ms\":" + F(Ms(t0, t1)) +
         ",\"heap_allocs\":" + U(g_allocs - a0) + ",\"retained_bytes\":" + U(legacy.Bytes()) +
         ",\"equal_roots\":" + (lroot == troot ? "true" : "false") + "}");
    a0 = g_allocs;
    t0 = Clock::now();
    auto pinned = tree.Pin();
    t1 = Clock::now();
    const Hash proot = pinned->RootDigest();
    auto t2 = Clock::now();
    Emit("{\"phase\":\"capture_and_root\",\"impl\":\"slab_pin\"," + N + ",\"pin_us\":" + F(Ms(t0, t1) * 1e3) +
         ",\"root_after_pin_us\":" + F(Ms(t1, t2) * 1e3) + ",\"heap_allocs\":" + U(g_allocs - a0) +
         ",\"equal_roots\":" + (proot == troot ? "true" : "false") + "}");

    // D. Batched random reconciliation updates with the advertised snapshot
    // pinned (forces path copies), then lazy completion of the new version.
    for (size_t batch : {size_t{100}, size_t{1000}, size_t{10000}}) {
        if (batch > n) continue;
        std::vector<size_t> victims(batch / 2);
        for (auto &v : victims) v = rng() % members.size();
        std::sort(victims.begin(), victims.end());
        victims.erase(std::unique(victims.begin(), victims.end()), victims.end());
        std::vector<std::pair<Hash, Hash>> adds(batch - victims.size());
        for (auto &[id, h] : adds) { id = Rand(rng); h = Rand(rng); }

        const size_t arena_before = arena.ArenaNodeCount();
        t0 = Clock::now();
        for (size_t v : victims) aroot = arena.EraseTxLeaf(aroot, members[v].first);
        for (const auto &[id, h] : adds) aroot = arena.InsertTxLeaf(aroot, id, h);
        t1 = Clock::now();
        const Hash ar = arena.SubtreeARoot(aroot);
        t2 = Clock::now();
        Emit("{\"phase\":\"batch_update\",\"impl\":\"legacy_arena\"," + N + ",\"batch\":" + U(batch) +
             ",\"update_ms\":" + F(Ms(t0, t1)) + ",\"commit_ms\":" + F(Ms(t1, t2)) +
             ",\"retained_growth_bytes\":" + U((arena.ArenaNodeCount() - arena_before) * sizeof(TxOverlayNode)) + "}");

        auto advertised = tree.Pin();
        const uint64_t c0 = Stat(txm::Stats().path_copies), i0 = Stat(txm::Stats().inplace_updates);
        const uint64_t hs0 = Stat(txm::Stats().node_hashes);
        const size_t live_before = tree.GetStore()->LiveBranches() + tree.GetStore()->LiveLeaves();
        t0 = Clock::now();
        for (size_t v : victims) tree.Erase(members[v].first);
        for (const auto &[id, h] : adds) tree.Insert(id, h, payload, 400);
        t1 = Clock::now();
        const Hash tr = tree.RootDigest();
        t2 = Clock::now();
        const size_t live_after = tree.GetStore()->LiveBranches() + tree.GetStore()->LiveLeaves();
        Emit("{\"phase\":\"batch_update\",\"impl\":\"slab_tree_pinned\"," + N + ",\"batch\":" + U(batch) +
             ",\"update_ms\":" + F(Ms(t0, t1)) + ",\"commit_ms\":" + F(Ms(t1, t2)) +
             ",\"path_copies\":" + U(Stat(txm::Stats().path_copies) - c0) +
             ",\"inplace\":" + U(Stat(txm::Stats().inplace_updates) - i0) +
             ",\"node_hashes\":" + U(Stat(txm::Stats().node_hashes) - hs0) +
             ",\"live_node_growth\":" + std::to_string(int64_t(live_after) - int64_t(live_before)) +
             ",\"equal_roots\":" + (tr == ar ? "true" : "false") + "}");
        // Releasing the superseded advertised version (reclamation pause).
        t0 = Clock::now();
        advertised.reset();
        t1 = Clock::now();
        Emit("{\"phase\":\"release_superseded_snapshot\",\"impl\":\"slab_tree\"," + N + ",\"batch\":" + U(batch) +
             ",\"us\":" + F(Ms(t0, t1) * 1e3) + "}");
        // Keep the member list consistent for later phases.
        for (size_t k = victims.size(); k-- > 0;) {
            members[victims[k]] = members.back();
            members.pop_back();
        }
        for (const auto &a : adds) members.push_back(a);
    }
    pinned.reset();

    // E. Repeated edits on shared paths: 64 hot keys re-hashed 10000 times
    // while one snapshot is pinned.
    {
        std::vector<size_t> hot(64);
        for (auto &h : hot) h = rng() % members.size();
        const size_t arena_before = arena.ArenaNodeCount();
        t0 = Clock::now();
        for (int i = 0; i < 10000; ++i) {
            auto &m = members[hot[size_t(i) % hot.size()]];
            m.second = Rand(rng);
            aroot = arena.InsertTxLeaf(aroot, m.first, m.second);
        }
        t1 = Clock::now();
        (void)arena.SubtreeARoot(aroot);
        t2 = Clock::now();
        Emit("{\"phase\":\"repeated_shared_path_edits\",\"impl\":\"legacy_arena\"," + N +
             ",\"update_ms\":" + F(Ms(t0, t1)) + ",\"commit_ms\":" + F(Ms(t1, t2)) +
             ",\"retained_growth_bytes\":" + U((arena.ArenaNodeCount() - arena_before) * sizeof(TxOverlayNode)) + "}");
        // Same edits replayed on the tree (identical final membership).
        auto snap = tree.Pin();
        std::mt19937_64 replay(seed ^ 0x55);
        const uint64_t c0 = Stat(txm::Stats().path_copies);
        const size_t live_before = tree.GetStore()->LiveBranches() + tree.GetStore()->LiveLeaves();
        t0 = Clock::now();
        for (int i = 0; i < 10000; ++i) {
            const auto &m = members[hot[size_t(i) % hot.size()]];
            tree.Insert(m.first, i + 64 >= 10000 ? m.second : Rand(replay), payload, 400);
        }
        t1 = Clock::now();
        const Hash tr = tree.RootDigest();
        t2 = Clock::now();
        const size_t live_after = tree.GetStore()->LiveBranches() + tree.GetStore()->LiveLeaves();
        Emit("{\"phase\":\"repeated_shared_path_edits\",\"impl\":\"slab_tree_pinned\"," + N +
             ",\"update_ms\":" + F(Ms(t0, t1)) + ",\"commit_ms\":" + F(Ms(t1, t2)) +
             ",\"path_copies\":" + U(Stat(txm::Stats().path_copies) - c0) +
             ",\"live_node_growth\":" + std::to_string(int64_t(live_after) - int64_t(live_before)) +
             ",\"equal_roots\":" + (tr == arena.SubtreeARoot(aroot) ? "true" : "false") + "}");
    }

    // F. Epoch freeze copy.
    t0 = Clock::now();
    TxOverlayArena frozen_arena = arena;
    t1 = Clock::now();
    Emit("{\"phase\":\"epoch_freeze_copy\",\"impl\":\"legacy_arena\"," + N + ",\"us\":" + F(Ms(t0, t1) * 1e3) +
         ",\"copied_bytes\":" + U(frozen_arena.ArenaNodeCount() * sizeof(TxOverlayNode)) + "}");
    t0 = Clock::now();
    txm::Tree frozen_tree = tree;
    t1 = Clock::now();
    Emit("{\"phase\":\"epoch_freeze_copy\",\"impl\":\"slab_tree\"," + N + ",\"us\":" + F(Ms(t0, t1) * 1e3) +
         ",\"copied_bytes\":0}");

    // G. Lookup throughput (members by TxId): slab tree vs std::map (the
    // overlay's existing active entry index).
    {
        std::map<Hash, Hash> index(members.begin(), members.end());
        std::vector<Hash> probes(200000);
        for (auto &p : probes) p = members[rng() % members.size()].first;
        size_t hits = 0;
        t0 = Clock::now();
        for (const auto &p : probes) hits += tree.Contains(p);
        t1 = Clock::now();
        for (const auto &p : probes) hits += index.count(p);
        t2 = Clock::now();
        Emit("{\"phase\":\"lookup\",\"impl\":\"slab_tree\"," + N + ",\"ns_per_lookup\":" + F(Ms(t0, t1) * 1e6 / probes.size()) + "}");
        Emit("{\"phase\":\"lookup\",\"impl\":\"std_map_entry_index\"," + N + ",\"ns_per_lookup\":" + F(Ms(t1, t2) * 1e6 / probes.size()) +
             ",\"hits\":" + U(hits) + "}");
    }

    // H. Long-lived snapshot during 10 rounds of 10% churn with a transient
    // advertised pin per round: retained memory and its release.
    {
        // The epoch-freeze measurement must not keep another owner of the
        // same old root, or resetting oldest would measure only a decrement.
        frozen_tree = txm::Tree(tree.GetStore());
        auto oldest = tree.Pin();
        const size_t arena_before = arena.ArenaNodeCount();
        for (int round = 0; round < 10; ++round) {
            auto transient = tree.Pin();
            for (size_t i = 0; i < n / 10; ++i) {
                const size_t v = rng() % members.size();
                tree.Erase(members[v].first);
                aroot = arena.EraseTxLeaf(aroot, members[v].first);
                members[v] = {Rand(rng), Rand(rng)};
                tree.Insert(members[v].first, members[v].second, payload, 400);
                aroot = arena.InsertTxLeaf(aroot, members[v].first, members[v].second);
            }
            (void)tree.RootDigest();
            (void)arena.SubtreeARoot(aroot);
        }
        const size_t with_old = tree.GetStore()->RetainedBytes();
        const size_t live_with_old = tree.GetStore()->LiveBranches() + tree.GetStore()->LiveLeaves();
        t0 = Clock::now();
        oldest.reset();
        t1 = Clock::now();
        const size_t live_after = tree.GetStore()->LiveBranches() + tree.GetStore()->LiveLeaves();
        Emit("{\"phase\":\"long_lived_snapshot_churn\",\"impl\":\"legacy_arena\"," + N +
             ",\"retained_growth_bytes\":" + U((arena.ArenaNodeCount() - arena_before) * sizeof(TxOverlayNode)) +
             ",\"retained_total_bytes\":" + U(arena.ArenaNodeCount() * sizeof(TxOverlayNode)) + "}");
        Emit("{\"phase\":\"long_lived_snapshot_churn\",\"impl\":\"slab_tree\"," + N +
             ",\"retained_slot_bytes\":" + U(with_old) + ",\"live_nodes_with_old\":" + U(live_with_old) +
             ",\"live_nodes_after_release\":" + U(live_after) + ",\"release_us\":" + F(Ms(t0, t1) * 1e3) +
             ",\"equal_roots\":" + (tree.RootDigest() == arena.SubtreeARoot(aroot) ? "true" : "false") + "}");
    }

    // I. MinHash exactness and costs at this size.
    {
        std::map<Hash, Hash> m(members.begin(), members.end());
        std::vector<uint64_t> values;
        for (const auto &[id, h] : m) values.push_back(minhash::Value(id, h));
        const bool exact = tree.CurrentSketch().values == minhash::Reference(values);
        t0 = Clock::now();
        minhash::Maintainer rebuild;
        rebuild.Rebuild(values);
        t1 = Clock::now();
        Emit("{\"phase\":\"minhash\",\"impl\":\"slab_tree\"," + N + ",\"exact_vs_reference\":" +
             (exact ? "true" : "false") + ",\"rebuild_ms_values_only\":" + F(Ms(t0, t1)) +
             ",\"rebuilds_so_far\":" + U(Stat(txm::Stats().sketch_rebuilds)) + "}");
    }
}
} // namespace

int main(int argc, char **argv) {
    std::vector<size_t> sizes;
    for (int i = 1; i < argc; ++i) sizes.push_back(std::strtoull(argv[i], nullptr, 10));
    if (sizes.empty()) sizes = {5000, 100000, 500000};
    for (size_t n : sizes) Run(n, unsigned(n));
    return 0;
}
