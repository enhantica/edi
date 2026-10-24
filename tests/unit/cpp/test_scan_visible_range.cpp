#include <doctest/doctest.h>
#include "edi/scan_views.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

TEST_CASE("Visible scan columns retain every in-range minimum and maximum") {
    std::vector<double> x, y;
    for (int i = 0; i <= 144; ++i) {
        x.push_back(-3.25 + i / 16.0);
        y.push_back((i * 73) % 257);
    }
    for (const auto bounds : {std::pair{-3.25, 5.75}, std::pair{-0.9375, 0.8125}}) {
        for (const std::size_t columns : {8, 32, 64}) {
            const auto actual = edi::scan_columns(x, y, bounds.first, bounds.second, columns);
            REQUIRE_MESSAGE((actual.low.size() == columns && actual.high.size() == columns),
                            "Visible-range reduction has exactly the requested pixel columns");
            for (std::size_t c = 0; c < columns; ++c) {
                const double left = bounds.first + (bounds.second - bounds.first) * c / columns;
                const double right = bounds.first + (bounds.second - bounds.first) * (c + 1) / columns;
                double low = INFINITY, high = -INFINITY;
                for (std::size_t i = 0; i < x.size(); ++i) {
                    if (x[i] >= left && (c + 1 == columns ? x[i] <= right : x[i] < right)) {
                        low = std::min(low, y[i]); high = std::max(high, y[i]);
                    }
                }
                if (!std::isfinite(low)) {
                    CHECK_MESSAGE((std::isnan(actual.low[c]) && std::isnan(actual.high[c])),
                                  "An empty visible pixel column cannot borrow an out-of-range point");
                } else {
                    CHECK_MESSAGE((actual.low[c] == low && actual.high[c] == high),
                                  "Each pixel retains the independently enumerated visible extrema");
                }
            }
        }
    }
}

TEST_CASE("A resolved scan range retains its measured samples without a full-range envelope") {
    std::vector<double> x, y;
    for (int i = 0; i <= 256; ++i) { x.push_back(i / 16.0); y.push_back((i * 53) % 251); }
    const auto full = edi::scan_columns(x, y, 0, 16, 16);
    const auto zoomed = edi::scan_columns(x, y, 7, 7.5, 16);
    int represented = 0;
    bool interior = false;
    for (int i = 112; i <= 120; ++i) {
        const std::size_t column = std::min<std::size_t>(15, (x[i] - 7) / 0.5 * 16);
        CHECK_MESSAGE((zoomed.low[column] == y[i] && zoomed.high[column] == y[i]),
                      "Below pixel resolution the visible reduction preserves each original sample");
        ++represented;
        interior = interior || (y[i] > full.low[7] && y[i] < full.high[7]);
    }
    CHECK_MESSAGE((represented == 9 && interior),
                  "The zoom witness includes values irrecoverable from the prior full-range extrema");
}
