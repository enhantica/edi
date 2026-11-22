// SPDX-License-Identifier: BSD-3-Clause
// The shared part of importing another program's project (ADR-0098): the importer list, finding the importer for a
// file, and the steps every conversion goes through.

#include "edi/project_import.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <locale>
#include <map>
#include <mutex>
#include <sstream>

#include "edi/edits.hpp"
#include "edi/model.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/display.hpp"
#include "cryspy_project.hpp"
#include "edi/fullprof.hpp"
#include "fullprof_project_io.hpp"
#include "gsas_project.hpp"

namespace edi {
namespace fs = std::filesystem;

namespace {

std::string lowercase(std::string text) {
    std::transform(text.begin(), text.end(), text.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return text;
}

std::mutex& importers_mutex() {
    static std::mutex mutex;
    return mutex;
}

std::vector<ProjectImporter>& importers() {
    static std::vector<ProjectImporter> list{
        {"cryspy", {".rcif"}, [](const std::string& path, const WarningSink& on_warning) {
             return load_cryspy_project(path, on_warning);
         }},
        {"FullProf", {".pcr"}, [](const std::string& path, const WarningSink& on_warning) {
             return detail::import_fullprof_project(path, on_warning);
         }},
        {"GSAS-II", {".gpx", ".gsas.json"}, [](const std::string& path, const WarningSink& on_warning) {
             return load_gsas_project(path, on_warning);
         }},
    };
    return list;
}

// The importer's suffix that ends the file name, longest first so ".gsas.json" wins over a shorter one.
std::optional<std::string> matching_suffix(const ProjectImporter& importer, const std::string& filename) {
    std::optional<std::string> found;
    for (const auto& suffix : importer.suffixes) {
        if (filename.ends_with(suffix) && filename.size() > suffix.size() && (!found || suffix.size() > found->size())) {
            found = suffix;
        }
    }
    return found;
}

std::string parameter_place(const Project& project, std::size_t index) {
    std::size_t at = 0;
    for (const auto& structure : project.structures) {
        const auto count = structure->parameters().size();
        if (index < at + count) return "structure '" + structure->name.value() + "'";
        at += count;
    }
    for (const auto& experiment : project.experiments) {
        const auto count = experiment->parameters().size();
        if (index < at + count) return "experiment '" + experiment->name.value() + "'";
        at += count;
    }
    return "the project";
}

std::string parameter_name(const Parameter& parameter) {
    return parameter.spec != nullptr ? std::string(parameter.spec->name) : std::string("a parameter");
}

}  // namespace

std::vector<ProjectImporter> project_importers() {
    const std::lock_guard lock(importers_mutex());
    return importers();
}

void register_project_importer(ProjectImporter importer) {
    if (importer.program.empty() || importer.suffixes.empty() || !importer.convert) {
        throw std::invalid_argument("a project importer needs a program name, at least one suffix and a conversion");
    }
    for (auto& suffix : importer.suffixes) {
        suffix = lowercase(suffix);
        if (suffix.size() < 2 || suffix.front() != '.') {
            throw std::invalid_argument("an importer's suffix starts with a dot: '" + suffix + "'");
        }
    }
    const std::lock_guard lock(importers_mutex());
    for (const auto& existing : importers()) {
        for (const auto& suffix : importer.suffixes) {
            if (std::find(existing.suffixes.begin(), existing.suffixes.end(), suffix) != existing.suffixes.end()) {
                throw std::invalid_argument("the " + existing.program + " importer already reads " + suffix + " files");
            }
        }
    }
    importers().push_back(std::move(importer));
}

std::optional<ProjectImporter> project_importer_for(const std::string& path) {
    const auto filename = lowercase(fs::path(path).filename().string());
    const std::lock_guard lock(importers_mutex());
    std::optional<ProjectImporter> best;
    std::size_t best_length = 0;
    for (const auto& importer : importers()) {
        if (const auto suffix = matching_suffix(importer, filename); suffix && suffix->size() > best_length) {
            best = importer;
            best_length = suffix->size();
        }
    }
    return best;
}

bool is_imported_project_path(const std::string& path) {
    std::error_code error;
    return project_importer_for(path).has_value() && !fs::is_directory(fs::path(path), error);
}

Project import_project(const std::string& path, const WarningSink& on_warning) {
    const auto importer = project_importer_for(path);
    if (!importer) {
        throw IoError("No importer reads '" + path + "'");
    }
    // With no sink the notes go to stderr, as the project loader's own warnings do.
    const WarningSink sink = on_warning ? on_warning : WarningSink([](const std::string& message) {
        std::cerr << "Warning: " << message << "\n";
    });
    Project project = importer->convert(path, sink);
    detail::finish_imported_project(project, *importer, path);
    return project;
}

std::vector<ProjectExporter> project_exporters() {
    return {
        {"cryspy", ".rcif", [](const Project& project, const std::string& directory) {
             return export_cryspy_project(project, directory);
         }},
        {"FullProf", ".pcr", [](const Project& project, const std::string& directory) {
             return export_fullprof_project(project, directory);
         }},
    };
}

std::string export_project(const std::string& program, const Project& project, const std::string& directory) {
    for (const auto& exporter : project_exporters()) {
        if (exporter.program == program) return exporter.write(project, directory);
    }
    throw IoError("No exporter writes " + program + " projects");
}

void check_import_roundtrip(const Project& imported, const std::string& directory) {
    save_project(imported, directory);
    Project reopened = load_project(directory);
    auto& original = const_cast<Project&>(imported);  // parameter_entries hands out pointers; nothing is changed
    const auto key = [](const ParameterEntry& entry) { return entry.block_kind + ":" + entry.block_name + ":" + entry.path; };
    std::map<std::string, ParameterEntry> after;
    for (auto& entry : parameter_entries(reopened)) after.emplace(key(entry), entry);
    const auto before = parameter_entries(original);
    const auto spelling = save_spelling(imported);
    if (before.size() != after.size()) {
        throw IoError("the saved project reopens with " + std::to_string(after.size()) + " parameters instead of " +
                      std::to_string(before.size()));
    }
    for (const auto& entry : before) {
        const auto found = after.find(key(entry));
        if (found == after.end()) throw IoError("the saved project reopens without " + key(entry));
        const Parameter& a = *entry.parameter;
        const Parameter& b = *found->second.parameter;
        const std::string where = entry.path + " of " + entry.block_kind + " '" + entry.block_name + "'";
        if (a.spec != b.spec) {
            throw IoError("the saved project reopens " + where + " as " + parameter_name(b));
        }
        if (a.free.get() != b.free.get()) {
            throw IoError("the saved project reopens " + where + (b.free.get() ? " free" : " fixed"));
        }
        // A value symmetry fixes or a tie sets is worked out again when the project opens.
        if (!entry.refinable || !found->second.refinable) continue;
        const double x = a.value.get();
        const double y = b.value.get();
        const auto close = [&](double expected, double relative, double absolute) {
            return std::abs(expected - y) <= relative * std::max(std::abs(expected), std::abs(y)) + absolute;
        };
        // The value as the save spells it: rounded by its s.u. under the project's rule, or exactly where the writer
        // keeps a cell or every value exact (save_spelling).
        std::optional<double> spelled;
        if (a.spec != nullptr && std::isfinite(x)) {
            std::istringstream written(file_text(a, imported.su_rule, written_exactly(spelling, imported, a)).value);
            written.imbue(std::locale::classic());
            double parsed = 0;
            if (written >> parsed && (written >> std::ws).eof()) spelled = parsed;
        }
        const auto su = a.uncertainty.get();
        const bool rounded_by_su = a.free.get() && su && std::isfinite(*su) && *su > 0.;
        // A value the s.u. does not round is saved to at least six significant digits.
        const bool kept = (spelled && close(*spelled, 1e-12, 1e-15)) || (!rounded_by_su && close(x, 5e-6, 1e-12));
        if (!kept) {
            std::ostringstream text;
            text.precision(17);
            text << "the saved project reopens " << where << " at " << y << " instead of " << spelled.value_or(x);
            throw IoError(text.str());
        }
    }
}

namespace detail {

std::string imported_name(std::string name, std::string_view fallback) {
    for (char& c : name) {
        if (!std::isalnum(static_cast<unsigned char>(c)) && c != '_' && c != '-') {
            c = '_';
        }
    }
    if (!persistable_name(name) || !std::isalpha(static_cast<unsigned char>(name.front()))) {
        name = std::string(fallback) + name;
    }
    if (name.size() < 2) {
        name += '_';
    }
    name.resize(std::min<std::size_t>(name.size(), 31));
    return name;
}

void finish_imported_project(Project& project, const ProjectImporter& importer, const std::string& path) {
    const auto filename = fs::path(path).filename().string();
    const auto suffix = matching_suffix(importer, lowercase(filename));
    const auto stem = suffix ? filename.substr(0, filename.size() - suffix->size()) : fs::path(path).stem().string();
    project.metadata.name = validated_project_name(imported_name(stem, "project_"));
    if (project.metadata.description.empty()) {
        project.metadata.description = "Imported from " + importer.program + ": " + filename;
    }
    // A conversion that replaced a whole parameter instead of setting its value leaves it without the slot's metadata
    // (its name, units and limits); a peak slot takes its own back, anything else is the importer's mistake.
    for (const auto& experiment : project.experiments) {
        canonicalize_peak_specs(experiment->peak);
        require_peak_slots_fit_type(*experiment);
    }
    const auto parameters = project.parameters();
    for (std::size_t i = 0; i < parameters.size(); ++i) {
        if (parameters[i]->spec == nullptr) {
            throw IoError("The " + importer.program + " import left a parameter of " + parameter_place(project, i) +
                          " without its metadata");
        }
    }
}

}  // namespace detail
}  // namespace edi
