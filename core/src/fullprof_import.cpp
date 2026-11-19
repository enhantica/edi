// SPDX-License-Identifier: BSD-3-Clause
#include "fullprof_import.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <map>
#include <numbers>
#include <optional>
#include <sstream>
#include <string_view>

#include "edi/categories.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/selectors.hpp"
#include "edi/symmetry.hpp"
#include "import_symmetry.hpp"

namespace edi::detail {
namespace {

namespace fs = std::filesystem;
using Words = std::vector<std::string>;
using Row = std::vector<double>;

std::string trim(std::string_view text) {
    const auto start = text.find_first_not_of(" \t\r\n");
    return start == text.npos ? std::string{} : std::string(text.substr(start, text.find_last_not_of(" \t\r\n") - start + 1));
}

std::string lower(std::string text) {
    for (char& c : text) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    return text;
}

Words words(std::string_view text) {
    std::istringstream in{std::string(text)};
    in.imbue(std::locale::classic());
    Words result;
    for (std::string word; in >> word;) {
        result.push_back(std::move(word));
    }
    return result;
}

double number(std::string token, const std::string& where) {
    for (char& c : token) {
        if (c == 'd' || c == 'D') {
            c = 'E';
        }
    }
    return parse_edi_double(token, where);
}

Row numbers(const Words& fields, const std::string& where) {
    Row result;
    result.reserve(fields.size());
    for (const auto& field : fields) {
        result.push_back(number(field, where));
    }
    return result;
}

int integer(double value, const std::string& where) {
    if (std::trunc(value) != value || value < std::numeric_limits<int>::min() || value > std::numeric_limits<int>::max()) {
        throw IoError(where + ": expected an integer");
    }
    return static_cast<int>(value);
}

std::ifstream input(const fs::path& path) {
    std::error_code error;
    if (!fs::is_regular_file(path, error)) {
        throw IoError("Missing or unreadable FullProf input " + path.string());
    }
    std::ifstream file(path);
    file.imbue(std::locale::classic());
    if (!file) {
        throw IoError("Unable to read FullProf input " + path.string());
    }
    return file;
}

struct Line {
    std::string text;
    std::string comment;
    std::string original_comment;
    std::size_t number;
};

struct PCR {
    fs::path path;
    std::vector<Line> lines;
    bool refinement_enabled = false;

    explicit PCR(const std::string& source) : path(source) {
        auto file = input(path);
        std::size_t i = 0;
        for (std::string line; std::getline(file, line);) {
            ++i;
            const auto bang = line.find('!');
            std::string comment = bang == line.npos ? "" : trim(std::string_view(line).substr(bang + 1));
            const auto end = std::min({bang, line.find('#'), line.find("<--")});
            auto text = trim(std::string_view(line).substr(0, end));
            if (!text.empty() || !comment.empty()) {
                lines.push_back({std::move(text), lower(comment), std::move(comment), i});
            }
        }
        if (file.bad()) {
            fail("Could not finish reading the control file");
        }
    }

    [[noreturn]] void fail(const std::string& reason, std::size_t i = std::string::npos) const {
        throw IoError(path.string() + (i < lines.size() ? ":" + std::to_string(lines[i].number) : "") + ": " + reason);
    }

    std::size_t header(std::string_view prefix, std::size_t start, std::size_t end) const {
        for (std::size_t i = start; i < end; ++i) {
            if (lines[i].comment.starts_with(prefix)) {
                return i;
            }
        }
        return end;
    }

    std::size_t require(std::string_view prefix, std::size_t start, std::size_t end) const {
        const auto found = header(prefix, start, end);
        if (found == end) {
            fail("Missing FullProf " + std::string(prefix) + " block", start);
        }
        return found;
    }

    std::size_t next(std::size_t start, std::size_t end) const {
        while (start < end && lines[start].text.empty()) {
            ++start;
        }
        if (start == end) {
            fail("Incomplete FullProf block", start);
        }
        return start;
    }

    Row row(std::size_t i, std::size_t count) const {
        const auto fields = words(lines.at(i).text);
        if (fields.size() < count) {
            fail("Incomplete numeric row", i);
        }
        return numbers(fields, path.string() + ":" + std::to_string(lines[i].number));
    }

    Row after(std::size_t i, std::size_t end, std::size_t count) const { return row(next(i + 1, end), count); }

    void zero(const Row& row, std::size_t from, std::size_t to, const std::string& field) const {
        if (from > to || to > row.size()) {
            fail("Incomplete FullProf " + field + " row");
        }
        if (std::any_of(row.begin() + static_cast<std::ptrdiff_t>(from), row.begin() + static_cast<std::ptrdiff_t>(to),
                        [](double value) { return value != 0.; })) {
            fail("Unsupported FullProf " + field);
        }
    }
};

struct Coded {
    double value;
    double code;
    double multiplier = 1.;
};

struct Refinement {
    std::map<Parameter*, Coded> codes;
    std::vector<std::pair<double, double>> transformed_independent_pairs;

    void set(Parameter& parameter, Coded coded) {
        parameter.value = coded.value;
        if (coded.code != 0.) {
            codes.emplace(&parameter, coded);
        }
    }

    void set(OptionalParameter& parameter, Coded coded) {
        set(parameter.value(), coded);
    }

    void set(OptionalParameter& parameter, const ParameterSpec& spec, Coded coded) {
        Parameter field;
        field.spec = &spec;
        parameter = field;
        set(parameter, coded);
    }

    void set(const std::vector<Parameter*>& targets, const Row& values, const Row& codewords) {
        for (std::size_t i = 0; i < targets.size(); ++i) {
            set(*targets[i], {values[i], codewords[i]});
        }
    }
};

std::string safe_name(std::string name, std::string_view fallback) {
    for (char& c : name) {
        if (!std::isalnum(static_cast<unsigned char>(c)) && c != '_' && c != '-' && c != '.') {
            c = '_';
        }
    }
    if (name.empty() || !std::isalpha(static_cast<unsigned char>(name.front()))) {
        name = std::string(fallback) + name;
    }
    if (name.size() < 2) {
        name += '_';
    }
    name.resize(std::min<std::size_t>(name.size(), 31));
    return name;
}

struct Pattern {
    std::shared_ptr<BraggPdExperiment> model = std::make_shared<BraggPdExperiment>();
    std::string file;
    int job = 0;
    int profile = 0;
    int background = 0;
    int exclusions = 0;
    int format = 0;
    int absorption = 0;
    int orientation = 0;
    int polarization_model = 0;
    bool default_companion = false;
    bool enabled = true;
    double background_origin = 0.;
    double asymmetry_limit = 180.;
    double lo = 0.;
    double hi = 0.;
    double scale_factor = 1.;
    std::vector<Row> profile_rows;

    bool tof() const { return job < 0; }
    bool xray() const { return job == 0; }
    bool single_crystal() const { return model->reflections.has_value(); }
};

fs::path companion(const PCR& pcr, const Pattern& pattern) {
    const std::string extension = pattern.single_crystal() ? ".int" : ".dat";
    const fs::path directory = pcr.path.parent_path();
    const auto conventional = directory / (pcr.path.stem().string() + extension);
    if (pattern.default_companion && fs::is_regular_file(conventional)) {
        return conventional;
    }
    const fs::path named(pattern.file);
    if (!pattern.file.empty()) {
        if (named.is_absolute() || named.has_parent_path() || named == "." || named == ".." ||
            pattern.file.find_first_of("\\:") != std::string::npos) {
            pcr.fail("Companion data must be beside the PCR file: " + pattern.file);
        }
        const auto candidate = directory / (named.has_extension() ? named : fs::path(pattern.file + extension));
        if (fs::is_regular_file(candidate)) {
            return candidate;
        }
        pcr.fail("Missing FullProf companion " + candidate.filename().string());
    }
    if (!fs::is_regular_file(conventional)) {
        pcr.fail("Missing FullProf companion " + conventional.filename().string());
    }
    return conventional;
}

struct Data {
    std::vector<double> x, y, sigma;

    void push(double coordinate, double intensity, double su) {
        x.push_back(coordinate);
        y.push_back(intensity);
        sigma.push_back(su);
    }
};

Data ial_data(const fs::path& path) {
    auto file = input(path);
    const auto line = [&] {
        std::string text;
        if (!std::getline(file, text)) {
            throw IoError(path.string() + ": truncated D1A/D2B data");
        }
        return text;
    };
    line();
    const auto header = line();
    if (header.size() < 24) {
        throw IoError(path.string() + ": incomplete D1A/D2B header");
    }
    const double step = number(trim(std::string_view(header).substr(16, 8)), path.string());
    const double first = number(trim(line()), path.string());
    const auto monitor = numbers(words(line()), path.string());
    if (monitor.size() < 2 || step <= 0.) {
        throw IoError(path.string() + ": invalid D1A/D2B monitor or step");
    }
    const double norm = monitor[1] < 1. ? 1. : monitor[0] / monitor[1];
    Data result;
    bool terminated = false;
    for (std::string text; std::getline(file, text);) {
        if (trim(text) == "-1000") {
            terminated = true;
            break;
        }
        if (!text.empty() && text.back() == '\r') {
            text.pop_back();
        }
        if (text.size() != 80) {
            throw IoError(path.string() + ": expected ten fixed-width D1A/D2B weight and intensity pairs");
        }
        for (std::size_t i = 0; i < text.size(); i += 8) {
            const auto pair = std::string_view(text).substr(i, 8);
            const auto weight = number(trim(pair.substr(0, 2)), path.string());
            const auto intensity = number(trim(pair.substr(2)), path.string());
            const auto y = intensity <= 0.00001 ? 1. : intensity;
            result.push(first + static_cast<double>(result.x.size()) * step, y,
                        std::sqrt(norm * y / (weight == 0. ? 1. : weight)));
        }
    }
    if (!terminated) {
        throw IoError(path.string() + ": missing D1A/D2B end marker");
    }
    return result;
}

Data stepped_data(const fs::path& path) {
    auto file = input(path);
    std::string line;
    std::getline(file, line);
    std::istringstream header(line);
    header.imbue(std::locale::classic());
    double first = 0., step = 0., last = 0.;
    if (!(header >> first >> step >> last) || !std::isfinite(first) || !std::isfinite(last) || step <= 0. || first > last) {
        throw IoError(path.string() + ": expected the FullProf start, step and end header");
    }
    Data result;
    for (double y; file >> y;) {
        result.push(first + static_cast<double>(result.x.size()) * step, y, std::sqrt(std::max(1., y)));
    }
    if (!file.eof() || result.x.empty() || std::abs(result.x.back() - last) > step * 0.51) {
        throw IoError(path.string() + ": intensity count disagrees with the FullProf data header");
    }
    return result;
}

Data gsas_data(const fs::path& path) {
    auto file = input(path);
    std::string line;
    std::getline(file, line);
    std::getline(file, line);
    const auto header = words(line);
    if (header.size() < 9 || header[0] != "BANK" || header[4] != "CONST" || header.back() != "ALT") {
        throw IoError(path.string() + ": expected a single GSAS CONST/ALT bank");
    }
    const auto count = integer(number(header[2], path.string()), path.string());
    Data result;
    for (double x, y, sigma; file >> x >> y >> sigma;) {
        result.push(x / 32., y, sigma);
    }
    if (count <= 0 || result.x.size() != static_cast<std::size_t>(count)) {
        throw IoError(path.string() + ": truncated or additional GSAS bank data");
    }
    return result;
}

Data xy_data(const fs::path& path) {
    auto file = input(path);
    Data result;
    double x_factor = 1.;
    double y_factor = 1.;
    bool xy_header = false;
    for (std::string line; std::getline(file, line);) {
        const auto fields = words(std::string_view(line).substr(0, line.find_first_of("!#")));
        if (fields.empty()) {
            continue;
        }
        if (result.x.empty()) {
            if (lower(fields.front()) == "xydata") {
                xy_header = true;
                continue;
            }
            if (xy_header && lower(fields.front()) == "inter") {
                const auto controls = numbers(Words(fields.begin() + 1, fields.end()), path.string());
                if (controls.size() != 4 || controls[0] <= 0. || controls[1] <= 0. ||
                    (controls[2] != 0. && controls[2] != 2.)) {
                    throw IoError(path.string() + ": unsupported FullProf XYDATA INTER control");
                }
                x_factor = controls[0];
                y_factor = controls[1];
                continue;
            }
            if (fields.front().find_first_of("0123456789+-.") != 0) {
                continue;
            }
        }
        if (fields.size() != 2 && fields.size() != 3) {
            throw IoError(path.string() + ": expected FullProf X Y [sigma] rows");
        }
        const auto row = numbers(fields, path.string());
        const double y = row[1] * y_factor;
        const double sigma = row.size() == 3 ? row[2] * y_factor : std::sqrt(std::max(1., y));
        result.push(row[0] * x_factor, y, sigma);
    }
    if (file.bad()) {
        throw IoError(path.string() + ": incomplete FullProf XY data read");
    }
    return result;
}

void reflection_data(const PCR& pcr, Pattern& pattern) {
    const auto path = companion(pcr, pattern);
    auto file = input(path);
    std::string header;
    if (!std::getline(file, header) || !std::getline(file, header) || !std::getline(file, header)) {
        pcr.fail("Incomplete FullProf reflection data header in " + path.filename().string());
    }
    const auto controls = words(header);
    if (controls.size() < 3 || number(controls[2], path.string()) != 0.) {
        pcr.fail("Unsupported FullProf reflection geometry (Ipow) in " + path.filename().string());
    }
    auto& exp = *pattern.model;
    auto loaded = experiment_with_plain_data(exp, path.string(), false);
    if (loaded.experiment.calculation_only || !loaded.more.empty()) {
        pcr.fail("FullProf reflection datasets require observed data and one scale per dataset");
    }
    exp.reflections = std::move(loaded.experiment.reflections);
    exp.data_file = loaded.file_name;
    exp.calculation_only = false;
    if (exp.instrument.setup_wavelength) {
        const auto& wavelength = loaded.experiment.instrument.setup_wavelength;
        if (!wavelength || wavelength->value <= 0.) {
            pcr.fail("Missing positive wavelength in FullProf reflection data " + path.filename().string());
        }
        exp.instrument.setup_wavelength->value = wavelength->value.get();
    }
}

void powder_data(const PCR& pcr, Pattern& pattern) {
    const auto path = companion(pcr, pattern);
    Data source;
    switch (pattern.format) {
        case 0: source = stepped_data(path); break;
        case 6: source = ial_data(path); break;
        case 10: source = xy_data(path); break;
        case 12: source = gsas_data(path); break;
        default: pcr.fail("Unsupported FullProf data format Ins=" + std::to_string(pattern.format));
    }
    Data data;
    for (std::size_t i = 0; i < source.x.size(); ++i) {
        const auto x = source.x[i];
        if (x < pattern.lo - 1.e-6 || x > pattern.hi + 1.e-6) {
            continue;
        }
        if ((!data.x.empty() && data.x.back() >= x) || !std::isfinite(x) || !std::isfinite(source.y[i]) ||
            !std::isfinite(source.sigma[i]) || source.sigma[i] <= 0.) {
            pcr.fail("Invalid FullProf data row in " + path.filename().string());
        }
        data.push(x, source.y[i], source.sigma[i]);
    }
    if (data.x.empty()) {
        pcr.fail("No observations in the FullProf calculation range: " + path.filename().string());
    }
    auto& exp = *pattern.model;
    exp.data_file = path.filename().string();
    exp.data.emplace();
    (pattern.tof() ? exp.data->time_of_flight : exp.data->two_theta) = std::move(data.x);
    exp.data->intensity_meas = std::move(data.y);
    exp.data->intensity_meas_su = std::move(data.sigma);
    exp.calculation_only = false;
}

struct CodedRow {
    Row values, codes;
    Coded at(std::size_t i, double factor = 1.) const { return {values.at(i) * factor, codes.at(i), factor}; }
};

CodedRow pair_after(const PCR& pcr, std::size_t header, std::size_t end, std::size_t count) {
    const auto first = pcr.next(header + 1, end);
    auto codewords = pcr.after(first, end, count);
    if (!pcr.refinement_enabled) {
        std::fill(codewords.begin(), codewords.end(), 0.);
    }
    return {pcr.row(first, count), std::move(codewords)};
}

std::vector<std::size_t> headers(const PCR& pcr, std::string_view prefix, std::size_t start, std::size_t end) {
    std::vector<std::size_t> result;
    for (auto i = pcr.header(prefix, start, end); i < end; i = pcr.header(prefix, i + 1, end)) {
        result.push_back(i);
    }
    return result;
}

std::string number_text(double value) {
    std::ostringstream text;
    text.imbue(std::locale::classic());
    text << std::setprecision(std::numeric_limits<double>::max_digits10) << value;
    return text.str();
}

void refinement_flags(const PCR& pcr, Project& project, const Refinement& refinement, bool active) {
    if (!active) {
        return;
    }
    struct Member {
        ParameterEntry entry;
        double direction;
    };
    std::map<int, std::vector<Member>> groups;
    for (const auto& entry : parameter_entries(project)) {
        const auto it = refinement.codes.find(entry.parameter);
        if (it == refinement.codes.end() || !entry.refinable) {
            continue;
        }
        const auto code = it->second;
        const double magnitude = std::abs(code.code);
        const int group = integer(std::floor(magnitude / 10.), pcr.path.string());
        const double direction = std::copysign(magnitude - 10. * group, code.code) * code.multiplier;
        if (direction == 0.) {
            pcr.fail("Invalid FullProf refinement codeword " + number_text(code.code));
        }
        entry.parameter->free = true;
        entry.parameter->uncertainty = std::nullopt;
        if (group != 0) {
            groups[group].push_back({entry, direction});
        }
    }
    for (const auto& [a, b] : refinement.transformed_independent_pairs) {
        const auto group_a = integer(std::floor(std::abs(a) / 10.), pcr.path.string());
        const auto group_b = integer(std::floor(std::abs(b) / 10.), pcr.path.string());
        if ((group_a != 0 && groups[group_a].size() != 1) || (group_b != 0 && groups[group_b].size() != 1)) {
            pcr.fail("Shared FullProf codewords combine two asymmetry terms in one EDI parameter");
        }
    }
    std::map<Parameter*, std::string> names;
    for (const auto& slot : named_slots(project)) {
        names.emplace(slot.parameter, slot.unique_name);
    }
    for (const auto& [code, members] : groups) {
        if (members.size() == 1) {
            continue;
        }
        const auto prefix = "fp" + std::to_string(code);
        for (std::size_t i = 0; i < members.size(); ++i) {
            const auto& member = members[i];
            const auto& entry = member.entry;
            auto alias = std::make_shared<ParameterAlias>();
            alias->id = prefix + "_" + std::to_string(i);
            const auto name = names.find(entry.parameter);
            if (name == names.end()) {
                pcr.fail("Cannot name a FullProf refinement relation member: " + entry.path);
            }
            alias->parameter_unique_name = name->second;
            project.aliases.push_back(alias);
            if (i == 0) {
                continue;
            }
            const auto& leader = members.front();
            auto constraint = std::make_shared<ParameterConstraint>();
            constraint->id = alias->id.value();
            constraint->expression = alias->id.value() + " = " + number_text(entry.parameter->value.get()) +
                " + " + number_text(member.direction / leader.direction) + " * (" + prefix + "_0 - (" +
                number_text(leader.entry.parameter->value.get()) + "))";
            entry.parameter->free = false;
            entry.parameter->uncertainty = 0.;
            project.constraints.push_back(constraint);
        }
    }
    if (!project.constraints.empty() && !apply_relations(project)) {
        pcr.fail("The FullProf refinement relations could not be represented in EDI");
    }
    refresh_relations(project);
}

void read_background(const PCR& pcr, Pattern& pattern, Refinement& refine,
                     std::size_t points, std::size_t coeffs, std::size_t end) {
    auto& exp = *pattern.model;
    if (pattern.background >= 2) {
        if (points == end) {
            pcr.fail("Missing interpolated background points");
        }
        std::vector<Row> rows;
        auto pos = points;
        for (int i = 0; i < pattern.background; ++i) {
            pos = pcr.next(pos + 1, end);
            rows.push_back(pcr.row(pos, 3));
        }
        std::sort(rows.begin(), rows.end());
        double previous = -std::numeric_limits<double>::infinity();
        for (const auto& values : rows) {
            if (values[0] == previous) {
                pcr.fail("FullProf background positions must be distinct", points);
            }
            previous = values[0];
            auto point = std::make_shared<LineSegment>();
            point->position = values[0];
            exp.background.push_back(point);
            refine.set(point->intensity, {values[1], pcr.refinement_enabled ? values[2] : 0.});
        }
        return;
    }
    if (pattern.background != 0 && pattern.background != -5) {
        pcr.fail("Unsupported FullProf background Nba=" + std::to_string(pattern.background));
    }
    if (coeffs == end) {
        pcr.fail("Missing FullProf background coefficients");
    }
    const bool chebyshev = pattern.background == -5;
    exp.background_type = chebyshev ? "chebyshev" : "polynomial";
    if (chebyshev) {
        exp.background_x_min = pattern.lo;
        exp.background_x_max = pattern.hi;
    } else {
        exp.background_origin = pattern.background_origin;
    }
    auto pos = coeffs;
    for (int group = 0; group < (chebyshev ? 4 : 1); ++group) {
        pos = pcr.next(pos + 1, end);
        const auto values = pcr.row(pos, 6);
        pos = pcr.next(pos + 1, end);
        const auto codes = pcr.row(pos, 6);
        for (int i = 0; i < 6; ++i) {
            const auto k = static_cast<std::size_t>(i);
            auto term = std::make_shared<PolynomialTerm>();
            term->order = group * 6 + i;
            exp.background_terms.push_back(term);
            refine.set(term->coef, {values[k], codes[k]});
        }
    }
}

void configure_pattern(const PCR& pcr, Pattern& pattern, Refinement& refine,
                       std::size_t setup, std::size_t range, std::size_t calibration, std::size_t end,
                       bool combined_range) {
    auto& exp = *pattern.model;
    auto& instrument = exp.instrument;
    exp.experiment_type.sample_form = pattern.single_crystal() ? SampleFormEnum::SINGLE_CRYSTAL : SampleFormEnum::POWDER;
    exp.experiment_type.beam_mode = pattern.tof() ? BeamModeEnum::TIME_OF_FLIGHT : BeamModeEnum::CONSTANT_WAVELENGTH;
    exp.experiment_type.radiation_probe = pattern.xray() ? RadiationProbeEnum::XRAY : RadiationProbeEnum::NEUTRON;
    exp.experiment_type.scattering_type = ScatteringTypeEnum::BRAGG;
    if (!pattern.xray()) {
        exp.neutron_scattering_length = "sears1992";
    }
    if (pattern.single_crystal()) {
        if (!pattern.tof()) {
            refine.set(instrument.setup_wavelength, spec::instrument_wavelength, {0., 0.});
        }
        return;
    }
    const auto limits = pcr.after(range, end, combined_range ? 9 : 3);
    const std::size_t offset = combined_range ? 6 : 0;
    pattern.lo = limits[offset];
    pattern.hi = limits[offset + 2];
    if (pattern.lo >= pattern.hi) {
        pcr.fail("Invalid FullProf calculation range", range);
    }
    const auto values = pcr.after(setup, end, pattern.tof() ? 3 : 8);
    const auto zero = pcr.after(calibration, end, 9);
    if (pattern.tof()) {
        pattern.background_origin = values[0];
        exp.peak.cutoff_fwhm = values[1];
        pattern.absorption = integer(values[2], pcr.path.string());
        refine.set(instrument.calib_d_to_tof_offset, {zero[0], zero[1]});
        refine.set(instrument.calib_d_to_tof_linear, {zero[2], zero[3]});
        refine.set(instrument.calib_d_to_tof_quadratic, {zero[4], zero[5]});
        refine.set(instrument.calib_d_to_tof_reciprocal, {zero[6], zero[7]});
        instrument.setup_twotheta_bank.value = zero[8];
    } else {
        pattern.background_origin = values[3];
        exp.peak.cutoff_fwhm = values[4];
        pattern.asymmetry_limit = values[7];
        if (values[0] <= 0. || zero[8] != 0. || (values.size() >= 10 && values[9] != 0.)) {
            pcr.fail("Unsupported FullProf wavelength, secondary absorption or additional CW instrument terms", setup);
        }
        refine.set(instrument.setup_wavelength, spec::instrument_wavelength, {zero[6] > 0. ? zero[6] : values[0], zero[7]});
        refine.set(instrument.calib_twotheta_offset, spec::instrument_twotheta_offset, {zero[0], zero[1]});
        if (zero[2] != 0. || zero[3] != 0.) {
            refine.set(instrument.calib_sample_displacement, spec::instrument_sample_displacement, {zero[2], zero[3]});
        }
        if (zero[4] != 0. || zero[5] != 0.) {
            refine.set(instrument.calib_sample_transparency, spec::instrument_sample_transparency, {zero[4], zero[5]});
        }
        if (pattern.xray()) {
            const auto cthm = values[5];
            const auto polarization = values.size() > 8 ? values[8] : 0.;
            if (values[2] < 0. || cthm < 0. || cthm > 1. || polarization < 0. || polarization > 1.) {
                pcr.fail("Unsupported FullProf X-ray doublet or polarization coefficients", setup);
            }
            if (values[2] > 0. && values[1] != values[0]) {
                refine.set(instrument.setup_wavelength_2, spec::instrument_wavelength_2, {values[1], 0.});
                refine.set(instrument.setup_wavelength_2_to_1_ratio, spec::instrument_wavelength_2_to_1_ratio, {values[2], 0.});
            }
            exp.xray_form_factor = "it1992";
            exp.xray_dispersion = "sasaki1989";
            if (cthm != 0. || polarization != 0.) {
                if (pattern.polarization_model != 0) {
                    pcr.fail("Unsupported FullProf X-ray polarization geometry (Ilo)", setup);
                }
                refine.set(instrument.setup_polarization_coefficient, spec::instrument_polarization_coefficient, {0.5, 0.});
                refine.set(instrument.setup_monochromator_twotheta, spec::instrument_monochromator_twotheta, {std::acos(std::sqrt(cthm)) * 180. / std::numbers::pi, 0.});
                pattern.scale_factor = 2.;
            } else {
                refine.set(instrument.setup_polarization_coefficient, spec::instrument_polarization_coefficient, {0., 0.});
                refine.set(instrument.setup_monochromator_twotheta, spec::instrument_monochromator_twotheta, {0., 0.});
            }
        } else if (values[2] != 0. && values[1] != values[0]) {
            pcr.fail("EDI supports one constant wavelength for neutron patterns", setup);
        }
        if (values[6] != 0.) {
            if (pattern.xray()) {
                pcr.fail("Unsupported FullProf X-ray absorption geometry", setup);
            }
            select_absorption(exp, "cylinder-hewat");
            refine.set(exp.absorption.mu_r, {values[6], 0.});
        }
    }
    if (exp.peak.cutoff_fwhm <= 0.) {
        pcr.fail("Invalid FullProf profile cutoff", setup);
    }
}

void cw_profile(const PCR& pcr, Pattern& pattern, Refinement& refine, const CodedRow& scale,
                const CodedRow& width, const CodedRow& shape) {
    auto& exp = *pattern.model;
    auto& peak = exp.peak;
    const auto nonzero = [&](std::size_t i) { return shape.values[i] != 0. || shape.codes[i] != 0.; };
    const bool beba = nonzero(2) || nonzero(3) || nonzero(4) || nonzero(5);
    const bool fcj = shape.values.size() >= 8 && shape.codes.size() >= 8 && (nonzero(6) || nonzero(7));
    pcr.zero(width.values, 5, 8, "CWL size/strain");
    pcr.zero(width.codes, 5, 7, "CWL size/strain code");
    if (beba && (pattern.profile != 5 || fcj)) {
        pcr.fail("Unsupported FullProf combination of CW peak profile and Bérar–Baldinozzi asymmetry");
    }
    std::string profile;
    switch (pattern.profile) {
        case 0: profile = "cwl-gaussian"; break;
        case 1: profile = "cwl-lorentzian"; break;
        case 5: profile = beba ? "cwl-pseudo-voigt-berar-baldinozzi" : "cwl-pseudo-voigt"; break;
        case 7: profile = fcj ? "cwl-tch-pseudo-voigt-fcj" : "cwl-tch-pseudo-voigt"; break;
        default: pcr.fail("Unsupported FullProf CW profile Npr=" + std::to_string(pattern.profile));
    }
    if (fcj && pattern.profile != 7) {
        pcr.fail("Unsupported FullProf FCJ profile");
    }
    select_peak_profile(exp, profile);
    refine.set(peak.broad_gauss_u, spec::peak_broad_gauss_u, width.at(0));
    refine.set(peak.broad_gauss_v, spec::peak_broad_gauss_v, width.at(1));
    refine.set(peak.broad_gauss_w, spec::peak_broad_gauss_w, width.at(2));
    if (peak.broad_lorentz_x) {
        refine.set(peak.broad_lorentz_x, width.at(3));
        refine.set(peak.broad_lorentz_y, width.at(4));
    } else {
        // FullProf Npr 5 uses X for the angular slope of the mixing coefficient.
        if (peak.mixing_eta_0) {
            refine.set(peak.mixing_eta_0, scale.at(1));
            refine.set(peak.mixing_eta_1, width.at(3));
            pcr.zero(width.values, 4, 5, "CWL width Y");
            pcr.zero(width.codes, 4, 5, "CWL width Y code");
        } else {
            pcr.zero(width.values, 3, 5, "CWL width X/Y");
            pcr.zero(width.codes, 3, 5, "CWL width X/Y code");
        }
    }
    if (fcj) {
        refine.set(peak.asym_fcj_1, shape.at(6));
        refine.set(peak.asym_fcj_2, shape.at(7));
    }
    if (beba) {
        const auto transform = [&](OptionalParameter& a, OptionalParameter& b, std::size_t i) {
            auto first = shape.at(i, -1.);
            const auto second = shape.at(i + 1, -1.);
            first.value += 3. * second.value;
            if (first.code != 0. && second.code != 0.) {
                // Two independent source directions span both native parameters. A coupling outside
                // this pair would also need the inverse two-parameter transformation.
                refine.transformed_independent_pairs.emplace_back(first.code, second.code);
            } else if (second.code != 0.) {
                first.code = second.code;
                first.multiplier = 3. * second.multiplier;
            }
            refine.set(a, first);
            refine.set(b, second);
        };
        transform(peak.asym_beba_a0, peak.asym_beba_b0, 2);
        transform(peak.asym_beba_a1, peak.asym_beba_b1, 4);
        peak.asym_beba_limit->value = pattern.asymmetry_limit;
    }
}

void tof_profile(const PCR& pcr, Pattern& pattern, Refinement& refine, const CodedRow& sigma,
                 const CodedRow& gamma, const CodedRow& shape, const CodedRow& absorption) {
    auto& exp = *pattern.model;
    std::string profile;
    switch (pattern.profile) {
        case 7: profile = "tof-pseudo-voigt"; break;
        case 9: profile = "tof-jorgensen-von-dreele"; break;
        default: pcr.fail("Unsupported FullProf TOF profile Npr=" + std::to_string(pattern.profile));
    }
    select_peak_profile(exp, profile);
    auto& peak = exp.peak;
    pcr.zero(sigma.values, 3, 4, "TOF Sigma-Q");
    pcr.zero(sigma.codes, 3, 4, "TOF Sigma-Q code");
    pcr.zero(sigma.values, 6, 8, "anisotropic TOF size");
    pcr.zero(sigma.codes, 6, 7, "anisotropic TOF size code");
    pcr.zero(sigma.codes, 4, 6, "TOF Gaussian size/strain refinement");
    pcr.zero(gamma.codes, 3, 5, "TOF Lorentzian size/strain refinement");
    auto sigma2 = sigma.at(0);
    auto sigma1 = sigma.at(1);
    sigma2.value -= sigma.values[5];
    sigma1.value -= sigma.values[4];
    refine.set(peak.broad_gauss_sigma_2, sigma2);
    refine.set(peak.broad_gauss_sigma_1, sigma1);
    refine.set(peak.broad_gauss_sigma_0, sigma.at(2));
    refine.set(peak.broad_gauss_strain, sigma.at(4));
    refine.set(peak.broad_gauss_size, sigma.at(5));
    auto gamma2 = gamma.at(0);
    auto gamma1 = gamma.at(1);
    gamma2.value -= gamma.values[4];
    gamma1.value -= gamma.values[3];
    refine.set(peak.broad_lorentz_gamma_2, gamma2);
    refine.set(peak.broad_lorentz_gamma_1, gamma1);
    refine.set(peak.broad_lorentz_gamma_0, gamma.at(2));
    refine.set(peak.broad_lorentz_strain, gamma.at(3));
    refine.set(peak.broad_lorentz_size, gamma.at(4));
    if (pattern.profile != 7) {
        refine.set(peak.rise_alpha_0, shape.at(2));
        refine.set(peak.decay_beta_0, shape.at(3));
        refine.set(peak.rise_alpha_1, shape.at(4));
        refine.set(peak.decay_beta_1, shape.at(5));
        pcr.zero(shape.values, 6, shape.values.size(), "TOF wavelength-dependent shape terms");
        pcr.zero(shape.codes, 6, shape.codes.size(), "TOF wavelength-dependent shape code");
    }
    if (!absorption.values.empty()) {
        if (absorption.values[2] != 0. || absorption.values[3] != 0.) {
            pcr.fail("Unsupported FullProf TOF absorption ABSCOR2");
        }
        if (absorption.values[0] != 0. || absorption.values[1] != 0.) {
            if (pattern.absorption != 2) {
                pcr.fail("Unsupported FullProf TOF absorption model");
            }
            select_absorption(exp, "cylinder");
            refine.set(exp.absorption.abscor1, {absorption.values[0], absorption.values[1]});
        }
    }
}

std::string element(std::string type) {
    auto first = std::find_if(type.begin(), type.end(), [](unsigned char c) { return std::isalpha(c); });
    if (first != type.end()) {
        *first++ = static_cast<char>(std::toupper(static_cast<unsigned char>(*first)));
        for (; first != type.end() && std::isalpha(static_cast<unsigned char>(*first)); ++first) {
            *first = static_cast<char>(std::tolower(static_cast<unsigned char>(*first)));
        }
    }
    return type;
}

std::vector<Row> profile_signature(const CodedRow& width, const CodedRow& shape, const CodedRow& gamma) {
    // Scale, orientation and absorption are handled separately from the bank's common profile.
    return {width.values, width.codes, shape.values, shape.codes, gamma.values, gamma.codes};
}

void structure_block(const PCR& pcr, Project& project, std::vector<Pattern>& patterns, Refinement& refine,
                     std::size_t start, std::size_t end, bool multi) {
    auto structure = std::make_shared<Structure>();
    const auto name = pcr.next(start + 1, end);
    auto title = pcr.lines[name].text;
    if (lower(title).starts_with("name:")) {
        title = trim(std::string_view(title).substr(5));
    }
    const auto labels = words(title);
    if (labels.empty()) {
        pcr.fail("Missing FullProf phase name", name);
    }
    const auto base = safe_name(labels.front(), "phase");
    structure->name = base;
    for (unsigned i = 2; std::any_of(project.structures.begin(), project.structures.end(), [&](const auto& held) {
             return datablock_key(held->name.value(), "structure") == datablock_key(structure->name.value(), "structure");
         }); ++i) {
        const auto suffix = "_" + std::to_string(i);
        structure->name = base.substr(0, 31 - suffix.size()) + suffix;
    }
    auto phase = pcr.require("nat ", name, end);
    const auto options = pcr.after(phase, end, multi ? 10 : 15);
    const int count = integer(options[0], pcr.path.string());
    const auto jbt = multi ? 3U : 6U;
    const auto isy = multi ? 4U : 8U;
    const auto nvk = multi ? 8U : 12U;
    if (count < 1 || options[jbt] != 0. || options[isy] != 0. || options[isy + 1] != 0. ||
        options[nvk] != 0.) {
        pcr.fail("Unsupported FullProf phase type, symmetry operators or propagation vectors", phase);
    }
    if (options[1] != 0. || options[2] != 0.) {
        pcr.fail("FullProf restrained phases need manual conversion", phase);
    }
    Row contributions(patterns.size(), 1.);
    std::vector<Row> axes(patterns.size());
    if (multi) {
        const auto contribution = pcr.require("contributions", phase, end);
        contributions = pcr.after(contribution, end, patterns.size());
        auto options_line = contribution;
        for (std::size_t i = 0; i < patterns.size(); ++i) {
            if (contributions[i] == 1.) {
                const auto ref = pcr.require("irf ", options_line + 1, end);
                const auto pattern_flags = pcr.after(ref, end, 5);
                if (pattern_flags[0] != 0. || (pattern_flags[1] != 0. && pattern_flags[1] != patterns[i].profile) ||
                    pattern_flags[3] != 0. || pattern_flags[4] != 0.) {
                    pcr.fail("Unsupported FullProf phase-specific reflections or profile family", ref);
                }
                options_line = pcr.require("pr1 ", ref, end);
                axes[i] = pcr.after(options_line, end, 3);
            }
        }
    } else {
        axes[0] = {options[3], options[4], options[5]};
        if (options[13] != 0. && options[13] != patterns[0].profile) {
            pcr.fail("Unsupported FullProf phase-specific profile family", phase);
        }
    }
    const auto atom_header = pcr.require("atom ", phase, end);
    auto group = atom_header;
    while (group > phase && pcr.lines[--group].text.empty()) {
    }
    auto symbol = pcr.lines[group].text;
    std::string origin;
    if (const auto suffix = symbol.find(':'); suffix != std::string::npos) {
        origin = trim(std::string_view(symbol).substr(suffix + 1));
        symbol = trim(std::string_view(symbol).substr(0, suffix));
    }
    for (const auto& [old_name, current_name] :
         {std::pair{"F d 3 m", "F d -3 m"}, std::pair{"F m 3 m", "F m -3 m"}}) {
        if (same_space_group_name(symbol, old_name)) {
            symbol = current_name;
        }
    }
    auto setting = fullprof_default_space_group(symbol);
    if (setting && !origin.empty()) {
        setting = space_group_setting_for_code(setting->it_number, origin);
    }
    if (!setting) {
        pcr.fail("Unsupported FullProf space group " + symbol, group);
    }
    assign_space_group_setting(structure->space_group, *setting, true);

    auto first_cell = pcr.require("a ", atom_header, end);
    const auto cell = pair_after(pcr, first_cell, end, 6);
    refine.set(structure->cell.parameters(), cell.values, cell.codes);
    const auto positions = wyckoff_positions(*structure);
    int general = 0;
    for (const auto& position : positions) {
        general = std::max(general, position.multiplicity);
    }
    auto atom_line = atom_header;
    std::vector<std::pair<std::shared_ptr<AtomSite>, Coded>> occupancies;
    for (int i = 0; i < count; ++i) {
        atom_line = pcr.next(atom_line + 1, first_cell);
        const auto fields = words(pcr.lines[atom_line].text);
        if (fields.size() < 10) {
            pcr.fail("Incomplete FullProf atom row", atom_line);
        }
        const auto values = numbers(Words(fields.begin() + 2, fields.end()), pcr.path.string());
        atom_line = pcr.next(atom_line + 1, first_cell);
        const auto codes = pcr.row(atom_line, 5);
        auto site = std::make_shared<AtomSite>();
        site->id = fields[0];
        site->type_symbol = element(fields[1]);
        structure->atom_sites.push_back(site);
        refine.set(site->fract_x, {values[0], codes[0]});
        refine.set(site->fract_y, {values[1], codes[1]});
        refine.set(site->fract_z, {values[2], codes[2]});
        site->wyckoff_letter = inferred_wyckoff_letter(*structure, *site);
        const auto position = std::find_if(positions.begin(), positions.end(), [&](const WyckoffOption& candidate) {
            return candidate.letter == site->wyckoff_letter.value();
        });
        if (position == positions.end() || position->multiplicity <= 0) {
            pcr.fail("Cannot establish FullProf site multiplicity for " + fields[0], atom_line);
        }
        const auto factor = static_cast<double>(general) / position->multiplicity;
        occupancies.emplace_back(site, Coded{values[4] * factor, codes[4], factor});
        if (values[7] == 0.) {
            refine.set(site->adp_iso, {values[3], codes[3]});
        } else if (values[7] == 2.) {
            auto tensor = std::make_shared<AtomSiteAniso>();
            tensor->id = site->id.value();
            site->adp_type = "beta";
            structure->atom_site_aniso.push_back(tensor);
            const auto row = pair_after(pcr, atom_line, first_cell, 6);
            atom_line = pcr.next(pcr.next(atom_line + 1, first_cell) + 1, first_cell);
            refine.set(tensor->parameters(), row.values, row.codes);
        } else {
            pcr.fail("Unsupported FullProf atom model N_t=" + number_text(values[7]), atom_line);
        }
    }
    for (const auto& [site, occupancy] : occupancies) {
        if (occupancy.value < 0. || occupancy.value > 1.00015) {
            pcr.fail("FullProf occupancy normalization is ambiguous for " + site->id.value());
        }
        refine.set(site->occupancy, occupancy);
    }
    project.structures.push_back(structure);

    const auto profiles = headers(pcr, "------->", atom_header, end);
    std::size_t profile_number = 0;
    for (std::size_t i = 0; i < patterns.size(); ++i) {
        if (contributions[i] == 0.) {
            continue;
        }
        if (contributions[i] != 1. || profile_number >= profiles.size()) {
            pcr.fail("Invalid FullProf phase contributions", phase);
        }
        auto& pattern = patterns[i];
        const auto begin = profiles[profile_number++];
        const auto limit = profile_number < profiles.size() ? profiles[profile_number] : end;
        const auto my_cell = pair_after(pcr, pcr.require("a ", begin, limit), limit, 6);
        if (my_cell.values != cell.values || my_cell.codes != cell.codes) {
            pcr.fail("EDI shares one cell across the experiments of a structure", begin);
        }
        auto link = std::make_shared<LinkedStructure>();
        link->structure_id = structure->name.value();
        pattern.model->linked_structures.push_back(link);
        if (pattern.single_crystal()) {
            const auto scale = pair_after(pcr, pcr.require("sc1 ", begin, limit), limit, 6);
            const auto ext = pair_after(pcr, pcr.require("ext1 ", begin, limit), limit, 7);
            pcr.zero(scale.values, 1, 6, "single-crystal secondary scale factors");
            pcr.zero(scale.codes, 1, 6, "single-crystal secondary scale codes");
            pcr.zero(ext.values, 0, 7, "single-crystal extinction");
            pcr.zero(ext.codes, 0, 7, "single-crystal extinction code");
            refine.set(link->scale, scale.at(0));
            continue;
        }
        const auto scale = pair_after(pcr, pcr.require("scale ", begin, limit), limit, 6);
        pcr.zero(scale.values, 2, scale.values.size(), "phase strain or overall B factor");
        pcr.zero(scale.codes, 2, scale.codes.size(), "phase strain or overall B code");
        if (pattern.tof() && (scale.values[1] != 0. || scale.codes[1] != 0.)) {
            pcr.fail("Unsupported FullProf TOF extinction", begin);
        }
        refine.set(link->scale, scale.at(0, pattern.scale_factor));
        const auto shape = pair_after(pcr, pcr.require("pref1 ", begin, limit), limit, 6);
        const bool has_texture = (shape.values[0] != 0. && shape.values[0] != 1.) ||
                                 shape.values[1] != 0. || shape.codes[0] != 0. || shape.codes[1] != 0.;
        if (has_texture) {
            if (pattern.tof() || pattern.orientation != 1 || shape.values[0] <= 0. ||
                shape.values[1] < 0. || shape.values[1] > 1.) {
                pcr.fail("Unsupported FullProf preferred orientation", begin);
            }
            auto row = std::make_shared<PrefOrient>();
            row->structure_id = structure->name.value();
            row->index_h = integer(axes[i][0], pcr.path.string());
            row->index_k = integer(axes[i][1], pcr.path.string());
            row->index_l = integer(axes[i][2], pcr.path.string());
            if (row->index_h == 0 && row->index_k == 0 && row->index_l == 0) {
                pcr.fail("FullProf preferred orientation has a zero direction", begin);
            }
            pattern.model->preferred_orientation.push_back(row);
            refine.set(row->march_r, shape.at(0));
            refine.set(row->march_random_fract, shape.at(1));
        }
        if (pattern.tof()) {
            const auto sigma = pair_after(pcr, pcr.require("sigma-2 ", begin, limit), limit, 7);
            const auto gamma = pair_after(pcr, pcr.require("gamma-2 ", begin, limit), limit, 5);
            const auto signature = profile_signature(sigma, shape, gamma);
            if (pattern.profile_rows.empty()) {
                const auto abs_line = pcr.next(pcr.next(pcr.require("pref1 ", begin, limit) + 1, limit) + 1, limit) + 1;
                CodedRow absorption;
                if (abs_line < limit && pcr.lines[abs_line].text.find("ABS:") != std::string::npos) {
                    const auto tokens = words(pcr.lines[abs_line].text);
                    if (tokens.size() < 5) {
                        pcr.fail("Incomplete FullProf TOF absorption row", abs_line);
                    }
                    absorption.values = numbers(Words(tokens.begin(), tokens.begin() + 4), pcr.path.string());
                }
                tof_profile(pcr, pattern, refine, sigma, gamma, shape, absorption);
                pattern.profile_rows = signature;
            } else if (pattern.profile_rows != signature) {
                pcr.fail("EDI requires a common profile for the phases in a powder pattern", begin);
            }
        } else {
            const auto width = pair_after(pcr, pcr.require("u ", begin, limit), limit, 7);
            auto signature = profile_signature(width, shape, {});
            signature.push_back({scale.values[1], scale.codes[1]});
            if (pattern.profile_rows.empty()) {
                cw_profile(pcr, pattern, refine, scale, width, shape);
                pattern.profile_rows = std::move(signature);
            } else if (pattern.profile_rows != signature) {
                pcr.fail("EDI requires a common profile for the phases in a powder pattern", begin);
            }
        }
    }
    if (profile_number != profiles.size()) {
        pcr.fail("Unexpected FullProf phase profile block", phase);
    }
}

std::vector<std::size_t> phase_starts(const PCR& pcr) {
    std::vector<std::size_t> phases;
    std::size_t previous = pcr.lines.size();
    for (const auto i : headers(pcr, "data for phase", 0, pcr.lines.size())) {
        if (previous == pcr.lines.size() ||
            std::any_of(pcr.lines.begin() + static_cast<std::ptrdiff_t>(previous + 1),
                        pcr.lines.begin() + static_cast<std::ptrdiff_t>(i),
                        [](const Line& line) { return !line.text.empty(); })) {
            phases.push_back(i);
        }
        previous = i;
    }
    if (phases.empty()) {
        pcr.fail("No labelled FullProf phase blocks");
    }
    return phases;
}

std::vector<Pattern> patterns_from_header(const PCR& pcr, std::size_t end, bool multi, Project& project,
                                         Refinement& refine) {
    const auto job_header = pcr.require("job ", 0, end);
    const auto output_header = pcr.require("ipr ", job_header, end);
    const auto ncy = pcr.require("ncy ", output_header, end);
    std::size_t count = 1;
    Words npatt;
    Row weights;
    if (multi) {
        for (std::size_t i = 0; i < job_header; ++i) {
            auto fields = words(pcr.lines[i].text);
            if (!fields.empty() && lower(fields.front()) == "npatt") {
                npatt = std::move(fields);
            } else if (!fields.empty() && lower(fields.front()) == "w_pat") {
                weights = numbers(Words(fields.begin() + 1, fields.end()), pcr.path.string());
            }
        }
        if (npatt.size() < 2) {
            pcr.fail("Missing FullProf NPATT declaration");
        }
        const auto n = integer(number(npatt[1], pcr.path.string()), pcr.path.string());
        if (n < 1 || n > 99) {
            pcr.fail("Invalid FullProf pattern count");
        }
        count = static_cast<std::size_t>(n);
        if (npatt.size() < count + 2 || (!weights.empty() && weights.size() != count)) {
            pcr.fail("Invalid FullProf pattern flags or weights");
        }
        if (count > 1) {
            project.fitting_mode = "joint";
        }
    }
    std::vector<Pattern> patterns(count);
    for (std::size_t i = 0; i < count; ++i) {
        auto& pattern = patterns[i];
        pattern.model->name = count == 1 ? "pattern" : "pattern_" + std::to_string(i + 1);
        pattern.model->linked_structures.clear();
        if (multi) {
            const auto flag = npatt[i + 2];
            if (flag != "0" && flag != "1") {
                pcr.fail("Invalid FullProf pattern flag");
            }
            pattern.enabled = flag == "1";
            if (!weights.empty() && weights[i] <= 0. && pattern.enabled) {
                pcr.fail("A FullProf weight must be positive for an active pattern");
            }
            if (!weights.empty()) {
                pattern.model->dataset_weight = weights[i];
            }
        }
    }
    auto job_line = job_header;
    auto output_line = output_header;
    for (auto& pattern : patterns) {
        job_line = pcr.next(job_line + 1, output_header);
        const auto job = pcr.row(job_line, multi ? 14 : 19);
        const std::size_t uni = multi ? 10 : 15;
        pattern.job = integer(job[0], pcr.path.string());
        pattern.polarization_model = integer(job[multi ? 7 : 9], pcr.path.string());
        pattern.profile = integer(job[1], pcr.path.string());
        pattern.background = integer(job[multi ? 2 : 3], pcr.path.string());
        pattern.orientation = integer(job[multi ? 5 : 6], pcr.path.string());
        if (job[multi ? 4 : 5] != 0.) {
            pcr.fail("Unsupported FullProf additional scattering factors", job_line);
        }
        pattern.exclusions = integer(job[multi ? 3 : 4], pcr.path.string());
        if ((pattern.job < -1 || pattern.job > 1) || job[uni] != (pattern.tof() ? 1. : 0.) ||
            pattern.exclusions < 0 || pattern.background > 10000) {
            pcr.fail("Unsupported FullProf Job or axis Uni, or invalid point count", job_line);
        }
        output_line = pcr.next(output_line + 1, ncy);
        const auto output = pcr.row(output_line, multi ? 11 : 17);
        pattern.format = integer(output[multi ? 7 : 10], pcr.path.string());
        if (multi && job[12] != 0.) {
            pcr.fail("Unsupported FullProf anomalous-scattering input", job_line);
        }
    }
    if (multi) {
        auto file = pcr.require("file names of data", job_line, output_header);
        for (auto& pattern : patterns) {
            file = pcr.next(file + 1, output_header);
            const auto& name = pcr.lines[file].text;
            if (name.size() > 1 && ((name.front() == '"' && name.back() == '"') ||
                                      (name.front() == '\'' && name.back() == '\''))) {
                pattern.file = name.substr(1, name.size() - 2);
            } else {
                pattern.file = name;
            }
        }
    } else {
        patterns.front().default_companion = true;
        for (std::size_t i = 0; i < job_header; ++i) {
            const auto& comment = pcr.lines[i].comment;
            const auto marker = comment.find("dat-file:");
            if (marker != std::string::npos) {
                const auto offset = marker + 9;
                // The single-pattern comment is saved by FullProf as a record of the last run.
                // Its basename is useful for the installed suite examples, which share data files.
                const auto code = trim(std::string_view(pcr.lines[i].original_comment)
                                           .substr(offset, comment.find(',', offset) - offset));
                patterns.front().file = code;
            }
        }
        const auto phase = pcr.require("nat ", end, pcr.lines.size());
        const auto phase_flags = pcr.after(phase, pcr.lines.size(), 15);
        if (phase_flags[7] == 4. && patterns.front().profile == 0) {
            patterns.front().model->reflections.emplace();
        } else if (phase_flags[7] != 0.) {
            pcr.fail("Unsupported FullProf external reflection model (Irf)", phase);
        }
    }

    auto source_range = ncy;
    auto setup = output_line;
    auto calibration = ncy;
    auto points = ncy;
    auto exclusions = ncy;
    auto coeffs = ncy;
    for (auto& pattern : patterns) {
        if (pattern.single_crystal()) {
            configure_pattern(pcr, pattern, refine, 0, 0, 0, end, false);
            continue;
        }
        setup = pcr.require(pattern.tof() ? "bkpos " : "lambda1 ", setup + 1, ncy);
        calibration = pcr.require("zero ", calibration + 1, end);
        if (multi) {
            source_range = pcr.require(pattern.tof() ? "tof-min " : "thmin ", source_range + 1, end);
        }
        configure_pattern(pcr, pattern, refine, setup, source_range, calibration, end, !multi);
        if (pattern.background >= 2) {
            points = pcr.require("2theta/tof/e(kev)", points + 1, end);
        } else {
            coeffs = pcr.require("background coefficients", coeffs + 1, end);
        }
        read_background(pcr, pattern, refine, points, coeffs, end);
        if (pattern.exclusions > 0) {
            exclusions = pcr.require("excluded regions", exclusions + 1, end);
            auto row = exclusions;
            for (int i = 0; i < pattern.exclusions; ++i) {
                row = pcr.next(row + 1, end);
                const auto interval = pcr.row(row, 2);
                if (interval[0] >= interval[1]) {
                    pcr.fail("FullProf exclusion start must precede its end", row);
                }
                pattern.model->excluded_regions.push_back(std::make_shared<ExcludedRegion>(interval[0], interval[1]));
            }
        }
    }
    return patterns;
}

bool refinements_active(const PCR& pcr, std::size_t end) {
    for (std::size_t i = 0; i < end; ++i) {
        if (pcr.lines[i].comment.starts_with("number of refined parameters")) {
            const auto count = pcr.row(i, 1);
            if (count[0] < 0. || std::trunc(count[0]) != count[0]) {
                pcr.fail("Invalid FullProf number of refined parameters", i);
            }
            return count[0] > 0.;
        }
    }
    pcr.fail("Missing FullProf number of refined parameters");
}

}  // namespace

std::optional<SpaceGroupSettingName> fullprof_default_space_group(const std::string& symbol) {
    if (same_space_group_name(symbol, "F d -3 m")) {
        return space_group_setting_for_code(227, "2");
    }
    return space_group_setting_for_name(symbol);
}

Project import_fullprof_project(const std::string& path) {
    PCR pcr(path);
    try {
        if (pcr.lines.empty() || pcr.lines.front().text.empty()) {
            pcr.fail("Expected a classic or multi-pattern FullProf PCR file");
        }
        const auto phases = phase_starts(pcr);
        const auto phase_end = phases.front();
        const bool multi = pcr.header("nph ", 0, phase_end) != phase_end;
        const auto phase_declaration = pcr.require(multi ? "nph " : "job ", 0, phase_end);
        const auto flags = pcr.after(phase_declaration, phase_end, multi ? 7 : 19);
        const auto phase_count = integer(flags[multi ? 0 : 2], path);
        const auto cry = flags[multi ? 4 : 14];
        if ((cry != 0. && cry != 1.) || (multi && cry != 0.)) {
            pcr.fail("Unsupported FullProf refinement geometry or search algorithm (Cry)", phase_declaration);
        }
        if (phase_count < 1 || static_cast<std::size_t>(phase_count) != phases.size()) {
            pcr.fail("FullProf phase count disagrees with the phase blocks", phase_declaration);
        }
        pcr.refinement_enabled = refinements_active(pcr, phase_end);
        if (pcr.refinement_enabled && flags[multi ? 3 : 13] != 0.) {
            pcr.fail("FullProf parameter limits (Nre) need manual conversion", phase_declaration);
        }
        auto project = empty_project(safe_name(pcr.path.stem().string(), "fullprof"), "");
        const auto& title = pcr.lines.front().text;
        project.metadata.title = title.starts_with("COMM ") ? trim(std::string_view(title).substr(5)) : title;
        Refinement refine;
        auto patterns = patterns_from_header(pcr, phase_end, multi, project, refine);
        if (patterns.front().single_crystal() != (cry == 1.)) {
            pcr.fail("FullProf integrated-intensity settings Cry and Irf disagree", phase_declaration);
        }
        for (std::size_t i = 0; i < phases.size(); ++i) {
            structure_block(pcr, project, patterns, refine, phases[i], i + 1 < phases.size() ? phases[i + 1] : pcr.lines.size(), multi);
        }
        for (auto& pattern : patterns) {
            if (!pattern.enabled) {
                continue;
            }
            auto& exp = *pattern.model;
            if (exp.linked_structures.empty()) {
                pcr.fail("No FullProf phase contributes to " + exp.name.value());
            }
            if (pattern.single_crystal()) {
                reflection_data(pcr, pattern);
            } else {
                powder_data(pcr, pattern);
            }
            project.experiments.push_back(pattern.model);
        }
        if (project.experiments.empty()) {
            pcr.fail("No active FullProf patterns");
        }
        refinement_flags(pcr, project, refine, pcr.refinement_enabled);
        return project;
    } catch (const IoError&) {
        throw;
    } catch (const std::exception& error) {
        pcr.fail(error.what());
    }
}

}  // namespace edi::detail
