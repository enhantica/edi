#include <doctest/doctest.h>

#include <string>

#include "edi/fittability.hpp"

#include "../../fixtures/dictionary_display/metadata_reference.hpp"

#if __has_include("edi/display.hpp")
#include "edi/display.hpp"
#define HAS_EDI_DICTIONARY_DISPLAY 1
#endif

TEST_CASE("The core metadata bridge retains every dictionary label unit and file tooltip") {
#ifdef HAS_EDI_DICTIONARY_DISPLAY
    for (const auto& row : kMetadataCases) {
        REQUIRE_MESSAGE(edi::has_item(row.uid),
                        "Every source item is available through the product bridge");
        CHECK_MESSAGE(
            (edi::label(row.uid) == row.label && edi::units_label(row.uid) == row.units),
            "Every core label and displayed unit equals the independently read YAML value");
        CHECK_MESSAGE(edi::edi_name(row.uid) == row.tag,
                      "Every core item identifies the current spelling written to file");
        CHECK_MESSAGE(edi::tooltip(row.uid).find(row.tag) != std::string::npos,
                      "Every core field tooltip names its actual file item");
        CHECK_MESSAGE(!edi::description(row.uid).empty(),
                      "Every core item has a dictionary description");
    }
    edi::Project project;
    project.experiments.emplace_back(edi::BraggPdExperiment{});
    edi::refresh_fittability(project);
    const auto& angle = project.experiment().instrument.setup_twotheta_bank;
    CHECK_MESSAGE(edi::is_descriptor("instrument.setup_twotheta_bank"),
                  "The dictionary bridge classifies numerical item-backed bank angles as descriptors");
    CHECK_MESSAGE(angle.fit_blocker == edi::FitBlocker::Descriptor,
                  "The core marks item-backed descriptors even without a runtime fit slot");
    CHECK_MESSAGE(angle.fit_reason == "a descriptor, never fitted",
                  "The core descriptor mark carries the one shared refusal reason");
    for (const auto& row : kCategoryCases) {
        CHECK_MESSAGE(edi::category_label(row.id) == (row.loop ? row.loop_title : row.title),
                      "Every group title uses its dictionary singular or loop title");
        CHECK_MESSAGE(edi::category_icon(row.id) == row.icon,
                      "Every group icon is owned by the dictionary");
    }
    for (const auto& row : kOptionCases) {
        CHECK_MESSAGE(edi::option_label(row.uid, row.token) == row.label,
                      "Every selector option uses the independently read dictionary display name");
        CHECK_MESSAGE(edi::option_tooltip(row.uid, row.token).find(row.token) != std::string::npos,
                      "Every selector tooltip retains the stored token");
    }
#else
    FAIL_CHECK("The product core exposes dictionary-owned labels options categories and tooltips");
#endif
}
