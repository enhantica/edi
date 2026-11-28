// SPDX-License-Identifier: BSD-3-Clause
#include "edi/fullprof.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/project_archive.hpp"
#include "edi/su_text.hpp"
#include "edi/symmetry.hpp"
#include "fullprof_project_io.hpp"
#include "import_symmetry.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <format>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <map>
#include <numbers>
#include <numeric>
#include <ostream>
#include <set>
#include <string_view>

namespace edi {
namespace {

namespace fs = std::filesystem;

[[noreturn]] void unsupported(const std::string& message) {
    throw IoError("FullProf export: " + message);
}

double value(const OptionalParameter& field) {
    return field ? field->value.get() : 0.;
}

struct Field {
    double value = 0.;
    double code = 0.;
};

class Codes {
    struct Direction {
        std::size_t ordinal = 0;
        std::string path;
        double slope = 0.;
    };

public:
    Codes(Project& project, bool fixed) {
        if (fixed) {
            return;
        }
        for (const auto& entry : parameter_entries(project)) {
            if (entry.refinable && entry.parameter->free.get() && !directions_.contains(entry.parameter)) {
                directions_.emplace(entry.parameter, Direction{++count_, entry.path, 1.});
            }
        }
        for (const auto& relation : detail::fullprof_relation_directions(project)) {
            const auto seed = directions_.find(relation.source);
            if (seed == directions_.end()) {
                unsupported("constraint has no exported free source for " + relation.name);
            }
            const auto ordinal = seed->second.ordinal;
            directions_.emplace(relation.target, Direction{ordinal, relation.name, relation.slope});
            double& largest = group_maximum_[ordinal];
            largest = std::max({1., largest, std::abs(relation.slope)});
        }
    }

    Field field(const Parameter& parameter, double factor = 1.) {
        const auto direction = directions_.find(&parameter);
        if (direction == directions_.end()) {
            return {parameter.value.get() * factor};
        }
        written_.insert(&parameter);
        const auto ordinal = direction->second.ordinal;
        double shift = 1.;
        if (const auto group = group_maximum_.find(ordinal); group != group_maximum_.end()) {
            // Leave room for unit conversions such as Uiso to Biso within the codeword's decimal slot.
            shift = (direction->second.slope / group->second) * (factor / 16.);
        }
        const double base = 10. * static_cast<double>(ordinal);
        const double code = std::copysign(base + std::abs(shift), shift);
        if (static_cast<float>(std::abs(code)) == static_cast<float>(base) || std::abs(shift) >= 10.) {
            unsupported("refinement multiplier is too small or large for " + direction->second.path);
        }
        return {parameter.value.get() * factor, code};
    }

    Field field(const OptionalParameter& parameter, double factor = 1.) {
        return parameter ? field(*parameter, factor) : Field{0.};
    }

    std::array<Field, 2> profile_pair(Field a, Field b, double first, double coupled, double second) const {
        const auto ordinal = [](double code) {
            return static_cast<std::size_t>(std::floor(std::abs(code) / 10.));
        };
        const auto shift = [&](double code) {
            return std::copysign(std::abs(code) - 10. * static_cast<double>(ordinal(code)), code);
        };
        const auto encode = [](std::size_t group, double step) {
            if (step == 0.) {
                return 0.;
            }
            const auto base = 10. * static_cast<double>(group);
            if (std::abs(step) >= 10. || static_cast<float>(base + std::abs(step)) == static_cast<float>(base)) {
                unsupported("unrepresentable transformed profile refinement multiplier");
            }
            return std::copysign(base + std::abs(step), step);
        };
        double combined = first * shift(a.code);
        if (a.code != 0. && b.code != 0. && ordinal(a.code) != ordinal(b.code)) {
            if (group_maximum_.contains(ordinal(a.code)) || group_maximum_.contains(ordinal(b.code))) {
                unsupported("two linked native directions contribute to one FullProf profile field");
            }
        } else {
            combined += coupled * shift(b.code);
        }
        return {{{first * a.value + coupled * b.value, encode(ordinal(a.code != 0. ? a.code : b.code), combined)},
                 {second * b.value, encode(ordinal(b.code), second * shift(b.code))}}};
    }

    std::size_t count() const { return count_; }

    void check_written() const {
        for (const auto& [parameter, direction] : directions_) {
            if (!written_.contains(parameter)) {
                unsupported("cannot write the refinement direction for " + direction.path);
            }
        }
    }

private:
    std::size_t count_ = 0;
    std::map<const Parameter*, Direction> directions_;
    std::map<std::size_t, double> group_maximum_;
    std::set<const Parameter*> written_;
};

void values(std::ostream& out, const std::vector<Field>& fields) {
    for (const auto& field : fields) {
        if (!std::isfinite(field.value)) {
            unsupported("a parameter is not finite");
        }
        out << ' ' << field.value;
    }
}

void pair_rows(std::ostream& out, std::string_view header, const std::vector<Field>& fields,
               std::string_view trailing = {}) {
    out << "! " << header << '\n';
    values(out, fields);
    out << trailing << '\n';
    for (const auto& field : fields) {
        out << ' ' << field.code;
    }
    out << '\n';
}

std::string title_text(std::string text) {
    for (char& c : text) {
        if (c == '!' || c == '#' || c == '\n' || c == '\r') {
            c = ' ';
        }
    }
    if (text.size() > 120) {
        text.resize(120);
    }
    return text;
}

bool token_field(std::string_view text) {
    return !text.empty() && text.find_first_of(" \t\n\r!#") == std::string_view::npos;
}

struct Bank {
    const BraggPdExperiment* model = nullptr;
    std::string file;
    int job = 0;
    int npr = 0;
    int nba = 0;
    bool texture = false;
    double step = 0.;
    double origin = 0.;
    double range_min = 0.;
    double range_max = 0.;
    double cthm = 0.;
    double intensity_scale = 1.;
    std::map<std::string, double> neutron_lengths{};

    bool tof() const { return job < 0; }
    bool simulation() const { return std::abs(job) > 1; }
    const PdDataBase& data() const {
        if (!model->data) unsupported("experiment " + model->name.value() + " has no measured data");
        return *model->data;
    }
};

Bank bank_for(const BraggPdExperiment& experiment, std::size_t index) {
    const auto prefix = experiment.name.value() + ": ";
    if (experiment.experiment_type.effective_sample_form() != SampleFormEnum::POWDER ||
        !experiment.data || experiment.experiment_type.effective_scattering_type() != ScatteringTypeEnum::BRAGG) {
        unsupported(prefix + "requires a nuclear powder pattern with an observation or calculation grid");
    }
    const bool tof = experiment.effective_beam_mode() == BeamModeEnum::TIME_OF_FLIGHT;
    const bool xray = experiment.experiment_type.effective_radiation_probe() == RadiationProbeEnum::XRAY;
    if (xray && (tof || experiment.xray_form_factor.value_or("") != "it1992" ||
                experiment.xray_dispersion.value_or("") != "sasaki1989")) {
        unsupported(prefix + "X-ray scattering tables differ from this FullProf export");
    }
    if (!xray && experiment.neutron_scattering_length.value_or("sears1992") != "sears1992") {
        unsupported(prefix + "neutron scattering table differs from FullProf's Sears table");
    }
    const auto& data = *experiment.data;
    const auto& x = data.axis();
    const bool simulation = experiment.calculation_only;
    if (x.size() < 2 ||
        (!simulation && (data.intensity_meas.size() != x.size() || data.intensity_meas_su.size() != x.size())) ||
        !std::isfinite(experiment.dataset_weight) || experiment.dataset_weight <= 0.) {
        unsupported(prefix + "invalid observation grid or bank weight");
    }
    for (std::size_t i = 0; i < x.size(); ++i) {
        const double y = simulation ? 0. : data.intensity_meas.get()[i];
        const double sigma = simulation ? 1. : data.intensity_meas_su.get()[i];
        if (!std::isfinite(x[i]) || (i > 0 && x[i] <= x[i - 1]) || !std::isfinite(y) ||
            !std::isfinite(sigma) || sigma <= 0.) {
            unsupported(prefix + "requires increasing coordinates and finite measurements with positive sigma");
        }
    }

    const auto peak = experiment.peak.type.value_or(tof ? "tof-jorgensen" : "cwl-tch-pseudo-voigt");
    int npr = 0;
    if (tof) {
        if (peak == "tof-pseudo-voigt") {
            npr = 7;
        } else if (peak == "tof-jorgensen" || peak == "tof-jorgensen-von-dreele") {
            npr = 9;
        } else {
            unsupported(prefix + "peak profile " + peak);
        }
    } else if (peak == "cwl-lorentzian") {
        npr = 1;
    } else if (peak == "cwl-pseudo-voigt" || peak == "cwl-pseudo-voigt-berar-baldinozzi") {
        npr = 5;
    } else if (peak == "cwl-tch-pseudo-voigt" || peak == "cwl-tch-pseudo-voigt-fcj") {
        npr = 7;
    } else if (peak != "cwl-gaussian") {
        unsupported(prefix + "peak profile " + peak);
    }

    const int job = simulation ? (tof ? -3 : xray ? 2 : 3) : (tof ? -1 : xray ? 0 : 1);
    Bank bank{&experiment, "pattern_" + std::to_string(index) + ".dat", job, npr, 0,
              !experiment.preferred_orientation.empty()};
    bank.range_min = x.front();
    bank.range_max = x.back();
    bank.step = (x.back() - x.front()) / static_cast<double>(x.size() - 1);
    if (simulation) {
        for (std::size_t i = 1; i < x.size(); ++i) {
            const double requested = x.front() + bank.step * static_cast<double>(i);
            if (std::abs(x[i] - requested) > bank.step * 1.e-6) {
                unsupported(prefix + "FullProf calculations require a regular grid");
            }
        }
    }
    if (experiment.background_type == "line-segment") {
        if (experiment.background.size() >= 2) {
            bank.nba = static_cast<int>(experiment.background.size());
        }
    } else if (experiment.background_type == "polynomial" && experiment.background_origin) {
        bank.origin = *experiment.background_origin;
        if (std::any_of(experiment.background_terms.begin(), experiment.background_terms.end(),
                        [](const auto& term) { return term->order.get() >= 6; })) {
            bank.nba = -3;
        }
    } else if (experiment.background_type == "chebyshev" &&
               experiment.background_x_min && experiment.background_x_max &&
               *experiment.background_x_min <= x.front() + detail::fullprof_range_tolerance(x.front()) &&
               *experiment.background_x_max >= x.back() - detail::fullprof_range_tolerance(x.back())) {
        bank.nba = -5;
        bank.range_min = *experiment.background_x_min;
        bank.range_max = *experiment.background_x_max;
    } else {
        unsupported(prefix + "background basis or Chebyshev interval");
    }

    const auto& instrument = experiment.instrument;
    if (xray && value(instrument.setup_polarization_coefficient) != 0.) {
        if (value(instrument.setup_polarization_coefficient) != 0.5) {
            unsupported(prefix + "only characteristic X-ray polarization is representable");
        }
        const double angle = value(instrument.setup_monochromator_twotheta) * std::numbers::pi / 180.;
        bank.cthm = std::pow(std::cos(angle), 2);
        if (bank.cthm < 1.e-12) {
            unsupported(prefix + "ambiguous zero Cthm polarization");
        }
        bank.intensity_scale = 0.5;
    }
    const auto absorption = experiment.absorption.type.value_or("none");
    if (absorption != "none" && absorption != (tof ? "cylinder" : "cylinder-hewat")) {
        unsupported(prefix + "absorption model " + absorption);
    }
    if (!tof && value(instrument.setup_wavelength) <= 0.) {
        unsupported(prefix + "a positive wavelength is required");
    }
    return bank;
}

const LinkedStructure* link_for(const Bank& bank, const Structure& structure) {
    const auto name = datablock_key(structure.name.value(), "structure");
    for (const auto& link : bank.model->linked_structures) {
        if (link->enabled.get() && datablock_key(link->structure_id.value(), "structure") == name) {
            return link.get();
        }
    }
    return nullptr;
}

bool magnetic_only(const Structure& structure) {
    const auto& lengths = structure.scattering_lengths_fm.get();
    return structure_magnetic(structure) && !lengths.empty() &&
        std::all_of(structure.atom_sites.begin(), structure.atom_sites.end(), [&](const auto& site) {
            const auto held = lengths.find(site->type_symbol.value());
            return held != lengths.end() && held->second == 0.;
        });
}

bool needs_neutron_lengths(const Structure& structure) {
    return !magnetic_only(structure) && (!structure.scattering_lengths_fm.empty() ||
        std::any_of(structure.atom_sites.begin(), structure.atom_sites.end(), [](const auto& site) {
            const auto& type = site->type_symbol.value();
            return !type.empty() && std::isdigit(static_cast<unsigned char>(type.front()));
        }));
}

void add_neutron_lengths(std::map<std::string, double>& lengths, const Structure& structure) {
    if (magnetic_only(structure)) {
        return;
    }
    for (const auto& site : structure.atom_sites) {
        const auto& type = site->type_symbol.value();
        const auto symbol = detail::fullprof_scattering_type(type);
        const auto& overrides = structure.scattering_lengths_fm.get();
        const auto held = overrides.find(type);
        const auto standard = detail::fullprof_default_neutron_length(type);
        if (!overrides.empty() && held == overrides.end()) {
            unsupported("missing custom neutron scattering length for " + type);
        }
        double length = 0.;
        if (held != overrides.end()) {
            length = held->second;
        } else if (standard) {
            length = *standard;
        } else {
            unsupported("unknown isotope scattering length for " + type);
        }
        const auto [entry, fresh] = lengths.emplace(symbol, length);
        if (!fresh && entry->second != length) {
            unsupported("FullProf patterns share one scattering length per atom type " + symbol);
        }
    }
}

void write_neutron_lengths(std::ostream& out, const std::map<std::string, double>& lengths, std::size_t index) {
    if (lengths.empty()) {
        return;
    }
    if (lengths.size() > 99) {
        unsupported("too many FullProf neutron scattering overrides");
    }
    out << "! Additional scattering factors for Pattern# " << index << '\n';
    for (const auto& [symbol, length] : lengths) {
        out << symbol << ' ' << length / 10. << " 0 0\n";
    }
}

const PrefOrient* texture_for(const Bank& bank, const Structure& structure) {
    for (const auto& row : bank.model->preferred_orientation) {
        if (row->structure_id.value() == structure.name.value()) {
            return row.get();
        }
    }
    return nullptr;
}

void write_setup(std::ostream& out, const Bank& bank, std::size_t index) {
    const auto& experiment = *bank.model;
    const auto& instrument = experiment.instrument;
    if (bank.tof()) {
        out << "! Bkpos Wdt Iabscor for Pattern# " << index << '\n'
            << bank.origin << ' ' << experiment.peak.cutoff_fwhm << ' '
            << (experiment.absorption.abscor1 ? 2 : 0) << '\n';
    } else {
        out << "! Lambda1 Lambda2 Ratio Bkpos Wdt Cthm muR AsyLim Rpolarz 2nd-muR -> Patt# " << index << '\n'
            << value(instrument.setup_wavelength) << ' '
            << (value(instrument.setup_wavelength_2_to_1_ratio) > 0. ? value(instrument.setup_wavelength_2)
                                                                    : value(instrument.setup_wavelength))
            << ' ' << value(instrument.setup_wavelength_2_to_1_ratio) << ' ' << bank.origin << ' '
            << experiment.peak.cutoff_fwhm << ' ' << bank.cthm << ' ' << value(experiment.absorption.mu_r) << ' '
            << (experiment.peak.asym_beba_limit ? value(experiment.peak.asym_beba_limit)
                                               : 180.) << " 0 "
            << (value(instrument.setup_wavelength_2_to_1_ratio) > 0. ? value(experiment.absorption.mu_r) : 0.) << '\n';
    }
}

void write_background(std::ostream& out, const Bank& bank, Codes& codes, std::size_t index) {
    const auto& experiment = *bank.model;
    if (bank.nba >= 2) {
        out << "!2Theta/TOF/E(Kev) Background for Pattern# " << index << '\n';
        double previous = -std::numeric_limits<double>::infinity();
        for (const auto& point : experiment.background) {
            if (!std::isfinite(point->position.get()) || point->position.get() <= previous) {
                unsupported(experiment.name.value() + ": background points must be distinct and in increasing order");
            }
            previous = point->position.get();
            const auto intensity = codes.field(point->intensity);
            out << previous << ' ' << intensity.value << ' ' << intensity.code << '\n';
        }
        return;
    }
    const std::size_t terms = bank.nba == -5 ? 24U : bank.nba == -3 ? 12U : 6U;
    std::vector<Field> fields(terms, Field{0.});
    if (!experiment.background.empty()) {
        fields.front() = codes.field(experiment.background[0]->intensity);
    }
    for (const auto& term : experiment.background_terms) {
        if (term->order.get() < 0 || static_cast<std::size_t>(term->order.get()) >= fields.size()) {
            unsupported(experiment.name.value() + ": polynomial order exceeds FullProf's supported range");
        }
        fields[static_cast<std::size_t>(term->order.get())] = codes.field(term->coef);
    }
    out << "! Background coefficients/codes for Pattern# " << index << '\n';
    for (std::size_t from = 0; from < fields.size(); from += 6) {
        const auto start = fields.begin() + static_cast<std::ptrdiff_t>(from);
        const std::vector<Field> row(start, start + 6);
        values(out, row);
        out << '\n';
        for (const auto& field : row) {
            out << ' ' << field.code;
        }
        out << '\n';
    }
}

void write_calibration(std::ostream& out, const Bank& bank, Codes& codes, std::size_t index) {
    const auto& instrument = bank.model->instrument;
    const auto field = [&](const Field& phase) { out << ' ' << phase.value << ' ' << phase.code; };
    if (bank.tof()) {
        out << "! Zero Code Dtt1 Code Dtt2 Code Dtt_1overd Code 2ThetaBank -> Patt# " << index << '\n';
        field(codes.field(instrument.calib_d_to_tof_offset));
        field(codes.field(instrument.calib_d_to_tof_linear));
        field(codes.field(instrument.calib_d_to_tof_quadratic));
        field(codes.field(instrument.calib_d_to_tof_reciprocal));
        out << ' ' << instrument.setup_twotheta_bank.value.get() << '\n';
    } else {
        out << "! Zero Code SyCos Code SySin Code Lambda Code MORE -> Patt# " << index << '\n';
        field(codes.field(instrument.calib_twotheta_offset));
        field(codes.field(instrument.calib_sample_displacement));
        field(codes.field(instrument.calib_sample_transparency));
        field(codes.field(instrument.setup_wavelength));
        out << " 0\n";
    }
}

void write_profile(std::ostream& out, Structure& structure, const Bank& bank, std::size_t index,
                   std::size_t phase, const LinkedStructure& link, Codes& codes) {
    const auto& peak = bank.model->peak;
    const auto* texture = texture_for(bank, structure);
    const auto field = [&codes](const auto& parameter) { return codes.field(parameter); };
    out << "!-------> Profile Parameters for Pattern # " << index << " ----> Phase # " << phase << '\n';
    pair_rows(out, bank.tof() ? "Scale Extinc Bov Str1 Str2 Str3 Strain-Model"
                             : "Scale Shape1 Bov Str1 Str2 Str3 Strain-Model",
              {codes.field(link.scale, bank.intensity_scale / detail::fullprof_powder_scale_in_native_units(structure)),
               bank.tof() ? Field{0.} : field(peak.mixing_eta_0), {0.}, {0.}, {0.}, {0.}}, " 0");
    if (bank.tof()) {
        // FullProf's base rows include the separately declared size and strain contributions.
        const auto sigma2 = codes.profile_pair(field(peak.broad_gauss_sigma_2), field(peak.broad_gauss_size), 1., 1., 1.);
        const auto sigma1 = codes.profile_pair(field(peak.broad_gauss_sigma_1), field(peak.broad_gauss_strain), 1., 1., 1.);
        const auto gamma2 = codes.profile_pair(field(peak.broad_lorentz_gamma_2), field(peak.broad_lorentz_size), 1., 1., 1.);
        const auto gamma1 = codes.profile_pair(field(peak.broad_lorentz_gamma_1), field(peak.broad_lorentz_strain), 1., 1., 1.);
        pair_rows(out, "Sigma-2 Sigma-1 Sigma-0 Sigma-Q Iso-GStrain Iso-GSize Ani-LSize Size-Model",
                  {sigma2[0], sigma1[0], field(peak.broad_gauss_sigma_0), {0.}, sigma1[1], sigma2[1], {0.}}, " 0");
        pair_rows(out, "Gamma-2 Gamma-1 Gamma-0 Iso-LorStrain Iso-LorSize",
                  {gamma2[0], gamma1[0], field(peak.broad_lorentz_gamma_0), gamma1[1], gamma2[1]});
    } else {
        std::vector<Field> widths{field(peak.broad_gauss_u), field(peak.broad_gauss_v),
                                  field(peak.broad_gauss_w),
                                  peak.mixing_eta_1 ? field(peak.mixing_eta_1) : field(peak.broad_lorentz_x),
                                  field(peak.broad_lorentz_y), {0.}, {0.}};
        pair_rows(out, "U V W X Y GauSiz LorSiz Size-Model", widths, " 0");
    }
    std::vector<Field> cell;
    for (const auto* parameter : structure.cell.parameters()) {
        cell.push_back(field(*parameter));
    }
    pair_rows(out, "a b c alpha beta gamma", cell);
    if (bank.tof()) {
        pair_rows(out, "Pref1 Pref2 alph0 beta0 alph1 beta1 alphQ betaQ",
                  {{0.}, {0.}, bank.npr == 9 ? field(peak.rise_alpha_0) : Field{0.},
                   bank.npr == 9 ? field(peak.decay_beta_0) : Field{0.},
                   bank.npr == 9 ? field(peak.rise_alpha_1) : Field{0.},
                   bank.npr == 9 ? field(peak.decay_beta_1) : Field{0.}, {0.}, {0.}});
        const auto absorption = field(bank.model->absorption.abscor1);
        out << "!Absorption correction parameters\n" << absorption.value << ' ' << absorption.code
            << " 0 0 ABS: ABSCOR1 ABSCOR2\n";
    } else {
        const auto low = codes.profile_pair(field(peak.asym_beba_a0), field(peak.asym_beba_b0), -1., 3., -1.);
        const auto high = codes.profile_pair(field(peak.asym_beba_a1), field(peak.asym_beba_b1), -1., 3., -1.);
        std::vector<Field> shape{texture ? field(texture->march_r) : Field{bank.texture ? 1. : 0.},
                                 texture ? field(texture->march_random_fract) : Field{0.},
                                 low[0], low[1], high[0], high[1]};
        if (bank.npr == 7) {
            const auto aperture_1 = field(peak.asym_fcj_1);
            const auto aperture_2 = field(peak.asym_fcj_2);
            if ((aperture_1.value == 0.) != (aperture_2.value == 0.)) {
                unsupported("FullProf interprets a single nonzero FCJ aperture as an equal-aperture model");
            }
            shape.push_back(aperture_1);
            shape.push_back(aperture_2);
        }
        pair_rows(out, "Pref1 Pref2 Asy1 Asy2 Asy3 Asy4 S_L D_L", shape);
    }
}

void require_structure(const Structure& structure) {
    if (!token_field(structure.name.value()) || structure.atom_sites.empty()) {
        unsupported(structure.name.value() + ": requires a named structure");
    }
    // A Le Bail or Pawley structure is not written as a Rietveld phase (edi ADR-0109).
    if (extracts_intensities(structure)) {
        unsupported(structure.name.value() + ": the export writes Rietveld phases only, not Le Bail or Pawley");
    }
}

std::string magnetic_label(const Structure& structure, const AtomSite& site) {
    const auto factor = std::find_if(structure.magnetic_form_factors.begin(), structure.magnetic_form_factors.end(),
                                    [&](const auto& row) { return row->id.value() == site.type_symbol.value(); });
    std::string ion = site.type_symbol.value();
    if (factor != structure.magnetic_form_factors.end()) {
        if ((*factor)->approximation.value() != "j0") {
            unsupported("non-j0 magnetic form factor for " + site.type_symbol.value());
        }
        if (!(*factor)->ion.empty()) {
            ion = (*factor)->ion.value();
        }
    }
    if (!ion.empty() && ion.back() == '+') {
        ion.pop_back();
    }
    if (ion.empty() || !std::isdigit(static_cast<unsigned char>(ion.back()))) {
        ion += '0';
    }
    for (char& c : ion) {
        c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    }
    const auto& radial = structure.magnetic->radial_coefficients;
    const auto held = std::find_if(radial.begin(), radial.end(),
                                   [&](const auto& row) { return row.first == site.type_symbol.value(); });
    if (held == radial.end()) {
        return "M" + ion;
    }
    const auto expected = detail::fullprof_magnetic_radial("J" + ion);
    if (!expected || expected->values != held->second.values) {
        unsupported("custom magnetic form factor for " + site.type_symbol.value());
    }
    return "J" + ion;
}

void write_magnetic_group(std::ostream& out, const Structure& structure) {
    const auto& magnetic = structure.magnetic.get();
    const auto setting = held_magnetic_setting(structure);
    if (!bns_transform_consistent(magnetic)) {
        unsupported(structure.name.value() + ": FullProf magnetic export requires consistent BNS setting information");
    }
    const auto symmetry = detail::fullprof_magnetic_operators(structure);
    if (symmetry.operators.empty()) {
        unsupported(structure.name.value() + ": no FullProf magnetic symmetry operators");
    }
    const auto& group = magnetic.group.name_uni.empty() ? magnetic.group.name_bns : magnetic.group.name_uni;
    if (magnetic.group.number_bns.empty()) {
        out << "P1 <--Magnetic Space Group Symbol\n";
    } else {
        out << group << " number: " << magnetic.group.number_bns << " <--Magnetic Space Group Symbol\n";
    }
    out << "Transform to standard: " << setting << '\n'
        << "Parent Space Group: "
        << (magnetic.parent.name_h_m_alt.empty() && magnetic.parent.it_number.empty()
                ? structure.space_group.name_h_m.value() : magnetic.parent.name_h_m_alt)
        << " IT_number: " << (magnetic.parent.it_number.empty() ? std::to_string(space_group_it_number(structure.space_group))
                                                               : magnetic.parent.it_number)
        << "\nTransform from Parent: " << (magnetic.parent.child_transform_pp_abc.empty() ? "a,b,c;0,0,0"
                                                                                         : magnetic.parent.child_transform_pp_abc)
        << "\n! Nsym Cen N_Clat N_Ant\n" << symmetry.operators.size() << ' '
        << (symmetry.centrosymmetric ? 2 : 1) << ' ' << symmetry.centerings.size() << ' '
        << symmetry.anti_centerings.size() << '\n';
    const auto write_centerings = [&](const auto& centerings, std::string_view heading) {
        if (!centerings.empty()) {
            out << heading << '\n';
        }
        for (const auto& shift : centerings) {
            out << shift[0] << ' ' << shift[1] << ' ' << shift[2] << '\n';
        }
    };
    write_centerings(symmetry.centerings, "! Centring vectors");
    write_centerings(symmetry.anti_centerings, "! Anti-Centring vectors");
    out << "! Symmetry operators\n";
    for (std::size_t i = 0; i < symmetry.operators.size(); ++i) {
        out << i + 1 << ' ' << symmetry.operators[i] << '\n';
    }
}

void write_atoms(std::ostream& out, Structure& structure, Codes& codes, bool magnetic = false) {
    if (magnetic) {
        write_magnetic_group(out, structure);
        out << "!Atom Typ Mag Vek X Y Z Biso Occ N_type Spc/Fftype\n";
    } else {
        std::string group = structure.space_group.name_h_m.value();
        const auto& setting = structure.space_group.coord_system_code.value();
        if (group.empty() || group.find_first_of("!#\r\n") != std::string::npos) {
            unsupported(structure.name.value() + ": missing or invalid Hermann–Mauguin symbol");
        }
        if (setting == "r") {
            group += ":R";
        } else if (setting.starts_with('1') || setting.starts_with('2')) {
            const auto default_setting = detail::fullprof_default_space_group(group);
            if (!default_setting || default_setting->coord_system_code != setting) {
                auto alternate = setting;
                alternate.front() = '2';
                if (setting.starts_with('1') && default_setting && default_setting->coord_system_code == alternate) {
                    group += ":1";
                } else {
                    unsupported(structure.name.value() + ": FullProf origin choice " + setting +
                                " is unsupported for " + group);
                }
            }
        }
        out << group << " <--Space group symbol\n!Atom Typ X Y Z Biso Occ In Fin N_t Spc /Codes\n";
    }

    const auto positions = wyckoff_positions(structure);
    int general = 0;
    for (const auto& position : positions) {
        general = std::max(general, position.multiplicity);
    }
    for (const auto& site : structure.atom_sites) {
        const auto label = site->id.value();
        auto type = detail::fullprof_scattering_type(site->type_symbol.value());
        const auto adp = site->adp_type.value();
        const auto moment = std::find_if(structure.atom_site_moment.begin(), structure.atom_site_moment.end(),
                                         [&](const auto& row) { return row->id.value() == label; });
        const bool moment_present = magnetic && moment != structure.atom_site_moment.end();
        if (moment_present) {
            type = magnetic_label(structure, *site);
        }
        if (!token_field(label) || label.size() > 6 || !token_field(type) ||
            (adp != "Biso" && adp != "Uiso" && adp != "beta")) {
            unsupported(structure.name.value() + ": unsupported atom label, scattering type or ADP for " + label);
        }
        int multiplicity = 0;
        int general_multiplicity = general;
        if (magnetic && positions.empty()) {
            const auto geometry = detail::fullprof_site_geometry(structure, *site);
            multiplicity = geometry.site_multiplicity;
            general_multiplicity = geometry.general_multiplicity;
        } else {
            const auto letter = site->wyckoff_letter.empty() ? detail::inferred_wyckoff_letter(structure, *site)
                                                            : site->wyckoff_letter.value();
            const auto site_position = std::find_if(positions.begin(), positions.end(), [&](const auto& position) {
                return position.letter == letter;
            });
            if (site_position != positions.end()) {
                multiplicity = site_position->multiplicity;
            }
        }
        if (multiplicity <= 0 || general_multiplicity <= 0) {
            unsupported(structure.name.value() + ": cannot establish site multiplicity for " + label);
        }
        const bool tensor = adp == "beta";
        const std::vector<Field> row{codes.field(site->fract_x), codes.field(site->fract_y), codes.field(site->fract_z),
                                     tensor ? Field{0.} : codes.field(site->adp_iso, adp == "Uiso" ? 8. * std::numbers::pi * std::numbers::pi : 1.),
                                     codes.field(site->occupancy, static_cast<double>(multiplicity) / general_multiplicity)};
        out << label << ' ' << type;
        if (magnetic) {
            out << (moment_present ? " 1 0" : " 0 0");
        }
        values(out, row);
        if (magnetic) {
            out << ' ' << static_cast<int>(moment_present) + 2 * static_cast<int>(tensor) << " 0\n";
        } else {
            out << " 0 0 " << (tensor ? 2 : 0) << " 0\n";
        }
        for (const auto& field : row) {
            out << ' ' << field.code;
        }
        out << '\n';
        if (moment_present) {
            std::vector<Field> fields;
            for (const auto* parameter : (*moment)->parameters()) {
                fields.push_back(codes.field(*parameter));
            }
            fields.resize(7, Field{0.});
            pair_rows(out, "Rx Ry Rz Ix Iy Iz MagPh", fields);
        }
        if (tensor) {
            const auto found = std::find_if(structure.atom_site_aniso.begin(), structure.atom_site_aniso.end(),
                                            [&](const auto& candidate) { return candidate->id.value() == label; });
            if (found == structure.atom_site_aniso.end()) {
                unsupported("missing beta tensor for " + label);
            }
            std::vector<Field> beta;
            for (const auto* parameter : (*found)->parameters()) {
                beta.push_back(codes.field(*parameter));
            }
            pair_rows(out, "beta11 beta22 beta33 beta12 beta13 beta23", beta);
        }
    }
}

void write_phase(std::ostream& out, Structure& structure, const std::vector<Bank>& banks, std::size_t number,
                 Codes& codes) {
    require_structure(structure);
    const bool magnetic = structure_magnetic(structure);
    std::vector<const LinkedStructure*> links;
    for (const auto& bank : banks) {
        const auto* link = link_for(bank, structure);
        if (link && magnetic && (bank.job == 0 || bank.job == 2)) {
            unsupported("FullProf magnetic export requires a neutron experiment");
        }
        links.push_back(link);
    }
    if (std::none_of(links.begin(), links.end(), [](const auto* link) { return link != nullptr; })) {
        unsupported(structure.name.value() + ": phase is unused");
    }
    out << "!-------------------------------------------------------------------------------\n"
        << "! Data for PHASE number: " << number << '\n'
        << "!-------------------------------------------------------------------------------\n"
        << structure.name.value() << (magnetic_only(structure) ? " mag_only\n" : "\n")
        << "!Nat Dis Ang Jbt Isy Str Furth ATZ Nvk More\n"
        << structure.atom_sites.size() << (magnetic ? " 0 0 10 2 0 0 0 0 0\n" : " 0 0 0 0 0 0 0 0 0\n")
        << "!Contributions (0/1) of this phase to the patterns\n";
    for (const auto* link : links) {
        out << (link ? " 1" : " 0");
    }
    out << '\n';
    for (std::size_t i = 0; i < banks.size(); ++i) {
        if (!links[i]) {
            continue;
        }
        const auto& bank = banks[i];
        const auto* texture = texture_for(bank, structure);
        out << "!Irf Npr Jtyp Nsp_Ref Ph_Shift for Pattern# " << i + 1 << "\n0 " << bank.npr
            << ' ' << (bank.tof() ? -1 : bank.job) << " 0 0\n"
            << "! Pr1 Pr2 Pr3 Brind Rmua Rmub Rmuc for Pattern# " << i + 1 << '\n';
        if (texture) {
            out << texture->index_h.get() << ' ' << texture->index_k.get() << ' ' << texture->index_l.get();
        } else {
            out << "0 0 1";
        }
        out << " 1 0 0 0\n";
    }
    write_atoms(out, structure, codes, magnetic);
    for (std::size_t i = 0; i < banks.size(); ++i) {
        if (links[i]) {
            write_profile(out, structure, banks[i], i + 1, number, *links[i], codes);
        }
    }
}

std::ofstream output_file(const fs::path& path) {
    std::ofstream out(path);
    if (!out) {
        unsupported("cannot write " + path.string());
    }
    out.imbue(std::locale::classic());
    out << std::setprecision(std::numeric_limits<double>::max_digits10);
    out.exceptions(std::ios::badbit | std::ios::failbit);
    return out;
}

void write_data(const Bank& bank, const fs::path& folder) {
    auto out = output_file(folder / bank.file);
    const auto& data = bank.data();
    const auto& x = data.axis();
    const double boundary = x.back() + (x.back() - x[x.size() - 2]);
    if (!std::isfinite(boundary) || boundary <= x.back()) {
        unsupported("cannot represent the FullProf powder grid's trailing boundary");
    }
    out << "XYDATA " << title_text(bank.model->name.value())
        << "\n! Exported by EasyDiffraction\n! X Y sigma"
        << "\n! Final record is an unmeasured grid boundary outside the calculation range\nINTER 1 1 0 0\nTEMP 0\n";
    for (std::size_t i = 0; i < x.size(); ++i) {
        out << x[i] << ' ' << data.intensity_meas.get()[i] << ' ' << data.intensity_meas_su.get()[i] << '\n';
    }
    // FullProf's XYDATA reader needs a following grid coordinate to evaluate
    // the last measured channel fully. The PCR ends at the last observation.
    out << boundary << " 0 1\n";
    out.close();
}

constexpr std::array extinction_fields{&ExtinctionBase::coefficient_11, &ExtinctionBase::coefficient_22,
    &ExtinctionBase::coefficient_33, &ExtinctionBase::coefficient_12, &ExtinctionBase::coefficient_13,
    &ExtinctionBase::coefficient_23};

void write_single_crystal(Project& project, const fs::path& folder, Codes& codes) {
    if (project.experiments.size() > 6 || project.structures.size() != 1) {
        unsupported("one FullProf INT file requires one structure and at most six datasets");
    }
    auto& structure = *project.structures[0];
    const auto& first = *project.experiments[0];
    require_structure(structure);
    const bool magnetic = structure_magnetic(structure);
    const bool tof = first.effective_beam_mode() == BeamModeEnum::TIME_OF_FLIGHT;
    const bool xray = first.experiment_type.effective_radiation_probe() == RadiationProbeEnum::XRAY;
    const auto wavelength = value(first.instrument.setup_wavelength);
    const auto threshold = first.reflns_threshold_sigma.value_or(0.);
    const auto extinction_type = first.extinction.type.value_or("none");
    const bool anisotropic = extinction_type == "larson-anisotropic";
    const bool isotropic = extinction_type == "larson-isotropic";
    if ((tof && xray) || (magnetic && xray) || (!tof && wavelength <= 0.) ||
        (!anisotropic && !isotropic && extinction_type != "none")) {
        unsupported("single-crystal wavelength, probe or extinction law");
    }
    std::vector<Field> scales;
    for (const auto& held : project.experiments) {
        const auto& exp = *held;
        if (exp.experiment_type.effective_sample_form() != SampleFormEnum::SINGLE_CRYSTAL ||
            exp.effective_beam_mode() != first.effective_beam_mode() ||
            exp.experiment_type.effective_radiation_probe() != first.experiment_type.effective_radiation_probe() ||
            value(exp.instrument.setup_wavelength) != wavelength || exp.extinction.type.value_or("none") != extinction_type ||
            !exp.reflections || !exp.reflections->rectangular() || exp.reflections->size() == 0 ||
            exp.reflections->wavelength.empty() == tof ||
            !exp.excluded_regions.empty() || !exp.excluded_reflections.empty() ||
            exp.reflns_threshold_sigma.value_or(0.) != threshold || exp.reflns_merge.value_or("none") != "none" ||
            exp.reflns_absences.value_or("include") != "include" || exp.dataset_weight != first.dataset_weight) {
            unsupported("single-crystal datasets must share geometry, wavelength, weighting and extinction law");
        }
        if ((!xray && exp.neutron_scattering_length.value_or("sears1992") != "sears1992") ||
            (xray && (exp.xray_form_factor.value_or("") != "it1992" || exp.xray_dispersion.value_or("") != "sasaki1989")) ||
            exp.linked_structures.size() != 1 || !exp.linked_structure().enabled.get() ||
            datablock_key(exp.linked_structure().structure_id.value(), "structure") !=
                datablock_key(structure.name.value(), "structure")) {
            unsupported("single-crystal export requires one enabled phase with standard scattering factors");
        }
        scales.push_back(codes.field(exp.linked_structure().scale));
    }
    scales.resize(6, Field{0.});
    std::map<std::string, double> neutron_lengths;
    if (!xray && needs_neutron_lengths(structure)) {
        add_neutron_lengths(neutron_lengths, structure);
    }
    const auto common_extinction = [&](auto field) {
        const auto common = codes.field(first.extinction.*field);
        for (const auto& exp : project.experiments) {
            const auto other = codes.field(exp->extinction.*field);
            if (other.value != common.value || other.code != common.code) {
                unsupported("FullProf INT datasets share one extinction coefficient tensor");
            }
        }
        return common;
    };
    std::vector<Field> extinction;
    if (isotropic) {
        extinction.push_back(common_extinction(&ExtinctionBase::coefficient));
    } else if (anisotropic) {
        for (const auto field : extinction_fields) {
            extinction.push_back(common_extinction(field));
        }
    }
    extinction.resize(7, Field{0.});
    const int job = tof ? -1 : xray ? 0 : 1;
    auto out = output_file(folder / "project.pcr");
    out << "COMM " << title_text(project.metadata.title.empty() ? project.metadata.name : project.metadata.title)
        << "\n! Files => DAT-file: project.int, PCR-file: project\n"
        << "!Job Npr Nph Nba Nex Nsc Nor Dum Iwg Ilo Ias Res Ste Nre Cry Uni Cor Opt Aut\n"
        << job << " 0 1 0 0 " << neutron_lengths.size() << " 0 0 0 0 0 0 0 0 1 0 0 0 1\n"
        << "!Ipr Ppl Ioc Mat Pcr Ls1 Ls2 Ls3 NLI Prf Ins Rpa Sym Hkl Fou Sho Ana\n"
        << "0 0 1 0 2 0 4 0 0 1 0 0 0 0 0 0 0\n"
        << "!NCY Eps R_at R_an R_pr R_gl Thmin Step Thmax PSD Sent0\n"
        << (codes.count() == 0 ? 1 : std::max(1, project.minimizer_max_iterations))
        << " 0.05 0.2 0.2 0.2 0.2 0 0.1 89.9 0 0\n";
    write_neutron_lengths(out, neutron_lengths, 1);
    out << codes.count() << " !Number of refined parameters\n"
        << "!-------------------------------------------------------------------------------\n"
        << "! Data for PHASE number: 1\n"
        << "!-------------------------------------------------------------------------------\n"
        << structure.name.value() << (magnetic_only(structure) ? " mag_only\n" : "\n")
        << "!Nat Dis Ang Pr1 Pr2 Pr3 Jbt Irf Isy Str Furth ATZ Nvk Npr More\n"
        << structure.atom_sites.size()
        << (magnetic ? " 0 0 0 0 1 10 4 2 0 0 0 0 0 1\n" : " 0 0 0 0 1 0 4 0 0 0 0 0 0 1\n")
        << "!Jvi Jdi Hel Sol Mom Ter Brind RMua RMub RMuc Jtyp Nsp_Ref Ph_Shift N_Domains\n"
        << "0 0 0 0 0 0 1 " << first.dataset_weight << ' ' << threshold << " 0 " << job << " 0 0 0\n";
    write_atoms(out, structure, codes, magnetic);
    out << "!-------> Scale, Extinction and Cell Parameters for Pattern # 1\n";
    pair_rows(out, "Sc1 Sc2 Sc3 Sc4 Sc5 Sc6", scales);
    pair_rows(out, "Ext1 Ext2 Ext3 Ext4 Ext5 Ext6 Ext7 Ext-Model", extinction, anisotropic ? " 4" : " 1");
    std::vector<Field> cell;
    for (const auto* parameter : structure.cell.parameters()) {
        cell.push_back(codes.field(*parameter));
    }
    pair_rows(out, "a b c alpha beta gamma", cell);
    pair_rows(out, "x-Lambda/2 optional terms", {{0.}, {0.}, {0.}, {0.}, {0.}});
    out << "! 2Th1/TOF1 2Th2/TOF2 Pattern to plot\n0 89.9 1\n";
    codes.check_written();
    out.close();

    auto data = output_file(folder / "project.int");
    data << title_text(first.name.value()) << (tof ? "\n(3i4,2f20.8,i4,4f16.8)\n" : "\n(3i4,2f20.8,i4,3f8.0)\n")
         << (tof ? 0. : wavelength) << " 0 0\n";
    data << std::fixed << std::setprecision(8);
    for (std::size_t dataset = 0; dataset < project.experiments.size(); ++dataset) {
        const auto& reflections = project.experiments[dataset]->reflections;
        if (!reflections) unsupported("experiment " + project.experiments[dataset]->name.value() + " has no reflections");
        const auto& rows = *reflections;
        for (std::size_t i = 0; i < rows.size(); ++i) {
            const auto h = rows.index_h.get()[i];
            const auto k = rows.index_k.get()[i];
            const auto l = rows.index_l.get()[i];
            const double y = rows.intensity_meas.get()[i];
            const double sigma = rows.intensity_meas_su.get()[i];
            if (h < -999 || h > 9999 || k < -999 || k > 9999 || l < -999 || l > 9999 ||
                !std::isfinite(y) || std::abs(y) >= 1.e9 || !std::isfinite(sigma) || sigma < 1.e-8 || sigma >= 1.e9) {
                unsupported("single-crystal observation exceeds the FullProf INT record precision or width");
            }
            data << std::setw(4) << h << std::setw(4) << k << std::setw(4) << l
                 << std::setw(20) << y << std::setw(20) << sigma << std::setw(4) << dataset + 1;
            if (tof) {
                const auto lambda = rows.wavelength.get()[i];
                if (!std::isfinite(lambda) || lambda < 1.e-8 || lambda > 1.e4) {
                    unsupported("TOF reflection wavelength exceeds the FullProf INT record precision or width");
                }
                // These auxiliary angles are not used by the supported nuclear F-squared laws.
                data << std::setw(16) << lambda << std::setw(16) << 0. << std::setw(16) << 0. << std::setw(16) << 0.;
            }
            data << '\n';
        }
    }
    data.close();
}

// The last fit's results beside the PCR, for the user: FullProf reads only the PCR, which already holds the fitted
// values, so the s.u.s and agreement factors would otherwise be lost (ADR-0096).
void write_fit_results(Project& project, const fs::path& folder) {
    const auto& fit = project.fit_result;
    if (!fit.held()) {
        return;
    }
    auto out = output_file(folder / "fit_results.txt");
    const auto number = [](double x) { return std::format("{:.6g}", x); };
    const auto percent = [](double x) { return std::format("{:.2f} %", 100. * x); };
    out << "EasyDiffraction fit results: "
        << (project.metadata.title.empty() ? project.metadata.name : project.metadata.title) << "\n"
        << "The fitted values are in project.pcr; FullProf does not read this file.\n\n"
        << "Fit: " << (fit.exit_reason.empty() ? std::string(fit.success ? "done" : "not converged") : fit.exit_reason)
        << ", " << fit.iterations << " iterations, " << fit.n_free_parameters << " free parameters, "
        << fit.n_data_points << " points\n";
    if (fit.reduced_chi_square) {
        out << "Reduced chi-square: " << number(*fit.reduced_chi_square) << "\n";
    }
    if (fit.prof_wr_factor) {
        out << "Rwp: " << percent(*fit.prof_wr_factor) << "\n";
    }
    if (fit.prof_r_factor) {
        out << "Rp: " << percent(*fit.prof_r_factor) << "\n";
    }
    if (fit.prof_wr_expected) {
        out << "Rexp: " << percent(*fit.prof_wr_expected) << "\n";
    }
    for (const auto& experiment : project.experiments) {
        if (!experiment->fit_share_held()) {
            continue;
        }
        out << "Experiment " << experiment->name.value() << ":";
        if (experiment->fit_prof_wr_factor) {
            out << " Rwp " << percent(*experiment->fit_prof_wr_factor);
        }
        if (experiment->fit_prof_r_factor) {
            out << ", Rp " << percent(*experiment->fit_prof_r_factor);
        }
        if (experiment->fit_n_data_points) {
            out << ", " << *experiment->fit_n_data_points << " points";
        }
        out << "\n";
    }
    out << "\nFree parameters, value(s.u.):\n";
    for (const auto& entry : parameter_entries(project)) {
        const auto& parameter = *entry.parameter;
        if (!parameter.free.get()) {
            continue;
        }
        const auto su = parameter.uncertainty.get();
        const double value = parameter.value.get();
        out << entry.block_name << " " << entry.path << " "
            << (su && std::isfinite(*su) && *su > 0. && std::isfinite(value) ? value_su_text(value, *su, project.su_rule)
                                                                              : number(value))
            << "\n";
    }
}

void write_pcr(Project& project, const fs::path& folder, bool fixed) {
    if (project.experiments.empty() || project.structures.empty() || project.sequential_fit.declared()) {
        unsupported("expected a complete project with measured experiments");
    }
    complete_relations(project);
    Codes codes(project, fixed);
    if (project.experiments[0]->experiment_type.effective_sample_form() == SampleFormEnum::SINGLE_CRYSTAL) {
        write_single_crystal(project, folder, codes);
        return;
    }
    std::vector<Bank> banks;
    for (const auto& experiment : project.experiments) {
        auto bank = bank_for(*experiment, banks.size() + 1);
        if (bank.job != 0 && bank.job != 2 &&
            std::any_of(project.structures.begin(), project.structures.end(), [&](const auto& phase) {
                return link_for(bank, *phase) && needs_neutron_lengths(*phase);
            })) {
            for (const auto& phase : project.structures) {
                if (link_for(bank, *phase)) {
                    add_neutron_lengths(bank.neutron_lengths, *phase);
                }
            }
        }
        banks.push_back(std::move(bank));
    }
    auto out = output_file(folder / "project.pcr");
    out << "COMM " << title_text(project.metadata.title.empty() ? project.metadata.name : project.metadata.title)
        << "\nNPATT " << banks.size();
    for (const auto& bank : banks) {
        if (std::none_of(project.structures.begin(), project.structures.end(),
                         [&](const auto& structure) { return link_for(bank, *structure); })) {
            unsupported(bank.model->name.value() + ": no enabled phase");
        }
        out << " 1";
    }
    out << "\nW_PAT";
    for (const auto& bank : banks) {
        out << ' ' << bank.model->dataset_weight;
    }
    out << "\n!Nph Dum Ias Nre Cry Opt Aut\n" << project.structures.size()
        << " 0 0 0 0 1 1\n!Job Npr Nba Nex Nsc Nor Iwg Ilo Res Ste Uni Cor Anm Int\n";
    for (const auto& bank : banks) {
        out << bank.job << ' ' << bank.npr << ' ' << bank.nba << ' ' << bank.model->excluded_regions.size()
            << ' ' << bank.neutron_lengths.size() << ' ' << static_cast<int>(bank.texture)
            << " 0 0 0 0 " << static_cast<int>(bank.tof()) << " 0 0 0\n";
    }
    out << "!File names of data(patterns) files\n";
    for (const auto& bank : banks) {
        out << bank.file << '\n';
    }
    out << "!Mat Pcr NLI Rpa Sym Sho\n0 2 0 1 0 0\n!Ipr Ppl Ioc Ls1 Ls2 Ls3 Prf Ins Hkl Fou Ana\n";
    for (std::size_t i = 0; i < banks.size(); ++i) {
        out << "0 2 1 0 4 0 2 10 0 0 0\n";
    }
    for (std::size_t i = 0; i < banks.size(); ++i) {
        write_setup(out, banks[i], i + 1);
    }
    out << "!NCY Eps R_at R_an R_pr R_gl\n" << (codes.count() == 0 ? 1 : std::max(1, project.minimizer_max_iterations))
        << " 0.05 0.2 0.2 0.2 0.2\n";
    for (const auto& bank : banks) {
        out << (bank.tof() ? "! TOF-min <Step> TOF-max\n" : "! Thmin Step Thmax PSD Sent0\n")
            << bank.range_min << ' ' << bank.step << ' ' << bank.range_max << (bank.tof() ? "\n" : " 0 0\n");
    }
    for (std::size_t i = 0; i < banks.size(); ++i) {
        // FullProf reads this section in pattern order, with each bank's
        // background points immediately followed by its exclusion intervals.
        if (banks[i].nba >= 2) {
            write_background(out, banks[i], codes, i + 1);
        }
        const auto& exclusions = banks[i].model->excluded_regions;
        if (!exclusions.empty()) {
            out << "! Excluded regions (LowT HighT) for Pattern# " << i + 1 << '\n';
            const auto& axis = banks[i].data().axis();
            for (const auto& row : exclusions) {
                const auto first = row->first.get();
                const auto last = row->second.get();
                const auto channel = std::lower_bound(axis.begin(), axis.end(), first);
                // FullProf converts lower exclusion endpoints to a preceding bin.
                // An exact channel value can round down on its float32 axis.
                double start = first;
                double end = last;
                if (!banks[i].tof() && !banks[i].model->calculation_only) {
                    const auto locate_edge = [&](auto next) {
                        const auto included = *std::prev(next);
                        const auto following = next == axis.end() ? included + banks[i].step : *next;
                        return std::midpoint(included, following);
                    };
                    const auto after = std::upper_bound(axis.begin(), axis.end(), last);
                    if (channel < after) {
                        start = locate_edge(std::next(channel));
                        end = locate_edge(after);
                        // FullProf requires a nonempty coordinate interval even
                        // when both edges select a single measured channel.
                        if (start == end) {
                            start = std::midpoint(*channel, end);
                        }
                    } else {
                        start = end = axis.back() + 2. * banks[i].step;
                        end += banks[i].step;
                    }
                } else if (channel != axis.end() && *channel == first && std::next(channel) != axis.end()) {
                    start = std::midpoint(first, std::min(last, *std::next(channel)));
                }
                out << start << ' ' << end << '\n';
            }
        }
    }
    for (std::size_t i = 0; i < banks.size(); ++i) {
        write_neutron_lengths(out, banks[i].neutron_lengths, i + 1);
    }
    out << codes.count() << " !Number of refined parameters\n";
    for (std::size_t i = 0; i < banks.size(); ++i) {
        write_calibration(out, banks[i], codes, i + 1);
        if (banks[i].nba < 2) {
            write_background(out, banks[i], codes, i + 1);
        }
    }
    for (std::size_t i = 0; i < project.structures.size(); ++i) {
        write_phase(out, *project.structures[i], banks, i + 1, codes);
    }
    out << "! 2Th1/TOF1 2Th2/TOF2 Pattern to plot\n" << banks.front().data().axis().front() << ' '
        << banks.front().data().axis().back() << " 1\n";
    codes.check_written();
    out.close();
    for (const auto& bank : banks) {
        if (!bank.simulation()) {
            write_data(bank, folder);
        }
    }
}

}  // namespace

std::string export_fullprof_project(const Project& source, const std::string& directory, bool fixed) {
    const auto destination = fs::absolute(directory).lexically_normal();
    if (destination.filename().empty() || fs::exists(destination)) {
        unsupported("choose a new output directory");
    }
    const auto stage = detail::fresh_archive_directory_at("fullprof", destination.parent_path().string());
    try {
        const auto output = fs::path(stage) / "export";
        fs::create_directory(output);
        auto project = source;
        write_pcr(project, output, fixed);
        write_fit_results(project, output);
        detail::publish_fresh_project_path(output.string(), destination.string());
        remove_archive_directory(stage);
    } catch (...) {
        remove_archive_directory(stage);
        throw;
    }
    return (destination / "project.pcr").string();
}

}  // namespace edi
