// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_SELECTORS_HPP
#define EDI_SELECTORS_HPP

// The categories whose type a user selects, the options each offers for an experiment's type, and
// the one write each selection makes. The options are always computed here, never listed by a
// surface, so the app never offers a type the model cannot hold. The Python setters keep their own
// rules unchanged (owner, 2026-09-27); where a rule is shared the function below reproduces it and a
// parity test holds the two equal.

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "edi/model.hpp"

namespace edi {

// The `_scattering_source` items (edi ADR-0014): which exist depends on the radiation probe.
enum class ScatteringSourceItem : std::uint8_t { NEUTRON_SCATTERING_LENGTH, XRAY_FORM_FACTOR, XRAY_DISPERSION };

// The `.edi` tag of a scattering-source item, e.g. "_scattering_source.neutron_scattering_length".
inline std::string scattering_source_tag(ScatteringSourceItem item) {
    switch (item) {
        case ScatteringSourceItem::XRAY_FORM_FACTOR: return "_scattering_source.xray_form_factor";
        case ScatteringSourceItem::XRAY_DISPERSION: return "_scattering_source.xray_dispersion";
        case ScatteringSourceItem::NEUTRON_SCATTERING_LENGTH: break;
    }
    return "_scattering_source.neutron_scattering_length";
}

// The items an experiment of this probe carries, in `.edi` order.
inline std::vector<ScatteringSourceItem> scattering_source_items(RadiationProbeEnum probe) {
    if (probe == RadiationProbeEnum::XRAY) {
        return {ScatteringSourceItem::XRAY_FORM_FACTOR, ScatteringSourceItem::XRAY_DISPERSION};
    }
    return {ScatteringSourceItem::NEUTRON_SCATTERING_LENGTH};
}

// The known values of an item, the default first (ADR-0014).
inline std::vector<std::string> supported_scattering_sources(ScatteringSourceItem item) {
    switch (item) {
        case ScatteringSourceItem::XRAY_FORM_FACTOR: return {"wk1995", "it1992"};
        case ScatteringSourceItem::XRAY_DISPERSION: return {"cromer-liberman", "sasaki1989", "it1992", "none"};
        case ScatteringSourceItem::NEUTRON_SCATTERING_LENGTH: break;
    }
    return {"rauch2003ext", "sears1992"};
}

// Why a value may not be set on an item, as the loader reports it (a schema code and message), or
// nothing when it may. One rule for the loader and select_scattering_source: an item of the other
// probe is refused, then a value outside the item's known set.
struct ScatteringSourceRefusal {
    std::string code;
    std::string message;
};
inline std::optional<ScatteringSourceRefusal> scattering_source_refusal(RadiationProbeEnum probe,
                                                                        ScatteringSourceItem item,
                                                                        const std::string& value) {
    const std::string tag = scattering_source_tag(item);
    const bool neutron_item = item == ScatteringSourceItem::NEUTRON_SCATTERING_LENGTH;
    if (neutron_item && probe == RadiationProbeEnum::XRAY) {
        return ScatteringSourceRefusal{"neutron-source-on-xray",
                                       tag + " is declared on an X-ray experiment — the neutron "
                                             "scattering-length source is neutron only"};
    }
    if (!neutron_item && probe != RadiationProbeEnum::XRAY) {
        return ScatteringSourceRefusal{"xray-source-on-non-xray",
                                       tag + " is declared on a non-X-ray experiment — the scattering-"
                                             "source selectors are X-ray only"};
    }
    const std::vector<std::string> known = supported_scattering_sources(item);
    for (const std::string& token : known) {
        if (token == value) {
            return std::nullopt;
        }
    }
    std::string names;
    for (const std::string& token : known) {
        names += (names.empty() ? "" : " | ") + token;
    }
    return ScatteringSourceRefusal{neutron_item ? "unknown-neutron-source" : "unknown-xray-source",
                                   tag + " '" + value + "' is not a known source (" + names + ")"};
}

// The item's value on this experiment: the declared token, or empty when absent (the default,
// the first known value, applies).
std::string scattering_source_value(const ExperimentBase& experiment, ScatteringSourceItem item);

// The peak profiles an experiment of this beam mode can use: the shipped ones in their `.edi` order,
// then any registered extension for the mode.
std::vector<std::string> supported_peak_profiles(BeamModeEnum mode);
// The profile a new experiment of this beam mode gets: the TCH pseudo-Voigt for constant wavelength.
std::string default_peak_profile(BeamModeEnum mode);
// What a profile selector shows for a token: the constant-wavelength profiles' short names
//, the token itself for any other.
std::string peak_profile_label(const std::string& token);
// The absorption families of a beam mode, as a file spells them: CW none / cylinder-hewat /
// cylinder-lobanov (the mu_r body), TOF none / cylinder (the ABSCOR pair). Read from crysta's
// vocabulary table (ADR-0017).
std::vector<std::string> supported_absorption_families(BeamModeEnum mode);
// The background models edi computes through crysta.
std::vector<std::string> supported_background_types();
// crysta is edi's only minimizer; another declared value warns at load and runs crysta.
std::vector<std::string> supported_minimizer_types();
// The declared fitting modes (model.hpp is_declared_fitting_mode), in `.edi` order.
std::vector<std::string> supported_fitting_modes();
// The registered descent flows (model.hpp descent_ids, crysta's registration order).
std::vector<std::string> supported_descents();

// Switch the peak profile: refuses an unknown token and a token of the other beam mode, engages the
// optional fields the new profile declares at the loader's defaults (asymmetry 0, the Berar-Baldinozzi
// limit 180) and drops the ones it does not; fields both profiles share keep their values and free
// flags.
void select_peak_profile(ExperimentBase& experiment, const std::string& token);
// The peak block reshaped to what a constant-wavelength token carries: the slots it keeps stay as
// they are, the ones it adds start at their defaults, the rest are cleared. Nothing for a TOF token,
// whose block is the whole family. select_peak_profile and the Python `peak.type` setter call it.
void conform_peak_slots(PeakBase& peak, const std::string& token);
// Switch the absorption family within the experiment's beam mode, with the Python
// AbsorptionBase.type setter's vocabulary and messages (a TOF "cylinder-hewat" is its "cylinder"),
// then apply the family contract (apply_absorption_family).
void select_absorption(ExperimentBase& experiment, const std::string& token);
// Set one scattering-source item under scattering_source_refusal (the loader's rule and message).
// An empty token clears the item back to its default.
void select_scattering_source(ExperimentBase& experiment, ScatteringSourceItem item,
                              const std::string& token);
// The fitting mode a fit runs: the declared one, else `single` (the Python Analysis.fit dispatch's
// fall-through for an undeclared mode).
inline std::string effective_fitting_mode(const Project& project) {
    return project.fitting_mode.empty() ? std::string("single") : project.fitting_mode;
}
// The declared fitting mode, one of supported_fitting_modes() (the Python fitting_mode setter's rule).
void set_fitting_mode(Project& project, const std::string& mode);
// The descent flow: a registered id or empty for the engine default (the Python descent setter's
// rule, over validate_descent).
void set_descent(Project& project, const std::string& id);

}  // namespace edi

#endif  // EDI_SELECTORS_HPP
