// SPDX-License-Identifier: BSD-3-Clause
#include <iostream>

#include "edi/version.hpp"

// Thin entry point (ADR-0007/0009): no product logic here — it lives in the core. E01 ships
// a stub that prints the core version; load / calculate / fit / round-trip arrive in E03.
int main() {
    std::cout << "easydiffraction (edi core " << edi::core_version() << ")\n";
    return 0;
}
