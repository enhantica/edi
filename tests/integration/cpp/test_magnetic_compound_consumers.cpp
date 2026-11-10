#define C18_EDI_CONSUMER
#include <doctest/doctest.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include "crysta/analysis.hpp"
#include "crysta/magnetic.hpp"
#include "crysta/model.hpp"
#ifdef C18_EDI_CONSUMER
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/symmetry.hpp"
namespace api = edi;
#else
namespace api = crysta;
#endif
namespace {
namespace fs = std::filesystem;
struct Scratch {
    fs::path root = fs::temp_directory_path() /
                    ("magnetic-consumer-" +
                     std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    Scratch() { fs::create_directories(root); }
    ~Scratch() {
        std::error_code error;
        fs::remove_all(root, error);
    }
};
struct Supplied {
    std::string field, tag, good;
    std::vector<std::string> bad;
};
const std::vector<Supplied> declarations{
    {"symmform",
     "_atom_site_moment.symmform",
     "Mx,My,Mz",
     {".", "?", "Mx/0,My,Mz", "1/0Mx,My,Mz", "1e308Mx+1e308Mx,My,Mz",
      "1e308/0.00000000000000000001Mx,My,Mz", "1e308Mx/0.00000000000000000001,My,Mz", "Mx,My,Mz,",
      "Mx,My", "Mx,My,Mz,0"}},
    {"k",
     "_parent_propagation_vector.kxkykz",
     "0,0,0",
     {".", "?", "0,0", "0,0,0,", "0,0,0,1junk", "0/0,0,0", "1e308/0.00000000000000000001,0,0"}},
    {"child",
     "_parent_space_group.child_transform_Pp_abc",
     "a,b,c;0,0,0",
     {".", "?", "a,b;0,0,0", ";0,0,0", ";1/4,0,0", "a,b,c,;0,0,0", "a,b,c;0,0",
      "a,b,c;0,0,0,1junk", "a,b,c;0,0,0,", "a,b,c;1e308/0.00000000000000000001,0,0"}},
    {"operation",
     "_space_group_symop_magn_operation.xyz",
     "x,y,z,+1",
     {".", "?", "x+1/2*x,y,z,+1", "x,y,z,+1,", "x,y,z,+1,0", "x+1/0,y,z,+1", "x,y,z,+1junk",
      "x,y,z,"}},
    {"centering",
     "_space_group_symop_magn_centering.xyz",
     "x,y,z,+1",
     {".", "?", "x+0junk,y,z,+1", "x,y,z,+1,", "x,y,z,+1,0", "x+1/0,y,z,+1", "x,y,z,+1junk"}},
    {"ion", "_magnetic_form_factor.ion", "Ho3+", {".", "?", "Ho3+junk"}},
    {"approximation", "_magnetic_form_factor.approximation", "j0", {".", "?", "j0junk"}},
};
void put(const fs::path& path, const std::string& text) { std::ofstream(path) << text; }
std::string text(const fs::path& path) {
    std::ifstream in(path);
    return {std::istreambuf_iterator<char>(in), {}};
}
void supply(api::Structure& s, const Supplied& declaration, const std::string& value) {
#ifdef C18_EDI_CONSUMER
    if (declaration.field == "symmform")
        s.atom_site_moment[0]->symmform = value;
    else if (declaration.field == "ion")
        s.magnetic_form_factors[0]->ion = value;
    else if (declaration.field == "approximation")
        s.magnetic_form_factors[0]->approximation = value;
    else {
        auto magnetic = s.magnetic.get();
        if (declaration.field == "k") magnetic.propagation_vectors = {{"1", value}};
        if (declaration.field == "child") magnetic.parent.child_transform_pp_abc = value;
        if (declaration.field == "operation") magnetic.operations = {{"1", value}};
        if (declaration.field == "centering") magnetic.centerings = {{"1", value}};
        s.magnetic = magnetic;
    }
#else
    if (declaration.field == "symmform") s.atom_site_moment[0].symmform = value;
    if (declaration.field == "ion") s.magnetic_form_factors[0].ion = value;
    if (declaration.field == "approximation") s.magnetic_form_factors[0].approximation = value;
    if (declaration.field == "k")
        s.propagation_vectors = std::vector<std::pair<std::string, std::string>>{{"1", value}};
    if (declaration.field == "child") {
        auto parent = s.parent_space_group.get();
        parent.child_transform_pp_abc = value;
        s.parent_space_group = parent;
    }
    if (declaration.field == "operation")
        s.magnetic_operations = std::vector<std::pair<std::string, std::string>>{{"1", value}};
    if (declaration.field == "centering")
        s.magnetic_centerings = std::vector<std::pair<std::string, std::string>>{{"1", value}};
#endif
}
void consume(api::Project& model, const std::string& stage, const fs::path& root) {
    if (stage == "completion" || stage == "adapter-transfer") {
#ifdef C18_EDI_CONSUMER
        edi::complete_atom_site_moments(model.structure());
#else
        model.structure().complete_atom_site_moment();
#endif
    } else if (stage == "save")
        api::save_project(model, (root / "saved").string());
    else if (stage == "second-save") {
        api::save_project(model, (root / "first").string());
        auto again = api::load_project((root / "first").string());
        api::save_project(again, (root / "second").string());
    } else if (stage == "parent-view") {
#ifdef C18_EDI_CONSUMER
        (void)crysta::parent_asymmetric_sites(model.structure().magnetic->parent,
                                              std::vector<std::array<double, 3>>{{0, 0, 0}},
                                              std::vector<std::string>{"Ho"});
#else
        (void)crysta::parent_asymmetric_sites(model.structure());
#endif
    } else if (stage == "calculate") {
#ifdef C18_EDI_CONSUMER
        model.calculate();
#else
        crysta::calculate_project(model);
#endif
    } else if (stage == "fit-preparation") {
#ifdef C18_EDI_CONSUMER
        model.structure().atom_site_moment[0]->crystalaxis_x.free = true;
        (void)model.fit();
#else
        model.structure().atom_site_moment[0].moment[0].set_free(true);
        (void)crysta::fit_project(model);
#endif
    }
}
}  // namespace

void exercise_compound_consumer(const std::string& field, const std::string& requested_stage) {
    const auto fixture = fs::path(__FILE__).parent_path() / "../../fixtures/magnetic_pnma";
    for (const auto& declaration : declarations) {
        if (declaration.field != field) continue;
        for (const std::string stage : {"completion", "adapter-transfer", "save", "second-save",
                                        "calculate", "fit-preparation", "parent-view"}) {
            if (stage != requested_stage) continue;
            // The parent-site view consumes only the child transform.
            if (stage == "parent-view" && declaration.field != "child") continue;
#ifndef C18_EDI_CONSUMER
            if (stage == "adapter-transfer") continue;
#endif
            for (const std::string entrance : {"project", "factory"}) {
                auto exercise = [&](const std::string& value, bool malformed) {
                    Scratch scratch;
                    fs::create_directories(scratch.root / "input/structures");
                    fs::create_directories(scratch.root / "input/experiments");
                    put(scratch.root / "input/project.edi",
                        "_edi.schema_version 3\n_minimizer.type crysta\n_minimizer.max_iterations "
                        "1\n");
                    put(scratch.root / "input/structures/cosio.edi",
                        text(fixture / "compound-control.edi"));
                    fs::copy_file(fixture / "compound-experiment.edi",
                                  scratch.root / "input/experiments/d20.edi");
                    auto model = api::load_project((scratch.root / "input").string());
                    if (entrance == "factory") {
#ifdef C18_EDI_CONSUMER
                        const auto structure = edi::structure_from_edi_text(
                            text(fixture / "compound-control.edi"), "compound consumer control");
#else
                        const auto structure = crysta::structure_from_edi_text(
                            text(fixture / "compound-control.edi"));
#endif
                        model.structure() = structure;
                    }
                    // Mutate a decoded member after successful load: an earlier parser
                    // cannot conceal an accepting consumer. An assignment that refuses
                    // the supplied value is also a valid earlier boundary.
                    bool refused = false;
                    std::string reason;
                    try {
                        supply(model.structure(), declaration, value);
                        consume(model, stage, scratch.root);
                    } catch (const std::exception& error) {
                        refused = true;
                        reason = error.what();
                    }
                    CAPTURE(declaration.tag);
                    CAPTURE(value);
                    CAPTURE(stage);
                    CAPTURE(entrance);
                    CAPTURE(reason);
                    if (malformed) {
                        CHECK_MESSAGE(refused,
                                      "ADR-0108 section 12 every supplied compound parses whole "
                                      "at its actual downstream consumer");
                        CHECK_MESSAGE(
                            (!refused || (reason.find(declaration.tag) != std::string::npos &&
                                          reason.find(value) != std::string::npos)),
                            "A malformed decoded declaration refuses naming its tag and complete "
                            "supplied value");
                    } else {
                        CHECK_MESSAGE(!refused,
                                      "A complete independently stated valid compound reaches the "
                                      "same downstream consumer");
                    }
                };
                exercise(declaration.good, false);
                if (declaration.field == "child") exercise("", false);
                if (declaration.field == "symmform") {
                    exercise("Mx/2,2My,Mz", false);
                    exercise("1/2Mx,My/2,Mz", false);
                }
                for (const auto& bad : declaration.bad) exercise(bad, true);
            }
        }
    }
}

TEST_CASE("Magnetic decoded symmform reaches completion") {
    exercise_compound_consumer("symmform", "completion");
}

TEST_CASE("Magnetic decoded symmform reaches save") {
    exercise_compound_consumer("symmform", "save");
}

TEST_CASE("Magnetic decoded symmform reaches second-save") {
    exercise_compound_consumer("symmform", "second-save");
}

TEST_CASE("Magnetic decoded symmform reaches calculate") {
    exercise_compound_consumer("symmform", "calculate");
}

TEST_CASE("Magnetic decoded symmform reaches fit-preparation") {
    exercise_compound_consumer("symmform", "fit-preparation");
}

TEST_CASE("Magnetic decoded k reaches completion") {
    exercise_compound_consumer("k", "completion");
}

TEST_CASE("Magnetic decoded k reaches save") { exercise_compound_consumer("k", "save"); }

TEST_CASE("Magnetic decoded k reaches second-save") {
    exercise_compound_consumer("k", "second-save");
}

TEST_CASE("Magnetic decoded k reaches calculate") { exercise_compound_consumer("k", "calculate"); }

TEST_CASE("Magnetic decoded k reaches fit-preparation") {
    exercise_compound_consumer("k", "fit-preparation");
}

TEST_CASE("Magnetic decoded child reaches completion") {
    exercise_compound_consumer("child", "completion");
}

TEST_CASE("Magnetic decoded child reaches save") { exercise_compound_consumer("child", "save"); }

TEST_CASE("Magnetic decoded child reaches second-save") {
    exercise_compound_consumer("child", "second-save");
}

TEST_CASE("Magnetic decoded child reaches calculate") {
    exercise_compound_consumer("child", "calculate");
}

TEST_CASE("Magnetic decoded child reaches fit-preparation") {
    exercise_compound_consumer("child", "fit-preparation");
}

TEST_CASE("Magnetic decoded child reaches parent-view") {
    exercise_compound_consumer("child", "parent-view");
}

TEST_CASE("Magnetic decoded operation reaches completion") {
    exercise_compound_consumer("operation", "completion");
}

TEST_CASE("Magnetic decoded operation reaches save") {
    exercise_compound_consumer("operation", "save");
}

TEST_CASE("Magnetic decoded operation reaches second-save") {
    exercise_compound_consumer("operation", "second-save");
}

TEST_CASE("Magnetic decoded operation reaches calculate") {
    exercise_compound_consumer("operation", "calculate");
}

TEST_CASE("Magnetic decoded operation reaches fit-preparation") {
    exercise_compound_consumer("operation", "fit-preparation");
}

TEST_CASE("Magnetic decoded centering reaches completion") {
    exercise_compound_consumer("centering", "completion");
}

TEST_CASE("Magnetic decoded centering reaches save") {
    exercise_compound_consumer("centering", "save");
}

TEST_CASE("Magnetic decoded centering reaches second-save") {
    exercise_compound_consumer("centering", "second-save");
}

TEST_CASE("Magnetic decoded centering reaches calculate") {
    exercise_compound_consumer("centering", "calculate");
}

TEST_CASE("Magnetic decoded centering reaches fit-preparation") {
    exercise_compound_consumer("centering", "fit-preparation");
}

TEST_CASE("Magnetic decoded ion reaches completion") {
    exercise_compound_consumer("ion", "completion");
}

TEST_CASE("Magnetic decoded ion reaches save") { exercise_compound_consumer("ion", "save"); }

TEST_CASE("Magnetic decoded ion reaches second-save") {
    exercise_compound_consumer("ion", "second-save");
}

TEST_CASE("Magnetic decoded ion reaches calculate") {
    exercise_compound_consumer("ion", "calculate");
}

TEST_CASE("Magnetic decoded ion reaches fit-preparation") {
    exercise_compound_consumer("ion", "fit-preparation");
}

TEST_CASE("Magnetic decoded approximation reaches completion") {
    exercise_compound_consumer("approximation", "completion");
}

TEST_CASE("Magnetic decoded approximation reaches save") {
    exercise_compound_consumer("approximation", "save");
}

TEST_CASE("Magnetic decoded approximation reaches second-save") {
    exercise_compound_consumer("approximation", "second-save");
}

TEST_CASE("Magnetic decoded approximation reaches calculate") {
    exercise_compound_consumer("approximation", "calculate");
}

TEST_CASE("Magnetic decoded approximation reaches fit-preparation") {
    exercise_compound_consumer("approximation", "fit-preparation");
}

TEST_CASE("Magnetic decoded symmform reaches adapter-transfer") {
    exercise_compound_consumer("symmform", "adapter-transfer");
}

TEST_CASE("Magnetic decoded k reaches adapter-transfer") {
    exercise_compound_consumer("k", "adapter-transfer");
}

TEST_CASE("Magnetic decoded child reaches adapter-transfer") {
    exercise_compound_consumer("child", "adapter-transfer");
}

TEST_CASE("Magnetic decoded operation reaches adapter-transfer") {
    exercise_compound_consumer("operation", "adapter-transfer");
}

TEST_CASE("Magnetic decoded centering reaches adapter-transfer") {
    exercise_compound_consumer("centering", "adapter-transfer");
}

TEST_CASE("Magnetic decoded ion reaches adapter-transfer") {
    exercise_compound_consumer("ion", "adapter-transfer");
}

TEST_CASE("Magnetic decoded approximation reaches adapter-transfer") {
    exercise_compound_consumer("approximation", "adapter-transfer");
}

namespace {
api::Project cache_layout_project(const fs::path& root) {
    const auto fixture = fs::path(__FILE__).parent_path() / "../../fixtures/magnetic_pnma";
    fs::create_directories(root / "structures");
    fs::create_directories(root / "experiments");
    put(root / "project.edi",
        "_edi.schema_version 3\n_minimizer.type crysta\n_minimizer.max_iterations 1\n");
    put(root / "structures/cosio.edi", text(fixture / "cache-layout-control.edi"));
    fs::copy_file(fixture / "compound-experiment.edi", root / "experiments/d20.edi");
    return api::load_project(root.string());
}

auto cache_rows(api::Structure& structure) {
    return std::vector{structure.atom_site_moment[0], structure.atom_site_moment[1],
                       structure.atom_site_moment[2]};
}

void keep_first_moment(api::Structure& structure) {
    const auto first = structure.atom_site_moment[0];
    structure.atom_site_moment.clear();
    structure.atom_site_moment.push_back(first);
}

void clear_cache_control_k(api::Structure& structure) {
#ifdef C18_EDI_CONSUMER
    auto held = structure.magnetic.get();
    held.propagation_vectors.clear();
    structure.magnetic = held;
#else
    structure.propagation_vectors = std::vector<std::pair<std::string, std::string>>{};
#endif
}

void invalid_cache_layout(api::Structure& structure) {
#ifdef C18_EDI_CONSUMER
    structure.atom_site_moment[1]->symmform = "Ho3+";
    structure.atom_site_moment[2]->symmform = "j0";
#else
    structure.atom_site_moment[1].symmform = std::string("Ho3+");
    structure.atom_site_moment[2].symmform = std::string("j0");
#endif
    structure.magnetic_form_factors.clear();
}

void cache_calculate(api::Project& project) {
#ifdef C18_EDI_CONSUMER
    project.calculate();
#else
    crysta::calculate_project(project);
#endif
}

void require_cache_refusal(api::Project& project, const std::string& history) {
    bool refused = false;
    std::string reason;
    try {
        cache_calculate(project);
    } catch (const std::exception& error) {
        refused = true;
        reason = error.what();
    }
    CAPTURE(history);
    CAPTURE(reason);
    CHECK_MESSAGE(refused,
                  "ADR-0108 invalid supplied symmetry forms refuse independently of earlier "
                  "validation history");
    CHECK_MESSAGE(
        (!refused ||
         (reason.find("_atom_site_moment.symmform") != std::string::npos &&
          (reason.find("Ho3+") != std::string::npos || reason.find("j0") != std::string::npos))),
        "Cold and warmed invalid layouts name the supplied moment-form tag and invalid value");
}

void exercise_typed_layout_cache(bool edit_same_project) {
    const Scratch scratch;
    auto sentinel = cache_layout_project(scratch.root / "sentinel");
    auto warm = cache_layout_project(scratch.root / "warm");
    auto cold = cache_layout_project(scratch.root / "cold");
    auto independent = cache_layout_project(scratch.root / "independent");
    auto valid_without_factors = cache_layout_project(scratch.root / "valid-without-factors");
    const auto retained_rows = cache_rows(warm.structure());
    keep_first_moment(warm.structure());
    keep_first_moment(sentinel.structure());
    clear_cache_control_k(sentinel.structure());
    valid_without_factors.structure().magnetic_form_factors.clear();
    REQUIRE_NOTHROW_MESSAGE(
        cache_calculate(valid_without_factors),
        "Three valid P1 moment rows remain valid without explicit form-factor rows");
    REQUIRE_NOTHROW_MESSAGE(
        cache_calculate(sentinel),
        "A distinct valid absent-k control establishes a cold typed-layout comparison");
    try {
        invalid_cache_layout(cold.structure());
        invalid_cache_layout(independent.structure());
    } catch (const std::exception& error) {
        const std::string reason = error.what();
        CHECK_MESSAGE(
            reason.find("_atom_site_moment.symmform") != std::string::npos,
            "An earlier assignment refusal closes the invalid layout at its typed boundary");
        return;
    }
    require_cache_refusal(cold, "cold invalid layout");
    // Both candidates retain exactly the same k, parent, operations, centrings and
    // numeric site data. Only the typed list layout differs: one form plus an
    // ion/approximation pair versus three supplied forms and no factor rows.
    REQUIRE_NOTHROW_MESSAGE(
        cache_calculate(warm),
        "A valid one-moment plus Ho3+/j0 layout warms the ordinary calculation path");
    if (edit_same_project) {
        try {
            warm.structure().atom_site_moment.clear();
            for (const auto& row : retained_rows) warm.structure().atom_site_moment.push_back(row);
            invalid_cache_layout(warm.structure());
        } catch (const std::exception& error) {
            const std::string reason = error.what();
            CHECK_MESSAGE(
                reason.find("_atom_site_moment.symmform") != std::string::npos,
                "A checked in-place edit may refuse the invalid supplied form before calculation");
            return;
        }
        require_cache_refusal(warm, "same project edited to a different typed layout");
    } else {
        require_cache_refusal(independent, "independent project after valid warm-up");
    }
}
}  // namespace

TEST_CASE("Magnetic validation history cannot admit a different independent typed layout") {
    exercise_typed_layout_cache(false);
}

TEST_CASE("Magnetic validation history cannot admit a different edited typed layout") {
    exercise_typed_layout_cache(true);
}
