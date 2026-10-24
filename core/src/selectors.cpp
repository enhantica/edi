// SPDX-License-Identifier: BSD-3-Clause
// The type selectors of edi/selectors.hpp — the options each category offers and the one write
// each selection makes.

#include "edi/selectors.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <locale>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "edi/background_estimate.hpp"
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
        {"cwl-pseudo-voigt-berar-baldinozzi", "Pseudo-Voigt + Bérar-Baldinozzi asymmetry"},
        {"cwl-tch-pseudo-voigt", "Thompson-Cox-Hastings pseudo-Voigt (TCH)"},
        {"cwl-tch-pseudo-voigt-fcj",
         "Thompson-Cox-Hastings pseudo-Voigt (TCH) + Finger-Cox-Jephcoat asymmetry (FCJ)"},
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

std::vector<std::string> applicable_fitting_modes(const Project& project) {
    if (project.sequential_fit.declared()) {
        return {"sequential", "independent", "single"};
    }
    if (project.experiments.size() > 1) {
        return {"joint"};
    }
    return {"single"};
}

std::string fitting_mode_label(const std::string& token) {
    static const std::vector<std::pair<std::string, std::string>> labels{
        {"single", "Single experiment"},
        {"joint", "Joint: all experiments at once"},
        {"sequential", "Sequential: each from the previous"},
        {"independent", "Independent: each from the same start"},
    };
    for (const auto& [known, label] : labels) {
        if (known == token) {
            return label;
        }
    }
    return token;
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

std::vector<std::string> extinction_type_labels() {
    std::vector<std::string> labels;
    for (const std::string& token : extinction_type_tokens()) {
        if (token == "none") {
            labels.emplace_back("None");
        } else if (token == "becker-coppens-type-1") {
            labels.emplace_back("Isotropic Becker-Coppens type I");
        } else if (token == "becker-coppens-type-2") {
            labels.emplace_back("Isotropic Becker-Coppens type II");
        } else if (token == "becker-coppens-mixed") {
            labels.emplace_back("Isotropic Becker-Coppens mixed");
        } else if (token == "larson-isotropic") {
            labels.emplace_back("Isotropic Larson");
        } else if (token == "larson-anisotropic") {
            labels.emplace_back("Anisotropic Larson");
        } else {
            labels.push_back(token);
        }
    }
    return labels;
}

std::vector<std::string> mosaic_distribution_labels() {
    std::vector<std::string> labels;
    for (const std::string& token : mosaic_distribution_tokens()) {
        labels.push_back(token == "gaussian" ? "Gaussian" : token == "lorentzian" ? "Lorentzian" : token);
    }
    return labels;
}

void select_extinction(ExperimentBase& experiment, const std::string& token) {
    if (!experiment.reflections.has_value()) {
        throw std::invalid_argument("extinction belongs to a single crystal");
    }
    apply_extinction_type(experiment.extinction, token);
}

std::vector<std::string> reflns_threshold_basis_labels() {
    std::vector<std::string> labels;
    for (const std::string& token : reflns_threshold_basis_tokens()) {
        labels.push_back(token == "amplitude" ? "F" : "I");
    }
    return labels;
}

void select_mosaic_distribution(ExperimentBase& experiment, const std::string& token) {
    const std::vector<std::string> distributions = mosaic_distribution_tokens();
    if (std::find(distributions.begin(), distributions.end(), token) == distributions.end()) {
        throw std::invalid_argument("mosaic distribution '" + token + "' is not supported (expected 'gaussian' or "
                                    "'lorentzian')");
    }
    if (!experiment.extinction.mosaic_distribution) {
        throw std::invalid_argument("extinction type '" + experiment.extinction.type.value_or("none") +
                                    "' has no mosaic distribution");
    }
    experiment.extinction.mosaic_distribution = token;
}

void select_background_type(ExperimentBase& experiment, const std::string& token) {
    const std::vector<std::string> types = supported_background_types();
    if (std::find(types.begin(), types.end(), token) == types.end()) {
        throw std::invalid_argument("background type '" + token + "' is not one edi computes (line-segment, " +
                                    "chebyshev, polynomial)");
    }
    if (token == experiment.background_type) {
        return;
    }
    // The measured axis's ends, for the constants the new type needs.
    double low = 0.0;
    double high = 1.0;
    if (experiment.data.has_value()) {
        try {
            const std::vector<double>& axis = experiment.data->axis();
            const auto [lowest, highest] = std::minmax_element(axis.begin(), axis.end());
            if (lowest != axis.end() && std::isfinite(*lowest) && std::isfinite(*highest) && *lowest < *highest) {
                low = *lowest;
                high = *highest;
            }
        } catch (const std::exception&) {
            // No single engaged axis: the defaults stand.
        }
    }
    const double middle = low + (high - low) / 2.0;
    experiment.background.clear();
    experiment.background_terms.clear();
    experiment.background_origin.reset();
    experiment.background_x_min.reset();
    experiment.background_x_max.reset();
    experiment.background_type = token;
    if (token == "polynomial") {
        experiment.background_origin = middle != 0.0 ? middle : 1.0;
    } else if (token == "chebyshev") {
        experiment.background_x_min = low;
        experiment.background_x_max = high;
    }
    rebaseline_background_estimate(experiment);  // ADR-0040: auto estimates the new type, never a hand edit
}

PolynomialTerm next_background_term(const ExperimentBase& experiment) {
    const int highest = background_max_order(experiment.background_type);
    if (highest < 0) {
        throw std::invalid_argument("a " + experiment.background_type + " background has points, not terms");
    }
    for (int order = 0; order <= highest; ++order) {
        const bool held = std::any_of(experiment.background_terms.begin(), experiment.background_terms.end(),
                                      [order](const auto& term) { return term->order.get() == order; });
        if (!held) {
            PolynomialTerm term;
            term.order = order;
            // Named by the first number no other term holds, as a loaded term without an id is numbered.
            for (int number = 1;; ++number) {
                const std::string id = std::to_string(number);
                if (std::none_of(experiment.background_terms.begin(), experiment.background_terms.end(),
                                 [&id](const auto& held_term) { return held_term->id.value() == id; })) {
                    term.id = id;
                    break;
                }
            }
            return term;
        }
    }
    throw std::invalid_argument("this " + experiment.background_type + " background holds every order 0.." +
                                std::to_string(highest));
}

std::vector<std::string> position_point_ids(const ExperimentBase& experiment) {
    const std::size_t n = experiment.background.size();
    std::vector<int> decimals(n, 0);
    std::vector<std::string> ids(n);
    const auto spelled = [](double position, int places) {
        std::ostringstream text;
        text.imbue(std::locale::classic());
        text << std::fixed << std::setprecision(places) << position;
        return text.str() == "-0" ? std::string("0") : text.str();
    };
    for (int round = 0; round < 16; ++round) {
        for (std::size_t i = 0; i < n; ++i) {
            ids[i] = spelled(experiment.background[i]->position.get(), decimals[i]);
        }
        std::map<std::string, std::vector<std::size_t>> holders;
        for (std::size_t i = 0; i < n; ++i) {
            holders[ids[i]].push_back(i);
        }
        bool shared = false;
        for (const auto& [id, rows] : holders) {
            if (rows.size() > 1) {
                shared = true;
                for (const std::size_t row : rows) {
                    ++decimals[row];
                }
            }
        }
        if (!shared) {
            return ids;
        }
    }
    // Positions equal to every printed decimal: the rows keep apart by their place.
    for (std::size_t i = 0; i < n; ++i) {
        ids[i] += "-" + std::to_string(i + 1);
    }
    return ids;
}

namespace {
// A background table's rows renamed to `ids`, in their order. Two passes, so no rename meets an id another row
// still holds: first to names no row holds, then to the ids asked for.
template <class Row>
void rename_rows(ItemVec<Row>& rows, const std::vector<std::string>& ids, const std::string& what) {
    if (ids.size() != rows.size()) {
        throw std::invalid_argument("background " + what + " ids: " + std::to_string(ids.size()) + " ids for " +
                                    std::to_string(rows.size()) + " " + what + "s");
    }
    const std::set<std::string> distinct(ids.begin(), ids.end());
    if (distinct.size() != ids.size() || distinct.contains(std::string())) {
        throw std::invalid_argument("background " + what + " ids must be distinct and not empty");
    }
    std::set<std::string> held;
    for (const auto& row : rows) {
        held.insert(row->id.value());
    }
    held.insert(ids.begin(), ids.end());
    std::size_t counter = 0;
    for (const auto& row : rows) {
        std::string spare;
        do {
            spare = "renaming-" + std::to_string(++counter);
        } while (held.contains(spare));
        row->id = spare;
    }
    for (std::size_t i = 0; i < ids.size(); ++i) {
        rows[i]->id = ids[i];
    }
}
}  // namespace

void set_background_point_ids(ExperimentBase& experiment, const std::vector<std::string>& ids) {
    rename_rows(experiment.background, ids, "point");
}

std::vector<std::string> order_term_ids(const ExperimentBase& experiment) {
    std::vector<std::string> ids;
    ids.reserve(experiment.background_terms.size());
    for (const auto& term : experiment.background_terms) {
        ids.push_back(std::to_string(term->order.get()));
    }
    return ids;
}

void set_background_term_ids(ExperimentBase& experiment, const std::vector<std::string>& ids) {
    rename_rows(experiment.background_terms, ids, "term");
}

void set_background_points(ExperimentBase& experiment, const std::vector<LineSegment>& points) {
    if (experiment.background_type != "line-segment") {
        throw std::invalid_argument("a " + experiment.background_type +
                                    " background holds terms, not line-segment points; set background_type first");
    }
    std::vector<std::shared_ptr<LineSegment>> rows;
    rows.reserve(points.size());
    for (const LineSegment& point : points) {
        rows.push_back(std::make_shared<LineSegment>(point));
    }
    experiment.background.assign(std::move(rows));
}

void set_background_terms(ExperimentBase& experiment, const std::vector<PolynomialTerm>& terms) {
    if (experiment.background_type == "line-segment") {
        throw std::invalid_argument("a line-segment background holds points, not terms; set background_type first");
    }
    std::vector<std::shared_ptr<PolynomialTerm>> rows;
    rows.reserve(terms.size());
    for (const PolynomialTerm& term : terms) {
        rows.push_back(std::make_shared<PolynomialTerm>(term));
    }
    experiment.background_terms.assign(std::move(rows));
}

void set_background_term_order(ExperimentBase& experiment, PolynomialTerm& term, int order) {
    const int highest = background_max_order(experiment.background_type);
    if (order < 0 || order > highest) {
        throw std::invalid_argument("a " + experiment.background_type + " background's term order is 0.." +
                                    std::to_string(highest));
    }
    for (const auto& other : experiment.background_terms) {
        if (other.get() != &term && other->order.get() == order) {
            throw std::invalid_argument("another term has order " + std::to_string(order));
        }
    }
    term.order = order;
}

void set_background_origin(ExperimentBase& experiment, double origin) {
    if (experiment.background_type != "polynomial") {
        throw std::invalid_argument("only a polynomial background has an origin");
    }
    if (!std::isfinite(origin) || origin == 0.0) {
        throw std::invalid_argument("the polynomial background's origin must be a finite number other than 0");
    }
    experiment.background_origin = origin;
}

void set_background_domain(ExperimentBase& experiment, bool end, double value) {
    if (experiment.background_type != "chebyshev") {
        throw std::invalid_argument("only a Chebyshev background has a domain");
    }
    const double low = end ? experiment.background_x_min.value_or(value) : value;
    const double high = end ? value : experiment.background_x_max.value_or(value);
    if (!std::isfinite(value) || !(low < high)) {
        throw std::invalid_argument("the Chebyshev background's x min must be a finite number below its x max");
    }
    (end ? experiment.background_x_max : experiment.background_x_min) = value;
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
