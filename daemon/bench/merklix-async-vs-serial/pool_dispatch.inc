// Variant C only: process-lifetime fixed worker pool + reclaim-or-wait join.
// Same partitioning/thresholds/hash as production; only the dispatch differs.
// Deadlock-free without help-while-waiting: Join() runs the job inline if no
// worker has started it, otherwise the job is already executing on a worker
// and (by induction on depth) will complete.
#include <atomic>
#include <condition_variable>
#include <deque>
#include <exception>
#include <functional>
#include <memory>
#include <mutex>
#include <thread>
namespace {
struct PoolJob {
    std::function<Hash()> fn;
    Hash result{};
    std::exception_ptr error;
    std::atomic<int> state{0}; // 0 queued, 1 running, 2 done
    void Run() {
        try { result = fn(); } catch (...) { error = std::current_exception(); }
        state.store(2, std::memory_order_release);
        state.notify_all();
    }
};
class HashPool {
public:
    static HashPool &Get() { static HashPool p; return p; }
    void Submit(std::shared_ptr<PoolJob> j) {
        { std::lock_guard<std::mutex> l(m_); q_.push_back(std::move(j)); }
        cv_.notify_one();
    }
private:
    HashPool() {
        unsigned n = std::min(15u, std::max(1u, std::thread::hardware_concurrency()));
        for (unsigned i = 0; i < n; ++i) threads_.emplace_back([this] { Loop(); });
    }
    ~HashPool() { // detached at exit: workers only block on cv_
        { std::lock_guard<std::mutex> l(m_); stop_ = true; }
        cv_.notify_all();
        for (auto &t : threads_) t.join();
    }
    void Loop() {
        for (;;) {
            std::shared_ptr<PoolJob> j;
            {
                std::unique_lock<std::mutex> l(m_);
                cv_.wait(l, [this] { return stop_ || !q_.empty(); });
                if (q_.empty()) return;
                j = std::move(q_.front()); q_.pop_front();
            }
            int expected = 0;
            if (j->state.compare_exchange_strong(expected, 1)) j->Run();
        }
    }
    std::mutex m_; std::condition_variable cv_;
    std::deque<std::shared_ptr<PoolJob>> q_;
    std::vector<std::thread> threads_;
    bool stop_ = false;
};
class ForkJoin {
public:
    explicit ForkJoin(std::function<Hash()> fn) : job_(std::make_shared<PoolJob>()) {
        job_->fn = std::move(fn);
        HashPool::Get().Submit(job_);
    }
    ~ForkJoin() { if (!joined_) { try { Join(); } catch (...) {} } }
    Hash Join() {
        joined_ = true;
        int expected = 0;
        if (job_->state.compare_exchange_strong(expected, 1)) job_->Run(); // reclaim
        else for (int s; (s = job_->state.load(std::memory_order_acquire)) != 2;) job_->state.wait(s);
        if (job_->error) std::rethrow_exception(job_->error);
        return job_->result;
    }
private:
    std::shared_ptr<PoolJob> job_;
    bool joined_ = false;
};
} // namespace
