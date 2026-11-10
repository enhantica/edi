#include <doctest/doctest.h>

#include <fstream>
#include <iterator>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

#include "adapter_test_access.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/validation.hpp"

TEST_CASE("C13-T4 adapter validates the raw texture structure key") {
    // Direct C++ insertion bypasses PrefOrientsView and the file loader.
    const std::string fixture =
        std::string(__FILE__).substr(0, std::string(__FILE__).find("tests/unit/")) +
        "tests/fixtures/c13_t4_march/model.edi";
    std::ifstream input(fixture);
    REQUIRE_MESSAGE(input.good(), " native adapter gate must read the independent fixture");
    const std::string text((std::istreambuf_iterator<char>(input)), {});
    auto experiment = edi::experiment_from_edi_text(text.substr(text.find("data_experiment")));
    auto row = std::make_shared<edi::PrefOrient>();
    row->march_r.value = 0.73;
    row->march_random_fract.value = 0.3;
    experiment.preferred_orientation.push_back(row);
    for (const std::string key : {"strcuture", "unknown", ""}) {
        row->structure_id = key;
        CHECK_THROWS_AS_MESSAGE(edi::detail::to_crysta_experiment(experiment),
                                edi::DomainValidationError,
                                " adapter must reject a row unrelated to the linked structure");
    }
    row->structure_id = experiment.linked_structure().structure_id;
    const auto built = edi::detail::to_crysta_experiment(experiment);
    REQUIRE_MESSAGE(built.preferred_orientations.front().march.size() == 2,
                    " adapter must carry both March parameters for the correct key");
    CHECK_MESSAGE(built.preferred_orientations.front().structure_id.value() == row->structure_id,
                  " adapter must preserve the validated structure identity");
    CHECK_MESSAGE(built.preferred_orientations.front().march[0].value() == doctest::Approx(0.73),
                  " adapter must preserve the nonidentity March ratio");
    experiment.linked_structure().structure_id = "";
    row->structure_id = "unknown";
    CHECK_THROWS_AS_MESSAGE(edi::detail::to_crysta_experiment(experiment),
                            edi::DomainValidationError,
                            " absent phase link cannot authorize an unknown texture key");
    row->structure_id = "structure";
    experiment.linked_structure().structure_id = "renamed_structure";
    CHECK_THROWS_AS_MESSAGE(edi::detail::to_crysta_experiment(experiment),
                            edi::DomainValidationError,
                            " changing the phase link cannot retain a stale texture key");
}

TEST_CASE("C13-T4 adapter refuses raw March domains before conversion") {
    const std::string fixture =
        std::string(__FILE__).substr(0, std::string(__FILE__).find("tests/unit/")) +
        "tests/fixtures/c13_t4_march/model.edi";
    std::ifstream input(fixture);
    REQUIRE_MESSAGE(input.good(), " raw domain gate requires its independent fixture");
    const std::string text((std::istreambuf_iterator<char>(input)), {});
    auto experiment = edi::experiment_from_edi_text(text.substr(text.find("data_experiment")));
    auto row = std::make_shared<edi::PrefOrient>();
    row->structure_id = experiment.linked_structure().structure_id;
    experiment.preferred_orientation.push_back(row);
    const double inf = std::numeric_limits<double>::infinity();
    const double nan = std::numeric_limits<double>::quiet_NaN();
    for (double ratio : {0.0, -0.73, inf, -inf, nan}) {
        row->march_r.value = ratio;
        CHECK_THROWS_AS_MESSAGE(edi::detail::to_crysta_experiment(experiment),
                                edi::DomainValidationError,
                                " adapter must reject a nonpositive or nonfinite March ratio");
    }
    row->march_r.value = 0.73;
    for (double fraction : {-0.01, 1.01, inf, -inf, nan}) {
        row->march_random_fract.value = fraction;
        CHECK_THROWS_AS_MESSAGE(
            edi::detail::to_crysta_experiment(experiment), edi::DomainValidationError,
            " adapter must reject a random fraction outside its finite domain");
    }
    row->march_random_fract.value = 0.3;
    row->index_l = 0;
    CHECK_THROWS_AS_MESSAGE(edi::detail::to_crysta_experiment(experiment),
                            edi::DomainValidationError,
                            " adapter must reject a zero preferred direction");
    row->index_l = 1;
    for (int component :
         {1001, -1001, std::numeric_limits<int>::max(), std::numeric_limits<int>::min()}) {
        for (auto* axis : {&row->index_h, &row->index_k, &row->index_l}) {
            const int old = *axis;
            *axis = component;
            CHECK_THROWS_AS_MESSAGE(edi::detail::to_crysta_experiment(experiment),
                                    edi::DomainValidationError,
                                    " native adapter must enforce the loader axis bound");
            *axis = old;
        }
    }
    row->index_l = 1000;
    for (double fraction : {0.0, 0.3, 1.0}) {
        row->march_random_fract.value = fraction;
        const auto built = edi::detail::to_crysta_experiment(experiment);
        REQUIRE_MESSAGE(built.preferred_orientations.front().march.size() == 2,
                        " valid adapter control must carry the exact row shape");
        CHECK_MESSAGE(
            built.preferred_orientations.front().march[0].value() == doctest::Approx(0.73),
            " valid adapter control must preserve nonidentity March ratio");
        CHECK_MESSAGE(
            built.preferred_orientations.front().march[1].value() == doctest::Approx(fraction),
            " valid adapter control must preserve mixture endpoints");
    }
}
