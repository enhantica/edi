// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_STRUCTURE_SCENE_HPP
#define EDI_STRUCTURE_SCENE_HPP

#include <array>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "edi/model.hpp"

// ADR-0022: the structure scene — the one description every structure renderer draws (the app's Qt
// Quick 3D view now). crysta computes every position, bond and distance; this file groups the rows
// into atoms, looks up colours and radii, and describes the view, and computes no geometry.
// `present_structure` is a pure function of its two arguments. Qt-free, and no crysta type.

namespace edi {

struct Rgb {
    std::uint8_t r = 0, g = 0, b = 0;
};
struct Vec3 {
    double x = 0.0, y = 0.0, z = 0.0;  // Angstrom, crysta's Cartesian frame
};

enum class ColorScheme : std::uint8_t { Jmol, Vesta };
// diffraction-lib's atom_view. Adp draws each site's displacement at `adp_probability`: an ellipsoid for an
// anisotropic site, a sphere for an isotropic one; a ball of the covalent radius where a site has neither.
enum class AtomView : std::uint8_t { Covalent, VanDerWaals, Ionic, Adp };
enum class Projection : std::uint8_t { Orthographic, Perspective };
enum class AtomSubset : std::uint8_t { All, AsymmetricUnit, None };

// The element tables: data/elements/element-styles.tsv, embedded in the core at build time. 118 rows,
// H to Og. Parsed once; a malformed row throws std::runtime_error naming it.
struct ElementStyle {
    std::string symbol;
    Rgb jmol;
    std::optional<Rgb> vesta;
    double covalent = 0.0, van_der_waals = 0.0;
    std::optional<double> ionic;
};
const std::vector<ElementStyle>& element_style_table();
// The type symbol's first capital letter and the lower-case letter directly after it, if any: `Co2+` is
// `Co`, `162Dy` is `Dy`, `2H` is `H`. A symbol with no capital letter gives the empty string.
std::string element_of(std::string_view type_symbol);
struct ElementColor {
    Rgb color;
    bool known = false;  // the element is in the table
};
struct ElementRadius {
    double radius = 0.0;
    bool substituted = false;  // the model had no value: the covalent radius, or 1.0 for an unknown element
};
// A missing VESTA colour is the Jmol one; an unknown or empty element is (255, 192, 203).
ElementColor element_color(std::string_view element, ColorScheme scheme);
// A missing ionic radius is the covalent one; an unknown or empty element is 1.0 Angstrom.
ElementRadius element_radius(std::string_view element, AtomView view);

// One structure's immutable buffers, captured on the model's owner thread. Plain data, so a renderer or
// a test may build one by hand.
struct SceneSource {
    template <class T>
    using Column = std::shared_ptr<const std::vector<T>>;
    std::string structure_id;
    bool current = false;  // the geometry described the structure when it was captured
    Column<std::string> atom_site_id, site_symmetry;  // `_expanded_atom_site`
    Column<double> fract_x, fract_y, fract_z, cartn_x, cartn_y, cartn_z, occupancy;
    Column<std::int32_t> cluster_id;
    Column<std::int32_t> bond_site_1, bond_site_2;  // `_geom_bond`: 1-based row ids
    Column<double> bond_distance;
    std::array<double, 9> cartn_matrix{};  // `_atom_sites_cartn_transform`, row-major
    std::vector<std::pair<std::string, std::string>> site_types;  // `_atom_site.id`, `.type_symbol`
    // Each site's displacement, by `_atom_site.id`: the isotropic U (Angstrom squared) and, for an anisotropic
    // site, its Cartesian U (row-major, the frame of `cartn_matrix`) at the site's own position.
    struct SiteAdp {
        std::string site_id;
        double u_iso = 0.0;
        std::optional<std::array<double, 9>> u_cartn;
    };
    std::vector<SiteAdp> site_adps;
    // The space group's rotations in fractional coordinates (row-major), by symmetry operation id - 1: an
    // expanded row's `site_symmetry` code `n_klm` names its operation n, which turns the site's tensor onto it.
    std::vector<std::array<int, 9>> operation_rotations;
};
// Owner thread. Reads the stored geometry only while `structure.geometry_current()` is true, and never
// computes it; otherwise the source has `current` false and no column.
SceneSource capture_scene(const Structure& structure);

struct SceneOptions {
    ColorScheme colors = ColorScheme::Jmol;
    AtomView atom_view = AtomView::Covalent;
    double atom_scale = 0.3;
    double adp_probability = 0.99;  // diffraction-lib's `_structure_style.adp_probability`, in (0, 1)
    AtomSubset atoms = AtomSubset::All;
    bool bonds = true, cell = true, axes = true, labels = false;
};

struct ScenePart {  // one site at a position
    std::size_t row = 0;  // its `_expanded_atom_site` row, 0-based
    std::string site_id, element;
    double occupancy = 0.0, fraction = 0.0;
    Rgb color;
};
struct SceneAtom {  // one position
    Vec3 centre;
    std::size_t row = 0;
    std::int32_t cluster_id = 0;
    double table_radius = 0.0, radius = 0.0;
    bool radius_substituted = false;
    // In the ADP view, an anisotropic atom's ellipsoid: its semi-axes (Angstrom) along the local x, y and z of
    // `orientation`, a unit quaternion (w, x, y, z). `radius` is then its largest semi-axis.
    bool ellipsoid = false;
    Vec3 semi_axes;
    std::array<double, 4> orientation{1.0, 0.0, 0.0, 0.0};
    std::string label;
    bool asymmetric = false;
    bool drawn = true;
    std::vector<ScenePart> parts;
    std::size_t major = 0;
};
struct SceneBond {
    std::size_t row = 0, atom_1 = 0, atom_2 = 0;
    Vec3 start, end;
    double distance = 0.0;
    Rgb color_1, color_2;
};
struct SceneEdge {
    Vec3 start, end;
};
struct SceneAxis {
    char letter = 'a';
    Vec3 vector;
    Rgb color;
};
struct SceneLabel {
    std::size_t atom = 0;
    Vec3 anchor;
    std::string text;
};
struct SceneLegendEntry {
    std::string element;
    Rgb color;
};
struct SceneFrame {  // diffraction-lib's home view, before any viewport
    Vec3 target;  // the point the home view centres, and the pivot of a rotation
    Vec3 view_direction, view_up;  // unit vectors: towards the viewer; the screen's up
    double half_width = 0.0, half_height = 0.0;  // Angstrom: the fitted extent across and up the screen
    double pad = 0.0;  // Angstrom: the greatest atom radius
};
struct StructureScene {
    bool current = false;
    bool has_copies = false;  // an atom outside the asymmetric unit exists
    std::array<Vec3, 3> cell_basis;
    std::vector<SceneAtom> atoms;
    std::vector<SceneBond> bonds;
    std::vector<SceneEdge> cell_edges;
    std::vector<SceneAxis> axes;
    std::vector<SceneLabel> labels;
    std::vector<SceneLegendEntry> legend;
    std::vector<std::string> substituted_elements;  // sorted, once each; "" for parts with no element
    SceneFrame frame;
};
StructureScene present_structure(const SceneSource& source, const SceneOptions& options);

// The view: an orthographic or a perspective camera, as pure functions.
struct SceneView {
    Vec3 direction, up;
    double magnification = 1.0;
    double pan_x = 0.0, pan_y = 0.0;
    Projection projection = Projection::Orthographic;
};
struct Viewport {
    double width = 0.0, height = 0.0, top_band = 0.0;  // logical pixels; the band kept clear at the top
};
struct Projected {
    double x = 0.0, y = 0.0, depth = 0.0;  // pixels, y down; depth towards the viewer, Angstrom
};
SceneView default_view(const StructureScene& scene);
SceneView view_along(const StructureScene& scene, int axis);  // 0, 1, 2: a, b, c
// Pixels per Angstrom of the home view. Zero for a viewport with no area.
double fitted_scale(const StructureScene& scene, const Viewport& viewport, Projection projection);
// A point behind the perspective camera has NaN x and y.
Projected project(const StructureScene& scene, const SceneView& view, const Viewport& viewport, const Vec3& point);
SceneView rotated(const SceneView& view, double dx, double dy);  // a drag, in pixels
SceneView zoomed(const StructureScene& scene, const SceneView& view, const Viewport& viewport, double x, double y,
                 int angle_delta);
SceneView panned(const SceneView& view, double dx, double dy);

// What an instancing table holds, in bulk: one entry per drawn mesh, in the scene's own units.
struct SceneInstance {
    Vec3 position, scale;
    std::array<double, 4> rotation{1.0, 0.0, 0.0, 0.0};  // a unit quaternion: w, x, y, z
    Rgb color;
    std::size_t atom = 0;  // a sphere's atom; unused otherwise
};
struct SceneArrow {  // one arrow of the triad, sized for the viewport
    char letter = 'a';
    Rgb color;
    Vec3 origin, direction;
    double shaft_length = 0.0, shaft_radius = 0.0, head_length = 0.0, head_radius = 0.0;
    Vec3 letter_anchor;
};
struct SceneDrawing {  // everything a renderer places, in scene units
    double fitted_half_height = 0.0;  // the fitted half height H for the viewport it was prepared for
    std::vector<SceneInstance> spheres, cylinders;  // cylinders: half-bonds, then cell edges
    std::vector<std::size_t> shared;  // the drawn shared sites: shared[k] is the atom whose mesh ordinal is k
    std::vector<SceneArrow> triad;
};
// The unit sphere has radius 1; the unit cylinder has radius 1 and length 1 along +y, centred.
SceneDrawing scene_drawing(const StructureScene& scene, const Viewport& viewport);
// The atom's label; per part its element and occupancy; its fractional coordinates and symmetry code as
// crysta gave them. Empty for an atom the scene does not have.
std::string hover_text(const SceneSource& source, const StructureScene& scene, std::size_t atom);

// One row of the style table: what a renderer needs beyond the scene, light and dark. A colour row has
// `light` and `dark` (`#RRGGBB`); a dimension row has `value` (Angstrom, or a share of the fitted half
// height where its key says so).
struct SceneStyle {
    std::string key, light, dark;
    double value = 0.0;
};
const std::vector<SceneStyle>& structure_style_table();

}  // namespace edi

#endif  // EDI_STRUCTURE_SCENE_HPP
