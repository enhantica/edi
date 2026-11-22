#include <doctest/doctest.h>

#include <filesystem>
#include <string>

#include "edi/io.hpp"
#include "edi/project_import.hpp"

TEST_CASE("FullProf imports retain native parameter metadata before any save") {
    const auto root = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path().parent_path();
    for (const std::string input : {"pd-neut-cwl_pbso4_basic/pbso4.pcr",
                                    "pd-neut-tof_si-sepd/fixed.pcr",
                                    "pd-xray-cwl_lif_single/lif_single_unpolarized.pcr"}) {
        CAPTURE(input);
        auto project = edi::load_project((root / "knowledge/verification/fullprof" / input).string());
        REQUIRE_MESSAGE(!project.structures.empty(), "The FullProf reference contains a crystal");
        REQUIRE_MESSAGE(!project.experiments.empty(), "The FullProf reference contains an experiment");
        for (const auto* parameter : project.parameters()) {
            REQUIRE_MESSAGE(parameter->spec != nullptr,
                            "Every FullProf parameter carries native metadata immediately after import");
            CHECK_MESSAGE(!std::string(parameter->spec->name).empty(),
                          "Imported native metadata declares its parameter name");
        }
        const auto& instrument = project.experiments[0]->instrument;
        if (instrument.setup_wavelength) {
            CHECK_MESSAGE(std::string(instrument.setup_wavelength->spec->name) == "setup_wavelength",
                          "The wavelength keeps its own native slot metadata");
            CHECK_MESSAGE(std::string(instrument.calib_twotheta_offset->spec->name) == "calib_twotheta_offset",
                          "The angular offset keeps its own native slot metadata");
        } else {
            CHECK_MESSAGE(std::string(instrument.calib_d_to_tof_linear.spec->name) == "calib_d_to_tof_linear",
                          "The TOF calibration keeps its own native slot metadata");
        }
    }
}
