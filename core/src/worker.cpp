// SPDX-License-Identifier: BSD-3-Clause
#include "edi/worker.hpp"

#include <chrono>
#include <condition_variable>
#include <deque>
#include <map>
#include <mutex>
#include <utility>

// ADR-0023: the single-thread WebAssembly build has no threads — starting one aborts — so there the worker
// runs each job on the owner thread, in its turn among the owner's posted calls. Every guarantee the header
// states holds; what changes is that the owner thread is busy while a job runs (the browser page does not
// repaint during a fit). The build sets the switch; an unthreaded Emscripten build without it is refused here
// rather than at its first calculation.
#ifndef EDI_WORKER_OWNER_THREAD
#define EDI_WORKER_OWNER_THREAD 0  // core/CMakeLists.txt defines it; a tree compiling these sources alone does not
#endif
#if defined(__EMSCRIPTEN__) && !defined(__EMSCRIPTEN_PTHREADS__) && !EDI_WORKER_OWNER_THREAD
#error "an Emscripten build without -pthread needs EDI_WORKER_OWNER_THREAD (edi ADR-0023)"
#endif

namespace edi::work {
namespace {
std::atomic<int> g_alive{0};
}  // namespace

struct Worker::State {
    struct Pending {
        Ticket ticket = 0;
        std::string channel;
        Job job;
        CancelToken token;
    };

    Post post;
    Seams seams;
    std::mutex mutex;  // queue, tokens, stopping
    std::condition_variable wake;
    std::deque<Pending> queue;
    struct Live {
        CancelToken token;
        std::string channel;
    };
    std::map<Ticket, Live> tokens;  // every job submitted and not yet finished
    Ticket next_ticket = 1;
    bool stopping = false;
    // False once the Worker is gone, so a delivery the owner thread has not run yet does nothing.
    std::shared_ptr<std::atomic<bool>> open = std::make_shared<std::atomic<bool>>(true);
    mutable std::mutex trace_mutex;

    void trace(EventKind kind, const std::string& channel, std::uint64_t id) const {
        if (!seams.trace) {
            return;
        }
        const std::lock_guard<std::mutex> lock(trace_mutex);
        const std::uint64_t now =
            seams.clock_ns ? seams.clock_ns()
                           : static_cast<std::uint64_t>(
                                 std::chrono::duration_cast<std::chrono::nanoseconds>(
                                     std::chrono::steady_clock::now().time_since_epoch())
                                     .count());
        seams.trace(Event{kind, channel, id, now, std::this_thread::get_id()});
    }

    // One delivery on its way to the owner thread: traced there, and dropped once the Worker is gone.
    void deliver(Ticket ticket, const std::string& channel, Delivery delivery) {
        post([self = this, keep = open, ticket, channel, delivery = std::move(delivery)] {
            if (!keep->load(std::memory_order_acquire)) {
                return;
            }
            self->trace(EventKind::Delivered, channel, ticket);
            if (delivery) {
                delivery();
            }
        });
    }

    // The worker thread: every job, in submission order, until the Worker stops.
    void run() {
        for (;;) {
            Pending next;
            {
                std::unique_lock<std::mutex> lock(mutex);
                wake.wait(lock, [this] { return stopping || !queue.empty(); });
                if (stopping) {
                    return;
                }
                next = std::move(queue.front());
                queue.pop_front();
            }
            if (!run_one(next)) {
                return;
            }
        }
    }

    // The owner thread (EDI_WORKER_OWNER_THREAD): the oldest job, once. One call is posted per submission,
    // so the calls and the jobs pair up in order.
    void run_next() {
        Pending next;
        {
            const std::lock_guard<std::mutex> lock(mutex);
            if (stopping || queue.empty()) {
                return;
            }
            next = std::move(queue.front());
            queue.pop_front();
        }
        run_one(next);
    }

    // One job and its final delivery; false when the Worker stopped meanwhile.
    bool run_one(Pending& next) {
        trace(EventKind::Started, next.channel, next.ticket);
        const Emit emit = [this, &next](Delivery delivery) {
            trace(EventKind::Emitted, next.channel, next.ticket);
            deliver(next.ticket, next.channel, std::move(delivery));
        };
        Delivery last;
        try {
            last = next.job(next.token, emit);
        } catch (...) {  // NOLINT(bugprone-empty-catch) — a job that throws delivers nothing more
        }
        trace(EventKind::Finished, next.channel, next.ticket);
        {
            const std::lock_guard<std::mutex> lock(mutex);
            tokens.erase(next.ticket);
            if (stopping) {
                return false;  // the destructor is waiting: nothing is delivered afterwards
            }
        }
        trace(EventKind::Emitted, next.channel, next.ticket);
        deliver(next.ticket, next.channel, std::move(last));
        return true;
    }
};

Worker::Worker(Post post, Seams seams) : state_(std::make_shared<State>()) {
    state_->post = std::move(post);
    state_->seams = std::move(seams);
    g_alive.fetch_add(1, std::memory_order_acq_rel);
#if !EDI_WORKER_OWNER_THREAD
    thread_ = std::thread([state = state_] { state->run(); });
#endif
}

Worker::~Worker() {
    state_->open->store(false, std::memory_order_release);
    {
        const std::lock_guard<std::mutex> lock(state_->mutex);
        state_->stopping = true;
        for (auto& [ticket, live] : state_->tokens) {
            live.token.flag_->store(true, std::memory_order_release);
        }
        state_->queue.clear();
    }
    state_->wake.notify_all();
    if (thread_.joinable()) {
        thread_.join();
    }
    g_alive.fetch_sub(1, std::memory_order_acq_rel);
}

Ticket Worker::submit(const std::string& channel, Job job) {
    State::Pending pending;
    pending.channel = channel;
    pending.job = std::move(job);
    Ticket ticket = 0;
    {
        const std::lock_guard<std::mutex> lock(state_->mutex);
        ticket = state_->next_ticket++;
        pending.ticket = ticket;
        state_->tokens.emplace(ticket, State::Live{pending.token, channel});
    }
    // Traced before the job can start, so `Submitted` always precedes `Started` in the trace.
    state_->trace(EventKind::Submitted, channel, ticket);
    {
        const std::lock_guard<std::mutex> lock(state_->mutex);
        state_->queue.push_back(std::move(pending));
    }
#if EDI_WORKER_OWNER_THREAD
    state_->post([state = state_, keep = state_->open] {
        if (keep->load(std::memory_order_acquire)) {
            state->run_next();
        }
    });
#else
    state_->wake.notify_one();
#endif
    return ticket;
}

void Worker::cancel(Ticket ticket) {
    std::string channel;
    {
        const std::lock_guard<std::mutex> lock(state_->mutex);
        const auto found = state_->tokens.find(ticket);
        if (found == state_->tokens.end()) {
            return;  // finished already, or never submitted
        }
        found->second.token.flag_->store(true, std::memory_order_release);
        channel = found->second.channel;
    }
    state_->trace(EventKind::Cancelled, channel, ticket);
}

const Seams& Worker::seams() const noexcept { return state_->seams; }

void Worker::trace(EventKind kind, const std::string& channel, std::uint64_t id) const {
    state_->trace(kind, channel, id);
}

bool Worker::any_alive() noexcept { return g_alive.load(std::memory_order_acquire) > 0; }

}  // namespace edi::work
