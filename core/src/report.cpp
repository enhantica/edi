// SPDX-License-Identifier: BSD-3-Clause
#include "edi/report.hpp"

#include "crysta/fit_report.hpp"

#include <cmath>
#include <cstdio>
#include <iomanip>
#include <locale>
#include <sstream>

// . The machine half is a straight call into the engine's emitter; everything else here is edi's
// own human view, which is the only reason this file is long. Presentation lives in the product
// core (not in a CLI, not in an example) so every edi surface renders one implementation.

namespace edi {
namespace {

// The refined-parameter table's reserved column widths. Data rows are ASCII, so character width is
// display width. The label column is wide because edi keys results by full identity paths
// (`experiments[wish_1_10].background[10].intensity`) rather than by short engine labels; a
// narrower column would ragged the numeric columns on almost every row.
constexpr int kLabelWidth = 48;

// Hand-aligned to the data-row widths below (7/11/10/12). The header and the change column carry
// UTF-8; every DATA cell is ASCII, so byte width equals display width there and the numeric columns
// stay aligned. The glyphs sit only where that is safe: in this literal, and at the END of a row.
constexpr const char* kIterHeader = "   iter   time (s)       Rwp          \u03c7\u00b2   change";

// Human-facing numbers are formatted for reading, not for comparison — the machine record is the
// comparison channel. Still classic-locale, so the two views cannot disagree about a decimal point.
std::string fixed(double value, int precision, int width = 0) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    if (width > 0) {
        out << std::setw(width);
    }
    out << std::fixed << std::setprecision(precision) << value;
    return out.str();
}

void append_padded(std::ostringstream& out, const std::string& text, int width) {
    out << text;
    for (int pad = static_cast<int>(text.size()); pad < width; ++pad) {
        out << ' ';
    }
}

}  // namespace

// The seam-S18 presentation contract; see report.hpp for the rule. This is its ONE implementation,
// shared by the streaming progress line and the `full` parameter table — and it is public so the
// contract can be exercised on constructed values rather than only on whatever a live fit happens
// to produce.
std::string format_change(double current, double previous) {
    // A percentage of zero is undefined, not infinite, and a non-finite operand cannot yield a
    // meaningful one either. Both blank rather than rendering a number a reader would trust.
    if (previous == 0.0 || !std::isfinite(previous) || !std::isfinite(current)) {
        return {};
    }
    // The denominator is the START value: this column answers "how far has it moved from where it
    // began", so using the refined value would silently change the question.
    const double percent = (current - previous) / std::fabs(previous) * 100.0;
    if (std::fabs(percent) < 0.05) {
        return {};  // immaterial — show nothing rather than noise
    }
    return fixed(std::fabs(percent), 1) + "% " + (percent < 0.0 ? "\u2193" : "\u2191");
}

namespace {

// edi verbosity -> the engine emitter's. Confined to this TU, like every other crysta contact.
crysta::VerbosityEnum to_engine(VerbosityEnum verbosity) {
    switch (verbosity) {
        case VerbosityEnum::OFF:
            return crysta::VerbosityEnum::Off;
        case VerbosityEnum::COMPACT:
            return crysta::VerbosityEnum::Compact;
        case VerbosityEnum::FULL:
            return crysta::VerbosityEnum::Full;
    }
    return crysta::VerbosityEnum::Off;
}

// edi status -> the engine's. The two sets are deliberately the same shape; this mapping is what
// keeps them from having to be the same TYPE on edi's public surface.
crysta::FitStatus to_engine(FitStatus status) {
    switch (status) {
        case FitStatus::DONE:
            return crysta::FitStatus::Done;
        case FitStatus::MAX_ITER:
            return crysta::FitStatus::MaxIter;
        case FitStatus::NO_STEP:
            return crysta::FitStatus::NoStep;
        case FitStatus::CANCELLED:
            return crysta::FitStatus::Cancelled;
        case FitStatus::ERROR:
            return crysta::FitStatus::Error;
        case FitStatus::UNAVAILABLE:
            return crysta::FitStatus::Unavailable;
        case FitStatus::SUPERSEDED:
            return crysta::FitStatus::Superseded;
    }
    return crysta::FitStatus::Error;
}

// edi's per-iteration record -> the engine's. crysta merged its streamed IterationRecord and the
// report's history row into ONE type, so the row is filled by name: only the members the record
// renders (iter / rwp / reduced_chi_square / elapsed_ms / unevaluable_trials) cross here;
// `chi_square` and `parameters` stay at their defaults, exactly as the emitter leaves them unread.
crysta::IterationRecord to_engine(const IterationRecord& record) {
    crysta::IterationRecord row;
    row.iteration = record.iteration;
    row.rwp = record.rwp;
    row.reduced_chi_square = record.reduced_chi_square;
    row.elapsed_ms = record.elapsed_ms;
    row.unevaluable_trials = record.unevaluable_trials;
    return row;
}

}  // namespace

std::string machine_report(const Project& project, const FitResultBase& outcome,
                           VerbosityEnum verbosity) {
    crysta::FitReport report;
    report.kind = crysta::RecordKind::Fit;
    report.status = to_engine(outcome.status);
    // Which refinement ran, not what the project could hold: `banks` is populated by the joint path
    // and left empty by the single-bank one, exactly as crysta emits mode=joint only from its joint
    // path. Deriving this from `project.experiments` instead would label a single-bank refine of a
    // multi-bank project as joint.
    report.joint = !outcome.banks.empty();
    report.converged = outcome.converged;
    report.n_points_loaded = outcome.n_points_loaded;
    report.n_points_fitted = outcome.n_points_fitted;
    // The count of refined parameters, taken from the engine-keyed map so it can never disagree with
    // the number of `param.*` rows below it.
    report.n_free = outcome.engine_values.size();
    report.iterations = outcome.iterations;
    // Schema 7: a fit record must name the descent flow that ran; carried verbatim from
    // the engine result.
    report.descent = outcome.descent;
    report.reduced_chi_square = outcome.reduced_chi_square;
    report.rwp = outcome.rwp;
    // `cutoff_policy` is LEFT EMPTY on purpose, which omits the row: edi exposes no cutoff-policy
    // control, and a surface that cannot vary a field must not emit a constant for it. It shows up
    // as a plain added line when diffing against crysta — the honest representation of a capability
    // edi does not have, rather than a field that looks aligned while hiding the asymmetry. The
    // boundary-contact counters are the ENGINE's values carried through the outcome — never edi
    // defaults: a record that always said 0 would erase exactly the signal that distinguishes
    // boundary-limited convergence from an interior optimum.
    report.unevaluable_trials = outcome.unevaluable_trials;
    report.terminal_unevaluable_trials = outcome.terminal_unevaluable_trials;
    report.elapsed_ms = outcome.elapsed_ms;
    for (const IterationRecord& record : outcome.iterations_history) {
        report.history.push_back(to_engine(record));
    }
    // Engine labels, not edi identity paths: the record is crysta's artifact and must use crysta's
    // parameter identity on every surface, or the per-parameter rows could never be compared.
    report.values = outcome.engine_values;
    report.uncertainty = outcome.engine_uncertainty;
    for (const BankMetric& bank : outcome.banks) {
        report.banks.push_back({bank.name, bank.n_points, bank.rwp, bank.chi_square});
    }
    return crysta::format_fit_report(report, to_engine(verbosity));
}

std::string error_report(VerbosityEnum verbosity) {
    // Rendered by the same engine emitter as every other shape, so the failure record cannot drift
    // from the contract the success records follow.
    return crysta::format_fit_report(crysta::make_error_report(), to_engine(verbosity));
}

std::string calc_report(std::size_t n_points, double checksum, double elapsed_ms,
                        VerbosityEnum verbosity) {
    // The engine's own calc record: make_calc_report + the shared emitter, exactly the path
    // `crysta <dir> calc` renders through, so the bytes cannot drift from crysta's.
    return crysta::format_fit_report(crysta::make_calc_report(n_points, checksum, elapsed_ms),
                                     to_engine(verbosity));
}

namespace {

// Scan-line building blocks, file-internal: the two public renderers below are the surface. The
// bar width is fixed — the packet's ~80-column budget; a real-terminal measurement narrowing it
// changes this ONE constant.
constexpr int kScanBarCells = 14;

// `MmSSs` / `Ss` / `HhMMmSSs`, rounded to whole seconds — a progress line reads as a clock, not
// a measurement (the machine record carries exact elapsed_ms; this channel is the human one).
std::string scan_duration(double seconds) {
    const long long total = static_cast<long long>(seconds + 0.5);
    char buffer[48];
    if (total < 60) {
        std::snprintf(buffer, sizeof buffer, "%llds", total);
    } else if (total < 3600) {
        std::snprintf(buffer, sizeof buffer, "%lldm%02llds", total / 60, total % 60);
    } else {
        std::snprintf(buffer, sizeof buffer, "%lldh%02lldm%02llds", total / 3600,
                      (total % 3600) / 60, total % 60);
    }
    return buffer;
}

// The display stem (fs::path::stem semantics on a bare name): the scan file's extension is walk
// plumbing, not identity — the owner's requested line names files as `cosio_213K`, never `.dat`.
std::string scan_display_name(const std::string& file_name) {
    const std::size_t dot = file_name.rfind('.');
    return dot != std::string::npos && dot > 0 ? file_name.substr(0, dot) : file_name;
}

// Review-1 F2: a duration whose population differs from the line's counts must SAY so, or the
// reader takes it for the scan's. `measured` is what the clock covered, `population` the count
// the rest of the line reports; equal means a fresh scan and the text is unchanged.
std::string scan_elapsed_suffix(const std::string& duration, int measured, int population) {
    return measured < population ? duration + " this run" : duration;
}

std::string scan_elapsed(double seconds, int measured, int population) {
    return scan_elapsed_suffix(scan_duration(seconds), measured, population);
}

void append_scan_part(std::string& line, const std::string& part) {
    if (!line.empty()) {
        line += " · ";
    }
    line += part;
}

}  // namespace

std::string scan_progress_line(int completed, std::optional<int> total_files,
                               double elapsed_seconds, int measured_completed, int ok_count,
                               int fail_count, const std::string& file_name,
                               double reduced_chi_square) {
    std::string line;
    if (total_files.has_value() && *total_files > 0) {
        const int filled = static_cast<int>(
            kScanBarCells * static_cast<double>(completed) / *total_files + 0.5);
        std::string bar = "[";
        for (int cell = 0; cell < filled; ++cell) {
            bar += "█";
        }
        for (int cell = filled; cell < kScanBarCells; ++cell) {
            bar += "░";
        }
        bar += "]";
        append_scan_part(line, bar);
        append_scan_part(line, std::to_string(completed) + "/" + std::to_string(*total_files));
        const int percent =
            static_cast<int>(100.0 * completed / *total_files + 0.5);
        append_scan_part(line, std::to_string(percent) + "%");
    } else {
        // N unknown: a bare count, NO percentage and NO eta — degrade rather than guess.
        append_scan_part(line, std::to_string(completed) + " files");
    }
    append_scan_part(line,
                     "elapsed " + scan_elapsed(elapsed_seconds, measured_completed, completed));
    if (total_files.has_value() && measured_completed > 0 && completed < *total_files) {
        // mean(elapsed over the completions the clock COVERS) × remaining — an ESTIMATE, and
        // labelled as one. The denominator is `measured_completed`, never `completed`: on a
        // resumed scan the elapsed covers only this call's files, so dividing by the whole-scan
        // total would pair one population's time with another's count and systematically
        // under-estimate.
        const double eta = elapsed_seconds / measured_completed * (*total_files - completed);
        append_scan_part(line, "eta " + scan_duration(eta));
    }
    append_scan_part(line, std::to_string(ok_count) + " ok");
    append_scan_part(line, std::to_string(fail_count) + " fail");
    if (!total_files.has_value() || completed < *total_files) {
        append_scan_part(line, scan_display_name(file_name));
        append_scan_part(line, "χ² " + fixed(reduced_chi_square, 2));
    }
    return line;
}

std::string scan_summary(int total_files, int ok_count, int fail_count, double chi2_min,
                         double chi2_max, double elapsed_seconds, int measured_completed) {
    std::string line;
    append_scan_part(line, "scan");
    append_scan_part(line, std::to_string(total_files) + " files");
    append_scan_part(line, std::to_string(ok_count) + " converged");
    append_scan_part(line, std::to_string(fail_count) + " failed");
    // A non-finite bound means the scan's committed rows produced no χ² at all: the group
    // renders NOTHING rather than a number no fit produced — the same blank rule format_change
    // follows. (the caller's fold now spans the resume rows too, so a resumed scan
    // reaches this blank only when nothing anywhere recorded one.)
    if (std::isfinite(chi2_min) && std::isfinite(chi2_max)) {
        append_scan_part(line, "χ² " + fixed(chi2_min, 2) + "-" + fixed(chi2_max, 2));
    }
    // The duration is the ONE quantity history cannot supply, so it is rendered on its own
    // basis or not at all: nothing fitted this call means no duration to report (a completed
    // scan re-run as a no-op would otherwise print `0s` as the scan's time), and a partial
    // resume says which run the number describes.
    if (measured_completed > 0) {
        append_scan_part(line,
                         scan_elapsed_suffix(scan_duration(elapsed_seconds), measured_completed,
                                             ok_count + fail_count));
    }
    line += "\n";
    return line;
}

std::string iteration_line(const IterationRecord& record, double previous_reduced_chi2) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << std::setw(7) << record.iteration << fixed(record.elapsed_ms / 1000.0, 2, 11)
        << fixed(record.rwp, 4, 10) << fixed(record.reduced_chi_square, 4, 12) << "   "
        << format_change(record.reduced_chi_square, previous_reduced_chi2);
    return out.str();
}

// File-internal: its binding left the surface; stream_header renders the starting row
// through it.
static std::string pre_fit_line(const IterationRecord& pre_fit) {
    // The starting row (iteration 0): iter (7) and time (11) columns blank, only Rwp (10) and
    // reduced χ² (12); no change column (there is no previous basis). Aligned to iteration_line's
    // widths so the pre-fit row and the iteration rows share one column grid.
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << std::string(18, ' ') << fixed(pre_fit.rwp, 4, 10) << fixed(pre_fit.reduced_chi_square, 4, 12);
    return out.str();
}

std::string stream_header(const FitPreamble& preamble, const std::string& project_name) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    if (preamble.joint) {
        std::string banks;
        for (std::size_t index = 0; index < preamble.banks.size(); ++index) {
            banks += (index == 0 ? "" : ", ") + preamble.banks[index];
        }
        out << "edi fit: joint project " << project_name << ", " << preamble.banks.size()
            << (preamble.banks.size() == 1 ? " bank (" : " banks (") << banks << "), ";
    } else {
        out << "edi fit: project " << project_name << ", ";
    }
    // BOTH counts, as the contract names them: reduced chi-square is normalised by the FITTED
    // count, so showing only the loaded one invites a wrong recomputation.
    out << preamble.n_points_fitted << " pts fitted / " << preamble.n_points_loaded << " loaded, "
        << preamble.n_free << " free\n";
    // The iteration-table header, then the pre-fit starting row — so the first iteration's
    // improvement over the initial model is visible (edi used to print a header then nothing for ~30
    // s).
    out << kIterHeader << '\n';
    out << pre_fit_line(preamble.pre_fit) << '\n';
    return out.str();
}

std::string summary_line(const FitResultBase& outcome) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << "  done · " << (outcome.converged ? "converged" : "not converged") << " · "
        << outcome.iterations << " iters · reduced χ² "
        << fixed(outcome.reduced_chi_square, 4) << " · Rwp " << fixed(outcome.rwp, 4)
        << " · " << fixed(outcome.elapsed_ms / 1000.0, 1) << " s\n";
    return out.str();
}

std::string parameter_table(const FitResultBase& outcome) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    // Per-bank metrics exist for a joint refinement only — the engine reports no per-bank block for
    // a single-bank fit, so there is nothing truthful to print there.
    if (!outcome.banks.empty()) {
        out << "\n  per-bank Rwp:";
        for (const BankMetric& bank : outcome.banks) {
            out << "   " << bank.name << ' ' << fixed(bank.rwp, 4);
        }
        out << '\n';
    }
    out << "\n  refined parameters (" << outcome.values.size() << " free):\n  ";
    append_padded(out, "parameter", kLabelWidth);
    out << std::setw(13) << "start" << std::setw(13) << "value" << std::setw(10) << "s.u."
        << "   change\n";
    // std::map iterates sorted by identity path, which is the stable display order.
    for (const auto& [path, value] : outcome.values) {
        const auto start_it = outcome.start.find(path);
        const double start = start_it == outcome.start.end() ? value : start_it->second;
        const auto esd_it = outcome.uncertainty.find(path);
        out << "  ";
        append_padded(out, path, kLabelWidth);
        out << fixed(start, 5, 13) << fixed(value, 5, 13)
            << fixed(esd_it == outcome.uncertainty.end() ? 0.0 : esd_it->second, 5, 10) << "   "
            << format_change(value, start) << '\n';
    }
    return out.str();
}

std::string progress_report(const IterationRecord& record) {
    // The machine streamed record is crysta's artifact — rendered by the shared engine emitter, not
    // by edi presentation — so `edi fit --report machine --stream` and `crysta fit --stream` emit
    // one implementation. `iter`/`rwp`/`reduced_chi_square` are contract; `elapsed_ms` is informational.
    return crysta::format_fit_report(crysta::make_progress_report(to_engine(record)),
                                     crysta::VerbosityEnum::Compact);
}

}  // namespace edi
