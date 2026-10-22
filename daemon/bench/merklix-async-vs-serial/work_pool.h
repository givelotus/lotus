// Generic persistent compute pool (prototype, header-only). Candidate home: src/util/work_pool.h.
// - Async(f) -> Future<T>; Post(f) for fire-and-forget. Jobs are move-only callables.
// - Future::Get(): runs the job inline if no worker started it (reclaim), else waits;
//   rethrows the job's exception. Destroying an un-fetched Future joins the job.
// - Growth: when work is queued and no worker is idle, add a worker (kept, never
//   shrunk) up to a hard cap (LOTUS_POOL_MAX, default 4*hardware threads).
//   Starts with 1 worker. A waiter that must block calls MaybeGrow() so queued
//   jobs are not starved by blocked workers.
// Contract: pool jobs may block only through Future::Get() on acyclic job
// dependencies. Async supports movable object results (not void or references);
// use Post for void work. Post intentionally discards exceptions.
// The pool must outlive all Futures. Destruction starts only after external
// submitters stop; draining jobs may still submit descendants. Never destroy
// the pool from one of its workers. Workers start lazily on the first enqueue.
#pragma once
#include <algorithm>
#include <atomic>
#include <condition_variable>
#include <cstdlib>
#include <deque>
#include <exception>
#include <memory>
#include <mutex>
#include <optional>
#include <thread>
#include <type_traits>
#include <vector>
#include <utility>
#include <stdexcept>

namespace util {

class WorkPool {
public:
    struct JobBase {
        std::atomic<int> state{0}; // 0 queued, 1 running, 2 done
        virtual ~JobBase() = default;
        virtual void Execute() = 0;
        bool TryStart() { int e = 0; return state.compare_exchange_strong(e, 1); }
        void Run() { Execute(); state.store(2, std::memory_order_release); state.notify_all(); }
    };

    template <class T> class Future {
    public:
        Future() = default;
        Future(WorkPool *p, std::shared_ptr<JobBase> j, std::shared_ptr<std::optional<T>> r,
               std::shared_ptr<std::exception_ptr> e)
            : pool_(p), job_(std::move(j)), res_(std::move(r)), err_(std::move(e)) {}
        Future(Future &&) = default;
        Future &operator=(Future &&other) noexcept {
            if (this != &other) {
                Wait(); // preserve the old job's captured-reference lifetime
                pool_ = other.pool_;
                job_ = std::move(other.job_);
                res_ = std::move(other.res_);
                err_ = std::move(other.err_);
            }
            return *this;
        }
        ~Future() { if (job_) { try { Wait(); } catch (...) {} } }
        T Get() {
            if (!job_) throw std::logic_error("Get requires a valid unconsumed Future");
            Wait();
            auto e = *err_;
            job_.reset();
            if (e) std::rethrow_exception(e);
            return std::move(**res_ptr());
        }
    private:
        std::optional<T> *res_ptr() { return res_.get(); }
        void Wait() {
            if (!job_) return;
            if (job_->TryStart()) { job_->Run(); return; } // reclaim
            if (job_->state.load(std::memory_order_acquire) == 2) return;
            pool_->MaybeGrow();
            for (int s; (s = job_->state.load(std::memory_order_acquire)) != 2;) job_->state.wait(s);
        }
        WorkPool *pool_ = nullptr;
        std::shared_ptr<JobBase> job_;
        std::shared_ptr<std::optional<T>> res_;
        std::shared_ptr<std::exception_ptr> err_;
    };

    static WorkPool &Shared() { static WorkPool p; return p; }
    explicit WorkPool(size_t max_threads = DefaultMax()) : max_(std::max(size_t{1}, max_threads)) {}
    ~WorkPool() {
        { std::lock_guard<std::mutex> l(m_); stop_ = true; }
        cv_.notify_all();
        for (auto &t : threads_) t.join();
    }
    WorkPool(const WorkPool &) = delete;
    WorkPool &operator=(const WorkPool &) = delete;

    template <class F> requires (std::is_object_v<std::invoke_result_t<F &>> &&
                                std::is_move_constructible_v<std::invoke_result_t<F &>>)
    auto Async(F &&f) -> Future<std::invoke_result_t<F &>> {
        using T = std::invoke_result_t<F &>;
        struct Impl final : JobBase {
            std::decay_t<F> fn;
            std::shared_ptr<std::optional<T>> res = std::make_shared<std::optional<T>>();
            std::shared_ptr<std::exception_ptr> err = std::make_shared<std::exception_ptr>();
            explicit Impl(F &&f) : fn(std::forward<F>(f)) {}
            void Execute() override { try { res->emplace(fn()); } catch (...) { *err = std::current_exception(); } }
        };
        auto j = std::make_shared<Impl>(std::forward<F>(f));
        Future<T> fut(this, j, j->res, j->err);
        Enqueue(j);
        return fut;
    }
    template <class F> void Post(F &&f) {
        struct Impl final : JobBase {
            std::decay_t<F> fn;
            explicit Impl(F &&f) : fn(std::forward<F>(f)) {}
            void Execute() override { try { fn(); } catch (...) {} }
        };
        Enqueue(std::make_shared<Impl>(std::forward<F>(f)));
    }
    size_t Threads() const { std::lock_guard<std::mutex> l(m_); return threads_.size(); }
    void MaybeGrow() { std::lock_guard<std::mutex> l(m_); GrowLocked(); }

private:
    static size_t DefaultMax() {
        if (const char *e = std::getenv("LOTUS_POOL_MAX")) { long v = std::atol(e); if (v > 0) return size_t(v); }
        return 4 * std::max(1u, std::thread::hardware_concurrency());
    }
    void Enqueue(std::shared_ptr<JobBase> j) {
        bool inline_fallback;
        {
            std::lock_guard<std::mutex> l(m_);
            q_.push_back(j);
            GrowLocked();
            inline_fallback = threads_.empty();
            if (inline_fallback) q_.pop_back();
        }
        if (inline_fallback) { if (j->TryStart()) j->Run(); }
        else cv_.notify_one();
    }
    void GrowLocked() { // m_ held
        // Once shutdown starts, the vector stays immutable while it is joined.
        // Existing workers drain queued work and descendants submitted by jobs.
        if (stop_) return;
        if (threads_.empty() || (idle_ == 0 && !q_.empty() && threads_.size() < max_)) {
            try { threads_.emplace_back([this] { Loop(); }); }
            catch (...) { /* Best-effort growth; no-worker submissions run inline. */ }
        }
    }
    void Loop() {
        for (;;) {
            std::shared_ptr<JobBase> j;
            {
                std::unique_lock<std::mutex> l(m_);
                ++idle_;
                cv_.wait(l, [this] { return stop_ || !q_.empty(); });
                --idle_;
                if (q_.empty()) return;
                j = std::move(q_.front()); q_.pop_front();
            }
            if (j->TryStart()) j->Run();
        }
    }
    mutable std::mutex m_;
    std::condition_variable cv_;
    std::deque<std::shared_ptr<JobBase>> q_;
    std::vector<std::thread> threads_;
    size_t idle_ = 0, max_;
    bool stop_ = false;
};

} // namespace util
