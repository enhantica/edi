#include <doctest/doctest.h>

#include <array>
#include <functional>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "canonical_encoding.hpp"
#include "edi/model.hpp"
#include "edi/validation.hpp"
#include "fit_policy.hpp"
#include "parameter_paths.hpp"

namespace {

crysta::Project empty_phase_project() {
    auto phase = crysta::structure_from_edi_text(
        "data_structure\n_cell.length_a 2.2\n_cell.length_b 3.1\n_cell.length_c 4.3\n"
        "_cell.angle_alpha 90\n_cell.angle_beta 90\n_cell.angle_gamma 90\n"
        "_space_group.name_h_m \"P 1\"\nloop_\n_atom_site.id\n_atom_site.type_symbol\n"
        "_atom_site.wyckoff_letter\n_atom_site.adp_type\n_atom_site.fract_x\n"
        "_atom_site.fract_y\n_atom_site.fract_z\n_atom_site.occupancy\n_atom_site.adp_iso\n"
        "X Gd a Biso 0 0 0 0.7 0\n");
    phase.atom_sites.clear();
    const auto bank = crysta::experiment_from_edi_text(
        "data_bank\n_experiment_type.sample_form powder\n"
        "_experiment_type.radiation_probe neutron\n_experiment_type.scattering_type bragg\n"
        "_experiment_type.beam_mode \"constant wavelength\"\n_peak.type cwl-tch-pseudo-voigt\n"
        "_peak.broad_gauss_u 0\n_peak.broad_gauss_v 0\n_peak.broad_gauss_w 0.01\n"
        "_peak.broad_lorentz_x 0\n_peak.broad_lorentz_y 0\n_peak.cutoff_fwhm 5\n"
        "_instrument.calib_twotheta_offset 0\n_instrument.setup_wavelength 1.54\n"
        "loop_\n_linked_structure.structure_id\n"
        "_linked_structure.scale\nstructure 1.125\n");
    return crysta::Project(phase, bank);
}

void check_invalid(const std::function<void()>& action, const std::string& fragment,
                   const char* requirement) {
    INFO(requirement);
    bool raised = false;
    try {
        action();
    } catch (const std::invalid_argument& error) {
        raised = true;
        CHECK_MESSAGE(std::string(error.what()).find(fragment) != std::string::npos,
                      "the invalid request must contain its required diagnostic fragment");
    }
    CHECK_MESSAGE(raised, "the invalid-request helper must observe std::invalid_argument");
}

edi::Structure one_site_structure(const std::string& label = "Si") {
    edi::Structure structure;
    structure.name = "silicon";
    structure.space_group.name_h_m = "F d -3 m";
    structure.atom_sites.push_back(edi::AtomSite{});
    structure.atom_sites.back()->id = label;
    structure.atom_sites.back()->type_symbol = "Si";
    return structure;
}

edi::PdDataBase measured_pattern() {
    edi::PdDataBase pattern;
    pattern.time_of_flight = std::vector<double>{1.0, 2.0};
    pattern.intensity_meas = {10.0, 20.0};
    pattern.intensity_meas_su = {1.0, 2.0};
    return pattern;
}

}  // namespace

TEST_CASE("E09-T55 parameter paths resolve the documented engine label grammar") {
    edi::Structure structure = one_site_structure();
    edi::ExperimentBase experiment;
    experiment.background.push_back(edi::LineSegment{});
    experiment.background.push_back(edi::LineSegment{});
    experiment.background[0]->position = 10.0;
    experiment.background[0]->intensity = edi::Parameter{4.0};
    experiment.background[1]->position = 20.0;
    experiment.background[1]->intensity = edi::Parameter{5.0};

    const std::array<std::pair<const char*, const char*>, 18> required{{
        {"calib_d_to_tof_offset", "experiment.instrument.calib_d_to_tof_offset"},
        {"calib_d_to_tof_linear", "experiment.instrument.calib_d_to_tof_linear"},
        {"calib_d_to_tof_quadratic", "experiment.instrument.calib_d_to_tof_quadratic"},
        {"calib_d_to_tof_reciprocal", "experiment.instrument.calib_d_to_tof_reciprocal"},
        {"rise_alpha_0", "experiment.peak.rise_alpha_0"},
        {"rise_alpha_1", "experiment.peak.rise_alpha_1"},
        {"decay_beta_0", "experiment.peak.decay_beta_0"},
        {"decay_beta_1", "experiment.peak.decay_beta_1"},
        {"broad_gauss_sigma_0", "experiment.peak.broad_gauss_sigma_0"},
        {"broad_gauss_sigma_1", "experiment.peak.broad_gauss_sigma_1"},
        {"broad_gauss_sigma_2", "experiment.peak.broad_gauss_sigma_2"},
        {"broad_gauss_size", "experiment.peak.broad_gauss_size"},
        {"broad_gauss_strain", "experiment.peak.broad_gauss_strain"},
        {"broad_lorentz_gamma_0", "experiment.peak.broad_lorentz_gamma_0"},
        {"broad_lorentz_gamma_1", "experiment.peak.broad_lorentz_gamma_1"},
        {"broad_lorentz_gamma_2", "experiment.peak.broad_lorentz_gamma_2"},
        {"broad_lorentz_size", "experiment.peak.broad_lorentz_size"},
        {"broad_lorentz_strain", "experiment.peak.broad_lorentz_strain"},
    }};
    for (const auto& [label, path] : required) {
        const auto resolved = edi::detail::resolve_label(structure, experiment, label);
        REQUIRE_MESSAGE(resolved.has_value(),
                        "every documented required engine label must resolve");
        CHECK_MESSAGE(resolved->path == path,
                      "a required engine label must retain its public identity path");
    }

    const auto background = edi::detail::resolve_label(structure, experiment, "background[1]");
    REQUIRE_MESSAGE(background.has_value(), "an in-range background label must resolve");
    CHECK_MESSAGE(background->target == &experiment.background[1]->intensity,
                  "a background label must target the indexed intensity");
    CHECK_MESSAGE(background->path == "experiment.background[1].intensity",
                  "a background label must use the documented indexed identity path");
    CHECK_MESSAGE(!edi::detail::resolve_label(structure, experiment, "background[2]"),
                  "an out-of-range background label must fail closed");

    const auto scale = edi::detail::resolve_label(structure, experiment, "scale");
    REQUIRE_MESSAGE(scale.has_value(), "the linked-structure scale label must resolve");
    CHECK_MESSAGE(scale->target == &experiment.linked_structure().scale,
                  "scale must target the linked-structure scale parameter");
}

TEST_CASE("E09-T55 optional and structural parameter identities fail closed") {
    edi::Structure structure = one_site_structure("Si1");
    edi::ExperimentBase experiment;
    const std::array<const char*, 8> optional_labels{{
        "calib_twotheta_offset",
        "setup_wavelength",
        "broad_gauss_u",
        "broad_gauss_v",
        "broad_gauss_w",
        "broad_lorentz_x",
        "broad_lorentz_y",
        "abscor1",
    }};
    for (const char* label : optional_labels) {
        CHECK_MESSAGE(!edi::detail::resolve_label(structure, experiment, label),
                      "an absent presence-tracked field must not acquire a write-back target");
    }
    experiment.instrument.calib_twotheta_offset = edi::Parameter{1.0};
    experiment.instrument.setup_wavelength = edi::Parameter{1.54};
    experiment.peak.broad_gauss_u = edi::Parameter{0.1};
    experiment.peak.broad_gauss_v = edi::Parameter{0.2};
    experiment.peak.broad_gauss_w = edi::Parameter{0.3};
    experiment.peak.broad_lorentz_x = edi::Parameter{0.4};
    experiment.peak.broad_lorentz_y = edi::Parameter{0.5};
    experiment.absorption.abscor1 = edi::Parameter{0.6};
    for (const char* label : optional_labels) {
        CHECK_MESSAGE(edi::detail::resolve_label(structure, experiment, label).has_value(),
                      "an engaged presence-tracked field must resolve");
    }

    const std::array<std::pair<const char*, const char*>, 11> structural{{
        {"cell_length_a", "structure.cell.length_a"},
        {"cell_length_b", "structure.cell.length_b"},
        {"cell_length_c", "structure.cell.length_c"},
        {"cell_angle_alpha", "structure.cell.angle_alpha"},
        {"cell_angle_beta", "structure.cell.angle_beta"},
        {"cell_angle_gamma", "structure.cell.angle_gamma"},
        {"Si1.fract_x", "structure.atom_sites[Si1].fract_x"},
        {"Si1.fract_y", "structure.atom_sites[Si1].fract_y"},
        {"Si1.fract_z", "structure.atom_sites[Si1].fract_z"},
        {"Si1.adp_iso", "structure.atom_sites[Si1].adp_iso"},
        {"Si1.occupancy", "structure.atom_sites[Si1].occupancy"},
    }};
    for (const auto& [label, path] : structural) {
        const auto resolved = edi::detail::resolve_structural_label(structure, label);
        REQUIRE_MESSAGE(resolved.has_value(),
                        "every documented structural engine label must resolve");
        CHECK_MESSAGE(resolved->path == path,
                      "a structural engine label must retain its stable public identity path");
    }
    CHECK_MESSAGE(!edi::detail::resolve_structural_label(structure, "missing.fract_x"),
                  "an unknown site label must fail closed");
    CHECK_MESSAGE(!edi::detail::resolve_structural_label(structure, "Si1.unknown"),
                  "an unknown structural field must fail closed");
    CHECK_MESSAGE(!edi::detail::resolve_structural_label(structure, "not_a_label"),
                  "an unknown unqualified label must fail closed");
}

TEST_CASE("E09-T55 joint parameter identities use longest bank prefix and project size") {
    edi::Structure structure = one_site_structure();
    edi::ItemVec<edi::BraggPdExperiment> banks;
    edi::BraggPdExperiment bank;
    bank.name = "bank";
    banks.push_back(std::move(bank));
    edi::BraggPdExperiment long_bank;
    long_bank.name = "bank.long";
    banks.push_back(std::move(long_bank));
    const auto longest =
        edi::detail::resolve_joint_label(structure, banks, "bank.long.calib_d_to_tof_linear");
    REQUIRE_MESSAGE(longest.has_value(), "the longest matching bank prefix must resolve");
    CHECK_MESSAGE(longest->path == "experiments[bank.long].instrument.calib_d_to_tof_linear",
                  "joint identity must retain the complete bank name");
    CHECK_MESSAGE(!edi::detail::resolve_joint_label(structure, banks, "calib_d_to_tof_linear"),
                  "a multi-bank instrument label must never fall back to bank zero");

    banks.clear();
    edi::BraggPdExperiment single_bank;
    single_bank.name = "bank";
    banks.push_back(std::move(single_bank));
    const auto single =
        edi::detail::resolve_joint_label(structure, banks, "calib_d_to_tof_linear");
    REQUIRE_MESSAGE(single.has_value(),
                    "a one-bank joint project must accept unprefixed engine labels");
    CHECK_MESSAGE(single->path == "experiments[bank].instrument.calib_d_to_tof_linear",
                  "a one-bank joint identity must still carry its bank name");
    const auto shared = edi::detail::resolve_joint_label(structure, banks, "Si.fract_x");
    REQUIRE_MESSAGE(shared.has_value(),
                    "shared structural labels must resolve in a joint project");
    CHECK_MESSAGE(shared->path == "structure.atom_sites[Si].fract_x",
                  "joint structural identity must remain shared and unprefixed");
}

TEST_CASE("E09-T55 refinement policy rejects ambiguous identities and malformed data") {
    edi::Structure structure = one_site_structure();
    // Before: call the unused private validator, including its obsolete spelling policy.
    // After  D11/U6: in-memory strings remain free; storage owns uniqueness,
    // and the retired validator is not a supported admission entry.
    for (const std::string label : {std::string{}, std::string{"Si.1"}}) {
        const auto named = one_site_structure(label);
        CHECK_MESSAGE(std::string(named.atom_sites[0]->id) == label,
                      " in-memory site identities preserve their exact strings");
    }
    check_invalid([&] { structure.atom_sites.push_back(*structure.atom_sites.front()); }, "Si",
                  " duplicate site admission refuses the named identity");
    CHECK_MESSAGE(structure.atom_sites.size() == 1,
                  " duplicate admission preserves original site storage");

    edi::Project valid;
    *valid.structures.front() = one_site_structure();
    edi::detail::validate_fit_request({1.0}, {2.0}, {1.0}, valid);
    check_invalid([&] { edi::detail::validate_fit_request({}, {2.0}, {1.0}, valid); },
                  "empty measured data", "empty refinement data must be rejected");
    check_invalid([&] { edi::detail::validate_fit_request({1.0, 2.0}, {2.0}, {1.0}, valid); },
                  "equal length", "ragged refinement data must be rejected");
    auto empty_structure = empty_phase_project();
    check_invalid(
        [&] { edi::detail::require_populated_participants(empty_structure, "single fit"); },
        "no atom sites", "an active participant without sites must be rejected");
}

TEST_CASE("E09-T55 joint refinement policy validates every bank identity and pattern") {
    edi::Project structure;
    *structure.structures.front() = one_site_structure("Si");
    edi::ItemVec<edi::BraggPdExperiment> banks;
    edi::BraggPdExperiment bank;
    bank.name = "bank1";
    banks.push_back(std::move(bank));
    std::vector<edi::PdDataBase> patterns{measured_pattern()};
    edi::detail::validate_joint_request(structure, banks, patterns);

    const edi::ItemVec<edi::BraggPdExperiment> no_banks;
    check_invalid([&] { edi::detail::validate_joint_request(structure, no_banks, {}); },
                  "no experiments", "a joint fit without banks must be rejected");
    check_invalid([&] { edi::detail::validate_joint_request(structure, banks, {}); },
                  "one measured pattern", "the pattern count must equal the bank count");
    auto empty_structure = empty_phase_project();
    check_invalid(
        [&] { edi::detail::require_populated_participants(empty_structure, "joint fit"); },
        "no atom sites", "a joint active participant without sites must be rejected");

    for (const std::string& bad_name :
         {std::string{}, std::string{"bad.name"}, std::string{"Si"}}) {
        banks[0]->name = bad_name;
        check_invalid([&] { edi::detail::validate_joint_request(structure, banks, patterns); },
                      bad_name.empty() ? "empty name"
                                       : (bad_name == "Si" ? "collides" : "reserved delimiter"),
                      "an ambiguous bank identity must be rejected");
    }
    banks.clear();
    edi::BraggPdExperiment duplicate_one;
    duplicate_one.name = "same";
    banks.push_back(std::move(duplicate_one));
    edi::BraggPdExperiment duplicate_two;
    duplicate_two.name = "same";
    // Before: admit duplicate banks and refuse at joint validation. After:
    // storage rejects the duplicate immediately and the surviving bank remains usable.
    check_invalid([&] { banks.push_back(std::move(duplicate_two)); }, "same",
                  " duplicate bank admission refuses the named identity");
    CHECK_MESSAGE(banks.size() == 1,
                  " refused duplicate bank leaves original membership unchanged");
    CHECK_NOTHROW_MESSAGE(edi::detail::validate_joint_request(structure, banks, patterns),
                          " joint admission remains usable after duplicate refusal");

    banks.clear();
    edi::BraggPdExperiment valid_bank;
    valid_bank.name = "bank1";
    banks.push_back(std::move(valid_bank));
    patterns = {edi::PdDataBase{}};
    check_invalid([&] { edi::detail::validate_joint_request(structure, banks, patterns); },
                  "exactly one", "a bank with no axis must be rejected");
    patterns = {measured_pattern()};
    auto ragged_values = static_cast<const std::vector<double>&>(patterns[0].intensity_meas);
    ragged_values.pop_back();
    patterns[0].intensity_meas = std::move(ragged_values);
    check_invalid([&] { edi::detail::validate_joint_request(structure, banks, patterns); },
                  "equal length", "ragged bank data must be rejected");
}

TEST_CASE("E09-T55 refinement bounds and write-back preserve their documented invariants") {
    CHECK_MESSAGE(edi::detail::reduced_chi_square_dof(10, 3) == 7.0,
                  "reduced chi-square degrees of freedom must be n_data minus n_free");
    CHECK_MESSAGE(edi::detail::reduced_chi_square_dof(3, 3) == 1.0,
                  "reduced chi-square degrees of freedom must be clamped to one");
    CHECK_MESSAGE(edi::detail::reduced_chi_square_dof(2, 3) == 1.0,
                  "an over-parameterized fit must still use one degree of freedom");
    CHECK_MESSAGE(edi::detail::bounded_max_iterations(12) == 12,
                  "a positive declared iteration bound must be retained");
    CHECK_MESSAGE(edi::detail::bounded_max_iterations(0) == 50,
                  "an absent iteration bound must use the documented cap of 50");
    CHECK_MESSAGE(edi::detail::bounded_max_iterations(-1) == 50,
                  "an invalid negative iteration bound must use the documented cap of 50");

    edi::Parameter parameter{1.0, 0.5};
    edi::detail::write_back({{{&parameter, "structure.cell.length_a"}, 2.0, 0.25}});
    CHECK_MESSAGE(parameter.value == 2.0, "write-back must update the resolved parameter value");
    REQUIRE_MESSAGE(parameter.uncertainty.has_value(),
                    "write-back must retain a standard uncertainty");
    CHECK_MESSAGE(*parameter.uncertainty == 0.25,
                  "write-back must update the resolved parameter uncertainty");
}

TEST_CASE("E09-T55 canonical encoding detects calculation-affecting mutations") {
    edi::Project project;
    project.structures.clear();
    project.structures.push_back(one_site_structure());
    // : rename the first default before inserting another default.
    // The resulting two-bank fixture and every encoding assertion stay the same.
    project.experiments[0]->name = "bank";
    project.experiments.push_back(edi::BraggPdExperiment{});
    project.experiments[0]->background.push_back(edi::LineSegment{});
    project.experiments[0]->background[0]->position = 10.0;
    project.experiments[0]->background[0]->intensity = edi::Parameter{2.0};
    project.fitting_mode = "single";
    const std::string baseline = edi::detail::canonical_encoding(project);
    CHECK_MESSAGE(!baseline.empty(),
                  "the canonical source encoding must represent a non-empty project");

    const auto distinct_after = [&](const std::function<void(edi::Project&)>& mutation) {
        edi::Project changed = project;
        mutation(changed);
        return edi::detail::canonical_encoding(changed) != baseline;
    };
    CHECK_MESSAGE(
        distinct_after([](edi::Project& p) { p.structures[0]->cell.length_a.value = 2.0; }),
        "a cell mutation must invalidate the canonical source encoding");
    CHECK_MESSAGE(
        distinct_after([](edi::Project& p) { p.structures[0]->atom_sites[0]->id = "Si2"; }),
        "a site-identity mutation must invalidate the canonical source encoding");
    CHECK_MESSAGE(distinct_after([](edi::Project& p) {
                      auto values = static_cast<const std::map<std::string, double>&>(
                          p.structures[0]->scattering_lengths_fm);
                      values["Si"] = 4.1491;
                      p.structures[0]->scattering_lengths_fm = std::move(values);
                  }),
                  "a scattering-length mutation must invalidate the canonical source encoding");
    CHECK_MESSAGE(
        distinct_after([](edi::Project& p) { p.experiments[0]->peak.type = "tof-jorgensen"; }),
        "a peak-type mutation must invalidate the canonical source encoding");
    CHECK_MESSAGE(distinct_after([](edi::Project& p) {
                      p.experiments[0]->experiment_type.beam_mode =
                          edi::BeamModeEnum::TIME_OF_FLIGHT;
                  }),
                  "an explicit beam-mode mutation must invalidate the canonical source encoding");
    CHECK_MESSAGE(
        distinct_after([](edi::Project& p) {
            p.experiments[0]->instrument.setup_wavelength = edi::Parameter{1.54};
        }),
        "engaging an optional instrument parameter must invalidate the canonical source encoding");
    CHECK_MESSAGE((distinct_after([](edi::Project& p) {
                      auto values =
                          edi::excluded_region_ranges(p.experiments[0]->excluded_regions);
                      values.emplace_back(1.0, 2.0);
                      p.experiments[0]->excluded_regions = edi::excluded_region_rows(values);
                  })),
                  "an excluded-region mutation must invalidate the canonical source encoding");
    CHECK_MESSAGE(distinct_after([](edi::Project& p) { p.fitting_mode = "joint"; }),
                  "a fitting-mode mutation must invalidate the canonical source encoding");

    edi::Project changed_data = project;
    changed_data.experiments[0]->data = measured_pattern();
    CHECK_MESSAGE(edi::detail::canonical_encoding(changed_data) == baseline,
                  "measured observations must not alter the calculation-source encoding");
}

TEST_CASE("E09-T55 validation errors retain tier, code, path, and message") {
    const auto verify = [](const std::function<void()>& action, int tier, const std::string& code,
                           const char* requirement) {
        INFO(requirement);
        bool raised = false;
        try {
            action();
        } catch (const edi::ValidationError& error) {
            raised = true;
            CHECK_MESSAGE(error.tier() == tier,
                          "the validation exception must retain its required tier");
            REQUIRE_MESSAGE(error.diagnostics().size() == 1,
                            "the validation exception must carry exactly one diagnostic");
            CHECK_MESSAGE(error.diagnostics()[0].code == code,
                          "the validation diagnostic must retain its required code");
            CHECK_MESSAGE(error.diagnostics()[0].path == "fixture.edi",
                          "the validation diagnostic must retain its source path");
            CHECK_MESSAGE(error.diagnostics()[0].severity == edi::Severity::Error,
                          "the validation diagnostic must retain error severity");
            CHECK_MESSAGE(std::string(error.what()).find("broken value") != std::string::npos,
                          "the validation exception must retain its explanatory message");
        }
        CHECK_MESSAGE(raised, "the validation helper must observe edi::ValidationError");
    };
    verify([] { edi::fail_syntax("fixture.edi", "token", "broken value"); }, 1, "edi.syntax.token",
           "syntax failures must retain their structured diagnostic");
    verify([] { edi::fail_schema("fixture.edi", "number", "broken value"); }, 2,
           "edi.schema.number", "schema failures must retain their structured diagnostic");
    verify([] { edi::fail_domain("fixture.edi", "range", "broken value"); }, 3, "edi.domain.range",
           "domain failures must retain their structured diagnostic");
    CHECK_MESSAGE(std::string(edi::severity_name(edi::Severity::Error)) == "error",
                  "error severity must have its stable lowercase name");
    CHECK_MESSAGE(std::string(edi::severity_name(edi::Severity::Warning)) == "warning",
                  "warning severity must have its stable lowercase name");
    CHECK_MESSAGE(std::string(edi::severity_name(edi::Severity::Info)) == "info",
                  "info severity must have its stable lowercase name");
}

TEST_CASE("E09-T55 one-call refinement sourcing fails closed without observations") {
    edi::Project project;
    project.structure().atom_sites.push_back(edi::AtomSite{});
    check_invalid(
        [&] { static_cast<void>(project.fit()); }, "carries no measured data",
        "single-bank one-call refinement must refuse an experiment without observations");
    check_invalid(
        [&] { static_cast<void>(project.fit(edi::IterationCallback{}, edi::PreambleCallback{})); },
        "carries no measured data",
        "the callback overload must share the one-call observation guard");

    project.experiment().data = measured_pattern();
    project.experiment().calculation_only = true;
    check_invalid([&] { static_cast<void>(project.fit()); }, "carries no measured data",
                  "a calculation-only grid must never be treated as observations");

    project.experiments.clear();
    check_invalid([&] { static_cast<void>(project.fit_joint()); }, "no experiments",
                  "joint one-call refinement must refuse a project without banks");
    project.experiments.push_back(edi::BraggPdExperiment{});
    project.experiments[0]->name = "bank";
    check_invalid(
        [&] {
            static_cast<void>(
                project.fit_joint(edi::IterationCallback{}, edi::PreambleCallback{}));
        },
        "carries no measured data",
        "the joint callback overload must refuse a bank without observations");
    project.experiments[0]->data = measured_pattern();
    project.experiments[0]->calculation_only = true;
    check_invalid([&] { static_cast<void>(project.fit_joint()); }, "carries no measured data",
                  "joint refinement must reject any calculation-only bank");
}

TEST_CASE("E09-T55 singular project views fail closed on empty collections") {
    edi::Project project;
    project.structures.clear();
    check_invalid([&] { static_cast<void>(project.structure()); }, "no structure",
                  "a mutable singular structure view must refuse an empty collection");
    const edi::Project& const_project = project;
    check_invalid([&] { static_cast<void>(const_project.structure()); }, "no structure",
                  "a const singular structure view must refuse an empty collection");

    edi::Structure structure;
    project.structures.push_back(std::move(structure));
    project.experiments.clear();
    check_invalid([&] { static_cast<void>(project.experiment()); }, "no experiment",
                  "a mutable singular experiment view must refuse an empty collection");
    check_invalid([&] { static_cast<void>(const_project.experiment()); }, "no experiment",
                  "a const singular experiment view must refuse an empty collection");
}
