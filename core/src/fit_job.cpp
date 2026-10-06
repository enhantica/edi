// SPDX-License-Identifier: BSD-3-Clause
#include "edi/fit_job.hpp"

#include <atomic>
#include <exception>
#include <map>
#include <stdexcept>
#include <iomanip>
#include <locale>
#include <sstream>
#include <utility>

#include "edi/calculation.hpp"
#include "edi/categories.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/scan.hpp"
#include "edi/selectors.hpp"

namespace edi {
namespace {
const char* const kChannel = "fit";

// Every input of a fit that the calculation stamps (WorkStamps) do not carry, when the fit was snapshotted.
// The stamps cover what a calculation reads; a fit also reads its free set, the fitting mode, the minimizer
// settings and the banks' joint weights, and its adoption writes each parameter's uncertainty and fit start
// (Undo's capture). So: every parameter's write identities — value, uncertainty, free flag and fit start, an
// equal-value write included, which an admitted-write epoch does not see when it goes round the door — and
// those settings' values. Any difference at the end supersedes the fit.
struct FitInputs {
    std::vector<std::uint64_t> identities;
    std::string settings;
};

FitInputs inputs_of(Project& project) {
    FitInputs inputs;
    for (const Parameter* parameter : project.parameters()) {
        inputs.identities.push_back(parameter->value.written());
        inputs.identities.push_back(parameter->uncertainty.written());
        inputs.identities.push_back(parameter->free.written());
        inputs.identities.push_back(parameter->start_value.written());
        inputs.identities.push_back(parameter->start_uncertainty.written());
    }
    std::ostringstream settings;
    settings.imbue(std::locale::classic());
    settings << std::setprecision(17) << project.fitting_mode << '\x1f' << project.descent << '\x1f'
             << project.minimizer_max_iterations << '\x1f' << project.minimizer_chi_square_tolerance << '\x1f'
             << (project.minimizer_type.has_value() ? "T" + *project.minimizer_type : std::string("-"));
    for (const auto& experiment : project.experiments) {
        settings << '\x1f' << experiment->dataset_weight;
    }
    inputs.settings = settings.str();
    return inputs;
}

bool operator!=(const FitInputs& a, const FitInputs& b) {
    return a.identities != b.identities || a.settings != b.settings;
}

// What the worker hands back: the fitted copy and what its fit returned, or why there is none.
struct Outcome {
    WorkStamps stamps;
    FitInputs inputs;
    std::shared_ptr<Project> fitted;
    std::optional<FitResultBase> result;
    std::string refusal;
    bool scan = false;
};

// Worker thread: the project's own fit entry for its mode, as the CLI's fit takes it (edi.Analysis.fit).
FitResultBase fit_by_mode(Project& project, const IterationCallback& on_iteration, const PreambleCallback& on_start,
                          const CancelCallback& should_cancel, const ScanStartCallback& on_scan_start,
                          const FileCompleteCallback& on_file_complete) {
    const std::string mode = effective_fitting_mode(project);
    if (mode == "single") {
        return project.fit(on_iteration, on_start, should_cancel);
    }
    if (mode == "joint") {
        return project.fit_joint(on_iteration, on_start, should_cancel);
    }
    if (mode == "sequential") {
        return project.fit_sequential({}, {}, on_scan_start, on_file_complete, should_cancel);
    }
    if (mode == "independent") {
        return project.fit_independent({}, {}, on_scan_start, on_file_complete, should_cancel);
    }
    throw std::invalid_argument("Start fitting runs the single, joint, sequential and independent fitting modes; this "
                                "project's is '" + mode + "'");
}

// Worker thread: `values` (identity path -> value) written onto the preview copy, its symmetry completed
// and its pattern calculated. Empty when a value names no parameter or the calculation refuses.
FitFrame frame_of(Project& preview, const std::map<std::string, double>& values) {
    if (values.empty()) {
        return {};
    }
    std::map<std::string, Parameter*> by_path;
    for (const ParameterEntry& entry : parameter_entries(preview)) {
        by_path.emplace(entry.path, entry.parameter);
    }
    for (const auto& [path, value] : values) {
        const auto found = by_path.find(path);
        if (found == by_path.end() || found->second == nullptr) {
            return {};
        }
        found->second->value = value;
    }
    FitFrame frame;
    try {
        apply_relations(preview);
        preview.calculate();
        frame.reserve(preview.experiments.size());
        for (std::size_t index = 0; index < preview.experiments.size(); ++index) {
            frame.push_back(capture_pattern(preview, index));
        }
    } catch (const std::exception&) {
        return {};
    }
    return frame;
}
// Worker thread: the scan's file just fitted, drawn on the preview copy: its measured data from the file, every
// parameter at its results row, the pattern calculated. Empty when the row is not that file's or anything refuses.
FitFrame scan_frame_of(Project& preview, const std::string& directory, const std::string& file) {
    FitFrame frame;
    try {
        const ScanResults last = read_last_scan_result(preview);
        const auto row = last.rows.find(file);
        if (row == last.rows.end()) {
            return {};
        }
        std::map<std::string, std::size_t> column;
        for (std::size_t i = 0; i < last.header.size(); ++i) {
            column.emplace(last.header[i], i);
        }
        for (const NamedSlot& slot : named_slots(preview)) {
            const auto found = column.find(scan_results_column(slot.unique_name));
            if (found != column.end()) {
                slot.parameter->value = std::stod(row->second[found->second]);
            }
        }
        preview.experiment().data = read_scan_dataset(directory, file, preview.experiment().effective_beam_mode());
        apply_relations(preview);
        preview.calculate();
        frame.push_back(capture_pattern(preview, 0));
    } catch (const std::exception&) {
        return {};
    }
    return frame;
}
}  // namespace

// Shared with the job and the deliveries on their way, so a delivery that arrives after the FitJob is
// gone finds `open` false and does nothing.
struct FitJob::State {
    State(Project& project, work::Worker& runner, Hooks callbacks, Seams injected)
        : live(project), worker(runner), hooks(std::move(callbacks)), seams(std::move(injected)) {}

    Project& live;
    work::Worker& worker;
    Hooks hooks;
    Seams seams;
    bool open = true;
    work::Ticket ticket = 0;  // the running fit's job, or 0
    // Set by the owner when it has shown a frame, cleared by the worker when it emits one.
    std::atomic<bool> frame_wanted{true};
    // A scan draws each file it fits (Follow).
    std::atomic<bool> following{true};

    // Owner thread: the fit has ended. The live project takes its result only if nothing it depends on
    // was written since the snapshot; then the fitted parameters and the fitted pattern, together.
    static void finish(const std::shared_ptr<State>& self, Outcome& outcome) {
        if (!self->open) {
            return;
        }
        self->ticket = 0;
        FitReport report;
        report.result = std::move(outcome.result);
        report.refusal = std::move(outcome.refusal);
        if (!report.result.has_value()) {
            report.status = FitStatus::ERROR;
            if (report.refusal.empty()) {
                report.refusal = "the fit failed";
            }
        } else if (report.result->status == FitStatus::ERROR) {
            report.status = FitStatus::ERROR;
            report.refusal = "the fit failed: crysta reported an error";
        } else if (outcome.scan) {
            // The scan's results are the rows on disk; the template is left as it was.
            report.status = report.result->status;
        } else if (!unchanged_since(self->live, outcome.stamps) ||
                   inputs_of(self->live) != outcome.inputs ||
                   !copy_parameter_states(self->live, *outcome.fitted)) {
            report.status = FitStatus::SUPERSEDED;
        } else {
            // The fitted copy's pattern is the fit's own last calculation, at the values just written: it
            // is published under the stamps the live project has now. The fit's result record goes with it.
            copy_fit_result(self->live, *outcome.fitted);
            publish(self->live, stage_computed(*outcome.fitted, work_stamps(self->live)));
            report.status = report.result->status;
        }
        if (self->hooks.finished) {
            self->hooks.finished(report);
        }
    }
};

FitJob::FitJob(Project& live, work::Worker& worker, Hooks hooks, Seams seams)
    : state_(std::make_shared<State>(live, worker, std::move(hooks), std::move(seams))) {}

FitJob::~FitJob() {
    state_->open = false;
    if (state_->ticket != 0) {
        state_->worker.cancel(state_->ticket);
    }
}

bool FitJob::start(const Project* scan_template) {
    if (state_->ticket != 0) {
        return false;
    }
    auto snapshot =
        std::make_shared<WorkSnapshot>(snapshot_for_work(scan_template != nullptr ? *scan_template : state_->live));
    auto inputs = std::make_shared<FitInputs>(inputs_of(state_->live));
    state_->frame_wanted.store(true, std::memory_order_release);
    const std::shared_ptr<State> self = state_;
    state_->ticket = state_->worker.submit(
        kChannel, [self, snapshot, inputs](const work::CancelToken& token, const work::Emit& emit) -> work::Delivery {
            auto outcome = std::make_shared<Outcome>();
            outcome->stamps = snapshot->stamps;
            outcome->inputs = *inputs;
            outcome->scan = is_scan_fitting_mode(effective_fitting_mode(snapshot->project));
            // The frames are drawn on a second copy, so the fit's own copy is touched by the fit alone. A scan
            // fits other files' data than the template's, so it draws none.
            std::shared_ptr<Project> preview;
            if ((self->hooks.frame && !outcome->scan) || (self->hooks.file_frame && outcome->scan)) {
                preview = std::make_shared<Project>(snapshot->project);
            }
            // The scan's data directory, resolved once, for the files it draws.
            std::string directory;
            if (outcome->scan && preview) {
                try {
                    directory = scan_datasets(snapshot->project).directory;
                } catch (const std::exception&) {
                    preview.reset();
                }
            }
            const PreambleCallback on_start = [&self, &emit](const FitPreamble& preamble) {
                emit([self, preamble] {
                    if (self->open && self->hooks.started) {
                        self->hooks.started(preamble);
                    }
                });
            };
            const IterationCallback on_iteration = [&self, &emit, &preview](const IterationRecord& record) {
                emit([self, record] {
                    if (self->open && self->hooks.iterated) {
                        self->hooks.iterated(record);
                    }
                });
                if (preview && self->frame_wanted.load(std::memory_order_acquire)) {
                    FitFrame frame = frame_of(*preview, record.values);
                    if (!frame.empty()) {
                        self->frame_wanted.store(false, std::memory_order_release);
                        emit([self, frame = std::move(frame)] {
                            if (self->open && self->hooks.frame) {
                                self->hooks.frame(frame);
                            }
                        });
                    }
                }
            };
            const ScanStartCallback on_scan_start = [&self, &emit](const ScanPreamble& preamble) {
                emit([self, preamble] {
                    if (self->open && self->hooks.scan_started) {
                        self->hooks.scan_started(preamble);
                    }
                });
            };
            const FileCompleteCallback on_file_complete = [&self, &emit, &preview,
                                                           &directory](const ScanFileRecord& record) {
                emit([self, record] {
                    if (self->open && self->hooks.file_completed) {
                        self->hooks.file_completed(record);
                    }
                });
                if (preview && self->following.load(std::memory_order_acquire) &&
                    self->frame_wanted.load(std::memory_order_acquire)) {
                    FitFrame frame = scan_frame_of(*preview, directory, record.file_name);
                    if (!frame.empty()) {
                        self->frame_wanted.store(false, std::memory_order_release);
                        emit([self, file = record.file_name, frame = std::move(frame)] {
                            if (self->open && self->hooks.file_frame) {
                                self->hooks.file_frame(file, frame);
                            }
                        });
                    }
                }
            };
            int polls = 0;
            const CancelCallback should_cancel = [&self, &token, &polls] {
                ++polls;
                if (self->seams.polled) {
                    self->seams.polled(polls);
                }
                return token.cancelled();
            };
            try {
                outcome->result = fit_by_mode(snapshot->project, on_iteration, on_start, should_cancel, on_scan_start,
                                              on_file_complete);
                outcome->fitted = std::shared_ptr<Project>(snapshot, &snapshot->project);
            } catch (const std::exception& refusal) {
                outcome->refusal = refusal.what();
            } catch (...) {
                outcome->refusal = "the fit failed";
            }
            return [self, outcome] { State::finish(self, *outcome); };
        });
    return true;
}

void FitJob::cancel() {
    if (state_->ticket != 0) {
        state_->worker.cancel(state_->ticket);
    }
}

void FitJob::frame_shown() { state_->frame_wanted.store(true, std::memory_order_release); }

void FitJob::follow(bool on) { state_->following.store(on, std::memory_order_release); }

bool FitJob::running() const noexcept { return state_->ticket != 0; }

work::Ticket FitJob::ticket() const noexcept { return state_->ticket; }

}  // namespace edi
