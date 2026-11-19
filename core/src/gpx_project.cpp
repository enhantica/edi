// SPDX-License-Identifier: BSD-3-Clause
#include "gpx_project.hpp"

#include <algorithm>
#include <array>

#include "gpx_records.hpp"

namespace edi::gpx {
namespace {
using json::Array;
using json::Object;
constexpr std::array instrument_names{"Lam", "Zero", "U", "V", "W", "X", "Y", "SH/L"};

Id entry(const Records& record, const Sequence& items, std::string_view label) {
    std::optional<Id> result;
    for (const auto item : items) {
        const auto& pair = record.sequence(item);
        require(pair.size() == 2, "invalid GPX tree entry");
        if (record.text(pair[0]) != label) continue;
        require(!result, "duplicate GPX tree entry " + std::string(label));
        result = pair[1];
    }
    if (!result) refuse("missing GPX tree entry " + std::string(label));
    return *result;
}

bool active(const Records& record, Id id, std::string_view key) {
    const auto value = record.find(id, key);
    return value && record.truth(*value);
}

bool any(const Records& record, const Sequence& values) {
    return std::any_of(values.begin(), values.end(),
                       [&](Id index) { return record.truth(index); });
}

bool entries_active(const Records& record, Id id, bool skip_private = false) {
    const auto& pairs = record.dictionary(id).pairs;
    for (std::size_t i = 0; i < pairs.size(); i += 2) {
        if (skip_private && record.text(pairs[i]).starts_with('_')) continue;
        if (record.truth(pairs[i + 1])) return true;
    }
    return false;
}

template <std::size_t N>
bool array_matches(const Records& record, Id id, const std::array<double, N>& expected) {
    const auto& values = record.array(id);
    std::size_t count = 1;
    for (const auto axis : values.shape) count *= axis;
    if (count != N) return false;
    for (std::size_t index = 0; index < N; ++index) {
        if (record.element(values, index) != expected[index]) return false;
    }
    return true;
}

void require_pnma(const Records& record, Id group) {
    require(record.text(record.field(group, "SpGrp")) == "P n m a" &&
                active(record, group, "SGInv") && !active(record, group, "SGFixed") &&
                !active(record, group, "SGGray") &&
                array_matches(record, record.field(group, "SGCen"), std::array{0., 0., 0.}),
            "only the standard P n m a space group is supported");
    // GSAS-II stores the four non-inverted operators and adds the inversion.
    constexpr std::array translations{std::array{0., 0., 0.}, std::array{0.5, 0.5, 0.5},
                                      std::array{0., 0.5, 0.}, std::array{0.5, 0., 0.5}};
    const auto& operators = record.sequence(record.field(group, "SGOps"));
    require(operators.size() == translations.size(), "unexpected P n m a operator count");
    for (std::size_t i = 0; i < operators.size(); ++i) {
        const auto& op = record.sequence(operators[i]);
        const auto x = (i & 1U) == 0 ? 1. : -1.;
        const auto y = (i & 2U) == 0 ? 1. : -1.;
        require(op.size() == 2 &&
                    array_matches(record, op[0], std::array{x, 0., 0., 0., y, 0., 0., 0., 1.}) &&
                    array_matches(record, op[1], translations[i]),
                "unexpected P n m a symmetry operator");
    }
}

Object phase_model(const Records& record, Id phase, const std::string& name) {
    const auto general = record.field(phase, "General");
    require(record.text(record.field(general, "Type")) == "nuclear" &&
                !active(record, general, "Modulated") && !active(record, general, "doPawley") &&
                !active(record, general, "HydIds") && !active(record, phase, "RBModels") &&
                !active(record, record.field(general, "SH Texture"), "Order"),
            "unsupported phase type, texture, modulation, rigid bodies or Pawley intensities");
    require_pnma(record, record.field(general, "SGData"));
    const auto& isotopes = record.dictionary(record.field(general, "Isotope")).pairs;
    for (std::size_t i = 1; i < isotopes.size(); i += 2) {
        require(record.text(isotopes[i]) == "Nat. Abund.", "expected natural isotope abundance");
    }
    const auto& cell = record.sequence(record.field(general, "Cell"));
    require(cell.size() == 8 && !record.truth(cell[0]), "the P n m a unit cell must be fixed");
    Array dimensions;
    for (std::size_t i = 1; i < 7; ++i) dimensions.emplace_back(record.number(cell[i]));

    const auto& pointers = record.sequence(record.field(general, "AtomPtrs"));
    require(pointers.size() == 4 && record.number(pointers[0]) == 3 &&
                record.number(pointers[1]) == 1 && record.number(pointers[3]) == 9,
            "unsupported GPX atom record layout");
    Array atoms;
    for (const auto id : record.sequence(record.field(phase, "Atoms"))) {
        const auto& row = record.sequence(id);
        require(row.size() >= 11 && record.text(row[2]).empty() && record.text(row[9]) == "I",
                "only fixed sites with isotropic displacement are supported");
        atoms.emplace_back(Array{record.text(row[0]), record.text(row[1]), record.number(row[3]),
                                 record.number(row[4]), record.number(row[5]),
                                 record.number(row[6]), record.number(row[10])});
    }
    return {{"name", name},
            {"space_group", "P n m a"},
            {"cell", std::move(dimensions)},
            {"atoms", std::move(atoms)}};
}

Array parameter(const Records& record, Id dictionary, const char* key,
                std::size_t value_index = 0) {
    const auto& values = record.sequence(record.field(dictionary, key));
    require(values.size() >= value_index + 2, std::string("invalid GPX parameter ") + key);
    return {record.number(values[value_index]), record.truth(values[value_index + 1])};
}

void fixed(const Records& record, Id dictionary, const char* key, double neutral = 0.,
           std::size_t index = 0) {
    const auto pair = parameter(record, dictionary, key, index);
    require(pair[0].number(key) == neutral && !pair[1].boolean(key),
            std::string("unsupported active GPX parameter ") + key);
}

double broadening(const Records& record, Id link, const char* key) {
    const auto& spec = record.sequence(record.field(link, key));
    require(spec.size() >= 3 && record.text(spec[0]) == "isotropic" &&
                !any(record, record.sequence(spec[2])),
            std::string(key) + " must be fixed and isotropic");
    const auto& values = record.sequence(spec[1]);
    require(values.size() == 3 && record.number(values[2]) == 1.,
            std::string(key) + " must be entirely Lorentzian");
    return record.number(values[0]);
}

Object sample_model(const Records& record, Id phase, Id sample, const std::string& histogram) {
    require(record.text(record.field(sample, "Type")) == "Debye-Scherrer",
            "only Debye-Scherrer sample geometry is supported");
    const auto links = record.field(phase, "Histograms");
    require(record.dictionary(links).pairs.size() == 2, "expected one phase-to-histogram link");
    const auto link = record.field(links, histogram);
    require(active(record, link, "Use") && !active(record, link, "LeBail") &&
                !active(record, link, "Layer Disp"),
            "expected an active Rietveld phase link");
    for (const auto key : {"Absorption", "DisplaceX", "DisplaceY"}) fixed(record, sample, key);
    fixed(record, link, "Extinction");
    const auto babinet = record.field(link, "Babinet");
    fixed(record, babinet, "BabA");
    fixed(record, babinet, "BabU");
    const auto& orientation = record.sequence(record.field(link, "Pref.Ori."));
    require(orientation.size() >= 3 && record.text(orientation[0]) == "MD" &&
                record.number(orientation[1]) == 1. && !record.truth(orientation[2]),
            "preferred orientation must be neutral");
    const auto& strain = record.sequence(record.field(link, "HStrain"));
    require(strain.size() == 2 && !any(record, record.sequence(strain[0])) &&
                !any(record, record.sequence(strain[1])),
            "hydrostatic strain must be inactive");
    return {{"size_um", broadening(record, link, "Size")},
            {"microstrain_ppm", broadening(record, link, "Mustrain")},
            {"scale", parameter(record, sample, "Scale")},
            {"phase_scale", parameter(record, link, "Scale")}};
}

Object instrument_model(const Records& record, Id input) {
    const auto& parts = record.sequence(input);
    require(parts.size() == 2 && record.dictionary(parts[1]).pairs.empty(),
            "unsupported auxiliary instrument settings");
    const auto instrument = parts[0];
    const auto& type = record.sequence(record.field(instrument, "Type"));
    require(type.size() >= 2 && record.text(type[1]) == "PNC", "expected one PNC instrument");
    const auto& settings = record.dictionary(instrument).pairs;
    for (std::size_t i = 0; i < settings.size(); i += 2) {
        const auto& name = record.text(settings[i]);
        require(std::find(instrument_names.begin(), instrument_names.end(), name) !=
                        instrument_names.end() ||
                    name == "Type" || name == "Z" || name == "Polariz." || name == "Azimuth" ||
                    name == "Source" || name == "Bank",
                "unsupported instrument parameter " + name);
    }
    fixed(record, instrument, "Z", 0., 1);
    Object output;
    for (const auto key : instrument_names) {
        output.emplace_back(key, parameter(record, instrument, key, 1));
    }
    return output;
}

Object background_model(const Records& record, Id input) {
    const auto& background = record.sequence(input);
    require(background.size() == 2, "unexpected GPX background layout");
    const auto& terms = record.sequence(background[0]);
    const auto extra = background[1];
    require(terms.size() > 3 && record.text(terms[0]) == "chebyschev-1" &&
                record.number(terms[2]) == static_cast<double>(terms.size() - 3),
            "expected GSAS-II's chebyschev-1 background");
    for (const auto key : {"nDebye", "nPeaks", "debyeTerms", "peaksList", "fixback"}) {
        require(!active(record, extra, key),
                std::string("unsupported additional background: ") + key);
    }
    if (const auto link = record.find(extra, "background PWDR")) {
        const auto& values = record.sequence(*link);
        require(!values.empty() && !record.truth(values[0]),
                "unsupported linked powder background");
    }
    Array coefficients;
    for (std::size_t i = 3; i < terms.size(); ++i)
        coefficients.emplace_back(record.number(terms[i]));
    return {{"refine", record.truth(terms[1])}, {"coefficients", std::move(coefficients)}};
}

Array observations(const Records& record, Id input, Id limits_id) {
    const auto& data = record.sequence(input);
    require(data.size() >= 2 && !active(record, data[0], "Dummy") &&
                record.number(record.field(data[0], "wtFactor")) == 1.,
            "expected measured observations and unit histogram weight");
    const auto& columns = record.sequence(data[1]);
    require(columns.size() >= 3, "missing GPX observation columns");
    const auto& x = record.array(columns[0]);
    const auto& y = record.array(columns[1]);
    const auto& w = record.array(columns[2]);
    require(x.shape.size() == 1 && x.shape.front() >= 2 && x.shape.front() <= 200'000 &&
                y.shape == x.shape && w.shape == x.shape,
            "inconsistent GPX observation columns");
    const auto& limits = record.sequence(limits_id);
    require(limits.size() == 2, "unsupported GPX exclusion regions");
    const auto& fit = record.sequence(limits[1]);
    require(fit.size() == 2 && record.number(fit[0]) == record.element(x, 0) &&
                record.number(fit[1]) == record.element(x, x.shape.front() - 1),
            "only the full measured GPX range is supported");
    Array output;
    output.reserve(x.shape.front());
    for (std::size_t i = 0; i < x.shape.front(); ++i) {
        output.emplace_back(
            Array{record.element(x, i), record.element(y, i), record.element(w, i)});
    }
    return output;
}
}  // namespace

json::Value decode_project(std::string_view bytes, const std::string& filename) {
    Records record(bytes);
    const auto roots = record.read();
    const Sequence* phases = nullptr;
    const Sequence* powder = nullptr;
    std::string histogram;
    std::optional<Id> controls;
    for (const auto id : roots) {
        const auto& members = record.sequence(id);
        require(!members.empty(), "empty GPX top-level entry");
        const auto& head = record.sequence(members.front());
        require(head.size() == 2, "invalid GPX top-level entry");
        const auto& name = record.text(head[0]);
        if (name == "Phases") {
            require(!phases && members.size() == 2, "expected exactly one GPX phase");
            phases = &members;
        } else if (name.starts_with("PWDR ")) {
            require(!powder, "expected exactly one GPX powder histogram");
            powder = &members;
            histogram = name;
        } else if (name == "Controls") {
            require(!controls && !active(record, head[1], "Seq Data"), "unsupported GPX controls");
            controls = head[1];
        } else if (name == "Constraints" || name == "Restraints") {
            require(!entries_active(record, head[1], name == "Constraints"),
                    "unsupported active GPX " + name);
        } else {
            require(name == "Notebook" || name == "Covariance" || name == "Rigid bodies",
                    "unsupported GPX tree entry " + name);
        }
    }
    require(phases && powder && controls, "expected one phase and one powder histogram");
    const auto& phase_entry = record.sequence(phases->at(1));
    require(phase_entry.size() == 2, "invalid GPX phase entry");
    const auto phase = phase_entry[1];
    return Object{
        {"format", "gsas-ii-pnc-v1"},
        {"source", Object{{"filename", filename}}},
        {"phase", phase_model(record, phase, record.text(phase_entry[0]))},
        {"histogram",
         Object{{"name", histogram},
                {"type", "PNC"},
                {"instrument",
                 instrument_model(record, entry(record, *powder, "Instrument Parameters"))},
                {"sample", sample_model(record, phase, entry(record, *powder, "Sample Parameters"),
                                        histogram)},
                {"background", background_model(record, entry(record, *powder, "Background"))},
                {"observations", observations(record, entry(record, *powder, histogram),
                                              entry(record, *powder, "Limits"))}}}};
}
}  // namespace edi::gpx
