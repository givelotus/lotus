// Experimental reusable CPU executor E. Historical work_pool.h (D) is frozen.
// Fixed worker/callback budget; bounded queue; structured same-pool fork/join.
// No locks may be held across Async/Post/Get: helping can invoke another job.
// Jobs may block only through descendant Future::Get in this same pool; external
// I/O, cross-root/cross-pool joins, cycles and destruction on a worker are outside
// the contract. Both logical and synchronous callback nesting are capped at64;
// further submission fails with length_error rather than unbounded recursion.
#pragma once
#include <algorithm>
#include <condition_variable>
#include <cstdlib>
#include <deque>
#include <exception>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <thread>
#include <type_traits>
#include <utility>
#include <vector>

namespace util {
class CooperativeWorkPool {
    enum State { Queued, Running, Done };
    struct Job {
        virtual ~Job() = default;
        virtual void Execute() noexcept = 0;
        State state = Queued; // protected by m_
        size_t logical_depth = 1;
    };
    template<class T> struct ResultJob : Job {
        std::optional<T> result;
        std::exception_ptr error;
    };
public:
    static constexpr size_t MaxDepth = 64;
    template<class T> class Future {
    public:
        Future() = default;
        Future(Future &&) = default;
        Future &operator=(Future &&other) noexcept {
            if (this != &other) {
                Wait();
                pool_ = other.pool_;
                job_ = std::move(other.job_);
            }
            return *this;
        }
        ~Future() { Wait(); }
        T Get() {
            if (!job_) throw std::logic_error("Get requires an unconsumed Future");
            Wait();
            auto job = std::move(job_);
            if (job->error) std::rethrow_exception(job->error);
            return std::move(*job->result);
        }
    private:
        friend class CooperativeWorkPool;
        Future(CooperativeWorkPool *pool, std::shared_ptr<ResultJob<T>> job)
            : pool_(pool), job_(std::move(job)) {}
        void Wait() noexcept { if (job_) pool_->Wait(job_); }
        CooperativeWorkPool *pool_ = nullptr;
        std::shared_ptr<ResultJob<T>> job_;
    };
    struct Stats {
        size_t workers, budget, queue_capacity, queued_peak, active_peak;
        size_t outstanding_peak, inline_backpressure, help_jobs, outstanding_limit, callback_depth_peak, own_reclaims;
    };
    static size_t DefaultBudget() {
        const size_t hw = std::max(1u, std::thread::hardware_concurrency());
        if (const char *value = std::getenv("LOTUS_POOL_E_WORKERS")) {
            char *end = nullptr;
            const unsigned long parsed = std::strtoul(value, &end, 10);
            if (!*value || *end || !parsed || parsed > hw)
                throw std::invalid_argument("LOTUS_POOL_E_WORKERS must be within1..hardware threads");
            return size_t(parsed);
        }
        return hw;
    }
    static CooperativeWorkPool &Shared() { static CooperativeWorkPool pool; return pool; }
    explicit CooperativeWorkPool(size_t budget = DefaultBudget(), size_t queue_capacity = 0)
        : budget_(std::max(size_t{1}, budget)), capacity_(queue_capacity ? queue_capacity : 4 * budget_),
          outstanding_limit_(capacity_ + budget_ * MaxDepth) {
        // All workers are established before admission; partial construction
        // failure joins those already started. No routine thread growth exists.
        try {
            for (size_t i = 0; i < budget_; ++i) workers_.emplace_back([this] { Loop(); });
        } catch (...) {
            { std::lock_guard lock(m_); stop_ = true; }
            cv_.notify_all();
            for (auto &worker : workers_) worker.join();
            throw;
        }
    }
    ~CooperativeWorkPool() { Shutdown(); }
    CooperativeWorkPool(const CooperativeWorkPool &) = delete;
    CooperativeWorkPool &operator=(const CooperativeWorkPool &) = delete;

    template<class F> requires (std::is_object_v<std::invoke_result_t<F &>> &&
                               std::is_move_constructible_v<std::invoke_result_t<F &>>)
    auto Async(F &&fn) -> Future<std::invoke_result_t<F &>> {
        using T = std::invoke_result_t<F &>;
        struct Impl final : ResultJob<T> {
            std::decay_t<F> fn;
            explicit Impl(F &&f) : fn(std::forward<F>(f)) {}
            void Execute() noexcept override {
                try { this->result.emplace(fn()); }
                catch (...) { this->error = std::current_exception(); }
            }
        };
        const size_t depth = SubmissionDepth();
        auto job = std::make_shared<Impl>(std::forward<F>(fn));
        job->logical_depth = depth;
        Submit(job);
        return Future<T>(this, job);
    }
    template<class F> void Post(F &&fn) {
        struct Impl final : Job {
            std::decay_t<F> fn;
            explicit Impl(F &&f) : fn(std::forward<F>(f)) {}
            void Execute() noexcept override { try { fn(); } catch (...) {} }
        };
        const size_t depth = SubmissionDepth();
        auto job = std::make_shared<Impl>(std::forward<F>(fn));
        job->logical_depth = depth;
        Submit(job);
    }
    // Stop external admission; accepted callbacks may submit descendants until
    // quiescence. Call only once, from outside the pool; object/Futures stay alive.
    void Shutdown() noexcept {
        std::unique_lock lock(m_);
        if (joined_) return;
        accepting_ = false;
        cv_.notify_all();
        cv_.wait(lock, [this] { return pending_ == 0; });
        stop_ = true;
        lock.unlock();
        cv_.notify_all();
        for (auto &worker : workers_) worker.join();
        lock.lock();
        joined_ = true;
    }
    Stats GetStats() const {
        std::lock_guard lock(m_);
        return {workers_.size(), budget_, capacity_, queued_peak_, active_peak_,
                outstanding_peak_, inline_backpressure_, help_jobs_, outstanding_limit_, callback_depth_peak_, own_reclaims_};
    }
private:
    size_t SubmissionDepth() const {
        if (current_pool_ != this) return 1;
        if (callback_depth_ >= MaxDepth || logical_depth_ >= MaxDepth)
            throw std::length_error("CooperativeWorkPool nesting budget exceeded");
        return logical_depth_ + 1;
    }
    void Submit(const std::shared_ptr<Job> &job) {
        const bool internal = current_pool_ == this;
        std::unique_lock lock(m_);
        if (!internal) {
            cv_.wait(lock, [this] { return !accepting_ || pending_ < outstanding_limit_; });
            if (!accepting_) throw std::runtime_error("pool admission closed");
        } else if (pending_ >= outstanding_limit_) {
            // Never block a producer holding a permit at the hard live-job cap.
            throw std::length_error("CooperativeWorkPool outstanding budget exceeded");
        }
        if (queue_.size() < capacity_) {
            queue_.push_back(job); // allocation may fail before admission
            queued_peak_ = std::max(queued_peak_, queue_.size());
            ++pending_;
            outstanding_peak_ = std::max(outstanding_peak_, pending_);
            lock.unlock(); cv_.notify_all(); return;
        }
        // Backpressure does not wait while holding a pool execution permit.
        // Internal producer runs its own new task inline; external producers
        // wait for the same bounded permit used by workers, then run it inline.
        ++pending_;
        outstanding_peak_ = std::max(outstanding_peak_, pending_);
        if (!internal) cv_.wait(lock, [this] { return active_ < budget_; });
        if (!internal) AcquireLocked();
        job->state = Running;
        ++inline_backpressure_;
        lock.unlock();
        Execute(job, !internal);
    }
    void AcquireLocked() {
        ++active_; active_peak_ = std::max(active_peak_, active_);
    }
    std::shared_ptr<Job> TakeLocked(const std::shared_ptr<Job> &preferred = {}) {
        auto it = preferred ? std::find(queue_.begin(), queue_.end(), preferred) : queue_.begin();
        if (it == queue_.end()) it = queue_.begin();
        auto job = std::move(*it);
        queue_.erase(it);
        job->state = Running;
        return job;
    }
    void Execute(const std::shared_ptr<Job> &job, bool release_permit) noexcept {
        const auto old_pool = current_pool_;
        const size_t old_logical = logical_depth_;
        current_pool_ = this; logical_depth_ = job->logical_depth; ++callback_depth_;
        const size_t execution_depth = callback_depth_;
        job->Execute();
        --callback_depth_; logical_depth_ = old_logical; current_pool_ = old_pool;
        {
            std::lock_guard lock(m_);
            job->state = Done;
            callback_depth_peak_ = std::max(callback_depth_peak_, execution_depth);
            --pending_;
            if (release_permit) --active_;
        }
        cv_.notify_all();
    }
    void Wait(const std::shared_ptr<Job> &target) noexcept {
        const bool internal = current_pool_ == this;
        std::unique_lock lock(m_);
        while (target->state != Done) {
            if (!queue_.empty() && (internal || active_ < budget_)) {
                if (!internal) AcquireLocked();
                const bool reclaim = target->state == Queued;
                auto job = TakeLocked(reclaim ? target : std::shared_ptr<Job>{});
                ++help_jobs_;
                if (reclaim) ++own_reclaims_;
                lock.unlock(); Execute(job, !internal); job.reset(); lock.lock();
                continue;
            }
            if (internal) {
                --active_; cv_.notify_all();
                cv_.wait(lock, [this, &target] {
                    return active_ < budget_ && (target->state == Done || !queue_.empty());
                });
                AcquireLocked(); // suspended callback resumes within same CPU budget
            } else {
                cv_.wait(lock, [this, &target] {
                    return target->state == Done || (active_ < budget_ && !queue_.empty());
                });
            }
        }
    }
    void Loop() noexcept {
        for (;;) {
            std::unique_lock lock(m_);
            cv_.wait(lock, [this] { return stop_ || (!queue_.empty() && active_ < budget_); });
            if (stop_) return;
            AcquireLocked(); auto job = TakeLocked();
            lock.unlock(); Execute(job, true);
        }
    }
    inline static thread_local CooperativeWorkPool *current_pool_ = nullptr;
    inline static thread_local size_t callback_depth_ = 0, logical_depth_ = 0;
    mutable std::mutex m_;
    std::condition_variable cv_;
    std::deque<std::shared_ptr<Job>> queue_;
    std::vector<std::thread> workers_;
    const size_t budget_, capacity_, outstanding_limit_;
    size_t active_ = 0, pending_ = 0, queued_peak_ = 0, active_peak_ = 0;
    size_t outstanding_peak_ = 0, inline_backpressure_ = 0, help_jobs_ = 0, callback_depth_peak_ = 0, own_reclaims_ = 0;
    bool accepting_ = true, stop_ = false, joined_ = false;
};
} // namespace util
