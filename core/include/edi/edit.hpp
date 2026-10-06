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
//   - several objects at once (`add_experiments`): everything is checked, then one mutation.
// No operation is a template: each names the model's own field, row and value types, so the only
// code an Edit runs is edi's and the standard library's. A value a caller converts is converted at
// the call, before the Edit exists, and a row is copied by its model type's own copy. An id is
// written only while its item is held by the model's own collection of that item type, whose rename
// rule is edi's (KeyTraits), never one a caller's keyed type would supply.
// Outside the claim: an allocation failing inside an operation's write.

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
    static Edit fitting_mode(Project& project, std::string mode) {
        return Edit([&project, mode = std::move(mode)] { set_fitting_mode(project, mode); });
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
    static Edit erase(ItemVec<AtomSite>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<LineSegment>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<PrefOrient>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<LinkedStructure>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<ParameterAlias>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<ParameterConstraint>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<Structure>& rows, std::size_t index) { return erasing(rows, index); }
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
    // A space-group setting chosen whole: the name, its coordinate-system code and the IT number, which is
    // stored when `declare_number` or when the structure already stores one, so the three never contradict one
    // another (the owner, 2026-10-06). Assignments, which cannot fail.
    static Edit space_group_setting(SpaceGroup& group, std::string name, std::string code, int it_number,
                                    bool declare_number) {
        return Edit([&group, name = std::move(name), code = std::move(code), it_number, declare_number] {
            group.name_h_m = name;
            group.coord_system_code = code;
            if (declare_number || group.it_number.has_value()) {
                group.it_number = it_number;
            }
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
    // Refuses an id whose item a collection other than the model's own ItemVec<Item> holds: a
    // caller's keyed type derived from a model type would bring its own rename rule (KeyTraits),
    // which could write and then throw. A detached id has no rule to run.
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
