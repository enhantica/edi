// SPDX-License-Identifier: BSD-3-Clause
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>

#include "edi/model.hpp"
#include "edi/report_model.hpp"
#include "json.hpp"

// The report model's JSON (edi ADR-0036 §1): every field, in declaration order, so a model read from its JSON writes
// the same JSON again.

namespace edi {

namespace {

using json::Array;
using json::Object;
using json::Value;

Value strings(const std::vector<std::string>& texts) {
    Array items;
    items.reserve(texts.size());
    for (const std::string& text : texts) {
        items.emplace_back(text);
    }
    return items;
}

std::vector<std::string> strings_of(const Value& value, const char* what) {
    std::vector<std::string> out;
    for (const Value& item : value.array(what)) {
        out.push_back(item.string(what));
    }
    return out;
}

Value numbers(const std::vector<double>& values) {
    Array items;
    items.reserve(values.size());
    for (double number : values) {
        items.emplace_back(number);
    }
    return items;
}

std::vector<double> numbers_of(const Value& value, const char* what) {
    std::vector<double> out;
    for (const Value& item : value.array(what)) {
        out.push_back(item.number(what));
    }
    return out;
}

Value rows(const std::vector<ReportRow>& list) {
    Array items;
    for (const ReportRow& row : list) {
        items.emplace_back(Object{{"label", row.label}, {"text", row.text}, {"units", row.units}});
    }
    return items;
}

std::vector<ReportRow> rows_of(const Value& value, const char* what) {
    std::vector<ReportRow> out;
    for (const Value& item : value.array(what)) {
        out.push_back({item.at("label").string("label"), item.at("text").string("text"),
                       item.at("units").string("units")});
    }
    return out;
}

Value table(const ReportTable& data) {
    Array body;
    for (const std::vector<std::string>& row : data.rows) {
        body.push_back(strings(row));
    }
    return Object{{"columns", strings(data.columns)}, {"rows", std::move(body)}};
}

ReportTable table_of(const Value& value) {
    ReportTable out;
    out.columns = strings_of(value.at("columns"), "columns");
    for (const Value& row : value.at("rows").array("rows")) {
        out.rows.push_back(strings_of(row, "row"));
    }
    return out;
}

Value categories(const std::vector<ReportCategory>& list) {
    Array items;
    for (const ReportCategory& part : list) {
        items.emplace_back(
            Object{{"id", part.id}, {"title", part.title}, {"rows", rows(part.rows)}, {"table", table(part.table)}});
    }
    return items;
}

std::vector<ReportCategory> categories_of(const Value& value, const char* what) {
    std::vector<ReportCategory> out;
    for (const Value& item : value.array(what)) {
        out.push_back({item.at("id").string("id"), item.at("title").string("title"), rows_of(item.at("rows"), "rows"),
                       table_of(item.at("table"))});
    }
    return out;
}

// A whole number from `low` to `high`, checked before it is converted: a JSON number can be fractional or too
// large, and null reads as NaN.
double whole_number(const Value& value, const char* what, double low, double high) {
    const double number = value.number(what);
    if (!(number >= low && number <= high) || std::floor(number) != number) {
        throw std::invalid_argument(std::string("report JSON: ") + what + " is not a whole number from " +
                                    std::to_string(static_cast<long long>(low)) + " to " +
                                    std::to_string(static_cast<long long>(high)));
    }
    return number;
}

template <typename Integer>
Integer integer_of(const Value& value, const char* what) {
    return static_cast<Integer>(whole_number(value, what, static_cast<double>(std::numeric_limits<Integer>::min()),
                                             static_cast<double>(std::numeric_limits<Integer>::max())));
}

// A count or an index: a whole number from 0 to 2^53, JSON's largest exact one, or to the largest std::size_t where
// that is smaller (32-bit WebAssembly).
std::size_t index_of(const Value& value, const char* what) {
    static const double largest =
        std::min(9007199254740992.0, static_cast<double>(std::numeric_limits<std::size_t>::max()));
    const double number = value.number(what);
    if (!(number >= 0.0 && number <= largest) || std::floor(number) != number) {
        throw std::invalid_argument(std::string("report JSON: ") + what + " is not a whole number from 0 to " +
                                    std::to_string(static_cast<long long>(largest)));
    }
    return static_cast<std::size_t>(number);
}

Value whole(std::size_t number) { return Value(static_cast<double>(number)); }

// A per-point row, -1 for none (kNoRow).
Value point_rows(const std::vector<std::size_t>& list) {
    Array items;
    items.reserve(list.size());
    for (std::size_t row : list) {
        items.emplace_back(row == kNoRow ? -1.0 : static_cast<double>(row));
    }
    return items;
}

std::vector<std::size_t> point_rows_of(const Value& value) {
    std::vector<std::size_t> out;
    for (const Value& item : value.array("rows")) {
        out.push_back(item.number("rows") == -1.0 ? kNoRow : index_of(item, "rows"));
    }
    return out;
}

// An enum as its name, and back; a name the reader does not know is refused.
template <typename Enum, std::size_t N>
const char* name_of(Enum value, const std::array<std::pair<Enum, const char*>, N>& names) {
    for (const auto& [item, name] : names) {
        if (item == value) {
            return name;
        }
    }
    return names.front().second;
}

template <typename Enum, std::size_t N>
Enum enum_of(const Value& value, const std::array<std::pair<Enum, const char*>, N>& names, const char* what) {
    const std::string& text = value.string(what);
    for (const auto& [item, name] : names) {
        if (text == name) {
            return item;
        }
    }
    throw std::invalid_argument(std::string("report JSON: unknown ") + what + " '" + text + "'");
}

constexpr std::array<std::pair<SeriesKind, const char*>, 6> kKinds{{{SeriesKind::Measured, "measured"},
                                                                    {SeriesKind::Calculated, "calculated"},
                                                                    {SeriesKind::Background, "background"},
                                                                    {SeriesKind::Residual, "residual"},
                                                                    {SeriesKind::BraggTicks, "bragg"},
                                                                    {SeriesKind::StructureCurve, "structure"}}};
constexpr std::array<std::pair<Pane, const char*>, 3> kPanes{
    {{Pane::Main, "main"}, {Pane::Bragg, "bragg"}, {Pane::Residual, "residual"}}};
constexpr std::array<std::pair<YScale, const char*>, 3> kScales{
    {{YScale::Linear, "linear"}, {YScale::Sqrt, "sqrt"}, {YScale::Log10, "log10"}}};
constexpr std::array<std::pair<Projection, const char*>, 2> kProjections{
    {{Projection::Orthographic, "orthographic"}, {Projection::Perspective, "perspective"}}};

// --- the pattern (ADR-0021)

Value axis_json(const AxisDescription& axis) {
    Array segments;
    for (const TitleSegment& segment : axis.segments) {
        segments.emplace_back(Object{{"text", segment.text}, {"style", segment.style}});
    }
    return Object{{"title", axis.title},
                  {"segments", std::move(segments)},
                  {"min", axis.min},
                  {"max", axis.max},
                  {"scale", name_of(axis.scale, kScales)}};
}

AxisDescription axis_of(const Value& value) {
    AxisDescription axis;
    axis.title = value.at("title").string("title");
    for (const Value& item : value.at("segments").array("segments")) {
        axis.segments.push_back({item.at("text").string("text"), item.at("style").string("style")});
    }
    axis.min = value.at("min").number("min");
    axis.max = value.at("max").number("max");
    axis.scale = enum_of(value.at("scale"), kScales, "scale");
    return axis;
}

Value series_json(const PatternSeries& series) {
    std::vector<double> x, y;
    x.reserve(series.points.size());
    y.reserve(series.points.size());
    for (const PresentedPoint& point : series.points) {
        x.push_back(point.x);
        y.push_back(point.y);
    }
    return Object{{"kind", name_of(series.kind, kKinds)},
                  {"pane", name_of(series.pane, kPanes)},
                  {"id", series.id},
                  {"label", series.label},
                  {"style", series.style},
                  {"x", numbers(x)},
                  {"y", numbers(y)},
                  {"rows", point_rows(series.rows)},
                  {"bar_low", numbers(series.bar_low)},
                  {"bar_high", numbers(series.bar_high)}};
}

PatternSeries series_of(const Value& value) {
    PatternSeries series;
    series.kind = enum_of(value.at("kind"), kKinds, "kind");
    series.pane = enum_of(value.at("pane"), kPanes, "pane");
    series.id = value.at("id").string("id");
    series.label = value.at("label").string("label");
    series.style = value.at("style").string("style");
    const std::vector<double> x = numbers_of(value.at("x"), "x");
    const std::vector<double> y = numbers_of(value.at("y"), "y");
    if (x.size() != y.size()) {
        throw std::invalid_argument("report JSON: a series' x and y differ in length");
    }
    for (std::size_t i = 0; i < x.size(); ++i) {
        series.points.push_back({x[i], y[i]});
    }
    series.rows = point_rows_of(value.at("rows"));
    series.bar_low = numbers_of(value.at("bar_low"), "bar_low");
    series.bar_high = numbers_of(value.at("bar_high"), "bar_high");
    return series;
}

// Renderer projections are derived from the report's values and style tables. The browser consumes them offline.
const SeriesStyle* browser_style(const std::vector<SeriesStyle>& styles, std::string_view key) {
    const auto found = std::find_if(styles.begin(), styles.end(), [key](const SeriesStyle& style) { return style.key == key; });
    return found == styles.end() ? nullptr : &*found;
}
std::string browser_colour(const std::string& text, const SeriesStyle* style) {
    return "<span style=\"color:" + (style ? style->light : "undefined") + "\">" + text + "</span>";
}
std::string browser_axis_title(const AxisDescription& axis, const std::vector<SeriesStyle>& styles) {
    if (axis.segments.empty()) return axis.title;
    std::string result;
    for (const TitleSegment& segment : axis.segments) result += segment.style.empty() ? segment.text : browser_colour(segment.text, browser_style(styles, segment.style));
    return result;
}
// The source model's non-finite values become JSON null before the browser's original arithmetic (Number(null)).
double browser_number(double value) { return std::isfinite(value) ? value : 0.0; }
// A derived Infinity/NaN must survive the JSON boundary; raw model values keep the existing null representation.
Value renderer_number(double value) {
    if (std::isfinite(value)) return value;
    return Object{{"edi_renderer_number", std::isnan(value) ? "NaN" : value < 0.0 ? "-Infinity" : "Infinity"}};
}
Value browser_trace(const ReportPattern& report, const PatternSeries& series, std::size_t index, const std::vector<SeriesStyle>& styles) {
    const auto* style = browser_style(styles, series.style);
    const auto marked = [style](std::string_view part) {
        const std::string marks = style ? style->mark : "line";
        std::size_t start = 0;
        for (;;) {
            const auto end = marks.find('+', start);
            if (std::string_view(marks).substr(start, end == std::string::npos ? end : end - start) == part) return true;
            if (end == std::string::npos) return false;
            start = end + 1;
        }
    };
    std::string name = browser_colour(series.label, style);
    if (series.kind == SeriesKind::Residual && !report.presentation.y_residual.segments.empty()) name = browser_colour("Residual (", style) + browser_axis_title(report.presentation.y_residual, styles) + browser_colour(")", style);
    Array x, y;
    for (const PresentedPoint& point : series.points) { x.emplace_back(point.x); y.emplace_back(point.y); }
    Object line{{"dash", marked("dash") ? "dash" : "solid"}};
    if (style) { line.emplace_back("color", style->light); line.emplace_back("width", style->width_px); }
    const char* pane = series.pane == Pane::Bragg ? "y2" : series.pane == Pane::Residual ? "y3" : "y";
    Object trace{{"type", "scatter"}, {"name", name}, {"x", std::move(x)}, {"y", std::move(y)}, {"xaxis", "x"}, {"yaxis", pane},
        {"mode", marked("markers") ? "lines+markers" : "lines"}, {"connectgaps", false}, {"opacity", style && std::isfinite(style->opacity) ? style->opacity : 1.0}, {"line", std::move(line)}, {"hovertemplate", "%{x}, %{y}<extra>%{fullData.name}</extra>"}};
    if (marked("markers")) {
        Object marker; if (style) { marker.emplace_back("color", style->light); marker.emplace_back("size", style->marker_px); } trace.emplace_back("marker", std::move(marker));
    }
    if (marked("bars") && series.bar_high.size() == series.points.size()) {
        Array high, low;
        for (std::size_t i = 0; i < series.points.size(); ++i) {
            const double value = series.points[i].y;
            high.push_back(!std::isfinite(value) || !std::isfinite(series.bar_high[i]) ? Value(nullptr) : renderer_number(series.bar_high[i] - value));
            if (!std::isfinite(value)) low.emplace_back(nullptr);
            else if (i >= series.bar_low.size()) low.push_back(renderer_number(std::numeric_limits<double>::quiet_NaN()));
            else low.push_back(renderer_number(value - (std::isfinite(series.bar_low[i]) ? series.bar_low[i] : browser_number(report.presentation.y_main.min))));
        }
        Object errors{{"type", "data"}, {"symmetric", false}, {"thickness", 1}, {"width", 0}, {"array", std::move(high)}, {"arrayminus", std::move(low)}};
        if (style) errors.emplace_back("color", style->light);
        trace.emplace_back("error_y", std::move(errors));
    }
    if (series.kind == SeriesKind::BraggTicks) {
        trace[1].second = browser_colour("Bragg peaks · " + series.label, style);
        if (index < report.hover.size()) trace.emplace_back("text", strings(report.hover[index]));
        for (auto& [key, value] : trace) if (key == "hovertemplate") value = "%{text}<extra>%{fullData.name}</extra>";
    }
    return trace;
}
Value browser_pattern(const ReportPattern& report, const std::vector<SeriesStyle>& styles) {
    Array traces, shapes, annotations;
    if (!report.title.empty()) annotations.emplace_back(Object{{"text", report.title}, {"xref", "paper"}, {"yref", "paper"}, {"x", 0}, {"y", 1}, {"xanchor", "left"}, {"yanchor", "bottom"}, {"showarrow", false}});
    bool bragg = false, residual = false; double fixed = 0.0;
    for (const PaneLayout& pane : report.presentation.layout) { bragg = bragg || pane.pane == Pane::Bragg; residual = residual || pane.pane == Pane::Residual; fixed += browser_number(pane.fixed_px); }
    for (std::size_t i = 0; i < report.presentation.series.size(); ++i) traces.push_back(browser_trace(report, report.presentation.series[i], i, styles));
    const auto* excluded = browser_style(styles, "excluded");
    for (const ExcludedBand& band : report.presentation.excluded) {
        Object shape{{"type", "rect"}, {"xref", "x"}, {"yref", "paper"}, {"x0", band.x_min}, {"x1", band.x_max}, {"y0", 0}, {"y1", 1}, {"line", Object{{"width", 0}}}, {"layer", "below"}};
        if (excluded) { shape.emplace_back("fillcolor", excluded->light); shape.emplace_back("opacity", excluded->opacity); } shapes.emplace_back(std::move(shape));
    }
    if (bragg) for (const BraggRowLabel& label : report.presentation.bragg_labels) annotations.emplace_back(Object{{"text", browser_colour(label.text, browser_style(styles, label.style))}, {"xref", "paper"}, {"yref", "y2"}, {"x", 0}, {"y", label.centre}, {"xanchor", "right"}, {"xshift", -6}, {"showarrow", false}});
    const auto rows = std::count_if(report.presentation.series.begin(), report.presentation.series.end(), [](const PatternSeries& series) { return series.kind == SeriesKind::BraggTicks; });
    return Object{{"traces", std::move(traces)}, {"shapes", std::move(shapes)}, {"annotations", std::move(annotations)}, {"main_title", browser_axis_title(report.presentation.y_main, styles)}, {"residual_title", browser_axis_title(report.presentation.y_residual, styles)}, {"bottom_axis", residual ? "y3" : bragg ? "y2" : "y"}, {"bragg_rows", static_cast<double>(rows)}, {"fixed_height", renderer_number(fixed)}};
}
Value browser_single_crystal(const ReportSingleCrystal& crystal, const std::vector<SeriesStyle>& styles) {
    double low = 0.0, high = 0.0;
    for (std::size_t i = 0; i < crystal.meas.size(); ++i) {
        const double measured = browser_number(crystal.meas[i]);
        const double uncertainty = i < crystal.su.size() ? browser_number(crystal.su[i]) : std::numeric_limits<double>::quiet_NaN();
        const double calculated = i < crystal.calc.size() ? crystal.calc[i] : std::numeric_limits<double>::quiet_NaN();
        for (double end : {measured - uncertainty, measured + uncertainty, calculated}) if (std::isfinite(end)) { low = std::min(low, end); high = std::max(high, end); }
    }
    double pad = (high - low) * 0.05; if (pad == 0.0 || std::isnan(pad)) pad = 1.0;
    Object out{{"range", Array{renderer_number(std::min(0.0, low - pad)), renderer_number(high + pad)}}};
    if (const auto* style = browser_style(styles, "meas.0")) out.emplace_back("color", style->light); return out;
}
Value browser_evolution(const ReportEvolution& series, const std::vector<SeriesStyle>& styles) {
    Array x, y, su, text;
    for (const ReportEvolutionPoint& point : series.points) { x.emplace_back(point.x); y.emplace_back(point.y); su.emplace_back(point.su); text.emplace_back(point.text); }
    Object out{{"x", std::move(x)}, {"y", std::move(y)}, {"su", std::move(su)}, {"text", std::move(text)}, {"title", series.units.empty() ? series.name : series.name + " (" + series.units + ")"}};
    if (const auto* style = browser_style(styles, "meas.0")) out.emplace_back("color", style->light); return out;
}

Value pattern_json(const ReportPattern& pattern, const std::vector<SeriesStyle>& styles) {
    const PatternPresentation& shown = pattern.presentation;
    Array series, excluded, layout, hover;
    for (const PatternSeries& item : shown.series) {
        series.push_back(series_json(item));
    }
    for (const ExcludedBand& band : shown.excluded) {
        excluded.push_back(numbers({band.x_min, band.x_max}));
    }
    for (const PaneLayout& pane : shown.layout) {
        layout.emplace_back(
            Object{{"pane", name_of(pane.pane, kPanes)}, {"stretch", pane.stretch}, {"fixed_px", pane.fixed_px}});
    }
    for (const std::vector<std::string>& texts : pattern.hover) {
        hover.push_back(strings(texts));
    }
    Array labels;
    for (const BraggRowLabel& label : shown.bragg_labels) {
        labels.emplace_back(Object{{"text", label.text}, {"style", label.style}, {"centre", label.centre}});
    }
    return Object{{"current", shown.current},   {"x", axis_json(shown.x)},
                  {"y_main", axis_json(shown.y_main)}, {"y_residual", axis_json(shown.y_residual)},
                  {"series", std::move(series)}, {"excluded", std::move(excluded)},
                  {"layout", std::move(layout)}, {"hover", std::move(hover)},
                  {"bragg_labels", std::move(labels)}, {"title", pattern.title}, {"legend", pattern.legend}, {"browser", browser_pattern(pattern, styles)}};
}

Value single_crystal_json(const ReportSingleCrystal& crystal, const std::vector<SeriesStyle>& styles) {
    const auto indices = [](const std::vector<int>& values) {
        return numbers(std::vector<double>(values.begin(), values.end()));
    };
    return Object{{"h", indices(crystal.h)},         {"k", indices(crystal.k)},       {"l", indices(crystal.l)},
                  {"meas", numbers(crystal.meas)},     {"su", numbers(crystal.su)},     {"calc", numbers(crystal.calc)},
                  {"title", crystal.title},            {"name", crystal.name},          {"x_title", crystal.x_title},
                  {"y_title", crystal.y_title},        {"hover", strings(crystal.hover)}, {"browser", browser_single_crystal(crystal, styles)}};
}

ReportSingleCrystal single_crystal_of(const Value& value) {
    ReportSingleCrystal crystal;
    const auto indices = [&value](const char* key) {
        std::vector<int> out;
        for (const Value& item : value.at(key).array(key)) {
            out.push_back(static_cast<int>(whole_number(item, key, -1e6, 1e6)));
        }
        return out;
    };
    crystal.h = indices("h");
    crystal.k = indices("k");
    crystal.l = indices("l");
    crystal.meas = numbers_of(value.at("meas"), "meas");
    crystal.su = numbers_of(value.at("su"), "su");
    crystal.calc = numbers_of(value.at("calc"), "calc");
    crystal.title = value.at("title").string("title");
    // A report written before the chart carried its labels and hover has none of them: they are made from its numbers
    // as a report makes them, by the dictionary and the report's IUCr rule.
    const Value& hover = value.get("hover");
    if (hover.is_null()) {
        label_single_crystal(crystal, kReportSuRule);
    } else {
        crystal.name = value.at("name").string("name");
        crystal.x_title = value.at("x_title").string("x_title");
        crystal.y_title = value.at("y_title").string("y_title");
        crystal.hover = strings_of(hover, "hover");
    }
    const std::size_t count = crystal.meas.size();
    if (crystal.h.size() != count || crystal.k.size() != count || crystal.l.size() != count ||
        crystal.su.size() != count || (!crystal.calc.empty() && crystal.calc.size() != count)) {
        throw std::invalid_argument("report JSON: a single crystal's columns differ in length");
    }
    return crystal;
}

ReportPattern pattern_of(const Value& value) {
    ReportPattern pattern;
    PatternPresentation& shown = pattern.presentation;
    shown.current = value.at("current").boolean("current");
    shown.x = axis_of(value.at("x"));
    shown.y_main = axis_of(value.at("y_main"));
    shown.y_residual = axis_of(value.at("y_residual"));
    for (const Value& item : value.at("series").array("series")) {
        shown.series.push_back(series_of(item));
    }
    for (const Value& item : value.at("excluded").array("excluded")) {
        const std::vector<double> ends = numbers_of(item, "excluded");
        if (ends.size() != 2) {
            throw std::invalid_argument("report JSON: an excluded band is not two numbers");
        }
        shown.excluded.push_back({ends[0], ends[1]});
    }
    for (const Value& item : value.at("layout").array("layout")) {
        shown.layout.push_back({enum_of(item.at("pane"), kPanes, "pane"), item.at("stretch").number("stretch"),
                                item.at("fixed_px").number("fixed_px")});
    }
    for (const Value& item : value.at("hover").array("hover")) {
        pattern.hover.push_back(strings_of(item, "hover"));
    }
    for (const Value& item : value.at("bragg_labels").array("bragg_labels")) {
        shown.bragg_labels.push_back(
            {item.at("text").string("text"), item.at("style").string("style"), item.at("centre").number("centre")});
    }
    pattern.title = value.at("title").string("title");
    pattern.legend = value.at("legend").boolean("legend");
    return pattern;
}

// --- the structure (ADR-0022)

Value color_json(const Rgb& color) {
    static const char* const kDigits = "0123456789ABCDEF";
    std::string text = "#";
    for (const std::uint8_t channel : {color.r, color.g, color.b}) {
        text += kDigits[channel >> 4U];
        text += kDigits[channel & 0xFU];
    }
    return text;
}

Rgb color_of(const Value& value) {
    const std::string& text = value.string("color");
    const auto digit = [&text](std::size_t at) -> unsigned {
        const char c = text[at];
        if (c >= '0' && c <= '9') {
            return static_cast<unsigned>(c - '0');
        }
        if (c >= 'A' && c <= 'F') {
            return static_cast<unsigned>(c - 'A' + 10);
        }
        throw std::invalid_argument("report JSON: colour '" + text + "' is not #RRGGBB");
    };
    if (text.size() != 7 || text[0] != '#') {
        throw std::invalid_argument("report JSON: colour '" + text + "' is not #RRGGBB");
    }
    const auto channel = [&digit](std::size_t at) { return static_cast<std::uint8_t>(digit(at) * 16U + digit(at + 1)); };
    return {channel(1), channel(3), channel(5)};
}

Value vec_json(const Vec3& vector) { return numbers({vector.x, vector.y, vector.z}); }

Vec3 vec_of(const Value& value) {
    const std::vector<double> parts = numbers_of(value, "vector");
    if (parts.size() != 3) {
        throw std::invalid_argument("report JSON: a vector is not three numbers");
    }
    return {parts[0], parts[1], parts[2]};
}

Value quaternion_json(const std::array<double, 4>& q) { return numbers({q[0], q[1], q[2], q[3]}); }

std::array<double, 4> quaternion_of(const Value& value) {
    const std::vector<double> parts = numbers_of(value, "quaternion");
    if (parts.size() != 4) {
        throw std::invalid_argument("report JSON: a quaternion is not four numbers");
    }
    return {parts[0], parts[1], parts[2], parts[3]};
}

Value letter_json(char letter) { return std::string(1, letter); }

char letter_of(const Value& value) {
    const std::string& text = value.string("letter");
    if (text.size() != 1) {
        throw std::invalid_argument("report JSON: an axis letter is not one character");
    }
    return text[0];
}

Value indices(const std::vector<std::size_t>& list) {
    Array items;
    for (std::size_t item : list) {
        items.push_back(whole(item));
    }
    return items;
}

std::vector<std::size_t> indices_of(const Value& value, const char* what) {
    std::vector<std::size_t> out;
    for (const Value& item : value.array(what)) {
        out.push_back(index_of(item, what));
    }
    return out;
}

Value atom_json(const SceneAtom& atom) {
    Array parts;
    for (const ScenePart& part : atom.parts) {
        parts.emplace_back(Object{{"row", whole(part.row)},
                                  {"site_id", part.site_id},
                                  {"element", part.element},
                                  {"occupancy", part.occupancy},
                                  {"fraction", part.fraction},
                                  {"color", color_json(part.color)}});
    }
    return Object{{"centre", vec_json(atom.centre)},
                  {"row", whole(atom.row)},
                  {"cluster_id", atom.cluster_id},
                  {"table_radius", atom.table_radius},
                  {"radius", atom.radius},
                  {"radius_substituted", atom.radius_substituted},
                  {"ellipsoid", atom.ellipsoid},
                  {"semi_axes", vec_json(atom.semi_axes)},
                  {"orientation", quaternion_json(atom.orientation)},
                  {"label", atom.label},
                  {"asymmetric", atom.asymmetric},
                  {"drawn", atom.drawn},
                  {"parts", std::move(parts)},
                  {"major", whole(atom.major)}};
}

SceneAtom atom_of(const Value& value) {
    SceneAtom atom;
    atom.centre = vec_of(value.at("centre"));
    atom.row = index_of(value.at("row"), "row");
    atom.cluster_id = integer_of<std::int32_t>(value.at("cluster_id"), "cluster_id");
    atom.table_radius = value.at("table_radius").number("table_radius");
    atom.radius = value.at("radius").number("radius");
    atom.radius_substituted = value.at("radius_substituted").boolean("radius_substituted");
    atom.ellipsoid = value.at("ellipsoid").boolean("ellipsoid");
    atom.semi_axes = vec_of(value.at("semi_axes"));
    atom.orientation = quaternion_of(value.at("orientation"));
    atom.label = value.at("label").string("label");
    atom.asymmetric = value.at("asymmetric").boolean("asymmetric");
    atom.drawn = value.at("drawn").boolean("drawn");
    for (const Value& item : value.at("parts").array("parts")) {
        atom.parts.push_back({index_of(item.at("row"), "row"), item.at("site_id").string("site_id"),
                              item.at("element").string("element"), item.at("occupancy").number("occupancy"),
                              item.at("fraction").number("fraction"), color_of(item.at("color"))});
    }
    atom.major = index_of(value.at("major"), "major");
    return atom;
}

Value scene_json(const StructureScene& scene) {
    Array basis, atoms, bonds, edges, axes, labels, legend;
    for (const Vec3& vector : scene.cell_basis) {
        basis.push_back(vec_json(vector));
    }
    for (const SceneAtom& atom : scene.atoms) {
        atoms.push_back(atom_json(atom));
    }
    for (const SceneBond& bond : scene.bonds) {
        bonds.emplace_back(Object{{"row", whole(bond.row)},
                                  {"atom_1", whole(bond.atom_1)},
                                  {"atom_2", whole(bond.atom_2)},
                                  {"start", vec_json(bond.start)},
                                  {"end", vec_json(bond.end)},
                                  {"distance", bond.distance},
                                  {"color_1", color_json(bond.color_1)},
                                  {"color_2", color_json(bond.color_2)}});
    }
    for (const SceneEdge& edge : scene.cell_edges) {
        edges.emplace_back(Object{{"start", vec_json(edge.start)}, {"end", vec_json(edge.end)}});
    }
    for (const SceneAxis& axis : scene.axes) {
        axes.emplace_back(
            Object{{"letter", letter_json(axis.letter)}, {"vector", vec_json(axis.vector)}, {"color", color_json(axis.color)}});
    }
    for (const SceneLabel& label : scene.labels) {
        labels.emplace_back(
            Object{{"atom", whole(label.atom)}, {"anchor", vec_json(label.anchor)}, {"text", label.text}});
    }
    for (const SceneLegendEntry& entry : scene.legend) {
        legend.emplace_back(Object{{"element", entry.element}, {"color", color_json(entry.color)}});
    }
    const SceneFrame& frame = scene.frame;
    return Object{{"current", scene.current},
                  {"has_copies", scene.has_copies},
                  {"cell_basis", std::move(basis)},
                  {"atoms", std::move(atoms)},
                  {"bonds", std::move(bonds)},
                  {"cell_edges", std::move(edges)},
                  {"axes", std::move(axes)},
                  {"labels", std::move(labels)},
                  {"legend", std::move(legend)},
                  {"substituted_elements", strings(scene.substituted_elements)},
                  {"frame", Object{{"target", vec_json(frame.target)},
                                   {"view_direction", vec_json(frame.view_direction)},
                                   {"view_up", vec_json(frame.view_up)},
                                   {"half_width", frame.half_width},
                                   {"half_height", frame.half_height},
                                   {"pad", frame.pad}}}};
}

StructureScene scene_of(const Value& value) {
    StructureScene scene;
    scene.current = value.at("current").boolean("current");
    scene.has_copies = value.at("has_copies").boolean("has_copies");
    const Array& basis = value.at("cell_basis").array("cell_basis");
    if (basis.size() != 3) {
        throw std::invalid_argument("report JSON: the cell basis is not three vectors");
    }
    for (std::size_t i = 0; i < 3; ++i) {
        scene.cell_basis.at(i) = vec_of(basis[i]);
    }
    for (const Value& item : value.at("atoms").array("atoms")) {
        scene.atoms.push_back(atom_of(item));
    }
    for (const Value& item : value.at("bonds").array("bonds")) {
        scene.bonds.push_back({index_of(item.at("row"), "row"), index_of(item.at("atom_1"), "atom_1"),
                               index_of(item.at("atom_2"), "atom_2"), vec_of(item.at("start")),
                               vec_of(item.at("end")), item.at("distance").number("distance"),
                               color_of(item.at("color_1")), color_of(item.at("color_2"))});
    }
    for (const Value& item : value.at("cell_edges").array("cell_edges")) {
        scene.cell_edges.push_back({vec_of(item.at("start")), vec_of(item.at("end"))});
    }
    for (const Value& item : value.at("axes").array("axes")) {
        scene.axes.push_back({letter_of(item.at("letter")), vec_of(item.at("vector")), color_of(item.at("color"))});
    }
    for (const Value& item : value.at("labels").array("labels")) {
        scene.labels.push_back(
            {index_of(item.at("atom"), "atom"), vec_of(item.at("anchor")), item.at("text").string("text")});
    }
    for (const Value& item : value.at("legend").array("legend")) {
        scene.legend.push_back({item.at("element").string("element"), color_of(item.at("color"))});
    }
    scene.substituted_elements = strings_of(value.at("substituted_elements"), "substituted_elements");
    const Value& frame = value.at("frame");
    scene.frame = {vec_of(frame.at("target")), vec_of(frame.at("view_direction")), vec_of(frame.at("view_up")),
                   frame.at("half_width").number("half_width"), frame.at("half_height").number("half_height"),
                   frame.at("pad").number("pad")};
    return scene;
}

Value view_json(const SceneView& view) {
    return Object{{"direction", vec_json(view.direction)},
                  {"up", vec_json(view.up)},
                  {"magnification", view.magnification},
                  {"pan_x", view.pan_x},
                  {"pan_y", view.pan_y},
                  {"projection", name_of(view.projection, kProjections)}};
}

SceneView view_of(const Value& value) {
    return {vec_of(value.at("direction")),       vec_of(value.at("up")),
            value.at("magnification").number("magnification"), value.at("pan_x").number("pan_x"),
            value.at("pan_y").number("pan_y"),   enum_of(value.at("projection"), kProjections, "projection")};
}

Value instances_json(const std::vector<SceneInstance>& list) {
    Array items;
    items.reserve(list.size());
    for (const SceneInstance& instance : list) {
        items.emplace_back(Object{{"position", vec_json(instance.position)},
                                  {"scale", vec_json(instance.scale)},
                                  {"rotation", quaternion_json(instance.rotation)},
                                  {"color", color_json(instance.color)},
                                  {"atom", whole(instance.atom)}});
    }
    return items;
}

std::vector<SceneInstance> instances_of(const Value& value, const char* what) {
    std::vector<SceneInstance> out;
    for (const Value& item : value.array(what)) {
        out.push_back({vec_of(item.at("position")), vec_of(item.at("scale")), quaternion_of(item.at("rotation")),
                       color_of(item.at("color")), index_of(item.at("atom"), "atom")});
    }
    return out;
}

Value drawing_json(const SceneDrawing& drawing) {
    Array triad;
    for (const SceneArrow& arrow : drawing.triad) {
        triad.emplace_back(Object{{"letter", letter_json(arrow.letter)},
                                  {"color", color_json(arrow.color)},
                                  {"origin", vec_json(arrow.origin)},
                                  {"direction", vec_json(arrow.direction)},
                                  {"shaft_length", arrow.shaft_length},
                                  {"shaft_radius", arrow.shaft_radius},
                                  {"head_length", arrow.head_length},
                                  {"head_radius", arrow.head_radius},
                                  {"letter_anchor", vec_json(arrow.letter_anchor)}});
    }
    return Object{{"fitted_half_height", drawing.fitted_half_height},
                  {"spheres", instances_json(drawing.spheres)},
                  {"cylinders", instances_json(drawing.cylinders)},
                  {"shared", indices(drawing.shared)},
                  {"triad", std::move(triad)}};
}

SceneDrawing drawing_of(const Value& value) {
    SceneDrawing drawing;
    drawing.fitted_half_height = value.at("fitted_half_height").number("fitted_half_height");
    drawing.spheres = instances_of(value.at("spheres"), "spheres");
    drawing.cylinders = instances_of(value.at("cylinders"), "cylinders");
    drawing.shared = indices_of(value.at("shared"), "shared");
    for (const Value& item : value.at("triad").array("triad")) {
        drawing.triad.push_back({letter_of(item.at("letter")), color_of(item.at("color")), vec_of(item.at("origin")),
                                 vec_of(item.at("direction")), item.at("shaft_length").number("shaft_length"),
                                 item.at("shaft_radius").number("shaft_radius"),
                                 item.at("head_length").number("head_length"),
                                 item.at("head_radius").number("head_radius"), vec_of(item.at("letter_anchor"))});
    }
    return drawing;
}

Value browser_mesh(const SharedSiteMesh& mesh) {
    Array positions, normals, colours, triangles;
    for (const SharedSiteVertex& vertex : mesh.vertices) {
        for (double value : {vertex.position.x, vertex.position.y, vertex.position.z}) positions.push_back(renderer_number(value));
        for (double value : {vertex.normal.x, vertex.normal.y, vertex.normal.z}) normals.push_back(renderer_number(value));
        for (double value : {vertex.color.x, vertex.color.y, vertex.color.z}) colours.push_back(renderer_number(value));
    }
    for (std::uint32_t index : mesh.indices) triangles.emplace_back(static_cast<double>(index));
    return Object{{"positions", std::move(positions)}, {"normals", std::move(normals)}, {"colours", std::move(colours)}, {"indices", std::move(triangles)}};
}
Value browser_structure(const ReportStructure& structure, const std::vector<SceneStyle>& style_table) {
    const auto& scene = structure.scene; const auto& drawing = structure.drawing;
    if (!scene.current || drawing.spheres.size() + drawing.shared.size() == 0) return Object{{"empty", true}};
    const auto basis = shared_site_browser_basis(scene);
    Object subsets;
    for (const std::string subset : {"all", "asymmetric", "none"}) {
        const auto visible = [&](std::size_t atom) { return subset == "all" || (subset == "asymmetric" && scene.atoms[atom].asymmetric); };
        std::vector<SceneInstance> spheres, bonds; std::vector<std::size_t> shared; Array labels;
        for (const SceneInstance& instance : drawing.spheres) if (visible(instance.atom)) spheres.push_back(instance);
        for (std::size_t atom : drawing.shared) if (visible(atom)) shared.push_back(atom);
        const std::size_t halves = std::min(drawing.cylinders.size(), 2 * scene.bonds.size());
        for (std::size_t i = 0; i < halves; ++i) {
            const SceneBond& bond = scene.bonds[i / 2]; if (visible(bond.atom_1) && visible(bond.atom_2)) bonds.push_back(drawing.cylinders[i]);
        }
        for (const SceneLabel& label : structure.labels) labels.emplace_back(visible(label.atom));
        const auto mesh = shared_site_mesh(scene, shared, 32, 16, SharedSiteMeshProfile::Three160, basis);
        subsets.emplace_back(subset, Object{{"spheres", instances_json(spheres)}, {"shared", browser_mesh(mesh)}, {"bonds", instances_json(bonds)}, {"labels", std::move(labels)}});
    }
    const std::size_t halves = std::min(drawing.cylinders.size(), 2 * scene.bonds.size());
    const std::vector<SceneInstance> cell(drawing.cylinders.begin() + static_cast<std::ptrdiff_t>(halves), drawing.cylinders.end());
    Object styles;
    for (const SceneStyle& style : style_table) {
        if (std::any_of(styles.begin(), styles.end(), [&](const auto& item) { return item.first == style.key; })) continue;
        styles.emplace_back(style.key, Object{{"key", style.key}, {"light", style.light}, {"dark", style.dark}, {"value", style.value}});
    }
    const Object boolean_next{{"false", true}, {"true", false}}, boolean_pressed{{"false", false}, {"true", true}};
    Object next{{"atoms", Object{{"all", scene.has_copies ? "asymmetric" : "none"}, {"asymmetric", "none"}, {"none", "all"}}}};
    Object pressed{{"atoms", Object{{"all", true}, {"asymmetric", true}, {"none", false}}}};
    for (const char* key : {"labels", "bonds", "cell", "axes"}) { next.emplace_back(key, boolean_next); pressed.emplace_back(key, boolean_pressed); }
    return Object{{"empty", !scene.current || drawing.spheres.size() + drawing.shared.size() == 0}, {"subsets", std::move(subsets)}, {"cell", instances_json(cell)}, {"styles", std::move(styles)}, {"next", std::move(next)}, {"pressed", std::move(pressed)},
        {"controls", Object{{"atoms", !scene.atoms.empty()}, {"labels", !scene.atoms.empty() && !structure.labels.empty()}, {"bonds", !scene.atoms.empty() && !scene.bonds.empty()}, {"atom_title", scene.has_copies ? "Atoms: all / asymmetric unit / none" : "Atoms: show / hide"}}}};
}

// --- the style tables

Value pattern_styles_json(const std::vector<SeriesStyle>& table) {
    Array items;
    for (const SeriesStyle& style : table) {
        items.emplace_back(Object{{"key", style.key},
                                  {"light", style.light},
                                  {"dark", style.dark},
                                  {"mark", style.mark},
                                  {"width_px", style.width_px},
                                  {"opacity", style.opacity},
                                  {"marker_px", style.marker_px}});
    }
    return items;
}

std::vector<SeriesStyle> pattern_styles_of(const Value& value) {
    std::vector<SeriesStyle> out;
    for (const Value& item : value.array("pattern_styles")) {
        out.push_back({item.at("key").string("key"), item.at("light").string("light"), item.at("dark").string("dark"),
                       item.at("mark").string("mark"), item.at("width_px").number("width_px"),
                       item.at("opacity").number("opacity"), item.at("marker_px").number("marker_px")});
    }
    return out;
}

Value structure_styles_json(const std::vector<SceneStyle>& table) {
    Array items;
    for (const SceneStyle& style : table) {
        items.emplace_back(
            Object{{"key", style.key}, {"light", style.light}, {"dark", style.dark}, {"value", style.value}});
    }
    return items;
}

std::vector<SceneStyle> structure_styles_of(const Value& value) {
    std::vector<SceneStyle> out;
    for (const Value& item : value.array("structure_styles")) {
        out.push_back({item.at("key").string("key"), item.at("light").string("light"), item.at("dark").string("dark"),
                       item.at("value").number("value")});
    }
    return out;
}

// The model's indices, as build_report makes them: each names an entry of the collection it addresses, and a series'
// per-point arrays are as long as its points. Renderers index with them, so a model that breaks one is refused here
// rather than read out of bounds there.
void check_indices(const ReportModel& model) {
    const auto refuse = [](const std::string& what) { throw std::invalid_argument("report JSON: " + what); };
    for (const ReportStructure& structure : model.structures) {
        const std::size_t atoms = structure.scene.atoms.size();
        const auto check_atom = [atoms, &refuse](std::size_t atom, const char* what) {
            if (atom >= atoms) {
                refuse(std::string(what) + " names atom " + std::to_string(atom) + " of " + std::to_string(atoms));
            }
        };
        for (const SceneAtom& atom : structure.scene.atoms) {
            if (atom.major >= atom.parts.size()) {
                refuse("an atom's major part " + std::to_string(atom.major) + " is not one of its " +
                       std::to_string(atom.parts.size()) + " parts");
            }
        }
        for (const SceneBond& bond : structure.scene.bonds) {
            check_atom(bond.atom_1, "a bond");
            check_atom(bond.atom_2, "a bond");
        }
        for (const SceneLabel& label : structure.scene.labels) {
            check_atom(label.atom, "a scene label");
        }
        for (const SceneLabel& label : structure.labels) {
            check_atom(label.atom, "a label");
        }
        for (const SceneInstance& sphere : structure.drawing.spheres) {
            check_atom(sphere.atom, "a sphere");
        }
        for (const std::size_t site : structure.drawing.shared) {
            check_atom(site, "a shared site");
        }
        // A structure the viewer draws (its scene current, a sphere or shared site to draw) offers a view along each
        // axis, so it has all three; another has three or none (a report without its figures).
        const bool drawn =
            structure.scene.current && structure.drawing.spheres.size() + structure.drawing.shared.size() > 0;
        if (structure.along.size() != 3 && (drawn || !structure.along.empty())) {
            refuse("a structure's views along the axes are not three");
        }
    }
    for (const ReportExperiment& experiment : model.experiments) {
        for (const PatternSeries& series : experiment.pattern.presentation.series) {
            // A measured series has a data row and both bar ends for every point; another series' bars are none or
            // one per point.
            const std::size_t points = series.points.size();
            const bool measured = series.kind == SeriesKind::Measured;
            const auto per_point = [points, measured](std::size_t size) {
                return size == points || (!measured && size == 0);
            };
            if (!per_point(series.bar_low.size()) || !per_point(series.bar_high.size()) ||
                (measured && series.rows.size() != points)) {
                refuse("series '" + series.id + "' has " + std::to_string(series.bar_low.size()) + " and " +
                       std::to_string(series.bar_high.size()) + " error bars and " +
                       std::to_string(series.rows.size()) + " rows for " + std::to_string(points) + " points");
            }
        }
    }
}

}  // namespace

std::string report_to_json(const ReportModel& model) {
    check_indices(model);
    Array sections;
    for (ReportSection section : model.sections) {
        sections.emplace_back(report_section_name(section));
    }
    Array contents;
    for (const ReportContentsItem& item : model.contents) {
        contents.emplace_back(Object{{"key", item.key}, {"title", item.title}, {"included", item.included}});
    }
    Value correlations;
    if (model.correlations.has_value()) {
        const ReportCorrelations& matrix = *model.correlations;
        correlations = Object{{"labels", strings(matrix.labels)},
                              {"values", numbers(matrix.values)},
                              {"level", matrix.level},
                              {"available", matrix.available},
                              {"empty_text", matrix.empty_text}};
    }
    Array parameters;
    for (const ReportParameter& parameter : model.parameters) {
        parameters.emplace_back(Object{{"unique_name", parameter.unique_name},
                                       {"label", parameter.label},
                                       {"value", parameter.value},
                                       {"su", parameter.su ? Value(*parameter.su) : Value(nullptr)},
                                       {"text", parameter.text},
                                       {"units", parameter.units},
                                       {"start", parameter.start ? Value(*parameter.start) : Value(nullptr)},
                                       {"free", parameter.free}});
    }
    Value evolution;
    if (model.evolution.has_value()) {
        Array series;
        for (const ReportEvolution& one : *model.evolution) {
            Array points;
            for (const ReportEvolutionPoint& point : one.points) {
                points.emplace_back(
                    Object{{"x", point.x}, {"y", point.y}, {"su", point.su}, {"text", point.text}});
            }
            series.emplace_back(Object{
                {"name", one.name}, {"units", one.units}, {"x_title", one.x_title}, {"points", std::move(points)}, {"browser", browser_evolution(one, model.pattern_styles)}});
        }
        evolution = std::move(series);
    }
    Array structures;
    for (const ReportStructure& structure : model.structures) {
        Array along, labels;
        for (const SceneView& view : structure.along) {
            along.push_back(view_json(view));
        }
        for (const SceneLabel& label : structure.labels) {
            labels.emplace_back(
                Object{{"atom", whole(label.atom)}, {"anchor", vec_json(label.anchor)}, {"text", label.text}});
        }
        structures.emplace_back(Object{{"id", structure.id},
                                       {"categories", categories(structure.categories)},
                                       {"scene", scene_json(structure.scene)},
                                       {"view", view_json(structure.view)},
                                       {"drawing", drawing_json(structure.drawing)},
                                       {"along", std::move(along)},
                                       {"labels", std::move(labels)}, {"browser", browser_structure(structure, model.structure_styles)}});
    }
    Array experiments;
    for (const ReportExperiment& experiment : model.experiments) {
        Object item{{"id", experiment.id},
                    {"categories", categories(experiment.categories)},
                    {"pattern", pattern_json(experiment.pattern, model.pattern_styles)}};
        // Only a single crystal carries its chart.
        if (experiment.single_crystal) {
            item.emplace_back("single_crystal", single_crystal_json(*experiment.single_crystal, model.pattern_styles));
        }
        experiments.emplace_back(std::move(item));
    }
    const Object document{{"schema_version", model.schema_version},
                          {"generated", model.generated},
                          {"sections", std::move(sections)},
                          {"contents", std::move(contents)},
                          {"name", model.name},
                          {"title", model.title},
                          {"authors", model.authors},
                          {"description", model.description},
                          {"structure_ids", strings(model.structure_ids)},
                          {"experiment_ids", strings(model.experiment_ids)},
                          {"analysis_categories", categories(model.analysis)},
                          {"parameters", std::move(parameters)},
                          {"fitted", model.fitted},
                          {"correlations", std::move(correlations)},
                          {"evolution", std::move(evolution)},
                          {"structures", std::move(structures)},
                          {"experiments", std::move(experiments)},
                          {"pattern_styles", pattern_styles_json(model.pattern_styles)},
                          {"structure_styles", structure_styles_json(model.structure_styles)}};
    return json::write(document);
}

ReportModel report_from_json(const std::string& text) {
    const Value document = json::parse(text);
    ReportModel model;
    const double version = document.at("schema_version").number("schema_version");
    if (version != kReportSchemaVersion) {
        throw std::invalid_argument("report JSON: schema version " + std::to_string(version) + ", this reader reads " +
                                    std::to_string(kReportSchemaVersion));
    }
    model.generated = document.at("generated").string("generated");
    for (const Value& name : document.at("sections").array("sections")) {
        const std::optional<ReportSection> section = report_section_from_name(name.string("section"));
        if (!section) {
            throw std::invalid_argument("report JSON: unknown section '" + name.string("section") + "'");
        }
        model.sections.push_back(*section);
    }
    for (const Value& item : document.at("contents").array("contents")) {
        model.contents.push_back(
            {item.at("key").string("key"), item.at("title").string("title"), item.at("included").boolean("included")});
    }
    model.name = document.at("name").string("name");
    model.title = document.at("title").string("title");
    model.authors = document.at("authors").string("authors");
    model.description = document.at("description").string("description");
    model.structure_ids = strings_of(document.at("structure_ids"), "structure_ids");
    model.experiment_ids = strings_of(document.at("experiment_ids"), "experiment_ids");
    model.analysis = categories_of(document.at("analysis_categories"), "analysis_categories");
    for (const Value& item : document.at("parameters").array("parameters")) {
        const auto optional_number = [](const Value& value) {
            return value.is_null() ? std::optional<double>() : std::optional<double>(value.number("number"));
        };
        model.parameters.push_back({item.at("unique_name").string("unique_name"), item.at("label").string("label"),
                                    item.at("value").number("value"), optional_number(item.at("su")),
                                    item.at("text").string("text"), item.at("units").string("units"),
                                    optional_number(item.at("start")), item.at("free").boolean("free")});
    }
    model.fitted = document.at("fitted").boolean("fitted");
    const Value& evolution = document.at("evolution");
    if (!evolution.is_null()) {
        std::vector<ReportEvolution> series;
        for (const Value& item : evolution.array("evolution")) {
            const Value& units = item.get("units");
            ReportEvolution one{item.at("name").string("name"), item.at("x_title").string("x_title"), {},
                                units.is_null() ? std::string() : units.string("units")};
            for (const Value& point : item.at("points").array("points")) {
                one.points.push_back({point.at("x").number("x"), point.at("y").number("y"),
                                      point.at("su").number("su"), point.at("text").string("text")});
            }
            series.push_back(std::move(one));
        }
        model.evolution = std::move(series);
    }
    const Value& correlations = document.at("correlations");
    if (!correlations.is_null()) {
        ReportCorrelations matrix;
        matrix.labels = strings_of(correlations.at("labels"), "labels");
        matrix.values = numbers_of(correlations.at("values"), "values");
        matrix.level = correlations.at("level").number("level");
        matrix.available = static_cast<int>(whole_number(correlations.at("available"), "available", 0.0,
                                                         static_cast<double>(std::numeric_limits<int>::max())));
        matrix.empty_text = correlations.at("empty_text").string("empty_text");
        model.correlations = std::move(matrix);
    }
    for (const Value& item : document.at("structures").array("structures")) {
        ReportStructure structure{item.at("id").string("id"), categories_of(item.at("categories"), "categories"),
                                  scene_of(item.at("scene")),  view_of(item.at("view")),
                                  drawing_of(item.at("drawing")), {}, {}};
        for (const Value& view : item.at("along").array("along")) {
            structure.along.push_back(view_of(view));
        }
        for (const Value& label : item.at("labels").array("labels")) {
            structure.labels.push_back(
                {index_of(label.at("atom"), "atom"), vec_of(label.at("anchor")), label.at("text").string("text")});
        }
        model.structures.push_back(std::move(structure));
    }
    for (const Value& item : document.at("experiments").array("experiments")) {
        ReportExperiment experiment{item.at("id").string("id"), categories_of(item.at("categories"), "categories"),
                                    pattern_of(item.at("pattern")), std::nullopt};
        if (const Value& crystal = item.get("single_crystal"); !crystal.is_null()) {
            experiment.single_crystal = single_crystal_of(crystal);
        }
        model.experiments.push_back(std::move(experiment));
    }
    model.pattern_styles = pattern_styles_of(document.at("pattern_styles"));
    model.structure_styles = structure_styles_of(document.at("structure_styles"));
    check_indices(model);
    return model;
}

}  // namespace edi
