#include <doctest/doctest.h>

#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <type_traits>
#include <vector>

#include "edi/model.hpp"

struct C34ImageRow {
    edi::detail::Written<double> value{1.25};
    edi::detail::WrittenText name;
    edi::Parameter scale{31.25};
};
template <>
struct crysta::RowSchema<C34ImageRow> {
    static constexpr const char* name = "_column_image_row";
    static constexpr auto fields =
        std::tuple{&C34ImageRow::value, &C34ImageRow::name, &C34ImageRow::scale};
    static constexpr std::array items{"value", "name", "scale"};
};
template <>
struct crysta::detail::ForeignTable<C34ImageRow> {
    using type = edi::ItemVec<C34ImageRow>;
};
namespace {
decltype(auto) image(const auto& cell) {
    if constexpr (requires { cell.get(); })
        return cell.get();
    else
        return cell.value();
}
void equal_cell(const auto& cell, const auto& column, std::size_t index) {
    using Cell = std::remove_cvref_t<decltype(cell)>;
    if constexpr (std::is_same_v<Cell, edi::Parameter>) {
        equal_cell(cell.value, column.value, index);
        equal_cell(cell.uncertainty, column.uncertainty, index);
        equal_cell(cell.free, column.free, index);
        equal_cell(cell.start_value, column.start_value, index);
        equal_cell(cell.start_uncertainty, column.start_uncertainty, index);
    } else {
        using Value = std::remove_cvref_t<decltype(image(cell))>;
        using Stored = std::conditional_t<std::is_same_v<Value, bool>, std::uint8_t, Value>;
        static_assert(
            std::is_same_v<std::remove_cvref_t<decltype(column)>, crysta::Column<Stored>>,
            " I14 every schema leaf has an actual typed value column");
        CHECK_MESSAGE(column.at(index) == static_cast<Stored>(image(cell)),
                      " F23 each item image equals its stored column cell");
    }
}
void keep_buffer(const auto& column, std::vector<std::function<void()>>& checks) {
    if constexpr (requires { column.value; }) {
        keep_buffer(column.value, checks);
        keep_buffer(column.uncertainty, checks);
        keep_buffer(column.free, checks);
        keep_buffer(column.start_value, checks);
        keep_buffer(column.start_uncertainty, checks);
    } else {
        auto held = column.buffer();
        if (!held) return;
        auto before = *held;
        checks.emplace_back([held, before] {
            CHECK_MESSAGE(*held == before,
                          " I8/F23 a kept column buffer never becomes the live read image");
        });
    }
}
template <class Row>
void coherent(const edi::ItemVec<Row>& rows) {
    std::apply(
        [&](auto... member) {
            auto field = [&](auto m) {
                const auto& column = rows.column(m);
                if constexpr (requires { column.value; }) {
                    CHECK_MESSAGE(
                        (column.value.size() == rows.size() &&
                         column.uncertainty.size() == rows.size() &&
                         column.free.size() == rows.size() &&
                         column.start_value.size() == rows.size() &&
                         column.start_uncertainty.size() == rows.size()),
                        " F23 all five parameter columns track the actual row order");
                } else
                    CHECK_MESSAGE(
                        column.size() == rows.size(),
                        " F23 a typed column has exactly one value per admitted row");
                for (std::size_t i = 0; i < rows.size(); ++i)
                    equal_cell(rows[i].get()->*m, column, i);
            };
            (field(member), ...);
        },
        crysta::RowSchema<Row>::fields);
}
auto supplied(const auto& cell, unsigned sequence) {
    using Value = std::remove_cvref_t<decltype(image(cell))>;
    if constexpr (std::is_same_v<Value, std::string>)
        return "column-image-" + std::to_string(sequence);
    else if constexpr (std::is_same_v<Value, bool>)
        return !image(cell);
    else if constexpr (std::is_same_v<Value, std::optional<double>>)
        return Value{17.125 + sequence};
    else
        return static_cast<Value>(17.125 + sequence);
}
void routes(auto& cell, const auto& check, unsigned& sequence) {
    using Cell = std::remove_cvref_t<decltype(cell)>;
    if constexpr (std::is_same_v<Cell, edi::Parameter>) {
        routes(cell.value, check, sequence);
        routes(cell.uncertainty, check, sequence);
        routes(cell.free, check, sequence);
        routes(cell.start_value, check, sequence);
        routes(cell.start_uncertainty, check, sequence);
    } else {
        const auto* held = &image(cell);
        auto next = supplied(cell, ++sequence);
        cell = next;
        CHECK_MESSAGE(image(cell) == next,
                      " F23 the cell write retains the caller's supplied value");
        check();
        CHECK_MESSAGE(&image(cell) == held, " F17 a write preserves the held image object");
        Cell other;
        other = supplied(cell, ++sequence);
        cell = other;
        check();
        if constexpr (std::is_move_constructible_v<Cell> && std::is_move_assignable_v<Cell>) {
            cell = std::move(other);
            check();
            Cell extracted(std::move(cell));
            check();
            using std::swap;
            swap(cell, extracted);
            check();
        }
        if constexpr (std::is_arithmetic_v<std::remove_cvref_t<decltype(image(cell))>> &&
                      requires {
                          cell += 2;
                          cell -= 1;
                      }) {
            cell += 2;
            check();
            cell -= 1;
            check();
        }
        if constexpr (requires { cell.reset(); }) {
            cell.reset();
            check();
        }
        if constexpr (requires { cell.modify([](auto&) {}); }) {
            cell.modify([&](auto& live) { live = supplied(cell, ++sequence); });
            check();
            try {
                cell.modify([&](auto& live) {
                    live = supplied(cell, ++sequence);
                    throw 37;
                });
            } catch (int value) {
                CHECK_MESSAGE(value == 37,
                              " F23 the throwing write actually reaches its exit");
            }
            check();
        }
    }
}
template <class Row>
void columns(std::type_identity<Row>) {
    using Rows = edi::ItemVec<Row>;
    auto a = std::make_shared<Row>(), b = std::make_shared<Row>();
    if constexpr (edi::KeyedItem<Row>) {
        edi::KeyTraits<Row>::key(*a) = "column-row-a";
        edi::KeyTraits<Row>::key(*b) = "column-row-b";
    }
    Rows first({a, b});
    Rows second;
    if constexpr (!edi::KeyedItem<Row>) second.assign({a, b, a});
    unsigned sequence = 0;
    std::vector<std::function<void()>> old_buffers;
    std::apply([&](auto... member) { (keep_buffer(first.column(member), old_buffers), ...); },
               crysta::RowSchema<Row>::fields);
    auto check = [&] {
        coherent(first);
        coherent(second);
        for (auto& held : old_buffers) held();
    };
    std::apply([&](auto... member) { (routes(a.get()->*member, check, sequence), ...); },
               crysta::RowSchema<Row>::fields);
    first.assign({b, a});
    check();
    if constexpr (!edi::KeyedItem<Row>) {
        second.erase_at(0);
        check();
    }
    first.erase_at(1);
    check();
    // Detached image writes may still reach a second unkeyed holder, never the removed table.
    std::apply([&](auto... member) { (routes(a.get()->*member, check, sequence), ...); },
               crysta::RowSchema<Row>::fields);
    first.push_back(a);
    check();
    auto fresh = std::make_shared<Row>();
    if constexpr (edi::KeyedItem<Row>) edi::KeyTraits<Row>::key(*fresh) = "column-row-fresh";
    first.replace_at(0, fresh);
    check();
    Rows copy(first);
    coherent(copy);
    auto copied = [&] {
        check();
        coherent(copy);
    };
    std::apply([&](auto... member) { (routes(a.get()->*member, copied, sequence), ...); },
               crysta::RowSchema<Row>::fields);
    copy = first;
    copied();
    Rows moved(std::move(copy));
    coherent(moved);
    first.clear();
    check();
    first.push_back(a);
    check();
}
}  // namespace
TEST_CASE("C34-T28 atom value columns and read images agree on every write") {
    columns(std::type_identity<edi::AtomSite>{});
}
TEST_CASE("C34-T28 background value columns and read images agree on every write") {
    columns(std::type_identity<edi::LineSegment>{});
}
TEST_CASE("C34-T28 texture value columns and read images agree on every write") {
    columns(std::type_identity<edi::PrefOrient>{});
}
TEST_CASE("C34-T28 extract value columns and read images agree on every write") {
    columns(std::type_identity<edi::SequentialExtractRule>{});
}
TEST_CASE("C34-T28 structure value columns and read images agree on every write") {
    columns(std::type_identity<edi::Structure>{});
}
TEST_CASE("C34-T28 experiment value columns and read images agree on every write") {
    columns(std::type_identity<edi::BraggPdExperiment>{});
}
TEST_CASE("C34-T28 caller value columns and read images agree on every write") {
    columns(std::type_identity<C34ImageRow>{});
}
