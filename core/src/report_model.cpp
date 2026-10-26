// SPDX-License-Identifier: BSD-3-Clause
#include "edi/report_model.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <ctime>
#include <filesystem>
#include <limits>
#include <map>
#include <unordered_map>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <utility>

#include "edi/categories.hpp"
#include "edi/correlation_matrix.hpp"
#include "edi/display.hpp"
#include "edi/duration_text.hpp"
#include "edi/edit.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/palette.hpp"
#include "edi/presentation.hpp"
#include "edi/scan.hpp"
#include "edi/structure_scene.hpp"
#include "edi/su_text.hpp"
#include "edi/symmetry.hpp"
#include "edi/version.hpp"

namespace edi {

namespace {


std::string shortest(double value) {
    char buffer[64];
    const auto result = std::to_chars(buffer, buffer + sizeof(buffer), value);
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

// A parameter's number as every surface shows it (the dictionary bridge): a value the space group fixes as its
// fraction, one with an s.u. in the project's spelling, any other by its dictionary format.
ReportValue value_of(const Parameter& parameter, const std::string& rule, std::string_view variant = {}) {
    ReportValue out;
    out.value = parameter.value.get();
    const std::optional<double>& su = parameter.uncertainty.get();
    if (su.has_value() && std::isfinite(*su) && *su != 0.0 && std::isfinite(out.value) &&
        parameter.dependence != Dependence::SymmetryFixed) {
        out.su = *su;
    }
    out.text = parameter.spec != nullptr ? display_text(parameter, rule, variant) : shortest(out.value);
    return out;
}

// A parameter's label and units, from the dictionary, for its variant (an atom site's ADP type).
std::string label_of(const Parameter& parameter, const std::string& fallback, std::string_view variant = {}) {
    return parameter.spec != nullptr ? label(uid_of(*parameter.spec), variant) : fallback;
}

std::string units_of(const Parameter& parameter, std::string_view variant = {}) {
    return parameter.spec != nullptr ? units_label(uid_of(*parameter.spec), variant) : std::string();
}

// The variant every row of a table column shares, for its header; the base item's when the rows differ.
std::string shared_variant(const std::vector<std::string>& variants) {
    if (variants.empty() || std::any_of(variants.begin(), variants.end(),
                                        [&variants](const std::string& v) { return v != variants.front(); })) {
        return {};
    }
    return variants.front();
}

// A table's column header for item `uid`: its dictionary label, with its units in brackets.
std::string header(std::string_view uid, std::string_view variant = {}) {
    const std::string units = units_label(uid, variant);
    return units.empty() ? label(uid, variant) : label(uid, variant) + " (" + units + ")";
}

// A number of item `uid`, by its dictionary format for `variant`; an empty cell for one that is not finite.
std::string formatted(std::string_view uid, double value, std::string_view variant = {}) {
    return std::isfinite(value) ? display_text(uid, value, variant) : std::string();
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
    return option_label("fitting_mode.type", mode.empty() ? "single" : mode);
}

// The pairs of correlation rows over their parameters, in the order the rows first name them: the names and the full
// matrix, NaN for a pair no row gives.
// The rows' parameters in the fit's order and their matrix, leaving out the parameters named with any of `hidden`.
void matrix_of_rows(const std::vector<const FitParameterCorrelation*>& rows, const std::vector<std::string>& hidden,
                    std::vector<std::string>& names, std::vector<double>& matrix) {
    const auto shown = [&hidden](const std::string& name) {
        return std::none_of(hidden.begin(), hidden.end(),
                            [&name](const std::string& prefix) { return name.starts_with(prefix); });
    };
    std::map<std::string, std::size_t> index;
    for (const FitParameterCorrelation* row : rows) {
        for (const std::string* name : {&row->parameter_unique_name_i.value(), &row->parameter_unique_name_j.value()}) {
            if (shown(*name) && !index.contains(*name)) {
                index.emplace(*name, names.size());
                names.push_back(*name);
            }
        }
    }
    const std::size_t n = names.size();
    matrix.assign(n * n, std::numeric_limits<double>::quiet_NaN());
    for (const FitParameterCorrelation* row : rows) {
        const auto i = index.find(row->parameter_unique_name_i.value());
        const auto j = index.find(row->parameter_unique_name_j.value());
        if (i != index.end() && j != index.end()) {
            const double value = row->correlation.get();
            matrix[i->second * n + j->second] = value;
            matrix[j->second * n + i->second] = value;
        }
    }
}

// The correlation chart as the Correlations tab draws it: the fit's pairs, the parameters whose strongest correlation
// reaches the level, at most as many as asked, in the fit's order. A scan's are its template file's (`scan_file`), as
// the tab shows a dataset's: the table its fit made (edi ADR-0034), else the rows read with it, else the saved rows
// that name it. Without a fit and without pairs there is no chart.
std::optional<ReportCorrelations> correlations_of(const Project& project, const ReportOptions& options,
                                                  const std::string* scan_file, bool fitted) {
    const std::optional<double>& level = options.correlation_level;
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
        // In a fit of several experiments, the chart of one, as the Correlations tab shows it.
        std::vector<std::string> experiments;
        for (const auto& experiment : project.experiments) {
            experiments.push_back(experiment->name.value());
        }
        const std::size_t shown = options.correlation_experiment < experiments.size() ? options.correlation_experiment : 0;
        matrix_of_rows(rows, other_experiment_prefixes(experiments, shown), names, matrix);
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
    const CorrelationMatrix full{names, matrix};
    const std::vector<double> strengths = correlation_strengths(full);
    // A level keeps every parameter reaching it, as the Correlations tab does; with none, diffraction-lib's automatic
    // rule, and the five strongest when a tie keeps more at every level.
    std::size_t count = n;
    if (level.has_value()) {
        out.level = *level;
    } else if (const std::optional<double> automatic = correlation_default_level(strengths)) {
        out.level = *automatic;
    } else {
        count = kDefaultCorrelatedParameters;
        out.level = correlation_level_for_count(strengths, count);
    }
    CorrelationSelection shown = correlation_matrix(full, out.level, count);
    if (shown.labels.empty()) {
        out.empty_text = "No pairs at this level";
        return out;
    }
    out.labels = std::move(shown.labels);
    out.values = std::move(shown.values);
    return out;
}

// A scan's template dataset as the app shows it (edi ADR-0036 §3): the declared template file, else the first file,
// as the app opens a scan; with that file's results row, the template takes the row's values and uncertainties (a
// parameter the results do not record keeps the template's); without one, the template's own. Either way the file's
// data are loaded, the relations completed and the pattern calculated, so the report draws the structure and the
// calculated pattern of the dataset it reports. Also the scan's counts.
struct ScanTemplate {
    Project project;
    std::string file;
    std::optional<ScanResultIndex::Row> row;
    std::size_t files = 0, fitted = 0, converged = 0;
    std::optional<std::size_t> place;  ///< the template dataset's place among the scan's datasets
};

ScanTemplate scan_template_of(const Project& scan) {
    const ScanDatasets datasets = scan_datasets(scan);
    ScanTemplate out{scan, effective_scan_template_file(scan, datasets), std::nullopt};
    const std::string& file = out.file;
    if (file.empty()) {
        return out;
    }
    const ScanPlaces places = scan_places(datasets);
    const ScanResultIndex index = index_scan_results(scan, datasets, places);
    out.files = datasets.files.size();
    if (const auto found = places.find(file); found != places.end()) {
        out.place = found->second;
    }
    std::vector<Edit::ScanValue> values;
    if (index.error.empty()) {
        for (const ScanResultIndex::Row& row : index.rows) {
            if (row.offset >= 0) {
                ++out.fitted;
                out.converged += row.converged ? 1 : 0;
            }
        }
        const auto place = places.find(file);
        if (place != places.end() && index.rows[place->second].offset >= 0) {
            out.row = index.rows[place->second];
            const std::vector<std::string> cells = read_scan_row(scan, out.row->offset);
            std::map<std::string, const ScanParameterColumns*> columns;
            for (const ScanParameterColumns& parameter : index.parameters) {
                columns.emplace(parameter.name, &parameter);
            }
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
        }
    }
    ExperimentBase& experiment = out.project.experiment();
    Edit::scan_view(out.project, experiment, std::move(values),
                    read_scan_dataset(datasets.directory, file, experiment.effective_beam_mode()))();
    return out;
}

// The structure view as the app's opens: the default scene options in the view's element colours, the home view, the
// report's viewport.
void add_scene(ReportStructure& out, const Structure& structure, ColorScheme colours) {
    const SceneSource source = capture_scene(structure);
    SceneOptions options;
    options.colors = colours;
    out.scene = present_structure(source, options);
    // The element legend is drawn flat on the report's white paper, so its colours are made readable there
    // (ADR-0047); the spheres keep the scheme's.
    for (SceneLegendEntry& entry : out.scene.legend) {
        char hex[8];
        std::snprintf(hex, sizeof(hex), "#%02X%02X%02X", entry.color.r, entry.color.g, entry.color.b);
        const std::string readable = readable_colour(hex, "#FFFFFF");
        entry.color = {static_cast<std::uint8_t>(std::stoi(readable.substr(1, 2), nullptr, 16)),
                       static_cast<std::uint8_t>(std::stoi(readable.substr(3, 2), nullptr, 16)),
                       static_cast<std::uint8_t>(std::stoi(readable.substr(5, 2), nullptr, 16))};
    }
    out.view = default_view(out.scene);
    out.drawing = scene_drawing(out.scene, kReportViewport);
    for (int axis = 0; axis != 3; ++axis) {
        out.along.push_back(view_along(out.scene, axis));
    }
    SceneOptions labelled = options;
    labelled.labels = true;
    out.labels = present_structure(source, labelled).labels;
}

// The pattern chart over the full range, undecimated and linear. The Charts options act on the source, so the panes
// stay present_pattern's: no residual column without the residual, no phases without the ticks. The measured series
// takes the style row of `place`, the experiment's place, or a scan's template dataset's among its datasets.
ReportPattern pattern_of(const Project& project, std::size_t index, const ReportOptions& options, std::size_t place) {
    PatternSource source =
        capture_pattern(project, index, options.d_spacing ? PatternAxis::DSpacing : PatternAxis::Native);
    source.experiment_place = place;
    if (!options.residual) {
        source.resid = nullptr;
    }
    if (!options.bragg_ticks) {
        source.phases.clear();
    }
    ReportPattern out;
    out.presentation = present_pattern(source, PatternView{});
    for (const PatternSeries& series : out.presentation.series) {
        std::vector<std::string> texts;
        if (series.kind == SeriesKind::BraggTicks) {
            texts.reserve(series.points.size());
            for (std::size_t point = 0; point < series.points.size(); ++point) {
                texts.push_back(hover_text(source, series, point));
            }
        }
        out.hover.push_back(std::move(texts));
    }
    return out;
}

// A single crystal's chart: its reflections' measured F² and s.u., and their calculated F² once calculated, with
// the axes' titles and each point's hover by the dictionary, as the app's chart shows them (edi ADR-0051).
ReportSingleCrystal single_crystal_of(const BraggPdExperiment& experiment, const std::string& su_rule) {
    const ReflnDataBase& reflections = *experiment.reflections;
    ReportSingleCrystal out;
    if (!reflections.rectangular()) {
        label_single_crystal(out, su_rule);
        return out;
    }
    out.h.assign(reflections.index_h.begin(), reflections.index_h.end());
    out.k.assign(reflections.index_k.begin(), reflections.index_k.end());
    out.l.assign(reflections.index_l.begin(), reflections.index_l.end());
    out.meas = reflections.intensity_meas;
    out.su = reflections.intensity_meas_su;
    const std::vector<double>& calc = reflections.intensity_calc.values();
    if (experiment.computed_current() && calc.size() == reflections.size()) {
        out.calc = calc;
    }
    label_single_crystal(out, su_rule);
    return out;
}

}  // namespace

void label_single_crystal(ReportSingleCrystal& crystal, const std::string& su_rule) {
    crystal.name = category_label("refln");
    crystal.x_title = label("refln.intensity_calc");
    crystal.y_title = label("refln.intensity_meas");
    crystal.hover.clear();
    const std::size_t rows = std::min({crystal.h.size(), crystal.k.size(), crystal.l.size(), crystal.meas.size(),
                                       crystal.su.size()});
    for (std::size_t row = 0; row < rows; ++row) {
        const double calc = row < crystal.calc.size() ? crystal.calc[row] : std::nan("");
        std::string text;
        for (const std::string& line : reflection_hover_lines(crystal.h[row], crystal.k[row], crystal.l[row],
                                                              crystal.meas[row], crystal.su[row], calc, true, su_rule)) {
            text += (text.empty() ? "" : "<br>") + line;
        }
        crystal.hover.push_back(std::move(text));
    }
}

namespace {

// A subsection of the report: a category and the title its page shows.
ReportCategory category(const std::string& id) { return {id, category_label(id), {}, {}}; }

// Where an experiment's data lie on its own axis, as a row label and units from the dictionary.
std::pair<std::string, std::string> axis_of(const PdDataBase& data) {
    const char* uid = data.two_theta.has_value() ? "data.two_theta" : "data.time_of_flight";
    return {label(uid), units_label(uid)};
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
            next.rows.push_back({label("space_group.name_h_m"), structure.space_group.name_h_m.value(), ""});
            try {
                next.rows.push_back({label("space_group.it_number"),
                                     std::to_string(space_group_it_number(structure.space_group)), ""});
                next.rows.push_back({"Crystal system", crystal_system_name(structure.space_group), ""});
            } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — an unknown setting names no number or system
            }
        } else if (listed.id == "cell") {
            const Cell& cell = structure.cell;
            for (const Parameter* parameter : {&cell.length_a, &cell.length_b, &cell.length_c, &cell.angle_alpha,
                                               &cell.angle_beta, &cell.angle_gamma}) {
                next.rows.push_back(
                    {label_of(*parameter, ""), value_of(*parameter, rule).text, units_of(*parameter)});
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
            // An ADP is labelled and rounded by its site's type: the column by the type every site shares.
            std::vector<std::string> types;
            for (const auto& site : structure.atom_sites) {
                types.push_back(site->adp_type.value());
            }
            next.table.columns = {header("atom_site.id"),          header("atom_site.type_symbol"),
                                  header("atom_site.fract_x"),     header("atom_site.fract_y"),
                                  header("atom_site.fract_z"),     header("atom_site.wyckoff_letter"),
                                  header("atom_site.occupancy"),   header("atom_site.adp_iso", shared_variant(types)),
                                  header("atom_site.adp_type")};
            for (const auto& site : structure.atom_sites) {
                const std::string& letter = site->wyckoff_letter.value();
                const auto found = multiplicity.find(letter);
                next.table.rows.push_back({site->id.value(), site->type_symbol.value(), value_of(site->fract_x, rule).text,
                                           value_of(site->fract_y, rule).text, value_of(site->fract_z, rule).text,
                                           found != multiplicity.end() ? std::to_string(found->second) + letter : letter,
                                           value_of(site->occupancy, rule).text,
                                           value_of(site->adp_iso, rule, site->adp_type.value()).text,
                                           site->adp_type.value()});
            }
        } else if (listed.id == "atom_site_aniso") {
            // A tensor is labelled and rounded by its site's type (Uani, Bani or beta).
            std::map<std::string, std::string> type_of;
            for (const auto& site : structure.atom_sites) {
                type_of.emplace(site->id.value(), site->adp_type.value());
            }
            std::vector<std::string> types;
            for (const auto& row : structure.atom_site_aniso) {
                types.push_back(type_of[row->id.value()]);
            }
            // Rows of several types (beta beside U or B) are different quantities: each row then names its type,
            // which gives its units, and no component column claims one.
            const std::string shared = shared_variant(types);
            const bool mixed = !types.empty() && shared.empty();
            static const std::array<const char*, 6> kComponents{
                "atom_site_aniso.adp_11", "atom_site_aniso.adp_22", "atom_site_aniso.adp_33",
                "atom_site_aniso.adp_12", "atom_site_aniso.adp_13", "atom_site_aniso.adp_23"};
            next.table.columns = {header("atom_site_aniso.id")};
            if (mixed) {
                next.table.columns.push_back(header("atom_site.adp_type"));
            }
            for (const char* component : kComponents) {
                next.table.columns.push_back(mixed ? label(component) : header(component, shared));
            }
            for (const auto& row : structure.atom_site_aniso) {
                const std::string& type = type_of[row->id.value()];
                std::vector<std::string> cells{row->id.value()};
                if (mixed) {
                    cells.push_back(type);
                }
                for (const Parameter* component : {&row->adp_11, &row->adp_22, &row->adp_33, &row->adp_12,
                                                   &row->adp_13, &row->adp_23}) {
                    cells.push_back(value_of(*component, rule, type).text);
                }
                next.table.rows.push_back(std::move(cells));
            }
        } else if (listed.id == "scattering_length") {
            next.table.columns = {header("scattering_length.type_symbol"), header("scattering_length.length_fm")};
            for (const auto& [type, length] : structure.scattering_lengths_fm.get()) {
                next.table.rows.push_back({type, formatted("scattering_length.length_fm", length)});
            }
        }
        if (!next.rows.empty() || !next.table.rows.empty()) {
            out.categories.push_back(std::move(next));
        }
    }
    return out;
}

// The measured points, as the Experiment page's points table lists them: the axis value, the measured intensity and
// its s.u., and the calculated intensity and the background when they describe the model, each column to fixed decimals
// (the axis as the reflections' positions, the intensities enough to give the largest measured one four digits, at
// least one). An excluded point is marked, not dropped: by crysta's status when the calculation is current, else by the
// excluded regions.
ReportTable data_table(const BraggPdExperiment& experiment) {
    const PdDataBase& data = *experiment.data;
    const std::vector<double>& axis = data.axis();
    const std::vector<double>& measured = data.intensity_meas;
    const char* axis_uid = data.two_theta.has_value() ? "data.two_theta" : "data.time_of_flight";
    const bool computed = experiment.computed_current() && data.intensity_calc.size() == axis.size() &&
                          data.intensity_bkg.size() == axis.size();
    const bool status = computed && data.calc_status.size() == axis.size();
    std::vector<bool> excluded(axis.size(), false);
    for (std::size_t row = 0; row < axis.size(); ++row) {
        const double x = axis[row];
        excluded[row] = status ? data.calc_status[row] == "excl"
                               : std::any_of(experiment.excluded_regions.begin(), experiment.excluded_regions.end(),
                                             [x](const auto& region) {
                                                 const double start = region->first.get();
                                                 const double end = region->second.get();
                                                 return x >= std::min(start, end) && x <= std::max(start, end);
                                             });
    }
    const bool any_excluded = std::find(excluded.begin(), excluded.end(), true) != excluded.end();
    // Every intensity column keeps one number of decimals for all its rows, chosen from the largest measured value
    // (owner, 2026-10-13): about three significant digits there, one to six decimals. An excluded row's computed
    // values are NaN; its cell stays empty.
    double largest = 0.0;
    for (const double value : measured) {
        if (std::isfinite(value)) {
            largest = std::max(largest, std::abs(value));
        }
    }
    const int decimals = largest > 0.0 ? std::clamp(3 - static_cast<int>(std::floor(std::log10(largest))), 1, 6) : 1;
    const auto cell = [decimals](const std::vector<double>& column, std::size_t row) {
        return row < column.size() && std::isfinite(column[row]) ? fixed_text(column[row], decimals) : std::string();
    };
    ReportTable table;
    table.columns = {header(axis_uid), header("data.intensity_meas"), header("data.intensity_meas_su")};
    if (computed) {
        table.columns.insert(table.columns.end(), {header("data.intensity_calc"), header("data.intensity_bkg")});
    }
    if (any_excluded) {
        table.columns.push_back(header("data.calc_status"));
    }
    table.rows.reserve(axis.size());
    for (std::size_t row = 0; row < axis.size(); ++row) {
        std::vector<std::string> cells{formatted(axis_uid, axis[row]), cell(measured, row),
                                       cell(data.intensity_meas_su, row)};
        if (computed) {
            cells.push_back(cell(data.intensity_calc.values(), row));
            cells.push_back(cell(data.intensity_bkg.values(), row));
        }
        if (any_excluded) {
            cells.emplace_back(excluded[row] ? "excluded" : "");
        }
        table.rows.push_back(std::move(cells));
    }
    return table;
}

// An experiment's categories in its page's order, filled as the page shows them, and its calculated reflections when
// they describe the model; a loop without rows is left out.
// The experiment's own file in the project, as a save names it; its name alone when a save would refuse it.
std::string own_file(const BraggPdExperiment& experiment) {
    try {
        return std::filesystem::path(entity_path("", "experiment", experiment.name.value())).generic_string();
    } catch (const std::exception&) {
        return experiment.name.value();
    }
}

ReportExperiment experiment_of(const BraggPdExperiment& experiment, const std::string& rule) {
    auto& walked = const_cast<BraggPdExperiment&>(experiment);  // NOLINT(cppcoreguidelines-pro-type-const-cast)
    ReportExperiment out;
    out.id = experiment.name.value();
    for (const Category& listed : experiment_categories(walked)) {
        if (listed.id == "instrument" && listed.fields.empty()) {
            continue;  // a time-of-flight single crystal's: no instrument parameter to report
        }
        ReportCategory next = category(listed.id);
        if (listed.id == "experiment_type") {
            const ExperimentType& type = experiment.experiment_type;
            const auto row = [](const char* uid, const char* value) {
                return ReportRow{label(uid), option_label(uid, value), ""};
            };
            next.rows = {row("experiment_type.sample_form", token(type.effective_sample_form())),
                         row("experiment_type.beam_mode", token(experiment.effective_beam_mode())),
                         row("experiment_type.radiation_probe", token(type.effective_radiation_probe())),
                         row("experiment_type.scattering_type", token(type.effective_scattering_type()))};
        } else if ((listed.id == "data" || listed.id == "data_range") && experiment.data.has_value()) {
            const PdDataBase& data = *experiment.data;
            const std::vector<double>& axis = data.axis();
            const auto [name, units] = axis_of(data);
            // Where the observations are: their data file, or the experiment's own file that holds them.
            if (listed.id == "data") {
                next.rows.push_back({"File", experiment.data_file.empty() ? own_file(experiment) : experiment.data_file, ""});
            }
            next.rows.push_back({"Points", std::to_string(axis.size()), ""});
            if (!axis.empty()) {
                // Each end and the step by the dictionary format of the axis they belong to.
                const std::string axis_uid = std::string(listed.id) + (data.two_theta.has_value() ? ".two_theta" : ".time_of_flight");
                const auto [low, high] = std::minmax_element(axis.begin(), axis.end());
                next.rows.push_back({name + " min", formatted(axis_uid, *low), units});
                next.rows.push_back({name + " max", formatted(axis_uid, *high), units});
                if (listed.id == "data_range" && axis.size() > 1) {
                    next.rows.push_back({name + " step", formatted(axis_uid, std::abs(axis[1] - axis[0])), units});
                }
            }
            if (listed.id == "data") {
                // The report's block holds the calculated columns too, so it is the Data block, not the page's
                // Measured data (the owner, 2026-10-13).
                next.title = "Data";
                next.table = data_table(experiment);
            }
        } else if (listed.id == "instrument" || listed.id == "absorption") {
            add_fields(next.rows, listed.fields, rule);
        } else if (listed.id == "extinction") {
            // The type's label, then its mosaic distribution and items (edi ADR-0049).
            const std::string type = experiment.extinction.type.value_or("none");
            next.rows.push_back({label("extinction.type"), option_label("extinction.type", type), ""});
            if (experiment.extinction.mosaic_distribution) {
                next.rows.push_back({label("extinction.mosaic_distribution"),
                                     option_label("extinction.mosaic_distribution",
                                                  *experiment.extinction.mosaic_distribution),
                                     ""});
            }
            add_fields(next.rows, listed.fields, rule);
        } else if (listed.id == "peak") {
            next.rows.push_back({label("peak.type"), option_label("peak.type", effective_peak_type(experiment)), ""});
            add_fields(next.rows, listed.fields, rule);
            add_fields(next.rows, listed.asymmetry, rule);
        } else if (listed.id == "background") {
            next.rows.push_back(
                {label("background.type"), option_label("background.type", experiment.background_type), ""});
            if (experiment.background_type == "line-segment") {
                next.table.columns = {header("background.position"), header("background.intensity")};
                for (const auto& point : experiment.background) {
                    next.table.rows.push_back(
                        {formatted("background.position", point->position.get()), value_of(point->intensity, rule).text});
                }
            } else {
                next.table.columns = {header("background.order"), header("background.coef")};
                for (const auto& term : experiment.background_terms) {
                    next.table.rows.push_back({std::to_string(term->order.get()), value_of(term->coef, rule).text});
                }
            }
        } else if (listed.id == "linked_structure") {
            next.table.columns = {header("linked_structure.structure_id"), header("linked_structure.scale")};
            for (const auto& link : experiment.linked_structures) {
                next.table.rows.push_back({link->structure_id.value(), value_of(link->scale, rule).text});
            }
        } else if (listed.id == "excluded_region") {
            // A time-of-flight region by its own variant: its units and format.
            const char* variant = experiment.data.has_value() && experiment.data->time_of_flight.has_value()
                                      ? "time-of-flight"
                                      : "";
            next.table.columns = {header("excluded_region.start", variant), header("excluded_region.end", variant)};
            for (const auto& region : experiment.excluded_regions) {
                next.table.rows.push_back({display_text("excluded_region.start", region->first.get(), variant),
                                           display_text("excluded_region.end", region->second.get(), variant)});
            }
        } else if (listed.id == "preferred_orientation") {
            next.table.columns = {header("preferred_orientation.structure_id"), header("preferred_orientation.march_r"),
                                  header("preferred_orientation.march_random_fract")};
            for (const auto& row : experiment.preferred_orientation) {
                next.table.rows.push_back({row->structure_id.value(), value_of(row->march_r, rule).text,
                                           value_of(row->march_random_fract, rule).text});
            }
        } else if (listed.id == "scattering_source") {
            const std::pair<const char*, const std::optional<std::string>*> sources[] = {
                {"scattering_source.xray_form_factor", &experiment.xray_form_factor},
                {"scattering_source.xray_dispersion", &experiment.xray_dispersion},
                {"scattering_source.neutron_scattering_length", &experiment.neutron_scattering_length}};
            for (const auto& [uid, value] : sources) {
                if (value->has_value() && !value->value().empty()) {
                    next.rows.push_back({label(uid), option_label(uid, value->value()), ""});
                }
            }
        }
        if (!next.rows.empty() || !next.table.rows.empty()) {
            out.categories.push_back(std::move(next));
        }
    }
    // A single crystal's measured reflections: where they were read from and how many, after the experiment type;
    // then each reflection with its calculated F² and normalised residual, as the app's reflection group writes them
    // (edi ADR-0049).
    if (experiment.reflections.has_value()) {
        const ReflnDataBase& reflections = *experiment.reflections;
        ReportCategory measured{"measured_reflections", "Measured reflections", {}, {}};
        measured.rows = {{"File", experiment.data_file.empty() ? own_file(experiment) : experiment.data_file, ""},
                         {category_label("refln"), std::to_string(reflections.size()), ""}};
        out.categories.insert(out.categories.empty() ? out.categories.end() : out.categories.begin() + 1,
                              std::move(measured));
        const std::vector<double>& calc = reflections.intensity_calc.values();
        const bool current = experiment.computed_current() && calc.size() == reflections.size();
        ReportCategory next = category("refln");
        next.table.columns = {header("refln.index_h"),        header("refln.index_k"),
                              header("refln.index_l"),        header("refln.intensity_meas"),
                              header("refln.intensity_meas_su"), header("refln.intensity_calc"),
                              "(F² meas \xE2\x88\x92 F² calc)/s.u."};
        for (std::size_t row = 0; reflections.rectangular() && row < reflections.size(); ++row) {
            const double meas = reflections.intensity_meas[row];
            const double su = reflections.intensity_meas_su[row];
            next.table.rows.push_back(
                {std::to_string(reflections.index_h[row]), std::to_string(reflections.index_k[row]),
                 std::to_string(reflections.index_l[row]), formatted("refln.intensity_meas", meas),
                 formatted("refln.intensity_meas_su", su),
                 current ? formatted("refln.intensity_calc", calc[row]) : std::string(),
                 current && su > 0.0 ? fixed_text((meas - calc[row]) / su, 2) : std::string()});
        }
        out.categories.push_back(std::move(next));
        return out;
    }
    // The reflections the calculation made, as the reference report lists them, each column by its dictionary format.
    const PowderReflnDataBase& refln = experiment.refln;
    if (experiment.computed_current() && refln.size() > 0 && experiment.data.has_value()) {
        ReportCategory next = category("refln");
        const char* position_uid = experiment.data->two_theta.has_value() ? "refln.two_theta" : "refln.time_of_flight";
        next.table.columns = {header("refln.structure_id"),   header("refln.d_spacing"),
                              header("refln.sin_theta_over_lambda"), header("refln.index_h"),
                              header("refln.index_k"),        header("refln.index_l"),
                              header("refln.f_calc"),         header("refln.f_squared_calc"),
                              header(position_uid)};
        for (std::size_t row = 0; row < refln.size(); ++row) {
            next.table.rows.push_back(
                {refln.structure_id[row], formatted("refln.d_spacing", refln.d_spacing[row]),
                 formatted("refln.sin_theta_over_lambda", refln.sin_theta_over_lambda[row]),
                 formatted("refln.index_h", refln.index_h[row]), formatted("refln.index_k", refln.index_k[row]),
                 formatted("refln.index_l", refln.index_l[row]), formatted("refln.f_calc", refln.f_calc[row]),
                 formatted("refln.f_squared_calc", refln.f_squared_calc[row]),
                 formatted(position_uid, refln.position[row])});
        }
        out.categories.push_back(std::move(next));
    }
    return out;
}

// The analysis categories: the software, the minimizer, the fitting mode and the fit result (the reference report's
// subsections). A scan's fit result is its dataset's, with the scan's counts.
std::vector<ReportCategory> analysis_of(const Project& project, const std::optional<ScanTemplate>& scan, bool fitted) {
    ReportCategory software{"software", "Software", {}, {}};
    software.rows = {{"Framework", "edi " + core_version(), ""}, {category_label("calculator"), "crysta", ""}};
    ReportCategory minimizer = category("minimizer");
    const std::string& descent = project.descent;
    minimizer.rows = {{label("minimizer.type"), descent.empty() ? "crysta" : "crysta (" + descent + ")", ""},
                      {label("minimizer.max_iterations"),
                       std::to_string(project.minimizer_max_iterations > 0 ? project.minimizer_max_iterations : 50), ""},
                      {label("minimizer.chi_square_tolerance"),
                       project.minimizer_chi_square_tolerance > 0.0
                           ? formatted("minimizer.chi_square_tolerance", project.minimizer_chi_square_tolerance)
                           : "crysta's default",
                       ""}};
    ReportCategory mode = category("fitting_mode");
    mode.rows = {{label("fitting_mode.type"), fitting_mode_name(project.fitting_mode), ""}};
    ReportCategory result = category("fit_result");
    const FitResultRecord& record = project.fit_result;
    if (scan && scan->row) {
        const ScanResultIndex::Row& row = *scan->row;
        result.rows = {{"Dataset", scan->file, ""},
                       {"Overall status", row.converged ? "Success" : "Failed", ""},
                       {label("fit_result.iterations"), std::to_string(row.iterations), ""},
                       {label("fit_result.reduced_chi_square"),
                        formatted("fit_result.reduced_chi_square", row.reduced_chi_square), ""},
                       {"Files fitted", std::to_string(scan->fitted) + "/" + std::to_string(scan->files), ""},
                       {"Converged", std::to_string(scan->converged), ""},
                       {"Failed", std::to_string(scan->fitted - scan->converged), ""}};
    } else if (fitted) {
        result.rows = {{"Overall status", status_word(record), ""},
                       {label("fit_result.fitting_time"), duration_text(record.fitting_time),
                        units_label("fit_result.fitting_time")},
                       {label("fit_result.iterations"), std::to_string(record.iterations), ""},
                       {label("fit_result.reduced_chi_square"),
                        formatted("fit_result.reduced_chi_square", record.reduced_chi_square), ""}};
        // A single crystal's fit is over F²: crysta records its R(F²) and wR(F²) as the profile pair, which the
        // dictionary names by the sample form.
        const bool single_crystal =
            !project.experiments.empty() &&
            std::all_of(project.experiments.begin(), project.experiments.end(),
                        [](const auto& experiment) { return experiment->reflections.has_value(); });
        const std::string form = single_crystal ? token(SampleFormEnum::SINGLE_CRYSTAL) : std::string();
        if (single_crystal && record.prof_r_factor) {
            result.rows.push_back({label("fit_result.prof_r_factor", form),
                                   formatted("fit_result.prof_r_factor", *record.prof_r_factor, form),
                                   units_label("fit_result.prof_r_factor", form)});
        }
        result.rows.push_back({label("fit_result.prof_wr_factor", form),
                               formatted("fit_result.prof_wr_factor", record.prof_wr_factor, form),
                               units_label("fit_result.prof_wr_factor", form)});
        for (const auto& experiment : project.experiments) {
            if (!single_crystal && experiment->fit_prof_wr_factor.has_value()) {
                result.rows.push_back(
                    {label("fit_result_bank.prof_wr_factor") + ", " + experiment->name.value(),
                     formatted("fit_result_bank.prof_wr_factor", *experiment->fit_prof_wr_factor),
                     units_label("fit_result_bank.prof_wr_factor")});
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

ReportOptions effective_report_options(const Project& project, const ReportOverrides& overrides) {
    ReportOptions options;
    if (overrides.excluded) {
        options.hidden = *overrides.excluded;
    } else if (project.report_excluded) {
        options.hidden.clear();
        std::istringstream keys(*project.report_excluded);
        for (std::string key; keys >> key;) {
            options.hidden.push_back(key);
        }
    }
    options.correlation_level =
        overrides.correlation_threshold ? overrides.correlation_threshold : project.correlation_threshold;
    options.d_spacing = overrides.x_axis.value_or(project.pattern_x_axis.value_or("native")) == "d_spacing";
    options.embed_libraries = overrides.html_offline.value_or(project.report_html_offline.value_or(false));
    const auto scheme_named = [](const std::string& name) {
        const std::optional<ColourScheme> scheme = colour_scheme_from_name(name);
        if (!scheme) {
            std::string known;
            for (const std::string_view each : colour_scheme_names()) {
                known += (known.empty() ? "" : ", ") + std::string(each);
            }
            throw std::invalid_argument("unknown colour scheme '" + name + "': one of " + known);
        }
        return *scheme;
    };
    if (overrides.colour_scheme) {
        options.colour_scheme = scheme_named(*overrides.colour_scheme);
    }
    if (overrides.structure_colour_scheme) {
        options.structure_colour_scheme = scheme_named(*overrides.structure_colour_scheme);
    }
    if (overrides.correlation_experiment) {
        const auto& experiments = project.experiments;
        const auto found = std::find_if(experiments.begin(), experiments.end(), [&overrides](const auto& experiment) {
            return experiment->name.value() == *overrides.correlation_experiment;
        });
        if (found == experiments.end()) {
            throw std::invalid_argument("the project has no experiment '" + *overrides.correlation_experiment + "'");
        }
        options.correlation_experiment = static_cast<std::size_t>(found - experiments.begin());
    }
    return options;
}

std::string reliability_text(const Project& project, std::size_t experiment) {
    if (project.fit_result.result_kind.empty()) {
        return {};
    }
    double rwp = project.fit_result.prof_wr_factor;
    if (experiment < project.experiments.size() && project.experiments[experiment]->fit_prof_wr_factor) {
        rwp = *project.experiments[experiment]->fit_prof_wr_factor;
    }
    // crysta records a single crystal's R(F²) and wR(F²) as the profile pair, which the dictionary names by the
    // sample form.
    if (experiment < project.experiments.size() && project.experiments[experiment]->reflections.has_value()) {
        const ExperimentBase& crystal = *project.experiments[experiment];
        const std::string form = token(crystal.experiment_type.effective_sample_form());
        const std::optional<double> r =
            crystal.fit_prof_r_factor ? crystal.fit_prof_r_factor : project.fit_result.prof_r_factor;
        const auto factor = [&form](const char* uid, double value) {
            return label(uid, form) + " " + formatted(uid, value, form) + " " + units_label(uid, form) + " \xC2\xB7 ";
        };
        return (r ? factor("fit_result.prof_r_factor", *r) : std::string()) + factor("fit_result.prof_wr_factor", rwp) +
               label("fit_result.reduced_chi_square") + " " +
               formatted("fit_result.reduced_chi_square", project.fit_result.reduced_chi_square);
    }
    return label("fit_result.prof_wr_factor") + " " + formatted("fit_result.prof_wr_factor", rwp) + " " +
           units_label("fit_result.prof_wr_factor") + " \xC2\xB7 " + label("fit_result.reduced_chi_square") + " " +
           formatted("fit_result.reduced_chi_square", project.fit_result.reduced_chi_square);
}

namespace {

// A scan's parameters across its datasets, as the Evolution tab draws them (evolution_series): each listed
// parameter's points at the first extract rule's value, else at the file's place, each value's text by
// `rule`. No series when the scan's datasets or results cannot be read.
std::vector<ReportEvolution> evolution_of(const Project& scan, const std::string& rule) {
    std::vector<ReportEvolution> out;
    try {
        const ScanDatasets datasets = scan_datasets(scan);
        const ScanPlaces places = scan_places(datasets);
        const ScanResultIndex index = index_scan_results(scan, datasets, places);
        std::string x_title = "file index";
        for (const auto& extract : scan.sequential_fit.extract) {
            const std::string unit = scan_target_unit(extract->target);
            x_title = unit.empty() ? extract->id.value() : extract->id.value() + " (" + unit + ")";
            break;
        }
        // Each parameter's units, dictionary item and variant (an ADP's site type) by its unique name or its results
        // column.
        const std::unordered_map<const Parameter*, std::string> variants = parameter_variants(scan);
        std::map<std::string, std::string> units;
        std::map<std::string, std::pair<std::string, std::string>> uids;
        for (const NamedParameter& named : named_parameters(scan)) {
            const auto variant = variants.find(named.parameter);
            const std::string type = variant != variants.end() ? variant->second : std::string();
            units.emplace(named.unique_name, units_of(*named.parameter, type));
            units.emplace(scan_results_column(named.unique_name), units_of(*named.parameter, type));
            if (named.parameter->spec != nullptr) {
                uids.emplace(named.unique_name, std::pair{uid_of(*named.parameter->spec), type});
                uids.emplace(scan_results_column(named.unique_name), std::pair{uid_of(*named.parameter->spec), type});
            }
        }
        const std::vector<std::string> names = evolution_parameters(scan, index);
        for (const std::string& name : names) {
            const auto found = units.find(name);
            out.push_back({name, x_title, {}, found != units.end() ? found->second : std::string()});
        }
        // Every series from one read of the results.
        evolution_series(scan, places, index, names, true,
                         [&out, &rule, &uids, &names](std::size_t i, const EvolutionPoint& point) {
                             const auto uid = uids.find(names[i]);
                             const std::string text =
                                 point.su > 0.0      ? value_su_text(point.y, point.su, rule)
                                 : uid != uids.end() ? formatted(uid->second.first, point.y, uid->second.second)
                                                     : shortest(point.y);
                             out[i].points.push_back({point.x, point.y, point.su, text});
                         });
    } catch (const std::exception&) {
        out.clear();
    }
    return out;
}

}  // namespace

ReportModel build_report(const Project& input, const ReportOptions& options) {
    // A scan's report is its template dataset's, fitted (ADR-0036 §3); one whose datasets or results cannot be read
    // reports the template as it is.
    const bool scan_mode = is_scan_fitting_mode(input.fitting_mode);
    std::optional<ScanTemplate> scan;
    if (scan_mode) {
        try {
            scan = scan_template_of(input);
        } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — the template as it is, below
        }
    }
    // Calculated where it stays: a project's computed state does not survive a copy or a move.
    if (scan) {
        apply_relations(scan->project);
        try {
            scan->project.calculate();
        } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — a refused calculation leaves the pattern not current
        }
    }
    const Project& project = scan ? scan->project : input;
    // A report and its CIF round by the IUCr rule whatever the project's own setting (the owner, 2026-10-24).
    const std::string rule = kReportSuRule;
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
    // "." and "?" are CIF's empty values: a project that names no authors shows none.
    const std::string& authors = project.metadata.authors;
    model.authors = authors == "." || authors == "?" ? std::string() : authors;
    model.description = project.metadata.description;
    for (const auto& structure : project.structures) {
        model.structure_ids.push_back(structure->name.value());
    }
    for (const auto& experiment : project.experiments) {
        model.experiment_ids.push_back(experiment->name.value());
    }
    model.fitted = scan_mode ? scan && scan->row.has_value() : project.fit_result.held();
    const bool charts = group("charts", "Charts");
    const bool correlations = group("correlations", category_label("fit_parameter_correlation"));
    const bool reflections = group("reflections", category_label("refln"));
    const bool data = group("data", "Data");
    const bool evolution = scan_mode && group("evolution", "Evolution");
    model.sections = {ReportSection::Summary, ReportSection::Analysis, ReportSection::Structures,
                      ReportSection::Experiments};
    model.analysis = analysis_of(project, scan, model.fitted);
    const std::unordered_map<const Parameter*, std::string> variants = parameter_variants(project);
    for (const NamedParameter& named : named_parameters(project)) {
        const Parameter& parameter = *named.parameter;
        const std::optional<double>& su = parameter.uncertainty.get();
        const auto variant = variants.find(&parameter);
        const std::string type = variant != variants.end() ? variant->second : std::string();
        model.parameters.push_back({named.unique_name, label_of(parameter, named.unique_name, type),
                                    parameter.value.get(), su && std::isfinite(*su) ? su : std::nullopt,
                                    value_of(parameter, rule, type).text, units_of(parameter, type),
                                    parameter.start_value.get(), parameter.free.get()});
    }
    for (const auto& structure : project.structures) {
        ReportStructure built = structure_of(*structure, rule);
        if (charts) {
            add_scene(built, *structure, options.element_colours);
        }
        model.structures.push_back(std::move(built));
    }
    for (std::size_t index = 0; index < project.experiments.size(); ++index) {
        ReportExperiment built = experiment_of(*project.experiments[index], rule);
        std::erase_if(built.categories, [reflections, data](const ReportCategory& part) {
            return (part.id == "refln" && !reflections) || (part.id == "data" && !data);
        });
        if (charts && project.experiments[index]->reflections.has_value()) {
            built.single_crystal = single_crystal_of(*project.experiments[index], rule);
            built.single_crystal->title = reliability_text(project, index);
        } else if (charts) {
            built.pattern = pattern_of(project, index, options, scan && scan->place ? *scan->place : index);
            built.pattern.title = reliability_text(project, index);
        }
        model.experiments.push_back(std::move(built));
    }
    if (correlations) {
        model.sections.push_back(ReportSection::Correlations);
        // A scan whose template could not be made still reports its template dataset's pairs.
        const std::string template_file = scan_mode && !scan ? effective_scan_template_file(input) : std::string();
        model.correlations =
            correlations_of(project, options, scan ? &scan->file : scan_mode ? &template_file : nullptr,
                            model.fitted);
    }
    // A scan's parameters across its datasets.
    if (evolution) {
        model.sections.push_back(ReportSection::Evolution);
        model.evolution = evolution_of(input, rule);
    }
    // A scan reports its template dataset at its place among the scan's datasets, in the colour the app's pages give
    // it there; the table has a measured row for each dataset.
    model.pattern_styles = pattern_style_table(options.colour_scheme,
                                               scan && scan->place ? scan->files : project.experiments.size(),
                                               project.structures.size(), options.structure_colour_scheme);
    model.structure_styles = structure_style_table();
    return model;
}

}  // namespace edi
