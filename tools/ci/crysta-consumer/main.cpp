// SPDX-License-Identifier: BSD-3-Clause
// Zero-Python installed-consumer proof: a fresh C++-only project that consumes the pinned, installed
// `crysta::crysta` package and makes a real public call — no Python, no edi. If this compiles, links,
// and runs against build/crysta-prefix, the standalone C++ package is genuinely usable.

#include <cstdio>

#include "crysta/scattering.hpp"

int main() {
    const crysta::NeutronScattering scattering = crysta::load_neutron_scattering();
    const double b_c_na = scattering.b_c.at("Na");  // a real public API call on the installed package
    std::printf("crysta zero-Python consumer OK: b_c(Na) = %.4f fm\n", b_c_na);
    return b_c_na > 0.0 ? 0 : 1;
}
