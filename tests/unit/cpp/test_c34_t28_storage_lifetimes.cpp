#include <doctest/doctest.h>

#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

#include "edi/model.hpp"

namespace {
using Values = std::vector<double>;
template <class Node>
void empty_reads(std::type_identity<Node>) {
    for (int route = 0; route != 4; ++route) {
        INFO(route);
        Node node, donor;
        if (route == 1) node = donor;
        if (route == 2) {
            Node moved(std::move(node));
            (void)moved;
        }
        const Values& measured = node.intensity_meas;
        const Values& sigma = node.intensity_meas_su;
        donor.intensity_meas = Values{31.25, 47.5};
        donor.intensity_meas_su = Values{0.125, 0.375};
        if (route == 3)
            node = donor;
        else {
            node.intensity_meas = Values{31.25, 47.5};
            node.intensity_meas_su = Values{0.125, 0.375};
        }
        CHECK_MESSAGE(&measured == &static_cast<const Values&>(node.intensity_meas),
                      " F17 first publication retains the empty measured vector object");
        CHECK_MESSAGE(&sigma == &static_cast<const Values&>(node.intensity_meas_su),
                      " F17 first publication retains the empty sigma vector object");
        CHECK_MESSAGE((measured == Values{31.25, 47.5} && sigma == Values{0.125, 0.375}),
                      " F17 empty and moved-from native reads observe their first write");
    }
    for (bool tof : {false, true}) {
        Node node;
        if (tof)
            node.time_of_flight.emplace();
        else
            node.two_theta.emplace();
        const Values& axis = node.axis();
        if (tof)
            node.write_axis(&edi::PdDataBase::time_of_flight, Values{2100.5, 3300.75});
        else
            node.write_axis(&edi::PdDataBase::two_theta, Values{12.5, 18.75});
        CHECK_MESSAGE(&axis == &node.axis(),
                      " F17 a default-engaged axis retains its own vector on first write");
        CHECK_MESSAGE((axis == (tof ? Values{2100.5, 3300.75} : Values{12.5, 18.75})),
                      " F17 both initially empty native axes observe their first write");
    }
    // The source vector object belongs to the source node even after a move.
    // Compare addresses before any dereference so an old dangling read is a
    // named red, never a crash that prevents the rest of the family sweep.
    for (bool tof : {false, true})
        for (bool assignment : {false, true}) {
            Node source, target;
            source.intensity_meas = Values{31.25, 47.5};
            source.intensity_meas_su = Values{0.125, 0.375};
            target.intensity_meas = Values{9.25};
            target.intensity_meas_su = Values{0.75};
            if (tof) {
                source.time_of_flight = Values{2100.5};
                target.time_of_flight = Values{4400.75};
            } else {
                source.two_theta = Values{12.5};
                target.two_theta = Values{21.75};
            }
            const Values* measured = &static_cast<const Values&>(source.intensity_meas);
            const Values* sigma = &static_cast<const Values&>(source.intensity_meas_su);
            const Values* axis = &source.axis();
            const Values* target_measured = &static_cast<const Values&>(target.intensity_meas);
            const Values* target_sigma = &static_cast<const Values&>(target.intensity_meas_su);
            const Values* target_axis = &target.axis();
            std::optional<Node> moved;
            if (assignment)
                target = std::move(source);
            else
                moved.emplace(std::move(source));
            CHECK_MESSAGE(
                measured == &static_cast<const Values&>(source.intensity_meas),
                " F17 each moved source retains its native measured vector object");
            CHECK_MESSAGE(sigma == &static_cast<const Values&>(source.intensity_meas_su),
                          " F17 each moved source retains its native sigma vector object");
            CHECK_MESSAGE(
                axis == &source.axis(),
                " F17 each still-engaged moved source retains its native axis object");
            if (assignment) {
                CHECK_MESSAGE(
                    (target_measured == &static_cast<const Values&>(target.intensity_meas) &&
                     target_sigma == &static_cast<const Values&>(target.intensity_meas_su) &&
                     target_axis == &target.axis()),
                    " F17 every moved target also keeps its prior native vector objects");
            }
            source.intensity_meas = Values{71.75};
            source.intensity_meas_su = Values{1.375};
            if (tof)
                source.time_of_flight = Values{5500.5};
            else
                source.two_theta = Values{31.25};
            if (measured == &static_cast<const Values&>(source.intensity_meas))
                CHECK_MESSAGE((*measured == Values{71.75}),
                              " F17 held source reads observe source reuse");
            if (sigma == &static_cast<const Values&>(source.intensity_meas_su))
                CHECK_MESSAGE((*sigma == Values{1.375}),
                              " F17 held sigma reads observe source reuse");
            if (axis == &source.axis())
                CHECK_MESSAGE((*axis == (tof ? Values{5500.5} : Values{31.25})),
                              " F17 held axis reads observe source reuse");
            const Node& destination = assignment ? target : *moved;
            CHECK_MESSAGE(
                (static_cast<const Values&>(destination.intensity_meas) == Values{31.25, 47.5} &&
                 static_cast<const Values&>(destination.intensity_meas_su) ==
                     Values{0.125, 0.375}),
                " F17 source reuse never changes the moved destination's values");
        }
}

template <class Field>
decltype(auto) read(Field& field) {
    if constexpr (requires { field.get(); })
        return field.get();
    else
        return field.value();
}
template <class Value>
Value changed(const Value& value) {
    if constexpr (std::is_same_v<Value, std::string>)
        return value + "-written";
    else if constexpr (std::is_same_v<Value, std::optional<double>>)
        return 0.375;
    else if constexpr (std::is_same_v<Value, bool>)
        return !value;
    else
        return static_cast<Value>(value + 2);
}
template <class Field>
void retain(Field& field, std::vector<std::function<void()>>& checks) {
    if constexpr (std::is_same_v<Field, edi::Parameter>) {
        retain(field.value, checks);
        retain(field.uncertainty, checks);
        retain(field.free, checks);
        retain(field.start_value, checks);
        retain(field.start_uncertainty, checks);
    } else {
        const auto* held = &read(field);
        checks.emplace_back([&field, held] {
            const auto* current = &read(field);
            CHECK_MESSAGE(
                held == current,
                " F17 every returned cell reference follows its held item lifetime");
            // A red reference may already dangle. Never dereference it unless
            // the address control proves it still names this item's live cell.
            if (held != current) return;
            const auto next = changed(*current);
            field = next;
            CHECK_MESSAGE(
                *held == next,
                " F17 the held item reference observes its detached native write");
        });
    }
}
template <class Row>
void item_lifetimes(std::type_identity<Row>) {
    using Rows = edi::ItemVec<Row>;
    for (bool before_attach : {false, true})
        for (int route = 0; route != 7; ++route) {
            INFO(before_attach, route);
            auto row = std::make_shared<Row>();
            auto rows = std::make_unique<Rows>();
            std::vector<std::function<void()>> checks;
            auto hold = [&] {
                std::apply([&](auto... member) { (retain(row.get()->*member, checks), ...); },
                           crysta::RowSchema<Row>::fields);
            };
            if (before_attach) hold();
            rows->push_back(row);
            if (!before_attach) hold();
            // Ordinary growth and removal of a different row are positive lifetime controls.
            auto other = std::make_shared<Row>();
            if constexpr (edi::KeyedItem<Row>) edi::KeyTraits<Row>::key(*other) = "other-row";
            rows->push_back(other);
            for (auto& check : checks) check();
            rows->erase_at(1);
            for (auto& check : checks) check();
            auto replacement = std::make_shared<Row>();
            if constexpr (edi::KeyedItem<Row>)
                edi::KeyTraits<Row>::key(*replacement) = "replacement";
            switch (route) {
                case 0:
                    rows->erase_at(0);
                    rows->push_back(replacement);
                    break;
                case 1:
                    rows->clear();
                    rows->push_back(replacement);
                    break;
                case 2:
                    rows->assign({replacement});
                    break;
                case 3:
                    rows->replace_at(0, replacement);
                    break;
                case 4: {
                    Rows donor({replacement});
                    *rows = donor;
                    break;
                }
                case 5: {
                    Rows donor({replacement});
                    *rows = std::move(donor);
                    break;
                }
                case 6:
                    rows.reset();
                    break;
            }
            for (auto& check : checks) check();
        }
}
}  // namespace
TEST_CASE("C34-T28 F17 base empty measured references retain their first publication") {
    empty_reads(std::type_identity<edi::PdDataBase>{});
}
TEST_CASE("C34-T28 F17 CW empty measured references retain their first publication") {
    empty_reads(std::type_identity<edi::PdCwlData>{});
}
TEST_CASE("C34-T28 F17 TOF empty measured references retain their first publication") {
    empty_reads(std::type_identity<edi::PdTofData>{});
}
TEST_CASE("C34-T28 F17 atom native references follow held items across removal") {
    item_lifetimes(std::type_identity<edi::AtomSite>{});
}
TEST_CASE("C34-T28 F17 texture native references follow held items across removal") {
    item_lifetimes(std::type_identity<edi::PrefOrient>{});
}
TEST_CASE("C34-T28 F17 background native references follow held items across removal") {
    item_lifetimes(std::type_identity<edi::LineSegment>{});
}
TEST_CASE("C34-T28 F17 extract native references follow held items across removal") {
    item_lifetimes(std::type_identity<edi::SequentialExtractRule>{});
}
TEST_CASE("C34-T28 F17 structure native references follow held items across removal") {
    item_lifetimes(std::type_identity<edi::Structure>{});
}
TEST_CASE("C34-T28 F17 experiment native references follow held items across removal") {
    item_lifetimes(std::type_identity<edi::BraggPdExperiment>{});
}
