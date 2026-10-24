// SPDX-License-Identifier: BSD-3-Clause
#include <algorithm>
#include <array>
#include <bit>
#include <cctype>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <functional>
#include <locale>
#include <memory>
#include <sstream>
#include <limits>
#include <cmath>
#include <deque>
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

#include "edi/background_estimate.hpp"
#include "edi/fit_job.hpp"
#include "edi/calculation.hpp"
#include "edi/presentation.hpp"
#include "edi/scan.hpp"
#include "adapter_test_access.hpp"  // edi::detail conversion seam (core/src only; test-only, not installed)
#include "number_token.hpp"
#include "canonical_encoding.hpp"  // edi-only logic: core/src-private, never installed
#include "identity_bridge.hpp"  // The loader's reach into crysta's identity rules
#include "crysta/adp.hpp"
#include "crysta/analysis.hpp"
#include "crysta/background_estimate.hpp"
#include "crysta/constraints.hpp"
#include "crysta/cell_metric.hpp"
#include "crysta/cell_symmetry.hpp"
#include "crysta/descent.hpp"
#include "crysta/experiment_builder.hpp"
#include "crysta/fit.hpp"
#include "crysta/fit_quality.hpp"
#include "crysta/fit_report.hpp"
#include "crysta/identity.hpp"
#include "crysta/model.hpp"
#include "crysta/parameter.hpp"
#include "crysta/partype.hpp"
#include "crysta/pattern.hpp"
#include "crysta/peak.hpp"
#include "crysta/recompute.hpp"
#include "crysta/residual.hpp"
#if __has_include("crysta/cif_report.hpp")
#include "crysta/cif_report.hpp"
#endif
#if __has_include("crysta/dictionary_items.hpp")
#include "crysta/dictionary_items.hpp"
#endif
#if __has_include("crysta/report_settings.hpp")
#include "crysta/report_settings.hpp"
#endif
#include "crysta/scattering.hpp"
#include "crysta/structure_geometry.hpp"
#include "crysta/symmetry.hpp"
#include "crysta/weight_fraction.hpp"
#include "crysta/threading.hpp"
#include "crysta/tokens.hpp"
#include "edi/categories.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"
#include "edi/selectors.hpp"
#include "edi/structure_scene.hpp"
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
                                 // A calculation of this structure (a fit's quality) reads the declared
                                 // scattering lengths from it, as the fit reads them from select_scattering.
                                 built.scattering_lengths_fm = s.scattering_lengths_fm;
                                 // The bond cutoffs cross presence-faithfully, so crysta's
                                 // writer saves a declared `_geom` and no other.
                                 built.geom.min_bond_distance_cutoff =
                                     s.geom.min_bond_distance_cutoff.get();
                                 built.geom.bond_distance_inc = s.geom.bond_distance_inc.get();
                                 built.atom_site_aniso = detail::to_crysta_atom_site_aniso(s);
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
    // The anisotropic tensors: crysta's site-symmetry ties (ADR-0027).
    for (const auto& tensor : s.atom_site_aniso) {
        const AtomSite* site = nullptr;
        for (const auto& candidate : s.atom_sites) {
            if (candidate->id.value() == tensor->id.value()) {
                site = candidate.get();
            }
        }
        if (site == nullptr) {
            continue;
        }
        const std::vector<Parameter*> components = const_cast<AtomSiteAniso&>(*tensor).parameters();
        ties.push_back({&site->adp_iso, TieKind::Follows, components[0], std::nullopt});
        std::vector<ParameterTie> rows;
        for (const Parameter* component : components) {
            rows.push_back({component});
        }
        try {
            const crysta::Structure engine = to_crysta_structure(s);
            for (const crysta::AtomSite& candidate : engine.atom_sites) {
                if (candidate.site_id.value() != site->id.value()) {
                    continue;
                }
                for (const crysta::AdpTie& tie : crysta::adp_ties(engine, candidate)) {
                    ParameterTie& row = rows[tie.component];
                    if (tie.fixed) {
                        row.kind = TieKind::Fixed;
                        row.fixed_value = 0.0;
                    } else {
                        row.kind = TieKind::Follows;
                        row.leader = components[tie.terms.front().first];
                    }
                }
            }
        } catch (const std::exception&) {
            // An unresolvable setting or site: the components are reported independent.
        }
        ties.insert(ties.end(), rows.begin(), rows.end());
    }
    return ties;
}

namespace {
// The cell the calculation uses: the model's cell completed by its space group's ties (a cubic
// structure declares only a), or the cell as written when the group does not resolve.
crysta::Cell completed_cell(const Structure& s) {
    try {
        return to_completed_crysta_cell(s.cell, crysta::cell_freedom(resolve_group(s)));
    } catch (const std::exception&) {
        return detail::to_crysta_cell(s.cell);
    }
}
}  // namespace

namespace {

// One coordinate of a Wyckoff representative ("1/2*x+1/2*y", "-x+1/4", "1/8") with x, y and z at 0: the sum of its
// terms without a variable.
double coordinate_at_origin(const std::string& expression) {
    double sum = 0.0;
    std::size_t start = 0;
    while (start < expression.size()) {
        std::size_t end = start + 1;
        while (end < expression.size() && expression[end] != '+' && expression[end] != '-') {
            ++end;
        }
        std::string term = expression.substr(start, end - start);
        start = end;
        const double sign = !term.empty() && term.front() == '-' ? -1.0 : 1.0;
        if (!term.empty() && (term.front() == '+' || term.front() == '-')) {
            term.erase(0, 1);
        }
        if (term.empty() || term.find_first_of("xyz") != std::string::npos) {
            continue;
        }
        const std::size_t slash = term.find('/');
        const double value = slash == std::string::npos
                                 ? std::stod(term)
                                 : std::stod(term.substr(0, slash)) / std::stod(term.substr(slash + 1));
        sum += sign * value;
    }
    return sum;
}

}  // namespace

std::vector<WyckoffOption> wyckoff_positions(const Structure& structure) {
    crysta::SpaceGroup group;
    try {
        group = resolve_group(structure);
    } catch (const std::exception&) {
        return {};
    }
    std::vector<WyckoffOption> options;
    for (const auto& [letter, position] : group.wyckoff) {
        WyckoffOption option{letter, position.multiplicity, position.representative, {}};
        std::size_t start = 0;
        for (std::size_t axis = 0; axis < 3; ++axis) {
            const std::size_t comma = position.representative.find(',', start);
            option.origin[axis] = coordinate_at_origin(position.representative.substr(start, comma - start));
            start = comma == std::string::npos ? position.representative.size() : comma + 1;
        }
        options.push_back(std::move(option));
    }
    // The table's order: a to z, then the capital letters (`A`, alpha, after `z`).
    std::stable_sort(options.begin(), options.end(), [](const WyckoffOption& one, const WyckoffOption& other) {
        const bool one_capital = !one.letter.empty() && std::isupper(static_cast<unsigned char>(one.letter.front()));
        const bool other_capital =
            !other.letter.empty() && std::isupper(static_cast<unsigned char>(other.letter.front()));
        return one_capital != other_capital ? !one_capital : one.letter < other.letter;
    });
    return options;
}

namespace {

// The elements a new atom may take: those the app styles that crysta's default neutron table and its default X-ray
// form factors both hold, so the atom computes whatever the probe.
const std::vector<std::string>& new_site_elements() {
    static const std::vector<std::string> elements = [] {
        std::vector<std::string> out;
        const crysta::NeutronScattering neutron = crysta::load_neutron_scattering();
        for (const ElementStyle& style : element_style_table()) {
            if (!neutron.b_c.contains(style.symbol)) {
                continue;
            }
            try {
                crysta::xray_scattering({"", "none", 0.0}, {style.symbol});
            } catch (const std::exception&) {
                continue;
            }
            out.push_back(style.symbol);
        }
        return out;
    }();
    return elements;
}

}  // namespace

AtomSite new_atom_site(const Structure& structure, const std::function<double()>& random) {
    const auto draw_index = [&random](std::size_t count) {
        return std::min(count - 1, static_cast<std::size_t>(random() * static_cast<double>(count)));
    };
    AtomSite site;
    // The element: one the structure does not hold yet when there is one.
    std::vector<std::string> unused;
    for (const std::string& element : new_site_elements()) {
        const bool held = std::any_of(structure.atom_sites.begin(), structure.atom_sites.end(),
                                      [&element](const auto& existing) { return existing->type_symbol.value() == element; });
        if (!held) {
            unused.push_back(element);
        }
    }
    const std::vector<std::string>& candidates = unused.empty() ? new_site_elements() : unused;
    site.type_symbol = candidates.empty() ? std::string("H") : candidates[draw_index(candidates.size())];
    // The label: the element and the next free number.
    for (int number = 1;; ++number) {
        const std::string label = site.type_symbol.value() + std::to_string(number);
        const bool taken = std::any_of(structure.atom_sites.begin(), structure.atom_sites.end(),
                                       [&label](const auto& existing) { return existing->id.value() == label; });
        if (!taken) {
            site.id = label;
            break;
        }
    }
    // The coordinates: three decimals, drawn again on a special position.
    std::vector<crysta::SymmetryOperation> operations;
    try {
        const crysta::SpaceGroup group = resolve_group(structure);
        operations = crysta::symmetry_operations(group);
        int highest = 0;
        for (const auto& [letter, position] : group.wyckoff) {
            if (position.multiplicity > highest) {
                highest = position.multiplicity;
                site.wyckoff_letter = letter;
            }
        }
    } catch (const std::exception&) {
        operations.clear();
    }
    const auto special = [&operations](const std::array<double, 3>& x) {
        for (const crysta::SymmetryOperation& operation : operations) {
            const bool identity = operation.rotation == std::array<int, 9>{1, 0, 0, 0, 1, 0, 0, 0, 1} &&
                                  operation.translation == std::array<double, 3>{0.0, 0.0, 0.0};
            if (identity) {
                continue;
            }
            bool fixed = true;
            for (std::size_t row = 0; row < 3 && fixed; ++row) {
                double image = operation.translation[row];
                for (std::size_t column = 0; column < 3; ++column) {
                    image += operation.rotation[row * 3 + column] * x[column];
                }
                const double shift = image - x[row];
                fixed = std::abs(shift - std::round(shift)) < 1e-6;
            }
            if (fixed) {
                return true;
            }
        }
        return false;
    };
    std::array<double, 3> x{};
    for (int attempt = 0; attempt < 1000; ++attempt) {
        for (double& coordinate : x) {
            coordinate = std::round(random() * 1000.0) / 1000.0;
            if (coordinate >= 1.0) {
                coordinate = 0.0;
            }
        }
        if (!special(x)) {
            break;
        }
    }
    site.fract_x.value = x[0];
    site.fract_y.value = x[1];
    site.fract_z.value = x[2];
    return site;
}

std::optional<std::array<double, 6>> site_u_star(const Structure& s, const AtomSite& site) {
    try {
        const crysta::AdpForm form = crysta::adp_form_of(site.adp_type.value());
        if (!crysta::is_anisotropic(form)) {
            return std::nullopt;
        }
        for (const auto& tensor : s.atom_site_aniso) {
            if (tensor->id.value() != site.id.value()) {
                continue;
            }
            crysta::AdpTensor components{};
            const std::vector<Parameter*> parameters = tensor->parameters();
            for (std::size_t k = 0; k < 6; ++k) {
                components[k] = parameters[k]->value;
            }
            return crysta::u_star_of(form, components, crysta::CellMetric::from_cell(completed_cell(s)));
        }
    } catch (const std::exception&) {
        // an unknown type or an unrealizable cell
    }
    return std::nullopt;
}

namespace {

// The space group crysta resolves for `s`, or crysta's default for a setting it cannot resolve
// (whose sites then carry no stabilizer ties).
crysta::SpaceGroup group_or_default(const Structure& s) {
    try {
        return resolve_group(s);
    } catch (const std::exception&) {
        return crysta::SpaceGroup{};
    }
}

// A one-site crysta structure for `site` at the structure's completed cell and space group, the
// site of type `adp_type`: crysta converts and ties its values (ADR-0027).
crysta::Structure one_site_engine(const Structure& s, const AtomSite& site, const std::string& adp_type,
                                  const crysta::Structure::Finish& finish = {}) {
    std::vector<crysta::AtomSite> sites{crysta::AtomSite(
        site.id.value(), site.type_symbol.value(), site.wyckoff_letter.value(), adp_type,
        param(site.fract_x, crysta::ATOM_POS, "fract_x"), param(site.fract_y, crysta::ATOM_POS, "fract_y"),
        param(site.fract_z, crysta::ATOM_POS, "fract_z"), param(site.occupancy, crysta::OCC, "occupancy"),
        param(site.adp_iso, crysta::ADP, "adp_iso"))};
    return crysta::Structure(completed_cell(s), group_or_default(s), sites, finish);
}

// The tensor rows in the order of their sites, as a loaded file holds them, so a row a type change
// adds sits with its site (the parameter walk lists the rows in this order).
void order_tensor_rows(Structure& s) {
    std::vector<std::shared_ptr<AtomSiteAniso>> ordered;
    for (const auto& site : s.atom_sites) {
        for (const auto& row : s.atom_site_aniso) {
            if (row->id.value() == site->id.value()) {
                ordered.push_back(row);
            }
        }
    }
    bool same = ordered.size() == s.atom_site_aniso.size();
    for (std::size_t i = 0; same && i < ordered.size(); ++i) {
        same = ordered[i] == s.atom_site_aniso[i];
    }
    if (!same && ordered.size() == s.atom_site_aniso.size()) {
        s.atom_site_aniso.assign(std::move(ordered));
    }
}

}  // namespace

void add_missing_aniso_rows(Structure& s) {
    for (const auto& site : s.atom_sites) {
        if (!is_anisotropic_adp_type(site->adp_type.value())) {
            continue;
        }
        bool held = false;
        for (const auto& tensor : s.atom_site_aniso) {
            held = held || tensor->id.value() == site->id.value();
        }
        if (held) {
            continue;
        }
        const crysta::AdpForm form = crysta::adp_form_of(site->adp_type.value());
        const crysta::CellMetric metric = crysta::CellMetric::from_cell(completed_cell(s));
        crysta::AdpTensor components = crysta::components_of(
            form, crysta::u_star_of_iso(crysta::equivalent_iso_form(form), site->adp_iso.value, metric), metric);
        // The site's symmetry exactly: a fixed component is 0, tied ones the same number.
        try {
            const crysta::Structure engine = one_site_engine(s, *site, site->adp_type.value());
            components = crysta::tied_components(engine, engine.atom_sites[0], components);
        } catch (const std::exception&) {
            // a position that names no stabilizer keeps the converted values
        }
        AtomSiteAniso tensor;
        tensor.id = site->id.value();
        const std::vector<Parameter*> parameters = tensor.parameters();
        for (std::size_t k = 0; k < 6; ++k) {
            parameters[k]->value = components[k];
            if (components[k] == 0.0) {
                parameters[k]->uncertainty = std::nullopt;  // an exact zero has no s.u.
            }
        }
        s.atom_site_aniso.push_back(std::move(tensor));
    }
    order_tensor_rows(s);
}

void sync_atom_site_aniso(Structure& s) {
    for (std::size_t row = s.atom_site_aniso.size(); row-- > 0;) {
        const std::string& id = s.atom_site_aniso[row]->id.value();
        bool kept = false;
        for (const auto& site : s.atom_sites) {
            kept = kept || (site->id.value() == id && is_anisotropic_adp_type(site->adp_type.value()));
        }
        if (!kept) {
            s.atom_site_aniso.erase_at(row);
        }
    }
    add_missing_aniso_rows(s);
    complete_atom_site_aniso(s);
}

void complete_atom_site_aniso(Structure& s) {
    const crysta::CellMetric metric = crysta::CellMetric::from_cell(completed_cell(s));
    for (const auto& tensor : s.atom_site_aniso) {
        for (const auto& site : s.atom_sites) {
            if (site->id.value() != tensor->id.value() || !is_anisotropic_adp_type(site->adp_type.value())) {
                continue;
            }
            const crysta::AdpForm form = crysta::adp_form_of(site->adp_type.value());
            crysta::AdpTensor components{};
            const std::vector<Parameter*> parameters = tensor->parameters();
            for (std::size_t k = 0; k < 6; ++k) {
                components[k] = parameters[k]->value;
            }
            // The site's symmetry exactly: a fixed component is 0 and a tied one its expression over the free ones.
            try {
                const crysta::Structure engine = one_site_engine(s, *site, site->adp_type.value());
                components = crysta::tied_components(engine, engine.atom_sites[0], components);
            } catch (const std::exception&) {
                // a position that names no stabilizer keeps its components
            }
            for (std::size_t k = 0; k < 6; ++k) {
                if (parameters[k]->value != components[k]) {
                    parameters[k]->value = components[k];
                }
                // An exact zero has no s.u., as in a new tensor: a fixed 0 read from a file keeps none either, so a
                // project reopened, or holding what it saved, shows its zeros as it did before.
                if (components[k] == 0.0 && !parameters[k]->free.get() &&
                    parameters[k]->uncertainty.get() == std::optional<double>(0.0)) {
                    parameters[k]->uncertainty = std::nullopt;
                }
            }
            // An anisotropic site's adp_iso is its tensor's equivalent value, in the form its type shows it.
            const double equivalent = crysta::iso_of(crysta::equivalent_iso_form(form),
                                                     crysta::u_star_of(form, components, metric), metric);
            // A different equivalent replaces the scalar; the scalar's uncertainty and fit start
            // belonged to that other value (ADR-0027), so they go (absent stays absent, any other
            // uncertainty the present zero of a value with none).
            if (site->adp_iso.value != equivalent) {
                const std::optional<double> before = site->adp_iso.uncertainty;
                site->adp_iso.value = equivalent;
                site->adp_iso.uncertainty = before.has_value() ? std::optional<double>(0.0) : std::nullopt;
                site->adp_iso.start_value = std::nullopt;
                site->adp_iso.start_uncertainty = std::nullopt;
            }
        }
    }
}

void change_adp_type(Structure& s, AtomSite& site, const std::string& adp_type) {
    if (!is_adp_type(adp_type)) {
        throw std::invalid_argument("adp_type '" + adp_type +
                                    "' is not one of Biso, Uiso, Bani, Uani, beta");
    }
    if (site.adp_type.value() == adp_type) {
        return;
    }
    // A one-site crysta structure at this cell and space group: crysta converts the values and
    // applies the site's symmetry ties.
    std::shared_ptr<AtomSiteAniso> held;
    for (const auto& tensor : s.atom_site_aniso) {
        if (tensor->id.value() == site.id.value()) {
            held = tensor;
        }
    }
    crysta::Structure engine = one_site_engine(s, site, site.adp_type.value(), [&held](crysta::Structure& built) {
        if (held) {
            Structure one;
            one.atom_site_aniso.push_back(*held);
            built.atom_site_aniso = detail::to_crysta_atom_site_aniso(one);
        }
    });
    crysta::change_adp_type(engine, engine.atom_sites[0], adp_type);
    // The converted state, value, uncertainty and fit start alike (ADR-0027): crysta
    // rescales what the change only rescales and drops what it cannot carry.
    // An uncertainty the change drops keeps edi's spelling of none: absent stays absent, any
    // other becomes the present zero a fixed value carries.
    const auto take = [](Parameter& to, const crysta::Parameter& from) {
        const std::optional<double> before = to.uncertainty;
        to.value = from.value();
        to.uncertainty = from.uncertainty().has_value() || !before.has_value()
                             ? from.uncertainty()
                             : std::optional<double>(0.0);
        to.start_value = from.start_value();
        to.start_uncertainty = from.start_uncertainty();
    };
    take(site.adp_iso, engine.atom_sites[0].adp_iso);
    site.adp_type = adp_type;
    if (engine.atom_site_aniso.empty()) {
        for (std::size_t i = 0; i < s.atom_site_aniso.size(); ++i) {
            if (s.atom_site_aniso[i]->id.value() == site.id.value()) {
                s.atom_site_aniso.erase_at(i);
                break;
            }
        }
        return;
    }
    if (!held) {
        AtomSiteAniso tensor;
        tensor.id = site.id.value();
        s.atom_site_aniso.push_back(std::move(tensor));
        held = s.atom_site_aniso[s.atom_site_aniso.size() - 1];
    }
    const std::vector<Parameter*> components = held->parameters();
    for (std::size_t k = 0; k < 6; ++k) {
        take(*components[k], engine.atom_site_aniso[0].adp[k]);
        if (components[k]->value == 0.0 && !engine.atom_site_aniso[0].adp[k].uncertainty()) {
            components[k]->uncertainty = std::nullopt;  // a component the symmetry fixes at 0
        }
    }
    order_tensor_rows(s);
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
    for (std::size_t row = 0; row < model.structure().atom_site_aniso.size(); ++row) {
        AtomSiteAniso& tensor = *model.structure().atom_site_aniso[row];
        crysta::AtomSiteAniso& ctensor = cstructure.atom_site_aniso[row];
        const std::string base = "structure.atom_site_aniso[" + tensor.id + "].";
        const char* const names[6] = {"adp_11", "adp_22", "adp_33", "adp_12", "adp_13", "adp_23"};
        const std::vector<Parameter*> components = tensor.parameters();
        for (std::size_t k = 0; k < 6; ++k) {
            index.emplace(base + names[k], Slot{&ctensor.adp[k], components[k]});
        }
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
    // A loop row by its id, never its position (the owner, 2026-10-11), as parameter_paths names it.
    index.emplace("experiment.linked_structures[" + experiment.linked_structure().structure_id.value() + "].scale",
                  Slot{&cexperiment.scale(), &experiment.linked_structure().scale});
    for (std::size_t i = 0; i < experiment.background.size(); ++i) {
        index.emplace(
            "experiment.background[" + experiment.background[i]->id.value() + "].intensity",
            Slot{&cexperiment.background[i].intensity, &experiment.background[i]->intensity});
    }
    for (std::size_t i = 0; i < experiment.background_terms.size(); ++i) {
        index.emplace("experiment.background[" + experiment.background_terms[i]->id.value() + "].coef",
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
        const std::string texture = "experiment.preferred_orientation[" + row.structure_id.value() + "].";
        index.emplace(texture + "march_r", Slot{cexperiment.texture()->march.data(), &row.march_r});
        index.emplace(texture + "march_random_fract",
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
    converted.template_file = config.template_file;
    converted.extract.clear();
    converted.extract.reserve(config.extract.size());
    for (const auto& rule : config.extract) {
        converted.extract.push_back({rule->id.value(), rule->target, rule->pattern, rule->required});
    }
}

std::string effective_scan_template_file(const Project& scan, const ScanDatasets& datasets) {
    if (!scan.sequential_fit.template_file.empty() || datasets.files.empty()) {
        return scan.sequential_fit.template_file;
    }
    return datasets.files.front();
}

std::string effective_scan_template_file(const Project& scan) {
    if (!scan.sequential_fit.template_file.empty()) {
        return scan.sequential_fit.template_file;
    }
    try {
        return effective_scan_template_file(scan, scan_datasets(scan));
    } catch (const std::exception&) {  // NOLINT(bugprone-empty-catch) — no listing, no template dataset
        return {};
    }
}

ScanDatasets scan_datasets(const Project& project) {
    crysta::SequentialFitConfig config;
    fill_crysta_sequential(project.sequential_fit, config);
    crysta::SequentialScanFiles files =
        crysta::sequential_scan_files(config, project.path, project.scan_data_root);
    return {std::move(files.directory), std::move(files.names)};
}

PdDataBase read_scan_dataset(const std::string& directory, const std::string& file, BeamModeEnum mode) {
    const crysta::PdDataBase read = crysta::read_sequential_scan_data((std::filesystem::path(directory) / file).string());
    PdDataBase data;
    std::vector<double> axis(read.grid.begin(), read.grid.end());
    (mode == BeamModeEnum::CONSTANT_WAVELENGTH ? data.two_theta : data.time_of_flight) = std::move(axis);
    data.intensity_meas = std::vector<double>(read.intensity.begin(), read.intensity.end());
    data.intensity_meas_su = std::vector<double>(read.sigma.begin(), read.sigma.end());
    return data;
}

bool persistable_name(const std::string& name) { return crysta::is_persistable_name(name); }

PlainDataRows read_plain_data(const std::string& path) {
    crysta::PlainData read;
    try {
        read = crysta::read_plain_data(path, true);
    } catch (const std::exception& refusal) {
        throw IoError(refusal.what());
    }
    return PlainDataRows{std::move(read.x),          std::move(read.y),         std::move(read.sigma),
                         read.counts.skipped,       read.counts.nonpositive, read.counts.duplicates,
                         read.counts.reordered,     read.counts.derived};
}

PlainDataLoad experiment_with_plain_data(const BraggPdExperiment& experiment, const std::string& path,
                                         bool take_file_name) {
    PlainDataRows read = read_plain_data(path);
    PlainDataLoad load{BraggPdExperiment(experiment), std::filesystem::path(path).filename().string()};
    load.points = read.x.size();
    load.skipped = read.skipped;
    load.nonpositive = read.nonpositive;
    load.duplicates = read.duplicates;
    load.reordered = read.reordered;
    load.derived = read.derived;
    PdDataBase data;
    (experiment.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH ? data.two_theta : data.time_of_flight) =
        std::move(read.x);
    data.intensity_meas = std::move(read.y);
    data.intensity_meas_su = std::move(read.sigma);
    load.experiment.data = std::move(data);
    load.experiment.calculation_only = false;
    load.experiment.data_file = load.file_name;
    if (take_file_name) {
        // The file's stem, with anything a datablock name cannot hold made an underscore; a stem the save would
        // still refuse (a reserved device name) leaves the name as it was.
        std::string stem = std::filesystem::path(path).stem().string();
        for (char& character : stem) {
            const bool keep = (character >= 'a' && character <= 'z') || (character >= 'A' && character <= 'Z') ||
                              (character >= '0' && character <= '9') || character == '_' || character == '-';
            character = keep ? character : '_';
        }
        if (persistable_name(stem)) {
            load.experiment.name = stem;
        }
    }
    return load;
}

std::vector<std::string> scan_extract_values(const Project& project, const std::string& directory,
                                             const std::string& file) {
    crysta::SequentialFitConfig config;
    fill_crysta_sequential(project.sequential_fit, config);
    return crysta::sequential_extract_values(config, (std::filesystem::path(directory) / file).string());
}

namespace {

// crysta writes plain comma-joined cells, with no quoting (its results.csv contract).
std::vector<std::string> split_scan_row(std::string_view line) {
    std::vector<std::string> cells(1);
    for (const char character : line) {
        if (character == ',') {
            cells.emplace_back();
        } else if (character != '\r') {
            cells.back() += character;
        }
    }
    return cells;
}

std::filesystem::path scan_results_path(const Project& project) {
    return std::filesystem::path(project.path) / "analysis" / "results.csv";
}

// Why each file's fit stopped, from crysta's ledger (`termination`, its fifth column), read in step with
// results.csv: crysta writes a file's ledger row just before its results row, so the k-th of each name the same
// file. Reading both together keeps one row in memory, not the whole scan's. A ledger written before it recorded
// the reason, none, or one whose row names another file gives nothing from there on; a path there that is not a
// regular file throws (scan_state_present).
class LedgerReader {
   public:
    explicit LedgerReader(const std::filesystem::path& path) {
        if (!scan_state_present(path, "analysis/results-provenance.csv")) {
            return;  // no ledger: no reasons
        }
        input_.open(path, std::ios::binary);
        std::string line;
        if (std::getline(input_, line)) {
            const std::vector<std::string> header = split_scan_row(line);
            usable_ = header.size() == 5 && header[0] == "file_path" && header[4] == "termination";
        }
    }
    std::string next(const std::string& file_cell) {
        std::string line;
        if (!usable_ || !std::getline(input_, line) || input_.eof()) {
            usable_ = false;
            return {};
        }
        std::vector<std::string> cells = split_scan_row(line);
        if (cells.size() != 5 || cells[0] != file_cell) {
            usable_ = false;
            return {};
        }
        return std::move(cells[4]);
    }

   private:
    std::ifstream input_;
    bool usable_ = false;
};

// The termination the ledger's last line records for `file_cell`; empty when that line is another file's, the
// ledger does not record reasons, or there is none. Reads only the file's end.
std::string ledger_termination(const std::filesystem::path& path, const std::string& file_cell) {
    if (!scan_state_present(path, "analysis/results-provenance.csv")) {
        return {};
    }
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) {
        return {};
    }
    const std::streamoff size = input.tellg();
    const std::streamoff tail = std::min<std::streamoff>(size, 64 * 1024);
    std::string text(static_cast<std::size_t>(tail), '\0');
    input.seekg(size - tail);
    input.read(text.data(), tail);
    if (!text.empty() && text.back() == '\n') {
        text.pop_back();
    }
    const std::size_t start = text.rfind('\n');
    const std::vector<std::string> cells = split_scan_row(start == std::string::npos ? text : text.substr(start + 1));
    return cells.size() == 5 && cells[0] == file_cell ? cells[4] : std::string();
}

// The results header, its columns resolved by name (crysta's order and any other alike): the file, χ², success and
// iteration columns are required, each extract rule's column is its target's (crysta's name) or its id's, and every
// other column is a parameter value with its `.uncertainty` beside it somewhere. A name twice is refused.
void check_scan_header(const Project& project, ScanResultIndex& index) {
    const auto refuse = [](const std::string& why) {
        throw std::invalid_argument("analysis/results.csv: " + why);
    };
    const std::vector<std::string>& header = index.header;
    std::map<std::string, std::size_t> column;
    for (std::size_t i = 0; i < header.size(); ++i) {
        if (!column.emplace(header[i], i).second) {
            refuse("the column '" + header[i] + "' appears twice");
        }
    }
    const auto required = [&](const char* name) {
        const auto found = column.find(name);
        if (found == column.end()) {
            refuse(std::string("the header has no '") + name + "' column");
        }
        return found->second;
    };
    index.file = required("file_path");
    index.directory = project.sequential_fit.data_dir + "/";
    index.chi = required("fit_result.reduced_chi_square");
    index.success = required("fit_result.success");
    index.iterations = required("fit_result.iterations");
    std::set<std::size_t> taken{index.file, index.chi, index.success, index.iterations};
    index.extract.clear();
    for (const auto& rule : project.sequential_fit.extract) {
        auto found = column.find(rule->target);
        if (found == column.end()) {
            found = column.find(rule->id.value());
        }
        index.extract.push_back(found == column.end() ? -1 : static_cast<std::ptrdiff_t>(found->second));
        if (found != column.end()) {
            taken.insert(found->second);
        }
    }
    index.parameters.clear();
    for (std::size_t i = 0; i < header.size(); ++i) {
        if (taken.contains(i) || header[i].ends_with(".uncertainty")) {
            continue;
        }
        const auto uncertainty = column.find(header[i] + ".uncertainty");
        if (uncertainty == column.end()) {
            refuse("the parameter column '" + header[i] + "' has no '.uncertainty' column");
        }
        index.parameters.push_back({header[i], i, uncertainty->second});
    }
    for (std::size_t i = 0; i < header.size(); ++i) {
        if (header[i].ends_with(".uncertainty") && !taken.contains(i) &&
            !column.contains(header[i].substr(0, header[i].size() - 12))) {
            refuse("the column '" + header[i] + "' has no value column");
        }
    }
}

}  // namespace

bool parse_scan_number(std::string_view token, double& value) {
    // The project loader's rule (number_token.hpp): the whole token, the same value on every platform.
    return edi::detail::read_number(std::string(token), value) == edi::detail::NumberToken::ok;
}

ScanPlaces scan_places(const ScanDatasets& datasets) {
    ScanPlaces places;
    places.reserve(datasets.files.size());
    for (std::size_t i = 0; i < datasets.files.size(); ++i) {
        places.emplace(datasets.files[i], i);
    }
    return places;
}

std::string scan_row_file(const ScanResultIndex& index, const std::vector<std::string>& cells) {
    const std::string& path = cells.at(index.file);
    std::string_view name(path);
    if (!index.directory.empty() && name.starts_with(index.directory)) {
        name.remove_prefix(index.directory.size());
    }
    return name.find('/') == std::string_view::npos ? std::string(name) : std::string();
}

std::pair<std::size_t, ScanResultIndex::Row> scan_row_facts(const Project& /*project*/, const ScanPlaces& places,
                                                           const ScanResultIndex& index,
                                                           const std::vector<std::string>& cells) {
    const auto refuse = [&cells, &index](const std::string& why) {
        throw std::invalid_argument("analysis/results.csv: the row for '" +
                                    (index.file < cells.size() ? cells[index.file] : std::string()) +
                                    "' " + why);
    };
    if (cells.size() != index.header.size()) {
        refuse("has " + std::to_string(cells.size()) + " cells, where the header has " +
               std::to_string(index.header.size()));
    }
    const auto found = places.find(scan_row_file(index, cells));
    if (found == places.end()) {
        refuse("names a file that is not one of the scan's");
    }
    ScanResultIndex::Row row;
    const std::string& success = cells[index.success];
    if (success != "True" && success != "False") {
        refuse("has '" + success + "' for its success, where crysta writes True or False");
    }
    row.converged = success == "True";
    // A failed row (a refused fit) has `nan` for what its fit never produced.
    const auto number = [&row](const std::string& cell, double& value) {
        if (!row.converged && cell == "nan") {
            value = std::numeric_limits<double>::quiet_NaN();
            return true;
        }
        return parse_scan_number(cell, value) && std::isfinite(value);
    };
    if (!number(cells[index.chi], row.reduced_chi_square) || row.reduced_chi_square < 0.0) {
        refuse("has no finite, non-negative reduced chi-square");
    }
    double iterations = 0.0;
    if (!parse_scan_number(cells[index.iterations], iterations) || iterations < 0 ||
        iterations != std::floor(iterations) || iterations > std::numeric_limits<int>::max()) {
        refuse("has no whole iteration count an int holds");
    }
    row.iterations = static_cast<int>(iterations);
    for (const std::ptrdiff_t column : index.extract) {
        row.extracted.push_back(column < 0 ? std::string() : cells[static_cast<std::size_t>(column)]);
    }
    for (const ScanParameterColumns& parameter : index.parameters) {
        double value = 0.0, uncertainty = 0.0;
        if (!parse_scan_number(cells[parameter.value], value) || !std::isfinite(value)) {
            refuse("has no finite value for '" + parameter.name + "'");
        }
        if (!number(cells[parameter.uncertainty], uncertainty) || uncertainty < 0.0) {
            refuse("has no finite, non-negative uncertainty for '" + parameter.name + "'");
        }
    }
    return {found->second, std::move(row)};
}

bool scan_state_present(const std::filesystem::path& path, const std::string& label) {
    std::error_code error;
    const std::filesystem::file_status link = std::filesystem::symlink_status(path, error);
    if (link.type() == std::filesystem::file_type::not_found) {
        return false;
    }
    if (link.type() == std::filesystem::file_type::none) {
        throw std::invalid_argument(label + ": cannot tell whether it exists: " + error.message());
    }
    if (!std::filesystem::is_regular_file(std::filesystem::status(path, error))) {
        throw std::invalid_argument(label + ": it is there but is not a regular file");
    }
    return true;
}

std::int64_t read_scan_notes(const Project& project, const ScanPlaces& places, ScanResultIndex& index,
                             std::int64_t from, bool writing) {
    const std::filesystem::path path = scan_results_path(project).parent_path() / "scan-notes.csv";
    if (!scan_state_present(path, "analysis/scan-notes.csv")) {
        return from;
    }
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::invalid_argument("analysis/scan-notes.csv cannot be read");
    }
    const auto refuse = [](const std::string& why) {
        throw std::invalid_argument("analysis/scan-notes.csv: " + why +
                                    "; the skipped and refused files cannot be known");
    };
    std::string line;
    std::int64_t end = from;
    if (from == 0) {
        if (!std::getline(input, line)) {
            if (writing && !input.bad()) {
                return 0;  // created by the run, nothing written yet
            }
            refuse(input.bad() ? "it could not be read" : "it is empty");
        }
        if (input.eof()) {
            if (writing) {
                return 0;
            }
            refuse("its header is not complete");
        }
        if (split_scan_row(line) !=
            std::vector<std::string>{"file_path", "negative_points", "skipped_dataset", "refusal"}) {
            refuse("its header is not file_path,negative_points,skipped_dataset,refusal");
        }
        end = input.tellg();
    } else {
        input.seekg(from);
        if (!input) {
            refuse("it could not be read from where the last read stopped");
        }
    }
    const std::string directory = project.sequential_fit.data_dir + "/";
    while (std::getline(input, line)) {
        if (input.eof()) {
            if (writing) {
                break;  // a line still being written
            }
            refuse("its last line is not complete");
        }
        const std::vector<std::string> cells = split_scan_row(line);
        if (cells.size() != 4) {
            refuse("a line has " + std::to_string(cells.size()) + " cells, not 4");
        }
        std::string_view name(cells[0]);
        if (name.starts_with(directory)) {
            name.remove_prefix(directory.size());
        }
        const auto found = places.find(std::string(name));
        if (found == places.end()) {
            refuse("'" + cells[0] + "' is not one of the scan's files");
        }
        // A count of points: decimal digits only, proved in range before it is converted.
        const std::string& count = cells[1];
        if (count.empty() || count.size() > 12 ||
            !std::all_of(count.begin(), count.end(), [](char c) { return c >= '0' && c <= '9'; })) {
            refuse("the negative_points of '" + cells[0] + "' is '" + count +
                   "', not a whole number of at most 12 digits");
        }
        if (cells[2] != "True" && cells[2] != "False") {
            refuse("the skipped_dataset of '" + cells[0] + "' is '" + cells[2] + "', not True or False");
        }
        ScanResultIndex::Row& row = index.rows[found->second];
        if (row.noted) {
            refuse("'" + cells[0] + "' is named twice");
        }
        row.noted = true;
        row.negative_points = static_cast<std::size_t>(std::stoull(count));
        row.refusal = cells[3];
        // A file with a results row was fitted, whatever an earlier run noted about it.
        if (cells[2] == "True" && row.offset < 0) {
            row.skipped = true;
            ++index.skipped;
        }
        end = input.tellg();
    }
    if (input.bad()) {
        refuse("it could not be read to its end");
    }
    return end;
}

namespace {

ScanResultIndex index_scan_rows(const Project& project, const ScanDatasets& datasets, const ScanPlaces& places,
                                bool writing);

}  // namespace

ScanResultIndex index_scan_results(const Project& project, const ScanDatasets& datasets, bool writing) {
    return index_scan_results(project, datasets, scan_places(datasets), writing);
}

ScanResultIndex index_scan_results(const Project& project, const ScanDatasets& datasets, const ScanPlaces& places,
                                   bool writing) {
    ScanResultIndex index = index_scan_rows(project, datasets, places, writing);
    if (index.error.empty()) {
        try {
            index.notes_end = read_scan_notes(project, places, index, 0, writing);
        } catch (const std::exception& refusal) {
            ScanResultIndex error;
            error.error = refusal.what();
            error.rows.resize(datasets.files.size());
            return error;
        }
    }
    return index;
}

ScanNotesReport scan_notes_report(const Project& project) {
    const ScanDatasets datasets = scan_datasets(project);
    const ScanResultIndex index = index_scan_results(project, datasets, false);
    if (!index.error.empty()) {
        throw std::invalid_argument(index.error);
    }
    ScanNotesReport report;
    report.skipped = index.skipped;
    for (std::size_t place = 0; place < index.rows.size(); ++place) {
        const ScanResultIndex::Row& row = index.rows[place];
        report.negative_points += row.negative_points;
        if (!row.refusal.empty()) {
            report.refused.emplace_back(datasets.files[place], row.refusal);
        }
    }
    return report;
}

namespace {

ScanResultIndex index_scan_rows(const Project& project, const ScanDatasets& datasets, const ScanPlaces& places,
                                bool writing) {
    ScanResultIndex index;
    index.rows.resize(datasets.files.size());
    const auto refused = [&datasets](const std::string& why) {
        ScanResultIndex error;
        error.error = "analysis/results.csv: " + why;
        error.rows.resize(datasets.files.size());
        return error;
    };
    // Only a file that is not there is no results; one that is there must read whole: a header, and complete
    // rows. A line still being written is expected only while a run writes (`writing`).
    const std::filesystem::path path = scan_results_path(project);
    try {
        if (!scan_state_present(path, "analysis/results.csv")) {
            return index;
        }
    } catch (const std::exception& refusal) {
        ScanResultIndex error;
        error.error = refusal.what();
        error.rows.resize(datasets.files.size());
        return error;
    }
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        return refused("cannot be read");
    }
    std::string line;
    if (!std::getline(input, line)) {
        return refused("is empty");
    }
    if (input.eof()) {
        return writing ? index : refused("its header is not complete");
    }
    try {
        index.header = split_scan_row(line);
        check_scan_header(project, index);
        std::int64_t offset = input.tellg();
        index.end = offset;
        LedgerReader reasons(scan_results_path(project).parent_path() / "results-provenance.csv");
        while (std::getline(input, line)) {
            if (input.eof()) {
                if (writing) {
                    break;  // no line break: a row still being written
                }
                throw std::invalid_argument("analysis/results.csv: its last row is not complete");
            }
            const std::int64_t next = input.tellg();
            const std::vector<std::string> cells = split_scan_row(line);
            auto [dataset, row] = scan_row_facts(project, places, index, cells);
            if (index.rows[dataset].offset >= 0) {
                throw std::invalid_argument("analysis/results.csv: '" + datasets.files[dataset] +
                                            "' has two rows");
            }
            row.termination = reasons.next(cells[index.file]);
            row.offset = offset;
            index.rows[dataset] = std::move(row);
            ++index.fitted;
            offset = next;
            index.end = next;
        }
    } catch (const std::exception& refusal) {
        ScanResultIndex error;
        error.error = refusal.what();
        error.rows.resize(datasets.files.size());
        return error;
    }
    return index;
}

}  // namespace

std::vector<std::string> read_scan_row(const Project& project, std::int64_t offset) {
    if (!scan_state_present(scan_results_path(project), "analysis/results.csv")) {
        throw std::invalid_argument("analysis/results.csv is not there; it has no row at byte " +
                                    std::to_string(offset));
    }
    std::ifstream input(scan_results_path(project), std::ios::binary);
    std::string line;
    if (!input || offset < 0 || !input.seekg(offset) || !std::getline(input, line) || input.eof()) {
        throw std::invalid_argument("analysis/results.csv has no complete row at byte " + std::to_string(offset));
    }
    return split_scan_row(line);
}

std::vector<std::string> evolution_parameters(const Project& project, const ScanResultIndex& index) {
    std::vector<std::string> names;
    std::set<std::string> columns;
    for (const NamedParameter& parameter : named_parameters(project)) {
        if (parameter.parameter->free) {
            names.push_back(parameter.unique_name);
            columns.insert(scan_results_column(parameter.unique_name));
        }
    }
    for (const ScanParameterColumns& parameter : index.parameters) {
        if (columns.insert(parameter.name).second) {
            names.push_back(parameter.name);
        }
    }
    return names;
}

void evolution_series(const Project& project, const ScanPlaces& places, const ScanResultIndex& index,
                      const std::string& parameter, bool by_value,
                      const std::function<void(const EvolutionPoint&)>& visit) {
    evolution_series(project, places, index, std::vector<std::string>{parameter}, by_value,
                     [&visit](std::size_t, const EvolutionPoint& point) { visit(point); });
}

void evolution_series(const Project& project, const ScanPlaces& places, const ScanResultIndex& index,
                      const std::vector<std::string>& parameters, bool by_value,
                      const std::function<void(std::size_t, const EvolutionPoint&)>& visit) {
    // Each parameter's value and s.u. columns, by its unique name or its results column; none for one not recorded.
    std::vector<const ScanParameterColumns*> columns(parameters.size(), nullptr);
    bool any = false;
    for (std::size_t i = 0; i < parameters.size(); ++i) {
        for (const std::string& name : {parameters[i], scan_results_column(parameters[i])}) {
            for (const ScanParameterColumns& recorded : index.parameters) {
                if (columns[i] == nullptr && recorded.name == name) {
                    columns[i] = &recorded;
                    any = true;
                }
            }
        }
    }
    if (!any || !index.error.empty() || !scan_state_present(scan_results_path(project), "analysis/results.csv")) {
        return;
    }
    std::ifstream input(scan_results_path(project), std::ios::binary);
    std::string line;
    // The columns mean what the indexed header says only while the file still has that header.
    if (!std::getline(input, line) || split_scan_row(line) != index.header) {
        return;
    }
    const bool extracted = by_value && !project.sequential_fit.extract.empty() && !index.extract.empty();
    std::int64_t offset = input.tellg();
    while (offset < index.end && std::getline(input, line) && !input.eof()) {
        offset = input.tellg();
        const std::vector<std::string> cells = split_scan_row(line);
        if (cells.size() != index.header.size()) {
            continue;
        }
        const auto place = places.find(scan_row_file(index, cells));
        // A refused file's row holds the values its fit started from, not a result.
        if (place == places.end() || cells[index.chi] == "nan") {
            continue;
        }
        double x = static_cast<double>(place->second + 1);
        if (extracted) {
            const std::ptrdiff_t column = index.extract.front();
            if (column < 0 || !parse_scan_number(cells[static_cast<std::size_t>(column)], x)) {
                continue;
            }
        }
        for (std::size_t i = 0; i < parameters.size(); ++i) {
            EvolutionPoint point;
            point.x = x;
            point.dataset = place->second;
            if (columns[i] == nullptr || !parse_scan_number(cells[columns[i]->value], point.y) ||
                !parse_scan_number(cells[columns[i]->uncertainty], point.su)) {
                continue;
            }
            constexpr double kLimit = 1e300;
            if (std::isfinite(point.x) && std::isfinite(point.y) && std::isfinite(point.su) && point.su >= 0.0 &&
                std::abs(point.x) <= kLimit && std::abs(point.y - point.su) <= kLimit &&
                std::abs(point.y + point.su) <= kLimit) {
                visit(i, point);
            }
        }
    }
}

void check_scan_template_file(const Project& project, const std::string& file) {
    crysta::SequentialFitConfig config;
    fill_crysta_sequential(project.sequential_fit, config);
    crysta::check_sequential_template_file(config, project.scan_data_root.empty() ? project.path : project.scan_data_root,
                                           file);
}

void set_scan_template_file(Project& project, const std::string& file) {
    check_scan_template_file(project, file);
    if (project.experiments.size() != 1) {
        throw std::invalid_argument("_sequential_fit.template_file: a scan has one template experiment; this project "
                                    "has " + std::to_string(project.experiments.size()));
    }
    // The data are read where the driver reads them (the scan data root of a project whose outputs go
    // elsewhere), and the template then holds measured data: no longer a range or a grid.
    const std::string directory =
        crysta::resolve_sequential_scan_dir(project.scan_data_root.empty() ? project.path : project.scan_data_root,
                                            project.sequential_fit.data_dir);
    PdDataBase data = read_scan_dataset(directory, file, project.experiment().effective_beam_mode());
    project.experiment().data = std::move(data);
    project.experiment().calculation_only = false;
    project.sequential_fit.template_file = file;
}

std::string scan_results_column(const std::string& unique_name) {
    const std::string category = ".instrument.";
    const std::size_t at = unique_name.find(category);
    if (at == std::string::npos) {
        return unique_name;
    }
    const std::size_t field = at + category.size();
    for (const std::string prefix : {"calib_", "setup_"}) {
        if (unique_name.compare(field, prefix.size(), prefix) == 0) {
            return unique_name.substr(0, field) + unique_name.substr(field + prefix.size());
        }
    }
    return unique_name;
}

std::string scan_target_unit(const std::string& target) {
    return target == "diffrn.ambient_temperature" ? std::string("K") : std::string();
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

#if __has_include("crysta/report_settings.hpp")  // drop the guard when the pin moves
// ADR-0036 §7: the report's settings, its saved-report rows and the two Analysis view items, as crysta writes them.
void copy_report_settings(const Project& model, crysta::Project& cproject) {
    cproject.report_html = model.report_html;
    cproject.report_pdf = model.report_pdf;
    cproject.report_cif = model.report_cif;
    cproject.report_html_offline = model.report_html_offline;
    cproject.report_excluded = model.report_excluded;
    cproject.report_files.clear();
    for (const auto& file : model.report_files) {
        crysta::ReportFile row;
        row.name = file->name.value();
        row.format = file->format.value();
        row.saved = file->saved.value();
        row.project_last_modified = file->project_last_modified.value();
        row.digest = file->digest.value();
        cproject.report_files.push_back(row);
    }
    cproject.correlation_threshold = model.correlation_threshold;
    cproject.pattern_x_axis = model.pattern_x_axis;
}
#endif

}  // namespace

void check_report_setting(const std::string& tag, const std::string& value) {
    const std::string_view name(tag);
    if (name.starts_with("_report.")) {
        Project scratch;
        detail::read_report_item(name.substr(std::string_view("_report.").size()), value, scratch);
    } else if (name == "_correlation_chart.threshold") {
        (void)detail::read_correlation_threshold(value);
    } else if (name == "_pattern_chart.x_axis") {
        (void)detail::read_pattern_x_axis(value);
    } else {
        throw std::invalid_argument(tag + " is not a report setting");
    }
}

bool save_report_settings(const Project& model, const std::string& directory) {
#if __has_include("crysta/report_settings.hpp")  // drop the guard when the pin moves
    // Only the report's settings cross: a project of nothing else carries them to crysta's writer.
    const crysta::Project carrier(std::vector<crysta::Structure>{}, std::vector<crysta::BraggPdExperiment>{},
                                  [&model](crysta::Project& project) { copy_report_settings(model, project); });
    return crysta::write_report_settings(carrier, directory);
#else
    (void)model;
    (void)directory;
    throw std::invalid_argument("saving the report settings needs a newer crysta");
#endif
}

std::string report_settings_text(const Project& model) {
#if __has_include("crysta/report_settings.hpp")  // drop the guard when the pin moves
    const crysta::Project carrier(std::vector<crysta::Structure>{}, std::vector<crysta::BraggPdExperiment>{},
                                  [&model](crysta::Project& project) {
                                      copy_report_settings(model, project);
                                      // The defaults effective_report_options takes for a setting left unstated.
                                      project.report_html = std::optional<bool>(model.report_html.value_or(true));
                                      project.report_pdf = std::optional<bool>(model.report_pdf.value_or(false));
                                      project.report_cif = std::optional<bool>(model.report_cif.value_or(false));
                                      project.report_html_offline =
                                          std::optional<bool>(model.report_html_offline.value_or(false));
                                      project.report_excluded =
                                          std::optional<std::string>(model.report_excluded.value_or("data"));
                                  });
    return crysta::report_settings_text(carrier);
#else
    (void)model;
    throw std::invalid_argument("showing the report settings needs a newer crysta");
#endif
}

namespace {

// The engine project a save writes, handed to `use`. Edi does not write — it asks crysta to. Build
// the full engine project from the model through the one conversion choke point (completed cell,
// start-carrying parameters), fill the persistence-only fields the calculation conversion never
// needed, and stamp the loader-grade identity with crysta's own exported stamp. crysta::Project
// cannot move, so it is lent rather than returned.
void with_saved_project(const Project& model, const std::function<void(crysta::Project&)>& use) {
    BuiltExperiments built_experiments;
    built_experiments.reserve(model.experiments.size());
    for (const auto& e_item : model.experiments) {
        const ExperimentBase& e = *e_item;
        crysta::BraggPdExperiment& built = build_on_heap(built_experiments, e);
        built.calculation_only = e.calculation_only;
        built.fit_n_data_points = e.fit_n_data_points;  // The bank's share of the last fit
        built.fit_prof_r_factor = e.fit_prof_r_factor;
        built.fit_prof_wr_factor = e.fit_prof_wr_factor;
        built.fit_prof_wr_expected = e.fit_prof_wr_expected;
        built.fit_prof_cr_factor = e.fit_prof_cr_factor;
        built.fit_prof_cwr_factor = e.fit_prof_cwr_factor;
        built.fit_chi_square = e.fit_chi_square;
        // Each phase's share; the links crossed in order (convert_experiment).
        for (std::size_t index = 0; index < built.linked_structures.size() && index < e.linked_structures.size();
             ++index) {
            built.linked_structures[index].fit_bragg_r_factor = e.linked_structures[index]->fit_bragg_r_factor;
            built.linked_structures[index].fit_f_r_factor = e.linked_structures[index]->fit_f_r_factor;
        }
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
        to.prof_r_factor = from.prof_r_factor;
        to.prof_wr_expected = from.prof_wr_expected;
        to.prof_cr_factor = from.prof_cr_factor;
        to.prof_cwr_factor = from.prof_cwr_factor;
        to.profile_function = from.profile_function;
        to.background_function = from.background_function;
        to.descent = from.descent;
        // A scan's per-file pairs are held with no result, so they cross whether or not one is held.
        std::vector<crysta::FitParameterCorrelation> rows;
        rows.reserve(from.correlations.size());
        for (const auto& row : from.correlations) {
            crysta::FitParameterCorrelation& copy = rows.emplace_back();
            copy.id = row->id.value();
            copy.source_kind = row->source_kind.value();
            copy.parameter_unique_name_i = row->parameter_unique_name_i.value();
            copy.parameter_unique_name_j = row->parameter_unique_name_j.value();
            copy.correlation = row->correlation.value();
            copy.file_path = row->file_path.value();
        }
        to.correlations.assign(rows);
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
    // Scan data read in place (a temporary copy of a read-only project) are carried into the saved one.
    cproject.scan_data_root = model.scan_data_root;
    // The project identity rides the delegated save. Copy the persisted metadata fields
    // across (the two ProjectMetadata mirrors are distinct C++ types; `path` is engine
    // bookkeeping the record never carries) and ENGAGE persistence — crysta's writer then merges
    // the `_metadata.*` block into a carried project.edi, or creates the record when none
    // exists. Safe to engage from here and only here: edi's loader restores the record's fields,
    // so this save writes back what a load carried in; crysta-native saves stay disengaged and
    // byte-identical.
    cproject.metadata.name = model.metadata.name;
    cproject.metadata.title = model.metadata.title;
    cproject.metadata.description = model.metadata.description;
#if __has_include("crysta/su_format.hpp")  // crysta's SDK; drop the guard when the pin moves
    cproject.metadata.authors = model.metadata.authors;
#endif
    cproject.metadata.created = model.metadata.created;
    cproject.metadata.last_modified = model.metadata.last_modified;
    cproject.metadata.timestamp = model.metadata.timestamp;
    cproject.persist_metadata = true;
#if __has_include("crysta/su_format.hpp")  // drop the guard when the pin moves
    // The delegated writer spells every value with an s.u. by the project's rule.
    cproject.su_rule = model.su_rule;
#endif
#if __has_include("crysta/report_settings.hpp")  // drop the guard when the pin moves
    // And writes the report's settings and saved-report rows, and the two Analysis view items.
    copy_report_settings(model, cproject);
#endif
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
        // A save writes edi's points. A bank whose estimate is due (its settings or data changed since its points)
        // is never current, so its columns stay out; the engine's calculation estimates it, and its points and
        // digests are put back afterwards (ADR-0040).
        // The whole background: points, or terms with their origin or domain, and its estimate record.
        struct HeldPoints {
            std::vector<crysta::LineSegment> points;
            std::vector<crysta::PolynomialTerm> terms;
            std::optional<double> origin, x_min, x_max;
            std::optional<std::string> mode;
            std::uint64_t inputs = 0;
            std::uint64_t written = 0;
        };
        std::vector<std::optional<HeldPoints>> held(cproject.experiments.size());
        for (std::size_t index = 0; index < model.experiments.size(); ++index) {
            if (background_estimate_due(*model.experiments[index])) {
                const crysta::BraggPdExperiment& bank = cproject.experiments[index];
                held[index] = HeldPoints{{bank.background.begin(), bank.background.end()},
                                         {bank.background_terms.begin(), bank.background_terms.end()},
                                         bank.background_origin.get(),
                                         bank.background_x_min.get(),
                                         bank.background_x_max.get(),
                                         bank.background_estimate_mode.get(),
                                         bank.background_estimate_inputs.get(),
                                         bank.background_estimate_points.get()};
            }
        }
        try {
            crysta::calculate_project(cproject);
        } catch (const std::invalid_argument&) {  // NOLINT(bugprone-empty-catch) — saved uncomputed
        }
        for (std::size_t index = 0; index < held.size(); ++index) {
            if (held[index]) {
                crysta::BraggPdExperiment& bank = cproject.experiments[index];
                bank.background.assign(held[index]->points);
                bank.background_terms.assign(held[index]->terms);
                bank.background_origin = held[index]->origin;
                bank.background_x_min = held[index]->x_min;
                bank.background_x_max = held[index]->x_max;
                bank.background_estimate_mode = held[index]->mode;
                bank.background_estimate_inputs = held[index]->inputs;
                bank.background_estimate_points = held[index]->written;
            }
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
    use(cproject);
}

}  // namespace

void save_project_via_crysta(const Project& model, const std::string& directory) {
    // crysta::save_project does the write: staging, atomic publish and fail-closed validation are its own.
    with_saved_project(model, [&directory](crysta::Project& project) {
        try {
            crysta::save_project(project, directory);
        } catch (const std::exception& error) {
            raise_coded(error);
            throw;
        }
    });
}

std::string cif_report_text(const Project& model) {
#if __has_include("crysta/cif_report.hpp")  // drop the guard when the pin moves
    std::string text;
    with_saved_project(model, [&text](crysta::Project& project) { text = crysta::cif_report(project); });
    return text;
#else
    (void)model;
    throw std::invalid_argument("the CIF report needs a newer crysta");
#endif
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

// The names are crysta's dictionary's; against an SDK without them every name is current.
std::string current_edi_name(const std::string& tag, bool every_name) {
#if __has_include("crysta/dictionary_items.hpp")  // drop the guard when the pin moves
    return crysta::current_edi_name(tag, every_name);
#else
    static_cast<void>(every_name);
    return tag;
#endif
}

// The CIF import is crysta's; against an SDK without it a text is read as `.edi`.
std::optional<std::string> structure_edi_from_cif(const std::string& text) {
#if __has_include("crysta/dictionary_items.hpp")  // drop the guard when the pin moves
    return crysta::structure_edi_from_cif(text);
#else
    static_cast<void>(text);
    return std::nullopt;
#endif
}

#if __has_include("crysta/report_settings.hpp")  // drop the guard when the pin moves
void read_report_item(std::string_view item, const std::string& value, Project& project) {
    const crysta::ReportItemValue read = crysta::read_report_item(item, value);
    if (item == "html") {
        project.report_html = read.flag;
    } else if (item == "pdf") {
        project.report_pdf = read.flag;
    } else if (item == "cif") {
        project.report_cif = read.flag;
    } else if (item == "html_offline") {
        project.report_html_offline = read.flag;
    } else {
        project.report_excluded = read.keys;
    }
}
double read_correlation_threshold(const std::string& value) { return crysta::read_correlation_threshold(value); }
std::string read_pattern_x_axis(const std::string& value) { return crysta::read_pattern_x_axis(value); }
std::string read_report_file_format(const std::string& value) { return crysta::read_report_file_format(value); }
#else
namespace {
[[noreturn]] void needs_newer_crysta() {
    throw std::invalid_argument("the report settings need a newer crysta");
}
}  // namespace
void read_report_item(std::string_view, const std::string&, Project&) { needs_newer_crysta(); }
double read_correlation_threshold(const std::string&) { needs_newer_crysta(); }
std::string read_pattern_x_axis(const std::string&) { needs_newer_crysta(); }
std::string read_report_file_format(const std::string&) { needs_newer_crysta(); }
#endif

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

// The anisotropic sites' tensors, in their declared types.
std::vector<crysta::AtomSiteAniso> to_crysta_atom_site_aniso(const Structure& s) {
    std::vector<crysta::AtomSiteAniso> rows;
    rows.reserve(s.atom_site_aniso.size());
    for (const auto& item : s.atom_site_aniso) {
        const AtomSiteAniso& t = *item;
        rows.emplace_back(t.id.value(),
                          std::array<crysta::Parameter, 6>{
                              param(t.adp_11, crysta::ADP, "adp_11"), param(t.adp_22, crysta::ADP, "adp_22"),
                              param(t.adp_33, crysta::ADP, "adp_33"), param(t.adp_12, crysta::ADP, "adp_12"),
                              param(t.adp_13, crysta::ADP, "adp_13"), param(t.adp_23, crysta::ADP, "adp_23")});
    }
    return rows;
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
// apply_post_build_fields then writes every link, so no phase is dropped. A bank with no link has no scale to
// seed: it converts with none, and crysta decides what it admits (background alone, no fit).
const Parameter& seed_scale(const ExperimentBase& e) {
    if (e.linked_structures.empty()) {
        static const Parameter no_scale{};
        return no_scale;
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
//   dataset_weight, excluded_regions  the per-bank joint weight and mask;
//   data_file     the plain-data file the measured data came from, which the save writes back.
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
    built.data_file = e.data_file;
    // ADR-0040: the estimate settings, with the mode in force and, in auto mode, what the points came from, so a save
    // writes edi's mode and digests and the engine estimates again only what edi would.
    if (e.background_estimate_mode) {
        built.background_estimate_mode = background_estimate_mode(e);
        if (*built.background_estimate_mode.get() == "auto") {
            built.background_estimate_inputs = e.background_estimate_inputs;
            built.background_estimate_points = e.background_estimate_points;
        }
    }
    built.background_estimate_method = e.background_estimate_method;
    built.background_estimate_width = e.background_estimate_width;
    built.background_estimate_smoothness = e.background_estimate_smoothness;
    built.background_estimate_n_points = e.background_estimate_n_points;
    built.background_estimate_tolerance = e.background_estimate_tolerance;
    built.background_estimate_in_peaks = e.background_estimate_in_peaks;
    built.background_estimate_use_model = e.background_estimate_use_model;
    built.background_estimate_max_terms = e.background_estimate_max_terms;
    std::vector<crysta::ExcludedRegion> regions;
    regions.reserve(e.excluded_regions.size());
    for (const auto& region : e.excluded_regions) {
        regions.emplace_back(region->first.get(), region->second.get());
        regions.back().id = region->id.value();
    }
    built.excluded_regions = regions;
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
            terms.back().id = term->id.value();
        }
        built.background_terms.assign(terms);
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
    instrument.reserve(8);
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
    // An X-ray experiment's monochromator polarization at instrument[4]/[5] and its K-alpha doublet
    // at [6]/[7], crysta's 8-wide X-ray layout; absent takes the loader's default 0 under the same
    // no-uncertainty rule. A neutron experiment stays 4-wide, as crysta's loader builds it.
    if (e.experiment_type.effective_radiation_probe() == RadiationProbeEnum::XRAY) {
        instrument.push_back(param(e.instrument.setup_polarization_coefficient.value_or(undeclared_shift),
                                   crysta::CALIBRATION, "setup_polarization_coefficient"));
        instrument.push_back(param(e.instrument.setup_monochromator_twotheta.value_or(undeclared_shift),
                                   crysta::CALIBRATION, "setup_monochromator_twotheta"));
        instrument.push_back(param(e.instrument.setup_wavelength_2.value_or(undeclared_shift),
                                   crysta::CALIBRATION, "setup_wavelength_2"));
        instrument.push_back(param(e.instrument.setup_wavelength_2_to_1_ratio.value_or(undeclared_shift),
                                   crysta::CALIBRATION, "setup_wavelength_2_to_1_ratio"));
    }
    std::vector<crysta::LineSegment> background;
    background.reserve(e.background.size());
    for (const auto& point : e.background) {
        background.emplace_back(point->position,
                                param(point->intensity, crysta::BACKGROUND, "intensity"));
        background.back().id = point->id.value();
    }
    crysta::BraggPdExperiment built(std::move(peak), std::move(instrument),
                             param(seed_scale(e), crysta::SCALE, "scale"), std::move(background));
    built.cutoff_fwhm = e.peak.cutoff_fwhm;
    built.kind = crysta::BeamModeEnum::ConstantWavelength;  // before the post-build fill: the
    // TOF-only abscor guard reads it
    apply_post_build_fields(e, built);
    if (!e.peak.type) {
        built.peak_type = "cwl-tch-pseudo-voigt";  // never leave the TOF default on a CW experiment
    }
    return crysta::BraggPdExperiment(built);  // a copy: an experiment never moves
}

// The ONE admission rule for the X-ray monochromator polarization and K-alpha doublet on an experiment
// that is not
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
              "setup_monochromator_twotheta", &e.instrument.setup_monochromator_twotheta},
          std::pair<const char*, const OptionalParameter*>{"setup_wavelength_2",
                                                           &e.instrument.setup_wavelength_2},
          std::pair<const char*, const OptionalParameter*>{
              "setup_wavelength_2_to_1_ratio", &e.instrument.setup_wavelength_2_to_1_ratio}}) {
        if (!*slot) {
            continue;
        }
        const Parameter& p = **slot;
        if (p.value != 0.0 || p.free || p.uncertainty.has_value() || p.start_value.has_value()) {
            throw std::invalid_argument(
                "experiment '" + e.name + "' carries _instrument." + name +
                (p.free ? " (free)" : "") +
                " but is not an X-ray constant-wavelength experiment — the " +
                (std::string(name).starts_with("setup_wavelength_2") ? "K-alpha doublet"
                                                                     : "monochromator polarization") +
                " is X-ray CW only: reset it to 0 and fixed, or declare the experiment X-ray CW");
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
        .scale(state(seed_scale(e)))
        .setup_twotheta_bank(e.instrument.setup_twotheta_bank.value)
        .cutoff_fwhm(e.peak.cutoff_fwhm);

    std::vector<crysta::LineSegment> background;
    background.reserve(e.background.size());
    for (const auto& point : e.background) {
        background.emplace_back(point->position,
                                param(point->intensity, crysta::BACKGROUND, "intensity"));
        background.back().id = point->id.value();
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
    refresh_background_estimates(*this);  // ADR-0040: auto background mode re-estimates first
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

}  // namespace

std::optional<WeightFraction> weight_fraction(const LinkedStructure& link) {
    const detail::Membership* membership = link.row.record();
    const detail::KeyedBase* owner = membership != nullptr ? membership->owner : nullptr;
    const Project* model = owner != nullptr ? owner->host() : nullptr;
    if (model == nullptr) {
        return std::nullopt;
    }
    std::size_t index = 0;
    bool found = false;
    for (const auto& item : model->experiments) {
        if (static_cast<const detail::KeyedBase*>(&item->linked_structures) == owner) {
            found = true;
            break;
        }
        ++index;
    }
    if (!found) {
        return std::nullopt;
    }
    RelationProject converted = relation_project(*model);
    // The correlations between scales the last fit stored, by the unique names crysta resolves.
    std::vector<crysta::FitParameterCorrelation> rows;
    for (const auto& row : model->fit_result.correlations) {
        crysta::FitParameterCorrelation& copy = rows.emplace_back();
        copy.id = row->id.value();
        copy.parameter_unique_name_i = row->parameter_unique_name_i.value();
        copy.parameter_unique_name_j = row->parameter_unique_name_j.value();
        copy.correlation = row->correlation.value();
        copy.file_path = row->file_path.value();
    }
    converted.project->fit_result.correlations.assign(rows);
    const std::optional<crysta::WeightFraction> fraction = crysta::weight_fraction(
        *converted.project, converted.project->experiments[index], link.structure_id.value());
    if (!fraction) {
        return std::nullopt;
    }
    return WeightFraction{fraction->value, fraction->uncertainty};
}

namespace {

enum class Completion : std::uint8_t { Values, ValuesAndUncertainties };

// Every dependent of `converted` set from its relation by crysta's one applier, then copied onto
// the model by unique name: its value, and after a fit its e.s.d., keeping the one it held before
// the fit for undo (a dependent has no fit-start row, so nothing is written for it).
std::set<const Parameter*> copy_dependents(crysta::Project& converted, Project& model,
                                           Completion completion) {
    const crysta::RelationGraph relations = crysta::apply_relations(converted, false);
    std::map<std::string, Parameter*> by_name;
    for (const NamedSlot& slot : named_slots(model)) {
        by_name.emplace(slot.unique_name, slot.parameter);
    }
    std::set<const Parameter*> dependents;
    for (const crysta::Relation& relation : relations.relations()) {
        const auto found = by_name.find(relation.target_name);
        if (found == by_name.end()) {
            continue;
        }
        Parameter& target = *found->second;
        dependents.insert(&target);
        if (target.value.get() != relation.target->value()) {
            target.value = relation.target->value();
        }
        if (completion == Completion::ValuesAndUncertainties) {
            target.start_uncertainty = target.uncertainty.get();
            // A present zero is edi's fixed value with no s.u.; crysta reads it as none, which is no change.
            if (relation.target->uncertainty().has_value() || target.uncertainty.get() != std::optional<double>(0.0)) {
                target.uncertainty = relation.target->uncertainty();
            }
        }
    }
    return dependents;
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
// when there is a sink to give it to. From a file, a constrained dependent's bracket with a nonzero s.u.
// is that s.u., not a free flag, so it goes without the warning.
void mark_dependents(Project& model, const crysta::RelationGraph& relations, const WarningSink& warn,
                     bool from_file = false) {
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
            const bool saved_su = from_file && relation.source == crysta::Dependence::Constrained &&
                                  target.uncertainty.get().value_or(0.0) != 0.0;
            if (warn && !saved_su) {
                warn("crysta.domain.dependent_free_ignored: parameter '" + relation.target_name +
                     "' is " + dependent_source(relation) +
                     "; free = True is ignored and it stays dependent");
            }
        }
    }
}

}  // namespace

void refresh_relations(Project& project, const WarningSink& warn, bool from_file) {
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
    mark_dependents(project, crysta::compile_relations(*converted->project, false), warn, from_file);
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

void restore_dependents(Project& project, const std::set<const Parameter*>& restored) {
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
        if (restored.contains(&target)) {
            continue;  // its own start row gave its e.s.d. back already
        }
        target.uncertainty = target.start_uncertainty.get();
        target.start_uncertainty = std::nullopt;
    }
}

int background_max_order(const std::string& type) {
    return crysta::background_max_order(crysta::background_form_of(type));
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
void publish_fit_state(Project& project, crysta::Project& converted, const std::vector<detail::RefinedValue>& refined) {
    for (const auto& structure : project.structures) {  // every structure (phase)
        rebalance_positional_fit_state(*structure);  // review-9 F1: lossless snapshot hand-off
    }
    // Every dependent as crysta completed it on the fit's own project (Wyckoff followers, cell
    // siblings and constrained parameters), values and e.s.d.s.
    const std::set<const Parameter*> dependents =
        copy_dependents(converted, project, Completion::ValuesAndUncertainties);
    // An s.u. belongs to the latest fit: a parameter this fit gave none (fixed, free in a phase it left out, or a
    // dependent no fitted parameter reaches, which crysta cleared) has none. Its prior s.u. becomes a start row at
    // its own value, as in crysta, so undo gives it back after a save and load too. Without an s.u. it gets no
    // row: an earlier fit's row would make undo restore a value this fit never moved.
    std::set<const Parameter*> fitted;
    for (const detail::RefinedValue& item : refined) {
        fitted.insert(item.resolved.target);
    }
    for (const NamedSlot& slot : named_slots(project)) {
        Parameter& p = *slot.parameter;
        if (fitted.contains(&p)) {
            continue;
        }
        if (dependents.contains(&p)) {
            // Its prior s.u. needs a row when crysta cleared it, and on a constrained dependent, whose s.u. a save
            // keeps, so undo after a reload gives it back.
            const bool kept = p.dependence == Dependence::Constrained && p.start_uncertainty.get().value_or(0.0) != 0.0;
            const bool cleared = !p.uncertainty.get().has_value() && p.start_uncertainty.get().value_or(0.0) != 0.0;
            if (kept || cleared) {
                p.start_value = p.value.get();
            }
            continue;
        }
        // A present zero is how edi spells a fixed value with no s.u., so it is neither cleared nor given a row.
        if (p.uncertainty.get().value_or(0.0) != 0.0) {
            p.start_value = p.value.get();
            p.start_uncertainty = p.uncertainty.get();
            p.uncertainty = std::optional<double>();
        } else {
            p.start_value.reset();
            p.start_uncertainty.reset();
        }
    }
    // A fit may refine auto-mode points; they are the background now (ADR-0040).
    for (const auto& experiment : project.experiments) {
        record_fitted_background(*experiment);
    }
    project.refresh_calculated_pattern();  // The pattern follows the model it describes
}

// The R factors of the fit that ran on `fitted` (its engine project, at the fitted values), over the measured
// patterns the fit read, one per bank: the caller's, which need not be the model's embedded data. A deque, because
// crysta's data node can't be moved and a vector may relocate its elements.
crysta::FitQuality fitted_quality(crysta::Project& fitted, const std::deque<crysta::PdDataBase>& measured,
                                  std::size_t n_free) {
    for (std::size_t bank = 0; bank < fitted.experiments.size() && bank < measured.size(); ++bank) {
        fitted.experiments[bank].data = measured[bank];
        fitted.experiments[bank].calculation_only = false;
        fitted.experiments[bank].explicit_grid = false;
        // The quality describes the points the fit ran with, never an estimate from these data (ADR-0040).
        if (fitted.experiments[bank].background_estimate_mode.get()) {
            crysta::set_background_estimate_mode(fitted.experiments[bank], "manual");
        }
    }
    crysta::calculate_project(fitted);
    return crysta::fit_quality(fitted, n_free);
}

// The fit's parameter correlations as crysta computes them over the project it fitted (crysta::fit_correlations:
// diffraction-lib's pairs from the covariance, by unique name, in crysta's shortest form), as edi's rows. One
// computation serves the app, Python and both CLIs.
// ADR-0034: what a scan run makes of its files' results: each file's bundle by file, the files this run fitted, the
// rows read with a file, and the last file's columns with their resolved names.
struct ScanRunResults {
    std::map<std::string, std::shared_ptr<const ScanFileResult>> results;
    std::set<std::string> fitted;
    std::vector<FitParameterCorrelation> read_rows;
    std::vector<std::string> labels;
    std::shared_ptr<const std::vector<std::string>> names;
};

// ADR-0034: a scan file's results from its fit. The correlations are numbers (I1 to I4); the names are resolved only
// when the file's columns differ from the previous file's, and are otherwise shared (I5).
std::shared_ptr<const ScanFileResult> scan_file_result(crysta::Project& project, const crysta::FitResultBase& result,
                                                       ScanRunResults& scan) {
    auto bundle = std::make_shared<ScanFileResult>();
    std::optional<std::vector<double>> values = crysta::correlation_values(result);
    if (!values) {
        return bundle;
    }
    if (!scan.names || scan.labels != result.covariance_labels) {
        std::optional<std::vector<std::string>> names = crysta::covariance_unique_names(project, result.covariance_labels);
        if (!names) {
            return bundle;
        }
        scan.names = std::make_shared<const std::vector<std::string>>(std::move(*names));
        scan.labels = result.covariance_labels;
    }
    auto table = std::make_shared<CorrelationTable>();
    table->names = scan.names;
    table->values = std::make_shared<const std::vector<double>>(std::move(*values));
    bundle->correlations = std::move(table);
    return bundle;
}

// ADR-0034: the record after a scan run. Its results by file are the run's. When this run fitted the template, the
// saved loop holds the template's rows made from its table (I6), and the other files' read rows move into their bundles
// as read (I7); otherwise the loop keeps the rows read with the files this run did not fit.
void settle_scan_results(FitResultRecord& record, ScanRunResults& scan, const std::string& template_file) {
    record.scan_results = std::move(scan.results);
    if (!template_file.empty() && scan.fitted.contains(template_file)) {
        std::vector<FitParameterCorrelation> template_rows;
        const auto found = record.scan_results.find(template_file);
        if (found != record.scan_results.end() && found->second && found->second->correlations) {
            template_rows = correlation_rows(*found->second->correlations, template_file);
        }
        std::vector<FitParameterCorrelation> others;
        for (const FitParameterCorrelation& row : scan.read_rows) {
            if (!scan.fitted.contains(row.file_path.value())) {
                others.push_back(row);
            }
        }
        hold_template_rows(record, std::move(template_rows), others, template_file);
        return;
    }
    std::vector<ItemVec<FitParameterCorrelation>::Ptr> rows;
    for (const FitParameterCorrelation& row : scan.read_rows) {
        if (!scan.fitted.contains(row.file_path.value())) {
            rows.push_back(std::make_shared<FitParameterCorrelation>(row));
        }
    }
    record.correlations.assign(std::move(rows));
}

std::vector<FitParameterCorrelation> crysta_correlations(crysta::Project& fitted, const crysta::FitResultBase& result) {
    std::vector<FitParameterCorrelation> rows;
    for (const crysta::FitParameterCorrelation& pair : crysta::fit_correlations(fitted, result)) {
        FitParameterCorrelation& row = rows.emplace_back();
        row.source_kind = pair.source_kind.get();
        row.parameter_unique_name_i = pair.parameter_unique_name_i.get();
        row.parameter_unique_name_j = pair.parameter_unique_name_j.get();
        row.correlation = pair.correlation.get();
    }
    return rows;
}

// The fit's result as the project records it (`_fit_result`, diffraction-lib's names, each experiment's share and
// each phase's), from what the fit returned — the same numbers the reports print — with the R factors and the
// parameter correlations crysta computed. The status label is crysta's machine-record spelling; the profile function
// is the peak type the experiments share (left out when they differ), the background edi's only one.
void record_fit_result(Project& project, FitResultBase& outcome, std::size_t considered,
                       std::vector<FitParameterCorrelation> correlations, const crysta::FitQuality& quality) {
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
    record.prof_r_factor = quality.pooled.rp;
    record.prof_wr_expected = quality.pooled.rexp;
    record.prof_cr_factor = quality.pooled.crp;
    record.prof_cwr_factor = quality.pooled.cwrp;
    const std::vector<ItemVec<FitParameterCorrelation>::Ptr> rows = numbered_correlations(correlations);
    outcome.correlations.clear();
    for (const auto& row : rows) {
        outcome.correlations.push_back(*row);
    }
    record.correlations.assign(rows);
    project.fit_result = std::move(record);
    for (const auto& experiment_item : project.experiments) {
        ExperimentBase& experiment = *experiment_item;
        clear_fit_share(experiment);
        for (const crysta::ProfileFactors& bank : quality.experiments) {
            if (bank.experiment == experiment.name) {
                experiment.fit_n_data_points = static_cast<int>(bank.n_points);
                experiment.fit_prof_r_factor = bank.rp;
                experiment.fit_prof_wr_factor = bank.rwp;
                experiment.fit_prof_wr_expected = bank.rexp;
                experiment.fit_prof_cr_factor = bank.crp;
                experiment.fit_prof_cwr_factor = bank.cwrp;
                experiment.fit_chi_square = bank.chi_square;
            }
        }
        // A bank the fit reported keeps the fit's own points, Rwp and chi-square, the numbers the report prints.
        for (const BankMetric& bank : outcome.banks) {
            if (bank.name == experiment.name) {
                experiment.fit_n_data_points = static_cast<int>(bank.n_points);
                experiment.fit_prof_wr_factor = bank.rwp;
                experiment.fit_chi_square = bank.chi_square;
            }
        }
        for (const auto& link : experiment.linked_structures) {
            const std::string& linked = link->structure_id.value();
            const std::string structure = KeyTraits<Structure>::canonical(
                linked.empty() && !project.structures.empty() ? project.structures.front()->name.value() : linked);
            for (const crysta::PhaseFactors& phase : quality.phases) {
                if (link->enabled.get() && phase.experiment == experiment.name &&
                    KeyTraits<Structure>::canonical(phase.structure) == structure) {
                    link->fit_bragg_r_factor = phase.r_bragg;
                    link->fit_f_r_factor = phase.r_f;
                }
            }
        }
    }
}

}  // namespace

void set_scan_file_start_observer(ScanFileStartObserver observer) { crysta::set_scan_file_start_observer(observer); }

void adopt_scan_file_result(FitResultRecord& record, const std::string& file,
                            std::shared_ptr<const ScanFileResult> result, const std::string& template_file) {
    record.scan_results[file] = std::move(result);
    if (!template_file.empty() && file == template_file) {
        const std::shared_ptr<const ScanFileResult>& adopted = record.scan_results[file];
        std::vector<FitParameterCorrelation> template_rows;
        if (adopted && adopted->correlations) {
            template_rows = correlation_rows(*adopted->correlations, file);
        }
        std::vector<FitParameterCorrelation> others;
        others.reserve(record.correlations.size());
        for (const auto& row : record.correlations) {
            others.push_back(*row);
        }
        hold_template_rows(record, std::move(template_rows), others, template_file);
        return;
    }
    // Another file's fit replaces the rows read with it; the rest stay as they are.
    const auto named = [&file](const auto& row) { return row->file_path.value() == file; };
    if (std::none_of(record.correlations.begin(), record.correlations.end(), named)) {
        return;
    }
    std::vector<ItemVec<FitParameterCorrelation>::Ptr> kept;
    for (const auto& row : record.correlations) {
        if (!named(row)) {
            kept.push_back(row);
        }
    }
    record.correlations.assign(std::move(kept));
}

std::vector<FitParameterCorrelation> correlation_rows(const CorrelationTable& table, const std::string& file) {
    std::vector<FitParameterCorrelation> rows;
    if (!table.names || !table.values) {
        return rows;
    }
    const std::vector<std::string>& names = *table.names;
    const std::vector<double>& values = *table.values;
    rows.reserve(values.size());
    for (std::size_t i = 0; i + 1 < names.size(); ++i) {
        for (std::size_t j = i + 1; j < names.size() && rows.size() < values.size(); ++j) {
            FitParameterCorrelation& row = rows.emplace_back();
            row.id = std::to_string(rows.size());
            row.source_kind = std::string("deterministic");
            row.parameter_unique_name_i = names[i];
            row.parameter_unique_name_j = names[j];
            row.correlation = crysta::correlation_text(values[rows.size() - 1]);
            row.file_path = file;
        }
    }
    return rows;
}

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

namespace {
// ADR-0040: an auto-mode background is estimated from the experiment's own measured pattern before a fit (the
// no-argument fits refresh first). A fit of other measurements, or one whose estimate is overdue, would solve with
// a background that does not belong to the data it fits, so it is refused before anything is built.
void require_auto_background_for(const ExperimentBase& experiment, const std::vector<double>& grid,
                                 const std::vector<double>& observed) {
    if (background_estimate_mode(experiment) != "auto") {
        return;
    }
    const bool own = experiment.data.has_value() && experiment.data->axis() == grid &&
                     experiment.data->intensity_meas.get() == observed;
    if (!own || background_estimate_due(experiment)) {
        throw std::invalid_argument("experiment '" + experiment.name +
                                    "': its background is estimated automatically from its own measured data, so a "
                                    "fit of other data cannot use it; set background_estimate.mode to manual, or fit "
                                    "the experiment's own data");
    }
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
    if (!experiments.empty()) {
        require_auto_background_for(experiment(), grid, observed);  // the one experiment a single fit fits
    }
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
        measured = crysta::apply_exclusions(measured, excluded_region_ranges(experiment().excluded_regions));
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
            publish_fit_state(*this, project, refined);
            record_fit_result(*this, outcome, considered, crysta_correlations(project, result),
                              fitted_quality(project, {crysta::PdDataBase(grid, observed, sigma)}, outcome.values.size()));
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
                                          const CancelCallback& should_cancel,
                                          const FileFittedCallback& on_file_fitted) {
    refresh_background_estimates(*this);  // ADR-0040: auto background mode re-estimates first
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
    return fit_scan(on_iteration, on_start, on_scan_start, on_file_complete, should_cancel, on_file_fitted);
}

FitResultBase Project::fit_sequential(const IterationCallback& on_iteration,
                                         const PreambleCallback& on_start,
                                         const ScanStartCallback& on_scan_start,
                                         const FileCompleteCallback& on_file_complete,
                                         const CancelCallback& should_cancel,
                                         const FileFittedCallback& on_file_fitted) {
    refresh_background_estimates(*this);  // ADR-0040: auto background mode re-estimates first
    // Serves EXACTLY `sequential` — the scan family is no longer accepted here.
    if (fitting_mode != "sequential") {
        throw std::invalid_argument("edi fit_sequential: _fitting_mode.type is '" +
                                    fitting_mode +
                                    "' - this entry point serves exactly the 'sequential' mode");
    }
    return fit_scan(on_iteration, on_start, on_scan_start, on_file_complete, should_cancel, on_file_fitted);
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

// A number cell reads as the project loader reads one (number_token.hpp): a stream read of a double diverges between
// the platforms' libraries.
bool parse_csv_cell(const std::string& cell, double& out) {
    return edi::detail::read_number(cell, out) == edi::detail::NumberToken::ok;
}

// A results row's file, as the scan's events name it: its file_path cell without the directory.
std::string scan_file_name(const std::string& file_path) {
    const std::size_t slash = file_path.rfind('/');
    return slash == std::string::npos ? file_path : file_path.substr(slash + 1);
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
    record.cells = cells;
    record.file_name = scan_file_name(cells[0]);
    record.converged = cells[2] == "True";
    if (!record.converged && cells[1] == "nan") {
        record.reduced_chi_square = std::numeric_limits<double>::quiet_NaN();  // a refused fit
    } else if (!parse_csv_cell(cells[1], record.reduced_chi_square)) {
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

// Every currently committed data row (header skipped). A missing or unreadable file reads as zero rows (the same
// view crysta's driver takes of a fresh scan) and a path that is not a regular file throws; a torn or foreign file
// is the driver's own fail-closed refusal, which edi does not preempt here.
std::vector<ScanFileRecord> read_scan_rows(const std::filesystem::path& csv_path) {
    std::vector<ScanFileRecord> rows;
    if (!scan_state_present(csv_path, "analysis/results.csv")) {
        return rows;
    }
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

// A scan file's pattern as crysta's fit left it on `fitted`: the measured and computed columns shared, not copied,
// the reflections grouped as capture_pattern groups them, the excluded regions and phase places from the template
// `model`. What a calculation of that file at its fitted values would show, without calculating it again.
PatternSource fitted_scan_pattern(const Project& model, const crysta::Project& fitted) {
    PatternSource source;
    const ExperimentBase& experiment = model.experiment();
    for (const auto& [start, end] : excluded_region_ranges(experiment.excluded_regions)) {
        source.excluded.push_back({std::min(start, end), std::max(start, end)});
    }
    source.x_title = experiment.effective_beam_mode() == BeamModeEnum::CONSTANT_WAVELENGTH ? "2θ (deg)" : "TOF (µs)";
    const crysta::ComputedView view = crysta::peek(fitted, fitted.experiment());
    const auto shared = [](const crysta::ColumnSnapshot<double>& column) -> PatternSource::Column {
        return column.empty() ? nullptr : column.buffer();
    };
    source.x = shared(view.data.axis);
    source.meas = shared(view.data.intensity_meas);
    source.su = shared(view.data.intensity_meas_su);
    source.current = view.data_state == crysta::ComputedState::Current &&
                     view.refln_state == crysta::ComputedState::Current;
    if (!source.current) {
        return source;
    }
    source.calc = shared(view.data.intensity_calc);
    source.bkg = shared(view.data.intensity_bkg);
    source.resid = shared(view.data.residual);
    std::vector<std::string> names;
    names.reserve(model.structures.size());
    for (const auto& structure : model.structures) {
        names.push_back(structure->name);
    }
    source.phases = group_reflections(view.refln.structure_id.values(), view.refln.position.values(),
                                      view.refln.index_h.values(), view.refln.index_k.values(),
                                      view.refln.index_l.values(), names);
    return source;
}

}  // namespace

// The ONE scan implementation. Both public scan entries reach it after proving their own exact
// token, so the code stays single while the public surface stays mode-specific.
FitResultBase Project::fit_scan(const IterationCallback& on_iteration,
                                   const PreambleCallback& on_start,
                                   const ScanStartCallback& on_scan_start,
                                   const FileCompleteCallback& on_file_complete,
                                   const CancelCallback& should_cancel,
                                   const FileFittedCallback& on_file_fitted) {
    refresh_background_estimates(*this);  // ADR-0040: auto background mode re-estimates first
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
        // Stateless rebuild-per-fit, the single-bank shape: one crysta Project over the
        // structures and the template experiment, with the identity and declarations the
        // sequential driver reads (structure names and experiment name feed the results.csv
        // column grammar; the scan block and iteration bound are the declared inputs).
        // Several structures (phases) are all handed over, as the single fit does, and crysta
        // fits each scan file through its phase-sum residual.
        const bool phases = structures.size() > 1 || experiment().linked_structures.size() != 1 ||
                            !experiment().linked_structure().enabled.get();
        crysta::Project cproject = [&]() -> crysta::Project {
            if (phases) {
                return crysta::Project(to_crysta_structures(*this),
                                       std::vector<crysta::BraggPdExperiment>{detail::to_crysta_experiment(experiment())});
            }
            return build_crysta_project(structure(), experiment());
        }();
        detail::require_populated_participants(cproject, "edi fit_sequential");
        fill_crysta_relations(*this, cproject);
        make_fit_ready(cproject.experiment());
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
        // The retained state is proven before anything is published: every state file the run reads, here and (for
        // a dry run that starts from the loaded project's results) there, is absent or a regular file.
        for (const char* name : {"results.csv", "results-provenance.csv", "scan-notes.csv"}) {
            scan_state_present(project_root / "analysis" / name, std::string("analysis/") + name);
            if (!scan_data_root.empty()) {
                scan_state_present(data_root / "analysis" / name, std::string("analysis/") + name);
            }
        }
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
                    scan_state_present(csv_path, "analysis/results.csv") || scan_data_root.empty()
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
        const std::filesystem::path ledger_path = project_root / "analysis" / "results-provenance.csv";
        auto completed_files = std::make_shared<std::size_t>(0);
        // ADR-0034: each file's results, by file: those an earlier run kept (a resume fits only the rest), then this
        // run's, each made once by its file's fit and shared from then on. The rows read with a file stay as read.
        auto scan = std::make_shared<ScanRunResults>();
        scan->results = fit_result.scan_results;
        for (const auto& pair : fit_result.correlations) {
            if (!pair->file_path.empty()) {
                scan->read_rows.push_back(*pair);
            }
        }
        // Each file's event carries its own fit result, so its correlations are crysta's from its covariance, as a
        // single fit's are, over the template project its labels name.
        const crysta::FileResultCallback engine_file_result =
            [this, file_history, last_file_history, ledger_path, completed_files, scan, &on_file_complete,
             &cproject](const std::vector<std::string>& row, const crysta::FitResultBase& file_result) {
                ++*completed_files;
                std::swap(*last_file_history, *file_history);
                file_history->clear();
                std::optional<ScanFileRecord> record = scan_record_from_cells(row);
                if (!record.has_value()) {
                    return;
                }
                record->result = scan_file_result(cproject, file_result, *scan);
                scan->results[record->file_name] = record->result;
                scan->fitted.insert(record->file_name);
                if (on_file_complete) {
                    // The driver wrote this file's ledger row just before its results row and waits
                    // here, so the ledger's last line is this file's.
                    record->termination = ledger_termination(ledger_path, row.empty() ? std::string() : row[0]);
                    on_file_complete(*record);
                }
            };
        crysta::FileFittedCallback engine_file_fitted;
        if (on_file_fitted) {
            engine_file_fitted = [this, &on_file_fitted](const std::vector<std::string>& row,
                                                         const crysta::Project& fitted) {
                if (row.empty()) {
                    return;
                }
                // The name the file's completion event carries, which the followed pattern is
                // matched to.
                on_file_fitted(scan_file_name(row[0]),
                               [this, &fitted] { return fitted_scan_pattern(*this, fitted); });
            };
        }
        const crysta::FitResultBase result = crysta::fit_project(
            cproject, engine_callback, should_cancel, crysta::FileCompleteCallback{}, engine_file_fitted,
            engine_file_result);
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
                detail::resolve_project_label(*this, experiment(), label);
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
        // crysta recovers the terminal result from its row (Rwp unavailable) when the terminal file
        // was not fitted by this call: on a completed scan, or after a gap filled before a file
        // fitted earlier. Its history is that file's and not known now, so none is reported, and
        // its iterations are the row's. Whether this call solved anything is its own completed
        // files, not the terminal record: fitting time is real when any file was fitted, none
        // otherwise (reading the CSV is not fitting time).
        const bool recovered = std::isnan(result.rwp);
        const bool solved = *completed_files > 0 || !recovered;
        FitResultBase outcome;
        if (!recovered) {
            outcome.iterations_history = result.cancelled ? *file_history : *last_file_history;
        }
        outcome.rwp = result.rwp;
        outcome.reduced_chi_square = result.reduced_chi_square;
        outcome.iterations = recovered ? result.iterations
                                       : static_cast<int>(outcome.iterations_history.size());
        outcome.converged = result.converged;
        outcome.elapsed_ms = solved ? elapsed_ms : 0.0;
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
            publish_fit_state(*this, cproject, refined);
            // crysta gives the R factors of the scan's template file when this call fitted it; otherwise there is
            // nothing to record, and an earlier fit's result would be stale. Each file's results are the scan's.
            if (result.scan_quality) {
                // The record describes the template file, not the file the scan ended on.
                const crysta::ProfileFactors& pooled = result.scan_quality->pooled;
                FitResultBase recorded = outcome;
                recorded.n_points_fitted = pooled.n_points;
                recorded.rwp = pooled.rwp;
                const std::size_t n_free = recorded.values.size();
                recorded.reduced_chi_square =
                    pooled.n_points > n_free ? pooled.chi_square / static_cast<double>(pooled.n_points - n_free) : 0.0;
                record_fit_result(*this, recorded, cproject.collect_parameters().size(), {}, *result.scan_quality);
            } else {
                clear_fit_result(*this);
            }
            settle_scan_results(fit_result, *scan, effective_scan_template_file(*this));
        } else if (*completed_files > 0) {
            // Each file this run completed has its row in results.csv, so its results are kept as well; a resume
            // skips that file and could not make them again. The unfinished file has none, and the rest of the
            // record stays as it was.
            settle_scan_results(fit_result, *scan, effective_scan_template_file(*this));
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
    for (std::size_t index = 0; index < experiments.size() && index < patterns.size(); ++index) {
        require_auto_background_for(*experiments[index], patterns[index].axis(),
                                    patterns[index].intensity_meas.get());
    }
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
            pattern = crysta::apply_exclusions(pattern, excluded_region_ranges(experiments[bank]->excluded_regions));
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
            publish_fit_state(*this, project, refined);
            std::deque<crysta::PdDataBase> fitted_patterns;
            for (const PdDataBase& pattern : patterns) {
                fitted_patterns.emplace_back(pattern.axis(), pattern.intensity_meas.get(), pattern.intensity_meas_su.get());
            }
            record_fit_result(*this, outcome, considered, crysta_correlations(project, result),
                              fitted_quality(project, fitted_patterns, outcome.values.size()));
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

std::vector<SpaceGroupSettingName> space_group_settings() {
    std::vector<SpaceGroupSettingName> settings;
    for (const crysta::SpaceGroupSettingName& entry : crysta::space_group_settings()) {
        settings.push_back({entry.it_number, entry.name_h_m, entry.coord_system_code, entry.setting});
    }
    return settings;
}

namespace {
const std::vector<SpaceGroupSettingName>& cached_settings() {
    static const std::vector<SpaceGroupSettingName> settings = space_group_settings();
    return settings;
}
std::string unspaced(const std::string& name) {
    std::string out;
    for (const char c : name) {
        if (c != ' ' && c != '\t') {
            out += c;
        }
    }
    return out;
}
template <class Pick>
std::optional<SpaceGroupSettingName> lowest_setting(Pick pick) {
    const SpaceGroupSettingName* found = nullptr;
    for (const SpaceGroupSettingName& setting : cached_settings()) {
        if (pick(setting) && (found == nullptr || setting.setting < found->setting)) {
            found = &setting;
        }
    }
    return found != nullptr ? std::optional<SpaceGroupSettingName>(*found) : std::nullopt;
}
}  // namespace

bool same_space_group_name(const std::string& a, const std::string& b) { return unspaced(a) == unspaced(b); }

std::optional<SpaceGroupSettingName> space_group_setting_for_name(const std::string& name) {
    const std::string wanted = unspaced(name);
    return lowest_setting([&wanted](const SpaceGroupSettingName& s) { return unspaced(s.name_h_m) == wanted; });
}

std::optional<SpaceGroupSettingName> space_group_setting_for_number(int it_number) {
    return lowest_setting([it_number](const SpaceGroupSettingName& s) { return s.it_number == it_number; });
}

std::optional<SpaceGroupSettingName> space_group_setting_for_code(int it_number, const std::string& code) {
    return lowest_setting(
        [it_number, &code](const SpaceGroupSettingName& s) { return s.it_number == it_number && s.coord_system_code == code; });
}

void assign_space_group_setting(SpaceGroup& group, const SpaceGroupSettingName& setting, bool declare_number) {
    group.name_h_m = setting.name_h_m;
    group.coord_system_code = setting.coord_system_code;
    if (declare_number || group.it_number.has_value()) {
        group.it_number = setting.it_number;
    }
}

std::vector<std::array<int, 9>> space_group_rotations(const SpaceGroup& space_group) {
    Structure structure;
    structure.space_group = space_group;
    std::vector<std::array<int, 9>> rotations;
    for (const crysta::SymmetryOperation& operation : crysta::symmetry_operations(resolve_group(structure))) {
        rotations.push_back(operation.rotation);
    }
    return rotations;
}

// The engine owns the policy; edi forwards through the one TU allowed to hold a crysta
// call (ADR-0003). See edi/threading.hpp for the contract.
void apply_engine_thread_defaults() noexcept { crysta::threading::apply_process_thread_defaults(); }

EngineThreading engine_threading() noexcept {
    return {crysta::threading::parallel_backend(), crysta::threading::parallel_workers(), crysta::threading::wasm_simd()};
}

void set_engine_threads(int count) noexcept { crysta::threading::set_thread_count(count); }

int engine_threads_setting() noexcept { return crysta::threading::thread_count_setting(); }

namespace {

static_assert(kDefaultBackgroundTolerance == crysta::kDefaultBackgroundTolerance);
static_assert(kAutoModelBelowShare == crysta::kAutoModelBelowShare);

crysta::BackgroundEstimateOptions engine_estimate_options(const BackgroundEstimateOptions& options) {
    crysta::BackgroundEstimateOptions out;
    out.method = options.method;
    out.width = options.width;
    out.smoothness = options.smoothness;
    out.n_points = options.n_points;
    out.tolerance = options.tolerance;
    out.in_peaks = options.in_peaks;
    out.use_model = options.use_model;
    out.max_terms = options.max_terms;
    return out;
}

// The pattern an estimate reads: the measured pattern on the whole axis, with the calculated one when
// the experiment holds it (stale or not, as diffraction-lib reads it: subtracting the calculated peaks
// stays right after a background edit). crysta keeps the points outside the excluded regions.
crysta::BackgroundEstimateInput engine_estimate_input(const ExperimentBase& experiment, const std::string& use_model) {
    if (!experiment.data.has_value() || experiment.data->intensity_meas.get().empty()) {
        return {};
    }
    const PdDataBase& data = *experiment.data;
    return crysta::background_estimate_input(data.axis(), data.intensity_meas.get(), data.intensity_calc.values(),
                                             data.intensity_bkg.values(),
                                             excluded_region_ranges(experiment.excluded_regions), use_model);
}

BackgroundEstimate from_engine(const crysta::BackgroundEstimate& estimate, bool used_model) {
    BackgroundEstimate out;
    out.method = estimate.method;
    out.model_choice = estimate.model_choice;
    out.model_reason = estimate.model_reason;
    out.width = estimate.width;
    out.noise = estimate.noise;
    out.used_model = used_model;
    out.warnings = estimate.warnings;
    for (const auto& [name, value] : estimate.backend_params) {
        if (name == "lam") {
            out.smoothness = value;
        } else if (name == "max_half_window") {
            out.half_window = static_cast<int>(value);
        }
    }
    out.summary = crysta::background_estimate_summary(estimate);
    return out;
}

}  // namespace

std::vector<std::string> background_estimator_methods() { return crysta::background_estimator_methods(); }

BackgroundEstimate background_estimate_defaults(const ExperimentBase& experiment,
                                                const BackgroundEstimateOptions& options) {
    const crysta::BackgroundEstimateInput input = engine_estimate_input(experiment, options.use_model);
    return from_engine(crysta::background_estimate_defaults(input, engine_estimate_options(options)),
                       input.used_model);
}

BackgroundEstimate estimate_background(const ExperimentBase& experiment, const BackgroundEstimateOptions& options) {
    const crysta::BackgroundEstimateInput input = engine_estimate_input(experiment, options.use_model);
    if (experiment.background_type != "line-segment") {
        // A polynomial about its origin, a Chebyshev series over its domain: the declared ones, else the middle
        // and the range of the included data.
        const double first = input.x.empty() ? 0.0 : input.x.front();
        const double last = input.x.empty() ? 1.0 : input.x.back();
        const crysta::BackgroundEstimate estimate = crysta::estimate_background_series(
            input, engine_estimate_options(options), experiment.background_type,
            experiment.background_origin.value_or(0.5 * (first + last)), experiment.background_x_min.value_or(first),
            experiment.background_x_max.value_or(last));
        BackgroundEstimate out = from_engine(estimate, input.used_model);
        out.origin = estimate.origin;
        out.x_min = estimate.x_min;
        out.x_max = estimate.x_max;
        for (std::size_t m = 0; m < estimate.coefficients.size(); ++m) {
            PolynomialTerm term;
            term.id = std::to_string(m);  // named by its order
            term.order = static_cast<int>(m);
            term.coef.value = estimate.coefficients[m];
            term.coef.free = false;
            out.terms.push_back(std::move(term));
        }
        return out;
    }
    const crysta::BackgroundEstimate estimate =
        crysta::estimate_background_points(input, engine_estimate_options(options));
    BackgroundEstimate out = from_engine(estimate, input.used_model);
    for (std::size_t i = 0; i < estimate.anchor_x.size(); ++i) {
        LineSegment point;
        point.id = std::to_string(i + 1);
        point.position = estimate.anchor_x[i];
        point.intensity.value = estimate.anchor_y[i];
        point.intensity.free = false;
        out.points.push_back(std::move(point));
    }
    return out;
}

namespace {

// What the points came from: 0 is no record (manual), kStaleEstimate "estimate at the next calculation". The digests
// are crysta's, so a file either product saves reads the same in both (ADR-0040).
constexpr std::uint64_t kNoRecord = 0;
constexpr std::uint64_t kStaleEstimate = 1;

std::uint64_t inputs_digest(const ExperimentBase& experiment, const BackgroundEstimateOptions& options) {
    // A series' basis, as crysta's own experiment digest has it.
    crysta::BackgroundSeriesBasis basis;
    if (experiment.background_type == "polynomial") {
        basis = {experiment.background_type, experiment.background_origin, {}, {}};
    } else if (experiment.background_type == "chebyshev") {
        basis = {experiment.background_type, {}, experiment.background_x_min, experiment.background_x_max};
    }
    return crysta::background_estimate_inputs_digest(engine_estimate_input(experiment, "ignore"),
                                                     engine_estimate_options(options), basis);
}

std::uint64_t points_digest(const ExperimentBase& experiment) {
    std::vector<crysta::BackgroundPointValues> points;
    if (experiment.background_type != "line-segment") {
        // A polynomial's or Chebyshev's terms, the order in place of a position, as the engine reads them.
        for (const auto& term : experiment.background_terms) {
            points.push_back({term->id.value(), static_cast<double>(term->order.get()), term->coef.value.get(),
                              term->coef.free.get()});
        }
        return crysta::background_points_digest(points);
    }
    points.reserve(experiment.background.size());
    for (const auto& point : experiment.background) {
        points.push_back({point->id.value(), point->position.get(), point->intensity.value.get(),
                          point->intensity.free.get()});
    }
    return crysta::background_points_digest(points);
}

bool declares_auto(const ExperimentBase& experiment) {
    return experiment.background_estimate_mode && *experiment.background_estimate_mode == "auto";
}

bool edited_by_hand(const ExperimentBase& experiment) {
    return experiment.background_estimate_points != kNoRecord &&
           experiment.background_estimate_points != points_digest(experiment);
}

bool has_included_points(const ExperimentBase& experiment) {
    return !engine_estimate_input(experiment, "ignore").x.empty();
}

}  // namespace

BackgroundEstimateOptions background_estimate_options(const ExperimentBase& experiment) {
    BackgroundEstimateOptions options;
    options.method = experiment.background_estimate_method.value_or("auto");
    options.width = experiment.background_estimate_width;
    options.smoothness = experiment.background_estimate_smoothness;
    options.n_points = experiment.background_estimate_n_points;
    options.tolerance = experiment.background_estimate_tolerance;
    options.in_peaks = experiment.background_estimate_in_peaks.value_or("move");
    options.use_model = experiment.background_estimate_use_model.value_or("auto");
    options.max_terms = experiment.background_estimate_max_terms;
    return options;
}

// ADR-0040: the declared mode; an auto-mode background whose rows differ from the estimate is refused, never read as
// manual.
std::string background_estimate_mode(const ExperimentBase& experiment) {
    return declares_auto(experiment) ? "auto" : "manual";
}

void set_background_estimate_mode(ExperimentBase& experiment, const std::string& mode) {
    if (mode != "manual" && mode != "auto") {
        throw std::invalid_argument("background_estimate.mode must be manual or auto, got '" + mode + "'.");
    }
    experiment.background_estimate_mode = mode;
    const bool automatic = mode == "auto";
    experiment.background_estimate_inputs = automatic ? kStaleEstimate : kNoRecord;
    experiment.background_estimate_points = automatic ? points_digest(experiment) : kNoRecord;
}

void set_background_estimate_method(ExperimentBase& experiment, const std::string& method) {
    crysta::resolve_background_estimator_method(method);
    experiment.background_estimate_method = method;
}

void set_background_estimate_width(ExperimentBase& experiment, std::optional<double> width) {
    crysta::BackgroundEstimateOptions check;
    check.width = width;
    crysta::validate_background_estimate_options(check);
    experiment.background_estimate_width = width;
}

void set_background_estimate_smoothness(ExperimentBase& experiment, std::optional<double> smoothness) {
    crysta::BackgroundEstimateOptions check;
    check.smoothness = smoothness;
    crysta::validate_background_estimate_options(check);
    experiment.background_estimate_smoothness = smoothness;
}

void set_background_estimate_n_points(ExperimentBase& experiment, std::optional<int> n_points) {
    crysta::BackgroundEstimateOptions check;
    check.n_points = n_points;
    crysta::validate_background_estimate_options(check);
    experiment.background_estimate_n_points = n_points;
}

void set_background_estimate_tolerance(ExperimentBase& experiment, std::optional<double> tolerance) {
    crysta::BackgroundEstimateOptions check;
    check.tolerance = tolerance;
    crysta::validate_background_estimate_options(check);
    experiment.background_estimate_tolerance = tolerance;
}

void set_background_estimate_in_peaks(ExperimentBase& experiment, const std::string& in_peaks) {
    crysta::BackgroundEstimateOptions check;
    check.in_peaks = in_peaks;
    crysta::validate_background_estimate_options(check);
    experiment.background_estimate_in_peaks = in_peaks;
}

void rebaseline_background_estimate(ExperimentBase& experiment) {
    if (declares_auto(experiment)) {
        experiment.background_estimate_inputs = kStaleEstimate;
        experiment.background_estimate_points = points_digest(experiment);
    }
}

void record_fitted_background(ExperimentBase& experiment) {
    if (declares_auto(experiment) && experiment.background_estimate_points != kNoRecord) {
        experiment.background_estimate_points = points_digest(experiment);
    }
}

void require_background_edit(const ExperimentBase& experiment) {
    if (background_estimate_mode(experiment) == "auto") {
        throw std::invalid_argument(
            "the background is estimated automatically (background_estimate.mode is auto); set "
            "background_estimate.mode to manual before editing its points or terms");
    }
}

std::vector<const Parameter*> estimated_background_values(const ExperimentBase& experiment) {
    std::vector<const Parameter*> values;
    if (background_estimate_mode(experiment) == "auto") {
        for (const auto& point : experiment.background) {
            values.push_back(&point->intensity);
        }
        for (const auto& term : experiment.background_terms) {
            values.push_back(&term->coef);
        }
    }
    return values;
}

void set_background_estimate_max_terms(ExperimentBase& experiment, std::optional<int> max_terms) {
    crysta::BackgroundEstimateOptions check;
    check.max_terms = max_terms;
    crysta::validate_background_estimate_options(check);
    experiment.background_estimate_max_terms = max_terms;
}

void set_background_estimate_use_model(ExperimentBase& experiment, const std::string& use_model) {
    crysta::BackgroundEstimateOptions check;
    check.use_model = use_model;
    crysta::validate_background_estimate_options(check);
    experiment.background_estimate_use_model = use_model;
}

std::uint64_t parse_background_digest(const std::string& text) { return crysta::parse_background_digest(text); }

void settle_loaded_background_estimate(ExperimentBase& experiment) {
    if (!declares_auto(experiment)) {
        experiment.background_estimate_inputs = kNoRecord;
        experiment.background_estimate_points = kNoRecord;
        return;
    }
    if (experiment.background_estimate_points == kNoRecord) {
        experiment.background_estimate_points = points_digest(experiment);
    }
    if (experiment.background_estimate_inputs == kNoRecord) {
        experiment.background_estimate_inputs = kStaleEstimate;
    }
}

void apply_background_estimate(ExperimentBase& experiment, const BackgroundEstimate& estimate,
                               const BackgroundEstimateOptions& options) {
    if (!estimate.terms.empty()) {
        set_background_terms(experiment, estimate.terms);
        // The origin or domain the terms are about, when the experiment declared none.
        if (experiment.background_type == "polynomial") {
            if (!experiment.background_origin) {
                experiment.background_origin = estimate.origin;
            }
        } else if (!experiment.background_x_min || !experiment.background_x_max) {
            experiment.background_x_min = estimate.x_min;
            experiment.background_x_max = estimate.x_max;
        }
        experiment.background_estimate_inputs = inputs_digest(experiment, options);
        experiment.background_estimate_points = points_digest(experiment);
        return;
    }
    if (estimate.points.empty()) {
        return;  // nothing measured: the points stay
    }
    set_background_points(experiment, estimate.points);
    experiment.background_estimate_inputs = inputs_digest(experiment, options);
    experiment.background_estimate_points = points_digest(experiment);
}

bool background_estimate_due(const ExperimentBase& experiment) {
    if (!declares_auto(experiment)) {
        return false;
    }
    if (edited_by_hand(experiment)) {
        return true;
    }
    if (!has_included_points(experiment)) {
        return false;
    }
    return experiment.background_estimate_inputs !=
           inputs_digest(experiment, background_estimate_options(experiment));
}

bool background_estimates_due(const Project& project) {
    return std::any_of(project.experiments.begin(), project.experiments.end(),
                       [](const auto& experiment) { return background_estimate_due(*experiment); });
}

bool refresh_background_estimates(Project& project, std::vector<std::pair<std::string, std::string>>* reasons) {
    if (!background_estimates_due(project)) {
        return false;
    }
    // crysta estimates, on the project a calculation would build, against the peaks of its current model; the
    // conversion carries each experiment's digests, so the engine estimates exactly the experiments due here.
    const BuiltExperiments banks = calculation_banks(project.experiments);
    crysta::Project engine(to_crysta_structures(project), experiment_list(banks));
    fill_crysta_relations(project, engine);
    std::vector<std::pair<std::size_t, std::string>> engine_reasons;
    crysta::refresh_background_estimates(engine, reasons != nullptr ? &engine_reasons : nullptr);
    if (reasons != nullptr) {
        for (const auto& [index, reason] : engine_reasons) {
            reasons->emplace_back(project.experiments[index]->name, reason);
        }
    }
    bool changed = false;
    for (std::size_t index = 0; index < project.experiments.size(); ++index) {
        ExperimentBase& experiment = *project.experiments[index];
        if (!background_estimate_due(experiment)) {
            continue;
        }
        if (edited_by_hand(experiment)) {
            // The engine refuses such an experiment before anything is written; never reached.
            throw std::invalid_argument("experiment '" + experiment.name +
                                        "': its background points or terms differ from the estimate while "
                                        "background_estimate.mode is auto; set background_estimate.mode to manual to "
                                        "keep them, or estimate again");
        }
        const crysta::BraggPdExperiment& estimated = engine.experiments[index];
        if (experiment.background_type != "line-segment") {
            std::vector<PolynomialTerm> terms;
            for (const crysta::PolynomialTerm& from : estimated.background_terms) {
                PolynomialTerm term;
                term.id = from.id.value();
                term.order = from.order.get();
                term.coef.value = from.coef.value();
                term.coef.free = from.coef.free();
                terms.push_back(std::move(term));
            }
            set_background_terms(experiment, terms);
            experiment.background_origin = estimated.background_origin.get();
            experiment.background_x_min = estimated.background_x_min.get();
            experiment.background_x_max = estimated.background_x_max.get();
            experiment.background_estimate_inputs = estimated.background_estimate_inputs.get();
            experiment.background_estimate_points = points_digest(experiment);
            changed = true;
            continue;
        }
        std::vector<LineSegment> points;
        points.reserve(estimated.background.size());
        for (const crysta::LineSegment& from : estimated.background) {
            LineSegment point;
            point.id = from.id.value();
            point.position = from.position.get();
            point.intensity.value = from.intensity.value();
            point.intensity.free = from.intensity.free();
            points.push_back(std::move(point));
        }
        set_background_points(experiment, points);
        experiment.background_estimate_inputs = estimated.background_estimate_inputs.get();
        experiment.background_estimate_points = points_digest(experiment);
        changed = true;
    }
    return changed;
}

BackgroundState capture_background(const ExperimentBase& experiment) {
    BackgroundState state;
    state.type = experiment.background_type;
    for (const auto& point : experiment.background) {
        state.points.push_back(*point);
    }
    for (const auto& term : experiment.background_terms) {
        state.terms.push_back(*term);
    }
    state.origin = experiment.background_origin;
    state.x_min = experiment.background_x_min;
    state.x_max = experiment.background_x_max;
    state.mode = experiment.background_estimate_mode;
    state.inputs = experiment.background_estimate_inputs;
    state.written = experiment.background_estimate_points;
    return state;
}

void restore_background(ExperimentBase& experiment, const BackgroundState& state) {
    // The whole typed state, the type included: an undo after a type change gives back the type with its rows, never
    // one type's rows in another's model.
    experiment.background_type = state.type;
    experiment.background.clear();
    experiment.background_terms.clear();
    if (state.type == "line-segment") {
        set_background_points(experiment, state.points);
    } else {
        set_background_terms(experiment, state.terms);
    }
    experiment.background_origin = state.origin;
    experiment.background_x_min = state.x_min;
    experiment.background_x_max = state.x_max;
    experiment.background_estimate_mode = state.mode;
    experiment.background_estimate_inputs = state.inputs;
    experiment.background_estimate_points = state.written;
}

}  // namespace edi
