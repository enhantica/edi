#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

#include "edi/io.hpp"
#include "edi/model.hpp"

namespace {

std::filesystem::path source_root() {
    std::filesystem::path start = std::filesystem::absolute(__FILE__).parent_path();
    for (int depth = 0; depth < 8; ++depth) {
        if (std::filesystem::exists(start / "CMakeLists.txt") &&
            std::filesystem::exists(start / "pixi.toml")) {
            return start;
        }
        start = start.parent_path();
    }
    throw std::runtime_error("cannot locate the edi source root");
}

std::string read_text(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open migrated fixture: " + path.string());
    }
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

}  // namespace

TEST_CASE("E09-T55 migrated owner-shape silicon pattern crosses space-group validation") {
    const std::filesystem::path root = source_root();
    edi::Project project = edi::load_project(
        (root / "tests/fixtures/c09_t6_ncaf_5bank_absorption/type_none_project").string());
    edi::Structure silicon = edi::structure_from_edi_text(
        read_text(root / "tests/fixtures/c12_t3_space_group_code/si_origin_2.edi"));
    silicon.scattering_lengths_fm = {{"Si", 4.1491}};
    project.structures.clear();
    project.structures.push_back(std::move(silicon));
    project.experiment().linked_structure().structure_id = "si";
    REQUIRE_MESSAGE(project.experiment().data.has_value(),
                    "the migrated owner-shape assertion requires measured data");
    project.calculate();
    const std::vector<double>& axis = project.experiment().data->axis();
    const std::vector<double>& calculated = project.experiment().data->intensity_calc.values();
    CHECK_MESSAGE((calculated.size() == 4166 && calculated.size() == axis.size()),
                  "the migrated owner-shape assertion requires all 4166 frozen input rows");
    const auto& status = project.experiment().data->calc_status;
    REQUIRE_MESSAGE(status.size() == calculated.size(),
                    "the computed pattern must declare the inclusion status of every row");
    for (std::size_t i = 0; i < calculated.size(); ++i) {
        REQUIRE_MESSAGE((status[i] == "incl" || status[i] == "excl"),
                        "the computed pattern must use the closed inclusion-status vocabulary");
        CHECK_MESSAGE(
            (status[i] == "excl" ? std::isnan(calculated[i])
                                 : std::isfinite(calculated[i]) && calculated[i] >= 0.0),
            "the migrated pattern must be non-negative on included rows and NaN on excluded rows");
    }
    CHECK_MESSAGE(std::any_of(calculated.begin(), calculated.end(),
                              [](double value) { return value > 0.0; }),
                  "the migrated owner-shape pattern must retain non-zero intensity");
}
