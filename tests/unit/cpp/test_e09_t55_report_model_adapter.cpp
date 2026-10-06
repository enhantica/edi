#include <doctest/doctest.h>

#include <algorithm>
#include <array>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "adapter_test_access.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/report.hpp"

namespace {

void check_contains(const std::string& text, const std::string& fragment,
                    const char* requirement) {
    INFO(requirement);
    INFO(text);
    INFO(fragment);
    CHECK_MESSAGE(text.find(fragment) != std::string::npos,
                  "the rendered report must contain its required fragment");
}

}  // namespace

TEST_CASE("E09-T55 human report renders the documented stream and summary facts") {
    edi::FitPreamble single;
    single.n_points_loaded = 120;
    single.n_points_fitted = 100;
    single.n_free = 3;
    single.pre_fit = {0, 0.25, 2.5, 0.0, 0};
    const std::string single_header = edi::stream_header(single, "demo");
    check_contains(single_header, "edi fit: project demo, 100 pts fitted / 120 loaded, 3 free",
                   "the single-bank header must distinguish fitted and loaded point counts");
    check_contains(single_header, "0.2500", "the stream header must include the pre-fit Rwp");
    check_contains(single_header, "2.5000",
                   "the stream header must include pre-fit reduced chi-square");

    edi::FitPreamble joint = single;
    joint.joint = true;
    joint.banks = {"bank-a", "bank-b"};
    const std::string joint_header = edi::stream_header(joint, "demo");
    check_contains(joint_header, "joint project demo, 2 banks (bank-a, bank-b)",
                   "the joint header must name every participating bank");
    joint.banks.resize(1);
    check_contains(edi::stream_header(joint, "demo"), "1 bank (bank-a)",
                   "the one-bank joint header must use the singular label");

    edi::FitResultBase outcome;
    outcome.converged = true;
    outcome.iterations = 7;
    outcome.reduced_chi_square = 1.25;
    outcome.rwp = 0.125;
    outcome.elapsed_ms = 2500.0;
    const std::string summary = edi::summary_line(outcome);
    check_contains(summary, "converged", "the summary must state convergence");
    check_contains(summary, "7 iters", "the summary must state the engine iteration count");
    check_contains(summary, "reduced χ² 1.2500", "the summary must state reduced chi-square");
    check_contains(summary, "Rwp 0.1250", "the summary must state Rwp");
    check_contains(summary, "2.5 s", "the summary must render elapsed milliseconds as seconds");
    outcome.converged = false;
    check_contains(edi::summary_line(outcome), "not converged",
                   "a non-converged outcome must be labelled explicitly");
}

TEST_CASE("E09-T55 report tables retain identity paths, starts, uncertainties, and bank metrics") {
    edi::FitResultBase outcome;
    outcome.values = {{"experiment.scale", 2.0}, {"structure.cell.length_a", 5.0}};
    outcome.start = {{"experiment.scale", 1.0}};
    outcome.uncertainty = {{"experiment.scale", 0.25}};
    outcome.banks = {{"bank-a", 10, 0.1, 1.0}, {"bank-b", 20, 0.2, 2.0}};
    const std::string table = edi::parameter_table(outcome);
    check_contains(table, "per-bank Rwp:   bank-a 0.1000   bank-b 0.2000",
                   "the full report must carry each engine-provided bank Rwp");
    check_contains(table, "refined parameters (2 free)",
                   "the parameter heading must match the displayed identity-path count");
    check_contains(table, "experiment.scale", "the human report must use edi identity paths");
    check_contains(table, "1.00000", "an explicitly recorded pre-fit value must be displayed");
    check_contains(table, "2.00000", "the refined value must be displayed");
    check_contains(table, "0.25000", "the engine-provided uncertainty must be displayed");
    check_contains(table, "100.0% ↑",
                   "the change column must use the documented start denominator");
    check_contains(table, "structure.cell.length_a",
                   "the table must include every refined structural identity path");

    outcome.banks.clear();
    CHECK_MESSAGE(edi::parameter_table(outcome).find("per-bank") == std::string::npos,
                  "a single-bank result must not invent per-bank metrics");
}

TEST_CASE("E09-T55 iteration and machine reports preserve engine-carried facts") {
    const edi::IterationRecord iteration{4, 0.125, 1.5, 2250.0, 3};
    const std::string human = edi::iteration_line(iteration, 2.0);
    check_contains(human, "4", "an iteration row must carry the iteration number");
    check_contains(human, "2.25", "an iteration row must convert elapsed milliseconds to seconds");
    check_contains(human, "0.1250", "an iteration row must carry Rwp");
    check_contains(human, "1.5000", "an iteration row must carry reduced chi-square");
    check_contains(human, "25.0% ↓", "an iteration row must show change from the previous metric");

    const std::string progress = edi::progress_report(iteration);
    check_contains(progress, "record=progress", "machine progress must identify its record kind");
    check_contains(progress, "iter=4", "machine progress must carry the iteration number");

    edi::Project project;
    edi::FitResultBase outcome;
    outcome.status = edi::FitStatus::MAX_ITER;
    outcome.converged = false;
    outcome.n_points_loaded = 12;
    outcome.n_points_fitted = 10;
    outcome.iterations = 1;
    outcome.descent = "lm";
    outcome.reduced_chi_square = 1.5;
    outcome.rwp = 0.125;
    outcome.unevaluable_trials = 8;
    outcome.terminal_unevaluable_trials = 2;
    outcome.elapsed_ms = 2250.0;
    outcome.engine_values = {{"scale", 2.0}};
    outcome.engine_uncertainty = {{"scale", 0.1}};
    edi::IterationRecord machine_iteration = iteration;
    machine_iteration.iteration = 1;
    outcome.iterations_history = {machine_iteration};
    outcome.banks = {{"bank-a", 10, 0.125, 15.0}};
    const std::string machine = edi::machine_report(project, outcome, edi::VerbosityEnum::FULL);
    check_contains(machine, "record=fit", "the machine fit must identify its record kind");
    check_contains(machine, "status=max_iter", "the machine fit must retain its terminal status");
    check_contains(machine, "mode=joint", "a result with bank metrics must identify joint mode");
    check_contains(machine, "param.scale.value=2",
                   "the machine fit must use engine parameter labels");
    check_contains(machine, "unevaluable_trials=8",
                   "the machine fit must retain total boundary-contact diagnostics");
    CHECK_MESSAGE(edi::machine_report(project, outcome, edi::VerbosityEnum::OFF).empty(),
                  "OFF verbosity must produce no machine output");

    check_contains(edi::error_report(edi::VerbosityEnum::COMPACT), "record=error",
                   "a compact machine failure must be a well-formed error record");
    CHECK_MESSAGE(edi::error_report(edi::VerbosityEnum::OFF).empty(),
                  "OFF verbosity must produce no machine failure output");
}

TEST_CASE("E09-T55 model collections expose all parameters and only the free subset") {
    edi::Project project;
    project.structure().atom_sites.push_back(edi::AtomSite{});
    project.experiment().background.push_back(edi::LineSegment{});
    project.experiment().background.push_back(edi::LineSegment{});
    project.experiment().peak.broad_gauss_u = edi::Parameter{0.1};
    project.experiment().instrument.setup_wavelength = edi::Parameter{1.54};
    project.experiment().absorption.abscor1 = edi::Parameter{0.2};
    std::vector<edi::Parameter*> all = project.parameters();
    CHECK_MESSAGE(
        all.size() > 20,
        "the project parameter view must include structural and experiment category leaves");
    project.structure().cell.length_a.free = true;
    project.structure().atom_sites[0]->occupancy.free = true;
    project.experiment().background[1]->intensity.free = true;
    const std::vector<edi::Parameter*> free = project.free_parameters();
    CHECK_MESSAGE(free.size() == 3,
                  "the project free-parameter view must filter by the free flag");
    CHECK_MESSAGE(
        std::find(free.begin(), free.end(), &project.structure().cell.length_a) != free.end(),
        "the free view must retain a free cell parameter");
    CHECK_MESSAGE(std::find(free.begin(), free.end(),
                            &project.experiment().background[1]->intensity) != free.end(),
                  "the free view must retain a free background parameter");

    edi::PdDataBase pattern;
    bool none_raised = false;
    try {
        static_cast<void>(pattern.axis());
    } catch (const std::invalid_argument&) {
        none_raised = true;
    }
    CHECK_MESSAGE(none_raised, "a measured pattern with no axis must fail closed");
    pattern.two_theta = std::vector<double>{1.0};
    pattern.time_of_flight = std::vector<double>{2.0};
    bool both_raised = false;
    try {
        static_cast<void>(pattern.axis());
    } catch (const std::invalid_argument&) {
        both_raised = true;
    }
    CHECK_MESSAGE(both_raised, "a measured pattern with two axes must fail closed");
}

TEST_CASE("E09-T55 adapter conversion preserves values, uncertainties, freedom, and order") {
    edi::Cell cell;
    cell.length_a = {7.1, 0.01, true};
    cell.length_b = {8.2, 0.02, false};
    cell.length_c = {9.3, 0.03, true};
    cell.angle_alpha = {78.5, 0.04, false};
    cell.angle_beta = {91.25, 0.05, true};
    cell.angle_gamma = {103.75, 0.06, false};
    const crysta::Cell converted_cell = edi::detail::to_crysta_cell(cell);
    REQUIRE_MESSAGE(converted_cell.parameters.size() == 6,
                    "the adapter must preserve all six independently recorded cell parameters");
    const std::array<double, 6> expected{{7.1, 8.2, 9.3, 78.5, 91.25, 103.75}};
    for (std::size_t i = 0; i < expected.size(); ++i) {
        CHECK_MESSAGE(converted_cell.parameters[i].value() == expected[i],
                      "the adapter must preserve cell parameter order and value");
        CHECK_MESSAGE(converted_cell.parameters[i].uncertainty() == 0.01 * (i + 1),
                      "the adapter must preserve cell parameter uncertainty");
        CHECK_MESSAGE(converted_cell.parameters[i].free() == (i % 2 == 0),
                      "the adapter must preserve cell parameter freedom");
    }

    edi::AtomSite atom;
    atom.id = "Na1";
    atom.type_symbol = "Na";
    atom.wyckoff_letter = "a";
    atom.fract_x = {0.137, 0.007, true};
    atom.fract_y = {0.281, 0.008, false};
    atom.fract_z = {0.419, 0.009, true};
    atom.occupancy = {0.73, 0.01, false};
    atom.adp_iso = {1.27, 0.02, true};
    edi::ItemVec<edi::AtomSite> atoms;
    atoms.push_back(std::move(atom));
    const std::vector<crysta::AtomSite> sites = edi::detail::to_crysta_atom_sites(atoms);
    REQUIRE_MESSAGE(sites.size() == 1, "one edi atom site must produce one engine atom site");
    CHECK_MESSAGE((sites[0].site_id == "Na1" && sites[0].type_symbol == "Na"),
                  "the adapter must preserve atom identity and element");
    CHECK_MESSAGE((sites[0].fract[0].value() == 0.137 && sites[0].adp_iso.value() == 1.27),
                  "the adapter must preserve independently recorded site coordinates and Biso");
}

TEST_CASE("E09-T55 adapter conversion preserves the complete TOF experiment layout") {
    edi::BraggPdExperiment source;
    source.name = "bank-a";
    source.peak.type = "tof-jorgensen-von-dreele";
    source.experiment_type.beam_mode = edi::BeamModeEnum::TIME_OF_FLIGHT;
    source.dataset_weight = 2.5;
    source.excluded_regions = {{10.0, 20.0}};
    source.peak.rise_alpha_0 = {1.0, 0.01, true};
    source.peak.rise_alpha_1 = {2.0, 0.02, false};
    source.peak.decay_beta_0 = {3.0, 0.03, true};
    source.peak.decay_beta_1 = {4.0, 0.04, false};
    source.peak.broad_gauss_sigma_0 = {5.0, 0.05, true};
    source.peak.broad_gauss_sigma_1 = {6.0, 0.06, false};
    source.peak.broad_gauss_sigma_2 = {7.0, 0.07, true};
    source.peak.broad_gauss_size = {8.0, 0.08, false};
    source.peak.broad_gauss_strain = {9.0, 0.09, true};
    source.peak.broad_lorentz_gamma_0 = {10.0, 0.10, false};
    source.peak.broad_lorentz_gamma_1 = {11.0, 0.11, true};
    source.peak.broad_lorentz_gamma_2 = {12.0, 0.12, false};
    source.peak.broad_lorentz_size = {13.0, 0.13, true};
    source.peak.broad_lorentz_strain = {14.0, 0.14, false};
    source.instrument.calib_d_to_tof_offset = {-1.0, 0.15, true};
    source.instrument.calib_d_to_tof_linear = {20000.0, 0.16, false};
    source.instrument.calib_d_to_tof_quadratic = {-2.0, 0.17, true};
    source.instrument.calib_d_to_tof_reciprocal = {0.5, 0.18, false};
    source.linked_structure().scale = {1.7, 0.19, true};
    source.instrument.setup_twotheta_bank.value = 137.2;
    source.peak.cutoff_fwhm = 17.5;
    source.absorption.type = "cylinder";
    source.absorption.abscor1 = edi::Parameter{0.2, 0.02, true};
    source.absorption.abscor2 = edi::Parameter{0.3, 0.03, false};
    source.background.push_back(edi::LineSegment{});
    source.background[0]->position = 10000.0;
    source.background[0]->intensity = {2.0, 0.20, true};

    const crysta::BraggPdExperiment converted = edi::detail::to_crysta_experiment(source);
    CHECK_MESSAGE(converted.kind.get() == crysta::BeamModeEnum::TimeOfFlight,
                  "the adapter must retain the declared TOF beam family");
    CHECK_MESSAGE(
        (converted.name == "bank-a" && converted.peak_type.get() == "tof-jorgensen-von-dreele"),
        "the adapter must retain bank identity and the exact profile selector");
    REQUIRE_MESSAGE(converted.peak.size() == 14,
                    "the TOF adapter must preserve all fourteen profile coefficients");
    CHECK_MESSAGE((converted.peak[0].value() == 1.0 && converted.peak[13].value() == 14.0),
                  "the TOF adapter must preserve the independently specified profile order");
    REQUIRE_MESSAGE(converted.instrument.size() == 4,
                    "the TOF adapter must preserve all four calibration terms");
    CHECK_MESSAGE(
        (converted.instrument[0].value() == -1.0 && converted.instrument[3].value() == 0.5),
        "the TOF adapter must preserve calibration order and values");
    CHECK_MESSAGE((converted.scale().value() == 1.7 && converted.scale().free()),
                  "the adapter must preserve linked-structure scale state");
    REQUIRE_MESSAGE(converted.background.size() == 1,
                    "the adapter must preserve every background point");
    CHECK_MESSAGE((converted.background[0].position == 10000.0 &&
                   converted.background[0].intensity.value() == 2.0),
                  "the adapter must preserve background coordinates and intensity");
    CHECK_MESSAGE((converted.absorption.size() == 2 && converted.absorption[0].value() == 0.2 &&
                   converted.absorption[1].value() == 0.3),
                  "the adapter must preserve the two-term absorption body");
    CHECK_MESSAGE(
        (converted.dataset_weight == 2.5 && converted.excluded_regions == source.excluded_regions),
        "the adapter must preserve joint-fit weight and exclusion masks");
}

TEST_CASE("E09-T55 adapter conversion preserves CW layout and refuses incomplete models") {
    edi::BraggPdExperiment source;
    source.name = "bank-cw";
    source.experiment_type.beam_mode = edi::BeamModeEnum::CONSTANT_WAVELENGTH;
    source.peak.broad_gauss_u = edi::Parameter{1.0, 0.01, true};
    source.peak.broad_gauss_v = edi::Parameter{2.0, 0.02, false};
    source.peak.broad_gauss_w = edi::Parameter{3.0, 0.03, true};
    source.peak.broad_lorentz_x = edi::Parameter{4.0, 0.04, false};
    source.peak.broad_lorentz_y = edi::Parameter{5.0, 0.05, true};
    source.instrument.calib_twotheta_offset = edi::Parameter{-0.5, 0.06, true};
    source.instrument.setup_wavelength = edi::Parameter{1.54, 0.07, false};
    source.instrument.calib_sample_displacement = edi::Parameter{0.12, 0.008, true};
    source.instrument.calib_sample_transparency = edi::Parameter{-0.23, 0.009, false};
    source.linked_structure().scale = {2.0, 0.08, true};
    source.background.push_back(edi::LineSegment{});
    source.background[0]->position = 40.0;
    source.background[0]->intensity = {100.0, 1.0, false};

    const crysta::BraggPdExperiment converted = edi::detail::to_crysta_experiment(source);
    CHECK_MESSAGE(converted.kind.get() == crysta::BeamModeEnum::ConstantWavelength,
                  "the adapter must retain the declared CW beam family");
    CHECK_MESSAGE(converted.peak_type.get() == "cwl-tch-pseudo-voigt",
                  "an omitted CW selector must acquire the one implemented CW profile");
    REQUIRE_MESSAGE(converted.peak.size() == 5,
                    "the CW adapter must preserve exactly the U/V/W/X/Y profile layout");
    CHECK_MESSAGE((converted.peak[0].value() == 1.0 && converted.peak[4].value() == 5.0),
                  "the CW adapter must preserve U/V/W/X/Y order and values");
    REQUIRE_MESSAGE(
        converted.instrument.size() == 4,
        "the CW adapter must preserve offset/wavelength/displacement/transparency layout");
    CHECK_MESSAGE(
        (converted.instrument[0].value() == -0.5 && converted.instrument[1].value() == 1.54 &&
         converted.instrument[2].value() == 0.12 && converted.instrument[3].value() == -0.23),
        "the CW adapter must preserve all four instrument slots in declared order");

    source.peak.broad_gauss_w.reset();
    bool raised = false;
    try {
        static_cast<void>(edi::detail::to_crysta_experiment(source));
    } catch (const std::invalid_argument& error) {
        raised = true;
        check_contains(error.what(), "peak.broad_gauss_w",
                       "an incomplete CW model must name the missing required field");
    }
    CHECK_MESSAGE(raised, "an incomplete programmatic CW model must fail closed");
}
