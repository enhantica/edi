#include <doctest/doctest.h>

#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

#include "edi/model.hpp"

namespace {
std::string encoding(const auto& cell) {
    std::string out;
    edi::detail::encode_cell(out, cell);
    return out;
}
template <class Cell, class Value, class Generation>
void drain(Cell& source, const Value& supplied, Generation generation, bool assignment) {
    source = supplied;
    const auto before = source.written();
    const auto encoded = encoding(source);
    const auto category = generation();
    Cell destination;
    std::optional<Cell> constructed;
    if (assignment)
        destination = std::move(source);
    else
        constructed.emplace(std::move(source));
    const auto& read = [&]() -> const Value& {
        if constexpr (requires { source.get(); })
            return source.get();
        else
            return source.value();
    }();
    // A cell view may preserve a bound source by copying its value. A move
    // that actually drains it is a write: the observation, its cell clock and
    // the owning category must then all change together. The immutable
    // pre-repair replay reaches the draining branch for every family below.
    if (read != supplied) {
        CHECK_MESSAGE(source.written() > before,
                      " F25 a draining source move renews the source cell identity");
        CHECK_MESSAGE(encoding(source) != encoded,
                      " F25 a draining source cannot retain its generation encoding");
        CHECK_MESSAGE(generation() != category,
                      " F25 source renewal reaches its live category generation");
    }
    const Cell& received = assignment ? destination : *constructed;
    if constexpr (requires { received.get(); })
        CHECK_MESSAGE(received.get() == supplied,
                      " F25 the destination receives the independently supplied values");
    else
        CHECK_MESSAGE(received.value() == supplied,
                      " F25 the destination receives the independently supplied text");
    if constexpr (requires { source.table().rows(); }) {
        CHECK_MESSAGE(source.table().rows() == read.size(),
                      " F25 the moved source aggregate table agrees with its read values");
        CHECK_MESSAGE(received.table().rows() == supplied.size(),
                      " F25 the destination aggregate keeps every supplied table row");
    }
}
template <class R, class Member>
void bound_text(std::type_identity<R>, Member member) {
    for (bool assignment : {false, true}) {
        auto row = std::make_shared<R>();
        edi::ItemVec<R> rows;
        rows.push_back(row);
        auto& cell = row.get()->*member;
        drain(cell, std::string(97, 'X'), [&] { return rows.category_stamp(); }, assignment);
        CHECK_MESSAGE(cell.bound(),
                      " F25 moving a field preserves its source row attachment");
    }
}
void standalone(auto& cell, const auto& supplied) {
    for (bool assignment : {false, true})
        drain(cell, supplied, [&] { return encoding(cell); }, assignment);
}
}  // namespace

TEST_CASE("C34-T28 F25 every bound text source renews on move construction and assignment") {
    bound_text(std::type_identity<edi::AtomSite>{}, &edi::AtomSite::type_symbol);
    bound_text(std::type_identity<edi::AtomSite>{}, &edi::AtomSite::wyckoff_letter);
    bound_text(std::type_identity<edi::AtomSite>{}, &edi::AtomSite::adp_type);
    bound_text(std::type_identity<edi::SequentialExtractRule>{},
               &edi::SequentialExtractRule::target);
    bound_text(std::type_identity<edi::SequentialExtractRule>{},
               &edi::SequentialExtractRule::pattern);
}
TEST_CASE("C34-T28 F25 standalone text moves renew the public space-group table") {
    for (auto member : {&edi::SpaceGroup::name_h_m, &edi::SpaceGroup::coord_system_code})
        for (bool assignment : {false, true}) {
            edi::SpaceGroup owner;
            edi::OneRow<edi::SpaceGroupCategory> table(owner);
            drain(
                owner.*member, std::string(97, 'Y'), [&] { return table.generation(); },
                assignment);
        }
}
TEST_CASE("C34-T28 F25 both measured vectors and axes renew their drained sources") {
    edi::PdDataBase owner;
    const std::vector<double> supplied{31.25, 47.5};
    standalone(owner.intensity_meas, supplied);
    standalone(owner.intensity_meas_su, supplied);
    const std::optional<std::vector<double>> axis{supplied};
    standalone(owner.two_theta, axis);
    standalone(owner.time_of_flight, axis);
}
TEST_CASE("C34-T28 F25 every aggregate family renews source identity and moves its table") {
    edi::Structure structure;
    standalone(structure.scattering_lengths_fm, std::map<std::string, double>{{"Si", 4.1491}});
    edi::BraggPdExperiment experiment;
    standalone(experiment.excluded_regions, std::vector<std::pair<double, double>>{{1.25, 4.5}});
    edi::CarriedLoop carried;
    standalone(carried.columns, std::vector<std::string>{"h", "k"});
    standalone(carried.rows, std::vector<std::vector<std::string>>{{"1", "2"}, {"3", "4"}});
}
TEST_CASE("C34-T28 F25 throwing emplacement renews both axes and public optional containers") {
    auto attempt = [](auto& cell) {
        using Value = std::remove_cvref_t<decltype(cell.value())>;
        cell.emplace(Value{typename Value::value_type{}});
        const auto before = cell.written();
        const auto encoded = encoding(cell);
        CHECK_THROWS_AS_MESSAGE(
            cell.emplace(std::numeric_limits<std::size_t>::max()), std::length_error,
            " F25 oversized native emplacement propagates length_error");
        CHECK_MESSAGE(!cell.has_value(),
                      " F25 the throwing vector constructor really disengages the axis");
        CHECK_MESSAGE(cell.written() > before,
                      " F25 throwing emplacement renews the changed optional identity");
        CHECK_MESSAGE(encoding(cell) != encoded,
                      " F25 throwing emplacement invalidates its generation encoding");
    };
    edi::PdDataBase data;
    attempt(data.two_theta);
    attempt(data.time_of_flight);
    edi::detail::Written<std::optional<std::vector<std::string>>> public_text;
    edi::detail::Written<std::optional<std::vector<int>>> public_numbers;
    attempt(public_text);
    attempt(public_numbers);
}
TEST_CASE("C34-T28 F25 native copies and whole keyed item moves preserve their source values") {
    auto source = std::make_shared<edi::AtomSite>();
    source->type_symbol = std::string(97, 'Z');
    edi::ItemVec<edi::AtomSite> rows({source});
    const auto before = rows.category_stamp();
    const auto written = source->type_symbol.written();
    const edi::detail::WrittenText copy(source->type_symbol);
    const edi::AtomSite moved(std::move(*source));
    CHECK_MESSAGE(source->type_symbol.value() == copy.value(),
                  " F25 a plain native copy does not drain its source");
    CHECK_MESSAGE(source->type_symbol.value() == moved.type_symbol.value(),
                  " F25 a whole keyed item move retains its intentional copy semantics");
    CHECK_MESSAGE((source->type_symbol.written() == written && rows.category_stamp() == before),
                  " F25 non-draining keyed copy paths retain the source generation");
}
