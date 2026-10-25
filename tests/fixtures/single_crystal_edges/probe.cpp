#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <memory>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

template <class T>
std::string word(const T& item) {
    if constexpr (requires { item.value(); })
        return item.value();
    else if constexpr (requires { item.get(); })
        return item.get();
    else
        return item;
}

#ifdef EDGE_EDI
#include "edi/categories.hpp"
#include "edi/edit.hpp"
#include "edi/io.hpp"
namespace api = edi;
using Project = edi::Project;
using Parameter = edi::Parameter;
auto& experiment(Project& p, std::size_t i = 0) { return *p.experiments[i]; }
auto load(const std::string& path) {
    return edi::load_project(
        path, [](const std::string& note) { std::cerr << "note " << note << '\n'; });
}
void calculate(Project& p) { p.calculate(); }
auto fit(Project& p) { return p.fitting_mode == "joint" ? p.fit_joint() : p.fit(); }
void save(Project& p, const std::string& path) { edi::save_project_as(p, path); }
double value(const Parameter& p) { return p.value.get(); }
bool is_free(const Parameter& p) { return p.free.get(); }
void number(Parameter& p, double x) { edi::assign_value(p, x); }
void freedom(Parameter& p, bool x) { p.free = x; }
auto start(const Parameter& p) { return p.start_value.get(); }
Parameter& parameter(Project& p, const std::string& name) {
    for (const auto& slot : edi::named_slots(p))
        if (slot.unique_name == name) return *slot.parameter;
    throw std::invalid_argument("No parameter " + name);
}
std::string name(const edi::ExperimentBase& e) { return word(e.name); }
std::string link_name(const edi::LinkedStructure& link) { return word(link.structure_id); }
auto& link_at(edi::ExperimentBase& e, std::size_t i) { return *e.linked_structures[i]; }
auto& rows(edi::ExperimentBase& e) { return *e.reflections; }
void type(edi::ExperimentBase& e, const std::string& token) { e.extinction.type = token; }
void distribution(edi::ExperimentBase& e, const std::string& token) {
    e.extinction.mosaic_distribution = token;
}
auto intensities(edi::ExperimentBase& e) { return e.reflections->intensity_calc.values(); }
void apply(Project& p) { edi::complete_relations(p); }
int state(Project& p) { return experiment(p).computed_current() ? 1 : 2; }
int peek_state(Project& p) { return state(p); }
void ensure(Project& p) { experiment(p).ensure_computed(); }
#else
#include "crysta/analysis.hpp"
#include "crysta/constraints.hpp"
#include "crysta/single_crystal.hpp"
namespace api = crysta;
using Project = crysta::Project;
using Parameter = crysta::Parameter;
auto& experiment(Project& p, std::size_t i = 0) { return p.experiments[i]; }
auto load(const std::string& path) { return crysta::load_project(path); }
void calculate(Project& p) { crysta::calculate_project(p); }
auto fit(Project& p) { return crysta::fit_project(p); }
void save(Project& p, const std::string& path) { crysta::save_project(p, path); }
double value(const Parameter& p) { return p.value(); }
bool is_free(const Parameter& p) { return p.free(); }
void number(Parameter& p, double x) { p.set_value(x); }
void freedom(Parameter& p, bool x) { p.set_free(x); }
auto start(const Parameter& p) { return p.start_value(); }
Parameter& parameter(Project& p, const std::string& name) {
    return crysta::resolve_unique_name(p, name);
}
std::string name(const crysta::ExperimentBase& e) { return word(e.name); }
std::string link_name(const crysta::LinkedStructure& link) { return word(link.structure_id); }
auto& link_at(crysta::ExperimentBase& e, std::size_t i) { return e.linked_structures[i]; }
auto& rows(crysta::ExperimentBase& e) { return *e.reflections.get(); }
void type(crysta::ExperimentBase& e, const std::string& token) { e.extinction_type = token; }
void distribution(crysta::ExperimentBase& e, const std::string& token) {
    e.extinction_model = token;
}
auto intensities(crysta::ExperimentBase& e) {
    return e.computed().refln().intensity_calc.values();
}
void apply(Project& p) { crysta::apply_relations(p); }
int state(Project& p) {
    return static_cast<int>(crysta::computed_state(p, experiment(p), crysta::ComputedUnit::Refln));
}
int peek_state(Project& p) { return static_cast<int>(crysta::peek(p, experiment(p)).refln_state); }
void ensure(Project& p) { crysta::current(p, experiment(p)); }
#endif

template <class Column>
auto values(const Column& column) {
    if constexpr (requires { column.values(); })
        return column.values();
    else
        return column.get();
}
template <class Column>
void replace(Column& column, std::size_t n) {
    auto copy = values(column);
    copy.resize(n);
    if constexpr (requires { column.assign(copy); })
        column.assign(copy);
    else
        column = copy;
}
void text(const std::string& key, const std::string& data) {
    std::cout << key << '\t';
    constexpr char digits[] = "0123456789abcdef";
    for (const unsigned char c : data) std::cout << digits[c >> 4] << digits[c & 15];
    std::cout << '\n';
}
template <class T>
void array(const std::string& key, const std::vector<T>& data) {
    std::cout << key;
    for (const auto item : data) std::cout << '\t' << item;
    std::cout << '\n';
}
std::vector<std::string> keys(Project& p) {
    std::vector<std::string> out;
    for (const std::string block : {"structure", "other"}) {
        for (const std::string field : {"fract_x", "fract_y", "fract_z", "adp_iso", "occupancy"})
            out.push_back(block + ".atom_site.Ni." + field);
    }
    for (std::size_t i = 0; i < p.experiments.size(); ++i) {
        auto& e = experiment(p, i);
        const auto prefix = name(e) + ".";
        out.push_back(prefix + "instrument.setup_wavelength");
        for (const std::string field :
             {"domain_radius", "mosaic_spread", "crystal_radius", "coefficient", "coefficient_11",
              "coefficient_22", "coefficient_33", "coefficient_12", "coefficient_13",
              "coefficient_23"})
            out.push_back(prefix + "extinction." + field);
        for (std::size_t j = 0; j < e.linked_structures.size(); ++j)
            out.push_back(prefix + "linked_structure." + link_name(link_at(e, j)) + ".scale");
    }
    return out;
}
void describe(Project& p, const std::string& prefix) {
    for (const auto& key : keys(p)) {
        try {
            const auto& slot = parameter(p, key);
            std::cout << prefix << "param\t" << key << '\t' << value(slot) << '\t' << is_free(slot)
                      << '\t';
            const auto original = start(slot);
            if (original)
                std::cout << *original;
            else
                std::cout << "none";
            std::cout << '\n';
        } catch (const std::invalid_argument&) {
        }
    }
    for (std::size_t i = 0; i < p.experiments.size(); ++i) {
        auto& e = experiment(p, i);
        for (std::size_t j = 0; j < e.linked_structures.size(); ++j) {
            const auto& link = link_at(e, j);
            std::cout << prefix << "link\t" << name(e) << '\t' << link_name(link) << '\t'
                      << static_cast<bool>(link.enabled) << '\t' << value(link.scale) << '\n';
        }
        if (e.reflections.has_value()) {
            const auto& r = rows(e);
            array(prefix + "h", values(r.index_h));
            array(prefix + "k", values(r.index_k));
            array(prefix + "l", values(r.index_l));
#ifdef EDGE_EDI
            array(prefix + "f2", values(r.intensity_meas));
            array(prefix + "su", values(r.intensity_meas_su));
#else
            array(prefix + "f2", values(r.intensity));
            array(prefix + "su", values(r.sigma));
#endif
            array(prefix + "lambda", values(r.wavelength));
        }
    }
}
void computed(Project& p, const std::string& prefix) {
    for (std::size_t i = 0; i < p.experiments.size(); ++i) {
        auto& e = experiment(p, i);
        array(prefix + "calc:" + name(e), intensities(e));
    }
}
void relation(Project& p, const std::string& id, const std::string& expression) {
    api::ParameterConstraint row;
    row.id = id;
    row.expression = expression;
    row.enabled = true;
    p.constraints.push_back(row);
}
void alias(Project& p, const std::string& id, const std::string& target) {
    api::ParameterAlias row;
    row.id = id;
    row.parameter_unique_name = target;
    p.aliases.push_back(row);
}
void shape(Project& p, const std::string& field, std::size_t n, bool setter) {
    auto& e = experiment(p);
#ifndef EDGE_EDI
    if (setter) {
        const auto& r = rows(e);
        crysta::ReflectionFile file;
        file.index_h = r.index_h.values();
        file.index_k = r.index_k.values();
        file.index_l = r.index_l.values();
        file.intensity = r.intensity.values();
        file.sigma = r.sigma.values();
        file.wavelength = r.wavelength.values();
        if (field == "index_h") file.index_h.resize(n);
        if (field == "index_k") file.index_k.resize(n);
        if (field == "index_l") file.index_l.resize(n);
        if (field == "intensity_meas") file.intensity.resize(n);
        if (field == "intensity_meas_su") file.sigma.resize(n);
        if (field == "wavelength") file.wavelength.resize(n);
        crysta::set_measured_reflections(e, file);
        return;
    }
#endif
#ifndef EDGE_EDI
    e.reflections.modify([&](auto& node) {
        auto& r = *node;
#else
    {
        auto& r = rows(e);
#endif
        if (field == "index_h") replace(r.index_h, n);
        if (field == "index_k") replace(r.index_k, n);
        if (field == "index_l") replace(r.index_l, n);
#ifdef EDGE_EDI
        if (field == "intensity_meas") replace(r.intensity_meas, n);
        if (field == "intensity_meas_su") replace(r.intensity_meas_su, n);
#else
        if (field == "intensity_meas") replace(r.intensity, n);
        if (field == "intensity_meas_su") replace(r.sigma, n);
#endif
        if (field == "wavelength") replace(r.wavelength, n);
#ifndef EDGE_EDI
    });
#else
    }
#endif
}
std::string empty_read(const std::filesystem::path& path) {
    std::ifstream stream(path);
    if (!stream) throw std::runtime_error("Cannot read lifecycle input " + path.string());
    return {std::istreambuf_iterator<char>(stream), std::istreambuf_iterator<char>()};
}
std::unique_ptr<Project> empty_project(const std::string& root, const std::string& origin,
                                       bool tof) {
    if (origin == "project") return std::unique_ptr<Project>(new Project(load(root)));
    const auto structure_text = empty_read(std::filesystem::path(root) / "structures/structure.edi");
#ifdef EDGE_EDI
    auto result = std::make_unique<Project>();
    result->structures.clear();
    result->experiments.clear();
    const auto structure = edi::structure_from_edi_text(structure_text);
    result->structures.push_back(std::make_shared<edi::Structure>(structure));
    if (origin == "create") {
        edi::ExperimentTypeTokens type;
        type.sample_form = "single crystal";
        type.beam_mode = tof ? "time-of-flight" : "constant wavelength";
        edi::Edit::create_experiment(*result, edi::simulation_experiment("bank", type, "structure"))();
    } else {
        const auto path = std::filesystem::path(root) / "experiments/bank.edi";
        const auto row = origin == "file" ? edi::load_experiment_edi_file(path.string())
                                          : edi::experiment_from_edi_text(empty_read(path));
        result->experiments.push_back(std::make_shared<edi::BraggPdExperiment>(row));
    }
    return result;
#else
    const auto structure = crysta::structure_from_edi_text(structure_text);
    if (origin == "create") {
        auto row = crysta::single_crystal_experiment(tof ? crysta::BeamModeEnum::TimeOfFlight
                                                      : crysta::BeamModeEnum::ConstantWavelength);
        row.name = "bank";
        if (!tof) row.instrument[0].set_value(1.6);
        row.linked_structures[0].structure_id = "structure";
        return std::unique_ptr<Project>(new Project(structure, row));
    }
    const auto path = std::filesystem::path(root) / "experiments/bank.edi";
    if (origin == "file")
        return std::unique_ptr<Project>(new Project(structure, crysta::experiment_from_edi_path(path.string())));
    return std::unique_ptr<Project>(new Project(structure, crysta::experiment_from_edi_text(empty_read(path))));
#endif
}
#ifdef EDGE_EDI
std::string empty_signature(Project& project) {
    auto& row = experiment(project);
    std::ostringstream out;
    out << std::setprecision(17) << project.experiments.size() << ':' << row.calculation_only << ':'
        << static_cast<int>(row.experiment_type.effective_sample_form()) << ':'
        << static_cast<int>(row.effective_beam_mode()) << ':' << row.data.has_value() << ':'
        << row.reflections.has_value();
    if (row.reflections) {
        const auto add = [&](const auto& column) { for (const auto& value : values(column)) out << ',' << value; out << ';'; };
        add(row.reflections->index_h); add(row.reflections->index_k); add(row.reflections->index_l);
        add(row.reflections->intensity_meas); add(row.reflections->intensity_meas_su); add(row.reflections->wavelength);
    }
    return out.str();
}
std::pair<bool, bool> empty_type_edit(Project& project, bool change_form) {
    Project trial(project);
    const auto before = empty_signature(trial);
    edi::ExperimentTypeTokens type;
    const bool tof = experiment(trial).effective_beam_mode() == edi::BeamModeEnum::TIME_OF_FLIGHT;
    type.sample_form = change_form ? "powder" : "single crystal";
    type.beam_mode = (change_form ? tof : !tof) ? "time-of-flight" : "constant wavelength";
    try {
        edi::Edit::replace_experiment(trial, experiment(trial),
                                     edi::simulation_experiment("bank", type, "structure"))();
        return {true, true};
    } catch (const std::invalid_argument&) {
        return {false, empty_signature(trial) == before};
    }
}
#endif
void empty_state(Project& project, const std::string& prefix) {
    auto& row = experiment(project);
#ifdef EDGE_EDI
    const bool tof = row.effective_beam_mode() == edi::BeamModeEnum::TIME_OF_FLIGHT;
    const bool single = row.experiment_type.effective_sample_form() == edi::SampleFormEnum::SINGLE_CRYSTAL;
#else
    const bool tof = row.kind == crysta::BeamModeEnum::TimeOfFlight;
    const bool single = row.sample_form.get() == "single crystal";
#endif
    const std::size_t count = row.reflections.has_value() ? rows(row).size() : 0;
    std::cout << prefix << "state\t" << static_cast<bool>(row.calculation_only) << '\t'
              << row.data.has_value() << '\t' << count << '\t' << tof << '\t' << single << '\n';
    if (row.reflections.has_value()) {
        auto& reflection = rows(row);
        array(prefix + "h", values(reflection.index_h));
        array(prefix + "k", values(reflection.index_k));
        array(prefix + "l", values(reflection.index_l));
#ifdef EDGE_EDI
        array(prefix + "f2", values(reflection.intensity_meas));
        array(prefix + "su", values(reflection.intensity_meas_su));
#else
        array(prefix + "f2", values(reflection.intensity));
        array(prefix + "su", values(reflection.sigma));
#endif
        array(prefix + "lambda", values(reflection.wavelength));
    } else {
        for (const auto* column : {"h", "k", "l", "f2", "su", "lambda"})
            std::cout << prefix << column << '\n';
    }
#ifdef EDGE_EDI
    const auto beam = empty_type_edit(project, false), form = empty_type_edit(project, true);
    std::cout << prefix << "editable\t" << beam.first << '\t' << form.first << '\t'
              << beam.second << '\t' << form.second << '\n';
#endif
}
void empty_lifecycle(const std::string& root, const std::string& output,
                     const std::string& origin, bool tof, const std::string& data) {
    auto project = empty_project(root, origin, tof);
    empty_state(*project, "created:");
    for (int cycle = 0; cycle < 3; ++cycle) {
        const std::string prefix = "empty" + std::to_string(cycle) + ':';
        const std::string path = output + "-empty-" + std::to_string(cycle);
        save(*project, path);
        empty_state(*project, prefix + "saved:");
        project.reset(new Project(load(path)));
        empty_state(*project, prefix + "loaded:");
    }
#ifdef EDGE_EDI
    const auto loaded = edi::experiment_with_plain_data(experiment(*project), data, false);
    edi::Edit::load_data(*project, experiment(*project), loaded.experiment)();
#else
    auto& row = experiment(*project);
    crysta::set_measured_reflections(row, crysta::read_reflection_file(data, row.kind));
#endif
    empty_state(*project, "measured:");
    for (int cycle = 0; cycle < 2; ++cycle) {
        const std::string path = output + "-measured-" + std::to_string(cycle);
        save(*project, path);
        project.reset(new Project(load(path)));
        empty_state(*project, "measured" + std::to_string(cycle) + ':');
    }
}

int main(int argc, char** argv) {
#ifdef EDGE_SOURCE_SHA
    if (argc == 2 && std::string(argv[1]) == "--identity") {
        std::cout << EDGE_SOURCE_SHA << '\n';
        return 0;
    }
#endif
    if (argc < 4) return 2;
    std::cout << std::setprecision(17) << "BEGIN\n";
    bool ok = false;
    std::string error;
    try {
        if (std::string(argv[2]) == "empty") {
            if (argc != 7) throw std::invalid_argument("Empty lifecycle needs origin, beam mode and data");
            empty_lifecycle(argv[1], argv[3], argv[4], std::string(argv[5]) == "tof", argv[6]);
            std::cout << "ok\t1\n";
            text("error", "");
            std::cout << "END\n";
            return 0;
        }
        auto p = load(argv[1]);
        const std::string action = argv[2], output = argv[3];
        describe(p, "loaded:");
        const std::map<std::string, int> arity{
            {"shape", 8}, {"bound", 6}, {"mark", 5}, {"fresh", 6}, {"distribution", 5}};
        if (const auto found = arity.find(action); found != arity.end() && argc < found->second)
            throw std::invalid_argument("Missing probe action arguments");
        try {
            if (action == "calc") {
                calculate(p);
                computed(p, "");
            } else if (action == "fit" || action == "free") {
                const auto result = fit(p);
                std::cout << "converged\t" << result.converged << "\nchi2\t"
                          << result.reduced_chi_square << '\n';
                for (const auto& [key, x] : result.values)
                    std::cout << "fitted\t" << key << '\t' << x << '\n';
                computed(p, "");
            } else if (action == "roundtrip") {
                save(p, output);
                auto restored = load(output);
                describe(restored, "saved:");
                calculate(restored);
                computed(restored, "saved:");
            } else if (action == "shape") {
                calculate(p);
                computed(p, "old:");
                const bool setter = std::string(argv[7]) == "setter";
                if (setter) describe(p, "before:");
                shape(p, argv[4], static_cast<std::size_t>(std::stoul(argv[5])), setter);
                if (!setter) describe(p, "before:");
                const std::string operation = argv[6];
                if (operation == "calc") calculate(p);
                if (operation == "fit") static_cast<void>(fit(p));
                if (operation == "save") save(p, output);
            } else if (action == "bound") {
                auto& dependent = parameter(p, "structure.atom_site.Ni.adp_iso");
#ifndef EDGE_EDI
                dependent.set_bounds(crysta::ParameterRange(0., 1.));
#endif
                alias(p, "a", "structure.atom_site.Ni.fract_x");
                alias(p, "b", "structure.atom_site.Ni.adp_iso");
                alias(p, "c", "structure.atom_site.Ni.occupancy");
                relation(p, "first", std::string(argv[4]) == "upper" ? "b = a + 5" : "b = -a");
                if (std::string(argv[4]) == "nonfinite") relation(p, "second", "c = sqrt(b)");
                describe(p, "before:");
                const std::string operation = argv[5];
                if (operation == "apply") apply(p);
                if (operation == "calc") calculate(p);
                if (operation == "fit") static_cast<void>(fit(p));
                if (operation == "save") {
                    save(p, output);
                    auto restored = load(output);
                    describe(restored, "saved:");
                }
            } else if (action == "mark") {
                freedom(parameter(p, argv[4]), true);
                if (argc > 5 && std::string(argv[5]) != "keep") type(experiment(p), argv[5]);
                describe(p, "before:");
                const auto result = fit(p);
                for (const auto& [key, x] : result.values)
                    std::cout << "fitted\t" << key << '\t' << x << '\n';
            } else if (action == "fresh") {
                calculate(p);
                std::cout << "state_before\t" << state(p) << '\t' << peek_state(p) << '\n';
                const std::string key = argv[4];
                if (key == "type")
                    type(experiment(p), argv[5]);
                else if (key == "distribution")
                    distribution(experiment(p), argv[5]);
                else if (std::string(argv[5]) == "free")
                    freedom(parameter(p, key), !is_free(parameter(p, key)));
                else
                    number(parameter(p, key), value(parameter(p, key)) + std::stod(argv[5]));
                std::cout << "state_after\t" << state(p) << '\t' << peek_state(p) << '\n';
                ensure(p);
                std::cout << "state_ensured\t" << state(p) << '\t' << peek_state(p) << '\n';
            } else if (action == "distribution") {
                distribution(experiment(p), argv[4]);
                calculate(p);
                computed(p, "");
                save(p, output);
                auto restored = load(output);
                describe(restored, "saved:");
                calculate(restored);
                computed(restored, "saved:");
            } else if (action != "load")
                throw std::runtime_error("Unknown probe action");
            ok = true;
        } catch (const std::exception& failure) {
            error = failure.what();
        }
        if (action == "shape") computed(p, "retained:");
        describe(p, "after:");
    } catch (const std::exception& failure) {
        error = failure.what();
    }
    std::cout << "ok\t" << ok << '\n';
    text("error", error);
    std::cout << "END\n";
}
