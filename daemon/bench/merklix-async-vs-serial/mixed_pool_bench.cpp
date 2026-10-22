// Synthetic shared-executor CPU clients, not daemon subsystems or TPS.
#include "cooperative_work_pool.h"
#include <atomic>
#include <bit>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <dlfcn.h>
#include <future>
#include <pthread.h>
#include <sys/resource.h>
#include <vector>
static std::atomic<uint64_t> threads_created{0};
extern "C" int pthread_create(pthread_t *thread, const pthread_attr_t *attr,
                              void *(*fn)(void *), void *arg) {
    using Create = int (*)(pthread_t *, const pthread_attr_t *, void *(*)(void *), void *);
    static const auto real_create = reinterpret_cast<Create>(dlsym(RTLD_NEXT, "pthread_create"));
    if (!real_create) std::abort();
    const int rc = real_create(thread, attr, fn, arg);
    if (!rc) ++threads_created;
    return rc;
}
using Pool = util::CooperativeWorkPool;
// Three different integer CPU loops imitate hash/scan/encoding-shaped work;
// they are not implementations of those production operations.
__attribute__((noinline)) static uint64_t Leaf(unsigned kind, uint64_t x, unsigned rounds) {
    for (unsigned i = 0; i < rounds; ++i) {
        if (kind == 0) { x ^= x >> 13; x *= 0x9e3779b185ebca87ULL; x ^= x << 17; }
        else if (kind == 1) { x += (x & 31) > 15 ? 0xa0761d6478bd642fULL : 0xe7037ed1a0b428dbULL; x = std::rotl(x, 9) ^ i; }
        else { x = std::rotl(x + 0x8ebc6af09c88c6e3ULL, 7); x ^= (x >> 29) + i; }
    }
    return x;
}
static uint64_t Reference(unsigned kind, unsigned depth, uint64_t seed, unsigned rounds) {
    if (!depth) return Leaf(kind, seed, rounds);
    return Reference(kind, depth - 1, seed * 2, rounds)
         ^ std::rotl(Reference(kind, depth - 1, seed * 2 + 1, rounds), 11);
}
static uint64_t ForkJoin(bool pooled, unsigned kind, unsigned depth, uint64_t seed, unsigned rounds) {
    if (!depth) return Leaf(kind, seed, rounds);
    auto left_fn = [=] { return ForkJoin(pooled, kind, depth - 1, seed * 2, rounds); };
    if (pooled) {
        auto left = Pool::Shared().Async(std::move(left_fn));
        const auto right = ForkJoin(pooled, kind, depth - 1, seed * 2 + 1, rounds);
        return left.Get() ^ std::rotl(right, 11);
    }
    auto left = std::async(std::launch::async, std::move(left_fn));
    const auto right = ForkJoin(pooled, kind, depth - 1, seed * 2 + 1, rounds);
    return left.get() ^ std::rotl(right, 11);
}
static uint64_t Root(bool pooled, unsigned kind, unsigned rounds) {
    auto fn = [=] { return ForkJoin(pooled, kind, 3, 123456789 + kind, rounds); };
    if (pooled) return Pool::Shared().Async(std::move(fn)).Get();
    return fn();
}
static double Cpu() {
    rusage u{}; getrusage(RUSAGE_SELF, &u);
    return u.ru_utime.tv_sec + u.ru_stime.tv_sec + (u.ru_utime.tv_usec + u.ru_stime.tv_usec) / 1e6;
}
int main(int argc, char **argv) {
    if (argc != 5) return 64;
    const bool pooled = argv[1][0] == 'E';
    const unsigned callers = std::stoul(argv[2]), rounds = std::stoul(argv[3]);
    const double seconds = std::stod(argv[4]);
    if (!callers || callers % 3 || !rounds || seconds <= 0) return 65;
    uint64_t expected[3];
    for (unsigned kind = 0; kind < 3; ++kind) {
        expected[kind] = Reference(kind, 3, 123456789 + kind, rounds);
        for (unsigned i = 0; i < 3; ++i) if (Root(pooled, kind, rounds) != expected[kind]) return 2;
    }
    const uint64_t warm_threads = threads_created.load();
    std::atomic<bool> go{false}, stop{false}, bad{false};
    std::atomic<uint64_t> roots{0};
    std::vector<std::thread> clients;
    std::vector<uint64_t> client_roots(callers, 0);
    for (unsigned i = 0; i < callers; ++i) clients.emplace_back([&, i, kind = i % 3] {
        go.wait(false);
        while (!stop.load()) {
            if (Root(pooled, kind, rounds) != expected[kind]) bad = true;
            ++roots; ++client_roots[i];
        }
    });
    const uint64_t before = threads_created.load();
    const double cpu0 = Cpu();
    const auto wall0 = std::chrono::steady_clock::now();
    go.store(true); go.notify_all();
    std::this_thread::sleep_for(std::chrono::duration<double>(seconds));
    stop = true;
    for (auto &client : clients) client.join();
    const double wall = std::chrono::duration<double>(std::chrono::steady_clock::now() - wall0).count();
    const double cpu = Cpu() - cpu0;
    const auto completed = roots.load();
    if (bad || !completed || *std::min_element(client_roots.begin(),client_roots.end()) == 0 || before - warm_threads != callers) return 3;
    const auto stats = pooled ? Pool::Shared().GetStats() : Pool::Stats{};
    if (pooled && (stats.active_peak > stats.budget || stats.queued_peak > stats.queue_capacity)) return 4;
    rusage u{}; getrusage(RUSAGE_SELF, &u);
    std::printf("{\"variant\":\"%s\",\"callers\":%u,\"rounds\":%u,\"roots\":%llu,"
                "\"wall_s\":%.9f,\"wall_ms_per_root\":%.9f,\"cpu_ms_per_root\":%.9f,\"maxrss_bytes\":%ld,"
                "\"threads_created_before_timing\":%llu,\"caller_threads\":%llu,\"threads_created_timed\":%llu,"
                "\"pool_workers\":%zu,\"pool_active_peak\":%zu,\"pool_budget\":%zu,\"pool_queue_peak\":%zu,"
                "\"pool_queue_capacity\":%zu,\"pool_help_jobs\":%zu,\"pool_inline_backpressure\":%zu,"
                "\"pool_callback_depth_peak\":%zu,\"pool_own_reclaims\":%zu,\"min_client_roots\":%llu,\"reference\":[\"%016llx\",\"%016llx\",\"%016llx\"]}\n",
                pooled ? "E" : "A", callers, rounds, (unsigned long long)completed, wall,
                1000*wall/completed, 1000*cpu/completed, u.ru_maxrss,
                (unsigned long long)warm_threads, (unsigned long long)(before-warm_threads),
                (unsigned long long)(threads_created.load()-before), stats.workers, stats.active_peak,
                stats.budget, stats.queued_peak, stats.queue_capacity, stats.help_jobs,
                stats.inline_backpressure, stats.callback_depth_peak, stats.own_reclaims,
                (unsigned long long)*std::min_element(client_roots.begin(),client_roots.end()),
                (unsigned long long)expected[0], (unsigned long long)expected[1], (unsigned long long)expected[2]);
}
