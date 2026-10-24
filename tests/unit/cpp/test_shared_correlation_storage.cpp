#include <doctest/doctest.h>

#include <cmath>
#include <memory>
#include <type_traits>

#include "edi/io.hpp"

namespace {
template <typename Record>
auto chosen_table() {
    using Map = decltype(std::declval<Record>().scan_results);
    using Bundle = typename Map::mapped_type::element_type;
    using Pointer = decltype(std::declval<Bundle>().correlations);
    auto result = std::make_shared<std::remove_const_t<typename Pointer::element_type>>();
    result->names = std::make_shared<const std::vector<std::string>>(std::vector<std::string>{
        "bank.background.base.coef", "bank.background.ramp.coef", "bank.background.curve.coef",
        "bank.instrument.setup_wavelength"});
    result->values = std::make_shared<const std::vector<double>>(
        std::vector<double>{.5, -1., -.84016805041680576, .125, .05, -.12345678901234566});
    return Pointer(result);
}
template <typename Record, typename TablePointer>
auto bundle(TablePointer table) {
    using Map = decltype(std::declval<Record>().scan_results);
    using Pointer = typename Map::mapped_type;
    auto result = std::make_shared<std::remove_const_t<typename Pointer::element_type>>();
    result->correlations = std::move(table);
    return Pointer(result);
}
}  // namespace

template <typename Record>
void storage_case_0() {
    if constexpr (requires(Record& record) { record.scan_results; }) {
        const auto table = chosen_table<Record>();
        const auto rows = correlation_rows(*table, "template.xy");
        REQUIRE_MESSAGE(rows.size() == 6,
                        "Four free columns must expose six ordered off-diagonal pairs");
        const std::vector<double> expected{.5,   -1., -.84016805041680576,
                                           .125, .05, -.12345678901234566};
        std::size_t k = 0;
        for (std::size_t i = 0; i < 4; ++i) {
            for (std::size_t j = i + 1; j < 4; ++j, ++k) {
                CAPTURE(i);
                CAPTURE(j);
                CAPTURE(k);
                CHECK_MESSAGE(rows[k].id.value() == std::to_string(k + 1),
                              "New rows must enumerate the packed upper triangle without "
                              "renumbering by names");
                CHECK_MESSAGE(rows[k].source_kind.value() == "deterministic",
                              "Computed covariance rows must identify their deterministic source");
                CHECK_MESSAGE(rows[k].parameter_unique_name_i.value() == table->names->at(i),
                              "The first endpoint must follow the free column order");
                CHECK_MESSAGE(rows[k].parameter_unique_name_j.value() == table->names->at(j),
                              "The second endpoint must follow the free column order");
                CHECK_MESSAGE(rows[k].correlation.value() == expected[k],
                              "Numeric rows must retain a clamped end and the "
                              "17-digit witness");
                CHECK_MESSAGE(rows[k].file_path.value() == "template.xy",
                              "Making rows must retain the selected dataset's identity");
            }
        }

    } else {
        REQUIRE_MESSAGE(false, "Fit records must expose their immutable per-file result bundles");
    }
}
TEST_CASE("Shared numeric tables preserve upper-triangle ids and shortest text") {
    storage_case_0<edi::FitResultRecord>();
}

template <typename Record>
void storage_case_1() {
    if constexpr (requires(Record& record) { record.scan_results; }) {
        const auto table = chosen_table<Record>();
        const auto first = bundle<Record>(table);
        const auto second = bundle<Record>(table);
        Record record;
        adopt_scan_file_result(record, "other.xy", first, "template.xy");
        CHECK_MESSAGE(record.correlations.empty(),
                      "A non-template event must not populate the saved loop");
        adopt_scan_file_result(record, "template.xy", second, "template.xy");
        REQUIRE_MESSAGE(record.scan_results.size() == 2,
                        "Each completed file must keep its own live result bundle");
        CHECK_MESSAGE(record.scan_results.at("other.xy") == first,
                      "Appending the template must not rebuild a previous file's bundle");
        CHECK_MESSAGE(record.correlations.size() == 6,
                      "The saved loop must contain precisely the template's own six pairs");
        auto copy = record;
        for (const auto& [file, result] : record.scan_results) {
            CHECK_MESSAGE(copy.scan_results.at(file) == result,
                          "Copying a fit record must copy bundle pointers rather than tables or "
                          "coefficients");
            CHECK_MESSAGE(copy.scan_results.at(file)->correlations == table,
                          "The copied bundle must retain the exact published table pointer");
        }
        CHECK_MESSAGE(
            (std::is_const_v<typename decltype(first)::element_type>),
            "Published bundles must forbid in-place mutation through their pointer type");
        CHECK_MESSAGE((std::is_const_v<typename decltype(first->correlations)::element_type>),
                      "Published tables must forbid in-place mutation through their pointer type");
        CHECK_MESSAGE((std::is_const_v<typename decltype(table->names)::element_type> &&
                       std::is_const_v<typename decltype(table->values)::element_type>),
                      "Published names and coefficients must each be immutable");
        record.scan_results.clear();
        CHECK_MESSAGE(
            copy.scan_results.at("template.xy") == second,
            "Clearing the current map must retain the Undo snapshot's original pointers");
        CHECK_MESSAGE(
            (*table->values ==
             std::vector<double>{.5, -1., -.84016805041680576, .125, .05, -.12345678901234566}),
            "Copying and clearing a record must never alter a retained table's coefficients");

    } else {
        REQUIRE_MESSAGE(false, "Fit records must expose their immutable per-file result bundles");
    }
}
TEST_CASE("Fit record copies retain immutable result pointers and only template rows") {
    storage_case_1<edi::FitResultRecord>();
}

template <typename Record>
void storage_case_2() {
    if constexpr (requires(Record& record) { record.scan_results; }) {
        Record record;
        edi::FitParameterCorrelation row;
        row.id = "pair17";
        row.source_kind = "deterministic";
        row.parameter_unique_name_i = "bank.background.base.coef";
        row.parameter_unique_name_j = "bank.background.ramp.coef";
        row.correlation = 0.50;
        row.file_path = "template.xy";
        record.correlations.push_back(row);
        adopt_scan_file_result(record, "other.xy", bundle<Record>(chosen_table<Record>()),
                               "template.xy");
        REQUIRE_MESSAGE(record.correlations.size() == 1,
                        "Another file's new fit must not replace the loaded template's rows");
        CHECK_MESSAGE(
            (record.correlations[0]->id.value() == "pair17" &&
             record.correlations[0]->correlation.value() == 0.50),
            "A loaded nonordinal identity and numeric coefficient survive unrelated live results");
        CHECK_MESSAGE(record.correlations[0]->correlation.value() == .5,
                      "The numeric view must retain the loaded coefficient as one half");

    } else {
        REQUIRE_MESSAGE(false, "Fit records must expose their immutable per-file result bundles");
    }
}
TEST_CASE("An unrelated scan event preserves literal loaded pair identity and spelling") {
    storage_case_2<edi::FitResultRecord>();
}
