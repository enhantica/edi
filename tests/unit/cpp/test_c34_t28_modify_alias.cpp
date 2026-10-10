#include <doctest/doctest.h>

#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

#include "edi/model.hpp"

namespace {
template <class T>
void change(T& value) {
    if constexpr (std::is_same_v<T, bool>)
        value = !value;
    else if constexpr (std::is_arithmetic_v<T>)
        value += 2;
    else if constexpr (requires {
                           value.emplace();
                           value.has_value();
                       }) {
        if (value)
            value.reset();
        else
            value.emplace();
    } else if constexpr (std::is_same_v<T, std::map<std::string, double>>) {
        value["Si"] = 4.1491;
    } else if constexpr (std::is_same_v<T, std::vector<std::pair<double, double>>>) {
        value.emplace_back(1.25, 4.5);
    } else if constexpr (std::is_same_v<T, std::vector<std::string>>)
        value.push_back("saved");
    else
        value.push_back({"1.25", "4.5"});
}
template <class T>
bool same(const T& a, const T& b) {
    if constexpr (requires { a == b; })
        return a == b;
    else
        return a.has_value() == b.has_value() &&
               (!a || static_cast<const std::vector<double>&>(*a) ==
                          static_cast<const std::vector<double>&>(*b));
}
template <class Cell>
void aggregate_matches(Cell& cell) {
    using T = std::remove_cvref_t<decltype(cell.get())>;
    if constexpr (requires {
                      cell.table().key;
                      cell.table().value;
                  }) {
        std::vector<std::string> keys;
        std::vector<double> values;
        for (const auto& [key, value] : cell.get()) {
            keys.push_back(key);
            values.push_back(value);
        }
        CHECK_MESSAGE(
            (cell.table().key.values() == keys && cell.table().value.values() == values),
            " F18 every callback exit keeps aggregate key and value columns aligned");
    } else if constexpr (requires {
                             cell.table().first;
                             cell.table().second;
                         }) {
        std::vector<double> first, second;
        for (const auto& pair : cell.get()) {
            first.push_back(pair.first);
            second.push_back(pair.second);
        }
        CHECK_MESSAGE(
            (cell.table().first.values() == first && cell.table().second.values() == second),
            " F18 every callback exit keeps aggregate pair columns aligned");
    } else if constexpr (std::is_same_v<T, std::vector<std::string>>) {
        CHECK_MESSAGE(
            cell.table().names.values() == cell.get(),
            " F18 carried name images agree with their callback-published column");
    } else if constexpr (std::is_same_v<T, std::vector<std::vector<std::string>>>) {
        std::size_t width = 0;
        for (const auto& row : cell.get()) width = std::max(width, row.size());
        CHECK_MESSAGE(
            (cell.table().columns.size() == width && cell.table().rows() == cell.get().size()),
            " F18 carried cell table dimensions agree with the callback image");
        if (cell.table().columns.size() != width || cell.table().rows() != cell.get().size())
            return;
        for (std::size_t col = 0; col < width; ++col) {
            std::vector<std::string> values;
            for (const auto& row : cell.get()) values.push_back(col < row.size() ? row[col] : "");
            CHECK_MESSAGE(
                cell.table().columns[col].values() == values,
                " F18 every carried callback-published column retains its exact cells");
        }
    }
}
template <class T>
void retained_container_write(T& value, int operation) {
    if (operation == 0) {
        if (!value.empty()) {
            if constexpr (std::is_same_v<T, std::map<std::string, double>>)
                value.begin()->second += 1.375;
            else if constexpr (std::is_same_v<T, std::vector<std::pair<double, double>>>)
                value.front().second += 1.375;
            else if constexpr (std::is_same_v<T, std::vector<std::string>>)
                value.front() += "-alias";
            else if (!value.front().empty())
                value.front().front() += "-alias";
        }
    } else if (operation == 1) {
        if constexpr (std::is_same_v<T, std::map<std::string, double>>)
            value["Fe"] = 9.45;
        else
            change(value);
    } else if (operation == 2) {
        if (!value.empty()) value.erase(value.begin());
    } else
        value.clear();
}

template <class Cell, class Generation>
void alias_exits(Cell& cell, Generation generation) {
    using T = std::remove_cvref_t<decltype(cell.get())>;
    for (bool throws : {false, true}) {
        INFO(throws);
        T* escaped = nullptr;
        T expected = cell.get();
        change(expected);
        const auto before = generation();
        auto edit = [&](T& value) {
            escaped = &value;
            change(value);
            if (throws) throw std::runtime_error("callback-exit");
        };
        if (throws) {
            CHECK_THROWS_AS_MESSAGE(cell.modify(edit), std::runtime_error,
                                    " F18 throwing callbacks preserve their exception");
        } else
            cell.modify(edit);
        CHECK_MESSAGE(same(cell.get(), expected),
                      " F18 both callback exits retain the actual partial edit");
        CHECK_MESSAGE(generation() != before,
                      " F18 both callback exits publish a write to the holder");
        aggregate_matches(cell);
        CHECK_MESSAGE(
            escaped != &cell.get(),
            " F18 a returned callback alias cannot name the protected live payload");
        // The repaired callback may return a short-lived work value. Do not
        // dereference that pointer. Exercise the live escape only if it exists.
        if (escaped == &cell.get()) {
            const auto after = generation();
            *escaped = *escaped;
            CHECK_MESSAGE(
                generation() != after,
                " F18 a reachable retained alias cannot bypass equal-write currency");
            if constexpr (requires {
                              escaped->clear();
                              escaped->erase(escaped->begin());
                          }) {
                for (int operation = 0; operation != 4; ++operation) {
                    const auto currency = generation();
                    retained_container_write(*escaped, operation);
                    CHECK_MESSAGE(generation() != currency,
                                  " F18 retained element insertion erasure and clear "
                                  "cannot bypass currency");
                    aggregate_matches(cell);
                }
            } else
                change(*escaped);
        }
    }
}
template <class Cell>
void standalone(Cell& cell) {
    alias_exits(cell, [&] { return cell.written(); });
}
void parameter(edi::Parameter& p, auto generation) {
    alias_exits(p.value, generation);
    alias_exits(p.uncertainty, generation);
    alias_exits(p.free, generation);
    alias_exits(p.start_value, generation);
    alias_exits(p.start_uncertainty, generation);
}
}  // namespace
TEST_CASE("C34-T28 F18 every standalone numeric optional and measured callback closes retention") {
    edi::Parameter p;
    parameter(p, [&] {
        return p.value.written() + p.uncertainty.written() + p.free.written() +
               p.start_value.written() + p.start_uncertainty.written();
    });
    edi::PrefOrient texture;
    standalone(texture.index_h);
    standalone(texture.index_k);
    standalone(texture.index_l);
    edi::LineSegment point;
    standalone(point.position);
    parameter(point.intensity, [&] {
        return point.intensity.value.written() + point.intensity.uncertainty.written() +
               point.intensity.free.written() + point.intensity.start_value.written() +
               point.intensity.start_uncertainty.written();
    });
    edi::SequentialExtractRule rule;
    standalone(rule.required);
    edi::PdDataBase data;
    standalone(data.two_theta);
    standalone(data.time_of_flight);
}
TEST_CASE("C34-T28 F18 bound numeric optional and flag callbacks renew their actual row holders") {
    edi::ItemVec<edi::AtomSite> sites;
    sites.push_back(edi::AtomSite{});
    for (auto* p : sites[0]->parameters()) parameter(*p, [&] { return sites.category_stamp(); });
    edi::ItemVec<edi::PrefOrient> texture;
    texture.push_back(edi::PrefOrient{});
    auto generation = [&] { return texture.category_stamp(); };
    alias_exits(texture[0]->index_h, generation);
    alias_exits(texture[0]->index_k, generation);
    alias_exits(texture[0]->index_l, generation);
    parameter(texture[0]->march_r, generation);
    parameter(texture[0]->march_random_fract, generation);
    edi::ItemVec<edi::LineSegment> background;
    background.push_back(edi::LineSegment{});
    alias_exits(background[0]->position, [&] { return background.category_stamp(); });
    parameter(background[0]->intensity, [&] { return background.category_stamp(); });
    edi::ItemVec<edi::SequentialExtractRule> rules;
    rules.push_back(edi::SequentialExtractRule{});
    alias_exits(rules[0]->required, [&] { return rules.category_stamp(); });
}
TEST_CASE("C34-T28 F18 aggregate callbacks cannot retain images outside their column tables") {
    edi::Structure structure;
    standalone(structure.scattering_lengths_fm);
    edi::ExperimentBase experiment;
    experiment.excluded_regions.push_back(edi::ExcludedRegion(1.25, 4.5));
    alias_exits(experiment.excluded_regions[0]->first, [&] { return experiment.excluded_regions.category_stamp(); });
    alias_exits(experiment.excluded_regions[0]->second, [&] { return experiment.excluded_regions.category_stamp(); });
    edi::CarriedLoop carried;
    standalone(carried.columns);
    standalone(carried.rows);
}
