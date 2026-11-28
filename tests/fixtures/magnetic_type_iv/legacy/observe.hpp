#pragma once
// Regression observations only, generated on edi 499909374 and crysta 8453a08e9.
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iterator>
#include <sstream>
#include <string>

#include "edi/fullprof.hpp"
#include "edi/io.hpp"
#include "edi/project_import.hpp"
#include "edi/symmetry.hpp"
namespace legacy_magnetic_editor {
inline std::string observe(const std::filesystem::path& input,
                           const std::filesystem::path& output) {
    auto project = edi::load_project(input.string());
    std::ostringstream result;
    result << std::setprecision(17);
    auto& model = *project.structures[0];
    const auto atom = edi::new_atom_site(model, [] { return .137; });
    result << "new-atom\n"
           << atom.wyckoff_letter << '\n'
           << atom.fract_x.value << ' ' << atom.fract_y.value << ' ' << atom.fract_z.value << '\n';
    result << "loaded\n"
           << edi::block_edi_text(project, edi::BlockKind::STRUCTURE, model.name.value());
    std::string exported;
    try {
        exported = edi::export_fullprof_project(project, output.string(), true);
        std::ifstream file(exported);
        result << "exported-data\n";
        std::string line;
        while (std::getline(file, line)) {
            const auto comment = line.find('!');
            if (comment == 0) continue;
            result << line.substr(0, comment) << '\n';
        }
    } catch (const std::exception& error) {
        result << "export-refusal\n" << error.what() << '\n';
    }
    if (!exported.empty()) {
        try {
            const auto imported = edi::import_project(exported);
            result << "imported\n";
            for (const auto& structure : imported.structures) {
                auto structure_only = edi::empty_project("regression", "");
                structure_only.structures.push_back(std::make_shared<edi::Structure>(*structure));
                result << edi::block_edi_text(structure_only, edi::BlockKind::STRUCTURE,
                                              structure->name.value());
            }
        } catch (const std::exception& error) {
            result << "import-refusal\n" << error.what() << '\n';
        }
    }
    auto text = result.str();
    const auto prefix = std::filesystem::absolute(output).string();
    std::size_t at = 0;
    while ((at = text.find(prefix, at)) != std::string::npos) {
        text.replace(at, prefix.size(), "<export>");
        at += 8;
    }
    return text;
}
}  // namespace legacy_magnetic_editor
