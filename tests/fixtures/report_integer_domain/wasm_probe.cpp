// SPDX-License-Identifier: BSD-3-Clause
#include <cstdio>
#include "../../../core/src/report_json.cpp"

int main() {
    static_assert(sizeof(std::size_t) == 4);
    int failures = 0;
    for (const double value : {4294967296.0, 9007199254740992.0}) {
        try { (void)edi::index_of(edi::json::Value(value), "index"); ++failures; }
        catch (const std::invalid_argument&) {}
    }
    try {
        if (edi::index_of(edi::json::Value(4294967295.0), "index") != 4294967295U) ++failures;
    } catch (...) { ++failures; }
    std::printf("actual size_t bits=32; boundary failures=%d\n", failures);
    return failures;
}
