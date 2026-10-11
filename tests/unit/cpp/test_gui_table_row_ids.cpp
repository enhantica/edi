#include <doctest/doctest.h>

#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include "edi/model.hpp"

namespace {
template <class Row>
void ordinal_admission(Row*) {
    edi::ItemVec<Row> rows;
    auto generated = std::make_shared<Row>();
    auto explicit_one = std::make_shared<Row>();
    explicit_one->id = "1";
    rows.assign({generated, explicit_one});
    REQUIRE_MESSAGE((rows.size() == 2), "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((generated->id == "2"),
                  "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((explicit_one->id == "1"),
                  "Stored row changes retain the declared ownership contract");
    const auto token = rows.token(1);
    rows.erase_at(0);
    CHECK_MESSAGE((rows[0]->id == "1"), "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((rows.token(0) == token),
                  "Stored row changes retain the declared ownership contract");
    rows[0]->id = "custom id";
    CHECK_MESSAGE((rows[0]->id == "custom id"),
                  "Stored row changes retain the declared ownership contract");
    const auto before = rows.category_stamp();
    CHECK_THROWS_AS_MESSAGE(rows[0]->id = "", std::invalid_argument,
                            "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((rows[0]->id == "custom id"),
                  "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((rows.category_stamp() == before),
                  "Stored row changes retain the declared ownership contract");
    rows.push_back(Row{});
    CHECK_MESSAGE((rows[1]->id == "1"), "Stored row changes retain the declared ownership contract");
    const auto two_rows = rows.category_stamp();
    CHECK_THROWS_AS_MESSAGE(rows[1]->id = "custom id", std::invalid_argument,
                            "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((rows[1]->id == "1"), "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((rows.category_stamp() == two_rows),
                  "Stored row changes retain the declared ownership contract");

    auto detached = std::make_shared<Row>();
    const auto generation = rows.generation();
    const auto detached_stamp = detached->id.written();
    CHECK_THROWS_AS_MESSAGE(rows.assign({detached, detached}), std::invalid_argument,
                            "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((detached->id.value().empty()),
                  "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((detached->id.written() == detached_stamp),
                  "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((rows.generation() == generation),
                  "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((rows.size() == 2), "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((rows[0]->id == "custom id"),
                  "Stored row changes retain the declared ownership contract");
    edi::ItemVec<Row> foreign;
    foreign.push_back(Row{});
    const auto foreign_generation = foreign.generation();
    CHECK_THROWS_AS_MESSAGE(rows.assign({detached, foreign[0]}), std::invalid_argument,
                            "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((detached->id.value().empty()),
                  "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((detached->id.written() == detached_stamp),
                  "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((rows.generation() == generation),
                  "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((foreign.generation() == foreign_generation),
                  "Stored row changes retain the declared ownership contract");
    CHECK_MESSAGE((foreign[0]->id == "1"),
                  "Stored row changes retain the declared ownership contract");
}

void alias(edi::Project& project, const char* id, const char* target) {
    edi::ParameterAlias row;
    row.id = id;
    row.parameter_unique_name = target;
    project.aliases.push_back(std::move(row));
}
}  // namespace

TEST_CASE("GUI table stored IDs reserve explicit keys and refuse changes atomically") {
    ordinal_admission(static_cast<edi::LineSegment*>(nullptr));
    ordinal_admission(static_cast<edi::ExcludedRegion*>(nullptr));
}

TEST_CASE("GUI exclusion bounds remain aligned with editable IDs and copy independently") {
    auto rows = edi::excluded_region_rows({{7.25, 9.5}, {1.125, 2.75}});
    rows[1]->id = "low angle";
    const auto frozen = rows.column(&edi::ExcludedRegion::second);
    auto copied = rows;
    const auto token = rows.token(1);
    rows.erase_at(0);
    rows[0]->second = 3.875;
    CHECK_MESSAGE((rows.token(0) == token),
                  "GUI exclusion bounds remain aligned with editable IDs and copy independently");
    CHECK_MESSAGE((
        rows.column(&edi::ExcludedRegion::id).values() == std::vector<std::string>{"low angle"}),
        "GUI exclusion bounds remain aligned with editable IDs and copy independently");
    CHECK_MESSAGE((rows.column(&edi::ExcludedRegion::first).values() == std::vector<double>{1.125}),
                  "GUI exclusion bounds remain aligned with editable IDs and copy independently");
    CHECK_MESSAGE((rows.column(&edi::ExcludedRegion::second).values() == std::vector<double>{3.875}),
                  "GUI exclusion bounds remain aligned with editable IDs and copy independently");
    CHECK_MESSAGE((frozen.values() == std::vector<double>{9.5, 2.75}),
                  "GUI exclusion bounds remain aligned with editable IDs and copy independently");
    CHECK_MESSAGE((copied[1]->id == "low angle"),
                  "GUI exclusion bounds remain aligned with editable IDs and copy independently");
    CHECK_MESSAGE((copied[1]->second.get() == 2.75),
                  "GUI exclusion bounds remain aligned with editable IDs and copy independently");
    copied[1]->id = "independent";
    CHECK_MESSAGE((rows[0]->id == "low angle"),
                  "GUI exclusion bounds remain aligned with editable IDs and copy independently");
}

TEST_CASE("GUI background ID rename follows every exact alias and preserves unrelated targets") {
    edi::Project project;
    project.experiment().name = "bank";
    edi::LineSegment point;
    point.id = "anchor";
    project.experiment().background.push_back(point);
    alias(project, "a", "bank.background.anchor.intensity");
    alias(project, "b", "bank.background.anchor.intensity");
    alias(project, "other", "other.background.anchor.intensity");
    project.experiment().background[0]->id = "renamed";
    CHECK_MESSAGE((
        project.aliases[0]->parameter_unique_name == "bank.background.renamed.intensity"),
        "GUI background ID rename follows every exact alias and preserves unrelated targets");
    CHECK_MESSAGE((
        project.aliases[1]->parameter_unique_name == "bank.background.renamed.intensity"),
        "GUI background ID rename follows every exact alias and preserves unrelated targets");
    CHECK_MESSAGE((
        project.aliases[2]->parameter_unique_name == "other.background.anchor.intensity"),
        "GUI background ID rename follows every exact alias and preserves unrelated targets");
    edi::LineSegment taken;
    taken.id = "taken";
    project.experiment().background.push_back(taken);
    CHECK_THROWS_AS_MESSAGE(
        project.experiment().background[0]->id = "taken", std::invalid_argument,
        "GUI background ID rename follows every exact alias and preserves unrelated targets");
    CHECK_MESSAGE((
        project.aliases[0]->parameter_unique_name == "bank.background.renamed.intensity"),
        "GUI background ID rename follows every exact alias and preserves unrelated targets");
}

TEST_CASE("GUI atom ID rename follows aliases with and without an anisotropic row") {
    for (bool anisotropic : {false, true}) {
        INFO(anisotropic);
        edi::Project project;
        project.structure().name = "sample";
        edi::AtomSite site;
        site.id = "Fe";
        project.structure().atom_sites.push_back(site);
        if (anisotropic) {
            edi::AtomSiteAniso tensor;
            tensor.id = "Fe";
            project.structure().atom_site_aniso.push_back(tensor);
        }
        alias(project, "position", "sample.atom_site.Fe.fract_x");
        alias(project, "occupancy", "sample.atom_site.Fe.occupancy");
        alias(project, "iso", "sample.atom_site.Fe.adp_iso");
        alias(project, "tensor", "sample.atom_site_aniso.Fe.adp_11");
        alias(project, "other", "other.atom_site.Fe.fract_x");
        project.structure().atom_sites[0]->id = "Fe1";
        CHECK_MESSAGE((project.aliases[0]->parameter_unique_name == "sample.atom_site.Fe1.fract_x"),
                      "GUI atom ID rename follows aliases with and without an anisotropic row");
        CHECK_MESSAGE((
            project.aliases[1]->parameter_unique_name == "sample.atom_site.Fe1.occupancy"),
            "GUI atom ID rename follows aliases with and without an anisotropic row");
        CHECK_MESSAGE((project.aliases[2]->parameter_unique_name == "sample.atom_site.Fe1.adp_iso"),
                      "GUI atom ID rename follows aliases with and without an anisotropic row");
        CHECK_MESSAGE((
            project.aliases[3]->parameter_unique_name == "sample.atom_site_aniso.Fe1.adp_11"),
            "GUI atom ID rename follows aliases with and without an anisotropic row");
        CHECK_MESSAGE((project.aliases[4]->parameter_unique_name == "other.atom_site.Fe.fract_x"),
                      "GUI atom ID rename follows aliases with and without an anisotropic row");
        if (anisotropic)
            CHECK_MESSAGE((
                project.structure().atom_site_aniso[0]->id == "Fe1"),
                "GUI atom ID rename follows aliases with and without an anisotropic row");
        edi::AtomSite taken;
        taken.id = "taken";
        project.structure().atom_sites.push_back(taken);
        CHECK_THROWS_AS_MESSAGE(
            project.structure().atom_sites[0]->id = "taken", std::invalid_argument,
            "GUI atom ID rename follows aliases with and without an anisotropic row");
        CHECK_MESSAGE((project.aliases[0]->parameter_unique_name == "sample.atom_site.Fe1.fract_x"),
                      "GUI atom ID rename follows aliases with and without an anisotropic row");
        CHECK_MESSAGE((
            project.aliases[3]->parameter_unique_name == "sample.atom_site_aniso.Fe1.adp_11"),
            "GUI atom ID rename follows aliases with and without an anisotropic row");
        if (anisotropic)
            CHECK_MESSAGE((
                project.structure().atom_site_aniso[0]->id == "Fe1"),
                "GUI atom ID rename follows aliases with and without an anisotropic row");
    }
}
