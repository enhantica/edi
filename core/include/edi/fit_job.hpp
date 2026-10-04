// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_FIT_JOB_HPP
#define EDI_FIT_JOB_HPP

#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "edi/model.hpp"
#include "edi/presentation.hpp"
#include "edi/worker.hpp"

// ADR-0020 §9: a fit on the worker. The fit runs on a snapshot of the project by its fitting mode —
// Project::fit for `single`, Project::fit_joint for `joint`, the entries the CLI's fit takes — and its
// preamble, every accepted iteration and its end arrive on the owner thread as the worker's ordered,
// never-dropped deliveries (work::Emit), the end last. The live project is written once, on the owner
// thread, when the fit ends: the fitted values, uncertainties and fit start, with the pattern the fit's
// own last calculation left, all or nothing. Qt-free; every member runs on the owner thread.

namespace edi {

// How a fit ended, on the owner thread.
struct FitReport {
    // DONE, MAX_ITER, NO_STEP or CANCELLED: the live project holds the fit's result, a cancelled fit's
    // partial one as crysta returns it. ERROR: the fit was refused or failed, and `refusal` says why.
    // SUPERSEDED: an input was written on the live project while the fit ran. Neither of these two
    // writes anything.
    FitStatus status = FitStatus::ERROR;
    std::string refusal;
    // What the fit returned; absent when it was refused.
    std::optional<FitResultBase> result;
    bool adopted() const noexcept {
        return status == FitStatus::DONE || status == FitStatus::MAX_ITER || status == FitStatus::NO_STEP ||
               status == FitStatus::CANCELLED;
    }
};

// One pattern frame of a running fit: each experiment's pattern at one iteration's parameters, in the
// project's experiment order (capture_pattern of a copy the job calculates; `current` is true).
using FitFrame = std::vector<PatternSource>;

class FitJob {
   public:
    struct Hooks {
        // Once, before the first iteration: the fit's facts and the pre-fit record.
        std::function<void(const FitPreamble&)> started;
        // Once per accepted iteration, in order.
        std::function<void(const IterationRecord&)> iterated;
        // A frame, between iterations. The job calculates the next one only after `frame_shown`, so a slow
        // owner sees fewer frames and the fit is never queued behind them. Empty: no frames are calculated.
        std::function<void(const FitFrame&)> frame;
        // Once, last: nothing of this fit is delivered afterwards.
        std::function<void(const FitReport&)> finished;
    };
    // Test instrumentation: production constructs a FitJob without it.
    struct Seams {
        // Worker thread: each time crysta asks whether to stop (between iterations), numbered from 1,
        // before the job's token is read. A test cancels at a chosen iteration from here.
        std::function<void(int)> polled;
    };

    FitJob(Project& live, work::Worker& worker, Hooks hooks, Seams seams = {});
    // Cancels a fit in progress; nothing of it is delivered afterwards.
    ~FitJob();
    FitJob(const FitJob&) = delete;
    FitJob& operator=(const FitJob&) = delete;

    // Fits the live project as it is now. False, and nothing starts, while a fit is running.
    bool start();
    // Asks a running fit to stop at crysta's next check; it still ends with `finished`.
    void cancel();
    // The owner has shown the last frame: the job may calculate the next.
    void frame_shown();
    // From `start` until `finished` has run.
    bool running() const noexcept;
    // The running fit's job on the worker, or 0.
    work::Ticket ticket() const noexcept;

   private:
    struct State;
    std::shared_ptr<State> state_;
};

}  // namespace edi

#endif  // EDI_FIT_JOB_HPP
