#include <doctest/doctest.h>

#include <algorithm>
#include <cmath>
#include <limits>
#include <memory>
#include <vector>

#include "edi/presentation.hpp"
namespace {
edi::PatternSource::Column column(std::initializer_list<double> values) {
    return std::make_shared<const std::vector<double>>(values);
}
template <class View>
bool request_residual_band(View& view) {
    if constexpr (requires { view.residual_band; }) {
        view.residual_band = true;
        return true;
    }
    return false;
}
edi::PatternSource input() {
    edi::PatternSource source;
    source.current = true;
    source.x = column({40, 52, 64});
    source.meas = column({20, 33, 25});
    source.su = column({2, 3, 4});
    source.calc = column({6, 6, 6});
    source.bkg = column({6, 6, 6});
    source.resid = column({14, 27, 19});
    return source;
}
const edi::PatternSeries& kind(const edi::PatternPresentation& result, edi::SeriesKind value) {
    const auto found = std::find_if(result.series.begin(), result.series.end(),
                                    [value](const auto& row) { return row.kind == value; });
    REQUIRE_MESSAGE(found != result.series.end(),
                    "The presentation retains the required measured or residual drawing series");
    return *found;
}
}  // namespace
TEST_CASE("Owner uncertainty bands retain independent measured and residual edges") {
    auto source = input();
    edi::PatternView view;
    REQUIRE_MESSAGE(
        request_residual_band(view),
        "The pattern presentation can request its owner-required residual uncertainty band");
    const auto result = edi::present_pattern(source, view);
    for (const auto value : {edi::SeriesKind::Measured, edi::SeriesKind::Residual}) {
        const auto& row = kind(result, value);
        REQUIRE_MESSAGE(row.points.size() == 3,
                        "The complete band contains each independent measured point once");
        REQUIRE_MESSAGE((row.bar_low.size() == 3 && row.bar_high.size() == 3),
                        "Both actual band edges cover every measured point");
        for (std::size_t index = 0; index < 3; ++index) {
            const auto centre = std::vector<double>{20, 33, 25}[index] -
                                (value == edi::SeriesKind::Residual ? 6 : 0);
            CHECK_MESSAGE((row.points[index].x == std::vector<double>{40, 52, 64}[index]),
                          "Every band edge retains the independently specified x coordinate");
            CHECK_MESSAGE((row.bar_low[index] == centre - std::vector<double>{2, 3, 4}[index]),
                          "The lower band edge equals the independent measured or residual value "
                          "minus s.u.");
            CHECK_MESSAGE(
                (row.bar_high[index] == centre + std::vector<double>{2, 3, 4}[index]),
                "The upper band edge equals the independent measured or residual value plus s.u.");
        }
    }
}
TEST_CASE("Owner uncertainty bands give absent zero and nonfinite su zero width") {
    for (const auto uncertainty :
         {edi::PatternSource::Column{}, column({0, 0, 0}), column({NAN, NAN, NAN})}) {
        auto source = input();
        source.su = uncertainty;
        edi::PatternView view;
        REQUIRE_MESSAGE(
            request_residual_band(view),
            "A missing uncertainty still reaches the owner-required band presentation");
        const auto result = edi::present_pattern(source, view);
        for (const auto value : {edi::SeriesKind::Measured, edi::SeriesKind::Residual}) {
            const auto& row = kind(result, value);
            INFO((std::string("uncertainty=") +
                  (!uncertainty                       ? "absent"
                   : std::isfinite((*uncertainty)[0]) ? "zero"
                                                      : "nonfinite") +
                  ", series=" + std::to_string(static_cast<int>(value))));
            REQUIRE_MESSAGE((row.bar_low.size() == 3 && row.bar_high.size() == 3),
                            "Absent uncertainties still publish both zero-width band edges");
            for (std::size_t index = 0; index < 3; ++index) {
                const auto centre = std::vector<double>{20, 33, 25}[index] -
                                    (value == edi::SeriesKind::Residual ? 6 : 0);
                CHECK_MESSAGE((row.bar_low[index] == centre && row.bar_high[index] == centre),
                              "Missing zero or nonfinite s.u. collapses both measured and "
                              "residual band edges exactly to their independent centre");
            }
        }
    }
}
