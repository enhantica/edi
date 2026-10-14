#include <doctest/doctest.h>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <regex>
#include <string>
#include <tuple>

#include "crysta/analysis.hpp"
#include "crysta/fit_quality.hpp"
#include "crysta/residual.hpp"
#include "crysta/threading.hpp"

TEST_CASE("FullProf phase factors at the fixed PCR model match its summary") {
    struct RestoreThreads {
        int previous = crysta::threading::thread_count_setting();
        ~RestoreThreads() { crysta::threading::set_thread_count(previous); }
    } restore_threads;
    crysta::threading::set_thread_count(1);  // A numerical reference does not need a worker-team startup.
    const auto fixture = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
                         "fixtures/fit_quality";
    std::ifstream summary_file(fixture / "lbco.sum");
    const std::string summary((std::istreambuf_iterator<char>(summary_file)),
                              std::istreambuf_iterator<char>());
    const auto printed = [&summary](const std::string& expression) {
        std::smatch match;
        REQUIRE_MESSAGE(std::regex_search(summary, match, std::regex(expression)),
                        "The independent FullProf summary must supply each printed factor");
        return std::stod(match[1].str());
    };
    const double allowance = 4 * std::abs(100 * 0.07233610852 - printed("Rwp:\\s+([0-9.]+)")) + 0.005;
    auto project = crysta::load_project((fixture / "fullprof-model").string());
    REQUIRE_MESSAGE(crysta::free_from_model(project).empty(),
                    "The phase comparison must calculate the fixed FullProf model without fitting");
    crysta::calculate_project(project);
    const auto quality = crysta::fit_quality(project, 0);
    REQUIRE_MESSAGE(quality.phases.size() == 1,
                    "The one-phase FullProf calculation must retain one phase metric row");
    const auto& phase = quality.phases.front();
    for (const auto& [field, obtained, expected] : {
             std::tuple{"bragg_r_factor", 100 * phase.r_bragg, printed("Bragg R-factor:\\s+([0-9.]+)")},
             std::tuple{"f_r_factor", 100 * phase.r_f, printed("Rf-factor=\\s+([0-9.]+)")}}) {
        CHECK_MESSAGE(std::abs(obtained - expected) <= allowance,
                      "The fixed-model phase factors must agree with the independent FullProf summary: ",
                      std::string(field), " obtained ", obtained, "%, expected ", expected,
                      "%, allowance ", allowance, " percentage points");
    }
}
