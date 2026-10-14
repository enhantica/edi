// SPDX-License-Identifier: BSD-3-Clause
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>

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
    return static_cast<std::size_t>(whole_number(value, what, 0.0, largest));
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

constexpr std::array<std::pair<SeriesKind, const char*>, 5> kKinds{{{SeriesKind::Measured, "measured"},
                                                                    {SeriesKind::Calculated, "calculated"},
                                                                    {SeriesKind::Background, "background"},
                                                                    {SeriesKind::Residual, "residual"},
                                                                    {SeriesKind::BraggTicks, "bragg"}}};
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

Value pattern_json(const ReportPattern& pattern) {
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
                  {"bragg_labels", std::move(labels)}, {"title", pattern.title}, {"legend", pattern.legend}};
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

}  // namespace

std::string report_to_json(const ReportModel& model) {
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
                {"name", one.name}, {"units", one.units}, {"x_title", one.x_title}, {"points", std::move(points)}});
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
                                       {"labels", std::move(labels)}});
    }
    Array experiments;
    for (const ReportExperiment& experiment : model.experiments) {
        experiments.emplace_back(Object{{"id", experiment.id},
                                        {"categories", categories(experiment.categories)},
                                        {"pattern", pattern_json(experiment.pattern)}});
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
        model.experiments.push_back(
            {item.at("id").string("id"), categories_of(item.at("categories"), "categories"), pattern_of(item.at("pattern"))});
    }
    model.pattern_styles = pattern_styles_of(document.at("pattern_styles"));
    model.structure_styles = structure_styles_of(document.at("structure_styles"));
    return model;
}

}  // namespace edi
