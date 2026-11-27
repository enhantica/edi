#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string_view>

#include "crysta/background_estimate.hpp"

namespace {
constexpr int points = 201;
constexpr double lower = 12.0;
constexpr double upper = 52.0;

double known_background(double t) {
    return 200.0 + 12.0 * t + 8.0 * (2.0 * t * t - 1.0);
}

void report(std::string_view label, int masked_per_end) {
    crysta::BackgroundEstimateInput input;
    input.peaks.emplace();
    for (int i = 0; i < points; ++i) {
        const double t = 2.0 * i / (points - 1) - 1.0;
        const auto background = known_background(t);
        const bool overlaps_peak = i < masked_per_end || i >= points - masked_per_end;
        input.x.push_back(lower + (upper - lower) * (t + 1.0) / 2.0);
        const double overlap = overlaps_peak ? 60.0 : 0.0;
        input.y.push_back(background + overlap);
        input.measured.push_back(background + overlap);
        input.peaks->push_back(overlaps_peak);
    }
    crysta::BackgroundEstimateOptions options;
    options.width = 2.0;
    options.max_terms = 3;
    const auto estimated =
        crysta::estimate_background_series(input, options, "chebyshev", 0.0, lower, upper);
    if (estimated.coefficients.empty())
        throw std::runtime_error("The pinned engine must return a Chebyshev estimate");
    for (const double endpoint : {-1.0, 1.0}) {
        double actual = 0.0;
        double basis = 1.0;
        for (const double value : estimated.coefficients) {
            actual += value * basis;
            basis *= endpoint;
        }
        if (!std::isfinite(actual))
            throw std::runtime_error("The endpoint estimate must be finite");
        const double expected = known_background(endpoint);
        std::cout << label << ' ' << endpoint << ' ' << expected << ' ' << actual << ' '
                  << actual - expected << '\n';
    }
}
}  // namespace

int main() {
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "case endpoint expected estimated error\n";
    report("long", 60);
    report("short", 8);
}
