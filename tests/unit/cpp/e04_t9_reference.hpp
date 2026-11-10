#pragma once
#include <array>
#include <crysta/cell_symmetry.hpp>
#include <crysta/model.hpp>

namespace e04_t9 {
// The engine's own setting map supplies every dependent value. For example a
// cubic length edit must compare with the cubic reference b=c=a, not a strained cell.
inline void reference_length_a(crysta::Project& reference, double length) {
    auto& cell = reference.structure().cell.parameters;
    cell[0].set_value(length);
    const auto freedom = crysta::cell_freedom(reference.structure().space_group.get());
    std::array<double, 6> independent{};
    for (std::size_t axis = 0; axis < independent.size(); ++axis)
        independent[axis] = cell[axis].value();
    for (std::size_t axis = 0; axis < independent.size(); ++axis) {
        const int leader = freedom.follows[axis];
        cell[axis].set_value(leader == crysta::CellFreedom::kFixed
                                ? freedom.fixed[axis]
                                : independent[static_cast<std::size_t>(leader)]);
    }
}
}  // namespace e04_t9
