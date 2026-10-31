// SPDX-License-Identifier: BSD-3-Clause
#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <exception>
#include <limits>
#include <vector>

#include "edi/structure_scene.hpp"

namespace {
edi::StructureScene shared_mesh_boundary_scene() {
    edi::StructureScene scene;
    scene.current = true;
    scene.frame.view_direction = {0, 0, 1};
    scene.frame.view_up = {0, 1, 0};
    edi::ScenePart first, second;
    first.fraction = .25;
    first.color = {17, 51, 85};
    second.fraction = .75;
    second.color = {187, 153, 119};
    edi::SceneAtom atom;
    atom.radius = 1;
    atom.parts = {first, second};
    atom.centre = {2, 3, 5};
    scene.atoms.push_back(atom);
    atom.centre = {-2, -3, -5};
    scene.atoms.push_back(atom);
    return scene;
}
}  // namespace

TEST_CASE("Shared mesh refuses bad sites at every selection position in both public profiles") {
    const auto scene = shared_mesh_boundary_scene();
    const auto beyond = scene.atoms.size();
    const auto maximum = std::numeric_limits<std::size_t>::max();
    const edi::SharedSiteBasis basis{{0, 0, 1}, {0, 1, 0}, {1, 0, 0}};
    for (const auto profile :
         {edi::SharedSiteMeshProfile::QtFloat, edi::SharedSiteMeshProfile::Three160}) {
        for (const auto& sites : std::vector<std::vector<std::size_t>>{{beyond},
                                                                       {0, beyond},
                                                                       {0, 1, beyond},
                                                                       {beyond, 0},
                                                                       {maximum, 0},
                                                                       {0, maximum},
                                                                       {0, 0, maximum}}) {
            INFO("profile=", static_cast<int>(profile), " selection count=", sites.size(),
                 " last=", sites.back());
            CHECK_THROWS_AS_MESSAGE(edi::shared_site_mesh(scene, sites, 12, 6, profile, basis),
                                    std::exception,
                                    "Every invalid site refuses through a checked C++ boundary");
        }
        const edi::StructureScene empty;
        for (const auto& sites : std::vector<std::vector<std::size_t>>{{0}, {maximum}}) {
            CHECK_THROWS_AS_MESSAGE(edi::shared_site_mesh(empty, sites, 12, 6, profile, basis),
                                    std::exception,
                                    "An empty scene cannot supply any requested shared site");
        }
    }
}

TEST_CASE("Shared mesh retains empty selections and the last valid repeated site identity") {
    const auto scene = shared_mesh_boundary_scene();
    const edi::SharedSiteBasis basis{{0, 0, 1}, {0, 1, 0}, {1, 0, 0}};
    for (const auto profile :
         {edi::SharedSiteMeshProfile::QtFloat, edi::SharedSiteMeshProfile::Three160}) {
        const auto empty = edi::shared_site_mesh(scene, {}, 12, 6, profile, basis);
        CHECK_MESSAGE(empty.vertices.empty() && empty.indices.empty(),
                      "An empty selection does not fabricate mesh geometry");
        const std::vector<std::size_t> sites{scene.atoms.size() - 1, scene.atoms.size() - 1};
        const auto mesh = edi::shared_site_mesh(scene, sites, 12, 6, profile, basis);
        REQUIRE_MESSAGE(!mesh.vertices.empty() && !mesh.indices.empty(),
                        "A genuine multipart final site reaches the public mesh kernel");
        bool first = false, second = false;
        for (const auto& vertex : mesh.vertices) {
            if (profile == edi::SharedSiteMeshProfile::QtFloat) {
                CHECK_MESSAGE(vertex.site == .5 || vertex.site == 1.5,
                              "Qt pick coordinates name selection ordinals, not source atoms");
                first = first || vertex.site == .5;
                second = second || vertex.site == 1.5;
            }
            CHECK_MESSAGE(std::isfinite(vertex.position.x) && std::isfinite(vertex.position.y) &&
                              std::isfinite(vertex.position.z),
                          "Finite valid site inputs retain finite positions");
        }
        if (profile == edi::SharedSiteMeshProfile::QtFloat)
            CHECK_MESSAGE(first && second,
                          "Repeated valid sites retain both original Qt selection identities");
        CHECK_MESSAGE(std::all_of(mesh.indices.begin(), mesh.indices.end(),
                                  [&](auto index) { return index < mesh.vertices.size(); }),
                      "Every output triangle addresses an existing output vertex");
    }
}
