// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_CALCULATION_HPP
#define EDI_CALCULATION_HPP

#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "edi/model.hpp"
#include "edi/worker.hpp"

// ADR-0020 §1: the publication transaction. A calculation works on a snapshot of the project
// and stages what it produced; `publish` then checks that nothing the result depends on was
// written on the live project since the snapshot was taken, and either writes everything staged
// or nothing.
//
// Threading: the live project belongs to its owner thread; `snapshot_for_work` and `publish` run
// there. `calculate` runs anywhere and touches only its snapshot, which shares nothing mutable with
// the live project.

namespace edi {

// The live project's stamps when a snapshot was taken: what `publish` compares.
struct WorkStamps {
    // Per experiment: the calculation-input encoding `computed_current()` compares.
    std::vector<std::string> experiment_inputs;
    // Per structure: the geometry-input encoding `geometry_current()` compares.
    std::vector<std::string> structure_inputs;
    // The membership of both collections — the record and the identity of its last write, which a
    // replacement, an insertion, a removal or a whole assignment renews — and the project's editor
    // record and its identity then (Project::note_edit).
    std::shared_ptr<const detail::Membership> experiments;
    std::shared_ptr<const detail::Membership> structures;
    std::uint64_t experiments_generation = 0;
    std::uint64_t structures_generation = 0;
    std::shared_ptr<const detail::EditRecord> edits;
    std::uint64_t edits_at = 0;
    // The alias and constraint collections and their encoding (edi ADR-0024): a declaration write
    // supersedes a result taken before it.
    std::shared_ptr<const detail::Membership> aliases;
    std::shared_ptr<const detail::Membership> constraints;
    std::string relations;
};

// A copy of the project to calculate on, and the stamps of the live project it was copied from.
struct WorkSnapshot {
    Project project;
    WorkStamps stamps;
    // Where `calculate` reports its own start and end (work::EventKind::Calculating and Calculated), from
    // the thread it runs on. Empty for a calculation nothing traces; LivePreview sets it. The two events are
    // the calculation's own, so a caller that times the call sees both inside its interval.
    std::function<void(work::EventKind)> trace;
};

// What one calculation produced, for `publish`.
struct CalculationResult {
    WorkStamps stamps;
    // The job's token was set before or during the calculation: nothing was staged.
    bool cancelled = false;
    // Why crysta refused the pattern calculation; empty when it did not.
    std::string refusal;
    // Per experiment: the computed `_data` columns (the residual included) and `_refln`. Empty
    // after a refusal.
    std::vector<PdDataBase> data;
    std::vector<PowderReflnDataBase> refln;
    // Per structure: its computed geometry, or none where crysta refused it.
    std::vector<std::optional<StructureGeometry>> geometry;
    // Each dependent's value as the calculation completed it, by unique name (edi ADR-0024): publish
    // writes them with the arrays they were calculated from.
    std::vector<std::pair<std::string, double>> completed;
};

enum class PublishOutcome : std::uint8_t {
    Published,
    Superseded,  // something the result depends on was written after the snapshot; nothing was written
};

// Owner thread. The live project's stamps now: what a snapshot taken now would carry.
WorkStamps work_stamps(const Project& live);

// Owner thread. Takes the stamps, then copies the project.
WorkSnapshot snapshot_for_work(const Project& live);

// Any thread. What `calculated` holds computed now, staged for `publish` under `stamps` (a fitted copy's
// pattern, which the fit's own last calculation left). Each structure's geometry where it is current.
// With a `refusal`, or when an experiment's computed categories are not current (a model the calculation
// refused — a fit can move a model there), the result is that refusal and stages no pattern.
CalculationResult stage_computed(const Project& calculated, WorkStamps stamps, std::string refusal = {});

// Any thread. Runs Project::calculate() on the snapshot's own copy — crysta's current-result path;
// edi computes none of it. A refused calculation is returned, not thrown. The token is read before
// the calculation and after it; a calculation in progress is not interrupted. Reports Calculating
// as its first act and Calculated as its last to the snapshot's `trace`, whatever it returns.
CalculationResult calculate(WorkSnapshot& snapshot, const work::CancelToken& token);

// Owner thread. Nothing a result taken under `stamps` depends on was written on the live project since:
// the comparison `publish` makes before it writes.
bool unchanged_since(const Project& live, const WorkStamps& stamps);

// Owner thread. Compares every stamp with the live project; on any difference, or for a cancelled
// result, writes nothing and returns Superseded. Otherwise writes every experiment's computed
// columns, residual and `_refln` and every structure's geometry, each with its currency record —
// the state a direct Project::calculate() on the live project would have left — and returns
// Published. A refused pattern calculation clears every experiment's computed categories, still
// writes the geometry, and returns Published.
PublishOutcome publish(Project& live, CalculationResult&& result);

}  // namespace edi

#endif  // EDI_CALCULATION_HPP
