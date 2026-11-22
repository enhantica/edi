#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

#include "edi/io.hpp"
#include "edi/project_import.hpp"

namespace {
std::filesystem::path cryspy_source() {
    return std::filesystem::path(__FILE__).parent_path().parent_path().parent_path() /
           "fixtures/project_imports/cryspy-pbso4.rcif";
}

std::string cryspy_text() {
    std::ifstream input(cryspy_source());
    std::ostringstream result;
    result << input.rdbuf();
    return result.str();
}

double source_number(const std::string& tag) {
    std::istringstream lines(cryspy_text());
    std::string line;
    while (std::getline(lines, line)) {
        if (line.starts_with(tag + " ")) return std::stod(line.substr(tag.size()));
    }
    throw std::runtime_error("Missing reference input " + tag);
}

struct RcifInput {
    std::filesystem::path path;
    explicit RcifInput(const std::string& name, const std::string& text)
        : path(std::filesystem::temp_directory_path() /
               ("edi-cryspy-" + name + "-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()) + ".rcif")) {
        std::ofstream(path) << text;
    }
    ~RcifInput() { std::filesystem::remove(path); }
};
}  // namespace

TEST_CASE("Cryspy source cell and signed instrument values survive conversion unchanged") {
    const auto project = edi::load_project(cryspy_source().string());
    REQUIRE_MESSAGE(project.structures.size() == 1, "The reference rcif has one crystal");
    REQUIRE_MESSAGE(project.experiments.size() == 1, "The reference rcif has one powder experiment");
    const auto& cell = project.structures[0]->cell;
    CHECK_MESSAGE(cell.length_a.value.get() == doctest::Approx(source_number("_cell_length_a")),
                  "The cell length is read independently from cryspy's source rcif");
    CHECK_MESSAGE(cell.length_b.value.get() == doctest::Approx(source_number("_cell_length_b")),
                  "The second nontrivial cell length retains its source value");
    const auto& instrument = project.experiments[0]->instrument;
    CHECK_MESSAGE(instrument.setup_wavelength->value.get() == doctest::Approx(source_number("_setup_wavelength")),
                  "The nonidentity wavelength retains the rcif's units");
    CHECK_MESSAGE(instrument.calib_twotheta_offset->value.get() == doctest::Approx(source_number("_setup_offset_2theta")),
                  "The nonzero signed zero offset retains cryspy's convention");
    CHECK_MESSAGE(edi::project_importers().front().program == "cryspy",
                  "Cryspy is the first built-in project importer");
}

TEST_CASE("Cryspy fitted cell uncertainty retains its rcif decimal scale") {
    const auto project = edi::load_project(cryspy_source().string());
    const auto& parameter = project.structures[0]->cell.length_a;
    REQUIRE_MESSAGE(parameter.uncertainty.get().has_value(),
                    "The source value 8.479343(100) carries a standard uncertainty");
    CHECK_MESSAGE(*parameter.uncertainty.get() == doctest::Approx(0.000100),
                  "The rcif's hundred last-place digits represent an uncertainty of 0.000100");
    CHECK_MESSAGE(parameter.free.get(), "A cryspy value with fitted uncertainty remains free");
}

TEST_CASE("Cryspy refuses unconverted scalar and loop input items") {
    for (const std::string declaration : {"_unsupported_model_value 0.37\n",
                                          "loop_\n_unsupported_model_label\n_unsupported_model_value\none 0.37\n"}) {
        auto text = cryspy_text();
        const auto pos = text.find("data_pbso4");
        REQUIRE_MESSAGE(pos != std::string::npos, "The unchanged reference declares its crystal block");
        text.insert(pos + std::string("data_pbso4").size(), "\n" + declaration);
        RcifInput source("unconverted", text);
        CHECK_THROWS_WITH_AS_MESSAGE(edi::load_project(source.path.string()), doctest::Contains("_unsupported_model"),
                                     edi::IoError, "An unconverted input item must never be silently discarded");
    }
}

TEST_CASE("Cryspy refuses parameter constraint marks") {
    for (const std::string marked : {"8.479343(100)A+", "8.479343()A-"}) {
        auto text = cryspy_text();
        const auto pos = text.find("8.479343(100)");
        REQUIRE_MESSAGE(pos != std::string::npos, "The source cell witness is present before mutation");
        text.replace(pos, std::string("8.479343(100)").size(), marked);
        RcifInput source("constraint", text);
        CHECK_THROWS_WITH_AS_MESSAGE(edi::load_project(source.path.string()), doctest::Contains("constraint mark"),
                                     edi::IoError, "Dropping a cryspy constraint mark would change the scientific model");
    }
}
