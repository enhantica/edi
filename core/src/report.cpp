// SPDX-License-Identifier: BSD-3-Clause
#include "edi/report.hpp"

#include "crysta/dictionary_items.hpp"
#include "edi/report_model.hpp"

#include "crysta/fit_report.hpp"
#include "edi/categories.hpp"
#include "edi/display.hpp"
#include "edi/parameter_walk.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <iomanip>
#include <locale>
#include <map>
#include <optional>
#include <sstream>
#include <unordered_map>
#include <vector>

// . The machine half is a straight call into the engine's emitter; everything else here is edi's
// own human view, which is the only reason this file is long. Presentation lives in the product
// core (not in a CLI, not in an example) so every edi surface renders one implementation.

namespace edi {
namespace {

// The refined-parameter table's reserved column widths. Data rows are ASCII, so character width is
// display width. The label column is wide because edi keys results by full identity paths
// (`experiments[wish_1_10].background[10].intensity`) rather than by short engine labels; a
// narrower column would ragged the numeric columns on almost every row.
constexpr int kLabelWidth = 48;
constexpr int kNameWidth = 16;

// The iteration table's columns: iter (7) and time (11), which no dictionary item names, then Rwp
// (10) and reduced χ² (12), whose labels and units are the dictionary's, then the change.
constexpr int kIterWidth = 7;
constexpr int kTimeWidth = 11;
constexpr int kRwpWidth = 10;
constexpr int kChiWidth = 12;

// Human-facing numbers are formatted for reading, not for comparison — the machine record is the
// comparison channel. Still classic-locale, so the two views cannot disagree about a decimal point.
// Rwp and χ² are the dictionary's (metric below); this is for the time and change columns, which have
// no dictionary item.
std::string fixed(double value, int precision, int width = 0) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    if (width > 0) {
        out << std::setw(width);
    }
    out << std::fixed << std::setprecision(precision) << value;
    return out.str();
}

// The dictionary item of an identity path read off the path, for a table printed without its project. A path is a
// root, then a category or a collection's row `<collection>[<id>]`, then the item's name after the last dot
// (`structure.atom_sites[Co].adp_iso` is `atom_site.adp_iso`). An id may hold any character, brackets and dots
// included, so the reading never counts brackets: the category is the word after the last dot before the name, and a
// row's collection a word between a dot and an opening bracket, its plural `s` left out, taken only when the
// dictionary has the name in it. Empty when the dictionary has none.
std::string item_of(const std::string& path) {
    const std::size_t last = path.rfind('.');
    if (last == std::string::npos) {
        return {};
    }
    const std::string name = path.substr(last + 1);
    const std::string head = path.substr(0, last);
    const auto item = [&name](const std::string& category) {
        for (const std::string& candidate :
             {category, category.ends_with('s') ? category.substr(0, category.size() - 1) : std::string()}) {
            if (!candidate.empty() && has_item(candidate + "." + name)) {
                return candidate + "." + name;
            }
        }
        return std::string();
    };
    if (!head.ends_with(']')) {
        const std::size_t dot = head.rfind('.');
        return dot == std::string::npos ? std::string() : item(head.substr(dot + 1));
    }
    for (std::size_t open = head.find('['); open != std::string::npos; open = head.find('[', open + 1)) {
        if (const std::size_t dot = head.rfind('.', open); dot != std::string::npos) {
            if (std::string uid = item(head.substr(dot + 1, open - dot - 1)); !uid.empty()) {
                return uid;
            }
        }
    }
    return {};
}

// A number of a fitted parameter: by its dictionary format, or to five decimals for a path the dictionary has
// no item for.
std::string padded_left(std::string text, int width) {
    if (static_cast<int>(text.size()) < width) {
        text.insert(0, static_cast<std::size_t>(width) - text.size(), ' ');
    }
    return text;
}

std::string number_of(const std::string& uid, double value, int width, const std::string& variant = {}) {
    return padded_left(uid.empty() ? fixed(value, 5) : display_text(uid, value, variant), width);
}

// A fit metric of item `uid` by its dictionary format for `variant`, right-aligned to `width` (Rwp in percent, χ²).
std::string metric(const char* uid, double value, int width = 0, const std::string& variant = {}) {
    std::string text = display_text(uid, value, variant);
    if (static_cast<int>(text.size()) < width) {
        text.insert(0, static_cast<std::size_t>(width) - text.size(), ' ');
    }
    return text;
}

// The characters `text` shows, counted as UTF-8 code points.
int shown_width(const std::string& text) {
    int shown = 0;
    for (const char byte : text) {
        shown += (static_cast<unsigned char>(byte) & 0xC0U) != 0x80U ? 1 : 0;
    }
    return shown;
}

// A metric in its column, with at least one space before it when it is as wide as the column (a
// reduced χ² of 140198364.17 would otherwise run into the Rwp before it).
std::string metric_column(const char* uid, double value, int width) {
    std::string text = metric(uid, value, width);
    if (shown_width(text) >= width) {
        text.insert(0, 1, ' ');
    }
    return text;
}

// Pads to `width` characters, counted as UTF-8 code points, so a label with Å or ² keeps the columns aligned.
void append_padded(std::ostringstream& out, const std::string& text, int width) {
    out << text;
    for (int pad = shown_width(text); pad < width; ++pad) {
        out << ' ';
    }
}

// `text` right-aligned to `width` characters, as append_padded counts them.
std::string right_aligned(const std::string& text, int width) {
    return std::string(static_cast<std::size_t>(std::max(0, width - shown_width(text))), ' ') + text;
}

// A metric's dictionary label for `variant`, with its units in brackets when it has some (`Rwp (%)`).
std::string metric_header(const char* uid, const std::string& variant = {}) {
    const std::string units = units_label(uid, variant);
    return units.empty() ? label(uid, variant) : label(uid, variant) + " (" + units + ")";
}

// The width of the iteration table's profile-factor column: its header and a space, the powder width at least.
int rwp_width(const std::string& variant) {
    return std::max(kRwpWidth, shown_width(metric_header("fit_result.prof_wr_factor", variant)) + 1);
}

// The iteration table's header, aligned to iteration_line's columns.
std::string iteration_header(const std::string& variant) {
    return right_aligned("iter", kIterWidth) + right_aligned(metric_header("fit_result.fitting_time"), kTimeWidth) +
           right_aligned(metric_header("fit_result.prof_wr_factor", variant), rwp_width(variant)) +
           right_aligned(metric_header("fit_result.reduced_chi_square"), kChiWidth) + "   change";
}

}  // namespace

// The seam-S18 presentation contract; see report.hpp for the rule. This is its ONE implementation,
// shared by the streaming progress line and the `full` parameter table — and it is public so the
// contract can be exercised on constructed values rather than only on whatever a live fit happens
// to produce.
std::string change_percent(double current, double previous) {
    // A percentage of zero is undefined, not infinite, and a non-finite operand cannot yield a
    // meaningful one either. Both blank rather than rendering a number a reader would trust.
    if (previous == 0.0 || !std::isfinite(previous) || !std::isfinite(current)) {
        return {};
    }
    // The denominator is the START value: this column answers "how far has it moved from where it
    // began", so using the refined value would silently change the question.
    const double percent = (current - previous) / std::fabs(previous) * 100.0;
    if (std::fabs(percent) < 0.05) {
        return {};  // immaterial — show nothing rather than noise
    }
    if (std::fabs(percent) >= 1000.0) {
        return table_number(std::fabs(percent), {}, false) + " %";
    }
    return fixed(std::fabs(percent), 1) + "%";
}

std::string format_change(double current, double previous) {
    const std::string percent = change_percent(current, previous);
    if (percent.empty()) return {};
    return percent + (current < previous ? " \u2193" : " \u2191");
}

namespace {

bool in_decimal_range(double value) {
    const double size = std::fabs(value);
    return value == 0.0 || !std::isfinite(value) || (size >= 0.001 && size < 1000.0);
}

// The power of ten of a value's first significant digit.
int power_of(double value) { return static_cast<int>(std::floor(std::log10(std::fabs(value)))); }

std::string exponent_text(int power, bool display) {
    if (!display) return "e" + std::to_string(power);
    static const char* const digits[] = {"\u2070", "\u00B9", "\u00B2", "\u00B3", "\u2074",
                                         "\u2075", "\u2076", "\u2077", "\u2078", "\u2079"};
    std::string out = "\u00D710";
    if (power < 0) out += "\u207B";
    for (const char digit : std::to_string(std::abs(power))) out += digits[digit - '0'];
    return out;
}

// A decimal number's text with its point moved `shift` places left (right for a negative shift), keeping its last digit
// in place: "0.000000000186515" by -10 is "1.86515"; "7453675696" by 9 is "7.453675696".
std::string shifted(const std::string& text, int shift) {
    std::string sign, digits = text;
    if (!digits.empty() && (digits[0] == '-' || digits[0] == '+')) {
        sign = digits.substr(0, 1);
        digits = digits.substr(1);
    }
    const std::size_t dot = digits.find('.');
    std::string whole = dot == std::string::npos ? digits : digits.substr(0, dot);
    std::string fraction = dot == std::string::npos ? std::string() : digits.substr(dot + 1);
    std::string all = whole + fraction;
    long point = static_cast<long>(whole.size()) - shift;  // the point's place in `all`
    if (point <= 0) {
        all.insert(0, static_cast<std::size_t>(1 - point), '0');
        point = 1;
    }
    if (point > static_cast<long>(all.size())) all.append(static_cast<std::size_t>(point) - all.size(), '0');
    std::string left = all.substr(0, static_cast<std::size_t>(point));
    const std::string right = all.substr(static_cast<std::size_t>(point));
    const std::size_t first = left.find_first_not_of('0');
    left = first == std::string::npos ? "0" : left.substr(first);
    return sign + left + (right.empty() ? std::string() : "." + right);
}

// "6.33e-3" as the decimal "0.00633", keeping its digits; any other text is returned as it is.
std::string expanded(const std::string& text) {
    const std::size_t e = text.find_first_of("eE");
    if (e == std::string::npos || e == 0) return text;
    const std::string mantissa = text.substr(0, e);
    const std::string power = text.substr(e + 1);
    const std::size_t start = !mantissa.empty() && (mantissa[0] == '-' || mantissa[0] == '+') ? 1 : 0;
    if (start >= mantissa.size() || mantissa.find_first_not_of("0123456789.", start) != std::string::npos) return text;
    const std::size_t digits = !power.empty() && (power[0] == '-' || power[0] == '+') ? 1 : 0;
    if (digits >= power.size() || power.find_first_not_of("0123456789", digits) != std::string::npos) return text;
    return shifted(mantissa, -std::stoi(power));
}

// A decimal text without the zeros that end its fraction ("0.500" is "0.5").
std::string trimmed(std::string text) {
    if (text.find('.') == std::string::npos) return text;
    text.erase(text.find_last_not_of('0') + 1);
    if (!text.empty() && text.back() == '.') text.pop_back();
    return text;
}

// A decimal text cut to `decimals` places, for digits known to be zeros.
std::string cut(const std::string& text, int decimals) {
    const std::size_t dot = text.find('.');
    if (dot == std::string::npos) return text;
    return decimals <= 0 ? text.substr(0, dot) : text.substr(0, std::min(text.size(), dot + 1 + decimals));
}

// The power of ten of the last digit a whole-number s.u. text keeps: its last nonzero digit, or one place lower for an
// s.u. starting with 1 (written with two digits). Nothing for a text with a fraction.
std::optional<int> whole_su_place(const std::string& su) {
    if (su.empty() || su.find('.') != std::string::npos) return std::nullopt;
    const std::size_t first = su.find_first_of("123456789");
    if (first == std::string::npos) return std::nullopt;
    const std::size_t last = su.find_last_of("123456789");
    int place = static_cast<int>(su.size() - 1 - last);
    if (su[first] == '1' && first == last) place = std::max(0, place - 1);
    return place;
}

// An s.u. shown alone: a decimal inside the range, else in its own power of ten with its own digits ("0.00025" is
// "2.5×10⁻⁴", "1600" is "1.6×10³").
std::string su_alone(const std::string& su, bool display) {
    char* end = nullptr;
    const double number = su.empty() ? 0.0 : std::strtod(su.c_str(), &end);
    if (su.empty() || end == su.c_str() || *end != '\0' || number == 0.0 || in_decimal_range(number)) return su;
    const int power = power_of(number);
    std::string mantissa = shifted(su, power);
    if (const std::optional<int> place = whole_su_place(su); place.has_value()) mantissa = cut(mantissa, power - *place);
    return mantissa + exponent_text(power, display);
}

}  // namespace

std::string table_number(double value, const std::string& decimal, bool display) {
    if (!std::isfinite(value)) return decimal;
    if (in_decimal_range(value)) {
        const bool exponent = decimal.find_first_of("eE") != std::string::npos;
        std::string text = exponent ? trimmed(expanded(decimal)) : decimal;
        // A format that rounds a nonzero value to zero ("0.00") shows its first three significant digits instead.
        char* end = nullptr;
        const double shown = text.empty() ? 0.0 : std::strtod(text.c_str(), &end);
        if (value != 0.0 && (text.empty() || shown == 0.0)) {
            char digits[32];
            std::snprintf(digits, sizeof(digits), "%.3g", value);
            text = trimmed(expanded(digits));
        }
        return text;
    }
    const int power = power_of(value);
    char mantissa[32];
    std::snprintf(mantissa, sizeof(mantissa), "%.2f", value / std::pow(10.0, power));
    std::string text = mantissa;
    if (text == "10.00" || text == "-10.00") {  // 9.996e-11 rounds up to 1.00e-10
        return table_number(value >= 0 ? std::pow(10.0, power + 1) : -std::pow(10.0, power + 1), decimal, display);
    }
    return text + exponent_text(power, display);
}

std::pair<std::string, std::string> table_value_su(double value, const std::string& value_text,
                                                   const std::string& su_text, bool display) {
    if (!std::isfinite(value)) return {value_text, su_text};
    const std::string number = expanded(value_text), su = expanded(su_text);
    if (in_decimal_range(value)) return {number, display ? su_alone(su, display) : su};
    const int power = power_of(value);
    const std::string exponent = exponent_text(power, display);
    std::string shown = shifted(number, power);
    std::string shown_su = su.empty() ? su : shifted(su, power);
    // A whole-number pair keeps the digits down to the s.u.'s last one, not the zeros after it.
    if (const std::optional<int> place = whole_su_place(su);
        place.has_value() && number.find('.') == std::string::npos) {
        shown = cut(shown, power - *place);
        shown_su = cut(shown_su, power - *place);
    }
    return {shown + exponent, shown_su.empty() ? shown_su : shown_su + exponent};
}

std::string table_text(double value, const std::string& text, bool display) {
    const std::size_t bracket = text.find('(');
    const std::string number = expanded(text.substr(0, bracket));
    const std::string rest = bracket == std::string::npos ? std::string() : text.substr(bracket);
    if (in_decimal_range(value)) return bracket == std::string::npos ? table_number(value, text, display) : number + rest;
    // Without an s.u. the value alone decides, whatever notation the text came in ("1.8652e-10").
    if (bracket == std::string::npos) return table_number(value, text, display);
    const int power = power_of(value);
    return shifted(number, power) + rest + exponent_text(power, display);
}

std::string display_exponents(const std::string& text) {
    std::string out;
    std::size_t at = 0;
    while (at < text.size()) {
        const std::size_t e = text.find('e', at);
        if (e == std::string::npos) break;
        std::size_t end = e + 1;
        if (end < text.size() && text[end] == '-') ++end;
        const std::size_t digits = end;
        while (end < text.size() && std::isdigit(static_cast<unsigned char>(text[end]))) ++end;
        const bool number_before = e > 0 && std::isdigit(static_cast<unsigned char>(text[e - 1]));
        if (!number_before || end == digits) {
            out += text.substr(at, e + 1 - at);
            at = e + 1;
            continue;
        }
        out += text.substr(at, e - at) + exponent_text(std::stoi(text.substr(e + 1, end - e - 1)), true);
        at = end;
    }
    return out + text.substr(at);
}

namespace {

// edi verbosity -> the engine emitter's. Confined to this TU, like every other crysta contact.
crysta::VerbosityEnum to_engine(VerbosityEnum verbosity) {
    switch (verbosity) {
        case VerbosityEnum::OFF:
            return crysta::VerbosityEnum::Off;
        case VerbosityEnum::COMPACT:
            return crysta::VerbosityEnum::Compact;
        case VerbosityEnum::FULL:
            return crysta::VerbosityEnum::Full;
    }
    return crysta::VerbosityEnum::Off;
}

// edi status -> the engine's. The two sets are deliberately the same shape; this mapping is what
// keeps them from having to be the same TYPE on edi's public surface.
crysta::FitStatus to_engine(FitStatus status) {
    switch (status) {
        case FitStatus::DONE:
            return crysta::FitStatus::Done;
        case FitStatus::MAX_ITER:
            return crysta::FitStatus::MaxIter;
        case FitStatus::NO_STEP:
            return crysta::FitStatus::NoStep;
        case FitStatus::CANCELLED:
            return crysta::FitStatus::Cancelled;
        case FitStatus::ERROR:
            return crysta::FitStatus::Error;
        case FitStatus::UNAVAILABLE:
            return crysta::FitStatus::Unavailable;
        case FitStatus::SUPERSEDED:
            return crysta::FitStatus::Superseded;
    }
    return crysta::FitStatus::Error;
}

// edi's per-iteration record -> the engine's. crysta merged its streamed IterationRecord and the
// report's history row into ONE type, so the row is filled by name: only the members the record
// renders (iter / rwp / reduced_chi_square / elapsed_ms / unevaluable_trials) cross here;
// `chi_square` and `parameters` stay at their defaults, exactly as the emitter leaves them unread.
crysta::IterationRecord to_engine(const IterationRecord& record) {
    crysta::IterationRecord row;
    row.iteration = record.iteration;
    row.rwp = record.rwp;
    row.reduced_chi_square = record.reduced_chi_square;
    row.elapsed_ms = record.elapsed_ms;
    row.unevaluable_trials = record.unevaluable_trials;
    return row;
}

}  // namespace

std::string machine_report(const Project& project, const FitResultBase& outcome,
                           VerbosityEnum verbosity) {
    crysta::FitReport report;
    report.kind = crysta::RecordKind::Fit;
    report.status = to_engine(outcome.status);
    // Which refinement ran, not what the project could hold: `banks` is populated by the joint path
    // and left empty by the single-bank one, exactly as crysta emits mode=joint only from its joint
    // path. Deriving this from `project.experiments` instead would label a single-bank refine of a
    // multi-bank project as joint.
    report.joint = !outcome.banks.empty();
    report.mode = outcome.mode;  // independent experiments name their mode (ADR-0081)
    report.converged = outcome.converged;
    report.n_points_loaded = outcome.n_points_loaded;
    report.n_points_fitted = outcome.n_points_fitted;
    // The count of refined parameters, taken from the engine-keyed map so it can never disagree with
    // the number of `param.*` rows below it.
    report.n_free = outcome.engine_values.size();
    report.iterations = outcome.iterations;
    // Schema 7: a fit record must name the descent flow that ran; carried verbatim from
    // the engine result.
    report.descent = outcome.descent;
    report.reduced_chi_square = outcome.reduced_chi_square;
    report.rwp = outcome.rwp;
    // What stopped the fit, its value and the last step's largest shift/s.u., as the engine gave them.
    report.stopping_rule = outcome.stopping_rule;
    report.stopping_value = outcome.stopping_value;
    report.last_shift_su = outcome.last_shift_su;
    // The default descent's probe accounting, as crysta emits it for the same fit.
    report.multistart_prune = outcome.descent == default_descent();
    report.multistart_probes_started = outcome.multistart_probes_started;
    report.multistart_probes_pruned = outcome.multistart_probes_pruned;
    report.multistart_probe_iterations = outcome.multistart_probe_iterations;
    report.multistart_survivor = outcome.multistart_survivor.empty() ? "none" : outcome.multistart_survivor;
    report.fast_descent = outcome.fast_descent;
    // `cutoff_policy` is LEFT EMPTY on purpose, which omits the row: edi exposes no cutoff-policy
    // control, and a surface that cannot vary a field must not emit a constant for it. It shows up
    // as a plain added line when diffing against crysta — the honest representation of a capability
    // edi does not have, rather than a field that looks aligned while hiding the asymmetry. The
    // boundary-contact counters are the ENGINE's values carried through the outcome — never edi
    // defaults: a record that always said 0 would erase exactly the signal that distinguishes
    // boundary-limited convergence from an interior optimum.
    report.unevaluable_trials = outcome.unevaluable_trials;
    report.terminal_unevaluable_trials = outcome.terminal_unevaluable_trials;
    report.elapsed_ms = outcome.elapsed_ms;
    for (const IterationRecord& record : outcome.iterations_history) {
        report.history.push_back(to_engine(record));
    }
    // Engine labels, not edi identity paths: the record is crysta's artifact and must use crysta's
    // parameter identity on every surface, or the per-parameter rows could never be compared.
    report.values = outcome.engine_values;
    report.uncertainty = outcome.engine_uncertainty;
    for (const BankMetric& bank : outcome.banks) {
        report.banks.push_back({bank.name, bank.n_points, bank.rwp, bank.chi_square});
    }
    // edi's own key: how many parameter pairs the fit's correlations hold (analysis.edi's
    // `_fit_parameter_correlation` rows).
    report.extra.emplace_back("x-edi.correlations", std::to_string(outcome.correlations.size()));
    return crysta::format_fit_report(report, to_engine(verbosity));
}

std::string error_report(VerbosityEnum verbosity) {
    // Rendered by the same engine emitter as every other shape, so the failure record cannot drift
    // from the contract the success records follow.
    return crysta::format_fit_report(crysta::make_error_report(), to_engine(verbosity));
}

std::string calc_report(std::size_t n_points, double checksum, double elapsed_ms,
                        VerbosityEnum verbosity) {
    // The engine's own calc record: make_calc_report + the shared emitter, exactly the path
    // `crysta <dir> calc` renders through, so the bytes cannot drift from crysta's.
    return crysta::format_fit_report(crysta::make_calc_report(n_points, checksum, elapsed_ms),
                                     to_engine(verbosity));
}

namespace {

// Scan-line building blocks, file-internal: the two public renderers below are the surface. The
// bar width is fixed — the packet's ~80-column budget; a real-terminal measurement narrowing it
// changes this ONE constant.
constexpr int kScanBarCells = 14;

// `MmSSs` / `Ss` / `HhMMmSSs`, rounded to whole seconds — a progress line reads as a clock, not
// a measurement (the machine record carries exact elapsed_ms; this channel is the human one).
std::string scan_duration(double seconds) {
    const long long total = static_cast<long long>(seconds + 0.5);
    char buffer[48];
    if (total < 60) {
        std::snprintf(buffer, sizeof buffer, "%llds", total);
    } else if (total < 3600) {
        std::snprintf(buffer, sizeof buffer, "%lldm%02llds", total / 60, total % 60);
    } else {
        std::snprintf(buffer, sizeof buffer, "%lldh%02lldm%02llds", total / 3600,
                      (total % 3600) / 60, total % 60);
    }
    return buffer;
}

// The display stem (fs::path::stem semantics on a bare name): the scan file's extension is walk
// plumbing, not identity — the owner's requested line names files as `cosio_213K`, never `.dat`.
std::string scan_display_name(const std::string& file_name) {
    const std::size_t dot = file_name.rfind('.');
    return dot != std::string::npos && dot > 0 ? file_name.substr(0, dot) : file_name;
}

// Review-1 F2: a duration whose population differs from the line's counts must SAY so, or the
// reader takes it for the scan's. `measured` is what the clock covered, `population` the count
// the rest of the line reports; equal means a fresh scan and the text is unchanged.
std::string scan_elapsed_suffix(const std::string& duration, int measured, int population) {
    return measured < population ? duration + " this run" : duration;
}

std::string scan_elapsed(double seconds, int measured, int population) {
    return scan_elapsed_suffix(scan_duration(seconds), measured, population);
}

void append_scan_part(std::string& line, const std::string& part) {
    if (!line.empty()) {
        line += " · ";
    }
    line += part;
}

}  // namespace

std::string scan_progress_line(int completed, std::optional<int> total_files,
                               double elapsed_seconds, int measured_completed, int ok_count,
                               int fail_count, const std::string& file_name,
                               double reduced_chi_square) {
    std::string line;
    if (total_files.has_value() && *total_files > 0) {
        const int filled = static_cast<int>(
            kScanBarCells * static_cast<double>(completed) / *total_files + 0.5);
        std::string bar = "[";
        for (int cell = 0; cell < filled; ++cell) {
            bar += "█";
        }
        for (int cell = filled; cell < kScanBarCells; ++cell) {
            bar += "░";
        }
        bar += "]";
        append_scan_part(line, bar);
        append_scan_part(line, std::to_string(completed) + "/" + std::to_string(*total_files));
        const int percent =
            static_cast<int>(100.0 * completed / *total_files + 0.5);
        append_scan_part(line, std::to_string(percent) + "%");
    } else {
        // N unknown: a bare count, NO percentage and NO eta — degrade rather than guess.
        append_scan_part(line, std::to_string(completed) + " files");
    }
    append_scan_part(line,
                     "elapsed " + scan_elapsed(elapsed_seconds, measured_completed, completed));
    if (total_files.has_value() && measured_completed > 0 && completed < *total_files) {
        // mean(elapsed over the completions the clock COVERS) × remaining — an ESTIMATE, and
        // labelled as one. The denominator is `measured_completed`, never `completed`: on a
        // resumed scan the elapsed covers only this call's files, so dividing by the whole-scan
        // total would pair one population's time with another's count and systematically
        // under-estimate.
        const double eta = elapsed_seconds / measured_completed * (*total_files - completed);
        append_scan_part(line, "eta " + scan_duration(eta));
    }
    append_scan_part(line, std::to_string(ok_count) + " ok");
    append_scan_part(line, std::to_string(fail_count) + " fail");
    if (!total_files.has_value() || completed < *total_files) {
        append_scan_part(line, scan_display_name(file_name));
        append_scan_part(line, label("fit_result.reduced_chi_square") + " " +
                                   display_text("fit_result.reduced_chi_square", reduced_chi_square));
    }
    return line;
}

std::string scan_summary(int total_files, int ok_count, int fail_count, double chi2_min,
                         double chi2_max, double elapsed_seconds, int measured_completed) {
    std::string line;
    append_scan_part(line, "scan");
    append_scan_part(line, std::to_string(total_files) + " files");
    append_scan_part(line, std::to_string(ok_count) + " converged");
    append_scan_part(line, std::to_string(fail_count) + " failed");
    // A non-finite bound means the scan's committed rows produced no χ² at all: the group
    // renders NOTHING rather than a number no fit produced — the same blank rule format_change
    // follows. (the caller's fold now spans the resume rows too, so a resumed scan
    // reaches this blank only when nothing anywhere recorded one.)
    if (std::isfinite(chi2_min) && std::isfinite(chi2_max)) {
        append_scan_part(line, label("fit_result.reduced_chi_square") + " " +
                                   display_text("fit_result.reduced_chi_square", chi2_min) + "-" +
                                   display_text("fit_result.reduced_chi_square", chi2_max));
    }
    // The duration is the ONE quantity history cannot supply, so it is rendered on its own
    // basis or not at all: nothing fitted this call means no duration to report (a completed
    // scan re-run as a no-op would otherwise print `0s` as the scan's time), and a partial
    // resume says which run the number describes.
    if (measured_completed > 0) {
        append_scan_part(line,
                         scan_elapsed_suffix(scan_duration(elapsed_seconds), measured_completed,
                                             ok_count + fail_count));
    }
    line += "\n";
    return line;
}

std::string iteration_line(const IterationRecord& record, double previous_reduced_chi2, const std::string& variant) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << std::setw(kIterWidth) << record.iteration << fixed(record.elapsed_ms / 1000.0, 3, kTimeWidth)
        << metric("fit_result.prof_wr_factor", record.rwp, rwp_width(variant), variant)
        << metric_column("fit_result.reduced_chi_square", record.reduced_chi_square, kChiWidth) << "   "
        << format_change(record.reduced_chi_square, previous_reduced_chi2);
    return out.str();
}

// File-internal: its binding left the surface; stream_header renders the starting row
// through it.
static std::string pre_fit_line(const IterationRecord& pre_fit, const std::string& variant) {
    // The starting row (iteration 0): iter (7) and time (11) columns blank, only Rwp (10) and
    // reduced χ² (12); no change column (there is no previous basis). Aligned to iteration_line's
    // widths so the pre-fit row and the iteration rows share one column grid.
    std::ostringstream out;
    out.imbue(std::locale::classic());
    out << std::string(kIterWidth + kTimeWidth, ' ')
        << metric("fit_result.prof_wr_factor", pre_fit.rwp, rwp_width(variant), variant)
        << metric_column("fit_result.reduced_chi_square", pre_fit.reduced_chi_square, kChiWidth);
    return out.str();
}

std::string stream_header(const FitPreamble& preamble, const std::string& project_name, const std::string& variant) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    if (preamble.joint) {
        std::string banks;
        for (std::size_t index = 0; index < preamble.banks.size(); ++index) {
            banks += (index == 0 ? "" : ", ") + preamble.banks[index];
        }
        out << "edi fit: joint project " << project_name << ", " << preamble.banks.size()
            << (preamble.banks.size() == 1 ? " bank (" : " banks (") << banks << "), ";
    } else {
        out << "edi fit: project " << project_name << ", ";
    }
    // BOTH counts, as the contract names them: reduced chi-square is normalised by the FITTED
    // count, so showing only the loaded one invites a wrong recomputation.
    out << preamble.n_points_fitted << " pts fitted / " << preamble.n_points_loaded << " loaded, "
        << preamble.n_free << " free\n";
    // The iteration-table header, then the pre-fit starting row — so the first iteration's
    // improvement over the initial model is visible (edi used to print a header then nothing for ~30
    // s).
    out << iteration_header(variant) << '\n';
    out << pre_fit_line(preamble.pre_fit, variant) << '\n';
    return out.str();
}

std::string summary_line(const FitResultBase& outcome, const std::string& variant) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    // The two metrics by their dictionary labels and units for `variant` (`reduced χ² 1.23 · Rwp 4.56 %`).
    const auto shown = [&variant](const char* uid, double value) {
        const std::string units = units_label(uid, variant);
        return label(uid, variant) + " " + metric(uid, value, 0, variant) + (units.empty() ? "" : " " + units);
    };
    out << "  done · " << (outcome.converged ? "converged" : "not converged") << " · "
        << outcome.iterations << " iters · " << shown("fit_result.reduced_chi_square", outcome.reduced_chi_square)
        << " · " << shown("fit_result.prof_wr_factor", outcome.rwp) << " · "
        << fixed(outcome.elapsed_ms / 1000.0, 2) << " s\n";
    return out.str();
}

std::string parameter_table(const FitResultBase& outcome, const Project* project) {
    std::ostringstream out;
    out.imbue(std::locale::classic());
    // Per-bank metrics exist for a joint refinement only — the engine reports no per-bank block for
    // a single-bank fit, so there is nothing truthful to print there.
    if (!outcome.banks.empty()) {
        const std::string variant = project != nullptr ? metric_variant(*project) : std::string();
        out << "\n  per-bank " << metric_header("fit_result_bank.prof_wr_factor", variant) << ":";
        for (const BankMetric& bank : outcome.banks) {
            out << "   " << bank.name << ' ' << metric("fit_result_bank.prof_wr_factor", bank.rwp, 0, variant);
        }
        out << '\n';
    }
    out << "\n  refined parameters (" << outcome.values.size() << " free):\n";
    // With the project, each row is its parameter's, found by the result path (parameter_entries walks the paths a fit
    // result carries): its item, an ADP labelled and rounded by its site's type, and a value and its s.u. by the
    // project's rule. Without it, the item is read off the path, with the default rule and the items' base entries.
    std::map<std::string, std::string> variants;
    std::map<std::string, std::string> uids;
    // Each result path's parameter, for its correlation mark (su_marks).
    std::map<std::string, const Parameter*> parameters;
    std::unordered_map<const Parameter*, SuMarks> marks;
    std::string rule = kDefaultSuRule;
    if (project != nullptr) {
        rule = project->su_rule;
        const std::unordered_map<const Parameter*, std::string> by_parameter = parameter_variants(*project);
        // The walk only reads; it hands out writable parameters for the app's editors. A result names a block's
        // parameter under either root, by the fit that made it: `experiment.` for the one block a single-bank fit
        // builds (the first), `experiments[<name>].` for a joint fit even with one bank. Each entry answers to the
        // walk's own path first, then to both roots. The root is cut off as the string the walk spelled it, since a
        // block's name may hold brackets and dots.
        const std::vector<ParameterEntry> entries = parameter_entries(const_cast<Project&>(*project));
        std::map<std::string, std::string> first_block;  // block kind -> its first block's name
        for (const ParameterEntry& entry : entries) {
            first_block.emplace(entry.block_kind, entry.block_name);
        }
        const auto keys_of = [&first_block](const ParameterEntry& entry) {
            std::vector<std::string> keys{entry.path};
            // A structure's named root is its datablock key, as structure_root spells it; an experiment's its name.
            const std::string named =
                entry.block_kind + "s[" +
                (entry.block_kind == "structure" ? datablock_key(entry.block_name, "structure") : entry.block_name) +
                "]";
            std::optional<std::string> rest;
            if (entry.path.starts_with(named + ".")) {
                rest = entry.path.substr(named.size());
            } else if (entry.path.starts_with(entry.block_kind + ".")) {
                rest = entry.path.substr(entry.block_kind.size());
            }
            if (rest.has_value()) {
                keys.push_back(named + *rest);
                if (first_block.at(entry.block_kind) == entry.block_name) {
                    keys.push_back(entry.block_kind + *rest);
                }
            }
            return keys;
        };
        marks = su_marks(*project);
        for (const ParameterEntry& entry : entries) {
            for (const std::string& key : keys_of(entry)) {
                parameters.emplace(key, entry.parameter);
                if (const auto found = by_parameter.find(entry.parameter); found != by_parameter.end()) {
                    variants.emplace(key, found->second);
                }
                if (const std::string uid = entry.category + "." + entry.name; has_item(uid)) {
                    uids.emplace(key, uid);
                }
            }
        }
    }
    // The rows are made first so that a name or path as long as its column widens it.
    struct Row {
        std::string name, path, rest;
    };
    std::vector<Row> rows;
    bool any_undefined = false;
    // The flagged rows' reasons, as notes under the table: the app shows these s.u. values red (edi ADR-0085).
    std::vector<std::string> flagged;
    int name_width = kNameWidth;
    int path_width = kLabelWidth;
    // std::map iterates sorted by identity path, which is the stable display order.
    for (const auto& [path, value] : outcome.values) {
        const auto start_it = outcome.start.find(path);
        const double start = start_it == outcome.start.end() ? value : start_it->second;
        const auto esd_it = outcome.uncertainty.find(path);
        const double su = esd_it == outcome.uncertainty.end() ? 0.0 : esd_it->second;
        // The dictionary's label and units name the row; the identity path stays its identity.
        const auto uid_it = uids.find(path);
        const std::string uid = uid_it != uids.end() ? uid_it->second : item_of(path);
        const auto variant_it = variants.find(path);
        const std::string variant = variant_it == variants.end() ? std::string() : variant_it->second;
        std::string name = uid.empty() ? std::string() : label(uid, variant);
        if (const std::string units = uid.empty() ? std::string() : units_label(uid, variant); !units.empty()) {
            name += ", " + units;
        }
        // A value with an s.u. is rounded by it, as a file writes it, and the s.u. by the uncertainty rule, never by
        // the value's own format.
        std::string value_cell = number_of(uid, value, 13, variant);
        std::string su_cell = number_of(uid, su, 10, variant);
        if (!uid.empty() && std::isfinite(su) && su > 0.0 && std::isfinite(value)) {
            const FileText fitted = fitted_text(uid, value, su, rule);
            const auto [value_text, su_text] = table_value_su(value, fitted.value, fitted.su, false);
            value_cell = padded_left(value_text, 13);
            su_cell = padded_left(su_text, 10);
        } else if (!in_decimal_range(value)) {
            value_cell = padded_left(table_number(value, {}, false), 13);
        }
        if (std::isnan(su)) {
            su_cell = padded_left(std::string(kUndefinedSu), 10);
            any_undefined = true;
        }
        name_width = std::max(name_width, shown_width(name) + 1);
        path_width = std::max(path_width, shown_width(path) + 1);
        std::string reasons;
        const crysta::DictionaryItem* item = uid.empty() ? nullptr : crysta::find_dictionary_item(uid);
        if (item != nullptr && !item->near_zero && std::isfinite(su) && su > 0.0 && std::fabs(su) > std::fabs(value)) {
            reasons = su_poor_text();
        }
        if (const auto parameter = parameters.find(path); parameter != parameters.end()) {
            if (const auto mark = marks.find(parameter->second); mark != marks.end() && !mark->second.partner.empty()) {
                reasons += (reasons.empty() ? "" : "; ") + su_correlated_text(mark->second);
            }
        }
        if (!reasons.empty()) flagged.push_back(path + ": " + reasons);
        rows.push_back({name, path,
                        (in_decimal_range(start) ? number_of(uid, start, 13, variant)
                                                 : padded_left(table_number(start, {}, false), 13)) +
                            value_cell + su_cell + (reasons.empty() ? "   " : " ! ") + format_change(value, start)});
    }
    out << "  ";
    append_padded(out, "name", name_width);
    append_padded(out, "parameter", path_width);
    out << std::setw(13) << "start" << std::setw(13) << "value" << std::setw(10) << "s.u." << "   change\n";
    for (const Row& row : rows) {
        out << "  ";
        append_padded(out, row.name, name_width);
        append_padded(out, row.path, path_width);
        out << row.rest << '\n';
    }
    out << '\n';
    for (const auto& [term, meaning] : fitted_columns()) {
        out << "  ";
        append_padded(out, "- " + term, 10);
        out << meaning << '\n';
    }
    if (any_undefined) {
        out << "  - " << kUndefinedSu << ' ' << kUndefinedSuNote << '\n';
    }
    if (!flagged.empty()) {
        out << "  - !       a poorly determined or strongly correlated parameter:\n";
        for (const std::string& line : flagged) out << "      " << line << '\n';
    }
    return out.str();
}

const std::vector<std::pair<std::string, std::string>>& fitted_columns() {
    static const std::vector<std::pair<std::string, std::string>> columns{
        {"start", "the value before the fit"},
        {"value", "the fitted value, where the least-squares fit ends: the weighted sum of squared residuals is smallest"},
        {"s.u.", "its standard uncertainty, the square root of its diagonal element of the fit's covariance matrix"},
        {"change", "how far the fit moved it, in % of the start: \xE2\x86\x91 up, \xE2\x86\x93 down"},
    };
    return columns;
}

std::string metric_variant(const Project& project) {
    const bool single_crystal =
        !project.experiments.empty() &&
        std::all_of(project.experiments.begin(), project.experiments.end(),
                    [](const auto& experiment) { return experiment->reflections.has_value(); });
    return single_crystal ? token(SampleFormEnum::SINGLE_CRYSTAL) : std::string();
}

std::string progress_report(const IterationRecord& record) {
    // The machine streamed record is crysta's artifact — rendered by the shared engine emitter, not
    // by edi presentation — so `edi fit --report machine --stream` and `crysta fit --stream` emit
    // one implementation. `iter`/`rwp`/`reduced_chi_square` are contract; `elapsed_ms` is informational.
    return crysta::format_fit_report(crysta::make_progress_report(to_engine(record)),
                                     crysta::VerbosityEnum::Compact);
}

}  // namespace edi
