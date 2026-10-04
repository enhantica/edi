// Capture with the pre-move native build; the output is a labelled regression pin.
#include <iostream>

#include "stamp_routes.hpp"
int main() {
    for (const auto& [name, flags] : c34_t28_baseline::capture())
        std::cout << name << ' ' << flags[0] << ' ' << flags[1] << ' ' << flags[2] << '\n';
}
