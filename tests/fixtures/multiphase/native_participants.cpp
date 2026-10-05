#include <iostream>
#include <string>
#include <vector>

#include "edi/io.hpp"
#include "edi/model.hpp"
int main(int argc, char** argv) {
    if (argc != 5) return 2;
    try {
        auto project = edi::load_project(argv[1]);
        const std::string route = argv[2], empty = argv[3], spelling = argv[4];
        for (auto& structure : project.structures)
            if (structure->name.value() == empty) structure->atom_sites.clear();
        if (spelling == "empty-structure-name") project.structures.front()->name = "";
        if (spelling == "empty-link-id") project.experiment().linked_structure().structure_id = "";
        const auto cancel = [] { return true; };
        if (route == "explicit-single") {
            const auto& data = *project.experiment().data;
            (void)project.fit(data.axis(), data.intensity_meas, data.intensity_meas_su, {}, {},
                              cancel);
        } else if (route == "explicit-joint") {
            std::vector<edi::PdDataBase> patterns;
            for (const auto& bank : project.experiments) patterns.push_back(*bank->data);
            (void)project.fit_joint(patterns, {}, {}, cancel);
        } else
            return 3;
        std::cout << "ADMITTED\n";
    } catch (const std::exception& e) {
        std::cout << "REFUSED " << e.what() << '\n';
    }
}
