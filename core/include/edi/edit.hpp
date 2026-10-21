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
#include <iterator>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <type_traits>
#include <tuple>
#include <vector>

#include "edi/edits.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/selectors.hpp"
#include "edi/symmetry.hpp"
#include "edi/categories.hpp"

namespace edi {

namespace detail {
struct ScanViewValue {
    std::string unique_name;
    double value = 0.0;
    std::optional<double> uncertainty;
};
// The existing scan-view operation split at its real write boundary. Scan Undo
// prepares it before reversing files; ordinary Edit still resolves at execution.
struct PreparedScanView {
    struct Target { Parameter* parameter; double value; std::optional<double> uncertainty; };
    ExperimentBase* experiment;
    std::optional<PdDataBase> data;
    std::vector<Target> targets;
    void commit() noexcept {
        static_assert(std::is_nothrow_move_assignable_v<std::optional<PdDataBase>>);
        experiment->data = std::move(data);
        experiment->calculation_only = false;
        for (const auto& target : targets) {
            target.parameter->value = target.value;
            target.parameter->uncertainty = target.uncertainty;
        }
    }
};
inline PreparedScanView prepare_scan_view(Project& project, ExperimentBase& experiment,
                                         const std::vector<ScanViewValue>& values, PdDataBase data) {
    PreparedScanView prepared{&experiment, std::move(data), {}};
    std::map<std::string, Parameter*> by_name;
    for (const NamedSlot& slot : named_slots(project)) by_name.emplace(slot.unique_name, slot.parameter);
    prepared.targets.reserve(values.size());
    for (const auto& value : values) {
        if (const auto found = by_name.find(value.unique_name); found != by_name.end())
            prepared.targets.push_back({found->second, value.value, value.uncertainty});
    }
    return prepared;
}
} // namespace detail

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

// The structures as they were before Create or Remove structure, with every experiment's links and texture rows,
// which undo puts back (restore_structures). Taken with capture_structures.
struct StructuresUndo {
    struct ExperimentRows {
        const ExperimentBase* experiment = nullptr;
        std::vector<LinkedStructure> links;
        std::vector<PrefOrient> texture;
    };
    std::vector<Structure> structures;
    std::vector<ExperimentRows> experiments;
    // Present only for ordinary structure metadata/site edits. Their linked
    // aliases/results and still-live experiment dependents must follow Undo too.
    std::optional<RelationsUndo> related;
    std::optional<FitResultRecord> fit_result;
};

inline StructuresUndo capture_structures(const Project& project) {
    StructuresUndo before;
    for (const auto& structure : project.structures) {
        before.structures.push_back(*structure);
    }
    for (const auto& experiment : project.experiments) {
        StructuresUndo::ExperimentRows rows{experiment.get(), {}, {}};
        for (const auto& link : experiment->linked_structures) {
            rows.links.push_back(*link);
        }
        for (const auto& row : experiment->preferred_orientation) {
            rows.texture.push_back(*row);
        }
        before.experiments.push_back(std::move(rows));
    }
    return before;
}

// Same structures Undo, with the coupled scientific footprint of symmetry/site
// edits. Structures, links and texture already own their complete parameter
// images; retain only the other experiment values in the original relations
// state, so restore never writes through pointers it is about to replace.
inline StructuresUndo capture_structure_edit(Project& project) {
    auto before = capture_structures(project);
    before.related = capture_relations(project);
    before.fit_result = project.fit_result;
    std::set<const Parameter*> replaced;
    for (const auto& structure : project.structures)
        for (const auto* parameter : structure->parameters()) replaced.insert(parameter);
    for (const auto& experiment : project.experiments) {
        for (const auto& link : experiment->linked_structures) replaced.insert(&link->scale);
        for (const auto& row : experiment->preferred_orientation)
            for (const auto* parameter : row->parameters()) replaced.insert(parameter);
    }
    std::set<std::string> retained;
    for (const auto& slot : named_slots(project))
        if (!replaced.contains(slot.parameter)) retained.insert(slot.unique_name);
    std::erase_if(before.related->parameters, [&retained](const auto& state) { return !retained.contains(state.unique_name); });
    return before;
}

// Narrow original experiment-control history: no measured-data/model copy.
struct ExperimentControlsUndo {
    const ExperimentBase* experiment=nullptr;
    std::optional<PeakBase> peak;
    std::optional<std::vector<ExcludedRegion>> regions;
    std::optional<std::vector<LinkedStructure>> links;
    std::optional<AbsorptionBase> absorption;
    std::optional<double> cutoff_fwhm, dataset_weight;
    std::optional<RelationsUndo> related;
    std::optional<FitResultRecord> fit_result;
};
inline ExperimentControlsUndo capture_experiment_controls(Project& project,ExperimentBase& experiment,bool profile) {
    ExperimentControlsUndo before;before.experiment=&experiment;
    if(profile) {
        before.peak.emplace(experiment.peak);before.related=capture_relations(project);before.fit_result=project.fit_result;
        const auto replaced=experiment.peak.parameters();
        std::set<std::string> retained;
        for(const auto& slot:named_slots(project))
            if(std::find(replaced.begin(),replaced.end(),slot.parameter)==replaced.end())retained.insert(slot.unique_name);
        std::erase_if(before.related->parameters,[&](const auto& state){return !retained.contains(state.unique_name);});
    } else {
        before.regions.emplace();
        for(const auto& row:experiment.excluded_regions)before.regions->push_back(*row);
    }
    return before;
}

// The original link table's complete narrow history; replaced scales are restored
// in their owning row images, never through a handle the restore will retire.
inline ExperimentControlsUndo capture_experiment_links(Project& project,ExperimentBase& experiment) {
    ExperimentControlsUndo before;before.experiment=&experiment;before.links.emplace();
    for(const auto& row:experiment.linked_structures)before.links->push_back(*row);
    before.related=capture_relations(project);before.fit_result=project.fit_result;
    std::set<const Parameter*> replaced;
    for(const auto& row:experiment.linked_structures)replaced.insert(&row->scale);
    std::set<std::string> retained;
    for(const auto& slot:named_slots(project))if(!replaced.contains(slot.parameter))retained.insert(slot.unique_name);
    std::erase_if(before.related->parameters,[&](const auto& state){return !retained.contains(state.unique_name);});
    return before;
}

enum class ExperimentScalarControl { Absorption, CutoffFwhm, DatasetWeight };
inline ExperimentControlsUndo capture_experiment_scalar(Project& project,ExperimentBase& experiment,ExperimentScalarControl control) {
    ExperimentControlsUndo before;before.experiment=&experiment;before.fit_result=project.fit_result;
    if(control==ExperimentScalarControl::CutoffFwhm)before.cutoff_fwhm=experiment.peak.cutoff_fwhm;
    else if(control==ExperimentScalarControl::DatasetWeight)before.dataset_weight=experiment.dataset_weight;
    else {
        before.absorption.emplace(experiment.absorption);before.related=capture_relations(project);
        const auto replaced=experiment.absorption.parameters();std::set<std::string> retained;
        for(const auto& slot:named_slots(project))
            if(std::find(replaced.begin(),replaced.end(),slot.parameter)==replaced.end())retained.insert(slot.unique_name);
        std::erase_if(before.related->parameters,[&](const auto& state){return !retained.contains(state.unique_name);});
    }
    return before;
}

/// The project's report settings (ADR-0036 §7) as one value: what an edit of one of them changes, and what its Undo
/// puts back.
struct ReportSettingsState {
    std::optional<bool> html, pdf, cif, html_offline;
    std::optional<std::string> excluded;
    std::optional<double> correlation_threshold;
    std::optional<std::string> pattern_x_axis;
    bool operator==(const ReportSettingsState&) const = default;
};

inline ReportSettingsState report_settings_state(const Project& project) {
    return {project.report_html,    project.report_pdf,           project.report_cif,     project.report_html_offline,
            project.report_excluded, project.correlation_threshold, project.pattern_x_axis};
}

// Same-owner completion is deliberately not a general merge/replacement. These
// borrowed checks allocate no scientific copy and preserve all metadata/settings/path.
inline bool empty_population_fit(const FitResultRecord& fit) {
    const FitResultRecord pristine;
    static_assert(std::tuple_size_v<decltype(FitResultCategory::columns)> > 0);
    return std::apply([&](auto... field) { return ((fit.*field == pristine.*field) && ...); },
        FitResultCategory::columns) && fit.correlations.empty() && fit.scan_results.empty();
}
inline bool empty_for_population(const Project& project) {
    const auto& scan = project.sequential_fit;
    return project.structures.empty() && project.experiments.empty() && project.aliases.empty() &&
        project.constraints.empty() && project.report_files.empty() && project.scan_data_root.empty() &&
        (project.fitting_mode.empty() || project.fitting_mode == "single" || project.fitting_mode == "joint") &&
        scan.data_dir.empty() && scan.file_pattern == "*" && !scan.reverse && scan.template_file.empty() && scan.extract.empty() &&
        empty_population_fit(project.fit_result);
}

// Owned complete scientific addition prepared before either live collection is
// touched. No metadata, project assignment or observer runs in the dual commit.
class EmptyProjectPopulation {
 public:
    static std::shared_ptr<EmptyProjectPopulation> prepare(Project candidate) {
        if (candidate.structures.size() != 1 || candidate.experiments.size() != 1 ||
            !candidate.aliases.empty() || !candidate.constraints.empty())
            throw std::invalid_argument("empty-project completion requires one validated phase and measured bank");
        auto result = std::make_shared<EmptyProjectPopulation>();
        result->structures_ = std::move(candidate.structures);
        result->experiments_ = std::move(candidate.experiments);
        result->structure_ = result->structures_.front();
        result->experiment_ = result->experiments_.front();
        return result;
    }
    bool committed() const noexcept { return committed_; }
 private:
    friend class Edit;
    ItemVec<Structure> structures_;
    ItemVec<BraggPdExperiment> experiments_;
    std::shared_ptr<Structure> structure_;
    std::shared_ptr<BraggPdExperiment> experiment_;
    bool committed_ = false, undone_ = false;
};

/// An explicit operation on one line-segment anchor in native measured-axis units.
/// App callers admit IDs/rows before constructing this input; it never selects a bank.
struct BackgroundPointInput {
    enum class Action { Add, Update, Remove } action = Action::Add;
    std::string id;
    double position = 0, intensity = 0;
    bool free = false;
};
/// Exact shared rows before/after one background operation, retained for ordinary Undo.
/// Only the updated/new row is copied. Other rows and all project data retain identity.
struct BackgroundPointChange {
    ExperimentBase* experiment = nullptr;
    std::vector<ItemVec<LineSegment>::Ptr> before, after;
    const PdDataBase* data = nullptr;
    std::uint64_t stamp = 0, data_stamp = 0, alias_stamp = 0, constraint_stamp = 0;
    std::uint64_t theta_stamp = 0, tof_stamp = 0, intensity_stamp = 0, sigma_stamp = 0;
    BeamModeEnum mode = BeamModeEnum::CONSTANT_WAVELENGTH;
    double low = 0, high = 0;
    std::optional<LineSegment> original, replacement;
    static bool same_point(const LineSegment& a, const LineSegment& b) noexcept {
        const auto& x = a.intensity; const auto& y = b.intensity;
        return a.id.value() == b.id.value() && a.position.get() == b.position.get() && x.value.get() == y.value.get() &&
            x.uncertainty.get() == y.uncertainty.get() && x.free.get() == y.free.get() && x.spec == y.spec &&
            x.start_value.get() == y.start_value.get() && x.start_uncertainty.get() == y.start_uncertainty.get() && x.dependence == y.dependence;
    }
    bool native_request = false, calculation_only = false;
    bool same_source(const ExperimentBase& bank) const noexcept {
        if (bank.background_type != "line-segment" || bank.calculation_only != calculation_only ||
            bank.effective_beam_mode() != mode || bool(bank.data) != (data != nullptr)) return false;
        if (!bank.data) return !native_request;
        return (!native_request || !bank.calculation_only) && &*bank.data == data && bank.data->written.value() == data_stamp &&
            bank.data->two_theta.written() == theta_stamp && bank.data->time_of_flight.written() == tof_stamp &&
            bank.data->intensity_meas.written() == intensity_stamp && bank.data->intensity_meas_su.written() == sigma_stamp;
    }
    bool committed = false, undone = false;
};
/// Prepare a bounded, validated line-segment add/update/remove without live writes.
/// Native callers require a measured bank and finite, distinct in-domain anchors.
/// Ordinary manual callers retain simulation, extrapolation and stored-row ordering.
/// Removing an alias target refuses; changing dependent intensity/free flags refuses.
/// @param project Borrowed live owner; it must outlive execution and Undo.
/// @param experiment Borrowed bank owned by project; measured data is required for native callers.
/// @param input Caller-owned exact operation/ID and native-axis scientific values.
/// @param max_points Inclusive caller admission for the complete result collection.
/// @param max_text Inclusive caller byte admission for IDs and named relation targets.
/// @param max_samples Inclusive borrowed-axis traversal admission.
/// @param max_aliases Inclusive borrowed alias collection admission.
/// @param native_request Apply native measured/domain policy; false preserves ordinary manual semantics.
/// @return Owned preparation retaining the original shared rows; no live values change.
/// Call on the model's owner thread without concurrent model mutation.
/// @throws std::invalid_argument Invalid source, shape or scientific input.
/// @throws std::length_error A declared caller capacity was exceeded.
inline std::shared_ptr<BackgroundPointChange> prepare_background_point(
    Project& project, ExperimentBase& experiment, const BackgroundPointInput& input, std::size_t max_points, std::size_t max_text, std::size_t max_samples, std::size_t max_aliases, bool native_request) {
    if (input.action != BackgroundPointInput::Action::Add && input.action != BackgroundPointInput::Action::Update &&
        input.action != BackgroundPointInput::Action::Remove) throw std::invalid_argument("unknown background operation");
    const auto owned = std::find_if(project.experiments.begin(), project.experiments.end(),
        [&](const auto& e) { return e.get() == &experiment; });
    if (owned == project.experiments.end() || experiment.background_type != "line-segment")
        throw std::invalid_argument("background editing requires an owned line-segment experiment");
    if (native_request && (!experiment.data || experiment.calculation_only))
        throw std::invalid_argument("native background editing requires measured data");
    if (!max_points || experiment.background.size() > max_points ||
        (input.action == BackgroundPointInput::Action::Add && experiment.background.size() == max_points))
        throw std::length_error("background collection exceeds its admitted capacity");
    if (!max_text || input.id.size() > max_text || experiment.name.value().size() > max_text)
        throw std::length_error("background identity exceeds its admitted capacity");
    for (const auto& row : experiment.background) if (row->id.value().size() > max_text)
        throw std::length_error("background identity exceeds its admitted capacity");
    (void)KeyTraits<LineSegment>::canonical(input.id);
    if (project.aliases.size() > max_aliases)
        throw std::length_error("background relation collection exceeds its admitted capacity");
    for (const auto& alias : project.aliases) if (alias->parameter_unique_name.value().size() > max_text)
        throw std::length_error("background relation identity exceeds its admitted capacity");
    double low = 0, high = 0;
    if (native_request) {
        const auto& axis = experiment.data->axis();
        if (axis.size() > max_samples) throw std::length_error("background source exceeds its admitted capacity");
        if (bool(experiment.data->two_theta) != (experiment.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH))
            throw std::invalid_argument("the measured axis does not match this experiment's mode");
        if (axis.empty() || axis.size() != experiment.data->intensity_meas.size())
            throw std::invalid_argument("the measured background axis is unavailable");
        low = high = axis.front();
        for (const double x : axis) {
            if (!std::isfinite(x)) throw std::invalid_argument("the measured axis is nonfinite");
            low = std::min(low, x); high = std::max(high, x);
        }
    }
    const auto found = std::find_if(experiment.background.begin(), experiment.background.end(),
        [&](const auto& p) { return p->id.value() == input.id; });
    if ((input.action == BackgroundPointInput::Action::Add) != (found == experiment.background.end()))
        throw std::invalid_argument("the background ID is already present or no longer exists");
    if (input.action != BackgroundPointInput::Action::Remove &&
        (!std::isfinite(input.position) || !std::isfinite(input.intensity) ||
         (native_request && (input.position < low || input.position > high))))
        throw std::invalid_argument("the background point is nonfinite or outside its native measured domain");
    if (input.action == BackgroundPointInput::Action::Remove) {
        const auto name = detail::background_parameter_name(experiment, input.id);
        for (const auto& alias : project.aliases) if (alias->parameter_unique_name.value() == name)
            throw std::invalid_argument("a declared alias still names this background intensity");
    } else if (input.action == BackgroundPointInput::Action::Update && (*found)->intensity.dependence != Dependence::Independent &&
        ((*found)->intensity.value.get() != input.intensity || (*found)->intensity.free.get() != input.free))
        throw std::invalid_argument("a relation owns this background intensity or free flag");
    auto prepared = std::make_shared<BackgroundPointChange>();
    prepared->experiment = &experiment; prepared->stamp = experiment.background.category_stamp();
    prepared->native_request = native_request; prepared->calculation_only = experiment.calculation_only;
    if (experiment.data) {
        prepared->data = &*experiment.data; prepared->data_stamp = experiment.data->written.value();
        prepared->theta_stamp = experiment.data->two_theta.written(); prepared->tof_stamp = experiment.data->time_of_flight.written();
        prepared->intensity_stamp = experiment.data->intensity_meas.written(); prepared->sigma_stamp = experiment.data->intensity_meas_su.written();
    }
    prepared->mode = experiment.effective_beam_mode(); prepared->low = low; prepared->high = high;
    if (found != experiment.background.end()) prepared->original.emplace(**found);
    prepared->alias_stamp = project.aliases.category_stamp(); prepared->constraint_stamp = project.constraints.category_stamp();
    prepared->before.assign(experiment.background.begin(), experiment.background.end());
    prepared->after.reserve(prepared->before.size() + (input.action == BackgroundPointInput::Action::Add ? 1 : 0));
    for (const auto& point : prepared->before) if (point->id.value() != input.id) prepared->after.push_back(point);
    if (input.action != BackgroundPointInput::Action::Remove) {
        auto point = input.action == BackgroundPointInput::Action::Update ? std::make_shared<LineSegment>(**found) : std::make_shared<LineSegment>();
        point->id = input.id; point->position = input.position;
        if (input.action == BackgroundPointInput::Action::Add || point->intensity.value.get() != input.intensity)
            assign_value(point->intensity, input.intensity);
        point->intensity.free = input.free;
        prepared->replacement.emplace(*point);
        if (!native_request && input.action == BackgroundPointInput::Action::Update)
            prepared->after.insert(prepared->after.begin() + std::distance(experiment.background.begin(), found), std::move(point));
        else prepared->after.push_back(std::move(point));
    }
    for (const auto& point : prepared->after) if (!std::isfinite(point->position.get()) || !std::isfinite(point->intensity.value.get()))
        throw std::invalid_argument("background anchors must be finite");
    if (native_request) {
        std::sort(prepared->after.begin(), prepared->after.end(), [](const auto& a, const auto& b) { return a->position.get() < b->position.get(); });
        std::optional<double> previous;
        for (const auto& point : prepared->after) {
            const double x = point->position.get();
            if (x < low || x > high || (previous && x <= *previous))
                throw std::invalid_argument("background points need distinct finite ordered measured positions");
            previous = x;
        }
    }
    return prepared;
}

class Edit {
   public:
    /// Add one prepared scientific graph to the SAME empty project. Collection
    /// moves are nonthrowing and keep target host linkage. All other fields stay.
    static Edit populate_empty_project(Project& project, std::shared_ptr<EmptyProjectPopulation> prepared) {
        return Edit([&project, prepared = std::move(prepared)] {
            if (!prepared || prepared->committed_ || !empty_for_population(project) ||
                prepared->structures_.size() != 1 || prepared->experiments_.size() != 1)
                throw std::invalid_argument("the original current project is no longer empty");
            static_assert(std::is_nothrow_move_assignable_v<ItemVec<Structure>>);
            static_assert(std::is_nothrow_move_assignable_v<ItemVec<BraggPdExperiment>>);
            project.structures = std::move(prepared->structures_);
            project.experiments = std::move(prepared->experiments_);
            project.adopt_experiments();
            prepared->committed_ = true; // adjacent actual latch, before any preview/UI callback
        });
    }
    /// Undo only this addition, with exact row identity; never restore a whole
    /// old Project over unrelated metadata/settings or a later scientific owner.
    static Edit undo_empty_population(Project& project, std::shared_ptr<EmptyProjectPopulation> prepared) {
        return Edit([&project, prepared = std::move(prepared)] {
            if (!prepared || !prepared->committed_ || prepared->undone_ ||
                project.structures.size() != 1 || project.experiments.size() != 1 ||
                project.structures.front() != prepared->structure_ || project.experiments.front() != prepared->experiment_ ||
                !project.aliases.empty() || !project.constraints.empty() || !project.report_files.empty() ||
                !empty_population_fit(project.fit_result))
                throw std::invalid_argument("undo: the added scientific graph has been replaced or has dependent results/relations");
            ItemVec<Structure> structures;
            ItemVec<BraggPdExperiment> experiments;
            project.structures = std::move(structures);
            project.experiments = std::move(experiments);
            project.adopt_experiments();
            prepared->undone_ = true;
        });
    }

    // Runs the operation: its refusal, with nothing written, or the whole write.
    struct AppliedResult {
        const Structure* structure = nullptr;
        const ExperimentBase* experiment = nullptr;
        const AtomSite* atom = nullptr;
        const ExcludedRegion* exclusion = nullptr;
        const LinkedStructure* linked_structure = nullptr;
        const ParameterConstraint* constraint = nullptr;
    };
    // Executes this same closed operation once. The result is an identity fact,
    // not a getter or a grant to use a row after its owner has retired.
    AppliedResult apply_result() const {
        if (result_operation_) return result_operation_();
        operation_(); return {};
    }
    void operator()() const { (void)apply_result(); }

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
    // Free or fix several parameters, by unique name, all or none (the parameter table's "free" header; the owner,
    // 2026-10-11): every name is resolved before any flag is written. Its undo is the same edit with the flags as
    // they were.
    static Edit set_free(Project& project, std::vector<std::pair<std::string, bool>> flags) {
        return Edit([&project, flags = std::move(flags)] {
            std::map<std::string, Parameter*> by_name;
            for (const NamedSlot& slot : named_slots(project)) {
                by_name.emplace(slot.unique_name, slot.parameter);
            }
            std::vector<std::pair<Parameter*, bool>> resolved;
            for (const auto& [name, free] : flags) {
                const auto found = by_name.find(name);
                if (found == by_name.end()) {
                    throw std::invalid_argument("'" + name + "' is not a refinable parameter of this project");
                }
                resolved.emplace_back(found->second, free);
            }
            for (const auto& [parameter, free] : resolved) {
                parameter->free = free;
            }
        });
    }
    static Edit assign(double& field, double value) {
        return Edit([&field, value] { field = value; });
    }
    static Edit assign(std::string& field, std::string value) {
        return Edit([&field, value = std::move(value)] { field = value; });
    }
    // Every report setting at once, as `state` holds them (an Undo of one of them).
    static Edit report_settings(Project& project, ReportSettingsState state) {
        return Edit([&project, state = std::move(state)] {
            project.report_html = state.html;
            project.report_pdf = state.pdf;
            project.report_cif = state.cif;
            project.report_html_offline = state.html_offline;
            project.report_excluded = state.excluded;
            project.correlation_threshold = state.correlation_threshold;
            project.pattern_x_axis = state.pattern_x_axis;
        });
    }
    // The project's report settings (ADR-0036 §7), each absent until stated.
    static Edit assign(std::optional<bool>& field, std::optional<bool> value) {
        return Edit([&field, value] { field = value; });
    }
    static Edit assign(std::optional<double>& field, std::optional<double> value) {
        return Edit([&field, value] { field = value; });
    }
    static Edit assign(std::optional<std::string>& field, std::optional<std::string> value) {
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
    /// Assign a whole validated assistant batch, resolving and checking every path before the first write.
    static Edit parameter_values(Project& project, std::vector<std::pair<std::string, double>> values) {
        return Edit([&project, values = std::move(values)] {
            std::map<std::string, Parameter*> by_name;
            for (const NamedSlot& slot : named_slots(project)) by_name.emplace(slot.unique_name, slot.parameter);
            std::vector<std::pair<Parameter*, double>> targets;
            std::set<std::string> seen;
            for (const auto& [name, value] : values) {
                const auto found = by_name.find(name);
                if (found == by_name.end() || !seen.insert(name).second || !std::isfinite(value))
                    throw std::invalid_argument("Invalid or duplicate parameter: " + name);
                Parameter copy = *found->second;
                assign_value(copy, value);
                targets.emplace_back(found->second, value);
            }
            for (const auto& [parameter, value] : targets) parameter->value = value;
        });
    }
    /// Adopt an isolated fit's parameter/result state without replacing the live model's identity-bearing rows.
    static Edit assistant_result(Project& project, std::shared_ptr<const Project> fitted) {
        return Edit([&project, fitted = std::move(fitted)] {
            const auto targets = named_slots(project);
            auto source = std::make_shared<Project>(*fitted);
            const auto sources = named_slots(*source);
            if (targets.size() != sources.size() || project.experiments.size() != source->experiments.size())
                throw std::invalid_argument("The trial no longer names this project's parameters");
            for (std::size_t i = 0; i < targets.size(); ++i) {
                if (targets[i].unique_name != sources[i].unique_name)
                    throw std::invalid_argument("The trial's parameter identities changed");
                Parameter checked = *sources[i].parameter;
                assign_value(checked, checked.value.get());
            }
            for (std::size_t i = 0; i < targets.size(); ++i) {
                Parameter& to = *targets[i].parameter;
                const Parameter& from = *sources[i].parameter;
                to.value = from.value.get(); to.uncertainty = from.uncertainty.get();
                to.free = from.free.get(); to.start_value = from.start_value.get();
                to.start_uncertainty = from.start_uncertainty.get();
            }
            static_assert(std::is_nothrow_move_assignable_v<FitResultRecord>);
            project.fit_result = std::move(source->fit_result);
            for (std::size_t i = 0; i < project.experiments.size(); ++i)
                copy_fit_share(*project.experiments[i], *source->experiments[i]);
        });
    }
    // A background point's fixed position: one recorded assignment, which cannot fail.
    static Edit background_position(LineSegment& point, double position) {
        return Edit([&point, position] { point.position = position; });
    }

    /// Commit one exact preparation, or restore its shared-row Undo, on the owner thread.
    /// Project and its original bank are borrowed and must outlive execution.
    /// The Edit owns prepared; no callbacks run inside its closed model mutation.
    /// Throws invalid_argument for stale/conflicting input; allocation may throw
    /// before ItemVec's all-or-none commit. A committed latch precedes publication.
    static Edit background_point(Project& project, std::shared_ptr<BackgroundPointChange> prepared, bool undo = false) {
        return Edit([&project, prepared = std::move(prepared), undo] {
            if (!prepared || !prepared->experiment || (undo ? !prepared->committed || prepared->undone : prepared->committed))
                throw std::invalid_argument("the background operation is no longer current");
            const auto owner = std::find_if(project.experiments.begin(), project.experiments.end(),
                [&](const auto& e) { return e.get() == prepared->experiment; });
            if (owner == project.experiments.end()) throw std::invalid_argument("the background experiment was replaced");
            auto& rows = (*owner)->background;
            if (!prepared->same_source(**owner) || (!undo && (rows.category_stamp() != prepared->stamp ||
                project.aliases.category_stamp() != prepared->alias_stamp || project.constraints.category_stamp() != prepared->constraint_stamp)))
                throw std::invalid_argument("the prepared background input changed before its edit");
            const auto& expected = undo ? prepared->after : prepared->before;
            if (rows.size() != expected.size() || !std::equal(rows.begin(), rows.end(), expected.begin()))
                throw std::invalid_argument("the exact background rows were replaced");
            // The affected detached/live row must still have the exact prepared state;
            // unrelated surviving rows are shared and never copied back by Undo.
            const auto matches = [](const auto& rows, const auto& state) {
                if (!state) return true;
                const auto row = std::find_if(rows.begin(), rows.end(), [&](const auto& p) { return p->id.value() == state->id.value(); });
                return row != rows.end() && BackgroundPointChange::same_point(**row, *state);
            };
            if (!matches(prepared->before, prepared->original) || !matches(prepared->after, prepared->replacement))
                throw std::invalid_argument("the affected background row changed outside its prepared edit");
            if (undo && !prepared->original && prepared->replacement) {
                const auto name = detail::background_parameter_name(**owner, prepared->replacement->id.value());
                for (const auto& alias : project.aliases) if (alias->parameter_unique_name.value() == name)
                    throw std::invalid_argument("a current alias still names the added background point");
            }
            // A new native result is strict, but Undo restores the captured
            // lawful manual arrangement, including its order/extrapolation.
            // Surviving unrelated rows stay shared, never copied back.
            auto candidate = undo ? prepared->before : prepared->after;
            for (const auto& point : candidate) if (!std::isfinite(point->position.get()) || !std::isfinite(point->intensity.value.get()))
                throw std::invalid_argument("background anchors must be finite");
            if (prepared->native_request && !undo) {
                std::sort(candidate.begin(), candidate.end(), [](const auto& a, const auto& b) { return a->position.get() < b->position.get(); });
                std::optional<double> previous;
                for (const auto& point : candidate) {
                    const auto x = point->position.get();
                    if (x < prepared->low || x > prepared->high || (previous && x <= *previous))
                        throw std::invalid_argument("background positions must remain distinct and in the measured domain");
                    previous = x;
                }
            }
            // Copies/admission precede the single live collection commit.
            rows.assign(std::move(candidate));
            if (undo) prepared->undone = true; else prepared->committed = true;
        });
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
        // Original mode/vocabulary/family rule executes on a detached narrow image.
        // Both creation and retirement of OptionalParameter cells precede live writes.
        return Edit([&experiment,token=std::move(token)] {
            auto image=experiment.absorption;
            apply_absorption_family(image,absorption_file_token(experiment.effective_beam_mode(),token));
            detail::PreparedAbsorptionRestore prepared(experiment.absorption,std::move(image));
            prepared.commit();
        });
    }
    // The background model, the old type's rows and constants removed (select_background_type).
    static Edit background_type(ExperimentBase& experiment, std::string token) {
        return Edit([&experiment, token = std::move(token)] { select_background_type(experiment, token); });
    }
    // A polynomial or Chebyshev background's terms: one appended at the lowest free order, a term's order, the
    // polynomial's origin and an end of the Chebyshev domain, each under its rule.
    static Edit background_point_ids(ExperimentBase& experiment, std::vector<std::string> ids) {
        return Edit([&experiment, ids = std::move(ids)] { set_background_point_ids(experiment, ids); });
    }
    static Edit append_background_term(ExperimentBase& experiment) {
        return Edit([&experiment] { experiment.background_terms.push_back(next_background_term(experiment)); });
    }
    static Edit background_term_order(ExperimentBase& experiment, PolynomialTerm& term, int order) {
        return Edit([&experiment, &term, order] { set_background_term_order(experiment, term, order); });
    }
    static Edit background_origin(ExperimentBase& experiment, double origin) {
        return Edit([&experiment, origin] { set_background_origin(experiment, origin); });
    }
    static Edit background_domain(ExperimentBase& experiment, bool end, double value) {
        return Edit([&experiment, end, value] { set_background_domain(experiment, end, value); });
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
    static Edit erase(ItemVec<PolynomialTerm>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<PrefOrient>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<LinkedStructure>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<ParameterAlias>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<ParameterConstraint>& rows, std::size_t index) { return erasing(rows, index); }
    static Edit erase(ItemVec<Structure>& rows, std::size_t index) { return erasing(rows, index); }
    // A row-level removal cannot see the project's scan declaration: the app removes experiments through
    // erase_experiment, which keeps a scan's one template experiment.
    static Edit erase(ItemVec<BraggPdExperiment>& rows, std::size_t index) { return erasing(rows, index); }
    /// Rename a background row under its collection's uniqueness rule.
    static Edit background_id(LineSegment& point, std::string id) {
        return Edit([&point, id = std::move(id)] { point.id = id; });
    }
    /// Rename an exclusion row under its collection's uniqueness rule.
    static Edit excluded_region_id(ExcludedRegion& region, std::string id) {
        return Edit([&region, id = std::move(id)] { region.id = id; });
    }
    static Edit append_excluded_region(ExperimentBase& experiment, double start, double end) {
        return appending(experiment.excluded_regions, ExcludedRegion(start,end));
    }
    static Edit erase_excluded_region(ExperimentBase& experiment, std::size_t row) {
        return Edit([&experiment, row] { require_region(experiment, row); experiment.excluded_regions.erase_at(row); });
    }
    static Edit excluded_region_bound(ExperimentBase& experiment, std::size_t row, bool end, double value) {
        return Edit([&experiment, row, end, value] {
            require_region(experiment, row);
            auto& region = *experiment.excluded_regions[row];
            (end ? region.second : region.first) = value;
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
        return Edit(ResultOperation{}, [&project, structure = std::make_shared<Structure>(std::move(structure))] {
            add_loaded_structure(project, *structure);
            const auto* inserted=project.structures.back().get();
            return AppliedResult{inserted, nullptr,
                inserted->atom_sites.size()==1?inserted->atom_sites[0].get():nullptr};
        });
    }
    // A structure removed with every experiment's link to it and texture row for it, all or none.
    static Edit remove_structure(Project& project, std::size_t index) {
        return Edit([&project, index] {
            if (index >= project.structures.size()) {
                throw std::out_of_range("the project has no structure " + std::to_string(index));
            }
            const std::string name = spelled_structure(project.structures[index]->name.value());
            std::vector<ItemVec<Structure>::Ptr> structures(project.structures.begin(), project.structures.end());
            structures.erase(structures.begin() + static_cast<std::ptrdiff_t>(index));
            std::vector<std::vector<ItemVec<LinkedStructure>::Ptr>> links;
            std::vector<std::vector<ItemVec<PrefOrient>::Ptr>> texture;
            for (const auto& experiment : project.experiments) {
                auto& kept_links = links.emplace_back();
                for (const auto& link : experiment->linked_structures) {
                    if (spelled_structure(link->structure_id.value()) != name) {
                        kept_links.push_back(link);
                    }
                }
                auto& kept_texture = texture.emplace_back();
                for (const auto& row : experiment->preferred_orientation) {
                    if (spelled_structure(row->structure_id.value()) != name) {
                        kept_texture.push_back(row);
                    }
                }
            }
            for (std::size_t i = 0; i < project.experiments.size(); ++i) {
                project.experiments[i]->linked_structures.assign(std::move(links[i]));
                project.experiments[i]->preferred_orientation.assign(std::move(texture[i]));
            }
            project.structures.assign(std::move(structures));
        });
    }
    // The structures, links and texture rows put back as `before` holds them (an undo of Create or Remove
    // structure): each experiment is found by identity first, so one removed since refuses with nothing written.
    static Edit restore_structures(Project& project, StructuresUndo before) {
        return Edit([&project, before = std::make_shared<StructuresUndo>(std::move(before))] {
            if (before->related.has_value() != before->fit_result.has_value())
                throw std::invalid_argument("undo: the structure scientific history is incomplete");
            std::vector<ExperimentBase*> experiments;
            for (const StructuresUndo::ExperimentRows& rows : before->experiments) {
                const auto found = std::find_if(project.experiments.begin(), project.experiments.end(),
                                                [&rows](const auto& held) { return held.get() == rows.experiment; });
                if (found == project.experiments.end())
                    throw std::invalid_argument("undo: an experiment the structures were linked to is no longer in the project");
                experiments.push_back(found->get());
            }
            std::vector<ItemVec<Structure>::Ptr> structures;
            for (const auto& structure : before->structures) structures.push_back(std::make_shared<Structure>(structure));
            ItemVec<Structure> prepared_structures(std::move(structures));
            std::vector<ItemVec<LinkedStructure>> links;
            std::vector<ItemVec<PrefOrient>> textures;
            links.reserve(experiments.size()); textures.reserve(experiments.size());
            for (const auto& rows : before->experiments) {
                std::vector<ItemVec<LinkedStructure>::Ptr> linked;
                for (const auto& row : rows.links) linked.push_back(std::make_shared<LinkedStructure>(row));
                links.emplace_back(std::move(linked));
                std::vector<ItemVec<PrefOrient>::Ptr> texture;
                for (const auto& row : rows.texture) texture.push_back(std::make_shared<PrefOrient>(row));
                textures.emplace_back(std::move(texture));
            }
            std::vector<std::pair<Parameter*,const RelationsUndo::ParameterState*>> targets;
            ItemVec<ParameterAlias> aliases;
            ItemVec<ParameterConstraint> constraints;
            std::optional<FitResultRecord> fit_result;
            if (before->related) {
                std::map<std::string,Parameter*> named;
                for (const auto& slot : named_slots(project)) named.emplace(slot.unique_name,slot.parameter);
                std::set<const Parameter*> replaced;
                for (const auto& structure : project.structures)
                    for (const auto* parameter : structure->parameters()) replaced.insert(parameter);
                for (const auto* experiment : experiments) {
                    for (const auto& link : experiment->linked_structures) replaced.insert(&link->scale);
                    for (const auto& row : experiment->preferred_orientation)
                        for (const auto* parameter : row->parameters()) replaced.insert(parameter);
                }
                std::set<const Parameter*> admitted;
                for (auto* experiment : experiments)
                    for (const auto* parameter : experiment->parameters())
                        if (!replaced.contains(parameter)) admitted.insert(parameter);
                for (const auto& state : before->related->parameters) {
                    const auto found=named.find(state.unique_name);
                    if (found==named.end() || replaced.contains(found->second) || !admitted.contains(found->second))
                        throw std::invalid_argument("undo: a related experiment parameter is no longer in the project");
                    targets.emplace_back(found->second,&state);
                }
                std::vector<ItemVec<ParameterAlias>::Ptr> alias_rows;
                for (const auto& row : before->related->aliases) alias_rows.push_back(std::make_shared<ParameterAlias>(row));
                aliases=ItemVec<ParameterAlias>(std::move(alias_rows));
                std::vector<ItemVec<ParameterConstraint>::Ptr> constraint_rows;
                for (const auto& row : before->related->constraints) constraint_rows.push_back(std::make_shared<ParameterConstraint>(row));
                constraints=ItemVec<ParameterConstraint>(std::move(constraint_rows));
                fit_result=before->fit_result;
            }
            // All owners, columns and target identities are prepared BEFORE the
            // first live replacement. ItemVec moves are its original noexcept
            // commit; remaining parameter writes are the original scalar roles.
            static_assert(std::is_nothrow_move_assignable_v<FitResultRecord>);
            project.structures=std::move(prepared_structures);
            for (std::size_t i=0;i<experiments.size();++i) {
                experiments[i]->linked_structures=std::move(links[i]);
                experiments[i]->preferred_orientation=std::move(textures[i]);
            }
            if (before->related) {
                project.aliases=std::move(aliases);project.constraints=std::move(constraints);
                project.fit_result=std::move(*fit_result);
                for (const auto& [parameter,state] : targets) {
                    parameter->value=state->value;parameter->uncertainty=state->uncertainty;parameter->free=state->free;
                }
            }
        });
    }

    static Edit restore_experiment_controls(Project& project,ExperimentControlsUndo state) {
        auto before=std::make_shared<const ExperimentControlsUndo>(std::move(state));
        return Edit([&project,before] {
            const auto found=std::find_if(project.experiments.begin(),project.experiments.end(),[&](const auto& member){return member.get()==before->experiment;});
            if(found==project.experiments.end())throw std::invalid_argument("undo: experiment control owner is no longer in the project");
            const int owners=int(before->peak.has_value())+int(before->regions.has_value())+int(before->absorption.has_value())+
                int(before->cutoff_fwhm.has_value())+int(before->dataset_weight.has_value())+int(before->links.has_value());
            const bool family=before->peak.has_value() || before->absorption.has_value() || before->links.has_value();
            if(owners!=1 || family!=before->related.has_value() || (!before->regions.has_value())!=before->fit_result.has_value())
                throw std::invalid_argument("undo: incomplete experiment-control footprint");
            auto& experiment=**found;
            std::unique_ptr<detail::PreparedPeakRestore> peak;
            std::unique_ptr<detail::PreparedAbsorptionRestore> absorption;
            ItemVec<ExcludedRegion> regions;ItemVec<LinkedStructure> links;
            std::vector<std::pair<Parameter*,const RelationsUndo::ParameterState*>> targets;
            ItemVec<ParameterAlias> aliases;ItemVec<ParameterConstraint> constraints;
            std::optional<FitResultRecord> fit_result;
            if(family) {
                if(before->peak)peak=std::make_unique<detail::PreparedPeakRestore>(experiment.peak,*before->peak);
                else if(before->absorption)absorption=std::make_unique<detail::PreparedAbsorptionRestore>(experiment.absorption,*before->absorption);
                else {
                    std::vector<ItemVec<LinkedStructure>::Ptr> rows;rows.reserve(before->links->size());
                    for(const auto& row:*before->links)rows.push_back(std::make_shared<LinkedStructure>(row));
                    links=ItemVec<LinkedStructure>(std::move(rows));
                }
                std::map<std::string,Parameter*> named;
                for(const auto& slot:named_slots(project))named.emplace(slot.unique_name,slot.parameter);
                auto replaced=before->peak?experiment.peak.parameters():before->absorption?experiment.absorption.parameters():std::vector<Parameter*>{};
                if(before->links)for(const auto& row:experiment.linked_structures)replaced.push_back(&row->scale);
                for(const auto& state:before->related->parameters) {
                    const auto at=named.find(state.unique_name);
                    if(at==named.end() || std::find(replaced.begin(),replaced.end(),at->second)!=replaced.end())
                        throw std::invalid_argument("undo: a related parameter is no longer in the project");
                    targets.emplace_back(at->second,&state);
                }
                std::vector<ItemVec<ParameterAlias>::Ptr> a;for(const auto& row:before->related->aliases)a.push_back(std::make_shared<ParameterAlias>(row));
                std::vector<ItemVec<ParameterConstraint>::Ptr> c;for(const auto& row:before->related->constraints)c.push_back(std::make_shared<ParameterConstraint>(row));
                aliases=ItemVec<ParameterAlias>(std::move(a));constraints=ItemVec<ParameterConstraint>(std::move(c));fit_result=before->fit_result;
            } else if(before->regions) {
                std::vector<ItemVec<ExcludedRegion>::Ptr> rows;
                for(const auto& row:*before->regions)rows.push_back(std::make_shared<ExcludedRegion>(row));
                regions=ItemVec<ExcludedRegion>(std::move(rows));
            }
            if(family) {
                // Every allocation/target validation above precedes these original no-throw transfers.
                static_assert(std::is_nothrow_move_assignable_v<ItemVec<LinkedStructure>>);
                static_assert(std::is_nothrow_move_assignable_v<FitResultRecord>);
                if(peak)peak->commit();else if(absorption)absorption->commit();else experiment.linked_structures=std::move(links);
                project.aliases=std::move(aliases);project.constraints=std::move(constraints);project.fit_result=std::move(*fit_result);
                for(const auto& [parameter,state]:targets){parameter->value=state->value;parameter->uncertainty=state->uncertainty;parameter->free=state->free;}
            } else if(before->regions)experiment.excluded_regions=std::move(regions);
            else {
                // Own the result image before either live scalar or result changes.
                auto restored=*before->fit_result;
                static_assert(std::is_nothrow_move_assignable_v<FitResultRecord>);
                if(before->cutoff_fwhm)experiment.peak.cutoff_fwhm=*before->cutoff_fwhm;
                else experiment.dataset_weight=*before->dataset_weight;
                project.fit_result=std::move(restored);
            }
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
    // against the project's. It may join experiments with measured data: a fit skips it.
    static Edit create_experiment(Project& project, BraggPdExperiment experiment) {
        auto created = std::make_shared<BraggPdExperiment>(std::move(experiment));
        return Edit(ResultOperation{}, [&project, created] {
            require_scan_template(project, project.experiments.size() + 1);
            const std::string key = KeyTraits<BraggPdExperiment>::canonical(created->name);
            for (const auto& held : project.experiments) {
                if (KeyTraits<BraggPdExperiment>::canonical(held->name) == key) {
                    throw IoError("an experiment named '" + detail::printable_id(created->name) +
                                  "' is already in the project");
                }
            }
            auto inserted = std::make_shared<BraggPdExperiment>(*created);
            project.experiments.push_back(inserted);
            return AppliedResult{nullptr, inserted.get()};
        });
    }
    // An experiment without measured data replaced in its place by `replacement` (a new type of it, from
    // simulation_experiment): refused once the experiment holds measured data, whose type the data fixes.
    static Edit replace_experiment(Project& project, const ExperimentBase& experiment, BraggPdExperiment replacement) {
        auto next = std::make_shared<BraggPdExperiment>(std::move(replacement));
        return Edit(ResultOperation{}, [&project, &experiment, next] {
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
            auto inserted = std::make_shared<BraggPdExperiment>(*next);
            *found = inserted;
            project.experiments.assign(std::move(all));
            return AppliedResult{nullptr, inserted.get()};
        });
    }
    // An experiment made with Create experiment replaced in its place by `replacement`: the same experiment with
    // measured data read from a file (Load data), or as it was before (its undo). The new name is checked against
    // the other experiments'.
    static Edit load_data(Project& project, const ExperimentBase& experiment, BraggPdExperiment replacement) {
        auto next = std::make_shared<BraggPdExperiment>(std::move(replacement));
        return Edit(ResultOperation{}, [&project, &experiment, next] {
            std::vector<ItemVec<BraggPdExperiment>::Ptr> all(project.experiments.begin(), project.experiments.end());
            const auto found = std::find_if(all.begin(), all.end(), [&experiment](const auto& held) {
                return held.get() == &experiment;
            });
            if (found == all.end()) {
                throw std::invalid_argument("the experiment is not in the project");
            }
            const std::string key = KeyTraits<BraggPdExperiment>::canonical(next->name);
            for (const auto& held : all) {
                if (held.get() != &experiment && KeyTraits<BraggPdExperiment>::canonical(held->name) == key) {
                    throw IoError("an experiment named '" + detail::printable_id(next->name) +
                                  "' is already in the project");
                }
            }
            auto inserted = std::make_shared<BraggPdExperiment>(*next);
            *found = inserted;
            project.experiments.assign(std::move(all));
            return AppliedResult{nullptr, inserted.get()};
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
    using ScanValue = detail::ScanViewValue;
    static Edit scan_view(Project& project, ExperimentBase& experiment, std::vector<ScanValue> values, PdDataBase data) {
        auto shown = std::make_shared<PdDataBase>(std::move(data));
        return Edit([&project, &experiment, values = std::move(values), shown] {
            auto prepared = detail::prepare_scan_view(project, experiment, values, *shown);
            prepared.commit();
        });
    }

    // An edit of the relations undone (edi ADR-0024): the alias and constraint rows as they were, and each
    // parameter the edit changed back to its state then. Every parameter is resolved first, so one whose
    // row was removed since refuses with nothing written. Both complete ItemVec replacements
    // (keys, table columns and memberships) are admitted before either live move commit;
    // numeric/optional/flag writes and those moves cannot fail. The door's completion then
    // re-derives every mark and implied value.
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
            // ItemVec admission builds the columns, keys and memberships. Prepare BOTH
            // collections before either live write; their move commits cannot throw.
            ItemVec<ParameterAlias> prepared_aliases(std::move(aliases));
            ItemVec<ParameterConstraint> prepared_constraints(std::move(constraints));
            project.aliases = std::move(prepared_aliases);
            project.constraints = std::move(prepared_constraints);
            for (const auto& [parameter, state] : targets) {
                parameter->value = state->value;
                parameter->uncertainty = state->uncertainty;
                parameter->free = state->free;
            }
        });
    }

    // FIRST ordinary relation edits: complete the prospective declaration inside
    // serialized execution, after Input observers and BEFORE the live assignment.
    static Edit constraint_append(Project& project, ParameterConstraint complete) {
        return Edit(ResultOperation{}, [&project, complete = std::make_shared<ParameterConstraint>(std::move(complete))] {
            {
                Project candidate = project;
                candidate.constraints.push_back(std::make_shared<ParameterConstraint>(*complete));
                if (complete->enabled.get() && candidate.structures.empty())
                    throw std::invalid_argument("An active constraint requires a structure");
                complete_relations(candidate);
            }
            auto inserted = std::make_shared<ParameterConstraint>(*complete);
            project.constraints.push_back(inserted);
            AppliedResult result; result.constraint = inserted.get(); return result;
        });
    }
    static Edit constraint_expression(Project& project, ParameterConstraint& member, std::string text) {
        return Edit([&project, &member, text = std::move(text)] {
            std::size_t at = 0;
            while (at < project.constraints.size() && project.constraints[at].get() != &member) ++at;
            if (at == project.constraints.size()) throw std::invalid_argument("The constraint is no longer in this project");
            {
                Project candidate = project;
                candidate.constraints[at]->expression = text;
                if (candidate.constraints[at]->enabled.get() && candidate.structures.empty())
                    throw std::invalid_argument("An active constraint requires a structure");
                complete_relations(candidate);
            }
            member.expression = text;
        });
    }
    static Edit constraint_enabled(Project& project, ParameterConstraint& member, bool enabled) {
        return Edit([&project, &member, enabled] {
            std::size_t at = 0;
            while (at < project.constraints.size() && project.constraints[at].get() != &member) ++at;
            if (at == project.constraints.size()) throw std::invalid_argument("The constraint is no longer in this project");
            {
                Project candidate = project;
                candidate.constraints[at]->enabled = enabled;
                if (enabled && candidate.structures.empty())
                    throw std::invalid_argument("An active constraint requires a structure");
                complete_relations(candidate);
            }
            member.enabled = enabled;
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
    struct ResultOperation {};
    explicit Edit(std::function<void()> operation) : operation_(std::move(operation)) {}
    Edit(ResultOperation, std::function<AppliedResult()> operation) : result_operation_(std::move(operation)) {}

    // The row factories' one body each, for the model row types above only: nothing outside this
    // class names them.
    template <typename Row>
    static Edit appending(ItemVec<Row>& rows, Row row) {
        return Edit(ResultOperation{}, [&rows, row = std::make_shared<Row>(std::move(row))] {
            auto inserted=std::make_shared<Row>(*row);
            rows.push_back(inserted);
            if constexpr (std::is_same_v<Row,AtomSite>) return AppliedResult{nullptr,nullptr,inserted.get()};
            else if constexpr (std::is_same_v<Row,ExcludedRegion>) return AppliedResult{nullptr,nullptr,nullptr,inserted.get()};
            else if constexpr (std::is_same_v<Row,LinkedStructure>) return AppliedResult{nullptr,nullptr,nullptr,nullptr,inserted.get()};
            else return AppliedResult{};
        });
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
    // A structure's name as links spell it: an empty one is `structure` (the loader's rule).
    static std::string spelled_structure(const std::string& id) { return id.empty() ? std::string("structure") : id; }
    static void require_region(const ExperimentBase& experiment, std::size_t row) {
        if (row >= experiment.excluded_regions.size()) {
            throw std::out_of_range("the experiment has no excluded region " + std::to_string(row));
        }
    }
    // Refuses an id whose item a collection other than the model's own ItemVec<Item> holds: a
    // caller's keyed type derived from a model type would bring its own rename rule (KeyTraits),
    // which could write and then throw. A detached id has no rule to run.
    template <typename Item>
    static void require_model_owner(const ItemKey& id, const char* what) {
        if (id.owner() != nullptr && dynamic_cast<const ItemVec<Item>*>(id.owner()) == nullptr) {
            throw std::invalid_argument(std::string(what) + " is not held by the model's own collection");
        }
    }

    std::function<void()> operation_;
    std::function<AppliedResult()> result_operation_;
};

}  // namespace edi

#endif  // EDI_EDIT_HPP
