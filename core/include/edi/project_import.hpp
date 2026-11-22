// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_PROJECT_IMPORT_HPP
#define EDI_PROJECT_IMPORT_HPP

#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "edi/io.hpp"

namespace edi {

// Importing another program's project (ADR-0098). An importer recognises its files by suffix and converts one into a
// new, unsaved project. The shared steps around every conversion name the project after its file, record where it
// came from, and refuse a parameter left without its metadata, so a further program only supplies the conversion.
struct ProjectImporter {
    std::string program;                // as users see it: "FullProf"
    std::vector<std::string> suffixes;  // lower case, with the dot: ".pcr", ".gsas.json"
    std::function<Project(const std::string& path, const WarningSink& on_warning)> convert;
};

// The importers in the order the Load project menu lists them.
std::vector<ProjectImporter> project_importers();
// Adds an importer after the built-in ones. A suffix another importer already claims is refused.
void register_project_importer(ProjectImporter importer);
// The importer whose suffix ends the file name, compared without case.
std::optional<ProjectImporter> project_importer_for(const std::string& path);
// A file (not a folder) that one of the importers reads.
bool is_imported_project_path(const std::string& path);
// Converts the file with its importer and applies the shared steps. Throws IoError when no importer reads it.
Project import_project(const std::string& path, const WarningSink& on_warning = {});

// Exporting a copy of a project for another program (ADR-0098): the program's name, the hint the Save project as
// menu shows, and a writer that creates `directory` and returns the main file it wrote there.
struct ProjectExporter {
    std::string program;  // as users see it: "FullProf"
    std::string hint;     // ".pcr"
    std::function<std::string(const Project& project, const std::string& directory)> write;
};

// The exporters in the order the Save project as menu lists them. GSAS-II has none yet (ADR-0097).
std::vector<ProjectExporter> project_exporters();
// Writes a copy of the project with the named program's exporter into the new `directory`. Throws IoError when no
// exporter has that name, and whatever the writer refuses.
std::string export_project(const std::string& program, const Project& project, const std::string& directory);

// Saves an imported project to `directory`, opens it again and compares every parameter's value (to the six
// significant digits a value without an s.u. is saved with), free flag and metadata. Throws IoError naming the
// first difference. Checks and the corpus tools use it; opening never does.
void check_import_roundtrip(const Project& imported, const std::string& directory);

namespace detail {
// A source name made usable as a project or datablock name: other characters become `_`, a name that cannot start
// one gets `fallback` in front, and it is cut to 31 characters.
std::string imported_name(std::string name, std::string_view fallback);
// The steps every importer's result goes through (also run by import_project).
void finish_imported_project(Project& project, const ProjectImporter& importer, const std::string& path);
}  // namespace detail

}  // namespace edi

#endif
