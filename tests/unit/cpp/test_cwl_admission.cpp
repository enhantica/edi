#include <doctest/doctest.h>

#include <cstdint>
#include <filesystem>
#include <functional>
#include <stdexcept>
#include <string>

static std::filesystem::path admission_root() {
    return std::filesystem::path(__FILE__)
               .parent_path()
               .parent_path()
               .parent_path()
               .parent_path() /
           "tests/fixtures/cwl_family/native";
}
static bool admission_refuses(const std::function<void()>& call) {
    try {
        call();
    } catch (const std::invalid_argument& error) {
        return std::string(error.what()).find("peak") != std::string::npos;
    } catch (const std::runtime_error& error) {
        return std::string(error.what()).find("peak") != std::string::npos;
    }
    return false;
}
#include "edi/io.hpp"
#include "edi/model.hpp"

static edi::Project admission_model(int damage) {
    auto project =
        edi::load_project((admission_root() / (damage == 0 ? "tch" : "gaussian")).string());
    auto& peak = project.experiment().peak;
    if (damage < 2) peak.type = std::string("cwl-pseudo-voigt");
    if (damage == 2) peak.broad_lorentz_x = edi::Parameter(.023);
    if (damage == 3) peak.mixing_eta_0 = edi::Parameter(.23);
    if (damage == 4) peak.asym_fcj_1 = edi::Parameter(.031);
    if (damage == 5) peak.asym_beba_a0 = edi::Parameter(.037);
    for (auto* parameter : peak.parameters()) parameter->free = true;
    return project;
}

TEST_CASE("CW native calculate admits only a matching token and slot block") {
    auto control = edi::load_project((admission_root() / "tch").string());
    CHECK_NOTHROW_MESSAGE(control.calculate(),
                          "A native admission witness must first accept its valid TCH control");
    const auto destination = std::filesystem::temp_directory_path() /
                             ("cwl-admission-edi-calculate-" +
                              std::to_string(reinterpret_cast<std::uintptr_t>(&control)));
    for (int damage = 0; damage < 6; ++damage) {
        CAPTURE(damage);
        auto project = admission_model(damage);
        CHECK_MESSAGE(admission_refuses([&] { project.calculate(); }),
                      "Native calculate must refuse stale, absent or foreign profile slots before "
                      "consumption");
        std::filesystem::remove_all(destination);
    }
}

TEST_CASE("CW native fit admits only a matching token and slot block") {
    auto control = edi::load_project((admission_root() / "tch").string());
    CHECK_NOTHROW_MESSAGE(control.calculate(),
                          "A native admission witness must first accept its valid TCH control");
    const auto destination =
        std::filesystem::temp_directory_path() /
        ("cwl-admission-edi-fit-" + std::to_string(reinterpret_cast<std::uintptr_t>(&control)));
    for (int damage = 0; damage < 6; ++damage) {
        CAPTURE(damage);
        auto project = admission_model(damage);
        CHECK_MESSAGE(
            admission_refuses([&] { project.fit(); }),
            "Native fit must refuse stale, absent or foreign profile slots before consumption");
        std::filesystem::remove_all(destination);
    }
}

TEST_CASE("CW native save admits only a matching token and slot block") {
    auto control = edi::load_project((admission_root() / "tch").string());
    CHECK_NOTHROW_MESSAGE(control.calculate(),
                          "A native admission witness must first accept its valid TCH control");
    const auto destination =
        std::filesystem::temp_directory_path() /
        ("cwl-admission-edi-save-" + std::to_string(reinterpret_cast<std::uintptr_t>(&control)));
    for (int damage = 0; damage < 6; ++damage) {
        CAPTURE(damage);
        auto project = admission_model(damage);
        CHECK_MESSAGE(
            admission_refuses([&] { edi::save_project(project, destination.string()); }),
            "Native save must refuse stale, absent or foreign profile slots before consumption");
        std::filesystem::remove_all(destination);
    }
}

TEST_CASE("CW native free admits only a matching token and slot block") {
    auto control = edi::load_project((admission_root() / "tch").string());
    CHECK_NOTHROW_MESSAGE((void)control.free_parameters(),
                          "A native free-set witness must first accept its valid TCH control");
    for (int damage = 0; damage < 6; ++damage) {
        CAPTURE(damage);
        auto project = admission_model(damage);
        CHECK_MESSAGE(admission_refuses([&] { (void)project.free_parameters(); }),
                      "Native free enumeration must refuse stale absent or foreign profile slots");
    }
}
