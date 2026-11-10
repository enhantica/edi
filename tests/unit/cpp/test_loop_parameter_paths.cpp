#include <doctest/doctest.h>

#include <map>
#include <string>

#include "edi/parameter_walk.hpp"

namespace {
template <class Term>
void seed_term(Term& term, const char* id) {
    if constexpr (requires { term.id; }) {
        term.id = id;
    } else {
        FAIL_CHECK("Every background term must own a declared row id before paths can name it");
    }
}
}  // namespace

TEST_CASE("Every experiment loop path names the declared row id") {
    for (const std::string type : {"line-segment", "polynomial", "chebyshev"}) {
        edi::Project project;
        auto& experiment = project.experiment();
        project.structures.clear();
        // This gate isolates experiment path spelling; structural paths have their own census.
        experiment.linked_structures[0]->structure_id = "phase";
        experiment.background_type = type;
        experiment.background.clear();
        experiment.background_terms.clear();
        std::map<edi::Parameter*, std::pair<std::string, std::string>> expected;
        if (type == "line-segment") {
            for (const char* id : {"p17", "p93"}) {
                edi::LineSegment point;
                point.id = id;
                point.position = 24.873;
                point.intensity.value = 0.375;
                experiment.background.push_back(point);
                expected[&experiment.background.back()->intensity] = {
                    id, "experiment.background[" + std::string(id) + "].intensity"};
            }
        } else {
            for (const char* id : {"base", "ramp"}) {
                edi::PolynomialTerm term;
                seed_term(term, id);
                term.coef.value = -.625;
                term.order = static_cast<int>(experiment.background_terms.size());
                experiment.background_terms.push_back(term);
                expected[&experiment.background_terms.back()->coef] = {
                    id, "experiment.background[" + std::string(id) + "].coef"};
            }
        }
        edi::PrefOrient texture;
        texture.structure_id = "phase";
        texture.march_r.value = .73;
        experiment.preferred_orientation.push_back(texture);
        auto& row = *experiment.preferred_orientation[0];
        expected[&row.march_r] = {"phase", "experiment.preferred_orientation[phase].march_r"};
        expected[&row.march_random_fract] = {
            "phase", "experiment.preferred_orientation[phase].march_random_fract"};
        expected[&experiment.linked_structures[0]->scale] = {
            "phase", "experiment.linked_structures[phase].scale"};
        std::size_t observed = 0;
        for (const auto& entry : edi::parameter_entries(project)) {
            if (!expected.contains(entry.parameter)) continue;
            ++observed;
            CHECK_MESSAGE(
                entry.row_label == expected.at(entry.parameter).first,
                "Every loop row label must retain its declared id rather than its index");
            CHECK_MESSAGE(
                entry.path == expected.at(entry.parameter).second,
                "Every loop path must use its declared id, including a single linked structure");
        }
        CHECK_MESSAGE(observed == expected.size(),
                      "The path census must reach each declared row parameter exactly once");
    }
}
