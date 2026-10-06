// SPDX-License-Identifier: BSD-3-Clause
// The type selectors of edi/selectors.hpp — the options each category offers and the one write
// each selection makes.

#include "edi/selectors.hpp"

#include <algorithm>
#include <stdexcept>

#include "edi/io.hpp"

namespace edi {
namespace {

// The shipped profiles of each beam mode in their `.edi` order (crysta's shipped grammar; the
// loader's peak_type_rows holds the same tokens and their modes).
const std::vector<std::string>& shipped_peak_profiles(BeamModeEnum mode) {
    static const std::vector<std::string> constant_wavelength{
        "cwl-gaussian",         "cwl-lorentzian",          "cwl-pseudo-voigt",
        "cwl-pseudo-voigt-berar-baldinozzi", "cwl-tch-pseudo-voigt", "cwl-tch-pseudo-voigt-fcj"};
    static const std::vector<std::string> time_of_flight{
        "tof-jorgensen", "tof-jorgensen-von-dreele", "tof-pseudo-voigt"};
    return mode == BeamModeEnum::CONSTANT_WAVELENGTH ? constant_wavelength : time_of_flight;
}

// A newly engaged optional field at the loader's default (io.cpp, the CW asymmetry block).
std::optional<Parameter> defaulted(const ParameterSpec& spec, double value = 0.0) {
    Parameter parameter;
    parameter.value = value;
    parameter.spec = &spec;
    return parameter;
}

// Engage `field` at its default when the new profile declares it and it is absent; drop it when the
// profile does not declare it. An engaged field the profile keeps is left as it is (D-j).
void keep_if(OptionalParameter& field, bool declared, const ParameterSpec& spec,
             double default_value = 0.0) {
    if (!declared) {
        field.reset();
    } else if (!field.has_value()) {
        field = defaulted(spec, default_value);
    }
}

bool contains(const std::vector<std::string>& values, const std::string& value) {
    return std::find(values.begin(), values.end(), value) != values.end();
}

}  // namespace

std::string scattering_source_value(const ExperimentBase& experiment, ScatteringSourceItem item) {
    const std::optional<std::string>* field = &experiment.neutron_scattering_length;
    if (item == ScatteringSourceItem::XRAY_FORM_FACTOR) {
        field = &experiment.xray_form_factor;
    } else if (item == ScatteringSourceItem::XRAY_DISPERSION) {
        field = &experiment.xray_dispersion;
    }
    return field->value_or(std::string{});
}

std::vector<std::string> supported_peak_profiles(BeamModeEnum mode) {
    std::vector<std::string> profiles = shipped_peak_profiles(mode);
    for (const std::string& token : registered_peak_types()) {
        if (!contains(profiles, token) && peak_type_beam_mode(token) == mode) {
            profiles.push_back(token);
        }
    }
    return profiles;
}

std::string default_peak_profile(BeamModeEnum mode) {
    return mode == BeamModeEnum::CONSTANT_WAVELENGTH ? "cwl-tch-pseudo-voigt" : "tof-jorgensen";
}

std::string peak_profile_label(const std::string& token) {
    static const std::vector<std::pair<std::string, std::string>> labels{
        {"cwl-gaussian", "Gaussian"},
        {"cwl-lorentzian", "Lorentzian"},
        {"cwl-pseudo-voigt", "Pseudo-Voigt"},
        {"cwl-pseudo-voigt-berar-baldinozzi", "Pseudo-Voigt + Bérar–Baldinozzi asymmetry"},
        {"cwl-tch-pseudo-voigt", "Thompson–Cox–Hastings pseudo-Voigt (TCH)"},
        {"cwl-tch-pseudo-voigt-fcj",
         "Thompson–Cox–Hastings pseudo-Voigt (TCH) + Finger–Cox–Jephcoat asymmetry (FCJ)"},
    };
    for (const auto& [known, label] : labels) {
        if (known == token) {
            return label;
        }
    }
    return token;
}

std::vector<std::string> supported_absorption_families(BeamModeEnum mode) {
    // crysta's vocabulary table, in its order (ADR-0017): edi keeps no list of its own.
    return absorption_file_tokens(mode);
}

std::vector<std::string> supported_background_types() {
    return {"line-segment", "chebyshev", "polynomial"};
}

std::vector<std::string> supported_minimizer_types() { return {"crysta"}; }

std::vector<std::string> supported_fitting_modes() {
    return {"single", "joint", "sequential", "independent"};
}

void select_peak_profile(ExperimentBase& experiment, const std::string& token) {
    const BeamModeEnum mode = experiment.effective_beam_mode();
    const std::optional<BeamModeEnum> token_mode = peak_type_beam_mode(token);
    if (!token_mode.has_value()) {
        throw std::invalid_argument("peak type '" + token +
                                    "' is neither a shipped profile token nor a registered extension");
    }
    if (*token_mode != mode) {
        throw std::invalid_argument("peak type '" + token + "' is a " +
                                    (*token_mode == BeamModeEnum::CONSTANT_WAVELENGTH
                                         ? "constant-wavelength"
                                         : "time-of-flight") +
                                    " profile; this experiment's beam mode is " + edi::token(mode));
    }
    experiment.peak.type = token;
    conform_peak_slots(experiment.peak, token);
}

void conform_peak_slots(PeakBase& peak, const std::string& token) {
    if (peak_type_beam_mode(token) != BeamModeEnum::CONSTANT_WAVELENGTH) {
        return;
    }
    // The slots the new CW profile carries, U, V, W on every one.
    const CwlProfileSlots slots = cwl_profile_slots(token);
    keep_if(peak.broad_lorentz_x, slots.lorentz_xy, spec::peak_broad_lorentz_x);
    keep_if(peak.broad_lorentz_y, slots.lorentz_xy, spec::peak_broad_lorentz_y);
    keep_if(peak.mixing_eta_0, slots.mixing_eta, spec::peak_mixing_eta_0);
    keep_if(peak.mixing_eta_1, slots.mixing_eta, spec::peak_mixing_eta_1);
    keep_if(peak.asym_fcj_1, slots.fcj, spec::peak_asym_fcj_1);
    keep_if(peak.asym_fcj_2, slots.fcj, spec::peak_asym_fcj_2);
    keep_if(peak.asym_beba_a0, slots.beba, spec::peak_asym_beba_a0);
    keep_if(peak.asym_beba_b0, slots.beba, spec::peak_asym_beba_b0);
    keep_if(peak.asym_beba_a1, slots.beba, spec::peak_asym_beba_a1);
    keep_if(peak.asym_beba_b1, slots.beba, spec::peak_asym_beba_b1);
    keep_if(peak.asym_beba_limit, slots.beba, spec::peak_asym_beba_limit, 180.0);
}

void select_absorption(ExperimentBase& experiment, const std::string& value) {
    // The one setter rule, which the Python AbsorptionBase.type setter calls too. The
    // vocabulary and the registry-token-to-file-spelling mapping are crysta's own table,
    // through the adapter — edi lists and maps nothing itself.
    apply_absorption_family(experiment.absorption,
                            absorption_file_token(experiment.effective_beam_mode(), value));
}

void select_scattering_source(ExperimentBase& experiment, ScatteringSourceItem item,
                              const std::string& token) {
    const RadiationProbeEnum probe = experiment.experiment_type.effective_radiation_probe();
    // Clearing checks only that the item applies to the probe: its default is always known.
    const std::string checked = token.empty() ? supported_scattering_sources(item).front() : token;
    if (const auto refusal = scattering_source_refusal(probe, item, checked)) {
        throw std::invalid_argument(refusal->message);
    }
    std::optional<std::string>& field =
        item == ScatteringSourceItem::XRAY_FORM_FACTOR  ? experiment.xray_form_factor
        : item == ScatteringSourceItem::XRAY_DISPERSION ? experiment.xray_dispersion
                                                        : experiment.neutron_scattering_length;
    if (token.empty()) {
        field.reset();
    } else {
        field = token;
    }
}

void set_fitting_mode(Project& project, const std::string& mode) {
    if (!is_declared_fitting_mode(mode)) {
        throw std::invalid_argument("_fitting_mode.type is '" + mode + "', expected " +
                                    declared_fitting_modes());
    }
    project.fitting_mode = mode;
}

std::vector<std::string> supported_descents() { return descent_ids(); }

void set_descent(Project& project, const std::string& id) {
    validate_descent(id, "edi descent");
    project.descent = id;
}

}  // namespace edi
