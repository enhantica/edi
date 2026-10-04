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
        self->owed = true;
        if (self->in_flight != 0) {
            self->worker.cancel(self->ticket);
            return;
        }
        start(self);
    }

    static void start(const std::shared_ptr<State>& self) {
        self->owed = false;
        const std::uint64_t generation = self->newest;
        self->in_flight = generation;
        auto snapshot = std::make_shared<WorkSnapshot>(snapshot_for_work(self->live));
        self->trace(work::EventKind::Snapshot, generation);
        self->ticket = self->worker.submit(
            kChannel,
            [self, snapshot, generation](const work::CancelToken& token,
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
            });
    }

    // Owner thread: the calculation of `generation` has finished.
    static void deliver(const std::shared_ptr<State>& self, std::uint64_t generation,
                        CalculationResult& result) {
        if (!self->open) {
            return;
        }
        self->in_flight = 0;
        if (generation != self->newest || result.cancelled) {
            // A newer request exists: nothing is written and nothing is shown.
            self->trace(work::EventKind::Rejected, generation);
            self->owed = true;
        } else {
            PreviewResult shown{generation, result.refusal};
            if (publish(self->live, std::move(result)) == PublishOutcome::Published) {
                self->trace(work::EventKind::Published, generation);
                if (self->hooks.published) {
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
            start(self);
        }
    }
};

LivePreview::LivePreview(Project& live, work::Worker& worker, Hooks hooks, Seams seams)
    : state_(std::make_shared<State>(live, worker, std::move(hooks), std::move(seams))) {}

LivePreview::~LivePreview() {
    state_->open = false;
    if (state_->in_flight != 0) {
        state_->worker.cancel(state_->ticket);
    }
}

void LivePreview::apply(const Edit& edit) {
    State& s = *state_;
    s.trace(work::EventKind::Input, s.newest + 1);
    // An Edit refuses before it writes (edi/edit.hpp), so a refusal leaves nothing to undo: the model,
    // its publication and a calculation in flight are untouched because nothing touched them (I10).
    try {
        edit();
    } catch (...) {
        s.trace(work::EventKind::Refused, s.newest + 1);
        throw;
    }
    s.live.note_edit();
    ++s.newest;
    s.trace(work::EventKind::Applied, s.newest);
    if (s.hooks.edited) {
        s.hooks.edited();
    }
    State::request(state_);
}

void LivePreview::recalculate() {
    State& s = *state_;
    s.trace(work::EventKind::Input, s.newest + 1);
    ++s.newest;
    s.trace(work::EventKind::Applied, s.newest);
    State::request(state_);
}

bool LivePreview::busy() const noexcept { return state_->in_flight != 0 || state_->owed; }

std::uint64_t LivePreview::newest_request() const noexcept { return state_->newest; }

}  // namespace edi
