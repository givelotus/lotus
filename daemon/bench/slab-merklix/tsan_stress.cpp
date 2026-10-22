// Copyright (c) 2026 The Lotus developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.
//
// Standalone ThreadSanitizer stress for lotus_v2/tx_merklix (no node linkage).
// One writer mutates, hashes and pins; reader threads hash the same pinned
// versions concurrently (CAS cache races), enumerate leaves, resolve weak
// handles that are concurrently freed and reused, and release snapshots off
// the writer thread while the writer keeps allocating from the same slabs.
// Every pinned root is checked against the consensus reference computed from
// the writer's recorded membership.

#include <lotus_v2/commitment.h>
#include <lotus_v2/minhash.h>
#include <lotus_v2/tx_merklix.h>

#include <atomic>
#include <cstdio>
#include <deque>
#include <map>
#include <mutex>
#include <random>
#include <thread>
#include <vector>

using namespace lotus::v2;

namespace {
Hash Rand(std::mt19937_64 &rng) {
    Hash h;
    for (size_t i = 0; i < 32; i += 8) {
        const uint64_t v = rng();
        for (size_t j = 0; j < 8; ++j) h[i + j] = uint8_t(v >> (8 * j));
    }
    return h;
}
Hash Reference(const std::map<Hash, Hash> &m) {
    std::vector<TxIdentityPair> pairs;
    for (const auto &[id, h] : m) pairs.push_back({h, id});
    return TransactionSubtreeARoot(pairs);
}
std::vector<uint64_t> RefSketch(const std::map<Hash, Hash> &m) {
    std::vector<uint64_t> v;
    for (const auto &[id, h] : m) v.push_back(minhash::Value(id, h));
    return minhash::Reference(std::move(v));
}
} // namespace

int main(int argc, char **argv) {
    const int rounds = argc > 1 ? std::atoi(argv[1]) : 200;
    std::mt19937_64 rng(7);
    auto store = txmerklix::Store::Create();
    txmerklix::Tree tree{store};
    std::map<Hash, Hash> members;
    for (int i = 0; i < 2000; ++i) {
        const Hash id = Rand(rng), h = Rand(rng);
        members.emplace(id, h);
        tree.Insert(id, h);
    }
    struct Work {
        std::shared_ptr<const txmerklix::Snapshot> snap;
        Hash expected;
        std::vector<uint64_t> sketch;
        size_t count;
        txmerklix::Store::WeakRef weak;
    };
    std::mutex mu;
    std::mutex writer; // family ownership lock: mutation, pin and weak retain
    std::deque<Work> queue;
    std::atomic<bool> done{false};
    std::atomic<int> failures{0}, checked{0}, weak_hits{0}, weak_misses{0};
    std::vector<txmerklix::Store::WeakRef> stale; // guarded by mu
    auto reader = [&] {
        for (;;) {
            Work w;
            std::vector<txmerklix::Store::WeakRef> probes;
            {
                std::lock_guard<std::mutex> lock(mu);
                if (!queue.empty()) {
                    w = std::move(queue.front());
                    queue.pop_front();
                }
                probes = stale;
            }
            for (const auto &weak : probes) {
                // Resolve handles whose snapshots may have been freed and
                // whose slots may be reused concurrently by the writer.
                std::lock_guard<std::mutex> ownership(writer);
                const auto n = store->TryRetain(weak);
                if (n != txmerklix::kNull) {
                    ++weak_hits;
                    store->Release(n);
                } else {
                    ++weak_misses;
                }
            }
            if (!w.snap) {
                if (done) return;
                std::this_thread::yield();
                continue;
            }
            Hash a{}, b{};
            std::thread twin([&] {
                b = w.snap->RootDigest();
                if (w.snap->GetSketch().values != w.sketch) ++failures;
            });
            a = w.snap->RootDigest();
            twin.join();
            size_t leaves = 0;
            w.snap->ForEachLeaf([&](const txmerklix::Leaf &) { ++leaves; });
            if (a != w.expected || b != w.expected || leaves != w.count ||
                w.snap->GetSketch().values != w.sketch) {
                ++failures;
            }
            ++checked;
            w.snap.reset();
        }
    };
    std::vector<std::thread> readers;
    for (int i = 0; i < 4; ++i) readers.emplace_back(reader);
    for (int r = 0; r < rounds; ++r) {
        std::lock_guard<std::mutex> ownership(writer);
        for (int i = 0; i < 40; ++i) {
            const int op = int(rng() % 3);
            if (op == 0 || members.empty()) {
                const Hash id = Rand(rng), h = Rand(rng);
                members.emplace(id, h);
                tree.Insert(id, h);
            } else {
                auto it = members.begin();
                std::advance(it, rng() % members.size());
                if (op == 1) {
                    tree.Erase(it->first);
                    members.erase(it);
                } else {
                    it->second = Rand(rng);
                    tree.Insert(it->first, it->second);
                }
            }
        }
        if (r % 5 == 0) (void)tree.RootDigest();
        Work w{tree.Pin(), Reference(members), RefSketch(members), members.size(),
               store->Weak(tree.Root())};
        std::lock_guard<std::mutex> lock(mu);
        stale.push_back(w.weak);
        if (stale.size() > 64) stale.erase(stale.begin());
        queue.push_back(std::move(w));
    }
    done = true;
    for (auto &t : readers) t.join();
    const bool final_ok = tree.RootDigest() == Reference(members);
    std::printf("rounds=%d checked=%d failures=%d weak_hits=%d weak_misses=%d final_ok=%d "
                "live_leaves=%zu members=%zu\n",
                rounds, checked.load(), failures.load(), weak_hits.load(),
                weak_misses.load(), int(final_ok), store->LiveLeaves(), members.size());
    return (failures == 0 && final_ok && checked == rounds &&
            store->LiveLeaves() == members.size()) ? 0 : 1;
}
