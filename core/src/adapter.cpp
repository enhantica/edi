// SPDX-License-Identifier: BSD-3-Clause
#include <algorithm>
#include <array>
#include <cctype>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <locale>
#include <memory>
#include <sstream>
#include <limits>
#include <cmath>
#include <map>
#include <optional>
#include <ranges>
#include <set>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "edi/calculation.hpp"
#include "adapter_test_access.hpp"  // edi::detail conversion seam (core/src only; test-only, not installed)
#include "canonical_encoding.hpp"  // edi-only logic: core/src-private, never installed
#include "identity_bridge.hpp"  // The loader's reach into crysta's identity rules
#include "crysta/analysis.hpp"
#include "crysta/cell_metric.hpp"
#include "crysta/cell_symmetry.hpp"
#include "crysta/descent.hpp"
#include "crysta/experiment_builder.hpp"
#include "crysta/fit.hpp"
#include "crysta/fit_report.hpp"
#include "crysta/identity.hpp"
#include "crysta/model.hpp"
#include "crysta/parameter.hpp"
#include "crysta/partype.hpp"
#include "crysta/pattern.hpp"
#include "crysta/peak.hpp"
#include "crysta/recompute.hpp"
#include "crysta/residual.hpp"
#include "crysta/scattering.hpp"
#include "crysta/structure_geometry.hpp"
#include "crysta/symmetry.hpp"
#include "crysta/threading.hpp"
#include "crysta/tokens.hpp"
#include "edi/categories.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/symmetry.hpp"
#include "edi/threading.hpp"
#include "edi/validation.hpp"
#include "parameter_paths.hpp"
#include "fit_policy.hpp"

// The crysta adapter (ADR-0003): the ONLY edi translation unit that touches the engine, through its
// public API only. Maps the edi model -> crysta model via the public constructors + the public
// TofJorgensenExperiment builder, then calls the public compute_pattern. No engine physics lives here
// (ADR-0009); crysta owns the forward model. The edi->crysta cell/site/experiment conversions are
// defined in `edi::detail` (declared in adapter_test_access.hpp) so a test can inspect them without
// exposing engine storage order in edi's public API.
//
// The logic that operates on edi VALUE TYPES only — the identity-path grammar and label
// resolution (parameter_paths.cpp), the canonical source encoding (canonical_encoding.cpp), the
// boundary checks, bounds, write-back and one-call data sourcing (fit_policy.cpp) — lives on
// edi's side of the ADR-0003 line, where it is unit-testable without the engine. What remains
// here is exactly what must hold a crysta:: type.

namespace edi {
namespace {

crysta::Parameter param(const Parameter& p, const crysta::ParameterType& type, const char* name) {
    crysta::Parameter built(p.value, type, crysta::ParameterLabel(name), p.free, std::nullopt,
                            p.uncertainty);
    built.set_fit_start(p.start_value, p.start_uncertainty);
    return built;
}

crysta::ParameterState state(const Parameter& p) {
    return {p.value, p.free, p.uncertainty, p.start_value, p.start_uncertainty};
}

// Resolve the model's space group through crysta's resolver — two-path selection: an optional
// coordinate-system code selects the exact (name, code) setting; absent (empty) keeps the name-only
// path (ambiguous names keep crysta's candidate-naming error). Every fail-closed decision —
// mismatch, unknown code, no-code ambiguity — stays in crysta's resolver; edi re-implements none of
// it.
//
// The choice between the two paths is crysta's own rule too (crysta::space_group_from_file,
// which its loader also calls). edi's model spells an undeclared code as the empty string, so
// that is the absent code here.
crysta::SpaceGroup resolve_group(const Structure& s) {
    const std::string& code = s.space_group.coord_system_code;
    return crysta::space_group_from_file(
        s.space_group.name_h_m, code.empty() ? std::nullopt : std::optional<std::string>(code));
}

// Every vocabulary token crosses into crysta through crysta's own converter. edi holds the FILE's
// spelling; crysta's table maps it to the model token and refuses a spelling the experiment's beam
// mode does not admit. No model token is built on this side: copying a file spelling straight into
// crysta's model is how a TOF
// `cylinder` reached the engine unconverted and switched reflection folding off, unseen.
std::string crossed(crysta::TokenField field, const crysta::ExperimentBase& built,
                    const std::string& spelling) {
    return crysta::model_token_from_file(field, built.kind, spelling);
}

// The symmetry-completed six cell values. crysta's own per-setting freedom map
// (crysta::cell_freedom) is the single source of the tie: a dependent parameter takes its
// independent leader's value and a symmetry-fixed angle takes its constant, so a cubic cell written
// as `a` alone computes with b = c = a rather than with the default 1.0 Å — the silent-wrong-answer
// path the crysta 501d49ea bump would otherwise open. This is exactly the tie crysta itself applies
// on its refinement path, sourced from the same map, so the forward and refinement cells cannot
// disagree and edi acquires no crystallographic knowledge of its own (ADR-0009).
std::array<double, 6> completed_cell_values(const Cell& cell, const crysta::CellFreedom& freedom) {
    const Parameter* const raw[6] = {&cell.length_a,     &cell.length_b,    &cell.length_c,
                                     &cell.angle_alpha, &cell.angle_beta, &cell.angle_gamma};
    std::array<double, 6> values{};
    for (std::size_t i = 0; i < 6; ++i) {
        const int leader = freedom.follows[i];
        values[i] = leader == crysta::CellFreedom::kFixed
                        ? freedom.fixed[i]
                        : raw[static_cast<std::size_t>(leader)]->value;
    }
    return values;
}

}  // namespace

namespace {

// The engine cell the boundary contract hands crysta: the user's cell parameters (esd + free flags
// verbatim — a free flag on a dependent parameter stays the user's claim, refused by crysta's own
// free-set builder with its own structured error) with the VALUES symmetry-completed per the map
// above. Sits beside — never inside — detail::to_crysta_cell: that seam is the space-group-free raw
// conversion the adapter probe drives with non-resolvable models, and completion requires a
// resolved setting by definition.
crysta::Cell to_completed_crysta_cell(const Cell& c, const crysta::CellFreedom& freedom) {
    const std::array<double, 6> values = completed_cell_values(c, freedom);
    const Parameter* const raw[6] = {&c.length_a, &c.length_b, &c.length_c, &c.angle_alpha, &c.angle_beta, &c.angle_gamma};
    const char* const names[6] = {"a", "b", "c", "alpha", "beta", "gamma"};
    std::vector<crysta::Parameter> cell_params;
    cell_params.reserve(6);
    for (std::size_t i = 0; i < 6; ++i) {
        Parameter completed = *raw[i];
        completed.value = values[i];
        cell_params.push_back(param(completed, crysta::CELL, names[i]));
    }
    return crysta::Cell(std::move(cell_params));
}

// Full structure for calculate(): needs the space group resolved (crysta MVP1: I 2₁3 only). Kept
// internal — the probe inspects cell + atom sites separately (via edi::detail), so it never needs a
// resolvable space group and can use a non-cubic conversion model. The cell crysta computes with is
// the symmetry-COMPLETED cell (fork 2's contract, above): this is the single edi→engine conversion
// choke point, so every consumer — calculate, fit, fit_joint —
// crosses the boundary with a cell that satisfies the model's own space-group ties.
crysta::Structure to_crysta_structure(const Structure& s) {
    crysta::SpaceGroup space_group = resolve_group(s);
    const crysta::CellFreedom freedom = crysta::cell_freedom(space_group);
    // Built in place: a crysta structure never moves.
    return crysta::Structure(to_completed_crysta_cell(s.cell, freedom), std::move(space_group),
                             detail::to_crysta_atom_sites(s.atom_sites),
                             [&s](crysta::Structure& built) {
                                 // Crysta proves a texture row's key against this identity
                                 built.name = s.name;
                                 // The bond cutoffs cross presence-faithfully, so crysta's
                                 // writer saves a declared `_geom` and no other.
                                 built.geom.min_bond_distance_cutoff =
                                     s.geom.min_bond_distance_cutoff.get();
                                 built.geom.bond_distance_inc = s.geom.bond_distance_inc.get();
                             });
}

}  // namespace

// ADR-0019: the freedom symmetry leaves, reported per parameter. The cell rows read crysta's
// cell freedom; the coordinate rows read its special positions, with the representative rule: the first axis that names a
// basic carries it, and a later axis of the same basic follows that one. A part crysta cannot
// resolve is reported independent (symmetry.hpp says why).
std::vector<ParameterTie> structure_ties(const Structure& s) {
    std::vector<ParameterTie> ties;
    ties.reserve(6 + 3 * s.atom_sites.size());
    const Parameter* const cell[6] = {&s.cell.length_a,    &s.cell.length_b,   &s.cell.length_c,
                                      &s.cell.angle_alpha, &s.cell.angle_beta, &s.cell.angle_gamma};
    std::optional<crysta::CellFreedom> freedom;
    try {
        freedom = crysta::cell_freedom(resolve_group(s));
    } catch (const std::exception&) {
        freedom.reset();
    }
    for (std::size_t i = 0; i < 6; ++i) {
        ParameterTie tie{cell[i]};
        if (freedom.has_value() && freedom->is_fixed(i)) {
            tie.kind = TieKind::Fixed;
            tie.fixed_value = freedom->fixed[i];
        } else if (freedom.has_value() && !freedom->is_independent(i)) {
            tie.kind = TieKind::Follows;
            tie.leader = cell[static_cast<std::size_t>(freedom->follows[i])];
        }
        ties.push_back(tie);
    }
    const std::size_t cell_rows = ties.size();
    try {
        const crysta::Structure engine = to_crysta_structure(s);
        const crysta::PositionalConstraints constraints = engine.positional_constraints();
        const auto& positions = constraints.sites();
        for (std::size_t i = 0; i < s.atom_sites.size(); ++i) {
            const crysta::SpecialPosition& position = positions.at(i).second;
            const Parameter* const fract[3] = {&s.atom_sites[i]->fract_x, &s.atom_sites[i]->fract_y,
                                               &s.atom_sites[i]->fract_z};
            // With every basic at zero a fixed axis reads its constant.
            const auto [cx, cy, cz] = position.evaluate(std::vector<double>(position.n_basic(), 0.0));
            const double constants[3] = {cx, cy, cz};
            const Parameter* representative[3] = {nullptr, nullptr, nullptr};
            for (std::size_t axis = 0; axis < 3; ++axis) {
                ParameterTie tie{fract[axis]};
                if (!position.axis_is_basic(axis)) {
                    tie.kind = TieKind::Fixed;
                    tie.fixed_value = constants[axis];
                } else if (const Parameter*& first = representative[position.axis_basic_index(axis)];
                           first == nullptr) {
                    first = fract[axis];
                } else {
                    tie.kind = TieKind::Follows;
                    tie.leader = first;
                }
                ties.push_back(tie);
            }
        }
    } catch (const std::exception&) {
        ties.resize(cell_rows);
        for (const auto& site : s.atom_sites) {
            for (const Parameter* axis : {&site->fract_x, &site->fract_y, &site->fract_z}) {
                ties.push_back({axis});
            }
        }
    }
    return ties;
}

// Review-9 F1 (the lossless prior-state property, edi's landing half): write_back snapshots
// and overwrites the RESULT-LABEL target — the representative — but the basic's snapshot must
// ride an axis whose own prior state the restore may legitimately write back (crysta
// b96a0b1b's rule: the representative when IT is free, else the first free axis), the fitted
// e.s.d. belongs to the declared free axes only, and a fixed representative keeps its own
// uncertainty presence. Runs between write_back and the completions, while every
// non-representative axis still holds its pre-fit state, so the hand-off is lossless.
void rebalance_positional_fit_state(Structure& s) {
    const crysta::Structure engine = to_crysta_structure(s);
    const crysta::PositionalConstraints constraints = engine.positional_constraints();
    const auto& positions = constraints.sites();
    for (std::size_t i = 0; i < s.atom_sites.size(); ++i) {
        const crysta::SpecialPosition& position = positions[i].second;
        Parameter* const fract[3] = {&s.atom_sites[i]->fract_x, &s.atom_sites[i]->fract_y,
                                     &s.atom_sites[i]->fract_z};
        bool seen[3] = {false, false, false};
        int representative[3] = {-1, -1, -1};
        int designated[3] = {-1, -1, -1};
        for (std::size_t axis = 0; axis < 3; ++axis) {
            if (!position.axis_is_basic(axis)) {
                continue;
            }
            const std::size_t local = position.axis_basic_index(axis);
            const bool is_representative = !seen[local];
            if (is_representative) {
                seen[local] = true;
                representative[local] = static_cast<int>(axis);
            }
            if (fract[axis]->free && (is_representative || designated[local] < 0)) {
                designated[local] = static_cast<int>(axis);
            }
        }
        for (std::size_t local = 0; local < 3; ++local) {
            const int rep = representative[local];
            if (rep < 0 || !fract[rep]->start_value.has_value() || designated[local] < 0) {
                continue;  // not a fit target this landing (or no declared free axis)
            }
            const std::optional<double> fitted_esd =
                fract[static_cast<std::size_t>(rep)]->uncertainty;
            for (std::size_t axis = 0; axis < 3; ++axis) {
                if (!position.axis_is_basic(axis) ||
                    position.axis_basic_index(axis) != local) {
                    continue;
                }
                Parameter& p = *fract[axis];
                if (static_cast<int>(axis) == designated[local]) {
                    if (static_cast<int>(axis) != rep) {
                        // Its own prior state is still intact — snapshot it, then land.
                        p.start_value = p.value;
                        p.start_uncertainty = p.uncertainty;
                        p.uncertainty = fitted_esd;
                    }
                    // designated == representative: write_back already did both.
                } else if (p.free) {
                    // Review-10 F1 (edi follows a CORRECTED crysta, never a known crysta
                    // defect for byte parity): the companion's PRIOR goes to the snapshot
                    // payload and the FITTED e.s.d. lands in its current field, so the model
                    // answers "what did the fit produce" on every declared-free axis (P2) and
                    // agrees with crysta's corrected landing. Until PR4 merges, the float's
                    // main-built writer persists no start_tied payload — the producer-first
                    // phasing exception, named in the ledger, never papered over.
                    p.start_uncertainty = p.uncertainty;
                    p.uncertainty = fitted_esd;
                } else if (static_cast<int>(axis) == rep) {
                    // Fixed representative: the landing stomped its uncertainty — put its own
                    // prior presence back and hand the basic's snapshot to the designated
                    // axis (one snapshot per basic; its value re-derives from the basic).
                    p.uncertainty = p.start_uncertainty;
                    p.start_value.reset();
                    p.start_uncertainty.reset();
                }
            }
        }
    }
}

// Review-9 F1 (edi's undo half — the mirror of crysta's restored-set pass): the snapshot may
// ride a non-representative free axis, so a restored axis derives its basic back onto the
// representative sign-correctly before values complete; a free tied axis that did not restore
// its OWN snapshot takes the restored axis's uncertainty (after a load only the designated
// row exists); a fixed axis's uncertainty is never touched.
void restore_positional_dependents(Structure& s, const std::set<const Parameter*>& restored) {
    const crysta::Structure engine = to_crysta_structure(s);
    const crysta::PositionalConstraints constraints = engine.positional_constraints();
    const auto& positions = constraints.sites();
    for (std::size_t i = 0; i < s.atom_sites.size(); ++i) {
        const crysta::SpecialPosition& position = positions[i].second;
        Parameter* const fract[3] = {&s.atom_sites[i]->fract_x, &s.atom_sites[i]->fract_y,
                                     &s.atom_sites[i]->fract_z};
        bool seen[3] = {false, false, false};
        int representative[3] = {-1, -1, -1};
        int snapshot[3] = {-1, -1, -1};
        for (std::size_t axis = 0; axis < 3; ++axis) {
            if (!position.axis_is_basic(axis)) {
                continue;
            }
            const std::size_t local = position.axis_basic_index(axis);
            if (!seen[local]) {
                seen[local] = true;
                representative[local] = static_cast<int>(axis);
            }
            if (restored.count(fract[axis]) != 0) {
                snapshot[local] = static_cast<int>(axis);
            }
        }
        for (std::size_t local = 0; local < 3; ++local) {
            if (snapshot[local] < 0) {
                continue;
            }
            const auto snap_axis = static_cast<std::size_t>(snapshot[local]);
            const Parameter& snap = *fract[snap_axis];
            if (representative[local] != snapshot[local]) {
                // The ±1 factors relating each coordinate to this basic, recovered through the
                // PUBLIC evaluate (edi builds against crysta main, which does not yet export
                // axis_sign): with a unit basic, a symbol axis of this local reads exactly its
                // sign. coordinate = sign * basic, and sign is ±1, so basic = coordinate * sign.
                std::vector<double> unit(position.n_basic(), 0.0);
                unit[local] = 1.0;
                const auto [ux, uy, uz] = position.evaluate(unit);
                const double axis_unit[3] = {ux, uy, uz};
                const double basic = snap.value * axis_unit[snap_axis];
                const auto rep_axis = static_cast<std::size_t>(representative[local]);
                fract[rep_axis]->value = basic * axis_unit[rep_axis];
            }
            for (std::size_t axis = 0; axis < 3; ++axis) {
                if (axis == snap_axis || !position.axis_is_basic(axis) ||
                    position.axis_basic_index(axis) != local || !fract[axis]->free ||
                    restored.count(fract[axis]) != 0) {
                    continue;
                }
                // Review-9: each companion restores its OWN captured prior (seeded by the
                // landing in memory and by the loader after a load) — absent and engaged
                // zero stay distinct per axis; the designated value is never spread.
                fract[axis]->uncertainty = fract[axis]->start_uncertainty;
                fract[axis]->start_uncertainty.reset();
            }
        }
    }
}

void seed_positional_start_companions(
    Project& project,
    const std::vector<std::pair<Parameter*, std::optional<std::string>>>& rows,
    const std::string& where) {
    if (rows.empty()) {
        return;
    }
    // Every structure's tied coordinates: where each row's parameter sits (structure, site, axis).
    struct Home {
        std::size_t structure;
        std::size_t site;
        std::size_t axis;
    };
    std::vector<crysta::PositionalConstraints> constraints;
    constraints.reserve(project.structures.size());
    std::map<const Parameter*, Home> homes;
    for (std::size_t k = 0; k < project.structures.size(); ++k) {
        Structure& s = *project.structures[k];
        constraints.push_back(to_crysta_structure(s).positional_constraints());
        const auto& positions = constraints.back().sites();
        for (std::size_t i = 0; i < s.atom_sites.size(); ++i) {
            const crysta::SpecialPosition& position = positions[i].second;
            Parameter* const fract[3] = {&s.atom_sites[i]->fract_x, &s.atom_sites[i]->fract_y,
                                         &s.atom_sites[i]->fract_z};
            for (std::size_t axis = 0; axis < 3; ++axis) {
                if (position.axis_is_basic(axis)) {
                    homes.emplace(fract[axis], Home{k, i, axis});
                }
            }
        }
    }
    const auto parse_esd = [&where](const std::string& text) -> std::optional<double> {
        if (text == ".") {
            return std::nullopt;
        }
        // Review-10 F2: the loader's own finite, full-token, classic-locale boundary — a
        // non-finite or partial token, or a locale-dependent spelling, refuses exactly as it
        // would anywhere else in the format.
        return parse_edi_double(text, where + " (_fit_parameter.start_tied)");
    };
    for (const auto& [parameter, token] : rows) {
        const auto home = homes.find(parameter);
        if (home == homes.end()) {
            if (token.has_value() && *token != ".") {
                throw IoError(
                    "analysis.edi: _fit_parameter.start_tied declared on a row that is not a "
                    "tied coordinate: " +
                    where);
            }
            continue;
        }
        Structure& s = *project.structures[home->second.structure];
        const std::size_t site_index = home->second.site;
        const std::size_t row_axis = home->second.axis;
        const crysta::SpecialPosition& position = constraints[home->second.structure].sites()[site_index].second;
        const std::size_t local = position.axis_basic_index(row_axis);
        Parameter* const fract[3] = {&s.atom_sites[site_index]->fract_x,
                                     &s.atom_sites[site_index]->fract_y,
                                     &s.atom_sites[site_index]->fract_z};
        std::map<std::size_t, std::optional<double>> declared;
        const bool token_declared = token.has_value() && *token != ".";
        if (token_declared) {
            const std::string& text = *token;
            std::size_t start = 0;
            while (start <= text.size()) {
                const std::size_t end = text.find(';', start);
                const std::string pair = text.substr(
                    start, end == std::string::npos ? std::string::npos : end - start);
                if (pair.size() < 3 || pair[1] != '=' ||
                    (pair[0] != 'x' && pair[0] != 'y' && pair[0] != 'z')) {
                    throw IoError("analysis.edi: malformed _fit_parameter.start_tied pair '" +
                                  pair + "': " + where);
                }
                if (!declared
                         .emplace(static_cast<std::size_t>(pair[0] - 'x'),
                                  parse_esd(pair.substr(2)))
                         .second) {
                    throw IoError(
                        "analysis.edi: _fit_parameter.start_tied declares an axis more than "
                        "once: " +
                        where);
                }
                if (end == std::string::npos) {
                    break;
                }
                start = end + 1;
            }
        }
        std::size_t consumed = 0;
        for (std::size_t axis = 0; axis < 3; ++axis) {
            if (axis == row_axis || !position.axis_is_basic(axis) ||
                position.axis_basic_index(axis) != local || !fract[axis]->free) {
                continue;
            }
            if (token_declared) {
                const auto found = declared.find(axis);
                if (found == declared.end()) {
                    throw IoError(
                        "analysis.edi: _fit_parameter.start_tied misses a free tied companion "
                        "axis: " +
                        where);
                }
                fract[axis]->start_uncertainty = found->second;
                ++consumed;
            } else if (token.has_value()) {
                throw IoError(
                    "analysis.edi: _fit_parameter.start_tied declares no companions but the "
                    "model holds a free tied companion axis: " +
                    where);
            } else {
                fract[axis]->start_uncertainty = fract[axis]->uncertainty;
            }
        }
        if (token_declared && consumed != declared.size()) {
            throw IoError(
                "analysis.edi: _fit_parameter.start_tied declares an axis that is not a free "
                "tied companion: " +
                where);
        }
    }
}

namespace detail {
// The conversion for the project's relations, which also admits a bank with no link.
crysta::BraggPdExperiment to_crysta_experiment(const ExperimentBase& e, bool for_relations);
}  // namespace detail

namespace {

// Every structure of the model as crysta's, in order: name and declared scattering lengths included.
// Each is built in place (a crysta structure never moves) and the list copied once, at its size.
std::vector<crysta::Structure> to_crysta_structures(const Project& model) {
    std::vector<std::unique_ptr<crysta::Structure>> built;
    built.reserve(model.structures.size());
    for (const auto& structure : model.structures) {
        // NOLINTNEXTLINE(modernize-make-unique) — make_unique would move the built prvalue
        built.emplace_back(new crysta::Structure(to_crysta_structure(*structure)));
        built.back()->scattering_lengths_fm = structure->scattering_lengths_fm;
    }
    const auto values = std::views::transform(
        built, [](const std::unique_ptr<crysta::Structure>& structure) -> const crysta::Structure& {
            return *structure;
        });
    return std::vector<crysta::Structure>(values.begin(), values.end());
}

crysta::Project build_crysta_project(const Structure& structure, const ExperimentBase& experiment) {
    return crysta::Project(to_crysta_structure(structure), detail::to_crysta_experiment(experiment));
}


crysta::NeutronScattering select_scattering(const Structure& structure) {
    // Honour the model's element->b_c map when supplied; fall back to crysta's default neutron table.
    return structure.scattering_lengths_fm.empty()
               ? crysta::load_neutron_scattering()
               : crysta::NeutronScattering(structure.scattering_lengths_fm);
}

// Make a converted experiment FIT-ready. Historically the forward builder emitted the 3-term
// calibration and crysta's fit path read instrument[3] — the reciprocal term — so this padded a
// fixed 0.0 there. Since crysta's builder stamps the 4-wide instrument itself, and since edi's
// model CARRIES the reciprocal and the conversion passes it through (`d_to_tof_reciprocal`
// below), so the guard here can no longer fire; it stays as a fail-safe for a caller that hands
// in a hand-built 3-term experiment.
void make_fit_ready(crysta::ExperimentBase& built) {
    // The reciprocal pad is TOF-only by construction: the CW instrument layout is with no
    // reciprocal slot — crysta's CW free_from_model reads exactly those, so a CW experiment
    // is already fit-ready as converted and padding it would corrupt the layout.
    if (built.kind != crysta::BeamModeEnum::TimeOfFlight) {
        return;
    }
    if (built.instrument.size() < 4) {
        built.instrument.emplace_back(0.0, crysta::CALIBRATION,
                                      crysta::ParameterLabel("calib_d_to_tof_reciprocal"));
    }
}

// ---------------------------------------------------------------------------------------------
// index helpers — the halves that hold crysta::Parameter pointers (Slot/Index, build_index,
// validate_index, cross_check_free_set) stay in this TU (ADR-0003): no crysta type reaches a
// header, a binding or a host. Their edi-only halves — the peak slot table and the identity-path
// grammar (parameter_paths.cpp), the canonical source encoding (canonical_encoding.cpp) and the
// site-identity check (fit_policy.cpp) — moved out in so they are unit-testable without the
// engine. Since retired the CachedForwardModel, nothing in edi_core calls the three
// crysta-holding helpers; the internal probe still exercises them.
// ---------------------------------------------------------------------------------------------


// One indexed parameter: the engine Parameter a mutation must click, and the edi model Parameter
// that mirrors it. Built together in ONE traversal so the two sides cannot drift.
struct Slot {
    crysta::Parameter* engine;
    Parameter* model;
};
using Index = std::map<std::string, Slot>;

// --- the parameter index ------------------------------------------------------------------------
//
// Maps every edi identity path to (engine Parameter, model Parameter). The path grammar is exactly
// the FitResultBase key grammar, so a FitResultBase key is directly usable as a set() path.
// `cproject` must already be in its FINAL storage: these pointers alias its members.
Index build_index(Project& model, crysta::Project& cproject) {
    Index index;
    crysta::Structure& cstructure = cproject.structure();
    crysta::ExperimentBase& cexperiment = cproject.experiment();

    Cell& cell = model.structure().cell;
    Parameter* const model_cell[6] = {&cell.length_a,     &cell.length_b,    &cell.length_c,
                                      &cell.angle_alpha, &cell.angle_beta, &cell.angle_gamma};
    const char* const cell_names[6] = {"length_a",    "length_b",   "length_c",
                                       "angle_alpha", "angle_beta", "angle_gamma"};
    for (std::size_t i = 0; i < 6; ++i) {
        index.emplace(std::string("structure.cell.") + cell_names[i],
                      Slot{&cstructure.cell.parameters[i], model_cell[i]});
    }

    for (std::size_t site = 0; site < model.structure().atom_sites.size(); ++site) {
        AtomSite& atom = *model.structure().atom_sites[site];
        crysta::AtomSite& catom = cstructure.atom_sites[site];
        const std::string base = "structure.atom_sites[" + atom.id + "].";
        index.emplace(base + "fract_x", Slot{&catom.fract[0], &atom.fract_x});
        index.emplace(base + "fract_y", Slot{&catom.fract[1], &atom.fract_y});
        index.emplace(base + "fract_z", Slot{&catom.fract[2], &atom.fract_z});
        index.emplace(base + "occupancy", Slot{&catom.occupancy, &atom.occupancy});
        index.emplace(base + "adp_iso", Slot{&catom.adp_iso, &atom.adp_iso});
    }

    ExperimentBase& experiment = model.experiment();
    for (std::size_t i = 0; i < detail::kPeakSlots.size(); ++i) {
        index.emplace(std::string("experiment.") + detail::kPeakSlots[i].first,
                      Slot{&cexperiment.peak[i], &detail::kPeakSlots[i].second(experiment)});
    }
    index.emplace("experiment.instrument.calib_d_to_tof_offset",
                  Slot{&cexperiment.instrument[0], &experiment.instrument.calib_d_to_tof_offset});
    index.emplace("experiment.instrument.calib_d_to_tof_linear",
                  Slot{&cexperiment.instrument[1], &experiment.instrument.calib_d_to_tof_linear});
    index.emplace("experiment.instrument.calib_d_to_tof_quadratic",
                  Slot{&cexperiment.instrument[2], &experiment.instrument.calib_d_to_tof_quadratic});
    index.emplace("experiment.instrument.calib_d_to_tof_reciprocal",
                  Slot{&cexperiment.instrument[3], &experiment.instrument.calib_d_to_tof_reciprocal});
    index.emplace("experiment.linked_structure.scale",
                  Slot{&cexperiment.scale(), &experiment.linked_structure().scale});
    for (std::size_t i = 0; i < experiment.background.size(); ++i) {
        index.emplace(
            "experiment.background[" + std::to_string(i) + "].intensity",
            Slot{&cexperiment.background[i].intensity, &experiment.background[i]->intensity});
    }
    for (std::size_t i = 0; i < experiment.background_terms.size(); ++i) {
        index.emplace("experiment.background[" + std::to_string(i) + "].coef",
                      Slot{&cexperiment.background_terms[i].coef, &experiment.background_terms[i]->coef});
    }
    // Presence-tracked: a model that never declared abscor1 has no such path, so a set() on it is an
    // unknown path rather than a silent write to a 0 the model never carried. abscor2 is
    // deliberately never indexed — crysta holds it fixed and freeing it is a hard error there.
    if (experiment.absorption.abscor1 && !cexperiment.absorption.empty()) {
        index.emplace("experiment.absorption.abscor1",
                      Slot{&cexperiment.absorption[0], &*experiment.absorption.abscor1});
    }
    // The CW families carry the single mu_r body at absorption[0] (crysta's cwl layout),
    // refinable exactly as abscor1. The family contract keeps mu_r and the TOF pair mutually
    // exclusive; a hand-built model carrying both fails closed at the injectivity check
    // below rather than silently double-mapping the slot.
    if (experiment.absorption.mu_r && !cexperiment.absorption.empty()) {
        index.emplace("experiment.absorption.mu_r",
                      Slot{&cexperiment.absorption[0], &*experiment.absorption.mu_r});
    }
    // The one preferred-orientation row, crysta's [march_r, march_random_fract] layout.
    if (experiment.preferred_orientation.size() != 0 && cexperiment.texture() != nullptr) {
        PrefOrient& row = *experiment.preferred_orientation[0];
        index.emplace("experiment.preferred_orientation[0].march_r",
                      Slot{cexperiment.texture()->march.data(), &row.march_r});
        index.emplace("experiment.preferred_orientation[0].march_random_fract",
                      Slot{cexperiment.texture()->march.data() + 1, &row.march_random_fract});
    }
    return index;
}

// --- V1: sentinel-injection totality proof -------------------------------------------------------
//
// Proves build_index selects exactly the engine Parameter that received each path's edi value, for
// FIXED parameters as well as free ones: assign every path a distinct sentinel in a throwaway copy,
// rebuild the engine project from it, and require each indexed engine Parameter to carry its own
// path's sentinel. Catches transposition, peak[]/background[] off-by-one, wrong site and wrong
// calibration slot. Then injectivity, then whole-tree completeness.
//
// It runs on a COPY, so the live project's clocks are never polluted; edi builds unbounded
// parameters, so any sentinel is legal, and the probe is never evaluated.
void validate_index(const Project& model, const Index& index, crysta::Project& cproject) {
    std::vector<std::string> paths;
    paths.reserve(index.size());
    for (const auto& entry : index) paths.push_back(entry.first);

    Project probe = model;
    crysta::Project seed = build_crysta_project(probe.structure(), probe.experiment());
    make_fit_ready(seed.experiment());
    Index seed_index = build_index(probe, seed);
    if (seed_index.size() != index.size()) {
        throw std::invalid_argument("edi cached model: index validation failed (unstable index size)");
    }
    for (std::size_t i = 0; i < paths.size(); ++i) {
        const auto it = seed_index.find(paths[i]);
        if (it == seed_index.end()) {
            throw std::invalid_argument("edi cached model: index validation failed (path '" +
                                        paths[i] + "' is not reproducible)");
        }
        it->second.model->value = 1.0e6 + static_cast<double>(i);
    }

    crysta::Project rebuilt = build_crysta_project(probe.structure(), probe.experiment());
    make_fit_ready(rebuilt.experiment());

    // Check THE INDEX UNDER TEST, not a freshly rebuilt one — otherwise the validator would only be
    // confirming build_index against itself and would accept any wrong mapping handed to it.
    //
    // `cproject` and `rebuilt` are built from the same model shape by the same code, so their
    // traversal orders coincide: a POSITION in collect_parameters() names a slot independently of
    // build_index. So map each indexed engine pointer to its position in the live project, and
    // require the same position in the sentinel-laden rebuild to carry that path's sentinel. A
    // transposed index yields a different position and therefore the wrong sentinel.
    const std::vector<crysta::Parameter*> live_slots = cproject.collect_parameters();
    const std::vector<crysta::Parameter*> rebuilt_slots = rebuilt.collect_parameters();
    if (live_slots.size() != rebuilt_slots.size()) {
        throw std::invalid_argument(
            "edi cached model: index validation failed (engine layout is not reproducible)");
    }
    std::map<const crysta::Parameter*, std::size_t> position;
    for (std::size_t i = 0; i < live_slots.size(); ++i) position.emplace(live_slots[i], i);

    // The cell paths' expected sentinels go through the completion contract (fork 2): a dependent
    // cell parameter's engine slot carries its LEADER's sentinel and a symmetry-fixed angle carries
    // its constant, per crysta's own freedom map — so V1 now also proves the completion is applied
    // through that map, not just that the six slots line up.
    const crysta::CellFreedom freedom = crysta::cell_freedom(resolve_group(model.structure()));
    std::map<std::string, double> sentinel_of_path;
    for (std::size_t i = 0; i < paths.size(); ++i) {
        sentinel_of_path.emplace(paths[i], 1.0e6 + static_cast<double>(i));
    }
    for (std::size_t i = 0; i < paths.size(); ++i) {
        const crysta::Parameter* engine = index.at(paths[i]).engine;
        const auto slot = position.find(engine);
        if (slot == position.end()) {
            throw std::invalid_argument(
                "edi cached model: index validation failed — path '" + paths[i] +
                "' addresses a parameter outside this project");
        }
        double expected = 1.0e6 + static_cast<double>(i);
        if (const std::optional<std::size_t> cell_index = detail::cell_path_slot(paths[i])) {
            // A dependent cell slot carries its LEADER's sentinel and a fixed angle its constant,
            // so two dependent (or two fixed) slots are value-indistinguishable and a sentinel
            // check alone would accept their transposition. The cell has what no other block has —
            // a canonical addressable layout (cell.parameters[i], dictionary order) — so the six
            // slots are proven by ADDRESS IDENTITY instead, which detects any cell transposition
            // outright; the value check below then proves the completion put the mapped value there.
            if (engine != &cproject.structure().cell.parameters[*cell_index]) {
                throw std::invalid_argument(
                    "edi cached model: index validation failed — path '" + paths[i] +
                    "' does not address its dictionary-order engine cell slot");
            }
            const int leader = freedom.follows[*cell_index];
            if (leader == crysta::CellFreedom::kFixed) {
                expected = freedom.fixed[*cell_index];
            } else {
                // Checked lookup: an index missing its leader's path must be the structured
                // refusal every other defect here gets, never an uncaught std::out_of_range.
                const std::string leader_path =
                    std::string("structure.cell.") + detail::kCellPathNames[static_cast<std::size_t>(leader)];
                const auto leader_sentinel = sentinel_of_path.find(leader_path);
                if (leader_sentinel == sentinel_of_path.end()) {
                    throw std::invalid_argument(
                        "edi cached model: index validation failed — path '" + paths[i] +
                        "' depends on missing leader path '" + leader_path + "'");
                }
                expected = leader_sentinel->second;
            }
        }
        if (rebuilt_slots[slot->second]->value() != expected) {
            throw std::invalid_argument(
                "edi cached model: index validation failed — path '" + paths[i] +
                "' does not address the engine parameter that carries its value");
        }
    }

    // Injectivity: no two paths may address the same engine parameter.
    std::set<const crysta::Parameter*> engines;
    for (const auto& entry : index) {
        if (!engines.insert(entry.second.engine).second) {
            throw std::invalid_argument("edi cached model: index validation failed — path '" +
                                        entry.first + "' aliases another path's engine parameter");
        }
    }

    // Completeness: every engine parameter reachable in the LIVE project is either indexed or one of
    // the deliberately unmapped slots, asserted by address rather than by count.
    crysta::ExperimentBase& cexperiment = cproject.experiment();
    std::set<const crysta::Parameter*> allowed_unmapped;
    if (cexperiment.absorption.size() > 1) {
        allowed_unmapped.insert(&cexperiment.absorption[1]);  // abscor2: engine-fixed, never indexed
    }
    if (!model.experiment().absorption.abscor1 && !model.experiment().absorption.mu_r &&
        !cexperiment.absorption.empty()) {
        allowed_unmapped.insert(&cexperiment.absorption[0]);  // absent in the model
    }
    for (const crysta::Parameter* parameter : cproject.collect_parameters()) {
        if (engines.count(parameter) != 0 || allowed_unmapped.count(parameter) != 0) continue;
        throw std::invalid_argument(
            "edi cached model: index validation failed — engine parameter '" + parameter->name() +
            "' is reachable in the project but addressed by no identity path");
    }
}

// --- V2: positional-aware free-set cross-check ---------------------------------------------------
//
// Re-proves, against crysta's OWN label emission, that the translation is total and that the index
// addresses the same parameters the engine will refine. Pointer identity is required only when the
// engine supplies a handle: positional basics are emitted with parameter == nullptr because crysta
// refines them through the constraint basis rather than the site Parameter (residual.hpp:51-58,
// residual.cpp:1590-1594). Requiring identity there would reject any model that frees a coordinate —
// which the acceptance model does; V1 already proves those coordinate pointers independently. Takes
// the free set the caller already computed, so it can run BOTH at construction (best effort) and at
// fit() (where a free set is required anyway and the check therefore always applies).
void cross_check_free_set(Project& model, const Index& index,
                          const std::vector<crysta::FreeParameter>& free_set) {
    for (const crysta::FreeParameter& free : free_set) {
        const std::optional<detail::ResolvedParameter> resolved =
            detail::resolve_label(model.structure(), model.experiment(), free.label);
        if (!resolved) {
            throw std::invalid_argument(
                "edi cached model: engine free-set label '" + free.label +
                "' does not resolve to an edi model parameter (unmapped engine label)");
        }
        const auto it = index.find(resolved->path);
        if (it == index.end()) {
            throw std::invalid_argument("edi cached model: engine free-set label '" + free.label +
                                        "' resolves to unindexed path '" + resolved->path + "'");
        }
        if (free.parameter == nullptr) {
            if (free.kind != crysta::FreeKind::POSITIONAL_BASIC || free.basic_index < 0) {
                throw std::invalid_argument(
                    "edi cached model: engine free-set label '" + free.label +
                    "' supplied no parameter handle and is not a positional basic");
            }
            continue;  // refined through the constraint basis; V1 covers the coordinate pointer
        }
        if (it->second.engine != free.parameter) {
            throw std::invalid_argument("edi cached model: engine free-set label '" + free.label +
                                        "' addresses a different parameter than path '" +
                                        resolved->path + "'");
        }
    }
}

// An engine experiment never moves, so a std::vector of them may never grow — libc++ refuses to
// instantiate the relocation (crysta #217's macOS build). Each conversion is built in place on the
// heap, and the engine project's list is copied from them once, at its final size.
using BuiltExperiments = std::vector<std::unique_ptr<crysta::BraggPdExperiment>>;

// `experiment` converted, built in place on the heap and appended to `built`.
crysta::BraggPdExperiment& build_on_heap(BuiltExperiments& built, const ExperimentBase& experiment,
                                         bool for_relations = false) {
    // NOLINTNEXTLINE(modernize-make-unique) — make_unique would move the converted prvalue
    std::unique_ptr<crysta::BraggPdExperiment> owned(
        new crysta::BraggPdExperiment(detail::to_crysta_experiment(experiment, for_relations)));
    built.push_back(std::move(owned));
    return *built.back();
}

std::vector<crysta::BraggPdExperiment> experiment_list(const BuiltExperiments& built) {
    const auto values = std::views::transform(
        built, [](const std::unique_ptr<crysta::BraggPdExperiment>& experiment)
                   -> const crysta::BraggPdExperiment& { return *experiment; });
    return std::vector<crysta::BraggPdExperiment>(values.begin(), values.end());
}

}  // namespace

// The declared `_sequential_fit.*` block crosses the boundary field-for-field — the two structs
// mirror each other by construction, and the loop/CSV consumers are crysta's alone. Filled in
// place: the engine's block holds a keyed collection, so it never moves.
void fill_crysta_sequential(const SequentialFitConfig& config,
                            crysta::SequentialFitConfig& converted) {
    converted.data_dir = config.data_dir;
    converted.file_pattern = config.file_pattern;
    converted.reverse = config.reverse;
    converted.extract.clear();
    converted.extract.reserve(config.extract.size());
    for (const auto& rule : config.extract) {
        converted.extract.push_back({rule->id.value(), rule->target, rule->pattern, rule->required});
    }
}

namespace {

// The declared aliases and constraints cross as declared, row for row: crysta reads, checks, saves and
// applies them; edi keeps the text.
void fill_crysta_relations(const Project& model, crysta::Project& converted) {
    converted.aliases.clear();
    converted.aliases.reserve(model.aliases.size());
    for (const auto& alias : model.aliases) {
        converted.aliases.push_back({alias->id.value(), alias->parameter_unique_name.value()});
    }
    converted.constraints.clear();
    converted.constraints.reserve(model.constraints.size());
    for (const auto& constraint : model.constraints) {
        converted.constraints.push_back(
            {constraint->id.value(), constraint->expression.value(), constraint->enabled.get()});
    }
}

// crysta's coded problems as edi's DomainValidationError, each code kept (ADR-0024).
DomainValidationError coded_refusal(const std::vector<crysta::RelationProblem>& problems) {
    std::vector<Diagnostic> diagnostics;
    diagnostics.reserve(problems.size());
    for (const crysta::RelationProblem& problem : problems) {
        diagnostics.push_back({problem.code, Severity::Error, "analysis", problem.message, {}, "crysta"});
    }
    return DomainValidationError(std::move(diagnostics));
}

// A refusal from crysta that carries codes is raised again as coded_refusal; the caller rethrows
// any other exception unchanged.
void raise_coded(const std::exception& error) {
    const std::vector<crysta::RelationProblem> problems = crysta::problems_of(error);
    if (!problems.empty()) {
        throw coded_refusal(problems);
    }
}

}  // namespace

void save_project_via_crysta(const Project& model, const std::string& directory) {
    // Edi does not write — it asks crysta to. Build the full engine project from the model
    // through the one conversion choke point (completed cell, start-carrying parameters),
    // fill the persistence-only fields the calculation conversion never needed, stamp the
    // loader-grade identity with crysta's own exported stamp, and hand crysta::save_project
    // the write (staging, atomic publish and fail-closed validation are its own).
    BuiltExperiments built_experiments;
    built_experiments.reserve(model.experiments.size());
    for (const auto& e_item : model.experiments) {
        const ExperimentBase& e = *e_item;
        crysta::BraggPdExperiment& built = build_on_heap(built_experiments, e);
        built.calculation_only = e.calculation_only;
        built.fit_n_data_points = e.fit_n_data_points;  // The bank's share of the last fit
        built.fit_prof_wr_factor = e.fit_prof_wr_factor;
        built.fit_chi_square = e.fit_chi_square;
        // Every token of the experiment — the absorption family, the experiment-type axes and the
        // scattering-source selectors — has already crossed, through crysta's converter, in the
        // one conversion both paths share (apply_post_build_fields). The delegated save used to
        // repeat some of them and was the only path to cross two.
        if (e.data.has_value()) {
            // The measured columns only: crysta writes computed columns from its own current
            // units (ADR-0073 §6), and a project built for a save has none, so the file keeps
            // today's bytes.
            built.data = crysta::PdDataBase(e.data->axis(), e.data->intensity_meas.get(),
                                            e.data->intensity_meas_su.get());
        }
        // The persisted pair follows the FAMILY, not key presence — a typed family's
        // parameters exist iff the type says so. Under "cylinder" the loader has already
        // canonicalised both coefficients (a missing key defaulted to 0), so they cross as
        // ordinary values; under "none" there is nothing to persist.
        if (crysta::absorption_form_of(built.kind, built.absorption_type.get()) ==
            crysta::AbsorptionForm::None) {
            built.absorption.clear();
        }
    }
    crysta::Project cproject(to_crysta_structures(model), experiment_list(built_experiments));
    cproject.fitting_mode =
        crysta::model_token_from_file(crysta::TokenField::FittingMode,
                                      crysta::BeamModeEnum::TimeOfFlight, model.fitting_mode);
    cproject.minimizer_max_iterations = model.minimizer_max_iterations;
    // The declared descent and chi-square tolerance round-trip the same way.
    cproject.minimizer_descent = model.descent;
    cproject.minimizer_chi_square_tolerance = model.minimizer_chi_square_tolerance;
    cproject.minimizer_type = model.minimizer_type;
    // The last fit's result rides the save (crysta writes `_fit_result` iff one is held).
    {
        const FitResultRecord& from = model.fit_result;
        crysta::FitResultRecord& to = cproject.fit_result;
        to.result_kind = from.result_kind;
        to.success = from.success;
        to.message = from.message;
        to.iterations = from.iterations;
        to.fitting_time = from.fitting_time;
        to.reduced_chi_square = from.reduced_chi_square;
        to.objective_name = from.objective_name;
        to.objective_value = from.objective_value;
        to.n_data_points = from.n_data_points;
        to.n_parameters = from.n_parameters;
        to.n_free_parameters = from.n_free_parameters;
        to.degrees_of_freedom = from.degrees_of_freedom;
        to.covariance_available = from.covariance_available;
        to.exit_reason = from.exit_reason;
        to.prof_wr_factor = from.prof_wr_factor;
        to.profile_function = from.profile_function;
        to.background_function = from.background_function;
        to.descent = from.descent;
    }
    // The declared scan block round-trips through the delegated save exactly as the fitting
    // mode does — a save that dropped it would turn a sequential project into a single one on
    // the next load.
    fill_crysta_sequential(model.sequential_fit, cproject.sequential_fit);
    fill_crysta_relations(model, cproject);
    // Review-1 F5/F1: the engine project must know WHERE this model came from. crysta's save
    // carries a scan's data directory and results.csv from the project's own directory and proves
    // the declared data_dir stays inside it; with an empty path it can do neither, so an edi save
    // silently dropped the scan inputs and the results, and the containment rule never ran on the
    // edi save path at all.
    cproject.path = model.path;
    // The project identity rides the delegated save. Copy the six persisted metadata fields
    // across (the two ProjectMetadata mirrors are distinct C++ types; `path` is engine
    // bookkeeping the record never carries) and ENGAGE persistence — crysta's writer then merges
    // the `_metadata.*` block into a carried project.edi, or creates the record when none
    // exists. Safe to engage from here and only here: edi's loader restores the record's fields,
    // so this save writes back what a load carried in; crysta-native saves stay disengaged and
    // byte-identical.
    cproject.metadata.name = model.metadata.name;
    cproject.metadata.title = model.metadata.title;
    cproject.metadata.description = model.metadata.description;
    cproject.metadata.created = model.metadata.created;
    cproject.metadata.last_modified = model.metadata.last_modified;
    cproject.metadata.timestamp = model.metadata.timestamp;
    cproject.persist_metadata = true;
    // Review-9 F1: ONE persisted snapshot row per basic. In memory every free tied axis may
    // carry its own prior state (lossless undo), but the persisted _fit_parameter loop keeps
    // only the designated axis's row — the representative when free, else the first free
    // axis — the same rule capture and landing use in both products.
    for (crysta::Structure& cstructure : cproject.structures) {
        const crysta::PositionalConstraints constraints = cstructure.positional_constraints();
        const auto& positions = constraints.sites();
        for (std::size_t i = 0; i < cstructure.atom_sites.size(); ++i) {
            const crysta::SpecialPosition& position = positions[i].second;
            crysta::AtomSite& site = cstructure.atom_sites[i];
            bool seen[3] = {false, false, false};
            int designated[3] = {-1, -1, -1};
            for (std::size_t axis = 0; axis < 3; ++axis) {
                if (!position.axis_is_basic(axis)) {
                    continue;
                }
                const std::size_t local = position.axis_basic_index(axis);
                const bool is_representative = !seen[local];
                seen[local] = true;
                if (site.fract[axis].free() &&
                    (is_representative || designated[local] < 0)) {
                    designated[local] = static_cast<int>(axis);
                }
            }
            for (std::size_t axis = 0; axis < 3; ++axis) {
                if (!position.axis_is_basic(axis)) {
                    continue;
                }
                if (designated[position.axis_basic_index(axis)] != static_cast<int>(axis)) {
                    // One ROW per basic: rows key on start_value. A companion's esd-only
                    // snapshot stays — it is the start_tied payload once the linked writer
                    // carries the column; main's two-column writer simply ignores it.
                    crysta::Parameter& companion = site.fract[axis];
                    companion.set_fit_start(std::nullopt, companion.start_uncertainty());
                }
            }
        }
    }
    crysta::stamp_canonical_identity(cproject);
    // Crysta writes the computed columns of a project whose calculation is current. When edi holds a
    // calculation, the engine project calculates last, after every write above, so the file carries
    // the columns a current calculation gives, exactly as crysta's own save does. A project edi never
    // calculated keeps today's bytes (schema 3), and a refused calculation saves it uncomputed. Each
    // bank's file carries a calculation exactly when its live categories do. The engine calculates
    // every bank together, so when any bank is current the engine project is recalculated, and each
    // bank edi reads as stale is then marked stale in it by an equal-value write to one of its inputs
    // (any input write stales the unit); crysta's writer leaves that bank's computed loops out.
    std::vector<bool> current;
    current.reserve(model.experiments.size());
    for (const auto& item : model.experiments) {
        current.push_back(item->data.has_value() && !item->data->intensity_calc.empty() &&
                          item->computed_current());
    }
    if (std::find(current.begin(), current.end(), true) != current.end()) {
        try {
            crysta::calculate_project(cproject);
        } catch (const std::invalid_argument&) {  // NOLINT(bugprone-empty-catch) — saved uncomputed
        }
        for (std::size_t index = 0; index < current.size(); ++index) {
            if (!current[index]) {
                for (crysta::LinkedStructure& link : cproject.experiments[index].linked_structures) {
                    link.scale.set_value(link.scale.value());
                }
            }
        }
    }
    // The structure file carries the computed structure categories exactly when edi's are
    // current. The engine structure calculates them here (the bank calculation above already
    // did, when it ran), or — when edi's are not current — an equal-value write to one of their
    // inputs stales any the engine holds, and crysta's writer leaves them out.
    for (std::size_t index = 0; index < model.structures.size(); ++index) {
        crysta::Structure& cstructure = cproject.structures.at(index);
        if (model.structures[index]->geometry_current()) {
            if (crysta::geometry_state(cstructure) != crysta::ComputedState::Current) {
                try {
                    crysta::calculate_structure(cstructure);
                } catch (const std::invalid_argument&) {  // NOLINT(bugprone-empty-catch) — uncomputed
                }
            }
        } else {
            crysta::Geom& geom = cstructure.geom;
            geom.bond_distance_inc = std::optional<double>(geom.bond_distance_inc.get());
        }
    }
    try {
        crysta::save_project(cproject, directory);
    } catch (const std::exception& error) {
        raise_coded(error);
        throw;
    }
}

namespace detail {

// ADR-0016: crysta's identity table and representable-id domain, for the
// loader (identity_bridge.hpp) — one decision for both products.
const char* identity_category(const std::string& tag) {
    for (const crysta::IdentityColumn& column : crysta::identity_columns()) {
        if (tag == column.tag) {
            return column.category;
        }
    }
    return nullptr;
}

void require_representable_id(const std::string& value, const std::string& category,
                              const std::string& where) {
    crysta::require_representable_id(value, category, where);
}

// The engine's own physical domains (crysta/cell_metric.hpp), for the loader.
std::string cell_domain_message(double a, double b, double c, double alpha_deg, double beta_deg,
                                double gamma_deg) {
    return crysta::cell_domain_message(a, b, c, alpha_deg, beta_deg, gamma_deg);
}

std::string wavelength_domain_message(double wavelength) {
    return crysta::wavelength_domain_message(wavelength);
}

// Edi's refusals spell an id exactly as crysta's do (edi/model.hpp).
std::string printable_id(const std::string& id) { return crysta::printable_id(id); }

}  // namespace detail

// ADR-0016: the one name -> path composition is crysta's.
std::string entity_path(const std::string& directory, const std::string& kind,
                        const std::string& name) {
    if (kind != "structure" && kind != "experiment") {
        throw std::invalid_argument("entity_path: the kind must be 'structure' or 'experiment', not '" +
                                    kind + "'");
    }
    return crysta::entity_path(std::filesystem::path(directory) / (kind + "s"),
                               crysta::datablock_key(name, kind), kind)
        .string();
}

namespace detail {

crysta::Cell to_crysta_cell(const Cell& c) {
    std::vector<crysta::Parameter> cell_params;
    cell_params.push_back(param(c.length_a, crysta::CELL, "a"));
    cell_params.push_back(param(c.length_b, crysta::CELL, "b"));
    cell_params.push_back(param(c.length_c, crysta::CELL, "c"));
    cell_params.push_back(param(c.angle_alpha, crysta::CELL, "alpha"));
    cell_params.push_back(param(c.angle_beta, crysta::CELL, "beta"));
    cell_params.push_back(param(c.angle_gamma, crysta::CELL, "gamma"));
    return crysta::Cell(std::move(cell_params));
}

std::vector<crysta::AtomSite> to_crysta_atom_sites(const ItemVec<AtomSite>& atoms) {
    std::vector<crysta::AtomSite> sites;
    sites.reserve(atoms.size());
    for (const auto& a_item : atoms) {
        const AtomSite& a = *a_item;
        // The site's own `adp_type` crosses through crysta's converter. An undeclared one is the
        // vocabulary's first word, which is what crysta has always been handed for an edi site.
        const std::vector<std::string> adp_types = crysta::file_tokens(
            crysta::TokenField::AdpType, crysta::BeamModeEnum::TimeOfFlight);
        sites.emplace_back(a.id, a.type_symbol, a.wyckoff_letter,
                           crysta::model_token_from_file(
                               crysta::TokenField::AdpType, crysta::BeamModeEnum::TimeOfFlight,
                               a.adp_type.empty() ? adp_types.front() : a.adp_type.value()),
                           param(a.fract_x, crysta::ATOM_POS, "fract_x"),
                           param(a.fract_y, crysta::ATOM_POS, "fract_y"),
                           param(a.fract_z, crysta::ATOM_POS, "fract_z"),
                           param(a.occupancy, crysta::OCC, "occupancy"),
                           param(a.adp_iso, crysta::ADP, "b_iso"));
    }
    return sites;
}

namespace {
// The engine experiment is built around one scale. It is seeded from the first row, and
// apply_post_build_fields then writes every link, so no phase is dropped. A bank with no link is
// converted only for the project's relations, where it has no scale to name; any other conversion
// refuses it.
const Parameter& seed_scale(const ExperimentBase& e, bool for_relations) {
    if (e.linked_structures.empty()) {
        if (for_relations) {
            static const Parameter no_scale{};
            return no_scale;
        }
        throw std::out_of_range("experiment '" + e.name.value() + "' links no structure");
    }
    return e.linked_structures[0]->scale;
}
}  // namespace

// Fields the public TofJorgensenExperiment builder has no setter for, applied to the built
// experiment. They are plain public members of crysta::ExperimentBase, so this needs no
// engine change. Unlike make_fit_ready above these are genuine model content — they belong on EVERY
// converted experiment, forward and fit alike (`peak_type` in particular selects the Lorentzian
// profile in crysta's forward kernel too, so omitting it would silently drop it from calculate()).
//
// Every one of these is load-bearing for a joint fit:
//   name          the joint free-set label prefix (`<bank>.<field>`) — without it labels collide;
//   peak_type     selects the Jorgensen-von-Dreele Lorentzian free block; crysta defaults to plain
//                 `tof-jorgensen`, under which a bracketed Lorentzian coefficient is REJECTED, so
//                 omitting this silently changes the free set (or hard-errors);
//   absorption    the per-bank ABSCOR1/ABSCOR2 pair; absent/0 means mu*R = 0, i.e. A == 1;
//   dataset_weight, excluded_regions  the per-bank joint weight and mask.
void apply_post_build_fields(const ExperimentBase& e, crysta::ExperimentBase& built) {
    built.name = e.name;
    // Each token below crosses through crysta's converter (crossed, above).
    if (e.peak.type) {
        built.peak_type = crossed(crysta::TokenField::PeakType, built, *e.peak.type);
    }
    // crysta's own beam_mode field holds the declared token; empty = the source declared none.
    built.beam_mode =
        crossed(crysta::TokenField::BeamMode, built,
                e.experiment_type.beam_mode ? token(*e.experiment_type.beam_mode) : std::string());
    // The radiation crosses on the CALCULATE path too — crysta selects the X-ray f0 amplitudes
    // and intensity unit from it. Only the declared token crosses, as for beam_mode.
    built.radiation_probe = crossed(crysta::TokenField::RadiationProbe, built,
                                    e.experiment_type.radiation_probe
                                        ? token(*e.experiment_type.radiation_probe)
                                        : std::string());
    // The other two declared axes cross on every path as well. They used to cross only on the
    // delegated save, so the model a calculation read differed from the one crysta's own loader
    // builds from the same file.
    built.sample_form = crossed(
        crysta::TokenField::SampleForm, built,
        e.experiment_type.sample_form ? token(*e.experiment_type.sample_form) : std::string());
    built.scattering_type =
        crossed(crysta::TokenField::ScatteringType, built,
                e.experiment_type.scattering_type ? token(*e.experiment_type.scattering_type)
                                                  : std::string());
    // The instrument registry token has no file tag; crysta declares it from the beam mode and
    // the radiation wherever an experiment is constructed, and it is an input of the computed
    // units, so a conversion declares it by crysta's own rule (the fingerprint of a file edi
    // saves then matches the one crysta computes on loading it).
    built.instrument_type = crysta::default_instrument_type(built.kind, built.is_xray());
    // ADR-0014: the declared X-ray source selectors, so crysta chooses the tables.
    built.xray_form_factor =
        crossed(crysta::TokenField::XrayFormFactor, built, e.xray_form_factor.value_or(""));
    built.xray_dispersion =
        crossed(crysta::TokenField::XrayDispersion, built, e.xray_dispersion.value_or(""));
    // The declared neutron source, so crysta chooses the table.
    built.neutron_scattering_length = crossed(crysta::TokenField::NeutronScatteringLength, built,
                                              e.neutron_scattering_length.value_or(""));
    built.dataset_weight = e.dataset_weight;
    built.excluded_regions = e.excluded_regions;
    // The declared background model, its constants and its terms, through crysta's converter like
    // every token; crysta refuses a model holding another type's rows or constants.
    built.background_type = crossed(crysta::TokenField::BackgroundType, built, e.background_type);
    built.background_origin = e.background_origin;
    built.background_x_min = e.background_x_min;
    built.background_x_max = e.background_x_max;
    {
        std::vector<crysta::PolynomialTerm> terms;
        terms.reserve(e.background_terms.size());
        for (const auto& term : e.background_terms) {
            terms.emplace_back(term->order.get(), param(term->coef, crysta::BACKGROUND, "coef"));
        }
        built.background_terms = std::move(terms);
    }
    // The declared family token crosses on the CALCULATE path too — crysta's CW kernel
    // resolves it (cwl_absorption_form on `absorption_type`), while its TOF derivation stays
    // structural (a present pair IS the cylinder). Same expression the delegated save uses.
    //
    // Through crysta's converter. The TOF file spells the Hewat cylinder `cylinder`; crysta's
    // model token is `cylinder-hewat`, and only that token lets the reflection sum fold.
    built.absorption_type =
        crossed(crysta::TokenField::AbsorptionType, built, e.absorption.type.value_or("none"));
    const crysta::AbsorptionForm absorption_form =
        crysta::absorption_form_of(built.kind, built.absorption_type.get());

    // AbsorptionBase: crysta expects [abscor1, abscor2]. A freed ABSCOR2 is passed through
    // rather than silently cleared; crysta rejects it with its own structured error.
    built.absorption.clear();
    // TOF only, and — review-8 F4 — only for the CYLINDER family: a typed family's
    // parameters exist iff the type says so, for the CALCULATION exactly as for
    // persistence. crysta's own loader fills the pair for a TOF cylinder block and leaves
    // both a CW block's and a type-none block's absorption EMPTY (F-d-ABS reversed), so the
    // conversion mirrors exactly that — a declared no-absorption project computes with no
    // absorption, before and after its round trip alike. Under "cylinder" the model holds
    // both coefficients (loader/factory canonical); value_or guards a hand-built partial
    // model only.
    if (built.kind == crysta::BeamModeEnum::TimeOfFlight &&
        absorption_form == crysta::AbsorptionForm::CylinderHewat) {
        built.absorption.push_back(
            param(e.absorption.abscor1.value_or(Parameter{}), crysta::CORRECTION, "abscor1"));
        built.absorption.push_back(
            param(e.absorption.abscor2.value_or(Parameter{}), crysta::CORRECTION, "abscor2"));
    }
    // The CW families carry the single mu_r body — [0]=mu_r, crysta's cwl layout, the same
    // typed-family rule as the TOF pair (parameters exist iff the type says so).
    if (built.kind == crysta::BeamModeEnum::ConstantWavelength &&
        absorption_form != crysta::AbsorptionForm::None) {
        built.absorption.push_back(
            param(e.absorption.mu_r.value_or(Parameter{}), crysta::CORRECTION, "mu_r"));
    }
    // The linked structures (phases) cross row by row: id, scale and whether each takes part. The
    // first keeps the scale the experiment was built with; every other is converted the same way.
    std::vector<crysta::LinkedStructure> links;
    links.reserve(e.linked_structures.size());
    for (const auto& link : e.linked_structures) {
        if (links.empty() && !built.linked_structures.empty()) {
            crysta::LinkedStructure first(built.linked_structures.at(0));
            first.structure_id = link->structure_id.value();
            first.enabled = link->enabled.get();
            links.push_back(first);
        } else {
            links.emplace_back(link->structure_id.value(),
                               param(link->scale, crysta::SCALE, "scale"), link->enabled.get());
        }
    }
    built.linked_structures.assign(links);
    // Every preferred-orientation row crosses as crysta's layout — [march_r, march_random_fract],
    // the fixed axis and the structure it names. crysta's loader refuses a TOF row; a hand-built
    // model reaching here with one fails closed rather than silently dropping it.
    std::vector<crysta::PreferredOrientation> textures;
    if (e.preferred_orientation.size() != 0 && built.kind != crysta::BeamModeEnum::ConstantWavelength) {
        throw std::invalid_argument("experiment '" + e.name +
                                    "': preferred orientation is constant-wavelength only");
    }
    for (const auto& item : e.preferred_orientation) {
        const PrefOrient& row = *item;
        // Review-2 F1: the row's key must name a structure it changes — a key mutated after
        // insertion is refused here, before any calculation or save crosses the boundary.
        const bool linked = std::any_of(
            e.linked_structures.begin(), e.linked_structures.end(), [&](const auto& link) {
                return !link->structure_id.value().empty() &&
                       link->structure_id.value() == row.structure_id.value();
            });
        if (!linked) {
            const std::string first =
                e.linked_structures.size() == 1 ? e.linked_structure().structure_id.value() : std::string();
            if (first.empty() && e.linked_structures.size() == 1) {
                fail_domain("experiment '" + e.name + "'", "preferred-orientation-structure",
                            "_preferred_orientation.structure_id '" + row.structure_id.value() +
                                "' cannot be proven: the experiment declares no linked structure");
            }
            fail_domain("experiment '" + e.name + "'", "preferred-orientation-structure",
                        "_preferred_orientation.structure_id '" + row.structure_id.value() +
                            "' does not name the linked structure '" + first + "'");
        }
        // Review-3 F1: the domain, as a structured error before anything crosses (crysta's own
        // boundary repeats it): finite r > 0, finite f in [0, 1], a nonzero axis.
        const double r = row.march_r.value;
        const double f = row.march_random_fract.value;
        const auto out_of_bound = [](int index) {  // review-4 F2: the loader's Miller-index bound
            return index > kPreferredOrientationAxisBound || index < -kPreferredOrientationAxisBound;
        };
        if (!std::isfinite(r) || !(r > 0.0) || !std::isfinite(f) || f < 0.0 || f > 1.0 ||
            (row.index_h == 0 && row.index_k == 0 && row.index_l == 0) ||
            out_of_bound(row.index_h) || out_of_bound(row.index_k) || out_of_bound(row.index_l)) {
            fail_domain("experiment '" + e.name + "'", "preferred-orientation-domain",
                        "preferred orientation needs a finite march_r > 0, a finite "
                        "march_random_fract in [0, 1] and a nonzero texture axis whose components "
                        "lie within the Miller-index bound " +
                            std::to_string(kPreferredOrientationAxisBound));
        }
        textures.emplace_back(row.structure_id.value(), param(row.march_r, crysta::CORRECTION, "march_r"),
                              param(row.march_random_fract, crysta::CORRECTION, "march_random_fract"),
                              std::array<int, 3>{row.index_h, row.index_k, row.index_l});
    }
    built.preferred_orientations.assign(textures);
}

// The CW conversion: crysta has no named CW builder at b9aee906, so the adapter uses the public
// ExperimentBase constructor with the documented CW vector layout — peak = [U, V, W, X, Y] and
// instrument = (calib_twotheta_offset, setup_wavelength, calib_sample_displacement,
// calib_sample_transparency) since — then sets the kind/beam-mode fields the constructor does not
// take. No value transformation happens here beyond marshalling (Fork 2's parity gate is what
// would catch one). A programmatic CW model with a missing field fails closed; a loaded one cannot
// reach that error (the per-family registry requires all seven).
crysta::BraggPdExperiment to_crysta_cwl_experiment(const ExperimentBase& e, bool for_relations) {
    const auto required = [&](const OptionalParameter& field,
                              const char* name) -> const Parameter& {
        if (!field.has_value()) {
            throw std::invalid_argument("constant-wavelength experiment '" + e.name +
                                        "' is missing required field " + name);
        }
        return *field;
    };
    std::vector<crysta::Parameter> peak;
    peak.reserve(5);
    peak.push_back(param(required(e.peak.broad_gauss_u, "peak.broad_gauss_u"), crysta::PROFILE, "broad_gauss_u"));
    peak.push_back(param(required(e.peak.broad_gauss_v, "peak.broad_gauss_v"), crysta::PROFILE, "broad_gauss_v"));
    peak.push_back(param(required(e.peak.broad_gauss_w, "peak.broad_gauss_w"), crysta::PROFILE, "broad_gauss_w"));
    // Every other slot the DECLARED profile carries, in crysta's dictionary order (its
    // peak_tags_for, ADR-0080) — exactly the slots crysta's loader would hold, whether or not a
    // programmatic model engaged them (an absent optional one takes the loader's default).
    const auto slot = [&](const OptionalParameter& field, const char* name,
                          double fallback) {
        Parameter value;
        value.value = fallback;
        peak.push_back(param(field ? *field : value, crysta::PROFILE, name));
    };
    const std::string declared = effective_peak_type(e);
    const CwlProfileSlots slots = cwl_profile_slots(declared);
    if (slots.lorentz_xy) {
        peak.push_back(param(required(e.peak.broad_lorentz_x, "peak.broad_lorentz_x"), crysta::PROFILE, "broad_lorentz_x"));
        peak.push_back(param(required(e.peak.broad_lorentz_y, "peak.broad_lorentz_y"), crysta::PROFILE, "broad_lorentz_y"));
    } else if (slots.mixing_eta) {
        slot(e.peak.mixing_eta_0, "mixing_eta_0", 0.0);
        slot(e.peak.mixing_eta_1, "mixing_eta_1", 0.0);
    }
    if (slots.fcj) {
        slot(e.peak.asym_fcj_1, "asym_fcj_1", 0.0);
        slot(e.peak.asym_fcj_2, "asym_fcj_2", 0.0);
    } else if (slots.beba) {
        slot(e.peak.asym_beba_a0, "asym_beba_a0", 0.0);
        slot(e.peak.asym_beba_b0, "asym_beba_b0", 0.0);
        slot(e.peak.asym_beba_a1, "asym_beba_a1", 0.0);
        slot(e.peak.asym_beba_b1, "asym_beba_b1", 0.0);
        slot(e.peak.asym_beba_limit, "asym_beba_limit", 180.0);
        peak.back().set_free(false);  // a fixed setting, whatever its flag (is_fixed_setting)
    }
    // Every other slot must be the declared profile's: one it does not carry would be dropped here,
    // from a calculation, a fit and a save alike, so it is refused instead.
    require_peak_slots_fit_type(e);
    std::vector<crysta::Parameter> instrument;
    instrument.reserve(6);
    instrument.push_back(param(required(e.instrument.calib_twotheta_offset, "instrument.calib_twotheta_offset"), crysta::CALIBRATION,
                               "calib_twotheta_offset"));
    instrument.push_back(
        param(required(e.instrument.setup_wavelength, "instrument.setup_wavelength"), crysta::INSTRUMENT, "setup_wavelength"));
    // The two line shifts at instrument[2]/[3], crysta's 4-wide CW layout — an absent one takes
    // the loader's default 0, exactly what crysta's loader would hold (and its writer omits a
    // fixed zero with no uncertainty, so a model that never declared them saves unchanged — hence
    // the fallback carries NO uncertainty, not Parameter{}'s present 0).
    Parameter undeclared_shift;
    undeclared_shift.uncertainty = std::nullopt;
    instrument.push_back(param(e.instrument.calib_sample_displacement.value_or(undeclared_shift),
                               crysta::CALIBRATION, "calib_sample_displacement"));
    instrument.push_back(param(e.instrument.calib_sample_transparency.value_or(undeclared_shift),
                               crysta::CALIBRATION, "calib_sample_transparency"));
    // An X-ray experiment's monochromator polarization at instrument[4]/[5], crysta's 6-wide X-ray
    // layout; absent takes the loader's default 0 under the same no-uncertainty rule. A neutron
    // experiment stays 4-wide, as crysta's loader builds it.
    if (e.experiment_type.effective_radiation_probe() == RadiationProbeEnum::XRAY) {
        instrument.push_back(param(e.instrument.setup_polarization_coefficient.value_or(undeclared_shift),
                                   crysta::CALIBRATION, "setup_polarization_coefficient"));
        instrument.push_back(param(e.instrument.setup_monochromator_twotheta.value_or(undeclared_shift),
                                   crysta::CALIBRATION, "setup_monochromator_twotheta"));
    }
    std::vector<crysta::LineSegment> background;
    background.reserve(e.background.size());
    for (const auto& point : e.background) {
        background.emplace_back(point->position,
                                param(point->intensity, crysta::BACKGROUND, "intensity"));
    }
    crysta::BraggPdExperiment built(std::move(peak), std::move(instrument),
                             param(seed_scale(e, for_relations), crysta::SCALE, "scale"), std::move(background));
    built.cutoff_fwhm = e.peak.cutoff_fwhm;
    built.kind = crysta::BeamModeEnum::ConstantWavelength;  // before the post-build fill: the
    // TOF-only abscor guard reads it
    apply_post_build_fields(e, built);
    if (!e.peak.type) {
        built.peak_type = "cwl-tch-pseudo-voigt";  // never leave the TOF default on a CW experiment
    }
    return crysta::BraggPdExperiment(built);  // a copy: an experiment never moves
}

// The ONE admission rule for the X-ray monochromator polarization on an experiment that is not
// X-ray CW (a view over another family's experiment, or X-ray state whose radiation or beam mode
// was changed after loading). A member that says nothing beyond crysta's
// default (value 0, fixed, no uncertainty, no fit start) is the default every reader applies, so
// it is inert and not converted; one that says something is refused by name, never dropped. Every
// calculation, fit (single and joint) and delegated save converts through here, so all of them
// apply it; crysta's own boundary applies the same rule to its native storage.
void require_polarization_family(const ExperimentBase& e) {
    if (e.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH &&
        e.experiment_type.effective_radiation_probe() == RadiationProbeEnum::XRAY) {
        return;
    }
    // Review-3 F1: the member's identity is the storage slot checked, never the parameter's
    // descriptor, which a native caller may leave null or point at another parameter's spec.
    for (const auto& [name, slot] :
         {std::pair<const char*, const OptionalParameter*>{
              "setup_polarization_coefficient", &e.instrument.setup_polarization_coefficient},
          std::pair<const char*, const OptionalParameter*>{
              "setup_monochromator_twotheta", &e.instrument.setup_monochromator_twotheta}}) {
        if (!*slot) {
            continue;
        }
        const Parameter& p = **slot;
        if (p.value != 0.0 || p.free || p.uncertainty.has_value() || p.start_value.has_value()) {
            throw std::invalid_argument(
                "experiment '" + e.name + "' carries _instrument." + name +
                (p.free ? " (free)" : "") +
                " but is not an X-ray constant-wavelength experiment — the monochromator "
                "polarization is X-ray CW only: reset it to 0 and fixed, or "
                "declare the experiment X-ray CW");
        }
    }
}

crysta::BraggPdExperiment to_crysta_experiment(const ExperimentBase& e, bool for_relations) {
    require_polarization_family(e);
    if (e.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH) {
        return to_crysta_cwl_experiment(e, for_relations);
    }
    crysta::TofJorgensenExperiment builder;
    builder.alpha0(state(e.peak.rise_alpha_0))
        .alpha1(state(e.peak.rise_alpha_1))
        .beta0(state(e.peak.decay_beta_0))
        .beta1(state(e.peak.decay_beta_1))
        .sigma0(state(e.peak.broad_gauss_sigma_0))
        .sigma1(state(e.peak.broad_gauss_sigma_1))
        .sigma2(state(e.peak.broad_gauss_sigma_2))
        .size_g(state(e.peak.broad_gauss_size))
        .strain_g(state(e.peak.broad_gauss_strain))
        .gamma0(state(e.peak.broad_lorentz_gamma_0))
        .gamma1(state(e.peak.broad_lorentz_gamma_1))
        .gamma2(state(e.peak.broad_lorentz_gamma_2))
        .size_l(state(e.peak.broad_lorentz_size))
        .strain_l(state(e.peak.broad_lorentz_strain))
        .zero(state(e.instrument.calib_d_to_tof_offset))
        .dtt1(state(e.instrument.calib_d_to_tof_linear))
        .dtt2(state(e.instrument.calib_d_to_tof_quadratic))
        .d_to_tof_reciprocal(state(e.instrument.calib_d_to_tof_reciprocal))
        .scale(state(seed_scale(e, for_relations)))
        .setup_twotheta_bank(e.instrument.setup_twotheta_bank.value)
        .cutoff_fwhm(e.peak.cutoff_fwhm);

    std::vector<crysta::LineSegment> background;
    background.reserve(e.background.size());
    for (const auto& point : e.background) {
        background.emplace_back(point->position,
                                param(point->intensity, crysta::BACKGROUND, "intensity"));
    }
    builder.background(std::move(background));
    crysta::BraggPdExperiment built = builder.build();
    apply_post_build_fields(e, built);
    return crysta::BraggPdExperiment(built);  // a copy: an experiment never moves
}

crysta::BraggPdExperiment to_crysta_experiment(const ExperimentBase& e) {
    return to_crysta_experiment(e, false);
}

}  // namespace detail

namespace {

// One column crysta published, shared into edi's model — the same buffer.
template <typename T>
ComputedColumn<T> shared_column(const crysta::Column<T>& column) {
    return ComputedColumn<T>(column.buffer());
}

// `calc_status` crosses as its file and Python spelling (`incl` / `excl`, seam S4).
ComputedColumn<std::string> status_column(const crysta::Column<crysta::CalcStatus>& column) {
    auto tokens = std::make_shared<std::vector<std::string>>();
    tokens->reserve(column.size());
    for (const crysta::CalcStatus status : column) {
        tokens->emplace_back(crysta::calc_status_token(status));
    }
    return ComputedColumn<std::string>(std::move(tokens));
}

}  // namespace

namespace {
// The experiment node a handed-out data object came from, while it is still that node.
PdDataBase* live_source(const PdDataBase& object) noexcept {
    ExperimentBase* experiment = object.source.experiment();
    if (experiment == nullptr || !experiment->data.has_value() ||
        experiment->data->epoch.value() != object.source.node()) {
        return nullptr;
    }
    return &*experiment->data;
}
}  // namespace

void PdDataBase::write_column(detail::Written<std::vector<double>> PdDataBase::* column,
                              std::vector<double> values) {
    if (PdDataBase* node = live_source(*this); node != nullptr && node != this) {
        node->*column = values;
        node->written = detail::Epoch();
    }
    this->*column = std::move(values);
    clear_computed();
    written = detail::Epoch();
}

void PdDataBase::write_axis(
    detail::Written<std::optional<std::vector<double>>> PdDataBase::* axis,
    std::optional<std::vector<double>> values) {
    if (PdDataBase* node = live_source(*this); node != nullptr && node != this) {
        node->*axis = values;
        node->written = detail::Epoch();
    }
    this->*axis = std::move(values);
    clear_computed();
    written = detail::Epoch();
}

bool PdDataBase::computed_current() const {
    const PdDataBase* node = live_source(*this);
    return node != nullptr && node != this && source.experiment()->computed_current() &&
           node->d_spacing.buffer() == d_spacing.buffer() &&
           node->intensity_calc.buffer() == intensity_calc.buffer() &&
           node->intensity_bkg.buffer() == intensity_bkg.buffer() &&
           node->calc_status.buffer() == calc_status.buffer();
}

// The one geometry read. crysta computes; every column below is crysta's own buffer, shared.
StructureGeometry structure_geometry(const Structure& structure, const ViewWindow& window) {
    const crysta::Structure engine = to_crysta_structure(structure);
    crysta::ViewWindow engine_window;
    engine_window.min = window.min;
    engine_window.max = window.max;
    const crysta::StructureGeometry computed =
        crysta::compute_structure_geometry(engine, engine_window);
    StructureGeometry out;
    out.window = window;
    out.space_group_symop.operation_xyz = shared_column(computed.space_group_symop.operation_xyz);
    const crysta::ExpandedAtomSites& atoms = computed.expanded_atom_sites;
    out.expanded_atom_sites.atom_site_id = shared_column(atoms.atom_site_id);
    out.expanded_atom_sites.site_symmetry = shared_column(atoms.site_symmetry);
    out.expanded_atom_sites.fract_x = shared_column(atoms.fract_x);
    out.expanded_atom_sites.fract_y = shared_column(atoms.fract_y);
    out.expanded_atom_sites.fract_z = shared_column(atoms.fract_z);
    out.expanded_atom_sites.cartn_x = shared_column(atoms.cartn_x);
    out.expanded_atom_sites.cartn_y = shared_column(atoms.cartn_y);
    out.expanded_atom_sites.cartn_z = shared_column(atoms.cartn_z);
    out.expanded_atom_sites.occupancy = shared_column(atoms.occupancy);
    out.expanded_atom_sites.u_iso = shared_column(atoms.u_iso);
    out.expanded_atom_sites.cluster_id = shared_column(atoms.cluster_id);
    const crysta::GeomBonds& bonds = computed.geom_bond;
    out.geom_bond.expanded_atom_site_id_1 = shared_column(bonds.expanded_atom_site_id_1);
    out.geom_bond.expanded_atom_site_id_2 = shared_column(bonds.expanded_atom_site_id_2);
    out.geom_bond.atom_site_label_1 = shared_column(bonds.atom_site_label_1);
    out.geom_bond.atom_site_label_2 = shared_column(bonds.atom_site_label_2);
    out.geom_bond.site_symmetry_1 = shared_column(bonds.site_symmetry_1);
    out.geom_bond.site_symmetry_2 = shared_column(bonds.site_symmetry_2);
    out.geom_bond.distance = shared_column(bonds.distance);
    out.atom_sites_cartn_transform.matrix = computed.atom_sites_cartn_transform.matrix;
    out.atom_sites_cartn_transform.axes = computed.atom_sites_cartn_transform.axes;
    return out;
}

namespace {
// The project that holds `structure`, reached through its sites' link to their project (edi ADR-0024)
// and checked to hold this very structure; null otherwise.
Project* project_holding(const Structure& structure) {
    Project* project = static_cast<const detail::KeyedBase&>(structure.atom_sites).host();
    if (project == nullptr) {
        return nullptr;
    }
    for (const auto& item : project->structures) {
        if (item.get() == &structure) {
            return project;
        }
    }
    return nullptr;
}

// Before a geometry is computed for a project-owned structure, its relations set the coordinates and the
// cell, as a calculation sets them (edi ADR-0024). A relation that cannot hold, or a value outside its
// range, refuses the read with crysta's code and leaves the model as it was.
Project* relations_applied(const Structure& structure) {
    Project* project = project_holding(structure);
    if (project != nullptr) {
        refresh_relations(*project);
        complete_relations(*project);
    }
    return project;
}

// Whether a source's relations still hold for its holder, now owned by `live` (null: no project), edi
// ADR-0024. The owner must be the same project, or none both times, so a structure that moved, left
// or outlived its project is stale. The collections must be the same records, so a first row in a
// collection that had none, or a replaced collection, is a change; then their rows must encode equal.
bool relations_unchanged(const Project* live, const std::shared_ptr<const detail::ProjectLink>& owner,
                         const std::shared_ptr<const detail::Membership>& aliases,
                         const std::shared_ptr<const detail::Membership>& constraints,
                         const std::string& relations) {
    if (live == nullptr) {
        return owner == nullptr;
    }
    return owner.get() == live->link().get() && aliases == live->aliases.record() &&
           constraints == live->constraints.record() &&
           detail::relation_inputs(live->aliases, live->constraints) == relations;
}

template <typename Source>
void record_relations(Source& source, const Project* project) {
    if (project != nullptr) {
        source.owner = project->link();
        source.aliases = project->aliases.record();
        source.constraints = project->constraints.record();
        source.relations = detail::relation_inputs(project->aliases, project->constraints);
    }
}

// Computes the structure's default-window geometry and records what it was computed from: with the
// project's declared relations when a project calculates it. A refusal leaves the structure with no
// geometry and rethrows.
void store_geometry(Structure& structure, const Project* project = nullptr) {
    structure.geometry = StructureGeometry{};
    structure.geometry_source.reset();
    // The inputs are read before the computation, so a write during it leaves the result stale.
    detail::GeometrySource source{detail::geometry_inputs(structure)};
    record_relations(source, project);
    structure.geometry = structure_geometry(structure, ViewWindow{});
    structure.geometry_source =
        std::make_shared<const detail::GeometrySource>(std::move(source));
}
}  // namespace

WindowGeometry window_geometry(const Structure& structure, const ViewWindow& window) {
    WindowGeometry out;
    // crysta's window check first, so a refused window applies no relation and writes nothing.
    crysta::ViewWindow checked;
    checked.min = window.min;
    checked.max = window.max;
    crysta::require_view_window(checked);
    const Project* project = relations_applied(structure);
    // The inputs are read before the computation, so a write during it leaves the result stale.
    detail::GeometrySource source{detail::geometry_inputs(structure)};
    record_relations(source, project);
    out.source = std::make_shared<const detail::GeometrySource>(std::move(source));
    out.geometry = structure_geometry(structure, window);
    return out;
}

bool window_geometry_current(const Structure& structure, const WindowGeometry& result) {
    const std::shared_ptr<const detail::GeometrySource>& source = result.source;
    return source != nullptr && detail::geometry_inputs(structure) == source->inputs &&
           relations_unchanged(project_holding(structure), source->owner, source->aliases,
                               source->constraints, source->relations);
}

double default_min_bond_distance_cutoff() {
    return crysta::Geom::kDefaultMinBondDistanceCutoff;
}
double default_bond_distance_inc() {
    return crysta::Geom::kDefaultBondDistanceInc;
}

bool Structure::geometry_current() const {
    const std::shared_ptr<const detail::GeometrySource>& source = geometry_source;
    return source != nullptr && detail::geometry_inputs(*this) == source->inputs &&
           relations_unchanged(project_holding(*this), source->owner, source->aliases, source->constraints,
                               source->relations);
}

const StructureGeometry& Structure::current_geometry() {
    if (!geometry_current()) {
        store_geometry(*this, relations_applied(*this));
    }
    return geometry;
}

const PdDataBase& PdDataBase::computed_for_read() const {
    static const PdDataBase none;
    const PdDataBase* node = live_source(*this);
    if (node == nullptr || node == this) {
        return none;
    }
    ExperimentBase* experiment = source.experiment();
    experiment->ensure_computed();
    return experiment->data.has_value() ? *experiment->data : none;
}

const PowderReflnDataBase& PowderReflnDataBase::computed_for_read() const {
    static const PowderReflnDataBase none;
    ExperimentBase* experiment = source.experiment();
    if (experiment == nullptr) {
        return none;
    }
    experiment->ensure_computed();
    return experiment->refln;
}

void ExperimentBase::ensure_computed() {
    if (computed_current()) {
        return;
    }
    const detail::KeyedBase* collection = name.owner();
    Project* project = collection != nullptr ? collection->host() : nullptr;
    if (project == nullptr) {
        throw std::invalid_argument("experiment '" + name.value() +
                                    "' is not held by a project, so its computed categories "
                                    "cannot be calculated; add it to a project first");
    }
    project->calculate();
}

bool PowderReflnDataBase::computed_current() const {
    const ExperimentBase* experiment = source.experiment();
    return experiment != nullptr && experiment->computed_current() &&
           experiment->refln.structure_id.buffer() == structure_id.buffer() &&
           experiment->refln.d_spacing.buffer() == d_spacing.buffer() &&
           experiment->refln.f_calc.buffer() == f_calc.buffer() &&
           experiment->refln.position.buffer() == position.buffer();
}

bool ExperimentBase::computed_current() const {
    const std::shared_ptr<const detail::ComputedSource>& source = computed_source;
    if (!source || !source->experiments || !source->structures) {
        return false;
    }
    // Still held by the collection it was calculated in: a copy, a removed row and a row of
    // another project are never current.
    if (!peak.row.attached() || peak.row.record() != source->experiments.get()) {
        return false;
    }
    // No editor transaction since.
    if (!source->edits || source->edits->epoch.value() != source->edits_at) {
        return false;
    }
    const auto* structures = dynamic_cast<const ItemVec<Structure>*>(source->structures->owner);
    const detail::KeyedBase* rows = name.owner();
    return structures != nullptr && detail::calculation_inputs(*structures, *this) == source->inputs &&
           relations_unchanged(rows != nullptr ? rows->host() : nullptr, source->owner, source->aliases,
                               source->constraints, source->relations);
}

void Project::calculate() {
    // The reference shape (diffraction-lib Analysis.calculate): no arguments — every input is
    // read from the model (grid = the data node's engaged axis, bank angle and
    // cutoff = the experiment's declared values, scattering = the structure's declared map or the
    // built-in table), and the output lands in the model too.
    //
    // Edi computes none of it. One engine project carries every bank; crysta's current-result
    // path calculates them together and publishes all or none, and edi shares the published
    // columns into its model, each bank with the record of what it was calculated from
    // (ExperimentBase::computed_current). A refusal clears every bank's computed
    // categories: no earlier result may stay readable beside a model the
    // calculation refused.
    const auto clear_banks = [this] {
        for (auto& bank_item : experiments) {
            if (bank_item->data.has_value()) {
                bank_item->data->clear_computed();
            }
            bank_item->refln.clear();
            bank_item->computed_source.reset();
        }
    };
    try {
        // Every dependent at its relation's value before anything reads it, the geometry included, by
        // crysta's applier; relations that cannot hold refuse the calculation with crysta's code and
        // leave no computed category, as crysta's own calculation does.
        refresh_relations(*this);
        apply_relations(*this);
    } catch (...) {
        clear_banks();
        for (const auto& structure_item : structures) {
            structure_item->geometry = StructureGeometry{};
            structure_item->geometry_source.reset();
        }
        throw;
    }
    // Every structure's computed geometry is part of a calculation. Its own refusal — a `geom`
    // value out of range, a site the one-digit symmetry code cannot reach — leaves that structure
    // without geometry and does not stop the pattern, as in crysta: a geometry read raises it by
    // name.
    for (const auto& structure_item : structures) {
        try {
            store_geometry(*structure_item, this);
        } catch (const std::invalid_argument&) {  // NOLINT(bugprone-empty-catch) — see above
        }
    }
    try {
        publish_calculation();
    } catch (...) {
        clear_banks();
        throw;
    }
}

namespace {
// The engine experiments a calculation runs on: one per bank, each with its data node. Shared by
// calculate() and the parity dump, so the dump is of the very model a
// calculation reads.
BuiltExperiments calculation_banks(const ItemVec<BraggPdExperiment>& experiments) {
    BuiltExperiments banks;
    banks.reserve(experiments.size());
    for (const auto& bank_item : experiments) {
        const BraggPdExperiment& bank = *bank_item;
        if (!bank.data.has_value()) {
            throw std::invalid_argument(
                "edi calculate: experiment carries no data node — a loaded project always has "
                "one (measured data or a _data_range grid); assign a data node first");
        }
        crysta::BraggPdExperiment& built = build_on_heap(banks, bank);
        built.data = crysta::PdDataBase(bank.data->axis(), bank.data->intensity_meas.get(),
                                        bank.data->intensity_meas_su.get());
    }
    return banks;
}

crysta::BeamModeEnum crysta_kind(BeamModeEnum mode) {
    return mode == BeamModeEnum::CONSTANT_WAVELENGTH ? crysta::BeamModeEnum::ConstantWavelength
                                                     : crysta::BeamModeEnum::TimeOfFlight;
}
}  // namespace

namespace {

// The whole model as one engine project, for its relations: the structure, every bank (no data
// needed) and the declared aliases and constraints.
struct RelationProject {
    BuiltExperiments banks;
    std::unique_ptr<crysta::Project> project;
};

RelationProject relation_project(const Project& model) {
    RelationProject converted;
    // Every structure of the project (its phases), so each one's relations are compiled.
    std::vector<crysta::Structure> structures = to_crysta_structures(model);
    converted.banks.reserve(model.experiments.size());
    for (const auto& bank_item : model.experiments) {
        crysta::BraggPdExperiment& built = build_on_heap(converted.banks, *bank_item, true);
        // crysta's project needs every bank to link a structure. A bank with no link has no scale
        // of its own, so here it links the first structure under a scale no edi parameter names.
        if (bank_item->linked_structures.empty() && !structures.empty()) {
            built.linked_structures.assign(std::vector<crysta::LinkedStructure>{crysta::LinkedStructure(
                structures.front().name.value(), param(Parameter{}, crysta::SCALE, "scale"), true)});
        }
    }
    converted.project =
        std::make_unique<crysta::Project>(std::move(structures), experiment_list(converted.banks));
    fill_crysta_relations(model, *converted.project);
    return converted;
}

enum class Completion : std::uint8_t { Values, ValuesAndUncertainties };

// Every dependent of `converted` set from its relation by crysta's one applier, then copied onto
// the model by unique name: its value, and after a fit its e.s.d., keeping the one it held before
// the fit for undo (a dependent has no fit-start row, so nothing is written for it).
void copy_dependents(crysta::Project& converted, Project& model, Completion completion) {
    const crysta::RelationGraph relations = crysta::apply_relations(converted, false);
    std::map<std::string, Parameter*> by_name;
    for (const NamedSlot& slot : named_slots(model)) {
        by_name.emplace(slot.unique_name, slot.parameter);
    }
    for (const crysta::Relation& relation : relations.relations()) {
        const auto found = by_name.find(relation.target_name);
        if (found == by_name.end()) {
            continue;
        }
        Parameter& target = *found->second;
        if (target.value.get() != relation.target->value()) {
            target.value = relation.target->value();
        }
        if (completion == Completion::ValuesAndUncertainties) {
            target.start_uncertainty = target.uncertainty.get();
            target.uncertainty = relation.target->uncertainty();
        }
    }
}

Dependence dependence_of(crysta::Dependence source) {
    switch (source) {
        case crysta::Dependence::SymmetryFixed: return Dependence::SymmetryFixed;
        case crysta::Dependence::SymmetryTied: return Dependence::SymmetryTied;
        case crysta::Dependence::Constrained: return Dependence::Constrained;
        case crysta::Dependence::Independent: break;
    }
    return Dependence::Independent;
}

// crysta's wording for why a dependent's free flag is ignored.
std::string dependent_source(const crysta::Relation& relation) {
    switch (relation.source) {
        case crysta::Dependence::SymmetryFixed: return "fixed by symmetry";
        case crysta::Dependence::SymmetryTied: return "constrained by symmetry";
        case crysta::Dependence::Constrained: return "constrained by '" + relation.declared + "'";
        case crysta::Dependence::Independent: break;
    }
    return "independent";
}

// Every parameter's mark from crysta's graph; a dependent's free flag cleared, with crysta's warning
// when there is a sink to give it to.
void mark_dependents(Project& model, const crysta::RelationGraph& relations, const WarningSink& warn) {
    std::map<std::string, Parameter*> by_name;
    for (const NamedSlot& slot : named_slots(model)) {
        slot.parameter->dependence = Dependence::Independent;
        by_name.emplace(slot.unique_name, slot.parameter);
    }
    for (const crysta::Relation& relation : relations.relations()) {
        const auto found = by_name.find(relation.target_name);
        if (found == by_name.end()) {
            continue;
        }
        Parameter& target = *found->second;
        target.dependence = dependence_of(relation.source);
        if (target.free.get()) {
            target.free = false;
            if (warn) {
                warn("crysta.domain.dependent_free_ignored: parameter '" + relation.target_name +
                     "' is " + dependent_source(relation) +
                     "; free = True is ignored and it stays dependent");
            }
        }
    }
}

}  // namespace

void refresh_relations(Project& project, const WarningSink& warn) {
    if (project.structures.empty()) {
        return;
    }
    std::optional<RelationProject> converted;
    try {
        converted = relation_project(project);
    } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — a calculation refuses it
        return;
    }
    const std::vector<crysta::RelationProblem> problems =
        crysta::relation_problems(*converted->project);
    if (!problems.empty()) {
        throw coded_refusal(problems);
    }
    mark_dependents(project, crysta::compile_relations(*converted->project, false), warn);
}

void complete_relations(Project& project) {
    if (project.structures.empty()) {
        return;
    }
    // crysta completes a converted copy, so a refusal leaves this model as it was.
    RelationProject converted = relation_project(project);
    copy_dependents(*converted.project, project, Completion::Values);
    mark_dependents(project, crysta::compile_relations(*converted.project, false), {});
}

bool apply_relations(Project& project) {
    if (project.structures.empty()) {
        return false;
    }
    try {
        complete_relations(project);
        return true;
    } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — a calculation says why
        return false;
    }
}

void restore_dependents(Project& project) {
    RelationProject converted = relation_project(project);
    const crysta::RelationGraph relations = crysta::compile_relations(*converted.project, false);
    copy_dependents(*converted.project, project, Completion::Values);
    std::map<std::string, Parameter*> by_name;
    for (const NamedSlot& slot : named_slots(project)) {
        by_name.emplace(slot.unique_name, slot.parameter);
    }
    for (const crysta::Relation& relation : relations.relations()) {
        const auto found = by_name.find(relation.target_name);
        if (found == by_name.end()) {
            continue;
        }
        Parameter& target = *found->second;
        target.uncertainty = target.start_uncertainty.get();
        target.start_uncertainty = std::nullopt;
    }
}

std::vector<std::string> absorption_file_tokens(BeamModeEnum mode) {
    return crysta::file_tokens(crysta::TokenField::AbsorptionType, crysta_kind(mode));
}

std::string absorption_file_token(BeamModeEnum mode, const std::string& token) {
    const crysta::BeamModeEnum kind = crysta_kind(mode);
    const std::vector<std::string> spellings =
        crysta::file_tokens(crysta::TokenField::AbsorptionType, kind);
    if (std::find(spellings.begin(), spellings.end(), token) != spellings.end()) {
        return token;
    }
    const std::vector<std::string> registry =
        crysta::model_tokens(crysta::TokenField::AbsorptionType, kind);
    if (std::find(registry.begin(), registry.end(), token) != registry.end()) {
        return crysta::file_token_from_model(crysta::TokenField::AbsorptionType, kind, token);
    }
    std::string spelled;
    for (std::size_t i = 0; i < spellings.size(); ++i) {
        spelled += i == 0 ? "" : (i + 1 == spellings.size() ? " or " : ", ");
        spelled += spellings[i];
    }
    throw std::invalid_argument(
        std::string("unknown ") +
        (mode == BeamModeEnum::CONSTANT_WAVELENGTH ? "CW" : "TOF") + " _absorption.type '" +
        token + "' (the registry spells " + spelled + ")");
}

void register_engine_peak_type(const std::string& token, BeamModeEnum mode) {
    if (crysta::PeakFactory::rows().count(token) == 0) {
        crysta::PeakFactory::register_type(token, {{crysta_kind(mode), true}, nullptr});
    }
}

std::string absorption_registry_token(BeamModeEnum mode, const std::string& file_token) {
    return crysta::model_token_from_file(crysta::TokenField::AbsorptionType, crysta_kind(mode),
                                         file_token);
}

std::string engine_model_dump(const Project& project) {
    const BuiltExperiments banks = calculation_banks(project.experiments);
    crysta::Project engine(to_crysta_structures(project), experiment_list(banks));
    fill_crysta_relations(project, engine);
    return crysta::model_dump(engine);
}

bool engine_folds_reflections(const Project& project) {
    const BuiltExperiments banks = calculation_banks(project.experiments);
    const crysta::Project engine(to_crysta_structures(project), experiment_list(banks));
    return crysta::folds_reflections(engine);
}

std::uint64_t engine_structure_factor_evaluations() noexcept {
    return crysta::structure_factor_evaluations();
}

void Project::publish_calculation() {
    const BuiltExperiments banks = calculation_banks(experiments);
    std::vector<std::shared_ptr<const detail::ComputedSource>> sources;
    sources.reserve(experiments.size());
    for (const auto& bank_item : experiments) {
        // What this bank is calculated from, read before anything is published.
        sources.push_back(std::make_shared<const detail::ComputedSource>(detail::ComputedSource{
            detail::calculation_inputs(structures, *bank_item), experiments.record(),
            structures.record(), edits_.record(), edits_.record()->epoch.value(), link(), aliases.record(),
            constraints.record(), detail::relation_inputs(aliases, constraints)}));
    }
    crysta::Project engine(to_crysta_structures(*this), experiment_list(banks));
    fill_crysta_relations(*this, engine);

    std::vector<PdDataBase> data;
    std::vector<PowderReflnDataBase> reflections;
    data.reserve(experiments.size());
    reflections.reserve(experiments.size());
    for (std::size_t index = 0; index < experiments.size(); ++index) {
        const crysta::ComputedUnits& units = crysta::current(engine, engine.experiments[index]);
        const crysta::ComputedData& computed = units.data();
        PdDataBase columns;
        columns.d_spacing = shared_column(computed.d_spacing);
        columns.intensity_calc = shared_column(computed.intensity_calc);
        columns.intensity_bkg = shared_column(computed.intensity_bkg);
        columns.calc_status = status_column(computed.calc_status);
        columns.residual = shared_column(crysta::residual(engine.experiments[index]));
        data.push_back(std::move(columns));

        const crysta::ComputedRefln& refln = units.refln();
        PowderReflnDataBase rows;
        rows.structure_id = shared_column(refln.structure_id);
        rows.d_spacing = shared_column(refln.d_spacing);
        rows.sin_theta_over_lambda = shared_column(refln.sin_theta_over_lambda);
        rows.index_h = shared_column(refln.index_h);
        rows.index_k = shared_column(refln.index_k);
        rows.index_l = shared_column(refln.index_l);
        rows.f_calc = shared_column(refln.f_calc);
        rows.f_squared_calc = shared_column(refln.f_squared_calc);
        rows.position = shared_column(refln.position);
        reflections.push_back(std::move(rows));
    }
    for (std::size_t index = 0; index < experiments.size(); ++index) {
        BraggPdExperiment& bank = *experiments[index];
        PdDataBase& target = *bank.data;
        target.d_spacing = std::move(data[index].d_spacing);
        target.intensity_calc = std::move(data[index].intensity_calc);
        target.intensity_bkg = std::move(data[index].intensity_bkg);
        target.calc_status = std::move(data[index].calc_status);
        target.residual = std::move(data[index].residual);
        bank.refln = std::move(reflections[index]);
        bank.computed_source = std::move(sources[index]);
    }
}
// --- (edi ADR-0020 §1): the publication transaction -------------------------------

WorkStamps work_stamps(const Project& live) {
    WorkStamps stamps;
    stamps.experiment_inputs.reserve(live.experiments.size());
    for (const auto& bank_item : live.experiments) {
        stamps.experiment_inputs.push_back(detail::calculation_inputs(live.structures, *bank_item));
    }
    stamps.structure_inputs.reserve(live.structures.size());
    for (const auto& structure_item : live.structures) {
        stamps.structure_inputs.push_back(detail::geometry_inputs(*structure_item));
    }
    stamps.experiments = live.experiments.record();
    stamps.structures = live.structures.record();
    stamps.experiments_generation = live.experiments.generation();
    stamps.structures_generation = live.structures.generation();
    stamps.edits = live.edits_.record();
    stamps.edits_at = live.edits_.record()->epoch.value();
    stamps.aliases = live.aliases.record();
    stamps.constraints = live.constraints.record();
    stamps.relations = detail::relation_inputs(live.aliases, live.constraints);
    return stamps;
}

WorkSnapshot snapshot_for_work(const Project& live) {
    // The stamps first, then the copy: a write after this call is newer than both.
    WorkStamps stamps = work_stamps(live);
    WorkSnapshot snapshot{live, std::move(stamps)};
    // The copy keeps no reference to a live record: what it shares with the live project is
    // immutable buffers only.
    for (const auto& bank_item : snapshot.project.experiments) {
        bank_item->computed_source.reset();
    }
    for (const auto& structure_item : snapshot.project.structures) {
        structure_item->geometry_source.reset();
    }
    return snapshot;
}

namespace {
// The calculation's own two trace events: Calculating now, Calculated when the call returns.
class CalculationTrace {
   public:
    explicit CalculationTrace(const WorkSnapshot& snapshot) : snapshot_(snapshot) {
        if (snapshot_.trace) {
            snapshot_.trace(work::EventKind::Calculating);
        }
    }
    ~CalculationTrace() {
        if (snapshot_.trace) {
            snapshot_.trace(work::EventKind::Calculated);
        }
    }
    CalculationTrace(const CalculationTrace&) = delete;
    CalculationTrace& operator=(const CalculationTrace&) = delete;

   private:
    const WorkSnapshot& snapshot_;
};
}  // namespace

CalculationResult calculate(WorkSnapshot& snapshot, const work::CancelToken& token) {
    const CalculationTrace traced(snapshot);
    CalculationResult result;
    result.stamps = snapshot.stamps;
    if (token.cancelled()) {
        result.cancelled = true;
        return result;
    }
    std::string refusal;
    try {
        snapshot.project.calculate();
    } catch (const std::exception& error) {
        refusal = error.what();
    } catch (...) {
        refusal = "the calculation failed";
    }
    if (refusal.empty() == false && refusal.find_first_not_of(' ') == std::string::npos) {
        refusal = "the calculation was refused";
    }
    if (token.cancelled()) {
        result.cancelled = true;
        return result;
    }
    return stage_computed(snapshot.project, std::move(result.stamps), std::move(refusal));
}

CalculationResult stage_computed(const Project& calculated, WorkStamps stamps, std::string refusal) {
    CalculationResult result;
    result.stamps = std::move(stamps);
    result.refusal = std::move(refusal);
    // The dependents as the calculation completed them, so the live project holds them beside the arrays.
    for (const NamedParameter& dependent : named_dependents(calculated)) {
        result.completed.emplace_back(dependent.unique_name, dependent.parameter->value.get());
    }
    // The geometry is staged whatever the pattern did, as Project::calculate() stores it first.
    result.geometry.reserve(calculated.structures.size());
    for (const auto& structure_item : calculated.structures) {
        if (structure_item->geometry_current()) {
            result.geometry.emplace_back(structure_item->geometry);
        } else {
            result.geometry.emplace_back(std::nullopt);
        }
    }
    if (result.refusal.empty()) {
        for (const auto& bank_item : calculated.experiments) {
            if (!bank_item->computed_current()) {
                // Project::refresh_calculated_pattern() clears what it cannot calculate, and keeps no message.
                result.refusal = "the model cannot be calculated";
            }
        }
    }
    if (!result.refusal.empty()) {
        return result;
    }
    result.data.reserve(calculated.experiments.size());
    result.refln.reserve(calculated.experiments.size());
    for (const auto& bank_item : calculated.experiments) {
        PdDataBase columns;
        if (bank_item->data.has_value()) {
            const PdDataBase& computed = *bank_item->data;
            columns.d_spacing = computed.d_spacing;
            columns.intensity_calc = computed.intensity_calc;
            columns.intensity_bkg = computed.intensity_bkg;
            columns.calc_status = computed.calc_status;
            columns.residual = computed.residual;
        }
        result.data.push_back(std::move(columns));
        result.refln.push_back(bank_item->refln);
    }
    return result;
}

bool unchanged_since(const Project& live, const WorkStamps& stamps) {
    const std::shared_ptr<detail::EditRecord>& edits = live.edits_.record();
    if (live.experiments.record() != stamps.experiments ||
        live.structures.record() != stamps.structures ||
        live.experiments.generation() != stamps.experiments_generation ||
        live.structures.generation() != stamps.structures_generation || edits != stamps.edits ||
        edits->epoch.value() != stamps.edits_at || live.aliases.record() != stamps.aliases ||
        live.constraints.record() != stamps.constraints ||
        detail::relation_inputs(live.aliases, live.constraints) != stamps.relations) {
        return false;
    }
    if (stamps.experiment_inputs.size() != live.experiments.size() ||
        stamps.structure_inputs.size() != live.structures.size()) {
        return false;
    }
    for (std::size_t index = 0; index < live.experiments.size(); ++index) {
        if (detail::calculation_inputs(live.structures, *live.experiments[index]) !=
            stamps.experiment_inputs[index]) {
            return false;
        }
    }
    for (std::size_t index = 0; index < live.structures.size(); ++index) {
        if (detail::geometry_inputs(*live.structures[index]) != stamps.structure_inputs[index]) {
            return false;
        }
    }
    return true;
}

PublishOutcome publish(Project& live, CalculationResult&& result) {
    const WorkStamps& stamps = result.stamps;
    const std::size_t banks = live.experiments.size();
    const std::size_t structures = live.structures.size();
    // --- preflight: nothing the result depends on was written since the snapshot -----------------
    if (result.cancelled || !unchanged_since(live, stamps) || result.geometry.size() != structures) {
        return PublishOutcome::Superseded;
    }
    const bool refused = !result.refusal.empty();
    if (!refused && (result.data.size() != banks || result.refln.size() != banks)) {
        return PublishOutcome::Superseded;
    }
    for (std::size_t index = 0; index < banks; ++index) {
        if (!refused && !live.experiments[index]->data.has_value()) {
            return PublishOutcome::Superseded;
        }
    }
    // --- the dependents the calculation completed (edi ADR-0024) --------------------------------
    // A relation edited before the snapshot leaves the live dependents behind the copy the arrays were
    // calculated from: they are written first, and the arrays are then current against them. The sources
    // below read these values, so they follow the writes; should one of them fail, each value written is
    // still the one its relation gives.
    if (!result.completed.empty()) {
        std::map<std::string, Parameter*> by_name;
        for (const NamedSlot& slot : named_slots(live)) {
            by_name.emplace(slot.unique_name, slot.parameter);
        }
        for (const auto& [name, value] : result.completed) {
            const auto found = by_name.find(name);
            if (found != by_name.end() && found->second->value.get() != value) {
                found->second->value = value;
            }
        }
    }
    // --- the sources, encoded from the live project as the arrays describe it --------------------
    std::vector<std::shared_ptr<const detail::ComputedSource>> sources(banks);
    if (!refused) {
        for (std::size_t index = 0; index < banks; ++index) {
            sources[index] = std::make_shared<const detail::ComputedSource>(detail::ComputedSource{
                detail::calculation_inputs(live.structures, *live.experiments[index]), stamps.experiments,
                stamps.structures, stamps.edits, stamps.edits_at, live.link(), stamps.aliases,
                stamps.constraints, stamps.relations});
        }
    }
    std::vector<std::shared_ptr<const detail::GeometrySource>> geometry_sources(structures);
    for (std::size_t index = 0; index < structures; ++index) {
        if (result.geometry[index].has_value()) {
            geometry_sources[index] = std::make_shared<const detail::GeometrySource>(
                detail::GeometrySource{detail::geometry_inputs(*live.structures[index]), live.link(),
                                       stamps.aliases, stamps.constraints, stamps.relations});
        }
    }
    // --- the write pass: the state Project::calculate() on the live project would have left ------
    for (std::size_t index = 0; index < structures; ++index) {
        Structure& structure = *live.structures[index];
        structure.geometry = result.geometry[index].has_value()
                                 ? std::move(*result.geometry[index])
                                 : StructureGeometry{};
        structure.geometry_source = std::move(geometry_sources[index]);
    }
    for (std::size_t index = 0; index < banks; ++index) {
        BraggPdExperiment& bank = *live.experiments[index];
        if (refused) {
            if (bank.data.has_value()) {
                bank.data->clear_computed();
            }
            bank.refln.clear();
            bank.computed_source.reset();
            continue;
        }
        PdDataBase& target = *bank.data;
        target.d_spacing = std::move(result.data[index].d_spacing);
        target.intensity_calc = std::move(result.data[index].intensity_calc);
        target.intensity_bkg = std::move(result.data[index].intensity_bkg);
        target.calc_status = std::move(result.data[index].calc_status);
        target.residual = std::move(result.data[index].residual);
        bank.refln = std::move(result.refln[index]);
        bank.computed_source = std::move(sources[index]);
    }
    return PublishOutcome::Published;
}

void Project::refresh_calculated_pattern() {
    // / crysta — contract in model.hpp. A refusal clears EVERY bank: no computed column may
    // describe a model the calculation refused (calculate() clears them itself).
    try {
        calculate();
    } catch (const std::invalid_argument&) {  // NOLINT(bugprone-empty-catch) — cleared, not raised
    }
}

namespace {

// . The engine's reporting types become edi's HERE, in the adapter — the only place allowed to touch
// crysta (ADR-0003). Everything on edi's side of this line trades in edi value types, which is what
// keeps the public surface engine-free and independently compilable.
edi::IterationRecord to_edi(const crysta::IterationRecord& record) {
    return {record.iteration, record.rwp, record.reduced_chi_square, record.elapsed_ms,
            record.unevaluable_trials};
}

std::vector<edi::IterationRecord> to_edi(const std::vector<crysta::IterationRecord>& history) {
    std::vector<edi::IterationRecord> converted;
    converted.reserve(history.size());
    for (const crysta::IterationRecord& record : history) {
        converted.push_back(to_edi(record));
    }
    return converted;
}

edi::FitStatus to_edi(crysta::FitStatus status) {
    switch (status) {
        case crysta::FitStatus::Done:
            return edi::FitStatus::DONE;
        case crysta::FitStatus::MaxIter:
            return edi::FitStatus::MAX_ITER;
        case crysta::FitStatus::NoStep:
            return edi::FitStatus::NO_STEP;
        case crysta::FitStatus::Cancelled:
            return edi::FitStatus::CANCELLED;
        case crysta::FitStatus::Error:
            return edi::FitStatus::ERROR;
        case crysta::FitStatus::Unavailable:
            return edi::FitStatus::UNAVAILABLE;
        case crysta::FitStatus::Superseded:
            return edi::FitStatus::SUPERSEDED;
    }
    return edi::FitStatus::ERROR;
}

// Wrap an edi-typed subscriber as the engine's callback. An ABSENT subscriber yields an EMPTY engine
// callback, so the engine's own `if (on_iteration)` guard means no crossing at all — that is the
// zero-overhead guarantee, and it is a call-count property rather than a timing one.
// `paths` names the engine's parameter columns by edi identity path (identity_paths, below); a streamed
// record carries the step's values under them.
crysta::IterationCallback to_engine_callback(const IterationCallback& subscriber,
                                             double dof,
                                             std::chrono::steady_clock::time_point started,
                                             std::vector<std::string> paths) {
    if (!subscriber) {
        return {};
    }
    return [subscriber, dof, started, paths = std::move(paths)](const crysta::IterationRecord& progress) {
        // The engine's raw progress carries chi_square; a subscriber sees the SAME derived values
        // the history and the machine record carry, so the streaming and after-the-fact views of
        // one iteration never disagree.
        const double elapsed_ms = std::chrono::duration<double, std::milli>(
                                      std::chrono::steady_clock::now() - started)
                                      .count();
        IterationRecord record{progress.iteration, progress.rwp, progress.chi_square / dof, elapsed_ms,
                               progress.unevaluable_trials};
        if (progress.parameters.size() == paths.size()) {
            for (std::size_t index = 0; index < paths.size(); ++index) {
                if (!paths[index].empty()) {
                    record.values[paths[index]] = progress.parameters[index];
                }
            }
        }
        subscriber(record);
    };
}

// The engine's parameter columns by edi identity path, through the resolver the fit's result is
// translated with; empty where a label does not resolve (the result's translation then refuses the
// fit). Only for a subscriber: with none, nothing is resolved.
template <typename Resolve>
std::vector<std::string> identity_paths(const IterationCallback& subscriber,
                                        const std::vector<std::string>& labels, Resolve resolve) {
    std::vector<std::string> paths;
    if (!subscriber) {
        return paths;
    }
    paths.reserve(labels.size());
    for (const std::string& label : labels) {
        std::optional<detail::ResolvedParameter> resolved = resolve(label);
        paths.push_back(resolved ? resolved->path : std::string());
    }
    return paths;
}

// THE FIT-COMPLETION TAIL, shared by all three fit paths — the part a NEW fit path could forget. Each path
// spells its own `detail::write_back` and then hands off here. Completing a fit writes BOTH halves of the
// model — the fitted values and the stored calculated pattern that sits beside them. Only the values were
// written, so `data->intensity_calc` kept the PRE-FIT series and every consumer reading it after a fit read
// the model the fit had just replaced, silently. The refresh is `calculate()`, the ORDINARY model-only
// forward path, so the stored pattern equals a fresh calculate at the fitted state; this changes WHEN the
// series is written, never what the engine computes. It runs LAST, after the value write-back and every
// completion pass, because the pattern must describe the model a SAVE would serialise. The three paths share
// one function rather than three agreeing copies: a fourth entry point cannot forget a step it never spells.
void publish_fit_state(Project& project, crysta::Project& converted) {
    for (const auto& structure : project.structures) {  // every structure (phase)
        rebalance_positional_fit_state(*structure);  // review-9 F1: lossless snapshot hand-off
    }
    // Every dependent as crysta completed it on the fit's own project (Wyckoff followers, cell
    // siblings and constrained parameters), values and e.s.d.s.
    copy_dependents(converted, project, Completion::ValuesAndUncertainties);
    project.refresh_calculated_pattern();  // The pattern follows the model it describes
}

// The fit's result as the project records it (`_fit_result`, diffraction-lib's names, and each bank's share
// for a joint fit), from what the fit returned — the same numbers the reports print. The status label is
// crysta's machine-record spelling; the profile function is the peak type the experiments share (left out
// when they differ), the background edi's only one.
void record_fit_result(Project& project, const FitResultBase& outcome, std::size_t considered) {
    FitResultRecord record;
    record.result_kind = "deterministic";
    record.success = outcome.status == FitStatus::DONE;
    switch (outcome.status) {
        case FitStatus::DONE: record.exit_reason = "done"; break;
        case FitStatus::MAX_ITER: record.exit_reason = "max_iter"; break;
        case FitStatus::NO_STEP: record.exit_reason = "no_step"; break;
        case FitStatus::CANCELLED: record.exit_reason = "cancelled"; break;
        case FitStatus::ERROR: record.exit_reason = "error"; break;
        case FitStatus::UNAVAILABLE: record.exit_reason = "unavailable"; break;
        case FitStatus::SUPERSEDED: record.exit_reason = "superseded"; break;
    }
    record.message = record.exit_reason;
    record.iterations = outcome.iterations;
    record.fitting_time = outcome.elapsed_ms / 1000.0;
    record.reduced_chi_square = outcome.reduced_chi_square;
    const std::size_t n_free = outcome.values.size();
    record.objective_name = "chi_square";
    record.objective_value =
        outcome.reduced_chi_square * detail::reduced_chi_square_dof(outcome.n_points_fitted, n_free);
    record.n_data_points = static_cast<int>(outcome.n_points_fitted);
    // diffraction-lib's n_parameters is every parameter the fit considered (its structures' and its experiments'
    // parameters, the active profile family only): the engine project the fit ran on, the count crysta's own
    // CLI fit writes. edi's Project.parameters walk lists every profile family's fields, whatever the beam
    // mode, so it is not that count. n_free_parameters is the ones it varied.
    record.n_parameters = static_cast<int>(considered);
    record.n_free_parameters = static_cast<int>(n_free);
    record.degrees_of_freedom =
        outcome.n_points_fitted > n_free ? static_cast<int>(outcome.n_points_fitted - n_free) : 0;
    record.covariance_available = !outcome.uncertainty.empty();
    record.prof_wr_factor = outcome.rwp;
    std::optional<std::string> profile;
    bool shared = true;
    for (const auto& experiment_item : project.experiments) {
        const std::optional<std::string>& type = experiment_item->peak.type;
        shared = shared && type.has_value() && (!profile.has_value() || *profile == *type);
        profile = type;
    }
    if (shared && profile.has_value()) {
        record.profile_function = *profile;
    }
    // Review-6 F11: the background model the banks declared, left out when they differ, as the profile above.
    std::optional<std::string> background;
    bool same_background = true;
    for (const auto& experiment_item : project.experiments) {
        const std::string& type = experiment_item->background_type;
        same_background = same_background && (!background.has_value() || *background == type);
        background = type;
    }
    if (same_background && background.has_value()) {
        record.background_function = *background;
    }
    record.descent = outcome.descent;  // review-1 F3: the descent that produced it
    project.fit_result = std::move(record);
    for (const auto& experiment_item : project.experiments) {
        ExperimentBase& experiment = *experiment_item;
        experiment.fit_n_data_points.reset();
        experiment.fit_prof_wr_factor.reset();
        experiment.fit_chi_square.reset();
        for (const BankMetric& bank : outcome.banks) {
            if (bank.name == experiment.name) {
                experiment.fit_n_data_points = static_cast<int>(bank.n_points);
                experiment.fit_prof_wr_factor = bank.rwp;
                experiment.fit_chi_square = bank.chi_square;
            }
        }
    }
}

}  // namespace

std::vector<std::string> descent_ids() { return crysta::descent_ids(); }

std::string default_descent() { return crysta::kDefaultDescent; }
double default_chi_square_tolerance() { return crysta::kDefaultChiSquareTolerance; }

// Validate a descent id at EDI's boundary — against the linked crysta registry (never a
// transcribed set), naming the registered ids on refusal. edi never passes an unknown id
// through for crysta to reject: the engine's own message is correct but reaches the user from
// the wrong surface. Empty means "no selection" (the historical default path). Called by the
// surface setter (bindings) and again before any fit work below — defense in depth for a value
// that is model state and could have been set from C++ directly.
void validate_descent(const std::string& descent, const std::string& where) {
    if (descent.empty()) {
        return;
    }
    const std::vector<std::string>& ids = crysta::descent_ids();
    if (std::find(ids.begin(), ids.end(), descent) != ids.end()) {
        return;
    }
    std::string registered;
    for (const std::string& id : ids) {
        registered += (registered.empty() ? "" : ", ") + id;
    }
    throw std::invalid_argument(where + ": unknown descent '" + descent +
                                "' (registered descents: " + registered + ")");
}

namespace {

// The project's declared minimization conditions as one crysta request — the descent
// (`_minimizer.descent`, empty -> crysta's default), the bounded iteration budget and the
// chi-square stop (`_minimizer.chi_square_tolerance`, 0 -> crysta's default).
crysta::DescentRequest declared_request(const std::string& descent, int max_iterations,
                                        double chi_square_tolerance) {
    crysta::DescentRequest request;
    if (!descent.empty()) {
        request.descent = descent;
    }
    request.max_iterations = detail::bounded_max_iterations(max_iterations);
    if (chi_square_tolerance > 0.0) {
        request.chi_square_tolerance = chi_square_tolerance;
    }
    return request;
}

}  // namespace

FitResultBase Project::fit(const std::vector<double>& grid, const std::vector<double>& observed,
                           const std::vector<double>& sigma, const IterationCallback& on_iteration,
                           const PreambleCallback& on_start, const CancelCallback& should_cancel) {
    // Boundary checks (clean fail-closed messages before any engine contact — ADR-0003 pt 5): a
    // structured ValueError, never a partial/silent result. The model is written only on success.
    // The checks themselves are edi-side policy (fit_policy.cpp).
    validate_descent(descent, "edi fit");
    detail::validate_fit_request(grid, observed, sigma, *this);
    try {
        // Stateless rebuild-per-fit: the same single crysta-touching build path
        // (build_crysta_project + select_scattering) the forward accessors use — no persistent
        // CachedForwardModel (a later C09 slice), and nothing here forecloses it.
        // A project of several structures (phases), or an experiment that disables its one link, fits
        // through crysta's phase-sum residual over every structure; any other through the
        // single-structure residual, as before.
        const bool phases = structures.size() > 1 || experiment().linked_structures.size() != 1 ||
                            !experiment().linked_structure().enabled.get();
        crysta::Project project = [&]() -> crysta::Project {
            if (phases) {
                return crysta::Project(to_crysta_structures(*this),
                                       std::vector<crysta::BraggPdExperiment>{detail::to_crysta_experiment(experiment())});
            }
            return build_crysta_project(structure(), experiment());
        }();
        fill_crysta_relations(*this, project);
        // The atom-site rule on exactly this fit's participants: the selected bank's enabled phases.
        detail::require_populated_participants(project, "edi fit");
        if (phases) {
            // The phase-sum residual reads the measured pattern from the experiment, and masks it itself.
            project.experiment().data = crysta::PdDataBase(grid, observed, sigma);
        }
        const std::size_t considered = project.collect_parameters().size();  // _fit_result
        make_fit_ready(project.experiment());

        // Measured pattern -> mask the model's excluded regions, exactly as the crysta CLI does
        // (apply_exclusions on the loaded project's regions); the caller supplies grid/observed/sigma.
        crysta::ResidualPattern measured{grid, observed, sigma};
        // Points as READ, before the mask — the caller-owned authority for `n_points_loaded`. It
        // must be taken here: apply_exclusions replaces `measured`, and the provider only ever
        // sees the masked pattern.
        const std::size_t n_points_loaded = measured.grid.size();
        measured = crysta::apply_exclusions(measured, experiment().excluded_regions);
        if (measured.grid.empty()) {
            throw std::invalid_argument(
                "edi fit: no measured data remains after applying the excluded regions");
        }

        // Free set from the model's own bracket flags (the crysta CLI `--free model` path); the
        // adapter already propagated each Parameter.free into the crysta model, so this is
        // byte-identical to the CLI's free_from_model on the same project.
        std::vector<crysta::FreeParameter> free = crysta::free_from_model(project);
        if (free.empty()) {
            throw std::invalid_argument(
                "edi fit: no free parameters (mark parameters refinable via their free flags)");
        }

        const auto finish = [&](auto& provider) -> FitResultBase {

            // Pre-fit values, captured from the provider BEFORE the minimizer runs — the same
            // labels()/values() pairing the crysta CLI uses to build its own start column. Held as raw
            // engine labels here and translated below through the same resolver as the refined values,
            // so `start` and `values` end up sharing one key set and no engine label escapes.
            std::map<std::string, double> start_by_label;
            {
                const std::vector<std::string> labels = provider.labels();
                const std::vector<double> values = provider.values();
                for (std::size_t index = 0; index < labels.size() && index < values.size(); ++index) {
                    start_by_label[labels[index]] = values[index];
                }
            }

            // dof for the per-iteration reduced chi-square, from the MASKED length — the same
            // denominator crysta's own record uses.
            const double dof = detail::reduced_chi_square_dof(provider.n_data(), provider.labels().size());
            // Pre-fit record: the initial model's Rwp/reduced-chi2 at the start params, via crysta's
            // shared residual seam — no fit, no numerics change. Always computed (engine-side, not a
            // host crossing) so the post-hoc report can render the starting row; the streamed surface
            // additionally gets it in the preamble below.
            const crysta::IterationRecord crysta_pre_fit = crysta::pre_fit_record(provider, dof);
            const IterationRecord pre_fit{crysta_pre_fit.iteration, crysta_pre_fit.rwp,
                                          crysta_pre_fit.reduced_chi_square, crysta_pre_fit.elapsed_ms,
                                          crysta_pre_fit.unevaluable_trials};
            // Preamble: fired ONCE here — after the provider is built (so the counts are
            // known) and the pre-fit is evaluated, BEFORE the LM loop. Empty callback => no host
            // crossing. Single-bank path: `banks` empty, mode single (mirrors crysta).
            if (on_start) {
                on_start(FitPreamble{/*joint=*/false, /*banks=*/{}, n_points_loaded, provider.n_data(),
                                     provider.n_free(), pre_fit});
            }
            const std::vector<std::string> paths =
                identity_paths(on_iteration, provider.labels(), [this](const std::string& label) {
                    return detail::resolve_project_label(*this, experiment(), label);
                });
            const auto fit_start = std::chrono::steady_clock::now();
            crysta::IterationHistoryCollector collector(dof, fit_start);
            // The subscriber is composed ON TOP of the always-on collector, so history exists whether
            // or not anyone subscribed, and an absent subscriber crosses no host boundary at all.
            // (F-bound) /: the project's declared `_minimizer.*` conditions — the iteration budget
            // (absent: the historical 50 cap), the descent and the chi-square stop. A declared
            // descent or tolerance goes through crysta's registry entry point (DescentRequest, id
            // validated above); a project declaring neither keeps the historical direct call
            // byte-for-byte, so the default path cannot move a number by construction. The request's
            // seed/polish pair mirrors `separable_linear=true` exactly (crysta descent.hpp: the
            // ordinary provider overloads set both from it).
            crysta::DescentRequest request =
                declared_request(descent, minimizer_max_iterations, minimizer_chi_square_tolerance);
            const crysta::FitResultBase result = [&] {
                if (descent.empty() && minimizer_chi_square_tolerance <= 0.0) {
                    return crysta::fit_problem(
                        provider, /*separable_linear=*/true, request.max_iterations,
                        collector.callback(to_engine_callback(on_iteration, dof, fit_start, paths)),
                        should_cancel);  // The cooperative cancel
                }
                request.on_iteration =
                    collector.callback(to_engine_callback(on_iteration, dof, fit_start, paths));
                request.should_cancel = should_cancel;
                return crysta::fit_problem(provider, request);
            }();
            const double elapsed_ms = std::chrono::duration<double, std::milli>(
                                          std::chrono::steady_clock::now() - fit_start)
                                          .count();

            // Translate EVERY crysta result label to an edi-owned parameter (path + write-back target)
            // FIRST, total and fail-closed: an unmapped/unknown label is a structured error, never a
            // silent drop or a raw-label passthrough. Only once the whole result resolves do we build the
            // edi-owned FitResultBase and apply the model write-back — so no crysta engine label ever
            // crosses the `import edi` boundary and a partial/garbled result can never mutate the model.
            std::vector<detail::RefinedValue> refined;
            refined.reserve(result.values.size());
            for (const auto& [label, value] : result.values) {
                std::optional<detail::ResolvedParameter> resolved =
                    detail::resolve_project_label(*this, experiment(), label);
                if (!resolved) {
                    throw std::invalid_argument(
                        "edi fit: crysta result label '" + label +
                        "' does not resolve to an edi model parameter (unmapped engine label)");
                }
                const auto found = result.uncertainty.find(label);
                refined.push_back({std::move(*resolved), value,
                                   found != result.uncertainty.end() ? found->second : 0.0});
            }

            FitResultBase outcome;
            outcome.rwp = result.rwp;
            outcome.reduced_chi_square = result.reduced_chi_square;
            outcome.iterations = result.iterations;
            outcome.converged = result.converged;
            outcome.n_points_loaded = n_points_loaded;
            outcome.n_points_fitted = provider.n_data();
            outcome.iterations_history = to_edi(collector.history());
            outcome.pre_fit = pre_fit;
            outcome.elapsed_ms = elapsed_ms;
            outcome.status = to_edi(crysta::classify_fit_status(result));
            // The engine's boundary-contact counters, verbatim — never recomputed and never
            // defaulted: a zero here is the engine's zero, not edi's.
            outcome.unevaluable_trials = result.unevaluable_trials;
            outcome.terminal_unevaluable_trials = result.terminal_unevaluable_trials;
            // Engine-keyed copies for the machine record (see FitResultBase::engine_values).
            outcome.engine_values = result.values;
            outcome.engine_uncertainty = result.uncertainty;
            outcome.descent = result.descent;
            outcome.reflections_folded = result.reflections_folded;
            outcome.structure_factor_evaluations = result.structure_factor_evaluations;
            // Key the result by the edi-owned identity path (no crysta label leaked).
            for (const detail::RefinedValue& item : refined) {
                outcome.values[item.resolved.path] = item.value;
                outcome.uncertainty[item.resolved.path] = item.uncertainty;
            }
            // The pre-fit values, translated through the SAME resolver so `start` is keyed identically
            // to `values`. A label that resolved above always resolves here (same model, same grammar).
            for (const auto& [label, value] : start_by_label) {
                std::optional<detail::ResolvedParameter> resolved =
                    detail::resolve_project_label(*this, experiment(), label);
                if (resolved) {
                    outcome.start[resolved->path] = value;
                }
            }
            // `banks` stays EMPTY on the single-bank path: crysta reports no per-bank block for a
            // single-file fit, and fabricating one from the global metrics would be edi inventing a
            // number the engine never produced.

            // Write the refined value/esd back onto the edi model Parameters (all labels resolved above).
            detail::write_back(refined);
            crysta::write_fit_result_into(project, result);  // crysta completes the dependents
            publish_fit_state(*this, project);
            record_fit_result(*this, outcome, considered);
            return outcome;
        };
        if (phases) {
            crysta::PhaseSumResidual provider(project);
            return finish(provider);
        }
        // Delegate the ENTIRE LM loop to crysta's public minimizer at the CLI defaults
        // (separable_linear, max_iter 50, CutoffPolicy::Off, SolverRung::Lm, chi2/param tol) — the
        // defaults fit_problem already carries, so the fit is bit-comparable to the CLI oracle.
        // The one structure's declared scattering lengths; a phase fit reads each phase's own.
        crysta::NeutronScattering scattering = select_scattering(structure());
        crysta::PowderBraggResidual provider(project, scattering, std::move(measured),
                                             experiment().instrument.setup_twotheta_bank.value, experiment().peak.cutoff_fwhm,
                                             std::move(free));
        return finish(provider);
    } catch (const std::invalid_argument&) {
        throw;  // already a clean, structured ValueError — surface as-is.
    } catch (const ValidationError&) {
        throw;  // a coded refusal keeps its codes
    } catch (const std::exception& error) {
        // Any other engine/model failure on the fit path fails closed as a structured ValueError.
        throw std::invalid_argument(std::string("edi fit failed: ") + error.what());
    }
}

FitResultBase Project::fit_independent(const IterationCallback& on_iteration,
                                          const PreambleCallback& on_start,
                                          const ScanStartCallback& on_scan_start,
                                          const FileCompleteCallback& on_file_complete,
                                          const CancelCallback& should_cancel) {
    // Review-2 F2: this entry serves EXACTLY `independent`, and it reaches the shared scan body
    // DIRECTLY. It used to delegate to fit_sequential(), which accepted either scan mode — so
    // an `independent` project also succeeded through the explicitly sequential entry, whose
    // shipped binding promises it raises. Sharing an implementation is right; making the public
    // mode-specific entries aliases of each other is what opened the escape.
    if (fitting_mode != "independent") {
        throw std::invalid_argument("edi fit_independent: _fitting_mode.type is '" +
                                    fitting_mode +
                                    "' - this entry point serves exactly the 'independent' mode");
    }
    return fit_scan(on_iteration, on_start, on_scan_start, on_file_complete, should_cancel);
}

FitResultBase Project::fit_sequential(const IterationCallback& on_iteration,
                                         const PreambleCallback& on_start,
                                         const ScanStartCallback& on_scan_start,
                                         const FileCompleteCallback& on_file_complete,
                                         const CancelCallback& should_cancel) {
    // Serves EXACTLY `sequential` — the scan family is no longer accepted here.
    if (fitting_mode != "sequential") {
        throw std::invalid_argument("edi fit_sequential: _fitting_mode.type is '" +
                                    fitting_mode +
                                    "' - this entry point serves exactly the 'sequential' mode");
    }
    return fit_scan(on_iteration, on_start, on_scan_start, on_file_complete, should_cancel);
}

namespace {

// ---: the scan-event observation seam -------------------------------------------------
//
// crysta's driver exposes no per-file hook, and the owner's committed rule makes
// analysis/results.csv the ONE carry-forward state source: the driver APPENDS each file's row
// before the next file's fit ("numbers commit as produced"). So edi derives its per-file
// completion event from the committed rows themselves — read when the row count grows, parsed
// from the same plain-cell contract crysta writes — and NEVER from iteration-number restarts,
// the heuristic the packet rules out by name. The walk below mirrors crysta's own (directory
// regular files + `*`/`?` glob + sort + optional reverse) so the preamble's N is the N crysta
// will fit; a mismatch cannot arise from a second convention, only from the directory changing
// mid-call.

// Minimal glob over a file NAME (`*` and `?` only) — byte-for-byte crysta's matcher
// (src/core/sequential.cpp), which is the point: the two walks must agree.
bool scan_glob_match(const std::string& pattern, const std::string& name) {
    std::size_t p = 0;
    std::size_t n = 0;
    std::size_t star = std::string::npos;
    std::size_t star_n = 0;
    while (n < name.size()) {
        if (p < pattern.size() && (pattern[p] == '?' || pattern[p] == name[n])) {
            ++p;
            ++n;
        } else if (p < pattern.size() && pattern[p] == '*') {
            star = p++;
            star_n = n;
        } else if (star != std::string::npos) {
            p = star + 1;
            n = ++star_n;
        } else {
            return false;
        }
    }
    while (p < pattern.size() && pattern[p] == '*') {
        ++p;
    }
    return p == pattern.size();
}

// The scan walk's size. nullopt when the walk is not resolvable (missing directory, fs error):
// that state is crysta's refusal to make, and a preamble for it would be a fabrication — the
// caller skips the event and lets the driver refuse.
std::optional<int> count_scan_files(const std::filesystem::path& scan_dir,
                                    const std::string& pattern) {
    std::error_code error;
    if (!std::filesystem::is_directory(scan_dir, error) || error) {
        return std::nullopt;
    }
    int count = 0;
    std::filesystem::directory_iterator it(scan_dir, error);
    if (error) {
        return std::nullopt;
    }
    for (const std::filesystem::directory_entry& entry : it) {
        if (entry.is_regular_file(error) && !error &&
            scan_glob_match(pattern, entry.path().filename().string())) {
            ++count;
        }
    }
    return count;
}

// The one numeric-cell device for this reader, mirroring io.cpp's `to_double` device-for-device:
// a classic-("C")-locale-imbued istringstream, fully consumed or refused. BOTH properties are
// load-bearing and neither may be traded for the other:
//   * portable — deliberately NOT std::from_chars: libc++ (Apple/AppleClang) `= delete`s the
//     floating-point overload, so that call does not compile on macOS (it broke crysta's own
//     macOS CI, PR #21, and a fresh instance here broke the owner's Mac build on this cycle's
//     head — the documented class, re-shipped; hence one shared device, not per-site calls);
//   * locale-independent — never strtod/std::stod, which honour the ambient LC_NUMERIC, so a
//     comma-decimal locale would silently mis-parse the committed `4.8056` cell.
template <typename Value>
bool parse_csv_cell(const std::string& cell, Value& out) {
    std::istringstream stream(cell);
    stream.imbue(std::locale::classic());
    stream >> out;
    return !stream.fail() && stream.eof();
}

// One results.csv row's facts for the per-file event. The row shape is crysta's own contract
// (cells file_path, reduced_chi_square, success, iterations...); a row that does not parse
// yields nullopt and fires nothing — the driver's own resume validation is the authority on
// malformed files, never this reader. The live event hands over the cells directly (crysta's
// on_file_complete); only the preamble's resume rows are read from the file.
std::optional<ScanFileRecord> scan_record_from_cells(const std::vector<std::string>& cells) {
    if (cells.size() < 4) {
        return std::nullopt;
    }
    ScanFileRecord record;
    const std::size_t slash = cells[0].rfind('/');
    record.file_name = slash == std::string::npos ? cells[0] : cells[0].substr(slash + 1);
    record.converged = cells[2] == "True";
    if (!parse_csv_cell(cells[1], record.reduced_chi_square)) {
        return std::nullopt;
    }
    if (!parse_csv_cell(cells[3], record.iterations)) {
        return std::nullopt;
    }
    return record;
}

// A committed results.csv line (plain comma-joined cells) as a record — the resume read.
std::optional<ScanFileRecord> scan_record_from_row(const std::string& line) {
    std::vector<std::string> cells;
    std::size_t start = 0;
    while (start <= line.size()) {
        const std::size_t comma = line.find(',', start);
        if (comma == std::string::npos) {
            cells.push_back(line.substr(start));
            break;
        }
        cells.push_back(line.substr(start, comma - start));
        start = comma + 1;
    }
    return scan_record_from_cells(cells);
}

// Every currently committed data row (header skipped). An unreadable or missing file reads as
// zero rows — the same view crysta's driver takes of a fresh scan; a torn/foreign file is the
// driver's own fail-closed refusal, which edi does not preempt here.
std::vector<ScanFileRecord> read_scan_rows(const std::filesystem::path& csv_path) {
    std::vector<ScanFileRecord> rows;
    std::ifstream in(csv_path);
    if (!in) {
        return rows;
    }
    std::string line;
    bool header = true;
    while (std::getline(in, line)) {
        if (header) {
            header = false;
            continue;
        }
        if (line.empty()) {
            continue;
        }
        std::optional<ScanFileRecord> record = scan_record_from_row(line);
        if (record.has_value()) {
            rows.push_back(std::move(*record));
        }
    }
    return rows;
}

}  // namespace

// The ONE scan implementation. Both public scan entries reach it after proving their own exact
// token, so the code stays single while the public surface stays mode-specific.
FitResultBase Project::fit_scan(const IterationCallback& on_iteration,
                                   const PreambleCallback& on_start,
                                   const ScanStartCallback& on_scan_start,
                                   const FileCompleteCallback& on_file_complete,
                                   const CancelCallback& should_cancel) {
    // The ONE native entry point the `sequential` fitting mode delegates to. The whole loop, the
    // carry-forward/resume state (the CSV) and the results.csv writer are crysta's — one
    // crysta::fit_project call on the converted project (criterion 6's one writer, literal); edi
    // contributes conversion, translation and these boundary refusals, nothing else. Review-1 F6:
    // `on_start` stays UNFIRED. A preamble carries the pre-fit chi-square of the fit it precedes;
    // a scan's first fit is against the first scan FILE, whose provider only crysta's loop
    // builds, so edi could only report the template's number — a value no fit in this run uses.
    // The per-file iteration callbacks below are forwarded instead, renumbered into ONE
    // scan-level sequence: the raw per-file numbering restarted at 1 for every file, so a
    // subscriber saw several ascending runs presented as one descent, and the record's own rule
    // (history indexed 1..N, length == iterations) could not hold over it. Internal invariant:
    // only the two public scan entries call this, each having proved its own exact token. Kept as
    // a refusal rather than an assert because it is the last line of defence if a future caller
    // is added.
    if (!is_scan_fitting_mode(fitting_mode)) {
        throw std::invalid_argument("edi fit_scan: _fitting_mode.type is '" + fitting_mode +
                                    "' - the scan body serves only 'sequential' and 'independent'");
    }
    if (experiments.size() != 1) {
        throw std::invalid_argument(
            "edi fit_sequential: the project has " + std::to_string(experiments.size()) +
            " experiments (a sequential fit iterates scan data files against exactly one "
            "template experiment)");
    }
    // The --dry lesson: the resolver must work on a project LOADED from disk — the scan
    // data_dir and analysis/results.csv resolve against the project directory.
    if (path.empty()) {
        throw std::invalid_argument(
            "edi fit_sequential: this project has no directory (never loaded or saved) - the "
            "scan data_dir and analysis/results.csv resolve against it; load or save_as first");
    }
    if (!sequential_fit.declared()) {
        throw std::invalid_argument(
            "edi fit_sequential: the project declares no _sequential_fit.data_dir - a "
            "sequential fit needs the scan directory");
    }
    validate_descent(descent, "edi fit_sequential");
    try {
        // Stateless rebuild-per-fit, the single-bank shape: one crysta Project over the shared
        // structure and the template experiment, with the identity and declarations the
        // sequential driver reads (structure name and experiment name feed the results.csv
        // column grammar; the scan block and iteration bound are the declared inputs).
        // The engine refuses a sequential or independent fit of several linked structures; this
        // single-structure build would otherwise fit the first structure alone and ignore the rest.
        if (structures.size() > 1 || experiment().linked_structures.size() != 1 ||
            !experiment().linked_structure().enabled.get()) {
            throw std::invalid_argument(
                "edi fit_sequential: a sequential or independent fit with several linked structures is not "
                "supported yet");
        }
        crysta::Project cproject = build_crysta_project(structure(), experiment());
        detail::require_populated_participants(cproject, "edi fit_sequential");
        fill_crysta_relations(*this, cproject);
        make_fit_ready(cproject.experiment());
        cproject.structure().name = structure().name;
        cproject.structure().scattering_lengths_fm = structure().scattering_lengths_fm;
        // Review-1 F4: forward the DECLARED mode, never a hard-coded one — pinning
        // "sequential" here would have run an `independent` project chained, silently answering
        // a different question than the project declares.
        cproject.fitting_mode = crysta::model_token_from_file(
            crysta::TokenField::FittingMode, crysta::BeamModeEnum::TimeOfFlight, fitting_mode);
        cproject.minimizer_max_iterations = minimizer_max_iterations;
        // Crysta's driver runs every inner fit under the declared descent and
        // tolerance and records them per row in analysis/results-provenance.csv.
        cproject.minimizer_descent = descent;
        cproject.minimizer_chi_square_tolerance = minimizer_chi_square_tolerance;
        cproject.minimizer_type = minimizer_type;
        fill_crysta_sequential(sequential_fit, cproject.sequential_fit);
        cproject.path = path;

        // The scan's own preamble and per-file completion events. The walk mirrors
        // crysta's (the helpers above) and the resume rows come from results.csv, read ONCE, for
        // the preamble only. An unresolvable walk fires nothing — crysta's driver is about to
        // refuse it with the authoritative message, and a preamble for a scan that cannot start
        // would report a fabrication. The per-file completion event is crysta's own
        // on_file_complete, fired with the row it just appended — no file polling and no CSV
        // parsing mid-scan (the retired watcher re-read the whole file per file: quadratic). The
        // two populations split by construction: the preamble carries the rows already
        // committed, and crysta fires only the rows this call appends.
        const std::filesystem::path project_root(path);
        // A dry run reads the scan data in place (scan_data_root) while results.csv lives
        // under `path`, the scratch directory that receives what the fit writes.
        const std::filesystem::path data_root(scan_data_root.empty() ? path : scan_data_root);
        cproject.scan_data_root = scan_data_root;
        const std::filesystem::path csv_path = project_root / "analysis" / "results.csv";
        bool preamble_delivered = false;
        if (on_scan_start) {
            const std::optional<int> total_files =
                count_scan_files(data_root / sequential_fit.data_dir, sequential_fit.file_pattern);
            if (total_files.has_value()) {
                ScanPreamble scan_preamble;
                scan_preamble.total_files = *total_files;
                // The rows THEMSELVES, not counts over them: a consumer needs the prior
                // failures' NAMES and χ² values to report the scan it is resuming (gate 6),
                // and counts alone could only ever be paired with this call's facts.
                // A dry run's results under `path` start as the loaded project's committed rows
                // (crysta seeds them when absent), so its resume state is read from there.
                const std::filesystem::path resume_csv =
                    std::filesystem::exists(csv_path) || scan_data_root.empty()
                        ? csv_path
                        : data_root / "analysis" / "results.csv";
                scan_preamble.completed_rows = read_scan_rows(resume_csv);
                on_scan_start(scan_preamble);
                preamble_delivered = true;
            }
        }

        const auto fit_start = std::chrono::steady_clock::now();
        // Amends review-1 F6 WITHOUT repealing it: the iteration SUBSCRIBER receives scan-level
        // renumbered records — one ascending sequence — but ONLY when this call DELIVERED the
        // honest whole-scan preamble (ScanPreamble above), which is exactly what F6's refusal
        // was missing. A caller subscribing on_iteration alone gets what it always got —
        // nothing. It is the FULL-verbosity diagnostic stream; surfaces suppress it by
        // default.
        // The RETAINED history is bounded by one file. `file_history` holds the file in flight
        // and `last_file_history` the last file crysta committed; the terminal record carries
        // the history of the fit its result describes (the last committed file, or the file a
        // cancel stopped), indexed 1..N with N that fit's own iteration count — so a long scan
        // never holds the whole scan's iterations.
        auto scan_steps = std::make_shared<int>(0);
        auto file_history = std::make_shared<std::vector<IterationRecord>>();
        auto last_file_history = std::make_shared<std::vector<IterationRecord>>();
        crysta::IterationCallback engine_callback =
            [scan_steps, file_history, fit_start, &on_iteration,
             preamble_delivered](const crysta::IterationRecord& progress) {
                const double elapsed_ms = std::chrono::duration<double, std::milli>(
                                              std::chrono::steady_clock::now() - fit_start)
                                              .count();
                IterationRecord record{++*scan_steps, progress.rwp, progress.reduced_chi_square,
                                       elapsed_ms, progress.unevaluable_trials};
                if (on_iteration && preamble_delivered) {
                    on_iteration(record);
                }
                record.iteration = static_cast<int>(file_history->size()) + 1;
                file_history->push_back(record);
            };
        const crysta::FileCompleteCallback engine_file_complete =
            [file_history, last_file_history,
             &on_file_complete](const std::vector<std::string>& row) {
                std::swap(*last_file_history, *file_history);
                file_history->clear();
                if (on_file_complete) {
                    const std::optional<ScanFileRecord> record = scan_record_from_cells(row);
                    if (record.has_value()) {
                        on_file_complete(*record);
                    }
                }
            };
        const crysta::FitResultBase result =
            crysta::fit_project(cproject, engine_callback, should_cancel, engine_file_complete);
        const double elapsed_ms = std::chrono::duration<double, std::milli>(
                                      std::chrono::steady_clock::now() - fit_start)
                                      .count();

        // Translate the terminal result exactly as fit does: every crysta label resolves to
        // an edi parameter BEFORE any write-back, fail-closed; a completed-scan resume returns
        // empty maps and mutates nothing.
        std::vector<detail::RefinedValue> refined;
        refined.reserve(result.values.size());
        for (const auto& [label, value] : result.values) {
            std::optional<detail::ResolvedParameter> resolved =
                detail::resolve_label(structure(), experiment(), label);
            if (!resolved) {
                throw std::invalid_argument(
                    "edi fit_sequential: crysta result label '" + label +
                    "' does not resolve to an edi model parameter (unmapped engine label)");
            }
            const auto found = result.uncertainty.find(label);
            refined.push_back({std::move(*resolved), value,
                               found != result.uncertainty.end() ? found->second : 0.0});
        }

        // Review-1 F3 at this boundary: a completed-scan resume runs no solve. crysta marks that
        // state by leaving `rwp` unavailable (a quiet NaN — results.csv has no Rwp column to
        // recover it from), and the facts that describe a SOLVE must not be invented for a call
        // that performed none: no wall-clock time, and no iterations, which is also the only
        // value consistent with the empty history such a call produces.
        const bool recovered_no_op = std::isnan(result.rwp);
        FitResultBase outcome;
        // A recovered no-op ran no solve, so it has no history and reports the CSV's recorded
        // terminal iteration count; a real scan reports the steps it actually took, which is
        // exactly the history's length.
        if (!recovered_no_op) {
            outcome.iterations_history = result.cancelled ? *file_history : *last_file_history;
        }
        outcome.rwp = result.rwp;
        outcome.reduced_chi_square = result.reduced_chi_square;
        outcome.iterations = recovered_no_op
                                 ? result.iterations
                                 : static_cast<int>(outcome.iterations_history.size());
        outcome.converged = result.converged;
        // ZERO, not NaN: unlike `rwp` — which is genuinely unknown because results.csv has no
        // column to recover it from — the fitting time of a call that ran no solve is a known
        // fact, and it is none. Wall-clock spent loading and reading the CSV is not fitting time.
        outcome.elapsed_ms = recovered_no_op ? 0.0 : elapsed_ms;
        outcome.status = to_edi(crysta::classify_fit_status(result));
        outcome.unevaluable_trials = result.unevaluable_trials;
        outcome.terminal_unevaluable_trials = result.terminal_unevaluable_trials;
        outcome.engine_values = result.values;
        outcome.engine_uncertainty = result.uncertainty;
        outcome.descent = result.descent;
        outcome.reflections_folded = result.reflections_folded;
        outcome.structure_factor_evaluations = result.structure_factor_evaluations;
        for (const detail::RefinedValue& item : refined) {
            outcome.values[item.resolved.path] = item.value;
            outcome.uncertainty[item.resolved.path] = item.uncertainty;
        }
        // `banks`, `iterations_history`, `pre_fit` and the point counts stay at their defaults:
        // they are per-single-fit facts, and the per-file fits that own them ran inside crysta.
        // Reporting the last file's counts as the scan's would be edi inventing a number.

        // A cancelled scan is a partial state, not a result — crysta wrote no row for the
        // unfinished file and no value into its own caller, and edi mirrors that: the model
        // keeps its pre-scan values, and results.csv is the resume point.
        if (!result.cancelled) {
            detail::write_back(refined);
            publish_fit_state(*this, cproject);
            clear_fit_result(*this);  // A scan records no `_fit_result`; an earlier fit's would be stale
        }
        return outcome;
    } catch (const std::invalid_argument&) {
        throw;
    } catch (const ValidationError&) {
        throw;  // a coded refusal keeps its codes
    } catch (const std::exception& error) {
        throw std::invalid_argument(std::string("edi fit_sequential failed: ") + error.what());
    }
}

FitResultBase Project::fit_joint(const std::vector<PdDataBase>& patterns,
                                 const IterationCallback& on_iteration,
                                 const PreambleCallback& on_start,
                                 const CancelCallback& should_cancel) {
    // Boundary checks first — every one of these is a clean, structured ValueError raised BEFORE any
    // engine contact, so a malformed request can never partially mutate the model (ADR-0003 pt 5).
    // The checks themselves are edi-side policy (fit_policy.cpp).
    validate_descent(descent, "edi fit_joint");
    detail::validate_joint_request(*this, experiments, patterns);
    try {
        // Stateless rebuild-per-fit, the same shape as the single-bank path: one crysta Project over
        // the shared structure and EVERY loaded bank, so crysta's own free_from_model dispatches to
        // its joint builder and derives the column layout ([shared structural | per-bank instrument]).
        // edi never composes a free vector; it only marshals each Parameter's free flag.
        BuiltExperiments built;
        built.reserve(experiments.size());
        for (const auto& experiment_item : experiments) {
            make_fit_ready(build_on_heap(built, *experiment_item));
        }
        // A project of several structures (phases), or a bank that disables its one link, fits through
        // crysta's phase-sum residual over every structure; any other through the joint residual.
        const bool phases =
            structures.size() > 1 ||
            std::any_of(experiments.begin(), experiments.end(), [](const auto& experiment) {
                return experiment->linked_structures.size() != 1 || !experiment->linked_structure().enabled.get();
            });
        crysta::Project project = [&]() -> crysta::Project {
            if (phases) {
                return crysta::Project(to_crysta_structures(*this), experiment_list(built));
            }
            return crysta::Project(to_crysta_structure(structure()), experiment_list(built));
        }();
        fill_crysta_relations(*this, project);
        // The atom-site rule on exactly this fit's participants: every bank's enabled phases.
        detail::require_populated_participants(project, "edi fit_joint");
        if (phases) {
            // The phase-sum residual reads each bank's measured pattern from its experiment, and masks
            // it itself.
            for (std::size_t bank = 0; bank < patterns.size(); ++bank) {
                project.experiments[bank].data = crysta::PdDataBase(
                    patterns[bank].axis(), patterns[bank].intensity_meas.get(), patterns[bank].intensity_meas_su.get());
            }
        }
        const std::size_t considered = project.collect_parameters().size();  // _fit_result
        project.fitting_mode = crysta::model_token_from_file(
            crysta::TokenField::FittingMode, crysta::BeamModeEnum::TimeOfFlight,
            fitting_mode.empty() ? std::string("joint") : fitting_mode);

        // One masked pattern per bank, in `experiments` order. The joint residual's constructor does
        // NOT apply exclusions (only its from_model helper does, and that reads data embedded in the
        // project), so edi masks each bank itself — exactly the call the single-bank path makes.
        std::vector<crysta::ResidualPattern> measured;
        measured.reserve(patterns.size());
        // Points as READ across every bank, before any mask — the caller-owned authority for
        // `n_points_loaded`.
        std::size_t n_points_loaded = 0;
        for (std::size_t bank = 0; bank < patterns.size(); ++bank) {
            n_points_loaded += patterns[bank].axis().size();
            crysta::ResidualPattern pattern{patterns[bank].axis(), patterns[bank].intensity_meas,
                                            patterns[bank].intensity_meas_su};
            pattern = crysta::apply_exclusions(pattern, experiments[bank]->excluded_regions);
            if (pattern.grid.empty()) {
                throw std::invalid_argument(
                    "edi fit_joint: no measured data remains for bank '" +
                    experiments[bank]->name + "' after applying its excluded regions");
            }
            measured.push_back(std::move(pattern));
        }

        const auto finish = [&](auto& provider) -> FitResultBase {
            if (provider.n_free() == 0) {
                throw std::invalid_argument("edi fit_joint: no free parameters (mark parameters "
                                            "refinable via their free flags)");
            }

            // Pre-fit values — captured before the minimizer, translated below (see the single bank
            // path for the rationale). Joint labels carry their `<bank>.` prefix and resolve through
            // resolve_joint_label, exactly as the refined values do.
            std::map<std::string, double> start_by_label;
            {
                const std::vector<std::string> labels = provider.labels();
                const std::vector<double> values = provider.values();
                for (std::size_t index = 0; index < labels.size() && index < values.size(); ++index) {
                    start_by_label[labels[index]] = values[index];
                }
            }

            const double dof = detail::reduced_chi_square_dof(provider.n_data(), provider.n_free());
            // Pre-fit record at the joint start params — the shared residual seam, no fit.
            const crysta::IterationRecord crysta_pre_fit = crysta::pre_fit_record(provider, dof);
            const IterationRecord pre_fit{crysta_pre_fit.iteration, crysta_pre_fit.rwp,
                                          crysta_pre_fit.reduced_chi_square, crysta_pre_fit.elapsed_ms,
                                          crysta_pre_fit.unevaluable_trials};
            // Preamble: fired ONCE before the loop with the joint bank names + counts.
            if (on_start) {
                std::vector<std::string> bank_names;
                bank_names.reserve(experiments.size());
                for (const auto& bank_item : experiments) {
                    bank_names.push_back(bank_item->name);
                }
                on_start(FitPreamble{/*joint=*/true, std::move(bank_names), n_points_loaded,
                                     provider.n_data(), provider.n_free(), pre_fit});
            }
            const std::vector<std::string> paths =
                identity_paths(on_iteration, provider.labels(), [this](const std::string& label) {
                    return detail::resolve_joint_project_label(*this, label);
                });
            const auto fit_start = std::chrono::steady_clock::now();
            crysta::IterationHistoryCollector collector(dof, fit_start);
            // (F-bound) /: the same declared conditions and the same registry-or-historical
            // split as the single-bank path above.
            crysta::DescentRequest request =
                declared_request(descent, minimizer_max_iterations, minimizer_chi_square_tolerance);
            const crysta::FitResultBase result = [&] {
                if (descent.empty() && minimizer_chi_square_tolerance <= 0.0) {
                    return crysta::fit_problem(
                        provider, /*separable_linear=*/true, request.max_iterations,
                        collector.callback(to_engine_callback(on_iteration, dof, fit_start, paths)),
                        should_cancel);  // The cooperative cancel
                }
                request.on_iteration =
                    collector.callback(to_engine_callback(on_iteration, dof, fit_start, paths));
                request.should_cancel = should_cancel;
                return crysta::fit_problem(provider, request);
            }();
            const double elapsed_ms = std::chrono::duration<double, std::milli>(
                                          std::chrono::steady_clock::now() - fit_start)
                                          .count();

            // Per-bank metrics, read from the provider while it is STILL ALIVE — it owns the per-bank
            // sub-residuals and is destroyed when this scope ends, so this must happen here and cannot
            // be recovered afterwards from the FitResultBase. Every number is the engine's; edi only
            // renames the fields into its own value type.
            std::vector<BankMetric> bank_metrics;
            for (const crysta::BankMetric& metric : provider.bank_metrics(provider.values())) {
                bank_metrics.push_back({metric.name, metric.n_points, metric.rwp, metric.chi_square});
            }

            // Translate EVERY joint label to an edi-owned parameter FIRST — total and fail-closed. Only
            // once the whole result resolves is the outcome built and the model written, so no crysta
            // label crosses the boundary and a partial/garbled result can never mutate the model.
            std::vector<detail::RefinedValue> refined;
            refined.reserve(result.values.size());
            for (const auto& [label, value] : result.values) {
                std::optional<detail::ResolvedParameter> resolved =
                    detail::resolve_joint_project_label(*this, label);
                if (!resolved) {
                    throw std::invalid_argument(
                        "edi fit_joint: crysta result label '" + label +
                        "' does not resolve to an edi model parameter (unmapped engine label)");
                }
                const auto found = result.uncertainty.find(label);
                refined.push_back({std::move(*resolved), value,
                                   found != result.uncertainty.end() ? found->second : 0.0});
            }

            FitResultBase outcome;
            outcome.rwp = result.rwp;
            outcome.reduced_chi_square = result.reduced_chi_square;
            outcome.iterations = result.iterations;
            outcome.converged = result.converged;
            outcome.banks = std::move(bank_metrics);
            outcome.n_points_loaded = n_points_loaded;
            outcome.n_points_fitted = provider.n_data();
            outcome.iterations_history = to_edi(collector.history());
            outcome.pre_fit = pre_fit;
            outcome.elapsed_ms = elapsed_ms;
            outcome.status = to_edi(crysta::classify_fit_status(result));
            outcome.unevaluable_trials = result.unevaluable_trials;
            outcome.terminal_unevaluable_trials = result.terminal_unevaluable_trials;
            outcome.engine_values = result.values;
            outcome.engine_uncertainty = result.uncertainty;
            outcome.descent = result.descent;
            outcome.reflections_folded = result.reflections_folded;
            outcome.structure_factor_evaluations = result.structure_factor_evaluations;
            for (const detail::RefinedValue& item : refined) {
                outcome.values[item.resolved.path] = item.value;
                outcome.uncertainty[item.resolved.path] = item.uncertainty;
            }
            for (const auto& [label, value] : start_by_label) {
                std::optional<detail::ResolvedParameter> resolved =
                    detail::resolve_joint_project_label(*this, label);
                if (resolved) {
                    outcome.start[resolved->path] = value;
                }
            }
            detail::write_back(refined);
            crysta::write_fit_result_into(project, result);  // crysta completes the dependents
            publish_fit_state(*this, project);
            record_fit_result(*this, outcome, considered);
            // Before shared items this copied bank 0 into the single-bank mirror (the loader set it
            // up that way), so `experiment` never reports stale values after a joint refinement.
            // `experiment()` IS the first bank now, so nothing is copied back: that
            // self-assignment was a write that staled bank 0's fresh calculation.
            return outcome;
        };
        if (phases) {
            crysta::PhaseSumResidual provider(project);
            return finish(provider);
        }
        // Delegate the ENTIRE joint LM loop to crysta's public minimizer at its documented defaults
        // (separable_linear, max_iter 50, CutoffPolicy::Off, SolverRung::Lm, chi2/param tolerances) —
        // the same settings `crysta fit <project> --rung lm` resolves to, so the fit is comparable to
        // the published path. The provider is move-only; it owns the per-bank sub-projects, built
        // from its own copy of the project.
        crysta::NeutronScattering scattering = select_scattering(structure());  // the one structure's
        std::optional<crysta::JointBraggResidual> joint;
        try {
            joint.emplace(project, scattering, std::move(measured));
        } catch (const std::exception& error) {
            raise_coded(error);  // a relation between banks keeps its code
            throw;
        }
        return finish(*joint);
    } catch (const std::invalid_argument&) {
        throw;  // already a clean, structured ValueError — surface as-is.
    } catch (const ValidationError&) {
        throw;  // a coded refusal keeps its codes
    } catch (const std::exception& error) {
        throw std::invalid_argument(std::string("edi fit_joint failed: ") + error.what());
    }
}

std::string crystal_system_name(const SpaceGroup& space_group) {
    Structure structure;
    structure.space_group = space_group;
    return crysta::crystal_system_name(crysta::cell_freedom(resolve_group(structure)).system);
}

int space_group_it_number(const SpaceGroup& space_group) {
    Structure structure;
    structure.space_group = space_group;
    return resolve_group(structure).it_number;
}

// The engine owns the policy; edi forwards through the one TU allowed to hold a crysta
// call (ADR-0003). See edi/threading.hpp for the contract.
void apply_engine_thread_defaults() noexcept { crysta::threading::apply_process_thread_defaults(); }

}  // namespace edi
