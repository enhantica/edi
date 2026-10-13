// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "edi/presentation.hpp"
#include "edi/structure_scene.hpp"

// The report model (edi ADR-0035): one versioned description of a project's report, free of Qt and HTML. Only
// build_report reads a project; the HTML writer, the Report page and the Python display read the model or its JSON.

namespace edi {

class Project;

/// The schema version every model carries; a reader refuses another.
inline constexpr int kReportSchemaVersion = 1;

/// The report's sections, in the order they appear (ADR-0035 §3; the owner's Contents tree, 2026-10-13).
enum class ReportSection : std::uint8_t { Summary, Analysis, Structures, Experiments, Correlations, Evolution };

/// Every section, in order.
const std::vector<ReportSection>& report_sections();
/// "summary", "analysis", "structures", "experiments", "correlations" or "evolution".
const char* report_section_name(ReportSection section);
std::optional<ReportSection> report_section_from_name(std::string_view name);

/// What a report holds. The app takes the correlation level and the x axis from the Analysis page; the CLI and Python
/// take them as options.
struct ReportOptions {
    /// The optional groups left out, by key: "charts", "correlations", "reflections", "data", "evolution". The data
    /// are left out unless asked for, as they are usually long (the owner, 2026-10-13); an empty list includes all.
    std::vector<std::string> hidden{"data"};
    std::optional<double> correlation_level;  ///< absent: the five most correlated parameters
    /// In a fit of several experiments, the one whose parameters the correlation chart shows, as the Correlations tab
    /// shows the experiment it is on: the app's shown experiment, else the first.
    std::size_t correlation_experiment = 0;
    bool d_spacing = false;                   ///< charts on d instead of 2θ or TOF
    bool residual = true;                     ///< the residual pane
    bool bragg_ticks = true;                  ///< the Bragg tick rows
    std::string generated;                    ///< the report's time; empty: now, in UTC
};

/// A number as the report shows it: its value, its s.u. when it has one, and its text (the project's s.u. rule).
struct ReportValue {
    double value = 0.0;
    std::optional<double> su;
    std::string text;
};

/// A labelled value, e.g. a cell length or a fit-result row.
struct ReportRow {
    std::string label;
    std::string text;
    std::string units;
};

/// A table of texts.
struct ReportTable {
    std::vector<std::string> columns;
    std::vector<std::vector<std::string>> rows;
};

/// One subsection of the report: an analysis category, or a structure's or an experiment's `.edi` category as its
/// page shows it (the reference report's subsections): its labelled values, then its table.
struct ReportCategory {
    std::string id;     ///< e.g. "software", "cell", "atom_site", "peak"
    std::string title;  ///< e.g. "Software", "Cell", "Atom sites", "Peak profile"
    std::vector<ReportRow> rows;
    ReportTable table;
};

/// One of the report's optional groups (the owner, 2026-10-13): the charts, the correlations, the reflections, the
/// data and, for a scan, the evolution; whether the report includes it. Everything else is always included.
struct ReportContentsItem {
    std::string key;  ///< "charts", "correlations", "reflections", "data" or "evolution"
    std::string title;
    bool included = true;
};

/// The correlation chart: the shown parameters and the lower triangle of their matrix, row by row (NaN above the
/// diagonal and on it), as the Correlations tab shows them.
struct ReportCorrelations {
    std::vector<std::string> labels;
    std::vector<double> values;
    double level = 0.0;     ///< the smallest strongest-correlation a shown parameter has
    int available = 0;      ///< the parameters the fit correlated
    std::string empty_text; ///< why nothing is shown; empty when the matrix is
};

/// The viewport a report's structure drawing is prepared for (ADR-0035 §1), in logical pixels, with room at the sides
/// for the element legend.
inline constexpr Viewport kReportViewport{800.0, 600.0, 0.0, 120.0};

struct ReportStructure {
    std::string id;
    std::vector<ReportCategory> categories;
    // The structure view (ADR-0022): present_structure's scene with the default options, its default_view, and
    // scene_drawing for kReportViewport. A renderer with another viewport runs scene_drawing on `scene` again.
    StructureScene scene;
    SceneView view;
    SceneDrawing drawing;
};

/// An experiment's pattern chart (ADR-0021): present_pattern's output over the full range with no decimation and a
/// linear y scale, and the core's hover text of each Bragg tick.
struct ReportPattern {
    PatternPresentation presentation;
    /// Per series, per point: hover_text for a Bragg tick series, empty for every other series.
    std::vector<std::vector<std::string>> hover;
};

struct ReportExperiment {
    std::string id;
    std::vector<ReportCategory> categories;
    ReportPattern pattern;
};

/// A project's report (ADR-0035).
struct ReportModel {
    int schema_version = kReportSchemaVersion;
    std::string generated;
    std::vector<ReportSection> sections;
    std::vector<ReportContentsItem> contents;
    // Project summary
    std::string name, title, authors, description;
    std::vector<std::string> structure_ids, experiment_ids;
    // Analysis: software, minimizer, fitting mode and fit result
    std::vector<ReportCategory> analysis;
    bool fitted = false;
    std::optional<ReportCorrelations> correlations;
    // Structures and experiments
    std::vector<ReportStructure> structures;
    std::vector<ReportExperiment> experiments;
    // The core's style tables, which the charts' and scenes' style keys name (I5).
    std::vector<SeriesStyle> pattern_styles;
    std::vector<SceneStyle> structure_styles;
};

/// The report of `project` as `options` ask: the only function that reads a project (ADR-0035 §2).
ReportModel build_report(const Project& project, const ReportOptions& options);

/// The model as JSON (ADR-0035 §1): every field, doubles in their shortest round-trip form, a non-finite one as null.
/// The text has no literal <, > or &, so it can sit inside an HTML <script> element.
std::string report_to_json(const ReportModel& model);
/// A model from its JSON; throws std::invalid_argument for malformed JSON, a missing field or another schema version.
ReportModel report_from_json(const std::string& json);

}  // namespace edi
