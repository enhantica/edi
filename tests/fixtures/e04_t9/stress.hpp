#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

#include "edi/io.hpp"

//  P12: deterministic interpolation of the committed echidna measurement.
// This generator supplies input, never a calculated correctness expectation.
namespace e04_t9_fixture {
inline constexpr const char* echidna =
    "docs/user/cli/pd-neut-cwl_lab6-echidna_fcj-asymmetry/project";
inline constexpr const char* silicon =
    "docs/user/cli/pd-neut-tof_si-sepd_start-2/project";
inline constexpr const char* wish =
    "docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-5/project";

inline std::vector<double> interpolate(const std::vector<double>& x,
                                       const std::vector<double>& y,
                                       const std::vector<double>& grid) {
    if (x.size() < 2 || x.size() != y.size() || !std::is_sorted(x.begin(), x.end()))
        throw std::invalid_argument(" D3 requires aligned monotonic measured columns");
    std::vector<double> out;
    out.reserve(grid.size());
    std::size_t j = 1;
    for (double at : grid) {
        while (j + 1 < x.size() && x[j] < at) ++j;
        const double share = (at - x[j - 1]) / (x[j] - x[j - 1]);
        out.push_back(y[j - 1] + share * (y[j] - y[j - 1]));
    }
    return out;
}

inline edi::Project stress(const std::string& root = ".") {
    auto project = edi::load_project(root + "/" + echidna);
    auto& data = *project.experiment().data;
    const auto original = data.axis();
    std::vector<double> grid(50000);
    for (std::size_t i = 0; i < grid.size(); ++i)
        grid[i] = original.front() + (original.back() - original.front()) *
                  static_cast<double>(i) / static_cast<double>(grid.size() - 1);
    grid.back() = original.back();
    auto measured = interpolate(original, data.intensity_meas, grid);
    auto uncertainty = interpolate(original, data.intensity_meas_su, grid);
    data.write_axis(&edi::PdDataBase::two_theta, std::move(grid));
    data.write_column(&edi::PdDataBase::intensity_meas, std::move(measured));
    data.write_column(&edi::PdDataBase::intensity_meas_su, std::move(uncertainty));
    return project;
}
}  // namespace e04_t9_fixture
