#include <doctest/doctest.h>

#include <filesystem>
#include <fstream>
#include <functional>
#include <iterator>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/validation.hpp"

namespace {

std::filesystem::path repo_root() {
    std::filesystem::path path = std::filesystem::absolute(__FILE__).parent_path();
    while (path.has_parent_path()) {
        if (std::filesystem::exists(path / "CMakeLists.txt") &&
            std::filesystem::exists(path / "pixi.toml")) {
            return path;
        }
        path = path.parent_path();
    }
    throw std::runtime_error("cannot locate edi repository root");
}

std::string read_text(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open fixture: " + path.string());
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

void write_text(const std::filesystem::path& path, const std::string& text) {
    std::ofstream output(path);
    if (!output) throw std::runtime_error("cannot write temporary fixture: " + path.string());
    output << text;
}

edi::Project populated_project(edi::Structure structure,
                               edi::BraggPdExperiment experiment) {
    edi::Project project;
    project.structures.clear();
    project.experiments.clear();
    project.structures.push_back(std::move(structure));
    project.experiments.push_back(std::move(experiment));
    return project;
}

void check_io_error(const std::function<void()>& action, const std::string& fragment,
                    const char* requirement) {
    INFO(requirement);
    bool raised = false;
    try {
        action();
    } catch (const edi::IoError& error) {
        raised = true;
        INFO(std::string(error.what()));
        CHECK_MESSAGE(std::string(error.what()).find(fragment) != std::string::npos,
                      "the I/O refusal must contain its required diagnostic fragment");
    }
    CHECK_MESSAGE(raised, "the I/O refusal helper must observe an edi::IoError");
}

struct TempTree {
    std::filesystem::path path;
    ~TempTree() { std::filesystem::remove_all(path); }
};

TempTree temp_tree(const std::string& leaf) {
    const std::filesystem::path path =
        std::filesystem::temp_directory_path() / ("edi--" + leaf);
    std::filesystem::remove_all(path);
    return TempTree{path};
}

}  // namespace

TEST_CASE("E09-T55 entity readers accept dot-form and classic CIF structures") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures";
    const edi::Structure dot = edi::structure_from_edi_text(
        read_text(fixtures / "c11_t4_cw_selection/structure.edi"));
    CHECK_MESSAGE(dot.name == "ncaf", "the dot-form structure must retain its data-block identity");
    CHECK_MESSAGE(dot.space_group.name_h_m == "I 21 3",
                  "the dot-form structure must retain its Hermann-Mauguin setting");
    CHECK_MESSAGE(dot.atom_sites.size() == 6,
                  "the dot-form fixture must retain all six independently recorded atom rows");
    CHECK_MESSAGE((dot.atom_sites.front()->id == "Ca" && dot.atom_sites.back()->id == "F3"),
                  "the dot-form atom loop must retain source order and labels");

    const edi::Structure classic = edi::structure_from_edi_text(
        read_text(fixtures / "e02_t2_ncaf_5bank/published_cod_1000236.cif"));
    CHECK_MESSAGE(!classic.name.empty(), "the classic CIF structure must retain its data-block identity");
    CHECK_MESSAGE(!classic.space_group.name_h_m.empty(),
                  "the classic CIF structure must resolve a space-group name");
    CHECK_MESSAGE(!classic.atom_sites.empty(), "the classic CIF atom loop must produce sites");

    const edi::Structure coded = edi::structure_from_edi_text(
        read_text(fixtures / "c12_t3_space_group_code/si_origin_2.edi"));
    CHECK_MESSAGE(coded.space_group.coord_system_code == "2",
                  "the origin-choice fixture must retain its independently recorded code 2");
}

TEST_CASE("E09-T55 experiment reader accepts both implemented beam families") {
    const std::filesystem::path cases =
        repo_root() / "tests/fixtures/c11_t4_cw_selection/cases";
    const edi::BraggPdExperiment cwl =
        edi::experiment_from_edi_text(read_text(cases / "cwl_valid.edi"));
    CHECK_MESSAGE(cwl.effective_beam_mode() == edi::BeamModeEnum::CONSTANT_WAVELENGTH,
                  "the CW fixture's typed beam mode must remain constant wavelength");
    REQUIRE_MESSAGE(cwl.data.has_value(), "the CW fixture must retain its embedded observations");
    CHECK_MESSAGE((cwl.data->two_theta.has_value() && !cwl.data->time_of_flight.has_value()),
                  "the CW fixture must engage only the two-theta axis");
    CHECK_MESSAGE(cwl.data->axis().size() == 6,
                  "the CW fixture must retain its six independently recorded observation rows");

    const edi::BraggPdExperiment tof =
        edi::experiment_from_edi_text(read_text(cases / "tof_valid.edi"));
    CHECK_MESSAGE(tof.effective_beam_mode() == edi::BeamModeEnum::TIME_OF_FLIGHT,
                  "the TOF fixture's typed beam mode must remain time-of-flight");
    REQUIRE_MESSAGE(tof.data.has_value(), "the TOF fixture must retain its embedded observations");
    CHECK_MESSAGE((!tof.data->two_theta.has_value() && tof.data->time_of_flight.has_value()),
                  "the TOF fixture must engage only the time-of-flight axis");
}

TEST_CASE("E09-T55 experiment reader translates the frozen diffraction-lib CIF vocabulary") {
    // Frozen from diffraction-lib 0ffba46f's public experiment descriptors. These are upstream
    // CIF names and upstream reference values, not output generated by edi's parser.
    const std::string reference = R"cif(data_reference_cwl
_easydiffraction_experiment_type.sample_form powder
_easydiffraction_experiment_type.beam_mode 'constant wavelength'
_easydiffraction_experiment_type.radiation_probe neutron
_easydiffraction_experiment_type.scattering_type bragg
_diffrn_radiation_wavelength.value 1.494
_pd_calib.2theta_offset 0.6225
_easydiffraction_peak.broad_gauss_u 0.0834
_easydiffraction_peak.broad_gauss_v -0.1168
_easydiffraction_peak.broad_gauss_w 0.123

loop_
_pd_background.id
_pd_background.line_segment_X
_pd_background.line_segment_intensity
1 10 100

loop_
_pd_phase_block.id
_pd_phase_block.scale
Si 1

loop_
_pd_data.point_id
_pd_meas.2theta_scan
_pd_meas.intensity_total
_pd_meas.intensity_total_su
1 10 100 1
)cif";
    const edi::BraggPdExperiment experiment = edi::experiment_from_edi_text(reference);
    CHECK_MESSAGE(experiment.name == "reference_cwl",
                  "classic CIF translation must retain the upstream data-block identity");
    REQUIRE_MESSAGE(experiment.instrument.setup_wavelength.has_value(),
                    "classic CIF translation must retain the upstream wavelength");
    CHECK_MESSAGE(experiment.instrument.setup_wavelength->value == doctest::Approx(1.494),
                  "the wavelength must equal the frozen diffraction-lib reference");
    REQUIRE_MESSAGE(experiment.instrument.calib_twotheta_offset.has_value(),
                    "classic CIF translation must retain the upstream two-theta offset");
    CHECK_MESSAGE(experiment.instrument.calib_twotheta_offset->value == doctest::Approx(0.6225),
                  "the offset must equal the frozen diffraction-lib reference");
    REQUIRE_MESSAGE(experiment.peak.broad_gauss_u.has_value(),
                    "classic CIF translation must retain upstream Caglioti U");
    CHECK_MESSAGE(experiment.peak.broad_gauss_u->value == doctest::Approx(0.0834),
                  "Caglioti U must equal the frozen diffraction-lib reference");
    CHECK_MESSAGE(experiment.linked_structure.structure_id == "Si",
                  "an absent classic phase block must use diffraction-lib's documented Si default");
    REQUIRE_MESSAGE(experiment.background.size() == 1,
                    "classic CIF translation must retain the line-segment background loop");
    CHECK_MESSAGE((experiment.background[0]->position == 10.0 &&
                   experiment.background[0]->intensity.value == 100.0),
                  "classic CIF translation must retain background coordinates and intensity");
    REQUIRE_MESSAGE(experiment.data.has_value(),
                    "classic CIF translation must retain the measured-data loop");
    const std::vector<double> classic_axis{10.0};
    CHECK_MESSAGE(experiment.data->axis() == classic_axis,
                  "classic CIF translation must retain the independently recorded axis row");
}

TEST_CASE("E09-T55 experiment reader refuses every committed selector-family crossing") {
    const std::filesystem::path cases =
        repo_root() / "tests/fixtures/c11_t4_cw_selection/cases";
    const std::vector<std::pair<std::string, std::string>> refusals{
        {"cwl_with_tof_beam.edi", "beam"},
        {"tof_with_cwl_beam.edi", "beam"},
        {"cwl_bad_beam_hyphen.edi", "beam"},
        {"cwl_unknown_peak.edi", "cwl-not-a-profile"},
        {"cwl_with_tof_tag.edi", "calib_d_to_tof_linear"},
        {"tof_with_cw_tag.edi", "setup_wavelength"},
    };
    for (const auto& [name, fragment] : refusals) {
        CAPTURE(name);
        const std::string source = read_text(cases / name);
        check_io_error([&] { static_cast<void>(edi::experiment_from_edi_text(source)); }, fragment,
                       "an invalid selector-family combination must be refused by name");
    }
}

TEST_CASE("C11-T57 formerly reserved CW selectors construct their experiment") {
    const auto cases = repo_root() / "tests/fixtures/c11_t4_cw_selection/cases";
    for (const auto* name : {"cwl_reserved_beba.edi", "cwl_reserved_fcj.edi"}) {
        CHECK_NOTHROW_MESSAGE(edi::experiment_from_edi_text(read_text(cases / name)),
                              " FCJ and BeBa reservations must become executable types");
    }
}

TEST_CASE("E09-T55 CW experiment reader requires every independently declared profile field") {
    const std::filesystem::path source_path =
        repo_root() / "tests/fixtures/c11_t4_cw_selection/cases/cwl_valid.edi";
    const std::string source = read_text(source_path);
    const std::vector<std::string> tags{
        "_peak.broad_gauss_u", "_peak.broad_gauss_v", "_peak.broad_gauss_w",
        "_peak.broad_lorentz_x", "_peak.broad_lorentz_y",
        "_instrument.calib_twotheta_offset", "_instrument.setup_wavelength",
    };
    for (const std::string& tag : tags) {
        const std::size_t begin = source.find(tag + " ");
        REQUIRE_MESSAGE(begin != std::string::npos,
                        "the committed CW fixture must carry each independently declared required tag");
        const std::size_t end = source.find('\n', begin);
        std::string missing = source;
        missing.erase(begin, end - begin + 1);
        check_io_error([&] { static_cast<void>(edi::experiment_from_edi_text(missing)); }, tag,
                       "a missing required CW profile field must be named in the refusal");
    }
}

TEST_CASE("E09-T55 project loader covers multi-bank, absent, and explicit-none absorption shapes") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures";
    const edi::Project five = edi::load_project(
        (fixtures / "e02_t2_ncaf_5bank/project").string());
    CHECK_MESSAGE(five.structures.size() == 1,
                  "the NCAF fixture must retain its single declared structure");
    CHECK_MESSAGE(five.experiments.size() == 5,
                  "the NCAF fixture must retain all five independently recorded banks");
    CHECK_MESSAGE(five.fitting_mode == "joint",
                  "the five-bank analysis fixture must retain joint fitting mode");

    const edi::Project absent = edi::load_project(
        (fixtures / "c09_t6_ncaf_5bank_absorption/key_absent_project").string());
    CHECK_MESSAGE(absent.experiment().absorption.type == "none",
                  "an absent absorption selector must load as the canonical none type");
    CHECK_MESSAGE(!absent.experiment().absorption.abscor1.has_value(),
                  "an absent absorption body must not synthesize ABSCOR1");

    const edi::Project explicit_none = edi::load_project(
        (fixtures / "c09_t6_ncaf_5bank_absorption/type_none_project").string());
    REQUIRE_MESSAGE(explicit_none.experiment().absorption.type.has_value(),
                    "an explicit none absorption selector must remain present");
    CHECK_MESSAGE(*explicit_none.experiment().absorption.type == "none",
                  "the explicit none absorption token must retain the canonical none type");
}

TEST_CASE("E09-T55 project writer and loader form a representation fixed point") {
    const std::filesystem::path source =
        repo_root() / "tests/fixtures/c09_t6_ncaf_5bank_absorption/type_none_project";
    const edi::Project project = edi::load_project(source.string());
    TempTree temporary = temp_tree("roundtrip");
    edi::save_project(project, temporary.path.string());
    const edi::Project restored = edi::load_project(temporary.path.string());
    CHECK_MESSAGE(restored.structures.size() == project.structures.size(),
                  "project save/load must preserve the structure count");
    CHECK_MESSAGE(restored.experiments.size() == project.experiments.size(),
                  "project save/load must preserve the experiment count");
    CHECK_MESSAGE(restored.experiment().name == project.experiment().name,
                  "project save/load must preserve bank identity");
    CHECK_MESSAGE(restored.experiment().data.has_value() == project.experiment().data.has_value(),
                  "project save/load must preserve measured-data presence");
    CHECK_MESSAGE(restored.experiment().absorption.type == project.experiment().absorption.type,
                  "project save/load must preserve the absorption selector");
}

TEST_CASE("E09-T55 constant-wavelength project writer preserves typed axes and observations") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures/c11_t4_cw_selection";
    edi::Structure structure = edi::structure_from_edi_text(read_text(fixtures / "structure.edi"));
    edi::BraggPdExperiment experiment =
        edi::experiment_from_edi_text(read_text(fixtures / "cases/cwl_valid.edi"));
    edi::Project project = populated_project(std::move(structure), std::move(experiment));
    project.fitting_mode = "single";
    project.experiment().peak.broad_gauss_u = edi::Parameter{0.125, 1.0e-40, true};
    project.experiment().excluded_regions = {{25.0, 30.0}};
    TempTree temporary = temp_tree("cwl-roundtrip");
    edi::save_project(project, temporary.path.string());
    edi::save_project(project, temporary.path.string());
    const edi::Project restored = edi::load_project(temporary.path.string());
    CHECK_MESSAGE(restored.experiment().effective_beam_mode() ==
                      edi::BeamModeEnum::CONSTANT_WAVELENGTH,
                  "the CW writer must retain the typed beam mode");
    REQUIRE_MESSAGE(restored.experiment().data.has_value(),
                    "the CW writer must retain embedded observations");
    CHECK_MESSAGE(restored.experiment().data->two_theta.has_value(),
                  "the CW writer must retain the two-theta axis name");
    CHECK_MESSAGE(restored.experiment().data->axis().size() == 6,
                  "the CW writer must retain all six independently recorded rows");
    CHECK_MESSAGE(restored.experiment().excluded_regions == project.experiment().excluded_regions,
                  "the CW writer must retain excluded-region pairs");
    REQUIRE_MESSAGE(restored.experiment().peak.broad_gauss_u.has_value(),
                    "the CW writer must retain Caglioti U");
    CHECK_MESSAGE(restored.experiment().peak.broad_gauss_u->uncertainty == doctest::Approx(1.0e-40),
                  "the CW writer must retain an independently specified nonzero uncertainty");
    CHECK_MESSAGE(restored.experiment().peak.broad_gauss_u->free,
                  "the CW writer must retain an independently specified free flag");
}

TEST_CASE("E09-T55 writer refuses calculation-only and ragged CW observations") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures/c11_t4_cw_selection";
    edi::Structure structure = edi::structure_from_edi_text(read_text(fixtures / "structure.edi"));
    edi::BraggPdExperiment experiment =
        edi::experiment_from_edi_text(read_text(fixtures / "cases/cwl_valid.edi"));
    edi::Project project = populated_project(structure, experiment);

    project.experiment().calculation_only = true;
    TempTree calculation = temp_tree("calculation-only-refusal");
    check_io_error([&] { edi::save_project(project, calculation.path.string()); }, "calculation-only",
                   "a generated calculation grid must never be persisted as observations");

    project = populated_project(std::move(structure), std::move(experiment));
    REQUIRE_MESSAGE(project.experiment().data.has_value(),
                    "the committed CW fixture must carry observations before the ragged mutation");
    auto ragged_values = static_cast<const std::vector<double>&>(
        project.experiment().data->intensity_meas);
    ragged_values.pop_back();
    project.experiment().data->intensity_meas = std::move(ragged_values);
    TempTree ragged = temp_tree("ragged-cwl-refusal");
    check_io_error([&] { edi::save_project(project, ragged.path.string()); }, "ragged or empty",
                   "a ragged programmatic CW pattern must fail before any row indexing");

    project = populated_project(
        edi::structure_from_edi_text(read_text(fixtures / "structure.edi")),
        edi::experiment_from_edi_text(read_text(fixtures / "cases/cwl_valid.edi")));
    project.experiment().peak.broad_gauss_u.reset();
    TempTree incomplete = temp_tree("incomplete-cwl-refusal");
    check_io_error([&] { edi::save_project(project, incomplete.path.string()); }, "missing required field",
                   "a programmatic CW model missing a required field must fail closed on write");
}

TEST_CASE("E09-T55 project metadata refreshes its public modification timestamp") {
    edi::ProjectMetadata metadata;
    CHECK_MESSAGE(!metadata.created.empty(), "project metadata must carry a construction timestamp");
    CHECK_MESSAGE(!metadata.last_modified.empty(),
                  "project metadata must carry a last-modified timestamp");
    const std::string before = metadata.last_modified;
    metadata.update_last_modified();
    CHECK_MESSAGE(metadata.last_modified >= before,
                  "refreshing project metadata must never move its timestamp backwards");
}

TEST_CASE("E09-T55 declared data ranges select calculation mode and reject ambiguity") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures/c11_t4_cw_selection";
    const std::string measured = read_text(fixtures / "cases/cwl_valid.edi");
    const std::size_t data_loop = measured.find("loop_\n_data.two_theta");
    REQUIRE_MESSAGE(data_loop != std::string::npos,
                    "the committed CW fixture must carry the measured-loop mutation seam");
    std::string ranged = measured.substr(0, data_loop);
    ranged += "_data_range.two_theta_min 10\n"
              "_data_range.two_theta_max 20\n"
              "_data_range.two_theta_step 5\n";
    const edi::BraggPdExperiment calculation = edi::experiment_from_edi_text(ranged);
    CHECK_MESSAGE(calculation.calculation_only,
                  "a complete declared range must select calculation-only mode");
    REQUIRE_MESSAGE(calculation.data.has_value(),
                    "a complete declared range must generate an axis container");
    const std::vector<double> expected_axis{10.0, 15.0, 20.0};
    CHECK_MESSAGE(calculation.data->axis() == expected_axis,
                  "the generated axis must follow the independently declared min/max/step");
    CHECK_MESSAGE((calculation.data->intensity_meas.empty() &&
                   calculation.data->intensity_meas_su.empty()),
                  "a generated range must not fabricate observations");

    std::string unusable = ranged;
    const std::size_t step = unusable.find("_data_range.two_theta_step 5");
    REQUIRE_MESSAGE(step != std::string::npos,
                    "the generated range fixture must carry the step mutation seam");
    unusable.replace(step, std::string("_data_range.two_theta_step 5").size(),
                     "_data_range.two_theta_step 0");
    check_io_error([&] { static_cast<void>(edi::experiment_from_edi_text(unusable)); }, "step",
                   "an unusable declared range must fail closed");
    check_io_error([&] {
        static_cast<void>(edi::experiment_from_edi_text(
            measured + "_data_range.two_theta_min 10\n_data_range.two_theta_max 20\n"
                       "_data_range.two_theta_step 5\n"));
    }, "declares both", "a block must not declare observations and a calculation range together");

    std::string partial = measured.substr(0, data_loop);
    partial += "_data_range.two_theta_min 10\n";
    check_io_error([&] { static_cast<void>(edi::experiment_from_edi_text(partial)); },
                   "must be declared together", "a partial declared range must fail closed");

    TempTree all_range = temp_tree("range-project");
    std::filesystem::create_directories(all_range.path / "structures");
    std::filesystem::create_directories(all_range.path / "experiments");
    std::filesystem::copy_file(fixtures / "structure.edi",
                               all_range.path / "structures/ncaf.edi");
    write_text(all_range.path / "experiments/range.edi", ranged);
    const edi::Project range_project = edi::load_project(all_range.path.string());
    CHECK_MESSAGE(range_project.experiment().calculation_only,
                  "a project whose banks all declare ranges must select calculation mode");

    write_text(all_range.path / "experiments/measured.edi", measured);
    check_io_error([&] { static_cast<void>(edi::load_project(all_range.path.string())); },
                   "project's contents select calculate or fit as a whole",
                   "a mixed observation/range project must fail closed");
}

TEST_CASE("E09-T55 project I/O fails closed before partial state escapes") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures";
    check_io_error([&] { static_cast<void>(edi::load_project("/definitely/not/an/edi/project")); },
                   "project directory", "a missing project directory must fail closed");

    edi::Project multi = edi::load_project(
        (fixtures / "c09_t6_ncaf_5bank_absorption/type_none_project").string());
    // : before, fixture setup duplicated the first key. After, a distinct
    // second structure reaches the unchanged multi-structure publication refusal.
    auto second_structure = *multi.structures.front();
    second_structure.name = "second-structure";
    multi.structures.push_back(second_structure);
    TempTree destination = temp_tree("multi-structure-refusal");
    check_io_error([&] { edi::save_project(multi, destination.path.string()); }, "multi-structure",
                   "the writer must refuse a project it cannot represent without data loss");
    CHECK_MESSAGE(!std::filesystem::exists(destination.path),
                  "a refused multi-structure save must not touch its destination");
}

TEST_CASE("E09-T55 STAR parser failures retain their validation tier") {
    const std::string valid = read_text(
        repo_root() / "tests/fixtures/c11_t4_cw_selection/structure.edi");
    const auto replacing = [&valid](const std::string& before, const std::string& after) {
        std::string changed = valid;
        const std::size_t offset = changed.find(before);
        REQUIRE_MESSAGE(offset != std::string::npos,
                        "the committed structure fixture must carry the intended mutation seam");
        changed.replace(offset, before.size(), after);
        return changed;
    };
    const std::vector<std::pair<std::string, int>> malformed{
        {replacing("data_ncaf", "not_a_data_block"), 1},
        {replacing("_cell.length_a 10.250256", "_cell.length_a not-a-number"), 2},
        // : finite occupancy 2.0 now loads; numeric corruption still refuses.
        {replacing("Ca Ca 0.4661 0 0.25 b 1 0.90 Biso", "Ca Ca 0.4661 0 0.25 b nan 0.90 Biso"), 2},
        {replacing("Ca Ca 0.4661 0 0.25 b 1 0.90 Biso", "Ca Ca 0.4661 0 0.25 b inf 0.90 Biso"), 2},
        {replacing("Ca Ca 0.4661 0 0.25 b 1 0.90 Biso", "Ca Ca 0.4661 0 0.25 b 2oops 0.90 Biso"),
         2},
    };
    std::size_t malformed_index = 0;
    for (const auto& [source, expected_tier] : malformed) {
        CAPTURE(malformed_index);
        bool raised = false;
        try {
            static_cast<void>(edi::structure_from_edi_text(source));
        } catch (const edi::ValidationError& error) {
            raised = true;
            CHECK_MESSAGE(error.tier() == expected_tier,
                          "a malformed STAR structure must retain its syntax/schema tier");
            CHECK_MESSAGE(!error.diagnostics().empty(),
                          "a malformed STAR structure must carry a structured diagnostic");
        }
        CHECK_MESSAGE(raised, "a malformed STAR structure must fail closed");
        ++malformed_index;
    }
    const std::string outside =
        replacing("Ca Ca 0.4661 0 0.25 b 1 0.90 Biso", "Ca Ca 0.4661 0 0.25 b 2 0.90 Biso");
    const edi::Structure parsed = edi::structure_from_edi_text(outside);
    CHECK_MESSAGE(
        parsed.atom_sites.front()->occupancy.value == 2.0,
        " entity reader preserves finite out-of-range occupancy without clamping");
    TempTree input = temp_tree("range-warning");
    std::filesystem::create_directories(input.path / "structures");
    std::filesystem::create_directories(input.path / "experiments");
    write_text(input.path / "structures/ncaf.edi", outside);
    std::filesystem::copy_file(
        repo_root() / "tests/fixtures/c11_t4_cw_selection/cases/cwl_valid.edi",
        input.path / "experiments/bank.edi");
    std::vector<std::string> warnings;
    const auto sink = [&](const std::string& message) { warnings.push_back(message); };
    const auto loaded = edi::load_project(input.path.string(), sink);
    CHECK_MESSAGE(loaded.structure().atom_sites.front()->occupancy.value == 2.0,
                  " public project loader retains the original occupancy 2.0");
    std::size_t range_warnings = 0;
    for (const auto& warning : warnings) {
        if (warning.find("occupancy") != std::string::npos &&
            warning.find("outside its admissible range") != std::string::npos) {
            ++range_warnings;
        }
    }
    CHECK_MESSAGE(range_warnings == 1,
                  " the project warning sink receives one occupancy range warning");
    TempTree saved = temp_tree("range-warning-saved");
    edi::save_project(loaded, saved.path.string());
    warnings.clear();
    const auto reopened = edi::load_project(saved.path.string(), sink);
    CHECK_MESSAGE(reopened.structure().atom_sites.front()->occupancy.value == 2.0,
                  " save/reopen preserves the exact admitted occupancy");
    CHECK_MESSAGE(warnings.size() == 1,
                  " metadata-complete saved output emits exactly the range warning");
}

TEST_CASE("E09-T55 experiment schema mutations fail at their declared boundary") {
    const std::string valid =
        read_text(repo_root() / "tests/fixtures/c11_t4_cw_selection/cases/cwl_valid.edi");
    const auto replace_one = [&valid](const std::string& before, const std::string& after) {
        std::string changed = valid;
        const std::size_t offset = changed.find(before);
        if (offset == std::string::npos) {
            throw std::runtime_error("committed CW fixture lost mutation seam: " + before);
        }
        changed.replace(offset, before.size(), after);
        return changed;
    };
    const std::vector<std::pair<std::string, std::string>> refusals{
        {replace_one("_edi.schema_version 2", "_edi.schema_version 1"), "unsupported"},
        {replace_one("_peak.broad_gauss_u", "_peak.not_a_real_tag"), "unknown tag"},
        {replace_one("_background.type line-segment\n", ""), "explicit _background.type"},
        {replace_one("_background.type line-segment", "_background.type chebyshev"),
         "chebyshev background cannot contain line-segment fields"},
        {replace_one("_background.type line-segment", "_background.type mystery"),
         "unknown _background.type"},
        {replace_one("_data.intensity_meas_su", "_data.unmodelled_su"),
         "missing required column"},
        {replace_one("18.25 1 0 1", "18.25 1 0 0"), "non-positive"},
        {replace_one("_experiment_type.sample_form powder",
                     "_experiment_type.sample_form liquid"), "not a known token"},
        {replace_one("_experiment_type.radiation_probe neutron",
                     "_experiment_type.radiation_probe electron"), "not a known token"},
        {replace_one("_experiment_type.scattering_type bragg",
                     "_experiment_type.scattering_type diffuse"), "not a known token"},
    };
    for (const auto& [source, fragment] : refusals) {
        check_io_error([&] { static_cast<void>(edi::experiment_from_edi_text(source)); }, fragment,
                       "a malformed experiment schema must fail at its declared boundary");
    }

    std::string ambiguous = valid;
    const std::size_t data_loop = ambiguous.find("loop_\n_data.two_theta");
    REQUIRE_MESSAGE(data_loop != std::string::npos,
                    "the committed CW fixture must carry the data-loop mutation seam");
    ambiguous.insert(data_loop, "_data.time_of_flight 1\n");
    check_io_error([&] { static_cast<void>(edi::experiment_from_edi_text(ambiguous)); },
                   "both _data.two_theta and _data.time_of_flight",
                   "a measured block with two axes must fail closed");

    std::string empty_loop = valid.substr(0, valid.find("18.25 1 0 1"));
    check_io_error([&] { static_cast<void>(edi::experiment_from_edi_text(empty_loop)); },
                   "no rows", "an empty measured-data loop must fail closed");

    std::string alternates = replace_one("_experiment_type.sample_form powder",
                                         "_experiment_type.sample_form \"single crystal\"");
    const std::size_t neutron = alternates.find("_experiment_type.radiation_probe neutron");
    REQUIRE_MESSAGE(neutron != std::string::npos,
                    "the committed CW fixture must carry the radiation mutation seam");
    alternates.replace(neutron, std::string("_experiment_type.radiation_probe neutron").size(),
                       "_experiment_type.radiation_probe xray");
    const std::size_t bragg = alternates.find("_experiment_type.scattering_type bragg");
    REQUIRE_MESSAGE(bragg != std::string::npos,
                    "the committed CW fixture must carry the scattering mutation seam");
    alternates.replace(bragg, std::string("_experiment_type.scattering_type bragg").size(),
                       "_experiment_type.scattering_type total");
    const edi::BraggPdExperiment typed = edi::experiment_from_edi_text(alternates);
    CHECK_MESSAGE(typed.experiment_type.sample_form == edi::SampleFormEnum::SINGLE_CRYSTAL,
                  "the alternate sample-form token must retain its typed value");
    CHECK_MESSAGE(typed.experiment_type.radiation_probe == edi::RadiationProbeEnum::XRAY,
                  "the alternate radiation token must retain its typed value");
    CHECK_MESSAGE(typed.experiment_type.scattering_type == edi::ScatteringTypeEnum::TOTAL,
                  "the alternate scattering token must retain its typed value");
}

TEST_CASE("E09-T55 structure schema handles optional identity and ADP branches") {
    const std::string valid = read_text(
        repo_root() / "tests/fixtures/c11_t4_cw_selection/structure.edi");
    const auto replacing = [&valid](const std::string& before, const std::string& after) {
        std::string changed = valid;
        const std::size_t offset = changed.find(before);
        if (offset == std::string::npos) {
            throw std::runtime_error("committed structure fixture lost mutation seam: " + before);
        }
        changed.replace(offset, before.size(), after);
        return changed;
    };
    const edi::Structure numbered = edi::structure_from_edi_text(
        replacing("_space_group.coord_system_code 1",
                  "_space_group.coord_system_code 1\n_space_group.it_number 199"));
    CHECK_MESSAGE(numbered.space_group.it_number == 199,
                  "a valid independently declared IT number must remain present");
    check_io_error([&] {
        static_cast<void>(edi::structure_from_edi_text(
            replacing("_space_group.coord_system_code 1",
                      "_space_group.coord_system_code 1\n_space_group.it_number 999")));
    }, "not an IT number", "an out-of-range IT number must fail closed");

    const edi::Structure uiso = edi::structure_from_edi_text(
        replacing("Ca Ca 0.4661 0 0.25 b 1 0.90 Biso",
                  "Ca Ca 0.4661 0 0.25 b 1 0.01 Uiso"));
    CHECK_MESSAGE(uiso.atom_sites.front()->adp_type == "Biso",
                  "a Uiso source must be stored in the model's Biso representation");
    CHECK_MESSAGE(uiso.atom_sites.front()->adp_iso.value ==
                      doctest::Approx(0.01 * 8.0 * 3.141592653589793238 *
                                      3.141592653589793238),
                  "Uiso must use the independently defined B=8*pi^2*U conversion");
    check_io_error([&] {
        static_cast<void>(edi::structure_from_edi_text(
            replacing("Ca Ca 0.4661 0 0.25 b 1 0.90 Biso",
                      "Ca Ca 0.4661 0 0.25 b 1 0.90 Uani")));
    }, "not readable", "an anisotropic ADP token must not be misread as isotropic B");
}

TEST_CASE("E09-T55 background and measured loops reject partial plausible shapes") {
    const std::string valid = read_text(
        repo_root() / "tests/fixtures/c11_t4_cw_selection/cases/cwl_valid.edi");
    const std::size_t background_begin = valid.find("loop_\n_background.id");
    const std::size_t data_begin = valid.find("loop_\n_data.two_theta");
    REQUIRE_MESSAGE((background_begin != std::string::npos && data_begin != std::string::npos),
                    "the committed CW fixture must retain background and data mutation seams");
    const auto with_background = [&](const std::string& block) {
        std::string changed = valid;
        changed.replace(background_begin, data_begin - background_begin, block + "\n");
        return changed;
    };
    const std::vector<std::pair<std::string, std::string>> background_refusals{
        {with_background("_background.position 10\n_background.intensity 169"),
         "must be a loop"},
        {with_background("loop_\n_background.id\n_background.position\n1 10\n2 90"),
         "requires a loop declaring both"},
        {with_background("loop_\n_background.id\n_background.position\n1 10\n"
                         "loop_\n_background.id\n_background.intensity\n1 169"),
         "the background points are declared in more than one loop"},
    };
    for (const auto& [source, fragment] : background_refusals) {
        check_io_error([&] { static_cast<void>(edi::experiment_from_edi_text(source)); }, fragment,
                       "a partial plausible background shape must fail closed");
    }

    std::string split_data = valid.substr(0, data_begin);
    split_data += "loop_\n_data.two_theta\n_data.id\n10 1\n"
                  "loop_\n_data.intensity_meas\n_data.intensity_meas_su\n100 1\n";
    check_io_error([&] { static_cast<void>(edi::experiment_from_edi_text(split_data)); },
                   "split across multiple loops",
                   "measured columns split across loops must fail closed");
}

TEST_CASE("E09-T55 TOF writer covers absorption") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures/c11_t4_cw_selection";
    edi::Project project = populated_project(
        edi::structure_from_edi_text(read_text(fixtures / "structure.edi")),
        edi::experiment_from_edi_text(read_text(fixtures / "cases/tof_valid.edi")));
    project.experiment().absorption.type = "cylinder";
    project.experiment().absorption.abscor1 = edi::Parameter{0.2, 0.01, true};
    project.experiment().absorption.abscor2 = edi::Parameter{0.3, 0.02, false};
    project.minimizer_max_iterations = 3;
    TempTree output = temp_tree("tof-absorption-write");
    edi::save_project(project, output.path.string());
    const edi::Project restored = edi::load_project(output.path.string());
    CHECK_MESSAGE(restored.minimizer_max_iterations == 3,
                  "the analysis writer must retain the declared minimizer bound");
    REQUIRE_MESSAGE(restored.experiment().absorption.abscor1.has_value(),
                    "the TOF writer must retain present ABSCOR1");
    CHECK_MESSAGE(restored.experiment().absorption.abscor1->value == doctest::Approx(0.2),
                  "the TOF writer must retain the independently specified ABSCOR1 value");
}

TEST_CASE("E09-T55 TOF writer refuses ragged observations") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures/c11_t4_cw_selection";
    edi::Project project = populated_project(
        edi::structure_from_edi_text(read_text(fixtures / "structure.edi")),
        edi::experiment_from_edi_text(read_text(fixtures / "cases/tof_valid.edi")));
    REQUIRE_MESSAGE(project.experiment().data.has_value(),
                    "the committed TOF fixture must carry observations before the ragged mutation");
    auto ragged_values = static_cast<const std::vector<double>&>(
        project.experiment().data->intensity_meas_su);
    ragged_values.pop_back();
    project.experiment().data->intensity_meas_su = std::move(ragged_values);
    TempTree ragged = temp_tree("ragged-tof-refusal");
    check_io_error([&] { edi::save_project(project, ragged.path.string()); }, "ragged or empty",
                   "a ragged programmatic TOF pattern must fail before any row indexing");
}

TEST_CASE("E09-T55 project loader rejects missing experiment completeness") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures/c11_t4_cw_selection";
    TempTree project = temp_tree("project-missing-experiment");
    std::filesystem::create_directories(project.path / "structures");
    std::filesystem::create_directories(project.path / "experiments");
    std::filesystem::copy_file(fixtures / "structure.edi", project.path / "structures/ncaf.edi");
    check_io_error([&] { static_cast<void>(edi::load_project(project.path.string())); },
                   "no experiments", "a project without experiment files must fail closed");
}

TEST_CASE("E09-T55 project loader rejects a malformed analysis bound") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures/c11_t4_cw_selection";
    TempTree project = temp_tree("project-malformed-analysis");
    std::filesystem::create_directories(project.path / "structures");
    std::filesystem::create_directories(project.path / "experiments");
    std::filesystem::copy_file(fixtures / "structure.edi", project.path / "structures/ncaf.edi");
    write_text(project.path / "experiments/cwl.edi", read_text(fixtures / "cases/cwl_valid.edi"));
    std::filesystem::create_directories(project.path / "analysis");
    write_text(project.path / "analysis/analysis.edi", "_minimizer.max_iterations zero\n");
    check_io_error([&] { static_cast<void>(edi::load_project(project.path.string())); },
                   "need a positive integer", "a malformed minimizer bound must fail closed");
}

TEST_CASE("E09-T55 project loader rejects a zero analysis bound") {
    const std::filesystem::path fixtures = repo_root() / "tests/fixtures/c11_t4_cw_selection";
    TempTree project = temp_tree("project-zero-analysis");
    std::filesystem::create_directories(project.path / "structures");
    std::filesystem::create_directories(project.path / "experiments");
    std::filesystem::copy_file(fixtures / "structure.edi", project.path / "structures/ncaf.edi");
    write_text(project.path / "experiments/cwl.edi", read_text(fixtures / "cases/cwl_valid.edi"));
    std::filesystem::create_directories(project.path / "analysis");
    write_text(project.path / "analysis/analysis.edi", "_minimizer.max_iterations 0\n");
    check_io_error([&] { static_cast<void>(edi::load_project(project.path.string())); },
                   "need a positive integer", "a zero minimizer bound must fail closed");
}

TEST_CASE("E09-T55 JVD selector requires every Lorentzian profile field") {
    const std::filesystem::path source_path =
        repo_root() /
        "tests/fixtures/c09_t6_ncaf_5bank_absorption/expected/desired_writer/jvd_absorption/experiments/wish_2_9.edi";
    const std::string source = read_text(source_path);
    const std::string tag = "_peak.broad_lorentz_gamma_0";
    const std::size_t begin = source.find(tag + " ");
    REQUIRE_MESSAGE(begin != std::string::npos,
                    "the committed JVD fixture must carry the Lorentzian mutation seam");
    const std::size_t end = source.find('\n', begin);
    std::string missing = source;
    missing.erase(begin, end - begin + 1);
    check_io_error([&] { static_cast<void>(edi::experiment_from_edi_text(missing)); }, tag,
                   "a JVD selector must name a missing required Lorentzian field");
}

TEST_CASE("E09-T55 live peak registration is idempotent and mode-specific") {
    CHECK_MESSAGE(!edi::peak_type_known("-private-profile"),
                  "an unregistered profile token must begin unknown");
    edi::register_peak_type("-private-profile", edi::BeamModeEnum::TIME_OF_FLIGHT);
    edi::register_peak_type("-private-profile", edi::BeamModeEnum::CONSTANT_WAVELENGTH);
    CHECK_MESSAGE(edi::peak_type_known("-private-profile"),
                  "a registered profile token must become known and remain registered");
}

TEST_CASE("E09-T55 refinement refuses a measured pattern wholly removed by exclusions") {
    edi::Project project = edi::load_project(
        (repo_root() / "tests/fixtures/e02_t2_ncaf_5bank/project").string());
    project.experiment().excluded_regions = {{-1.0e9, 1.0e9}};

    bool raised = false;
    try {
        static_cast<void>(project.fit({10000.0, 20000.0}, {1.0, 1.0}, {1.0, 1.0}));
    } catch (const std::invalid_argument& error) {
        raised = true;
        CHECK_MESSAGE(std::string(error.what()).find("no measured data remains") != std::string::npos,
                      "a fully excluded measured pattern must identify the empty masked input");
    }
    CHECK_MESSAGE(raised,
                  "a fully excluded measured pattern must fail before entering the minimizer");
}
