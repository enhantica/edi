// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

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
    /// The contents left out, each by its key (ReportContentsItem::key), with everything under it.
    std::vector<std::string> hidden;
    std::optional<double> correlation_level;  ///< absent: the five most correlated parameters
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

/// One entry of the report's contents: every section, analysis category, structure, experiment and their categories,
/// whether or not it is included, in the report's order.
struct ReportContentsItem {
    std::string key;  ///< "analysis", "analysis/fit_result", "structures/<id>", "experiments/<id>/peak", ...
    std::string title;
    int depth = 0;  ///< 0 a section, 1 an analysis category, a structure or an experiment, 2 their categories
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

struct ReportStructure {
    std::string id;
    std::vector<ReportCategory> categories;
};

struct ReportExperiment {
    std::string id;
    std::vector<ReportCategory> categories;
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
};

/// The report of `project` as `options` ask: the only function that reads a project (ADR-0035 §2).
ReportModel build_report(const Project& project, const ReportOptions& options);

/// The model as JSON (ADR-0035 §1): every field, doubles in their shortest round-trip form, a non-finite one as null.
/// The text has no literal <, > or &, so it can sit inside an HTML <script> element.
std::string report_to_json(const ReportModel& model);
/// A model from its JSON; throws std::invalid_argument for malformed JSON, a missing field or another schema version.
ReportModel report_from_json(const std::string& json);

}  // namespace edi
