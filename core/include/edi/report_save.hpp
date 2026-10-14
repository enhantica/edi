// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <string>
#include <vector>

#include "edi/report_html.hpp"
#include "edi/report_model.hpp"

// Save report for the command line and Python (edi ADR-0036 §7): the report's formats written into the project's
// `reports/` folder with their `_report_file` rows, and the state of each report saved so far. The app writes its
// own, the PDF included.

namespace edi {

class Project;

/// What a save wrote: the files' paths, and whether a ticked PDF was left to the app (its file and row as they were).
struct ReportSaveResult {
    std::vector<std::string> written;
    bool pdf_left = false;
};

/// Each ticked format but the PDF (the app's) written into `<project.path>/reports/` as `<short name>.html`, then its
/// row (the name's row replaced), then `reports/report.edi` alone. A file is written beside its old one and renamed
/// over it, so a failed write leaves the old file; the project's rows change only when `reports/report.edi` is
/// written. `overrides` replace the stored options for this run and are not saved; `libraries` are the vendored ones,
/// used when the HTML embeds them. Throws std::invalid_argument for a project with no folder and std::runtime_error
/// when a file cannot be written.
ReportSaveResult save_report(Project& project, const ReportOverrides& overrides, const ReportLibraries& libraries);

/// The options a saved report's row records its digest with and is judged by (ADR-0036 §7): `options` with the default
/// colour scheme and the first experiment's correlations. A report is then out of date only when the project changed,
/// whatever scheme or experiment the surface that saved it chose.
ReportOptions report_file_options(ReportOptions options);

/// Whether `options` choose another colour scheme or correlations' experiment than report_file_options.
bool chooses_presentation(const ReportOptions& options);

/// One saved report's state: "current", "out of date" (its digest differs from the digest of the report the project
/// makes now with its own settings, in report_file_options) or "missing" (its file is not in `reports/`).
struct ReportFileState {
    std::string name;
    std::string format;
    std::string state;
};

/// Every `_report_file` row's state, in the rows' order. `libraries` as for save_report.
std::vector<ReportFileState> report_file_states(const Project& project, const ReportLibraries& libraries);

/// The time `stamp` (the project's STAR form, `13 Oct 2026 23:56:16`, UTC) as ISO 8601 UTC; `stamp` when it is not
/// one.
std::string iso_utc_from_star(const std::string& stamp);

}  // namespace edi
