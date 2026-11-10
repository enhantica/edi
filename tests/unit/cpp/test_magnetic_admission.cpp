#include <doctest/doctest.h>

#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include "crysta/cif_import.hpp"
#include "edi/io.hpp"

namespace {
void check_admission(const std::string& extension) {
    const auto root = std::filesystem::path(__FILE__).parent_path() /
                      "../../fixtures/magnetic_pnma/admission";
    REQUIRE_MESSAGE(std::filesystem::is_directory(root),
                    "Independent lattice-character controls are committed for C++ replay");
    std::size_t controls = 0;
    for (const auto& entry : std::filesystem::directory_iterator(root)) {
        if (entry.path().extension() != extension) continue;
        ++controls;
        std::ifstream input(entry.path());
        const std::string text{std::istreambuf_iterator<char>(input), {}};
        const bool expected = entry.path().filename().string().starts_with("accept-");
        bool admitted = false;
        std::string reason;
        try {
            const std::string native = extension == ".mcif"
                ? crysta::cif_to_edi(text, crysta::DocumentKind::Structure,
                                     entry.path().string(), nullptr)
                : text;
            const auto structure = edi::structure_from_edi_text(native);
            (void)structure;
            admitted = true;
        } catch (const std::exception& error) {
            reason = error.what();
        }
        CHECK_MESSAGE(admitted == expected,
                      "C++ native and magCIF handoff apply the independent character rule: ",
                      entry.path().filename().string(), " ", reason);
    }
    CHECK_MESSAGE(controls == 29, "Both C++ entrances exercise every independent admission control");
}
}

TEST_CASE("Native C++ factories share the magnetic admission rule") {
    check_admission(".edi");
}

TEST_CASE("The C++ magCIF handoff shares the magnetic admission rule") {
    check_admission(".mcif");
}
