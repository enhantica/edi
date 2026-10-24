// SPDX-License-Identifier: BSD-3-Clause
#include "edi/display.hpp"

// crysta's SDK carries the dictionary from this pin on; drop the guard when the pin moves.
#if __has_include("crysta/dictionary_items.hpp")

#include <cmath>
#include <stdexcept>
#include <string>

#include "crysta/dictionary_items.hpp"
#include "crysta/su_format.hpp"
#include "edi/model.hpp"
#include "edi/parameter_spec.hpp"

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

double display_step(const Parameter& parameter, std::string_view variant) {
    return display_step(uid_of(spec_of(parameter)), parameter.value, variant);
}

double display_step(std::string_view uid, double value, std::string_view variant) {
    const crysta::DictionaryItem& found = item(uid);
    return crysta::display_step(value, format_of(found, variant));
}

FileText file_text(const Parameter& parameter, const std::string& su_rule) {
    const crysta::DictionaryItem& found = item(uid_of(spec_of(parameter)));
    const crysta::WrittenText text =
        crysta::written_text(parameter.value, parameter.uncertainty.get(), parameter.free.get(),
                             dependence_of(parameter.dependence), found, rule_of(su_rule));
    return {text.value, text.su};
}

std::optional<std::string> exact_fraction(double value) { return crysta::exact_fraction(value); }

}  // namespace edi

#endif
