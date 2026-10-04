// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_LIVE_PREVIEW_HPP
#define EDI_LIVE_PREVIEW_HPP

#include <cstdint>
#include <functional>
#include <memory>
#include <string>

#include "edi/calculation.hpp"
#include "edi/edit.hpp"
#include "edi/model.hpp"
#include "edi/worker.hpp"

// ADR-0020 §2: the preview protocol. Every edit is written to the live project at once and is a
// request. One calculation is in flight at a time, on the worker; when its delivery runs it
// publishes only if no newer request exists. Otherwise it is rejected — nothing is written and
// nothing is shown — and the newest state is calculated. Qt-free; every member runs on the owner
// thread.

namespace edi {

struct PreviewResult {
    std::uint64_t generation = 0;  // the request this publication serves
    std::string refusal;           // empty, or why crysta refused the calculation
};

class LivePreview {
   public:
    struct Hooks {
        std::function<void()> edited;                         // a change ran on the live project
        std::function<void(const PreviewResult&)> published;  // a calculation was published
        // A calculation of this generation began, and ended, on the worker: edi::calculate's own first and
        // last acts (Calculating, Calculated), for every calculation the worker runs, a superseded one
        // included. Each arrives on the owner thread, in order, before that calculation's publication or
        // rejection. Empty for an owner that does not count calculations.
        std::function<void(std::uint64_t)> calculating;
        std::function<void(std::uint64_t)> calculated;
    };
    // Test instrumentation: production constructs a LivePreview without it.
    struct Seams {
        std::function<CalculationResult(WorkSnapshot&, const work::CancelToken&)> calculate;
    };

    LivePreview(Project& live, work::Worker& worker, Hooks hooks, Seams seams = {});
    ~LivePreview();
    LivePreview(const LivePreview&) = delete;
    LivePreview& operator=(const LivePreview&) = delete;

    // An edit: runs it on the live project at once. The door takes an edi::Edit and nothing else: one
    // operation that refuses before it writes, or completes (edi/edit.hpp). If it refuses, the
    // exception reaches the caller and nothing else happens: nothing was written, there is no
    // request, the publication the model holds stays current, and a calculation in flight is still
    // the newest and publishes. Otherwise the edit is noted (Project::note_edit), `edited` is called,
    // and it is a request. There is no rollback: a callable cannot be passed, so a change that writes
    // and then throws cannot reach this door.
    void apply(const Edit& edit);
    // A request with no change (a project just opened, a block just loaded).
    void recalculate();
    // A calculation is in flight or owed.
    bool busy() const noexcept;
    std::uint64_t newest_request() const noexcept;

   private:
    struct State;
    std::shared_ptr<State> state_;
};

}  // namespace edi

#endif  // EDI_LIVE_PREVIEW_HPP
