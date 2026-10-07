#include <doctest/doctest.h>

#include <Eigen/Dense>
#include <Eigen/Geometry>
#include <filesystem>
#include <fstream>
#include <memory>
#include <vector>

#include "edi/structure_scene.hpp"

namespace {
template <class T>
auto column(std::vector<T> values) {
    return std::make_shared<const std::vector<T>>(std::move(values));
}

template <class Source, class Options>
bool check_ellipsoids() {
    using View = decltype(Options{}.atom_view);
    if constexpr (requires(Source s, Options o) {
                      s.site_adps;
                      o.adp_probability;
                      View::Adp;
                  }) {
        Options options;
        CHECK_MESSAGE(options.adp_probability == .99,
                      "The ellipsoid probability default must be 0.99");
        options.atom_view = View::Adp;
        options.bonds = options.cell = options.axes = false;
        Source source;
        source.current = true;
        source.structure_id = "tensor";
        source.atom_site_id = column<std::string>({"O"});
        source.site_symmetry = column<std::string>({"1_555"});
        source.cluster_id = column<std::int32_t>({1});
        source.fract_x = source.fract_y = source.fract_z = column<double>({0});
        source.cartn_x = source.cartn_y = source.cartn_z = column<double>({0});
        source.occupancy = column<double>({1});
        source.site_types = {{"O", "O"}};
        source.cartn_matrix = {1, 0, 0, 0, 1, 0, 0, 0, 1};
        source.operation_rotations = {{{1, 0, 0, 0, 1, 0, 0, 0, 1}}};
        const auto path =
            std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
            "fixtures/anisotropic_adps/ellipsoids.tsv";
        std::ifstream input(path);
        REQUIRE_MESSAGE(input.good(),
                        "The renderer must be checked against cctbx Cartesian tensors");
        std::array<double, 6> u{};
        int count = 0;
        while (input >> u[0] >> u[1] >> u[2] >> u[3] >> u[4] >> u[5]) {
            const std::array<double, 9> cart{u[0], u[3], u[4], u[3], u[1], u[5], u[4], u[5], u[2]};
            source.site_adps = {typename Source::SiteAdp{"O", 0, cart}};
            auto scene = edi::present_structure(source, options);
            REQUIRE_MESSAGE(scene.atoms.size() == 1, "The ADP scene must keep every source atom");
            const auto& atom = scene.atoms[0];
            REQUIRE_MESSAGE(atom.ellipsoid, "An anisotropic site must be drawn as an ellipsoid");
            Eigen::Quaterniond q(atom.orientation[0], atom.orientation[1], atom.orientation[2],
                                 atom.orientation[3]);
            CHECK_MESSAGE(q.norm() == doctest::Approx(1).epsilon(1e-12),
                          "Ellipsoid orientation must be a unit quaternion");
            const Eigen::Vector3d axes(atom.semi_axes.x, atom.semi_axes.y, atom.semi_axes.z);
            CHECK_MESSAGE(axes.minCoeff() > 0,
                          "A positive definite tensor must have positive ellipsoid axes");
            const Eigen::Matrix3d drawn = q.toRotationMatrix() *
                                          axes.array().square().matrix().asDiagonal() *
                                          q.toRotationMatrix().transpose();
            Eigen::Matrix3d expected;
            expected << u[0], u[3], u[4], u[3], u[1], u[5], u[4], u[5], u[2];
            CHECK_MESSAGE((drawn / drawn.trace() - expected / expected.trace()).norm() < 1e-11,
                          "The drawn ellipsoid axes and orientation must reproduce the cctbx "
                          "Cartesian tensor shape");
            Options smaller = options;
            smaller.adp_probability = .5;
            const auto half = edi::present_structure(source, smaller);
            CHECK_MESSAGE(half.atoms[0].radius < atom.radius,
                          "Lower probability must make the same displacement ellipsoid smaller");
            ++count;
        }
        return count == 2;
    } else {
        REQUIRE_MESSAGE(
            false, "The core scene must support anisotropic tensors and ellipsoid probability");
        return false;
    }
}
}  // namespace

TEST_CASE("Anisotropic scene axes and orientation preserve cctbx tensor shape") {
    CHECK_MESSAGE((check_ellipsoids<edi::SceneSource, edi::SceneOptions>()),
                  "Both monoclinic and hexagonal Cartesian references must reach the scene");
}
