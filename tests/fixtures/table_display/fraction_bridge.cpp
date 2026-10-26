#include <iostream>
#include <string>

#include "edi/display.hpp"

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    const double value = std::stod(argv[2]);
    const double su = std::stod(argv[3]);
    if (su > 0) {
        const auto text = edi::fitted_text(argv[1], value, su, "iucr_19");
        std::cout << text.value << '\t' << text.su;
    } else {
        std::cout << edi::display_text(argv[1], value) << '\t';
    }
}
