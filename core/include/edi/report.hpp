// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "edi/model.hpp"

// Edi's fit reporting — the product half of the shared output contract.
//
// Two channels with deliberately different stability guarantees:
//
//   * MACHINE — the verification channel. Not implemented here: it is
//     `crysta::format_fit_report`, called through machine_report() below. edi does not re-implement
//     the record and does not re-emit crysta's bytes verbatim either; it fills a crysta::FitReport
//     from its own FitResultBase, which is what lets it omit an engine-only row it has no capability
//     for (see machine_report) and append `x-edi.*` keys it owns (none today).
//
//   * HUMAN — the user channel, owned by edi outright and free to evolve. It lives HERE, in the
//     product core rather than in a CLI or an example, so every edi surface (the `python -m edi`
//     entry point, notebooks, and later the desktop/WASM front ends) renders one implementation.
//
// Both RETURN strings and print nothing: the core stays silent by policy, and `import edi` +
// `project.fit()` must emit nothing at all unless the caller asks. Choosing a stream is the
// surface's job.
//
// This header is engine-free like the rest of edi's public surface (ADR-0003): the crysta contact
// lives in report.cpp, so edi's API shape does not track crysta's.

namespace edi {

// How much to report. ONE enum for both channels, so a surface offers a single `--verbosity`
// selector that means the same thing whichever `--report` channel is chosen.
enum class VerbosityEnum : std::uint8_t {
    OFF,      // nothing at all (an empty string)
    COMPACT,  // the summary
    FULL      // + per-bank R-factors, every iteration, every refined parameter
};

// The machine record for this outcome, rendered by the ENGINE's emitter (one implementation, shared
// with `crysta fit`).
//
// `project` supplies the bank names and joint/single mode. Two deliberate differences from crysta's
// own record, both required by the contract rather than incidental:
//   * `cutoff_policy` is OMITTED — edi exposes no cutoff-policy control, and a surface that cannot
//     vary a field must not emit a constant for it. It appears as a plain added line when diffing
//     against crysta, which is the honest representation of a capability edi does not have.
//   * parameters are keyed by crysta ENGINE label (FitResultBase::engine_values), not by edi identity
//     path. The record is crysta's artifact and must use crysta's identity on every surface, or the
//     two sides' per-parameter lines could never be compared. edi's paths are the human view's key.
std::string machine_report(const Project& project, const FitResultBase& outcome,
                           VerbosityEnum verbosity);


// The minimal machine FAILURE record: `schema`, `record=error`, `status=error`, and nothing else.
//
// No numeric rows, ever — after a failure there is no trustworthy iteration count, metric or
// parameter, and a placeholder would be worse than an omission. A parser gets a well-formed record
// saying the run produced no fit; the human explanation belongs on stderr beside the non-zero exit.
//
// A surface emits this once it has REACHED the point of attempting a fit (loading, model build, or
// the refinement itself failing). An argument or usage error is not a run and produces no record.
std::string error_report(VerbosityEnum verbosity);

// The percent-change rule, exposed so it can be exercised on CONSTRUCTED values rather than only
// through whatever a live fit happens to produce.
//
// It is a presentation CONTRACT, not an implementation detail, and every clause is load-bearing:
//   * the denominator is |previous| — the pre-fit START value, never the refined one;
//   * `previous == 0` yields BLANK: a percentage of zero is undefined, not infinite;
//   * a non-finite `current` or `previous` yields BLANK;
//   * a move smaller than 0.05 % yields BLANK, so an unmoved parameter shows nothing rather than
//     noise — 1.00049 against 1.0 is blank, 1.00051 is rendered;
//   * the arrow follows the SIGN of the change, not its magnitude.
std::string format_change(double current, double previous);

// One per-iteration progress line, for a surface that subscribes to fit()'s `on_iteration`.
// Rendered here so the streaming view and the `full` table share this module's formatting rules.
std::string iteration_line(const IterationRecord& record, double previous_reduced_chi2);

// Streaming seams. The live human table (`python -m edi fit`, default) and the post-hoc the
// retired post-hoc report shared ONE implementation with them, so a streamed table and an
// after-the-fact one are byte-identical by construction.
//
// `stream_header` — the `edi fit: …` header line, the iteration-table header, AND the pre-fit
// starting row (iteration 0: the initial model's Rwp/reduced-χ², with iter/time/change blank). It is
// rendered from a `FitPreamble` because a live surface has only the pre-fit facts before iteration 1;
// `project_name` labels the
// header (typically the directory name).
std::string stream_header(const FitPreamble& preamble, const std::string& project_name);


// The summary line: `  done · <converged> · <n> iters · reduced χ² … · Rwp … · <t> s`.
std::string summary_line(const FitResultBase& outcome);

// The blocks that follow the summary at `full` verbosity: the per-bank Rwp line (joint only) and the
// `parameter · start · value · s.u. · change` table keyed by edi identity path. Always renders the
// block; the SURFACE decides whether to print it (only at full), so this is a pure renderer.
std::string parameter_table(const FitResultBase& outcome);

// The scan progress line, in the house `·` style — one line per completed scan file, rendered
// here so every surface (CLI, notebooks, later front ends) shows one implementation and only
// chooses the emission mode (in place on a TTY, one line per file otherwise):
//
//   [███░░░░░░░░░░░] · 38/213 · 18% · elapsed 2m41s · eta 12m05s · 35 ok · 3 fail · cosio_213K · χ² 4.81
//
// Every clause is load-bearing:
//   * `total_files` comes from the scan preamble — with it unknown (nullopt) the line degrades
//     to a bare completed count with NO bar, NO percentage and NO eta, rather than guessing
//    ; a number no fit produced never appears.
//   * `elapsed_seconds` is the CALLER's injected-clock reading, never a wall-clock read here —
//     the renderer computes nothing time-like on its own.
//   * `measured_completed` is how many of those `completed` files `elapsed_seconds` ACTUALLY
//     COVERS: equal to `completed` on a fresh scan, and only the files fitted THIS CALL on a
//     resumed one (review-1 F2 — a committed results.csv row records iterations, never
//     duration, so history contributes no time). It is the ETA's denominator and the sole
//     reason the two can never disagree: the parameter is required, so a caller must state the
//     time basis it is handing over rather than letting `completed` stand in for it. With
//     `measured_completed <= 0` nothing this call timed, so NO eta appears at all.
//   * the ETA is mean(elapsed over measured) × remaining, labelled `eta` because it is an
//     estimate, never presented as a measurement; it disappears at completion.
//   * when the two bases differ (a resumed scan) the elapsed group NAMES its own — `elapsed
//     5m12s this run` — because an unqualified duration beside whole-scan counts reads as the
//     scan's, which is a number no run produced. A fresh scan renders exactly as before.
//   * `ok/fail` stay on the line so a scan with failures never reports unqualified success
//     (gate 6); the current file is shown by its stem, as the owner's request spells it.
//   * at 100% the line freezes to bar/count/percent/elapsed/ok/fail — no eta, no current file.
std::string scan_progress_line(int completed, std::optional<int> total_files,
                               double elapsed_seconds, int measured_completed, int ok_count,
                               int fail_count, const std::string& file_name,
                               double reduced_chi_square);

// The scan summary, after the frozen progress line:
//
//   scan · 213 files · 210 converged · 3 failed · χ² 3.91-8.44 · 14m52s
//
// The summary COUNTS failures and never lists them — a 324-file scan printed 99 names; the
// per-file outcome is in analysis/results.csv. Every population quantity — the counts and the χ²
// range — is the caller's fold over ONE set: the scan's committed rows, this call's and any
// resumed call's alike.
//
// `elapsed_seconds` is the same injected-clock reading the progress line used, and
// `measured_completed` again says how many completions it covers. Two consequences, both about
// never showing a duration no run produced: with `measured_completed <= 0` (a completed scan
// re-run as a no-op) the duration group renders NOTHING, the same blank rule the χ² group
// follows; and when it is below the scan's completed total the group names its basis
// (`5m12s this run`). A fresh scan renders exactly as before.
std::string scan_summary(int total_files, int ok_count, int fail_count, double chi2_min,
                         double chi2_max, double elapsed_seconds, int measured_completed);

// The machine streamed progress record for ONE iteration (`record=progress`), rendered by crysta's
// shared emitter (make_progress_report + format_fit_report) — edi's `--report machine --stream`
// surface writes one per accepted step, before the terminal record. Contract, not edi presentation.
std::string progress_report(const IterationRecord& record);

// The machine calc record, rendered by crysta's shared
// emitter (make_calc_report + format_fit_report) — one implementation with `crysta <dir> calc`,
// which is what makes the two records byte-comparable rather than convergently formatted.
// `n_points` and `checksum` describe the series the calculate() run left in the model
// (`data.intensity_calc`, summed in experiment order); `elapsed_ms` is informational, never
// compared. Identical at compact and full: a forward calculation has no iterations or parameters.
std::string calc_report(std::size_t n_points, double checksum, double elapsed_ms,
                        VerbosityEnum verbosity);

}  // namespace edi
