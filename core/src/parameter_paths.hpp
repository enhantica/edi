// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_PARAMETER_PATHS_HPP
#define EDI_PARAMETER_PATHS_HPP

// edi-owned parameter identity (lifted verbatim out of adapter.cpp): the identity-path
// grammar (`structure.cell.length_a`, `experiment.peak.rise_alpha_0`,
// `experiments[<bank>].background[3].intensity`, ...) and the translation of a crysta free-set /
// result LABEL onto the edi model Parameter it refines plus that parameter's path. Everything here
// operates on edi value types only — no crysta type, so it sits on edi's side of the ADR-0003 line
// and is unit-testable without the engine. core/src-private (never installed): the label grammar it
// mirrors is crysta's residual.cpp `free_from_model`, an engine fact edi's public surface must not
// expose (ADR-0009).

#include <array>
#include <cstddef>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "edi/model.hpp"

namespace edi::detail {

// A crysta FitResultBase label resolved onto edi's own model: the edi Parameter it refines + a
// stable, edi-owned identity path that resolves through `import edi`'s public model
// (`Project`.<attr>[.<attr>|[i]]…) — NO crysta engine label crosses the boundary. The path is the
// FitResultBase key; the pointer is the write-back target.
struct ResolvedParameter {
    Parameter* target;
    std::string path;
};

// The 14 profile coefficients in the engine's peak[] slot order (crysta experiment_builder.cpp:31-80:
// Gaussian [0..8], Lorentzian [9..13]) — the same order to_crysta_experiment feeds the builder, so
// build_index and the conversion cannot drift. V1 proves it rather than trusting this comment.
using PeakSlotField = Parameter& (*)(ExperimentBase&);
extern const std::array<std::pair<const char*, PeakSlotField>, 14> kPeakSlots;

// The six cell identity paths in dictionary order — shared by V1's completion-aware expectations
// and the cached surface's cell-write dispatch, so the two cannot disagree on the path grammar.
extern const std::array<const char*, 6> kCellPathNames;
std::optional<std::size_t> cell_path_slot(const std::string& path);

// Resolve the INSTRUMENT half of the label grammar (per-experiment quantities; `path_prefix` is the
// edi-owned path root — `experiment.` single-bank, `experiments[<bank>].` joint). nullopt if `label`
// is not an instrument label or names a field this experiment does not carry.
std::optional<ResolvedParameter> resolve_instrument_label(ExperimentBase& experiment,
                                                          const std::string& label,
                                                          const std::string& path_prefix);
// Resolve the SHARED STRUCTURAL half (cell, per-site coordinates / Biso / occupancy, by site label).
// `root` is the structure's path root (structure_root).
std::optional<ResolvedParameter> resolve_structural_label(Structure& structure,
                                                          const std::string& label,
                                                          const std::string& root = "structure.");
// A structure's path root: `structure.` in a project of one structure, else `structures[<name>].`.
std::string structure_root(const Project& project, const Structure& structure);
// The seam of a project of several structures (phases), one experiment: a `<structure>.` prefixed label
// names that structure's parameter, its link's scale or its texture row; anything else is resolve_label's.
std::optional<ResolvedParameter> resolve_project_label(Project& project, ExperimentBase& experiment,
                                                       const std::string& label);
// The joint seam of a project of several structures: `<bank>.<structure>.scale` (and texture) is that
// bank's link, `<bank>.<field>` its instrument, `<structure>.<label>` a structure's parameter; anything
// else is resolve_joint_label's.
std::optional<ResolvedParameter> resolve_joint_project_label(Project& project, const std::string& label);
// The SINGLE-BANK seam: unprefixed instrument labels, then the structural half.
std::optional<ResolvedParameter> resolve_label(Structure& structure, ExperimentBase& experiment,
                                               const std::string& label);
// The JOINT seam: longest-match `<bank>.` prefix, the one-bank unprefixed form, then the
// structural half. No bank-0 fallback on a multi-bank project.
std::optional<ResolvedParameter> resolve_joint_label(Structure& structure,
                                                     ItemVec<BraggPdExperiment>& experiments,
                                                     const std::string& label);

}  // namespace edi::detail

#endif  // EDI_PARAMETER_PATHS_HPP
