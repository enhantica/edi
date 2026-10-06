#include <doctest/doctest.h>

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

static std::filesystem::path admission_root() {
    return std::filesystem::path(__FILE__)
               .parent_path()
               .parent_path()
               .parent_path()
               .parent_path() /
           "tests/fixtures/cwl_family/native";
}
static bool admission_refuses(const std::function<void()>& call) {
    const auto peak_admission = [](const std::string& message) {
        return message.find("peak") != std::string::npos &&
               message.find("unsupported") == std::string::npos &&
               message.find("not a CW profile coefficient") == std::string::npos;
    };
    try {
        call();
    } catch (const std::invalid_argument& error) {
        return peak_admission(error.what());
    } catch (const std::runtime_error& error) {
        return peak_admission(error.what());
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
    control.experiment().data->intensity_meas =
        std::vector<double>(control.experiment().data->axis().size(), 1.0);
    control.experiment().peak.broad_lorentz_x->value = 0.023;
    control.experiment().peak.broad_lorentz_x->free = true;
    control.minimizer_max_iterations = 1;
    CHECK_NOTHROW_MESSAGE(
        control.fit(),
        "A native fit refusal needs a successful fit of its valid free TCH control");
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
    CHECK_NOTHROW_MESSAGE(
        edi::save_project(control, (destination / "valid").string()),
        "A native save refusal needs successful persistence of its valid TCH control");
    std::filesystem::remove_all(destination);
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

TEST_CASE("CW native optional profile slots use declared defaults") {
    for (const std::string type : {"cwl-pseudo-voigt", "cwl-pseudo-voigt-berar-baldinozzi"}) {
        auto project = edi::load_project((admission_root() / "gaussian").string());
        auto& peak = project.experiment().peak;
        peak.type = type;
        peak.broad_gauss_u->free = true;
        CHECK_NOTHROW_MESSAGE(
            project.calculate(),
            "A native profile admits absent optional mixing and asymmetry defaults");
        CHECK_NOTHROW_MESSAGE((void)project.experiment().free_parameters(),
                              "Experiment free selection admits absent optional profile defaults");
        CHECK_NOTHROW_MESSAGE(
            (void)project.free_parameters(),
            "Project free selection admits absent optional mixing and asymmetry defaults");
        project.experiment().data->intensity_meas =
            std::vector<double>(project.experiment().data->axis().size(), 1.0);
        project.minimizer_max_iterations = 1;
        CHECK_NOTHROW_MESSAGE(
            project.fit(),
            "Native fitting accepts the profile's declared absent optional defaults");
        const auto destination =
            std::filesystem::temp_directory_path() / "cwl-edi-optional-defaults";
        std::filesystem::remove_all(destination);
        CHECK_NOTHROW_MESSAGE(
            edi::save_project(project, destination.string()),
            "Saving admits a native profile whose optional coefficients take defaults");
        if (std::filesystem::exists(destination)) {
            auto reloaded = edi::load_project(destination.string());
            CHECK_NOTHROW_MESSAGE(reloaded.calculate(),
                                  "Saved native optional defaults remain consumable after reload");
        }
        std::filesystem::remove_all(destination);
    }
}

TEST_CASE("CW native fixed BeBa setting stays outside Edi free walks") {
    auto project = edi::load_project((admission_root() / "beba").string());
    auto& peak = project.experiment().peak;
    peak.asym_beba_limit->value = 160;
    peak.asym_beba_limit->free = true;
    peak.asym_beba_a0->free = true;
    const auto check = [&](const std::vector<edi::Parameter*>& free) {
        CHECK_MESSAGE(std::find(free.begin(), free.end(), &*peak.asym_beba_limit) == free.end(),
                      "The fixed BeBa limit cannot be advertised by a native Edi free walk");
        CHECK_MESSAGE(
            std::find(free.begin(), free.end(), &*peak.asym_beba_a0) != free.end(),
            "A supplied free BeBa coefficient remains selectable beside its fixed setting");
    };
    check(project.experiment().free_parameters());
    check(project.free_parameters());
    CHECK_NOTHROW_MESSAGE(project.calculate(),
                          "A nondefault fixed limit remains valid calculation input");
    project.experiment().data->intensity_meas =
        std::vector<double>(project.experiment().data->axis().size(), 1.0);
    project.minimizer_max_iterations = 1;
    CHECK_NOTHROW_MESSAGE(
        project.fit(),
        "Edi fitting excludes the fixed limit before constructing a derivative chain");
}

static void metadata_free_walk(edi::Project& project, bool experiment_walk,
                               bool allow_refusal = false) {
    auto& peak = project.experiment().peak;
    std::vector<edi::Parameter*> free;
    try {
        free =
            experiment_walk ? project.experiment().free_parameters() : project.free_parameters();
    } catch (const std::invalid_argument& error) {
        const std::string message = error.what();
        CHECK_MESSAGE((allow_refusal &&
                       (message.find("peak") != std::string::npos ||
                        message.find("asym_beba") != std::string::npos) &&
                       (message.find("descriptor") != std::string::npos ||
                        message.find("metadata") != std::string::npos ||
                        message.find("spec") != std::string::npos)),
                      "A metadata refusal must identify the canonical peak descriptor mismatch");
        return;
    }
    CHECK_MESSAGE(
        std::find(free.begin(), free.end(), &*peak.asym_beba_limit) == free.end(),
        "The owning limit slot remains fixed after any descriptor or parameter replacement");
    CHECK_MESSAGE(std::find(free.begin(), free.end(), &*peak.asym_beba_a0) != free.end(),
                  "The actual free coefficient cannot be suppressed by the limit descriptor");
    CHECK_MESSAGE(std::find(free.begin(), free.end(), &*peak.broad_gauss_w) != free.end(),
                  "Metadata admission must retain an independently free width coefficient");
}

static edi::Project metadata_control() {
    auto project = edi::load_project((admission_root() / "beba").string());
    auto& peak = project.experiment().peak;
    peak.asym_beba_limit->value = 160;
    peak.asym_beba_limit->free = true;
    peak.asym_beba_a0->value = .031;
    peak.asym_beba_a0->free = true;
    peak.broad_gauss_w->value = .047;
    peak.broad_gauss_w->free = true;
    return project;
}

TEST_CASE("CW fixed limit metadata cannot change its owning slot selection") {
    auto control = metadata_control();
    CHECK_NOTHROW_MESSAGE(metadata_free_walk(control, true),
                          "Canonical metadata admits the experiment's real free coefficients");
    CHECK_NOTHROW_MESSAGE(metadata_free_walk(control, false),
                          "Canonical metadata admits the project's real free coefficients");
    for (int mutation = 0; mutation < 4; ++mutation) {
        CAPTURE(mutation);
        for (const bool experiment_walk : {true, false}) {
            CAPTURE(experiment_walk);
            auto project = metadata_control();
            auto& peak = project.experiment().peak;
            const auto* coefficient_spec = peak.asym_beba_a0->spec;
            REQUIRE_MESSAGE(
                coefficient_spec != nullptr,
                "The different non-null descriptor comes from a real loaded coefficient");
            REQUIRE_MESSAGE(
                coefficient_spec != peak.asym_beba_limit->spec,
                "The metadata substitution must differ from the fixed limit descriptor");
            if (mutation == 0) peak.asym_beba_limit->spec = nullptr;
            if (mutation == 1) peak.asym_beba_limit->spec = coefficient_spec;
            if (mutation == 2) peak.asym_beba_limit = edi::Parameter(160, 0.0, true);
            if (mutation == 3) peak.asym_beba_limit = *peak.asym_beba_a0;
            peak.asym_beba_limit->value = 160;
            peak.asym_beba_limit->free = true;
            CHECK_NOTHROW_MESSAGE(
                metadata_free_walk(project, experiment_walk, true),
                "Free enumeration classifies the slot or refuses only its descriptor mismatch");
            CHECK_MESSAGE(peak.asym_beba_limit->value == 160,
                          "Descriptor admission retains the supplied nondefault limit angle");
        }
    }
}

TEST_CASE("CW real coefficient remains selectable with the fixed limit descriptor") {
    auto control = metadata_control();
    metadata_free_walk(control, true);
    metadata_free_walk(control, false);
    for (const bool replacement : {false, true}) {
        CAPTURE(replacement);
        for (const bool experiment_walk : {true, false}) {
            CAPTURE(experiment_walk);
            auto project = metadata_control();
            auto& peak = project.experiment().peak;
            const auto* limit_spec = peak.asym_beba_limit->spec;
            REQUIRE_MESSAGE(limit_spec != nullptr,
                            "The mirror escape copies the actual loaded fixed limit descriptor");
            if (replacement) {
                peak.asym_beba_a0 = *peak.asym_beba_limit;
            } else {
                peak.asym_beba_a0->spec = limit_spec;
            }
            peak.asym_beba_a0->value = .031;
            peak.asym_beba_a0->free = true;
            CHECK_NOTHROW_MESSAGE(
                metadata_free_walk(project, experiment_walk, true),
                "The mirrored descriptor cannot silently remove a real free coefficient");
            CHECK_MESSAGE(peak.asym_beba_a0->value == .031,
                          "Mirror admission retains the real coefficient's supplied value");
        }
    }
}
