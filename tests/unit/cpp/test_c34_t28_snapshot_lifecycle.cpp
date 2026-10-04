#include <doctest/doctest.h>

#include <cstring>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

#include "edi/io.hpp"
#include "edi/model.hpp"

TEST_CASE("C34-T28 edi computed snapshots survive growth erase copies and owner destruction") {
    std::vector<edi::ComputedColumn<double>> held;
    std::vector<std::vector<double>> bytes;
    std::vector<edi::ComputedColumn<std::string>> text;
    std::vector<std::vector<std::string>> text_before;
    auto unchanged = [&] {
        for (std::size_t index = 0; index < held.size(); ++index) {
            REQUIRE_MESSAGE(held[index].size() == bytes[index].size(),
                            " I17 a numeric snapshot keeps its original length");
            CHECK_MESSAGE(std::memcmp(held[index].values().data(), bytes[index].data(),
                                      bytes[index].size() * sizeof(double)) == 0,
                          " I17 a numeric snapshot keeps its exact bytes including NaNs");
        }
        for (std::size_t index = 0; index < text.size(); ++index) {
            CHECK_MESSAGE(text[index].values() == text_before[index],
                          " I17 a string snapshot keeps its captured row contents");
        }
    };
    {
        const auto path =
            std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
            "fixtures/c34_t28_baseline/freshness-input";
        auto project = edi::load_project(path.string());
        project.calculate();
        const auto& geometry = project.structure().current_geometry();
        held = {project.experiment().data->intensity_calc, project.experiment().refln.d_spacing,
                geometry.expanded_atom_sites.cartn_x};
        text = {project.experiment().refln.structure_id,
                geometry.expanded_atom_sites.atom_site_id};
        for (const auto& column : held) {
            REQUIRE_MESSAGE(!column.empty(), " I17 the snapshot control has real rows");
            bytes.push_back(column.values());
        }
        for (const auto& column : text) {
            REQUIRE_MESSAGE(!column.empty(), " I17 the string control has real rows");
            text_before.push_back(column.values());
        }
        auto copy = project;
        copy.structure().cell.length_a.value += 0.375;
        copy.calculate();
        unchanged();
        auto& rows = project.structure().atom_sites;
        for (int index = 0; index < 7; ++index) {
            auto site = std::make_shared<edi::AtomSite>(*rows[0]);
            site->id = "added-" + std::to_string(index);
            site->fract_x.value = 0.071 * index;
            rows.push_back(site);
        }
        rows[0]->occupancy.value = 0.437;
        project.calculate();
        unchanged();
        rows.erase_at(0);
        project.calculate();
        unchanged();
    }
    unchanged();
}
