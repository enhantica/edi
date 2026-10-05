// SPDX-License-Identifier: BSD-3-Clause
#include "parameter_paths.hpp"

#include <algorithm>
#include <map>
#include <string>
#include <utility>
#include <vector>

#include "edi/categories.hpp"
#include "edi/model.hpp"
#include "edi/parameter_walk.hpp"

// Lifted verbatim out of adapter.cpp; see the header for what this file is.

namespace edi::detail {

// The 14 profile coefficients in the engine's peak[] slot order (crysta experiment_builder.cpp:31-80:
// Gaussian [0..8], Lorentzian [9..13]) — the same order to_crysta_experiment feeds the builder, so
// build_index and the conversion cannot drift. V1 proves it rather than trusting this comment.
const std::array<std::pair<const char*, PeakSlotField>, 14> kPeakSlots{{
    {"peak.rise_alpha_0", +[](ExperimentBase& e) -> Parameter& { return e.peak.rise_alpha_0; }},
    {"peak.rise_alpha_1", +[](ExperimentBase& e) -> Parameter& { return e.peak.rise_alpha_1; }},
    {"peak.decay_beta_0", +[](ExperimentBase& e) -> Parameter& { return e.peak.decay_beta_0; }},
    {"peak.decay_beta_1", +[](ExperimentBase& e) -> Parameter& { return e.peak.decay_beta_1; }},
    {"peak.broad_gauss_sigma_0",
     +[](ExperimentBase& e) -> Parameter& { return e.peak.broad_gauss_sigma_0; }},
    {"peak.broad_gauss_sigma_1",
     +[](ExperimentBase& e) -> Parameter& { return e.peak.broad_gauss_sigma_1; }},
    {"peak.broad_gauss_sigma_2",
     +[](ExperimentBase& e) -> Parameter& { return e.peak.broad_gauss_sigma_2; }},
    {"peak.broad_gauss_size", +[](ExperimentBase& e) -> Parameter& { return e.peak.broad_gauss_size; }},
    {"peak.broad_gauss_strain",
     +[](ExperimentBase& e) -> Parameter& { return e.peak.broad_gauss_strain; }},
    {"peak.broad_lorentz_gamma_0",
     +[](ExperimentBase& e) -> Parameter& { return e.peak.broad_lorentz_gamma_0; }},
    {"peak.broad_lorentz_gamma_1",
     +[](ExperimentBase& e) -> Parameter& { return e.peak.broad_lorentz_gamma_1; }},
    {"peak.broad_lorentz_gamma_2",
     +[](ExperimentBase& e) -> Parameter& { return e.peak.broad_lorentz_gamma_2; }},
    {"peak.broad_lorentz_size", +[](ExperimentBase& e) -> Parameter& { return e.peak.broad_lorentz_size; }},
    {"peak.broad_lorentz_strain",
     +[](ExperimentBase& e) -> Parameter& { return e.peak.broad_lorentz_strain; }},
}};

// The six cell identity paths in dictionary order — shared by V1's completion-aware expectations
// and the cached surface's cell-write dispatch, so the two cannot disagree on the path grammar.
const std::array<const char*, 6> kCellPathNames{"length_a",    "length_b",   "length_c",
                                                "angle_alpha", "angle_beta", "angle_gamma"};

std::optional<std::size_t> cell_path_slot(const std::string& path) {
    static const std::string kPrefix = "structure.cell.";
    if (path.compare(0, kPrefix.size(), kPrefix) != 0) return std::nullopt;
    for (std::size_t i = 0; i < kCellPathNames.size(); ++i) {
        if (path.compare(kPrefix.size(), std::string::npos, kCellPathNames[i]) == 0) return i;
    }
    return std::nullopt;
}

// Resolve the INSTRUMENT half of the label grammar — the per-experiment quantities crysta emits
// unprefixed for a single-bank fit and `<bank>.`-prefixed for a joint one. `path_prefix` is the
// edi-owned path root the caller wants (`experiment.` for the single-bank seam,
// `experiments[<bank>].` for a joint one), so both entry points share ONE label table and cannot
// drift apart. Returns nullopt if `label` is not an instrument label at all (the caller then tries
// the structural half) or names a field this experiment does not carry.
std::optional<ResolvedParameter> resolve_instrument_label(ExperimentBase& experiment,
                                                          const std::string& label,
                                                          const std::string& path_prefix) {
    if (label.rfind("background[", 0) == 0 && !label.empty() && label.back() == ']') {
        const std::size_t index = static_cast<std::size_t>(
            std::stoul(label.substr(11, label.size() - 12)));  // "background[<i>]"
        // The label names a row of the declared model's table.
        if (experiment.background_type != "line-segment") {
            if (index >= experiment.background_terms.size()) return std::nullopt;
            return ResolvedParameter{&experiment.background_terms[index]->coef,
                                     path_prefix + "background[" + std::to_string(index) + "].coef"};
        }
        if (index >= experiment.background.size()) return std::nullopt;
        return ResolvedParameter{&experiment.background[index]->intensity,
                                 path_prefix + "background[" + std::to_string(index) + "].intensity"};
    }
    // An unprefixed scale or texture label names the bank's one link and its one row; a bank of
    // several phases is addressed through `<structure>.scale` / `<structure>.march_*` only, so a
    // bare label never lands on the first phase.
    if (label == "scale") {
        if (experiment.linked_structures.size() != 1) return std::nullopt;
        return ResolvedParameter{&experiment.linked_structure().scale,
                                 path_prefix + "linked_structure.scale"};
    }
    if (label == "march_r" || label == "march_random_fract") {
        if (experiment.preferred_orientation.size() != 1 || experiment.linked_structures.size() != 1) {
            return std::nullopt;
        }
        PrefOrient& row = *experiment.preferred_orientation[0];
        return ResolvedParameter{label == "march_r" ? &row.march_r : &row.march_random_fract,
                                 path_prefix + "preferred_orientation[0]." + label};
    }
    // ONE flat label table: the seam rename made the TOF and CW label sets disjoint (crysta's CW 2θ
    // zero-shift is now "calib_twotheta_offset", its TOF calibration zero "calib_d_to_tof_offset"),
    // so the kind dispatch died with the collision that forced it. Every label leaf equals the edi
    // field leaf. Presence-tracked CW fields keep the fail-closed rule: a label whose field the
    // model never carried stays unresolvable — the abscor1 precedent — never a write to a value the
    // model never had.
    using RequiredField = Parameter& (*)(ExperimentBase&);
    static const std::map<std::string, std::pair<RequiredField, const char*>> kRequired{
        {"calib_d_to_tof_offset",
         {+[](ExperimentBase& e) -> Parameter& { return e.instrument.calib_d_to_tof_offset; },
          "instrument.calib_d_to_tof_offset"}},
        {"calib_d_to_tof_linear",
         {+[](ExperimentBase& e) -> Parameter& { return e.instrument.calib_d_to_tof_linear; },
          "instrument.calib_d_to_tof_linear"}},
        {"calib_d_to_tof_quadratic",
         {+[](ExperimentBase& e) -> Parameter& { return e.instrument.calib_d_to_tof_quadratic; },
          "instrument.calib_d_to_tof_quadratic"}},
        {"calib_d_to_tof_reciprocal",
         {+[](ExperimentBase& e) -> Parameter& { return e.instrument.calib_d_to_tof_reciprocal; },
          "instrument.calib_d_to_tof_reciprocal"}},
        {"rise_alpha_0",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.rise_alpha_0; }, "peak.rise_alpha_0"}},
        {"rise_alpha_1",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.rise_alpha_1; }, "peak.rise_alpha_1"}},
        {"decay_beta_0",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.decay_beta_0; }, "peak.decay_beta_0"}},
        {"decay_beta_1",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.decay_beta_1; }, "peak.decay_beta_1"}},
        {"broad_gauss_sigma_0",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.broad_gauss_sigma_0; },
          "peak.broad_gauss_sigma_0"}},
        {"broad_gauss_sigma_1",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.broad_gauss_sigma_1; },
          "peak.broad_gauss_sigma_1"}},
        {"broad_gauss_sigma_2",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.broad_gauss_sigma_2; },
          "peak.broad_gauss_sigma_2"}},
        {"broad_gauss_size",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.broad_gauss_size; },
          "peak.broad_gauss_size"}},
        {"broad_gauss_strain",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.broad_gauss_strain; },
          "peak.broad_gauss_strain"}},
        {"broad_lorentz_gamma_0",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.broad_lorentz_gamma_0; },
          "peak.broad_lorentz_gamma_0"}},
        {"broad_lorentz_gamma_1",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.broad_lorentz_gamma_1; },
          "peak.broad_lorentz_gamma_1"}},
        {"broad_lorentz_gamma_2",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.broad_lorentz_gamma_2; },
          "peak.broad_lorentz_gamma_2"}},
        {"broad_lorentz_size",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.broad_lorentz_size; },
          "peak.broad_lorentz_size"}},
        {"broad_lorentz_strain",
         {+[](ExperimentBase& e) -> Parameter& { return e.peak.broad_lorentz_strain; },
          "peak.broad_lorentz_strain"}},
    };
    if (const auto it = kRequired.find(label); it != kRequired.end()) {
        return ResolvedParameter{&it->second.first(experiment), path_prefix + it->second.second};
    }
    using OptionalField = std::optional<Parameter>& (*)(ExperimentBase&);
    static const std::map<std::string, std::pair<OptionalField, const char*>> kPresenceTracked{
        {"calib_twotheta_offset",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.instrument.calib_twotheta_offset; },
          "instrument.calib_twotheta_offset"}},
        {"setup_wavelength",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.instrument.setup_wavelength; },
          "instrument.setup_wavelength"}},
        // The CW line shifts, crysta's instrument[2]/[3].
        {"calib_sample_displacement",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.instrument.calib_sample_displacement; },
          "instrument.calib_sample_displacement"}},
        {"calib_sample_transparency",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.instrument.calib_sample_transparency; },
          "instrument.calib_sample_transparency"}},
        // The X-ray monochromator polarization, crysta's instrument[4]/[5].
        {"setup_polarization_coefficient",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.instrument.setup_polarization_coefficient; },
          "instrument.setup_polarization_coefficient"}},
        {"setup_monochromator_twotheta",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.instrument.setup_monochromator_twotheta; },
          "instrument.setup_monochromator_twotheta"}},
        {"broad_gauss_u",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.broad_gauss_u; },
          "peak.broad_gauss_u"}},
        {"broad_gauss_v",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.broad_gauss_v; },
          "peak.broad_gauss_v"}},
        {"broad_gauss_w",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.broad_gauss_w; },
          "peak.broad_gauss_w"}},
        {"broad_lorentz_x",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.broad_lorentz_x; },
          "peak.broad_lorentz_x"}},
        {"broad_lorentz_y",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.broad_lorentz_y; },
          "peak.broad_lorentz_y"}},
        // The pseudo-Voigt mixing, present only on the profiles that carry it.
        {"mixing_eta_0",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.mixing_eta_0; },
          "peak.mixing_eta_0"}},
        {"mixing_eta_1",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.mixing_eta_1; },
          "peak.mixing_eta_1"}},
        // The CW asymmetry coefficients, present only on the rung that carries them.
        {"asym_fcj_1",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.asym_fcj_1; },
          "peak.asym_fcj_1"}},
        {"asym_fcj_2",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.asym_fcj_2; },
          "peak.asym_fcj_2"}},
        {"asym_beba_a0",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.asym_beba_a0; },
          "peak.asym_beba_a0"}},
        {"asym_beba_b0",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.asym_beba_b0; },
          "peak.asym_beba_b0"}},
        {"asym_beba_a1",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.asym_beba_a1; },
          "peak.asym_beba_a1"}},
        {"asym_beba_b1",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.asym_beba_b1; },
          "peak.asym_beba_b1"}},
        {"asym_beba_limit",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.peak.asym_beba_limit; },
          "peak.asym_beba_limit"}},
        {"abscor1",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.absorption.abscor1; },
          "absorption.abscor1"}},
        {"mu_r",
         {+[](ExperimentBase& e) -> std::optional<Parameter>& { return e.absorption.mu_r; },
          "absorption.mu_r"}},
    };
    if (const auto it = kPresenceTracked.find(label); it != kPresenceTracked.end()) {
        std::optional<Parameter>& field = it->second.first(experiment);
        if (!field) return std::nullopt;
        return ResolvedParameter{&*field, path_prefix + it->second.second};
    }
    return std::nullopt;
}

// Resolve the SHARED STRUCTURAL half — the quantities crysta emits once per fit, unprefixed, for
// both the single-bank and joint layouts (cell length, positional basics, per-site Biso/occupancy).
std::optional<ResolvedParameter> resolve_structural_label(Structure& structure,
                                                          const std::string& label,
                                                          const std::string& root) {
    // All six cell labels crysta's free-set builder can emit (cell_symmetry.cpp kLabels). Mapping
    // cell_a alone was fact 5's gap: a Pnma cell_b/cell_c — or any non-cubic independent
    // edge/angle — died at the unmapped-label refusal. crysta only ever emits the INDEPENDENT
    // parameters of the resolved setting; the dependent ones follow through the completion
    // contract (to_completed_crysta_cell above).
    static const std::map<std::string, std::pair<Parameter Cell::*, const char*>> kCell{
        {"cell_length_a", {&Cell::length_a, "length_a"}},
        {"cell_length_b", {&Cell::length_b, "length_b"}},
        {"cell_length_c", {&Cell::length_c, "length_c"}},
        {"cell_angle_alpha", {&Cell::angle_alpha, "angle_alpha"}},
        {"cell_angle_beta", {&Cell::angle_beta, "angle_beta"}},
        {"cell_angle_gamma", {&Cell::angle_gamma, "angle_gamma"}},
    };
    if (const auto it = kCell.find(label); it != kCell.end()) {
        return ResolvedParameter{&(structure.cell.*(it->second.first)),
                                 root + "cell." + it->second.second};
    }
    const std::size_t dot = label.rfind('.');
    if (dot != std::string::npos) {
        const std::string site = label.substr(0, dot);
        const std::string field = label.substr(dot + 1);
        for (auto& atom_item : structure.atom_sites) {
            AtomSite& atom = *atom_item;
            if (atom.id != site) continue;
            // Sites are addressed by their edi label (stable across model edits), not list position.
            const std::string base = root + "atom_sites[" + atom.id + "].";
            if (field == "fract_x") return ResolvedParameter{&atom.fract_x, base + "fract_x"};
            if (field == "fract_y") return ResolvedParameter{&atom.fract_y, base + "fract_y"};
            if (field == "fract_z") return ResolvedParameter{&atom.fract_z, base + "fract_z"};
            if (field == "adp_iso") return ResolvedParameter{&atom.adp_iso, base + "adp_iso"};
            if (field == "occupancy") {
                return ResolvedParameter{&atom.occupancy, base + "occupancy"};
            }
        }
    }
    return std::nullopt;
}

std::string structure_root(const Project& project, const Structure& structure) {
    return project.structures.size() > 1 ? "structures[" + datablock_key(structure.name, "structure") + "]."
                                         : std::string("structure.");
}

namespace {
// The structure a `<structure>.` prefix names in a project of several structures, and the rest.
std::optional<std::pair<Structure*, std::string>> split_structure(Project& project, const std::string& label) {
    if (project.structures.size() < 2) {
        return std::nullopt;
    }
    for (const auto& item : project.structures) {
        const std::string key = datablock_key(item->name, "structure");
        if (label.size() > key.size() + 1 && label.compare(0, key.size(), key) == 0 && label[key.size()] == '.') {
            return std::make_pair(item.get(), label.substr(key.size() + 1));
        }
    }
    return std::nullopt;
}

// A phase-owned label of `experiment` (paths under `root`): `<structure>.scale` is its link's scale,
// `<structure>.march_*` its texture row's.
std::optional<ResolvedParameter> resolve_phase_label(Project& project, ExperimentBase& experiment,
                                                     const std::string& root, const std::string& label) {
    const auto split = split_structure(project, label);
    if (!split) {
        return std::nullopt;
    }
    const std::string key = datablock_key(split->first->name, "structure");
    const std::string& rest = split->second;
    if (rest == "scale") {
        for (const auto& link : experiment.linked_structures) {
            if (datablock_key(link->structure_id, "structure") == key) {
                return ResolvedParameter{&link->scale, root + "linked_structures[" + link->structure_id.value() + "].scale"};
            }
        }
    }
    if (rest == "march_r" || rest == "march_random_fract") {
        for (std::size_t row = 0; row < experiment.preferred_orientation.size(); ++row) {
            PrefOrient& texture = *experiment.preferred_orientation[row];
            if (datablock_key(texture.structure_id, "structure") == key) {
                return ResolvedParameter{rest == "march_r" ? &texture.march_r : &texture.march_random_fract,
                                         root + "preferred_orientation[" + std::to_string(row) + "]." + rest};
            }
        }
    }
    return std::nullopt;
}

// A structural label of a project of several structures: `<structure>.<label>`.
std::optional<ResolvedParameter> resolve_prefixed_structural(Project& project, const std::string& label) {
    const auto split = split_structure(project, label);
    if (!split) {
        return std::nullopt;
    }
    return resolve_structural_label(*split->first, split->second, structure_root(project, *split->first));
}
}  // namespace

std::optional<ResolvedParameter> resolve_project_label(Project& project, ExperimentBase& experiment,
                                                       const std::string& label) {
    if (auto phase = resolve_phase_label(project, experiment, "experiment.", label)) {
        return phase;
    }
    if (auto structural = resolve_prefixed_structural(project, label)) {
        return structural;
    }
    if (project.structures.size() > 1) {
        // Several structures: a structural label carries its structure's prefix (above); an
        // unprefixed one is the bank's own instrument label or nothing, never structure 0's.
        return resolve_instrument_label(experiment, label, "experiment.");
    }
    return resolve_label(project.structure(), experiment, label);
}

std::optional<ResolvedParameter> resolve_joint_project_label(Project& project, const std::string& label) {
    if (project.structures.size() > 1) {
        // A bank's own label `<bank>.<rest>`, the longest bank name first.
        std::vector<ExperimentBase*> banks;
        for (const auto& item : project.experiments) {
            banks.push_back(item.get());
        }
        std::sort(banks.begin(), banks.end(),
                  [](const ExperimentBase* a, const ExperimentBase* b) { return a->name.value().size() > b->name.value().size(); });
        for (ExperimentBase* bank : banks) {
            const std::string name = datablock_key(bank->name, "experiment");
            if (label.size() <= name.size() + 1 || label.compare(0, name.size(), name) != 0 || label[name.size()] != '.') {
                continue;
            }
            const std::string rest = label.substr(name.size() + 1);
            const std::string root = "experiments[" + bank->name.value() + "].";
            if (auto phase = resolve_phase_label(project, *bank, root, rest)) {
                return phase;
            }
            if (auto instrument = resolve_instrument_label(*bank, rest, root)) {
                return instrument;
            }
        }
        if (auto structural = resolve_prefixed_structural(project, label)) {
            return structural;
        }
        // One bank: crysta emits its instrument labels unprefixed. Anything else names no
        // parameter here, never the first structure's.
        if (project.experiments.size() == 1) {
            ExperimentBase& bank = *project.experiments[0];
            return resolve_instrument_label(bank, label, "experiments[" + bank.name.value() + "].");
        }
        return std::nullopt;
    }
    return resolve_joint_label(project.structure(), project.experiments, label);
}

// Translate a crysta free_from_model label (residual.cpp grammar) into the edi model parameter +
// its edi-owned path. Returns std::nullopt for a label with no edi field — the caller fails closed
// (a total translation is required before any write-back). Site coordinates/ADP/occupancy resolve
// by the site's edi label (stable across model edits), not list position.
//
// This is the SINGLE-BANK seam: crysta emits instrument labels unprefixed here. The joint seam is
// resolve_joint_label below; the two share the label tables but never each other's grammar.
std::optional<ResolvedParameter> resolve_label(Structure& structure, ExperimentBase& experiment,
                                                const std::string& label) {
    if (auto instrument = resolve_instrument_label(experiment, label, "experiment.")) {
        return instrument;
    }
    return resolve_structural_label(structure, label);
}

// Translate a JOINT crysta label. The label grammar crysta emits is a property of the PROJECT
// SIZE (residual.cpp `free_from_model`): with
// `experiments.size() > 1` every per-bank instrument parameter is namespaced `<bank-name>.<field>`
// (`append_instrument_free`) and the shared structural block is emitted unprefixed exactly once;
// a ONE-experiment project always gets the single-file UNPREFIXED instrument labels instead —
// whatever entry point built it. This resolver mirrors that dispatch exactly, in three stages:
//
//  1. LONGEST-MATCH bank prefix with validation backtracking (the multi-bank grammar). Every bank
//     name that prefixes the label followed by `.` is tried, longest first, and the remainder must
//     resolve as an INSTRUMENT label; otherwise the next-longest candidate is tried. Longest-match
//     (rather than splitting at the first `.`) is what makes the mapping total: crysta forms
//     labels as `name + "." + field`, so some candidate always reproduces the true split even when
//     one bank name prefixes another.
//  2. ONE-BANK projects only: an unprefixed label is tried as that single bank's instrument label
//     (kind-dispatched as everywhere) — the grammar crysta actually emits for that size, not a
//     fallback past a failed prefix match. Unambiguous by construction (there is exactly one
//     bank), and the resolved path keeps the bank-named joint key grammar
//     (`experiments[<bank>].<field>`), so the result shape does not depend on bank count.
//  3. Otherwise the label must be shared structural.
//
// Bank and site namespaces cannot be confused even if a bank were named after a site: their field
// sets are disjoint (`scale/offset/.../abscor1` vs `x/y/z/Biso/occ`), so a site label falls through
// stage 1 by construction, and stage 2's instrument tables cannot claim a `<site>.<field>` label
// (every entry is dot-free). `fit_joint` additionally rejects such a project outright, so the
// ambiguity is unrepresentable rather than merely resolvable. On a MULTI-bank project there is
// still no bank-0 fallback: an unprefixed instrument label names no bank there, resolves to
// nullopt, and the caller fails closed.
std::optional<ResolvedParameter> resolve_joint_label(Structure& structure,
                                                     ItemVec<BraggPdExperiment>& experiments,
                                                     const std::string& label) {
    std::vector<std::size_t> candidates;
    for (std::size_t bank = 0; bank < experiments.size(); ++bank) {
        const std::string& name = experiments[bank]->name;
        if (!name.empty() && label.size() > name.size() + 1 && label.compare(0, name.size(), name) == 0
            && label[name.size()] == '.') {
            candidates.push_back(bank);
        }
    }
    std::sort(candidates.begin(), candidates.end(),
              [&experiments](std::size_t left, std::size_t right) {
                  return experiments[left]->name.size() > experiments[right]->name.size();
              });
    for (const std::size_t bank : candidates) {
        ExperimentBase& experiment = *experiments[bank];
        const std::string field = label.substr(experiment.name.size() + 1);
        if (auto resolved = resolve_instrument_label(
                experiment, field, "experiments[" + experiment.name + "].")) {
            return resolved;
        }
    }
    // ONE-BANK layout: crysta's free_from_model uses the joint (prefixed) grammar only for
    // experiments.size() > 1 — a one-experiment project always emits the single-file UNPREFIXED
    // instrument labels (residual.cpp free_from_model), whatever entry point built it. Mirror
    // that dispatch exactly, for both kinds: with one bank an unprefixed instrument label is
    // unambiguous, and the result path stays bank-named (`experiments[<bank>].<field>`) so the
    // joint key grammar is unchanged. Before this, a one-bank fit_joint died at write-back on
    // 'offset'/'zero' for TOF and CW alike — the pre-existing half of the fact-5 label gap.
    if (experiments.size() == 1) {
        if (auto resolved = resolve_instrument_label(
                *experiments[0], label, "experiments[" + experiments[0]->name + "].")) {
            return resolved;
        }
    }
    return resolve_structural_label(structure, label);
}

}  // namespace edi::detail

namespace edi {

// The app's parameter rows. Each path is the one the label resolvers above give the field — the
// key a fit result carries — and only a field no fit label reaches (the TOF bank angle, the second
// ABSCOR coefficient, a texture row after the first) is spelled here, in the same
// `<root><category>.<field>` shape.
std::vector<ParameterEntry> parameter_entries(Project& project) {
    std::vector<ParameterEntry> entries;
    const auto path_of = [](const std::optional<detail::ResolvedParameter>& resolved,
                            const Parameter* field, const std::string& spelled) {
        return resolved.has_value() && resolved->target == field ? resolved->path : spelled;
    };
    for (const auto& structure : project.structures) {
        for (const Category& category : structure_categories(*structure)) {
            for (std::size_t i = 0; i < category.fields.size(); ++i) {
                const CategoryField& field = category.fields[i];
                ParameterEntry entry{field.parameter, "", "structure", structure->name, category.id, "", field.name,
                                     field.refinable};
                const std::string root = detail::structure_root(project, *structure);
                if (category.id == "atom_site") {
                    entry.row_label = structure->atom_sites[i / 5]->id;
                    entry.path = path_of(
                        detail::resolve_structural_label(*structure, entry.row_label + "." + field.name, root),
                        field.parameter, root + "atom_sites[" + entry.row_label + "]." + field.name);
                } else {
                    entry.path = path_of(
                        detail::resolve_structural_label(*structure, category.id + "_" + field.name, root),
                        field.parameter, root + category.id + "." + field.name);
                }
                entries.push_back(entry);
            }
        }
    }
    const bool joint = project.experiments.size() > 1;
    for (const auto& experiment : project.experiments) {
        const std::string prefix = joint ? "experiments[" + experiment->name + "]." : std::string("experiment.");
        for (const Category& category : experiment_categories(*experiment)) {
            std::vector<CategoryField> fields = category.fields;
            fields.insert(fields.end(), category.asymmetry.begin(), category.asymmetry.end());
            for (std::size_t i = 0; i < fields.size(); ++i) {
                const CategoryField& field = fields[i];
                ParameterEntry entry{field.parameter, "", "experiment", experiment->name, category.id, "", field.name,
                                     field.refinable};
                std::string label = field.name;
                std::string spelled = prefix + category.id + "." + field.name;
                if (category.id == "background") {
                    entry.row_label = std::to_string(i);
                    label = "background[" + entry.row_label + "]";
                    spelled = prefix + "background[" + entry.row_label + "]." + field.name;
                } else if (category.id == "preferred_orientation") {
                    entry.row_label = std::to_string(i / 2);
                    spelled = prefix + "preferred_orientation[" + entry.row_label + "]." + field.name;
                } else if (category.id == "linked_structure") {
                    // A loop category as the two above: its one field per row is that row's scale (the
                    // app names a loop row's parameter by its row, edi ADR-0017 §8). In a project of
                    // several structures each row, and its path, is named by its structure.
                    label = "scale";
                    if (project.structures.size() > 1) {
                        entry.row_label = experiment->linked_structures[i]->structure_id.value();
                        entry.path = prefix + "linked_structures[" + entry.row_label + "].scale";
                        entries.push_back(entry);
                        continue;
                    }
                    entry.row_label = std::to_string(i);
                }
                entry.path = path_of(detail::resolve_instrument_label(*experiment, label, prefix), field.parameter,
                                     spelled);
                entries.push_back(entry);
            }
        }
    }
    return entries;
}

bool copy_parameter_states(Project& to, Project& from) {
    const std::vector<ParameterEntry> targets = parameter_entries(to);
    const std::vector<ParameterEntry> sources = parameter_entries(from);
    if (targets.size() != sources.size()) {
        return false;
    }
    for (std::size_t i = 0; i < targets.size(); ++i) {
        if (targets[i].path != sources[i].path || targets[i].parameter == nullptr || sources[i].parameter == nullptr) {
            return false;
        }
    }
    for (std::size_t i = 0; i < targets.size(); ++i) {
        Parameter& target = *targets[i].parameter;
        const Parameter& source = *sources[i].parameter;
        if (target.value.get() != source.value.get()) {
            target.value = source.value.get();
            target.epoch = detail::Epoch();
        }
        if (target.uncertainty.get() != source.uncertainty.get()) {
            target.uncertainty = source.uncertainty.get();
        }
        if (target.start_value.get() != source.start_value.get()) {
            target.start_value = source.start_value.get();
        }
        if (target.start_uncertainty.get() != source.start_uncertainty.get()) {
            target.start_uncertainty = source.start_uncertainty.get();
        }
    }
    return true;
}

}  // namespace edi
