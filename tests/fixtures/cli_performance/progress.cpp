#include "scan_progress.hpp"
#include <iostream>
#include <optional>
#include <string>

std::optional<int> total(const std::string& text) {
    return text == "-" ? std::nullopt : std::optional<int>(std::stoi(text));
}
int main(int argc, char** argv) {
    if (argc == 7 && std::string(argv[1]) == "heading") {
        std::cout << edi::detail::scan_progress_heading(argv[2], std::stoi(argv[3]) != 0,
            total(argv[4]), std::stoi(argv[5]) != 0, std::stoull(argv[6]));
    } else if (argc == 10 && std::string(argv[1]) == "row") {
        std::cout << edi::detail::scan_progress_row(std::stoi(argv[2]), total(argv[3]),
            std::stod(argv[4]), std::stoi(argv[5]), std::stoi(argv[6]), std::stoi(argv[7]),
            std::stod(argv[8]), std::stoull(argv[9]));
    } else if (argc == 5 && std::string(argv[1]) == "rewrite") {
        std::cout << edi::detail::scan_progress_rewrite(argv[2], std::stoull(argv[3]),
            std::stoull(argv[4]));
    } else {
        return 2;
    }
}
