#include <doctest/doctest.h>

#include <filesystem>
#include <fstream>
#include <map>
#include <string>

#include "../../fixtures/c34_t28_baseline/stamp_routes.hpp"

namespace {
void check_stamp_partition(const c34_t28_baseline::Measurements& actual, int part) {
    const auto path = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
                      "fixtures/c34_t28_baseline/stamps.tsv";
    std::ifstream input(path);
    REQUIRE_MESSAGE(input.good(),
                    " I23 the independent pre-move stamp fixture must resolve");
    std::map<std::string, c34_t28_baseline::Flags> expected;
    std::string name;
    bool a, b, c;
    while (input >> name >> a >> b >> c) {
        const bool dependant = name.starts_with("plain-dependants/");
        if ((part == 0 && !dependant) || (part == 1 && dependant && name.ends_with("-equal")) ||
            (part == 2 && dependant && name.ends_with("-changed"))) {
            expected.emplace(name, c34_t28_baseline::Flags{a, b, c});
        }
    }
    // F25 deliberately closes the draining-text renewal defect. The measured
    // historical fixture stays immutable; every other route retains its pin.
    if (part == 0) {
        REQUIRE_MESSAGE(expected.contains("written-text/move-source"),
                        " F25 the retained source-move route must still be present");
        REQUIRE_MESSAGE(
            (expected.at("written-text/move-source") ==
             c34_t28_baseline::Flags{false, false, false}),
            " F25 the independent reference records the superseded unstamped move");
        expected.at("written-text/move-source") = {true, false, false};
    }
    REQUIRE_MESSAGE(input.eof(), " I23 malformed baseline stamp rows cannot silently pass");
    REQUIRE_MESSAGE(actual.size() == expected.size(),
                    " I23 every pre-move write route remains exercised");
    for (const auto& [route, flags] : actual) {
        INFO(route);
        REQUIRE_MESSAGE(expected.contains(route),
                        " I23 a route needs a pre-move reference");
        CHECK_MESSAGE(flags == expected.at(route),
                      " I23/F25 every route retains its pin except the required "
                      "draining-source renewal");
    }
}
}  // namespace

TEST_CASE("C34-T28 native write routes retain their measured pre-move stamps") {
    check_stamp_partition(c34_t28_baseline::capture(false), 0);
}
TEST_CASE("C34-T28 equal plain writes retain their pre-move dependent stamps") {
    c34_t28_baseline::Measurements actual;
    c34_t28_baseline::capture_plain_dependants(actual, 0, 2);
    check_stamp_partition(actual, 1);
}
TEST_CASE("C34-T28 changed plain writes retain their pre-move dependent stamps") {
    c34_t28_baseline::Measurements actual;
    c34_t28_baseline::capture_plain_dependants(actual, 1, 2);
    check_stamp_partition(actual, 2);
}
