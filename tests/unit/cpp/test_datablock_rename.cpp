#include <doctest/doctest.h>

#include <string>
#include <vector>

#include "edi/edit.hpp"

namespace {
void relations(edi::Project& project, const std::string& name) {
    edi::ParameterAlias alias;
    alias.id = "a";
    alias.parameter_unique_name = name + ".atom_site.La.adp_iso";
    project.aliases.push_back(alias);
    alias.id = "unchanged";
    alias.parameter_unique_name = name + "0.atom_site.La.adp_iso";
    project.aliases.push_back(alias);
    edi::ParameterConstraint constraint;
    constraint.id = "c";
    constraint.expression = "a = 0.125";
    project.constraints.push_back(constraint);
    edi::FitParameterCorrelation pair;
    pair.id = "pair";
    pair.source_kind = "deterministic";
    pair.parameter_unique_name_i = name + ".atom_site.La.adp_iso";
    pair.parameter_unique_name_j = name + ".cell.length_a";
    pair.correlation = "-0.625";
    pair.file_path = "structure1.xy";
    project.fit_result.correlations.push_back(pair);
    edi::SequentialExtractRule rule;
    rule.id = "temperature";
    rule.target = name + ".diffrn.ambient_temperature";
    rule.pattern = "structure1=(.*)";
    project.sequential_fit.extract.push_back(rule);
}

std::vector<std::string> names(const edi::Project& project) {
    std::vector<std::string> result;
    for (const auto& alias : project.aliases)
        result.push_back(alias->parameter_unique_name.value());
    for (const auto& pair : project.fit_result.correlations) {
        result.push_back(pair->parameter_unique_name_i.value());
        result.push_back(pair->parameter_unique_name_j.value());
    }
    for (const auto& rule : project.sequential_fit.extract) result.push_back(rule->target.value());
    for (const auto& experiment : project.experiments) {
        for (const auto& row : experiment->linked_structures)
            result.push_back(row->structure_id.value());
        for (const auto& row : experiment->preferred_orientation)
            result.push_back(row->structure_id.value());
    }
    return result;
}

void check_relations(const edi::Project& project, const std::string& old_name,
                     const std::string& next) {
    CHECK_MESSAGE(
        project.aliases[0]->parameter_unique_name.value() == next + ".atom_site.La.adp_iso",
        "A datablock rename must follow the owner's La ADP alias");
    CHECK_MESSAGE(
        project.aliases[1]->parameter_unique_name.value() == old_name + "0.atom_site.La.adp_iso",
        "A rename must preserve a different datablock sharing the old name prefix");
    CHECK_MESSAGE(project.constraints[0]->expression.value() == "a = 0.125",
                  "A constraint continues using its alias and keeps its numerical expression");
    CHECK_MESSAGE(project.fit_result.correlations[0]->parameter_unique_name_i.value() ==
                      next + ".atom_site.La.adp_iso",
                  "The first correlation endpoint must follow its renamed datablock");
    CHECK_MESSAGE(project.fit_result.correlations[0]->parameter_unique_name_j.value() ==
                      next + ".cell.length_a",
                  "The second correlation endpoint must follow its renamed datablock");
    CHECK_MESSAGE(project.fit_result.correlations[0]->correlation.value() == "-0.625",
                  "Renaming preserves the measured correlation coefficient text");
    CHECK_MESSAGE(project.fit_result.correlations[0]->file_path.value() == "structure1.xy",
                  "A scan data filename is not a datablock reference");
    CHECK_MESSAGE(
        project.sequential_fit.extract[0]->target.value() == next + ".diffrn.ambient_temperature",
        "A scan extraction target must follow its renamed datablock");
    CHECK_MESSAGE(project.sequential_fit.extract[0]->pattern.value() == "structure1=(.*)",
                  "Renaming a datablock must preserve the scan's input matching expression");
    for (const auto& field : names(project)) {
        CHECK_MESSAGE((field != old_name && !field.starts_with(old_name + ".")),
                      "No name-bearing relation field may retain the renamed datablock identity");
    }
}
}  // namespace

TEST_CASE("Structure rename follows all relation categories and exact name boundaries") {
    edi::Project project;
    project.structure().name = "structure1";
    project.experiment().linked_structures[0]->structure_id = "structure1";
    edi::PrefOrient texture;
    texture.structure_id = "structure1";
    texture.march_r.value = .8125;
    project.experiment().preferred_orientation.push_back(texture);
    relations(project, "structure1");
    edi::Edit::structure_name(project.structure(), "lbco")();
    CHECK_MESSAGE(project.experiment().linked_structures[0]->structure_id.value() == "lbco",
                  "Every linked structure must follow the rename");
    CHECK_MESSAGE(project.experiment().preferred_orientation[0]->structure_id.value() == "lbco",
                  "Every preferred-orientation structure reference must follow the rename");
    CHECK_MESSAGE(project.experiment().preferred_orientation[0]->march_r.value == .8125,
                  "Renaming preserves the preferred-orientation value");
    check_relations(project, "structure1", "lbco");
}

TEST_CASE("Experiment rename follows all relation categories and exact name boundaries") {
    edi::Project project;
    project.experiment().name = "experiment1";
    relations(project, "experiment1");
    edi::Edit::rename_experiment(project, project.experiment(), "hrpt")();
    check_relations(project, "experiment1", "hrpt");
}

TEST_CASE("Refused datablock rename preserves every reference") {
    for (bool structure : {true, false}) {
        edi::Project project;
        if (structure) {
            project.structure().name = "old";
            edi::Structure taken;
            taken.name = "taken";
            project.structures.push_back(taken);
        } else {
            project.experiment().name = "old";
            edi::BraggPdExperiment taken;
            taken.name = "taken";
            project.experiments.push_back(taken);
        }
        relations(project, "old");
        const auto before = names(project);
        if (structure) {
            CHECK_THROWS_AS_MESSAGE(edi::Edit::structure_name(*project.structures[0], "taken")(),
                                    std::invalid_argument,
                                    "A colliding structure rename must be refused");
        } else {
            CHECK_THROWS_AS_MESSAGE(
                edi::Edit::rename_experiment(project, *project.experiments[0], "taken")(),
                edi::IoError, "A colliding experiment rename must be refused");
        }
        CHECK_MESSAGE(names(project) == before,
                      "A refused rename must preserve all relation identities");
    }
}

namespace {
void parameter_relations(edi::Project& project, const std::vector<std::string>& references) {
    int ordinal = 0;
    for (const auto& name : references) {
        edi::ParameterAlias alias;
        alias.id = "ref" + std::to_string(ordinal);
        alias.parameter_unique_name = name;
        project.aliases.push_back(alias);
        for (bool first : {true, false}) {
            edi::FitParameterCorrelation pair;
            pair.id = "pair" + std::to_string(ordinal) + (first ? "i" : "j");
            pair.source_kind = "deterministic";
            pair.parameter_unique_name_i = first ? name : "other.cell.length_a";
            pair.parameter_unique_name_j = first ? "other.cell.length_a" : name;
            pair.correlation = "-0.625";
            pair.file_path = "old.xy";
            project.fit_result.correlations.push_back(pair);
        }
        ++ordinal;
    }
}
void require_parameter_relations(const edi::Project& project,
                                 const std::vector<std::string>& expected) {
    for (std::size_t i = 0; i < expected.size(); ++i) {
        CHECK_MESSAGE(project.aliases[i]->parameter_unique_name.value() == expected[i],
                      "Every alias must follow the exact renamed identity position");
        CHECK_MESSAGE(
            project.fit_result.correlations[2 * i]->parameter_unique_name_i.value() == expected[i],
            "Every first correlation endpoint must follow the renamed identity");
        CHECK_MESSAGE(
            project.fit_result.correlations[2 * i + 1]->parameter_unique_name_j.value() ==
                expected[i],
            "Every second correlation endpoint must follow the renamed identity");
        CHECK_MESSAGE(project.fit_result.correlations[2 * i]->parameter_unique_name_j.value() ==
                          "other.cell.length_a",
                      "A rename must preserve endpoints owned by another identity");
        CHECK_MESSAGE(project.fit_result.correlations[2 * i]->correlation.value() == "-0.625",
                      "A reference rewrite must retain the exact coefficient text");
        CHECK_MESSAGE(project.fit_result.correlations[2 * i]->file_path.value() == "old.xy",
                      "A reference rewrite must retain the data filename");
    }
}
}  // namespace

TEST_CASE("Phase rename follows experiment-owned link and texture parameter references") {
    edi::Project project;
    project.structure().name = "old";
    project.experiment().name = "bank";
    project.experiment().linked_structures[0]->structure_id = "old";
    edi::PrefOrient texture;
    texture.structure_id = "old";
    project.experiment().preferred_orientation.push_back(texture);
    parameter_relations(
        project,
        {"bank.linked_structure.old.scale", "bank.preferred_orientation.old.march_r",
         "bank.preferred_orientation.old.march_random_fract", "bank.linked_structure.old0.scale"});
    edi::Edit::structure_name(project.structure(), "new_phase")();
    require_parameter_relations(
        project,
        {"bank.linked_structure.new_phase.scale", "bank.preferred_orientation.new_phase.march_r",
         "bank.preferred_orientation.new_phase.march_random_fract",
         "bank.linked_structure.old0.scale"});
}

TEST_CASE("Site and tensor key edits follow every coordinate and ADP reference") {
    for (bool tensor_key : {false, true}) {
        CAPTURE(tensor_key);
        edi::Project project;
        project.structure().name = "phase";
        edi::AtomSite site;
        site.id = "old";
        project.structure().atom_sites.push_back(site);
        edi::AtomSiteAniso tensor;
        tensor.id = "old";
        project.structure().atom_site_aniso.push_back(tensor);
        std::vector<std::string> before, after;
        for (const std::string field : {"fract_x", "fract_y", "fract_z", "occupancy", "adp_iso"}) {
            before.push_back("phase.atom_site.old." + field);
            after.push_back("phase.atom_site.new_site." + field);
        }
        for (const std::string field :
             {"adp_11", "adp_22", "adp_33", "adp_12", "adp_13", "adp_23"}) {
            before.push_back("phase.atom_site_aniso.old." + field);
            after.push_back("phase.atom_site_aniso.new_site." + field);
        }
        before.push_back("phase.atom_site.old0.fract_x");
        after.push_back(before.back());
        parameter_relations(project, before);
        if (tensor_key) {
            const auto held = names(project);
            CHECK_THROWS_AS_MESSAGE(
                project.structure().atom_site_aniso[0]->id = "new_site", std::invalid_argument,
                "A paired tensor's key cannot change independently of its site");
            CHECK_MESSAGE(names(project) == held,
                          "A refused standalone tensor rename must preserve every reference");
        }
        project.structure().atom_sites[0]->id = "new_site";
        require_parameter_relations(project, after);
        CHECK_MESSAGE(project.structure().atom_sites[0]->id.value() == "new_site",
                      "A tensor or site rename must keep their common identity bound");
        CHECK_MESSAGE(project.structure().atom_site_aniso[0]->id.value() == "new_site",
                      "A site or tensor rename must preserve the paired tensor identity");
    }
}

TEST_CASE("Point and coefficient key edits follow aliases and both endpoints") {
    for (bool point_key : {false, true}) {
        edi::Project project;
        project.experiment().name = "bank";
        project.experiment().background.clear();
        project.experiment().background_terms.clear();
        edi::LineSegment point;
        point.id = "old";
        project.experiment().background.push_back(point);
        edi::PolynomialTerm term;
        term.id = "old";
        project.experiment().background_terms.push_back(term);
        const std::string field = point_key ? "intensity" : "coef";
        parameter_relations(project,
                            {"bank.background.old." + field, "bank.background.old0." + field});
        if (point_key)
            project.experiment().background[0]->id = "new_row";
        else
            project.experiment().background_terms[0]->id = "new_row";
        require_parameter_relations(
            project, {"bank.background.new_row." + field, "bank.background.old0." + field});
    }
}
