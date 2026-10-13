#include <doctest/doctest.h>

#include <filesystem>
#include <string>

#include "edi/edit.hpp"
#include "edi/io.hpp"

namespace {
edi::Project reference_project() {
    const auto tests = std::filesystem::path(__FILE__).parent_path().parent_path().parent_path();
    return edi::load_project((tests / "fixtures/e04_t1/editable-project").string());
}
std::string category_bytes(const std::string& block) { return block.substr(block.find('\n') + 1); }
}  // namespace

TEST_CASE("Duplicate experiment preserves every saved category and isolates nested edits") {
    auto project = reference_project();
    const auto source = project.experiments[0];
    const auto before = edi::block_edi_text(project, edi::BlockKind::EXPERIMENT, source->name);
    const auto copy = edi::experiment_copy(project, *source);
    CHECK_MESSAGE(copy.name.value() == "hrpt_copy",
                  "The first duplicate gets its source-name copy suffix");
    edi::Edit::create_experiment(project, copy)();
    const auto duplicate = project.experiments.back();
    CHECK_MESSAGE(duplicate.get() != source.get(),
                  "A duplicate experiment owns an independent object");
    CHECK_MESSAGE(category_bytes(edi::block_edi_text(project, edi::BlockKind::EXPERIMENT,
                                                     duplicate->name)) == category_bytes(before),
                  "A whole experiment duplicate preserves all saved category bytes except the "
                  "datablock name");
    CHECK_MESSAGE(duplicate->background[0].get() != source->background[0].get(),
                  "A duplicate background owns independent rows");
    CHECK_MESSAGE(duplicate->excluded_regions[0].get() != source->excluded_regions[0].get(),
                  "Duplicate excluded regions own independent rows");
    CHECK_MESSAGE(duplicate->linked_structures[0].get() != source->linked_structures[0].get(),
                  "Duplicate links own independent rows");
    CHECK_MESSAGE(
        duplicate->preferred_orientation[0].get() != source->preferred_orientation[0].get(),
        "Duplicate texture owns independent rows");
    REQUIRE_MESSAGE(duplicate->data.has_value(), "The duplicate must retain its measured data");
    duplicate->data->intensity_meas.modify([](auto& values) { values[0] += 123.125; });
    duplicate->instrument.setup_wavelength->value = 1.711;
    duplicate->background[0]->intensity.value = 249.125;
    duplicate->excluded_regions[0]->first = 1.125;
    CHECK_MESSAGE(
        edi::block_edi_text(project, edi::BlockKind::EXPERIMENT, source->name) == before,
        "Editing nested duplicate categories leaves every source category byte unchanged");
    CHECK_MESSAGE(edi::experiment_copy(project, *source).name.value() == "hrpt_copy2",
                  "Duplicating the original again uses copy2");
}

TEST_CASE("Duplicate structure preserves categories and leaves experiment links unchanged") {
    auto project = reference_project();
    const auto source = project.structures[0];
    source->atom_sites[0]->adp_type = "Uani";
    edi::AtomSiteAniso tensor;
    tensor.id = source->atom_sites[0]->id.value();
    tensor.adp_11.value = .00625;
    tensor.adp_22.value = .0075;
    tensor.adp_33.value = .00875;
    source->atom_site_aniso.push_back(tensor);
    const auto before = edi::block_edi_text(project, edi::BlockKind::STRUCTURE, source->name);
    const auto experiment =
        edi::block_edi_text(project, edi::BlockKind::EXPERIMENT, project.experiments[0]->name);
    const auto copy = edi::structure_copy(project, *source);
    CHECK_MESSAGE(copy.name.value() == "lbco_copy",
                  "A duplicate structure gets its source-name copy suffix");
    edi::Edit::add_structure(project, copy)();
    const auto duplicate = project.structures.back();
    CHECK_MESSAGE(duplicate.get() != source.get(),
                  "A duplicate structure owns an independent object");
    CHECK_MESSAGE(category_bytes(edi::block_edi_text(project, edi::BlockKind::STRUCTURE,
                                                     duplicate->name)) == category_bytes(before),
                  "A whole structure duplicate preserves all saved category bytes except its "
                  "datablock name");
    CHECK_MESSAGE(duplicate->atom_sites[0].get() != source->atom_sites[0].get(),
                  "Duplicate atom sites own independent rows");
    REQUIRE_MESSAGE(!duplicate->atom_site_aniso.empty(),
                    "The duplicate must retain its anisotropic tensor category");
    CHECK_MESSAGE(duplicate->atom_site_aniso[0].get() != source->atom_site_aniso[0].get(),
                  "Duplicate tensors own independent row objects");
    duplicate->atom_site_aniso[0]->adp_11.value = .009125;
    duplicate->cell.length_a.value = 4.125;
    duplicate->atom_sites[0]->occupancy.value = .625;
    CHECK_MESSAGE(
        edi::block_edi_text(project, edi::BlockKind::STRUCTURE, source->name) == before,
        "Editing duplicate cell and atom values leaves every source category byte unchanged");
    CHECK_MESSAGE(edi::block_edi_text(project, edi::BlockKind::EXPERIMENT,
                                      project.experiments[0]->name) == experiment,
                  "Adding an unlinked structure copy changes no experiment category or link");
    CHECK_MESSAGE(edi::structure_copy(project, *source).name.value() == "lbco_copy2",
                  "Duplicating the original structure again uses copy2");
}
