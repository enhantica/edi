// Compile against isolated edi 499909374 and crysta 8453a08e9 headers and libraries.
#include <fstream>

#include "observe.hpp"
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    const auto root = std::filesystem::path(argv[1]);
    for (const std::string kind : {"I", "III"})
        std::ofstream(root / (kind + ".pin"))
            << legacy_magnetic_editor::observe(root / kind, std::filesystem::path(argv[2]) / kind);
}
