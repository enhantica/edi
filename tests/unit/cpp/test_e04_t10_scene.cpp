#include <doctest/doctest.h>

#include <atomic>
#include <bit>
#include <crysta/model.hpp>
#include <crysta/structure_geometry.hpp>
#include <iomanip>
#include <set>
#include <thread>

#include "../../fixtures/e04_t10/generated.hpp"
#include "e04_t10_reference.hpp"
#include "e04_t9_support.hpp"

TEST_CASE("E04-T10 independent inputs cover published elements and G1") {
    const auto reference = e04_t10::elements();
    REQUIRE_MESSAGE(reference.size() == 118, " I6 reference has all 118 published elements");
    CHECK_MESSAGE((reference.front().symbol == "H" && reference.back().symbol == "Og"),
                  " I6 reference spans H through Og");
    auto g = e04_t10_fixture::generated();
    REQUIRE_MESSAGE(g.structures.size() == 1, " M1 generated input has one structure");
    REQUIRE_MESSAGE(g.experiments.size() == 1,
                    " amended M1 generated input has exactly one small experiment");
    CHECK_MESSAGE(g.experiment().calculation_only,
                  " amended M1 G1 experiment is calculation-only");
    CHECK_MESSAGE(g.experiment().linked_structure().structure_id == "G1",
                  " amended M1 grid links the declared G1 structure");
    REQUIRE_MESSAGE(g.experiment().data.has_value(),
                    " amended M1 experiment declares a calculation grid");
    CHECK_MESSAGE((g.experiment().data->axis() == std::vector<double>{10, 11, 12}),
                  " amended M1 calculation grid is the independently declared three points");
    CHECK_MESSAGE((g.experiment().data->intensity_meas.empty() &&
                   g.experiment().data->intensity_meas_su.empty()),
                  " amended M1 calculation grid carries no measured data");
    struct FixtureDirectory {
        std::filesystem::path path =
            std::filesystem::temp_directory_path() / std::to_string(e04_t9::clock_ns());
        ~FixtureDirectory() { std::filesystem::remove_all(path); }
    } directory;
    e04_t10_fixture::write_calculation_project(g, directory.path.string());
    auto loaded = edi::load_project(directory.path.string());
    REQUIRE_MESSAGE(loaded.experiments.size() == 1,
                    " amended M1 saved project opens with exactly one experiment");
    CHECK_MESSAGE((loaded.experiment().calculation_only &&
                   loaded.experiment().linked_structure().structure_id == "G1"),
                  " amended M1 saved grid remains calculation-only and linked to G1");
    REQUIRE_MESSAGE(loaded.experiment().data.has_value(),
                    " amended M1 saved experiment retains its declared grid");
    CHECK_MESSAGE((loaded.experiment().data->axis() == std::vector<double>{10, 11, 12} &&
                   loaded.experiment().data->intensity_meas.empty() &&
                   loaded.experiment().data->intensity_meas_su.empty()),
                  " amended M1 saved grid retains three points and no measured data");
    CHECK_MESSAGE(g.structure().atom_sites.size() == 30, " M1 generated input has thirty sites");
    CHECK_MESSAGE(
        g.structure().atom_sites[29]->fract_z.value == doctest::Approx(.127 + .0113 * 29),
        " M1 final input coordinate follows the declared deterministic formula");
    const auto independent = crysta::structure_from_edi_text(e04_t10_fixture::generated_text());
    REQUIRE_MESSAGE(independent.atom_sites.size() == 30,
                    " M1 generated text is valid independent engine input with all sites");
    for (std::size_t i = 0; i < 30; ++i) {
        CHECK_MESSAGE((independent.atom_sites[i].wyckoff_letter == "l" &&
                       g.structure().atom_sites[i]->wyckoff_letter == "l"),
                      " M1 both input forms declare the F m -3 m general position");
        for (int axis = 0; axis < 3; ++axis) {
            const double expected = axis == 0   ? .011 + .0157 * i
                                    : axis == 1 ? .073 + .0131 * i
                                                : .127 + .0113 * i;
            CHECK_MESSAGE(
                independent.atom_sites[i].fract[axis].value() == expected,
                " M1 independent reader retains every declared deterministic coordinate");
        }
    }
    g.structure().current_geometry();
    CHECK_MESSAGE(
        g.structure().geometry.expanded_atom_sites.size() == 5760,
        " M1 fixture reaches the independently measured engine count from packet P0 table 2");
    CHECK_MESSAGE(
        g.structure().geometry.geom_bond.size() == 4176,
        " M1 fixture reaches the independently measured engine bond count from packet P0 table 2");
}

#if __has_include("edi/structure_scene.hpp")
#include "edi/live_preview.hpp"
#include "edi/structure_scene.hpp"
namespace {
bool bits(double a, double b) {
    return std::bit_cast<std::uint64_t>(a) == std::bit_cast<std::uint64_t>(b);
}
void vec(edi::Vec3 a, e04_t10::Vector b) {
    CHECK_MESSAGE(a.x == doctest::Approx(b[0]).epsilon(1e-12),
                  " independent Cartesian or closed-form x equals the scene");
    CHECK_MESSAGE(a.y == doctest::Approx(b[1]).epsilon(1e-12),
                  " independent Cartesian or closed-form y equals the scene");
    CHECK_MESSAGE(a.z == doctest::Approx(b[2]).epsilon(1e-12),
                  " independent Cartesian or closed-form z equals the scene");
}
void color(edi::Rgb actual, const std::string& hex) {
    CHECK_MESSAGE(actual.r == std::stoi(hex.substr(1, 2), nullptr, 16),
                  " I5 published sRGB red byte is unchanged");
    CHECK_MESSAGE(actual.g == std::stoi(hex.substr(3, 2), nullptr, 16),
                  " I5 published sRGB green byte is unchanged");
    CHECK_MESSAGE(actual.b == std::stoi(hex.substr(5, 2), nullptr, 16),
                  " I5 published sRGB blue byte is unchanged");
}
template <class T>
auto col(std::vector<T> v) {
    return std::make_shared<const std::vector<T>>(std::move(v));
}
edi::SceneSource source() {
    edi::SceneSource s;
    s.current = true;
    s.structure_id = "independent-input";
    s.atom_site_id = col<std::string>({"La", "Ba", "H", "He"});
    s.site_symmetry = col<std::string>({"1_555", "2_555", "1_655", ""});
    s.cluster_id = col<std::int32_t>({42, 42, 7, 9});
    s.cartn_x = col<double>({3, 3, 8, 11});
    s.cartn_y = col<double>({4, 4, 9, 12});
    s.cartn_z = col<double>({5, 5, 10, 13});
    // Deliberately inconsistent with the Cartesian columns: edi may not recompute them.
    s.fract_x = col<double>({.11, .11, .33, .44});
    s.fract_y = col<double>({.12, .12, .34, .45});
    s.fract_z = col<double>({.13, .13, .35, .46});
    s.occupancy = col<double>({.6, .2, .4, 0});
    s.bond_site_1 = col<std::int32_t>({2});
    s.bond_site_2 = col<std::int32_t>({3});
    s.bond_distance = col<double>({8.123});
    s.cartn_matrix = {4, 1, 2, 0, 10, 3, 0, 0, 6};
    s.site_types = {{"La", "La3+"}, {"Ba", "Ba2+"}, {"H", "2H"}, {"He", "He"}};
    return s;
}
edi::StructureScene cube() {
    auto s = source();
    s.atom_site_id = col<std::string>({});
    s.site_symmetry = col<std::string>({});
    s.cluster_id = col<std::int32_t>({});
    s.cartn_x = col<double>({});
    s.cartn_y = col<double>({});
    s.cartn_z = col<double>({});
    s.fract_x = col<double>({});
    s.fract_y = col<double>({});
    s.fract_z = col<double>({});
    s.occupancy = col<double>({});
    s.bond_site_1 = col<std::int32_t>({});
    s.bond_site_2 = col<std::int32_t>({});
    s.bond_distance = col<double>({});
    s.site_types.clear();
    s.cartn_matrix = {10, 0, 0, 0, 10, 0, 0, 0, 10};
    return edi::present_structure(s, {});
}
}  // namespace

TEST_CASE("E04-T10 gate 2 every published colour radius and fallback") {
    const auto reference = e04_t10::elements();
    const auto& actual = edi::element_style_table();
    REQUIRE_MESSAGE(actual.size() == reference.size(),
                    " I6 embedded table is total over the independent periodic table");
    for (std::size_t i = 0; i < reference.size(); ++i) {
        const auto& r = reference[i];
        const auto& a = actual[i];
        INFO(r.symbol);
        CHECK_MESSAGE(a.symbol == r.symbol, " I6 table order is the published periodic order");
        color(a.jmol, r.jmol);
        CHECK_MESSAGE(a.vesta.has_value() == !r.vesta.empty(),
                      " I5 missing VESTA values stay explicitly absent");
        if (a.vesta && !r.vesta.empty()) color(*a.vesta, r.vesta);
        CHECK_MESSAGE(a.covalent == r.covalent,
                      " I6 covalent radius equals the independent published value");
        CHECK_MESSAGE(a.van_der_waals == r.vdw,
                      " I6 van der Waals radius equals the independent published value");
        CHECK_MESSAGE(a.ionic.has_value() == (r.ionic >= 0),
                      " I5 missing ionic radii stay explicitly absent");
        if (a.ionic)
            CHECK_MESSAGE(*a.ionic == r.ionic,
                          " I6 ionic radius equals the independent published value");
        for (auto scheme : {edi::ColorScheme::Jmol, edi::ColorScheme::Vesta}) {
            auto c = edi::element_color(r.symbol, scheme);
            CHECK_MESSAGE(c.known, " I5 every published element is known");
            color(c.color, scheme == edi::ColorScheme::Jmol || r.vesta.empty() ? r.jmol : r.vesta);
        }
        for (auto mode :
             {edi::AtomView::Covalent, edi::AtomView::VanDerWaals, edi::AtomView::Ionic}) {
            const auto r2 = edi::element_radius(r.symbol, mode);
            const double want = mode == edi::AtomView::Covalent      ? r.covalent
                                : mode == edi::AtomView::VanDerWaals ? r.vdw
                                : r.ionic < 0                        ? r.covalent
                                                                     : r.ionic;
            CHECK_MESSAGE(r2.radius == want,
                          " I5 radius lookup follows the declared model and fallback");
            CHECK_MESSAGE(r2.substituted == (mode == edi::AtomView::Ionic && r.ionic < 0),
                          " I5 substitution is reported only for an absent model");
        }
    }
    for (const auto symbol : {"", "D", "Qq"}) {
        const auto c = edi::element_color(symbol, edi::ColorScheme::Vesta);
        color(c.color, "#FFC0CB");
        CHECK_MESSAGE(!c.known, " I5 unknown elements are explicitly unknown");
        const auto r = edi::element_radius(symbol, edi::AtomView::Ionic);
        CHECK_MESSAGE((r.radius == 1 && r.substituted),
                      " I5 unknown radius takes the stated one Angstrom fallback");
    }
    for (const auto& [input, want] :
         std::vector<std::pair<std::string, std::string>>{{"Co2+", "Co"},
                                                          {"162Dy", "Dy"},
                                                          {"2H", "H"},
                                                          {"O", "O"},
                                                          {"o2-", ""},
                                                          {"D", "D"},
                                                          {"", ""}})
        CHECK_MESSAGE(edi::element_of(input) == want,
                      " I4 isotope and ion symbols follow the first-capital rule");
}

TEST_CASE("E04-T10 gate 1 every CLI scene equals independently loaded crysta geometry") {
    const auto paths = e04_t9::projects();
    REQUIRE_MESSAGE(!paths.empty(), " gate 1 independent CLI corpus must be nonempty");
    const auto published = e04_t10::elements();
    for (const auto& path : paths) {
        INFO(path);
        auto reference = crysta::load_project(path);
        auto live = edi::load_project(path);
        REQUIRE_MESSAGE(live.structures.size() == 1,
                        " gate 1 every loaded structure has a reference");
        for (std::size_t si = 0; si < live.structures.size(); ++si) {
            auto& s = *live.structures[si];
            s.current_geometry();
            const auto& g = crysta::current(reference.structure());
            const auto& rows = g.expanded_atom_sites;
            const auto capture = edi::capture_scene(s);
            const auto scene = edi::present_structure(capture, {});
            REQUIRE_MESSAGE(scene.current, " I11 fresh stored geometry presents a current scene");
            CHECK_MESSAGE(
                capture.cartn_x.get() == s.geometry.expanded_atom_sites.cartn_x.buffer().get(),
                " I1 capture shares the actual immutable position buffer");
            CHECK_MESSAGE(capture.atom_site_id.get() ==
                              s.geometry.expanded_atom_sites.atom_site_id.buffer().get(),
                          " I1 capture shares the actual immutable identity buffer");
            CHECK_MESSAGE(
                capture.bond_distance.get() == s.geometry.geom_bond.distance.buffer().get(),
                " I1 capture shares the actual immutable bond buffer");
            const auto& stored = s.geometry.expanded_atom_sites;
            CHECK_MESSAGE(
                (capture.site_symmetry == stored.site_symmetry.buffer() &&
                 capture.fract_x == stored.fract_x.buffer() &&
                 capture.fract_y == stored.fract_y.buffer() &&
                 capture.fract_z == stored.fract_z.buffer() &&
                 capture.cartn_y == stored.cartn_y.buffer() &&
                 capture.cartn_z == stored.cartn_z.buffer() &&
                 capture.occupancy == stored.occupancy.buffer() &&
                 capture.cluster_id == stored.cluster_id.buffer() &&
                 capture.bond_site_1 == s.geometry.geom_bond.expanded_atom_site_id_1.buffer() &&
                 capture.bond_site_2 == s.geometry.geom_bond.expanded_atom_site_id_2.buffer()),
                " I1 every captured immutable column shares stored geometry without a copy");
            std::map<std::int32_t, std::vector<std::size_t>> clusters;
            std::vector<std::int32_t> order;
            for (std::size_t r = 0; r < rows.size(); ++r) {
                if (!clusters.count(rows.cluster_id[r])) order.push_back(rows.cluster_id[r]);
                clusters[rows.cluster_id[r]].push_back(r);
            }
            REQUIRE_MESSAGE(scene.atoms.size() == order.size(),
                            " I3 one atom represents every independent position");
            std::map<std::size_t, std::size_t> row_atom;
            for (std::size_t ai = 0; ai < order.size(); ++ai) {
                const auto& atom = scene.atoms[ai];
                const auto& rs = clusters.at(order[ai]);
                const auto r = rs.front();
                CHECK_MESSAGE((atom.row == r && atom.cluster_id == order[ai]),
                              " I3 positions preserve first-row and cluster identity");
                CHECK_MESSAGE(
                    (bits(atom.centre.x, rows.cartn_x[r]) &&
                     bits(atom.centre.y, rows.cartn_y[r]) && bits(atom.centre.z, rows.cartn_z[r])),
                    " I1 independent engine position bits reach the renderer unchanged");
                REQUIRE_MESSAGE(atom.parts.size() == rs.size(),
                                " I3 every independent shared-site row is represented");
                std::string label;
                std::size_t major = 0;
                double total = 0;
                bool asymmetric = false;
                for (auto rr : rs) total += rows.occupancy[rr];
                for (std::size_t k = 0; k < rs.size(); ++k) {
                    const auto rr = rs[k];
                    row_atom[rr] = ai;
                    const auto& part = atom.parts[k];
                    if (k) label += "/";
                    label += rows.atom_site_id[rr];
                    if (rows.occupancy[rr] > rows.occupancy[rs[major]]) major = k;
                    asymmetric = asymmetric || rows.site_symmetry[rr] == "1_555";
                    CHECK_MESSAGE(
                        (part.row == rr && part.site_id == rows.atom_site_id[rr] &&
                         bits(part.occupancy, rows.occupancy[rr])),
                        " I3 parts retain independently read site identity occupancy and order");
                    CHECK_MESSAGE(
                        part.fraction == doctest::Approx(total == 0 ? 1. / rs.size()
                                                                    : rows.occupancy[rr] / total),
                        " I5 independent relative occupancy or equal zero-total share reaches "
                        "every part");
                    const auto& refsites = reference.structure().atom_sites;
                    auto site = std::find_if(refsites.begin(), refsites.end(), [&](const auto& q) {
                        return q.site_id == rows.atom_site_id[rr];
                    });
                    REQUIRE_MESSAGE(site != refsites.end(),
                                    " gate 2 engine labels resolve into independent loaded sites");
                    const auto symbol = site->type_symbol.get();
                    const auto pos = symbol.find_first_of("ABCDEFGHIJKLMNOPQRSTUVWXYZ");
                    const auto element = pos == std::string::npos
                                             ? std::string{}
                                             : symbol.substr(pos, 1 + (pos + 1 < symbol.size() &&
                                                                       symbol[pos + 1] >= 'a' &&
                                                                       symbol[pos + 1] <= 'z'));
                    CHECK_MESSAGE(part.element == element,
                                  " gate 2 scene element is independently read from the project "
                                  "type symbol");
                    const auto style = std::find_if(published.begin(), published.end(),
                                                    [&](auto q) { return q.symbol == element; });
                    color(part.color, style == published.end() ? "#FFC0CB" : style->jmol);
                }
                CHECK_MESSAGE(
                    (atom.label == label && atom.major == major && atom.asymmetric == asymmetric),
                    " I3 engine site order defines labels major ties and asymmetric identity");
                const auto major_style =
                    std::find_if(published.begin(), published.end(),
                                 [&](auto q) { return q.symbol == atom.parts[major].element; });
                const double radius = major_style == published.end() ? 1. : major_style->covalent;
                CHECK_MESSAGE(
                    atom.radius == doctest::Approx(.3 * std::sqrt(radius)),
                    " gate 2 atom sizing follows the published radius rather than view output");
            }
            REQUIRE_MESSAGE(scene.bonds.size() == g.geom_bond.size(),
                            " I7 every independent bond appears exactly once");
            for (std::size_t b = 0; b < scene.bonds.size(); ++b) {
                const auto r1 = static_cast<std::size_t>(g.geom_bond.expanded_atom_site_id_1[b] -
                                                         1),
                           r2 = static_cast<std::size_t>(g.geom_bond.expanded_atom_site_id_2[b] -
                                                         1);
                const auto& bond = scene.bonds[b];
                CHECK_MESSAGE(
                    (bond.row == b && bond.atom_1 == row_atom.at(r1) &&
                     bond.atom_2 == row_atom.at(r2)),
                    " I7 one-based engine bond ends map to the actual grouped atom identity");
                CHECK_MESSAGE(
                    (bits(bond.start.x, rows.cartn_x[r1]) &&
                     bits(bond.start.y, rows.cartn_y[r1]) &&
                     bits(bond.start.z, rows.cartn_z[r1]) && bits(bond.end.x, rows.cartn_x[r2]) &&
                     bits(bond.end.y, rows.cartn_y[r2]) && bits(bond.end.z, rows.cartn_z[r2]) &&
                     bits(bond.distance, g.geom_bond.distance[b])),
                    " I1 every bond coordinate and distance carries independent engine bits");
            }
            const auto m = g.atom_sites_cartn_transform.matrix;
            for (int k = 0; k < 3; ++k) vec(scene.cell_basis[k], {m[k], m[3 + k], m[6 + k]});
            REQUIRE_MESSAGE(scene.cell_edges.size() == 12,
                            " I2 cell box has exactly twelve edges");
            std::size_t edge = 0;
            for (int axis = 0; axis < 3; ++axis)
                for (int i = 0; i < 2; ++i)
                    for (int j = 0; j < 2; ++j) {
                        const int other1 = axis == 0 ? 1 : 0, other2 = axis == 2 ? 1 : 2;
                        e04_t10::Vector start{0, 0, 0}, end{0, 0, 0};
                        for (int coordinate = 0; coordinate < 3; ++coordinate) {
                            start[coordinate] =
                                i * m[3 * coordinate + other1] + j * m[3 * coordinate + other2];
                            end[coordinate] = start[coordinate] + m[3 * coordinate + axis];
                        }
                        vec(scene.cell_edges[edge].start, start);
                        vec(scene.cell_edges[edge++].end, end);
                    }
        }
    }
}

TEST_CASE("E04-T10 I1 I3 I7 skew source grouping and row provenance") {
    const auto s = source();
    const auto scene = edi::present_structure(s, {});
    REQUIRE_MESSAGE(scene.atoms.size() == 3,
                    " I3 noncontiguous cluster ids are positions in first-seen order");
    const auto& atom = scene.atoms[0];
    vec(atom.centre, {3, 4, 5});
    CHECK_MESSAGE((atom.label == "La/Ba" && atom.major == 0 && atom.row == 0 && atom.asymmetric),
                  " I3 shared position retains label first major and exact identity symmetry");
    REQUIRE_MESSAGE(scene.bonds.size() == 1,
                    " I7 one-based bond from a nonfirst shared row is retained");
    CHECK_MESSAGE((scene.bonds[0].atom_1 == 0 && scene.bonds[0].atom_2 == 1 &&
                   scene.bonds[0].distance == 8.123),
                  " I1 I7 bond distance is carried rather than recomputed from coordinates");
    vec(scene.cell_basis[1], {1, 10, 0});
    vec(scene.cell_basis[2], {2, 3, 6});
}

TEST_CASE("E04-T10 I5 zero total partial occupancies and major ties") {
    for (auto occupancies :
         std::vector<std::vector<double>>{{.6, .2}, {0, 0}, {0, .4}, {.5, .5}}) {
        auto s = source();
        s.occupancy = col<double>({occupancies[0], occupancies[1], .4, 0});
        const auto scene = edi::present_structure(s, {});
        const auto& a = scene.atoms.at(0);
        const double total = occupancies[0] + occupancies[1];
        INFO("input La/Ba occupancies=[", occupancies[0], ",", occupancies[1], "]");
        for (std::size_t k = 0; k < 2; ++k) {
            const double expected = total == 0 ? .5 : occupancies[k] / total;
            CHECK_MESSAGE(a.parts[k].fraction == doctest::Approx(expected),
                          " I5 seam 9 relative occupancy share; part=", k, "; expected=", expected,
                          "; actual=", a.parts[k].fraction);
        }
        const std::size_t expected_major = occupancies[1] > occupancies[0] ? 1 : 0;
        CHECK_MESSAGE(a.major == expected_major,
                      " I3 greatest occupancy selects the first equal row; expected major=",
                      expected_major, "; actual major=", a.major);
        CHECK_MESSAGE(scene.atoms.at(2).parts.at(0).fraction == 1,
                      " I5 seam 9 lone He occupancy=0; expected fraction=1; actual=",
                      scene.atoms.at(2).parts.at(0).fraction);
        const double expected_radius = .3 * std::sqrt(expected_major == 0 ? 2.07 : 2.15);
        CHECK_MESSAGE(
            a.radius == doctest::Approx(expected_radius),
            " I5 drawn radius uses published major-element radius and scale=0.3; expected=",
            expected_radius, "; actual=", a.radius);
    }
    auto s = source();
    s.cluster_id = col<std::int32_t>({42, 42, 42, 42});
    s.occupancy = col<double>({0, 0, 0, 0});
    const auto four = edi::present_structure(s, {});
    for (const auto& p : four.atoms.at(0).parts)
        CHECK_MESSAGE(p.fraction == .25,
                      " I5 four occupancies=[0,0,0,0] at one cluster; row=", p.row,
                      "; expected fraction=0.25; actual=", p.fraction);
    s.site_types.clear();
    edi::SceneOptions ionic;
    ionic.atom_view = edi::AtomView::Ionic;
    const auto unknown = edi::present_structure(s, ionic);
    CHECK_MESSAGE((unknown.atoms[0].radius_substituted && unknown.atoms[0].table_radius == 1),
                  " I4 I5 site types=[] in Ionic view; expected substituted=true, table_radius=1; "
                  "actual substituted=",
                  unknown.atoms[0].radius_substituted,
                  "; actual table_radius=", unknown.atoms[0].table_radius);
    std::ostringstream actual_substitutions;
    actual_substitutions << '[';
    for (std::size_t k = 0; k < unknown.substituted_elements.size(); ++k) {
        if (k) actual_substitutions << ',';
        actual_substitutions << std::quoted(unknown.substituted_elements[k]);
    }
    actual_substitutions << ']';
    // I4 maps an unmatched site to ""; I5 reports every substituted element.
    // diffraction-lib cb2cda7b builder.py adds even "" to its substitution set.
    CHECK_MESSAGE((unknown.substituted_elements == std::vector<std::string>{""}),
                  " I4 I5 radius substitution report retains the empty element once; input site "
                  "ids=[La,Ba,H,He], site types=[], occupancies=[0,0,0,0], cluster "
                  "ids=[42,42,42,42], model=Ionic; expected=[\"\"]; actual=",
                  actual_substitutions.str());
}

TEST_CASE("E04-T10 I8 selection labels legend and feature independence") {
    auto s = source();
    s.site_types.push_back({"duplicate-hydrogen", "H"});
    for (auto subset :
         {edi::AtomSubset::All, edi::AtomSubset::AsymmetricUnit, edi::AtomSubset::None}) {
        edi::SceneOptions o;
        o.atoms = subset;
        o.labels = true;
        const auto a = edi::present_structure(s, o);
        REQUIRE_MESSAGE(a.atoms.size() == 3, " I8 subsets keep the complete geometry description");
        CHECK_MESSAGE(a.has_copies, " I8 exact symmetry codes distinguish non-asymmetric copies");
        CHECK_MESSAGE(a.labels.size() == (subset == edi::AtomSubset::All    ? 3
                                          : subset == edi::AtomSubset::None ? 0
                                                                            : 1),
                      " I8 labels are restricted to drawn atoms");
        CHECK_MESSAGE(a.bonds.size() == 1, " I7 bonds do not disappear with an atom subset");
        CHECK_MESSAGE(a.legend.size() == (subset == edi::AtomSubset::None ? 0 : 4),
                      " I8 legend contains first-seen elements without duplicates");
        if (!a.legend.empty())
            CHECK_MESSAGE((a.legend[0].element == "La" && a.legend[1].element == "Ba" &&
                           a.legend[2].element == "H" && a.legend[3].element == "He"),
                          " I8 legend order follows the loaded sites");
        for (const auto& label : a.labels) {
            CHECK_MESSAGE(a.atoms[label.atom].drawn, " I8 each label names a drawn atom");
            vec(label.anchor, {a.atoms[label.atom].centre.x, a.atoms[label.atom].centre.y,
                               a.atoms[label.atom].centre.z});
        }
    }
    edi::SceneOptions off;
    off.bonds = false;
    off.cell = false;
    off.axes = false;
    const auto a = edi::present_structure(s, off);
    CHECK_MESSAGE((a.bonds.empty() && a.cell_edges.empty() && a.axes.empty()),
                  " I8 disabled feature lists are empty");
    CHECK_MESSAGE(a.atoms.size() == 3,
                  " I8 disabling features keeps the independent atom positions");
}

TEST_CASE("E04-T10 I11 stale capture never computes and old source survives edits") {
    auto live = edi::load_project(e04_t10_fixture::t1);
    auto& s = live.structure();
    s.current_geometry();
    const auto held = edi::capture_scene(s);
    REQUIRE_MESSAGE((held.current && held.cartn_x),
                    " I11 current geometry supplies immutable source columns");
    const auto old = *held.cartn_x;
    s.cell.length_a.value = s.cell.length_a.value + .01;
    const auto stale = edi::capture_scene(s);
    CHECK_MESSAGE(!s.geometry_current(), " I11 capture must not calculate an edited structure");
    CHECK_MESSAGE(
        (!stale.current && !stale.cartn_x && !stale.atom_site_id && !stale.bond_distance),
        " I11 stale source exposes no computed column");
    const auto scene = edi::present_structure(stale, {});
    CHECK_MESSAGE((!scene.current && scene.atoms.empty() && scene.bonds.empty() &&
                   scene.cell_edges.empty() && scene.axes.empty()),
                  " I11 stale source draws no geometry");
    CHECK_MESSAGE(*held.cartn_x == old, " I1 immutable held source survives later model edits");
}

TEST_CASE("E04-T10 I9 home orientation and fit independently follow diffraction-lib") {
    for (const auto matrix : std::vector<std::array<double, 9>>{{10, 0, 0, 0, 10, 0, 0, 0, 10},
                                                                {4, 0, 0, 0, 10, 0, 0, 0, 6},
                                                                {4, 1, 2, 0, 10, 3, 0, 0, 6}}) {
        auto s = source();
        s.cartn_matrix = matrix;
        const auto scene = edi::present_structure(s, {});
        std::array<e04_t10::Vector, 3> basis{};
        for (int k = 0; k < 3; ++k) basis[k] = {matrix[k], matrix[3 + k], matrix[6 + k]};
        // Fixture centres and published radii, independent of scene output.
        const double pad = .3 * std::sqrt(2.07);
        const std::vector<e04_t10::Vector> points{{3, 4, 5}, {8, 9, 10}, {11, 12, 13}};
        const auto expected = e04_t10::home(basis, points, pad);
        vec(scene.frame.target, expected.target);
        vec(scene.frame.view_direction, expected.direction);
        vec(scene.frame.view_up, expected.up);
        CHECK_MESSAGE(scene.frame.half_width == doctest::Approx(expected.width),
                      " I9 independently projected fit points and radius padding determine "
                      "horizontal extent");
        CHECK_MESSAGE(
            scene.frame.half_height == doctest::Approx(expected.height),
            " I9 independently projected fit points and radius padding determine vertical extent");
        edi::SceneOptions off;
        off.axes = false;
        off.atoms = edi::AtomSubset::None;
        const auto hidden = edi::present_structure(s, off);
        CHECK_MESSAGE((hidden.frame.half_width == scene.frame.half_width &&
                       hidden.frame.half_height == scene.frame.half_height),
                      " I9 hiding atoms and axes never changes the fitted home view");
    }
    const auto empty = edi::present_structure({}, {});
    vec(empty.frame.view_direction, e04_t10::unit({1, .8, 1.5}));
}

TEST_CASE("E04-T10 I13 I14 both projections and pointer transformations") {
    const auto scene = cube();
    const edi::Viewport viewport{400, 400, 84};
    auto view = edi::view_along(scene, 2);
    vec(view.direction, {0, 0, 1});
    vec(view.up, {0, 1, 0});
    const double H = std::max(scene.frame.half_height, scene.frame.half_width);
    const double scale = 400 / (2 * H * 1.21), cy = 200 + 84 / (2 * 1.21);
    const auto p = edi::project(scene, view, viewport, {10, 0, 0});
    CHECK_MESSAGE(
        (p.x == doctest::Approx(200 + 5 * scale) && p.y == doctest::Approx(cy + 5 * scale) &&
         p.depth == -5),
        " I13 orthographic projection obeys independent nontrivial pixel and top-band formulas");
    CHECK_MESSAGE(edi::fitted_scale(scene, viewport, edi::Projection::Orthographic) ==
                      doctest::Approx(scale),
                  " I13 fitted orthographic scale matches the independent projected extent");
    const auto rotation = edi::rotated(view, 90, 0);
    vec(rotation.direction, {-1, 0, 0});
    vec(rotation.up, {0, 1, 0});
    const auto pan = edi::panned(view, 12, -7);
    CHECK_MESSAGE((pan.pan_x == 12 && pan.pan_y == -7),
                  " I14 right drag moves the view in logical pixels");
    const auto zoom = edi::zoomed(scene, view, viewport, p.x, p.y, 120);
    const auto after = edi::project(scene, zoom, viewport, {10, 0, 0});
    CHECK_MESSAGE(zoom.magnification == 1.25,
                  " I14 one wheel notch multiplies magnification by the published factor");
    CHECK_MESSAGE((after.x == doctest::Approx(p.x) && after.y == doctest::Approx(p.y)),
                  " I14 orthographic wheel zoom anchors the actual scene point under the pointer");
    const auto inverse = edi::zoomed(scene, zoom, viewport, p.x, p.y, -120);
    CHECK_MESSAGE(inverse.magnification == doctest::Approx(1),
                  " I14 opposite wheel notches undo magnification");
    auto maximum = view;
    maximum.magnification = 100;
    CHECK_MESSAGE(edi::zoomed(scene, maximum, viewport, 200, 200, 120).magnification == 100,
                  " I14 wheel zoom respects the upper magnification bound");
    auto minimum = view;
    minimum.magnification = .05;
    CHECK_MESSAGE(edi::zoomed(scene, minimum, viewport, 200, 200, -120).magnification == .05,
                  " I14 wheel zoom respects the lower magnification bound");
    view.projection = edi::Projection::Perspective;
    const double D = 1.05 * H / std::tan(std::acos(-1.) / 12), ps = 400 / (2.1 * H);
    for (double z : {0., 10.}) {
        const auto q = edi::project(scene, view, viewport, {10, 0, z});
        CHECK_MESSAGE(
            (q.x == doctest::Approx(200 + ps * D / (D - (z - 5)) * 5) &&
             q.y == doctest::Approx(200 + ps * D / (D - (z - 5)) * 5)),
            " I13 perspective depth changes magnification with the thirty-degree field of view");
    }
    const auto perspective_zoom = edi::zoomed(scene, view, viewport, 300, 123, 120);
    CHECK_MESSAGE((perspective_zoom.pan_x == 0 && perspective_zoom.pan_y == 0),
                  " I14 perspective wheel zoom leaves pan unchanged");
}

TEST_CASE("E04-T10 I15 I16 drawing hit maps half bonds and viewport dimensions") {
    auto scene = cube();
    scene.atoms.resize(4);
    for (std::size_t i = 0; i < 4; ++i) {
        auto& a = scene.atoms[i];
        a.drawn = true;
        a.centre = {double(i), 2, 3};
        a.radius = .4;
        a.parts.resize(i % 2 ? 2 : 1);
        a.parts[0].color = {10, 20, 30};
    }
    edi::SceneBond bond;
    bond.start = {0, 0, 0};
    bond.end = {0, 0, 2};
    bond.distance = 2;
    bond.color_1 = {200, 0, 0};
    bond.color_2 = {0, 0, 200};
    scene.bonds = {bond};
    const auto landscape = edi::scene_drawing(scene, {600, 400, 84});
    const auto portrait = edi::scene_drawing(scene, {400, 600, 84});
    REQUIRE_MESSAGE((landscape.spheres.size() == 2 && landscape.cylinders.size() == 14),
                    " I16 one sphere per single site and two half-bonds followed by twelve edges");
    CHECK_MESSAGE(
        (landscape.spheres[0].atom == 0 && landscape.spheres[1].atom == 2 &&
         landscape.shared == std::vector<std::size_t>{1, 3}),
        " I15 hit identity is a table entry or shared-mesh ordinal rather than nearest centre");
    vec(landscape.spheres[0].position, {0, 2, 3});
    vec(landscape.spheres[0].scale, {.4, .4, .4});
    vec(landscape.cylinders[0].position, {0, 0, .5});
    vec(landscape.cylinders[1].position, {0, 0, 1.5});
    vec(landscape.cylinders[0].scale, {.06, 1, .06});
    vec(landscape.cylinders[1].scale, {.06, 1, .06});
    color(landscape.cylinders[0].color, "#C80000");
    color(landscape.cylinders[1].color, "#0000C8");
    for (int k = 0; k < 2; ++k) {
        const auto q = landscape.cylinders[k].rotation;
        CHECK_MESSAGE((std::abs(q[0]) == doctest::Approx(std::sqrt(.5)) &&
                       q[1] / q[0] == doctest::Approx(1) && q[2] == 0 && q[3] == 0),
                      " seam 10 unit cylinder rotates from positive y to positive z");
    }
    for (const auto& draw : {landscape, portrait}) {
        const bool tall = draw.fitted_half_height > scene.frame.half_height;
        const double H =
            std::max(scene.frame.half_height, scene.frame.half_width * (tall ? 1.5 : 2. / 3));
        CHECK_MESSAGE(
            draw.fitted_half_height == doctest::Approx(H),
            " I16 I19 each drawing reports the actual viewport-dependent fitted half-height");
        vec(draw.cylinders[2].scale, {.0025 * H, 10, .0025 * H});
        REQUIRE_MESSAGE(draw.triad.size() == 3,
                        " I19 triad has one arrow for each crysta basis vector");
        const auto& a = draw.triad[0];
        const double overhang = std::max(.09 * H, .125 * H);
        CHECK_MESSAGE((a.shaft_radius == doctest::Approx(.009 * H) &&
                       a.head_radius == doctest::Approx(.028 * H) &&
                       a.head_length == doctest::Approx(.085 * H) &&
                       a.shaft_length == doctest::Approx(10 + overhang - .085 * H)),
                      " I19 independent viewport formulas size the arrow shaft head and overhang");
        vec(a.letter_anchor, {10 + overhang + .05 * H, 0, 0});
    }
    CHECK_MESSAGE(portrait.cylinders[0].scale.y == landscape.cylinders[0].scale.y,
                  " seam 22 viewport dimensions never change bond lengths");
    const auto same = edi::scene_drawing(scene, {900, 600, 84});
    CHECK_MESSAGE(same.fitted_half_height == landscape.fitted_half_height,
                  " I16 proportional resize leaves geometry dimensions unchanged");
    scene.atoms[3].drawn = false;
    const auto hidden = edi::scene_drawing(scene, {600, 400, 84});
    CHECK_MESSAGE((hidden.shared == std::vector<std::size_t>{1}),
                  " I15 an undrawn shared atom is absent from the pick map");
}

TEST_CASE("E04-T10 I15 hover retains engine fractional and symmetry provenance") {
    const auto s = source();
    const auto scene = edi::present_structure(s, {});
    const auto text = edi::hover_text(s, scene, 0);
    for (const std::string wanted :
         {"La/Ba", "La", "Ba", "0.6", "0.2", "0.11", "0.12", "0.13", "1_555"})
        CHECK_MESSAGE(text.find(wanted) != std::string::npos,
                      " I15 hover names the actual hit atom and every independent source field");
}

TEST_CASE("E04-T10 gate 3 latest worker publication presents only newest scene") {
    auto project = edi::load_project("docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project");
    project.structure().current_geometry();
    const auto owner = std::this_thread::get_id();
    e04_t9::OwnerQueue queue;
    e04_t9::Barrier blocked;
    std::atomic<int> calculations{0};
    std::vector<std::uint64_t> captures;
    const auto final = project.structure().atom_sites[1]->fract_x.value + .002;
    auto reference = crysta::load_project("docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project");
    reference.structure().atom_sites[1].fract[0].set_value(final);
    const auto& expected = crysta::current(reference.structure()).expanded_atom_sites;
    edi::work::Worker worker([&](auto delivery) { queue.post(std::move(delivery)); });
    edi::LivePreview preview(
        project, worker,
        {[&] {
             const auto pending = edi::capture_scene(project.structure());
             CHECK_MESSAGE(!pending.current,
                           " I12 admitted edit exposes the pending state before publication");
         },
         [&](const auto& result) {
             CHECK_MESSAGE(std::this_thread::get_id() == owner,
                           " I12 capture in the published hook executes on the owner thread");
             captures.push_back(result.generation);
             const auto s = edi::capture_scene(project.structure());
             REQUIRE_MESSAGE(s.current,
                             " I12 newest publication supplies current stored geometry");
             REQUIRE_MESSAGE((s.cartn_x && s.cartn_x->size() == expected.size()),
                             " I12 newest scene covers the independently computed expanded rows");
             for (std::size_t r = 0; r < expected.size(); ++r)
                 CHECK_MESSAGE((bits((*s.cartn_x)[r], expected.cartn_x[r]) &&
                                bits((*s.cartn_y)[r], expected.cartn_y[r]) &&
                                bits((*s.cartn_z)[r], expected.cartn_z[r])),
                               " M6 final published positions equal crysta for the requested "
                               "newest coordinate");
             CHECK_MESSAGE(edi::present_structure(s, {}).current,
                           " I12 scene is actually presented inside the real publication hook");
         }},
        {[&](auto& snapshot, const auto& token) {
            if (++calculations == 1) blocked.block();
            return edi::calculate(snapshot, token);
        }});
    preview.apply(edi::Edit::value(project.structure().atom_sites[1]->fract_x, final - .001));
    blocked.entered();
    preview.apply(edi::Edit::value(project.structure().atom_sites[1]->fract_x, final));
    blocked.release();
    for (int n = 0; n < 6 && preview.busy(); ++n) queue.one();
    CHECK_MESSAGE((captures == std::vector<std::uint64_t>{2}),
                  " I12 blocked older request never captures or presents a superseded scene");
}

#else
#define E04_T10_MISSING(name)                                                                  \
    TEST_CASE(name) {                                                                          \
        REQUIRE_MESSAGE(false, "accepted scene API is absent on the pre-implementation tree"); \
    }
E04_T10_MISSING(" gate 2 every published colour radius and fallback")
E04_T10_MISSING(" gate 1 every CLI scene equals independently loaded crysta geometry")
E04_T10_MISSING(" I1 I3 I7 skew source grouping and row provenance")
E04_T10_MISSING(" I5 zero total partial occupancies and major ties")
E04_T10_MISSING(" I8 selection labels legend and feature independence")
E04_T10_MISSING(" I11 stale capture never computes and old source survives edits")
E04_T10_MISSING(" I9 home orientation and fit independently follow diffraction-lib")
E04_T10_MISSING(" I13 I14 both projections and pointer transformations")
E04_T10_MISSING(" I15 I16 drawing hit maps half bonds and viewport dimensions")
E04_T10_MISSING(" I15 hover retains engine fractional and symmetry provenance")
E04_T10_MISSING(" gate 3 latest worker publication presents only newest scene")
#endif
