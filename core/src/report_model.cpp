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
#include "edi/duration_text.hpp"
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

// A subsection of the report: a category and the title its page shows.
ReportCategory category(const std::string& id) { return {id, category_title(id), {}, {}}; }

// Where an experiment's data lie on its own axis, as a row label and units: 2θ in degrees or TOF in µs.
std::pair<std::string, std::string> axis_of(const PdDataBase& data) {
    return data.two_theta.has_value() ? std::pair<std::string, std::string>{"2θ", "°"}
                                      : std::pair<std::string, std::string>{"TOF", "µs"};
}

// A structure's categories in its page's order, filled as the page shows them; a loop without rows is left out. The
// category walk takes a structure that can be edited; the builder only reads through it.
ReportStructure structure_of(const Structure& structure, const std::string& rule) {
    auto& walked = const_cast<Structure&>(structure);  // NOLINT(cppcoreguidelines-pro-type-const-cast)
    ReportStructure out;
    out.id = structure.name.value();
    for (const Category& listed : structure_categories(walked)) {
        ReportCategory next = category(listed.id);
        if (listed.id == "space_group") {
            next.rows.push_back({"H-M symbol", structure.space_group.name_h_m.value(), ""});
            try {
                next.rows.push_back({"IT number", std::to_string(space_group_it_number(structure.space_group)), ""});
                next.rows.push_back({"Crystal system", crystal_system_name(structure.space_group), ""});
            } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — an unknown setting names no number or system
            }
        } else if (listed.id == "cell") {
            const Cell& cell = structure.cell;
            const std::pair<const char*, const Parameter*> lengths[] = {
                {"a", &cell.length_a}, {"b", &cell.length_b}, {"c", &cell.length_c}};
            for (const auto& [name, parameter] : lengths) {
                next.rows.push_back({name, value_of(*parameter, rule).text, "Å"});
            }
            const std::pair<const char*, const Parameter*> angles[] = {
                {"α", &cell.angle_alpha}, {"β", &cell.angle_beta}, {"γ", &cell.angle_gamma}};
            for (const auto& [name, parameter] : angles) {
                next.rows.push_back({name, value_of(*parameter, rule).text, "°"});
            }
        } else if (listed.id == "atom_site") {
            std::map<std::string, int> multiplicity;
            try {
                for (const WyckoffOption& option : wyckoff_positions(structure)) {
                    multiplicity.emplace(option.letter, option.multiplicity);
                }
            } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — no positions: the column stays empty
            }
            // The Wyckoff position as the International Tables write it, the multiplicity then the letter (`1a`).
            next.table.columns = {"Label", "Type", "x", "y", "z", "Wyckoff", "Occ.", "ADP (Å²)", "ADP type"};
            for (const auto& site : structure.atom_sites) {
                const std::string& letter = site->wyckoff_letter.value();
                const auto found = multiplicity.find(letter);
                next.table.rows.push_back({site->id.value(), site->type_symbol.value(), value_of(site->fract_x, rule).text,
                                           value_of(site->fract_y, rule).text, value_of(site->fract_z, rule).text,
                                           found != multiplicity.end() ? std::to_string(found->second) + letter : letter,
                                           value_of(site->occupancy, rule).text, value_of(site->adp_iso, rule).text,
                                           site->adp_type.value()});
            }
        } else if (listed.id == "atom_site_aniso") {
            next.table.columns = {"Label", "11", "22", "33", "12", "13", "23"};
            for (const auto& row : structure.atom_site_aniso) {
                next.table.rows.push_back({row->id.value(), value_of(row->adp_11, rule).text,
                                           value_of(row->adp_22, rule).text, value_of(row->adp_33, rule).text,
                                           value_of(row->adp_12, rule).text, value_of(row->adp_13, rule).text,
                                           value_of(row->adp_23, rule).text});
            }
        } else if (listed.id == "scattering_length") {
            next.table.columns = {"Type", "b (fm)"};
            for (const auto& [type, length] : structure.scattering_lengths_fm.get()) {
                next.table.rows.push_back({type, shortest(length)});
            }
        }
        if (!next.rows.empty() || !next.table.rows.empty()) {
            out.categories.push_back(std::move(next));
        }
    }
    return out;
}

// An experiment's categories in its page's order, filled as the page shows them, and its calculated reflections when
// they describe the model; a loop without rows is left out.
ReportExperiment experiment_of(const BraggPdExperiment& experiment, const std::string& rule) {
    auto& walked = const_cast<BraggPdExperiment&>(experiment);  // NOLINT(cppcoreguidelines-pro-type-const-cast)
    ReportExperiment out;
    out.id = experiment.name.value();
    for (const Category& listed : experiment_categories(walked)) {
        ReportCategory next = category(listed.id);
        if (listed.id == "experiment_type") {
            const ExperimentType& type = experiment.experiment_type;
            next.rows = {{"Sample form", token(type.effective_sample_form()), ""},
                         {"Beam mode", token(experiment.effective_beam_mode()), ""},
                         {"Radiation probe", token(type.effective_radiation_probe()), ""},
                         {"Scattering type", token(type.effective_scattering_type()), ""}};
        } else if ((listed.id == "data" || listed.id == "data_range") && experiment.data.has_value()) {
            const PdDataBase& data = *experiment.data;
            const std::vector<double>& axis = data.axis();
            const auto [name, units] = axis_of(data);
            if (listed.id == "data" && !experiment.data_file.empty()) {
                next.rows.push_back({"File", experiment.data_file, ""});
            }
            next.rows.push_back({"Points", std::to_string(axis.size()), ""});
            if (!axis.empty()) {
                const auto [low, high] = std::minmax_element(axis.begin(), axis.end());
                next.rows.push_back({name + " min", shortest(*low), units});
                next.rows.push_back({name + " max", shortest(*high), units});
                if (listed.id == "data_range" && axis.size() > 1) {
                    next.rows.push_back({name + " step", display_text(std::abs(axis[1] - axis[0])), units});
                }
            }
        } else if (listed.id == "instrument" || listed.id == "absorption") {
            add_fields(next.rows, listed.fields, rule);
        } else if (listed.id == "peak") {
            next.rows.push_back({"Type", effective_peak_type(experiment), ""});
            add_fields(next.rows, listed.fields, rule);
            add_fields(next.rows, listed.asymmetry, rule);
        } else if (listed.id == "background") {
            next.rows.push_back({"Type", experiment.background_type, ""});
            if (experiment.background_type == "line-segment") {
                next.table.columns = {"x", "Intensity"};
                for (const auto& point : experiment.background) {
                    next.table.rows.push_back({shortest(point->position.get()), value_of(point->intensity, rule).text});
                }
            } else {
                next.table.columns = {"Order", "Coefficient"};
                for (const auto& term : experiment.background_terms) {
                    next.table.rows.push_back({std::to_string(term->order.get()), value_of(term->coef, rule).text});
                }
            }
        } else if (listed.id == "linked_structure") {
            next.table.columns = {"Structure", "Scale"};
            for (const auto& link : experiment.linked_structures) {
                next.table.rows.push_back({link->structure_id.value(), value_of(link->scale, rule).text});
            }
        } else if (listed.id == "excluded_region") {
            next.table.columns = {"Start", "End"};
            for (const auto& region : experiment.excluded_regions) {
                next.table.rows.push_back({shortest(region->first.get()), shortest(region->second.get())});
            }
        } else if (listed.id == "preferred_orientation") {
            next.table.columns = {"Structure", "r", "f rand"};
            for (const auto& row : experiment.preferred_orientation) {
                next.table.rows.push_back({row->structure_id.value(), value_of(row->march_r, rule).text,
                                           value_of(row->march_random_fract, rule).text});
            }
        } else if (listed.id == "scattering_source") {
            const std::pair<const char*, const std::optional<std::string>*> sources[] = {
                {"X-ray form factor", &experiment.xray_form_factor},
                {"X-ray dispersion", &experiment.xray_dispersion},
                {"Neutron scattering length", &experiment.neutron_scattering_length}};
            for (const auto& [name, value] : sources) {
                if (value->has_value() && !value->value().empty()) {
                    next.rows.push_back({name, value->value(), ""});
                }
            }
        }
        if (!next.rows.empty() || !next.table.rows.empty()) {
            out.categories.push_back(std::move(next));
        }
    }
    // The reflections the calculation made, as the reference report lists them, six significant digits each.
    const PowderReflnDataBase& refln = experiment.refln;
    if (experiment.computed_current() && refln.size() > 0 && experiment.data.has_value()) {
        ReportCategory next = category("refln");
        const auto [name, units] = axis_of(*experiment.data);
        next.table.columns = {"Structure", "d (Å)", "sinθ/λ (Å⁻¹)", "h", "k", "l", "F calc", "F² calc",
                              name + " (" + units + ")"};
        for (std::size_t row = 0; row < refln.size(); ++row) {
            next.table.rows.push_back(
                {refln.structure_id[row], display_text(refln.d_spacing[row]),
                 display_text(refln.sin_theta_over_lambda[row]), std::to_string(refln.index_h[row]),
                 std::to_string(refln.index_k[row]), std::to_string(refln.index_l[row]), display_text(refln.f_calc[row]),
                 display_text(refln.f_squared_calc[row]), display_text(refln.position[row])});
        }
        out.categories.push_back(std::move(next));
    }
    return out;
}

// The analysis categories: the software, the minimizer, the fitting mode and the fit result (the reference report's
// subsections). A scan's fit result is its dataset's, with the scan's counts.
std::vector<ReportCategory> analysis_of(const Project& project, const std::optional<ScanTemplate>& scan, bool fitted) {
    ReportCategory software{"software", "Software", {}, {}};
    software.rows = {{"Framework", "edi " + core_version(), ""}, {"Calculator", "crysta", ""}};
    ReportCategory minimizer = category("minimizer");
    const std::string& descent = project.descent;
    minimizer.rows = {{"Type", descent.empty() ? "crysta" : "crysta (" + descent + ")", ""},
                      {"Maximum iterations",
                       std::to_string(project.minimizer_max_iterations > 0 ? project.minimizer_max_iterations : 50), ""},
                      {"χ² change tolerance",
                       project.minimizer_chi_square_tolerance > 0.0 ? shortest(project.minimizer_chi_square_tolerance)
                                                                    : "crysta's default",
                       ""}};
    ReportCategory mode = category("fitting_mode");
    mode.rows = {{"Type", fitting_mode_name(project.fitting_mode), ""}};
    ReportCategory result{"fit_result", "Fit result", {}, {}};
    const FitResultRecord& record = project.fit_result;
    if (scan && scan->row) {
        const ScanResultIndex::Row& row = *scan->row;
        result.rows = {{"Dataset", scan->file, ""},
                       {"Overall status", row.converged ? "Success" : "Failed", ""},
                       {"Iterations", std::to_string(row.iterations), ""},
                       {"Goodness-of-fit (reduced χ²)", fixed(row.reduced_chi_square, 2), ""},
                       {"Files fitted", std::to_string(scan->fitted) + "/" + std::to_string(scan->files), ""},
                       {"Converged", std::to_string(scan->converged), ""},
                       {"Failed", std::to_string(scan->fitted - scan->converged), ""}};
    } else if (fitted) {
        result.rows = {{"Overall status", status_word(record), ""},
                       {"Fitting time", duration_text(record.fitting_time), "s"},
                       {"Iterations", std::to_string(record.iterations), ""},
                       {"Goodness-of-fit (reduced χ²)", fixed(record.reduced_chi_square, 2), ""},
                       {"Weighted profile R-factor (Rwp)", fixed(record.prof_wr_factor * 100.0, 2), "%"}};
        for (const auto& experiment : project.experiments) {
            if (experiment->fit_prof_wr_factor.has_value()) {
                result.rows.push_back(
                    {"Rwp, " + experiment->name.value(), fixed(*experiment->fit_prof_wr_factor * 100.0, 2), "%"});
            }
        }
    } else {
        result.rows = {{"Overall status", "Not fitted yet", ""}};
    }
    return {software, minimizer, mode, result};
}

}  // namespace

const std::vector<ReportSection>& report_sections() {
    static const std::vector<ReportSection> all = {ReportSection::Summary,     ReportSection::Analysis,
                                                   ReportSection::Structures,  ReportSection::Experiments,
                                                   ReportSection::Correlations, ReportSection::Evolution};
    return all;
}

const char* report_section_name(ReportSection section) {
    switch (section) {
        case ReportSection::Summary:
            return "summary";
        case ReportSection::Analysis:
            return "analysis";
        case ReportSection::Structures:
            return "structures";
        case ReportSection::Experiments:
            return "experiments";
        case ReportSection::Correlations:
            return "correlations";
        case ReportSection::Evolution:
            return "evolution";
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
    // The optional groups (the owner, 2026-10-13): each in the contents, marked whether the options leave it out.
    // Everything else is always in the report.
    const auto group = [&model, &options](const std::string& key, const std::string& title) {
        const bool included = std::find(options.hidden.begin(), options.hidden.end(), key) == options.hidden.end();
        model.contents.push_back({key, title, included});
        return included;
    };
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
    model.fitted = scan_mode ? scan && scan->row.has_value() : project.fit_result.held();
    group("charts", "Charts");
    const bool correlations = group("correlations", "Correlations");
    const bool reflections = group("reflections", "Reflections");
    const bool measured = group("measured_data", "Measured data");
    const bool evolution = scan_mode && group("evolution", "Evolution");
    model.sections = {ReportSection::Summary, ReportSection::Analysis, ReportSection::Structures,
                      ReportSection::Experiments};
    model.analysis = analysis_of(project, scan, model.fitted);
    for (const auto& structure : project.structures) {
        model.structures.push_back(structure_of(*structure, rule));
    }
    for (const auto& experiment : project.experiments) {
        ReportExperiment built = experiment_of(*experiment, rule);
        std::erase_if(built.categories, [reflections, measured](const ReportCategory& part) {
            return (part.id == "refln" && !reflections) || (part.id == "data" && !measured);
        });
        model.experiments.push_back(std::move(built));
    }
    if (correlations) {
        model.sections.push_back(ReportSection::Correlations);
        model.correlations =
            correlations_of(project, options.correlation_level,
                            scan ? &scan->file : scan_mode ? &project.sequential_fit.template_file : nullptr,
                            model.fitted);
    }
    // A scan's parameters across its datasets.
    if (evolution) {
        model.sections.push_back(ReportSection::Evolution);
    }
    return model;
}

}  // namespace edi
