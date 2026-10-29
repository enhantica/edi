// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>
#include <utility>
#include <variant>
#include <vector>

namespace edi_app::assistant_data::summary {
// Internal arithmetic for one already-captured inspection, never a data owner,
// currentness proof, engine inclusion rule, fit factor or physical validator.
// ADR-0057 owns populations/units and the later source-specific capture boundary.
static_assert(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits == 53);
inline constexpr std::uint64_t max_exact_index = 9007199254740991ULL; // 2^53-1, original JSON index law.

enum class RowSpace { Powder, SingleCrystal, BraggPhase };
enum class MaskSource { NativeCalcStatus, SingleCrystalFileFitUse, NotApplicable };
enum class Inclusion { Unknown, Included, Excluded };
enum class ColumnKind { X, H, K, L, Measured, Sigma, Calculated, Background, Residual,
                        DSpacing, SinThetaOverLambda, Wavelength };
enum class AxisOrder { StrictlyIncreasing, StrictlyDecreasing, Nondecreasing, Nonincreasing,
                       Constant, Unordered, Unknown, NotApplicable };
enum class Population { AllFinite, KnownIncludedFinite };
enum class MomentState { Ok, EmptyRange, UnavailableColumn, NoFiniteValues,
                         NoKnownIncludedFiniteValues, ArithmeticUnavailable };

struct Range {
    std::size_t first = 0, end = 0; // Native rows; end exclusive.
    std::size_t count() const noexcept { return end - first; }
};
struct ColumnMetadata {
    ColumnKind kind = ColumnKind::X;
    std::string name, item, unit, quantity; // Copied source metadata, never inferred here.
    std::size_t length = 0;
    bool available = false, current = false;
};
// Plain columns borrow original immutable buffers. Optional cells preserve SC
// absent QVariant versus present NaN/Inf, before the old JSON-null conversion.
using Cells = std::variant<std::span<const double>, std::span<const std::optional<double>>>;
struct ColumnInput {
    ColumnMetadata metadata;
    std::size_t first_row = 0;
    Cells cells = std::span<const double>{};
};
struct MaskInput {
    MaskSource source = MaskSource::NotApplicable;
    bool current = false;
    std::size_t first_row = 0;
    std::span<const Inclusion> rows;
};
struct IdentityMapping {};
struct ExplicitMapping {
    std::size_t first_row = 0;
    std::span<const std::optional<std::size_t>> rows;
};
using RowMapping = std::variant<IdentityMapping, ExplicitMapping>;
struct Input {
    RowSpace row_space = RowSpace::Powder;
    std::size_t total = 0, start = 0, count = 0, partitions = 1;
    std::span<const ColumnInput> columns;
    MaskInput mask;
    RowMapping mapping = IdentityMapping{};
    std::optional<std::size_t> axis_column; // Existing x column only; no SC angle fiction.
};
struct Witness {
    double value = 0;
    std::size_t row = 0;
    std::optional<std::size_t> source_row;
};
struct Coverage {
    std::size_t finite = 0, missing = 0, nan = 0, positive_infinity = 0, negative_infinity = 0;
};
struct SigmaQuality { std::size_t positive = 0, zero = 0, negative = 0; };
struct MaskCoverage {
    MaskSource source = MaskSource::NotApplicable;
    bool applicable = false, current = false;
    std::optional<std::size_t> included, excluded, unknown;
};
struct Moments {
    Population population = Population::AllFinite;
    std::size_t count = 0;
    bool population_complete = true;
    MomentState state = MomentState::NoFiniteValues;
    std::optional<double> mean, rms;
};
struct ColumnSummary {
    ColumnMetadata metadata;
    Coverage coverage;
    std::optional<Witness> minimum, maximum, first, last;
    std::optional<SigmaQuality> sigma_quality;
    std::optional<Moments> all_finite, included_finite;
};
struct RangeSummary {
    Range range;
    MaskCoverage mask;
    AxisOrder axis_order = AxisOrder::Unknown;
    std::vector<ColumnSummary> columns;
};
struct Summary {
    std::size_t requested_partitions = 0;
    RangeSummary overall;
    std::vector<RangeSummary> bins;
};

namespace detail {
inline void exact(std::size_t value) {
    if (static_cast<std::uintmax_t>(value) > max_exact_index)
        throw std::invalid_argument("Summary index is not exactly representable in JSON");
}
inline void valid_range(Range range) {
    exact(range.first); exact(range.end);
    if (range.end < range.first) throw std::invalid_argument("Summary range is reversed");
}
inline void valid_view(std::size_t first, std::size_t size) {
    exact(first); exact(size);
    if (static_cast<std::uintmax_t>(size) > max_exact_index - first)
        throw std::invalid_argument("Summary source view extent overflows");
}
inline bool moments_kind(ColumnKind kind) {
    switch (kind) {
        case ColumnKind::Measured: case ColumnKind::Sigma: case ColumnKind::Calculated:
        case ColumnKind::Background: case ColumnKind::Residual: return true;
        case ColumnKind::X: case ColumnKind::H: case ColumnKind::K: case ColumnKind::L:
        case ColumnKind::DSpacing: case ColumnKind::SinThetaOverLambda: case ColumnKind::Wavelength: return false;
    }
    throw std::invalid_argument("Unknown summary column kind");
}
inline std::optional<double> cell(const ColumnInput& column, std::size_t row) {
    if (!column.metadata.available || row >= column.metadata.length || row < column.first_row) return {};
    const auto place = row - column.first_row;
    return std::visit([place](const auto& values) -> std::optional<double> {
        if (place >= values.size()) return {};
        return values[place];
    }, column.cells);
}
inline Inclusion inclusion(const MaskInput& mask, std::size_t row) {
    if (!mask.current || row < mask.first_row || row - mask.first_row >= mask.rows.size()) return Inclusion::Unknown;
    return mask.rows[row - mask.first_row];
}
inline std::optional<std::size_t> source_row(const RowMapping& mapping, std::size_t row) {
    if (std::holds_alternative<IdentityMapping>(mapping)) return row;
    const auto& values = std::get<ExplicitMapping>(mapping);
    return row >= values.first_row && row - values.first_row < values.rows.size() ? values.rows[row - values.first_row] : std::nullopt;
}
inline MaskCoverage mask_coverage(const MaskInput& mask, Range range) {
    MaskCoverage out; out.source = mask.source;
    if (mask.source == MaskSource::NotApplicable) return out;
    out.applicable = true; out.current = mask.current;
    out.included = 0; out.excluded = 0; out.unknown = 0;
    for (auto row = range.first; row < range.end; ++row) {
        switch (inclusion(mask, row)) {
            case Inclusion::Included: ++*out.included; break;
            case Inclusion::Excluded: ++*out.excluded; break;
            case Inclusion::Unknown: ++*out.unknown; break;
        }
    }
    return out;
}
struct CompensatedSum {
    double value = 0, correction = 0;
    bool add(double next) noexcept {
        const double sum = value + next;
        const double delta = std::abs(value) >= std::abs(next) ? (value - sum) + next : (next - sum) + value;
        correction += delta; value = sum;
        return std::isfinite(value) && std::isfinite(correction);
    }
    double total() const noexcept { return value + correction; }
};
inline Moments moments(const ColumnInput& column, Range range, const MaskInput& mask,
                       const MaskCoverage& coverage, Population population) {
    Moments out; out.population = population;
    const bool included = population == Population::KnownIncludedFinite;
    out.population_complete = !included || (coverage.current && coverage.unknown && *coverage.unknown == 0);
    if (!column.metadata.available) { out.state = MomentState::UnavailableColumn; return out; }
    if (range.count() == 0) { out.state = MomentState::EmptyRange; return out; }
    const auto selected = [&](std::size_t row) {
        return !included || inclusion(mask, row) == Inclusion::Included;
    };
    double scale = 0;
    for (auto row = range.first; row < range.end; ++row) {
        const auto value = cell(column, row);
        if (selected(row) && value && std::isfinite(*value)) { ++out.count; scale = std::max(scale, std::abs(*value)); }
    }
    if (out.count == 0) {
        out.state = included ? MomentState::NoKnownIncludedFiniteValues : MomentState::NoFiniteValues;
        return out;
    }
    if (scale == 0) { out.state = MomentState::Ok; out.mean = 0; out.rms = 0; return out; }
    CompensatedSum signed_sum, square_sum;
    bool valid = true;
    for (auto row = range.first; row < range.end; ++row) {
        const auto value = cell(column, row);
        if (selected(row) && value && std::isfinite(*value)) {
            const double scaled = *value / scale;
            // Scaling must not erase a nonzero contribution before cancellation.
            // Subnormal scale ratios cannot retain binary64 relative precision.
            if (*value != 0 && !std::isnormal(scaled)) valid = false;
            valid = signed_sum.add(scaled) && valid;
            valid = square_sum.add(scaled * scaled) && valid;
        }
    }
    const double mean_scaled = signed_sum.total() / static_cast<double>(out.count);
    const double square_mean = square_sum.total() / static_cast<double>(out.count);
    const double mean = scale * mean_scaled;
    const double rms = square_mean >= 0 ? scale * std::sqrt(square_mean) : std::numeric_limits<double>::quiet_NaN();
    const double signed_total = signed_sum.total();
    if (!valid || !std::isfinite(mean_scaled) || !std::isfinite(square_mean) || !std::isfinite(mean) || !std::isfinite(rms) ||
        (signed_total != 0 && !std::isnormal(mean_scaled)) || (mean_scaled != 0 && mean == 0) || rms == 0) {
        out.state = MomentState::ArithmeticUnavailable; return out;
    }
    out.state = MomentState::Ok; out.mean = mean; out.rms = rms;
    return out;
}
inline AxisOrder axis_order(const Input& input, Range range) {
    if (input.row_space == RowSpace::SingleCrystal) return AxisOrder::NotApplicable;
    if (!input.axis_column || range.count() < 2) return AxisOrder::Unknown;
    const auto& axis = input.columns[*input.axis_column];
    std::optional<double> previous;
    bool rising = true, falling = true, nondecreasing = true, nonincreasing = true;
    for (auto row = range.first; row < range.end; ++row) {
        const auto value = cell(axis, row);
        if (!value || !std::isfinite(*value)) return AxisOrder::Unknown;
        if (previous) {
            rising = rising && *previous < *value; falling = falling && *previous > *value;
            nondecreasing = nondecreasing && *previous <= *value; nonincreasing = nonincreasing && *previous >= *value;
        }
        previous = value;
    }
    if (rising) return AxisOrder::StrictlyIncreasing;
    if (falling) return AxisOrder::StrictlyDecreasing;
    if (nondecreasing && nonincreasing) return AxisOrder::Constant;
    if (nondecreasing) return AxisOrder::Nondecreasing;
    if (nonincreasing) return AxisOrder::Nonincreasing;
    return AxisOrder::Unordered;
}
inline RangeSummary describe(const Input& input, Range range) {
    RangeSummary out; out.range = range; out.mask = mask_coverage(input.mask, range); out.axis_order = axis_order(input, range);
    out.columns.reserve(input.columns.size());
    for (const auto& column : input.columns) {
        ColumnSummary result; result.metadata = column.metadata;
        if (column.metadata.kind == ColumnKind::Sigma) result.sigma_quality.emplace();
        for (auto row = range.first; row < range.end; ++row) {
            const auto value = cell(column, row);
            if (!value) { ++result.coverage.missing; continue; }
            if (std::isnan(*value)) { ++result.coverage.nan; continue; }
            if (std::isinf(*value)) { if (*value > 0) ++result.coverage.positive_infinity; else ++result.coverage.negative_infinity; continue; }
            ++result.coverage.finite;
            Witness witness{*value, row, source_row(input.mapping, row)};
            if (!result.minimum || *value < result.minimum->value) result.minimum = witness;
            if (!result.maximum || *value > result.maximum->value) result.maximum = witness;
            if (row == range.first) result.first = witness;
            if (row == range.end - 1) result.last = witness;
            if (result.sigma_quality) {
                if (*value > 0) ++result.sigma_quality->positive;
                else if (*value < 0) ++result.sigma_quality->negative;
                else ++result.sigma_quality->zero;
            }
        }
        if (moments_kind(column.metadata.kind)) {
            result.all_finite = moments(column, range, input.mask, out.mask, Population::AllFinite);
            if (out.mask.applicable) result.included_finite = moments(column, range, input.mask, out.mask, Population::KnownIncludedFinite);
        }
        out.columns.push_back(std::move(result));
    }
    return out;
}
inline void validate(const Input& input) {
    exact(input.total); exact(input.start); exact(input.count); exact(input.partitions);
    switch (input.row_space) {
        case RowSpace::Powder:
            if (input.mask.source != MaskSource::NativeCalcStatus) throw std::invalid_argument("Powder summary needs its native mask owner");
            break;
        case RowSpace::SingleCrystal:
            if (input.mask.source != MaskSource::SingleCrystalFileFitUse || input.axis_column)
                throw std::invalid_argument("Single-crystal summary needs file fit-use and no powder axis");
            break;
        case RowSpace::BraggPhase:
            if (input.mask.source != MaskSource::NotApplicable) throw std::invalid_argument("Bragg summary has no measurement fit-use mask");
            break;
        default: throw std::invalid_argument("Unknown summary row space");
    }
    if (input.mask.source == MaskSource::NotApplicable && (input.mask.current || !input.mask.rows.empty()))
        throw std::invalid_argument("Inapplicable summary mask contains fit-use data");
    valid_view(input.mask.first_row, input.mask.rows.size());
    for (const auto value : input.mask.rows)
        if (value != Inclusion::Unknown && value != Inclusion::Included && value != Inclusion::Excluded)
            throw std::invalid_argument("Unknown summary inclusion state");
    if (const auto* mapping = std::get_if<ExplicitMapping>(&input.mapping)) {
        valid_view(mapping->first_row, mapping->rows.size());
        for (const auto row : mapping->rows) if (row) exact(*row);
    }
    if (input.axis_column && (*input.axis_column >= input.columns.size() || input.columns[*input.axis_column].metadata.kind != ColumnKind::X))
        throw std::invalid_argument("Summary axis must name its original x column");
    for (const auto& column : input.columns) {
        exact(column.metadata.length); (void)moments_kind(column.metadata.kind);
        std::visit([&](const auto& values) { valid_view(column.first_row, values.size()); }, column.cells);
    }
}
} // namespace detail

inline Range select_range(std::size_t start, std::size_t count, std::size_t total) {
    detail::exact(start); detail::exact(count); detail::exact(total);
    if (start > total) throw std::invalid_argument("Summary starts beyond the original native extent");
    return {start, start + std::min(count, total - start)};
}
inline std::vector<Range> partition_range(Range range, std::size_t partitions) {
    detail::valid_range(range); detail::exact(partitions);
    if (partitions == 0) throw std::invalid_argument("Summary partitions must be positive");
    const auto bins = std::min(partitions, range.count());
    std::vector<Range> result; result.reserve(bins);
    if (bins == 0) return result;
    const auto quotient = range.count() / bins, remainder = range.count() % bins;
    auto first = range.first;
    for (std::size_t bin = 0; bin < bins; ++bin) {
        const auto end = first + quotient + (bin < remainder ? 1 : 0);
        result.push_back({first, end}); first = end;
    }
    return result;
}
inline Summary summarize(const Input& input) {
    detail::validate(input);
    const auto range = select_range(input.start, input.count, input.total);
    const auto partitions = partition_range(range, input.partitions);
    Summary result; result.requested_partitions = input.partitions;
    result.overall = detail::describe(input, range); result.bins.reserve(partitions.size());
    for (const auto bin : partitions) result.bins.push_back(detail::describe(input, bin));
    return result;
}
} // namespace edi_app::assistant_data::summary
