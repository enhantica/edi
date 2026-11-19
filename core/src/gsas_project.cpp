// SPDX-License-Identifier: BSD-3-Clause
#include "gsas_project.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <numbers>
#include <set>

#include "edi/io.hpp"
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

void assign_parameter(Parameter& target, const Parameter& value) {
    target.value = value.value.get();
    target.free = value.free.get();
    target.uncertainty = value.uncertainty.get();
}

Structure structure_model(const Value& phase) {
    shape(phase, {"name", "space_group", "cell", "atoms"});
    require(phase.at("space_group").string("space group") == "P n m a",
            "only the standard P n m a space group is supported");
    Structure structure;
    structure.name = "phase";
    structure.space_group.name_h_m = "P n m a";
    const auto& cell = phase.at("cell").array("cell");
    const auto parameters = structure.cell.parameters();
    require(cell.size() == parameters.size(), "expected six cell parameters");
    for (std::size_t i = 0; i < cell.size(); ++i) {
        const double value = finite(cell[i], "cell parameter");
        require(i < 3 ? value > 0 : value == 90, "invalid orthorhombic cell");
        parameters[i]->value = value;
    }
    const auto& atoms = phase.at("atoms").array("atoms");
    require(!atoms.empty() && atoms.size() <= 10'000, "unsupported atom count");
    for (const auto& atom : atoms) {
        const auto& row = atom.array("atom");
        require(row.size() == 7, "expected seven atom fields");
        AtomSite site;
        const auto& id = row[0].string("atom id");
        const auto& element = row[1].string("atom element");
        require(!id.empty() && id.size() <= 64 &&
                    std::all_of(id.begin(), id.end(),
                                [](unsigned char ch) {
                                    return std::isalnum(ch) || ch == '_' || ch == '-' || ch == '.';
                                }),
                "invalid GPX atom id");
        require(element == "Pb" || element == "S" || element == "O",
                "unsupported atom element " + element);
        site.id = id;
        site.type_symbol = element;
        site.adp_type = "Uiso";
        const auto atomic = site.parameters();
        for (std::size_t i = 0; i < atomic.size(); ++i) {
            atomic[i]->value = finite(row[i + 2], "atom parameter");
        }
        require(site.occupancy.value.get() >= 0 && site.occupancy.value.get() <= 1 &&
                    site.adp_iso.value.get() >= 0,
                "invalid occupancy or isotropic displacement");
        site.wyckoff_letter = detail::inferred_wyckoff_letter(structure, site);
        structure.atom_sites.push_back(site);
    }
    return structure;
}

void profile_model(BraggPdExperiment& experiment, const Value& instrument, const Value& sample) {
    shape(instrument, {"Lam", "Zero", "U", "V", "W", "X", "Y", "SH/L"});
    const auto lam = parameter(instrument.at("Lam"), "Lam");
    const auto axial = parameter(instrument.at("SH/L"), "SH/L");
    require(lam.value.get() > 0 && !lam.free.get() && !axial.free.get(),
            "expected positive fixed wavelength and fixed SH/L");
    experiment.instrument.setup_wavelength = lam;
    experiment.instrument.calib_twotheta_offset = parameter(instrument.at("Zero"), "Zero");
    auto& peak = experiment.peak;
    peak.type = "cwl-tch-pseudo-voigt-fcj";
    peak.cutoff_fwhm = 50.;
    const auto aperture = std::max(axial.value.get(), 0.002) / 2;
    peak.asym_fcj_1 = Parameter(aperture);
    peak.asym_fcj_2 = Parameter(aperture);

    // Gaussian variance, combined Lorentzian widths, and the axial apertures
    // have different units and names in the two profiles. See edi ADR-0096.
    const auto gaussian = [&](const char* name) {
        auto value = parameter(instrument.at(name), name);
        value.value = value.value.get() * (8 * std::numbers::ln2 / 10'000.);
        return value;
    };
    const double size = finite(sample.at("size_um"), "crystallite size");
    const double strain = finite(sample.at("microstrain_ppm"), "microstrain");
    require(size > 0 && strain >= 0, "invalid crystallite size or microstrain");
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
}

void background_model(BraggPdExperiment& experiment, const Value& background, double lo,
                      double hi) {
    shape(background, {"refine", "coefficients"});
    const auto& coefficients = background.at("coefficients").array("background coefficients");
    require(!coefficients.empty() && coefficients.size() <= 24,
            "invalid Chebyshev background order");
    experiment.background_type = "chebyshev";
    experiment.background_x_min = lo;
    experiment.background_x_max = hi;
    const bool free = background.at("refine").boolean("background refine flag");
    for (std::size_t i = 0; i < coefficients.size(); ++i) {
        PolynomialTerm term;
        term.id = std::to_string(i + 1);
        term.order = static_cast<int>(i);
        assign_parameter(term.coef,
                         {finite(coefficients[i], "background coefficient"), std::nullopt, free});
        experiment.background_terms.push_back(term);
    }
}

void set_observations(BraggPdExperiment& experiment, const Value& histogram) {
    const auto& rows = histogram.at("observations").array("observations");
    require(rows.size() >= 2 && rows.size() <= 200'000, "unsupported observation count");
    std::vector<double> x, intensity, sigma;
    x.reserve(rows.size());
    intensity.reserve(rows.size());
    sigma.reserve(rows.size());
    double previous = 0.;
    for (const auto& row : rows) {
        const auto& columns = row.array("observation");
        require(columns.size() == 3, "expected two-theta, intensity and inverse variance");
        const double position = finite(columns[0], "two-theta");
        const double weight = finite(columns[2], "weight");
        require(position > previous && position < 180 && weight > 0,
                "expected ascending two-theta in (0, 180) and positive weights");
        previous = position;
        x.push_back(position);
        intensity.push_back(finite(columns[1], "observed intensity"));
        sigma.push_back(1. / std::sqrt(weight));
    }
    background_model(experiment, histogram.at("background"), x.front(), x.back());
    PdDataBase observations;
    observations.two_theta = std::move(x);
    observations.intensity_meas = std::move(intensity);
    observations.intensity_meas_su = std::move(sigma);
    experiment.data = std::move(observations);
}

BraggPdExperiment experiment_model(const Value& histogram, const Structure& structure) {
    shape(histogram, {"name", "type", "instrument", "sample", "background", "observations"});
    require(histogram.at("type").string("histogram type") == "PNC", "expected a PNC histogram");
    const auto& sample = histogram.at("sample");
    shape(sample, {"size_um", "microstrain_ppm", "scale", "phase_scale"});
    BraggPdExperiment experiment;
    experiment.name = "powder";
    experiment.experiment_type.sample_form = SampleFormEnum::POWDER;
    experiment.experiment_type.beam_mode = BeamModeEnum::CONSTANT_WAVELENGTH;
    experiment.experiment_type.radiation_probe = RadiationProbeEnum::NEUTRON;
    experiment.experiment_type.scattering_type = ScatteringTypeEnum::BRAGG;
    experiment.neutron_scattering_length = "sears1992";
    profile_model(experiment, histogram.at("instrument"), sample);

    const auto scale = parameter(sample.at("scale"), "histogram scale");
    const auto phase_scale = parameter(sample.at("phase_scale"), "phase scale");
    require(std::min(scale.value.get(), phase_scale.value.get()) >= 1e-12 &&
                !(scale.free.get() && phase_scale.free.get()),
            "unsupported GSAS-II scale state");
    const auto& cell = structure.cell;
    const double volume =
        cell.length_a.value.get() * cell.length_b.value.get() * cell.length_c.value.get();
    const double combined = scale.value.get() * phase_scale.value.get() / (100 * volume);
    require(std::isfinite(combined) && combined > 0, "invalid converted scale");
    LinkedStructure link;
    link.structure_id = structure.name.value();
    assign_parameter(link.scale,
                     {combined, std::nullopt, scale.free.get() || phase_scale.free.get()});
    experiment.linked_structures.clear();
    experiment.linked_structures.push_back(link);
    set_observations(experiment, histogram);
    return experiment;
}

Project convert(const Value& bundle) {
    shape(bundle, {"format", "source", "phase", "histogram"}, {"reference"});
    require(bundle.at("format").string("format") == "gsas-ii-pnc-v1",
            "unsupported GSAS-II bundle format");
    const auto& phase = bundle.at("phase");
    const auto& histogram = bundle.at("histogram");
    auto structure = structure_model(phase);
    auto experiment = experiment_model(histogram, structure);
    const auto& source = bundle.at("source");
    shape(source, {"filename"}, {"sha256", "last_saved_using"});
    const auto& filename = source.at("filename").string("source filename");
    Project project = empty_project("gsas_ii_import", "Imported from GSAS-II: " + filename);
    project.metadata.title = phase.at("name").string("phase name") + " / " +
                             histogram.at("name").string("histogram name");
    project.fitting_mode = "single";
    add_loaded_structure(project, std::move(structure));
    add_loaded_experiment(project, std::move(experiment));
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
