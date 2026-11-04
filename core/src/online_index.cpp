// SPDX-License-Identifier: BSD-3-Clause
#include "edi/online_index.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <map>
#include <regex>
#include <sstream>
#include <stdexcept>

#include "json.hpp"

namespace edi::online {
namespace {

std::string lower(std::string text) {
    for (char& c : text) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return text;
}

std::string trimmed(const std::string& text) {
    const auto begin = text.find_first_not_of(" \t\r\n");
    if (begin == std::string::npos) return {};
    const auto end = text.find_last_not_of(" \t\r\n");
    return text.substr(begin, end - begin + 1);
}

std::string without_spaces(const std::string& text) {
    std::string out;
    for (char c : text)
        if (!std::isspace(static_cast<unsigned char>(c))) out += c;
    return out;
}

bool contains_ci(const std::string& text, const std::string& needle) {
    return needle.empty() || lower(text).find(lower(needle)) != std::string::npos;
}

std::string text_member(const json::Value& object, const char* key) {
    const json::Value& value = object.get(key);
    if (value.is_null()) return {};
    return value.string(key);
}

const char* kKinds[] = {"structure", "experiment", "data", "project"};

bool known_kind(const std::string& kind) {
    return std::find(std::begin(kKinds), std::end(kKinds), kind) != std::end(kKinds);
}

// A file path inside a collection: segments of letters, digits, '.', '_', '~' and '-', each starting with a letter
// or digit, joined by single slashes. That excludes a leading slash, a drive or scheme (no ':'), backslashes,
// percent-encoding, '.' and '..' segments and hidden files, on every platform the path may be joined on.
bool relative_path(const std::string& path) {
    if (path.empty()) return false;
    bool start = true;
    for (const char ch : path) {
        const auto c = static_cast<unsigned char>(ch);
        if (ch == '/') {
            if (start) return false;  // a leading, doubled or trailing slash
            start = true;
            continue;
        }
        const bool word = std::isalnum(c) != 0;
        if (start ? !word : !(word || ch == '.' || ch == '_' || ch == '~' || ch == '-')) return false;
        start = false;
    }
    return !start;
}

// A formula's elements with their counts, summed when an element repeats.
std::map<std::string, double> counted_elements(const std::string& formula) {
    std::map<std::string, double> counts;
    std::size_t i = 0;
    const std::string text = formula;
    while (i < text.size()) {
        const unsigned char c = static_cast<unsigned char>(text[i]);
        if (std::isspace(c) || c == '-' || c == '(' || c == ')') {
            ++i;
            continue;
        }
        if (!std::isupper(c)) throw std::invalid_argument("not a chemical formula: " + formula);
        std::string symbol(1, text[i++]);
        if (i < text.size() && std::islower(static_cast<unsigned char>(text[i]))) symbol += text[i++];
        std::string number;
        while (i < text.size() && (std::isdigit(static_cast<unsigned char>(text[i])) || text[i] == '.')) number += text[i++];
        double count = 1.0;
        if (!number.empty()) {
            // Digits, optionally one dot and digits: "1.2.3" or "1." is refused, never cut down to a prefix.
            static const std::regex whole("[0-9]+(\\.[0-9]+)?");
            if (!std::regex_match(number, whole)) throw std::invalid_argument("not a chemical formula: " + formula);
            try {
                count = std::stod(number);
            } catch (const std::exception&) {
                throw std::invalid_argument("not a chemical formula: " + formula);
            }
        }
        counts[symbol] += count;
        if (!std::isfinite(counts[symbol])) throw std::invalid_argument("not a chemical formula: " + formula);
    }
    if (counts.empty()) throw std::invalid_argument("not a chemical formula: " + formula);
    return counts;
}

std::vector<std::string> hill_order(const std::map<std::string, double>& counts) {
    std::vector<std::string> symbols;
    for (const auto& [symbol, count] : counts) symbols.push_back(symbol);
    // std::map already sorts alphabetically; carbon and hydrogen move to the front when carbon is present.
    if (counts.count("C") != 0U) {
        std::stable_partition(symbols.begin(), symbols.end(), [](const std::string& s) { return s == "C"; });
        std::stable_partition(symbols.begin() + 1, symbols.end(), [](const std::string& s) { return s == "H"; });
    }
    return symbols;
}

std::string count_text(double count) {
    if (count == 1.0) return {};
    if (count == std::floor(count) && count >= 0 && count < 1e15) return std::to_string(static_cast<long long>(count));
    std::ostringstream out;
    out.precision(10);
    out << count;
    return out.str();
}

std::string percent_encoded(const std::string& text) {
    std::string out;
    for (unsigned char c : text) {
        if (std::isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') out += static_cast<char>(c);
        else {
            char hex[4];
            std::snprintf(hex, sizeof hex, "%%%02X", c);
            out += hex;
        }
    }
    return out;
}

// An element list as typed: commas or semicolons stand for spaces.
std::string element_words(const std::string& text) {
    std::string symbols;
    for (char c : text) symbols += (c == ',' || c == ';') ? ' ' : c;
    return symbols;
}

std::string cod_text(const json::Value& row, const char* key) {
    const json::Value& value = row.get(key);
    if (value.is_null()) return {};
    if (const auto* number = std::get_if<double>(&value.data)) return count_text(*number).empty() ? "1" : count_text(*number);
    return value.string(key);
}

}  // namespace

Index parse_index(const std::string& text) {
    json::Value root;
    try {
        root = json::parse(text);
    } catch (const std::exception& error) {
        throw std::invalid_argument(std::string("the index is not JSON: ") + error.what());
    }
    Index index;
    index.schema = text_member(root, "schema");
    if (index.schema != "edi-data-index/1") throw std::invalid_argument("the index schema is not edi-data-index/1");
    const json::Array& entries = root.at("entries").array("entries");
    std::map<std::string, bool> seen;
    for (const json::Value& item : entries) {
        Entry entry;
        entry.id = text_member(item, "id");
        entry.kind = text_member(item, "kind");
        if (entry.id.empty()) throw std::invalid_argument("an index entry has no id");
        if (!known_kind(entry.kind)) throw std::invalid_argument("entry " + entry.id + " has the unknown kind '" + entry.kind + "'");
        if (seen[entry.id]) throw std::invalid_argument("entry " + entry.id + " appears twice");
        seen[entry.id] = true;
        entry.name = text_member(item, "name");
        entry.description = text_member(item, "description");
        entry.formula = text_member(item, "formula");
        if (!entry.formula.empty()) entry.formula = hill_formula(entry.formula);
        const json::Value& elements = item.get("elements");
        if (!elements.is_null()) {
            std::string symbols;
            for (const json::Value& symbol : elements.array("elements")) symbols += symbol.string("elements") + ' ';
            entry.elements = formula_elements(symbols);
        } else if (!entry.formula.empty()) {
            entry.elements = formula_elements(entry.formula);
        }
        entry.space_group = text_member(item, "space_group");
        entry.radiation = text_member(item, "radiation");
        entry.technique = text_member(item, "technique");
        entry.instrument = text_member(item, "instrument");
        entry.facility = text_member(item, "facility");
        entry.source = text_member(item, "source");
        entry.authors = text_member(item, "authors");
        entry.journal = text_member(item, "journal");
        entry.volume = text_member(item, "volume");
        entry.first_page = text_member(item, "first_page");
        entry.year = text_member(item, "year");
        entry.doi = text_member(item, "doi");
        const json::Value& cell = item.get("cell");
        if (!cell.is_null()) {
            for (const json::Value& number : cell.array("cell")) {
                const double value = number.number("cell");
                if (!std::isfinite(value)) throw std::invalid_argument("entry " + entry.id + " has a cell value that is not a number");
                entry.cell.push_back(value);
            }
            if (entry.cell.size() != 6) throw std::invalid_argument("entry " + entry.id + " has a cell without six values");
        }
        for (const json::Value& file : item.at("files").array("files")) {
            File f;
            f.path = text_member(file, "path");
            f.format = text_member(file, "format");
            f.sha256 = text_member(file, "sha256");
            if (!relative_path(f.path)) throw std::invalid_argument("entry " + entry.id + " has a file path that is not relative: " + f.path);
            if (f.format.empty()) throw std::invalid_argument("entry " + entry.id + " has a file without a format: " + f.path);
            if (!f.sha256.empty() && (f.sha256.size() != 64 || f.sha256.find_first_not_of("0123456789abcdef") != std::string::npos))
                throw std::invalid_argument("entry " + entry.id + " has a sha256 that is not 64 hex digits: " + f.path);
            const json::Value& bytes = file.get("bytes");
            if (!bytes.is_null()) {
                // A whole number a double holds exactly (below 2^53) and a file can have; anything else is refused
                // before the conversion, which would otherwise be undefined for an out-of-range value.
                const double n = bytes.number("bytes");
                if (!(n >= 0) || n != std::floor(n) || n > 9007199254740992.0)
                    throw std::invalid_argument("entry " + entry.id + " has a size that is not a whole number of bytes: " + f.path);
                f.bytes = static_cast<long long>(n);
            }
            entry.files.push_back(std::move(f));
        }
        if (entry.files.empty()) throw std::invalid_argument("entry " + entry.id + " has no files");
        index.entries.push_back(std::move(entry));
    }
    return index;
}

std::string hill_formula(const std::string& formula) {
    const auto counts = counted_elements(formula);
    std::string out;
    for (const std::string& symbol : hill_order(counts)) {
        if (!out.empty()) out += ' ';
        out += symbol + count_text(counts.at(symbol));
    }
    return out;
}

std::vector<std::string> formula_elements(const std::string& formula) {
    return hill_order(counted_elements(formula));
}

std::vector<const Entry*> search(const Index& index, const std::string& kind, const Query& query) {
    std::vector<const Entry*> found;
    const std::string wanted_formula = trimmed(query.formula).empty() ? std::string() : hill_formula(query.formula);
    std::vector<std::string> formula_symbols;
    if (!wanted_formula.empty()) formula_symbols = formula_elements(wanted_formula);
    std::vector<std::string> wanted_elements;
    if (!trimmed(query.elements).empty()) wanted_elements = formula_elements(element_words(query.elements));
    const auto holds_all = [](const Entry& entry, const std::vector<std::string>& symbols) {
        if (entry.elements.empty()) return false;
        for (const std::string& symbol : symbols)
            if (std::find(entry.elements.begin(), entry.elements.end(), symbol) == entry.elements.end()) return false;
        return true;
    };
    std::vector<const Entry*> by_elements;  // formula matches by elements only, listed after the exact ones
    const std::string wanted_group = lower(without_spaces(query.space_group));
    const std::string wanted_id = lower(trimmed(query.id));
    for (const Entry& entry : index.entries) {
        if (entry.kind != kind) continue;
        if (!wanted_id.empty() && lower(entry.id) != wanted_id) continue;
        if (!contains_ci(entry.name, trimmed(query.name))) continue;
        bool exact_formula = true;
        if (!wanted_formula.empty() && entry.formula != wanted_formula) {
            if (query.formula_exact || !holds_all(entry, formula_symbols)) continue;
            exact_formula = false;
        }
        if (!wanted_elements.empty() && !holds_all(entry, wanted_elements)) continue;
        if (!wanted_group.empty() && lower(without_spaces(entry.space_group)) != wanted_group) continue;
        if (!contains_ci(entry.radiation, trimmed(query.radiation))) continue;
        if (!contains_ci(entry.technique, trimmed(query.technique))) continue;
        if (!contains_ci(entry.instrument, trimmed(query.instrument))) continue;
        (exact_formula ? found : by_elements).push_back(&entry);
    }
    found.insert(found.end(), by_elements.begin(), by_elements.end());
    return found;
}

std::vector<std::string> element_list(const std::string& text) { return formula_elements(element_words(text)); }

const Entry* find(const Index& index, const std::string& id) {
    for (const Entry& entry : index.entries)
        if (entry.id == id) return &entry;
    return nullptr;
}

std::string cod_search_url(const std::string& base, const Query& query) {
    std::string url = base;
    while (!url.empty() && url.back() == '/') url.pop_back();
    url += "/result?format=json";
    if (!trimmed(query.id).empty()) url += "&id=" + percent_encoded(trimmed(query.id));
    if (!trimmed(query.formula).empty()) url += "&formula=" + percent_encoded(hill_formula(query.formula));
    if (!trimmed(query.elements).empty()) {
        // The service takes el1 to el8; a longer list is sent in full up to eight and the caller filters the
        // answer with the whole query (search over the mapped entries), so no constraint is dropped.
        int n = 0;
        for (const std::string& symbol : formula_elements(element_words(query.elements))) {
            if (++n > 8) break;
            url += "&el" + std::to_string(n) + "=" + percent_encoded(symbol);
        }
    }
    if (!trimmed(query.space_group).empty()) url += "&spacegroup=" + percent_encoded(trimmed(query.space_group));
    // The Name field is COD's free-text search (its documented `text`: bibliographic data, common and systematic
    // names, the mineral), so the server applies it; the caller does not filter the answer's name again.
    if (!trimmed(query.name).empty()) url += "&text=" + percent_encoded(trimmed(query.name));
    return url;
}

std::string short_reference(const Entry& entry) {
    std::string out;
    const std::string authors = trimmed(entry.authors);
    if (!authors.empty()) {
        // "Smith, J.; Doe, A." or "Smith, J. and Doe, A.": the first surname, "et al." when others follow.
        const std::size_t end = authors.find_first_of(",;");
        std::string first = trimmed(authors.substr(0, end));
        const std::size_t and_at = first.find(" and ");
        if (and_at != std::string::npos) first = trimmed(first.substr(0, and_at));
        const bool several = authors.find(';') != std::string::npos || authors.find(" and ") != std::string::npos;
        out = first + (several ? " et al." : "");
    }
    std::string where = trimmed(entry.journal);
    if (!trimmed(entry.volume).empty()) where += (where.empty() ? "" : " ") + trimmed(entry.volume);
    if (!trimmed(entry.first_page).empty()) where += (where.empty() ? "" : ", ") + trimmed(entry.first_page);
    if (!where.empty()) out += (out.empty() ? "" : ", ") + where;
    if (!trimmed(entry.year).empty()) out += (out.empty() ? "" : " ") + ("(" + trimmed(entry.year) + ")");
    return out;
}

std::string reference_url(const Entry& entry) {
    const std::string doi = trimmed(entry.doi);
    return doi.empty() ? std::string() : "https://doi.org/" + doi;
}

std::vector<Entry> cod_entries(const std::string& text) {
    json::Value root;
    try {
        root = json::parse(text);
    } catch (const std::exception& error) {
        throw std::invalid_argument(std::string("the COD answer is not JSON: ") + error.what());
    }
    std::vector<Entry> entries;
    for (const json::Value& row : root.array("the COD answer")) {
        Entry entry;
        entry.id = cod_text(row, "file");
        if (entry.id.empty()) continue;
        entry.kind = "structure";
        for (const char* key : {"commonname", "mineral", "chemname", "title"}) {
            entry.name = trimmed(cod_text(row, key));
            if (!entry.name.empty()) break;
        }
        const std::string formula = trimmed(cod_text(row, "formula"));
        if (!formula.empty()) {
            try {
                entry.formula = hill_formula(formula);
            } catch (const std::invalid_argument&) {
                entry.formula = formula;
            }
        }
        entry.space_group = trimmed(cod_text(row, "sg"));
        bool cell = true;
        for (const char* key : {"a", "b", "c", "alpha", "beta", "gamma"}) {
            const std::string value = cod_text(row, key);
            try {
                if (value.empty()) throw std::invalid_argument(key);
                const double number = std::stod(value);
                if (!std::isfinite(number)) throw std::invalid_argument(key);
                entry.cell.push_back(number);
            } catch (const std::exception&) {
                cell = false;
                break;
            }
        }
        if (!cell) entry.cell.clear();
        if (!entry.formula.empty()) {
            try {
                entry.elements = formula_elements(entry.formula);
            } catch (const std::invalid_argument&) {
            }
        }
        entry.source = "COD " + entry.id;
        entry.authors = trimmed(cod_text(row, "authors"));
        entry.journal = trimmed(cod_text(row, "journal"));
        entry.volume = trimmed(cod_text(row, "volume"));
        entry.first_page = trimmed(cod_text(row, "firstpage"));
        entry.year = trimmed(cod_text(row, "year"));
        entry.doi = trimmed(cod_text(row, "doi"));
        File file;
        file.path = entry.id + ".cif";
        file.format = "cif";
        entry.files.push_back(std::move(file));
        entries.push_back(std::move(entry));
    }
    return entries;
}

}  // namespace edi::online
