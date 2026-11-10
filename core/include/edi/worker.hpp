// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_WORKER_HPP
#define EDI_WORKER_HPP

#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <thread>

// ADR-0020 §1: the calculation worker. One worker thread runs jobs one at a time, in submission
// order. A job may emit deliveries and returns a final one; every delivery runs on the owner thread
// — the thread that built the Worker — exactly once and in order. Nothing a later submission does
// replaces, skips or reorders a job or a delivery: this is the ordered, never-dropped stream a
// fit's iterations and result use, and the latest-wins preview is built on top of it
// (edi::LivePreview), not into it. Qt-free.
//
// Built with EDI_WORKER_OWNER_THREAD (the single-thread WebAssembly build, ADR-0023), there is no worker thread:
// each job runs on the owner thread, in its turn among the calls `post` hands it. The order, delivery and
// cancellation guarantees are the same; the owner thread is busy while a job runs.

namespace edi::work {

// Runs on the owner thread.
using Delivery = std::function<void()>;
// Hands a delivery to the owner thread: first in, first out. Called from the worker thread, so it
// is thread-safe. In the app it is a queued invocation on the project view-model.
using Post = std::function<void(Delivery)>;

// A job's cooperative stop: `cancel` sets it and does nothing else. A job reads it on entry and at
// its checkpoints, and still returns its final delivery.
class CancelToken {
   public:
    CancelToken() : flag_(std::make_shared<std::atomic<bool>>(false)) {}
    bool cancelled() const noexcept { return flag_->load(std::memory_order_acquire); }

   private:
    friend class Worker;
    std::shared_ptr<std::atomic<bool>> flag_;
};

// Called by a job, on the worker thread: one more delivery, before the final one.
using Emit = std::function<void(Delivery)>;
// Runs on the worker thread and returns the final delivery (an empty one delivers nothing).
using Job = std::function<Delivery(const CancelToken&, const Emit&)>;
// 1, 2, 3, … in submission order.
using Ticket = std::uint64_t;

enum class EventKind : std::uint8_t {
    // The Worker's; `id` is the ticket. `Emitted` and `Delivered` repeat per delivery.
    Submitted,
    Started,
    Emitted,
    Finished,
    Cancelled,
    Delivered,
    // LivePreview's requests; `id` is the request number (the one the call would take, for
    // `Refused`).
    Input,
    Applied,
    Refused,
    // LivePreview's calculations; `id` is the generation.
    Snapshot,
    Calculating,
    Calculated,
    Published,
    Superseded,
    Rejected,
};

struct Event {
    EventKind kind{};
    std::string channel;
    std::uint64_t id = 0;
    std::uint64_t at_ns = 0;
    std::thread::id thread;
};

// Test instrumentation: production constructs a Worker without it. `clock_ns` defaults to the
// steady clock. `trace` receives every event of the Worker and of the LivePreview on it; calls are
// serialised and come from either thread.
struct Seams {
    std::function<std::uint64_t()> clock_ns;
    std::function<void(const Event&)> trace;
};

class Worker {
   public:
    explicit Worker(Post post, Seams seams = {});
    // Cancels every token, waits for the running job, and delivers nothing afterwards: a job not
    // yet started never starts, and a delivery not yet run never runs.
    ~Worker();
    Worker(const Worker&) = delete;
    Worker& operator=(const Worker&) = delete;
    Worker(Worker&&) = delete;
    Worker& operator=(Worker&&) = delete;

    Ticket submit(const std::string& channel, Job job);
    void cancel(Ticket ticket);
    const Seams& seams() const noexcept;
    // One event through the seams: the clock's time, the calling thread, serialised with the
    // Worker's own. What LivePreview traces with.
    void trace(EventKind kind, const std::string& channel, std::uint64_t id) const;
    // A Worker exists in this process. While one does, nothing registers a type (edi ADR-0020 §3).
    static bool any_alive() noexcept;

   private:
    struct State;
    std::shared_ptr<State> state_;
    std::thread thread_;  // never started under EDI_WORKER_OWNER_THREAD
};

}  // namespace edi::work

#endif  // EDI_WORKER_HPP
