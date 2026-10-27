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

namespace {

// A block's text split as crysta's writer orders it: the lines up to its `data_` line, then each item, loop (its
// keys and rows) or multi-line value, with whether its category is an output one.
struct TextUnits {
    std::vector<std::string> head;
    std::vector<std::pair<bool, std::vector<std::string>>> units;
};

TextUnits text_units(const std::string& text) {
    TextUnits out;
    std::istringstream in(text);
    std::vector<std::string> lines;
    for (std::string line; std::getline(in, line);) {
        lines.push_back(line);
    }
    const auto output_of = [](const std::string& line) {
        const std::size_t end = line.find_first_of(". \t");
        return category_is_output(std::string_view(line).substr(0, end));
    };
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
            out.units.back().second.push_back(line);
            in_text_field = !line.starts_with(';');
            continue;
        }
        if (line.empty()) {
            in_loop_keys = false;
            continue;
        }
        if (line == "loop_") {
            out.units.push_back({false, {}});
            in_loop_keys = true;
        } else if (line.starts_with('_') && in_loop_keys) {
            if (out.units.back().second.size() == 1) {
                out.units.back().first = output_of(line);
            }
        } else if (line.starts_with('_')) {
            out.units.push_back({output_of(line), {}});
        } else if (out.units.empty()) {
            out.units.push_back({false, {}});
        } else {
            in_loop_keys = false;
        }
        in_text_field = line.starts_with(';');
        out.units.back().second.push_back(line);
    }
    return out;
}

// The units of one kind, each after a blank line, as a save writes them.
void append_units(std::string& out, const TextUnits& split, bool output) {
    for (const auto& [is_output, lines] : split.units) {
        if (is_output != output) {
            continue;
        }
        if (!out.empty() && !out.ends_with("\n\n")) {
            out += '\n';
        }
        for (const std::string& line : lines) {
            out.append(line).push_back('\n');
        }
    }
}

}  // namespace

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
