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

/// The report's sections, in the order they appear (ADR-0035 §3).
enum class ReportSection : std::uint8_t { Summary, Analysis, Parameters, Correlations, Evolution, Structures, Experiments };

/// Every section, in order.
const std::vector<ReportSection>& report_sections();
/// "summary", "analysis", "parameters", "correlations", "evolution", "structures" or "experiments".
const char* report_section_name(ReportSection section);
std::optional<ReportSection> report_section_from_name(std::string_view name);

/// What a report holds; the Report page's Contents and Charts groups.
struct ReportOptions {
    std::vector<ReportSection> sections = report_sections();  ///< included; the order is always report_sections()
    bool free_parameters_only = false;                         ///< the Parameters section: free ones, or all
    std::optional<double> correlation_level;                   ///< absent: the five most correlated parameters
    std::vector<std::string> experiments;                      ///< the experiments drawn; empty: all
    bool d_spacing = false;                                    ///< charts on d instead of 2θ or TOF
    bool residual = true;                                      ///< the residual pane
    bool bragg_ticks = true;                                   ///< the Bragg tick rows
    std::string generated;                                     ///< the report's time; empty: now, in UTC
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

/// One parameter of the Parameters section.
struct ReportParameter {
    std::string name;   ///< the unique name, e.g. "cosio.cell.length_a"
    std::string label;  ///< the display name, e.g. "a"
    std::string units;
    ReportValue value;
    std::optional<double> start;  ///< the value before the last fit, when recorded
    bool free = false;
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
    std::vector<ReportRow> space_group;
    std::vector<ReportRow> cell;
    ReportTable atom_sites;
    ReportTable aniso;  ///< empty when no site is anisotropic
};

struct ReportExperiment {
    std::string id;
    std::vector<ReportRow> type;
    std::vector<ReportRow> instrument;
    std::vector<ReportRow> peak;
    ReportTable background;
    ReportTable excluded_regions;
    ReportTable linked_structures;
};

/// A project's report (ADR-0035).
struct ReportModel {
    int schema_version = kReportSchemaVersion;
    std::string generated;
    std::vector<ReportSection> sections;
    // Project summary
    std::string name, title, authors, description;
    std::vector<std::string> structure_ids, experiment_ids;
    // Analysis
    std::vector<ReportRow> software;
    std::string fitting_mode;
    bool fitted = false;
    std::vector<ReportRow> fit_result;
    std::vector<ReportParameter> parameters;
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
