#include <iostream>
#include <optional>
#include <string>

#include "scan_progress.hpp"

std::optional<int> total(const std::string& text) {
    return text == "-" ? std::nullopt : std::optional<int>(std::stoi(text));
}
int main(int argc, char** argv) {
    if (argc == 3 && std::string(argv[1]) == "sequence") {
        const auto columns = std::stoull(argv[2]);
        std::cout << edi::detail::scan_progress_heading("widths", true, 2, false, columns) << '\n';
        std::cout << edi::detail::scan_progress_row(1, 2, 59.0, 1, 1, 0, 4.81, 4.81, 4.81,
                                                    "scan-first.dat", columns);
        std::cout
            << edi::detail::scan_progress_row(
                   2, 2, 36611.0, 2, 2, 0, 4.81, 3.91, 8.44,
                   "scan-last-abcdefghijklmnopqrstuvwxyz-abcdefghijklmnopqrstuvwxyz-tail.dat",
                   columns)
            << '\n';
    } else if (argc == 7 && std::string(argv[1]) == "heading") {
        std::cout << edi::detail::scan_progress_heading(argv[2], std::stoi(argv[3]) != 0,
                                                        total(argv[4]), std::stoi(argv[5]) != 0,
                                                        std::stoull(argv[6]));
    } else if (argc == 13 && std::string(argv[1]) == "row") {
        std::cout << edi::detail::scan_progress_row(
            std::stoi(argv[2]), total(argv[3]), std::stod(argv[4]), std::stoi(argv[5]),
            std::stoi(argv[6]), std::stoi(argv[7]), std::stod(argv[8]), std::stod(argv[9]),
            std::stod(argv[10]), argv[11], std::stoull(argv[12]));
    } else if (argc == 5 && std::string(argv[1]) == "rewrite") {
        std::cout << edi::detail::scan_progress_rewrite(argv[2], std::stoull(argv[3]),
                                                        std::stoull(argv[4]));
    } else {
        return 2;
    }
}
