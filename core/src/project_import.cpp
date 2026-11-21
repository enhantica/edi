// SPDX-License-Identifier: BSD-3-Clause
// The shared part of importing another program's project (ADR-0098): the importer list, finding the importer for a
// file, and the steps every conversion goes through.

#include "edi/project_import.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <map>
#include <mutex>
#include <sstream>

#include "edi/edits.hpp"
#include "edi/model.hpp"
#include "edi/parameter_walk.hpp"
#include "cryspy_project.hpp"
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
        {"FullProf", {".pcr"}, [](const std::string& path, const WarningSink&) {
             return detail::import_fullprof_project(path);
         }},
        {"GSAS-II", {".gpx", ".gsas.json"}, [](const std::string& path, const WarningSink&) {
             return load_gsas_project(path);
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
    Project project = importer->convert(path, on_warning);
    detail::finish_imported_project(project, *importer, path);
    return project;
}

void check_import_roundtrip(const Project& imported, const std::string& directory) {
    save_project(imported, directory);
    Project reopened = load_project(directory);
    auto& original = const_cast<Project&>(imported);  // parameter_entries hands out pointers; nothing is changed
    const auto key = [](const ParameterEntry& entry) { return entry.block_kind + ":" + entry.block_name + ":" + entry.path; };
    std::map<std::string, ParameterEntry> after;
    for (auto& entry : parameter_entries(reopened)) after.emplace(key(entry), entry);
    const auto before = parameter_entries(original);
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
        // A value without an s.u. is saved to six significant digits.
        if (std::abs(x - y) > 5e-6 * std::max(std::abs(x), std::abs(y)) + 1e-12) {
            std::ostringstream text;
            text.precision(17);
            text << "the saved project reopens " << where << " at " << y << " instead of " << x;
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
