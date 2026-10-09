#include <doctest/doctest.h>

#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "edi/model.hpp"
namespace {
using Values = std::vector<double>;
template <class Cell>
void measured(Cell& cell) {
    if constexpr (requires(Cell& a, const Cell& b, const Values& v) {
                      a = {1, 2.5};
                      a = {};
                      a == v;
                      v != a;
                      a == b;
                      a != b;
                  }) {
        const Values expected{1, 2.5};
        cell = {1, 2.5};
        CHECK_MESSAGE(static_cast<const Values&>(cell) == expected,
                      " F20 mixed numeric lists retain the vector's actual values");
        CHECK_MESSAGE((cell == expected && !(expected != cell)),
                      " F20 measured-vector equality retains its standard value meaning");
        Cell other;
        other = expected;
        CHECK_MESSAGE(
            (cell == other && !(cell != other)),
            " F20 measured-member equality observes values, not wrapper identity");
        other = Values{9.25};
        CHECK_MESSAGE((cell != other && !(cell == other)),
                      " F20 distinct measured values still compare unequal");
        cell = {};
        CHECK_MESSAGE(static_cast<const Values&>(cell).empty(),
                      " F20 the preserved empty braced assignment still clears a vector");
    } else
        CHECK_MESSAGE(false,
                      " F20 all preserved vector value expressions must be spellable");
}
template <class Axis>
void axis(Axis& cell) {
    using Optional = std::optional<Values>;
    if constexpr (requires(Axis& a, const Axis& b, const Optional& o, const Values& v) {
                      a == o;
                      o != a;
                      a == v;
                      v != a;
                      a == b;
                      a != b;
                  }) {
        const Values expected{12.5, 18.75};
        cell = expected;
        CHECK_MESSAGE((cell == Optional{expected} && !(Optional{expected} != cell) &&
                       cell == expected && !(expected != cell)),
                      " F20 both optional and plain vector operands retain axis equality");
        Axis other;
        other = expected;
        CHECK_MESSAGE((cell == other && !(cell != other)),
                      " F20 equal engaged axes compare their values");
        cell.reset();
        CHECK_MESSAGE((cell == Optional{} && cell != other),
                      " F20 axis equality retains absence and engagement semantics");
    } else
        CHECK_MESSAGE(false, " F20 every former optional axis equality remains spellable");
}
template <class Text>
void text(Text& cell) {
    if constexpr (requires(Text& a, const Text& b) {
                      a.begin();
                      a.end();
                      a.cbegin();
                      a.cend();
                      a.at(0);
                      a.front();
                      a.back();
                      a.find("ab", 1);
                      a < std::string("dab");
                      std::string("dab") > a;
                      a <= b;
                      a >= b;
                  }) {
        cell = "cab";
        CHECK_MESSAGE((std::string(cell.begin(), cell.end()) == "cab" &&
                       std::string(cell.cbegin(), cell.cend()) == "cab" && cell.at(0) == 'c' &&
                       cell.front() == 'c' && cell.back() == 'b' && cell.find("ab", 1) == 1),
                      " F20 preserved string reads retain their actual character values");
        Text other;
        other = "dab";
        CHECK_MESSAGE(
            (cell < std::string("dab") && std::string("dab") > cell && cell <= other &&
             !(cell >= other)),
            " F20 preserved string ordering retains standard lexicographic order");
    } else
        CHECK_MESSAGE(false,
                      " F20 each retyped plain string keeps all its const value reads");
}
template <class Cell, class Value>
void ordered(Cell& cell, const Value& low, const Value& high) {
    if constexpr (requires(Cell& a, const Cell& b, const Value& v) {
                      a < v;
                      v > a;
                      a <= b;
                      a >= b;
                  }) {
        cell = low;
        Cell other;
        other = high;
        const bool expected = low < high;
        CHECK_MESSAGE(
            (cell < high) == expected,
            " F20 aggregate ordering follows the former standard-container value");
        CHECK_MESSAGE((high > cell) == expected,
                      " F20 reversed aggregate operands retain their ordering meaning");
        CHECK_MESSAGE((cell <= other) == (low <= high),
                      " F20 aggregate wrapper ordering retains the standard <= relation");
        CHECK_MESSAGE((cell >= other) == (low >= high),
                      " F20 aggregate wrapper ordering retains the standard >= relation");
    } else
        CHECK_MESSAGE(false,
                      " F20 all former aggregate ordering expressions remain spellable");
}
}  // namespace
TEST_CASE("C34-T28 F20 preserved measured expressions retain values and equality") {
    edi::PdDataBase data;
    measured(data.intensity_meas);
    measured(data.intensity_meas_su);
    axis(data.two_theta);
    axis(data.time_of_flight);
}
TEST_CASE("C34-T28 F20 preserved plain string expressions retain reads and ordering") {
    edi::AtomSite site;
    text(site.wyckoff_letter);
    edi::SequentialExtractRule rule;
    text(rule.target);
    text(rule.pattern);
    edi::ItemVec<edi::AtomSite> sites;
    sites.push_back(site);
    text(sites[0]->wyckoff_letter);
    edi::ItemVec<edi::SequentialExtractRule> rules;
    rules.push_back(rule);
    text(rules[0]->target);
    text(rules[0]->pattern);
}
TEST_CASE("C34-T28 F20 preserved aggregate comparisons retain standard value order") {
    edi::Structure structure;
    ordered(structure.scattering_lengths_fm, std::map<std::string, double>{{"Al", 3.449}},
            std::map<std::string, double>{{"Si", 4.1491}});
    edi::ExperimentBase experiment;
    const std::vector<std::pair<double, double>> low{{1.25, 4.5}}, high{{2.5, 4.5}};
    experiment.excluded_regions = edi::excluded_region_rows(low);
    auto other = edi::excluded_region_rows(high);
    CHECK_MESSAGE(edi::excluded_region_ranges(experiment.excluded_regions) == low,
                  " F20 keyed exclusion bounds retain their independently supplied values");
    CHECK_MESSAGE(edi::excluded_region_ranges(other) == high,
                  " F20 a second keyed table retains its distinct bounds");
    const auto actual_low = edi::excluded_region_ranges(experiment.excluded_regions);
    const auto actual_high = edi::excluded_region_ranges(other);
    CHECK_MESSAGE((actual_low < actual_high) == (low < high),
                  " F20 bounds snapshots retain the former standard pair-vector < relation");
    CHECK_MESSAGE((actual_high > actual_low) == (high > low),
                  " F20 reversed bounds snapshot operands retain the > relation");
    CHECK_MESSAGE((actual_low <= actual_high) == (low <= high),
                  " F20 bounds snapshots retain the standard <= relation");
    CHECK_MESSAGE((actual_low >= actual_high) == (low >= high),
                  " F20 bounds snapshots retain the standard >= relation");
    edi::CarriedLoop carried;
    ordered(carried.columns, std::vector<std::string>{"a"}, std::vector<std::string>{"z"});
    ordered(carried.rows, std::vector<std::vector<std::string>>{{"a"}},
            std::vector<std::vector<std::string>>{{"z"}});
}
