// SPDX-License-Identifier: BSD-3-Clause
#include "edi/correlation_matrix.hpp"

#include "edi/model.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <optional>

namespace edi {

std::vector<double> correlation_strengths(const CorrelationMatrix& matrix) {
    const std::size_t n = matrix.names.size();
    std::vector<double> strength(n, 0.0);
    if (matrix.values.size() != n * n) {
        return strength;
    }
    for (std::size_t i = 0; i < n; ++i) {
        for (std::size_t j = 0; j < n; ++j) {
            const double value = matrix.values[i * n + j];
            if (i != j && std::isfinite(value)) {
                strength[i] = std::max(strength[i], std::abs(value));
            }
        }
    }
    return strength;
}

double correlation_level_for_count(const std::vector<double>& strengths, std::size_t count) {
    if (strengths.empty()) {
        return 0.0;
    }
    std::vector<double> ranked = strengths;
    std::sort(ranked.begin(), ranked.end(), std::greater<>());
    count = std::min(std::max<std::size_t>(count, 1), ranked.size());
    // The lowest strength that keeps at most `count`, every parameter at that strength included.
    std::optional<double> lowest;
    for (std::size_t i = 0; i < ranked.size(); ++i) {
        if (i + 1 < ranked.size() && ranked[i + 1] == ranked[i]) {
            continue;  // the last of a tie tells how many its strength keeps
        }
        if (i + 1 > count) {
            break;
        }
        lowest = ranked[i];
    }
    // A tie that keeps more than `count` at every strength is kept whole, at the count-th strength.
    return lowest.value_or(ranked[count - 1]);
}

std::optional<double> correlation_default_level(const std::vector<double>& strengths) {
    if (strengths.size() <= kDefaultCorrelatedParameters) {
        return 0.0;
    }
    const double level = correlation_level_for_count(strengths, kDefaultCorrelatedParameters);
    if (correlation_count_for_level(strengths, level) > kDefaultCorrelatedParameters) {
        return std::nullopt;
    }
    return level;
}

std::size_t correlation_count_for_level(const std::vector<double>& strengths, double level) {
    return static_cast<std::size_t>(
        std::count_if(strengths.begin(), strengths.end(), [level](double strength) { return strength >= level; }));
}

CorrelationSelection correlation_matrix(const CorrelationMatrix& matrix, double level, std::size_t count) {
    CorrelationSelection out;
    const std::size_t n = matrix.names.size();
    if (matrix.values.size() != n * n) {
        return out;
    }
    const std::vector<double> strength = correlation_strengths(matrix);
    std::vector<std::size_t> kept;
    for (std::size_t i = 0; i < n; ++i) {
        if (strength[i] >= level) {
            kept.push_back(i);
        }
    }
    std::stable_sort(kept.begin(), kept.end(), [&strength](std::size_t a, std::size_t b) { return strength[a] > strength[b]; });
    kept.resize(std::min(kept.size(), count));
    std::sort(kept.begin(), kept.end());
    if (kept.size() < 2) {
        return out;
    }
    for (std::size_t row : kept) {
        out.labels.push_back(matrix.names[row]);
        for (std::size_t column : kept) {
            const double value = matrix.values[row * n + column];
            out.values.push_back(column < row && std::isfinite(value) ? value
                                                                       : std::numeric_limits<double>::quiet_NaN());
        }
    }
    return out;
}

std::vector<std::string> other_experiment_prefixes(const std::vector<std::string>& experiment_names, std::size_t shown) {
    std::vector<std::string> out;
    for (std::size_t i = 0; i < experiment_names.size(); ++i) {
        if (i != shown) {
            out.push_back(datablock_key(experiment_names[i], "experiment") + ".");
        }
    }
    return out;
}

}  // namespace edi
