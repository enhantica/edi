#include <doctest/doctest.h>
#include <limits>
#include <string>
#include <utility>
#include <vector>

#if __has_include("edi/correlation_matrix.hpp")
#include "edi/correlation_matrix.hpp"
#define HAS_CORRELATION_FILTER 1

// A test-owned argument type makes API availability an ordinary red assertion on
// the old core, rather than an unrelated compiler failure during red-first replay.
namespace edi {
struct ReferenceStrengths : std::vector<double> { using std::vector<double>::vector; };
struct ReferenceExperimentNames : std::vector<std::string> { using std::vector<std::string>::vector; };
}
namespace {
template <class Strengths>
void check_default_level(const Strengths& strengths) {
    if constexpr (requires { correlation_default_level(strengths); }) {
        const auto level = correlation_default_level(strengths);
        REQUIRE_MESSAGE(level.has_value(),
                        "The independent pair fixture has an automatic threshold keeping at most five");
        CHECK_MESSAGE(*level == doctest::Approx(.95),
                      "The shared automatic filter selects the lowest coefficient keeping four complete identities");
        CHECK_MESSAGE(correlation_default_level(Strengths{.9, .9, .9, .3}) == 0,
                      "With at most five identities the automatic filter includes every parameter");
        CHECK_MESSAGE(!correlation_default_level(Strengths{.9, .9, .9, .9, .9, .9}),
                      "When every threshold keeps more than five the automatic API requests the stable top-five fallback");
    } else {
        FAIL_CHECK("The shared core must expose the amendment's automatic correlation threshold");
    }
}
template <class Names>
void check_experiment_prefixes(const Names& names) {
    if constexpr (requires { other_experiment_prefixes(names, 0); }) {
        CHECK_MESSAGE((other_experiment_prefixes(names, 0) ==
                       std::vector<std::string>{"bank_extra.", "bank2."}),
                      "A joint-fit report excludes the other experiments by full datablock prefix");
        CHECK_MESSAGE((other_experiment_prefixes(names, 1) ==
                       std::vector<std::string>{"bank.", "bank2."}),
                      "Changing the shown experiment changes exactly the other experiment prefixes");
        CHECK_MESSAGE(other_experiment_prefixes(Names{"bank"}, 0).empty(),
                      "A single experiment retains every global and experiment parameter identity");
    } else {
        FAIL_CHECK("The report and Analysis tab must share the shown-experiment prefix rule");
    }
}
}
#endif

TEST_CASE("Report automatic correlation level preserves complete threshold ties") {
#ifdef HAS_CORRELATION_FILTER
    check_default_level(edi::ReferenceStrengths{.99, .99, .95, .95, .90, .90});
#else
    FAIL_CHECK("The report and Analysis tab must share the core correlation filter");
#endif
}

TEST_CASE("Report correlation context leaves global and shown-experiment identities") {
#ifdef HAS_CORRELATION_FILTER
    check_experiment_prefixes(edi::ReferenceExperimentNames{"bank", "bank_extra", "bank2"});
#else
    FAIL_CHECK("The report and Analysis tab must share the core correlation filter");
#endif
}

TEST_CASE("Report count chooses the lowest threshold within the requested count") {
#ifdef HAS_CORRELATION_FILTER
    const std::vector<double> pairs{.99, .99, .95, .95, .90, .90};
    // Before: the count-th strength cut the .90 pair and then truncated it.
    // Amendment 4: count five chooses .95, retaining four complete identities.
    for (const auto& [count, expected] :
         std::vector<std::pair<std::size_t, double>>{{5, .95}, {2, .99}, {1, .99}}) {
        CHECK_MESSAGE(edi::correlation_level_for_count(pairs, count) == doctest::Approx(expected),
                      "The pair fixture uses the hand-derived lowest threshold, never a split tie");
    }
#else
    FAIL_CHECK("The report and Analysis tab must share the core correlation filter");
#endif
}

TEST_CASE("Report count keeps an unavoidable clique tie whole") {
#ifdef HAS_CORRELATION_FILTER
    const std::vector<double> clique{.9, .9, .9, .3};
    const double level = edi::correlation_level_for_count(clique, 2);
    CHECK_MESSAGE(level == doctest::Approx(.9),
                  "A requested count of two selects the independently declared three-way clique threshold");
    CHECK_MESSAGE(edi::correlation_count_for_level(clique, level) == 3,
                  "An unavoidable correlation tie keeps all three identities rather than truncating to two");
    CHECK_MESSAGE(edi::correlation_level_for_count({}, 5) == 0,
                  "An empty strength vector has a finite neutral threshold");
#else
    FAIL_CHECK("The report and Analysis tab must share the core correlation filter");
#endif
}

TEST_CASE("Report threshold selects five of fifty-three independent identities") {
#ifdef HAS_CORRELATION_FILTER
    edi::CorrelationMatrix matrix;
    for (int i = 0; i < 53; ++i) matrix.names.push_back("parameter_" + std::to_string(i));
    matrix.values.assign(53 * 53, .1);
    for (int i = 0; i < 53; ++i) {
        matrix.values[i * 53 + i] = std::numeric_limits<double>::quiet_NaN();
        for (int j = 0; j < i; ++j) {
            const double value = i < 5 ? .54 : .1;
            matrix.values[i * 53 + j] = matrix.values[j * 53 + i] = value;
        }
    }
    const auto selected = edi::correlation_matrix(matrix, .54, 53);
    CHECK_MESSAGE((selected.labels == std::vector<std::string>{"parameter_0", "parameter_1",
                   "parameter_2", "parameter_3", "parameter_4"}),
                  "The hand-declared 0.54 clique keeps exactly five of fifty-three in input order");
    REQUIRE_MESSAGE(selected.values.size() == 25,
                    "The filtered correlation matrix has one cell for every selected identity pair");
    for (std::size_t i = 0; i < 5; ++i) for (std::size_t j = 0; j < i; ++j)
        CHECK_MESSAGE(selected.values[i * 5 + j] == .54,
                      "The selected lower triangle retains each independently declared boundary coefficient");
#else
    FAIL_CHECK("The report and Analysis tab must share the core correlation filter");
#endif
}
