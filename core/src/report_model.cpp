// SPDX-License-Identifier: BSD-3-Clause
#include "edi/report_model.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <ctime>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <stdexcept>

#include "edi/categories.hpp"
#include "edi/edit.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/scan.hpp"
#include "edi/su_text.hpp"
#include "edi/symmetry.hpp"
#include "edi/version.hpp"

namespace edi {

namespace {

constexpr int kDefaultCorrelatedParameters = 5;  // diffraction-lib's DEFAULT_CORRELATION_MAX_PARAMETERS

std::string shortest(double value) {
    char buffer[64];
    const auto result = std::to_chars(buffer, buffer + sizeof(buffer), value);
    return std::string(buffer, result.ptr);
}

std::string fixed(double value, int decimals) {
    char buffer[400];
    const auto result =
        std::to_chars(buffer, buffer + sizeof(buffer), value, std::chars_format::fixed, decimals);
    return std::string(buffer, result.ptr);
}

std::string utc_now() {
    const std::time_t now = std::time(nullptr);
    std::tm parts{};
#if defined(_WIN32)
    gmtime_s(&parts, &now);
#else
    gmtime_r(&now, &parts);
#endif
    char buffer[32];
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M UTC", &parts);
    return buffer;
}

// A number as the app's tables show one without an s.u. (NumberText): six significant digits without trailing
// zeros, and from a million up or below 1e-4 four in scientific notation (`2.290e7`).
std::string display_text(double value) {
    if (!std::isfinite(value)) {
        return shortest(value);
    }
    char buffer[64];
    if (value != 0.0 && (std::abs(value) >= 1e6 || std::abs(value) < 1e-4)) {
        const auto end = std::to_chars(buffer, buffer + sizeof(buffer), value, std::chars_format::scientific, 3).ptr;
        std::string text(buffer, end);
        const std::size_t e = text.find('e');
        std::string exponent = text.substr(e + 1);
        const bool negative = exponent.front() == '-';
        exponent.erase(0, exponent.find_first_not_of("+-0"));
        return text.substr(0, e + 1) + (negative ? "-" : "") + (exponent.empty() ? "0" : exponent);
    }
    const auto end = std::to_chars(buffer, buffer + sizeof(buffer), value, std::chars_format::general, 6).ptr;
    std::string text(buffer, end);
    // Just under a million rounds up to one: written whole, as the app writes it.
    return text.find('e') == std::string::npos ? text : fixed(value, 0);
}

// A parameter's number: with its s.u. in the project's spelling when it is free, or set from others (a symmetry
// tie or a constraint, whose s.u. the fit propagates), and has one. A dependent without one is written as the app's
// tables write it, never at full double precision (the owner, 2026-10-13); any other is written as it is.
ReportValue value_of(const Parameter& parameter, const std::string& rule) {
    ReportValue out;
    out.value = parameter.value.get();
    const bool dependent =
        parameter.dependence == Dependence::SymmetryTied || parameter.dependence == Dependence::Constrained;
    const std::optional<double>& su = parameter.uncertainty.get();
    if ((parameter.free.get() || dependent) && su.has_value() && std::isfinite(*su) && *su != 0.0 &&
        std::isfinite(out.value)) {
        out.su = *su;
        out.text = value_su_text(out.value, *su, rule);
    } else if (dependent) {
        out.text = display_text(out.value);
    } else {
        out.text = shortest(out.value);
    }
    return out;
}

// A parameter's short symbol, as the app's tables show it.
std::string label_of(const Parameter& parameter, const std::string& fallback) {
    const std::string symbol = parameter_symbol(parameter.spec);
    return symbol.empty() ? fallback : symbol;
}

std::string units_of(const Parameter& parameter) {
    return parameter.spec != nullptr && parameter.spec->display_units != nullptr ? parameter.spec->display_units : "";
}

void add_fields(std::vector<ReportRow>& rows, const std::vector<CategoryField>& fields, const std::string& rule) {
    for (const CategoryField& field : fields) {
        if (field.parameter == nullptr || (!field.used_by_profile && !field.parameter->free.get())) {
            continue;
        }
        rows.push_back({label_of(*field.parameter, field.name), value_of(*field.parameter, rule).text,
                        units_of(*field.parameter)});
    }
}

std::string status_word(const FitResultRecord& result) {
    if (result.exit_reason == "done") {
        return "Success";
    }
    if (result.exit_reason == "max_iter") {
        return "Max iterations";
    }
    if (result.exit_reason == "no_step") {
        return "No step";
    }
    if (result.exit_reason == "cancelled") {
        return "Stopped";
    }
    return result.success ? "Success" : "Failed";
}

std::string fitting_mode_name(const std::string& mode) {
    if (mode == "joint") {
        return "Joint: all experiments at once";
    }
    if (mode == "sequential") {
        return "Sequential: each from the previous";
    }
    if (mode == "independent") {
        return "Independent: each from the same start";
    }
    return "Single experiment";
}

// The pairs of correlation rows over their parameters, in the order the rows first name them: the names and the full
// matrix, NaN for a pair no row gives.
void matrix_of_rows(const std::vector<const FitParameterCorrelation*>& rows, std::vector<std::string>& names,
                    std::vector<double>& matrix) {
    std::map<std::string, std::size_t> index;
    for (const FitParameterCorrelation* row : rows) {
        for (const std::string* name : {&row->parameter_unique_name_i.value(), &row->parameter_unique_name_j.value()}) {
            if (!index.contains(*name)) {
                index.emplace(*name, names.size());
                names.push_back(*name);
            }
        }
    }
    const std::size_t n = names.size();
    matrix.assign(n * n, std::numeric_limits<double>::quiet_NaN());
    for (const FitParameterCorrelation* row : rows) {
        const std::size_t i = index.at(row->parameter_unique_name_i.value());
        const std::size_t j = index.at(row->parameter_unique_name_j.value());
        const double value = correlation_value(*row);
        matrix[i * n + j] = value;
        matrix[j * n + i] = value;
    }
}

// The correlation chart as the Correlations tab draws it: the fit's pairs, the parameters whose strongest correlation
// reaches the level, at most as many as asked, in the fit's order. A scan's are its template file's (`scan_file`), as
// the tab shows a dataset's: the table its fit made (edi ADR-0034), else the rows read with it, else the saved rows
// that name it. Without a fit and without pairs there is no chart.
std::optional<ReportCorrelations> correlations_of(const Project& project, const std::optional<double>& level,
                                                  const std::string* scan_file, bool fitted) {
    std::vector<std::string> names;
    std::vector<double> matrix;
    std::vector<const FitParameterCorrelation*> rows;
    const auto& results = project.fit_result.scan_results;
    const auto found = scan_file != nullptr ? results.find(*scan_file) : results.end();
    if (found != results.end() && found->second && found->second->correlations &&
        found->second->correlations->names && found->second->correlations->values) {
        // The table's pairs i < j, row by row.
        names = *found->second->correlations->names;
        const std::vector<double>& pairs = *found->second->correlations->values;
        const std::size_t n = names.size();
        matrix.assign(n * n, std::numeric_limits<double>::quiet_NaN());
        std::size_t at = 0;
        for (std::size_t i = 0; i < n; ++i) {
            for (std::size_t j = i + 1; j < n && at < pairs.size(); ++j, ++at) {
                matrix[i * n + j] = pairs[at];
                matrix[j * n + i] = pairs[at];
            }
        }
    } else {
        if (found != results.end() && found->second) {
            for (const auto& row : found->second->read_rows) {
                rows.push_back(row.get());
            }
        } else {
            for (const auto& row : project.fit_result.correlations) {
                if (scan_file != nullptr ? row->file_path.value() == *scan_file : row->file_path.empty()) {
                    rows.push_back(row.get());
                }
            }
        }
        matrix_of_rows(rows, names, matrix);
    }
    if (!fitted && names.empty()) {
        return std::nullopt;
    }
    ReportCorrelations out;
    const std::size_t n = names.size();
    out.available = static_cast<int>(n);
    if (n < 2) {
        out.empty_text = "No correlations yet";
        return out;
    }
    std::vector<double> strength(n, 0.0);
    for (std::size_t i = 0; i < n; ++i) {
        for (std::size_t j = 0; j < n; ++j) {
            if (i != j && std::isfinite(matrix[i * n + j])) {
                strength[i] = std::max(strength[i], std::abs(matrix[i * n + j]));
            }
        }
    }
    std::vector<double> ranked = strength;
    std::sort(ranked.begin(), ranked.end(), std::greater<>());
    std::size_t count = 0;
    if (level.has_value()) {
        out.level = *level;
        count = static_cast<std::size_t>(std::count_if(strength.begin(), strength.end(),
                                                        [&level](double value) { return value >= *level; }));
    } else {
        count = std::min<std::size_t>(n, kDefaultCorrelatedParameters);
        out.level = ranked[count - 1];
    }
    std::vector<std::size_t> kept;
    for (std::size_t i = 0; i < n; ++i) {
        if (strength[i] >= out.level) {
            kept.push_back(i);
        }
    }
    std::stable_sort(kept.begin(), kept.end(), [&strength](std::size_t a, std::size_t b) { return strength[a] > strength[b]; });
    kept.resize(std::min(kept.size(), count));
    std::sort(kept.begin(), kept.end());
    if (kept.size() < 2) {
        out.empty_text = "No pairs at this level";
        return out;
    }
    for (std::size_t row : kept) {
        out.labels.push_back(names[row]);
        for (std::size_t column : kept) {
            const double value = matrix[row * n + column];
            out.values.push_back(column < row && std::isfinite(value) ? value
                                                                       : std::numeric_limits<double>::quiet_NaN());
        }
    }
    return out;
}

ReportStructure structure_of(const Structure& structure, const std::string& rule) {
    ReportStructure out;
    out.id = structure.name.value();
    out.space_group.push_back({"H-M symbol", structure.space_group.name_h_m.value(), ""});
    try {
        out.space_group.push_back({"IT number", std::to_string(space_group_it_number(structure.space_group)), ""});
        out.space_group.push_back({"Crystal system", crystal_system_name(structure.space_group), ""});
    } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — an unknown setting names no number or system
    }
    const Cell& cell = structure.cell;
    const std::pair<const char*, const Parameter*> lengths[] = {
        {"a", &cell.length_a}, {"b", &cell.length_b}, {"c", &cell.length_c}};
    for (const auto& [name, parameter] : lengths) {
        out.cell.push_back({name, value_of(*parameter, rule).text, "Å"});
    }
    const std::pair<const char*, const Parameter*> angles[] = {
        {"α", &cell.angle_alpha}, {"β", &cell.angle_beta}, {"γ", &cell.angle_gamma}};
    for (const auto& [name, parameter] : angles) {
        out.cell.push_back({name, value_of(*parameter, rule).text, "°"});
    }
    std::map<std::string, int> multiplicity;
    try {
        for (const WyckoffOption& option : wyckoff_positions(structure)) {
            multiplicity.emplace(option.letter, option.multiplicity);
        }
    } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — no positions: the column stays empty
    }
    out.atom_sites.columns = {"Label", "Type", "x", "y", "z", "Wyckoff", "Mult.", "Occ.", "ADP (Å²)", "ADP type"};
    for (const auto& site : structure.atom_sites) {
        const auto found = multiplicity.find(site->wyckoff_letter.value());
        out.atom_sites.rows.push_back({site->id.value(), site->type_symbol.value(), value_of(site->fract_x, rule).text,
                                       value_of(site->fract_y, rule).text, value_of(site->fract_z, rule).text,
                                       site->wyckoff_letter.value(),
                                       found != multiplicity.end() ? std::to_string(found->second) : "",
                                       value_of(site->occupancy, rule).text, value_of(site->adp_iso, rule).text,
                                       site->adp_type.value()});
    }
    if (!structure.atom_site_aniso.empty()) {
        out.aniso.columns = {"Label", "11", "22", "33", "12", "13", "23"};
        for (const auto& row : structure.atom_site_aniso) {
            out.aniso.rows.push_back({row->id.value(), value_of(row->adp_11, rule).text, value_of(row->adp_22, rule).text,
                                      value_of(row->adp_33, rule).text, value_of(row->adp_12, rule).text,
                                      value_of(row->adp_13, rule).text, value_of(row->adp_23, rule).text});
        }
    }
    return out;
}

// The category walks take an experiment that can be edited; the builder only reads through them.
ReportExperiment experiment_of(const BraggPdExperiment& experiment, const std::string& rule) {
    auto& walked = const_cast<BraggPdExperiment&>(experiment);  // NOLINT(cppcoreguidelines-pro-type-const-cast)
    ReportExperiment out;
    out.id = experiment.name.value();
    const ExperimentType& type = experiment.experiment_type;
    out.type = {{"Sample form", token(type.effective_sample_form()), ""},
                {"Beam mode", token(experiment.effective_beam_mode()), ""},
                {"Radiation probe", token(type.effective_radiation_probe()), ""},
                {"Scattering type", token(type.effective_scattering_type()), ""},
                {"Peak profile", effective_peak_type(experiment), ""}};
    add_fields(out.instrument, instrument_category(walked).fields, rule);
    const Category peak = peak_category(walked);
    add_fields(out.peak, peak.fields, rule);
    add_fields(out.peak, peak.asymmetry, rule);
    if (experiment.background_type == "line-segment") {
        out.background.columns = {"x", "Intensity"};
        for (const auto& point : experiment.background) {
            out.background.rows.push_back({shortest(point->position.get()), value_of(point->intensity, rule).text});
        }
    } else {
        out.background.columns = {"Order", "Coefficient"};
        for (const auto& term : experiment.background_terms) {
            out.background.rows.push_back({std::to_string(term->order.get()), value_of(term->coef, rule).text});
        }
    }
    out.excluded_regions.columns = {"Start", "End"};
    for (const auto& region : experiment.excluded_regions) {
        out.excluded_regions.rows.push_back({shortest(region->first.get()), shortest(region->second.get())});
    }
    out.linked_structures.columns = {"Structure", "Scale"};
    for (const auto& link : experiment.linked_structures) {
        out.linked_structures.rows.push_back({link->structure_id.value(), value_of(link->scale, rule).text});
    }
    return out;
}

// A scan's template dataset as the app shows it once fitted (edi ADR-0035 §3): the declared template file, else the
// first file, as the app opens a scan; the template with that file's results row (its values and uncertainties over
// the template's; a parameter the results do not record keeps the template's), the file's data, its relations
// completed and its pattern calculated; and the scan's counts. Without a row for the file, the template as it is.
struct ScanTemplate {
    Project project;
    std::string file;
    std::optional<ScanResultIndex::Row> row;
    std::size_t files = 0, fitted = 0, converged = 0;
};

ScanTemplate scan_template_of(const Project& scan) {
    ScanTemplate out{scan, scan.sequential_fit.template_file, std::nullopt};
    const ScanDatasets datasets = scan_datasets(scan);
    if (out.file.empty() && !datasets.files.empty()) {
        out.file = datasets.files.front();
    }
    const std::string& file = out.file;
    const ScanPlaces places = scan_places(datasets);
    const ScanResultIndex index = index_scan_results(scan, datasets, places);
    out.files = datasets.files.size();
    if (!index.error.empty()) {
        return out;
    }
    for (const ScanResultIndex::Row& row : index.rows) {
        if (row.offset >= 0) {
            ++out.fitted;
            out.converged += row.converged ? 1 : 0;
        }
    }
    const auto place = places.find(file);
    if (place == places.end() || index.rows[place->second].offset < 0) {
        return out;
    }
    const std::vector<std::string> cells = read_scan_row(scan, index.rows[place->second].offset);
    std::map<std::string, const ScanParameterColumns*> columns;
    for (const ScanParameterColumns& parameter : index.parameters) {
        columns.emplace(parameter.name, &parameter);
    }
    std::vector<Edit::ScanValue> values;
    for (const NamedSlot& slot : named_slots(out.project)) {
        Edit::ScanValue value{slot.unique_name, slot.parameter->value.get(), slot.parameter->uncertainty.get()};
        if (const auto column = columns.find(scan_results_column(slot.unique_name)); column != columns.end()) {
            double number = 0.0, uncertainty = 0.0;
            const std::string& uncertainty_cell = cells.at(column->second->uncertainty);
            if (!parse_scan_number(cells.at(column->second->value), number) ||
                (uncertainty_cell != "nan" && !parse_scan_number(uncertainty_cell, uncertainty))) {
                throw std::invalid_argument("analysis/results.csv: the row's '" + column->second->name +
                                            "' cells are not numbers");
            }
            value.value = number;
            value.uncertainty = uncertainty;
        }
        values.push_back(std::move(value));
    }
    ExperimentBase& experiment = out.project.experiment();
    Edit::scan_view(out.project, experiment, std::move(values),
                    read_scan_dataset(datasets.directory, file, experiment.effective_beam_mode()))();
    apply_relations(out.project);
    try {
        out.project.calculate();
    } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — a refused calculation leaves the pattern not current
    }
    out.row = index.rows[place->second];
    return out;
}

}  // namespace

const std::vector<ReportSection>& report_sections() {
    static const std::vector<ReportSection> all = {ReportSection::Summary,    ReportSection::Analysis,
                                                   ReportSection::Parameters, ReportSection::Correlations,
                                                   ReportSection::Evolution,  ReportSection::Structures,
                                                   ReportSection::Experiments};
    return all;
}

const char* report_section_name(ReportSection section) {
    switch (section) {
        case ReportSection::Summary:
            return "summary";
        case ReportSection::Analysis:
            return "analysis";
        case ReportSection::Parameters:
            return "parameters";
        case ReportSection::Correlations:
            return "correlations";
        case ReportSection::Evolution:
            return "evolution";
        case ReportSection::Structures:
            return "structures";
        case ReportSection::Experiments:
            return "experiments";
    }
    return "summary";
}

std::optional<ReportSection> report_section_from_name(std::string_view name) {
    for (ReportSection section : report_sections()) {
        if (name == report_section_name(section)) {
            return section;
        }
    }
    return std::nullopt;
}

ReportModel build_report(const Project& input, const ReportOptions& options) {
    // A scan's report is its template dataset's, fitted (ADR-0035 §3); one whose datasets or results cannot be read
    // reports the template as it is.
    const bool scan_mode = is_scan_fitting_mode(input.fitting_mode);
    std::optional<ScanTemplate> scan;
    if (scan_mode) {
        try {
            scan = scan_template_of(input);
        } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — the template as it is, below
        }
    }
    const Project& project = scan ? scan->project : input;
    const std::string& rule = project.su_rule;
    ReportModel model;
    model.generated = options.generated.empty() ? utc_now() : options.generated;
    for (ReportSection section : report_sections()) {
        if (std::find(options.sections.begin(), options.sections.end(), section) != options.sections.end()) {
            model.sections.push_back(section);
        }
    }
    model.name = project.metadata.name;
    model.title = project.metadata.title;
    model.authors = project.metadata.authors;
    model.description = project.metadata.description;
    for (const auto& structure : project.structures) {
        model.structure_ids.push_back(structure->name.value());
    }
    for (const auto& experiment : project.experiments) {
        model.experiment_ids.push_back(experiment->name.value());
    }
    const FitResultRecord& result = project.fit_result;
    const std::string minimizer = result.descent.empty() ? "crysta" : "crysta (" + result.descent + ")";
    model.software = {{"Framework", "edi " + core_version(), ""}, {"Calculator", "crysta", ""}, {"Minimizer", minimizer, ""}};
    model.fitting_mode = fitting_mode_name(project.fitting_mode);
    model.fitted = scan_mode ? scan && scan->row.has_value() : result.held();
    if (scan && scan->row) {
        // The template dataset's fit, from its results row, and the scan's counts.
        const ScanResultIndex::Row& row = *scan->row;
        model.fit_result = {{"Dataset", scan->file, ""},
                            {"Overall status", row.converged ? "Success" : "Failed", ""},
                            {"Iterations", std::to_string(row.iterations), ""},
                            {"Goodness-of-fit (reduced χ²)", fixed(row.reduced_chi_square, 2), ""},
                            {"Files fitted", std::to_string(scan->fitted) + "/" + std::to_string(scan->files), ""},
                            {"Converged", std::to_string(scan->converged), ""},
                            {"Failed", std::to_string(scan->fitted - scan->converged), ""}};
    } else if (model.fitted) {
        model.fit_result = {{"Overall status", status_word(result), ""},
                            {"Fitting time", fixed(result.fitting_time, 2), "s"},
                            {"Iterations", std::to_string(result.iterations), ""},
                            {"Goodness-of-fit (reduced χ²)", fixed(result.reduced_chi_square, 2), ""},
                            {"Weighted profile R-factor (Rwp)", fixed(result.prof_wr_factor * 100.0, 2), "%"}};
        for (const auto& experiment : project.experiments) {
            if (experiment->fit_prof_wr_factor.has_value()) {
                model.fit_result.push_back(
                    {"Rwp, " + experiment->name.value(), fixed(*experiment->fit_prof_wr_factor * 100.0, 2), "%"});
            }
        }
    }
    for (const NamedParameter& named : named_parameters(project)) {
        const Parameter& parameter = *named.parameter;
        if (options.free_parameters_only && !parameter.free.get()) {
            continue;
        }
        ReportParameter row;
        row.name = named.unique_name;
        row.label = label_of(parameter, named.unique_name);
        row.units = units_of(parameter);
        row.value = value_of(parameter, rule);
        row.start = parameter.start_value.get();
        row.free = parameter.free.get();
        model.parameters.push_back(std::move(row));
    }
    model.correlations = correlations_of(project, options.correlation_level,
                                         scan ? &scan->file : scan_mode ? &project.sequential_fit.template_file : nullptr,
                                         model.fitted);
    for (const auto& structure : project.structures) {
        model.structures.push_back(structure_of(*structure, rule));
    }
    for (const auto& experiment : project.experiments) {
        const std::string& id = experiment->name.value();
        if (options.experiments.empty() ||
            std::find(options.experiments.begin(), options.experiments.end(), id) != options.experiments.end()) {
            model.experiments.push_back(experiment_of(*experiment, rule));
        }
    }
    return model;
}

}  // namespace edi
