#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "edi/io.hpp"
#include "edi/model.hpp"

namespace {

edi::Structure geometry_fixture() {
    edi::Structure structure;
    structure.space_group.name_h_m = "P 1";
    structure.cell.length_a.value = 5.0;
    structure.cell.length_b.value = 6.0;
    structure.cell.length_c.value = 7.0;
    auto site = std::make_shared<edi::AtomSite>();
    site->id = "Si1";
    site->type_symbol = "Si";
    site->wyckoff_letter = "a";
    site->adp_type = "Biso";
    site->fract_x.value = 0.2;
    site->fract_y.value = 0.3;
    site->fract_z.value = 0.4;
    site->adp_iso.value = 0.5;
    structure.atom_sites.push_back(site);
    structure.geom.min_bond_distance_cutoff = 0.0;
    structure.geom.bond_distance_inc = 0.25;
    return structure;
}

void check_stale(const edi::Structure& structure, const edi::WindowGeometry& window) {
    CHECK_MESSAGE(!structure.geometry_current(),
                  " every admitted geometry input edit stales stored geometry");
    CHECK_MESSAGE(!edi::window_geometry_current(structure, window),
                  " every admitted geometry input edit stales held window geometry");
}

}  // namespace

TEST_CASE("C34-T27 same-object atom-site collection edits stay stale") {
    for (const std::string route : {"remove/readd", "assign", "replace_at"}) {
        INFO(route);
        auto structure = geometry_fixture();
        structure.current_geometry();
        const auto window = edi::window_geometry(structure, {});
        REQUIRE_MESSAGE(
            structure.geometry_current(),
            " fixture stored geometry starts current before a collection write");
        REQUIRE_MESSAGE(
            edi::window_geometry_current(structure, window),
            " fixture window geometry starts current before a collection write");
        const auto site = structure.atom_sites[0];
        if (route == "remove/readd") {
            structure.atom_sites.erase_at(0);
            check_stale(structure, window);
            structure.atom_sites.push_back(site);
        } else if (route == "assign") {
            structure.atom_sites.assign({site});
        } else {
            structure.atom_sites.replace_at(0, site);
        }
        check_stale(structure, window);
    }
}

TEST_CASE("C34-T27 equal-value native geometry input writes stay stale") {
    using Edit = std::function<void(edi::Structure&)>;
    const std::vector<std::pair<std::string, Edit>> edits{
        {"cell length_a", [](auto& s) { s.cell.length_a.value = s.cell.length_a.value; }},
        {"cell length_b", [](auto& s) { s.cell.length_b.value = s.cell.length_b.value; }},
        {"cell length_c", [](auto& s) { s.cell.length_c.value = s.cell.length_c.value; }},
        {"cell angle_alpha", [](auto& s) { s.cell.angle_alpha.value = s.cell.angle_alpha.value; }},
        {"cell angle_beta", [](auto& s) { s.cell.angle_beta.value = s.cell.angle_beta.value; }},
        {"cell angle_gamma", [](auto& s) { s.cell.angle_gamma.value = s.cell.angle_gamma.value; }},
        {"space group name", [](auto& s) { s.space_group.name_h_m = s.space_group.name_h_m; }},
        {"space group code",
         [](auto& s) { s.space_group.coord_system_code = s.space_group.coord_system_code; }},
        {"site id", [](auto& s) { s.atom_sites[0]->id = s.atom_sites[0]->id; }},
        {"site type",
         [](auto& s) { s.atom_sites[0]->type_symbol = s.atom_sites[0]->type_symbol; }},
        {"site ADP type", [](auto& s) { s.atom_sites[0]->adp_type = s.atom_sites[0]->adp_type; }},
        {"site x",
         [](auto& s) { s.atom_sites[0]->fract_x.value = s.atom_sites[0]->fract_x.value; }},
        {"site y",
         [](auto& s) { s.atom_sites[0]->fract_y.value = s.atom_sites[0]->fract_y.value; }},
        {"site z",
         [](auto& s) { s.atom_sites[0]->fract_z.value = s.atom_sites[0]->fract_z.value; }},
        {"site occupancy",
         [](auto& s) { s.atom_sites[0]->occupancy.value = s.atom_sites[0]->occupancy.value; }},
        {"site ADP",
         [](auto& s) { s.atom_sites[0]->adp_iso.value = s.atom_sites[0]->adp_iso.value; }},
        {"geom cutoff",
         [](auto& s) { s.geom.min_bond_distance_cutoff = s.geom.min_bond_distance_cutoff; }},
        {"geom increment", [](auto& s) { s.geom.bond_distance_inc = s.geom.bond_distance_inc; }},
    };
    for (const auto& [name, edit] : edits) {
        INFO(name);
        auto structure = geometry_fixture();
        structure.current_geometry();
        const auto window = edi::window_geometry(structure, {});
        REQUIRE_MESSAGE(
            structure.geometry_current(),
            " fixture stored geometry starts current before an equal-value native write");
        REQUIRE_MESSAGE(
            edi::window_geometry_current(structure, window),
            " fixture window geometry starts current before an equal-value native write");
        edit(structure);
        check_stale(structure, window);
    }
}

namespace {

struct SavedGeometryTree {
    std::filesystem::path path;
    ~SavedGeometryTree() { std::filesystem::remove_all(path); }
};

SavedGeometryTree saved_geometry_tree(const std::string& route) {
    const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
    return {std::filesystem::temp_directory_path() /
            ("edi--alias-" + route + "-" + std::to_string(stamp))};
}

std::string fixture_text(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open fixture: " + path.string());
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

void check_alias_assignment(const std::string& route,
                            const std::function<void(edi::Structure&)>& commit) {
    edi::Project project;
    project.structures.clear();
    project.structures.push_back(geometry_fixture());
    project.experiments.clear();
    project.experiments.push_back(edi::experiment_from_edi_text(fixture_text(
        "tests/fixtures/c11_t4_cw_selection/cases/cwl_valid.edi")));
    auto& structure = project.structure();
    auto neighbour = std::make_shared<edi::AtomSite>(*structure.atom_sites[0]);
    neighbour->id = "Si2";
    neighbour->fract_x.value = 0.6;
    structure.atom_sites.push_back(neighbour);
    structure.current_geometry();
    const auto window = edi::window_geometry(structure, {});
    REQUIRE_MESSAGE(structure.geometry_current(),
                    " alias-commit fixture starts with current stored geometry");
    REQUIRE_MESSAGE(edi::window_geometry_current(structure, window),
                    " alias-commit fixture starts with current window geometry");

    SavedGeometryTree current = saved_geometry_tree(route + "-current");
    edi::save_project(project, current.path.string());
    const auto current_text = fixture_text(current.path / "structures/structure.edi");
    REQUIRE_MESSAGE((current_text.find("_expanded_atom_site.") != std::string::npos &&
                     current_text.find("_geom_bond.") != std::string::npos),
                    " delegated save includes both categories while geometry is current");

    commit(structure);
    check_stale(structure, window);

    SavedGeometryTree stale = saved_geometry_tree(route + "-stale");
    edi::save_project(project, stale.path.string());
    const auto stale_text = fixture_text(stale.path / "structures/structure.edi");
    CHECK_MESSAGE((stale_text.find("_expanded_atom_site.") == std::string::npos &&
                   stale_text.find("_geom_bond.") == std::string::npos),
                  " delegated save omits geometry after an aliased collection commit");
}

}  // namespace

TEST_CASE("C34-T27 editor copy-assigns the live atom-site collection through an alias") {
    check_alias_assignment("copy", [](edi::Structure& structure) {
        // An editor's pending collection can alias the live one when an unchanged edit is committed.
        const auto& pending = structure.atom_sites;
        structure.atom_sites = pending;
    });
}

TEST_CASE("C34-T27 undo move-assigns the live atom-site collection through an alias") {
    check_alias_assignment("move", [](edi::Structure& structure) {
        // Undo can pass a live collection reference as its pending value for a no-op commit.
        auto& pending = structure.atom_sites;
        structure.atom_sites = std::move(pending);
    });
}
