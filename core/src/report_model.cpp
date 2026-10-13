// SPDX-License-Identifier: BSD-3-Clause
#include "edi/report_model.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <ctime>
#include <limits>
#include <map>
#include <memory>
#include <stdexcept>

#include "edi/categories.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
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

// A parameter's number: with its s.u. in the project's spelling when it is free and has one, else as it is.
ReportValue value_of(const Parameter& parameter, const std::string& rule) {
    ReportValue out;
    out.value = parameter.value.get();
    const std::optional<double>& su = parameter.uncertainty.get();
    if (parameter.free.get() && su.has_value() && std::isfinite(*su) && *su != 0.0 && std::isfinite(out.value)) {
        out.su = *su;
        out.text = value_su_text(out.value, *su, rule);
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

// The correlation chart as the Correlations tab draws it: the fit's pairs (the template file's in a scan), the
// parameters whose strongest correlation reaches the level, at most as many as asked, in the fit's order.
std::optional<ReportCorrelations> correlations_of(const Project& project, const std::optional<double>& level) {
    const bool scan = is_scan_fitting_mode(project.fitting_mode);
    const std::string& template_file = project.sequential_fit.template_file;
    std::vector<const FitParameterCorrelation*> rows;
    for (const auto& row : project.fit_result.correlations) {
        if (scan ? row->file_path.value() == template_file : row->file_path.empty()) {
            rows.push_back(row.get());
        }
    }
    if (!project.fit_result.held() && rows.empty()) {
        return std::nullopt;
    }
    ReportCorrelations out;
    std::vector<std::string> names;
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
    std::vector<double> matrix(n * n, std::numeric_limits<double>::quiet_NaN());
    for (const FitParameterCorrelation* row : rows) {
        const std::size_t i = index.at(row->parameter_unique_name_i.value());
        const std::size_t j = index.at(row->parameter_unique_name_j.value());
        const double value = correlation_value(*row);
        matrix[i * n + j] = value;
        matrix[j * n + i] = value;
    }
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

ReportModel build_report(const Project& project, const ReportOptions& options) {
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
    model.fitted = result.held();
    if (model.fitted) {
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
    model.correlations = correlations_of(project, options.correlation_level);
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
