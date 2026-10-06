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
    if (damage == 0) peak.type = std::string("cwl-pseudo-voigt");
    // ADR-0080 makes eta optional/default-zero, but the TCH X/Y pair remains required.
    if (damage == 1) peak.type = std::string("cwl-tch-pseudo-voigt");
    if (damage == 2) peak.broad_lorentz_x = edi::Parameter(.023);
    if (damage == 3) peak.broad_lorentz_y = edi::Parameter(.047);
    if (damage == 4) peak.mixing_eta_0 = edi::Parameter(.23);
    if (damage == 5) peak.mixing_eta_1 = edi::Parameter(.0031);
    if (damage == 6) peak.asym_fcj_1 = edi::Parameter(.031);
    if (damage == 7) peak.asym_fcj_2 = edi::Parameter(.037);
    if (damage == 8) peak.asym_beba_a0 = edi::Parameter(.031);
    if (damage == 9) peak.asym_beba_b0 = edi::Parameter(.037);
    if (damage == 10) peak.asym_beba_a1 = edi::Parameter(.0031);
    if (damage == 11) peak.asym_beba_b1 = edi::Parameter(.0037);
    if (damage == 12) peak.asym_beba_limit = edi::Parameter(160);
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
    for (int damage = 0; damage < 13; ++damage) {
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
    for (int damage = 0; damage < 13; ++damage) {
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
    for (int damage = 0; damage < 13; ++damage) {
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
    control.experiment().peak.broad_lorentz_x->free = true;
    CHECK_MESSAGE(!control.free_parameters().empty(),
                  "A native free-set control must include its supplied free TCH slot");
    CHECK_NOTHROW_MESSAGE((void)control.free_parameters(),
                          "A native free-set witness must first accept its valid TCH control");
    for (int damage = 0; damage < 13; ++damage) {
        CAPTURE(damage);
        auto project = admission_model(damage);
        CHECK_MESSAGE(admission_refuses([&] { (void)project.free_parameters(); }),
                      "Native free enumeration must refuse stale absent or foreign profile slots");
    }
}
