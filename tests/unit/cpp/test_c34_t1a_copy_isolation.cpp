#include <doctest/doctest.h>

#include <string>
#include <type_traits>
#include <utility>

#include "edi/model.hpp"

namespace {

template <typename Slot>
auto& item_from(Slot& slot) {
    if constexpr (requires { *slot; }) {
        return *slot;
    } else {
        return slot;
    }
}

template <typename Item>
Item& append_item(edi::ItemVec<Item>& vector, Item item) {
    vector.push_back(std::move(item));
    return *vector.back();
}

edi::Structure structure_fixture() {
    edi::Structure structure;
    structure.name = "c34-structure";
    structure.cell.length_a.value = 5.125;
    edi::AtomSite site;
    site.id = "Si1";
    site.type_symbol = "Si";
    site.adp_iso.value = 0.375;
    append_item(structure.atom_sites, std::move(site));
    return structure;
}

edi::BraggPdExperiment experiment_fixture() {
    edi::BraggPdExperiment experiment;
    experiment.name = "c34-bank";
    experiment.instrument.setup_twotheta_bank.value = 91.25;
    edi::LineSegment point;
    point.position = 1234.5;
    point.intensity.value = 18.75;
    append_item(experiment.background, std::move(point));
    return experiment;
}

edi::Project project_fixture() {
    edi::Project project;
    append_item(project.structures, structure_fixture());
    append_item(project.experiments, experiment_fixture());
    return project;
}

}  // namespace

TEST_CASE("C34-T1a Project copy construction and assignment deep-clone item storage") {
    edi::Project source = project_fixture();
    const double source_length = item_from(source.structures[0]).cell.length_a.value;
    const double source_angle =
        item_from(source.experiments[0]).instrument.setup_twotheta_bank.value;
    edi::Project constructed = source;
    CHECK_MESSAGE(&item_from(constructed.structures[0]) != &item_from(source.structures[0]),
                  " Project copy construction must allocate fresh Structure storage");
    CHECK_MESSAGE(&item_from(constructed.experiments[0]) != &item_from(source.experiments[0]),
                  " Project copy construction must allocate fresh experiment storage");
    item_from(constructed.structures[0]).cell.length_a.value = 7.625;
    item_from(constructed.experiments[0]).instrument.setup_twotheta_bank.value = 111.5;
    CHECK_MESSAGE(item_from(source.structures[0]).cell.length_a.value == source_length,
                  "mutating a copy-constructed Project must not reach the source Structure");
    CHECK_MESSAGE(item_from(source.experiments[0]).instrument.setup_twotheta_bank.value == source_angle,
                  "mutating a copy-constructed Project must not reach the source experiment");

    edi::Project assigned;
    assigned = source;
    CHECK_MESSAGE(&item_from(assigned.structures[0]) != &item_from(source.structures[0]),
                  " Project copy assignment must allocate fresh Structure storage");
    CHECK_MESSAGE(&item_from(assigned.experiments[0]) != &item_from(source.experiments[0]),
                  " Project copy assignment must allocate fresh experiment storage");
    item_from(assigned.structures[0]).cell.length_a.value = 8.875;
    item_from(assigned.experiments[0]).instrument.setup_twotheta_bank.value = 127.0;
    CHECK_MESSAGE(item_from(source.structures[0]).cell.length_a.value == source_length,
                  "mutating a copy-assigned Project must not reach the source Structure");
    CHECK_MESSAGE(item_from(source.experiments[0]).instrument.setup_twotheta_bank.value == source_angle,
                  "mutating a copy-assigned Project must not reach the source experiment");
}

TEST_CASE("C34-T1a nested collection owners deep-clone their item storage") {
    edi::Structure structure = structure_fixture();
    edi::Structure structure_copy = structure;
    CHECK_MESSAGE(&item_from(structure_copy.atom_sites[0]) != &item_from(structure.atom_sites[0]),
                  " Structure copy construction must allocate fresh AtomSite storage");
    item_from(structure_copy.atom_sites[0]).adp_iso.value = 1.25;
    CHECK_MESSAGE(item_from(structure.atom_sites[0]).adp_iso.value == 0.375,
                  "mutating a copied Structure's AtomSite must not reach the source");
    edi::Structure structure_assigned;
    structure_assigned = structure;
    CHECK_MESSAGE(&item_from(structure_assigned.atom_sites[0]) != &item_from(structure.atom_sites[0]),
                  " Structure copy assignment must allocate fresh AtomSite storage");

    edi::BraggPdExperiment experiment = experiment_fixture();
    edi::BraggPdExperiment experiment_copy = experiment;
    CHECK_MESSAGE(&item_from(experiment_copy.background[0]) != &item_from(experiment.background[0]),
                  " experiment copy construction must allocate fresh LineSegment storage");
    item_from(experiment_copy.background[0]).intensity.value = 44.5;
    CHECK_MESSAGE(item_from(experiment.background[0]).intensity.value == 18.75,
                  "mutating a copied experiment background must not reach the source");
    edi::BraggPdExperiment experiment_assigned;
    experiment_assigned = experiment;
    CHECK_MESSAGE(&item_from(experiment_assigned.background[0]) != &item_from(experiment.background[0]),
                  " experiment copy assignment must allocate fresh LineSegment storage");
}

TEST_CASE("C34-T1a move operations preserve the owned item identities") {
    edi::Project source = project_fixture();
    auto* structure = &item_from(source.structures[0]);
    auto* experiment = &item_from(source.experiments[0]);
    edi::Project constructed = std::move(source);
    CHECK_MESSAGE(&item_from(constructed.structures[0]) == structure,
                  " Project move construction must not clone Structure storage");
    CHECK_MESSAGE(&item_from(constructed.experiments[0]) == experiment,
                  " Project move construction must not clone experiment storage");

    edi::Project assigned;
    structure = &item_from(constructed.structures[0]);
    experiment = &item_from(constructed.experiments[0]);
    assigned = std::move(constructed);
    CHECK_MESSAGE(&item_from(assigned.structures[0]) == structure,
                  " Project move assignment must preserve Structure identity");
    CHECK_MESSAGE(&item_from(assigned.experiments[0]) == experiment,
                  " Project move assignment must preserve experiment identity");
}

static_assert(
    !std::is_constructible_v<edi::Project, edi::Structure, edi::BraggPdExperiment>,
    " requires native edi::Project(Structure, BraggPdExperiment) to remain retired");
