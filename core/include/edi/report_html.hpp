// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <array>
#include <cstdint>
#include <filesystem>
#include <optional>
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

/// One part of a report, as a notebook's display shows it (edi ADR-0079).
enum class ReportViewKind : std::uint8_t {
    Pattern,       ///< an experiment's chart
    Structure,     ///< a structure's view
    FitResults,    ///< the Analysis section's fit result
    Correlations,  ///< the correlation chart
    Evolution,     ///< a scan's evolution charts
    Parameters,    ///< the parameter list, as `parameters` selects
    Relations,     ///< the aliases and constraints
};

/// Which parameters a parameter view lists.
enum class ReportParameterSet : std::uint8_t { Free, Fittable, All };

struct ReportView {
    ReportViewKind kind = ReportViewKind::Pattern;
    std::size_t index = 0;               ///< the experiment's or the structure's index in the model
    std::optional<double> x_min, x_max;  ///< a powder pattern's x range; absent, its own
    ReportParameterSet parameters = ReportParameterSet::Free;
};

/// One part of the report as a whole HTML document: the same style, model JSON and report.js as `report_html`, with
/// only that part in its body and no page round it. Throws std::invalid_argument for an index outside the model or a
/// range whose end is not above its start, and std::invalid_argument as `report_html` does for the libraries.
std::string report_view_html(const ReportModel& model, const ReportView& view, const ReportLibraries& libraries = {});

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
/// and the static text the PDF lays out, as its figures are drawn from the model. Empty for "cif", whose report is not
/// made from the model: its digest is of the CIF text itself.
std::string report_digest(ReportModel model, std::string_view format, const ReportLibraries& libraries = {});

}  // namespace edi
