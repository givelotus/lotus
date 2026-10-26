// Focused correctness gate, not a performance benchmark.
// Compile only in the coordinated host window:
// c++ -std=c++20 -O1 -g -pthread -I. work_pool_test.cpp -o work_pool_test
#include "work_pool.h"
#include <atomic>
#include <cassert>
#include <memory>
#include <string>

static int Tree(util::WorkPool &pool, int depth) {
    if (!depth) return 1;
    auto left = pool.Async([&pool, depth] { return Tree(pool, depth - 1); });
    const int right = Tree(pool, depth - 1);
    return left.Get() + right;
}

int main() {
    for (size_t cap : {size_t{1}, size_t{2}, size_t{4}}) {
        util::WorkPool pool(cap);
        auto movable = pool.Async([p = std::make_unique<int>(17)] { return std::make_unique<int>(*p); });
        assert(*movable.Get() == 17);
        auto fail = pool.Async([]() -> int { throw std::runtime_error("expected"); });
        try { (void)fail.Get(); assert(false); }
        catch (const std::runtime_error &e) { assert(std::string(e.what()) == "expected"); }
        try { (void)fail.Get(); assert(false); }
        catch (const std::logic_error &) {}
        for (int i = 0; i < 20; ++i) assert(Tree(pool, 7) == 128);
        assert(pool.Threads() <= cap);
        int joined = 0;
        { auto discarded = pool.Async([&] { joined = 1; return 0; }); }
        assert(joined == 1);
    }
    {
        util::WorkPool pool(1);
        // Test-only external gate pins the sole worker so both Futures below
        // remain queued; real pool jobs must use acyclic Future dependencies.
        std::atomic<bool> started{false}, release{false};
        auto pinned = pool.Async([&] {
            started.store(true); started.notify_all();
            release.wait(false);
            return 0;
        });
        started.wait(false);
        int joined = 0;
        auto old = pool.Async([&] { joined = 1; return 1; });
        auto replacement = pool.Async([] { return 2; });
        old = std::move(replacement);
        assert(joined == 1); // overwritten Future must join its previous job
        assert(old.Get() == 2);
        release.store(true); release.notify_all();
        assert(pinned.Get() == 0);
    }
    std::atomic<int> drained{0};
    {
        util::WorkPool pool(4);
        for (int i = 0; i < 100; ++i) pool.Post([&] {
            pool.Post([&] { ++drained; });
            ++drained;
        });
    }
    assert(drained == 200); // shutdown drains descendants without growing
}
