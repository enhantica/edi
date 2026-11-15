// SPDX-License-Identifier: BSD-3-Clause
// ADR-0087 point 1: grouping a selection of data files into a series of joint fits by their names alone.
#include <algorithm>
#include <cctype>
#include <cstddef>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#include "edi/io.hpp"
#include "edi/scan.hpp"

namespace edi {

namespace {

// A name cut into runs, digit runs and the text between them, in order.
struct Runs {
    std::vector<std::string> parts;
    std::vector<std::size_t> digits;  // the places of the digit runs in `parts`
};

Runs runs_of(const std::string& name) {
    Runs out;
    for (std::size_t i = 0; i < name.size();) {
        const bool digit = std::isdigit(static_cast<unsigned char>(name[i])) != 0;
        std::size_t j = i;
        while (j < name.size() && (std::isdigit(static_cast<unsigned char>(name[j])) != 0) == digit) {
            ++j;
        }
        if (digit) {
            out.digits.push_back(out.parts.size());
        }
        out.parts.push_back(name.substr(i, j - i));
        i = j;
    }
    return out;
}

}  // namespace

std::vector<SeriesGroup> group_series_files(const std::vector<std::string>& names) {
    std::vector<SeriesGroup> groups;
    const auto each_alone = [&names] {
        std::vector<SeriesGroup> alone;
        for (const std::string& name : names) {
            alone.push_back({name, {name}});
        }
        return alone;
    };
    if (names.size() < 2) {
        return each_alone();
    }
    std::vector<Runs> cut;
    cut.reserve(names.size());
    for (const std::string& name : names) {
        cut.push_back(runs_of(name));
    }
    // The first digit run, counted from the left, whose text differs between the names.
    const std::size_t count = cut.front().digits.size();
    for (const Runs& runs : cut) {
        if (runs.digits.size() != count) {
            return each_alone();
        }
    }
    std::size_t varying = count;
    for (std::size_t k = 0; k < count && varying == count; ++k) {
        for (const Runs& runs : cut) {
            if (runs.parts[runs.digits[k]] != cut.front().parts[cut.front().digits[k]]) {
                varying = k;
                break;
            }
        }
    }
    if (varying == count) {
        return each_alone();
    }
    std::map<std::string, std::size_t> place;
    for (std::size_t n = 0; n < names.size(); ++n) {
        std::string pattern;
        for (std::size_t i = 0; i < cut[n].parts.size(); ++i) {
            pattern += i == cut[n].digits[varying] ? std::string("*") : cut[n].parts[i];
        }
        const auto [it, fresh] = place.try_emplace(pattern, groups.size());
        if (fresh) {
            groups.push_back({pattern, {}});
        }
        groups[it->second].files.push_back(names[n]);
    }
    return groups;
}

std::vector<std::string> declare_series_of_joint_fits(Project& project, const std::string& template_experiment,
                                                      const std::string& data_dir,
                                                      const std::vector<SeriesGroup>& groups,
                                                      const std::string& set_id) {
    if (groups.empty()) {
        throw std::invalid_argument("a series of joint fits needs at least one group of files");
    }
    BraggPdExperiment* source = nullptr;
    for (const auto& experiment : project.experiments) {
        if (datablock_key(experiment->name, "experiment") == datablock_key(template_experiment, "experiment")) {
            source = experiment.get();
        }
    }
    if (source == nullptr) {
        throw std::invalid_argument("no experiment '" + template_experiment + "' to make the series from");
    }
    const auto name_of = [](const std::string& pattern) {
        std::string name = pattern.substr(0, pattern.rfind('.'));
        name.erase(std::remove(name.begin(), name.end(), '*'), name.end());
        while (!name.empty() && (name.front() == '_' || name.front() == '-')) {
            name.erase(name.begin());
        }
        while (!name.empty() && (name.back() == '_' || name.back() == '-')) {
            name.pop_back();
        }
        return name;
    };
    std::vector<std::string> names{source->name};
    const BraggPdExperiment template_copy(*source);
    for (std::size_t g = 1; g < groups.size(); ++g) {
        BraggPdExperiment copy = experiment_copy(project, template_copy);
        const std::string wanted = name_of(groups[g].pattern);
        bool taken = wanted.empty();
        for (const auto& held : project.experiments) {
            taken = taken || datablock_key(held->name, "experiment") == wanted;
        }
        if (!taken) {
            copy.name = wanted;
        }
        names.push_back(copy.name);
        project.experiments.push_back(std::move(copy));
    }
    project.sequential_fit.data_dir = data_dir;
    project.sequential_fit.experiments.clear();
    for (std::size_t g = 0; g < groups.size(); ++g) {
        SequentialFitExperiment member;
        member.experiment_id = names[g];
        member.file_pattern = groups[g].pattern;
        project.sequential_fit.experiments.push_back(std::move(member));
    }
    ExperimentSet set;
    set.id = set_id;
    set.template_experiment_id = names.front();
    project.experiment_sets.push_back(std::move(set));
    for (const std::string& name : names) {
        ExperimentSetMember member;
        member.experiment_id = name;
        member.set_id = set_id;
        project.experiment_set_members.push_back(std::move(member));
    }
    return names;
}

}  // namespace edi
