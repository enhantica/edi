// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_EDIT_HPP
#define EDI_EDIT_HPP

// ADR-0020 §8: an edit, as the app's one write door takes it (LivePreview::apply).
//
// An Edit is one model operation that is all-or-nothing: it throws its refusal having written
// nothing, or it completes. The door therefore has nothing to undo, and it promises no undo: it takes
// an Edit and nothing else. An undo is itself an Edit, built from a record taken before the change:
// undo_fit from a fit's start state, restore_relations from an edit of the relations (RelationsUndo).
// An Edit is made only by the operations below — it cannot be made from a callable — so a change that
// writes and then throws cannot be passed to the door. The set is closed
// and lives here; an operation the app needs is added here, with the rule that makes it whole:
//   - one assignment (`assign`): it cannot fail;
//   - a validated setter (the named ones, the ids' among them): it checks first, with the library's
//     rule and message;
//   - one collection mutator (`append`, `erase`): a mutator that throws leaves the collection as it
//     was (ADR-0016 §2);
//   - several objects at once (`add_experiments`, `erase_experiments`): everything is checked, then one
//     mutation.
// No operation is a template: each names the model's own field, row and value types, so the only
// code an Edit runs is edi's and the standard library's. A value a caller converts is converted at
// the call, before the Edit exists, and a row is copied by its model type's own copy. An id is
// written only while its item is held by the model's own collection of that item type, whose rename
// rule is edi's (KeyTraits), never one a caller's keyed type would supply.
// Outside the claim: an allocation failing inside an operation's write.

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "edi/edits.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/selectors.hpp"
#include "edi/symmetry.hpp"
#include "edi/categories.hpp"

namespace edi {

// edi ADR-0024: an edit of the declared relations, as undo restores it. The alias and constraint rows
// before the edit, and the state then of every parameter the edit changed (a dependent's implied value,
// a free flag a new relation cleared, an uncertainty), each by its unique name. Taken with
// capture_relations before the edit and narrowed with keep_changed after it, as undo_fit's capture is
// taken at a fit's start.
struct RelationsUndo {
    struct ParameterState {
        std::string unique_name;
        double value = 0.0;
        std::optional<double> uncertainty;
        bool free = false;
    };
    std::vector<ParameterAlias> aliases;
    std::vector<ParameterConstraint> constraints;
    std::vector<ParameterState> parameters;
};

inline RelationsUndo capture_relations(Project& project) {
    RelationsUndo before;
    for (const auto& alias : project.aliases) {
        before.aliases.push_back(*alias);
    }
    for (const auto& constraint : project.constraints) {
        before.constraints.push_back(*constraint);
    }
    for (const NamedSlot& slot : named_slots(project)) {
        before.parameters.push_back({slot.unique_name, slot.parameter->value.get(),
                                     slot.parameter->uncertainty.get(), slot.parameter->free.get()});
    }
    return before;
}

// After the edit: keeps only the parameters whose state it changed.
inline void keep_changed(RelationsUndo& before, Project& project) {
    std::map<std::string, const Parameter*> now;
    for (const NamedSlot& slot : named_slots(project)) {
        now.emplace(slot.unique_name, slot.parameter);
    }
    std::erase_if(before.parameters, [&now](const RelationsUndo::ParameterState& state) {
        const auto found = now.find(state.unique_name);
        return found != now.end() && found->second->value.get() == state.value &&
               found->second->uncertainty.get() == state.uncertainty &&
               found->second->free.get() == state.free;
    });
}

class Edit {
   public:
    // Runs the operation: its refusal, with nothing written, or the whole write.
    void operator()() const { operation_(); }

    // --- One assignment ---------------------------------------------------------------------------
    // `field = value`, for the model's plain fields: a flag, recorded or plain, a number, a text, an
    // optional integer and a text that records its writes. None can refuse. A recorded number has no
    // `assign`: a parameter's value is written by `value`, under its range, and a background point's
    // position by `background_position`.
    static Edit assign(bool& field, bool value) {
        return Edit([&field, value] { field = value; });
    }
    static Edit assign(detail::Written<bool>& field, bool value) {
        return Edit([&field, value] { field = value; });
    }
    static Edit assign(double& field, double value) {
        return Edit([&field, value] { field = value; });
    }
    static Edit assign(std::string& field, std::string value) {
        return Edit([&field, value = std::move(value)] { field = value; });
    }
    static Edit assign(std::optional<int>& field, std::optional<int> value) {
        return Edit([&field, value] { field = value; });
    }
    static Edit assign(detail::WrittenText& field, std::string value) {
        return Edit([&field, value = std::move(value)] { field = value; });
    }
    // A parameter's value, under its admissible range (assign_value).
    static Edit value(Parameter& parameter, double value) {
        return Edit([&parameter, value] { assign_value(parameter, value); });
    }
    // A background point's fixed position: one recorded assignment, which cannot fail.
    static Edit background_position(LineSegment& point, double position) {
        return Edit([&point, position] { point.position = position; });
    }

    // --- Validated settings -----------------------------------------------------------------------
    static Edit project_name(Project& project, std::string name) {
        return Edit([&project, name = std::move(name)] { project.metadata.name = validated_project_name(name); });
    }
    // Both construction times at once (the demo's pinned timestamps): two assignments that cannot fail.
    static Edit timestamps(Project& project, std::string time) {
        return Edit([&project, time = std::move(time)] {
            project.metadata.created = time;
            project.metadata.last_modified = time;
        });
    }
    // A project that declares a scan fits its one template experiment against each file: joint is refused there.
    static Edit fitting_mode(Project& project, std::string mode) {
        return Edit([&project, mode = std::move(mode)] {
            if (mode == "joint" && project.sequential_fit.declared()) {
                throw std::invalid_argument(
                    "joint fitting is not available in a project that declares a scan (_sequential_fit): its datasets "
                    "are fitted one at a time against the template experiment");
            }
            set_fitting_mode(project, mode);
        });
    }
    static Edit descent(Project& project, std::string id) {
        return Edit([&project, id = std::move(id)] { set_descent(project, id); });
    }
    static Edit max_iterations(Project& project, int bound) {
        return Edit([&project, bound] { set_minimizer_max_iterations(project, bound); });
    }
    static Edit chi_square_tolerance(Project& project, double tolerance) {
        return Edit([&project, tolerance] { set_minimizer_chi_square_tolerance(project, tolerance); });
    }
    static Edit peak_profile(ExperimentBase& experiment, std::string token) {
        return Edit([&experiment, token = std::move(token)] { select_peak_profile(experiment, token); });
    }
    static Edit absorption(ExperimentBase& experiment, std::string token) {
        return Edit([&experiment, token = std::move(token)] { select_absorption(experiment, token); });
    }
    static Edit scattering_source(ExperimentBase& experiment, ScatteringSourceItem item, std::string token) {
        return Edit(
            [&experiment, item, token = std::move(token)] { select_scattering_source(experiment, item, token); });
    }
    // A site's ADP type, its values converted (change_adp_type): crysta computes the new values on a
    // copy, so a refusal writes nothing.
    static Edit adp_type(Structure& structure, AtomSite& site, std::string type) {
        return Edit([&structure, &site, type = std::move(type)] { change_adp_type(structure, site, type); });
    }
    static Edit texture_axis_component(PrefOrient& row, detail::Written<int> PrefOrient::*component, int value) {
        return Edit([&row, component, value] { set_texture_axis_component(row, component, value); });
    }

    // --- Renames ----------------------------------------------------------------------------------
    // An id (ItemKey) is refused by its collection before it is written.
    static Edit rename_experiment(Project& project, ExperimentBase& experiment, std::string name) {
        return Edit([&project, &experiment, name = std::move(name)] {
            require_model_owner<BraggPdExperiment>(experiment.name, "the experiment");
            edi::rename_experiment(project, experiment, name);
        });
    }
    static Edit rename_atom_site(Structure& structure, AtomSite& site, std::string id) {
        return Edit([&structure, &site, id = std::move(id)] {
            require_model_owner<AtomSite>(site.id, "the atom site");
            edi::rename_atom_site(structure, site, id);
        });
    }
    static Edit structure_name(Structure& structure, std::string name) {
        return Edit([&structure, name = std::move(name)] {
            require_model_owner<Structure>(structure.name, "the structure");
            structure.name = name;
        });
    }
    // The structure a texture row corrects, which keys the row in its experiment's collection.
    static Edit texture_structure(PrefOrient& row, std::string id) {
        return Edit([&row, id = std::move(id)] {
            require_model_owner<PrefOrient>(row.structure_id, "the texture row");
            row.structure_id = id;
        });
    }
    // The structure a linked-structure row names, which keys the row in its experiment's collection.
    static Edit link_structure(LinkedStructure& row, std::string id) {
        return Edit([&row, id = std::move(id)] {
            require_model_owner<LinkedStructure>(row.structure_id, "the linked structure");
            row.structure_id = id;
        });
    }
    // An alias's or a constraint's id, which keys it in the project's collection.
    static Edit rename_alias(ParameterAlias& alias, std::string id) {
        return Edit([&alias, id = std::move(id)] {
            require_model_owner<ParameterAlias>(alias.id, "the alias");
            alias.id = id;
        });
    }
    static Edit rename_constraint(ParameterConstraint& constraint, std::string id) {
        return Edit([&constraint, id = std::move(id)] {
            require_model_owner<ParameterConstraint>(constraint.id, "the constraint");
            constraint.id = id;
        });
    }
    static Edit rename_scattering_length(Structure& structure, std::string from, std::string to) {
        return Edit([&structure, from = std::move(from), to = std::move(to)] {
            edi::rename_scattering_length(structure, from, to);
        });
    }

    // --- Rows -------------------------------------------------------------------------------------
    // One row added to, or removed from, one of the model's collections, by its own row type: atom
    // sites, background points, texture rows, linked structures, aliases and constraints are added;
    // those, structures and experiments are removed. `erase` refuses a row that is not there.
    static Edit append(ItemVec<AtomSite>& rows, AtomSite row) { return appending(rows, std::move(row)); }
    static Edit append(ItemVec<LineSegment>& rows, LineSegment row) { return appending(rows, std::move(row)); }
    static Edit append(ItemVec<PrefOrient>& rows, PrefOrient row) { return appending(rows, std::move(row)); }
    static Edit append(ItemVec<LinkedStructure>& rows, LinkedStructure row) {
        return appending(rows, std::move(row));
    }
    static Edit append(ItemVec<ParameterAlias>& rows, ParameterAlias row) { return appending(rows, std::move(row)); }
    static Edit append(ItemVec<ParameterConstraint>& rows, ParameterConstraint row) {
        return appending(rows, std::move(row));
    }
    // A site of a structure goes with its tensor row (erase_atom_site); any other row alone.
    static Edit erase(ItemVec<AtomSite>& rows, std::size_t index) {
        if (Structure* structure = rows.holder()) {
            return erase_atom_site(*structure, index);
        }
        return erasing(rows, index);
    }
    // A copy of a site under a new id, with a copy of its tensor row when it has one.
    static Edit duplicate_atom_site(Structure& structure, const AtomSite& source, std::string id) {
        return Edit([&structure, &source, id = std::move(id)] {
            for (const auto& existing : structure.atom_sites) {
                if (existing->id.value() == id) {
                    throw std::invalid_argument("an atom site labelled '" + detail::printable_id(id) +
                                                "' is already in the structure");
                }
            }
            AtomSite site = source;
            site.id = id;
            std::optional<AtomSiteAniso> tensor;
            for (const auto& row : structure.atom_site_aniso) {
                if (row->id.value() == source.id.value()) {
                    tensor = *row;
                    tensor->id = id;
                }
            }
            structure.atom_sites.push_back(std::move(site));
            if (tensor) {
                structure.atom_site_aniso.push_back(std::move(*tensor));
            }
        });
    }
    // An atom site and, when it is anisotropic, its tensor row: the row would otherwise name no site.
    static Edit erase_atom_site(Structure& structure, std::size_t index) {
        return Edit([&structure, index] {
            if (index >= structure.atom_sites.size()) {
                throw std::out_of_range("no atom site at row " + std::to_string(index));
            }
            const std::string id = structure.atom_sites[index]->id.value();
            std::optional<std::size_t> tensor;
            for (std::size_t row = 0; row < structure.atom_site_aniso.size(); ++row) {
                if (structure.atom_site_aniso[row]->id.value() == id) {
                    tensor = row;
                }
            }
            structure.atom_sites.erase_at(index);
            if (tensor) {
                structure.atom_site_aniso.erase_at(*tensor);
            }
        });
    }
    static Edit erase(ItemVec<LineSegment>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<PrefOrient>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<LinkedStructure>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<ParameterAlias>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<ParameterConstraint>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<Structure>& rows, std::size_t index) { return erasing(rows, index); }
    // A row-level removal cannot see the project's scan declaration: the app removes experiments through
    // erase_experiment, which keeps a scan's one template experiment.
    static Edit erase(ItemVec<BraggPdExperiment>& rows, std::size_t index) { return erasing(rows, index); }
    // An excluded region: its row added at the end, removed, or one of its two bounds assigned. The
    // regions are one recorded field (ADR-0018), written through its `modify`, which records a write
    // even when its callback throws: a missing row is therefore refused before it.
    using Regions = std::vector<std::pair<double, double>>;
    static Edit append_excluded_region(ExperimentBase& experiment, double start, double end) {
        return Edit([&experiment, start, end] {
            experiment.excluded_regions.modify([start, end](Regions& regions) { regions.emplace_back(start, end); });
        });
    }
    static Edit erase_excluded_region(ExperimentBase& experiment, std::size_t row) {
        return Edit([&experiment, row] {
            require_region(experiment, row);
            experiment.excluded_regions.modify(
                [row](Regions& regions) { regions.erase(regions.begin() + static_cast<std::ptrdiff_t>(row)); });
        });
    }
    static Edit excluded_region_bound(ExperimentBase& experiment, std::size_t row, bool end, double value) {
        return Edit([&experiment, row, end, value] {
            require_region(experiment, row);
            experiment.excluded_regions.modify([row, end, value](Regions& regions) {
                auto& region = regions[row];
                (end ? region.second : region.first) = value;
            });
        });
    }
    // A space-group setting chosen whole (assign_space_group_setting): name, code and IT number never contradict
    // one another (the owner, 2026-10-06). Assignments, which cannot fail.
    static Edit space_group_setting(SpaceGroup& group, SpaceGroupSettingName setting, bool declare_number) {
        return Edit([&group, setting = std::move(setting), declare_number] {
            assign_space_group_setting(group, setting, declare_number);
        });
    }
    // A structure's declared scattering length: set (declaring it when it is new) or removed. The map is
    // one recorded field, written through its `modify`; neither callback can refuse.
    using Lengths = std::map<std::string, double>;
    static Edit scattering_length(Structure& structure, std::string symbol, double length) {
        return Edit([&structure, symbol = std::move(symbol), length] {
            structure.scattering_lengths_fm.modify([&symbol, length](Lengths& lengths) { lengths[symbol] = length; });
        });
    }
    static Edit erase_scattering_length(Structure& structure, std::string symbol) {
        return Edit([&structure, symbol = std::move(symbol)] {
            structure.scattering_lengths_fm.modify([&symbol](Lengths& lengths) { lengths.erase(symbol); });
        });
    }

    // --- Loaded blocks ----------------------------------------------------------------------------
    // A loaded structure added (add_loaded_structure's rule: its name is not taken).
    static Edit add_structure(Project& project, Structure structure) {
        return Edit([&project, structure = std::make_shared<Structure>(std::move(structure))] {
            add_loaded_structure(project, *structure);
        });
    }
    // Loaded experiments added, all or none: every name is checked against the project and against
    // the others (add_loaded_experiment's rule and message), then the collection takes them in one
    // mutation.
    static Edit add_experiments(Project& project, std::vector<BraggPdExperiment> experiments) {
        auto batch = std::make_shared<std::vector<BraggPdExperiment>>(std::move(experiments));
        return Edit([&project, batch] {
            require_scan_template(project, project.experiments.size() + batch->size());
            std::vector<ItemVec<BraggPdExperiment>::Ptr> all(project.experiments.begin(), project.experiments.end());
            for (const BraggPdExperiment& experiment : *batch) {
                const std::string key = KeyTraits<BraggPdExperiment>::canonical(experiment.name);
                for (const auto& held : all) {
                    if (KeyTraits<BraggPdExperiment>::canonical(held->name) == key) {
                        throw IoError("an experiment named '" + detail::printable_id(experiment.name) +
                                      "' is already in the project");
                    }
                }
                all.push_back(std::make_shared<BraggPdExperiment>(experiment));
            }
            project.experiments.assign(std::move(all));
        });
    }

    // A new experiment without measured data (simulation_experiment) added at the end: its name is checked
    // against the project's, and a project whose experiments carry measured data refuses it (load_project's
    // rule: a project calculates or fits as a whole).
    static Edit create_experiment(Project& project, BraggPdExperiment experiment) {
        auto created = std::make_shared<BraggPdExperiment>(std::move(experiment));
        return Edit([&project, created] {
            require_calculation_project(project);
            require_scan_template(project, project.experiments.size() + 1);
            const std::string key = KeyTraits<BraggPdExperiment>::canonical(created->name);
            for (const auto& held : project.experiments) {
                if (KeyTraits<BraggPdExperiment>::canonical(held->name) == key) {
                    throw IoError("an experiment named '" + detail::printable_id(created->name) +
                                  "' is already in the project");
                }
            }
            project.experiments.push_back(std::make_shared<BraggPdExperiment>(*created));
        });
    }
    // An experiment without measured data replaced in its place by `replacement` (a new type of it, from
    // simulation_experiment): refused once the experiment holds measured data, whose type the data fixes.
    static Edit replace_experiment(Project& project, const ExperimentBase& experiment, BraggPdExperiment replacement) {
        auto next = std::make_shared<BraggPdExperiment>(std::move(replacement));
        return Edit([&project, &experiment, next] {
            if (!experiment.calculation_only) {
                throw std::invalid_argument("the experiment '" + experiment.name +
                                            "' holds measured data, which fixes its type");
            }
            std::vector<ItemVec<BraggPdExperiment>::Ptr> all(project.experiments.begin(), project.experiments.end());
            const auto found = std::find_if(all.begin(), all.end(), [&experiment](const auto& held) {
                return held.get() == &experiment;
            });
            if (found == all.end()) {
                throw std::invalid_argument("the experiment is not in the project");
            }
            *found = std::make_shared<BraggPdExperiment>(*next);
            project.experiments.assign(std::move(all));
        });
    }
    // The calculation grid of an experiment without measured data: `start` to `end` by `step`, as the
    // loader generates a `_data_range` grid, and under the same rule (step > 0, end > start). Refused for an
    // experiment with measured data, whose points are its data's, and above `kMaximumGridPoints`.
    static constexpr std::size_t kMaximumGridPoints = 1000000;
    static Edit data_range(ExperimentBase& experiment, double start, double end, double step) {
        return Edit([&experiment, start, end, step] {
            if (!experiment.calculation_only) {
                throw std::invalid_argument("the experiment '" + experiment.name +
                                            "' holds measured data, whose points set its range");
            }
            // A range a save can declare again: finite, at least two points.
            if (!std::isfinite(start) || !std::isfinite(end) || !std::isfinite(step) || !(step > 0.0) ||
                !(end > start)) {
                throw std::invalid_argument("a calculation range needs finite values, step > 0 and end > start");
            }
            if (step > end - start) {
                throw std::invalid_argument("a calculation range needs a step no larger than its span, so it holds "
                                            "at least two points");
            }
            const double intervals = std::floor((end - start) / step);
            if (!(intervals < static_cast<double>(kMaximumGridPoints))) {
                throw std::invalid_argument("a calculation range holds at most " +
                                            std::to_string(kMaximumGridPoints) + " points");
            }
            std::vector<double> axis(static_cast<std::size_t>(intervals) + 1);
            for (std::size_t index = 0; index < axis.size(); ++index) {
                axis[index] = start + static_cast<double>(index) * step;
                // Every point distinct, as the saved declaration regenerates them: a step too small for
                // the range's values leaves two points equal.
                if (index > 0 && !(axis[index] > axis[index - 1])) {
                    throw std::invalid_argument("a calculation range needs a step large enough for its values: "
                                                "two of its points would coincide");
                }
            }
            PdDataBase generated;
            (experiment.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH ? generated.two_theta
                                                                                  : generated.time_of_flight) =
                std::move(axis);
            experiment.data = std::move(generated);
        });
    }
    // One experiment removed; a scan project keeps its template experiment.
    static Edit erase_experiment(Project& project, std::size_t index) {
        return Edit([&project, index] {
            if (index >= project.experiments.size()) {
                throw std::out_of_range("the project has no experiment " + std::to_string(index));
            }
            require_scan_template(project, project.experiments.size() - 1);
            project.experiments.erase_at(index);
        });
    }
    // Experiments removed, all or none (an undo of their addition): each is found by identity first, so one
    // removed since refuses with nothing written.
    static Edit erase_experiments(Project& project, std::vector<const ExperimentBase*> experiments) {
        return Edit([&project, experiments = std::move(experiments)] {
            std::vector<ItemVec<BraggPdExperiment>::Ptr> kept(project.experiments.begin(), project.experiments.end());
            for (const ExperimentBase* gone : experiments) {
                const auto found = std::find_if(kept.begin(), kept.end(),
                                                [gone](const auto& held) { return held.get() == gone; });
                if (found == kept.end()) {
                    throw std::invalid_argument("undo: an added experiment is no longer in the project");
                }
                kept.erase(found);
            }
            require_scan_template(project, kept.size());
            project.experiments.assign(std::move(kept));
        });
    }

    // A scan dataset shown in the model (the app's dataset view): the experiment's measured data replaced by the
    // dataset's, and each named parameter given its value and uncertainty (a fitted dataset's results row, or the
    // template's). Every name is resolved first; one the model does not have is left out, as a results column of
    // a parameter the template no longer has. The writes are assignments, which cannot fail.
    struct ScanValue {
        std::string unique_name;
        double value = 0.0;
        std::optional<double> uncertainty;
    };
    static Edit scan_view(Project& project, ExperimentBase& experiment, std::vector<ScanValue> values, PdDataBase data) {
        auto shown = std::make_shared<PdDataBase>(std::move(data));
        return Edit([&project, &experiment, values = std::move(values), shown] {
            std::map<std::string, Parameter*> by_name;
            for (const NamedSlot& slot : named_slots(project)) {
                by_name.emplace(slot.unique_name, slot.parameter);
            }
            std::vector<std::pair<Parameter*, const ScanValue*>> targets;
            for (const ScanValue& value : values) {
                if (const auto found = by_name.find(value.unique_name); found != by_name.end()) {
                    targets.emplace_back(found->second, &value);
                }
            }
            experiment.data = *shown;
            experiment.calculation_only = false;
            for (const auto& [parameter, value] : targets) {
                parameter->value = value->value;
                parameter->uncertainty = value->uncertainty;
            }
        });
    }

    // An edit of the relations undone (edi ADR-0024): the alias and constraint rows as they were, and each
    // parameter the edit changed back to its state then. Every parameter is resolved first, so one whose
    // row was removed since refuses with nothing written; the rows were admitted before, so the
    // assignments cannot refuse. The door's completion then re-derives every mark and implied value.
    static Edit restore_relations(Project& project, RelationsUndo before) {
        return Edit([&project, before = std::move(before)] {
            std::map<std::string, Parameter*> by_name;
            for (const NamedSlot& slot : named_slots(project)) {
                by_name.emplace(slot.unique_name, slot.parameter);
            }
            std::vector<std::pair<Parameter*, const RelationsUndo::ParameterState*>> targets;
            for (const RelationsUndo::ParameterState& state : before.parameters) {
                const auto found = by_name.find(state.unique_name);
                if (found == by_name.end()) {
                    throw std::invalid_argument("undo: the parameter '" + state.unique_name +
                                                "' is no longer in the project");
                }
                targets.emplace_back(found->second, &state);
            }
            std::vector<std::shared_ptr<ParameterAlias>> aliases;
            for (const ParameterAlias& row : before.aliases) {
                aliases.push_back(std::make_shared<ParameterAlias>(row));
            }
            std::vector<std::shared_ptr<ParameterConstraint>> constraints;
            for (const ParameterConstraint& row : before.constraints) {
                constraints.push_back(std::make_shared<ParameterConstraint>(row));
            }
            project.aliases.assign(std::move(aliases));
            project.constraints.assign(std::move(constraints));
            for (const auto& [parameter, state] : targets) {
                parameter->value = state->value;
                parameter->uncertainty = state->uncertainty;
                parameter->free = state->free;
            }
        });
    }

    // The last fit undone — undo_fit's restore, without its calculation (the door's own calculation
    // follows). It is worked out on a copy, which may refuse with nothing written, and the restored
    // parameters are then written: assignments, which cannot fail.
    static Edit undo_fit(Project& project) {
        return Edit([&project] {
            Project restored = project;
            restore_fit_start(restored);
            if (!copy_parameter_states(project, restored)) {
                throw std::logic_error("undo: the restored copy does not match the project");
            }
            copy_fit_result(project, restored);  // assignments too: cleared when the undo restored anything
        });
    }

   private:
    explicit Edit(std::function<void()> operation) : operation_(std::move(operation)) {}

    // The row factories' one body each, for the model row types above only: nothing outside this
    // class names them.
    template <typename Row>
    static Edit appending(ItemVec<Row>& rows, Row row) {
        return Edit([&rows, row = std::make_shared<Row>(std::move(row))] { rows.push_back(std::make_shared<Row>(*row)); });
    }
    template <typename Row>
    static Edit erasing(ItemVec<Row>& rows, std::size_t index) {
        return Edit([&rows, index] { rows.erase_at(index); });
    }
    // A project that declares a scan fits its one template experiment against each file (edi ADR-0017 §19): an
    // edit that would leave it another number of experiments is refused.
    static void require_scan_template(const Project& project, std::size_t experiments) {
        if (project.sequential_fit.declared() && experiments != 1) {
            throw std::invalid_argument(
                "this project declares a scan (_sequential_fit), which fits one template experiment against each "
                "file: an edit leaving it " + std::to_string(experiments) + " experiments is refused");
        }
    }
    // Refuses an id whose item a collection other than the model's own ItemVec<Item> holds: a
    // caller's keyed type derived from a model type would bring its own rename rule (KeyTraits),
    // which could write and then throw. A detached id has no rule to run.
    static void require_calculation_project(const Project& project) {
        for (const auto& held : project.experiments) {
            if (!held->calculation_only) {
                throw IoError("the project's experiments carry measured data - a project calculates or fits "
                              "as a whole, so an experiment without data cannot join it");
            }
        }
    }
    static void require_region(const ExperimentBase& experiment, std::size_t row) {
        if (row >= experiment.excluded_regions.size()) {
            throw std::out_of_range("the experiment has no excluded region " + std::to_string(row));
        }
    }
    template <typename Item>
    static void require_model_owner(const ItemKey& id, const char* what) {
        if (id.owner() != nullptr && dynamic_cast<const ItemVec<Item>*>(id.owner()) == nullptr) {
            throw std::invalid_argument(std::string(what) + " is not held by the model's own collection");
        }
    }

    std::function<void()> operation_;
};

}  // namespace edi

#endif  // EDI_EDIT_HPP
