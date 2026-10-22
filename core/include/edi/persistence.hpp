// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <memory>
#include <cstddef>
#include <string>
#include <string_view>
#include <utility>
#include <vector>
#include "edi/calculation.hpp"
namespace edi {
// One admitted current-owner image. Owner-thread capture records currentness
// BEFORE copying (a model copy deliberately renews collection generations).
struct PersistenceSnapshot {
    std::unique_ptr<Project> model;
    WorkStamps stamps;
    std::vector<bool> geometry_current;
    std::vector<bool> computed_current;
    std::size_t construction_bytes = 0;
    std::size_t retained_bytes = 0;
    // Preowned reusable payload slot after model is released by the save worker.
    // This is an allowance, not a claim that rounded hkl/geometry counts cannot
    // grow: calculate_saved_project checks its actual result before transfer.
    std::size_t calculation_bytes = 0;
};
struct PersistenceLimits {
    std::size_t construction_bytes;
    std::size_t file_bytes;
    std::size_t collection_bytes;
    std::size_t files;
};
PersistenceSnapshot snapshot_for_persistence(const Project&, const PersistenceLimits&);
// Worker-safe; the one existing native formatter, no calculation or file IO.
std::vector<std::pair<std::string,std::string>> prepare_project_documents(
    const PersistenceSnapshot&, const PersistenceLimits&);
/// Prepare the same native documents using an admitted captured project record.
/// The immutable scalar UTF-8 view belongs to the caller until return; no path
/// is opened and no view is retained. The same SDK formatter owns metadata/SU
/// merging. Existing limits apply before growth; malformed input, insufficient
/// capacity and stream/allocation errors propagate without returning a partial set.
std::vector<std::pair<std::string,std::string>> prepare_project_documents(
    const PersistenceSnapshot&, const PersistenceLimits&, std::string_view carried_record);
// Worker-side ordinary calculation of a strict native reopen. Inputs and
// copied stamps are admitted first; cancellation/refusal never publishes data.
// The returned immutable staged units must fit the caller's preowned retained
// role before transfer. No file I/O or publication on the live project occurs.
CalculationResult calculate_saved_project(Project& reopened, const WorkStamps& original,
    const PersistenceLimits&, std::size_t retained_limit, const work::CancelToken&);
// Prepared against the actual live owner, before disk publication. This is the
// existing save rounding contract (values/SUs and saved correlations), with all
// row/source/path allocations moved before its nonthrowing landing.
class PreparedSavedValues {
 public:
    PreparedSavedValues(Project&, const Project& reopened, WorkStamps, CalculationResult, std::string destination);
    // Bounded owner-thread preparation. New joins, copied rows/currentness and
    // publication metadata are admitted before allocation against this role;
    // CalculationResult's already owned buffers are moved, never charged as a
    // second model. The caller retains this reservation through presentation.
    PreparedSavedValues(Project&, const Project& reopened, const WorkStamps&, CalculationResult,
        std::string destination, std::size_t metadata_limit);
    ~PreparedSavedValues();
    PreparedSavedValues(const PreparedSavedValues&)=delete;
    PreparedSavedValues& operator=(const PreparedSavedValues&)=delete;
    // Owner thread, immediately after the caller rechecks original WorkStamps.
    // Wrong-owner/repeated commits refuse without writing. No callbacks occur.
    bool commit(Project&) noexcept;
 private:
    struct State;
    std::unique_ptr<State> state_;
};
}
