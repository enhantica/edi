#include <doctest/doctest.h>

#include <limits>

#include "edi/report.hpp"

TEST_CASE("format_change uses the starting value as its denominator") {
    CHECK(edi::format_change(2.0, 1.0) == "100.0% ↑");
    CHECK(edi::format_change(1.0, 2.0) == "50.0% ↓");
}

TEST_CASE("format_change brackets the non-trivial blanking threshold") {
    CHECK(edi::format_change(1.00049, 1.0).empty());
    CHECK(edi::format_change(1.00051, 1.0) == "0.1% ↑");
    CHECK(edi::format_change(0.99951, 1.0).empty());
    CHECK(edi::format_change(0.99949, 1.0) == "0.1% ↓");
}

TEST_CASE("format_change refuses undefined percentages") {
    const double infinity = std::numeric_limits<double>::infinity();
    const double nan = std::numeric_limits<double>::quiet_NaN();

    CHECK(edi::format_change(1.0, 0.0).empty());
    CHECK(edi::format_change(infinity, 1.0).empty());
    CHECK(edi::format_change(1.0, infinity).empty());
    CHECK(edi::format_change(nan, 1.0).empty());
    CHECK(edi::format_change(1.0, nan).empty());
}
