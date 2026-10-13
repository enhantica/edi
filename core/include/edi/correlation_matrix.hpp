// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <cstddef>
#include <optional>
#include <string>
#include <vector>

// The correlation chart's filter, which the Correlations tab and the report share (edi ADR-0035 §1): diffraction-lib's
// _filter_correlation_dataframe keeps the parameters whose strongest correlation reaches a level, and of these the
// most correlated, up to a count. The level and the count set each other (the owner, 2026-10-11).

namespace edi {

/// A fit's correlations: the parameters' unique names in the fit's order and the full symmetric matrix over them,
/// row-major, NaN for a pair the fit did not record (the diagonal is not read).
struct CorrelationMatrix {
    std::vector<std::string> names;
    std::vector<double> values;
};

/// What the chart shows: the chosen parameters in the fit's order, and their matrix's lower triangle row by row, NaN
/// on and above the diagonal and for a pair the fit did not record.
struct CorrelationSelection {
    std::vector<std::string> labels;
    std::vector<double> values;
};

/// Each parameter's strongest absolute correlation with another; 0 when it has none.
std::vector<double> correlation_strengths(const CorrelationMatrix& matrix);
/// diffraction-lib's DEFAULT_CORRELATION_MAX_PARAMETERS: the chart's size with no level set.
inline constexpr std::size_t kDefaultCorrelatedParameters = 5;

/// The level a count sets (ADR-0035 §7, after diffraction-lib's _resolve_correlation_filter): the lowest strength
/// that keeps at most `count` parameters, a tie kept whole; when a tie keeps more at every strength, the count-th
/// strength, which keeps that tie whole. `count` is at least 1; with fewer strengths, the least of them (0 with none).
double correlation_level_for_count(const std::vector<double>& strengths, std::size_t count);
/// The level with none set, diffraction-lib's automatic rule (_auto_filtered_correlation_dataframe): 0, every
/// parameter, with at most five; else the lowest strength keeping one to five; absent when even the strongest keeps
/// more, and then the chart shows the five strongest (correlation_matrix's count).
std::optional<double> correlation_default_level(const std::vector<double>& strengths);
/// The count a level sets: the parameters whose strength reaches it.
std::size_t correlation_count_for_level(const std::vector<double>& strengths, double level);
/// The parameters whose strength reaches `level`, the `count` strongest of them (the earlier on a tie), in the fit's
/// order. Fewer than two give an empty selection.
CorrelationSelection correlation_matrix(const CorrelationMatrix& matrix, double level, std::size_t count);

/// One experiment's chart of a fit of several leaves out the others' parameters, as the Correlations tab shows it: the
/// name prefixes to leave out, each other experiment's datablock key and a dot. One experiment leaves out nothing.
std::vector<std::string> other_experiment_prefixes(const std::vector<std::string>& experiment_names, std::size_t shown);

}  // namespace edi
