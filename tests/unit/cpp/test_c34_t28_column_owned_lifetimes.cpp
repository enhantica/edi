#include <doctest/doctest.h>

#include <functional>
#include <memory>
#include <string>
#include <type_traits>
#include <vector>

#include "edi/model.hpp"

struct C34StableRow {
    edi::detail::Written<double> position{1.25};
    edi::detail::WrittenText name;
    edi::Parameter scale{31.25};
};
template <>
struct crysta::RowSchema<C34StableRow> {
    static constexpr const char* name = "_stable_public_row";
    static constexpr auto fields =
        std::tuple{&C34StableRow::position, &C34StableRow::name, &C34StableRow::scale};
    static constexpr std::array items{"position", "name", "scale"};
};
template <>
struct crysta::detail::ForeignTable<C34StableRow> {
    using type = edi::ItemVec<C34StableRow>;
};
namespace {
decltype(auto) read(const auto& field) {
    if constexpr (requires { field.get(); })
        return field.get();
    else
        return field.value();
}
void retain(auto& cell, std::vector<std::function<void()>>& checks) {
    using Cell = std::remove_cvref_t<decltype(cell)>;
    if constexpr (std::is_same_v<Cell, edi::Parameter>) {
        retain(cell.value, checks);
        retain(cell.uncertainty, checks);
        retain(cell.free, checks);
        retain(cell.start_value, checks);
        retain(cell.start_uncertainty, checks);
    } else {
        const auto* pointer = &read(cell);
        checks.emplace_back([&cell, pointer] {
            const auto* actual = &read(cell);
            CHECK_MESSAGE(
                pointer == actual,
                " F17/F23 a held cell reference survives each storage transition");
            if (pointer != actual) return;  // never dereference a dangling pre-repair reference
            using Value = std::remove_cvref_t<decltype(*actual)>;
            Value next{};
            if constexpr (std::is_same_v<Value, std::string>)
                next = *actual + "-kept";
            else if constexpr (std::is_same_v<Value, std::optional<double>>)
                next = 0.375;
            else if constexpr (std::is_same_v<Value, bool>)
                next = !*actual;
            else
                next = static_cast<Value>(*actual + 1.25);
            cell = next;
            CHECK_MESSAGE(*pointer == next,
                          " F17/F23 the old reference remains valid and current on reuse");
        });
    }
}
template <class R>
void transitions(std::type_identity<R>) {
    using Rows = edi::ItemVec<R>;
    for (bool read_empty : {false, true}) {
        auto old = std::make_shared<R>();
        auto collection = std::make_unique<Rows>();
        REQUIRE_MESSAGE(collection->empty(), " F23 the first holder starts empty");
        std::vector<std::function<void()>> checks;
        auto hold = [&] {
            std::apply([&](auto... member) { (retain(old.get()->*member, checks), ...); },
                       crysta::RowSchema<R>::fields);
        };
        if (read_empty) hold();
        collection->push_back(old);
        if (!read_empty) hold();
        for (auto& check : checks) check();
        const std::string key = [&] {
            if constexpr (edi::KeyedItem<R>)
                return edi::KeyTraits<R>::key(*old).value();
            else
                return std::string{};
        }();
        collection->clear();
        CHECK_MESSAGE(collection->empty(), " F23 removing the last row empties its table");
        for (auto& check : checks) check();
        auto fresh = std::make_shared<R>();
        if constexpr (edi::KeyedItem<R>) edi::KeyTraits<R>::key(*fresh) = key;
        collection->push_back(fresh);  // the same id, a different row and different value cells
        const auto token = collection->token(0);
        const auto before = collection->category_stamp();
        for (auto& check : checks) check();
        CHECK_MESSAGE(collection->front() == fresh,
                      " F23 reused ids never alias the removed item's identity");
        CHECK_MESSAGE(
            (collection->token(0) == token && collection->category_stamp() == before),
            " F23 writes through the held detached row do not stamp the new id owner");
        collection->clear();
        collection->push_back(old);
        const auto reattached = collection->category_stamp();
        for (auto& check : checks) check();
        CHECK_MESSAGE(collection->category_stamp() > reattached,
                      " F23 re-admission observes every write to the held original row");
        collection.reset();
        for (auto& check : checks) check();
        Rows again;
        again.push_back(old);
        for (auto& check : checks) check();
        Rows moved(std::move(again));
        for (auto& check : checks) check();
        CHECK_MESSAGE(moved.front() == old,
                      " F17/F23 moving the replacement holder keeps the exact held row");
    }
}
}  // namespace
TEST_CASE("C34-T28 F23 atom cell reads survive empty detach and reused-id transitions") {
    transitions(std::type_identity<edi::AtomSite>{});
}
TEST_CASE("C34-T28 F23 background cell reads survive empty detach and reused-id transitions") {
    transitions(std::type_identity<edi::LineSegment>{});
}
TEST_CASE("C34-T28 F23 texture cell reads survive empty detach and reused-id transitions") {
    transitions(std::type_identity<edi::PrefOrient>{});
}
TEST_CASE("C34-T28 F23 extract cell reads survive empty detach and reused-id transitions") {
    transitions(std::type_identity<edi::SequentialExtractRule>{});
}
TEST_CASE("C34-T28 F23 structure cell reads survive empty detach and reused-id transitions") {
    transitions(std::type_identity<edi::Structure>{});
}
TEST_CASE("C34-T28 F23 experiment cell reads survive empty detach and reused-id transitions") {
    transitions(std::type_identity<edi::BraggPdExperiment>{});
}
TEST_CASE("C34-T28 F23 public schema reads survive empty detach and repeated admission") {
    transitions(std::type_identity<C34StableRow>{});
}
