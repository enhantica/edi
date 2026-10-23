// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "edi/presentation.hpp"
#include "edi/structure_scene.hpp"

// The report model (edi ADR-0036): one versioned description of a project's report, free of Qt and HTML. Only
// build_report reads a project; the HTML writer, the Report page and the Python display read the model or its JSON.

namespace edi {

class Project;

/// The schema version every model carries; a reader refuses another.
inline constexpr int kReportSchemaVersion = 1;

/// The report's sections, in the order they appear (ADR-0036 §3; the owner's Contents tree, 2026-10-13).
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
    ColourScheme colour_scheme = kDefaultColourScheme;  ///< the experiments' and structures' colours
    /// The HTML writer's choice, not the model's: whether a saved file carries the chart libraries.
    bool embed_libraries = false;
};

/// One run's choices over a project's report settings (the CLI's flags, Python's keywords, the app's): an absent one
/// keeps the stored setting, a given one replaces it for the run. Nothing is written to the project. The colour scheme
/// and the correlations' experiment are the surface's choices, not project settings: the app gives its Preferences'
/// scheme and the experiment the Analysis page shows.
struct ReportOverrides {
    std::optional<bool> html_offline;
    std::optional<double> correlation_threshold;
    std::optional<std::string> x_axis;  ///< "native" or "d_spacing"
    std::optional<std::vector<std::string>> excluded;
    std::optional<std::string> colour_scheme;  ///< a token of colour_scheme_from_name; absent, the default scheme
    /// In a fit of several experiments, the name of the one whose parameters the correlation chart shows; absent, the
    /// first.
    std::optional<std::string> correlation_experiment;
};

/// The options a report of `project` is made with (ADR-0036 §7): its report settings (`reports/report.edi`) and the
/// correlation threshold and x axis (`analysis/analysis.edi`), each replaced by a given override, and the given colour
/// scheme and correlations' experiment. With no `excluded` the data are left out; with no threshold the correlations
/// follow diffraction-lib's automatic rule; with no x axis the charts are on their own. Throws std::invalid_argument
/// for an unknown scheme or experiment name.
ReportOptions effective_report_options(const Project& project, const ReportOverrides& overrides = {});

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

/// A parameter of the project as the report's list holds it: its unique name, its label, its value and s.u. as stored
/// (a non-finite or absent s.u. is null), its text in the project's s.u. rule, its units, the value its last fit
/// started from, and whether it is free.
struct ReportParameter {
    std::string unique_name;
    std::string label;
    double value = 0.0;
    std::optional<double> su;
    std::string text;
    std::string units;
    std::optional<double> start;
    bool free = false;
};

/// One parameter's evolution over a scan (evolution_series): its points, each with the value's text in the project's
/// s.u. rule, as the Evolution tab draws them.
struct ReportEvolutionPoint {
    double x = 0.0;
    double y = 0.0;
    double su = 0.0;
    std::string text;
};
struct ReportEvolution {
    std::string name;     ///< the parameter's unique name, or its results column
    std::string x_title;  ///< the first extract rule's column heading, or "file index"
    std::vector<ReportEvolutionPoint> points;
    std::string units;  ///< the parameter's units as the report writes them; empty without
};

/// The viewport a report's structure drawing is prepared for (ADR-0036 §1), in logical pixels, with room at the sides
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
    // For a renderer's buttons, as the Structure page has them: the views along a, b and c (view_along), and the atom
    // labels the view shows when they are asked for (present_structure's, with labels on).
    std::vector<SceneView> along;
    std::vector<SceneLabel> labels;
};

/// An experiment's pattern chart (ADR-0021): present_pattern's output over the full range with no decimation and a
/// linear y scale, and the core's hover text of each Bragg tick.
struct ReportPattern {
    PatternPresentation presentation;
    /// Per series, per point: hover_text for a Bragg tick series, empty for every other series.
    std::vector<std::vector<std::string>> hover;
    /// The chart's title: the experiment's reliability text (reliability_text); empty with no fit.
    std::string title;
    /// Whether the chart opens with its legend box; by default it does not, its y titles naming the series in their
    /// colours.
    bool legend = false;
};

/// A single crystal's chart (edi ADR-0049), as the app draws it: per reflection its Miller indices, its measured F²
/// and s.u., and its calculated F², which is empty before a calculation; F²meas against F²calc with the y = x line.
struct ReportSingleCrystal {
    std::vector<int> h, k, l;
    std::vector<double> meas, su, calc;
    /// The experiment's reliability text (reliability_text); empty with no fit.
    std::string title;
};

struct ReportExperiment {
    std::string id;
    std::vector<ReportCategory> categories;
    /// A powder experiment's chart; empty for a single crystal, whose chart is `single_crystal`.
    ReportPattern pattern;
    std::optional<ReportSingleCrystal> single_crystal;
};

/// A project's report (ADR-0036).
struct ReportModel {
    int schema_version = kReportSchemaVersion;
    std::string generated;
    std::vector<ReportSection> sections;
    std::vector<ReportContentsItem> contents;
    // Project summary
    std::string name, title, authors, description;
    std::vector<std::string> structure_ids, experiment_ids;
    // Analysis: software, minimizer, fitting mode and fit result (the JSON's `analysis_categories`); the correlation
    // chart and, for a scan, the parameters' evolution.
    std::vector<ReportCategory> analysis;
    std::vector<ReportParameter> parameters;
    bool fitted = false;
    std::optional<ReportCorrelations> correlations;
    std::optional<std::vector<ReportEvolution>> evolution;
    // Structures and experiments
    std::vector<ReportStructure> structures;
    std::vector<ReportExperiment> experiments;
    // The core's style tables, which the charts' and scenes' style keys name (I5).
    std::vector<SeriesStyle> pattern_styles;
    std::vector<SceneStyle> structure_styles;
};

/// The reliability of the experiment at `experiment` in the project's last fit, as every pattern plot shows it:
/// "Rwp 16.35 % · χ² 75.62", the weighted-profile R factor in per cent and the reduced χ², both with two decimals,
/// as the fit results show them. A joint fit gives each bank its own Rwp. Empty when the project holds no fit.
/// A single crystal's fit is over F²: "R(F²) 5.12 % · wR(F²) 4.25 % · χ² 9.78".
std::string reliability_text(const Project& project, std::size_t experiment);

/// The report of `project` as `options` ask: the only function that reads a project (ADR-0036 §2).
ReportModel build_report(const Project& project, const ReportOptions& options);

/// The model as JSON (ADR-0036 §1): every field, doubles in their shortest round-trip form, a non-finite one as null.
/// The text has no literal <, > or &, so it can sit inside an HTML <script> element.
std::string report_to_json(const ReportModel& model);
/// A model from its JSON; throws std::invalid_argument for malformed JSON, a missing field or another schema version.
ReportModel report_from_json(const std::string& json);

}  // namespace edi
