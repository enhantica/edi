// SPDX-License-Identifier: BSD-3-Clause
// edi project I/O. A small STAR/CIF reader + `.edi` writer shaped after diffraction-lib's io module:
// `_category.item` scalar tags, `loop_` tables, line-segment background, joint-fit analysis.
// Self-contained (no gemmi/engine dependency) so parity with crysta's loader is proven by compared
// values, never shared code. Every failure is an `edi::IoError` and no partial model is returned.
// (ADR-0016) is the one exception: the identity-column table, the representable-id domain and the
// entity-path rule are crysta's, reached through the adapter — one decision for both products rather
// than a parity to prove.

#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/categories.hpp"
#include "edi/validation.hpp"

#include "edi/parameter_spec.hpp"
#include "edi/edits.hpp"
#include "edi/scan.hpp"
#include "edi/selectors.hpp"
#include "edi/worker.hpp"
#include "identity_bridge.hpp"  // Crysta's identity rules, via the adapter

#include <algorithm>
#include <stdexcept>
#include <array>
#include <cctype>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <locale>
#include <map>
#include <optional>
#include <random>
#include <regex>
#include <set>
#include <span>
#include <sstream>
#include <string>
#include <utility>
#include <vector>
#include <iomanip>

namespace fs = std::filesystem;

namespace edi {
namespace {

// ---- STAR/CIF parsing -----------------------------------------------------------------------------

// ADR-0016: the constructor is the one way a loop exists — parsed, translated from CIF or
// synthesised — and it checks every identity column the loop carries against crysta's one table
// (identity_bridge.hpp): each cell, decoded ONCE by the tokenizer, must be representable, and no
// two may be equal. `tags` and `rows` are immutable afterwards.
struct Loop {
    const std::vector<std::string> tags;
    const std::vector<std::vector<std::string>> rows;
    Loop(std::vector<std::string> tags_in, std::vector<std::vector<std::string>> rows_in,
         const std::string& where)
        : tags(std::move(tags_in)), rows(std::move(rows_in)) {
        for (std::size_t column = 0; column < tags.size(); ++column) {
            const char* category = detail::identity_category(tags[column]);
            if (category == nullptr) {
                continue;
            }
            const std::string context = "the " + tags[column] + " column";
            std::vector<std::string> ids;
            ids.reserve(rows.size());
            for (const std::vector<std::string>& row : rows) {
                if (column >= row.size()) {
                    continue;  // a ragged row is the parser's refusal
                }
                try {
                    detail::require_representable_id(row[column], category, context);
                } catch (const std::invalid_argument& error) {
                    fail_syntax(where, "unrepresentable-id", error.what());
                }
                ids.push_back(row[column]);
            }
            try {
                require_unique_ids(ids, category, context);
            } catch (const std::invalid_argument& error) {
                fail_domain(where, "duplicate-id", error.what());
            }
        }
    }
    // Column index of `tag`, or -1 if the loop does not declare it.
    int column(const std::string& tag) const {
        for (std::size_t index = 0; index < tags.size(); ++index) {
            if (tags[index] == tag) {
                return static_cast<int>(index);
            }
        }
        return -1;
    }
};

struct Block {
    std::string name;
    std::vector<std::pair<std::string, std::string>> items;  // ordered `_tag value`
    std::vector<Loop> loops;

    const std::string* find(const std::string& tag) const {
        for (const auto& item : items) {
            if (item.first == tag) {
                return &item.second;
            }
        }
        return nullptr;
    }
    const std::string& require(const std::string& tag, const std::string& where) const {
        const std::string* value = find(tag);
        if (value == nullptr) {
            fail_schema(where, "missing-required-tag", "missing required tag " + tag);
        }
        return *value;
    }
    // The first loop declaring `tag`, or nullptr.
    const Loop* loop_with(const std::string& tag) const {
        for (const auto& loop : loops) {
            if (loop.column(tag) >= 0) {
                return &loop;
            }
        }
        return nullptr;
    }
};

// What a non-regular-file entry at the record's name IS, for the refusal message — a
// directory, a symlink that does not resolve, a FIFO, a socket and a device are one class
// (present in the namespace, not a readable regular file), and each names itself.
std::string describe_non_regular_entry(const fs::file_status& followed,
                                       const fs::file_status& link) {
    switch (followed.type()) {
        case fs::file_type::directory:
            return "a directory";
        case fs::file_type::fifo:
            return "a FIFO";
        case fs::file_type::socket:
            return "a socket";
        case fs::file_type::block:
            return "a block device";
        case fs::file_type::character:
            return "a character device";
        case fs::file_type::not_found:
            return fs::is_symlink(link) ? "a symlink that does not resolve"
                                        : "an entry that vanished mid-examination";
        default:
            return "not a regular file";
    }
}

// RFC 3629 UTF-8 validation, exactly as strict as CPython's decoder (truncated sequences,
// bare continuation bytes, overlongs, surrogates and values past U+10FFFF all refuse) — a
// weaker check would let a crafted byte sequence through to leak the same far-from-cause
// RuntimeError this boundary exists to stop. Returns the offset of the first invalid byte,
// or nullopt for valid text.
std::optional<std::size_t> first_invalid_utf8_offset(const std::string& text) {
    const auto* bytes = reinterpret_cast<const unsigned char*>(text.data());
    const std::size_t size = text.size();
    std::size_t index = 0;
    while (index < size) {
        const unsigned char lead = bytes[index];
        std::size_t continuations = 0;
        unsigned char first_low = 0x80;
        unsigned char first_high = 0xBF;
        if (lead < 0x80) {
            ++index;
            continue;
        } else if (lead >= 0xC2 && lead <= 0xDF) {
            continuations = 1;
        } else if (lead == 0xE0) {
            continuations = 2;
            first_low = 0xA0;
        } else if (lead >= 0xE1 && lead <= 0xEC) {
            continuations = 2;
        } else if (lead == 0xED) {
            continuations = 2;
            first_high = 0x9F;  // no surrogates
        } else if (lead >= 0xEE && lead <= 0xEF) {
            continuations = 2;
        } else if (lead == 0xF0) {
            continuations = 3;
            first_low = 0x90;
        } else if (lead >= 0xF1 && lead <= 0xF3) {
            continuations = 3;
        } else if (lead == 0xF4) {
            continuations = 3;
            first_high = 0x8F;  // no values past U+10FFFF
        } else {
            return index;  // 0x80..0xC1 (bare continuation / overlong lead), 0xF5..0xFF
        }
        for (std::size_t k = 1; k <= continuations; ++k) {
            if (index + k >= size) {
                return index;  // truncated sequence
            }
            const unsigned char byte = bytes[index + k];
            const unsigned char low = (k == 1) ? first_low : 0x80;
            const unsigned char high = (k == 1) ? first_high : 0xBF;
            if (byte < low || byte > high) {
                return index;
            }
        }
        index += continuations + 1;
    }
    return std::nullopt;
}

std::string read_file(const std::string& path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        throw IoError("cannot open " + path);
    }
    std::ostringstream buffer;
    buffer << stream.rdbuf();
    return buffer.str();
}

bool is_space(char character) {
    return character == ' ' || character == '\t' || character == '\n' || character == '\r';
}

// ADR-0016: a token is decoded exactly once, here, and remembers whether it was delimited — a
// quoted `'data_x'`, `'_x'` or `'loop_'` is a VALUE, never a control word.
struct Token {
    std::string text;
    bool quoted = false;
};

std::vector<Token> tokenize(const std::string& text, const std::string& where) {
    std::vector<Token> tokens;
    std::size_t index = 0;
    const std::size_t size = text.size();
    while (index < size) {
        const char character = text[index];
        // A `;` in the first column of a line opens a CIF multi-line text field; its value runs to
        // the next line that begins with `;`. Consumed as a single token so published-CIF prose
        // (author lists, section titles with `~2~`/`^-^` markup) never leaks as stray tokens.
        if (character == ';' && (index == 0 || text[index - 1] == '\n')) {
            ++index;  // opening ';'
            std::string token;
            bool closed = false;
            while (index < size) {
                if (text[index] == '\n' && index + 1 < size && text[index + 1] == ';') {
                    index += 2;  // closing newline + ';'
                    closed = true;
                    break;
                }
                token += text[index++];
            }
            if (!closed) {
                fail_syntax(where, "unterminated-text-field", "unterminated ; text field");
            }
            tokens.push_back({token, true});
            continue;
        }
        if (is_space(character)) {
            ++index;
            continue;
        }
        if (character == '#') {  // comment to end of line
            while (index < size && text[index] != '\n') {
                ++index;
            }
            continue;
        }
        if (character == '\'' || character == '"') {  // quoted string
            const char quote = character;
            ++index;
            std::string token;
            bool closed = false;
            while (index < size) {
                if (text[index] == quote &&
                    (index + 1 >= size || is_space(text[index + 1]))) {
                    ++index;
                    closed = true;
                    break;
                }
                token += text[index++];
            }
            if (!closed) {
                fail_syntax(where, "unterminated-string", "unterminated quoted string");
            }
            tokens.push_back({token, true});
            continue;
        }
        std::string token;  // bare token
        while (index < size && !is_space(text[index])) {
            token += text[index++];
        }
        tokens.push_back({token, false});
    }
    return tokens;
}

bool starts_with(const std::string& text, const std::string& prefix) {
    return text.size() >= prefix.size() && text.compare(0, prefix.size(), prefix) == 0;
}

bool is_control(const Token& token) {
    if (token.quoted) {
        return false;  // A delimited token is always a value
    }
    const std::string& text = token.text;
    return text == "loop_" || (!text.empty() && text[0] == '_') || starts_with(text, "data_");
}

bool is_tag(const Token& token) {
    return !token.quoted && !token.text.empty() && token.text[0] == '_';
}

// Parse a file's single `data_` block. A second `data_` header ends the parse (these files are one
// block each). Any dangling tag/row (truncation) fails closed. `require_data` is relaxed for the
// analysis section, which is a headerless STAR body (no `data_` line).
Block parse_block(const std::string& text, const std::string& where, bool require_data = true) {
    const std::vector<Token> tokens = tokenize(text, where);
    Block block;
    bool have_data = false;
    std::size_t index = 0;
    const std::size_t size = tokens.size();
    while (index < size) {
        const Token& token = tokens[index];
        if (!token.quoted && starts_with(token.text, "data_")) {
            // A structure/experiment file is exactly one data_ block; the analysis body has none. A
            // second (or, for the headerless analysis, any) data_ header is unexpected — fail closed
            // rather than silently dropping the trailing block.
            if (have_data || !require_data) {
                fail_syntax(where, "unexpected-data-block",
                            "unexpected data_ block '" + token.text + "'");
            }
            block.name = token.text.substr(5);
            have_data = true;
            ++index;
        } else if (!token.quoted && token.text == "loop_") {
            ++index;
            std::vector<std::string> tags;
            std::vector<std::vector<std::string>> rows;
            while (index < size && is_tag(tokens[index])) {
                tags.push_back(tokens[index].text);
                ++index;
            }
            if (tags.empty()) {
                fail_syntax(where, "loop-without-tags", "loop_ with no header tags");
            }
            const std::size_t columns = tags.size();
            while (index < size && !is_control(tokens[index])) {
                std::vector<std::string> row;
                for (std::size_t column = 0; column < columns; ++column) {
                    if (index >= size || is_control(tokens[index])) {
                        fail_syntax(where, "truncated-loop-row", "truncated loop row for " + tags[0]);
                    }
                    row.push_back(tokens[index].text);
                    ++index;
                }
                rows.push_back(std::move(row));
            }
            block.loops.emplace_back(std::move(tags), std::move(rows), where);
        } else if (is_tag(token)) {
            const std::string tag = token.text;
            ++index;
            if (index >= size || is_control(tokens[index])) {
                fail_syntax(where, "tag-without-value", "tag " + tag + " has no value (truncated)");
            }
            block.items.emplace_back(tag, tokens[index].text);
            ++index;
        } else {
            fail_syntax(where, "unexpected-token", "unexpected token '" + token.text + "'");
        }
    }
    if (require_data && !have_data) {
        fail_syntax(where, "missing-data-block", "missing data_ block");
    }
    return block;
}

// ---- numeric + parameter parsing ------------------------------------------------------------------

int fractional_digits(const std::string& mantissa) {
    const std::size_t dot = mantissa.find('.');
    if (dot == std::string::npos) {
        return 0;
    }
    int digits = 0;
    for (std::size_t index = dot + 1; index < mantissa.size(); ++index) {
        if (std::isdigit(static_cast<unsigned char>(mantissa[index])) != 0) {
            ++digits;
        } else {
            break;
        }
    }
    return digits;
}

// Parse a complete numeric token into a double, locale-independently AND portably.
//
// An istringstream imbued with the classic ("C") locale always reads a '.' decimal separator
// whatever the process locale is, so the same project bytes parse identically under, say, a
// comma-decimal de_DE — the bug the previous std::stod implementation carried, since strtod follows
// LC_NUMERIC and would have rejected `449.2719` there. Requiring eof() means the WHOLE token was
// consumed, so trailing characters (including a `(su)` suffix, which is a model-parameter grammar and
// never valid in a data column) fail rather than silently truncating.
//
// Deliberately NOT std::from_chars: libc++ (Apple/macOS AppleClang) `= delete`s the floating-point
// overload, so that call does not compile there — it broke crysta's own macOS CI (PR #21), and edi
// ships osx-arm64/osx-64. This mirrors crysta's `parse_double` (src/core/edi.cpp) device-for-device,
// which also means the accepted grammar (leading '+', exponents, `.5`, `1.`) is identical by
// construction rather than by argument.
double to_double(const std::string& text, const std::string& where) {
    double value = 0.0;
    std::istringstream stream(text);
    stream.imbue(std::locale::classic());
    stream >> value;
    if (stream.fail() || !stream.eof()) {
        fail_schema(where, "invalid-number", "invalid number '" + text + "'");
    }
    if (!std::isfinite(value)) {
        fail_domain(where, "non-finite-number", "non-finite number '" + text + "'");
    }
    return value;
}

// Parse a value token, optionally carrying a `(uncertainty)` standard-uncertainty suffix. Mirrors
// crysta's reference loader (`src/core/edi.cpp::decode_su`) bit-for-bit, using the identical regex so
// the accepted grammar is the same by construction, not merely by argument: the MANTISSA
// `[+-]?(?:\d+\.?\d*|\.\d+)` accepts leading-dot (`.5(3)`) and trailing-dot (`18.(1)`) spellings — the
// FULL reference mantissa — and still rejects an in-bracket exponent `1.2e3(4)` (the reference
// rejects it too), which misses the mantissa and falls through to the fixed-value parse (which
// rejects the trailing bracket). The BRACKET carries three forms:
//   * all-digit su -> esd in units of the mantissa's last decimal (last-digit-scaled, UNCHANGED):
//     `3.89(2)` -> 0.02; `18.(1)` -> 1*10^0 -> 1.0; `.5(3)` -> 3*10^-1 -> 0.3;
//   * a su containing a '.' -> ABSOLUTE standard uncertainty (`383.2(1.2)` -> 1.2);
//   * empty bracket `value()` -> refinable (free) with no prior esd (std::nullopt), distinct from a
//     fixed value (esd 0.0, not free) and a zero-esd refined `value(0)`.
// A bare token (no bracket) is fixed: present esd 0.0, not free — preserving the public esd==0.0
// save->load fixed point. `to_double` rejects non-finite at the boundary.
Parameter parse_parameter(const std::string& token, const std::string& where) {
    static const std::regex pattern(R"(^([+-]?(?:\d+\.?\d*|\.\d+))\((\d+|\d*\.\d+|\d+\.)?\)$)");
    std::smatch match;
    if (std::regex_match(token, match, pattern)) {
        const std::string mantissa = match[1].str();
        const std::string uncertainty = match[2].str();
        const double value = to_double(mantissa, where);
        if (uncertainty.empty()) {
            return Parameter(value, std::nullopt, true);  // refinable, no prior esd
        }
        // Integer su: DIVIDE by 10^ndec (not multiply by 10^-ndec) so a single correctly-rounded op
        // matches crysta/the reference bit-for-bit ('.5(3)' -> 3/10 = 0.3, not 3*0.1 = 0.3000...04).
        const double esd = uncertainty.find('.') != std::string::npos
                               ? to_double(uncertainty, where)  // decimal su -> absolute
                               : to_double(uncertainty, where) /
                                     std::pow(10.0, fractional_digits(mantissa));  // last-digit-scaled
        return Parameter(value, esd, true);
    }
    // No (well-formed) bracket: a bare fixed value; a malformed bracket also lands here and to_double
    // rejects it as an invalid number.
    return Parameter(to_double(token, where), 0.0, false);
}

// , review-9 F13: a cell the engine's metric refuses is a physical domain it refuses at every
// calculation, fit and save, never an editing range a fit may leave, so both readers refuse it at
// load by crysta's own check (CellMetric, through the adapter), in its words.
void require_realizable_cell(const Cell& cell, const std::string& where) {
    const std::string detail =
        detail::cell_domain_message(cell.length_a.value, cell.length_b.value, cell.length_c.value,
                                    cell.angle_alpha.value, cell.angle_beta.value, cell.angle_gamma.value);
    if (!detail.empty()) {
        fail_domain(where, "cell-geometry", "cell is not geometrically realizable (" + detail + ")");
    }
}

std::string cell_value(const Block& block, const std::string& tag, const std::string& where) {
    return block.require(tag, where);
}

// A parsed value outside its spec's admissible range LOADS. A fit keeps such a value and every save
// writes it, so refusing it would make a fitted project unopenable. A malformed or non-finite number
// is still refused (to_double, parse_edi_double); load_project names each value outside its range in
// one warning, and the app marks it red. The admissible range keeps binding a value a user types
// (assign_value, the Python setter): it describes the input, not what a fit may return.

// The single write path from a parsed token onto a spec-carrying model field. Preserves the field's
// spec (a parsed Parameter is bare). A value outside the spec's range is admitted (above).
void read_into(Parameter& field, const Parameter& parsed, const std::string& where) {
    (void)where;
    const ParameterSpec* spec = field.spec;
    field = parsed;
    field.spec = spec;
}

// Spec-driven in-place read for the `.edi` reader: the field's own attached spec names the tag,
// so the spec table is the single source of the serialized spelling. A spec-less field fails
// closed: its tag would be underivable, and plan I6 makes a Project-reachable spec-less
// Parameter a defect anyway.
void read_spec_into(const Block& block, Parameter& field, const std::string& where) {
    if (field.spec == nullptr) {
        throw IoError(where + ": internal: field carries no ParameterSpec to derive its tag from");
    }
    read_into(field, parse_parameter(block.require(field.spec->edi_names[0], where), where), where);
}

// The two spec-driven reads for presence-CREATED parameters (the CW scalars and the optional
// absorption pair), which have no pre-attached field to read into. Tag from the spec's canonical
// first edi name; parsed value range-checked exactly as read_into does.
Parameter require_spec_parameter(const Block& block, const ParameterSpec& spec,
                                 const std::string& where) {
    Parameter parameter = parse_parameter(block.require(spec.edi_names[0], where), where);
    parameter.spec = &spec;
    return parameter;
}

std::optional<Parameter> find_spec_parameter(const Block& block, const ParameterSpec& spec,
                                             const std::string& where) {
    const std::string* token = block.find(spec.edi_names[0]);
    if (token == nullptr) {
        return std::nullopt;
    }
    Parameter parameter = parse_parameter(*token, where);
    parameter.spec = &spec;
    return parameter;
}

// ---- .edi schema helpers --------------------------------------------------------------------------

void require_edi_schema(const Block& block, const std::string& where) {
    const std::string& version = block.require("_edi.schema_version", where);
    // Schema 2 is the vocabulary epoch — the four renamed `_peak.*` TOF size/strain tags and
    // the typed `_experiment_type.*` axes. A v1 file fails here with one clear message rather
    // than a tag-by-tag trickle. Schema 3 adds the _fit_parameter start-state loop and the
    // _scattering_length structure loop; schema-2 files stay readable (additive,
    // presence-tracked). Schema 4 is an experiment file crysta saved with its computed `_data`
    // columns, `_refln` and their provenance. Those are crysta's to trust: edi reads the file's
    // inputs as before, carries `_refln` read-only, and takes computed values only from a
    // calculation.
    if (version != "2" && version != "3" && version != "4") {
        fail_schema(where, "unsupported-schema-version",
                    "unsupported _edi.schema_version '" + version +
                        "' (this build reads schema 2, 3 and 4)");
    }
}

const std::string& loop_cell(const Loop& loop, const std::vector<std::string>& row,
                             const std::string& tag, const std::string& where) {
    const int column = loop.column(tag);
    if (column < 0) {
        fail_schema(where, "missing-loop-column", "loop is missing required column " + tag);
    }
    return row[static_cast<std::size_t>(column)];
}

// ---- unknown-tag policy -------------------------------------------------------------------

// The reference's unknown-tag rule is TWO-SIDED, and edi mirrors both halves:
//   * a tag in a dictionary-covered category that is not a known tag  -> ERROR (a typo like
//     `_peak.not_a_real_tag` must not load silently, which is what edi did);
//   * a tag in an unmodelled category (`_data`, `_diffrn`, `_experiment_type`, `_geom`,
//     `_space_group`, `_edi`, `_joint_fit`, `_fitting_mode`, `_excluded_region`) -> IGNORED.
// Rejecting the second group would make edi stricter than the reference and refuse projects it
// fits — a divergent dialect, which is exactly what the parity claim forbids.
//
// The allowlist is the reference dictionary's own tags plus its tolerated non-parameter tags,
// transcribed from `crysta/data/dictionary/parameters.tsv` at the pinned commit. It was verified to
// reject nothing across every `.edi` in the acceptance vehicle and in edi's fixtures.
const std::set<std::string>& covered_categories() {
    static const std::set<std::string> categories{"absorption", "atom_site",        "background",
                                                  "cell",       "data_range",       "experiment_type",
                                                  "instrument",  "linked_structure",
                                                  "fit_parameter", "peak", "preferred_orientation",
                                                  "scattering_length", "scattering_source"};
    return categories;
}

const std::set<std::string>& known_covered_tags() {
    static const std::set<std::string> tags{
        // _absorption
        "_absorption.abscor1", "_absorption.abscor2", "_absorption.mu_r", "_absorption.type",
        // _atom_site
        "_atom_site.adp_iso", "_atom_site.adp_type", "_atom_site.fract_x", "_atom_site.fract_y",
        "_atom_site.fract_z", "_atom_site.id", "_atom_site.multiplicity", "_atom_site.occupancy",
        "_atom_site.type_symbol", "_atom_site.wyckoff_letter",
        // _background
        "_background.coef", "_background.id", "_background.intensity", "_background.order",
        "_background.origin", "_background.position", "_background.type", "_background.x_max",
        "_background.x_min",
        // _cell
        "_cell.angle_alpha", "_cell.angle_beta", "_cell.angle_gamma", "_cell.length_a",
        "_cell.length_b", "_cell.length_c",
        // _data_range (the declared calculation grid, crysta's
        // `_min/_max/_step` spelling — now a modelled category, so a typo fails closed)
        "_data_range.time_of_flight_max", "_data_range.time_of_flight_min",
        "_data_range.time_of_flight_step", "_data_range.two_theta_max",
        "_data_range.two_theta_min", "_data_range.two_theta_step",
        // _experiment_type (the four typed axes)
        "_experiment_type.beam_mode", "_experiment_type.radiation_probe",
        "_experiment_type.sample_form", "_experiment_type.scattering_type",
        // _instrument
        "_instrument.calib_d_to_tof_linear", "_instrument.calib_d_to_tof_offset",
        "_instrument.calib_d_to_tof_quadratic", "_instrument.calib_d_to_tof_reciprocal",
        "_instrument.calib_sample_displacement", "_instrument.calib_sample_transparency",
        "_instrument.calib_twotheta_offset", "_instrument.setup_monochromator_twotheta",
        "_instrument.setup_polarization_coefficient", "_instrument.setup_twotheta_bank",
        "_instrument.setup_wavelength",
        // _linked_structure
        "_linked_structure.enabled", "_linked_structure.scale", "_linked_structure.structure_id",
        // _preferred_orientation (diffraction-lib's category, CW only)
        "_preferred_orientation.index_h", "_preferred_orientation.index_k",
        "_preferred_orientation.index_l", "_preferred_orientation.march_r",
        "_preferred_orientation.march_random_fract", "_preferred_orientation.structure_id",
        // _scattering_source (the X-ray source selectors;,
        // crysta: the neutron one)
        "_scattering_source.neutron_scattering_length",
        "_scattering_source.xray_dispersion", "_scattering_source.xray_form_factor",
        // _fit_parameter (the persisted pre-fit snapshot undo restores from)
        "_fit_parameter.id", "_fit_parameter.start_value", "_fit_parameter.start_uncertainty",
        "_fit_parameter.start_tied",
        // _scattering_length (the structure's declared per-element coherent scattering
        // lengths, fm — the model home of `Structure.scattering_lengths_fm`; absent = the
        // built-in table applies by element lookup)
        "_scattering_length.length_fm", "_scattering_length.type_symbol",
        // _peak
        "_peak.broad_gauss_sigma_0", "_peak.broad_gauss_sigma_1", "_peak.broad_gauss_sigma_2",
        "_peak.broad_gauss_size", "_peak.broad_gauss_strain", "_peak.broad_gauss_u",
        "_peak.broad_gauss_v", "_peak.broad_gauss_w", "_peak.broad_lorentz_gamma_0",
        "_peak.broad_lorentz_gamma_1", "_peak.broad_lorentz_gamma_2", "_peak.broad_lorentz_size",
        "_peak.broad_lorentz_strain", "_peak.broad_lorentz_x", "_peak.broad_lorentz_y",
        "_peak.mixing_eta_0", "_peak.mixing_eta_1", "_peak.cutoff_fwhm", "_peak.decay_beta_0", "_peak.decay_beta_1", "_peak.rise_alpha_0",
        "_peak.rise_alpha_1", "_peak.type",
        // The CW asymmetry coefficients (read only on the rung that carries them).
        "_peak.asym_beba_a0", "_peak.asym_beba_a1", "_peak.asym_beba_b0", "_peak.asym_beba_b1",
        "_peak.asym_beba_limit",
        "_peak.asym_fcj_1", "_peak.asym_fcj_2",
    };
    return tags;
}

std::string tag_category(const std::string& tag) {
    const std::size_t dot = tag.find('.');
    if (tag.empty() || tag[0] != '_' || dot == std::string::npos) {
        return "";
    }
    return tag.substr(1, dot - 1);
}

void check_known_tag(const std::string& tag, const std::string& where) {
    const std::string category = tag_category(tag);
    if (!covered_categories().contains(category)) {
        return;  // unmodelled category — not edi's schema to enforce, mirroring the reference.
    }
    if (!known_covered_tags().contains(tag)) {
        fail_schema(where, "unknown-tag", "unknown tag '" + tag + "' in category '" + category + "'");
    }
}

// Every scalar item and every loop column of a block, checked against the policy above.
void validate_known_tags(const Block& block, const std::string& where) {
    for (const auto& item : block.items) {
        check_known_tag(item.first, where);
    }
    for (const Loop& loop : block.loops) {
        for (const std::string& tag : loop.tags) {
            check_known_tag(tag, where);
        }
    }
}

// ---- structure / experiment / analysis loaders ----------------------------------------------------

Structure structure_from_block(const Block& block, const std::string& where) {
    require_edi_schema(block, where);
    validate_known_tags(block, where);
    Structure structure;
    structure.name = block.name;
    structure.space_group.name_h_m = block.require("_space_group.name_h_m", where);
    // Optional ITA coordinate-system code: carried as the raw token. Absent => empty => name-only
    // resolution.
    if (const std::string* code = block.find("_space_group.coord_system_code")) {
        structure.space_group.coord_system_code = *code;
    }
    // Optional IUCr IT number: a positive integer, presence-tracked. `_space_group` is an
    // unmodelled category for the tag policy, so the tag needs no registry entry.
    if (const std::string* number = block.find("_space_group.it_number")) {
        std::size_t consumed = 0;
        int value = 0;
        try {
            value = std::stoi(*number, &consumed);
        } catch (const std::exception&) {
            consumed = 0;
        }
        if (consumed != number->size() || value < 1 || value > 230) {
            fail_schema(where, "invalid-it-number",
                        "_space_group.it_number '" + *number + "' is not an IT number (1..230)");
        }
        structure.space_group.it_number = value;
    }
    read_into(structure.cell.length_a,
              parse_parameter(cell_value(block, spec::cell_length_a.edi_names[0], where), where),
              where);
    read_into(structure.cell.length_b,
              parse_parameter(cell_value(block, spec::cell_length_b.edi_names[0], where), where),
              where);
    read_into(structure.cell.length_c,
              parse_parameter(cell_value(block, spec::cell_length_c.edi_names[0], where), where),
              where);
    read_into(structure.cell.angle_alpha,
              parse_parameter(cell_value(block, spec::cell_angle_alpha.edi_names[0], where), where),
              where);
    read_into(structure.cell.angle_beta,
              parse_parameter(cell_value(block, spec::cell_angle_beta.edi_names[0], where), where),
              where);
    read_into(structure.cell.angle_gamma,
              parse_parameter(cell_value(block, spec::cell_angle_gamma.edi_names[0], where), where),
              where);
    require_realizable_cell(structure.cell, where);

    // The bond-generation cutoffs, presence-tracked — an absent tag stays unset and takes crysta's
    // default. `_geom` is an unmodelled category for the tag policy, so the two tags need no
    // registry entry; a declared value is finite and >= 0.
    for (const auto& [tag, field] :
         {std::pair<const char*, detail::Written<std::optional<double>> Geom::*>{
              "_geom.min_bond_distance_cutoff", &Geom::min_bond_distance_cutoff},
          {"_geom.bond_distance_inc", &Geom::bond_distance_inc}}) {
        if (const std::string* text = block.find(tag)) {
            const double value = to_double(*text, where);
            if (value < 0.0) {
                fail_domain(where, "out-of-range",
                            std::string(tag) + " '" + *text + "' must be finite and >= 0");
            }
            structure.geom.*field = value;
        }
    }

    const Loop* loop = block.loop_with("_atom_site.id");
    if (loop == nullptr) {
        fail_schema(where, "missing-atom-site-loop", "missing _atom_site loop");
    }
    // The adp_iso interpretation is KEYED on `_atom_site.adp_type` where the column exists —
    // absent or `Biso` reads as B (unchanged behaviour); `Uiso` converts by
    // B = 8*pi^2*U at this boundary; an anisotropic type refuses (edi models isotropic ADP only,
    // and tolerating-then-misreading the value as B was a silent misinterpretation).
    const int adp_type_column = loop->column("_atom_site.adp_type");
    for (const auto& row : loop->rows) {
        AtomSite site;
        site.id = loop_cell(*loop, row, "_atom_site.id", where);
        site.type_symbol = loop_cell(*loop, row, "_atom_site.type_symbol", where);
        const int wyckoff = loop->column("_atom_site.wyckoff_letter");
        if (wyckoff >= 0) {
            site.wyckoff_letter = row[static_cast<std::size_t>(wyckoff)];
        }
        read_into(site.fract_x,
                  parse_parameter(
                      loop_cell(*loop, row, spec::atom_site_fract_x.edi_names[0], where), where),
                  where);
        read_into(site.fract_y,
                  parse_parameter(
                      loop_cell(*loop, row, spec::atom_site_fract_y.edi_names[0], where), where),
                  where);
        read_into(site.fract_z,
                  parse_parameter(
                      loop_cell(*loop, row, spec::atom_site_fract_z.edi_names[0], where), where),
                  where);
        read_into(site.occupancy,
                  parse_parameter(
                      loop_cell(*loop, row, spec::atom_site_occupancy.edi_names[0], where), where),
                  where);
        Parameter adp = parse_parameter(
            loop_cell(*loop, row, spec::atom_site_adp_iso.edi_names[0], where), where);
        if (adp_type_column >= 0) {
            const std::string& adp_type = row[static_cast<std::size_t>(adp_type_column)];
            if (adp_type == "Uiso") {
                constexpr double pi = 3.141592653589793238;
                adp.value *= 8.0 * pi * pi;
                if (adp.uncertainty) {
                    adp.uncertainty = *adp.uncertainty * (8.0 * pi * pi);
                }
                site.adp_type = "Biso";  // the STORED representation: B after conversion
            } else if (adp_type == "Biso") {
                site.adp_type = "Biso";
            } else if (adp_type != "." && !adp_type.empty()) {
                fail_domain(where, "unreadable-adp-type",
                            "_atom_site.adp_type '" + adp_type +
                                "' is not readable here: edi models isotropic ADP stored as B "
                                "(accepted: Biso, Uiso; anisotropic rows cannot be reduced)");
            }
        }
        read_into(site.adp_iso, adp, where);
        structure.atom_sites.push_back(std::move(site));
    }

    // The optional declared scattering-length map (`Structure.scattering_lengths_fm`). Absent
    // means "not set" — the built-in table applies by element lookup; there is no other route
    // for the value to arrive. A duplicate element declaration fails closed rather than
    // silently letting the last row win.
    if (const Loop* lengths = block.loop_with("_scattering_length.type_symbol")) {
        std::map<std::string, double> declared;
        for (const auto& row : lengths->rows) {
            const std::string& symbol =
                loop_cell(*lengths, row, "_scattering_length.type_symbol", where);
            const double length_fm =
                to_double(loop_cell(*lengths, row, "_scattering_length.length_fm", where), where);
            if (!declared.emplace(symbol, length_fm).second) {
                fail_schema(where, "duplicate-scattering-length",
                            "_scattering_length loop declares '" + symbol + "' more than once");
            }
        }
        structure.scattering_lengths_fm = std::move(declared);
    }
    return structure;
}

// True if `tag` is present in the block as a scalar item or as a loop column. Mirrors the
// diffraction-lib shape source's `_has_tag` so the selector/body consistency check sees body fields
// whether they were written as scalars or loop columns.
bool block_has_tag(const Block& block, const std::string& tag) {
    return block.find(tag) != nullptr || block.loop_with(tag) != nullptr;
}

// The five Jorgensen-von-Dreele Lorentzian coefficients. Present exactly on a
// `tof-jorgensen-von-dreele` experiment: required there (a truncated JvD block must fail closed
// rather than silently refine a zeroed Lorentzian) and forbidden on a pure `tof-jorgensen` block,
// where they would have no profile effect. Order matches the write order and crysta's peak[9..13].
// Tag spellings sourced from the spec table: changing a spec's canonical edi name moves the
// serialized contract with it, here as everywhere.
const std::array<const char*, 5> kLorentzTags{{spec::peak_broad_lorentz_gamma_0.edi_names[0],
                                               spec::peak_broad_lorentz_gamma_1.edi_names[0],
                                               spec::peak_broad_lorentz_gamma_2.edi_names[0],
                                               spec::peak_broad_lorentz_size.edi_names[0],
                                               spec::peak_broad_lorentz_strain.edi_names[0]}};
constexpr const char* kPeakJorgensen = "tof-jorgensen";
constexpr const char* kPeakJvd = "tof-jorgensen-von-dreele";

// ---- experiment families -----------------------------------------------------------------
//
// The closed `_peak.type` token table, mirroring crysta's shipped grammar — the
// token→(kind, implemented) rows. The default CW
// profile is the TCH pseudo-Voigt. `implemented: false` means recognised-but-refused BY NAME: the
// token is a known file, not a typo, and loading it is refused naming the token.
constexpr const char* kPeakCwlDefault = "cwl-tch-pseudo-voigt";
constexpr const char* kPeakTofPseudoVoigt = "tof-pseudo-voigt";
constexpr const char* kBeamModeTof = "time-of-flight";
constexpr const char* kBeamModeCwl = "constant wavelength";  // WITH a space — quoted on write

struct PeakTypeRow {
    BeamModeEnum mode;
    bool implemented;
};

// Registration-live (seam 20 / I15): seeded with the shipped grammar, extended at runtime by
// edi::register_peak_type (the Python registration seam), so the loader accepts a registered
// token without a rebuild — crysta's known_peak_types() pattern, mirrored.
std::map<std::string, PeakTypeRow>& peak_type_rows() {
    static std::map<std::string, PeakTypeRow> rows{
        {kPeakJorgensen, {BeamModeEnum::TIME_OF_FLIGHT, true}},
        {kPeakJvd, {BeamModeEnum::TIME_OF_FLIGHT, true}},
        {"cwl-gaussian", {BeamModeEnum::CONSTANT_WAVELENGTH, true}},
        {"cwl-lorentzian", {BeamModeEnum::CONSTANT_WAVELENGTH, true}},
        {"cwl-pseudo-voigt", {BeamModeEnum::CONSTANT_WAVELENGTH, true}},
        {"cwl-pseudo-voigt-berar-baldinozzi", {BeamModeEnum::CONSTANT_WAVELENGTH, true}},
        {"cwl-tch-pseudo-voigt", {BeamModeEnum::CONSTANT_WAVELENGTH, true}},
        {"cwl-tch-pseudo-voigt-fcj", {BeamModeEnum::CONSTANT_WAVELENGTH, true}},
        {kPeakTofPseudoVoigt, {BeamModeEnum::TIME_OF_FLIGHT, true}},
    };
    return rows;
}

// The per-family tag registry: every CW profile requires U, V, W and the two instrument scalars, and
// the TCH pair also X, Y (crysta's required family-`cwl` rows, by profile); the forbidden set on each family is the FULL other family — a
// tag on a type that does not consume it is a hard error naming both tags (the
// `tof-jorgensen`-forbids-Lorentzian idiom, generalised; verified against crysta's loader, which
// refuses e.g. `_peak.broad_gauss_size` on a CW block as family-crossing). `_peak.cutoff_fwhm`
// is family-NEUTRAL (not a dictionary parameter row; both context builders consume it) and appears
// in neither set.
constexpr std::array<const char*, 3> kCwlPeakTags{{"_peak.broad_gauss_u", "_peak.broad_gauss_v",
                                                   "_peak.broad_gauss_w"}};
constexpr std::array<const char*, 2> kCwlLorentzTags{{"_peak.broad_lorentz_x",
                                                      "_peak.broad_lorentz_y"}};
constexpr std::array<const char*, 2> kCwlInstrumentTags{{"_instrument.setup_wavelength",
                                                         "_instrument.calib_twotheta_offset"}};
constexpr std::array<const char*, 19> kTofFamilyTags{{
    "_peak.rise_alpha_0", "_peak.rise_alpha_1", "_peak.decay_beta_0", "_peak.decay_beta_1",
    "_peak.broad_gauss_sigma_0", "_peak.broad_gauss_sigma_1", "_peak.broad_gauss_sigma_2",
    "_peak.broad_gauss_size", "_peak.broad_gauss_strain", "_peak.broad_lorentz_gamma_0",
    "_peak.broad_lorentz_gamma_1", "_peak.broad_lorentz_gamma_2", "_peak.broad_lorentz_size",
    "_peak.broad_lorentz_strain", "_instrument.setup_twotheta_bank",
    "_instrument.calib_d_to_tof_offset", "_instrument.calib_d_to_tof_linear",
    "_instrument.calib_d_to_tof_quadratic", "_instrument.calib_d_to_tof_reciprocal",
}};
constexpr std::array<const char*, 13> kCwlFamilyTags{{
    "_peak.broad_gauss_u", "_peak.broad_gauss_v", "_peak.broad_gauss_w", "_peak.broad_lorentz_x",
    "_peak.broad_lorentz_y", "_peak.mixing_eta_0", "_peak.mixing_eta_1",
    "_instrument.setup_wavelength", "_instrument.calib_twotheta_offset",
    "_instrument.calib_sample_displacement", "_instrument.calib_sample_transparency",
    "_instrument.setup_polarization_coefficient", "_instrument.setup_monochromator_twotheta",
}};

const char* family_name(BeamModeEnum mode) {
    return mode == BeamModeEnum::CONSTANT_WAVELENGTH ? "constant-wavelength" : "time-of-flight";
}

// Resolve the experiment kind from the `_peak.type` family, cross-validated against
// `_experiment_type.beam_mode` per the shipped four-case matrix: both matching
// pairs accepted; either valid beam token against the other family rejected naming BOTH tags; any
// other beam token a bad enum. An absent `beam_mode` is NOT an error (the kind comes from the
// `_peak.type` family alone — how every pre-CW file loads), and an absent `_peak.type` keeps the
// historical `tof-jorgensen` default.
struct ResolvedExperimentKind {
    std::string peak_type;                // the verbatim token (for error text and family checks)
    std::optional<std::string> declared;  // the token iff the block carried `_peak.type`
    BeamModeEnum mode;
    bool beam_declared;  // whether the block carried `_experiment_type.beam_mode`
};

ResolvedExperimentKind resolve_experiment_kind(const Block& block, const std::string& where) {
    const std::string* type_item = block.find("_peak.type");
    const std::string peak_type = type_item != nullptr ? *type_item : kPeakJorgensen;
    const auto& rows = peak_type_rows();
    const auto found_row = rows.find(peak_type);
    if (found_row == rows.end()) {
        fail_schema(where, "unsupported-peak-type",
                    "unsupported _peak.type '" + peak_type +
                      "' (not a shipped or registered profile token)");
    }
    const PeakTypeRow* row = &found_row->second;
    if (!row->implemented) {
        // Recognised-but-refused, by name (Fork 3 (a)): a reserved rung is a known token this build
        // cannot compute — never silently painted as the symmetric rung 0.
        fail_domain(where, "reserved-peak-type",
                    "_peak.type '" + peak_type +
                        "' is a reserved profile type this build cannot compute yet");
    }
    const std::string* beam = block.find("_experiment_type.beam_mode");
    if (beam != nullptr) {
        if (*beam != kBeamModeTof && *beam != kBeamModeCwl) {
            fail_schema(where, "unknown-beam-mode",
                        "_experiment_type.beam_mode '" + *beam +
                            "' is not a known beam mode for _peak.type '" + peak_type +
                          "' (expected 'time-of-flight' or 'constant wavelength')");
        }
        const BeamModeEnum beam_mode =
            *beam == kBeamModeCwl ? BeamModeEnum::CONSTANT_WAVELENGTH : BeamModeEnum::TIME_OF_FLIGHT;
        if (beam_mode != row->mode) {
            fail_domain(where, "beam-mode-contradicts-peak-type",
                        "_experiment_type.beam_mode '" + *beam +
                            "' contradicts _peak.type '" + peak_type + "', which is a " +
                          std::string(family_name(row->mode)) + " profile");
        }
    }
    return {peak_type, type_item != nullptr ? std::optional<std::string>(peak_type) : std::nullopt,
            row->mode, beam != nullptr};
}

// Enforce the .edi implementation selectors before decoding an experiment body — the per-family
// tag registry, generalising the hard-coded JvD/Lorentz check: required / forbidden tag sets are
// per experiment family, a family crossing is a hard error naming both tags, and one background
// implementation (line-segment) is shared by both families. An unknown or reserved
// `_peak.type` was already refused by resolve_experiment_kind; a selector/body mismatch here fails
// closed rather than returning a plausible model — the packet's fail-closed format-detection
// contract and diffraction-lib's edi/serialize.py `_validate_selector_body_consistency` shape,
// restricted to the implementations edi-core reads.
void validate_experiment_selectors(const Block& block, const std::string& peak_type,
                                   BeamModeEnum mode, const std::string& where) {
    // A `_peak` item is one value. Written as a loop column it would be dropped on read, and a
    // profile's declaration would vanish before the rules below see it.
    for (const Loop& loop : block.loops) {
        for (const std::string& tag : loop.tags) {
            if (tag.rfind("_peak.", 0) == 0) {
                fail_schema(where, "peak-item-in-loop", tag + " is a scalar item, not a loop column");
            }
        }
    }
    // Family crossings, both directions: a tag of the OTHER family on this block is a hard error
    // naming both the tag and the selector it contradicts (verified to mirror crysta's b9aee906
    // loader, whose forbidden set is the full other family — size_g/strain_g included).
    const auto forbid_family = [&](const char* tag, const char* other_family) {
        if (block_has_tag(block, tag)) {
            fail_domain(where, "tag-of-other-family",
                        std::string("tag ") + tag + " belongs to the " + other_family +
                            " family and cannot appear with _peak.type '" + peak_type + "'");
        }
    };
    if (mode == BeamModeEnum::CONSTANT_WAVELENGTH) {
        for (const char* tag : kTofFamilyTags) {
            forbid_family(tag, "time-of-flight");
        }
        // Every CW profile requires U, V, W and the two `_instrument` CW scalars, the TCH pair X
        // and Y too — the same requires-idiom as the JvD Lorentzian block below. A `_peak`
        // parameter of another CW profile is refused by name with the type: each profile carries
        // only its own parameters.
        const CwlProfileSlots slots = cwl_profile_slots(peak_type);
        for (const char* tag : kCwlPeakTags) {
            if (!block_has_tag(block, tag)) {
                fail_schema(where, "missing-family-tag",
                            "_peak.type '" + peak_type + "' requires " + tag);
            }
        }
        for (const char* tag : kCwlLorentzTags) {
            if (slots.lorentz_xy && !block_has_tag(block, tag)) {
                fail_schema(where, "missing-family-tag",
                            "_peak.type '" + peak_type + "' requires " + tag);
            }
        }
        const auto forbid_profile = [&](const char* tag, bool carried) {
            if (!carried && block_has_tag(block, tag)) {
                fail_domain(where, "tag-of-other-profile",
                            std::string("tag ") + tag + " is not a parameter of _peak.type '" +
                                peak_type + "': each profile carries only its own parameters");
            }
        };
        for (const char* tag : kCwlLorentzTags) {
            forbid_profile(tag, slots.lorentz_xy);
        }
        for (const char* tag : {"_peak.mixing_eta_0", "_peak.mixing_eta_1"}) {
            forbid_profile(tag, slots.mixing_eta);
        }
        for (const char* tag : {"_peak.asym_fcj_1", "_peak.asym_fcj_2"}) {
            forbid_profile(tag, slots.fcj);
        }
        for (const char* tag : {"_peak.asym_beba_a0", "_peak.asym_beba_b0", "_peak.asym_beba_a1",
                                "_peak.asym_beba_b1", "_peak.asym_beba_limit"}) {
            forbid_profile(tag, slots.beba);
        }
        for (const char* tag : kCwlInstrumentTags) {
            if (!block_has_tag(block, tag)) {
                fail_schema(where, "missing-family-tag",
                            "_peak.type '" + peak_type + "' requires " + tag);
            }
        }
    } else {
        for (const char* tag : kCwlFamilyTags) {
            forbid_family(tag, "constant-wavelength");
        }
        // Selector/body consistency for the Lorentzian block: the JvD selector requires every
        // coefficient. A plain-jorgensen block may CARRY the Lorentz tags — the canonical
        // writer emits the full 14-tag TOF block for either profile — and the engine simply
        // does not evaluate the channel on a jorgensen profile (a bracketed Lorentz coefficient
        // on a jorgensen fit is still refused by crysta's own free-set builder, which is the
        // guard that matters).
        for (const char* tag : kLorentzTags) {
            if (peak_type == kPeakJvd && !block_has_tag(block, tag)) {
                fail_schema(where, "missing-family-tag",
                            std::string("_peak.type 'tof-jorgensen-von-dreele' requires ") + tag);
            }
        }
    }

    // Every occurrence, not the first a lookup returns. Each scalar of the background
    // declaration appears at most once and never as a loop column; a row loop names a column at
    // most once; there is at most one point loop and one term loop.
    {
        const char* const scalars[] = {"_background.type", "_background.origin", "_background.x_min",
                                       "_background.x_max"};
        for (const char* scalar : scalars) {
            const auto count = std::count_if(block.items.begin(), block.items.end(),
                                             [scalar](const auto& item) { return item.first == scalar; });
            if (count > 1) {
                fail_schema(where, "background-declared-twice",
                            std::string(scalar) + " is declared " + std::to_string(count) + " times");
            }
        }
        int point_loops = 0;
        int term_loops = 0;
        for (const Loop& loop : block.loops) {
            for (const char* scalar : scalars) {
                if (loop.column(scalar) >= 0) {
                    fail_schema(where, "background-scalar-in-loop",
                                std::string(scalar) + " is a scalar item, not a loop column");
                }
            }
            for (const char* column : {"_background.id", "_background.position", "_background.intensity",
                                       "_background.order", "_background.coef"}) {
                if (std::count(loop.tags.begin(), loop.tags.end(), column) > 1) {
                    fail_schema(where, "background-column-twice",
                                std::string("a background loop names ") + column + " twice");
                }
            }
            point_loops += loop.column("_background.position") >= 0 ||
                                   loop.column("_background.intensity") >= 0
                               ? 1
                               : 0;
            term_loops +=
                loop.column("_background.order") >= 0 || loop.column("_background.coef") >= 0 ? 1 : 0;
        }
        if (point_loops > 1 || term_loops > 1) {
            fail_schema(where, "background-loop-twice",
                        std::string("the background ") + (point_loops > 1 ? "points" : "terms") +
                            " are declared in more than one loop");
        }
    }
    const std::string* background_type = block.find("_background.type");
    const bool has_line_segment_fields =
        block_has_tag(block, "_background.position") || block_has_tag(block, "_background.intensity");
    const bool has_chebyshev_fields =
        block_has_tag(block, "_background.order") || block_has_tag(block, "_background.coef");
    // The polynomial's origin and the Chebyshev domain.
    const bool has_origin = block_has_tag(block, "_background.origin");
    const bool has_domain = block_has_tag(block, "_background.x_min") || block_has_tag(block, "_background.x_max");
    if (background_type == nullptr) {
        if (has_line_segment_fields || has_chebyshev_fields || has_origin || has_domain) {
            fail_schema(where, "missing-background-selector",
                        "background fields require an explicit _background.type selector");
        }
        return;
    }
    if (*background_type == "line-segment") {
        if (has_chebyshev_fields || has_origin || has_domain) {
            fail_domain(where, "background-fields-of-other-type",
                        "line-segment background cannot contain polynomial or Chebyshev fields");
        }
        // A supported line-segment body is exactly one loop declaring BOTH required columns. The
        // decoder reads the background from `loop_with("_background.position")` and pairs each row
        // with `_background.intensity` in that same loop, so a one-sided, scalar, or split-loop
        // body would otherwise be silently decoded as an empty background — a partial plausible
        // model. Reject those here so a malformed line-segment body fails closed.
        if (block.find("_background.position") != nullptr ||
            block.find("_background.intensity") != nullptr) {
            fail_schema(where, "background-not-a-loop",
                        "line-segment background must be a loop, not scalar "
                        "_background.position/_background.intensity items");
        }
        const Loop* position_loop = block.loop_with("_background.position");
        const Loop* intensity_loop = block.loop_with("_background.intensity");
        if (position_loop == nullptr || intensity_loop == nullptr) {
            fail_schema(where, "background-loop-incomplete",
                        "line-segment background requires a loop declaring both "
                        "_background.position and _background.intensity");
        }
        if (position_loop != intensity_loop) {
            fail_schema(where, "background-columns-split",
                        "line-segment background _background.position and "
                        "_background.intensity must share one loop");
        }
    } else if (*background_type == "chebyshev" || *background_type == "polynomial") {
        // A term loop declaring both columns, and only this type's constants — the polynomial its
        // origin, the Chebyshev series its domain.
        const bool polynomial = *background_type == "polynomial";
        if (has_line_segment_fields) {
            fail_domain(where, "background-fields-of-other-type",
                        *background_type + " background cannot contain line-segment fields");
        }
        if (block.find("_background.order") != nullptr || block.find("_background.coef") != nullptr) {
            fail_schema(where, "background-not-a-loop",
                        *background_type + " background must be a loop, not scalar "
                                           "_background.order/_background.coef items");
        }
        const Loop* order_loop = block.loop_with("_background.order");
        const Loop* coef_loop = block.loop_with("_background.coef");
        if (order_loop == nullptr || coef_loop == nullptr) {
            fail_schema(where, "background-loop-incomplete",
                        *background_type + " background requires a loop declaring both "
                                           "_background.order and _background.coef");
        }
        if (order_loop != coef_loop) {
            fail_schema(where, "background-columns-split",
                        *background_type + " background _background.order and _background.coef "
                                           "must share one loop");
        }
        if (polynomial ? has_domain : has_origin) {
            fail_domain(where, "background-fields-of-other-type",
                        polynomial ? "polynomial background cannot declare the Chebyshev domain "
                                     "_background.x_min/_background.x_max"
                                   : "chebyshev background cannot declare the polynomial "
                                     "_background.origin");
        }
        const char* const required[] = {"_background.origin", "_background.x_min", "_background.x_max"};
        for (const char* tag : polynomial ? std::span(required, 1) : std::span(required + 1, 2)) {
            if (block.find(tag) == nullptr) {
                fail_schema(where, "missing-background-constant",
                            *background_type + " background requires " + tag);
            }
        }
    } else {
        fail_schema(where, "unknown-background-type",
                    "unknown _background.type selector '" + *background_type + "'");
    }
}

// ---- embedded measured data ---------------------------------------------------------------

constexpr const char* kDataCategory = "_data.";
constexpr const char* kDataTof = "_data.time_of_flight";
constexpr const char* kDataTwoTheta = "_data.two_theta";
constexpr const char* kDataIntensity = "_data.intensity_meas";
constexpr const char* kDataSigma = "_data.intensity_meas_su";

// The measured-data axis column is per family: degrees 2theta for a
// `cwl-*` experiment, microseconds TOF for a `tof-*` one.
const char* data_axis_tag(BeamModeEnum mode) {
    return mode == BeamModeEnum::CONSTANT_WAVELENGTH ? kDataTwoTheta : kDataTof;
}

// Discover the embedded measured loop by the `_data.*` CATEGORY, never by one required member.
//
// Discovering through `_data.time_of_flight` alone made that one tag a silent sentinel: a loop
// declaring `_data.intensity_meas`/`_data.intensity_meas_su` but omitting or misspelling the TOF
// column was not recognized as a `_data` loop at all, so a malformed pattern was reported as "no
// embedded data" — silently accepted as data-less and misdiagnosed by the completeness check.
// Category discovery makes every required column checkable in both modes.
//
// Columns split across two `_data` loops are rejected rather than half-read, on the same reasoning
// as the line-segment background above: the decoder pairs cells within ONE loop, so a split body
// would otherwise decode into a plausible-but-wrong pattern.
const Loop* find_data_loop(const Block& block, const std::string& where) {
    const Loop* found = nullptr;
    for (const Loop& loop : block.loops) {
        const bool declares_data =
            std::any_of(loop.tags.begin(), loop.tags.end(), [](const std::string& tag) {
                return tag.rfind(kDataCategory, 0) == 0;  // prefix test
            });
        if (!declares_data) {
            continue;
        }
        if (found != nullptr) {
            fail_schema(where, "data-columns-split",
                        "_data columns are split across multiple loops; the measured "
                        "pattern must be declared in one loop");
        }
        found = &loop;
    }
    return found;
}

// Parse the embedded `_data.*` measured loop, or return nullopt if the block declares none.
//
// Column mapping is TAG-DRIVEN, never positional: the acceptance vehicle's header order is
// (time_of_flight, id, intensity_meas, intensity_meas_su), so the physical columns sit at indices
// 0/2/3 and a positional reader would silently take `_data.id` as the intensity. `_data.id` is read
// past and ignored, exactly as the reference loader does — it is a row ordinal, not a measurement.
//
// Extra `_data.*` columns are TOLERATED (the reference treats `_data` as an unmodelled category, so
// rejecting them would refuse projects it happily fits). The one place this is deliberately STRICTER
// than the reference is an empty loop: a header with zero rows parses there and yields a zero-point
// fit that looks successful, which is the single most dangerous failure this task exists to remove.
std::optional<PdDataBase> parse_measured_data(const Block& block, BeamModeEnum mode,
                                                   const std::string& where) {
    const Loop* loop = find_data_loop(block, where);
    if (loop == nullptr) {
        return std::nullopt;  // genuinely no `_data` loop — the only data-less case
    }
    const char* axis = data_axis_tag(mode);
    // I13 at the file boundary: a block carrying BOTH axis tags (in any form — column or
    // scalar) is ambiguous about which axis the data means, and refuses rather than letting
    // the beam mode silently pick one.
    const char* other_axis = mode == BeamModeEnum::CONSTANT_WAVELENGTH ? kDataTof : kDataTwoTheta;
    if (block_has_tag(block, other_axis)) {
        fail_domain(where, "ambiguous-measured-axis",
                    "ambiguous measured axis — the block carries both " +
                      std::string(kDataTwoTheta) + " and " + kDataTof +
                      "; exactly one axis must be declared");
    }
    for (const char* tag : {axis, kDataIntensity, kDataSigma}) {
        if (loop->column(tag) < 0) {
            fail_schema(where, "missing-data-column",
                        std::string("_data loop is missing required column ") + tag);
        }
    }
    if (loop->rows.empty()) {
        fail_schema(where, "empty-data-loop", "_data loop declares columns but has no rows");
    }
    // The columns are built here and assigned once (a column takes whole writes).
    std::vector<double> axis_values;
    std::vector<double> intensity_meas;
    std::vector<double> intensity_meas_su;
    axis_values.reserve(loop->rows.size());
    intensity_meas.reserve(loop->rows.size());
    intensity_meas_su.reserve(loop->rows.size());
    for (const std::vector<std::string>& row : loop->rows) {
        const double sigma = to_double(loop_cell(*loop, row, kDataSigma, where), where);
        // A non-positive sigma is an infinite (or negative) weight: it would poison the fit silently
        // rather than fail, so it is rejected at the boundary like any other unusable measurement.
        if (sigma <= 0.0) {
            fail_domain(where, "non-positive-sigma",
                        "non-positive " + std::string(kDataSigma) + " '" +
                          loop_cell(*loop, row, kDataSigma, where) + "'");
        }
        axis_values.push_back(to_double(loop_cell(*loop, row, axis, where), where));
        intensity_meas.push_back(to_double(loop_cell(*loop, row, kDataIntensity, where), where));
        intensity_meas_su.push_back(sigma);
    }
    PdDataBase data;
    // The mode-named axis: engage exactly the axis this experiment's beam mode names.
    (mode == BeamModeEnum::CONSTANT_WAVELENGTH ? data.two_theta : data.time_of_flight) =
        std::move(axis_values);
    data.intensity_meas = std::move(intensity_meas);
    data.intensity_meas_su = std::move(intensity_meas_su);
    return data;
}

BraggPdExperiment experiment_from_block(const Block& block, const std::string& where) {
    require_edi_schema(block, where);
    validate_known_tags(block, where);
    BraggPdExperiment experiment;
    experiment.name = block.name;
    // Resolve the experiment kind from the `_peak.type` family cross-validated against
    // `_experiment_type.beam_mode` (the shipped four-case matrix), then validate the per-family
    // registry before decoding any body field.
    const ResolvedExperimentKind resolved = resolve_experiment_kind(block, where);
    // The typed profile is always engaged after a load (mirroring the historical always-set
    // token); the typed beam-mode axis is engaged iff the block declared the tag, so the writer
    // can reproduce a tag-absent file byte-for-byte (ExperimentBase::effective_beam_mode carries the
    // dispatch for the absent case).
    experiment.peak.type =
        resolved.declared.value_or(resolved.mode == BeamModeEnum::CONSTANT_WAVELENGTH
                                       ? std::string(kPeakCwlDefault)
                                       : std::string(kPeakJorgensen));
    if (resolved.beam_declared) {
        experiment.experiment_type.beam_mode = resolved.mode;
    }
    // The other three typed axes — presence-tracked reads with fail-closed token decoding; an
    // absent tag leaves the declared edi default in force.
    if (const std::string* form = block.find("_experiment_type.sample_form")) {
        if (*form == "powder") {
            experiment.experiment_type.sample_form = SampleFormEnum::POWDER;
        } else if (*form == "single crystal") {
            experiment.experiment_type.sample_form = SampleFormEnum::SINGLE_CRYSTAL;
        } else {
            fail_schema(where, "unknown-sample-form",
                        "_experiment_type.sample_form '" + *form +
                          "' is not a known token (expected 'powder' or 'single crystal')");
        }
    }
    if (const std::string* probe = block.find("_experiment_type.radiation_probe")) {
        if (*probe == "neutron") {
            experiment.experiment_type.radiation_probe = RadiationProbeEnum::NEUTRON;
        } else if (*probe == "xray") {
            experiment.experiment_type.radiation_probe = RadiationProbeEnum::XRAY;
        } else {
            fail_schema(where, "unknown-radiation-probe",
                        "_experiment_type.radiation_probe '" + *probe +
                          "' is not a known token (expected 'neutron' or 'xray')");
        }
    }
    if (const std::string* scattering = block.find("_experiment_type.scattering_type")) {
        if (*scattering == "bragg") {
            experiment.experiment_type.scattering_type = ScatteringTypeEnum::BRAGG;
        } else if (*scattering == "total") {
            experiment.experiment_type.scattering_type = ScatteringTypeEnum::TOTAL;
        } else {
            fail_schema(where, "unknown-scattering-type",
                        "_experiment_type.scattering_type '" + *scattering +
                          "' is not a known token (expected 'bragg' or 'total')");
        }
    }
    // ADR-0067 §1, ADR-0014: the scattering-source selectors — each only on an experiment of its
    // probe, known values only, kept exactly as written. The rule is edi/selectors.hpp's
    // scattering_source_refusal, shared with the app's selector so the two cannot differ; the
    // order, codes and messages are unchanged.
    for (const ScatteringSourceItem item :
         {ScatteringSourceItem::XRAY_FORM_FACTOR, ScatteringSourceItem::XRAY_DISPERSION,
          ScatteringSourceItem::NEUTRON_SCATTERING_LENGTH}) {
        const std::string* value = block.find(scattering_source_tag(item));
        if (value == nullptr) {
            continue;
        }
        if (const auto refusal = scattering_source_refusal(
                experiment.experiment_type.effective_radiation_probe(), item, *value)) {
            fail_schema(where, refusal->code, refusal->message);
        }
        (item == ScatteringSourceItem::XRAY_FORM_FACTOR  ? experiment.xray_form_factor
         : item == ScatteringSourceItem::XRAY_DISPERSION ? experiment.xray_dispersion
                                                         : experiment.neutron_scattering_length) = *value;
    }
    validate_experiment_selectors(block, resolved.peak_type, resolved.mode, where);
    experiment.peak.cutoff_fwhm = to_double(block.require("_peak.cutoff_fwhm", where), where);

    if (resolved.mode == BeamModeEnum::CONSTANT_WAVELENGTH) {
        // The required family-`cwl` scalars — presence already proven by the registry, so the
        // require inside can only fail on a value-level defect (malformed number, out-of-range
        // value).
        const CwlProfileSlots slots = cwl_profile_slots(resolved.peak_type);
        experiment.peak.broad_gauss_u =
            require_spec_parameter(block, spec::peak_broad_gauss_u, where);
        experiment.peak.broad_gauss_v =
            require_spec_parameter(block, spec::peak_broad_gauss_v, where);
        experiment.peak.broad_gauss_w =
            require_spec_parameter(block, spec::peak_broad_gauss_w, where);
        if (slots.lorentz_xy) {
            experiment.peak.broad_lorentz_x =
                require_spec_parameter(block, spec::peak_broad_lorentz_x, where);
            experiment.peak.broad_lorentz_y =
                require_spec_parameter(block, spec::peak_broad_lorentz_y, where);
        }
        // The mixing and asymmetry coefficients the declared profile carries, optional with
        // default 0 — engaged exactly on that profile (another profile's is refused above).
        const auto optional_zero = [&](const ParameterSpec& spec, double fallback = 0.0) {
            std::optional<Parameter> found = find_spec_parameter(block, spec, where);
            if (!found) {
                found = Parameter{};
                found->value = fallback;
                found->spec = &spec;
            }
            return found;
        };
        if (slots.mixing_eta) {
            experiment.peak.mixing_eta_0 = optional_zero(spec::peak_mixing_eta_0);
            experiment.peak.mixing_eta_1 = optional_zero(spec::peak_mixing_eta_1);
        }
        if (slots.fcj) {
            experiment.peak.asym_fcj_1 = optional_zero(spec::peak_asym_fcj_1);
            experiment.peak.asym_fcj_2 = optional_zero(spec::peak_asym_fcj_2);
        } else if (slots.beba) {
            experiment.peak.asym_beba_a0 = optional_zero(spec::peak_asym_beba_a0);
            experiment.peak.asym_beba_b0 = optional_zero(spec::peak_asym_beba_b0);
            experiment.peak.asym_beba_a1 = optional_zero(spec::peak_asym_beba_a1);
            experiment.peak.asym_beba_b1 = optional_zero(spec::peak_asym_beba_b1);
            // The owner's default: corrected at every angle.
            experiment.peak.asym_beba_limit = optional_zero(spec::peak_asym_beba_limit, 180.0);
        }
        experiment.instrument.setup_wavelength =
            require_spec_parameter(block, spec::instrument_wavelength, where);
        // The wavelength's domain (finite and positive, the reflection limit), crysta's own check,
        // refused at load as the calculation refuses it.
        if (const std::string domain =
                detail::wavelength_domain_message(experiment.instrument.setup_wavelength->value);
            !domain.empty()) {
            fail_domain(where, "wavelength-domain", domain);
        }
        experiment.instrument.calib_twotheta_offset =
            require_spec_parameter(block, spec::instrument_twotheta_offset, where);
        // The line shifts are optional (absent = crysta's default 0).
        experiment.instrument.calib_sample_displacement =
            find_spec_parameter(block, spec::instrument_sample_displacement, where);
        experiment.instrument.calib_sample_transparency =
            find_spec_parameter(block, spec::instrument_sample_transparency, where);
        // A finite pair whose |SyCos| + |SySin| overflows makes every reflection centre non-finite; crysta
        // refuses it at every use (ADR-0070), so the load refuses it too.
        {
            const double displacement = experiment.instrument.calib_sample_displacement
                                            ? experiment.instrument.calib_sample_displacement->value
                                            : 0.0;
            const double transparency = experiment.instrument.calib_sample_transparency
                                            ? experiment.instrument.calib_sample_transparency->value
                                            : 0.0;
            if (!std::isfinite(std::abs(displacement) + std::abs(transparency))) {
                fail_domain(where, "line-shift-domain",
                            "|_instrument.calib_sample_displacement| + "
                            "|_instrument.calib_sample_transparency| overflows: the shifted reflection "
                            "centres would not be finite");
            }
        }
        // The monochromator polarization is the X-ray CW instrument's, optional with upstream's
        // default 0 and engaged on every X-ray CW load, as crysta's loader holds it. The default
        // carries NO uncertainty, so crysta's writer omits it and a file that never declared the
        // pair saves unchanged. A neutron block declaring one is refused by name, as crysta's
        // loader refuses it.
        const bool xray =
            experiment.experiment_type.effective_radiation_probe() == RadiationProbeEnum::XRAY;
        for (const auto& [slot, polarization_spec] :
             {std::pair{&experiment.instrument.setup_polarization_coefficient,
                        &spec::instrument_polarization_coefficient},
              std::pair{&experiment.instrument.setup_monochromator_twotheta,
                        &spec::instrument_monochromator_twotheta}}) {
            std::optional<Parameter> found = find_spec_parameter(block, *polarization_spec, where);
            if (!xray) {
                if (found) {
                    fail_schema(where, "xray-instrument-on-non-xray",
                                std::string(polarization_spec->edi_names[0]) +
                                    " is declared on a non-X-ray experiment — the monochromator "
                                    "polarization is X-ray only");
                }
                continue;
            }
            if (!found) {
                found = Parameter{};
                found->value = 0.0;
                found->uncertainty = std::nullopt;
                found->spec = polarization_spec;
            }
            *slot = std::move(found);
        }
        // The pair's domain (K in [0, 1], 2theta_m in [0, 180] degrees) is a physical one the engine
        // enforces at calculate, fit and save, refused at load as crysta's loader refuses it, in its
        // words.
        if (xray) {
            const auto shown = [](double value) {
                char text[32];
                std::snprintf(text, sizeof text, "%g", value);
                return std::string(text);
            };
            const double coefficient = experiment.instrument.setup_polarization_coefficient->value;
            const double monochromator = experiment.instrument.setup_monochromator_twotheta->value;
            if (!(coefficient >= 0.0 && coefficient <= 1.0)) {
                fail_domain(where, "polarization-domain",
                            "_instrument.setup_polarization_coefficient is " + shown(coefficient) +
                                ", outside its domain [0, 1]");
            }
            if (!(monochromator >= 0.0 && monochromator <= 180.0)) {
                fail_domain(where, "polarization-domain",
                            "_instrument.setup_monochromator_twotheta is " + shown(monochromator) +
                                ", outside its domain [0, 180] degrees");
            }
        }
    } else {
        read_spec_into(block, experiment.instrument.setup_twotheta_bank, where);

        // Tof-pseudo-voigt requires only its three Gaussian variance coefficients — no back-to-back
        // exponentials (never read by its kernel) and size/strain at diffraction-lib's default 0 —
        // exactly crysta's loader rule; every other TOF type requires them all.
        const bool pseudo_voigt = resolved.peak_type == kPeakTofPseudoVoigt;
        const auto read_tof = [&](Parameter& field) {
            if (pseudo_voigt && !block_has_tag(block, field.spec->edi_names[0])) {
                return;  // stays at its {0, 0, false} default
            }
            read_spec_into(block, field, where);
        };
        read_tof(experiment.peak.rise_alpha_0);
        read_tof(experiment.peak.rise_alpha_1);
        read_tof(experiment.peak.decay_beta_0);
        read_tof(experiment.peak.decay_beta_1);
        read_spec_into(block, experiment.peak.broad_gauss_sigma_0, where);
        read_spec_into(block, experiment.peak.broad_gauss_sigma_1, where);
        read_spec_into(block, experiment.peak.broad_gauss_sigma_2, where);
        read_tof(experiment.peak.broad_gauss_size);
        read_tof(experiment.peak.broad_gauss_strain);
        // The JvD Lorentzian block. `validate_experiment_selectors` has already proven the five
        // tags are all present exactly when the selector is 'tof-jorgensen-von-dreele', so a pure
        // Jorgensen experiment leaves them at their {0, 0, false} defaults (no profile
        // contribution).
        if (pseudo_voigt) {
            // The pseudo-Voigt's Lorentzian block is optional tag by tag (default 0).
            read_tof(experiment.peak.broad_lorentz_gamma_0);
            read_tof(experiment.peak.broad_lorentz_gamma_1);
            read_tof(experiment.peak.broad_lorentz_gamma_2);
            read_tof(experiment.peak.broad_lorentz_size);
            read_tof(experiment.peak.broad_lorentz_strain);
        } else if (block_has_tag(block, kLorentzTags[0])) {
            read_spec_into(block, experiment.peak.broad_lorentz_gamma_0, where);
            read_spec_into(block, experiment.peak.broad_lorentz_gamma_1, where);
            read_spec_into(block, experiment.peak.broad_lorentz_gamma_2, where);
            read_spec_into(block, experiment.peak.broad_lorentz_size, where);
            read_spec_into(block, experiment.peak.broad_lorentz_strain, where);
        }

        read_spec_into(block, experiment.instrument.calib_d_to_tof_offset, where);
        read_spec_into(block, experiment.instrument.calib_d_to_tof_linear, where);
        read_spec_into(block, experiment.instrument.calib_d_to_tof_quadratic, where);
        // The reciprocal term is OPTIONAL on read — every project edi wrote before this change
        // lacks the tag (the writer dropped it, deviation D15) — and defaults to the fixed 0
        // crysta's own loader produces; the writer below always emits it, as crysta's does, so a
        // value set through the model survives a rewrite.
        if (block_has_tag(block, spec::instrument_d_to_tof_reciprocal.edi_names[0])) {
            read_spec_into(block, experiment.instrument.calib_d_to_tof_reciprocal, where);
        }
    }

    // The ruled selector/body contract applies at THIS boundary too, so both loaders accept
    // the same inputs and build the same model. The selector always exists (absent in the
    // file means "none") and an unknown one refuses; a typed family's parameters exist IFF
    // the type says so — under TOF "cylinder" the ABSCOR pair is required and a missing key
    // takes the owner's general default ("0" ⇒ A ≡ 1); under TOF "none" a declared abscor key
    // refuses as contradictory. CW cylinder absorption is its own term, so a CW block never
    // carries the pair — mirroring crysta, which reads nothing and refuses nothing there. The
    // canonical state then crosses the delegated save unchanged — no new serializer. A
    // malformed value still fails closed through parse_parameter/to_double.
    experiment.absorption.type =
        (block.find("_absorption.type") != nullptr) ? *block.find("_absorption.type")
                                                    : std::string("none");
    // The selector vocabulary is beam-scoped — a CW block spells
    // none/cylinder-hewat/cylinder-lobanov (the mu_r body), a TOF block none/cylinder (the
    // ABSCOR pair) — and a typed family's parameters exist IFF the type says so, each family
    // reading only its OWN key list (crysta model.cpp's family_absorption_keys split).
    {
        const bool loader_is_cw = resolved.mode == BeamModeEnum::CONSTANT_WAVELENGTH;
        const std::string& absorption_type = *experiment.absorption.type;
        const bool absorption_type_known =
            loader_is_cw ? (absorption_type == "none" || absorption_type == "cylinder-hewat" ||
                            absorption_type == "cylinder-lobanov")
                         : (absorption_type == "none" || absorption_type == "cylinder");
        if (!absorption_type_known) {
            fail_domain(where, "unknown-absorption-type",
                        "unknown _absorption.type '" + absorption_type +
                            (loader_is_cw ? "' (the registry spells none, cylinder-hewat or "
                                            "cylinder-lobanov)"
                                          : "' (the registry spells none or cylinder)"));
        }
        if (absorption_type == "cylinder") {
            // Declared keys read first; apply_absorption_family (the ONE spelling of the
            // family contract) then supplies any missing coefficient's default.
            experiment.absorption.abscor1 =
                find_spec_parameter(block, spec::absorption_abscor1, where);
            experiment.absorption.abscor2 =
                find_spec_parameter(block, spec::absorption_abscor2, where);
            apply_absorption_family(experiment.absorption, "cylinder");
        } else if (absorption_type == "cylinder-hewat" || absorption_type == "cylinder-lobanov") {
            experiment.absorption.mu_r = find_spec_parameter(block, spec::absorption_mu_r, where);
            apply_absorption_family(experiment.absorption, absorption_type);
        } else {
            std::vector<const ParameterSpec*> family_keys;
            if (loader_is_cw) {
                family_keys = {&spec::absorption_mu_r};
            } else {
                family_keys = {&spec::absorption_abscor1, &spec::absorption_abscor2};
            }
            for (const ParameterSpec* spec : family_keys) {
                if (block_has_tag(block, spec->edi_names[0])) {
                    fail_domain(where, "absorption-key-beside-none",
                                std::string("block declares ") + spec->edi_names[0] +
                                    " beside _absorption.type none — a typed family's "
                                    "parameters exist only when the type says so");
                }
            }
        }
    }

    const Loop* linked = block.loop_with("_linked_structure.structure_id");
    if (linked == nullptr || linked->rows.empty()) {
        fail_schema(where, "missing-linked-structure-loop", "missing _linked_structure loop");
    }
    // Every row is a linked structure (phase) with its scale and an optional enabled flag (absent
    // = taking part).
    std::vector<std::shared_ptr<LinkedStructure>> links;
    for (const std::vector<std::string>& row : linked->rows) {
        auto link = std::make_shared<LinkedStructure>();
        link->structure_id = loop_cell(*linked, row, "_linked_structure.structure_id", where);
        read_into(link->scale,
                  parse_parameter(loop_cell(*linked, row, spec::linked_structure_scale.edi_names[0], where),
                                  where),
                  where);
        if (linked->column("_linked_structure.enabled") >= 0) {
            const std::string token = loop_cell(*linked, row, "_linked_structure.enabled", where);
            if (token != "true" && token != "false") {
                fail_schema(where, "invalid-linked-structure-enabled",
                            "_linked_structure.enabled is '" + token + "', expected true or false");
            }
            link->enabled = token == "true";
        }
        links.push_back(std::move(link));
    }
    try {
        experiment.linked_structures.assign(std::move(links));
    } catch (const std::invalid_argument& error) {
        fail_domain(where, "duplicate-id", error.what());
    }

    // ADR-0068: the optional `_preferred_orientation` loop, one row per textured linked
    // structure, keyed by it, constant wavelength only — the same refusals crysta's loader makes,
    // so both loaders accept the same inputs.
    {
        static const std::vector<std::string> po_tags{
            "_preferred_orientation.structure_id", "_preferred_orientation.march_r",
            "_preferred_orientation.index_h",      "_preferred_orientation.index_k",
            "_preferred_orientation.index_l",      "_preferred_orientation.march_random_fract"};
        const Loop* po = nullptr;
        for (const std::string& tag : po_tags) {
            if (block.find(tag) != nullptr) {
                fail_schema(where, "preferred-orientation-not-a-loop",
                            "_preferred_orientation must be a loop, not scalar items");
            }
            if (po == nullptr) {
                po = block.loop_with(tag);
            }
        }
        if (po != nullptr) {
            if (resolved.mode != BeamModeEnum::CONSTANT_WAVELENGTH) {
                fail_domain(where, "preferred-orientation-not-cw",
                            "preferred orientation is constant-wavelength only");
            }
            const auto has = [&](const std::string& tag) { return po->column(tag) >= 0; };
            for (const std::vector<std::string>& row : po->rows) {
            auto item = std::make_shared<PrefOrient>();
            item->structure_id =
                has(po_tags[0]) ? loop_cell(*po, row, po_tags[0], where) : std::string();
            const bool linked_id = std::any_of(
                experiment.linked_structures.begin(), experiment.linked_structures.end(),
                [&](const std::shared_ptr<LinkedStructure>& link) {
                    return link->structure_id.value() == item->structure_id.value();
                });
            if (!linked_id) {
                fail_domain(where, "preferred-orientation-structure",
                            "_preferred_orientation.structure_id '" + item->structure_id.value() +
                                "' does not name the linked structure '" +
                                (experiment.linked_structures.size() == 1
                                     ? experiment.linked_structure().structure_id.value()
                                     : std::string()) +
                                "'");
            }
            if (has(po_tags[1])) {
                read_into(item->march_r, parse_parameter(loop_cell(*po, row, po_tags[1], where), where),
                          where);
            }
            if (has(po_tags[5])) {
                read_into(item->march_random_fract,
                          parse_parameter(loop_cell(*po, row, po_tags[5], where), where), where);
            }
            if (!(item->march_r.value > 0.0)) {
                fail_domain(where, "preferred-orientation-march-r", "march_r must be > 0");
            }
            // The fraction's [0, 1] is a physical domain the engine enforces at calculate, fit and save,
            // never an editing range a fitted value may leave (crysta's loader refuses it too).
            if (!(item->march_random_fract.value >= 0.0 && item->march_random_fract.value <= 1.0)) {
                fail_domain(where, "preferred-orientation-march-random-fract",
                            "march_random_fract must lie in [0, 1]");
            }
            detail::Written<int>* const axis[3] = {&item->index_h, &item->index_k, &item->index_l};
            for (std::size_t i = 0; i < 3; ++i) {
                if (has(po_tags[2 + i])) {
                    const double value = to_double(loop_cell(*po, row, po_tags[2 + i], where), where);
                    if (value != std::round(value) ||
                        std::abs(value) > static_cast<double>(kPreferredOrientationAxisBound)) {
                        fail_domain(where, "preferred-orientation-index",
                                    po_tags[2 + i] + " is not an integer Miller index");
                    }
                    *axis[i] = static_cast<int>(value);
                }
            }
            if (item->index_h == 0 && item->index_k == 0 && item->index_l == 0) {
                fail_domain(where, "preferred-orientation-axis",
                            "the texture axis [0 0 0] has no direction");
            }
            try {
                experiment.preferred_orientation.push_back(std::move(item));
            } catch (const std::invalid_argument& error) {
                fail_domain(where, "duplicate-id", error.what());
            }
            }
        }
    }

    const Loop* excluded = block.loop_with("_excluded_region.start");
    if (excluded != nullptr) {
        std::vector<std::pair<double, double>> regions;
        for (const auto& row : excluded->rows) {
            const double start = to_double(loop_cell(*excluded, row, "_excluded_region.start", where),
                                           where);
            const double end =
                to_double(loop_cell(*excluded, row, "_excluded_region.end", where), where);
            regions.emplace_back(start, end);
        }
        experiment.excluded_regions = std::move(regions);
    }

    // The file's reflections, kept as read (model.hpp ExperimentBase::carried_reflections).
    if (const Loop* refln = block.loop_with("_refln.id"); refln != nullptr) {
        CarriedLoop carried;
        std::vector<std::string> columns;
        for (const std::string& tag : refln->tags) {
            columns.push_back(tag.rfind("_refln.", 0) == 0 ? tag.substr(7) : tag);
        }
        carried.columns = std::move(columns);
        carried.rows = refln->rows;
        experiment.carried_reflections = std::move(carried);
    }

    // The declared model, its constants and its term rows (the selector body was proven
    // consistent by validate_experiment_selectors).
    if (const std::string* background_type = block.find("_background.type")) {
        experiment.background_type = *background_type;
    }
    const auto background_constant = [&](const char* tag) -> std::optional<double> {
        const std::string* text = block.find(tag);
        return text == nullptr ? std::nullopt : std::optional<double>(to_double(*text, where));
    };
    experiment.background_origin = background_constant("_background.origin");
    experiment.background_x_min = background_constant("_background.x_min");
    experiment.background_x_max = background_constant("_background.x_max");
    if (experiment.background_origin && *experiment.background_origin == 0.0) {
        fail_domain(where, "background-origin-zero", "_background.origin must be non-zero");
    }
    if (experiment.background_x_min && experiment.background_x_max &&
        !(*experiment.background_x_min < *experiment.background_x_max)) {
        fail_domain(where, "background-domain-empty",
                    "_background.x_min must be below _background.x_max");
    }
    if (const Loop* terms = block.loop_with("_background.coef"); terms != nullptr) {
        std::set<int> orders;
        for (const auto& row : terms->rows) {
            PolynomialTerm term;
            const std::string order_text = loop_cell(*terms, row, "_background.order", where);
            const double order = to_double(order_text, where);
            // Review 1 F2: each model's terms — the Chebyshev series' 0..23 (FullProf's 24), the
            // polynomial's 0..5 (its six); a term may be left out, never added.
            const double highest = experiment.background_type == "chebyshev" ? 23.0 : 5.0;
            if (!(order >= 0.0) || order != std::floor(order) || order > highest) {
                fail_domain(where, "background-order-invalid",
                            "_background.order '" + order_text + "' of a " +
                                experiment.background_type + " background is not an integer in 0.." +
                                std::to_string(static_cast<int>(highest)));
            }
            term.order = static_cast<int>(order);
            if (!orders.insert(term.order).second) {
                fail_domain(where, "background-order-duplicate",
                            "two background terms declare order " + std::to_string(term.order.get()));
            }
            read_into(term.coef,
                      parse_parameter(loop_cell(*terms, row, spec::background_coef.edi_names[0], where), where),
                      where);
            experiment.background_terms.push_back(std::move(term));
        }
    }

    const Loop* background = block.loop_with("_background.position");
    if (background != nullptr) {
        for (const auto& row : background->rows) {
            LineSegment point;
            point.position = to_double(loop_cell(*background, row, "_background.position", where), where);
            read_into(point.intensity,
                      parse_parameter(loop_cell(*background, row,
                                                spec::background_intensity.edi_names[0], where),
                                      where),
                      where);
            experiment.background.push_back(std::move(point));
        }
    }
    experiment.data = parse_measured_data(block, resolved.mode, where);

    // The one-loader ruling ("one loader, project contents select calculate vs fit"): a block may
    // declare its measured `_data` loop (fit-ready) or its `_data_range.<axis>_min/_max/_step`
    // calculation grid, never both. The generated axis carries EMPTY intensity vectors and marks
    // the experiment calculation-only, so a grid can never be read back as an observation.
    {
        const std::string axis_leaf = resolved.mode == BeamModeEnum::CONSTANT_WAVELENGTH
                                          ? "two_theta"
                                          : "time_of_flight";
        const std::string prefix = "_data_range." + axis_leaf;
        const std::string* min_text = block.find(prefix + "_min");
        const std::string* max_text = block.find(prefix + "_max");
        const std::string* step_text = block.find(prefix + "_step");
        if (min_text != nullptr || max_text != nullptr || step_text != nullptr) {
            if (experiment.data.has_value()) {
                fail_domain(where, "data-and-range-declared",
                            "declares both an embedded _data loop and a " + prefix +
                                " grid - a project selects calculate or fit by declaring exactly "
                                "one of them");
            }
            if (min_text == nullptr || max_text == nullptr || step_text == nullptr) {
                fail_schema(where, "partial-data-range",
                            prefix +
                                "_min/_max/_step must be declared together - a partial range "
                                "cannot generate a grid");
            }
            const double min_value = to_double(*min_text, where);
            const double max_value = to_double(*max_text, where);
            const double step_value = to_double(*step_text, where);
            if (!(step_value > 0.0) || !(max_value > min_value)) {
                fail_domain(where, "unusable-data-range",
                            prefix + " needs step > 0 and max > min");
            }
            PdDataBase generated;
            std::vector<double> axis_values;
            const auto count =
                static_cast<std::size_t>(std::floor((max_value - min_value) / step_value)) + 1;
            axis_values.reserve(count);
            for (std::size_t index = 0; index < count; ++index) {
                axis_values.push_back(min_value + (static_cast<double>(index) * step_value));
            }
            (resolved.mode == BeamModeEnum::CONSTANT_WAVELENGTH ? generated.two_theta
                                                                : generated.time_of_flight) =
                std::move(axis_values);
            experiment.data = std::move(generated);
            experiment.calculation_only = true;
        }
    }
    return experiment;
}

std::vector<fs::path> sorted_edi_files(const fs::path& directory) {
    std::vector<fs::path> files;
    if (!fs::is_directory(directory)) {
        return files;
    }
    for (const auto& entry : fs::directory_iterator(directory)) {
        if (entry.is_regular_file() && entry.path().extension() == ".edi") {
            files.push_back(entry.path());
        }
    }
    std::sort(files.begin(), files.end(),
              [](const fs::path& left, const fs::path& right) {
                  return left.filename().string() < right.filename().string();
              });
    return files;
}

// ---- .edi writing ---------------------------------------------------------------------------------

std::string format_double(double value) {
    char buffer[64];
    const auto result = std::to_chars(buffer, buffer + sizeof(buffer), value);
    return std::string(buffer, result.ptr);
}

std::string format_fixed(double value, int ndec) {
    char buffer[400];
    std::snprintf(buffer, sizeof(buffer), "%.*f", ndec, value);
    return std::string(buffer);
}

// Parse a fixed-point string back to a double, locale-independently (the round-trip probe below).
double parse_fixed(const std::string& text) {
    double out = 0.0;
    std::istringstream stream(text);
    stream.imbue(std::locale::classic());
    stream >> out;
    return (stream.fail() || !stream.eof()) ? std::numeric_limits<double>::quiet_NaN() : out;
}

// Minimal number of decimals for which `format_fixed(value, ndec)` round-trips `value` exactly —
// i.e. the shortest FIXED-POINT (no exponent) rendering. `format_double` uses exponent notation for
// extreme magnitudes (`1e-07`), which the mantissa grammar rejects inside a bracket, so a bracketed
// value must go through this instead.
int fixed_round_trip_ndec(double value) {
    for (int ndec = 0; ndec <= 340; ++ndec) {
        if (parse_fixed(format_fixed(value, ndec)) == value) {
            return ndec;
        }
    }
    return 340;
}

// The parameter slot walk: per refinable scalar, its `_fit_parameter.id` slot, its diffraction-lib
// unique name (`<datablock>.<category>[.<entry>].<name>`, the `_alias.parameter_unique_name`
// spelling) and the parameter, in crysta's storage/dictionary order, mirroring crysta's
// core/fit_state.hpp byte-for-byte (the slot grammar is the shared `.edi` `_fit_parameter.id`
// schema; the two writers must emit identical rows for one project). One walk serves writer and
// loader, and both spellings, so they cannot drift.
template <typename ParameterPtr>
struct ParameterSlot {
    std::string id;
    std::string unique_name;
    ParameterPtr parameter;
};

template <typename ProjectT>
auto parameter_slots(ProjectT& project) {
    using ParameterPtr = decltype(&project.structures.front()->cell.length_a);
    std::vector<ParameterSlot<ParameterPtr>> slots;
    const auto add = [&slots](std::string id, std::string unique_name, ParameterPtr parameter) {
        slots.push_back({std::move(id), std::move(unique_name), parameter});
    };
    // Several structures name each one's slots by its datablock key, as crysta's fit_state.hpp; one
    // structure keeps `structure.`.
    const bool several_structures = project.structures.size() > 1;
    for (auto& structure_item : project.structures) {
        auto& structure = *structure_item;
        const std::string block = datablock_key(structure.name.value(), "structure");
        const std::string base = several_structures ? "structure." + block + "." : std::string("structure.");
        const auto cell = [&](const char* name, ParameterPtr parameter) {
            add(base + "cell." + name, block + ".cell." + name, parameter);
        };
        cell("length_a", &structure.cell.length_a);
        cell("length_b", &structure.cell.length_b);
        cell("length_c", &structure.cell.length_c);
        cell("angle_alpha", &structure.cell.angle_alpha);
        cell("angle_beta", &structure.cell.angle_beta);
        cell("angle_gamma", &structure.cell.angle_gamma);
        for (auto& site_item : structure.atom_sites) {
            auto& site = *site_item;
            const std::string prefix = base + site.id.value() + ".";
            const std::string unique = block + ".atom_site." + site.id.value() + ".";
            add(prefix + "fract_x", unique + "fract_x", &site.fract_x);
            add(prefix + "fract_y", unique + "fract_y", &site.fract_y);
            add(prefix + "fract_z", unique + "fract_z", &site.fract_z);
            add(prefix + "occupancy", unique + "occupancy", &site.occupancy);
            add(prefix + "adp_iso", unique + "adp_iso", &site.adp_iso);
        }
    }
    for (auto& experiment_item : project.experiments) {
        auto& experiment = *experiment_item;
        // ADR-0016: the canonical datablock key, as crysta's writer composes it.
        const std::string prefix = datablock_key(experiment.name, "experiment") + ".";
        // A link with no structure id names its scale by the project's structure, as crysta's walk
        // does (structure_link_id); several links prefix their own slots by structure.
        const auto entry_of = [&](const std::string& linked) {
            return datablock_key(
                linked.empty() && !project.structures.empty() ? project.structures.front()->name.value() : linked,
                "structure");
        };
        const bool several_links = experiment.linked_structures.size() > 1;
        const auto phase_prefix = [&](const std::string& structure_id) {
            return several_links ? prefix + datablock_key(structure_id, "structure") + "." : prefix;
        };
        const auto peak = [&](const std::string& name, ParameterPtr parameter) {
            add(prefix + name, prefix + "peak." + name, parameter);
        };
        const auto instrument = [&](const std::string& name, ParameterPtr parameter) {
            add(prefix + name, prefix + "instrument." + name, parameter);
        };
        const auto absorption = [&](const std::string& name, ParameterPtr parameter) {
            add(prefix + name, prefix + "absorption." + name, parameter);
        };
        if (experiment.effective_beam_mode() == BeamModeEnum::TIME_OF_FLIGHT) {
            peak("rise_alpha_0", &experiment.peak.rise_alpha_0);
            peak("rise_alpha_1", &experiment.peak.rise_alpha_1);
            peak("decay_beta_0", &experiment.peak.decay_beta_0);
            peak("decay_beta_1", &experiment.peak.decay_beta_1);
            peak("broad_gauss_sigma_0", &experiment.peak.broad_gauss_sigma_0);
            peak("broad_gauss_sigma_1", &experiment.peak.broad_gauss_sigma_1);
            peak("broad_gauss_sigma_2", &experiment.peak.broad_gauss_sigma_2);
            peak("broad_gauss_size", &experiment.peak.broad_gauss_size);
            peak("broad_gauss_strain", &experiment.peak.broad_gauss_strain);
            peak("broad_lorentz_gamma_0", &experiment.peak.broad_lorentz_gamma_0);
            peak("broad_lorentz_gamma_1", &experiment.peak.broad_lorentz_gamma_1);
            peak("broad_lorentz_gamma_2", &experiment.peak.broad_lorentz_gamma_2);
            peak("broad_lorentz_size", &experiment.peak.broad_lorentz_size);
            peak("broad_lorentz_strain", &experiment.peak.broad_lorentz_strain);
            instrument("calib_d_to_tof_offset", &experiment.instrument.calib_d_to_tof_offset);
            instrument("calib_d_to_tof_linear", &experiment.instrument.calib_d_to_tof_linear);
            instrument("calib_d_to_tof_quadratic", &experiment.instrument.calib_d_to_tof_quadratic);
            instrument("calib_d_to_tof_reciprocal", &experiment.instrument.calib_d_to_tof_reciprocal);
        } else {
            if (experiment.peak.broad_gauss_u) {
                peak("broad_gauss_u", &*experiment.peak.broad_gauss_u);
            }
            if (experiment.peak.broad_gauss_v) {
                peak("broad_gauss_v", &*experiment.peak.broad_gauss_v);
            }
            if (experiment.peak.broad_gauss_w) {
                peak("broad_gauss_w", &*experiment.peak.broad_gauss_w);
            }
            if (experiment.peak.broad_lorentz_x) {
                peak("broad_lorentz_x", &*experiment.peak.broad_lorentz_x);
            }
            if (experiment.peak.broad_lorentz_y) {
                peak("broad_lorentz_y", &*experiment.peak.broad_lorentz_y);
            }
            if (experiment.peak.mixing_eta_0) {
                peak("mixing_eta_0", &*experiment.peak.mixing_eta_0);
            }
            if (experiment.peak.mixing_eta_1) {
                peak("mixing_eta_1", &*experiment.peak.mixing_eta_1);
            }
            // The asymmetry coefficients the declared rung carries. Each slot is named by its
            // storage member, never by the parameter's descriptor, which a native caller may leave
            // null.
            using Named = std::pair<const char*, OptionalParameter*>;
            for (const auto& [name, asym] :
                 {Named{"asym_fcj_1", &experiment.peak.asym_fcj_1},
                  Named{"asym_fcj_2", &experiment.peak.asym_fcj_2},
                  Named{"asym_beba_a0", &experiment.peak.asym_beba_a0},
                  Named{"asym_beba_b0", &experiment.peak.asym_beba_b0},
                  Named{"asym_beba_a1", &experiment.peak.asym_beba_a1},
                  Named{"asym_beba_b1", &experiment.peak.asym_beba_b1},
                  Named{"asym_beba_limit", &experiment.peak.asym_beba_limit}}) {
                if (*asym) {
                    peak(name, &**asym);
                }
            }
            if (experiment.instrument.calib_twotheta_offset) {
                instrument("calib_twotheta_offset", &*experiment.instrument.calib_twotheta_offset);
            }
            if (experiment.instrument.setup_wavelength) {
                instrument("setup_wavelength", &*experiment.instrument.setup_wavelength);
            }
            // Crysta's instrument[2]/[3], after the pair (its storage order);: then the X-ray
            // polarization pair, its instrument[4]/[5].
            for (const auto& [name, shift] :
                 {Named{"calib_sample_displacement", &experiment.instrument.calib_sample_displacement},
                  Named{"calib_sample_transparency", &experiment.instrument.calib_sample_transparency},
                  Named{"setup_polarization_coefficient",
                        &experiment.instrument.setup_polarization_coefficient},
                  Named{"setup_monochromator_twotheta",
                        &experiment.instrument.setup_monochromator_twotheta}}) {
                if (*shift) {
                    instrument(name, &**shift);
                }
            }
        }
        // One scale per linked structure; several links name theirs by structure.
        for (auto& link : experiment.linked_structures) {
            add(phase_prefix(link->structure_id) + "scale",
                prefix + "linked_structure." + entry_of(link->structure_id.value()) + ".scale", &link->scale);
        }
        if (experiment.absorption.abscor1) {
            absorption("abscor1", &*experiment.absorption.abscor1);
        }
        if (experiment.absorption.abscor2) {
            absorption("abscor2", &*experiment.absorption.abscor2);
        }
        if (experiment.absorption.mu_r) {
            absorption("mu_r", &*experiment.absorption.mu_r);
        }
        // The preferred-orientation pair, crysta fit_state.hpp's order (after absorption).
        for (auto& row : experiment.preferred_orientation) {
            const std::string texture = prefix + "preferred_orientation." + row->structure_id.value() + ".";
            add(phase_prefix(row->structure_id) + "march_r", texture + "march_r", &row->march_r);
            add(phase_prefix(row->structure_id) + "march_random_fract", texture + "march_random_fract",
                &row->march_random_fract);
        }
        // The declared model's parameters by row (crysta fit_state.hpp) — the line-segment
        // intensities, or a polynomial or Chebyshev model's coefficients.
        if (experiment.background_type == "line-segment") {
            for (std::size_t index = 0; index < experiment.background.size(); ++index) {
                // The written `_background.id` is the row ordinal, from 1.
                add(prefix + "background[" + std::to_string(index) + "]",
                    prefix + "background." + std::to_string(index + 1) + ".intensity",
                    &experiment.background[index]->intensity);
            }
        } else {
            for (std::size_t index = 0; index < experiment.background_terms.size(); ++index) {
                add(prefix + "background[" + std::to_string(index) + "]",
                    prefix + "background." + std::to_string(index + 1) + ".coef",
                    &experiment.background_terms[index]->coef);
            }
        }
    }
    return slots;
}

// The `_fit_parameter` slot spelling of the walk above: (id, parameter) per refinable scalar.
template <typename ProjectT>
auto fit_state_slots(ProjectT& project) {
    using ParameterPtr = decltype(&project.structures.front()->cell.length_a);
    std::vector<std::pair<std::string, ParameterPtr>> slots;
    for (auto& slot : parameter_slots(project)) {
        slots.emplace_back(std::move(slot.id), slot.parameter);
    }
    return slots;
}

}  // namespace

// ---- public entry points --------------------------------------------------------------------------

namespace {
// STAR-format UTC timestamp ('%d %b %Y %H:%M:%S' — upstream _PROJECT_TIMESTAMP_FORMAT).
std::string star_timestamp_format(std::time_t t) {
    std::tm utc{};
    gmtime_r(&t, &utc);
    char buffer[32];
    std::strftime(buffer, sizeof(buffer), "%d %b %Y %H:%M:%S", &utc);
    return buffer;
}

std::string star_timestamp_now() { return star_timestamp_format(std::time(nullptr)); }

// The stamp's epoch seconds, or nullopt when it does not parse as STAR format.
std::optional<std::time_t> star_timestamp_seconds(const std::string& stamp) {
    std::tm parsed{};
    std::istringstream in(stamp);
    in.imbue(std::locale::classic());
    in >> std::get_time(&parsed, "%d %b %Y %H:%M:%S");
    if (in.fail()) {
        return std::nullopt;
    }
    return timegm(&parsed);
}
}  // namespace

ProjectMetadata::ProjectMetadata() {
    created = star_timestamp_now();
    last_modified = created;
}

// Strictly advancing: a save landing in the same STAR-format clock tick as the stored stamp
// (1 s resolution) still advances `last_modified`, stepping one second past the stored value
// instead of repeating a wall clock that has not ticked yet.
void ProjectMetadata::update_last_modified() {
    const std::time_t now = std::time(nullptr);
    const std::optional<std::time_t> stored = star_timestamp_seconds(last_modified);
    last_modified =
        star_timestamp_format(stored.has_value() && now <= *stored ? *stored + 1 : now);
}

// The bare element symbol from a CIF `_atom_site_type_symbol`, dropping any oxidation-state
// suffix so a CIF structure's scattering species matches the
// `.edi` twin's plain element symbol. Falls back to the raw token when there is no leading
// alphabetic run.
std::string element_from_type_symbol(const std::string& type_symbol) {
    std::size_t end = 0;
    while (end < type_symbol.size() &&
           std::isalpha(static_cast<unsigned char>(type_symbol[end])) != 0) {
        ++end;
    }
    return end == 0 ? type_symbol : type_symbol.substr(0, end);
}

// Classic IUCr CIF structure reader (`_cell_*` / `_atom_site_*` underscore tags) — the core
// reader this task's necessity sweep removed with its binding, RESTORED per review-32 F1 with
// two task-era adaptations: `esd` is spelled `uncertainty`, and a landed isotropic ADP
// records the stored representation `adp_type = "Biso"`.
Structure structure_from_cif_block(const Block& block, const std::string& where) {
    Structure structure;
    structure.name = block.name;
    // A CIF spells the bond increment `incr`; the model and a
    // `.edi` file spell it `inc`. Both CIF forms are read: the DDLm data name and its classic alias.
    for (const auto& [dotted, classic, field] :
         {std::tuple<const char*, const char*, detail::Written<std::optional<double>> Geom::*>{
              "_geom.min_bond_distance_cutoff", "_geom_min_bond_distance_cutoff",
              &Geom::min_bond_distance_cutoff},
          {"_geom.bond_distance_incr", "_geom_bond_distance_incr", &Geom::bond_distance_inc}}) {
        const std::string* text = block.find(dotted);
        if (text == nullptr) {
            text = block.find(classic);
        }
        if (text != nullptr) {
            const double value = to_double(*text, where);
            if (value < 0.0) {
                fail_domain(where, "out-of-range",
                            std::string(dotted) + " '" + *text + "' must be finite and >= 0");
            }
            structure.geom.*field = value;
        }
    }
    if (const std::string* symbol = block.find("_space_group_name_H-M_alt")) {
        structure.space_group.name_h_m = *symbol;
    } else {
        structure.space_group.name_h_m = block.require("_symmetry_space_group_name_H-M", where);
    }
    read_into(structure.cell.length_a,
              parse_parameter(block.require("_cell_length_a", where), where), where);
    read_into(structure.cell.length_b,
              parse_parameter(block.require("_cell_length_b", where), where), where);
    read_into(structure.cell.length_c,
              parse_parameter(block.require("_cell_length_c", where), where), where);
    read_into(structure.cell.angle_alpha,
              parse_parameter(block.require("_cell_angle_alpha", where), where), where);
    read_into(structure.cell.angle_beta,
              parse_parameter(block.require("_cell_angle_beta", where), where), where);
    read_into(structure.cell.angle_gamma,
              parse_parameter(block.require("_cell_angle_gamma", where), where), where);
    require_realizable_cell(structure.cell, where);

    const Loop* loop = block.loop_with("_atom_site_label");
    if (loop == nullptr) {
        throw IoError(where + ": missing _atom_site loop (not a CIF structure)");
    }

    // A published CIF often records ADPs only anisotropically (COD 1000236). Reduce each aniso
    // row to the equivalent isotropic B, B_eq = 8*pi^2*(U11+U22+U33)/3, keyed by site label, so a
    // site with no _atom_site_B_iso_or_equiv column still carries the isotropic representation.
    std::map<std::string, double> b_eq_from_aniso;
    if (const Loop* aniso = block.loop_with("_atom_site_aniso_label")) {
        const double pi = 3.141592653589793238;
        for (const auto& row : aniso->rows) {
            const std::string& label = loop_cell(*aniso, row, "_atom_site_aniso_label", where);
            const double u11 =
                parse_parameter(loop_cell(*aniso, row, "_atom_site_aniso_U_11", where), where)
                    .value;
            const double u22 =
                parse_parameter(loop_cell(*aniso, row, "_atom_site_aniso_U_22", where), where)
                    .value;
            const double u33 =
                parse_parameter(loop_cell(*aniso, row, "_atom_site_aniso_U_33", where), where)
                    .value;
            b_eq_from_aniso[label] = 8.0 * (pi * pi) * (u11 + u22 + u33) / 3.0;
        }
    }

    for (const auto& row : loop->rows) {
        AtomSite site;
        site.id = loop_cell(*loop, row, "_atom_site_label", where);
        site.type_symbol =
            element_from_type_symbol(loop_cell(*loop, row, "_atom_site_type_symbol", where));
        const int wyckoff = loop->column("_atom_site_Wyckoff_symbol");
        if (wyckoff >= 0) {
            site.wyckoff_letter = row[static_cast<std::size_t>(wyckoff)];
        }
        read_into(site.fract_x,
                  parse_parameter(loop_cell(*loop, row, "_atom_site_fract_x", where), where),
                  where);
        read_into(site.fract_y,
                  parse_parameter(loop_cell(*loop, row, "_atom_site_fract_y", where), where),
                  where);
        read_into(site.fract_z,
                  parse_parameter(loop_cell(*loop, row, "_atom_site_fract_z", where), where),
                  where);
        read_into(site.occupancy,
                  parse_parameter(loop_cell(*loop, row, "_atom_site_occupancy", where), where),
                  where);
        // Isotropic ADP, read-all over the ordered spellings: prefer the canonical
        // _atom_site_B_iso_or_equiv; else _atom_site_U_iso_or_equiv converted B = 8*pi^2*U (the
        // same factor as the anisotropic reduction); else the aniso-derived B_eq; else default.
        const int b_iso_column = loop->column("_atom_site_B_iso_or_equiv");
        const int u_iso_column = loop->column("_atom_site_U_iso_or_equiv");
        if (b_iso_column >= 0) {
            read_into(site.adp_iso,
                      parse_parameter(row[static_cast<std::size_t>(b_iso_column)], where), where);
            site.adp_type = "Biso";
        } else if (u_iso_column >= 0) {
            constexpr double pi = 3.141592653589793238;
            Parameter adp = parse_parameter(row[static_cast<std::size_t>(u_iso_column)], where);
            adp.value *= 8.0 * pi * pi;
            if (adp.uncertainty) {
                adp.uncertainty = *adp.uncertainty * (8.0 * pi * pi);
            }
            read_into(site.adp_iso, adp, where);
            site.adp_type = "Biso";
        } else if (const auto found = b_eq_from_aniso.find(site.id);
                   found != b_eq_from_aniso.end()) {
            site.adp_iso.value = found->second;
            site.adp_type = "Biso";
        }
        structure.atom_sites.push_back(std::move(site));
    }
    return structure;
}

Structure structure_from_edi_text(const std::string& text) {
    const std::string where = "<from_cif_str>";
    const Block block = parse_block(text, where);
    // Vocabulary dispatch: the dot-form `.edi` schema and classic IUCr CIF are both accepted,
    // exactly one per document, decided by which cell vocabulary is present.
    if (block.find("_cell.length_a") != nullptr) {
        return structure_from_block(block, where);
    }
    if (block.find("_cell_length_a") != nullptr) {
        return structure_from_cif_block(block, where);
    }
    throw IoError(where +
                  ": neither `.edi` (_cell.length_a) nor CIF (_cell_length_a) cell vocabulary "
                  "present");
}

// ---- classic-CIF experiment translation (experiment half) ----------------------------
//
// The classic vocabulary is diffraction-lib's own `cif_names` tables at the frozen anchor
// (`datablocks/experiment/categories/*` — every TagSpec pairs the dot-form `.edi` spelling with its
// classic CIF spellings). Translation is mechanical: each classic item/loop-column is rewritten to
// its `.edi` tag and the block then flows through the ONE experiment builder, so the CIF branch can
// never drift from the `.edi` semantics. Classic tags with no `.edi` schema counterpart (the
// double-exponential peak terms, the CW wavelength-2 family) are dropped exactly as the `.edi`
// reader ignores unmodelled categories.

struct CifExperimentItemRule {
    const char* edi;                    // the `.edi` tag the builder reads
    std::vector<const char*> classic;   // classic spellings, upstream priority order (first wins)
    // Which selector family requires this tag, and the upstream-declared default that fills it
    // when the CIF omits it (diffraction-lib AttributeSpec defaults at the frozen anchor):
    // "" = never filled; "cwl" / "tof" = the family's concrete classes; "tof-jvd" = only the
    // Lorentzian-carrying tof-jorgensen-von-dreele (TofJorgensen has no Lorentzian mixin, and a
    // default there would change which profile the block means).
    const char* family = "";
    const char* fallback = nullptr;
};

const std::vector<CifExperimentItemRule>& experiment_cif_item_rules() {
    static const std::vector<CifExperimentItemRule> rules{
        {"_experiment_type.sample_form",
         {"_easydiffraction_experiment_type.sample_form", "_expt_type.sample_form"}},
        {"_experiment_type.beam_mode",
         {"_easydiffraction_experiment_type.beam_mode", "_expt_type.beam_mode"}},
        {"_experiment_type.radiation_probe",
         {"_easydiffraction_experiment_type.radiation_probe", "_expt_type.radiation_probe"}},
        {"_experiment_type.scattering_type",
         {"_easydiffraction_experiment_type.scattering_type", "_expt_type.scattering_type"}},
        {"_peak.type", {"_easydiffraction_peak.type"}},
        {"_peak.cutoff_fwhm", {"_easydiffraction_peak.cutoff_fwhm"}},
        {"_background.type", {"_easydiffraction_background.type"}},
        // CW broadening (cwl_mixins)
        {"_peak.broad_gauss_u", {"_easydiffraction_peak.broad_gauss_u"}, "cwl", "0.01"},
        {"_peak.broad_gauss_v", {"_easydiffraction_peak.broad_gauss_v"}, "cwl", "-0.01"},
        {"_peak.broad_gauss_w", {"_easydiffraction_peak.broad_gauss_w"}, "cwl", "0.02"},
        {"_peak.broad_lorentz_x", {"_easydiffraction_peak.broad_lorentz_x"}, "cwl-tch", "0.0"},
        {"_peak.broad_lorentz_y", {"_easydiffraction_peak.broad_lorentz_y"}, "cwl-tch", "0.0"},
        // The CW asymmetry mixins, filled only on the rung that carries them.
        // The pseudo-Voigt mixing: the loader reads an absent one as 0, so no fallback is filled.
        {"_peak.mixing_eta_0", {"_easydiffraction_peak.mixing_eta_0"}},
        {"_peak.mixing_eta_1", {"_easydiffraction_peak.mixing_eta_1"}},
        {"_peak.asym_fcj_1", {"_easydiffraction_peak.asym_fcj_1"}, "cwl-fcj", "0.0"},
        {"_peak.asym_fcj_2", {"_easydiffraction_peak.asym_fcj_2"}, "cwl-fcj", "0.0"},
        {"_peak.asym_beba_a0", {"_easydiffraction_peak.asym_beba_a0"}, "cwl-beba", "0.0"},
        {"_peak.asym_beba_b0", {"_easydiffraction_peak.asym_beba_b0"}, "cwl-beba", "0.0"},
        {"_peak.asym_beba_a1", {"_easydiffraction_peak.asym_beba_a1"}, "cwl-beba", "0.0"},
        {"_peak.asym_beba_b1", {"_easydiffraction_peak.asym_beba_b1"}, "cwl-beba", "0.0"},
        // The limit angle: the loader reads an absent one as 180, so no fallback is filled.
        {"_peak.asym_beba_limit", {"_easydiffraction_peak.asym_beba_limit"}},
        // TOF broadening (tof_mixins)
        {"_peak.broad_gauss_sigma_0", {"_easydiffraction_peak.broad_gauss_sigma_0"}, "tof",
         "7.0"},
        {"_peak.broad_gauss_sigma_1", {"_easydiffraction_peak.broad_gauss_sigma_1"}, "tof",
         "0.0"},
        {"_peak.broad_gauss_sigma_2", {"_easydiffraction_peak.broad_gauss_sigma_2"}, "tof",
         "0.0"},
        {"_peak.broad_gauss_size", {"_easydiffraction_peak.broad_gauss_size"}, "tof", "0.0"},
        {"_peak.broad_gauss_strain", {"_easydiffraction_peak.broad_gauss_strain"}, "tof", "0.0"},
        {"_peak.broad_lorentz_gamma_0", {"_easydiffraction_peak.broad_lorentz_gamma_0"},
         "tof-jvd", "0.0"},
        {"_peak.broad_lorentz_gamma_1", {"_easydiffraction_peak.broad_lorentz_gamma_1"},
         "tof-jvd", "0.0"},
        {"_peak.broad_lorentz_gamma_2", {"_easydiffraction_peak.broad_lorentz_gamma_2"},
         "tof-jvd", "0.0"},
        {"_peak.broad_lorentz_size", {"_easydiffraction_peak.broad_lorentz_size"}, "tof-jvd",
         "0.0"},
        {"_peak.broad_lorentz_strain", {"_easydiffraction_peak.broad_lorentz_strain"}, "tof-jvd",
         "0.0"},
        {"_peak.rise_alpha_0", {"_easydiffraction_peak.rise_alpha_0"}, "tof", "0.0"},
        {"_peak.rise_alpha_1", {"_easydiffraction_peak.rise_alpha_1"}, "tof", "0.2"},
        {"_peak.decay_beta_0", {"_easydiffraction_peak.decay_beta_0"}, "tof", "0.04"},
        {"_peak.decay_beta_1", {"_easydiffraction_peak.decay_beta_1"}, "tof", "0.0"},
        // CW instrument
        {"_instrument.setup_wavelength",
         {"_diffrn_radiation_wavelength.value", "_instr.wavelength"},
         "cwl",
         "1.5406"},
        {"_instrument.calib_twotheta_offset",
         {"_pd_calib.2theta_offset", "_instr.2theta_offset"},
         "cwl",
         "0.0"},
        // Optional line shifts, translated when present and never filled
        {"_instrument.calib_sample_displacement", {"_instr.sample_displacement"}},
        {"_instrument.calib_sample_transparency", {"_instr.sample_transparency"}},
        // The X-ray polarization pair, translated when present and never filled
        {"_instrument.setup_polarization_coefficient", {"_instr.polarization_coefficient"}},
        {"_instrument.setup_monochromator_twotheta", {"_instr.monochromator_twotheta"}},
        // TOF instrument
        {"_instrument.setup_twotheta_bank", {"_instr.2theta_bank"}, "tof", "150.0"},
        {"_instrument.calib_d_to_tof_offset", {"_instr.d_to_tof_offset"}, "tof", "0.0"},
        {"_instrument.calib_d_to_tof_linear", {"_instr.d_to_tof_linear"}, "tof", "10000.0"},
        {"_instrument.calib_d_to_tof_quadratic", {"_instr.d_to_tof_quad"}, "tof", "0.0"},
        {"_instrument.calib_d_to_tof_reciprocal", {"_instr.d_to_tof_recip"}, "tof", "0.0"},
    };
    return rules;
}

// The declared-range items translate ONLY when the document carries no measured loop: in a real
// pdCIF the `_pd_meas.*_range_*` summary rides BESIDE the data, and translating it there would
// declare data and range at once — the exact contradiction the one-loader ruling refuses.
const std::vector<CifExperimentItemRule>& experiment_cif_range_rules() {
    static const std::vector<CifExperimentItemRule> rules{
        {"_data_range.two_theta_min", {"_pd_meas.2theta_range_min"}},
        {"_data_range.two_theta_max", {"_pd_meas.2theta_range_max"}},
        {"_data_range.two_theta_step", {"_pd_meas.2theta_range_inc"}},
        {"_data_range.time_of_flight_min", {"_pd_meas.time_of_flight_range_min"}},
        {"_data_range.time_of_flight_max", {"_pd_meas.time_of_flight_range_max"}},
        {"_data_range.time_of_flight_step", {"_pd_meas.time_of_flight_range_inc"}},
    };
    return rules;
}

const std::map<std::string, std::string>& experiment_cif_loop_key_map() {
    static const std::map<std::string, std::string> map{
        {"_pd_background.id", "_background.id"},
        {"_pd_background.line_segment_X", "_background.position"},
        {"_pd_background_line_segment_X", "_background.position"},
        {"_pd_background.line_segment_intensity", "_background.intensity"},
        {"_pd_background_line_segment_intensity", "_background.intensity"},
        {"_pd_phase_block.id", "_linked_structure.structure_id"},
        {"_pd_phase_block.scale", "_linked_structure.scale"},
        {"_easydiffraction_excluded_region.id", "_excluded_region.id"},
        {"_easydiffraction_excluded_region.start", "_excluded_region.start"},
        {"_easydiffraction_excluded_region.end", "_excluded_region.end"},
        {"_pd_data.point_id", "_data.id"},
        {"_pd_meas.2theta_scan", "_data.two_theta"},
        {"_pd_proc.2theta_scan", "_data.two_theta"},
        {"_pd_meas.time_of_flight", "_data.time_of_flight"},
        {"_pd_meas.intensity_total", "_data.intensity_meas"},
        {"_pd_proc.intensity_norm", "_data.intensity_meas"},
        {"_pd_meas.intensity_total_su", "_data.intensity_meas_su"},
        {"_pd_proc.intensity_norm_su", "_data.intensity_meas_su"},
    };
    return map;
}

bool experiment_block_is_classic_cif(const Block& block) {
    static const std::set<std::string> classic = [] {
        std::set<std::string> tags;
        for (const auto& rule : experiment_cif_item_rules()) {
            tags.insert(rule.classic.begin(), rule.classic.end());
        }
        for (const auto& rule : experiment_cif_range_rules()) {
            tags.insert(rule.classic.begin(), rule.classic.end());
        }
        for (const auto& [cif, edi] : experiment_cif_loop_key_map()) {
            tags.insert(cif);
        }
        return tags;
    }();
    for (const auto& item : block.items) {
        if (classic.contains(item.first)) {
            return true;
        }
    }
    for (const Loop& loop : block.loops) {
        for (const std::string& tag : loop.tags) {
            if (classic.contains(tag)) {
                return true;
            }
        }
    }
    return false;
}

Block translate_experiment_cif(const Block& in) {
    // The peak category is one row in either vocabulary. A peak item written as a loop column has
    // no translation, and dropping it would let a profile's foreign or supplied coefficients vanish
    // before the profile rules see them, so it is refused.
    for (const Loop& loop : in.loops) {
        for (const std::string& tag : loop.tags) {
            if (starts_with(tag, "_peak.") || starts_with(tag, "_easydiffraction_peak.")) {
                fail_schema("classic CIF experiment block '" + in.name + "'", "peak-item-in-loop",
                            tag + " is a scalar item, not a loop column");
            }
        }
    }
    Block out;
    out.name = in.name;
    out.items.emplace_back("_edi.schema_version", "3");
    const auto translate_items = [&in, &out](const std::vector<CifExperimentItemRule>& rules) {
        for (const CifExperimentItemRule& rule : rules) {
            const std::string* value = nullptr;
            for (const char* classic : rule.classic) {
                value = in.find(classic);
                if (value != nullptr) {
                    break;  // upstream priority order: the first declared spelling wins
                }
            }
            // A peak item in the dot-form spelling is the same declaration, so it is carried
            // rather than dropped (a profile's coefficients never fall back to defaults).
            if (value == nullptr && starts_with(rule.edi, "_peak.")) {
                value = in.find(rule.edi);
            }
            if (value != nullptr) {
                out.items.emplace_back(rule.edi, *value);
            }
        }
    };
    translate_items(experiment_cif_item_rules());
    bool have_data_loop = false;
    const std::string translated_where = "classic CIF experiment block '" + in.name + "'";
    for (const Loop& loop : in.loops) {
        std::vector<std::string> tags;
        std::vector<std::size_t> keep;
        for (std::size_t index = 0; index < loop.tags.size(); ++index) {
            const auto found = experiment_cif_loop_key_map().find(loop.tags[index]);
            if (found != experiment_cif_loop_key_map().end()) {
                tags.push_back(found->second);
                keep.push_back(index);
            }
        }
        if (tags.empty()) {
            continue;  // no `.edi` counterpart in this loop (publication metadata etc.)
        }
        std::vector<std::vector<std::string>> rows;
        rows.reserve(loop.rows.size());
        for (const std::vector<std::string>& row : loop.rows) {
            std::vector<std::string> cells;
            cells.reserve(keep.size());
            for (const std::size_t index : keep) {
                cells.push_back(row[index]);
            }
            rows.push_back(std::move(cells));
        }
        for (const std::string& tag : tags) {
            have_data_loop = have_data_loop || starts_with(tag, kDataCategory);
        }
        out.loops.emplace_back(std::move(tags), std::move(rows), translated_where);
    }
    if (!have_data_loop) {
        translate_items(experiment_cif_range_rules());
    }
    // A CIF with no phase block keeps diffraction-lib's default linked structure (structure_id
    // 'Si', scale 1.0 — the reference constructs the category and overrides only what the CIF
    // carries), so the builder's required loop is synthesized when absent.
    bool have_linked = false;
    for (const Loop& loop : out.loops) {
        have_linked = have_linked || loop.column("_linked_structure.scale") >= 0;
    }
    if (!have_linked) {
        out.loops.emplace_back(
            std::vector<std::string>{"_linked_structure.structure_id", "_linked_structure.scale"},
            std::vector<std::vector<std::string>>{{"Si", "1.0"}}, translated_where);
    }
    // A `_pd_background` line-segment loop declares its own type by shape (upstream's
    // line-segment class matches exactly these cif columns), so the `.edi` selector the builder
    // requires is synthesized when the CIF spells none.
    if (out.find("_background.type") == nullptr) {
        for (const Loop& loop : out.loops) {
            if (loop.column("_background.position") >= 0) {
                out.items.emplace_back("_background.type", "line-segment");
                break;
            }
        }
    }
    // Upstream defaults, mirrored where our builder is stricter than the reference: the peak type
    // follows the declared beam mode's family default when the CIF names none, and the cutoff
    // carries diffraction-lib's declared default (0.0).
    if (out.find("_peak.type") == nullptr) {
        if (const std::string* beam = out.find("_experiment_type.beam_mode")) {
            if (*beam == kBeamModeCwl) {
                out.items.emplace_back("_peak.type", kPeakCwlDefault);
            } else if (*beam == kBeamModeTof) {
                out.items.emplace_back("_peak.type", kPeakJorgensen);
            }
        }
    }
    if (out.find("_peak.cutoff_fwhm") == nullptr) {
        out.items.emplace_back("_peak.cutoff_fwhm", "0");
    }
    // A parameter the CIF omits keeps diffraction-lib's declared default (the reference builds
    // the concrete class first, then overrides only what the CIF carries), so the builder's
    // required-item reads are satisfied exactly as upstream satisfies them — scoped to the
    // block's own selector family, because emitting another family's tags would change what the
    // block declares.
    const std::string* type_item = out.find("_peak.type");
    const std::string selector = type_item != nullptr ? *type_item : "";
    const bool fills_cwl = selector.rfind("cwl-", 0) == 0;
    const bool fills_tof = selector.rfind("tof-", 0) == 0;
    // The TOF pseudo-Voigt carries the Lorentzian mixin too.
    const bool fills_jvd = selector == "tof-jorgensen-von-dreele" || selector == kPeakTofPseudoVoigt;
    for (const CifExperimentItemRule& rule : experiment_cif_item_rules()) {
        if (rule.fallback == nullptr || out.find(rule.edi) != nullptr) {
            continue;
        }
        const std::string family = rule.family;
        // A CW rule fills only a slot the selector's profile carries.
        const CwlProfileSlots slots = cwl_profile_slots(selector);
        if ((family == "cwl" && fills_cwl) || (family == "tof" && fills_tof) ||
            (family == "tof-jvd" && fills_jvd) ||
            (family == "cwl-tch" && fills_cwl && slots.lorentz_xy) ||
            (family == "cwl-fcj" && slots.fcj) || (family == "cwl-beba" && slots.beba)) {
            out.items.emplace_back(rule.edi, rule.fallback);
        }
    }
    return out;
}

BraggPdExperiment experiment_from_edi_text(const std::string& text) {
    const std::string where = "<from_cif_str>";
    const Block block = parse_block(text, where);
    // Vocabulary dispatch: a block spelling any tag of the classic diffraction-lib
    // `cif_names` vocabulary is translated to the dot-form `.edi` tags and built by the one
    // experiment builder; everything else takes the `.edi` path exactly as before.
    if (experiment_block_is_classic_cif(block)) {
        return experiment_from_block(translate_experiment_cif(block), where);
    }
    return experiment_from_block(block, where);
}

BraggPdExperiment simulation_experiment(const std::string& name, const ExperimentTypeTokens& type,
                                        const std::string& structure_id) {
    const bool constant_wavelength = type.beam_mode == "constant wavelength";
    std::string text = "data_" + name + "\n\n_edi.schema_version 3\n\n";
    text += "_experiment_type.sample_form \"" + type.sample_form + "\"\n";
    text += "_experiment_type.beam_mode \"" + type.beam_mode + "\"\n";
    text += "_experiment_type.radiation_probe \"" + type.radiation_probe + "\"\n";
    text += "_experiment_type.scattering_type \"" + type.scattering_type + "\"\n\n";
    // Starting values that give a readable pattern: a Thompson-Cox-Hastings pseudo-Voigt at about a
    // diffractometer's resolution for constant wavelength (HRPT's neutron wavelength, Cu Kα for X-rays),
    // Jorgensen's profile on a 90° bank for time-of-flight.
    if (constant_wavelength) {
        text += type.radiation_probe == "xray" ? "_instrument.setup_wavelength 1.54056\n"
                                               : "_instrument.setup_wavelength 1.494\n";
        text += "_instrument.calib_twotheta_offset 0.\n\n"
                "_peak.type cwl-tch-pseudo-voigt\n"
                "_peak.broad_gauss_u 0.1\n_peak.broad_gauss_v -0.1\n_peak.broad_gauss_w 0.1\n"
                "_peak.broad_lorentz_x 0.\n_peak.broad_lorentz_y 0.1\n_peak.cutoff_fwhm 8.\n\n"
                "_data_range.two_theta_min 10.\n_data_range.two_theta_max 150.\n"
                "_data_range.two_theta_step 0.05\n";
    } else {
        text += "_instrument.setup_twotheta_bank 90.\n"
                "_instrument.calib_d_to_tof_offset 0.\n_instrument.calib_d_to_tof_linear 7000.\n"
                "_instrument.calib_d_to_tof_quadratic 0.\n\n"
                "_peak.type tof-jorgensen\n"
                "_peak.rise_alpha_0 0.\n_peak.rise_alpha_1 0.25\n"
                "_peak.decay_beta_0 0.025\n_peak.decay_beta_1 0.03\n"
                "_peak.broad_gauss_sigma_0 0.\n_peak.broad_gauss_sigma_1 80.\n_peak.broad_gauss_sigma_2 3.\n"
                "_peak.broad_gauss_size 0.\n_peak.broad_gauss_strain 0.\n_peak.cutoff_fwhm 8.\n\n"
                "_data_range.time_of_flight_min 2000.\n_data_range.time_of_flight_max 20000.\n"
                "_data_range.time_of_flight_step 10.\n";
    }
    if (!structure_id.empty()) {
        text += "\nloop_\n_linked_structure.structure_id\n_linked_structure.scale\n" + structure_id + " 1.\n";
    }
    return experiment_from_edi_text(text);
}

// ----: structures and experiments from `.edi` block files ------------

namespace {

// The block of a `.edi` block file: the extension and the project format's schema are checked
// before anything is built.
Block edi_file_block(const std::string& path) {
    if (fs::path(path).extension() != ".edi") {
        throw IoError(path + ": not a .edi file - structures and experiments load from .edi block "
                             "files only");
    }
    Block block = parse_block(read_file(path), path);
    require_edi_schema(block, path);
    return block;
}

// ADR-0016: compared by canonical key — the comparison the collection itself makes when it admits
// the experiment — so this friendlier early refusal can never disagree with it.
bool holds_experiment(const Project& project, const std::string& name) {
    const std::string wanted = KeyTraits<BraggPdExperiment>::canonical(name);
    for (const auto& item : project.experiments) {
        if (KeyTraits<BraggPdExperiment>::canonical(item->name) == wanted) {
            return true;
        }
    }
    return false;
}

}  // namespace

Structure load_structure_edi_file(const std::string& path) {
    return structure_from_block(edi_file_block(path), path);
}

BraggPdExperiment load_experiment_edi_file(const std::string& path) {
    const Block block = edi_file_block(path);
    // The file must say what it is: all four type axes, read from the block itself, because the
    // builder would supply an absent one (beam mode from `_peak.type`, the others by default).
    std::string missing;
    for (const char* tag : {"_experiment_type.sample_form", "_experiment_type.beam_mode",
                            "_experiment_type.radiation_probe", "_experiment_type.scattering_type"}) {
        if (block.find(tag) == nullptr) {
            missing += (missing.empty() ? "" : ", ") + std::string(tag);
        }
    }
    if (!missing.empty()) {
        throw IoError(path + ": an experiment file must declare its experiment type; missing " +
                      missing);
    }
    // A declared type edi's experiment class does not implement is refused by axis (an unknown
    // token is left to the builder's own message).
    if (*block.find("_experiment_type.sample_form") == "single crystal") {
        throw IoError(path + ": _experiment_type.sample_form 'single crystal' is not implemented - "
                             "edi experiments are powder + bragg");
    }
    if (*block.find("_experiment_type.scattering_type") == "total") {
        throw IoError(path + ": _experiment_type.scattering_type 'total' is not implemented - edi "
                             "experiments are powder + bragg");
    }
    BraggPdExperiment experiment = experiment_from_block(block, path);
    // load_project's rule for every experiment of a project: measured data or a calculation grid.
    if (!experiment.data.has_value()) {
        throw IoError(path + ": experiment '" + experiment.name +
                      "' declares neither an embedded _data loop nor a _data_range grid - an "
                      "experiment must say what it computes over");
    }
    return experiment;
}

std::vector<BraggPdExperiment> load_experiment_edi_files(const Project& project,
                                                         const std::vector<std::string>& paths) {
    // load_project's project-level rule: every experiment carries measured data, or every one a
    // calculation grid, so an addition never makes a project the loader would refuse.
    std::optional<bool> calculation;
    for (const auto& item : project.experiments) {
        calculation = item->calculation_only;
    }
    std::vector<BraggPdExperiment> loaded;
    std::set<std::string> names;
    for (const auto& item : project.experiments) {
        names.insert(KeyTraits<BraggPdExperiment>::canonical(item->name));
    }
    for (const std::string& path : paths) {
        BraggPdExperiment experiment = load_experiment_edi_file(path);
        if (!names.insert(KeyTraits<BraggPdExperiment>::canonical(experiment.name)).second) {
            throw IoError(path + ": an experiment named '" +
                          detail::printable_id(experiment.name) + "' is already " +
                          (holds_experiment(project, experiment.name) ? "in the project" : "in this load"));
        }
        if (calculation.has_value() && *calculation != experiment.calculation_only) {
            throw IoError(path + ": experiment '" + experiment.name + "' declares " +
                          (experiment.calculation_only ? "a _data_range grid" : "measured data") +
                          " where the project's experiments declare " +
                          (*calculation ? "a _data_range grid" : "measured data") +
                          " - a project calculates or fits as a whole");
        }
        calculation = experiment.calculation_only;
        loaded.push_back(std::move(experiment));
    }
    return loaded;
}

void add_loaded_structure(Project& project, Structure structure) {
    if (std::any_of(project.structures.begin(), project.structures.end(),
                    [&](const std::shared_ptr<Structure>& held) {
                        return datablock_key(held->name, "structure") ==
                               datablock_key(structure.name, "structure");
                    })) {
        throw IoError("a structure named '" + detail::printable_id(structure.name) +
                      "' is already in the project");
    }
    project.structures.push_back(std::move(structure));
}

void add_loaded_experiment(Project& project, BraggPdExperiment experiment) {
    if (holds_experiment(project, experiment.name)) {
        throw IoError("an experiment named '" + detail::printable_id(experiment.name) +
                      "' is already in the project");
    }
    project.experiments.push_back(std::move(experiment));
}

void rename_experiment(Project& project, ExperimentBase& experiment, const std::string& name) {
    if (name == experiment.name) {
        return;
    }
    // The scan the collection's own rename admission makes — canonical keys, EXCLUDING the
    // experiment being renamed, so its own default spelling ('' <-> experiment) is not mistaken for
    // a second experiment.
    const std::string wanted = KeyTraits<BraggPdExperiment>::canonical(name);
    for (const auto& item : project.experiments) {
        if (static_cast<const ExperimentBase*>(item.get()) != &experiment &&
            KeyTraits<BraggPdExperiment>::canonical(item->name) == wanted) {
            throw IoError("an experiment named '" + detail::printable_id(name) +
                          "' is already in the project");
        }
    }
    experiment.name = name;
}

Project empty_project(const std::string& name, const std::string& description) {
    Project project;
    project.structures.clear();
    project.experiments.clear();
    project.metadata.name = validated_project_name(name);
    project.metadata.description = description;
    return project;
}

void register_peak_type(const std::string& token, BeamModeEnum mode) {
    // ADR-0020 §3: this table and crysta's registry are not locked, and a calculation on the
    // worker thread reads them. So a type is registered before the first worker is built, never
    // while one exists.
    if (work::Worker::any_alive()) {
        throw std::logic_error(
            "edi register_peak_type: a calculation worker exists in this process; a peak type is "
            "registered before the first worker is built");
    }
    peak_type_rows().emplace(token, PeakTypeRow{mode, true});  // idempotent; shipped rows win
    // ADR-0017: the crossing into crysta reads crysta's registry.
    register_engine_peak_type(token, mode);
}

bool peak_type_known(const std::string& token) { return peak_type_rows().count(token) != 0; }

std::optional<BeamModeEnum> peak_type_beam_mode(const std::string& token) {
    const auto& rows = peak_type_rows();
    const auto found = rows.find(token);
    if (found == rows.end() || !found->second.implemented) {
        return std::nullopt;
    }
    return found->second.mode;
}

std::vector<std::string> registered_peak_types() {
    std::vector<std::string> tokens;
    for (const auto& [token, row] : peak_type_rows()) {
        tokens.push_back(token);
    }
    return tokens;
}

Project load_project(const std::string& directory, const WarningSink& on_warning) {
    // One exit for the loader's warnings — the sink when given, else stderr as before.
    const auto warn = [&on_warning](const std::string& message) {
        if (on_warning) {
            on_warning(message);
        } else {
            std::cerr << "Warning: " << message << "\n";
        }
    };
    const fs::path root(directory);
    if (!fs::is_directory(root)) {
        throw IoError("not a project directory: " + directory);
    }
    const std::vector<fs::path> structure_files = sorted_edi_files(root / "structures");
    if (structure_files.empty()) {
        throw IoError("project has no structures/*.edi: " + directory);
    }
    Project project;
    // The loader REPLACES the default-constructed placeholders wholesale — a seeded default
    // surviving next to loaded banks would be a phantom nameless block.
    project.structures.clear();
    project.experiments.clear();
    // Every structure file is a structure (phase), in file order; two declaring one name refuse.
    for (const fs::path& file : structure_files) {
        Structure structure =
            structure_from_block(parse_block(read_file(file.string()), file.string()), file.string());
        if (std::any_of(project.structures.begin(), project.structures.end(),
                        [&](const std::shared_ptr<Structure>& held) {
                            return datablock_key(held->name, "structure") ==
                                   datablock_key(structure.name, "structure");
                        })) {
            throw IoError("two structure files declare the datablock '" +
                          datablock_key(structure.name, "structure") + "' (" + file.string() +
                          "): a project's structures need distinct names");
        }
        project.structures.push_back(std::move(structure));
    }

    // One-loader ruling, PROJECT-level: the project's contents select ONE mode — every
    // experiment declares measured data (a fit-ready project) or every experiment declares a
    // calculation grid (a calculation project). A mixed project would be neither: joint
    // refinement refuses at its calculation bank while the range bank rides beside observations.
    std::optional<bool> project_is_calculation;
    std::string mode_setting_file;
    const auto mode_name = [](bool is_calculation) {
        return is_calculation ? "a _data_range grid (calculation)"
                              : "an embedded _data loop (fit-ready)";
    };
    // `crysta` is the one calculator. Any other `_calculator.type` warns naming it, once per distinct
    // value, exactly as the minimizer below does, and the calculation runs with crysta. The category is
    // not modelled, so the value is not kept.
    std::set<std::string> warned_calculators;
    for (const fs::path& file : sorted_edi_files(root / "experiments")) {
        const Block experiment_block = parse_block(read_file(file.string()), file.string());
        if (const std::string* calculator = experiment_block.find("_calculator.type")) {
            if (*calculator != "crysta" && warned_calculators.insert(*calculator).second) {
                warn("unsupported _calculator.type \"" + *calculator + "\" - using crysta");
            }
        }
        BraggPdExperiment experiment = experiment_from_block(experiment_block, file.string());
        // The file's own contents declare its category — a `_data` loop means measured data
        // (its postconditions were proven during parsing), a `_data_range` grid means a
        // generated axis. Declaring neither is a load-time error naming the offending file
        // (declaring both already refused inside the parser).
        if (!experiment.data.has_value()) {
            throw IoError("project " + directory + ": experiment '" + experiment.name +
                          "' (" + file.string() +
                          ") declares neither an embedded _data loop nor a _data_range grid - a "
                          "project must say what it computes over");
        }
        if (!project_is_calculation.has_value()) {
            project_is_calculation = experiment.calculation_only;
            mode_setting_file = file.string();
        } else if (*project_is_calculation != experiment.calculation_only) {
            throw IoError("project " + directory + ": experiment '" + experiment.name + "' (" +
                          file.string() + ") declares " + mode_name(experiment.calculation_only) +
                          " where '" + mode_setting_file + "' declared " +
                          mode_name(*project_is_calculation) +
                          " - the project's contents select calculate or fit as a whole, and a "
                          "mixed data/range project is refused");
        }
        // Every linked structure names a structure of the project, as crysta's loader requires (an empty
        // id spells `structure`).
        const auto spelled = [](const std::string& id) { return id.empty() ? std::string("structure") : id; };
        for (const auto& link : experiment.linked_structures) {
            const std::string wanted = spelled(link->structure_id.value());
            const bool held = std::any_of(project.structures.begin(), project.structures.end(),
                                          [&](const auto& structure) { return spelled(structure->name.value()) == wanted; });
            if (!held) {
                throw IoError("project " + directory + ": experiment '" + experiment.name + "' (" + file.string() +
                              ") links the structure '" + detail::printable_id(wanted) +
                              "', which the project does not hold");
            }
        }
        project.experiments.push_back(std::move(experiment));
    }

    const fs::path analysis_file = root / "analysis" / "analysis.edi";
    if (fs::is_regular_file(analysis_file)) {
        const Block block =
            parse_block(read_file(analysis_file.string()), analysis_file.string(), false);
        const std::string* mode = block.find("_fitting_mode.type");
        if (mode != nullptr) {
            // Review-1 F4: the closed set is enforced at LOAD on this side too. Without it a
            // lookalike survived loading and then performed one plausible template fit through
            // the single-bank path, writing no scan CSV — a wrong answer that looked right.
            if (!is_declared_fitting_mode(*mode)) {
                throw IoError("_fitting_mode.type is '" + *mode + "', expected " +
                              declared_fitting_modes() + ": " + analysis_file.string());
            }
            project.fitting_mode = *mode;
        }
        // The declared iteration bound. The tag has ridden in analysis files since the
        // diffraction-lib ports; honoring it makes the project data the ONE place a bounded fit
        // is declared (edi's CLI deliberately has no iteration flag). Malformed values fail
        // closed — a bound that silently parsed as unbounded would run a fit the project said
        // not to run.
        const std::string* declared_bound = block.find("_minimizer.max_iterations");
        if (declared_bound != nullptr) {
            std::size_t consumed = 0;
            int bound = 0;
            try {
                bound = std::stoi(*declared_bound, &consumed);
            } catch (const std::exception&) {
                consumed = 0;
            }
            if (consumed != declared_bound->size() || bound < 1) {
                throw IoError("malformed _minimizer.max_iterations '" + *declared_bound +
                              "' (need a positive integer): " + analysis_file.string());
            }
            project.minimizer_max_iterations = bound;
        }
        // `crysta` is the supported minimizer and the default. Any other value warns naming it
        // and the fit runs with crysta; the value is kept as written, so a save returns it and
        // a later edi that supports it still sees it.
        if (const std::string* type = block.find("_minimizer.type")) {
            if (*type != "crysta") {
                warn("unsupported _minimizer.type \"" + *type + "\" - using crysta");
            }
            project.minimizer_type = *type;
        }
        // The declared descent and chi-square tolerance, under the bound's fail-closed rule. The
        // descent must be a registered id verbatim (resolved from the linked crysta registry,
        // never a transcribed list) — an unknown or lookalike token refuses naming the registry
        // rather than running the default.
        if (const std::string* descent = block.find("_minimizer.descent")) {
            const std::vector<std::string> ids = descent_ids();
            if (std::find(ids.begin(), ids.end(), *descent) == ids.end()) {
                std::string registered;
                for (const std::string& id : ids) {
                    registered += (registered.empty() ? "" : ", ") + id;
                }
                throw IoError("unknown _minimizer.descent '" + *descent +
                              "' (registered descents: " + registered +
                              "): " + analysis_file.string());
            }
            project.descent = *descent;
        }
        if (const std::string* tolerance = block.find("_minimizer.chi_square_tolerance")) {
            double value = 0.0;
            try {
                value = to_double(*tolerance, analysis_file.string());
            } catch (const std::exception&) {
                value = 0.0;
            }
            if (!(value > 0.0)) {
                throw IoError("malformed _minimizer.chi_square_tolerance '" + *tolerance +
                              "' (need a positive number): " + analysis_file.string());
            }
            project.minimizer_chi_square_tolerance = value;
        }
        // The `_sequential_fit.*` declaration and its extract loop (crysta's parse,
        // mirrored). Boolean tokens are strict ("true"/"false" only) — a token that silently
        // parsed as false would run the scan in the wrong order, the iteration bound's own
        // fail-closed rule.
        const auto strict_bool = [&analysis_file](const std::string& token, const char* tag) {
            if (token == "true") {
                return true;
            }
            if (token == "false") {
                return false;
            }
            throw IoError(std::string("malformed ") + tag + " '" + token +
                          "' (need true or false): " + analysis_file.string());
        };
        if (const std::string* data_dir = block.find("_sequential_fit.data_dir")) {
            // Review-1 F5: refuse an escaping spelling before it can cross into the engine.
            validate_sequential_data_dir(*data_dir, ": " + analysis_file.string());
            project.sequential_fit.data_dir = *data_dir;
        }
        if (const std::string* pattern = block.find("_sequential_fit.file_pattern")) {
            project.sequential_fit.file_pattern = *pattern;
        }
        if (const std::string* reverse = block.find("_sequential_fit.reverse")) {
            project.sequential_fit.reverse = strict_bool(*reverse, "_sequential_fit.reverse");
        }
        if (const std::string* file = block.find("_sequential_fit.template_file")) {
            project.sequential_fit.template_file = *file;
        }
        if (const Loop* extract = block.loop_with("_sequential_fit_extract.id")) {
            for (const auto& row : extract->rows) {
                SequentialExtractRule rule;
                rule.id = loop_cell(*extract, row, "_sequential_fit_extract.id",
                                    analysis_file.string());
                rule.target = loop_cell(*extract, row, "_sequential_fit_extract.target",
                                        analysis_file.string());
                rule.pattern = loop_cell(*extract, row, "_sequential_fit_extract.pattern",
                                         analysis_file.string());
                rule.required = strict_bool(loop_cell(*extract, row,
                                                      "_sequential_fit_extract.required",
                                                      analysis_file.string()),
                                            "_sequential_fit_extract.required");
                project.sequential_fit.extract.push_back(std::move(rule));
            }
        }
        if (const Loop* aliases = block.loop_with("_alias.id")) {
            for (const auto& row : aliases->rows) {
                ParameterAlias alias;
                alias.id = loop_cell(*aliases, row, "_alias.id", analysis_file.string());
                alias.parameter_unique_name = loop_cell(*aliases, row, "_alias.parameter_unique_name",
                                                        analysis_file.string());
                project.aliases.push_back(std::move(alias));
            }
        }
        if (const Loop* constraints = block.loop_with("_constraint.expression")) {
            const bool has_id = constraints->column("_constraint.id") >= 0;
            for (const auto& row : constraints->rows) {
                ParameterConstraint constraint;
                constraint.expression =
                    loop_cell(*constraints, row, "_constraint.expression", analysis_file.string());
                // An omitted id is the text left of the '=', as diffraction-lib and crysta read it;
                // crysta then checks the whole constraint (refresh_relations below).
                std::string id;
                if (has_id) {
                    id = loop_cell(*constraints, row, "_constraint.id", analysis_file.string());
                } else {
                    const std::string& text = constraint.expression.value();
                    const std::size_t equals = text.find('=');
                    id = equals == std::string::npos ? std::string() : text.substr(0, equals);
                    id.erase(0, id.find_first_not_of(" \t"));
                    id.erase(id.find_last_not_of(" \t") + 1);
                    // crysta's reader refuses the same two rows with the same codes.
                    const auto refuse = [&analysis_file](const char* code, std::string message) {
                        throw DomainValidationError({Diagnostic{code, Severity::Error,
                                                                analysis_file.string(),
                                                                std::move(message), {}, "crysta"}});
                    };
                    if (id.empty()) {
                        refuse("crysta.domain.constraint_syntax",
                               "constraint '" + std::to_string(project.constraints.size() + 1) +
                                   "': a constraint is '<alias> = <expression>', and '" + text +
                                   "' names no alias left of an '='");
                    }
                    for (const auto& other : project.constraints) {
                        if (other->id.value() == id) {
                            refuse("crysta.domain.constraint_target",
                                   "parameter '" + id + "' is set by two constraints, '" +
                                       other->expression.value() + "' and '" + text + "'");
                        }
                    }
                }
                constraint.id = id;
                if (constraints->column("_constraint.enabled") >= 0) {  // absent: every constraint applies
                    constraint.enabled = strict_bool(
                        loop_cell(*constraints, row, "_constraint.enabled", analysis_file.string()),
                        "_constraint.enabled");
                }
                project.constraints.push_back(std::move(constraint));
            }
        }
        if (is_scan_fitting_mode(project.fitting_mode) && !project.sequential_fit.declared()) {
            throw IoError("_fitting_mode.type is '" + project.fitting_mode +
                          "' but no _sequential_fit.data_dir is declared - a scan fit needs the "
                          "scan directory: " +
                          analysis_file.string());
        }
        const Loop* weights = block.loop_with("_joint_fit.experiment_id");
        if (weights != nullptr) {
            for (const auto& row : weights->rows) {
                const std::string& id =
                    loop_cell(*weights, row, "_joint_fit.experiment_id", analysis_file.string());
                const double weight =
                    to_double(loop_cell(*weights, row, "_joint_fit.weight", analysis_file.string()),
                              analysis_file.string());
                for (auto& experiment_item : project.experiments) {
                    ExperimentBase& experiment = *experiment_item;
                    if (experiment.name == id) {
                        experiment.dataset_weight = weight;
                    }
                }
            }
        }
        // The last fit's result (`_fit_result`, diffraction-lib's names) and each bank's share
        // (`_fit_result_bank`), read iff `_fit_result.result_kind` is present — crysta's read,
        // mirrored. A malformed value fails closed: a result read wrong would describe a fit that never
        // ran. The category stays outside the covered set, so the fields diffraction-lib writes and edi
        // does not carry yet (its other R factors) load as they always did.
        if (const std::string* kind = block.find("_fit_result.result_kind")) {
            const std::string where = analysis_file.string();
            const auto text = [&block](const char* tag) {
                const std::string* value = block.find(tag);
                return value != nullptr ? *value : std::string();
            };
            const auto number = [&block, &where](const char* tag) {
                const std::string* value = block.find(tag);
                return value != nullptr ? to_double(*value, where) : 0.0;
            };
            const auto count = [&number, &block, &where](const char* tag) {
                const double value = number(tag);
                if (!(value >= 0.0) || value > 2.0e9 || value != std::floor(value)) {
                    const std::string* raw = block.find(tag);
                    throw IoError(std::string("malformed ") + tag + " '" + (raw != nullptr ? *raw : "") +
                                  "' (need a whole number): " + where);
                }
                return static_cast<int>(value);
            };
            const auto flag = [&block, &strict_bool](const char* tag) {
                const std::string* value = block.find(tag);
                return value != nullptr && strict_bool(*value, tag);
            };
            FitResultRecord& result = project.fit_result;
            result.result_kind = *kind;
            result.success = flag("_fit_result.success");
            result.message = text("_fit_result.message");
            result.iterations = count("_fit_result.iterations");
            result.fitting_time = number("_fit_result.fitting_time");
            result.reduced_chi_square = number("_fit_result.reduced_chi_square");
            result.objective_name = text("_fit_result.objective_name");
            result.objective_value = number("_fit_result.objective_value");
            result.n_data_points = count("_fit_result.n_data_points");
            result.n_parameters = count("_fit_result.n_parameters");
            result.n_free_parameters = count("_fit_result.n_free_parameters");
            result.degrees_of_freedom = count("_fit_result.degrees_of_freedom");
            result.covariance_available = flag("_fit_result.covariance_available");
            result.exit_reason = text("_fit_result.exit_reason");
            result.prof_wr_factor = number("_fit_result.prof_wr_factor");
            result.profile_function = text("_fit_result.profile_function");
            result.background_function = text("_fit_result.background_function");
            result.descent = text("_fit_result.descent");
            if (const Loop* banks = block.loop_with("_fit_result_bank.experiment_id")) {
                for (const auto& row : banks->rows) {
                    const std::string& id = loop_cell(*banks, row, "_fit_result_bank.experiment_id", where);
                    ExperimentBase* bank = nullptr;
                    for (auto& experiment_item : project.experiments) {
                        bank = experiment_item->name == id ? experiment_item.get() : bank;
                    }
                    if (bank == nullptr) {
                        throw IoError("_fit_result_bank row '" + id + "' names no experiment of the project: " + where);
                    }
                    const std::string& points = loop_cell(*banks, row, "_fit_result_bank.n_data_points", where);
                    if (points != ".") {
                        const double value = to_double(points, where);
                        if (!(value >= 0.0) || value > 2.0e9 || value != std::floor(value)) {
                            throw IoError("malformed _fit_result_bank.n_data_points '" + points + "': " + where);
                        }
                        bank->fit_n_data_points = static_cast<int>(value);
                    }
                    bank->fit_prof_wr_factor =
                        to_double(loop_cell(*banks, row, "_fit_result_bank.prof_wr_factor", where), where);
                    const std::string& chi_square = loop_cell(*banks, row, "_fit_result_bank.chi_square", where);
                    if (chi_square != ".") {
                        bank->fit_chi_square = to_double(chi_square, where);
                    }
                }
            }
        }
        // Read the persisted pre-fit snapshot back onto the model. Each row's id resolves
        // through the SAME slot walk the writer emits from, so the two cannot drift; an
        // unresolvable or duplicate id fails closed — a start state silently dropped would make
        // undo restore less than the file promised. `.` = disengaged uncertainty.
        const Loop* fit_rows = block.loop_with("_fit_parameter.id");
        if (fit_rows != nullptr) {
            // ADR-0016: the composed ids pass the one predicate, so a collision refuses by name
            // here rather than resolving first-wins.
            std::map<std::string, Parameter*> slot_map;
            std::vector<std::string> composed;
            for (const auto& [slot_id, parameter] : fit_state_slots(project)) {
                slot_map.emplace(slot_id, parameter);
                composed.push_back(slot_id);
            }
            try {
                require_unique_ids(composed, "fit-state row", "fit-state composition");
            } catch (const std::invalid_argument& error) {
                throw IoError(std::string(error.what()) + ": " + analysis_file.string());
            }
            // Review-9 (the start_tied mirror): the optional _fit_parameter.start_tied column
            // carries a tied basic's free-companion priors. Its per-row tokens are collected
            // here and resolved by the adapter (the constraint knowledge is crysta's, ADR-0003);
            // a file without the column seeds companions from their own coordinate su — under
            // the keep-prior rule that IS the prior.
            const bool has_tied = fit_rows->column("_fit_parameter.start_tied") >= 0;
            std::vector<std::pair<Parameter*, std::optional<std::string>>> tied_rows;
            for (const auto& row : fit_rows->rows) {
                const std::string& id =
                    loop_cell(*fit_rows, row, "_fit_parameter.id", analysis_file.string());
                const auto slot = slot_map.find(id);
                if (slot == slot_map.end()) {
                    throw IoError("analysis.edi: _fit_parameter row '" + id +
                                  "' does not resolve to a model parameter: " +
                                  analysis_file.string());
                }
                if (slot->second->start_value.has_value()) {
                    throw IoError("analysis.edi: _fit_parameter declares '" + id +
                                  "' more than once: " + analysis_file.string());
                }
                slot->second->start_value = to_double(
                    loop_cell(*fit_rows, row, "_fit_parameter.start_value",
                              analysis_file.string()),
                    analysis_file.string());
                const std::string& su = loop_cell(*fit_rows, row,
                                                  "_fit_parameter.start_uncertainty",
                                                  analysis_file.string());
                slot->second->start_uncertainty =
                    su == "." ? std::optional<double>()
                              : std::optional<double>(to_double(su, analysis_file.string()));
                tied_rows.emplace_back(
                    slot->second,
                    has_tied ? std::optional<std::string>(loop_cell(
                                   *fit_rows, row, "_fit_parameter.start_tied",
                                   analysis_file.string()))
                             : std::optional<std::string>());
            }
            seed_positional_start_companions(project, tied_rows, analysis_file.string());
        }
    }

    // The completeness count: a successful return proves every experiment declared what it
    // computes over — measured data (fit-ready; per-bank validity — non-empty, required columns,
    // finite values, positive sigma — was enforced during parsing) or a declared calculation
    // grid. A project with no experiments at all declares neither, so it refuses here for the
    // same reason.
    if (project.experiments.empty()) {
        throw IoError("project has no experiments/*.edi: " + directory);
    }

    // The project record:
    //   - a restorable record restores silently — the round trip is identity on every field the
    //     writer emits (bare `?` is the record's spelling for an empty value; a quoted value is
    //     a literal);
    //   - a malformed, unreadable, or not-provably-understood record REFUSES (IoError naming
    //     the file and the offending item) — the record exists, so defaulting would silently
    //     discard what it holds;
    //   - a present-but-incomplete record (every partial record written before records were complete, the committed
    //     corpus ones included) restores what it carries and keeps constructed defaults for the
    //     rest, silently — nothing saved is substituted, and a diagnostic here fired on all
    //     prior output forever, breaking the shipped stderr-silence contracts;
    //   - an absent record defaults with the named diagnostic below.
    const fs::path record_file = root / "project.edi";
    // Presence is decided IN THE NAMESPACE (symlink_status — the only query that does not
    // follow), never by is_regular_file alone: a directory, a symlink that does not resolve, a
    // FIFO, a socket, a device or an entry stat cannot examine all used to read as "absent" and
    // silently default — the silent-default class reached through the filesystem instead of
    // through content. Present in the namespace, the record is restored only from a readable
    // regular file (following links); every other shape REFUSES naming what it is.
    std::error_code record_link_error;
    const fs::file_status record_link = fs::symlink_status(record_file, record_link_error);
    if (record_link_error && record_link.type() != fs::file_type::not_found) {
        throw IoError("project.edi at '" + record_file.string() + "' cannot be examined (" +
                      record_link_error.message() + ")");
    }
    if (fs::exists(record_link)) {
        const std::string record_where = record_file.string();
        std::error_code record_status_error;
        const fs::file_status record_status = fs::status(record_file, record_status_error);
        if (record_status_error && record_status.type() != fs::file_type::not_found) {
            throw IoError("project.edi at '" + record_where + "' cannot be examined (" +
                          record_status_error.message() + ")");
        }
        if (!fs::is_regular_file(record_status)) {
            throw IoError("project.edi at '" + record_where +
                          "' is present but is not a readable regular file (" +
                          describe_non_regular_entry(record_status, record_link) + ")");
        }
        const std::string record_text = read_file(record_where);
        // Content-level readability, same tier: the record must be text this process can hand
        // to Python faithfully, so invalid UTF-8 refuses HERE, naming the file and offset —
        // restored into metadata it would leak a RuntimeError at first attribute access, far
        // from its cause (and the offending bytes are deliberately not echoed into the message).
        if (const std::optional<std::size_t> bad = first_invalid_utf8_offset(record_text)) {
            throw IoError("project.edi at '" + record_where +
                          "' is not valid UTF-8 (first invalid byte at offset " +
                          std::to_string(*bad) + ")");
        }
        // Structural well-formedness of the WHOLE document stays parse_block's job — an
        // unterminated quote or truncated loop anywhere in the record refuses exactly as
        // before; the parsed block is deliberately NOT consumed for the owned fields.
        parse_block(record_text, record_where, false);
        // The six owned fields and the version declaration are extracted LEXICALLY, line by
        // line, in the writer's own grammar — parse_block's token stream erases the
        // quoted-vs-bare distinction, so a quoted literal "?" silently collapsed into the
        // bare `?` missing-value sentinel and a save-load changed a reachable user value. The
        // grammar, exactly as the writer emits it: bare `?` is the empty sentinel; a
        // double-quoted value is a LITERAL (quotes stripped, no interior quote); any other
        // whitespace-free token is a literal; a value line the writer cannot produce refuses.
        const auto lexical_value = [&record_where](const std::string& line,
                                                   std::size_t value_start,
                                                   const std::string& tag) -> std::string {
            const std::size_t start = line.find_first_not_of(" \t", value_start);
            if (start == std::string::npos) {
                throw IoError("project.edi " + tag + " has no value: " + record_where);
            }
            std::string value = line.substr(start);
            while (!value.empty() &&
                   (value.back() == ' ' || value.back() == '\t' || value.back() == '\r')) {
                value.pop_back();
            }
            if (value == "?") {
                return std::string();  // the BARE missing-value sentinel — empty
            }
            if (value.front() == '"') {
                if (value.size() < 2 || value.back() != '"' ||
                    value.find('"', 1) != value.size() - 1) {
                    throw IoError("project.edi " + tag +
                                  " has a malformed quoted value: " + record_where);
                }
                return value.substr(1, value.size() - 2);  // a quoted LITERAL — "?" stays ?
            }
            if (value.find_first_of(" \t") != std::string::npos) {
                throw IoError("project.edi " + tag +
                              " has an unquoted value carrying whitespace: " + record_where);
            }
            return value;
        };
        const auto is_tag_line = [](const std::string& line, const std::string& tag) {
            return line.rfind(tag, 0) == 0 &&
                   (line.size() == tag.size() || line[tag.size()] == ' ' ||
                    line[tag.size()] == '\t' || line[tag.size()] == '\r');
        };
        static const char* const kMetadataFields[6] = {
            "name", "title", "description", "created", "last_modified", "timestamp"};
        std::optional<std::string> declared_version;
        // ADR-0017 §14: the plot renderer diffraction-lib declares in the record - an engine
        // choice, beside the calculator and the minimizer, that edi does not make.
        std::optional<std::string> declared_plot_renderer;
        std::map<std::string, std::string> restored;
        {
            std::istringstream record_lines(record_text);
            std::string line;
            const std::string version_tag = "_edi.schema_version";
            const std::string renderer_tag = "_rendering_plot.type";
            while (std::getline(record_lines, line)) {
                if (is_tag_line(line, version_tag) && !declared_version.has_value()) {
                    declared_version = lexical_value(line, version_tag.size(), version_tag);
                    continue;
                }
                if (is_tag_line(line, renderer_tag) && !declared_plot_renderer.has_value()) {
                    declared_plot_renderer = lexical_value(line, renderer_tag.size(), renderer_tag);
                    continue;
                }
                for (const char* field : kMetadataFields) {
                    const std::string tag = std::string("_metadata.") + field;
                    if (!is_tag_line(line, tag)) {
                        continue;
                    }
                    // A duplicated field is ambiguous about what the record holds — refuse,
                    // the `_fit_parameter` duplicate rule's shape.
                    if (restored.count(tag) != 0) {
                        throw IoError("project.edi declares " + tag +
                                      " more than once: " + record_where);
                    }
                    restored.emplace(tag, lexical_value(line, tag.size(), tag));
                    break;
                }
            }
        }
        // The format declaration is required, integer, and no newer than the version the
        // delegated writer emits (3): a record from a NEWER writer refuses rather than being
        // misread. The 3 here and crysta's writer constant cannot drift silently — a crysta
        // version bump reds the round-trip gate at crysta's own edi-verification step.
        if (!declared_version.has_value()) {
            throw IoError("project.edi declares no _edi.schema_version: " + record_where);
        }
        {
            std::size_t consumed = 0;
            int version = 0;
            try {
                version = std::stoi(*declared_version, &consumed);
            } catch (const std::exception&) {
                consumed = 0;
            }
            if (consumed != declared_version->size() || version < 1 || version > 3) {
                throw IoError("project.edi declares unsupported _edi.schema_version '" +
                              *declared_version + "' (this loader reads 1..3): " + record_where);
            }
        }
        // `auto` is the one plot renderer: each host draws with its own. Any other declared
        // `_rendering_plot.type` warns naming it, as the calculator and the minimizer do, and the
        // project loads; a missing value (`?`) declares no choice.
        if (declared_plot_renderer.has_value() && !declared_plot_renderer->empty() &&
            *declared_plot_renderer != "auto") {
            warn("unsupported _rendering_plot.type \"" + *declared_plot_renderer +
                 "\" - using auto");
        }
        // / paired-verify ruling: a field the record does not carry keeps its constructed
        // default SILENTLY. Every record committed before then is partial, so an
        // incomplete-record stderr diagnostic fired on every load of the tool's own prior
        // output, forever, and broke the shipped stderr-silence contracts (c09_t9's silent
        // library fit, the machine channel, c11_t35's CLI runs). Nothing saved is being
        // substituted here — what the record carries restores exactly — so silence is not the
        // defect this task removes; the ABSENT-record diagnostic below is unchanged.
        const auto restore = [&restored](const char* field, std::string& into) {
            const auto found = restored.find(std::string("_metadata.") + field);
            if (found != restored.end()) {
                into = found->second;
            }
        };
        restore("name", project.metadata.name);
        restore("title", project.metadata.title);
        restore("description", project.metadata.description);
        restore("created", project.metadata.created);
        restore("last_modified", project.metadata.last_modified);
        restore("timestamp", project.metadata.timestamp);
        // Semantic validity of what was restored: a name carrying a path separator reaches
        // datablock paths on the next save (the binding setter and crysta's writer both refuse
        // it), and a created/last_modified this grammar cannot read would break every later
        // access far from its cause (the binding parses BOTH via star_datetime) — refuse here,
        // at the boundary, instead. `_metadata.timestamp` is deliberately NOT validated: the
        // binding exposes it as an opaque string, and upstream's own written records carry it
        // as ISO-8601 (the committed cosio-d20-scan-3f corpus record) — STAR-validating it
        // refused real saved data.
        if (project_name_has_separator(project.metadata.name)) {
            throw IoError("project.edi _metadata.name '" + project.metadata.name +
                          "' contains a path separator: " + record_where);
        }
        {
            // The accepted domain is the one the public boundary can MATERIALIZE, not merely
            // the lexical shape — `31 Feb 2024 12:34:56` matches the shape, parses through
            // std::get_time (which validates no calendar), and then blows up in the binding's
            // datetime construction at first attribute access, far from the record. So after
            // the shape, the fields are checked as a real calendar datetime: year >= 1 (Python
            // datetime's floor), day within the month (leap Februaries included), clock fields
            // in range.
            static const std::regex star_timestamp(
                R"((\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4}) (\d{2}):(\d{2}):(\d{2}))");
            static const char* const kMonths[12] = {"Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"};
            const auto validate_timestamp = [&record_where](const char* tag,
                                                            const std::string& value) {
                if (value.empty()) {
                    return;
                }
                std::smatch parts;
                if (!std::regex_match(value, parts, star_timestamp)) {
                    throw IoError(std::string("project.edi ") + tag + " '" + value +
                                  "' is not a STAR timestamp ('%d %b %Y %H:%M:%S'): " +
                                  record_where);
                }
                const int day = std::stoi(parts[1]);
                int month = 0;
                while (parts[2] != kMonths[month]) {
                    ++month;
                }
                const int year = std::stoi(parts[3]);
                const int hour = std::stoi(parts[4]);
                const int minute = std::stoi(parts[5]);
                const int second = std::stoi(parts[6]);
                const bool leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
                static const int kDays[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
                const int days_in_month = kDays[month] + (month == 1 && leap ? 1 : 0);
                if (year < 1 || day < 1 || day > days_in_month || hour > 23 || minute > 59 ||
                    second > 59) {
                    throw IoError(std::string("project.edi ") + tag + " '" + value +
                                  "' is not a materializable calendar datetime: " + record_where);
                }
            };
            validate_timestamp("_metadata.created", project.metadata.created);
            validate_timestamp("_metadata.last_modified", project.metadata.last_modified);
        }
    } else {
        // , the packet-committed decision (2026-09-20): a record-less directory is VALID —
        // every directory saved before the record writer landed is in this state, and refusing
        // would make edi's own prior output unopenable. The substitution is no longer silent:
        // exactly one diagnostic line, on stderr, because stdout stays the machine channel's
        // versioned record (`--report machine`).
        warn("no project.edi in '" + directory +
             "' - loading with default metadata (name 'untitled_project')");
    }

    project.path = directory;
    project.metadata.path = directory;
    // A declared template dataset must be one of the scan's files.
    if (!project.sequential_fit.template_file.empty()) {
        check_scan_template_file(project, project.sequential_fit.template_file);
    }
    // Each value outside its admissible range — a fit may leave one there — is loaded and named in one
    // warning; the app marks it red.
    for (const ParameterEntry& entry : parameter_entries(project)) {
        const ParameterSpec* spec = entry.parameter != nullptr ? entry.parameter->spec : nullptr;
        if (spec == nullptr) {
            continue;
        }
        const double value = entry.parameter->value;
        if (value < spec->range.min || value > spec->range.max) {
            std::ostringstream message;
            message.imbue(std::locale::classic());
            message << entry.path << " = " << value << " is outside its admissible range [" << spec->range.min
                    << ", " << spec->range.max << "]; loaded as saved (a fit may leave a value there)";
            warn(message.str());
        }
    }
    // The declared and symmetry relations, as crysta reads them: refused when they cannot hold,
    // every parameter marked, a dependent's free flag cleared with a warning.
    refresh_relations(project, warn);
    return project;
}

double parse_edi_double(const std::string& text, const std::string& where) {
    // Review-10 F2: the ONE numeric boundary, exported for the adapter's start_tied parsing —
    // finite, full-token, classic-locale (the loader's own to_double), so the new column can
    // never re-open the numeric seam the products already resolved.
    return to_double(text, where);
}

void apply_absorption_family(AbsorptionBase& absorption, const std::string& token) {
    // Review-8 F4: the ruled family contract at the MUTATION boundary — the same contract the
    // loader applies to a file, one spelling. A typed family's parameters exist IFF the type
    // says so: "none" clears the body; "cylinder" keeps declared coefficients and supplies a
    // missing one as the owner's general default ("0" ⇒ A ≡ 1); any other token refuses, so a
    // supported mutation can never leave the model in a state its own loaders would reject.
    if (token != "none" && token != "cylinder" && token != "cylinder-hewat" &&
        token != "cylinder-lobanov") {
        throw std::invalid_argument("unknown _absorption.type '" + token +
                                    "' (the registry spells none, cylinder, cylinder-hewat or "
                                    "cylinder-lobanov)");
    }
    absorption.type = token;
    const auto default_coefficient = [](const ParameterSpec& spec) -> Parameter {
        Parameter defaulted = parse_parameter("0", "<absorption-family-default>");
        defaulted.spec = &spec;
        return defaulted;
    };
    if (token == "cylinder") {
        if (!absorption.abscor1.has_value()) {
            absorption.abscor1 = default_coefficient(spec::absorption_abscor1);
        }
        if (!absorption.abscor2.has_value()) {
            absorption.abscor2 = default_coefficient(spec::absorption_abscor2);
        }
        absorption.mu_r.reset();
    } else if (token == "cylinder-hewat" || token == "cylinder-lobanov") {
        // The CW families carry the single mu_r body ("0" ⇒ A ≡ 1), never the pair.
        if (!absorption.mu_r.has_value()) {
            absorption.mu_r = default_coefficient(spec::absorption_mu_r);
        }
        absorption.abscor1.reset();
        absorption.abscor2.reset();
    } else {
        absorption.abscor1.reset();
        absorption.abscor2.reset();
        absorption.mu_r.reset();
    }
}

std::vector<FitStartRow> fit_start_rows(const Project& project) {
    // The rows the writer emits: the slot walk's parameters carrying a start state (the app's
    // `_fit_parameter` table, one row per written row).
    std::vector<FitStartRow> rows;
    for (const auto& [id, parameter] : fit_state_slots(project)) {
        if (parameter->start_value.has_value()) {
            rows.push_back({id, parameter});
        }
    }
    return rows;
}

std::vector<NamedParameter> named_parameters(const Project& project) {
    std::vector<NamedParameter> named;
    for (const auto& slot : parameter_slots(project)) {
        if (slot.parameter->dependence == Dependence::Independent) {
            named.push_back({slot.unique_name, slot.parameter});
        }
    }
    return named;
}

std::vector<NamedParameter> named_dependents(const Project& project) {
    std::vector<NamedParameter> named;
    for (const auto& slot : parameter_slots(project)) {
        if (slot.parameter->dependence != Dependence::Independent) {
            named.push_back({slot.unique_name, slot.parameter});
        }
    }
    return named;
}

std::vector<NamedSlot> named_slots(Project& project) {
    std::vector<NamedSlot> named;
    for (const auto& slot : parameter_slots(project)) {
        named.push_back({slot.unique_name, slot.parameter});
    }
    return named;
}

UndoFitOutcome undo_fit(Project& project) {
    const UndoFitOutcome outcome = restore_fit_start(project);
    if (!outcome.was_no_op) {
        // / crysta, the undo half: an undone model is the PRE-FIT model, so the stored
        // calculated pattern must be the pre-fit one too. Without this, undoing left the FITTED
        // pattern beside pre-fit parameters — the same silent inconsistency the fit paths had.
        // Measured before the fix (LBCO/HRPT, 8 parameters restored): the stored pattern
        // disagreed with a fresh calculate by 2.679e+03 counts. Inside the was_no_op guard and
        // last, exactly as the fit tail: an undo that restores NOTHING still changes nothing.
        project.refresh_calculated_pattern();
    }
    return outcome;
}

UndoFitOutcome restore_fit_start(Project& project) {
    // Restore each parameter carrying persisted start state and clear the snapshot; report the
    // structured outcome (upstream UndoFitOutcome). No persisted state = a reported no-op that
    // changes NOTHING, so a second undo is idempotent by construction. The walk is the writer's
    // own fit_state_slots, so undo restores exactly what the file persisted.
    UndoFitOutcome outcome;
    std::set<const Parameter*> restored;
    for (const auto& [id, parameter] : fit_state_slots(project)) {
        if (!parameter->start_value.has_value()) {
            continue;
        }
        parameter->value = *parameter->start_value;
        parameter->uncertainty = parameter->start_uncertainty;
        parameter->start_value.reset();
        parameter->start_uncertainty.reset();
        restored.insert(parameter);
        outcome.restored_parameters.push_back(id);
    }
    outcome.was_no_op = outcome.restored_parameters.empty();
    if (!outcome.was_no_op) {
        // Review-7 F1 (edi half): a restored representative pulls its symmetry-tied dependents
        // back too. Review-9 F1: the snapshot may ride a non-representative free axis, so the
        // positional pass derives the basic back from the restored axis sign-correctly and
        // never touches a fixed axis's uncertainty presence — an undone model matches the
        // pre-fit state on every axis. A no-op undo changes NOTHING, so the second undo stays
        // idempotent by construction.
        for (const auto& structure : project.structures) {
            restore_positional_dependents(*structure, restored);
        }
        // Every dependent follows its restored independents through crysta's applier and gets
        // back the e.s.d. it held before the fit.
        restore_dependents(project);
        clear_fit_result(project);  // The undone fit's result goes with it
    }
    return outcome;
}

void copy_fit_result(Project& to, const Project& from) {
    to.fit_result = from.fit_result;
    for (std::size_t index = 0; index < to.experiments.size() && index < from.experiments.size(); ++index) {
        ExperimentBase& target = *to.experiments[index];
        const ExperimentBase& source = *from.experiments[index];
        target.fit_n_data_points = source.fit_n_data_points;
        target.fit_prof_wr_factor = source.fit_prof_wr_factor;
        target.fit_chi_square = source.fit_chi_square;
    }
}

void clear_fit_result(Project& project) {
    project.fit_result = FitResultRecord{};
    for (const auto& experiment_item : project.experiments) {
        experiment_item->fit_n_data_points.reset();
        experiment_item->fit_prof_wr_factor.reset();
        experiment_item->fit_chi_square.reset();
    }
}

void save_project(const Project& project, const std::string& directory) {
    // Edi's writer body is RETIRED — edi does not write, it asks crysta to: every structure, every
    // validation, the staging and the atomic publish are crysta's writer's own.
    // Review r63 F-b: refuse a datablock name carrying a reserved fit-identity delimiter BEFORE
    // any conversion or write — `.`, `[` and `]` are structural in the shared `_fit_parameter`
    // id grammar (`<exp>.<label>`, `<exp>.background[<i>]`), so a name containing them would
    // make its parameters unaddressable. Input validation, the one thing this shell owns;
    // serialization stays crysta's.
    const auto refuse_reserved_name = [](const std::string& name, const char* role) {
        if (name.find_first_of(".[]") != std::string::npos) {
            throw IoError(std::string(role) + " datablock name '" + detail::printable_id(name) +
                          "' carries a reserved identity delimiter ('.', '[' or ']'): the "
                          "shared fit-parameter id grammar cannot address its parameters");
        }
    };
    for (const auto& structure : project.structures) {
        refuse_reserved_name(structure->name, "structure");
    }
    for (const auto& experiment_item : project.experiments) {
        refuse_reserved_name(experiment_item->name, "experiment");
    }
    try {
        save_project_via_crysta(project, directory);
    } catch (const IoError&) {  // a coded refusal (a ValidationError) keeps its codes
        throw;
    } catch (const std::exception& error) {
        throw IoError(error.what());
    }
}

void save_project_as(Project& project, const std::string& directory) {
    const std::string previous = project.metadata.last_modified;
    project.metadata.update_last_modified();
    try {
        save_project(project, directory);
    } catch (...) {
        project.metadata.last_modified = previous;
        throw;
    }
    project.path = directory;
    project.metadata.path = directory;
    // The saved project holds its scan data: it reads them from its own directory from now on.
    project.scan_data_root.clear();
}


// ----: the text a save writes ------------------------------------------

namespace {

// A save of the project into a fresh scratch directory, removed when this object goes.
class ScratchSave {
   public:
    explicit ScratchSave(const Project& project) {
        std::random_device random;
        for (int attempt = 0; root_.empty(); ++attempt) {
            const fs::path candidate =
                fs::temp_directory_path() / ("edi-block-text-" + std::to_string(random()));
            if (fs::create_directory(candidate)) {
                root_ = candidate;
            } else if (attempt == 16) {
                throw IoError("cannot create a scratch directory under " +
                              fs::temp_directory_path().string());
            }
        }
        // The save starts from a source holding only the project record. Seeded from the project's own
        // directory it would copy every file there, a scan's data included, to write a few small texts.
        const fs::path source = root_ / "source";
        fs::create_directories(source);
        if (!project.path.empty()) {
            std::error_code absent;
            fs::copy_file(fs::path(project.path) / "project.edi", source / "project.edi", absent);
        }
        Project unseeded = project;
        unseeded.path = source.string();
        unseeded.scan_data_root.clear();
        save_project(unseeded, (root_ / "project").string());
    }
    ~ScratchSave() {
        std::error_code ignored;
        fs::remove_all(root_, ignored);
    }
    ScratchSave(const ScratchSave&) = delete;
    ScratchSave& operator=(const ScratchSave&) = delete;

    // The written file's text, or empty when the writer wrote no such file.
    std::string text(const std::string& relative) const {
        const fs::path path = root_ / "project" / relative;
        return fs::is_regular_file(path) ? read_file(path.string()) : std::string();
    }

   private:
    fs::path root_;
};

// The files a save writes, as paths relative to the project directory, in the loader's order.
std::vector<std::string> saved_file_order(const Project& project) {
    std::vector<std::string> files{"project.edi"};
    // ADR-0016: the paths come from the one path decision.
    for (const auto& structure : project.structures) {
        files.push_back(fs::path(entity_path("", "structure", structure->name)).generic_string());
    }
    for (const auto& experiment : project.experiments) {
        files.push_back(
            fs::path(entity_path("", "experiment", experiment->name)).generic_string());
    }
    files.emplace_back("analysis/analysis.edi");
    return files;
}

}  // namespace

std::string block_edi_text(const Project& project, BlockKind kind, const std::string& name) {
    const ScratchSave save(project);
    switch (kind) {
        case BlockKind::PROJECT: return save.text("project.edi");
        case BlockKind::STRUCTURE: return save.text(entity_path("", "structure", name));
        case BlockKind::EXPERIMENT: return save.text(entity_path("", "experiment", name));
        case BlockKind::ANALYSIS: break;
    }
    return save.text("analysis/analysis.edi");
}

std::vector<std::pair<std::string, std::string>> project_edi_files(const Project& project) {
    const ScratchSave save(project);
    std::vector<std::pair<std::string, std::string>> files;
    for (const std::string& relative : saved_file_order(project)) {
        std::string text = save.text(relative);
        if (!text.empty()) {
            files.emplace_back(relative, std::move(text));
        }
    }
    return files;
}
}  // namespace edi
