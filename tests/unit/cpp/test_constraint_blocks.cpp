#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>

#include "edi/io.hpp"

namespace {
struct ProjectDirectory {
    std::filesystem::path path =
        std::filesystem::temp_directory_path() /
        ("constraint-blocks-" +
         std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    ProjectDirectory(const std::string& independent, const std::string& dependent) {
        const auto source =
            std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
            "fixtures/constraint_expressions/project";
        std::filesystem::copy(source, path, std::filesystem::copy_options::recursive);
        const auto bank = path / "experiments/bank.edi";
        std::ifstream input(bank);
        std::string text((std::istreambuf_iterator<char>(input)), {});
        text.replace(text.find("data_bank"), 9, "data_second");
        std::ofstream(path / "experiments/second.edi") << text;
        std::ofstream(path / "analysis/analysis.edi")
            << "_edi.schema_version 3\n_fitting_mode.type joint\n_minimizer.max_iterations 1\n"
               "loop_\n_alias.id\n_alias.parameter_unique_name\na "
            << independent << "\nb " << dependent
            << "\nloop_\n_constraint.expression\n\"b = .1*a + .01\"\n";
    }
    ~ProjectDirectory() { std::filesystem::remove_all(path); }
};
}  // namespace

TEST_CASE("Core joint fitting refuses unsupported relation directions") {
    for (const std::string target :
         {"second.instrument.calib_twotheta_offset", "phase.atom_site.B.adp_iso"}) {
        ProjectDirectory directory("bank.instrument.calib_twotheta_offset", target);
        auto project = edi::load_project(directory.path.string());
        project.experiment().instrument.calib_twotheta_offset->free = true;
        bool refused = false;
        try {
            (void)project.fit_joint();
        } catch (const std::exception& error) {
            refused = true;
            const std::string message(error.what());
            CHECK_MESSAGE(
                message.find("crysta.domain.constraint_crosses_blocks") != std::string::npos,
                "The core adapter must preserve the joint block refusal code");
            CHECK_MESSAGE(message.find("bank") != std::string::npos,
                          "The joint refusal must identify its independent bank");
        }
        CHECK_MESSAGE(
            refused,
            "Unsupported cross-bank and reverse-prefix relations must refuse before solving");
    }
}

TEST_CASE("Core joint bank dependents can reach the shared structural prefix") {
    ProjectDirectory directory("phase.atom_site.A.adp_iso",
                               "bank.instrument.calib_twotheta_offset");
    auto project = edi::load_project(directory.path.string());
    project.structure().atom_sites[0]->adp_iso.free = true;
    (void)project.fit_joint();
    const double value = project.structure().atom_sites[0]->adp_iso.value;
    CHECK_MESSAGE(
        project.experiment().instrument.calib_twotheta_offset->value ==
            doctest::Approx(.1 * value + .01),
        "The core adapter must retain admitted shared-prefix relations during joint write-back");
}
