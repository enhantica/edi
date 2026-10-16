// SPDX-License-Identifier: BSD-3-Clause
#include "edi/live_preview.hpp"

#include <utility>

namespace edi {
namespace {
const char* const kChannel = "preview";
}  // namespace

// Shared with the jobs and deliveries on their way, so a delivery that arrives after the
// LivePreview is gone finds `open` false and does nothing.
struct LivePreview::State {
    State(Project& project, work::Worker& runner, Hooks callbacks, Seams injected)
        : live(project), worker(runner), hooks(std::move(callbacks)), seams(std::move(injected)) {}

    Project& live;
    work::Worker& worker;
    Hooks hooks;
    Seams seams;
    bool open = true;
    std::uint64_t newest = 0;     // the number of the newest request
    std::uint64_t in_flight = 0;  // the generation being calculated, or 0
    work::Ticket ticket = 0;      // its job
    bool owed = false;            // a calculation of the current state is owed

    void trace(work::EventKind kind, std::uint64_t id) const { worker.trace(kind, kChannel, id); }

    // Worker thread: a calculation's start or end, traced, and handed to the owner's hook in the job's
    // own ordered stream (work::Emit), so it arrives before the job's final delivery.
    static void observe(const std::shared_ptr<State>& self, work::EventKind kind, std::uint64_t generation,
                        const work::Emit& emit) {
        self->trace(kind, generation);
        const bool start = kind == work::EventKind::Calculating;
        if (start ? self->hooks.calculating : self->hooks.calculated) {
            emit([self, start, generation] {
                if (self->open) {
                    (start ? self->hooks.calculating : self->hooks.calculated)(generation);
                }
            });
        }
    }

    // A request exists that no calculation serves yet. The calculation in flight, if any, is
    // obsolete: it stops at its next checkpoint and its result is rejected. The newest state is
    // calculated as soon as the worker is free.
    static void request(const std::shared_ptr<State>& self) {
        if (!self->open) return;
        self->owed = true;
        if (self->in_flight != 0) {
            self->worker.cancel(self->ticket);
            return;
        }
        start(self);
    }

    static void start(const std::shared_ptr<State>& self) {
        if (!self->open || self->in_flight != 0) return;
        const std::uint64_t generation = self->newest;
        auto snapshot = std::make_shared<WorkSnapshot>(snapshot_for_work(self->live));
        self->trace(work::EventKind::Snapshot, generation);
        if (!self->open) return;
        work::Job job = [self, snapshot, generation](const work::CancelToken& token,
                                         const work::Emit& emit) -> work::Delivery {
                // The calculation traces its own start and end (edi::calculate), so the two events lie
                // inside whatever times the call. A seam that replaces the calculation without running
                // it has none of its own: the pair is then traced when it returns.
                bool traced = false;
                snapshot->trace = [&self, &traced, &emit, generation](work::EventKind kind) {
                    traced = true;
                    observe(self, kind, generation, emit);
                };
                auto result = std::make_shared<CalculationResult>(
                    self->seams.calculate ? self->seams.calculate(*snapshot, token)
                                          : calculate(*snapshot, token));
                snapshot->trace = nullptr;
                if (!traced) {
                    observe(self, work::EventKind::Calculating, generation, emit);
                    observe(self, work::EventKind::Calculated, generation, emit);
                }
                return [self, result, generation] { deliver(self, generation, *result); };
            };
        // Snapshot, callable and Worker queue admission may allocate. Until submit
        // returns, owed remains true and no real in-flight ticket is published.
        const work::Ticket ticket = self->worker.submit(kChannel, std::move(job));
        self->ticket = ticket;
        self->in_flight = generation;
        self->owed = false;
        if (!self->open) {
            // Retirement during admission must cancel the ACTUAL returned job,
            // not discard its ticket as though preparation never admitted it.
            try { self->worker.cancel(ticket); } catch (...) { /* Worker teardown still owns this cancelled/retired job. */ }
        }
    }

    // Owner thread: the calculation of `generation` has finished.
    static void deliver(const std::shared_ptr<State>& self, std::uint64_t generation,
                        CalculationResult& result) {
        if (!self->open) {
            return;
        }
        self->in_flight = 0;
        self->ticket = 0; // A finished ticket can never stand for a later preparation.
        if (generation != self->newest || result.cancelled) {
            // A newer request exists: nothing is written and nothing is shown.
            self->trace(work::EventKind::Rejected, generation);
            self->owed = true;
        } else {
            PreviewResult shown{generation, result.refusal};
            if (publish(self->live, std::move(result)) == PublishOutcome::Published) {
                self->trace(work::EventKind::Published, generation);
                if (self->open && self->hooks.published) {
                    self->hooks.published(shown);
                }
            } else {
                // A write went round LivePreview: nothing is written, and the current state is
                // calculated.
                self->trace(work::EventKind::Superseded, generation);
                self->owed = true;
            }
        }
        // The next calculation, in the same turn — unless a hook started it already.
        if (self->open && self->owed && self->in_flight == 0) {
            try { start(self); }
            catch (...) {
                // This is an owner-thread delivery, outside an edit's catch.
                // No new job was admitted; keep owed for an actual edit/Undo retry.
                // The normal observer reports the preparation refusal, not a
                // fabricated completed calculation or cleared busy state.
                if (self->open && self->hooks.published) {
                    const PreviewResult refused{self->newest,
                        "The newest calculation could not be prepared; retry the edit or Undo."};
                    self->hooks.published(refused);
                }
            }
        }
    }
};

LivePreview::LivePreview(Project& live, work::Worker& worker, Hooks hooks, Seams seams)
    : state_(std::make_shared<State>(live, worker, std::move(hooks), std::move(seams))) {}

LivePreview::~LivePreview() {
    state_->open = false;
    if (state_->in_flight != 0) {
        try { state_->worker.cancel(state_->ticket); }
        catch (...) { /* Cancel sets the real token before fallible tracing; Worker teardown also owns it. */ }
    }
}

void LivePreview::apply(const Edit& edit, bool* applied) {
    if (applied != nullptr) *applied = false;
    const auto self = state_; // The edited hook may retire/delete the LivePreview owner.
    State& s = *self;
    if (!s.open) return;
    s.trace(work::EventKind::Input, s.newest + 1);
    if (!s.open) return;
    // An Edit refuses before it writes (edi/edit.hpp), so a refusal leaves nothing to undo: the model,
    // its publication and a calculation in flight are untouched because nothing touched them (I10).
    try {
        edit();
    } catch (...) {
        s.trace(work::EventKind::Refused, s.newest + 1);
        throw;
    }
    if (applied != nullptr) *applied = true;
    s.live.note_edit();
    ++s.newest;
    s.trace(work::EventKind::Applied, s.newest);
    if (!s.open) return;
    if (s.hooks.edited) {
        s.hooks.edited();
    }
    if (s.open) State::request(self);
}

void LivePreview::apply_setting(const Edit& edit) { edit(); }

void LivePreview::recalculate() {
    const auto self = state_;
    State& s = *self;
    if (!s.open) return;
    s.trace(work::EventKind::Input, s.newest + 1);
    ++s.newest;
    s.trace(work::EventKind::Applied, s.newest);
    if (s.open) State::request(self);
}

bool LivePreview::busy() const noexcept { return state_->in_flight != 0 || state_->owed; }

std::uint64_t LivePreview::newest_request() const noexcept { return state_->newest; }

}  // namespace edi
