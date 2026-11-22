#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>

#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/project_import.hpp"

namespace {
struct ImportDirectory {
    std::filesystem::path path;
    explicit ImportDirectory(const std::string& name)
        : path(std::filesystem::temp_directory_path() /
               ("edi-import-" + name + "-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()))) {
        if (!std::filesystem::create_directory(path)) throw std::runtime_error("Test directory already exists");
    }
    ~ImportDirectory() { std::filesystem::remove_all(path); }
};

edi::Project stub_project() {
    const auto fixture = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
                         "fixtures/constraint_expressions/project";
    auto result = edi::load_project(fixture.string());
    auto& structure = *result.structures[0];
    structure.cell.length_a.value = 5.123456;
    structure.cell.length_a.free = true;
    return result;
}
}  // namespace

TEST_CASE("One registered converter receives shared naming description and native round trip") {
    edi::register_project_importer({"Witness", {".witness"}, [](const std::string&, const edi::WarningSink&) {
                                       return stub_project();
                                   }});
    ImportDirectory dir("registered");
    const auto input = dir.path / "sample-name.WiTnEsS";
    std::ofstream(input) << "independent input";
    auto project = edi::load_project(input.string());
    CHECK_MESSAGE(project.metadata.name == "sample-name", "Every importer receives source-stem naming");
    CHECK_MESSAGE(project.metadata.description == "Imported from Witness: sample-name.WiTnEsS",
                  "Every importer receives a source-program description");
    CHECK_NOTHROW_MESSAGE(edi::check_import_roundtrip(project, (dir.path / "native").string()),
                          "Every registered importer can use the shared native round-trip check");
    const auto reopened = edi::load_project((dir.path / "native").string());
    CHECK_MESSAGE(reopened.structures[0]->cell.length_a.value.get() == doctest::Approx(5.123456),
                  "The round trip retains the independently supplied noninteger cell length");
    CHECK_MESSAGE(reopened.structures[0]->cell.length_a.free.get(),
                  "The round trip retains the converter's free flag");
}

TEST_CASE("Importer suffix detection ignores case and chooses the longest registered suffix") {
    const auto convert = [](const std::string&, const edi::WarningSink&) { return stub_project(); };
    edi::register_project_importer({"ShortSuffix", {".longtest"}, convert});
    edi::register_project_importer({"LongSuffix", {".PaRt.LoNgTeSt"}, convert});
    auto found = edi::project_importer_for("sample.PART.LONGTEST");
    REQUIRE_MESSAGE(found.has_value(), "Mixed-case input suffixes select a registered converter");
    CHECK_MESSAGE(found->program == "LongSuffix", "A compound suffix wins over an earlier short suffix");
    found = edi::project_importer_for("sample.LONGTEST");
    REQUIRE_MESSAGE(found.has_value(), "The shorter converter remains reachable");
    CHECK_MESSAGE(found->program == "ShortSuffix", "The plain suffix selects its own converter");
    CHECK_MESSAGE(!edi::project_importer_for("sample.longtest.extra"),
                  "Suffix matching never accepts a matching substring inside a different extension");
}

TEST_CASE("Registering an existing suffix is refused even with different case") {
    CHECK_THROWS_AS_MESSAGE(
        edi::register_project_importer({"Duplicate", {".PcR"}, [](const std::string&, const edi::WarningSink&) {
                                           return stub_project();
                                       }}),
        std::invalid_argument, "A new converter cannot take another program's suffix");
    CHECK_MESSAGE(edi::project_importer_for("sample.pcr")->program == "FullProf",
                  "A refused registration leaves the original converter selected");
}

TEST_CASE("An importer supplied description survives the shared post-conversion steps") {
    edi::register_project_importer({"Described", {".described"}, [](const std::string&, const edi::WarningSink&) {
                                       auto project = stub_project();
                                       project.metadata.description = "Source title";
                                       return project;
                                   }});
    const auto project = edi::import_project("sample.described");
    CHECK_MESSAGE(project.metadata.description == "Source title", "A converter's description is retained");
    CHECK_MESSAGE(project.metadata.name == "sample", "Source-stem naming also applies to described projects");
}

TEST_CASE("A converter losing a parameter spec is refused with its program and datablock") {
    edi::register_project_importer({"BrokenSpec", {".brokenspec"}, [](const std::string&, const edi::WarningSink&) {
                                       auto project = stub_project();
                                       project.structures[0]->cell.length_a.spec = nullptr;
                                       return project;
                                   }});
    try {
        edi::import_project("sample.brokenspec");
        FAIL_CHECK("An imported parameter without native metadata must be refused");
    } catch (const edi::IoError& error) {
        const std::string message = error.what();
        INFO(message);
        CHECK_MESSAGE(message.find("BrokenSpec") != std::string::npos,
                      "The missing-metadata refusal identifies the program");
        CHECK_MESSAGE(message.find("phase") != std::string::npos,
                      "The missing-metadata refusal identifies the datablock");
    }
}

TEST_CASE("An experiment parameter without its spec is refused with its program and datablock") {
    edi::register_project_importer({"BrokenInstrument", {".brokeninstrument"},
                                   [](const std::string&, const edi::WarningSink&) {
                                       auto project = stub_project();
                                       project.experiments[0]->instrument.calib_twotheta_offset->spec = nullptr;
                                       return project;
                                   }});
    try {
        edi::import_project("sample.brokeninstrument");
        FAIL_CHECK("An imported instrument parameter without native metadata must be refused");
    } catch (const edi::IoError& error) {
        const std::string message = error.what();
        CHECK_MESSAGE(message.find("BrokenInstrument") != std::string::npos,
                      "The missing-metadata refusal identifies the instrument converter");
        CHECK_MESSAGE(message.find("bank") != std::string::npos,
                      "The missing-metadata refusal identifies the experiment datablock");
    }
}

TEST_CASE("The shared round-trip checker detects parameter metadata loss") {
    ImportDirectory dir("roundtrip-fault");
    auto project = stub_project();
    project.metadata.name = "sample";
    project.structures[0]->cell.length_a.spec = nullptr;
    CHECK_THROWS_AS_MESSAGE(edi::check_import_roundtrip(project, (dir.path / "native").string()), edi::IoError,
                            "The round-trip check must detect metadata reconstructed only after saving");
}
