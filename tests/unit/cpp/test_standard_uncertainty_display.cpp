#include <doctest/doctest.h>

#include <array>
#include <string>
#include <tuple>

#if __has_include("edi/su_text.hpp")
#include "edi/su_text.hpp"
#define HAS_SU_DISPLAY 1
#endif

TEST_CASE("Standard uncertainty display follows both IUCr decimal rules") {
#ifdef HAS_SU_DISPLAY
    const std::array<std::tuple<double, double, const char*, const char*>, 11> cases{{
        {1.54249, .01532, "iucr_19", "1.542(16)"},
        {2.16352, .00481, "iucr_19", "2.164(5)"},
        {2.16352, .00481, "iucr_99", "2.1635(49)"},
        {.4637, .0196, "iucr_19", "0.46(2)"},
        {.4637, .0196, "iucr_99", "0.464(20)"},
        {54912, 1234, "iucr_19", "54900(1300)"},
        {0, .0123, "iucr_19", "0.000(13)"},
        {-.02134, .00151, "iucr_19", "-0.0213(16)"},
        {1.2345, .015, "iucr_19", "1.235(15)"},
        {-1.2345, .015, "iucr_19", "-1.235(15)"},
        {10.30925, .00157, "iucr_19", "10.3093(16)"},
    }};
    for (const auto& [value, su, rule, expected] : cases) {
        CAPTURE(value, su, rule);
        CHECK_MESSAGE(edi::value_su_text(value, su, rule) == expected,
                      "The core display must carry the independent IUCr decimal spelling");
    }
    CHECK_MESSAGE(edi::value_su_text(0, 2e-310, "iucr_19") == "0." + std::string(310, '0') + "(2)",
                  "A subnormal uncertainty must keep its nonzero fixed-point bracket");
    const auto standard = edi::su_text(2.16352, .00481, "iucr_19");
    const auto two_digit = edi::su_text(2.16352, .00481, "iucr_99");
    CHECK_MESSAGE(standard.value == "2.164" && standard.su == "0.005" && standard.bracket == "5",
                  "The default GUI cells share the file's rounded value and standard uncertainty");
    CHECK_MESSAGE(
        two_digit.value == "2.1635" && two_digit.su == "0.0049" && two_digit.bracket == "49",
        "The two-digit GUI cells share the file's selected alternative rule");
#else
    FAIL_CHECK("The planned core standard-uncertainty display formatter must exist");
#endif
}

TEST_CASE("Written correlation text follows magnitude-dependent significant figures") {
#ifdef HAS_SU_DISPLAY
    for (const auto& [value, expected] :
         std::array<std::pair<double, const char*>, 5>{{{.9449, "0.94"},
                                                        {.9512, "0.951"},
                                                        {-.0234, "-0.023"},
                                                        {1.0, "1.00"},
                                                        {-.99987, "-1.00"}}}) {
        CHECK_MESSAGE(
            edi::correlation_text(value) == expected,
            "Report correlation text must follow the independent IUCr significant figures");
    }
#else
    FAIL_CHECK("The planned core correlation text formatter must exist");
#endif
}
