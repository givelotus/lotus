// One process = one sample. Identical source for variants A and B; only the
// linked commitment.cpp differs (see make-variants.sh).
// Timed operation: BuildTxSubtreeA(span<const TxIdentityPair>) including its
// internal pointer-array allocation, partitioning, std::async dispatch, join
// and future destruction. Fixture generation, reference check and warm-up are
// outside the timed region. Allocator: system default.
// usage: bench N dist(random|prefix) callers min_seconds [warmup_roots]
#include <lotus_v2/commitment.h>
#include <lotus_v2/tagged_hash.h>
#ifdef BENCH_COOPERATIVE_ENTRY
#include "cooperative_work_pool.h"
#endif
#include <sys/resource.h>
#include <pthread.h>
#include <dlfcn.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <thread>
#include <vector>
using namespace lotus::v2;

// Count successful thread starts through the actual executable symbol. dyld
// interpose sections do not rewrite calls originating in this same image.
static std::atomic<uint64_t> g_threads{0};
extern "C" int pthread_create(pthread_t *t, const pthread_attr_t *a,
                              void *(*f)(void *), void *arg) {
    using Create = int (*)(pthread_t *, const pthread_attr_t *, void *(*)(void *), void *);
    static const Create real_create = reinterpret_cast<Create>(dlsym(RTLD_NEXT, "pthread_create"));
    if (!real_create) std::abort();
    const int rc = real_create(t, a, f, arg);
    if (rc == 0) g_threads.fetch_add(1, std::memory_order_relaxed);
    return rc;
}

static Hash Reference(std::vector<const TxIdentityPair *> txs, unsigned depth = 0) {
    if (txs.empty()) return TaggedHash(HashDomain::TxRoot, std::array<uint8_t, 1>{2});
    if (txs.size() == 1) {
        std::array<uint8_t, 65> b{};
        std::copy(txs[0]->tx_id.begin(), txs[0]->tx_id.end(), b.begin() + 1);
        std::copy(txs[0]->tx_hash.begin(), txs[0]->tx_hash.end(), b.begin() + 33);
        return TaggedHash(HashDomain::TxRoot, b);
    }
    std::vector<const TxIdentityPair *> l, r;
    for (auto *tx : txs) (((tx->tx_id[depth / 8] >> (depth % 8)) & 1) ? r : l).push_back(tx);
    auto a = Reference(l, depth + 1), b = Reference(r, depth + 1);
    std::array<uint8_t, 67> bytes{};
    bytes[0] = 1; bytes[1] = depth; bytes[2] = depth >> 8;
    std::copy(a.begin(), a.end(), bytes.begin() + 3);
    std::copy(b.begin(), b.end(), bytes.begin() + 35);
    return TaggedHash(HashDomain::TxRoot, bytes);
}

static std::vector<TxIdentityPair> Fixture(size_t n, bool prefix) {
    uint64_t s = 234567891;
    auto next = [&] { s ^= s << 13; s ^= s >> 7; s ^= s << 17; return s; };
    std::vector<TxIdentityPair> out(n);
    for (auto &tx : out) for (size_t i = 0; i < 32; ++i) { tx.tx_id[i] = next(); tx.tx_hash[i] = next(); }
    // "prefix": 4 distinct key prefixes; first 3 key bytes fixed per prefix
    // (byte0 in 0..3, bytes 1-2 constant), remaining 29 bytes random.
    // Routing is LSB-first within a byte, so splits exist at depths 0-1 only
    // until bit 24; async depths 2 and 3 see one-sided partitions.
    if (prefix) for (auto &tx : out) { tx.tx_id[0] = tx.tx_id[0] & 3; tx.tx_id[1] = 0xA5; tx.tx_id[2] = 0x5A; }
    return out;
}

static Hash ComputeRoot(std::span<const TxIdentityPair> fixture) {
#ifdef BENCH_COOPERATIVE_ENTRY
    return util::CooperativeWorkPool::Shared().Async([fixture] { return BuildTxSubtreeA(fixture); }).Get();
#else
    return BuildTxSubtreeA(fixture);
#endif
}

static double cpu_seconds() {
    rusage u; getrusage(RUSAGE_SELF, &u);
    return u.ru_utime.tv_sec + u.ru_stime.tv_sec + (u.ru_utime.tv_usec + u.ru_stime.tv_usec) / 1e6;
}
static long maxrss_bytes() { rusage u; getrusage(RUSAGE_SELF, &u); return u.ru_maxrss; } // bytes on macOS

int main(int argc, char **argv) {
    if (argc < 5) return 64;
    const size_t n = std::stoull(argv[1]);
    const bool prefix = std::string(argv[2]) == "prefix";
    const int callers = std::stoi(argv[3]);
    const double min_s = std::stod(argv[4]);
    const int warm = argc > 5 ? std::stoi(argv[5]) : 3;
    auto fx = Fixture(n, prefix);
    std::vector<const TxIdentityPair *> ptrs;
    for (auto &t : fx) ptrs.push_back(&t);
    const Hash expected = Reference(ptrs);
    const uint64_t threads_before_warmup = g_threads.load();
    const double cold_cpu0 = cpu_seconds();
    const auto cold_wall0 = std::chrono::steady_clock::now();
    if (ComputeRoot(fx) != expected) return 2;
    const double cold_wall = std::chrono::duration<double>(std::chrono::steady_clock::now() - cold_wall0).count();
    const double cold_cpu = cpu_seconds() - cold_cpu0;
    for (int i = 1; i < warm; ++i) if (ComputeRoot(fx) != expected) return 2;

    std::atomic<bool> go{false}, stop{false}, bad{false};
    std::atomic<uint64_t> roots{0};
    auto worker = [&] {
        while (!go.load()) std::this_thread::yield();
        // each caller runs whole roots until stop; a root in flight at stop is counted
        while (!stop.load(std::memory_order_relaxed)) {
            if (ComputeRoot(fx) != expected) bad = true;
            roots.fetch_add(1, std::memory_order_relaxed);
        }
    };
    // Callers are created before timing; threads_created counts only after.
    std::vector<std::thread> pool;
    const uint64_t t0_threads = g_threads.load();
    for (int i = 0; i < callers; ++i) pool.emplace_back(worker);
    const uint64_t caller_threads = g_threads.load() - t0_threads;
    const double c0 = cpu_seconds();
    const uint64_t th0 = g_threads.load();
    const auto w0 = std::chrono::steady_clock::now();
    go = true;
    std::this_thread::sleep_for(std::chrono::duration<double>(min_s));
    stop = true;
    for (auto &t : pool) t.join();
    const double wall = std::chrono::duration<double>(std::chrono::steady_clock::now() - w0).count();
    const double cpu = cpu_seconds() - c0;
    const uint64_t r = roots.load();
    if (bad) return 3;
    // wall_ms_per_root: wall / roots completed across callers (throughput view);
    // latency_ms_per_root: wall * callers / roots (mean per-call latency).
    std::printf("{\"n\":%zu,\"dist\":\"%s\",\"callers\":%d,\"roots\":%llu,\"wall_s\":%.6f,"
                "\"wall_ms_per_root\":%.6f,\"latency_ms_per_root\":%.6f,\"cpu_s\":%.6f,"
                "\"cpu_ms_per_root\":%.6f,\"maxrss_bytes\":%ld,\"threads_created_timed\":%llu,"
                "\"threads_per_root\":%.3f,\"caller_threads\":%llu,\"root\":\"",
                n, argv[2], callers, (unsigned long long)r, wall, wall * 1000 / r,
                wall * 1000 * callers / r, cpu, cpu * 1000 / r, maxrss_bytes(),
                (unsigned long long)(g_threads.load() - th0), double(g_threads.load() - th0) / r,
                (unsigned long long)caller_threads);
    for (auto b : expected) std::printf("%02x", unsigned(b));
    std::printf("\",\"first_root_wall_s\":%.9f,\"first_root_cpu_s\":%.9f,"
                "\"threads_created_before_timing\":%llu", cold_wall, cold_cpu,
                (unsigned long long)(th0 - threads_before_warmup - caller_threads));
#ifdef BENCH_COOPERATIVE_ENTRY
    const auto stats = util::CooperativeWorkPool::Shared().GetStats();
    std::printf(",\"pool_workers\":%zu,\"pool_budget\":%zu,\"pool_active_peak\":%zu,"
                "\"pool_queue_peak\":%zu,\"pool_queue_capacity\":%zu,\"pool_outstanding_peak\":%zu,"
                "\"pool_outstanding_limit\":%zu,\"pool_inline_backpressure\":%zu,\"pool_help_jobs\":%zu,"
                "\"pool_callback_depth_peak\":%zu,\"pool_own_reclaims\":%zu", stats.workers, stats.budget, stats.active_peak,
                stats.queued_peak, stats.queue_capacity, stats.outstanding_peak,
                stats.outstanding_limit, stats.inline_backpressure, stats.help_jobs, stats.callback_depth_peak, stats.own_reclaims);
#endif
    std::puts("}");
}
