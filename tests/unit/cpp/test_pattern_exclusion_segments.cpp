#include <doctest/doctest.h>
#include <algorithm>
#include <cmath>
#include <optional>
#include "edi/presentation.hpp"

namespace {
void exclusion_segments(bool descending, int columns) {
    std::vector<double> x, y;
    for (int i = 0; i < 64; ++i) {
        x.push_back(10.0 + i);
        y.push_back(100.0 + i + (i == 17 ? 200.0 : 0.0));
    }
    if (descending) {
        std::reverse(x.begin(), x.end());
        std::reverse(y.begin(), y.end());
    }
    edi::PatternSource source;
    source.x = std::make_shared<const std::vector<double>>(x);
    source.meas = source.calc = source.bkg = source.resid = std::make_shared<const std::vector<double>>(y);
    source.su = std::make_shared<const std::vector<double>>(64, 2.5);
    source.current = true;
    source.excluded = {{40.4, 40.6}};
    REQUIRE_MESSAGE(std::none_of(x.begin(), x.end(), [](double value) { return value >= 40.4 && value <= 40.6; }),
                    "The excluded band lies strictly between observations, so sample masking cannot create its gap");
    for (bool included_only : {false, true}) {
        CAPTURE(descending);
        CAPTURE(columns);
        CAPTURE(included_only);
        edi::PatternView view;
        view.columns = columns;
        view.included_only = included_only;
        const auto shown = edi::present_pattern(source, view);
        REQUIRE_MESSAGE(shown.series.size() == 4, "Every measured, calculated, background and difference consumer reaches the shared presenter");
        for (const auto& series : shown.series) {
            CAPTURE(series.id);
            std::optional<double> previous;
            std::size_t finite = 0;
            bool crosses = false, left = false, right = false;
            for (const auto& point : series.points) {
                if (!std::isfinite(point.x) || !std::isfinite(point.y)) {
                    previous.reset();
                    continue;
                }
                ++finite;
                left |= point.x < 40.4;
                right |= point.x > 40.6;
                const auto row = std::find(x.begin(), x.end(), point.x);
                REQUIRE_MESSAGE(row != x.end(), "Every finite presentation coordinate retains a real source observation");
                CHECK_MESSAGE(point.y == y[static_cast<std::size_t>(row - x.begin())],
                              "Creating a segment gap never changes a surviving observation's value");
                if (previous)
                    crosses |= std::max(std::min(*previous, point.x), 40.4) < std::min(std::max(*previous, point.x), 40.6);
                previous = point.x;
            }
            CHECK_MESSAGE((left && right), "Both sides of a narrow exclusion remain represented rather than dropping a complete side");
            if (columns == 0)
                CHECK_MESSAGE(finite == x.size(), "Full-resolution gaps retain every included observation on both sides");
            else
                CHECK_MESSAGE(finite < x.size(), "The decimation witness actually discards observations before its segment check");
            if (series.kind == edi::SeriesKind::Measured && !included_only)
                CHECK_MESSAGE(crosses, "Toggle off retains the measured line's full-range continuity through exclusions");
            else
                CHECK_MESSAGE(!crosses, "No finite segment crosses an excluded interval, even when neither endpoint is excluded");
        }
    }
}
}

TEST_CASE("A narrow exclusion breaks every derived curve between observations") { exclusion_segments(false, 0); }
TEST_CASE("A descending axis preserves narrow exclusion gaps") { exclusion_segments(true, 0); }
TEST_CASE("Decimation cannot erase a narrow exclusion boundary") { exclusion_segments(false, 1); }
TEST_CASE("Descending decimation cannot erase a narrow exclusion boundary") { exclusion_segments(true, 1); }
