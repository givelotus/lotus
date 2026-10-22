// Correctness only: assertions enabled; also run with ThreadSanitizer.
#include "cooperative_work_pool.h"
#include <atomic>
#include <cassert>
#include <memory>
#include <string>
#include <cstdio>
using Pool = util::CooperativeWorkPool;

static uint64_t Mix(uint64_t x, unsigned rounds) {
    for (unsigned i = 0; i < rounds; ++i) {
        x ^= x >> 13; x *= 0x9e3779b185ebca87ULL; x ^= x << 17;
    }
    return x;
}
static uint64_t Tree(Pool &pool, int depth, uint64_t seed) {
    if (!depth) return Mix(seed, 128);
    auto left = pool.Async([&pool, depth, seed] { return Tree(pool, depth - 1, seed * 2); });
    const auto right = Tree(pool, depth - 1, seed * 2 + 1);
    return left.Get() ^ right;
}
static uint64_t Reference(int depth, uint64_t seed) {
    if (!depth) return Mix(seed, 128);
    return Reference(depth - 1, seed * 2) ^ Reference(depth - 1, seed * 2 + 1);
}
static int Chain(Pool &pool, int depth) {
    if (!depth) return 1;
    auto child = pool.Async([&pool, depth] { return Chain(pool, depth - 1); });
    return child.Get() + 1;
}
static void CheckStats(Pool &pool) {
    const auto s = pool.GetStats();
    assert(s.workers == s.budget);
    assert(s.active_peak <= s.budget);
    assert(s.queued_peak <= s.queue_capacity);
    assert(s.outstanding_peak <= s.outstanding_limit);
    assert(s.callback_depth_peak <= Pool::MaxDepth);
    assert(s.help_jobs >= s.own_reclaims);
    std::printf("PASS budget=%zu workers=%zu active_peak=%zu queue_peak=%zu/%zu outstanding_peak=%zu/%zu depth_peak=%zu backpressure=%zu other_help=%zu\n",
                s.budget,s.workers,s.active_peak,s.queued_peak,s.queue_capacity,
                s.outstanding_peak,s.outstanding_limit,s.callback_depth_peak,
                s.inline_backpressure,s.help_jobs-s.own_reclaims);
}
int main() {
    const auto hw = std::max(1u, std::thread::hardware_concurrency());
    for (size_t cap : {size_t{1}, size_t{2}, size_t{hw}}) {
        Pool pool(cap, 1); // deliberately exercise backpressure on every tree
        auto movable = pool.Async([p = std::make_unique<int>(17)] { return std::make_unique<int>(*p); });
        assert(*movable.Get() == 17);
        auto fail = pool.Async([]() -> int { throw std::runtime_error("expected"); });
        try { (void)fail.Get(); assert(false); }
        catch (const std::runtime_error &e) { assert(std::string(e.what()) == "expected"); }
        try { (void)fail.Get(); assert(false); } catch (const std::logic_error &) {}
        auto bounded = pool.Async([&] { return Chain(pool, 24); });
        assert(bounded.Get() == 25);
        auto too_deep = pool.Async([&] { return Chain(pool, 10000); });
        try { (void)too_deep.Get(); assert(false); } catch (const std::length_error &) {}
        int joined = 0;
        { auto future = pool.Async([&] { joined = 1; return 1; }); }
        assert(joined == 1);
        joined = 0;
        auto old = pool.Async([&] { joined = 1; return 1; });
        auto replacement = pool.Async([] { return 2; });
        old = std::move(replacement);
        assert(joined == 1 && old.Get() == 2);

        // Concurrent synthetic subsystems all enter through this same executor.
        std::atomic<unsigned> completed{0};
        std::vector<std::thread> clients;
        for (unsigned client = 0; client < 12; ++client) clients.emplace_back([&, client] {
            for (unsigned i = 0; i < 8; ++i) {
                const uint64_t seed = 1 + client % 3;
                auto root = pool.Async([&, seed] { return Tree(pool, 6, seed); });
                assert(root.Get() == Reference(6, seed));
                ++completed;
            }
        });
        for (auto &client : clients) client.join();
        assert(completed == 96);
        std::atomic<unsigned> posted{0};
        for (unsigned i = 0; i < 100; ++i) pool.Post([&] {
            pool.Post([&] { ++posted; });
            ++posted;
        });
        pool.Post([] { throw std::runtime_error("intentionally discarded Post error"); });
        pool.Shutdown();
        assert(posted == 200);
        try { (void)pool.Async([] { return 1; }); assert(false); }
        catch (const std::runtime_error &) {}
        CheckStats(pool);
        assert(pool.GetStats().inline_backpressure > 0);
    }
    // An accepted Future may be fetched after explicit quiescence while its
    // pool object is still alive. Destruction also drains unjoined Posts.
    std::atomic<unsigned> destroyed{0};
    {
        Pool pool(2, 1);
        auto result = pool.Async([] { return 23; });
        pool.Post([&] { pool.Post([&] { ++destroyed; }); ++destroyed; });
        pool.Shutdown();
        assert(result.Get() == 23);
    }
    assert(destroyed == 2);
    // A detached helped job may be the last owner of an arbitrary callable.
    // Its destructor can reenter the scheduler: never release it under m_.
    struct ReentrantDestructor {
        Pool &pool;
        std::atomic<unsigned> &count;
        ~ReentrantDestructor() { (void)pool.GetStats(); ++count; }
    };
    Pool reentrant(2, 128);
    std::atomic<unsigned> released{0};
    auto root = reentrant.Async([&] {
        auto child = reentrant.Async([&] { return Tree(reentrant, 9, 7); });
        for (unsigned i = 0; i < 100; ++i)
            reentrant.Post([probe = std::unique_ptr<ReentrantDestructor>(new ReentrantDestructor{reentrant,released})] {
                (void)probe->pool.GetStats();
            });
        return child.Get();
    });
    assert(root.Get() == Reference(9, 7));
    reentrant.Shutdown();
    assert(released == 100);
    CheckStats(reentrant);
}
