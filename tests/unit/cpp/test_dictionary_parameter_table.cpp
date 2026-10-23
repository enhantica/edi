#include <doctest/doctest.h>

#include <algorithm>
#include <iterator>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

#include "edi/report.hpp"

TEST_CASE("CLI parameter tables use the dictionary format for each numeric category") {
    // Python format supplies these strings; the numbers are independent inputs.
    const std::tuple<const char*, double, const char*> cases[] = {
        {"structure.cell.length_a", 3.890915, "3.8909"},
        {"structure.cell.angle_beta", 91.234567, "91.235"},
        {"structure.atom_sites[A].fract_x", .33333, "0.33333"},
        {"structure.atom_sites[A].occupancy", .5823456, "0.5823"},
        {"experiment.instrument.setup_wavelength", 1.49412345, "1.49412"},
        {"experiment.instrument.calib_d_to_tof_linear", 7476.91234, "7476.91"},
        {"experiment.linked_structures[phase].scale", 1234567.8, "1.2346e6"},
        {"experiment.background[pA].intensity", .000012345678, "1.2346e-5"},
        {"experiment.peak.broad_gauss_u", .123456789, "0.12346"},
        {"experiment.absorption.mu_r", .036123456, "0.0361"},
        {"experiment.preferred_orientation[phase].march_r", .923456, "0.9235"}};
    for (const auto& [path, value, expected] : cases) {
        edi::FitResultBase outcome;
        outcome.values[path] = value;
        outcome.start[path] = value;
        const auto text = edi::parameter_table(outcome);
        std::istringstream stream(text);
        const std::vector<std::string> tokens{std::istream_iterator<std::string>(stream),
                                              std::istream_iterator<std::string>()};
        CHECK_MESSAGE(
            std::count(tokens.begin(), tokens.end(), expected) == 2,
            "The CLI start and value cells each use their independent dictionary format");
        CHECK_MESSAGE(
            text.find(path) != std::string::npos,
            "Dictionary display labels retain the existing parameter path as row identity");
    }
}
