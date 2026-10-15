// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <memory>
#include <optional>
#include <utility>
#include <vector>

#include "edi/calculation.hpp"

namespace edi::detail {
// Existing publication split into throwing preparation and a same-owner, same-shape noexcept commit.
// Internal only: no caller-controlled callback or alternate scientific result is introduced.
struct PreparedPublication {
    CalculationResult result;
    std::vector<std::pair<Parameter*, double>> completed;
    std::vector<std::shared_ptr<ComputedSource>> sources;
    std::vector<std::shared_ptr<GeometrySource>> geometry_sources;
    void commit(Project& live) noexcept;
};
std::optional<PreparedPublication> prepare_publication(Project& live, CalculationResult&& result);
}
