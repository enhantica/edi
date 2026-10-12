#include <cstdint>
#include <iostream>
#include <memory>
#include <vector>

#include "edi/model.hpp"
#if defined(__clang__)
#define NO_COUNT __attribute__((no_sanitize("coverage")))
#else
#define NO_COUNT __attribute__((no_sanitize_coverage))
#endif
namespace {
bool enabled = false;
std::uint64_t count = 0;
}  // namespace
extern "C" {
NO_COUNT void __sanitizer_cov_trace_cmp1(std::uint8_t, std::uint8_t) {
    if (enabled) ++count;
}
NO_COUNT void __sanitizer_cov_trace_cmp2(std::uint16_t, std::uint16_t) {
    if (enabled) ++count;
}
NO_COUNT void __sanitizer_cov_trace_cmp4(std::uint32_t, std::uint32_t) {
    if (enabled) ++count;
}
NO_COUNT void __sanitizer_cov_trace_cmp8(std::uint64_t, std::uint64_t) {
    if (enabled) ++count;
}
NO_COUNT void __sanitizer_cov_trace_const_cmp1(std::uint8_t, std::uint8_t) {
    if (enabled) ++count;
}
NO_COUNT void __sanitizer_cov_trace_const_cmp2(std::uint16_t, std::uint16_t) {
    if (enabled) ++count;
}
NO_COUNT void __sanitizer_cov_trace_const_cmp4(std::uint32_t, std::uint32_t) {
    if (enabled) ++count;
}
NO_COUNT void __sanitizer_cov_trace_const_cmp8(std::uint64_t, std::uint64_t) {
    if (enabled) ++count;
}
NO_COUNT void __sanitizer_cov_trace_switch(std::uint64_t, void*) {
    if (enabled) ++count;
}
}
extern "C" NO_COUNT void __sanitizer_cov_trace_pc_guard(std::uint32_t*) {}
extern "C" NO_COUNT void __sanitizer_cov_trace_pc_guard_init(std::uint32_t*, std::uint32_t*) {}

template <typename Row>
void exercise(std::size_t n, const std::string& mode) {
    using Table = edi::ItemVec<Row>;
    std::vector<typename Table::Ptr> rows;
    for (std::size_t i = 0; i < n; ++i) {
        auto row = std::make_shared<Row>();
        if constexpr (std::is_same_v<Row, edi::FitParameterCorrelation>) {
            row->id = "row-" + std::to_string(10000000 + i);
            row->correlation = "0.50";
        }
        rows.push_back(row);
    }
    Table table;
    if (mode == "replace" || mode == "reorder" || mode == "copy") table.assign(rows);
    if (mode == "replace") {
        rows.clear();
        for (std::size_t i = 0; i < n; ++i) {
            auto row = std::make_shared<Row>();
            if constexpr (std::is_same_v<Row, edi::FitParameterCorrelation>)
                row->id = "new-" + std::to_string(10000000 + i);
            rows.push_back(row);
        }
    }
    if (mode == "reorder") std::reverse(rows.begin(), rows.end());
    enabled = true;
    if (mode == "copy") {
        Table copy = table;
        enabled = false;
        if (copy.size() != n || copy[0] == table[0])
            throw std::runtime_error("copy lost value semantics");
    } else {
        table.assign(rows);
        enabled = false;
    }
    if (table.size() != n || table[0] != rows[0])
        throw std::runtime_error("assignment lost row identity");
    std::cout << n << '\t' << count << '\n';
}
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    const auto n = std::stoul(argv[1]);
    const std::string mode = argv[2];
    if (mode == "default-ids")
        exercise<edi::LineSegment>(n, mode);
    else if (mode == "unkeyed")
        exercise<edi::ExcludedRegion>(n, mode);
    else
        exercise<edi::FitParameterCorrelation>(n, mode);
}
