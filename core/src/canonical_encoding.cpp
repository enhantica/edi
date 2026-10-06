// SPDX-License-Identifier: BSD-3-Clause
#include "canonical_encoding.hpp"

#include <bit>
#include <cstdint>
#include <cstdio>
#include <map>
#include <optional>
#include <string>
#include <vector>

#include "edi/categories.hpp"
#include "edi/model.hpp"
#include "parameter_paths.hpp"  // kPeakSlots: the peak[] slot order the encoding walks

// Lifted verbatim out of adapter.cpp; see the header for what this file is.

namespace edi {
namespace {

// --- canonical source encoding (the stale-source guard) ---------------------------------------
//
// An INJECTIVE byte encoding of everything in a Project that can affect the built engine graph, the
// parameter index, a calculation or a refinement. Compared VERBATIM (never hashed), so no digest
// collision can mask a mutation. Doubles are emitted as their exact 64-bit pattern, so -0.0 vs 0.0,
// NaN payloads and full precision all distinguish; strings and containers are length-prefixed, so no
// concatenation of one field can imitate another.
//
// Deliberately TOTAL over the whole Project — including `experiments` and `fitting_mode`, which the
// single-bank handle never reads. Failing closed on an unrelated edit is the conservative direction;
// missing a field is not. Adding a field to edi::Project REQUIRES extending this.
void put_u64(std::string& out, std::uint64_t value) {
    char buffer[17];
    std::snprintf(buffer, sizeof(buffer), "%016llx", static_cast<unsigned long long>(value));
    out.append(buffer, 16);
}

void put_double(std::string& out, double value) {
    put_u64(out, std::bit_cast<std::uint64_t>(value));
}

void put_text(std::string& out, const std::string& value) {
    put_u64(out, value.size());
    out += value;
    out += '\x1e';
}

// What an encoding covers: everything a calculation or a fit can read (the stale-source guard), or
// a calculation's inputs alone (a parameter's VALUE is an input, its uncertainty and free flag
// never are, nor is a bank's joint-fit weight).
enum class Scope { Everything, CalculationInputs };

// A bare number is never a parameter here: an implicit Parameter(double) temporary would carry a
// fresh identity (detail::Epoch) on every call, so no two encodings could ever be equal.
void put_parameter(std::string& out, double value, Scope scope) = delete;

void put_parameter(std::string& out, const Parameter& parameter, Scope scope) {
    put_double(out, parameter.value);
    if (scope == Scope::CalculationInputs) {
        put_u64(out, parameter.epoch.value());  // review 9 F1: every admitted write
    }
    if (scope == Scope::Everything) {
        put_double(out, parameter.uncertainty.value_or(0.0));
        out += parameter.free ? '1' : '0';
    }
}

void put_optional_parameter(std::string& out, const std::optional<Parameter>& parameter,
                            Scope scope) {
    out += parameter ? 'P' : '-';  // presence encoded distinctly from a 0 value
    if (parameter) put_parameter(out, *parameter, scope);
}

void put_experiment(std::string& out, const ExperimentBase& experiment, Scope scope) {
    for (const auto& slot : detail::kPeakSlots) {
        put_text(out, slot.first);
        put_parameter(out, slot.second(const_cast<ExperimentBase&>(experiment)), scope);
    }
    put_parameter(out, experiment.instrument.calib_d_to_tof_offset, scope);
    put_parameter(out, experiment.instrument.calib_d_to_tof_linear, scope);
    put_parameter(out, experiment.instrument.calib_d_to_tof_quadratic, scope);
    put_parameter(out, experiment.instrument.calib_d_to_tof_reciprocal, scope);
    for (const auto& link : experiment.linked_structures) {  // one scale per linked structure
        put_parameter(out, link->scale, scope);
    }
    put_u64(out, experiment.background.size());
    for (const auto& point_item : experiment.background) {
        const LineSegment& point = *point_item;
        put_double(out, point.position);  // NOT a Parameter, but it moves the background
        put_parameter(out, point.intensity, scope);
    }
    // The declared model, its constants and its terms.
    put_text(out, experiment.background_type);
    for (const std::optional<double>* constant :
         {&experiment.background_origin, &experiment.background_x_min, &experiment.background_x_max}) {
        out += constant->has_value() ? 'C' : '-';
        if (constant->has_value()) put_double(out, **constant);
    }
    put_u64(out, experiment.background_terms.size());
    for (const auto& term : experiment.background_terms) {
        put_u64(out, static_cast<std::uint64_t>(static_cast<std::int64_t>(term->order)));
        put_parameter(out, term->coef, scope);
    }
    put_parameter(out, experiment.instrument.setup_twotheta_bank, scope);
    put_double(out, experiment.peak.cutoff_fwhm);
    put_optional_parameter(out, experiment.absorption.abscor1, scope);
    put_optional_parameter(out, experiment.absorption.abscor2, scope);
    put_optional_parameter(out, experiment.absorption.mu_r, scope);  // The CW body
    // The preferred-orientation rows — key, fit pair and fixed axis all move P.
    put_u64(out, experiment.preferred_orientation.size());
    for (const auto& row : experiment.preferred_orientation) {
        put_text(out, row->structure_id);
        put_parameter(out, row->march_r, scope);
        put_parameter(out, row->march_random_fract, scope);
        put_u64(out, static_cast<std::uint64_t>(static_cast<std::int64_t>(row->index_h)));
        put_u64(out, static_cast<std::uint64_t>(static_cast<std::int64_t>(row->index_k)));
        put_u64(out, static_cast<std::uint64_t>(static_cast<std::int64_t>(row->index_l)));
    }
    out += experiment.absorption.type ? 'T' : '-';
    if (experiment.absorption.type) put_text(out, *experiment.absorption.type);
    put_text(out, experiment.name);
    // The scattering-source selectors choose the form factors, dispersion and scattering
    // lengths a calculation reads.
    for (const auto* selector : {&experiment.xray_form_factor, &experiment.xray_dispersion,
                                 &experiment.neutron_scattering_length}) {
        out += selector->has_value() ? 'S' : '-';
        if (selector->has_value()) put_text(out, **selector);
    }
    out += experiment.peak.type ? 'P' : '-';
    if (experiment.peak.type) put_text(out, *experiment.peak.type);
    // The four typed axes and all seven CW fields are part of the calculation-affecting source
    // state, so they are fingerprinted — a TOF handle whose source is mutated CW-ward (a beam-mode
    // flip or any CW field write) is DETECTED as a stale source rather than continuing on stale
    // TOF engine state. Presence is encoded distinctly from every value, so engaging an axis at
    // its default is still a detected mutation.
    const auto put_axis = [&out](const auto& axis) {
        out += axis ? 'A' : '-';
        if (axis) put_text(out, token(*axis));
    };
    put_axis(experiment.experiment_type.sample_form);
    put_axis(experiment.experiment_type.beam_mode);
    put_axis(experiment.experiment_type.radiation_probe);
    put_axis(experiment.experiment_type.scattering_type);
    put_optional_parameter(out, experiment.peak.broad_gauss_u, scope);
    put_optional_parameter(out, experiment.peak.broad_gauss_v, scope);
    put_optional_parameter(out, experiment.peak.broad_gauss_w, scope);
    put_optional_parameter(out, experiment.peak.broad_lorentz_x, scope);
    put_optional_parameter(out, experiment.peak.broad_lorentz_y, scope);
    put_optional_parameter(out, experiment.peak.asym_fcj_1, scope);
    put_optional_parameter(out, experiment.peak.asym_fcj_2, scope);
    put_optional_parameter(out, experiment.peak.asym_beba_a0, scope);
    put_optional_parameter(out, experiment.peak.asym_beba_b0, scope);
    put_optional_parameter(out, experiment.peak.asym_beba_a1, scope);
    put_optional_parameter(out, experiment.peak.asym_beba_b1, scope);
    put_optional_parameter(out, experiment.peak.asym_beba_limit, scope);
    put_optional_parameter(out, experiment.instrument.setup_wavelength, scope);
    put_optional_parameter(out, experiment.instrument.calib_twotheta_offset, scope);
    put_optional_parameter(out, experiment.instrument.calib_sample_displacement, scope);
    put_optional_parameter(out, experiment.instrument.calib_sample_transparency, scope);
    put_optional_parameter(out, experiment.instrument.setup_polarization_coefficient, scope);
    put_optional_parameter(out, experiment.instrument.setup_monochromator_twotheta, scope);
    // Each link's structure, and whether it takes part (written only when it can differ from
    // the one link of a single-phase experiment).
    for (const auto& link : experiment.linked_structures) {
        put_text(out, link->structure_id);
        if (experiment.linked_structures.size() > 1 || !link->enabled.get()) {
            put_text(out, link->enabled.get() ? "enabled" : "disabled");
        }
    }
    if (scope == Scope::Everything) {
        put_double(out, experiment.dataset_weight);  // joint-fit weighting, never a calculation input
    }
    put_u64(out, experiment.excluded_regions.size());
    for (const auto& region : experiment.excluded_regions) {
        put_double(out, region.first);
        put_double(out, region.second);
    }
    // `ExperimentBase::data` is DELIBERATELY NOT ENCODED: the encoding fingerprints the
    // model content, and embedded data alters nothing a forward calculation computes.
}

// The bond cutoffs, presence included (an unset one and its default are different models: only a
// declared one is saved).
void put_geom(std::string& out, const Geom& geom) {
    for (const std::optional<double>* value :
         {&geom.min_bond_distance_cutoff.get(), &geom.bond_distance_inc.get()}) {
        out += value->has_value() ? 'G' : '-';
        if (value->has_value()) {
            put_double(out, **value);
        }
    }
}

// A geometry input with the identity of its last write. The identity alone would do: no two
// writes share one. The value stays in the encoding so that it reads as what it is.
void put_written(std::string& out, const detail::Written<double>& field) {
    put_double(out, field.get());
    put_u64(out, field.written());
}
void put_written(std::string& out, const detail::WrittenText& field) {
    put_text(out, field.value());
    put_u64(out, field.written());
}

void put_structure(std::string& out, const Structure& structure, Scope scope) {
    put_text(out, structure.name);
    put_text(out, structure.space_group.name_h_m);
    // The code changes the resolved setting
    put_text(out, structure.space_group.coord_system_code);
    out += structure.space_group.it_number ? 'N' : '-';
    if (structure.space_group.it_number) {
        put_u64(out, static_cast<std::uint64_t>(static_cast<std::int64_t>(*structure.space_group.it_number)));
    }
    for (const Parameter* cell :
         {&structure.cell.length_a, &structure.cell.length_b, &structure.cell.length_c,
          &structure.cell.angle_alpha, &structure.cell.angle_beta, &structure.cell.angle_gamma}) {
        put_parameter(out, *cell, scope);
    }
    put_u64(out, structure.atom_sites.size());
    for (const auto& site_item : structure.atom_sites) {
        const AtomSite& site = *site_item;
        put_text(out, site.id);
        put_text(out, site.type_symbol);
        put_text(out, site.wyckoff_letter);
        put_text(out, site.adp_type);  // An input of F and the pattern
        put_parameter(out, site.fract_x, scope);
        put_parameter(out, site.fract_y, scope);
        put_parameter(out, site.fract_z, scope);
        put_parameter(out, site.occupancy, scope);
        put_parameter(out, site.adp_iso, scope);
    }
    // The anisotropic sites' tensors: an input of F and the pattern.
    put_u64(out, structure.atom_site_aniso.size());
    for (const auto& tensor_item : structure.atom_site_aniso) {
        AtomSiteAniso& tensor = *tensor_item;
        put_text(out, tensor.id);
        for (const Parameter* component : tensor.parameters()) {
            put_parameter(out, *component, scope);
        }
    }
    put_u64(out, structure.scattering_lengths_fm.size());
    for (const auto& entry : structure.scattering_lengths_fm) {  // std::map: key-ordered
        put_text(out, entry.first);
        put_double(out, entry.second);
    }
    // `geom` is model state a save persists, but no pattern or reflection reads a bond cutoff,
    // so it is not a CALCULATION input (crysta's computed-input table agrees).
    if (scope == Scope::Everything) {
        put_geom(out, structure.geom);
    }
}

}  // namespace

namespace detail {

std::string canonical_encoding(const Project& project) {
    std::string out;
    out.reserve(4096);
    // TOTAL over the PLURAL storage — count-prefixed, so an emptied collection is encoded
    // state (a detectable mutation), never a throw from a singular view.
    put_u64(out, project.structures.size());
    for (const auto& structure_item : project.structures) {
        put_structure(out, *structure_item, Scope::Everything);
    }
    put_u64(out, project.experiments.size());
    for (const auto& experiment_item : project.experiments) {
        put_experiment(out, *experiment_item, Scope::Everything);
    }
    put_text(out, project.fitting_mode);
    // The declared scan block is fit-relevant state exactly as the mode is — two sequential
    // projects differing only in data_dir/pattern/order/extract rules must never share an
    // encoding.
    put_text(out, project.sequential_fit.data_dir);
    put_text(out, project.sequential_fit.file_pattern);
    put_text(out, project.sequential_fit.reverse ? "1" : "0");
    put_u64(out, project.sequential_fit.extract.size());
    for (const auto& rule : project.sequential_fit.extract) {
        put_text(out, rule->id);
        put_text(out, rule->target);
        put_text(out, rule->pattern);
        put_text(out, rule->required ? "1" : "0");
    }
    return out;
}

std::string geometry_inputs(const Structure& structure) {
    // Crysta's geometry inputs and no other field: the space group, the six cell values, the site
    // rows with each site's id, type symbol, Wyckoff letter, ADP type, coordinates, occupancy and
    // ADP, and `geom`. The letter is one because a geometry read applies the relations, and the
    // letter selects a site's symmetry relation. The structure's name and its scattering lengths are
    // pattern inputs only, so put_structure is not reused here: a write to one of them must leave
    // the geometry current.
    //
    // Each input is encoded with the identity of its last write. Every one of them records its
    // own writes — a parameter's value, a text field, a site's id, `geom`'s two values, and the
    // site collection through its generation — so an equal-value assignment, a self-assignment,
    // a whole-object assignment, and removing a row and adding the same object back each leave a
    // different encoding. No object identity is encoded: an object's identity also renews on
    // writes to its non-input fields.
    std::string out;
    out.reserve(1024);
    put_written(out, structure.space_group.name_h_m);
    put_written(out, structure.space_group.coord_system_code);
    for (const Parameter* cell :
         {&structure.cell.length_a, &structure.cell.length_b, &structure.cell.length_c,
          &structure.cell.angle_alpha, &structure.cell.angle_beta, &structure.cell.angle_gamma}) {
        put_written(out, cell->value);
    }
    put_u64(out, structure.atom_sites.size());
    put_u64(out, structure.atom_sites.generation());
    for (const auto& site_item : structure.atom_sites) {
        const AtomSite& site = *site_item;
        put_text(out, site.id);
        put_u64(out, site.id.written());
        put_written(out, site.type_symbol);
        put_written(out, site.wyckoff_letter);
        put_written(out, site.adp_type);
        for (const Parameter* value :
             {&site.fract_x, &site.fract_y, &site.fract_z, &site.occupancy, &site.adp_iso}) {
            put_written(out, value->value);
        }
    }
    // The tensors are geometry inputs too: the app's ellipsoids are drawn from them.
    put_u64(out, structure.atom_site_aniso.size());
    put_u64(out, structure.atom_site_aniso.generation());
    for (const auto& tensor_item : structure.atom_site_aniso) {
        AtomSiteAniso& tensor = *tensor_item;
        put_text(out, tensor.id);
        put_u64(out, tensor.id.written());
        for (const Parameter* component : tensor.parameters()) {
            put_written(out, component->value);
        }
    }
    put_geom(out, structure.geom);
    put_u64(out, structure.geom.min_bond_distance_cutoff.written());
    put_u64(out, structure.geom.bond_distance_inc.written());
    return out;
}

std::string calculation_inputs(const ItemVec<Structure>& structures,
                               const ExperimentBase& experiment) {
    std::string out;
    out.reserve(4096);
    put_u64(out, structures.size());
    for (const auto& structure_item : structures) {
        put_structure(out, *structure_item, Scope::CalculationInputs);
    }
    put_experiment(out, experiment, Scope::CalculationInputs);
    out += experiment.calculation_only ? 'C' : 'M';
    // The data node: its grid is the calculation's grid (crysta: `PdDataBase.grid`), and its
    // measured intensities and uncertainties are part of the `_data` category the computed columns
    // sit in, so a write to them is a write to that category (conservative). The arrays go in as
    // their bytes, in one append each, after their length. Two encodings are still equal exactly
    // when every number has the same bit
    // pattern (-0.0 vs 0.0 and NaN payloads distinguish); one snprintf per number cost 18 ms per
    // encoding at 50 000 points, on the thread that publishes a calculation. Compared in memory
    // only, never saved.
    const auto put_values = [&out](const std::vector<double>& values) {
        put_u64(out, values.size());
        out.append(reinterpret_cast<const char*>(values.data()), values.size() * sizeof(double));
    };
    out += experiment.data ? 'D' : '-';
    if (experiment.data) {
        for (const auto* axis : {&experiment.data->two_theta, &experiment.data->time_of_flight}) {
            out += axis->has_value() ? 'A' : '-';
            if (axis->has_value()) {
                put_values(**axis);
            }
        }
        put_values(experiment.data->intensity_meas);
        put_values(experiment.data->intensity_meas_su);
    }
    // Identities: every object's epoch, so replacing a structure, a row, a category or
    // the data node, or assigning one whole, is a write even when every value is equal.
    for (const auto& structure_item : structures) {
        const Structure& structure = *structure_item;
        put_u64(out, structure.epoch.value());
        put_u64(out, structure.cell.epoch.value());
        put_u64(out, structure.space_group.epoch.value());
        for (const auto& site : structure.atom_sites) {
            put_u64(out, site->epoch.value());
        }
        for (const auto& tensor : structure.atom_site_aniso) {
            put_u64(out, tensor->epoch.value());
        }
    }
    for (const std::uint64_t epoch :
         {experiment.epoch.value(), experiment.experiment_type.epoch.value(),
          experiment.peak.epoch.value(), experiment.instrument.epoch.value()}) {
        put_u64(out, epoch);
    }
    for (const auto& link : experiment.linked_structures) {
        put_u64(out, link->epoch.value());
    }
    put_u64(out, experiment.absorption.epoch.value());
    for (const auto& point : experiment.background) {
        put_u64(out, point->epoch.value());
    }
    for (const auto& term : experiment.background_terms) {
        put_u64(out, term->epoch.value());
    }
    for (const auto& row : experiment.preferred_orientation) {
        put_u64(out, row->epoch.value());
    }
    if (experiment.data) {
        put_u64(out, experiment.data->epoch.value());
        put_u64(out, experiment.data->written.value());
    }
    return out;
}


std::string relation_inputs(const ItemVec<ParameterAlias>& aliases,
                            const ItemVec<ParameterConstraint>& constraints) {
    std::string out;
    put_u64(out, aliases.generation());
    put_u64(out, aliases.size());
    for (const auto& alias : aliases) {
        put_text(out, alias->id.value());
        put_written(out, alias->parameter_unique_name);
    }
    put_u64(out, constraints.generation());
    put_u64(out, constraints.size());
    for (const auto& constraint : constraints) {
        put_text(out, constraint->id.value());
        put_written(out, constraint->expression);
        put_u64(out, constraint->enabled.get() ? 1 : 0);
        put_u64(out, constraint->enabled.written());
    }
    // An expression reads only aliases, so the parameters they name are every source a relation has,
    // in any block or bank. Each one's value and last write are inputs of whatever the relations reach.
    if (const Project* project = aliases.host(); project != nullptr && !aliases.empty()) {
        std::map<std::string, const Parameter*> by_name;
        for (const NamedParameter& named : named_parameters(*project)) {
            by_name.emplace(named.unique_name, named.parameter);
        }
        for (const auto& alias : aliases) {
            const auto found = by_name.find(alias->parameter_unique_name.value());
            put_u64(out, found != by_name.end() ? 1 : 0);
            if (found != by_name.end()) {
                put_written(out, found->second->value);
            }
        }
    }
    return out;
}

}  // namespace detail
// ADR-0018: the table view of every non-loop category, instantiated whole, so each schema's one
// generation is compiled over exactly its columns.
template class OneRow<CellCategory>;
template class OneRow<SpaceGroupCategory>;
template class OneRow<GeomCategory>;
template class OneRow<ExperimentTypeCategory>;
template class OneRow<ScatteringSourceCategory>;
template class OneRow<PeakCategory>;
template class OneRow<InstrumentCategory>;
template class OneRow<AbsorptionCategory>;
template class OneRow<BackgroundCategory>;
template class OneRow<JointFitCategory>;
template class OneRow<DataRangeCategory>;
template class OneRow<FittingModeCategory>;
template class OneRow<MinimizerCategory>;
template class OneRow<SequentialFitCategory>;
template class OneRow<FitResultCategory>;
template class OneRow<FitResultBankCategory>;
template class OneRow<MetadataCategory>;
template class OneRow<ProjectStateCategory>;

}  // namespace edi
