#pragma once

#include <filesystem>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

#include "edi/io.hpp"

namespace c34_t28_baseline {
inline void capture_plain_dependants(Measurements& out, std::size_t shard = 0,
                                     std::size_t shards = 1) {
    using E = edi::ExperimentBase;
    const std::vector<std::pair<std::string, std::function<void(E&)>>> writes = {
        {"cutoff-equal", [](E& e) { e.peak.cutoff_fwhm = e.peak.cutoff_fwhm; }},
        {"cutoff-changed", [](E& e) { e.peak.cutoff_fwhm += 1.375; }},
        {"peak-selector-equal", [](E& e) { e.peak.type = e.peak.type; }},
        {"peak-selector-changed", [](E& e) { e.peak.type = "cwl-thompson-cox-hastings"; }},
        {"experiment-type-equal",
         [](E& e) { e.experiment_type.sample_form = e.experiment_type.sample_form; }},
        {"experiment-type-changed",
         [](E& e) { e.experiment_type.sample_form = edi::SampleFormEnum::SINGLE_CRYSTAL; }},
        {"linked-key-equal",
         [](E& e) { e.linked_structure.structure_id = e.linked_structure.structure_id; }},
        {"linked-key-changed",
         [](E& e) { e.linked_structure.structure_id = "another-structure"; }},
        {"scattering-selector-equal",
         [](E& e) { e.neutron_scattering_length = e.neutron_scattering_length; }},
        {"scattering-selector-changed", [](E& e) { e.neutron_scattering_length = "sears1992"; }},
        {"absorption-selector-equal", [](E& e) { e.absorption.type = e.absorption.type; }},
        {"absorption-selector-changed", [](E& e) { e.absorption.type = "none"; }},
    };
    for (std::size_t index = shard; index < writes.size(); index += shards) {
        const auto& [name, write] = writes[index];
        const auto input = std::filesystem::path(__FILE__).parent_path() / "freshness-input";
        auto project = edi::load_project(input.string());
        project.calculate();
        project.structure().current_geometry();
        auto read = [&] {
            return Ticks{project.experiment().computed_current(),
                         project.structure().geometry_current(),
                         project.experiment().epoch.value()};
        };
        const auto before = read();
        if (!before[0] || !before[1]) {
            throw std::runtime_error(" R5 the pre-write dependent control must be current");
        }
        write(project.experiment());
        difference(out, "plain-dependants/" + name, before, read());
    }
}
}  // namespace c34_t28_baseline
