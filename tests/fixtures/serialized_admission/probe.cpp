// Exercise public parser entries. Input bytes and expected outcomes belong to
// Python's authored fixtures.
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef SERIALIZED_EDI
#include "edi/io.hpp"
namespace parser_api = edi;
#else
#include "crysta/cif_import.hpp"
#include "crysta/model.hpp"
namespace parser_api = crysta;
#endif
template <class Range>
void numbers(const char* key, const Range& values) {
    std::cout << key;
    for (const auto x : values) std::cout << ' ' << std::setprecision(17) << x;
    std::cout << '\n';
}
void describe(parser_api::BraggPdExperiment& experiment) {
    std::cout << "ADMITTED " << experiment.name.value() << '\n';
    std::cout << "PATH " << std::string(experiment.data_path) << '\n';
    std::cout << "COLLECTION " << std::string(experiment.collection_id) << '\n';
    std::cout << "DIGEST " << std::string(experiment.data_digest) << '\n';
#ifdef SERIALIZED_EDI
    if (experiment.reflections) {
        numbers("I", experiment.reflections->intensity_meas.get());
        numbers("SU", experiment.reflections->intensity_meas_su.get());
    } else if (experiment.data) {
        numbers("I", experiment.data->intensity_meas.get());
        numbers("SU", experiment.data->intensity_meas_su.get());
    }
#else
    if (experiment.reflections.has_value()) {
        numbers("I", experiment.reflections.get()->intensity.values());
        numbers("SU", experiment.reflections.get()->sigma.values());
    } else if (experiment.data.has_value()) {
        numbers("I", experiment.data.get()->intensity.values());
        numbers("SU", experiment.data.get()->sigma.values());
    }
#endif
}
int main(int argc, char** argv) {
    if (argc == 2 && std::string(argv[1]) == "--identity") {
        std::cout << SERIALIZED_OBSERVER_SHA << '\n';
        return 0;
    }
    if (argc != 5) return 3;
    const std::string route(argv[1]), path(argv[2]), project(argv[3]), baseline(argv[4]);
    std::ifstream input(path);
    if (!input) return 4;
    const std::string text((std::istreambuf_iterator<char>(input)), {});
    bool entered = false;
    try {
        if (route == "text") {
            entered = true;
            auto admitted = parser_api::experiment_from_edi_text(text);
            describe(admitted);
#ifdef SERIALIZED_EDI
        } else if (route == "file" || route == "legacy-file") {
            entered = true;
            auto admitted = route == "file" ? edi::load_experiment_file(path)
                                            : edi::load_experiment_edi_file(path);
            describe(admitted);
        } else if (route == "batch") {
            auto destination = edi::load_project(baseline);
            entered = true;
            auto admitted = edi::load_experiment_edi_files(destination, {path});
            describe(admitted.at(0));
        } else if (route == "complete" || route == "construction") {
            entered = true;
            auto admitted = edi::load_project(project, route == "complete"
                                                           ? edi::ProjectLoadMode::Complete
                                                           : edi::ProjectLoadMode::Construction);
#ifdef SERIALIZED_EDI
            describe(*admitted.experiments.front());
#else
            describe(admitted.experiments.front());
#endif
#else
        } else if (route == "convert") {
            entered = true;
            std::vector<std::string> notes;
            const auto converted =
                crysta::cif_to_edi(text, crysta::DocumentKind::Experiment, path, &notes);
            for (const auto& note : notes) std::cout << "NOTE " << note << '\n';
            std::cout << "CONVERTED\n" << converted;
        } else if (route == "file") {
            entered = true;
            auto admitted = crysta::experiment_from_edi_path(path);
            describe(admitted);
#endif
        } else if (route == "project") {
            entered = true;
            auto admitted = parser_api::load_project(project);
#ifdef SERIALIZED_EDI
            describe(*admitted.experiments.front());
#else
            describe(admitted.experiments.front());
#endif
        } else {
            return 5;
        }
    } catch (const std::exception& refusal) {
        std::cout << (entered ? "REFUSED " : "SETUP_FAILURE ") << refusal.what() << '\n';
        return entered ? 0 : 6;
    }
}
