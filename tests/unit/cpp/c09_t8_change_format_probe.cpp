#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <string_view>

#include "edi/report.hpp"

namespace {

void require_equal(const std::string& actual, std::string_view expected, std::string_view case_name) {
    if (actual == expected) {
        return;
    }
    std::cerr << case_name << ": expected '" << expected << "', got '" << actual << "'\n";
    std::exit(1);
}

}  // namespace

int main() {
    constexpr std::string_view up = "100.0% ↑";
    constexpr std::string_view down = "50.0% ↓";
    const double infinity = std::numeric_limits<double>::infinity();
    const double nan = std::numeric_limits<double>::quiet_NaN();

    // The previous/start value is the denominator. A current-value denominator would render
    // these as 50% up and 100% down respectively.
    require_equal(edi::format_change(2.0, 1.0), up, "start denominator, increase");
    require_equal(edi::format_change(1.0, 2.0), down, "start denominator, decrease");

    require_equal(edi::format_change(1.0, 0.0), "", "zero start");
    require_equal(edi::format_change(infinity, 1.0), "", "infinite current");
    require_equal(edi::format_change(1.0, infinity), "", "infinite start");
    require_equal(edi::format_change(nan, 1.0), "", "NaN current");
    require_equal(edi::format_change(1.0, nan), "", "NaN start");

    // Bracket both sides and both directions of the 0.05% blanking threshold. Values exactly on
    // the boundary are intentionally avoided because their binary64 representation is ambiguous.
    require_equal(edi::format_change(1.00049, 1.0), "", "+0.049% blanks");
    require_equal(edi::format_change(1.00051, 1.0), "0.1% ↑", "+0.051% renders");
    require_equal(edi::format_change(0.99951, 1.0), "", "-0.049% blanks");
    require_equal(edi::format_change(0.99949, 1.0), "0.1% ↓", "-0.051% renders");
    return 0;
}
