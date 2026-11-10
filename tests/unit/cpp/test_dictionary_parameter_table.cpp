#include <doctest/doctest.h>

#include <algorithm>
#include <iterator>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

#include "edi/report.hpp"
#include "edi/model.hpp"

TEST_CASE("CLI parameter tables use the dictionary format for each numeric category") {
    // Python format supplies these strings; the numbers are independent inputs.
    const std::tuple<const char*, double, const char*> cases[] = {
        {"structure.cell.length_a", 3.890915, "3.8909"},
        {"experiment.background[pA].intensity", 0.000999, "9.99e-4"},
        {"experiment.background[pA].intensity", 0.001, "0.001"},
        {"experiment.background[pA].intensity", 999.9, "999.9"},
        {"experiment.background[pA].intensity", 1000.0, "1.00e3"},
        {"experiment.background[pA].intensity", -0.000999, "-9.99e-4"},
        {"experiment.background[pA].intensity", -0.001, "-0.001"},
        {"experiment.background[pA].intensity", -999.9, "-999.9"},
        {"experiment.background[pA].intensity", -1000.0, "-1.00e3"},
        {"experiment.background[pA].intensity", 0.0, "0"},
        {"experiment.background[pA].intensity", 7453675696.0, "7.45e9"},
        {"structure.cell.angle_beta", 91.234567, "91.235"},
        {"structure.atom_sites[A].fract_x", .33333, "0.33333"},
        {"structure.atom_sites[A].occupancy", .5823456, "0.5823"},
        {"experiment.instrument.setup_wavelength", 1.49412345, "1.49412"},
        {"experiment.instrument.calib_d_to_tof_linear", 7476.91234, "7.48e3"},
        {"experiment.linked_structures[phase].scale", 1234567.8, "1.23e6"},
        {"experiment.background[pA].intensity", .000012345678, "1.23e-5"},
        {"experiment.peak.broad_gauss_u", .123456789, "0.12346"},
        {"experiment.absorption.mu_r", .036123456, "0.0361"},
        {"experiment.preferred_orientation[phase].march_r", .923456, "0.9235"}};
    for (const auto& [path, value, expected] : cases) {
        INFO(path);
        edi::FitResultBase outcome;
        outcome.values[path] = value;
        outcome.start[path] = value;
        const auto text = edi::parameter_table(outcome);
        INFO(text);
        std::istringstream stream(text);
        const std::vector<std::string> tokens{std::istream_iterator<std::string>(stream),
                                              std::istream_iterator<std::string>()};
        const auto identity = std::find(tokens.begin(), tokens.end(), path);
        REQUIRE_MESSAGE(
            (identity != tokens.end() && std::distance(identity, tokens.end()) >= 3),
            "Dictionary display labels retain the existing parameter path before start and value");
        CHECK_MESSAGE(
            (*std::next(identity) == expected && *std::next(identity, 2) == expected),
            "The CLI start and value cells each use their independent dictionary format");
    }
}

TEST_CASE("CLI parameter table scientific pairs keep the project uncertainty precision") {
    edi::Project project;
    project.su_rule = "iucr_19";
    for (const auto& [value, su, shown, error] : std::vector<std::tuple<double, double, const char*, const char*>>{
             {1000.0, 2.01, "1.000e3", "0.003e3"},
             {-1000.0, 2.01, "-1.000e3", "0.003e3"},
             {.000999, .00000201, "9.99e-4", "0.03e-4"},
             {-.000999, .00000201, "-9.99e-4", "0.03e-4"}}) {
        edi::FitResultBase outcome;
        const std::string path = "experiment.background[pA].intensity";
        outcome.values[path] = value;
        outcome.start[path] = value;
        outcome.uncertainty[path] = su;
        const auto text = edi::parameter_table(outcome, &project);
        INFO(text);
        std::istringstream stream(text);
        const std::vector<std::string> tokens{std::istream_iterator<std::string>(stream),
                                              std::istream_iterator<std::string>()};
        CHECK_MESSAGE(std::find(tokens.begin(), tokens.end(), shown) != tokens.end(),
                      "Owner 7dea80601 CLI values keep the IUCr last place in scientific notation");
        CHECK_MESSAGE(std::find(tokens.begin(), tokens.end(), error) != tokens.end(),
                      "Owner 7dea80601 CLI uncertainties share the value power and retain IUCr rounding");
    }
}
