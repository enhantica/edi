// SPDX-License-Identifier: BSD-3-Clause
#include "gsas_project.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <map>
#include <numbers>
#include <numeric>
#include <set>

#include "crysta/cell_symmetry.hpp"
#include "crysta/magnetic.hpp"
#include "crysta/symmetry.hpp"
#include "edi/io.hpp"
#include "edi/symmetry.hpp"
#include "gpx_project.hpp"
#include "gpx_records.hpp"
#include "import_symmetry.hpp"

namespace edi {
namespace {
using gpx::require;
using json::Value;
namespace fs = std::filesystem;
constexpr std::size_t max_gsas_bytes = 16U * 1024U * 1024U;

std::string lowercase_filename(const std::string& path) {
    auto filename = fs::path(path).filename().string();
    std::transform(filename.begin(), filename.end(), filename.begin(),
                   [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    return filename;
}

std::string bounded_file(const std::string& path) {
    require(fs::is_regular_file(path), "expected a regular file");
    const auto size = fs::file_size(path);
    require(size > 0 && size <= max_gsas_bytes, "unsupported GSAS-II project size");
    std::ifstream in(path, std::ios::binary);
    require(in.is_open(), "cannot read project file");
    std::string bytes(static_cast<std::size_t>(size), '\0');
    require(static_cast<bool>(in.read(bytes.data(), static_cast<std::streamsize>(size))) &&
                in.peek() == std::char_traits<char>::eof() && !in.bad(),
            "GSAS-II project file changed or could not be read");
    return bytes;
}

void shape(const Value& value, std::initializer_list<std::string_view> required,
           std::initializer_list<std::string_view> optional = {}) {
    std::set<std::string_view> remaining(required);
    std::set<std::string_view> optional_keys(optional);
    for (const auto& [key, field] : value.object("GSAS-II bundle object")) {
        if (remaining.erase(key) == 0 && optional_keys.erase(key) == 0) {
            gpx::refuse("unexpected or duplicate GSAS-II bundle field " + key);
        }
        static_cast<void>(field);
    }
    require(remaining.empty(),
            remaining.empty() ? ""
                              : "missing GSAS-II bundle field " + std::string(*remaining.begin()));
}

double finite(const Value& item, const char* name) {
    const double numeric = item.number(name);
    require(std::isfinite(numeric), std::string(name) + " must be finite");
    return numeric;
}

Parameter parameter(const Value& item, const char* name) {
    const auto& pair = item.array(name);
    require(pair.size() == 2, std::string("expected value and refine flag for ") + name);
    return {finite(pair[0], name), std::nullopt, pair[1].boolean(name)};
}

Parameter with_spec(Parameter value, const ParameterSpec& spec) {
    value.spec = &spec;
    return value;
}

void assign_parameter(Parameter& target, const Parameter& value) {
    target.value = value.value.get();
    target.free = value.free.get();
    target.uncertainty = value.uncertainty.get();
}

using SymmetryRow = std::array<int, 12>;

void set_shift(SymmetryRow& row, std::size_t axis, double fraction) {
    const double folded = fraction - std::floor(fraction);
    const auto ticks = std::lround(24 * folded);
    require(std::abs(folded - static_cast<double>(ticks) / 24) < 1e-6,
            "unsupported fractional GPX symmetry translation");
    row[axis + 9] = static_cast<int>(ticks % 24);
}

crysta::SpaceGroup standard_group(const Value& phase) {
    const auto& name = phase.at("space_group").string("space group");
    const auto& operators = phase.get("operators");
    if (operators.is_null()) {
        return crysta::resolve_space_group_by_hm(name);
    }
    std::set<SymmetryRow> source;
    for (const auto& op : operators.array("operators")) {
        const auto& values = op.array("operator");
        require(values.size() == 12, "invalid symmetry operator width");
        SymmetryRow row{};
        for (std::size_t i = 0; i < 9; ++i) {
            const double value = finite(values[i], "rotation entry");
            require(value == -1 || value == 0 || value == 1, "invalid symmetry rotation");
            row[i] = static_cast<int>(value);
        }
        for (std::size_t i = 0; i < 3; ++i)
            set_shift(row, i, finite(values[i + 9], "translation entry"));
        source.insert(row);
    }
    for (auto& candidate : crysta::space_groups_named(name)) {
        std::set<SymmetryRow> model;
        for (const auto& op : crysta::symmetry_operations(candidate)) {
            SymmetryRow row{};
            std::copy(op.rotation.begin(), op.rotation.end(), row.begin());
            for (std::size_t i = 0; i < 3; ++i) set_shift(row, i, op.translation[i]);
            model.insert(row);
        }
        if (model == source) return candidate;
    }
    gpx::refuse("No EasyDiffraction space-group setting matches GPX operators for " + name);
}

std::string edi_ion(const std::string& type) {
    const auto charge = type.find_first_of("+-");
    if (charge == std::string::npos || charge + 1 == type.size()) return type;
    return type.substr(0, charge) + type.substr(charge + 1) + type[charge];
}

void apply_magnetic_model(Structure& structure, const crysta::SpaceGroup& group,
                          const Value& model) {
    if (model.is_null()) return;
    shape(model, {"operations", "moments", "group"});
    const auto& rows = model.at("operations").array("magnetic operations");
    std::map<SymmetryRow, int> signs;
    for (const auto& op : rows) {
        if (const auto* text = std::get_if<std::string>(&op.data)) {
            const auto parsed = crysta::parse_magnetic_operation(*text);
            SymmetryRow row{};
            std::copy(parsed.rotation.begin(), parsed.rotation.end(), row.begin());
            for (std::size_t i = 0; i < 3; ++i) set_shift(row, i, parsed.translation[i]);
            require(signs.emplace(row, parsed.theta).second, "duplicated magnetic operator");
            continue;
        }
        const auto& values = op.array("magnetic operator");
        require(values.size() == 13, "invalid magnetic operator width");
        SymmetryRow row{};
        for (std::size_t i = 0; i < 9; ++i) {
            const double value = finite(values[i], "magnetic rotation");
            require(value == -1 || value == 0 || value == 1, "invalid magnetic rotation");
            row[i] = static_cast<int>(value);
        }
        for (std::size_t i = 0; i < 3; ++i)
            set_shift(row, i, finite(values[i + 9], "magnetic translation"));
        const double sign = finite(values.back(), "magnetic spin");
        require((sign == 1 || sign == -1) && signs.emplace(row, static_cast<int>(sign)).second,
                "invalid or duplicated magnetic operator");
    }

    MagneticDescription magnetism;
    magnetism.group.name_bns = model.at("group").string("magnetic group");
    const auto group_operations = crysta::symmetry_operations(group);
    require(group_operations.size() == signs.size(), "magnetic and nuclear symmetries differ");
    for (const auto& op : group_operations) {
        SymmetryRow row{};
        std::copy(op.rotation.begin(), op.rotation.end(), row.begin());
        for (std::size_t i = 0; i < 3; ++i) set_shift(row, i, op.translation[i]);
        const auto sign = signs.find(row);
        require(sign != signs.end(), "magnetic and nuclear spatial operators differ");
        magnetism.operations.emplace_back(std::to_string(op.id),
                                          op.xyz + (sign->second > 0 ? ",+1" : ",-1"));
    }
    structure.magnetic = std::move(magnetism);

    for (const auto& record : model.at("moments").array("magnetic moments")) {
        const auto& values = record.array("magnetic moment");
        require(values.size() == 6, "invalid magnetic moment width");
        const auto& id = values[0].string("magnetic atom");
        const auto site = std::find_if(structure.atom_sites.begin(), structure.atom_sites.end(),
                                       [&](const auto& item) { return item->id.value() == id; });
        require(site != structure.atom_sites.end(), "magnetic moment has no nuclear site");
        AtomSiteMoment moment;
        moment.id = id;
        auto axes = moment.parameters();
        const auto& flags = values[5].array("moment refine flags");
        require(flags.size() == 3, "invalid magnetic refine flags");
        for (std::size_t i = 0; i < axes.size(); ++i) {
            axes[i]->value = finite(values[i + 2], "moment component");
            axes[i]->free = flags[i].boolean("moment refine flag");
        }
        structure.atom_site_moment.push_back(moment);
        const auto type = edi_ion(values[1].string("magnetic ion"));
        const auto& element = (*site)->type_symbol.value();
        MagneticFormFactor factor;
        factor.id = element;
        factor.ion = type;
        const bool known = std::any_of(
            structure.magnetic_form_factors.begin(), structure.magnetic_form_factors.end(),
            [&](const auto& prior) {
                if (prior->id.value() != element) return false;
                require(prior->ion.value() == type, "one element has distinct magnetic ions");
                return true;
            });
        if (!known) structure.magnetic_form_factors.push_back(factor);
    }
    complete_atom_site_moments(structure);
}

Structure structure_model(const Value& phase, bool nuclear_neutron_only) {
    shape(phase, {"name", "space_group", "cell", "atoms"},
          {"operators", "cell_refine", "atom_flags", "magnetic"});
    Structure structure;
    structure.name = "phase";
    const auto group = standard_group(phase);
    structure.space_group.name_h_m = group.name_h_m;
    if (!phase.get("operators").is_null() && group.name_h_m != "P n m a")
        structure.space_group.coord_system_code = group.coord_system_code;
    const auto freedom = crysta::cell_freedom(group);
    const auto& cell_flag = phase.get("cell_refine");
    const auto& cell = phase.at("cell").array("cell");
    const auto parameters = structure.cell.parameters();
    require(cell.size() == parameters.size(), "expected six cell parameters");
    for (std::size_t i = 0; i < cell.size(); ++i) {
        const double value = finite(cell[i], "cell parameter");
        require(value > 0 && (i < 3 || value < 180), "invalid unit cell");
        parameters[i]->value = value;
        parameters[i]->free = !cell_flag.is_null() && cell_flag.boolean("cell refine") &&
                              freedom.follows[i] == static_cast<int>(i);
    }
    const auto& atoms = phase.at("atoms").array("atoms");
    require(!atoms.empty() && atoms.size() <= 10'000, "unsupported atom count");
    const auto& atom_flags = phase.get("atom_flags");
    if (!atom_flags.is_null())
        require(atom_flags.array("atom flags").size() == atoms.size(), "invalid atom flags");
    for (std::size_t index = 0; index < atoms.size(); ++index) {
        const auto& row = atoms[index].array("atom");
        require(row.size() == 7 || row.size() == 13,
                "expected isotropic or anisotropic atom fields");
        AtomSite site;
        const auto& id = row[0].string("atom id");
        const auto& element = row[1].string("atom element");
        require(!id.empty() && id.size() <= 64 &&
                    std::all_of(id.begin(), id.end(),
                                [](unsigned char ch) {
                                    return std::isalnum(ch) || ch == '_' || ch == '-' || ch == '.';
                                }),
                "invalid GPX atom id");
        require(!element.empty() && element.size() <= 8 &&
                    std::all_of(element.begin(), element.end(),
                                [](unsigned char ch) {
                                    return std::isalnum(ch) || ch == '+' || ch == '-';
                                }),
                "invalid GPX atom type");
        site.id = id;
        site.type_symbol = nuclear_neutron_only ? element.substr(0, element.find_first_of("+-"))
                                                : edi_ion(element);
        site.adp_type = row.size() == 7 ? "Uiso" : "Uani";
        const auto atomic = site.parameters();
        for (std::size_t i = 0; i < atomic.size(); ++i) {
            atomic[i]->value = finite(row[i + 2], "atom parameter");
        }
        require(site.occupancy.value.get() >= 0 && site.occupancy.value.get() <= 1 &&
                    site.adp_iso.value.get() >= 0,
                "GPX occupancy or Uiso is outside the EasyDiffraction model domain");
        site.wyckoff_letter = detail::inferred_wyckoff_letter(structure, site);
        if (!atom_flags.is_null()) {
            const auto& flags = atom_flags.array("atom flags")[index].string("atom flags");
            require(std::all_of(flags.begin(), flags.end(),
                                [](char flag) {
                                    return flag == 'X' || flag == 'U' || flag == 'F' ||
                                           flag == ' ';
                                }),
                    "unsupported GPX site refine flag " + flags);
            site.fract_x.free = site.fract_y.free = site.fract_z.free =
                flags.find('X') != std::string::npos;
            site.occupancy.free = flags.find('F') != std::string::npos;
            site.adp_iso.free = flags.find('U') != std::string::npos;
        }
        if (row.size() == 13) {
            AtomSiteAniso tensor;
            tensor.id = site.id.value();
            const auto components = tensor.parameters();
            for (std::size_t i = 0; i < components.size(); ++i) {
                components[i]->value = finite(row[i + 7], "anisotropic displacement");
                components[i]->free = site.adp_iso.free.get();
            }
            site.adp_iso.free = false;
            structure.atom_site_aniso.push_back(tensor);
        }
        structure.atom_sites.push_back(site);
    }
    if (!structure.atom_site_aniso.empty()) complete_atom_site_aniso(structure);
    apply_magnetic_model(structure, group, phase.get("magnetic"));
    return structure;
}

void cw_profile(BraggPdExperiment& experiment, const Value& instrument, const Value& sample,
                double size, double strain) {
    shape(instrument, {"Lam", "Zero", "U", "V", "W", "X", "Y", "SH/L"},
          {"Lam2", "ratio", "polarization", "azimuth"});
    const auto lam = parameter(instrument.at("Lam"), "Lam");
    const auto axial = parameter(instrument.at("SH/L"), "SH/L");
    require(lam.value.get() > 0 && !lam.free.get(), "expected positive fixed wavelength");
    require(!axial.free.get() || axial.value.get() >= 0.002,
            "unsupported free SH/L below the floor");
    experiment.instrument.setup_wavelength = with_spec(lam, spec::instrument_wavelength);
    experiment.instrument.calib_twotheta_offset =
        with_spec(parameter(instrument.at("Zero"), "Zero"), spec::instrument_twotheta_offset);
    const auto& radius = sample.get("radius_mm");
    if (!radius.is_null()) {
        const double mm = finite(radius, "goniometer radius");
        require(mm > 0, "invalid goniometer radius");
        const auto shift = [&](const char* key) {
            auto value = parameter(sample.at(key), key);
            value.value = value.value.get() * -0.18 / (std::numbers::pi * mm);
            return value;
        };
        experiment.instrument.calib_sample_displacement =
            with_spec(shift("displace_x"), spec::instrument_sample_displacement);
        experiment.instrument.calib_sample_transparency =
            with_spec(shift("displace_y"), spec::instrument_sample_transparency);
    }
    const auto& lam2 = instrument.get("Lam2");
    if (!lam2.is_null()) {
        experiment.instrument.setup_wavelength_2 =
            with_spec(parameter(lam2, "Lam2"), spec::instrument_wavelength_2);
        experiment.instrument.setup_wavelength_2_to_1_ratio = with_spec(
            parameter(instrument.at("ratio"), "ratio"), spec::instrument_wavelength_2_to_1_ratio);
    }
    if (!instrument.get("polarization").is_null()) {
        const auto azimuth = parameter(instrument.at("azimuth"), "azimuth");
        require(!azimuth.free.get(), "cannot refine GPX polarization azimuth in EasyDiffraction");
        const double angle = azimuth.value.get() * std::numbers::pi / 180;
        const double cosine = std::cos(angle) * std::cos(angle);
        const auto polarization = parameter(instrument.at("polarization"), "polarization");
        const double effective = cosine + (1 - 2 * cosine) * polarization.value.get();
        experiment.instrument.setup_polarization_coefficient =
            with_spec(Parameter(effective, std::nullopt, polarization.free.get()),
                      spec::instrument_polarization_coefficient);
        experiment.instrument.setup_monochromator_twotheta =
            with_spec(Parameter(0.), spec::instrument_monochromator_twotheta);
        experiment.xray_form_factor = "it1992";
    }
    auto& peak = experiment.peak;
    peak.type = "cwl-tch-pseudo-voigt-fcj";
    peak.cutoff_fwhm = 50.;
    const auto aperture = std::max(axial.value.get(), 0.002) / 2;
    peak.asym_fcj_1 = Parameter(aperture, std::nullopt, axial.free.get());
    peak.asym_fcj_2 = Parameter(aperture);

    // Gaussian variance, combined Lorentzian widths, and the axial apertures
    // have different units and names in the two profiles. See edi ADR-0096.
    const auto gaussian = [&](const char* name) {
        auto value = parameter(instrument.at(name), name);
        value.value = value.value.get() * (8 * std::numbers::ln2 / 10'000.);
        return value;
    };
    const auto lorentzian = [&](const char* name, double sample_width) {
        auto value = parameter(instrument.at(name), name);
        value.value = (value.value.get() + sample_width) / 100.;
        return value;
    };
    peak.broad_gauss_u = gaussian("U");
    peak.broad_gauss_v = gaussian("V");
    peak.broad_gauss_w = gaussian("W");
    peak.broad_lorentz_x = lorentzian("Y", 0.018 * strain / std::numbers::pi);
    peak.broad_lorentz_y = lorentzian("X", 1.8 * lam.value.get() / (std::numbers::pi * size));
    canonicalize_peak_specs(peak);
}

void tof_profile(BraggPdExperiment& experiment, const Value& instrument, double size,
                 double strain) {
    shape(instrument, {"Zero", "difC", "difA", "2-theta", "alpha", "beta-0", "beta-1", "sig-0",
                       "sig-1", "sig-2", "Z", "X", "Y"});
    const auto value = [&](const char* key) { return parameter(instrument.at(key), key); };
    const auto linear = value("difC");
    assign_parameter(experiment.instrument.calib_d_to_tof_offset, value("Zero"));
    assign_parameter(experiment.instrument.calib_d_to_tof_linear, linear);
    assign_parameter(experiment.instrument.calib_d_to_tof_quadratic, value("difA"));
    auto angle = value("2-theta");
    angle.value = std::abs(angle.value.get());
    assign_parameter(experiment.instrument.setup_twotheta_bank, angle);

    auto& peak = experiment.peak;
    peak.type = "tof-jorgensen-von-dreele";
    peak.cutoff_fwhm = 50.;
    assign_parameter(peak.rise_alpha_1, value("alpha"));
    assign_parameter(peak.decay_beta_0, value("beta-0"));
    assign_parameter(peak.decay_beta_1, value("beta-1"));
    assign_parameter(peak.broad_gauss_sigma_0, value("sig-0"));
    assign_parameter(peak.broad_gauss_sigma_1, value("sig-1"));
    assign_parameter(peak.broad_gauss_sigma_2, value("sig-2"));
    assign_parameter(peak.broad_lorentz_gamma_0, value("Z"));
    assign_parameter(peak.broad_lorentz_gamma_1, value("X"));
    assign_parameter(peak.broad_lorentz_gamma_2, value("Y"));
    peak.broad_lorentz_size.value = 1e-4 * linear.value.get() / size;
    peak.broad_lorentz_strain.value = 1e-6 * linear.value.get() * strain;
}

void background_model(BraggPdExperiment& experiment, const Value& background, double lo,
                      double hi) {
    shape(background, {"refine", "coefficients"}, {"basis"});
    const auto& coefficients = background.at("coefficients").array("background coefficients");
    require(!coefficients.empty() && coefficients.size() <= 24,
            "invalid Chebyshev background order");
    experiment.background_type = "chebyshev";
    experiment.background_x_min = lo;
    experiment.background_x_max = hi;
    const bool free = background.at("refine").boolean("background refine flag");
    std::vector<double> terms(coefficients.size());
    const auto& basis = background.get("basis");
    if (!basis.is_null() && basis.string("background basis") == "chebyschev") {
        // Expand powers of the normalised coordinate in the Chebyshev basis.
        std::vector<double> power(terms.size());
        power.at(0) = 1;
        for (std::size_t i = 0; i < terms.size(); ++i) {
            const auto coefficient = finite(coefficients[i], "background coefficient");
            for (std::size_t j = 0; j <= i; ++j) terms[j] += coefficient * power[j];
            if (i + 1 == terms.size()) break;
            std::vector<double> next(terms.size());
            next[1] = power[0];
            for (std::size_t j = 1; j <= i; ++j) {
                next[j - 1] += power[j] / 2;
                next[j + 1] += power[j] / 2;
            }
            power = std::move(next);
        }
    } else {
        require(basis.is_null() || basis.string("background basis") == "chebyschev-1",
                "unsupported GSAS-II background basis");
        for (std::size_t i = 0; i < terms.size(); ++i)
            terms[i] = finite(coefficients[i], "background coefficient");
    }
    for (std::size_t i = 0; i < terms.size(); ++i) {
        PolynomialTerm term;
        term.id = std::to_string(i + 1);
        term.order = static_cast<int>(i);
        assign_parameter(term.coef, {terms[i], std::nullopt, free});
        experiment.background_terms.push_back(term);
    }
}

std::pair<double, double> apply_fit_limits(BraggPdExperiment& experiment, const Value& limits,
                                           const std::vector<double>& x) {
    if (limits.is_null()) return {x.front(), x.back()};
    const auto& ranges = limits.array("fit limits");
    require(!ranges.empty(), "missing GPX active fit range");
    const auto range = [](const Value& input) {
        const auto& endpoints = input.array("fit region");
        require(endpoints.size() == 2, "expected two fit region endpoints");
        const auto low = finite(endpoints.front(), "low fit limit");
        const auto high = finite(endpoints.back(), "high fit limit");
        require(low < high, "invalid fit region");
        return std::pair{low, high};
    };
    const auto [low, high] = range(ranges.front());
    const auto first = std::lower_bound(x.begin(), x.end(), low);
    const auto end = std::upper_bound(x.begin(), x.end(), high);
    require(end - first >= 2, "GPX fit range contains fewer than two observations");
    if (first != x.begin())
        experiment.excluded_regions.push_back(
            ExcludedRegion{x.front(), std::midpoint(*(first - 1), *first)});
    if (end != x.end())
        experiment.excluded_regions.push_back(
            ExcludedRegion{std::midpoint(*(end - 1), *end), x.back()});
    for (std::size_t i = 1; i < ranges.size(); ++i) {
        const auto [start, finish] = range(ranges[i]);
        experiment.excluded_regions.push_back(ExcludedRegion{start, finish});
    }
    return {*first, *(end - 1)};
}

void set_observations(BraggPdExperiment& experiment, const Value& histogram) {
    const auto& rows = histogram.at("observations").array("observations");
    require(rows.size() >= 2 && rows.size() <= 200'000, "unsupported observation count");
    std::vector<double> x, intensity, sigma;
    std::vector<bool> disabled, masks;
    x.reserve(rows.size());
    intensity.reserve(rows.size());
    sigma.reserve(rows.size());
    const bool tof = experiment.effective_beam_mode() == BeamModeEnum::TIME_OF_FLIGHT;
    double previous = 0.;
    for (const auto& row : rows) {
        const auto& columns = row.array("observation");
        require(columns.size() == 3 || columns.size() == 4, "expected measurement columns");
        masks.push_back(columns.size() == 4 && columns.back().boolean("observation mask"));
        const double position = finite(columns[0], "two-theta");
        const double weight = finite(columns[2], "weight");
        require(position > previous && (tof || position < 180) && weight >= 0,
                "expected ascending physical observation coordinates and nonnegative weights");
        require(weight != 0 || !histogram.get("fit_limits").is_null(),
                "expected positive weights when no fit limits are supplied");
        previous = position;
        x.push_back(position);
        intensity.push_back(finite(columns[1], "observed intensity"));
        disabled.push_back(weight == 0);
        sigma.push_back(weight == 0 ? 1 : 1. / std::sqrt(weight));
    }
    const auto [low, high] = apply_fit_limits(experiment, histogram.get("fit_limits"), x);
    // Edi requires positive uncertainties. Keep zero-weight measurements on their
    // original grid, and give their excluded runs reversible region identifiers.
    const auto exclude = [&](const std::vector<bool>& omitted, const std::string& prefix) {
        for (std::size_t i = 0; i < x.size(); ++i) {
            if (!omitted[i]) continue;
            const std::size_t first = i;
            while (i + 1 < x.size() && omitted[i + 1]) ++i;
            const double start = first == 0 ? x.front() : std::midpoint(x[first - 1], x[first]);
            const double finish = i + 1 == x.size() ? x.back() : std::midpoint(x[i], x[i + 1]);
            ExcludedRegion excluded{start, finish};
            excluded.id = prefix + std::to_string(first + 1);
            experiment.excluded_regions.push_back(excluded);
        }
    };
    exclude(disabled, "gsas-zero-weight-");
    exclude(masks, "gsas-mask-");
    background_model(experiment, histogram.at("background"), low, high);
    PdDataBase observations;
    if (tof)
        observations.time_of_flight = std::move(x);
    else
        observations.two_theta = std::move(x);
    observations.intensity_meas = std::move(intensity);
    observations.intensity_meas_su = std::move(sigma);
    experiment.data = std::move(observations);
}

double cell_volume(const Structure& structure) {
    const auto& cell = structure.cell;
    const auto cosine = [](const Parameter& angle) {
        return std::cos(angle.value.get() * std::numbers::pi / 180);
    };
    const double a = cosine(cell.angle_alpha), b = cosine(cell.angle_beta),
                 c = cosine(cell.angle_gamma);
    return cell.length_a.value.get() * cell.length_b.value.get() * cell.length_c.value.get() *
           std::sqrt(1 - a * a - b * b - c * c + 2 * a * b * c);
}

BraggPdExperiment experiment_model(const Value& histogram,
                                   const std::vector<Structure>& structures) {
    shape(histogram, {"name", "type", "instrument", "sample", "background", "observations"},
          {"fit_limits", "links"});
    const auto& mode = histogram.at("type").string("histogram type");
    require(mode == "PNC" || mode == "PXC" || mode == "PNT", "unsupported powder mode");
    const bool tof = mode == "PNT";
    const auto& sample = histogram.at("sample");
    shape(sample, {"scale"},
          {"size_um", "microstrain_ppm", "phase_scale", "radius_mm", "displace_x", "displace_y",
           "geometry"});
    const auto& linked = histogram.get("links");
    const json::Array legacy{json::Object{{"phase_index", 0},
                                          {"phase_scale", sample.get("phase_scale")},
                                          {"size_um", sample.get("size_um")},
                                          {"microstrain_ppm", sample.get("microstrain_ppm")}}};
    const auto& links = linked.is_null() ? legacy : linked.array("phase links");
    require(links.size() <= structures.size(), "invalid GPX phase link count");
    const double size =
        links.empty() ? 1 : finite(links.front().at("size_um"), "crystallite size");
    const double strain =
        links.empty() ? 0 : finite(links.front().at("microstrain_ppm"), "microstrain");
    require(size > 0 && strain >= 0, "invalid crystallite size or microstrain");

    BraggPdExperiment experiment;
    experiment.name = "powder";
    experiment.experiment_type.sample_form = SampleFormEnum::POWDER;
    experiment.experiment_type.beam_mode =
        tof ? BeamModeEnum::TIME_OF_FLIGHT : BeamModeEnum::CONSTANT_WAVELENGTH;
    experiment.experiment_type.radiation_probe =
        mode == "PXC" ? RadiationProbeEnum::XRAY : RadiationProbeEnum::NEUTRON;
    experiment.experiment_type.scattering_type = ScatteringTypeEnum::BRAGG;
    if (mode != "PXC") experiment.neutron_scattering_length = "sears1992";
    const auto& instrument = histogram.at("instrument");
    if (tof)
        tof_profile(experiment, instrument, size, strain);
    else
        cw_profile(experiment, instrument, sample, size, strain);

    const auto refined = [](const Value& value) {
        return !value.is_null() && value.boolean("phase broadening refine flag");
    };
    if (links.size() == 1) {
        const bool size_refine = refined(links.front().get("size_refine"));
        const bool strain_refine = refined(links.front().get("strain_refine"));
        if (tof) {
            experiment.peak.broad_lorentz_size.free = size_refine;
            experiment.peak.broad_lorentz_strain.free = strain_refine;
        } else {
            auto& x = experiment.peak.broad_lorentz_x.value();
            auto& y = experiment.peak.broad_lorentz_y.value();
            x.free = x.free.get() || strain_refine;
            y.free = y.free.get() || size_refine;
        }
    }
    const auto scale = parameter(sample.at("scale"), "histogram scale");
    experiment.linked_structures.clear();
    for (const auto& entry : links) {
        shape(entry, {"phase_index", "phase_scale", "size_um", "microstrain_ppm"},
              {"size_refine", "strain_refine"});
        require(entry.at("size_um").number("size") == size &&
                    entry.at("microstrain_ppm").number("strain") == strain &&
                    (links.size() == 1 ||
                     (!refined(entry.get("size_refine")) && !refined(entry.get("strain_refine")))),
                "phase-specific GSAS-II broadening differs within this histogram");
        const double index = finite(entry.at("phase_index"), "phase index");
        require(index >= 0 && index < static_cast<double>(structures.size()) &&
                    std::floor(index) == index,
                "invalid GPX phase index");
        const auto& structure = structures[static_cast<std::size_t>(index)];
        const auto phase_scale = parameter(entry.at("phase_scale"), "phase scale");
        require(std::min(scale.value.get(), phase_scale.value.get()) >= 1e-12 &&
                    !(scale.free.get() && phase_scale.free.get()),
                "unsupported GSAS-II scale state");
        const double combined = scale.value.get() * phase_scale.value.get() /
                                (cell_volume(structure) * (tof ? 1 : 100));
        require(std::isfinite(combined) && combined > 0, "invalid converted scale");
        LinkedStructure link;
        link.structure_id = structure.name.value();
        assign_parameter(link.scale,
                         {combined, std::nullopt, scale.free.get() || phase_scale.free.get()});
        experiment.linked_structures.push_back(link);
    }
    set_observations(experiment, histogram);
    return experiment;
}

void tie_axial_apertures(Project& project, const BraggPdExperiment& experiment,
                         std::size_t index) {
    if (!experiment.peak.asym_fcj_1 || !experiment.peak.asym_fcj_1.value().free.get()) return;
    const auto prefix = "gsas_fcj_" + std::to_string(index) + "_";
    for (int aperture : {1, 2}) {
        ParameterAlias alias;
        const auto suffix = std::to_string(aperture);
        alias.id = prefix + suffix;
        alias.parameter_unique_name = experiment.name.value() + ".peak.asym_fcj_" + suffix;
        project.aliases.push_back(alias);
    }
    ParameterConstraint relation;
    relation.id = prefix + "2";
    relation.expression = prefix + "2 = " + prefix + "1";
    project.constraints.push_back(relation);
}

void apply_adp_ties(Project& project, const Value& ties) {
    if (ties.is_null()) return;
    std::size_t ordinal = 0;
    for (const auto& group : ties.array("ADP ties")) {
        const auto& targets = group.array("ADP tie");
        require(targets.size() >= 2, "invalid GSAS-II ADP tie");
        std::string leader;
        Parameter* initial = nullptr;
        for (const auto& target : targets) {
            const auto& pair = target.array("ADP target");
            require(pair.size() == 2, "invalid GSAS-II ADP target");
            const auto index = finite(pair[0], "phase index");
            require(index >= 0 && index < static_cast<double>(project.structures.size()) &&
                        std::floor(index) == index,
                    "invalid GSAS-II ADP phase");
            const auto& structure = project.structures[static_cast<std::size_t>(index)];
            const auto& label = pair[1].string("ADP atom");
            const auto atom =
                std::find_if(structure->atom_sites.begin(), structure->atom_sites.end(),
                             [&](const auto& site) { return site->id.value() == label; });
            require(atom != structure->atom_sites.end() && (*atom)->adp_type == "Uiso",
                    "missing isotropic site for GSAS-II ADP tie");
            ParameterAlias alias;
            const auto id = "gsas_adp_" + std::to_string(++ordinal);
            alias.id = id;
            alias.parameter_unique_name =
                structure->name.value() + ".atom_site." + label + ".adp_iso";
            project.aliases.push_back(alias);
            if (leader.empty()) {
                leader = id;
                initial = &(*atom)->adp_iso;
            } else {
                require(std::abs((*atom)->adp_iso.value.get() - initial->value.get()) < 1e-8,
                        "GSAS-II ADP tie has inconsistent site values");
                initial->free = initial->free.get() || (*atom)->adp_iso.free.get();
                (*atom)->adp_iso.free = false;
                ParameterConstraint relation;
                relation.id = id;
                relation.expression = id + " = " + leader;
                project.constraints.push_back(relation);
            }
        }
    }
}

Project convert(const Value& bundle) {
    const auto& format = bundle.at("format").string("format");
    const bool legacy = format == "gsas-ii-pnc-v1";
    const json::Array one_phase{legacy ? bundle.at("phase") : Value{}};
    const json::Array one_histogram{legacy ? bundle.at("histogram") : Value{}};
    if (legacy) {
        shape(bundle, {"format", "source", "phase", "histogram"}, {"reference"});
    } else {
        require(format == "gsas-ii-powder-v2", "unsupported GSAS-II bundle format");
        shape(bundle, {"format", "source", "phases", "histograms"}, {"reference", "adp_ties"});
    }
    const auto& phases = legacy ? one_phase : bundle.at("phases").array("phases");
    const auto& histograms = legacy ? one_histogram : bundle.at("histograms").array("histograms");
    require(
        !phases.empty() && phases.size() <= 128 && !histograms.empty() && histograms.size() <= 128,
        "invalid GSAS-II phase or histogram count");
    const bool xray =
        std::any_of(histograms.begin(), histograms.end(), [](const Value& histogram) {
            return histogram.at("type").string("histogram mode") == "PXC";
        });
    const auto& source = bundle.at("source");
    shape(source, {"filename"}, {"sha256", "last_saved_using"});
    const auto& filename = source.at("filename").string("source filename");
    Project project = empty_project("gsas_ii_import", "Imported from GSAS-II: " + filename);
    project.metadata.title = phases.front().at("name").string("phase name") + " / " +
                             histograms.front().at("name").string("histogram name");
    project.fitting_mode = histograms.size() == 1 ? "single" : "joint";
    std::vector<Structure> structures;
    for (const auto& phase : phases) {
        auto structure = structure_model(phase, !xray);
        if (phases.size() > 1) structure.name = "phase-" + std::to_string(structures.size() + 1);
        add_loaded_structure(project, structure);
        structures.push_back(std::move(structure));
    }
    for (std::size_t i = 0; i < histograms.size(); ++i) {
        auto experiment = experiment_model(histograms[i], structures);
        if (histograms.size() > 1) experiment.name = "powder-" + std::to_string(i + 1);
        tie_axial_apertures(project, experiment, i + 1);
        add_loaded_experiment(project, std::move(experiment));
    }
    apply_adp_ties(project, bundle.get("adp_ties"));
    return project;
}

}  // namespace

bool is_gsas_project_path(const std::string& path) {
    const auto filename = lowercase_filename(path);
    return filename.ends_with(".gpx") || filename.ends_with(".gsas.json");
}

Project load_gsas_project(const std::string& path) {
    return reading_file(path, [&] {
        try {
            const auto bytes = bounded_file(path);
            if (lowercase_filename(path).ends_with(".gpx")) {
                return convert(gpx::decode_project(bytes, fs::path(path).filename().string()));
            }
            return convert(json::parse(bytes));
        } catch (const std::exception& error) {
            throw IoError("Cannot import GSAS-II project '" + path + "': " + error.what());
        }
    });
}
}  // namespace edi
