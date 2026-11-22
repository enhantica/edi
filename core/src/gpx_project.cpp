// SPDX-License-Identifier: BSD-3-Clause
#include "gpx_project.hpp"

#include <algorithm>
#include <array>
#include <cmath>

#include "gpx_records.hpp"

namespace edi::gpx {
namespace {
using json::Array;
using json::Object;
constexpr std::array cwl_names{"Zero", "U", "V", "W", "X", "Y", "SH/L"};
constexpr std::array tof_names{"Zero",   "difC",  "difA",  "2-theta", "alpha", "beta-0",
                               "beta-1", "sig-0", "sig-1", "sig-2",   "X",     "Y"};

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

bool restraints_active(const Records& record, Id input) {
    const auto& phases = record.dictionary(input).pairs;
    for (std::size_t i = 1; i < phases.size(); i += 2) {
        const auto& categories = record.dictionary(phases[i]).pairs;
        for (std::size_t j = 1; j < categories.size(); j += 2) {
            const auto category = categories[j];
            if (record.find(category, "Use") && !active(record, category, "Use")) continue;
            const auto& values = record.dictionary(category).pairs;
            for (std::size_t k = 0; k < values.size(); k += 2) {
                const auto& key = record.text(values[k]);
                if (key != "Use" && key != "Range" && key != "wtFactor" && key != "Coeff" &&
                    record.truth(values[k + 1]))
                    return true;
            }
        }
    }
    return false;
}

Array numbers(const Records& record, Id value) {
    const auto& array = record.array(value);
    std::size_t count = 1;
    for (const auto axis : array.shape) count *= axis;
    require(count <= 512, "unexpected GPX symmetry array size");
    Array result;
    for (std::size_t i = 0; i < count; ++i) result.emplace_back(record.element(array, i));
    return result;
}

Array symmetry_operators(const Records& record, Id group, bool magnetic = false) {
    require(!active(record, group, "SGFixed") && !active(record, group, "SGGray"),
            "unsupported nonstandard GPX symmetry operations");
    const bool inversion = active(record, group, "SGInv");
    const auto centres = numbers(record, record.field(group, "SGCen"));
    const auto& operators = record.sequence(record.field(group, "SGOps"));
    require(!centres.empty() && centres.size() % 3 == 0 && centres.size() <= 12 &&
                !operators.empty() && operators.size() <= 192,
            "invalid GPX space-group operators");
    Array expanded;
    Array spins;
    if (magnetic) {
        const auto token = record.field(group, "SpnFlp");
        if (const auto* rows = std::get_if<Sequence>(&record.value(token))) {
            for (const auto item : *rows) spins.emplace_back(record.number(item));
        } else {
            spins = numbers(record, token);
        }
    }
    const std::size_t symmetry_count = operators.size() * (inversion ? 2 : 1);
    require(!magnetic || spins.size() == symmetry_count * centres.size() / 3,
            "unsupported magnetic anti-translation or spin layout");
    for (std::size_t index = 0; index < operators.size(); ++index) {
        const auto& op = record.sequence(operators[index]);
        require(op.size() == 2, "invalid GPX symmetry operator");
        const auto rotation = numbers(record, op[0]);
        const auto translation = numbers(record, op[1]);
        require(rotation.size() == 9 && translation.size() == 3,
                "invalid GPX symmetry operator dimensions");
        for (std::size_t centre = 0; centre < centres.size(); centre += 3) {
            for (const auto sign : {1., -1.}) {
                if (sign < 0 && !inversion) break;
                Array row;
                for (const auto& value : rotation)
                    row.emplace_back(sign * value.number("rotation"));
                for (std::size_t axis = 0; axis < 3; ++axis)
                    row.emplace_back(sign * translation[axis].number("translation") +
                                     centres[centre + axis].number("centering"));
                if (magnetic) {
                    const auto spin = spins
                                          .at(centre / 3 * symmetry_count + index +
                                              (sign == 1. ? 0 : operators.size()))
                                          .number("spin");
                    require(spin == -1 || spin == 1, "invalid magnetic spin");
                    row.emplace_back(spin);
                }
                expanded.emplace_back(std::move(row));
            }
        }
    }
    return expanded;
}

Object phase_model(const Records& record, Id phase, const std::string& name) {
    const auto general = record.field(phase, "General");
    const auto rb = record.find(phase, "RBModels");
    if (rb) {
        const auto& rows = record.dictionary(*rb).pairs;
        for (std::size_t i = 1; i < rows.size(); i += 2)
            require(!record.truth(rows[i]), "active GSAS-II rigid body");
    }
    require(record.text(record.field(general, "Type")) == "nuclear" &&
                !active(record, general, "Modulated") && !active(record, general, "doPawley") &&
                !active(record, general, "HydIds") &&
                !active(record, record.field(general, "SH Texture"), "Order"),
            "unsupported phase type, texture, modulation, rigid bodies or Pawley intensities");
    const auto group = record.field(general, "SGData");
    const auto& isotopes = record.dictionary(record.field(general, "Isotope")).pairs;
    for (std::size_t i = 1; i < isotopes.size(); i += 2) {
        require(record.text(isotopes[i]) == "Nat. Abund.", "expected natural isotope abundance");
    }
    const auto& cell = record.sequence(record.field(general, "Cell"));
    require(cell.size() == 8, "expected GPX cell values");
    Array dimensions;
    for (std::size_t i = 1; i < 7; ++i) dimensions.emplace_back(record.number(cell[i]));

    const auto& pointers = record.sequence(record.field(general, "AtomPtrs"));
    require(pointers.size() == 4 && record.number(pointers[0]) == 3 &&
                record.number(pointers[1]) == 1 && record.number(pointers[3]) == 9,
            "unsupported GPX atom record layout");
    Array atoms;
    Array flags;
    for (const auto id : record.sequence(record.field(phase, "Atoms"))) {
        const auto& row = record.sequence(id);
        require(row.size() >= 11, "incomplete GPX atom site");
        const auto& displacement = record.text(row[9]);
        require(displacement == "I" || (displacement == "A" && row.size() >= 17),
                "unsupported GPX atomic displacement");
        flags.emplace_back(record.text(row[2]));
        Array atom{record.text(row[0]),
                   record.text(row[1]),
                   record.number(row[3]),
                   record.number(row[4]),
                   record.number(row[5]),
                   record.number(row[6]),
                   displacement == "I" ? record.number(row[10]) : 0.};
        if (displacement == "A") {
            for (std::size_t i = 11; i < 17; ++i) atom.emplace_back(record.number(row[i]));
        }
        atoms.emplace_back(std::move(atom));
    }
    return {{"name", name},
            {"space_group", record.text(record.field(group, "SpGrp"))},
            {"operators", symmetry_operators(record, group)},
            {"cell_refine", record.truth(cell[0])},
            {"atom_flags", std::move(flags)},
            {"cell", std::move(dimensions)},
            {"atoms", std::move(atoms)}};
}

Object magnetic_model(const Records& record, Id phase, const Object& standard) {
    const auto nuclear = json::Value(standard);
    const auto general = record.field(phase, "General");
    require(!active(record, general, "Modulated") && !active(record, general, "doPawley") &&
                !active(record, record.field(general, "SH Texture"), "Order"),
            "unsupported magnetic modulation or texture");
    const auto group = record.field(general, "SGData");
    require(nuclear.at("space_group").string("nuclear space group") ==
                record.text(record.field(group, "SpGrp")),
            "magnetic cell setting differs");
    const auto& cell = record.sequence(record.field(general, "Cell"));
    require(cell.size() == 8, "missing magnetic cell");
    for (std::size_t i = 0; i < 6; ++i) {
        require(std::abs(record.number(cell[i + 1]) -
                         nuclear.at("cell").array("nuclear cell")[i].number("cell")) < 1e-8,
                "independent magnetic and nuclear cells are not representable in EasyDiffraction");
    }
    const auto& pointers = record.sequence(record.field(general, "AtomPtrs"));
    require(pointers.size() == 4 && record.number(pointers[0]) == 3 &&
                record.number(pointers[1]) == 1 && record.number(pointers[3]) == 12,
            "unsupported magnetic atom layout");
    Array moments;
    for (const auto id : record.sequence(record.field(phase, "Atoms"))) {
        const auto& row = record.sequence(id);
        require(row.size() >= 14 && record.text(row[12]) == "I",
                "unsupported magnetic site displacement");
        const auto& name = record.text(row[0]);
        const auto& type = record.text(row[1]);
        const auto& sites = nuclear.at("atoms").array("nuclear atoms");
        const auto nucleus = std::find_if(sites.begin(), sites.end(), [&](const auto& candidate) {
            const auto& atom = candidate.array("nuclear atom");
            return atom[0].string("atom name") == name && atom[1].string("atom type") == type;
        });
        require(nucleus != sites.end(), "magnetic site has no matching nuclear site");
        const auto& atom = nucleus->array("nuclear site");
        require(atom.size() == 7, "magnetic site requires a matching isotropic nuclear site");
        for (std::size_t i = 0; i < 4; ++i) {
            require(
                std::abs(record.number(row[3 + i]) - atom[2 + i].number("atom location")) < 1e-8,
                "independent magnetic site coordinates are not representable");
        }
        require(std::abs(record.number(row[13]) - atom[6].number("isotropic displacement")) < 1e-8,
                "independent magnetic site displacement is not representable");
        const auto& flags = record.text(row[2]);
        require(flags.find('X') == std::string::npos && flags.find('F') == std::string::npos,
                "independent magnetic site refinement is not representable");
        moments.emplace_back(Array{name, type, record.number(row[7]), record.number(row[8]),
                                   record.number(row[9]),
                                   Array(3, flags.find('M') != std::string::npos)});
    }
    const auto lande = record.find(general, "Lande g");
    if (lande) {
        for (const auto factor : record.sequence(*lande))
            require(std::abs(record.number(factor) - 2.) < 1e-8, "unsupported magnetic g factor");
    }
    return {{"operations", symmetry_operators(record, group, true)},
            {"moments", std::move(moments)},
            {"group", record.text(record.field(group, "MagSpGrp"))}};
}

Array parameter(const Records& record, Id dictionary, const char* key,
                std::size_t value_index = 0) {
    const auto field = record.field(dictionary, key);
    if (const auto* data = std::get_if<gpx::Array>(&record.value(field))) {
        require(data->shape.size() == 1 && data->shape.front() >= value_index + 2,
                std::string("invalid GPX parameter ") + key);
        return {record.element(*data, value_index), record.element(*data, value_index + 1) != 0};
    }
    const auto& values = record.sequence(field);
    require(values.size() >= value_index + 2, std::string("invalid GPX parameter ") + key);
    return {record.number(values[value_index]), record.truth(values[value_index + 1])};
}

void fixed(const Records& record, Id dictionary, const char* key, double neutral = 0.,
           std::size_t index = 0) {
    const auto pair = parameter(record, dictionary, key, index);
    require(pair[0].number(key) == neutral && !pair[1].boolean(key),
            std::string("unsupported active GPX parameter ") + key);
}

Array broadening(const Records& record, Id link, const char* key) {
    const auto& spec = record.sequence(record.field(link, key));
    require(spec.size() >= 3 && record.text(spec[0]) == "isotropic",
            std::string(key) + " must be isotropic");
    const auto& values = record.sequence(spec[1]);
    const auto& flags = record.sequence(spec[2]);
    require(values.size() == 3 && flags.size() == 3 && record.number(values[2]) == 1. &&
                !record.truth(flags[1]) && !record.truth(flags[2]),
            std::string(key) + " must be entirely Lorentzian");
    return {record.number(values[0]), record.truth(flags[0])};
}

Object phase_link(const Records& record, Id link) {
    require(!active(record, link, "LeBail"), "unsupported Le Bail intensities");
    if (const auto layer = record.find(link, "Layer Disp")) {
        if (!record.none(*layer)) fixed(record, link, "Layer Disp");
    }
    if (record.find(link, "Extinction")) fixed(record, link, "Extinction");
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
    const auto size = broadening(record, link, "Size");
    const auto strain_terms = broadening(record, link, "Mustrain");
    return {{"size_um", size[0]},
            {"size_refine", size[1]},
            {"microstrain_ppm", strain_terms[0]},
            {"strain_refine", strain_terms[1]},
            {"phase_scale", parameter(record, link, "Scale")}};
}

Object sample_model(const Records& record, Id sample) {
    const auto& geometry = record.text(record.field(sample, "Type"));
    require(geometry == "Debye-Scherrer" || geometry == "Bragg-Brentano",
            "unsupported GPX sample geometry");
    for (const auto key : {"Absorption", "Shift", "Transparency", "SurfRoughA", "SurfRoughB"}) {
        if (record.find(sample, key)) fixed(record, sample, key);
    }
    return {{"scale", parameter(record, sample, "Scale")},
            {"radius_mm", record.number(record.field(sample, "Gonio. radius"))},
            {"displace_x", parameter(record, sample, "DisplaceX")},
            {"displace_y", parameter(record, sample, "DisplaceY")},
            {"geometry", geometry}};
}

Object instrument_model(const Records& record, Id input, std::string& mode) {
    const auto& parts = record.sequence(input);
    require(parts.size() == 2 && record.dictionary(parts[1]).pairs.empty(),
            "unsupported auxiliary instrument settings");
    const auto instrument = parts[0];
    const auto& type = record.sequence(record.field(instrument, "Type"));
    require(type.size() >= 2, "missing GPX instrument mode");
    mode = record.text(type[1]);
    require(mode == "PNC" || mode == "PXC" || mode == "PNT",
            "unsupported GPX instrument type " + mode);
    const auto& settings = record.dictionary(instrument).pairs;
    Object output;
    const auto approved = [&](const std::string& name) {
        return name == "Type" || name == "Source" || name == "Bank" || name == "Azimuth" ||
               name == "Polariz." || name == "Z";
    };
    for (std::size_t i = 0; i < settings.size(); i += 2) {
        const auto& name = record.text(settings[i]);
        if (mode == "PNT") {
            if (std::find(tof_names.begin(), tof_names.end(), name) != tof_names.end()) continue;
            if (name == "fltPath" || approved(name)) continue;
            require(name == "difB" || name == "sig-q" || name == "beta-q",
                    "unsupported TOF instrument parameter " + name);
        } else {
            if (std::find(cwl_names.begin(), cwl_names.end(), name) != cwl_names.end()) continue;
            require(approved(name) || name == "Lam" || name == "Lam1" || name == "Lam2" ||
                        name == "I(L2)/I(L1)",
                    "unsupported CW instrument parameter " + name);
        }
    }
    if (mode == "PNT") {
        for (const auto key : {"difB", "sig-q", "beta-q"}) {
            if (record.find(instrument, key)) fixed(record, instrument, key, 0., 1);
        }
        for (const auto key : tof_names) {
            if (key == std::string_view("difA") && !record.find(instrument, key)) {
                output.emplace_back(key, Array{0., false});
            } else {
                output.emplace_back(key, parameter(record, instrument, key, 1));
            }
        }
        output.emplace_back("Z", record.find(instrument, "Z")
                                     ? parameter(record, instrument, "Z", 1)
                                     : Array{0., false});
    } else {
        if (record.find(instrument, "Z")) fixed(record, instrument, "Z", 0., 1);
        for (const auto key : cwl_names)
            output.emplace_back(key, parameter(record, instrument, key, 1));
        const bool doublet = record.find(instrument, "Lam2").has_value();
        output.emplace_back("Lam", parameter(record, instrument, doublet ? "Lam1" : "Lam", 1));
        if (doublet) {
            require(mode == "PXC", "unsupported neutron wavelength doublet");
            output.emplace_back("Lam2", parameter(record, instrument, "Lam2", 1));
            output.emplace_back("ratio", parameter(record, instrument, "I(L2)/I(L1)", 1));
        }
        if (mode == "PXC") {
            output.emplace_back("polarization", parameter(record, instrument, "Polariz.", 1));
            output.emplace_back("azimuth", parameter(record, instrument, "Azimuth", 1));
        }
    }
    return output;
}

Object background_model(const Records& record, Id input) {
    const auto& background = record.sequence(input);
    require(background.size() == 2, "unexpected GPX background layout");
    const auto& terms = record.sequence(background[0]);
    const auto extra = background[1];
    const auto& kind = record.text(terms.at(0));
    require(terms.size() > 3 && (kind == "chebyschev" || kind == "chebyschev-1") &&
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
    return {{"refine", record.truth(terms[1])},
            {"coefficients", std::move(coefficients)},
            {"basis", kind}};
}

Array observations(const Records& record, Id input) {
    const auto& data = record.sequence(input);
    require(data.size() >= 2 && !active(record, data[0], "Dummy") &&
                record.number(record.field(data[0], "wtFactor")) == 1.,
            "expected measured observations and unit histogram weight");
    Array output;
    if (const auto* table = std::get_if<gpx::Array>(&record.value(data[1]))) {
        require(table->shape.size() == 2 && table->shape[0] >= 3 && table->shape[1] >= 2 &&
                    table->shape[1] <= 200'000,
                "inconsistent GPX masked observation table");
        const auto count = table->shape[1];
        output.reserve(count);
        for (std::size_t i = 0; i < count; ++i) {
            Array observed{record.element(*table, i), record.element(*table, count + i),
                           record.element(*table, 2 * count + i)};
            if (record.masked(*table, i) || record.masked(*table, count + i) ||
                record.masked(*table, 2 * count + i))
                observed.emplace_back(true);
            output.emplace_back(std::move(observed));
        }
    } else {
        const auto& columns = record.sequence(data[1]);
        require(columns.size() >= 3, "missing GPX observation columns");
        const auto& x = record.array(columns[0]);
        const auto& y = record.array(columns[1]);
        const auto& w = record.array(columns[2]);
        require(x.shape.size() == 1 && x.shape.front() >= 2 && x.shape.front() <= 200'000 &&
                    y.shape == x.shape && w.shape == x.shape,
                "inconsistent GPX observation columns");
        output.reserve(x.shape.front());
        for (std::size_t i = 0; i < x.shape.front(); ++i) {
            Array observed{record.element(x, i), record.element(y, i), record.element(w, i)};
            if (record.masked(x, i) || record.masked(y, i) || record.masked(w, i))
                observed.emplace_back(true);
            output.emplace_back(std::move(observed));
        }
    }
    return output;
}
void require_paired_constraints(const Records& record, Id input, Id nuclear_phase,
                                Id magnetic_phase, Id histogram, Object& magnetic_model) {
    const auto random_id = [&](Id object, const char* field) {
        const auto* value = std::get_if<std::int64_t>(&record.value(record.field(object, field)));
        require(value != nullptr, std::string("invalid paired phase identifier ") + field);
        return *value;
    };
    const auto nuclear_id = random_id(nuclear_phase, "ranId");
    const auto magnetic_id = random_id(magnetic_phase, "ranId");
    const auto histogram_id = random_id(histogram, "ranId");
    const auto label = [&](Id phase, std::int64_t identifier) {
        for (const auto atom : record.sequence(record.field(phase, "Atoms"))) {
            const auto& fields = record.sequence(atom);
            const auto* key = std::get_if<std::int64_t>(&record.value(fields.back()));
            if (key && *key == identifier) return record.text(fields[0]);
        }
        refuse("unresolved paired constraint site");
    };
    const auto& groups = record.dictionary(input).pairs;
    for (std::size_t i = 0; i < groups.size(); i += 2) {
        const auto& scope = record.text(groups[i]);
        if (scope.starts_with('_') || !record.truth(groups[i + 1])) continue;
        require(scope == "HAP" || scope == "Phase", "unsupported paired magnetic constraint");
        for (const auto id : record.sequence(groups[i + 1])) {
            const auto& terms = record.sequence(id);
            if (scope == "Phase" && terms.size() == 4 && record.text(terms.back()) == "h") {
                const auto& term = record.sequence(terms.front());
                require(term.size() == 2, "invalid held magnetic variable");
                const auto* variable = std::get_if<ObjectState>(&record.value(term[1]));
                require(variable && variable->type == Factory::Variable && variable->state,
                        "invalid held magnetic variable");
                const auto state = *variable->state;
                const auto& name = record.text(record.field(state, "name"));
                const auto axis =
                    name == "AMx" ? 0 : (name == "AMy" ? 1 : (name == "AMz" ? 2 : -1));
                const auto atom_id =
                    std::get_if<std::int64_t>(&record.value(record.field(state, "atom")));
                const auto phase =
                    std::get_if<std::int64_t>(&record.value(record.field(state, "phase")));
                const auto expected = std::get_if<std::int64_t>(
                    &record.value(record.field(magnetic_phase, "ranId")));
                require(axis >= 0 && atom_id && phase && expected && *phase == *expected,
                        "unsupported held magnetic variable");
                const auto& atoms = record.sequence(record.field(magnetic_phase, "Atoms"));
                auto& moments = std::get<Array>(
                    std::find_if(magnetic_model.begin(), magnetic_model.end(),
                                 [](const auto& entry) { return entry.first == "moments"; })
                        ->second.data);
                bool found = false;
                for (std::size_t k = 0; k < atoms.size(); ++k) {
                    const auto& site = record.sequence(atoms[k]);
                    const auto* ref = std::get_if<std::int64_t>(&record.value(site.back()));
                    if (!ref || *ref != *atom_id) continue;
                    auto& flags = std::get<Array>(std::get<Array>(moments[k].data)[5].data);
                    flags[static_cast<std::size_t>(axis)] = false;
                    found = true;
                    break;
                }
                require(found, "unresolved held magnetic variable");
                continue;
            }
            require(terms.size() == 5 && record.text(terms.back()) == "e",
                    "unsupported magnetic hold or parameter constraint");
            std::string_view name;
            std::array<Id, 2> states{};
            for (std::size_t j = 0; j < 2; ++j) {
                const auto& term = record.sequence(terms[j]);
                require(term.size() == 2 && record.number(term[0]) == 1.,
                        "unsupported magnetic constraint multiplier");
                const auto* variable = std::get_if<ObjectState>(&record.value(term[1]));
                require(variable && variable->type == Factory::Variable && variable->state,
                        "invalid magnetic constraint variable");
                states[j] = *variable->state;
                const auto& item = record.text(record.field(states[j], "name"));
                if (j == 0) name = item;
                require(item == name, "paired constraint mixes parameters");
            }
            const bool hap = name == "Scale" || name == "Size;i" || name == "Mustrain;i";
            const bool atomic = name == "Afrac" || name == "AUiso" || name == "AU11" ||
                                name == "AU22" || name == "AU33" || name == "AU12" ||
                                name == "AU13" || name == "AU23";
            const bool cell =
                name.size() == 2 && name[0] == 'A' && name[1] >= '0' && name[1] <= '5';
            require(scope == "HAP" ? hap : (atomic || cell), "unsupported paired constraint");
            const auto first = random_id(states[0], "phase");
            const auto second = random_id(states[1], "phase");
            require((first == nuclear_id && second == magnetic_id) ||
                        (first == magnetic_id && second == nuclear_id),
                    "paired constraint does not tie the two source phases");
            if (hap) {
                require(random_id(states[0], "histogram") == histogram_id &&
                            random_id(states[1], "histogram") == histogram_id,
                        "paired constraint has a different histogram");
            } else if (atomic) {
                require(label(first == nuclear_id ? nuclear_phase : magnetic_phase,
                              random_id(states[0], "atom")) ==
                            label(second == nuclear_id ? nuclear_phase : magnetic_phase,
                                  random_id(states[1], "atom")),
                        "paired constraint refers to distinct sites");
            }
        }
    }
}

Array adp_ties(const Records& record, Id constraints, const std::vector<Id>& phases) {
    const auto& groups = record.dictionary(constraints).pairs;
    Array result;
    for (std::size_t i = 0; i < groups.size(); i += 2) {
        const auto& scope = record.text(groups[i]);
        if (scope.starts_with('_') || !record.truth(groups[i + 1])) continue;
        require(scope == "Phase", "unsupported GSAS-II non-phase constraints");
        for (const auto row : record.sequence(groups[i + 1])) {
            const auto& terms = record.sequence(row);
            require(terms.size() >= 5 && record.text(terms.back()) == "e",
                    "unsupported GSAS-II phase constraint type");
            Array group;
            for (std::size_t j = 0; j + 3 < terms.size(); ++j) {
                const auto& term = record.sequence(terms[j]);
                require(term.size() == 2 && record.number(term[0]) == 1.,
                        "unsupported GSAS-II constraint multiplier");
                const auto* variable = std::get_if<ObjectState>(&record.value(term[1]));
                require(variable && variable->type == Factory::Variable && variable->state,
                        "invalid GSAS-II constraint variable");
                const auto state = *variable->state;
                require(record.text(record.field(state, "name")) == "AUiso" &&
                            record.none(record.field(state, "histogram")),
                        "unsupported GSAS-II phase constraint variable");
                const auto& phase_id = record.value(record.field(state, "phase"));
                const auto& atom_id = record.value(record.field(state, "atom"));
                const auto* pid = std::get_if<std::int64_t>(&phase_id);
                const auto* aid = std::get_if<std::int64_t>(&atom_id);
                require(pid && aid, "invalid GSAS-II atom constraint identifiers");
                bool found = false;
                for (std::size_t k = 0; k < phases.size(); ++k) {
                    const auto* candidate =
                        std::get_if<std::int64_t>(&record.value(record.field(phases[k], "ranId")));
                    if (!candidate || *candidate != *pid) continue;
                    for (const auto atom : record.sequence(record.field(phases[k], "Atoms"))) {
                        const auto& fields = record.sequence(atom);
                        const auto* num = std::get_if<std::int64_t>(&record.value(fields.back()));
                        if (num && *num == *aid) {
                            require(record.text(fields.at(9)) == "I",
                                    "cannot tie a derived isotropic ADP");
                            group.emplace_back(
                                Array{static_cast<double>(k), record.text(fields[0])});
                            found = true;
                            break;
                        }
                    }
                    break;
                }
                require(found, "unresolved GSAS-II atom constraint variable");
            }
            result.emplace_back(std::move(group));
        }
    }
    return result;
}

Array fit_limits(const Records& record, Id limits_id) {
    const auto& limits = record.sequence(limits_id);
    require(limits.size() >= 2, "missing GPX fit limits");
    Array result;
    for (std::size_t i = 1; i < limits.size(); ++i) {
        const auto& range = record.sequence(limits[i]);
        require(range.size() == 2, "invalid GPX fit limits");
        result.emplace_back(Array{record.number(range[0]), record.number(range[1])});
    }
    return result;
}

}  // namespace

json::Value decode_project(std::string_view bytes, const std::string& filename) {
    Records record(bytes);
    const auto roots = record.read();
    const Sequence* phases = nullptr;
    std::vector<std::pair<std::string, const Sequence*>> powders;
    std::optional<Id> controls, constraints;
    for (const auto id : roots) {
        const auto& members = record.sequence(id);
        require(!members.empty(), "empty GPX top-level entry");
        const auto& head = record.sequence(members.front());
        require(head.size() == 2, "invalid GPX top-level entry");
        const auto& name = record.text(head[0]);
        if (name == "Phases") {
            require(!phases, "duplicate GPX phases section");
            phases = &members;
        } else if (name.starts_with("PWDR ")) {
            powders.emplace_back(name, &members);
        } else if (name == "Controls") {
            require(!controls && !active(record, head[1], "Seq Data"),
                    "unsupported GPX sequential setup");
            controls = head[1];
        } else if (name == "Constraints") {
            require(!constraints, "duplicate GPX constraints");
            constraints = head[1];
        } else if (name == "Restraints") {
            require(!restraints_active(record, head[1]), "unsupported active GPX Restraints");
        } else {
            require(name == "Notebook" || name == "Covariance" || name == "Rigid bodies",
                    "unsupported GPX tree entry " + name);
        }
    }
    require(phases && phases->size() > 1 && !powders.empty() && controls,
            "expected at least one phase and powder histogram");
    require(phases->size() <= 129 && powders.size() <= 128, "too many GPX phases or banks");

    json::Array structures, experiments;
    std::vector<Id> phase_ids;
    std::optional<Id> magnetic;
    for (std::size_t i = 1; i < phases->size(); ++i) {
        const auto& phase = record.sequence((*phases)[i]);
        require(phase.size() == 2, "invalid GPX phase entry");
        const auto general = record.field(phase[1], "General");
        if (record.text(record.field(general, "Type")) == "magnetic") {
            require(!magnetic, "only one paired magnetic phase is supported");
            magnetic = phase[1];
        } else {
            structures.emplace_back(phase_model(record, phase[1], record.text(phase[0])));
            phase_ids.push_back(phase[1]);
        }
    }
    if (magnetic) {
        require(structures.size() == 1 && powders.size() == 1,
                "unsupported GPX magnetic phase arrangement");
        auto& phase = std::get<Object>(structures.front().data);
        auto model = magnetic_model(record, *magnetic, phase);
        if (constraints) {
            const auto& [name, members] = powders.front();
            const auto histogram = record.sequence(entry(record, *members, name)).at(0);
            require_paired_constraints(record, *constraints, phase_ids.front(), *magnetic,
                                       histogram, model);
        }
        phase.emplace_back("magnetic", std::move(model));
    }
    for (const auto& [name, members] : powders) {
        std::string mode;
        auto instrument =
            instrument_model(record, entry(record, *members, "Instrument Parameters"), mode);
        auto sample = sample_model(record, entry(record, *members, "Sample Parameters"));
        json::Array links;
        for (std::size_t i = 0; i < phase_ids.size(); ++i) {
            const auto histograms = record.field(phase_ids[i], "Histograms");
            const auto link = record.find(histograms, name);
            if (!link || (record.find(*link, "Use") && !active(record, *link, "Use"))) continue;
            auto model = phase_link(record, *link);
            if (magnetic) {
                require(mode == "PNC", "expected paired magnetic powder CW data");
                const auto other = record.field(record.field(*magnetic, "Histograms"), name);
                require(!record.find(other, "Use") || active(record, other, "Use"),
                        "inactive paired GPX magnetic link");
                require(json::write(model) == json::write(phase_link(record, other)),
                        "magnetic phase has independent scale or peak widths");
            }
            model.emplace_back("phase_index", static_cast<double>(i));
            links.emplace_back(std::move(model));
        }

        experiments.emplace_back(
            Object{{"name", name},
                   {"type", mode},
                   {"instrument", std::move(instrument)},
                   {"sample", std::move(sample)},
                   {"links", std::move(links)},
                   {"background", background_model(record, entry(record, *members, "Background"))},
                   {"observations", observations(record, entry(record, *members, name))},
                   {"fit_limits", fit_limits(record, entry(record, *members, "Limits"))}});
    }
    return Object{{"format", "gsas-ii-powder-v2"},
                  {"source", Object{{"filename", filename}}},
                  {"phases", std::move(structures)},
                  {"histograms", std::move(experiments)},
                  {"adp_ties", constraints && !magnetic ? adp_ties(record, *constraints, phase_ids)
                                                        : json::Array{}}};
}
}  // namespace edi::gpx
