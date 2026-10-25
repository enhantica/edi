// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <array>
#include <filesystem>
#include <string>
#include <string_view>

#include "edi/report_model.hpp"

// The HTML report (edi ADR-0036): one file written from a report model, never from a project. The text sections are
// HTML; the model's JSON sits in the file once, and report.js (embedded in the core) draws its charts and structure
// views with plotly.js and three.js, loaded from their pinned web addresses or inlined from edi's vendored copies.

namespace edi {

/// The pinned web addresses of the chart libraries, loaded when a report does not embed them.
inline constexpr const char* kReportPlotlyUrl = "https://cdn.plot.ly/plotly-cartesian-3.7.0.min.js";
inline constexpr const char* kReportThreeUrl = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.min.js";
inline constexpr const char* kReportOrbitControlsUrl =
    "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js";

/// The chart libraries' texts, for a report that embeds them. All three empty: the report loads them from the web.
struct ReportLibraries {
    std::string plotly;          ///< plotly.js's cartesian bundle
    std::string three;           ///< three.js's module build
    std::string orbit_controls;  ///< three.js's OrbitControls module
};

/// The vendored library files, relative to edi's data directory, in the order of ReportLibraries' fields.
const std::array<const char*, 3>& report_library_files();

/// The vendored libraries read from `data_dir`; throws std::runtime_error naming a file that cannot be read.
ReportLibraries read_report_libraries(const std::filesystem::path& data_dir);

/// The report as one HTML file. Throws std::invalid_argument when only some of the libraries are given.
std::string report_html(const ReportModel& model, const ReportLibraries& libraries = {});

/// The report as static HTML in the subset a rich-text layout engine reads (Qt's QTextDocument), for the PDF: the same
/// sections and tables, with attributes and a small style sheet in px at 96 to the inch, and no scripts. Each figure is
/// an image named `structure-<i>` or `pattern-<i>` (the record's index in its section), `figure_width` px wide, which
/// the reader supplies.
std::string report_static_html(const ReportModel& model, double figure_width);

/// FNV-1a 64-bit of `bytes`, as 16 lower-case hex digits (the algorithm the FNV authors publish).
std::string fnv1a64(std::string_view bytes);

/// The digest a saved report's `_report_file` row records (ADR-0036 §7): FNV-1a 64 over what the format's writer writes
/// for `model` with its time left out, so it is equal exactly when that writer would write the same now, the time
/// aside. For "html" the file's text, with `libraries` in it (all empty: loaded online); for "pdf" the model's JSON
/// and the static text the PDF lays out, as its figures are drawn from the model. Empty for a format with no writer
/// here ("cif").
std::string report_digest(ReportModel model, std::string_view format, const ReportLibraries& libraries = {});

}  // namespace edi
