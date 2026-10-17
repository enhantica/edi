// SPDX-License-Identifier: BSD-3-Clause
#include "edi/report_html.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iterator>
#include <optional>
#include <stdexcept>
#include <string_view>
#include <utility>
#include <vector>

// The HTML report (edi ADR-0036): the text sections written here from the model, set after the owner's reference
// report (diffraction-lib's, 2026-10-13), and report.js drawing the charts from the model's JSON in the same file.

namespace edi::detail {
extern const char* const kReportJs;  // data/report/report.js, embedded by core/CMakeLists.txt
}  // namespace edi::detail

namespace edi {

namespace {

// plotly.js's Subresource Integrity hash, of the vendored file (the same bytes the web address serves).
constexpr const char* kPlotlyIntegrity = "sha256-fFk7ntoOdKHQczXPicv3pV/8EUkJmAw3Ka+DVFO9sCo=";

constexpr const char* kStyle = R"css(
:root {
  color-scheme: light;
  --paper: #ffffff;
  --page-bg: #8a8a8a;
  --ink: #000000;
  --muted: #5f6368;
  --rowshade: #ebf0f8;
  --tableborder: #bec7d0;
  --bw: 0.4pt;
  --body-font: 'Utopia', 'Charter', 'Bitstream Charter', Georgia, 'Times New Roman', serif;
  --head-font: 'PT Sans', 'Trebuchet MS', 'Segoe UI', sans-serif;
  --colsep: 6pt;
  --wide-colsep: 3pt;
  --lead: 20.4pt;
}
* { box-sizing: border-box; }
html { background: var(--page-bg); }
body {
  margin: 0;
  padding: 24px 0;
  background: var(--page-bg);
  color: var(--ink);
  font-family: var(--body-font);
  font-size: 10.04pt;
  font-variant-numeric: lining-nums;
  line-height: var(--lead);
}
.report-shell {
  width: 21.59cm;
  min-height: 27.94cm;
  margin: 0 auto;
  padding: 2.5cm;
  background: var(--paper);
  box-shadow: 0 2px 14px rgb(0 0 0 / 45%);
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.report-title, h1, h2, h3, h4 { margin: 0; font-family: var(--head-font); font-weight: 400; line-height: 1.2; }
.report-title { margin: 0 0 22.8pt; }
.report-title .t1 { margin: 0 0 14pt; font-size: 14.35pt; line-height: 1.15; }
.report-title .t2 { margin: 0; font-size: 17.22pt; line-height: 1.15; }
.report-title .authors { margin: 7pt 0 0; font-family: var(--body-font); font-size: 10.04pt; color: var(--muted); }
h2 { margin: 16.8pt 0 7pt; font-size: 14.35pt; }
h3 { margin: 17.5pt 0 10.8pt; font-size: 11.96pt; }
h4 { margin: 13.2pt 0 6.2pt; font-size: 10.91pt; }
.section-number { margin-right: 0.5em; }
p { margin: 11.9pt 0 20.4pt; hyphens: auto; text-align: justify; }
p.note { margin: 1.55pt 0 9.5pt; color: var(--muted); text-align: left; }
.record + .record { margin-top: 26px; }
table {
  width: auto;
  max-width: 100%;
  margin: 1.55pt 0 9.5pt;
  border: var(--bw) solid var(--tableborder);
  border-collapse: collapse;
  font-variant-numeric: lining-nums tabular-nums;
}
thead tr { background: var(--rowshade); }
tbody tr:nth-child(even) { background: var(--rowshade); }
tbody tr:nth-child(odd) { background: var(--paper); }
thead th { border-bottom: var(--bw) solid var(--tableborder); }
th, td {
  padding: 0 var(--colsep);
  text-align: left;
  vertical-align: baseline;
  font-weight: 400;
  line-height: var(--lead);
  white-space: nowrap;
}
.numeric { text-align: right; }
.numeric-header { text-align: center; }
.number {
  display: inline-grid;
  grid-template-columns: var(--number-left) 0.35ch var(--number-right);
  white-space: nowrap;
}
.number-left { text-align: right; }
.number-dot { text-align: center; }
.number-right { text-align: left; }
.number-joined { grid-column: 2 / 4; }
.key-value .key { padding-right: 28px; }
.table-scroll { max-width: 100%; margin: 1.55pt 0 9.5pt; overflow-x: auto; }
.table-scroll table { margin: 0; }
.wide-table th, .wide-table td { padding: 0 var(--wide-colsep); }
table.correlations { border: none; }
table.correlations tbody tr { background: none; }
table.correlations thead tr { background: none; }
table.correlations thead th { border-bottom: none; text-align: center; }
table.correlations td {
  width: 3.2em;
  min-width: 3.2em;
  height: 3.2em;
  padding: 0;
  border: var(--bw) solid var(--tableborder);
  text-align: center;
  vertical-align: middle;
}
/* A figure is spaced as a table is; a structure view is also framed as one, a chart has no border round it (the
   owner, 2026-10-13 and 2026-10-14). */
.figure { margin: 1.55pt 0 9.5pt; }
.pattern-figure { width: 100%; height: 440px; }
/* A scan's evolution: one chart per parameter, one to a row, its height to its width the app's Evolution tab's (the
   owner, 2026-10-14). */
.evolution-figure { aspect-ratio: 100 / 105; min-width: 0; box-sizing: border-box; overflow: hidden; }
.structure-figure {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  border: var(--bw) solid var(--tableborder);
}
.figure-note {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  font-family: var(--head-font);
}
.structure-legend {
  position: absolute;
  bottom: 10px;
  left: 10px;
  padding: 6px 10px;
  border: 1px solid #e2e2e2;
  background: rgb(255 255 255 / 70%);
  font: 12px/1.7 var(--head-font);
}
.structure-legend .swatch {
  display: inline-block;
  width: 11px;
  height: 11px;
  margin-right: 7px;
  border: 1px solid rgb(0 0 0 / 18%);
  border-radius: 50%;
  vertical-align: middle;
}
.axis-letter {
  position: absolute;
  transform: translate(-50%, -50%);
  pointer-events: none;
  font: 700 18px/1 var(--head-font);
}
.atom-label {
  position: absolute;
  transform: translate(-50%, -50%);
  pointer-events: none;
  font: 12px/1 var(--head-font);
  text-shadow: 0 0 2px #fff, 0 0 2px #fff;
}
/* The structure view's toolbar, as the app's Structure page has it. */
.viewer-toolbar { position: absolute; top: 10px; right: 10px; display: flex; gap: 4px; }
.viewer-toolbar .gap { width: 8px; }
.viewer-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid #dcdcdc;
  background: #f4f4f4;
  color: #333;
  cursor: pointer;
  font: 700 16px/1 var(--head-font);
}
.viewer-button:hover { background: #e9e9e9; }
.viewer-button[aria-pressed="true"] { color: #00a3e3; }
.viewer-button svg { width: 15px; height: 15px; fill: currentColor; }
.viewer-snapshot { position: absolute; right: 10px; bottom: 10px; }
@media (max-width: 700px) {
  html, body { background: var(--paper); }
  body { padding: 0; }
  .report-shell { width: 100%; min-height: 0; padding: 24px 16px 42px; box-shadow: none; }
}
@media print {
  html, body { background: none; }
  body { padding: 0; }
  .report-shell { width: auto; min-height: 0; padding: 0; box-shadow: none; }
}
)css";

// Text as HTML: the five characters with a meaning there written as entities.
std::string escaped(std::string_view text) {
    std::string out;
    out.reserve(text.size());
    for (const char c : text) {
        switch (c) {
            case '&':
                out += "&amp;";
                break;
            case '<':
                out += "&lt;";
                break;
            case '>':
                out += "&gt;";
                break;
            case '"':
                out += "&quot;";
                break;
            case '\'':
                out += "&#39;";
                break;
            default:
                out += c;
        }
    }
    return out;
}

// Code as the text of a <script> element: a "</script" in it, in any case, would end the element early, so its "/" is
// written as "\/", which JavaScript reads the same inside a string.
std::string script_text(std::string_view code) {
    std::string out;
    out.reserve(code.size());
    for (std::size_t i = 0; i < code.size(); ++i) {
        out += code[i];
        if (code[i] == '<' && i + 7 < code.size() && code[i + 1] == '/') {
            std::string tag(code.substr(i + 2, 6));
            std::transform(tag.begin(), tag.end(), tag.begin(),
                           [](char c) { return static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c); });
            if (tag == "script") {
                out += '\\';
            }
        }
    }
    return out;
}

std::string base64(std::string_view data) {
    static constexpr char kDigits[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string out;
    out.reserve((data.size() + 2) / 3 * 4);
    for (std::size_t i = 0; i < data.size(); i += 3) {
        const std::size_t count = std::min<std::size_t>(3, data.size() - i);
        std::uint32_t group = 0;
        for (std::size_t k = 0; k < 3; ++k) {
            group = (group << 8U) | (k < count ? static_cast<unsigned char>(data[i + k]) : 0U);
        }
        for (std::size_t k = 0; k < 4; ++k) {
            out += k <= count ? kDigits[(group >> (18U - 6U * k)) & 0x3FU] : '=';
        }
    }
    return out;
}

// The number of characters in UTF-8 text.
std::size_t characters(std::string_view text) {
    return static_cast<std::size_t>(std::count_if(
        text.begin(), text.end(), [](char c) { return (static_cast<unsigned char>(c) & 0xC0U) != 0x80U; }));
}

std::string whole(std::size_t number) { return std::to_string(number); }

// A number's text split at its decimal point, as the Report page's tables split it: the sign and whole digits; then the
// decimals with an s.u. bracket, an exponent and units after a space. Absent for a text that is not a number.
struct NumberParts {
    std::string left, right;
    bool dot = false;
};

std::optional<NumberParts> number_parts(std::string_view text) {
    std::size_t at = 0;
    const auto digits = [&text, &at] {
        const std::size_t start = at;
        while (at < text.size() && text[at] >= '0' && text[at] <= '9') {
            ++at;
        }
        return at - start;
    };
    if (text.starts_with("\xE2\x88\x92")) {  // U+2212, the minus sign
        at = 3;
    } else if (!text.empty() && (text[0] == '-' || text[0] == '+')) {
        at = 1;
    }
    bool any = digits() > 0;
    NumberParts parts;
    parts.left = std::string(text.substr(0, at));
    if (at < text.size() && text[at] == '.') {
        parts.dot = true;
        ++at;
    }
    const std::size_t right = at;
    any = digits() > 0 || any;
    if (at < text.size() && text[at] == '(') {
        ++at;
        if (digits() == 0 || at >= text.size() || text[at] != ')') {
            return std::nullopt;
        }
        ++at;
        any = true;
    }
    if (at < text.size() && (text[at] == 'e' || text[at] == 'E')) {
        ++at;
        if (at < text.size() && (text[at] == '-' || text[at] == '+')) {
            ++at;
        }
        if (digits() == 0) {
            return std::nullopt;
        }
        any = true;
    }
    const std::string_view rest = text.substr(at);
    const bool units =
        rest.empty() || (rest.size() >= 2 && rest[0] == ' ' && rest[1] != ' ' && (rest[1] < '0' || rest[1] > '9'));
    if (!units || !any) {
        return std::nullopt;
    }
    parts.right = std::string(text.substr(right));
    return parts;
}

// A number's part after its point, escaped. Units right after the whole digits (90 deg) keep the space before them,
// which a cell or a grid item would drop at its start.
std::string right_html(const NumberParts& parts) {
    return parts.right.starts_with(' ') ? "&#160;" + escaped(std::string_view(parts.right).substr(1))
                                        : escaped(parts.right);
}

// A column of numbers when every cell of it that has text is a number and one is: its widest parts, in characters.
struct ColumnLayout {
    bool numeric = false;
    std::size_t left = 0, right = 0;
};

std::vector<ColumnLayout> layout_of(const std::vector<std::vector<std::string>>& rows, std::size_t columns) {
    std::vector<ColumnLayout> out(columns);
    for (std::size_t column = 0; column < columns; ++column) {
        std::size_t numbers = 0, others = 0;
        for (const std::vector<std::string>& row : rows) {
            if (column >= row.size() || row[column].empty()) {
                continue;
            }
            if (const std::optional<NumberParts> parts = number_parts(row[column])) {
                ++numbers;
                out[column].left = std::max(out[column].left, characters(parts->left));
                out[column].right = std::max(out[column].right, characters(parts->right));
            } else {
                ++others;
            }
        }
        out[column].numeric = numbers > 0 && others == 0;
    }
    return out;
}

// A value with its units after a space: 90 deg, 3.88 Å.
std::string with_units(const ReportRow& row) {
    if (row.units.empty()) {
        return row.text;
    }
    return row.text + " " + row.units;
}

// A correlation cell's colour: from white at 0 to diffraction-lib's red at -1 or blue at 1, as the Correlations tab
// colours it.
std::string correlation_colour(double value) {
    static constexpr std::array<int, 3> kNegative{0xD7, 0x30, 0x27};
    static constexpr std::array<int, 3> kPositive{0x45, 0x75, 0xB4};
    const std::array<int, 3>& end = value < 0.0 ? kNegative : kPositive;
    const double share = std::min(1.0, std::fabs(value));
    static const char* const kDigits = "0123456789abcdef";
    std::string out = "#";
    for (const int channel : end) {
        const auto mixed = static_cast<unsigned>(std::lround(255.0 + (channel - 255.0) * share));
        out += kDigits[mixed >> 4U];
        out += kDigits[mixed & 0xFU];
    }
    return out;
}

std::string fixed2(double value) {
    std::array<char, 64> buffer{};
    const auto result = std::to_chars(buffer.data(), buffer.data() + buffer.size(), value, std::chars_format::fixed, 2);
    return {buffer.data(), result.ptr};
}

// The static report's style sheet, in the subset a rich-text engine reads: lengths in px at 96 to the inch, the HTML
// report's points times 4/3.
constexpr const char* kDocumentStyle = R"css(
h2, h3, h4 { font-weight: normal; }
h2 { font-size: 14.35pt; margin-top: 22.4px; margin-bottom: 9.3px; }
h3 { font-size: 11.96pt; margin-top: 23.3px; margin-bottom: 14.4px; }
h4 { font-size: 10.91pt; margin-top: 17.6px; margin-bottom: 8.3px; }
p { margin-top: 0px; margin-bottom: 0px; }
p.description { margin-top: 15.9px; margin-bottom: 27.2px; }
p.note { margin-top: 2.1px; margin-bottom: 12.7px; color: #5f6368; }
p.t1 { font-size: 14.35pt; margin-bottom: 18.7px; }
p.t2 { font-size: 17.22pt; }
p.authors { margin-top: 9.3px; color: #5f6368; }
p.after-title { margin-bottom: 30.4px; }
table { margin-top: 2.1px; margin-bottom: 12.7px; }
)css";

constexpr const char* kRowShade = "#ebf0f8";
constexpr const char* kPaper = "#ffffff";
// The static tables' borders: finer and lighter than the HTML report's, which print bolder (the owner, 2026-10-14).
constexpr const char* kTableBorder = "#d3d9df";
constexpr const char* kDocumentBorderWidth = "0.25px";

// A cell of a static table: its HTML, its alignment, the columns it spans and its padding at each side, in px.
struct DocumentCell {
    std::string html;
    const char* align = "left";
    std::size_t span = 1;
    double left = 4.0, right = 4.0;
};

class Writer {
public:
    // The HTML report's text sections; with `figure_width`, the static report's, its figures that wide.
    explicit Writer(const ReportModel& model, std::optional<double> figure_width = std::nullopt)
        : model_(model), figure_width_(figure_width) {}

    std::string body() {
        if (!document()) {
            out_ += "<main class=\"report-shell\">\n";
        }
        title_block();
        for (const ReportSection section : model_.sections) {
            ++section_;
            if (!document()) {
                out_ += "<section id=\"" + std::string(report_section_name(section)) + "\">\n";
            }
            switch (section) {
                case ReportSection::Summary:
                    summary();
                    break;
                case ReportSection::Analysis:
                    heading(2, number(), "Analysis");
                    for (std::size_t i = 0; i < model_.analysis.size(); ++i) {
                        category(model_.analysis[i], 3);
                    }
                    break;
                case ReportSection::Structures:
                    heading(2, number(), "Structures");
                    for (std::size_t i = 0; i < model_.structures.size(); ++i) {
                        record(model_.structures[i].id, model_.structures[i].categories, i, "structure");
                    }
                    break;
                case ReportSection::Experiments:
                    heading(2, number(), "Experiments");
                    for (std::size_t i = 0; i < model_.experiments.size(); ++i) {
                        record(model_.experiments[i].id, model_.experiments[i].categories, i, "pattern");
                    }
                    break;
                case ReportSection::Correlations:
                    heading(2, number(), "Correlations");
                    correlations();
                    break;
                case ReportSection::Evolution:
                    heading(2, number(), "Evolution");
                    note("The fitted parameters across the scan\xE2\x80\x99s datasets");
                    // One chart per parameter, as the Evolution tab lists them (report.js draws each).
                    if (model_.evolution && !model_.evolution->empty()) {
                        evolution_figures();
                    }
                    break;
            }
            if (!document()) {
                out_ += "</section>\n";
            }
        }
        if (!document()) {
            out_ += "</main>\n";
        }
        return std::move(out_);
    }

private:
    bool document() const { return figure_width_.has_value(); }

    std::string number() const { return whole(section_) + "."; }

    bool charts() const {
        return std::any_of(model_.contents.begin(), model_.contents.end(),
                           [](const ReportContentsItem& item) { return item.key == "charts" && item.included; });
    }

    void heading(int level, const std::string& number, std::string_view text) {
        const std::string tag = "h" + std::to_string(level);
        out_ += "<" + tag + ">";
        if (!number.empty()) {
            // The static report spaces the number with two no-break spaces, as its engine has no inline margins.
            out_ += document() ? number + "\xC2\xA0\xC2\xA0" : "<span class=\"section-number\">" + number + "</span>";
        }
        out_ += escaped(text) + "</" + tag + ">\n";
    }

    void note(std::string_view text) { out_ += "<p class=\"note\">" + escaped(text) + "</p>\n"; }

    // The title block: what it is, then the project's title (its short name without one) and its authors.
    void title_block() {
        if (document()) {
            out_ += "<p class=\"t1\">EasyDiffraction Report</p>\n";
            out_ += "<p class=\"t2\">" + escaped(model_.title.empty() ? model_.name : model_.title) + "</p>\n";
            if (!model_.authors.empty()) {
                out_ += "<p class=\"authors\">" + escaped(model_.authors) + "</p>\n";
            }
            out_ += "<p class=\"after-title\"></p>\n";
            return;
        }
        out_ += "<header class=\"report-title\">\n<div class=\"t1\">EasyDiffraction Report</div>\n";
        out_ += "<h1 class=\"t2\">" + escaped(model_.title.empty() ? model_.name : model_.title) + "</h1>\n";
        if (!model_.authors.empty()) {
            out_ += "<div class=\"authors\">" + escaped(model_.authors) + "</div>\n";
        }
        out_ += "</header>\n";
    }

    void summary() {
        heading(2, number(), "Project summary");
        if (!model_.description.empty()) {
            out_ += (document() ? "<p class=\"description\">" : "<p>") + escaped(model_.description) + "</p>\n";
        }
        const auto joined = [](const std::vector<std::string>& ids) {
            std::string text;
            for (const std::string& id : ids) {
                text += (text.empty() ? "" : ", ") + id;
            }
            return text;
        };
        key_values({{"Short name", model_.name},
                    {"Structures", joined(model_.structure_ids)},
                    {"Experiments", joined(model_.experiment_ids)},
                    {"Generated", model_.generated}});
    }

    // A structure or an experiment: its numbered heading, its figure when the report has charts, then its categories.
    void record(const std::string& id, const std::vector<ReportCategory>& categories, std::size_t index,
                const char* figure) {
        if (!document()) {
            out_ += "<article class=\"record\">\n";
        }
        heading(3, number() + whole(index + 1) + ".", id);
        if (charts() && document()) {
            // The figure's image, by its kind and index: a structure view framed as a table is, a chart with no border.
            DocumentCell cell{"<img src=\"" + std::string(figure) + "-" + whole(index) + "\" width=\"" +
                                  fixed2(*figure_width_) + "\">",
                              "left", 1, 0.0, 0.0};
            document_table(nullptr, {{cell}}, false, std::string_view(figure) == "structure");
        } else if (charts()) {
            out_ += "<div class=\"figure " + std::string(figure) + "-figure\" data-index=\"" + whole(index) +
                    "\"></div>\n";
        }
        for (const ReportCategory& part : categories) {
            category(part, 4);
        }
        if (!document()) {
            out_ += "</article>\n";
        }
    }

    // A scan's evolution charts, one to a row with no border round them: in the HTML report a column of figures, in
    // the static report their images, each a table of its own so a page break never splits a chart.
    void evolution_figures() {
        const std::size_t count = model_.evolution->size();
        if (!document()) {
            out_ += "<div class=\"evolution-grid\">\n";
            for (std::size_t index = 0; index < count; ++index) {
                out_ += "<div class=\"figure evolution-figure\" data-index=\"" + whole(index) + "\"></div>\n";
            }
            out_ += "</div>\n";
            return;
        }
        for (std::size_t index = 0; index < count; ++index) {
            const DocumentCell cell{
                "<img src=\"evolution-" + whole(index) + "\" width=\"" + fixed2(*figure_width_) + "\">", "left", 1, 0.0,
                0.0};
            document_table(nullptr, {{cell}}, false, false);
        }
    }

    // A numeric cell of the static report as two cells, so the column's points line up: the sign and whole digits
    // to the right, then the point and the rest to the left. A header wider than the numbers widens them outwards,
    // never between the digits and the point. A number without a point gives the point's place to what follows its
    // digits, as the HTML report does; a cell that is not a number spans both.
    static std::vector<DocumentCell> number_cells(const std::string& text, double pad) {
        const std::optional<NumberParts> parts = number_parts(text);
        if (!parts) {
            return {{escaped(text), "right", 2, pad, pad}};
        }
        return {{escaped(parts->left), "right", 1, pad, 0.0},
                {(parts->dot ? "." : "") + right_html(*parts), "left", 1, 0.0, pad}};
    }

    // A static table: the frame on its outer cells' edges (unless `framed` is false), the header shaded with a line
    // under it, the body's even rows shaded, as the HTML report's tables are; `header` may be null. Cells never wrap.
    void document_table(const std::vector<DocumentCell>* header, const std::vector<std::vector<DocumentCell>>& rows,
                        bool shaded = true, bool framed = true) {
        out_ += "<table cellspacing=\"0\" cellpadding=\"0\" style=\"border-collapse: collapse\">\n";
        const std::size_t total = rows.size() + (header != nullptr ? 1 : 0);
        std::size_t at = 0;
        const auto edge = [framed](const char* side) {
            return framed ? std::string("border-") + side + "-width: " + kDocumentBorderWidth + "; border-" + side +
                                "-style: solid; border-" + side + "-color: " + kTableBorder + "; "
                          : std::string();
        };
        const auto row_html = [&](const std::vector<DocumentCell>& row, bool head, std::size_t body_index) {
            const char* shade = !shaded ? kPaper : head || body_index % 2 == 1 ? kRowShade : kPaper;
            out_ += "<tr>";
            for (std::size_t k = 0; k < row.size(); ++k) {
                const DocumentCell& cell = row[k];
                std::string style = "padding-left: " + fixed2(cell.left) + "px; padding-right: " + fixed2(cell.right) +
                                    "px; padding-top: 3px; padding-bottom: 3px; white-space: nowrap; font-weight: normal; ";
                if (at == 0) {
                    style += edge("top");
                }
                if (at + 1 == total || head) {
                    style += edge("bottom");
                }
                if (k == 0) {
                    style += edge("left");
                }
                if (k + 1 == row.size()) {
                    style += edge("right");
                }
                const char* tag = head ? "th" : "td";
                out_ += std::string("<") + tag + " bgcolor=\"" + shade + "\" align=\"" + cell.align + "\"";
                if (cell.span > 1) {
                    out_ += " colspan=\"" + whole(cell.span) + "\"";
                }
                out_ += " style=\"" + style + "\">" + cell.html + "</" + tag + ">";
            }
            out_ += "</tr>\n";
            ++at;
        };
        if (header != nullptr) {
            out_ += "<thead>\n";
            row_html(*header, true, 0);
            out_ += "</thead>\n";
        }
        out_ += "<tbody>\n";
        for (std::size_t i = 0; i < rows.size(); ++i) {
            row_html(rows[i], false, i);
        }
        out_ += "</tbody>\n</table>\n";
    }

    // One category: its heading, its labelled values, then its table.
    void category(const ReportCategory& part, int level) {
        heading(level, "", part.title);
        std::vector<std::pair<std::string, std::string>> rows;
        rows.reserve(part.rows.size());
        for (const ReportRow& row : part.rows) {
            rows.emplace_back(row.label, with_units(row));
        }
        key_values(rows);
        table(part.table);
    }

    void cell(const std::string& text, const ColumnLayout& column, const char* key = nullptr) {
        const std::optional<NumberParts> parts = column.numeric ? number_parts(text) : std::nullopt;
        if (key != nullptr) {
            out_ += "<td class=\"key\">" + escaped(text) + "</td>";
            return;
        }
        if (!parts) {
            out_ += column.numeric ? "<td class=\"numeric\">" : "<td>";
            out_ += escaped(text) + "</td>";
            return;
        }
        // A number without a point gives the point's place to what follows its digits, so 611(16) stays together and
        // its digits still end where the column's points are.
        out_ += "<td class=\"numeric\"><span class=\"number\" style=\"--number-left: " + whole(column.left) +
                "ch; --number-right: " + whole(column.right) + "ch\"><span class=\"number-left\">" +
                escaped(parts->left) + "</span>";
        if (parts->dot) {
            out_ += "<span class=\"number-dot\">.</span><span class=\"number-right\">";
        } else {
            out_ += "<span class=\"number-right number-joined\">";
        }
        out_ += right_html(*parts) + "</span></span></td>";
    }

    void key_values(const std::vector<std::pair<std::string, std::string>>& rows) {
        if (rows.empty()) {
            return;
        }
        std::vector<std::vector<std::string>> values;
        values.reserve(rows.size());
        for (const auto& row : rows) {
            values.push_back({row.second});
        }
        const ColumnLayout column = layout_of(values, 1).front();
        if (document()) {
            std::vector<std::vector<DocumentCell>> cells;
            for (const auto& [label, value] : rows) {
                std::vector<DocumentCell> row{{escaped(label), "left", 1, 8.0, 37.3}};
                if (column.numeric) {
                    const std::vector<DocumentCell> number = number_cells(value, 8.0);
                    row.insert(row.end(), number.begin(), number.end());
                } else {
                    row.push_back({escaped(value), "left", 1, 8.0, 8.0});
                }
                cells.push_back(std::move(row));
            }
            document_table(nullptr, cells);
            return;
        }
        out_ += "<table class=\"key-value\">\n<tbody>\n";
        for (const auto& [label, value] : rows) {
            out_ += "<tr>";
            cell(label, {}, "key");
            cell(value, column);
            out_ += "</tr>\n";
        }
        out_ += "</tbody>\n</table>\n";
    }

    void table(const ReportTable& data) {
        if (data.rows.empty()) {
            return;
        }
        const std::vector<ColumnLayout> columns = layout_of(data.rows, data.columns.size());
        if (document()) {
            std::vector<DocumentCell> header;
            for (std::size_t i = 0; i < data.columns.size(); ++i) {
                header.push_back({escaped(data.columns[i]), columns[i].numeric ? "center" : "left",
                                  columns[i].numeric ? 2U : 1U});
            }
            std::vector<std::vector<DocumentCell>> cells;
            for (const std::vector<std::string>& row : data.rows) {
                std::vector<DocumentCell> line;
                for (std::size_t i = 0; i < columns.size(); ++i) {
                    const std::string text = i < row.size() ? row[i] : std::string();
                    if (columns[i].numeric) {
                        const std::vector<DocumentCell> number = number_cells(text, 4.0);
                        line.insert(line.end(), number.begin(), number.end());
                    } else {
                        line.push_back({escaped(text)});
                    }
                }
                cells.push_back(std::move(line));
            }
            document_table(&header, cells);
            return;
        }
        // Every row, however long the table, as the PDF prints them (the owner, 2026-10-14).
        out_ += "<div class=\"table-scroll\">";
        out_ += "<table class=\"wide-table\">\n<thead>\n<tr>";
        for (std::size_t i = 0; i < data.columns.size(); ++i) {
            out_ += columns[i].numeric ? "<th class=\"numeric-header\">" : "<th>";
            out_ += escaped(data.columns[i]) + "</th>";
        }
        out_ += "</tr>\n</thead>\n<tbody>\n";
        for (const std::vector<std::string>& row : data.rows) {
            out_ += "<tr>";
            for (std::size_t i = 0; i < columns.size(); ++i) {
                cell(i < row.size() ? row[i] : std::string(), columns[i]);
            }
            out_ += "</tr>\n";
        }
        out_ += "</tbody>\n</table></div>\n";
    }

    // The correlation chart, as the Correlations tab draws it: the lower triangle, each cell coloured from red at -1
    // to blue at 1 and labelled with its value, the parameters numbered down the left and along the top, every cell
    // bordered.
    void correlations() {
        const std::optional<ReportCorrelations>& matrix = model_.correlations;
        const std::size_t count = matrix ? matrix->labels.size() : 0;
        if (count < 2 || matrix->values.size() != count * count) {
            note(matrix && !matrix->empty_text.empty() ? matrix->empty_text : "No correlations yet");
            return;
        }
        if (document()) {
            document_correlations(*matrix);
            return;
        }
        out_ += "<div class=\"table-scroll\"><table class=\"correlations\">\n<thead>\n<tr><th></th>";
        for (std::size_t column = 0; column < count; ++column) {
            out_ += "<th>" + whole(column + 1) + "</th>";
        }
        out_ += "</tr>\n</thead>\n<tbody>\n";
        for (std::size_t row = 0; row < count; ++row) {
            out_ += "<tr><th>" + whole(row + 1) + "\xC2\xA0\xC2\xA0" + escaped(matrix->labels[row]) + "</th>";
            for (std::size_t column = 0; column < count; ++column) {
                const double value = matrix->values[row * count + column];
                if (!std::isfinite(value)) {
                    out_ += "<td></td>";
                    continue;
                }
                // Light text on the strongest cells' full colour.
                out_ += "<td style=\"background: " + correlation_colour(value) +
                        (std::fabs(value) >= 0.5 ? "; color: #f5f5f5" : "") + "\">" + fixed2(value) + "</td>";
            }
            out_ += "</tr>\n";
        }
        out_ += "</tbody>\n</table></div>\n";
    }

    // The correlation chart of the static report: the same cells, each bordered and 3.2 em wide.
    void document_correlations(const ReportCorrelations& matrix) {
        const std::size_t count = matrix.labels.size();
        std::string border;
        for (const char* side : {"top", "right", "bottom", "left"}) {
            border += std::string("border-") + side + "-width: " + kDocumentBorderWidth + "; border-" + side +
                      "-style: solid; border-" + side + "-color: " + kTableBorder + "; ";
        }
        out_ += "<table cellspacing=\"0\" cellpadding=\"0\" style=\"border-collapse: collapse\">\n<thead>\n<tr><th></th>";
        for (std::size_t column = 0; column < count; ++column) {
            out_ += "<th align=\"center\" style=\"font-weight: normal\">" + whole(column + 1) + "</th>";
        }
        out_ += "</tr>\n</thead>\n<tbody>\n";
        for (std::size_t row = 0; row < count; ++row) {
            out_ += "<tr><th align=\"left\" valign=\"middle\" style=\"font-weight: normal; white-space: nowrap; "
                    "padding-right: 8px\">" +
                    whole(row + 1) + "\xC2\xA0\xC2\xA0" + escaped(matrix.labels[row]) + "</th>";
            for (std::size_t column = 0; column < count; ++column) {
                const double value = matrix.values[row * count + column];
                const std::string size = "width=\"43\" style=\"padding-top: 13px; padding-bottom: 13px; ";
                if (!std::isfinite(value)) {
                    out_ += "<td " + size + "\"></td>";
                    continue;
                }
                const std::string text = std::fabs(value) >= 0.5 ? "<span style=\"color: #f5f5f5\">" + fixed2(value) +
                                                                       "</span>"
                                                                 : fixed2(value);
                out_ += "<td align=\"center\" valign=\"middle\" bgcolor=\"" + correlation_colour(value) + "\" " + size +
                        border + "\">" +
                        text + "</td>";
            }
            out_ += "</tr>\n";
        }
        out_ += "</tbody>\n</table>\n";
    }

    const ReportModel& model_;
    std::optional<double> figure_width_;
    std::string out_;
    std::size_t section_ = 0;
};

}  // namespace

const std::array<const char*, 3>& report_library_files() {
    static const std::array<const char*, 3> kFiles{"report/vendor/plotly-cartesian-3.7.0.min.js",
                                                   "report/vendor/three-0.160.0.module.min.js",
                                                   "report/vendor/three-0.160.0-OrbitControls.js"};
    return kFiles;
}

ReportLibraries read_report_libraries(const std::filesystem::path& data_dir) {
    const auto read = [&data_dir](const char* name) {
        const std::filesystem::path path = data_dir / name;
        std::ifstream file(path, std::ios::binary);
        if (!file) {
            throw std::runtime_error("cannot read the report library " + path.string());
        }
        return std::string(std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>());
    };
    const auto& files = report_library_files();
    return {read(files[0]), read(files[1]), read(files[2])};
}

std::string report_html(const ReportModel& model, const ReportLibraries& libraries) {
    const bool embedded = !libraries.plotly.empty();
    if (embedded == libraries.three.empty() || embedded == libraries.orbit_controls.empty()) {
        throw std::invalid_argument("report_html: give all three chart libraries, or none");
    }
    const auto module_url = [embedded](const std::string& text, const char* url) {
        return embedded ? "data:text/javascript;base64," + base64(text) : std::string(url);
    };
    std::string out = "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
                      "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n";
    out += "<title>" + escaped(model.title.empty() ? model.name : model.title) + "</title>\n";
    out += "<style>" + std::string(kStyle) + "</style>\n";
    // three.js's modules, mapped to their web addresses or carried as data URLs, so report.js imports them by name.
    out += "<script type=\"importmap\">{\"imports\": {\"three\": \"" + module_url(libraries.three, kReportThreeUrl) +
           "\", \"three/addons/controls/OrbitControls.js\": \"" +
           module_url(libraries.orbit_controls, kReportOrbitControlsUrl) + "\"}}</script>\n";
    out += "</head>\n<body>\n";
    out += Writer(model).body();
    // The model's JSON has no literal <, > or &, so it cannot end this element. A group the report leaves out is not
    // named in the file at all: its contents entry stays with the app's Contents boxes.
    ReportModel embedded_model = model;
    std::erase_if(embedded_model.contents, [](const ReportContentsItem& item) { return !item.included; });
    out += "<script type=\"application/json\" id=\"edi-report-model\">" + report_to_json(embedded_model) +
           "</script>\n";
    if (embedded) {
        out += "<script>" + script_text(libraries.plotly) + "</script>\n";
    } else {
        out += "<script src=\"" + std::string(kReportPlotlyUrl) + "\" integrity=\"" + kPlotlyIntegrity +
               "\" crossorigin=\"anonymous\"></script>\n";
    }
    out += "<script type=\"module\">\n" + script_text(detail::kReportJs) + "</script>\n";
    out += "</body>\n</html>\n";
    return out;
}

std::string fnv1a64(std::string_view bytes) {
    std::uint64_t hash = 0xcbf29ce484222325ULL;
    for (const char c : bytes) {
        hash ^= static_cast<unsigned char>(c);
        hash *= 0x100000001b3ULL;
    }
    static const char* const kDigits = "0123456789abcdef";
    std::string out(16, '0');
    for (int i = 15; i >= 0; --i) {
        out[static_cast<std::size_t>(i)] = kDigits[hash & 0xFU];
        hash >>= 4U;
    }
    return out;
}

std::string report_digest(ReportModel model, std::string_view format, const ReportLibraries& libraries) {
    model.generated.clear();
    if (format == "html") {
        return fnv1a64(report_html(model, libraries));
    }
    if (format == "pdf") {
        return fnv1a64(report_to_json(model) + report_static_html(model, 0.0));
    }
    return {};
}

std::string report_static_html(const ReportModel& model, double figure_width) {
    std::string out = "<html>\n<head>\n<meta charset=\"utf-8\">\n";
    out += "<title>" + escaped(model.title.empty() ? model.name : model.title) + "</title>\n";
    out += "<style>" + std::string(kDocumentStyle) + "</style>\n</head>\n<body>\n";
    out += Writer(model, figure_width).body();
    out += "</body>\n</html>\n";
    return out;
}

}  // namespace edi
