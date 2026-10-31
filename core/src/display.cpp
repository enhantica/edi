// SPDX-License-Identifier: BSD-3-Clause
#include "edi/display.hpp"

// crysta's SDK carries the dictionary from this pin on; drop the guard when the pin moves.
#if __has_include("crysta/dictionary_items.hpp")

#include <algorithm>
#include <cmath>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "crysta/dictionary_items.hpp"
#include "crysta/su_format.hpp"
#include "edi/model.hpp"
#include "edi/parameter_spec.hpp"
#include "edi/su_text.hpp"

namespace edi {

namespace {

const crysta::DictionaryItem& item(std::string_view uid) {
    const crysta::DictionaryItem* found = crysta::find_dictionary_item(uid);
    if (found == nullptr) {
        throw std::invalid_argument("crysta's dictionary has no item '" + std::string(uid) + "'");
    }
    return *found;
}

crysta::SuRule rule_of(const std::string& rule) {
    const std::optional<crysta::SuRule> found = crysta::su_rule_from_name(rule);
    if (!found.has_value()) {
        throw std::invalid_argument("_su_format.rule is '" + rule + "', expected iucr_19 or iucr_99");
    }
    return *found;
}

const ParameterSpec& spec_of(const Parameter& parameter) {
    if (parameter.spec == nullptr) {
        throw std::invalid_argument("a parameter without a spec has no dictionary item");
    }
    return *parameter.spec;
}

crysta::Dependence dependence_of(Dependence dependence) {
    switch (dependence) {
        case Dependence::SymmetryFixed:
            return crysta::Dependence::SymmetryFixed;
        case Dependence::SymmetryTied:
            return crysta::Dependence::SymmetryTied;
        case Dependence::Constrained:
            return crysta::Dependence::Constrained;
        case Dependence::Independent:
            break;
    }
    return crysta::Dependence::Independent;
}

crysta::DisplayFormat format_of(const crysta::DictionaryItem& found, std::string_view variant) {
    const std::optional<crysta::DisplayFormat> format = found.format_for(variant);
    if (!format.has_value()) {
        throw std::invalid_argument("dictionary item '" + found.uid + "' has no display format");
    }
    return *format;
}

}  // namespace

std::string uid_of(const ParameterSpec& spec) { return std::string(spec.category) + "." + spec.name; }

bool has_item(std::string_view uid) { return crysta::find_dictionary_item(uid) != nullptr; }

std::string label(std::string_view uid, std::string_view variant) { return item(uid).display_name_for(variant); }

std::string units_label(std::string_view uid, std::string_view variant) {
    return item(uid).display_units_for(variant);
}

std::string description(std::string_view uid) { return item(uid).description; }

std::string edi_name(std::string_view uid) { return item(uid).edi_tag; }

std::string tooltip(std::string_view uid, std::string_view variant) {
    const crysta::DictionaryItem& found = item(uid);
    return found.display_name_for(variant) + ": " + found.edi_tag;
}

std::vector<DisplayOption> options(std::string_view uid) {
    std::vector<DisplayOption> out;
    for (const crysta::DictionaryOption& option : item(uid).options) {
        out.push_back({option.token, option.display_name, option.description});
    }
    return out;
}

std::string option_label(std::string_view uid, std::string_view token) {
    const crysta::DictionaryItem& found = item(uid);
    const crysta::DictionaryOption* option = found.option(token);
    if (option == nullptr) {
        throw std::invalid_argument("'" + std::string(token) + "' is not a value of " + found.edi_tag);
    }
    return option->display_name;
}

std::string option_tooltip(std::string_view uid, std::string_view token) {
    return item(uid).edi_tag + " " + std::string(token);
}

std::string category_label(std::string_view id) {
    const crysta::DictionaryCategory* found = crysta::find_dictionary_category(id);
    if (found == nullptr) {
        return {};
    }
    return found->loop ? found->loop_title : found->title;
}

bool category_counts_rows(std::string_view id) {
    const crysta::DictionaryCategory* found = crysta::find_dictionary_category(id);
    return found != nullptr && found->count_in_title;
}

std::string category_icon(std::string_view id) {
    const crysta::DictionaryCategory* found = crysta::find_dictionary_category(id);
    return found != nullptr ? found->icon : std::string();
}

std::string category_description(std::string_view id) {
    const crysta::DictionaryCategory* found = crysta::find_dictionary_category(id);
    return found != nullptr ? found->description : std::string();
}

std::string category_tooltip(std::string_view id) {
    const crysta::DictionaryCategory* found = crysta::find_dictionary_category(id);
    return found != nullptr ? found->title + ": " + found->edi_name : std::string();
}

int category_order(std::string_view id) {
    const crysta::DictionaryCategory* found = crysta::find_dictionary_category(id);
    return found != nullptr ? found->order : std::numeric_limits<int>::max();
}

bool category_is_output(std::string_view id) {
    const crysta::DictionaryCategory* found = crysta::find_dictionary_category(id);
    return found != nullptr && found->output;
}

bool item_is_set_by_program(std::string_view tag) {
    static const std::string_view kSet[] = {"_metadata.created", "_metadata.last_modified", "_metadata.timestamp",
                                            "_metadata.path"};
    return std::find(std::begin(kSet), std::end(kSet), tag) != std::end(kSet);
}

namespace {

// A block's text split as crysta's writer orders it: the lines up to its `data_` line, then each item, loop (its
// keys and rows) or multi-line value, with its category's id and whether that category is an output one.
struct TextUnit {
    bool output = false;
    std::string id;
    std::vector<std::string> lines;
};
struct TextUnits {
    std::vector<std::string> head;
    std::vector<TextUnit> units;
};

// The category id of an item line, `_cell.length_a 5` giving `cell`.
std::string category_of(const std::string& line) {
    const std::size_t end = line.find_first_of(". \t");
    return line.substr(1, end == std::string::npos ? std::string::npos : end - 1);
}

TextUnits text_units(const std::string& text) {
    TextUnits out;
    std::istringstream in(text);
    std::vector<std::string> lines;
    for (std::string line; std::getline(in, line);) {
        lines.push_back(line);
    }
    bool body = std::none_of(lines.begin(), lines.end(), [](const std::string& line) { return line.starts_with("data_"); });
    bool in_text_field = false;
    bool in_loop_keys = false;
    for (const std::string& line : lines) {
        if (!body) {
            out.head.push_back(line);
            body = line.starts_with("data_");
            continue;
        }
        if (in_text_field) {
            out.units.back().lines.push_back(line);
            in_text_field = !line.starts_with(';');
            continue;
        }
        if (line.empty()) {
            in_loop_keys = false;
            continue;
        }
        if (line == "loop_") {
            out.units.push_back({});
            in_loop_keys = true;
        } else if (line.starts_with('_') && in_loop_keys) {
            if (out.units.back().lines.size() == 1) {
                out.units.back().id = category_of(line);
                out.units.back().output = category_is_output(out.units.back().id);
            }
        } else if (line.starts_with('_')) {
            const std::string id = category_of(line);
            const std::string tag = line.substr(0, line.find_first_of(" \t"));
            out.units.push_back({category_is_output(id) || item_is_set_by_program(tag), id, {}});
        } else if (out.units.empty()) {
            out.units.push_back({});
        } else {
            in_loop_keys = false;
        }
        in_text_field = line.starts_with(';');
        out.units.back().lines.push_back(line);
    }
    // An experiment's type is fixed once it holds measured data (the owner, 2026-10-27): its items are then not
    // the user's to edit.
    const bool measured = std::any_of(out.units.begin(), out.units.end(), [](const TextUnit& unit) {
        return std::find(unit.lines.begin(), unit.lines.end(), "_data.intensity_meas") != unit.lines.end();
    });
    if (measured) {
        for (TextUnit& unit : out.units) {
            unit.output = unit.output || unit.id == "experiment_type";
        }
    }
    return out;
}

// A unit after `previous` as a save writes it: one category's items one after another, one blank line between
// categories and around each loop (the owner, 2026-10-27).
void append_unit(std::string& out, const TextUnit* previous, const TextUnit& unit) {
    const bool loop = !unit.lines.empty() && unit.lines.front() == "loop_";
    const bool together = previous != nullptr && !loop && !previous->lines.empty() &&
                          previous->lines.front() != "loop_" && previous->id == unit.id && !unit.id.empty();
    if (!out.empty() && !together && !out.ends_with("\n\n")) {
        out += '\n';
    }
    for (const std::string& line : unit.lines) {
        out.append(line).push_back('\n');
    }
}

// The units of one kind.
void append_units(std::string& out, const TextUnits& split, bool output) {
    const TextUnit* previous = nullptr;
    for (const TextUnit& unit : split.units) {
        if (unit.output != output) {
            continue;
        }
        append_unit(out, previous, unit);
        previous = &unit;
    }
}

// A line's values: words, a quoted text (its quotes removed) or a bracketed list, each one value.
std::vector<std::string> line_values(const std::string& line) {
    std::vector<std::string> values;
    std::size_t i = 0;
    while (i < line.size()) {
        if (line[i] == ' ' || line[i] == '\t') {
            ++i;
            continue;
        }
        std::size_t end = i;
        if (line[i] == '\'' || line[i] == '"') {
            end = line.find(line[i], i + 1);
            end = end == std::string::npos ? line.size() : end;
            values.push_back(line.substr(i + 1, end - i - 1));
            i = end + 1;
            continue;
        }
        if (line[i] == '[') {
            int depth = 0;
            for (; end < line.size(); ++end) {
                depth += line[end] == '[' ? 1 : line[end] == ']' ? -1 : 0;
                if (depth == 0) {
                    break;
                }
            }
            end = std::min(end + 1, line.size());
        } else {
            end = line.find_first_of(" \t", i);
            end = end == std::string::npos ? line.size() : end;
        }
        values.push_back(line.substr(i, end - i));
        i = end;
    }
    return values;
}

// A value as the writer spells one: quoted when it is empty or holds a space or a quote.
std::string written_value(const std::string& value) {
    if (!value.empty() && value.find_first_of(" \t'\"") == std::string::npos) {
        return value;
    }
    return (value.find('"') == std::string::npos ? "\"" : "'") + value + (value.find('"') == std::string::npos ? "\"" : "'");
}

}  // namespace

std::vector<std::string> text_category_ids(const std::string& text) {
    std::vector<std::string> ids;
    for (const TextUnit& unit : text_units(text).units) {
        if (!unit.id.empty() && std::find(ids.begin(), ids.end(), unit.id) == ids.end()) {
            ids.push_back(unit.id);
        }
    }
    return ids;
}

TextCategory text_category(const std::string& text, std::string_view id) {
    TextCategory out;
    for (const TextUnit& unit : text_units(text).units) {
        if (unit.id != id || unit.lines.empty()) {
            continue;
        }
        if (unit.lines.front() == "loop_") {
            out.loop = true;
            std::vector<std::string> values;
            for (std::size_t k = 1; k < unit.lines.size(); ++k) {
                const std::string& line = unit.lines[k];
                if (line.starts_with('_') && values.empty()) {
                    out.names.push_back(line.substr(line.find('.') + 1));
                } else {
                    const std::vector<std::string> more = line_values(line);
                    values.insert(values.end(), more.begin(), more.end());
                }
            }
            for (std::size_t k = 0; !out.names.empty() && k + out.names.size() <= values.size(); k += out.names.size()) {
                out.rows.emplace_back(values.begin() + static_cast<std::ptrdiff_t>(k),
                                      values.begin() + static_cast<std::ptrdiff_t>(k + out.names.size()));
            }
            continue;
        }
        // One item: its name, then its value on the line, or the lines of a text field after it.
        const std::string& line = unit.lines.front();
        const std::size_t dot = line.find('.');
        const std::size_t end = line.find_first_of(" \t");
        out.names.push_back(line.substr(dot + 1, end == std::string::npos ? std::string::npos : end - dot - 1));
        std::string value;
        if (unit.lines.size() > 1 && unit.lines[1].starts_with(';')) {
            // A text field, as crysta writes a long description: a line break inside a paragraph is a space, an
            // empty line a paragraph break.
            std::size_t breaks = 0;
            value.clear();
            std::vector<std::string> field{unit.lines[1].substr(1)};
            if (unit.lines.size() > 2) {
                field.insert(field.end(), unit.lines.begin() + 2, unit.lines.end() - 1);
            }
            for (const std::string& line : field) {
                if (line.empty()) {
                    breaks += value.empty() ? 0 : 1;
                    continue;
                }
                if (!value.empty()) {
                    value += breaks > 0 ? std::string(breaks, '\n') : std::string(" ");
                }
                breaks = 0;
                value += line;
            }
        } else {
            const std::vector<std::string> values = line_values(end == std::string::npos ? std::string() : line.substr(end));
            value = values.empty() ? std::string() : values.front();
        }
        if (out.rows.empty()) {
            out.rows.emplace_back();
        }
        out.rows.front().push_back(value);
    }
    return out;
}

std::string with_text_value(const std::string& text, std::string_view id, std::size_t row, std::string_view name,
                            const std::string& value) {
    TextUnits split = text_units(text);
    const std::string tag = "_" + std::string(id) + "." + std::string(name);
    for (TextUnit& unit : split.units) {
        if (unit.id != id || unit.lines.empty()) {
            continue;
        }
        if (unit.lines.front() != "loop_") {
            if (unit.lines.front() == tag || unit.lines.front().starts_with(tag + " ") ||
                unit.lines.front().starts_with(tag + "\t")) {
                unit.lines = {tag + " " + written_value(value)};
            }
            continue;
        }
        const TextCategory category = text_category(std::string("data_x\n") + [&unit] {
            std::string lines;
            for (const std::string& line : unit.lines) {
                lines.append(line).push_back('\n');
            }
            return lines;
        }(), id);
        const auto column = std::find(category.names.begin(), category.names.end(), name);
        if (column == category.names.end() || row >= category.rows.size()) {
            continue;
        }
        std::vector<std::vector<std::string>> rows = category.rows;
        rows[row][static_cast<std::size_t>(column - category.names.begin())] = value;
        unit.lines = {"loop_"};
        for (const std::string& key : category.names) {
            unit.lines.push_back("_" + std::string(id) + "." + key);
        }
        for (const std::vector<std::string>& values : rows) {
            std::string line;
            for (const std::string& v : values) {
                line += (line.empty() ? "" : " ") + (v.starts_with('[') ? v : written_value(v));
            }
            unit.lines.push_back(line);
        }
    }
    std::string out;
    for (const std::string& line : split.head) {
        out.append(line).push_back('\n');
    }
    const TextUnit* previous = nullptr;
    for (const TextUnit& unit : split.units) {
        append_unit(out, previous, unit);
        previous = &unit;
    }
    return out;
}

std::string input_categories_text(const std::string& text) {
    const TextUnits split = text_units(text);
    std::string out;
    for (const std::string& line : split.head) {
        out.append(line).push_back('\n');
    }
    append_units(out, split, false);
    return out;
}

std::string with_output_categories(const std::string& edited, const std::string& full) {
    std::string out = edited;
    if (!out.empty() && !out.ends_with('\n')) {
        out.push_back('\n');
    }
    append_units(out, text_units(full), true);
    return out;
}

std::string display_text(const Parameter& parameter, const std::string& su_rule, std::string_view variant) {
    const crysta::DictionaryItem& found = item(uid_of(spec_of(parameter)));
    return crysta::display_text(parameter.value, parameter.uncertainty.get(),
                                parameter.dependence == Dependence::SymmetryFixed, found, rule_of(su_rule),
                                variant);
}

std::string display_text(std::string_view uid, double value, std::string_view variant) {
    const crysta::DictionaryItem& found = item(uid);
    return crysta::format_display(value, format_of(found, variant));
}

std::vector<std::string> reflection_hover_lines(int h, int k, int l, double meas, double su, double calc, bool squared,
                                                const std::string& su_rule) {
    const char* const measured = squared ? "refln.intensity_meas" : "refln.f_meas";
    const char* const calculated = squared ? "refln.intensity_calc" : "refln.f_calc";
    std::vector<std::string> lines{std::to_string(h) + " " + std::to_string(k) + " " + std::to_string(l)};
    if (std::isfinite(meas) && std::isfinite(su) && su > 0.0) {
        const SuText text = su_text(meas, su, su_rule);
        lines.push_back(label(measured) + ": " + text.value + " \xC2\xB1 " + text.su);
    } else if (std::isfinite(meas)) {
        lines.push_back(label(measured) + ": " + display_text(measured, meas));
    }
    if (std::isfinite(calc)) {
        lines.push_back(label(calculated) + ": " + display_text(calculated, calc));
    }
    return lines;
}

double display_step(const Parameter& parameter, std::string_view variant) {
    return display_step(uid_of(spec_of(parameter)), parameter.value, variant);
}

double display_step(std::string_view uid, double value, std::string_view variant) {
    const crysta::DictionaryItem& found = item(uid);
    return crysta::display_step(value, format_of(found, variant));
}

FileText file_text(const Parameter& parameter, const std::string& su_rule, bool exact) {
    const crysta::DictionaryItem& found = item(uid_of(spec_of(parameter)));
    const crysta::WrittenText text =
        crysta::written_text(parameter.value, parameter.uncertainty.get(), parameter.free.get(),
                             dependence_of(parameter.dependence), found, rule_of(su_rule), exact);
    return {text.value, text.su};
}

FileText fitted_text(std::string_view uid, double value, double su, const std::string& su_rule) {
    const crysta::WrittenText text =
        crysta::written_text(value, su, true, crysta::Dependence::Independent, item(uid), rule_of(su_rule));
    return {text.value, text.su};
}

std::unordered_map<const Parameter*, std::string> parameter_variants(const Structure& structure) {
    std::unordered_map<const Parameter*, std::string> variants;
    for (const auto& site : structure.atom_sites) {
        variants.emplace(&site->adp_iso, site->adp_type.value());
        for (const auto& tensor : structure.atom_site_aniso) {
            if (tensor->id.value() == site->id.value()) {
                for (const Parameter* component : tensor->parameters()) {
                    variants.emplace(component, site->adp_type.value());
                }
            }
        }
    }
    return variants;
}

std::unordered_map<const Parameter*, std::string> parameter_variants(const ExperimentBase& experiment) {
    std::unordered_map<const Parameter*, std::string> variants;
    const InstrumentBase& instrument = experiment.instrument;
    if (experiment.experiment_type.effective_radiation_probe() == RadiationProbeEnum::XRAY &&
        instrument.setup_wavelength && instrument.setup_wavelength_2_to_1_ratio &&
        instrument.setup_wavelength_2_to_1_ratio->value.get() > 0.0) {
        variants.emplace(&*instrument.setup_wavelength, "doublet");
    }
    return variants;
}

std::unordered_map<const Parameter*, std::string> parameter_variants(const Project& project) {
    std::unordered_map<const Parameter*, std::string> variants;
    for (const auto& structure : project.structures) {
        variants.merge(parameter_variants(*structure));
    }
    for (const auto& experiment : project.experiments) {
        variants.merge(parameter_variants(*experiment));
    }
    return variants;
}

bool written_exactly(const SaveSpelling& spelling, const Project& project, const Parameter& parameter) {
    if (spelling.all_exact) {
        return true;
    }
    for (const auto& structure : project.structures) {
        if (std::find(spelling.exact_cells.begin(), spelling.exact_cells.end(), structure->name.value()) ==
            spelling.exact_cells.end()) {
            continue;
        }
        for (const Parameter* cell : {&structure->cell.length_a, &structure->cell.length_b, &structure->cell.length_c,
                                      &structure->cell.angle_alpha, &structure->cell.angle_beta,
                                      &structure->cell.angle_gamma}) {
            if (cell == &parameter) {
                return true;
            }
        }
    }
    return false;
}

std::string file_text(std::string_view uid, double value) {
    return crysta::written_text(value, std::nullopt, false, crysta::Dependence::Independent, item(uid),
                                crysta::SuRule::Iucr19)
        .value;
}

std::string fixed_text(double value, int decimals) {
    return crysta::format_display(value, crysta::DisplayFormat{crysta::DisplayFormat::Kind::Fixed, decimals});
}

std::optional<std::string> exact_fraction(double value) { return crysta::exact_fraction(value); }

}  // namespace edi

#endif
