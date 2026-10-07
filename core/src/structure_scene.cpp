// SPDX-License-Identifier: BSD-3-Clause
// ADR-0022: the structure scene. See edi/structure_scene.hpp for the contract. Every position, bond end and
// bond distance is crysta's value, carried bit for bit; the only arithmetic on crysta's numbers is the
// cell's corners, the drawn radius, the shares of a shared site, the home frame and, in the ADP view, each
// site's displacement turned onto its copies (a draft; crysta is to carry it per row).

#include "edi/structure_scene.hpp"

#include "edi/io.hpp"
#include "crysta/adp.hpp"
#include "edi/symmetry.hpp"
#include "crysta/tokens.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <limits>
#include <locale>
#include <numbers>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace edi {

namespace detail {
// The embedded copy of data/elements/element-styles.tsv (core/CMakeLists.txt generates its definition).
extern const char* const kElementStylesTsv;
}  // namespace detail

namespace {

constexpr Rgb kUnknownColor{255, 192, 203};  // diffraction-lib's fallback pink
constexpr double kUnknownRadius = 1.0;       // Angstrom, diffraction-lib's and crysta's bond rule's
constexpr double kHomeMargin = 1.24;         // diffraction-lib's margin for a scene with its triad
constexpr double kMinHalfExtent = 0.5;       // Angstrom
constexpr double kPerspectiveHalfFovDeg = 15.0;
constexpr double kPerspectiveDistance = 1.05;  // the camera stands back 1.05 times the fitted extent
constexpr double kZoomPerNotch = 1.25;
constexpr double kMinMagnification = 0.05;
constexpr double kMaxMagnification = 100.0;
constexpr double kDegree = std::numbers::pi / 180.0;

// ---- vectors ---------------------------------------------------------------------------------------

Vec3 add(const Vec3& a, const Vec3& b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
Vec3 sub(const Vec3& a, const Vec3& b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
Vec3 mul(const Vec3& a, double s) { return {a.x * s, a.y * s, a.z * s}; }
double dot(const Vec3& a, const Vec3& b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
Vec3 cross(const Vec3& a, const Vec3& b) {
    return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}
double norm(const Vec3& a) { return std::sqrt(dot(a, a)); }
Vec3 divided(const Vec3& a, double s) { return {a.x / s, a.y / s, a.z / s}; }
Vec3 unit(const Vec3& a) {
    const double length = norm(a);
    return length > 0.0 ? divided(a, length) : Vec3{};
}
// `v` turned by `angle` radians about the unit axis `axis` (Rodrigues).
Vec3 turned(const Vec3& v, const Vec3& axis, double angle) {
    const double c = std::cos(angle), s = std::sin(angle);
    return add(add(mul(v, c), mul(cross(axis, v), s)), mul(axis, dot(axis, v) * (1.0 - c)));
}

// ---- the element table -----------------------------------------------------------------------------

[[noreturn]] void refuse_row(std::size_t line, const std::string& text, const std::string& why) {
    throw std::runtime_error("element-styles.tsv line " + std::to_string(line) + " ('" + text + "'): " + why);
}

// Locale-independent, the whole token (io.cpp's to_double device: libc++ deletes floating from_chars).
std::optional<double> parse_radius(const std::string& token) {
    double value = 0.0;
    std::istringstream stream(token);
    stream.imbue(std::locale::classic());
    stream >> value;
    if (stream.fail() || !stream.eof() || !std::isfinite(value) || value <= 0.0) {
        return std::nullopt;
    }
    return value;
}

std::optional<Rgb> parse_color(const std::string& token) {
    if (token.size() != 7 || token[0] != '#') {
        return std::nullopt;
    }
    std::uint8_t bytes[3] = {};
    for (int i = 0; i != 3; ++i) {
        const char* first = token.data() + 1 + 2 * i;
        const auto [ptr, ec] = std::from_chars(first, first + 2, bytes[i], 16);
        if (ec != std::errc() || ptr != first + 2) {
            return std::nullopt;
        }
    }
    return Rgb{bytes[0], bytes[1], bytes[2]};
}

std::vector<std::string> split_tabs(const std::string& line) {
    std::vector<std::string> fields;
    std::size_t start = 0;
    while (true) {
        const std::size_t tab = line.find('\t', start);
        fields.push_back(line.substr(start, tab == std::string::npos ? std::string::npos : tab - start));
        if (tab == std::string::npos) {
            return fields;
        }
        start = tab + 1;
    }
}

std::vector<ElementStyle> parse_element_styles(const std::string& text) {
    static const char* const kHeader = "symbol\tjmol\tvesta\tcovalent\tvan_der_waals\tionic";
    std::vector<ElementStyle> rows;
    std::istringstream lines(text);
    std::string line;
    std::size_t number = 0;
    while (std::getline(lines, line)) {
        ++number;
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (number == 1) {
            if (line != kHeader) {
                refuse_row(number, line, "the header is not the declared columns");
            }
            continue;
        }
        if (line.empty()) {
            continue;
        }
        const std::vector<std::string> fields = split_tabs(line);
        if (fields.size() != 6) {
            refuse_row(number, line, "a row has 6 tab-separated fields");
        }
        ElementStyle style;
        style.symbol = fields[0];
        if (style.symbol.empty() || element_of(style.symbol) != style.symbol) {
            refuse_row(number, line, "the symbol is not an element symbol");
        }
        const auto jmol = parse_color(fields[1]);
        if (!jmol) {
            refuse_row(number, line, "the Jmol colour is not #RRGGBB");
        }
        style.jmol = *jmol;
        if (!fields[2].empty()) {
            style.vesta = parse_color(fields[2]);
            if (!style.vesta) {
                refuse_row(number, line, "the VESTA colour is not #RRGGBB");
            }
        }
        const auto covalent = parse_radius(fields[3]);
        const auto van_der_waals = parse_radius(fields[4]);
        if (!covalent || !van_der_waals) {
            refuse_row(number, line, "a covalent or van der Waals radius is not a positive number");
        }
        style.covalent = *covalent;
        style.van_der_waals = *van_der_waals;
        if (!fields[5].empty()) {
            style.ionic = parse_radius(fields[5]);
            if (!style.ionic) {
                refuse_row(number, line, "the ionic radius is not a positive number");
            }
        }
        for (const ElementStyle& earlier : rows) {
            if (earlier.symbol == style.symbol) {
                refuse_row(number, line, "the symbol is listed twice");
            }
        }
        rows.push_back(std::move(style));
    }
    if (rows.empty()) {
        throw std::runtime_error("element-styles.tsv: the embedded table has no row");
    }
    return rows;
}

const ElementStyle* find_element(std::string_view element) {
    static const std::unordered_map<std::string, std::size_t> index = [] {
        std::unordered_map<std::string, std::size_t> map;
        const auto& table = element_style_table();
        for (std::size_t i = 0; i != table.size(); ++i) {
            map.emplace(table[i].symbol, i);
        }
        return map;
    }();
    if (element.empty()) {
        return nullptr;
    }
    const auto found = index.find(std::string(element));
    return found == index.end() ? nullptr : &element_style_table()[found->second];
}

// ---- the scene -------------------------------------------------------------------------------------

template <class T>
std::size_t column_size(const SceneSource::Column<T>& column) {
    return column ? column->size() : 0;
}
template <class T>
T column_value(const SceneSource::Column<T>& column, std::size_t row, T fallback) {
    return column && row < column->size() ? (*column)[row] : fallback;
}

Vec3 row_centre(const SceneSource& source, std::size_t row) {
    return {(*source.cartn_x)[row], (*source.cartn_y)[row], (*source.cartn_z)[row]};
}

// I9: diffraction-lib's home view.
SceneFrame home_frame(const StructureScene& scene, bool has_cell) {
    SceneFrame frame;
    Vec3 middle{0.0, 1.0, 0.0};
    Vec3 direction = unit(Vec3{1.0, 0.8, 1.5});
    const auto& basis = scene.cell_basis;
    if (has_cell) {
        std::array<int, 3> order{0, 1, 2};
        std::stable_sort(order.begin(), order.end(),
                         [&](int p, int q) { return norm(basis[p]) > norm(basis[q]); });
        const Vec3 longest = unit(basis[order[0]]);
        middle = unit(basis[order[1]]);
        const Vec3 shortest = unit(basis[order[2]]);
        direction = unit(add(add(mul(longest, 0.37), mul(middle, 0.24)), mul(shortest, 0.90)));
    }
    const Vec3 right = unit(cross(middle, direction));
    const Vec3 up = cross(direction, right);
    const Vec3 centre = mul(add(add(basis[0], basis[1]), basis[2]), 0.5);

    std::vector<Vec3> points;
    double pad = 0.0;
    for (const SceneAtom& atom : scene.atoms) {
        points.push_back(atom.centre);
        pad = std::max(pad, atom.radius);
    }
    if (has_cell) {
        for (int i = 0; i != 2; ++i) {
            for (int j = 0; j != 2; ++j) {
                for (int k = 0; k != 2; ++k) {
                    Vec3 corner;
                    if (i != 0) corner = add(corner, basis[0]);
                    if (j != 0) corner = add(corner, basis[1]);
                    if (k != 0) corner = add(corner, basis[2]);
                    points.push_back(corner);
                }
            }
        }
    }
    double u_min = 0.0, u_max = 0.0, v_min = 0.0, v_max = 0.0;
    if (!points.empty()) {
        u_min = v_min = std::numeric_limits<double>::infinity();
        u_max = v_max = -std::numeric_limits<double>::infinity();
        for (const Vec3& p : points) {
            const Vec3 d = sub(p, centre);
            const double u = dot(d, right), v = dot(d, up);
            u_min = std::min(u_min, u);
            u_max = std::max(u_max, u);
            v_min = std::min(v_min, v);
            v_max = std::max(v_max, v);
        }
    }
    frame.target = add(add(centre, mul(right, (u_min + u_max) / 2.0)), mul(up, (v_min + v_max) / 2.0));
    frame.view_direction = direction;
    frame.view_up = up;
    frame.pad = pad;
    frame.half_width = std::max((u_max - u_min) / 2.0 + pad, kMinHalfExtent) * kHomeMargin;
    frame.half_height = std::max((v_max - v_min) / 2.0 + pad, kMinHalfExtent) * kHomeMargin;
    return frame;
}

// I13's H: the fitted half height of the home view in this viewport.
double fitted_half_height(const SceneFrame& frame, const Viewport& viewport) {
    if (!(viewport.width > 0.0) || !(viewport.height > 0.0)) {
        return std::max(frame.half_height, frame.half_width);
    }
    return std::max(frame.half_height, frame.half_width * viewport.height / viewport.width);
}

double perspective_distance(double h) {
    return kPerspectiveDistance * h / std::tan(kPerspectiveHalfFovDeg * kDegree);
}

// The quaternion (w, x, y, z) that turns +y onto the unit vector `v`.
std::array<double, 4> rotation_from_y(const Vec3& v) {
    const double w = std::sqrt(std::max(0.0, (1.0 + v.y) / 2.0));
    const double s = std::sqrt(std::max(0.0, (1.0 - v.y) / 2.0));
    Vec3 axis = cross(Vec3{0.0, 1.0, 0.0}, v);  // (v.z, 0, -v.x)
    if (norm(axis) > 0.0) {
        axis = unit(axis);
    } else {
        axis = {1.0, 0.0, 0.0};  // along +y (s = 0) or -y: a half turn about x
    }
    return {w, axis.x * s, axis.y * s, axis.z * s};
}

// ---- displacement ellipsoids --------------------------------------------------------------------------

using Matrix3 = std::array<double, 9>;  // row-major

Matrix3 product(const Matrix3& a, const Matrix3& b) {
    Matrix3 out{};
    for (int i = 0; i != 3; ++i) {
        for (int j = 0; j != 3; ++j) {
            for (int k = 0; k != 3; ++k) {
                out[3 * i + j] += a[3 * i + k] * b[3 * k + j];
            }
        }
    }
    return out;
}

Matrix3 transposed(const Matrix3& a) {
    return {a[0], a[3], a[6], a[1], a[4], a[7], a[2], a[5], a[8]};
}

Matrix3 inverted(const Matrix3& m) {
    const double det = m[0] * (m[4] * m[8] - m[5] * m[7]) - m[1] * (m[3] * m[8] - m[5] * m[6]) +
                       m[2] * (m[3] * m[7] - m[4] * m[6]);
    Matrix3 out{};
    for (int i = 0; i != 3; ++i) {
        for (int j = 0; j != 3; ++j) {
            const int r1 = (j + 1) % 3, r2 = (j + 2) % 3, c1 = (i + 1) % 3, c2 = (i + 2) % 3;
            out[3 * i + j] = (m[3 * r1 + c1] * m[3 * r2 + c2] - m[3 * r1 + c2] * m[3 * r2 + c1]) / det;
        }
    }
    return out;
}

// The radius, in units of the RMS displacement, that holds `probability` of a three-dimensional Gaussian: the
// chi distribution's quantile for three degrees of freedom (ORTEP's scale; 1.5382 at 0.5, 3.3682 at 0.99).
double probability_scale(double probability) {
    const auto cdf = [](double r) {
        return std::erf(r / std::numbers::sqrt2) - std::sqrt(2.0 / std::numbers::pi) * r * std::exp(-r * r / 2.0);
    };
    double low = 0.0, high = 10.0;
    for (int i = 0; i != 100; ++i) {
        const double middle = (low + high) / 2.0;
        (cdf(middle) < probability ? low : high) = middle;
    }
    return (low + high) / 2.0;
}

// A symmetric matrix's eigenvalues and eigenvectors (the columns of `vectors`), by Jacobi rotations.
void eigen_symmetric(Matrix3 a, std::array<double, 3>& values, Matrix3& vectors) {
    vectors = {1, 0, 0, 0, 1, 0, 0, 0, 1};
    for (int sweep = 0; sweep != 50; ++sweep) {
        const double off = a[1] * a[1] + a[2] * a[2] + a[5] * a[5];
        if (off < 1e-30) {
            break;
        }
        for (const auto& [p, q] : {std::pair{0, 1}, std::pair{0, 2}, std::pair{1, 2}}) {
            const double apq = a[3 * p + q];
            if (std::abs(apq) < 1e-300) {
                continue;
            }
            const double theta = (a[3 * q + q] - a[3 * p + p]) / (2.0 * apq);
            const double t = (theta >= 0.0 ? 1.0 : -1.0) / (std::abs(theta) + std::sqrt(theta * theta + 1.0));
            const double c = 1.0 / std::sqrt(t * t + 1.0), sn = t * c;
            Matrix3 rotation{1, 0, 0, 0, 1, 0, 0, 0, 1};
            rotation[3 * p + p] = c;
            rotation[3 * q + q] = c;
            rotation[3 * p + q] = sn;
            rotation[3 * q + p] = -sn;
            a = product(transposed(rotation), product(a, rotation));
            vectors = product(vectors, rotation);
        }
    }
    values = {a[0], a[4], a[8]};
}

// The unit quaternion (w, x, y, z) of a proper rotation matrix.
std::array<double, 4> quaternion_of(const Matrix3& m) {
    const double trace = m[0] + m[4] + m[8];
    std::array<double, 4> q{};
    if (trace > 0.0) {
        const double s = 2.0 * std::sqrt(trace + 1.0);
        q = {s / 4.0, (m[7] - m[5]) / s, (m[2] - m[6]) / s, (m[3] - m[1]) / s};
    } else if (m[0] > m[4] && m[0] > m[8]) {
        const double s = 2.0 * std::sqrt(1.0 + m[0] - m[4] - m[8]);
        q = {(m[7] - m[5]) / s, s / 4.0, (m[1] + m[3]) / s, (m[2] + m[6]) / s};
    } else if (m[4] > m[8]) {
        const double s = 2.0 * std::sqrt(1.0 + m[4] - m[0] - m[8]);
        q = {(m[2] - m[6]) / s, (m[1] + m[3]) / s, s / 4.0, (m[5] + m[7]) / s};
    } else {
        const double s = 2.0 * std::sqrt(1.0 + m[8] - m[0] - m[4]);
        q = {(m[3] - m[1]) / s, (m[2] + m[6]) / s, (m[5] + m[7]) / s, s / 4.0};
    }
    const double length = std::sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]);
    for (double& component : q) {
        component /= length;
    }
    return q;
}

// The symmetry operation id an expanded row's `site_symmetry` code `n_klm` names; 0 when it names none.
std::size_t operation_id(const std::string& code) {
    std::size_t id = 0;
    const char* end = code.data() + code.size();
    const auto [stop, error] = std::from_chars(code.data(), end, id);
    return error == std::errc() && stop != code.data() ? id : 0;
}

SceneInstance segment_instance(const Vec3& start, const Vec3& end, double radius, const Rgb& color) {
    SceneInstance instance;
    const Vec3 along = sub(end, start);
    instance.position = mul(add(start, end), 0.5);
    instance.scale = {radius, norm(along), radius};
    instance.rotation = rotation_from_y(unit(along));
    instance.color = color;
    return instance;
}

const SceneStyle& style_row(std::string_view key) {
    for (const SceneStyle& style : structure_style_table()) {
        if (style.key == key) {
            return style;
        }
    }
    throw std::logic_error("structure style table has no key " + std::string(key));
}

double style_value(std::string_view key) { return style_row(key).value; }

// A colour of the style table in the light theme: the one a theme-free renderer draws.
Rgb style_color(std::string_view key) {
    const auto color = parse_color(style_row(key).light);
    if (!color) {
        throw std::logic_error("structure style table key " + std::string(key) + " has no light colour");
    }
    return *color;
}

std::string format_number(double value) {
    char buffer[64];
    const auto result = std::to_chars(buffer, buffer + sizeof(buffer), value);
    return std::string(buffer, result.ptr);
}

}  // namespace

const std::vector<ElementStyle>& element_style_table() {
    static const std::vector<ElementStyle> table = parse_element_styles(detail::kElementStylesTsv);
    return table;
}

std::string element_of(std::string_view type_symbol) {
    for (std::size_t i = 0; i != type_symbol.size(); ++i) {
        const char c = type_symbol[i];
        if (c >= 'A' && c <= 'Z') {
            std::string element(1, c);
            if (i + 1 < type_symbol.size() && type_symbol[i + 1] >= 'a' && type_symbol[i + 1] <= 'z') {
                element.push_back(type_symbol[i + 1]);
            }
            return element;
        }
    }
    return {};
}

ElementColor element_color(std::string_view element, ColorScheme scheme) {
    const ElementStyle* style = find_element(element);
    if (style == nullptr) {
        return {kUnknownColor, false};
    }
    if (scheme == ColorScheme::Vesta && style->vesta) {
        return {*style->vesta, true};
    }
    return {style->jmol, true};
}

ElementRadius element_radius(std::string_view element, AtomView view) {
    const ElementStyle* style = find_element(element);
    if (style == nullptr) {
        return {kUnknownRadius, true};
    }
    switch (view) {
        case AtomView::Covalent:
            return {style->covalent, false};
        case AtomView::VanDerWaals:
            return {style->van_der_waals, false};
        case AtomView::Ionic:
            return style->ionic ? ElementRadius{*style->ionic, false} : ElementRadius{style->covalent, true};
        case AtomView::Adp:
            return {style->covalent, false};  // a site with no displacement, and a shared site's slices
    }
    return {style->covalent, false};
}

SceneSource capture_scene(const Structure& structure) {
    SceneSource source;
    source.structure_id = structure.name.value();
    // An anisotropic site's U*, through crysta's conversion (crysta ADR-0081), to turn Cartesian below.
    std::unordered_map<std::string, std::array<double, 6>> u_star;
    for (const auto& site : structure.atom_sites) {
        source.site_types.emplace_back(site->id.value(), site->type_symbol.value());
        // adp_iso holds the value in the site's type, or an anisotropic site's equivalent value.
        double u_iso = site->adp_iso.value;
        try {
            if (crysta::equivalent_iso_form(crysta::adp_form_of(site->adp_type.value())) ==
                crysta::AdpForm::Biso) {
                u_iso /= 8.0 * std::numbers::pi * std::numbers::pi;
            }
        } catch (const std::exception&) {
            u_iso /= 8.0 * std::numbers::pi * std::numbers::pi;  // an unknown type: read as B
        }
        if (const auto tensor = site_u_star(structure, *site)) {
            u_star.emplace(site->id.value(), *tensor);
        }
        source.site_adps.push_back({site->id.value(), u_iso, std::nullopt});
    }
    if (!structure.geometry_current()) {
        return source;  // I11: no column of a geometry that no longer describes the structure
    }
    const StructureGeometry& geometry = structure.geometry;
    const ExpandedAtomSites& rows = geometry.expanded_atom_sites;
    source.current = true;
    source.atom_site_id = rows.atom_site_id.buffer();
    source.site_symmetry = rows.site_symmetry.buffer();
    source.fract_x = rows.fract_x.buffer();
    source.fract_y = rows.fract_y.buffer();
    source.fract_z = rows.fract_z.buffer();
    source.cartn_x = rows.cartn_x.buffer();
    source.cartn_y = rows.cartn_y.buffer();
    source.cartn_z = rows.cartn_z.buffer();
    source.occupancy = rows.occupancy.buffer();
    source.cluster_id = rows.cluster_id.buffer();
    source.bond_site_1 = geometry.geom_bond.expanded_atom_site_id_1.buffer();
    source.bond_site_2 = geometry.geom_bond.expanded_atom_site_id_2.buffer();
    source.bond_distance = geometry.geom_bond.distance.buffer();
    source.cartn_matrix = geometry.atom_sites_cartn_transform.matrix;
    // The Cartesian U = M U* M^T, M taking fractional coordinates to Cartesian ones.
    for (SceneSource::SiteAdp& adp : source.site_adps) {
        const auto found = u_star.find(adp.site_id);
        if (found == u_star.end()) {
            continue;
        }
        const std::array<double, 6>& s = found->second;
        const double star[3][3] = {{s[0], s[3], s[4]}, {s[3], s[1], s[5]}, {s[4], s[5], s[2]}};
        const auto& m = source.cartn_matrix;
        std::array<double, 9> u{};
        for (int i = 0; i < 3; ++i) {
            for (int j = 0; j < 3; ++j) {
                double value = 0.0;
                for (int a = 0; a < 3; ++a) {
                    for (int b = 0; b < 3; ++b) {
                        value += m[3 * i + a] * star[a][b] * m[3 * j + b];
                    }
                }
                u[3 * i + j] = value;
            }
        }
        adp.u_cartn = u;
    }
    try {
        source.operation_rotations = space_group_rotations(structure.space_group);
    } catch (const std::exception&) {
        source.operation_rotations.clear();  // no operation: an anisotropic site is drawn at its own orientation
    }
    return source;
}

StructureScene present_structure(const SceneSource& source, const SceneOptions& options) {
    StructureScene scene;
    scene.current = source.current;
    if (!source.current) {
        scene.frame = home_frame(scene, false);
        return scene;
    }
    const auto& m = source.cartn_matrix;
    for (int k = 0; k != 3; ++k) {
        scene.cell_basis[k] = {m[k], m[3 + k], m[6 + k]};  // I2: column k of the row-major matrix
    }

    // I3: one atom per position, in the order of each position's first row.
    const std::size_t n = std::min({column_size(source.atom_site_id), column_size(source.cartn_x),
                                    column_size(source.cartn_y), column_size(source.cartn_z),
                                    column_size(source.cluster_id)});
    std::unordered_map<std::string, std::string> type_of_site;
    for (const auto& [site_id, type_symbol] : source.site_types) {
        type_of_site.emplace(site_id, type_symbol);
    }
    std::unordered_map<std::int32_t, std::size_t> atom_of_cluster;
    std::vector<std::size_t> atom_of_row(n);
    for (std::size_t row = 0; row != n; ++row) {
        const std::int32_t cluster = (*source.cluster_id)[row];
        auto [found, inserted] = atom_of_cluster.emplace(cluster, scene.atoms.size());
        if (inserted) {
            SceneAtom atom;
            atom.centre = row_centre(source, row);
            atom.row = row;
            atom.cluster_id = cluster;
            scene.atoms.push_back(std::move(atom));
        }
        atom_of_row[row] = found->second;
        ScenePart part;
        part.row = row;
        part.site_id = (*source.atom_site_id)[row];
        const auto type = type_of_site.find(part.site_id);
        part.element = type == type_of_site.end() ? std::string() : element_of(type->second);  // I4
        part.occupancy = column_value(source.occupancy, row, 0.0);
        part.color = element_color(part.element, options.colors).color;
        scene.atoms[found->second].parts.push_back(std::move(part));
    }

    std::unordered_map<std::string, const SceneSource::SiteAdp*> adp_of_site;
    for (const SceneSource::SiteAdp& adp : source.site_adps) {
        adp_of_site.emplace(adp.site_id, &adp);
    }
    const double probability = options.atom_view == AtomView::Adp ? probability_scale(options.adp_probability) : 0.0;
    std::vector<std::string> substituted;
    for (SceneAtom& atom : scene.atoms) {
        // I5: relative shares; a zero sum gives equal shares; one part is whole.
        const std::size_t parts = atom.parts.size();
        double total = 0.0;
        for (const ScenePart& part : atom.parts) {
            total += part.occupancy;
        }
        for (std::size_t i = 0; i != parts; ++i) {
            ScenePart& part = atom.parts[i];
            part.fraction = parts == 1    ? 1.0
                            : total != 0.0 ? part.occupancy / total
                                           : 1.0 / static_cast<double>(parts);
            if (part.occupancy > atom.parts[atom.major].occupancy) {
                atom.major = i;
            }
            if (i != 0) {
                atom.label += '/';
            }
            atom.label += part.site_id;
            if (column_value(source.site_symmetry, part.row, std::string()) == "1_555") {
                atom.asymmetric = true;
            }
        }
        const ElementRadius radius = element_radius(atom.parts[atom.major].element, options.atom_view);
        atom.table_radius = radius.radius;
        atom.radius_substituted = radius.substituted;
        atom.radius = options.atom_scale * std::sqrt(radius.radius);
        if (options.atom_view == AtomView::Adp && parts == 1) {
            const ScenePart& part = atom.parts[atom.major];
            const auto adp = adp_of_site.find(part.site_id);
            if (adp != adp_of_site.end() && adp->second->u_cartn.has_value()) {
                // The site's tensor turned onto this copy by its operation's Cartesian rotation A R A^-1.
                Matrix3 u = *adp->second->u_cartn;
                const std::size_t id = operation_id(column_value(source.site_symmetry, part.row, std::string()));
                if (id >= 1 && id <= source.operation_rotations.size()) {
                    const std::array<int, 9>& r = source.operation_rotations[id - 1];
                    const Matrix3 fractional{double(r[0]), double(r[1]), double(r[2]), double(r[3]), double(r[4]),
                                             double(r[5]), double(r[6]), double(r[7]), double(r[8])};
                    const Matrix3 turn = product(source.cartn_matrix, product(fractional, inverted(source.cartn_matrix)));
                    u = product(turn, product(u, transposed(turn)));
                }
                std::array<double, 3> values{};
                Matrix3 vectors{};
                eigen_symmetric(u, values, vectors);
                const double det = vectors[0] * (vectors[4] * vectors[8] - vectors[5] * vectors[7]) -
                                   vectors[1] * (vectors[3] * vectors[8] - vectors[5] * vectors[6]) +
                                   vectors[2] * (vectors[3] * vectors[7] - vectors[4] * vectors[6]);
                if (det < 0.0) {  // a proper rotation: flip the third axis
                    vectors[2] = -vectors[2];
                    vectors[5] = -vectors[5];
                    vectors[8] = -vectors[8];
                }
                atom.ellipsoid = true;
                atom.semi_axes = {probability * std::sqrt(std::max(values[0], 0.0)),
                                  probability * std::sqrt(std::max(values[1], 0.0)),
                                  probability * std::sqrt(std::max(values[2], 0.0))};
                atom.orientation = quaternion_of(vectors);
                atom.radius = std::max({atom.semi_axes.x, atom.semi_axes.y, atom.semi_axes.z});
            } else if (adp != adp_of_site.end() && adp->second->u_iso > 0.0) {
                atom.radius = probability * std::sqrt(adp->second->u_iso);
            }
        }
        if (radius.substituted) {
            substituted.push_back(atom.parts[atom.major].element);  // the empty element (no symbol) too, once
        }
        // I8: the atom subset.
        atom.drawn = options.atoms == AtomSubset::All ||
                     (options.atoms == AtomSubset::AsymmetricUnit && atom.asymmetric);
        if (!atom.asymmetric) {
            scene.has_copies = true;
        }
    }
    std::sort(substituted.begin(), substituted.end());
    substituted.erase(std::unique(substituted.begin(), substituted.end()), substituted.end());
    scene.substituted_elements = std::move(substituted);

    // I7: one bond per `_geom_bond` row; an id naming no row is skipped.
    if (options.bonds) {
        const std::size_t bonds = std::min({column_size(source.bond_site_1), column_size(source.bond_site_2),
                                            column_size(source.bond_distance)});
        for (std::size_t b = 0; b != bonds; ++b) {
            const std::int64_t id_1 = (*source.bond_site_1)[b], id_2 = (*source.bond_site_2)[b];
            if (id_1 < 1 || id_2 < 1 || static_cast<std::size_t>(id_1) > n || static_cast<std::size_t>(id_2) > n) {
                continue;
            }
            const auto row_1 = static_cast<std::size_t>(id_1 - 1), row_2 = static_cast<std::size_t>(id_2 - 1);
            SceneBond bond;
            bond.row = b;
            bond.atom_1 = atom_of_row[row_1];
            bond.atom_2 = atom_of_row[row_2];
            bond.start = row_centre(source, row_1);
            bond.end = row_centre(source, row_2);
            bond.distance = (*source.bond_distance)[b];
            const SceneAtom& atom_1 = scene.atoms[bond.atom_1];
            const SceneAtom& atom_2 = scene.atoms[bond.atom_2];
            bond.color_1 = atom_1.parts[atom_1.major].color;
            bond.color_2 = atom_2.parts[atom_2.major].color;
            scene.bonds.push_back(bond);
        }
    }

    // I2: the 12 edges, along a, then b, then c, each group ordered by the other two indices.
    if (options.cell) {
        const auto corner = [&](int i, int j, int k) {
            Vec3 c;
            if (i != 0) c = add(c, scene.cell_basis[0]);
            if (j != 0) c = add(c, scene.cell_basis[1]);
            if (k != 0) c = add(c, scene.cell_basis[2]);
            return c;
        };
        for (int p = 0; p != 2; ++p) {
            for (int q = 0; q != 2; ++q) {
                scene.cell_edges.push_back({corner(0, p, q), corner(1, p, q)});
            }
        }
        for (int p = 0; p != 2; ++p) {
            for (int q = 0; q != 2; ++q) {
                scene.cell_edges.push_back({corner(p, 0, q), corner(p, 1, q)});
            }
        }
        for (int p = 0; p != 2; ++p) {
            for (int q = 0; q != 2; ++q) {
                scene.cell_edges.push_back({corner(p, q, 0), corner(p, q, 1)});
            }
        }
    }
    if (options.axes) {
        for (int k = 0; k != 3; ++k) {
            static const char* const kKeys[3] = {"axis.a", "axis.b", "axis.c"};
            scene.axes.push_back({static_cast<char>('a' + k), scene.cell_basis[k], style_color(kKeys[k])});
        }
    }
    if (options.labels) {
        for (std::size_t i = 0; i != scene.atoms.size(); ++i) {
            if (scene.atoms[i].drawn) {
                scene.labels.push_back({i, scene.atoms[i].centre, scene.atoms[i].label});
            }
        }
    }
    if (options.atoms != AtomSubset::None) {
        for (const auto& [site_id, type_symbol] : source.site_types) {
            const std::string element = element_of(type_symbol);
            if (element.empty()) {
                continue;
            }
            const bool seen = std::any_of(scene.legend.begin(), scene.legend.end(),
                                          [&](const SceneLegendEntry& entry) { return entry.element == element; });
            if (!seen) {
                scene.legend.push_back({element, element_color(element, options.colors).color});
            }
        }
    }
    scene.frame = home_frame(scene, true);
    return scene;
}

SceneView default_view(const StructureScene& scene) {
    SceneView view;
    view.direction = scene.frame.view_direction;
    view.up = scene.frame.view_up;
    return view;
}

SceneView view_along(const StructureScene& scene, int axis) {
    SceneView view = default_view(scene);
    if (axis < 0 || axis > 2 || !(norm(scene.cell_basis[axis]) > 0.0)) {
        return view;
    }
    const int first = (axis + 1) % 3, second = (axis + 2) % 3;
    const int lower = std::min(first, second), upper = std::max(first, second);
    // The longer of the other two lies across the screen; equals in the order a, b, c.
    const int horizontal = norm(scene.cell_basis[upper]) > norm(scene.cell_basis[lower]) ? upper : lower;
    const int third = horizontal == lower ? upper : lower;
    Vec3 direction = unit(scene.cell_basis[axis]);
    const Vec3 across = scene.cell_basis[horizontal];
    const Vec3 right = unit(sub(across, mul(direction, dot(across, direction))));
    Vec3 up = cross(direction, right);
    if (dot(scene.cell_basis[third], up) < 0.0) {
        direction = mul(direction, -1.0);  // seen from the opposite side, so the third points up
        up = cross(direction, right);
    }
    view.direction = direction;
    view.up = up;
    return view;
}

double fitted_scale(const StructureScene& scene, const Viewport& viewport, Projection projection) {
    if (!(viewport.width > 0.0) || !(viewport.height > 0.0)) {
        return 0.0;
    }
    const double h = fitted_half_height(scene.frame, viewport);
    if (projection == Projection::Perspective) {
        return viewport.height / (2.0 * kPerspectiveDistance * h);
    }
    return viewport.height / (2.0 * h * (1.0 + viewport.top_band / viewport.height));
}

Projected project(const StructureScene& scene, const SceneView& view, const Viewport& viewport, const Vec3& point) {
    Projected out;
    const Vec3 d = sub(point, scene.frame.target);
    const Vec3 right = cross(view.up, view.direction);
    out.depth = dot(d, view.direction);
    const double fitted = fitted_scale(scene, viewport, view.projection);
    if (view.projection == Projection::Perspective) {
        const double distance = perspective_distance(fitted_half_height(scene.frame, viewport));
        if (out.depth >= distance) {
            out.x = out.y = std::numeric_limits<double>::quiet_NaN();
            return out;
        }
        const double scale = fitted * view.magnification * distance / (distance - out.depth);
        out.x = viewport.width / 2.0 + scale * dot(d, right) + view.pan_x;
        out.y = viewport.height / 2.0 - scale * dot(d, view.up) + view.pan_y;
        return out;
    }
    const double scale = fitted * view.magnification;
    const double shift = viewport.height > 0.0 ? viewport.top_band / (2.0 * (1.0 + viewport.top_band / viewport.height))
                                               : 0.0;
    out.x = viewport.width / 2.0 + scale * dot(d, right) + view.pan_x;
    out.y = viewport.height / 2.0 + shift - scale * dot(d, view.up) + view.pan_y;
    return out;
}

SceneView rotated(const SceneView& view, double dx, double dy) {
    // I14: the scene turns dx degrees about the screen's vertical axis, then dy degrees about its horizontal
    // axis; the camera turns the opposite way about the same axes.
    SceneView out = view;
    out.direction = unit(turned(view.direction, view.up, -dx * kDegree));
    const Vec3 right = unit(cross(out.up, out.direction));
    out.direction = unit(turned(out.direction, right, -dy * kDegree));
    out.up = unit(turned(out.up, right, -dy * kDegree));
    return out;
}

SceneView zoomed(const StructureScene& scene, const SceneView& view, const Viewport& viewport, double x, double y,
                 int angle_delta) {
    SceneView out = view;
    const double wanted = view.magnification * std::pow(kZoomPerNotch, angle_delta / 120.0);
    out.magnification = std::clamp(wanted, kMinMagnification, kMaxMagnification);
    if (view.projection == Projection::Orthographic && view.magnification > 0.0) {
        // The scene point under the pointer stays under it.
        const double ratio = out.magnification / view.magnification;
        const Projected target = project(scene, SceneView{view.direction, view.up, 1.0, 0.0, 0.0, view.projection},
                                         viewport, scene.frame.target);
        out.pan_x = x - target.x - ratio * (x - target.x - view.pan_x);
        out.pan_y = y - target.y - ratio * (y - target.y - view.pan_y);
    }
    return out;
}

SceneView panned(const SceneView& view, double dx, double dy) {
    SceneView out = view;
    out.pan_x += dx;
    out.pan_y += dy;
    return out;
}

SceneDrawing scene_drawing(const StructureScene& scene, const Viewport& viewport) {
    SceneDrawing drawing;
    const double h = fitted_half_height(scene.frame, viewport);
    drawing.fitted_half_height = h;
    for (std::size_t i = 0; i != scene.atoms.size(); ++i) {
        const SceneAtom& atom = scene.atoms[i];
        if (!atom.drawn) {
            continue;
        }
        if (atom.parts.size() > 1) {
            drawing.shared.push_back(i);
            continue;
        }
        SceneInstance sphere;
        sphere.position = atom.centre;
        sphere.scale = atom.ellipsoid ? atom.semi_axes : Vec3{atom.radius, atom.radius, atom.radius};
        sphere.rotation = atom.orientation;
        sphere.color = atom.parts[atom.major].color;
        sphere.atom = i;
        drawing.spheres.push_back(sphere);
    }
    const double bond_radius = style_value("bond.radius");
    for (const SceneBond& bond : scene.bonds) {
        // Two halves, each distance / 2 long from an end towards the middle, turned from +y to the bond.
        const Vec3 along = sub(bond.end, bond.start);
        const Vec3 direction = bond.distance > 0.0 ? divided(along, bond.distance) : unit(along);
        const auto rotation = rotation_from_y(direction);
        const Vec3 scale{bond_radius, bond.distance / 2.0, bond_radius};
        drawing.cylinders.push_back({add(bond.start, mul(along, 0.25)), scale, rotation, bond.color_1, 0});
        drawing.cylinders.push_back({add(bond.start, mul(along, 0.75)), scale, rotation, bond.color_2, 0});
    }
    const double edge_radius = style_value("cell.edge.radius") * h;
    const Rgb edge_color = style_color("cell.edge");  // a themed renderer draws its theme's colour
    for (const SceneEdge& edge : scene.cell_edges) {
        drawing.cylinders.push_back(segment_instance(edge.start, edge.end, edge_radius, edge_color));
    }
    const double head_length = style_value("axis.head.length") * h;
    const double overhang = std::max(style_value("axis.overhang") * h,
                                     scene.frame.pad + head_length + style_value("axis.clearance") * h);
    for (const SceneAxis& axis : scene.axes) {
        SceneArrow arrow;
        arrow.letter = axis.letter;
        arrow.color = axis.color;
        arrow.direction = unit(axis.vector);
        const double length = norm(axis.vector);
        arrow.shaft_radius = style_value("axis.shaft.radius") * h;
        arrow.head_radius = style_value("axis.head.radius") * h;
        arrow.head_length = head_length;
        arrow.shaft_length = length + overhang - head_length;
        arrow.letter_anchor = mul(arrow.direction, length + overhang + style_value("axis.letter.offset") * h);
        drawing.triad.push_back(arrow);
    }
    return drawing;
}

std::string hover_text(const SceneSource& source, const StructureScene& scene, std::size_t atom) {
    if (atom >= scene.atoms.size()) {
        return {};
    }
    const SceneAtom& a = scene.atoms[atom];
    std::string text = a.label;
    for (const ScenePart& part : a.parts) {
        text += "\n" + (part.element.empty() ? std::string("?") : part.element) + "  occupancy " +
                format_number(part.occupancy);
    }
    text += "\nfract " + format_number(column_value(source.fract_x, a.row, 0.0)) + ", " +
            format_number(column_value(source.fract_y, a.row, 0.0)) + ", " +
            format_number(column_value(source.fract_z, a.row, 0.0));
    const std::string symmetry = column_value(source.site_symmetry, a.row, std::string());
    if (!symmetry.empty()) {
        text += "\nsymmetry " + symmetry;
    }
    return text;
}

const std::vector<SceneStyle>& structure_style_table() {
    // edi ADR-0017 §16. Colours are `#RRGGBB` per theme; a dimension's `value` is in Angstrom, or a share of
    // the fitted half height H for the keys the ADR marks so. Every value is diffraction-lib's
    // (`display/theme.py` and `templates/structure.html.j2` at cb2cda7b; the owner, 2026-10-02): the scene's
    // background and foreground per theme, the axis colours, the arrow's shares, and the lights — an ambient
    // term, and a key and a fill light along camera-local directions (right, up, towards the camera).
    static const std::vector<SceneStyle> table = {
        {"background", "#FFFFFF", "#212121", 0.0},
        {"cell.edge", "#222222", "#E6E8EE", 0.0},
        {"cell.edge.radius", "", "", 0.0025},
        {"bond.radius", "", "", 0.06},
        {"axis.a", "#DC2828", "#DC2828", 0.0},
        {"axis.b", "#28B428", "#28B428", 0.0},
        {"axis.c", "#2850DC", "#2850DC", 0.0},
        {"axis.shaft.radius", "", "", 0.009},
        {"axis.head.radius", "", "", 0.028},
        {"axis.head.length", "", "", 0.085},
        {"axis.overhang", "", "", 0.09},
        {"axis.clearance", "", "", 0.04},
        {"axis.letter.offset", "", "", 0.05},
        {"label", "#222222", "#E6E8EE", 0.0},
        {"label.halo", "#FFFFFF", "#212121", 0.0},
        {"light.ambient", "", "", 0.68},
        {"light.key", "", "", 1.25},
        {"light.key.right", "", "", 0.3},
        {"light.key.up", "", "", 0.45},
        {"light.key.toward", "", "", 0.85},
        {"light.fill", "", "", 0.34},
        {"light.fill.right", "", "", -0.4},
        {"light.fill.up", "", "", -0.2},
        {"light.fill.toward", "", "", -0.45},
        {"material.specular", "", "", 0.2},
        {"material.shininess", "", "", 90.0},
    };
    return table;
}

}  // namespace edi
