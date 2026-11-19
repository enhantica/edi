// SPDX-License-Identifier: BSD-3-Clause
#include "fullprof_project_io.hpp"

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
#include "edi/edit.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/project_archive.hpp"
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

std::string heading(const std::string& comment) {
    auto fields = words(lower(comment));
    if (!fields.empty() && fields.front() == "------->") {
        fields.erase(fields.begin());
    }
    if (!fields.empty() && fields.front() == "sig-2") {
        fields.front() = "sigma-2";
    }
    if (!fields.empty() && fields.front() == "gam-2") {
        fields.front() = "gamma-2";
    }
    std::string result;
    for (const auto& field : fields) {
        if (!result.empty()) {
            result += ' ';
        }
        result += field;
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
            const auto end = std::min({bang, line.find('#'), line.find("<-")});
            auto text = trim(std::string_view(line).substr(0, end));
            if (!text.empty() || !comment.empty()) {
                lines.push_back({std::move(text), heading(comment), std::move(comment), i});
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
    int converted_automatic_groups = 0;

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

struct TofResolution {
    std::array<double, 4> calibration{};
    std::array<double, 3> sigma{};
    std::array<double, 3> gamma{};
    std::array<double, 4> exponential{};
    double bank_angle = 0.;
    std::optional<std::array<double, 3>> range;
};

struct CwResolution {
    std::array<double, 5> widths{};
    std::array<double, 2> asymmetry{};
    std::optional<std::array<double, 3>> wavelengths;
    std::optional<double> polarization;
};

struct Pattern {
    std::shared_ptr<BraggPdExperiment> model = std::make_shared<BraggPdExperiment>();
    std::string file;
    int job = 0;
    int profile = 0;
    int background = 0;
    int exclusions = 0;
    int format = 0;
    int scattering_count = 0;
    int resolution_format = 0;
    std::optional<TofResolution> resolution;
    std::optional<CwResolution> cw_resolution;
    std::map<std::string, double> neutron_lengths;
    int absorption = 0;
    int orientation = 0;
    int polarization_model = 0;
    bool default_companion = false;
    bool enabled = true;
    double background_origin = 0.;
    double asymmetry_limit = 180.;
    double lo = 0.;
    double hi = 0.;
    double step = 0.;
    double scale_factor = 1.;
    std::vector<Row> profile_rows;
    std::map<std::string, Coded> overall_displacements;
    std::vector<Coded> reflection_scales;
    std::vector<Coded> reflection_extinction;
    int reflection_extinction_model = 0;

    bool tof() const { return job < 0; }
    bool xray() const { return job == 0 || job == 2; }
    bool single_crystal() const { return model->reflections.has_value(); }
    bool simulation() const { return !single_crystal() && std::abs(job) > 1; }
};

fs::path sibling_input(const PCR& pcr, const fs::path& name) {
    const auto directory = pcr.path.parent_path();
    if (fs::is_regular_file(directory / name)) {
        return directory / name;
    }
    const auto key = lower(name.string());
    fs::path match;
    for (const auto& entry : fs::directory_iterator(directory.empty() ? fs::path(".") : directory)) {
        if (entry.is_regular_file() && lower(entry.path().filename().string()) == key) {
            if (!match.empty()) {
                pcr.fail("Multiple FullProf companions match " + name.string());
            }
            match = entry.path();
        }
    }
    return match;
}

std::string companion_basename(std::string reference) {
    // Old FullProf files retain workstation paths. Resolve their basename
    // beside the control, as a portable project, without inspecting that path.
    const auto separator = reference.find_last_of("/\\");
    return separator == std::string::npos ? reference : reference.substr(separator + 1);
}

fs::path companion(const PCR& pcr, const Pattern& pattern) {
    const auto conventional = pcr.path.stem().string() + (pattern.single_crystal() ? ".int" : ".dat");
    if (pattern.default_companion) {
        if (const auto path = sibling_input(pcr, conventional); !path.empty()) {
            return path;
        }
    }
    if (!pattern.file.empty()) {
        const auto portable = companion_basename(pattern.file);
        const fs::path named(portable);
        if (portable.empty() || named == "." || named == ".." || portable.find(':') != std::string::npos) {
            pcr.fail("Companion data must be beside the PCR file: " + pattern.file);
        }
        if (named.has_extension()) {
            if (const auto path = sibling_input(pcr, named); !path.empty()) {
                return path;
            }
        } else if (pattern.single_crystal()) {
            if (const auto path = sibling_input(pcr, portable + ".int"); !path.empty()) {
                return path;
            }
        } else {
            for (const auto* suffix : {".dat", ".uxd", ".acq"}) {
                if (const auto path = sibling_input(pcr, portable + suffix); !path.empty()) {
                    return path;
                }
            }
        }
        pcr.fail("Missing FullProf companion " + named.string());
    }
    if (const auto path = sibling_input(pcr, conventional); !path.empty()) {
        return path;
    }
    if (!pattern.single_crystal()) {
        for (const auto* suffix : {".uxd", ".acq"}) {
            if (const auto path = sibling_input(pcr, pcr.path.stem().string() + suffix); !path.empty()) {
                return path;
            }
        }
    }
    pcr.fail("Missing FullProf companion " + conventional);
}

fs::path resolution_path(const PCR& pcr, std::size_t declaration) {
    auto name = pcr.lines[declaration].text;
    if (name.size() >= 2 && (name.front() == '\'' || name.front() == '"') && name.back() == name.front()) {
        name = name.substr(1, name.size() - 2);
    }
    const auto portable = companion_basename(name);
    const fs::path relative(portable);
    if (relative.empty() || relative == "." || relative == ".." || portable.find(':') != std::string::npos) {
        pcr.fail("FullProf resolution file must be beside the PCR file: " + name, declaration);
    }
    if (const auto found = sibling_input(pcr, relative); !found.empty()) {
        return found;
    }
    pcr.fail("Missing FullProf resolution companion " + portable, declaration);
}

TofResolution tof_resolution(const PCR& pcr, std::size_t declaration) {
    const auto path = resolution_path(pcr, declaration);
    auto source = input(path);
    TofResolution result;
    std::set<std::string> seen;
    bool reading = false;
    for (std::string line; std::getline(source, line);) {
        const auto fields = words(std::string_view(line).substr(0, line.find_first_of("!#")));
        if (fields.empty()) {
            continue;
        }
        const auto label = lower(fields[0]);
        if (label == "nprof") {
            const auto options = numbers(Words(fields.begin() + 1, fields.end()), path.string());
            if (reading || options != Row{9.}) {
                pcr.fail("FullProf polynomial TOF resolution requires NPROF 9", declaration);
            }
            reading = true;
            continue;
        }
        if (!reading) {
            continue;
        }
        if (label == "end") {
            break;
        }
        if (!seen.insert(label).second) {
            pcr.fail("Duplicate FullProf resolution directive " + fields[0], declaration);
        }
        const auto values = numbers(Words(fields.begin() + 1, fields.end()), path.string());
        if (label == "d2tof" && values.size() >= 2 && values.size() <= 4) {
            result.calibration = {values.size() >= 3 ? values.back() : 0., values[0], values[1],
                                  values.size() == 4 ? values[2] : 0.};
        } else if (label == "zd2tof" && values.size() == 3) {
            result.calibration = {values[0], values[1], values[2], 0.};
        } else if (label == "twoth" && values.size() == 1) {
            result.bank_angle = values[0];
        } else if (label == "sigma" && values.size() == result.sigma.size()) {
            std::copy(values.begin(), values.end(), result.sigma.begin());
        } else if (label == "gamma" && values.size() == result.gamma.size()) {
            std::copy(values.begin(), values.end(), result.gamma.begin());
        } else if (label == "alfbe" && values.size() == result.exponential.size()) {
            std::copy(values.begin(), values.end(), result.exponential.begin());
        } else if (label == "tofrg" && values.size() == 3 && values[0] < values[2] && values[1] > 0.) {
            result.range = std::array{values[0], values[1], values[2]};
        } else {
            pcr.fail("Unsupported FullProf resolution directive " + fields[0], declaration);
        }
    }
    if (!reading || (!seen.contains("d2tof") && !seen.contains("zd2tof")) ||
        (seen.contains("d2tof") && seen.contains("zd2tof")) ||
        !seen.contains("twoth") || !seen.contains("sigma") || !seen.contains("gamma") ||
        !seen.contains("alfbe") || result.bank_angle <= 0.) {
        pcr.fail("Incomplete FullProf polynomial TOF resolution data", declaration);
    }
    return result;
}

CwResolution cw_resolution(const PCR& pcr, const Pattern& pattern, std::size_t declaration) {
    const auto path = resolution_path(pcr, declaration);
    auto source = input(path);
    CwResolution result;
    std::vector<Row> widths;
    for (std::string line; std::getline(source, line);) {
        const auto fields = words(std::string_view(line).substr(0, line.find_first_of("!#")));
        if (fields.empty()) {
            continue;
        }
        if (lower(line).starts_with("resolution function") && widths.empty()) {
            continue;  // Legacy IRFs put the instrument description before JOBT.
        }
        const auto label = lower(fields[0]);
        if (label == "end") {
            break;
        }
        if (label == "jobt" || label == "geom") {
            const auto value = fields.size() > 1 ? lower(fields[1]) : "";
            if ((label == "geom" && value != "deby" && !(value == "bragg" && !pattern.xray())) ||
                (label == "jobt" && value != (pattern.xray() ? "xray" : "neut"))) {
                pcr.fail("Unsupported FullProf resolution geometry or probe", declaration);
            }
            continue;
        }
        if (label == "wave" || label == "prof" || label == "cthm" || label == "thrg" || label == "asym") {
            const auto values = numbers(Words(fields.begin() + 1, fields.end()), path.string());
            if (label == "wave" && values.size() == 3) {
                result.wavelengths = std::array{values[0], values[1], values[2]};
            } else if (label == "prof" && !values.empty() && values[0] == 7.) {
                // TCH does not use the three generic Shape parameters.
            } else if (label == "cthm" && values.size() == 1 && values[0] >= 0. && values[0] <= 1.) {
                result.polarization = values[0];
            } else if (label == "asym" && values.size() == 2) {
                result.asymmetry = {values[0], values[1]};
            } else if (label != "thrg" || values.size() != 3) {
                pcr.fail("Unsupported FullProf CW resolution directive " + fields[0], declaration);
            }
        } else if (fields.size() == 6 && fields.front().find_first_of("0123456789+-.") == 0) {
            widths.push_back(numbers(fields, path.string()));
        } else {
            pcr.fail("Unsupported FullProf CW resolution record " + fields[0], declaration);
        }
    }
    if (widths.empty() || widths.size() > 2 || widths[0][5] != 0. ||
        (widths.size() == 2 && widths[1] != widths[0] &&
         (!result.wavelengths || ((*result.wavelengths)[2] != 0. &&
                                 (*result.wavelengths)[0] != (*result.wavelengths)[1])))) {
        pcr.fail("FullProf CW resolution requires one supported width law for both wavelengths", declaration);
    }
    std::copy_n(widths[0].begin(), result.widths.size(), result.widths.begin());
    return result;
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
        if (text.empty() || text.size() > 80 || text.size() % 8 != 0) {
            throw IoError(path.string() + ": invalid fixed-width D1A/D2B weight and intensity pairs");
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

struct Grid {
    double first;
    double step;
    std::size_t count;
};

Grid uniform_grid(double first, double step, double last, const fs::path& path) {
    const double count = std::floor((last - first) / step + 1.5);
    if (!std::isfinite(first) || !std::isfinite(last) || step <= 0. || first > last ||
        !(count >= 1.) || count > 10000000.) {
        throw IoError(path.string() + ": invalid FullProf start, step and end");
    }
    return {first, step, static_cast<std::size_t>(count)};
}

Grid grid_from_line(const std::string& line, const fs::path& path) {
    std::istringstream stream(line);
    stream.imbue(std::locale::classic());
    double first = 0., step = 0., last = 0.;
    if (!(stream >> first >> step >> last)) {
        throw IoError(path.string() + ": expected the FullProf start, step and end header");
    }
    return uniform_grid(first, step, last, path);
}

Data stepped_data(const fs::path& path) {
    auto file = input(path);
    std::string line;
    std::optional<Grid> grid;
    for (int i = 0; i <= 7 && std::getline(file, line); ++i) {
        std::istringstream header(line);
        header.imbue(std::locale::classic());
        double first = 0., step = 0., last = 0.;
        if (header >> first >> step >> last) {
            grid = uniform_grid(first, step, last, path);
            break;
        }
    }
    if (!grid) {
        throw IoError(path.string() + ": expected the FullProf start, step and end header");
    }
    Data result;
    for (double y; result.x.size() < grid->count && file >> y;) {
        result.push(grid->first + static_cast<double>(result.x.size()) * grid->step, y, std::sqrt(std::max(1., y)));
    }
    if (result.x.size() != grid->count) {
        throw IoError(path.string() + ": intensity count disagrees with the FullProf data header");
    }
    return result;
}

std::string data_line(std::istream& file, const fs::path& path) {
    std::string line;
    if (!std::getline(file, line)) {
        throw IoError(path.string() + ": truncated FullProf data");
    }
    if (!line.empty() && line.back() == '\r') {
        line.pop_back();
    }
    return line;
}

Row packed_columns(std::istream& file, const fs::path& path, std::size_t count, std::size_t width) {
    Row result;
    result.reserve(count);
    while (result.size() < count) {
        const auto line = data_line(file, path);
        const auto columns = std::min<std::size_t>(10, count - result.size());
        if (line.size() < columns * width) {
            throw IoError(path.string() + ": incomplete fixed-width FullProf data record");
        }
        for (std::size_t i = 0; i < columns; ++i) {
            result.push_back(number(trim(std::string_view(line).substr(i * width, width)), path.string()));
        }
    }
    return result;
}

Data weighted_counts(const fs::path& path, bool d20) {
    auto file = input(path);
    Grid grid;
    const std::size_t stride = d20 ? 10 : 8;
    if (d20) {
        const auto runs = words(data_line(file, path));
        if (runs.empty() || number(runs.front(), path.string()) != 1.) {
            throw IoError(path.string() + ": expected a single ILL run");
        }
        data_line(file, path);
        data_line(file, path);
        const auto header = words(data_line(file, path));
        const auto count = words(data_line(file, path));
        if (header.size() < 9 || count.empty()) {
            throw IoError(path.string() + ": incomplete ILL D20 time and step header");
        }
        const int n = integer(number(count.front(), path.string()), path.string());
        const auto first = number(header[2], path.string());
        const auto step = number(header[8], path.string());
        if (n < 1) {
            throw IoError(path.string() + ": invalid ILL D20 point count");
        }
        grid = uniform_grid(first, step, first + (n - 1) * step, path);
    } else {
        grid = grid_from_line(data_line(file, path), path);
    }
    Data result;
    while (result.x.size() < grid.count) {
        const auto line = data_line(file, path);
        const auto columns = std::min<std::size_t>(10, grid.count - result.x.size());
        if (line.size() < stride * columns) {
            throw IoError(path.string() + ": incomplete FullProf weight and intensity record");
        }
        for (std::size_t i = 0; i < columns; ++i) {
            const auto pair = std::string_view(line).substr(i * stride, stride);
            const auto fields = words(pair);
            const auto weight = std::max(1., number(fields.size() == 2 ? fields[0] : trim(pair.substr(0, 2)),
                                                   path.string()));
            const auto intensity = number(fields.size() == 2 ? fields[1] : trim(pair.substr(2)), path.string());
            const auto y = intensity > 0.00001 ? intensity : 1.;
            result.push(grid.first + static_cast<double>(result.x.size()) * grid.step, y, std::sqrt(y / weight));
        }
    }
    return result;
}

Data two_axis_data(const fs::path& path) {
    auto file = input(path);
    for (int i = 0; i < 3; ++i) {
        data_line(file, path);
    }
    const auto header = numbers(words(data_line(file, path)), path.string());
    if (header.size() < 6) {
        throw IoError(path.string() + ": incomplete two-axis FullProf monitor header");
    }
    const auto grid = grid_from_line(data_line(file, path), path);
    if (static_cast<double>(grid.count) != header[0]) {
        throw IoError(path.string() + ": two-axis FullProf data count disagrees with the grid");
    }
    const auto y = packed_columns(file, path, grid.count, 8);
    const bool supplied = header[3] != 0.;
    const auto uncertainties = supplied ? packed_columns(file, path, grid.count, 8) : Row{};
    const double monitor_ratio = header[4] > 1. && header[5] > 1. ? header[4] / header[5] : 1.;
    Data result;
    for (std::size_t i = 0; i < grid.count; ++i) {
        const auto intensity = supplied ? std::max(y[i], 0.0001) : y[i];
        const auto sigma = supplied ? (std::abs(uncertainties[i]) < 0.001 ? 1. : std::abs(uncertainties[i]))
                                    : std::sqrt(intensity * monitor_ratio);
        result.push(grid.first + static_cast<double>(i) * grid.step, intensity, sigma);
    }
    return result;
}

Data dmc_data(const fs::path& path) {
    auto file = input(path);
    data_line(file, path);
    data_line(file, path);
    const auto grid = grid_from_line(data_line(file, path), path);
    const auto y = packed_columns(file, path, grid.count, 8);
    const auto sigma = packed_columns(file, path, grid.count, 8);
    Data result;
    for (std::size_t i = 0; i < grid.count; ++i) {
        result.push(grid.first + static_cast<double>(i) * grid.step, y[i], std::abs(sigma[i]));
    }
    return result;
}

Data gsas_data(const fs::path& path) {
    auto file = input(path);
    std::string line;
    std::getline(file, line);
    std::getline(file, line);
    const auto header = words(line);
    if (header.size() < 9 || header[0] != "BANK" ||
        (header[4] != "CONST" && header[4] != "RALF") || header.back() != "ALT") {
        throw IoError(path.string() + ": expected a single GSAS CONST/ALT or RALF/ALT bank");
    }
    const auto count = integer(number(header[2], path.string()), path.string());
    const bool ralf = header[4] == "RALF";
    Data raw;
    if (ralf) {
        while (std::getline(file, line)) {
            for (std::size_t start = 0; start < line.size(); start += 20) {
                const auto field = std::string_view(line).substr(start, 20);
                if (trim(field).empty()) {
                    continue;
                }
                if (field.size() != 20) {
                    throw IoError(path.string() + ": incomplete GSAS RALF/ALT record");
                }
                raw.push(number(trim(field.substr(0, 8)), path.string()), number(trim(field.substr(8, 7)), path.string()),
                         number(trim(field.substr(15)), path.string()));
            }
        }
    } else {
        for (double x, y, sigma; file >> x >> y >> sigma;) {
            raw.push(x, y, sigma);
        }
    }
    if (count < (ralf ? 2 : 1) || raw.x.size() != static_cast<std::size_t>(count)) {
        throw IoError(path.string() + ": truncated or additional GSAS bank data");
    }
    Data result;
    const auto points = raw.x.size() - (ralf ? 1U : 0U);
    for (std::size_t i = 0; i < points; ++i) {
        // RALF records are leading bin edges in 1/32 microsecond units.
        // FullProf normalizes the integrated counts by the forward width
        // and omits the last edge, which has no following bin boundary.
        const double factor = ralf ? 32. / (10. * (raw.x[i + 1] - raw.x[i])) : 1.;
        if (!std::isfinite(factor) || factor <= 0.) {
            throw IoError(path.string() + ": invalid GSAS RALF bin width");
        }
        result.push(raw.x[i] / 32., raw.y[i] * factor, raw.sigma[i] * factor);
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

PlainDataLoad fullprof_reflections(const BraggPdExperiment& experiment, const fs::path& path) {
    auto source = input(path);
    std::string text;
    bool annotated = false;
    std::size_t row = 0;
    for (std::string line; std::getline(source, line);) {
        if (++row > 3) {
            const auto annotation = line.find("<- Dubious reflection");
            if (annotation != std::string::npos) {
                line.resize(annotation);
                annotated = true;
            }
        }
        text += line + '\n';
    }
    if (!annotated) {
        return experiment_with_plain_data(experiment, path.string(), false);
    }
    // FullProf may append a diagnostic outside the formatted fields of a valid INT row.
    // Normalize that annotation in a private copy and let the normal reflection reader validate the fields.
    struct Capture {
        std::string directory = fresh_archive_directory("fullprof-int");
        ~Capture() { remove_archive_directory(directory); }
    } capture;
    const auto copy = fs::path(capture.directory) / path.filename();
    try {
        std::ofstream normalized(copy);
        normalized.exceptions(std::ios::badbit | std::ios::failbit);
        normalized << text;
        normalized.close();
        return experiment_with_plain_data(experiment, copy.string(), path.string(), false);
    } catch (const std::ios_base::failure&) {
        throw IoError(path.string() + ": unable to normalize FullProf reflection annotations");
    } catch (const IoError& issue) {
        std::string diagnostic = issue.what();
        if (const auto marker = diagnostic.find(copy.string()); marker != std::string::npos) {
            diagnostic.replace(marker, copy.string().size(), path.string());
        }
        throw IoError(diagnostic);
    }
}

void reflection_data(const PCR& pcr, Pattern& pattern, Refinement& refine, Project& project) {
    const auto path = companion(pcr, pattern);
    auto file = input(path);
    std::string header;
    if (!std::getline(file, header) || !std::getline(file, header) || !std::getline(file, header)) {
        pcr.fail("Incomplete FullProf reflection data header in " + path.filename().string());
    }
    const auto controls = words(header);
    if (controls.empty() || (!pattern.tof() && controls.size() < 3) ||
        (controls.size() >= 3 && number(controls[2], path.string()) != 0.)) {
        pcr.fail("Unsupported FullProf reflection geometry (Ipow) in " + path.filename().string());
    }
    const auto intensity_type = controls.size() > 1 ? number(controls[1], path.string()) : 0.;
    if (intensity_type != 0. && (intensity_type != 1. || pattern.tof())) {
        pcr.fail("Unsupported FullProf reflection intensity selector in " + path.filename().string());
    }
    auto loaded = fullprof_reflections(*pattern.model, path);
    if (loaded.experiment.calculation_only || loaded.dataset_codes.size() != loaded.more.size() + 1) {
        pcr.fail("FullProf reflection datasets require observed data and one scale per dataset");
    }
    const auto add_dataset = [&](const std::shared_ptr<BraggPdExperiment>& exp, BraggPdExperiment& data,
                                 std::int32_t code) {
        if (code < 1 || static_cast<std::size_t>(code) > pattern.reflection_scales.size()) {
            pcr.fail("FullProf INT dataset code has no matching scale: " + std::to_string(code));
        }
        if (intensity_type == 1.) {
            auto& rows = data.reflections.value();
            auto f_squared = rows.intensity_meas.get();
            auto sigma = rows.intensity_meas_su.get();
            for (std::size_t i = 0; i < f_squared.size(); ++i) {
                const auto amplitude = f_squared[i];
                if (amplitude <= 0.) {
                    pcr.fail("Nonpositive FullProf F amplitude needs reflection exclusion");
                }
                f_squared[i] = amplitude * amplitude;
                sigma[i] *= 2. * amplitude;
            }
            rows.intensity_meas = std::move(f_squared);
            rows.intensity_meas_su = std::move(sigma);
        }
        exp->reflections = std::move(data.reflections);
        exp->name = data.name.value();
        exp->data_file = loaded.file_name;
        exp->calculation_only = false;
        if (!pattern.tof()) {
            const auto& wavelength = data.instrument.setup_wavelength;
            if (!wavelength || wavelength->value <= 0.) {
                pcr.fail("Missing positive wavelength in FullProf reflection data " + path.filename().string());
            }
            exp->instrument.setup_wavelength->value = wavelength->value.get();
        }
        auto link = exp->linked_structures[0];
        refine.set(link->scale, pattern.reflection_scales[static_cast<std::size_t>(code - 1)]);
        if (pattern.reflection_extinction_model == 1) {
            select_extinction(*exp, "larson-isotropic");
            refine.set(exp->extinction.coefficient, pattern.reflection_extinction.front());
        } else if (pattern.reflection_extinction_model == 4) {
            select_extinction(*exp, "larson-anisotropic");
            auto& extinction = exp->extinction;
            const std::array<OptionalParameter*, 6> fields{
                &extinction.coefficient_11, &extinction.coefficient_22, &extinction.coefficient_33,
                &extinction.coefficient_12, &extinction.coefficient_13, &extinction.coefficient_23};
            for (std::size_t i = 0; i < fields.size(); ++i) {
                refine.set(*fields[i], pattern.reflection_extinction[i]);
            }
        }
        project.experiments.push_back(exp);
    };
    add_dataset(pattern.model, loaded.experiment, loaded.dataset_codes.front());
    for (std::size_t i = 0; i < loaded.more.size(); ++i) {
        auto model = std::make_shared<BraggPdExperiment>(*pattern.model);
        add_dataset(model, loaded.more[i], loaded.dataset_codes[i + 1]);
    }
    if (pattern.model->reflns_threshold_sigma) {
        project.refine_ls_threshold_sigma = pattern.model->reflns_threshold_sigma;
    }
    if (!loaded.more.empty()) {
        project.fitting_mode = "joint";
    }
}

void powder_data(const PCR& pcr, Pattern& pattern) {
    const auto path = companion(pcr, pattern);
    Data source;
    switch (pattern.format) {
        case 0: source = stepped_data(path); break;
        case 1: source = weighted_counts(path, false); break;
        case 3: source = weighted_counts(path, true); break;
        case 5: source = two_axis_data(path); break;
        case 6: source = ial_data(path); break;
        case 8: source = dmc_data(path); break;
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
        if (source.sigma[i] == 0. && std::any_of(pattern.model->excluded_regions.begin(),
                                                pattern.model->excluded_regions.end(), [x](const auto& region) {
                return x >= region->first.get() && x <= region->second.get();
            })) {
            continue;  // No weight was supplied for a point the source explicitly excludes.
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
    // FullProf can exclude a channel even when a narrow interval lies entirely between its
    // recorded coordinate and the edge of its bin. Carry that observation mask into EDI.
    for (const auto& region : exp.excluded_regions) {
        const auto first = region->first.get();
        const auto second = region->second.get();
        const auto after = std::lower_bound(data.x.begin(), data.x.end(), first);
        if (after == data.x.begin() || after == data.x.end() || *after <= second) {
            continue;
        }
        const auto before = *std::prev(after);
        const auto boundary = (before + *after) / 2.;
        if (second <= boundary) {
            region->first = before;
        } else if (first >= boundary) {
            region->second = *after;
        }
    }
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

Coded rotated_code(const PCR& pcr, double value, const Row& codes, const Row& factors,
                   std::size_t line) {
    double direction = 0.;
    double code = 0.;
    const auto group = [](double encoded) { return std::floor(std::abs(encoded) / 10.); };
    const auto shift = [&](double encoded) {
        return std::copysign(std::abs(encoded) - 10. * group(encoded), encoded);
    };
    for (std::size_t i = 0; i < factors.size(); ++i) {
        if (factors[i] == 0. || codes[i] == 0.) {
            continue;
        }
        if (code != 0. && (group(code) == 0. || group(code) != group(codes[i]))) {
            pcr.fail("A FullProf symmetry image mixes independent refinement directions", line);
        }
        code = codes[i];
        const auto step = shift(code);
        if (step == 0.) {
            pcr.fail("A FullProf refinement codeword has a zero shift", line);
        }
        direction += factors[i] * step;
    }
    if (direction == 0.) {
        return {value, 0.};
    }
    return {value, code, direction / shift(code)};
}

CodedRow pair_after(const PCR& pcr, std::size_t header, std::size_t end, std::size_t count,
                    std::size_t minimum_codes = 0) {
    const auto first = pcr.next(header + 1, end);
    auto codewords = pcr.after(first, end, minimum_codes == 0 ? count : minimum_codes);
    if (codewords.size() < count) {
        codewords.resize(count);
    }
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
        if (it == refinement.codes.end() || !entry.refinable ||
            entry.parameter->dependence != Dependence::Independent) {
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
    if (pattern.background != 0 && pattern.background != -3 && pattern.background != -5) {
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
    const int groups = chebyshev ? 4 : pattern.background == -3 ? 2 : 1;
    for (int group = 0; group < groups; ++group) {
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
    if (pattern.xray()) {
        exp.xray_form_factor = "it1992";
        exp.xray_dispersion = "sasaki1989";
    } else {
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
    pattern.step = limits[offset + 1];
    pattern.hi = limits[offset + 2];
    if (pattern.lo >= pattern.hi) {
        pcr.fail("Invalid FullProf calculation range", range);
    }
    auto values = pcr.after(setup, end, pattern.tof() ? 3 : 8);
    if (pattern.cw_resolution) {
        if (pattern.cw_resolution->wavelengths) {
            std::copy(pattern.cw_resolution->wavelengths->begin(), pattern.cw_resolution->wavelengths->end(), values.begin());
        }
        if (pattern.cw_resolution->polarization) {
            values[5] = *pattern.cw_resolution->polarization;
        }
    }
    const auto zero = pcr.after(calibration, end, pattern.tof() ? 7 : 9);
    if (pattern.tof()) {
        pattern.background_origin = values[0];
        exp.peak.cutoff_fwhm = values[1];
        pattern.absorption = integer(values[2], pcr.path.string());
        if (zero.size() != 7 && zero.size() != 9) {
            pcr.fail("Unexpected FullProf TOF calibration columns", calibration);
        }
        const auto base = pattern.resolution.value_or(TofResolution{});
        refine.set(instrument.calib_d_to_tof_offset, {zero[0] + base.calibration[0], zero[1]});
        refine.set(instrument.calib_d_to_tof_linear, {zero[2] + base.calibration[1], zero[3]});
        refine.set(instrument.calib_d_to_tof_quadratic, {zero[4] + base.calibration[2], zero[5]});
        refine.set(instrument.calib_d_to_tof_reciprocal,
                   {base.calibration[3] + (zero.size() == 9 ? zero[6] : 0.), zero.size() == 9 ? zero[7] : 0.});
        instrument.setup_twotheta_bank.value = pattern.resolution ? base.bank_angle : zero.back();
        if (base.range) {
            pattern.lo = (*base.range)[0];
            pattern.step = (*base.range)[1];
            pattern.hi = (*base.range)[2];
        }
    } else {
        pattern.background_origin = values[3];
        exp.peak.cutoff_fwhm = values[4];
        pattern.asymmetry_limit = values[7];
        if (values[0] <= 0. || zero[8] != 0. ||
            (values.size() >= 10 && values[9] != 0. && values[9] != values[6])) {
            pcr.fail("Unsupported FullProf wavelength, secondary absorption or additional CW instrument terms", setup);
        }
        refine.set(instrument.setup_wavelength, spec::instrument_wavelength, {zero[6] > 0. && !(pattern.cw_resolution && pattern.cw_resolution->wavelengths)
                                                                         ? zero[6] : values[0], zero[7]});
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
            if (pattern.xray() && pattern.polarization_model != 0) {
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
    const auto base = pattern.cw_resolution.value_or(CwResolution{});
    const bool fcj_from_pcr = shape.values.size() >= 8 && shape.codes.size() >= 8 && (nonzero(6) || nonzero(7));
    pcr.zero(width.values, 7, width.values.size(), "CWL anisotropic size model");
    pcr.zero(width.codes, 6, width.codes.size(), "CWL size refinement");
    if (pattern.profile != 7) {
        pcr.zero(width.values, 5, 7, "non-TCH size coefficients");
        pcr.zero(width.codes, 5, 6, "non-TCH size refinement");
    }
    const bool fcj = fcj_from_pcr || base.asymmetry[0] != 0. || base.asymmetry[1] != 0.;
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
    const auto width_at = [&](std::size_t column) {
        auto coded = width.at(column);
        coded.value += base.widths[column];
        if (pattern.profile == 7 && (column == 0 || column == 2)) {
            coded.value += width.values[5];
            if (width.codes[5] != 0.) {
                if (coded.code != 0.) {
                    pcr.fail("FullProf Gaussian size and Caglioti width both vary");
                }
                coded.code = width.codes[5];
            }
        }
        return coded;
    };
    refine.set(peak.broad_gauss_u, spec::peak_broad_gauss_u, width_at(0));
    refine.set(peak.broad_gauss_v, spec::peak_broad_gauss_v, width_at(1));
    refine.set(peak.broad_gauss_w, spec::peak_broad_gauss_w, width_at(2));
    if (peak.broad_lorentz_x) {
        refine.set(peak.broad_lorentz_x, width_at(3));
        refine.set(peak.broad_lorentz_y, width_at(4));
    } else {
        // FullProf Npr 5 uses X for the angular slope of the mixing coefficient.
        if (peak.mixing_eta_0) {
            refine.set(peak.mixing_eta_0, scale.at(1));
            refine.set(peak.mixing_eta_1, width_at(3));
            pcr.zero(width.values, 4, 5, "CWL width Y");
            pcr.zero(width.codes, 4, 5, "CWL width Y code");
        } else {
            pcr.zero(width.values, 3, 5, "CWL width X/Y");
            pcr.zero(width.codes, 3, 5, "CWL width X/Y code");
        }
    }
    if (fcj) {
        std::array<Coded, 2> apertures{};
        for (std::size_t column = 0; column < apertures.size(); ++column) {
            apertures[column] = shape.values.size() > 6 + column && shape.codes.size() > 6 + column
                ? shape.at(6 + column) : Coded{0., 0.};
            apertures[column].value += base.asymmetry[column];
        }
        if ((apertures[0].value == 0.) != (apertures[1].value == 0.)) {
            const auto present = apertures[0].value != 0. ? 0U : 1U;
            if (apertures[1U - present].code != 0.) {
                pcr.fail("An active zero FullProf FCJ aperture changes the parameterization");
            }
            // FullProf uses the retained aperture as the sum of equal physical
            // apertures in its one-parameter mode.
            auto shared = apertures[present];
            shared.value /= 2.;
            shared.multiplier /= 2.;
            if (shared.code != 0. && std::abs(shared.code) < 10.) {
                // Allocate an internal shared group for one automatically assigned
                // source direction that now drives two native fields.
                const double group = 1.e10 + 10. * ++refine.converted_automatic_groups;
                shared.code = std::copysign(group + std::abs(shared.code), shared.code);
            }
            apertures.fill(shared);
        }
        refine.set(peak.asym_fcj_1, apertures[0]);
        refine.set(peak.asym_fcj_2, apertures[1]);
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
    const auto base = pattern.resolution.value_or(TofResolution{});
    auto sigma2 = sigma.at(0);
    auto sigma1 = sigma.at(1);
    auto sigma0 = sigma.at(2);
    sigma2.value += base.sigma[0] - sigma.values[5];
    sigma1.value += base.sigma[1] - sigma.values[4];
    sigma0.value += base.sigma[2];
    refine.set(peak.broad_gauss_sigma_2, sigma2);
    refine.set(peak.broad_gauss_sigma_1, sigma1);
    refine.set(peak.broad_gauss_sigma_0, sigma0);
    refine.set(peak.broad_gauss_strain, sigma.at(4));
    refine.set(peak.broad_gauss_size, sigma.at(5));
    auto gamma2 = gamma.at(0);
    auto gamma1 = gamma.at(1);
    auto gamma0 = gamma.at(2);
    gamma2.value += base.gamma[0] - gamma.values[4];
    gamma1.value += base.gamma[1] - gamma.values[3];
    gamma0.value += base.gamma[2];
    refine.set(peak.broad_lorentz_gamma_2, gamma2);
    refine.set(peak.broad_lorentz_gamma_1, gamma1);
    refine.set(peak.broad_lorentz_gamma_0, gamma0);
    refine.set(peak.broad_lorentz_strain, gamma.at(3));
    refine.set(peak.broad_lorentz_size, gamma.at(4));
    if (pattern.profile != 7) {
        const auto exponential = [&](std::size_t column) {
            auto coded = shape.at(column + 2);
            coded.value += base.exponential[column];
            return coded;
        };
        refine.set(peak.rise_alpha_0, exponential(0));
        refine.set(peak.decay_beta_0, exponential(1));
        refine.set(peak.rise_alpha_1, exponential(2));
        refine.set(peak.decay_beta_1, exponential(3));
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
    const auto charge = type.find_first_of("+-");
    if (charge != std::string::npos && charge > 0 && charge + 1 < type.size() &&
        type.find_first_not_of("0123456789", charge + 1) == std::string::npos) {
        return type.substr(0, charge) + type.substr(charge + 1) + type[charge];
    }
    const auto isotope_at = type.find_first_of("0123456789");
    if (isotope_at != std::string::npos && isotope_at > 0 &&
        type.find_first_not_of("0123456789", isotope_at) == std::string::npos) {
        const auto isotope = type.substr(isotope_at) + type.substr(0, isotope_at);
        if (import_atomic_mass(isotope)) {
            return isotope;
        }
    }
    return type;
}

std::vector<Row> profile_signature(const CodedRow& width, const CodedRow& shape, const CodedRow& gamma) {
    // Scale, orientation and absorption are handled separately from the bank's common profile.
    return {width.values, width.codes, shape.values, shape.codes, gamma.values, gamma.codes};
}

struct MagneticType {
    std::string element;
    std::string ion;
    std::optional<crysta::MagneticRadialCoefficients> radial;
};

MagneticType magnetic_type(const PCR& pcr, std::string label, std::size_t source) {
    const char family = label.empty() ? '\0' : static_cast<char>(std::toupper(static_cast<unsigned char>(label.front())));
    const auto radial = family == 'J' ? fullprof_magnetic_radial(label) : std::nullopt;
    if (family != 'M' && !radial) {
        pcr.fail("Unsupported FullProf magnetic form factor " + label, source);
    }
    label = element(label.substr(1));
    const auto tail = label.find_first_of("0123456789");
    if (tail == std::string::npos || tail + 1 != label.size()) {
        pcr.fail("Expected a FullProf magnetic ion charge in " + label, source);
    }
    return {label.substr(0, tail), label + (label.back() == '0' ? "" : "+"), radial};
}

void magnetic_moment(const PCR& pcr, Structure& phase, const AtomSite& site, const MagneticType& type,
                     Refinement& refine, const Row& values, const Row& codes, bool spherical, std::size_t source) {
    const auto existing = std::find_if(phase.magnetic_form_factors.begin(), phase.magnetic_form_factors.end(),
                                       [&](const auto& row) { return row->id.value() == site.type_symbol.value(); });
    const auto& magnetic = phase.magnetic.get();
    const auto prior = std::find_if(magnetic.radial_coefficients.begin(), magnetic.radial_coefficients.end(),
                                    [&](const auto& row) { return row.first == site.type_symbol.value(); });
    if (existing == phase.magnetic_form_factors.end()) {
        auto factor = std::make_shared<MagneticFormFactor>();
        factor->id = site.type_symbol.value();
        factor->ion = type.ion;
        phase.magnetic_form_factors.push_back(factor);
        if (type.radial) {
            phase.magnetic.modify([&](MagneticDescription& update) {
                update.radial_coefficients.emplace_back(site.type_symbol.value(), *type.radial);
            });
        }
    } else if ((*existing)->ion.value() != type.ion ||
               (type.radial && (prior == magnetic.radial_coefficients.end() || prior->second != *type.radial)) ||
               (!type.radial && prior != magnetic.radial_coefficients.end())) {
        pcr.fail("Magnetic ions sharing a native type must use the same form factor", source);
    }
    auto moment = std::make_shared<AtomSiteMoment>();
    moment->id = site.id.value();
    if (spherical) {
        pcr.zero(codes, 0, 3, "refinement in spherical magnetic coordinates");
        if (phase.cell.angle_alpha.value.get() != 90. || phase.cell.angle_beta.value.get() != 90. ||
            phase.cell.angle_gamma.value.get() != 90.) {
            pcr.fail("Spherical FullProf moments require an orthogonal cell for this conversion", source);
        }
        const auto azimuth = values[1] * std::numbers::pi / 180.;
        const auto polar = values[2] * std::numbers::pi / 180.;
        moment->crystalaxis_x.value = values[0] * std::sin(polar) * std::cos(azimuth);
        moment->crystalaxis_y.value = values[0] * std::sin(polar) * std::sin(azimuth);
        moment->crystalaxis_z.value = values[0] * std::cos(polar);
    } else {
        refine.set(moment->parameters(), values, codes);
    }
    phase.atom_site_moment.push_back(moment);
}

void add_magnetic_operation(MagneticDescription& magnetic, const std::string& operation, bool centrosymmetric) {
    magnetic.operations.emplace_back(std::to_string(magnetic.operations.size() + 1), operation);
    if (centrosymmetric) {
        magnetic.operations.emplace_back(std::to_string(magnetic.operations.size() + 1),
                                         fullprof_inverted_operator(operation));
    }
}

void combined_magnetic_symmetry(const PCR& pcr, Structure& structure, std::size_t start, std::size_t end) {
    const auto counts_line = pcr.require("nsym cen n_clat n_ant", start, end);
    const auto counts = pcr.after(counts_line, end, 4);
    const auto count = integer(counts[0], pcr.path.string());
    const int centering = integer(counts[2], pcr.path.string());
    const int anti_centering = integer(counts[3], pcr.path.string());
    if (count < 1 || count > 192 || (counts[1] != 0. && counts[1] != 1. && counts[1] != 2.) ||
        centering < 0 || centering > 4 || anti_centering < 0 || anti_centering > 4) {
        pcr.fail("Unsupported FullProf magnetic centring or inversion layout", counts_line);
    }
    std::string bns;
    std::string bns_transform = "a,b,c;0,0,0";
    crysta::ParentSpaceGroup parent;
    for (std::size_t i = start; i < counts_line; ++i) {
        const auto& line = pcr.lines[i].text;
        const auto marker = lower(line).find("number:");
        if (marker != std::string::npos && !lower(line).starts_with("parent")) {
            const auto fields = words(std::string_view(line).substr(marker + 7));
            if (!fields.empty()) {
                bns = fields[0];
            }
        }
        const auto transform = line.find(':');
        if (lower(line).starts_with("transform to standard:") && transform != std::string::npos) {
            bns_transform = trim(std::string_view(line).substr(transform + 1));
        } else if (lower(line).starts_with("transform from parent:") && transform != std::string::npos) {
            parent.child_transform_pp_abc = trim(std::string_view(line).substr(transform + 1));
        } else if (lower(line).starts_with("parent space group:")) {
            const auto number_at = lower(line).find("it_number:");
            if (number_at != std::string::npos) {
                parent.name_h_m_alt = trim(std::string_view(line).substr(transform + 1, number_at - transform - 1));
                parent.it_number = trim(std::string_view(line).substr(number_at + 10));
            }
        }
    }
    MagneticDescription magnetic;
    if (bns.empty() || bns == "0.0") {
        structure.space_group.name_h_m = "P 1";
        magnetic.space_group_declared = false;
    } else {
        const auto separator = bns.find('.');
        if (separator == std::string::npos) {
            pcr.fail("Invalid FullProf magnetic BNS number", start);
        }
        const auto family = integer(number(bns.substr(0, separator), pcr.path.string()), pcr.path.string());
        const auto setting = space_group_setting_for_number(family);
        if (!setting) {
            pcr.fail("Unknown FullProf magnetic family " + bns, start);
        }
        assign_space_group_setting(structure.space_group, *setting, true);
        magnetic.group = fullprof_magnetic_group(bns);
    }
    magnetic.transforms.push_back({"1", {bns_transform, "BNS"}});
    magnetic.parent = std::move(parent);
    magnetic.centerings.emplace_back("1", "x,y,z,+1");
    auto row = pcr.next(counts_line + 1, end);
    for (int i = 0; i < centering + anti_centering; ++i) {
        row = pcr.next(row + 1, end);
        const auto coordinates = pcr.row(row, 3);
        std::string operation;
        for (std::size_t coordinate = 0; coordinate < 3; ++coordinate) {
            if (!operation.empty()) {
                operation += ',';
            }
            operation += "xyz"[coordinate];
            const double translation = coordinates[coordinate] - std::floor(coordinates[coordinate]);
            if (translation != 0.) {
                operation += '+' + number_text(translation);
            }
        }
        magnetic.centerings.emplace_back(std::to_string(magnetic.centerings.size() + 1),
                                         operation + (i < centering ? ",+1" : ",-1"));
    }
    for (int i = 0; i < count; ++i) {
        row = pcr.next(row + 1, end);
        const auto fields = words(pcr.lines[row].text);
        if (fields.size() != 2 || fields[1].find(',') == std::string::npos) {
            pcr.fail("Invalid FullProf signed magnetic operation", row);
        }
        add_magnetic_operation(magnetic, fields[1], counts[1] == 2.);
    }
    if (!bns_transform_consistent(magnetic)) {
        pcr.fail("FullProf magnetic group operators disagree with its BNS setting", counts_line);
    }
    structure.magnetic = std::move(magnetic);
}

void structure_block(const PCR& pcr, Project& project, std::vector<Pattern>& patterns, Refinement& refine,
                     std::size_t start, std::size_t end, bool multi) {
    auto structure = std::make_shared<Structure>();
    const auto phase = pcr.require("nat ", start + 1, end);
    const auto name = std::find_if(pcr.lines.begin() + static_cast<std::ptrdiff_t>(start + 1),
                                   pcr.lines.begin() + static_cast<std::ptrdiff_t>(phase),
                                   [](const auto& line) { return !line.text.empty(); });
    auto title = name->text.empty() ? std::string("phase") : name->text;
    if (lower(title).starts_with("name:")) {
        title = trim(std::string_view(title).substr(5));
    }
    const auto labels = words(title);
    if (labels.empty()) {
        pcr.fail("Missing FullProf phase name", start);
    }
    const auto base = safe_name(labels.front(), "phase");
    structure->name = base;
    for (unsigned i = 2; std::any_of(project.structures.begin(), project.structures.end(), [&](const auto& held) {
             return datablock_key(held->name.value(), "structure") == datablock_key(structure->name.value(), "structure");
         }); ++i) {
        const auto suffix = "_" + std::to_string(i);
        structure->name = base.substr(0, 31 - suffix.size()) + suffix;
    }
    const auto options = pcr.after(phase, end, multi ? 10 : 15);
    const int count = integer(options[0], pcr.path.string());
    const auto jbt = multi ? 3U : 6U;
    const auto isy = multi ? 4U : 8U;
    const auto nvk = multi ? 8U : 12U;
    const bool magnetic = std::abs(options[jbt]) == 10. && options[isy] == 2.;
    const bool magnetic_only = std::any_of(labels.begin(), labels.end(),
                                           [](const auto& label) { return lower(label) == "mag_only"; });
    const bool spherical = options[jbt] < 0.;
    if (count < 1 || (!magnetic && (options[jbt] != 0. || options[isy] != 0.)) ||
        options[isy + 1] != 0. || options[nvk] != 0.) {
        pcr.fail("Unsupported FullProf phase type, symmetry operators or propagation vectors", phase);
    }
    if (options[1] != 0. || options[2] != 0.) {
        pcr.fail("FullProf restrained phases need manual conversion", phase);
    }
    Row contributions(patterns.size(), 1.);
    std::vector<Row> axes(patterns.size());
    double brindley = 1.;
    if (!multi && options[14] != 0.) {
        const auto extra = pcr.header("jvi ", phase + 1, end);
        if (extra != end) {
            brindley = pcr.after(extra, end, 7)[6];
        }
    }
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
                if (axes[i].size() > 3 && axes[i][3] != 1.) {
                    brindley = axes[i][3];
                }
            }
        }
    } else {
        axes[0] = {options[3], options[4], options[5]};
        if (options[13] != 0. && options[13] != patterns[0].profile) {
            pcr.fail("Unsupported FullProf phase-specific profile family", phase);
        }
    }
    const auto atom_header = pcr.require("atom ", phase, end);
    if (magnetic) {
        combined_magnetic_symmetry(pcr, *structure, phase, atom_header);
    } else {
        auto group = atom_header;
        while (group > phase && pcr.lines[--group].text.empty()) {
        }
        auto symbol = pcr.lines[group].text;
        std::string origin;
        if (const auto suffix = symbol.find(':'); suffix != std::string::npos) {
            origin = trim(std::string_view(symbol).substr(suffix + 1));
            symbol = trim(std::string_view(symbol).substr(0, suffix));
        }
        auto setting = fullprof_default_space_group(symbol);
        if (setting && !origin.empty()) {
            setting = space_group_setting_for_code(setting->it_number, origin);
        }
        if (!setting) {
            pcr.fail("Unsupported FullProf space group " + symbol, group);
        }
        assign_space_group_setting(structure->space_group, *setting, true);
    }

    auto first_cell = pcr.require("a ", atom_header, end);
    const auto cell = pair_after(pcr, first_cell, end, 6);
    refine.set(structure->cell.parameters(), cell.values, cell.codes);
    if (magnetic) {
        (void)adopt_magnetic_family_setting(*structure);
    }
    auto atom_line = atom_header;
    std::vector<std::pair<std::shared_ptr<AtomSite>, Coded>> occupancies;
    double nominal_mass = 0.;
    bool mass_known = true;
    double largest = 0.;
    for (int i = 0; i < count; ++i) {
        atom_line = pcr.next(atom_line + 1, first_cell);
        const auto fields = words(pcr.lines[atom_line].text);
        if (fields.size() < (magnetic ? 11U : 10U)) {
            pcr.fail("Incomplete FullProf atom row", atom_line);
        }
        const auto values = numbers(Words(fields.begin() + 2, fields.end()), pcr.path.string());
        atom_line = pcr.next(atom_line + 1, first_cell);
        auto codes = pcr.row(atom_line, 5);
        if (!pcr.refinement_enabled) {
            std::fill(codes.begin(), codes.end(), 0.);
        }
        auto site = std::make_shared<AtomSite>();
        site->id = fields[0];
        for (unsigned suffix = 2; std::any_of(structure->atom_sites.begin(), structure->atom_sites.end(),
                        [&](const auto& held) { return lower(held->id.value()) == lower(site->id.value()); }); ++suffix) {
            site->id = fields[0] + "_" + std::to_string(suffix);
        }
        const std::size_t coordinate = magnetic ? 2 : 0;
        const auto atom_model = values[7];
        const bool moment_present = magnetic && atom_model == 1.;
        if (magnetic && values[1] != 0.) {
            pcr.fail("Magnetic propagation vector needs a non-collinear conversion", atom_line);
        }
        MagneticType moment_type;
        if (moment_present) {
            moment_type = magnetic_type(pcr, fields[1], atom_line);
            site->type_symbol = moment_type.element;
        } else {
            site->type_symbol = element(fields[1]);
        }
        structure->atom_sites.push_back(site);
        const auto coordinates = site->parameters();
        for (std::size_t axis = 0; axis < 3; ++axis) {
            coordinates[axis]->value = values[coordinate + axis];
        }
        const auto geometry = fullprof_site_geometry(*structure, *site);
        if (geometry.site_multiplicity <= 0 || geometry.general_multiplicity <= 0) {
            pcr.fail("Cannot establish FullProf site multiplicity for " + fields[0], atom_line);
        }
        constexpr std::array<int, 9> identity{1, 0, 0, 0, 1, 0, 0, 0, 1};
        if (magnetic && geometry.rotation != identity) {
            pcr.fail("FullProf magnetic site image changes the moment's axes", atom_line);
        }
        for (std::size_t axis = 0; axis < 3; ++axis) {
            const auto first = geometry.rotation.begin() + static_cast<std::ptrdiff_t>(axis * 3);
            refine.set(*coordinates[axis], rotated_code(pcr, geometry.representative[axis], codes,
                                                       Row(first, first + 3), atom_line));
        }
        site->wyckoff_letter = geometry.letter;
        const auto factor = static_cast<double>(geometry.general_multiplicity) / geometry.site_multiplicity;
        const auto occupancy = values[coordinate + 4] * factor;
        if (occupancy < 0.) {
            pcr.fail("Negative FullProf site occupancy for " + site->id.value(), atom_line);
        }
        occupancies.emplace_back(site, Coded{occupancy, codes[4], factor});
        largest = std::max(largest, occupancy);
        const auto mass = import_atomic_mass(site->type_symbol.value());
        if (mass) {
            nominal_mass += values[coordinate + 4] * geometry.general_multiplicity * *mass;
        } else {
            mass_known = false;
        }
        if (atom_model == 0. || moment_present) {
            refine.set(site->adp_iso, {values[coordinate + 3], codes[3]});
        } else if (atom_model == 2.) {
            auto tensor = std::make_shared<AtomSiteAniso>();
            tensor->id = site->id.value();
            site->adp_type = "beta";
            structure->atom_site_aniso.push_back(tensor);
            const auto row = pair_after(pcr, atom_line, first_cell, 6);
            atom_line = pcr.next(pcr.next(atom_line + 1, first_cell) + 1, first_cell);
            std::array<double, 6> beta{};
            std::copy_n(row.values.begin(), beta.size(), beta.begin());
            const auto rotated = fullprof_rotated_beta(beta, geometry.rotation);
            std::array<Row, 6> factors;
            for (std::size_t source = 0; source < beta.size(); ++source) {
                std::array<double, 6> unit{};
                unit[source] = 1.;
                const auto image = fullprof_rotated_beta(unit, geometry.rotation);
                for (std::size_t destination = 0; destination < image.size(); ++destination) {
                    factors[destination].push_back(image[destination]);
                }
            }
            const auto parameters = tensor->parameters();
            for (std::size_t column = 0; column < parameters.size(); ++column) {
                refine.set(*parameters[column], rotated_code(pcr, rotated[column], row.codes, factors[column], atom_line));
            }
        } else {
            pcr.fail("Unsupported FullProf atom model N_t=" + number_text(atom_model), atom_line);
        }
        if (moment_present) {
            const auto observation = pair_after(pcr, atom_line, first_cell, 7);
            pcr.zero(observation.values, 3, 7, "imaginary magnetic moments or phase");
            pcr.zero(observation.codes, 3, 7, "imaginary magnetic moment code or phase");
            atom_line = pcr.next(pcr.next(atom_line + 1, first_cell) + 1, first_cell);
            magnetic_moment(pcr, *structure, *site, moment_type, refine, observation.values, observation.codes, spherical, atom_line);
        }
    }
    double occupancy_factor = 1.;
    if (largest > 1.00015) {
        const double atz = options[multi ? 7 : 11];
        if (!mass_known || nominal_mass <= 0. || atz <= 0. || brindley <= 0.) {
            pcr.fail("FullProf occupancy normalization requires credible ATZ and Brindley values", phase);
        }
        const auto matches = [](double candidate, double observed) {
            return std::abs(candidate - observed) <= 0.005 * std::max(candidate, observed);
        };
        const double atz_mass_ratio = atz * brindley / nominal_mass;
        const double integral_plateau = std::round(largest);
        if (integral_plateau >= 2. && matches(integral_plateau, largest) &&
            (matches(integral_plateau, atz_mass_ratio) || matches(integral_plateau, nominal_mass / atz))) {
            // Some legacy files store the fully normalized cell mass in ATZ. Others include
            // FullProf's squared scale convention. Both can corroborate the occupancy plateau.
            occupancy_factor = integral_plateau;
        } else if (!(matches(1., atz_mass_ratio) && largest <= 1.05)) {
            pcr.fail("FullProf occupancy normalization conflicts with the phase mass", phase);
        }
    }
    for (const auto& [site, occupancy] : occupancies) {
        refine.set(site->occupancy,
                   {occupancy.value / occupancy_factor, occupancy.code, occupancy.multiplier / occupancy_factor});
    }
    if (magnetic_only) {
        if (!magnetic) {
            pcr.fail("FullProf MAG_ONLY requires a combined magnetic phase", phase);
        }
        std::map<std::string, double> nuclear_lengths;
        for (const auto& site : structure->atom_sites) {
            nuclear_lengths.emplace(site->type_symbol.value(), 0.);
        }
        structure->scattering_lengths_fm = std::move(nuclear_lengths);
    }
    if (magnetic) {
        check_magnetic_acceptance(*structure);
        complete_atom_site_moments(*structure);
    }
    project.structures.push_back(structure);

    const auto prefix = patterns.front().single_crystal() ? "scale, extinction and cell parameters for pattern"
                                                          : "profile parameters for pattern";
    const auto profiles = headers(pcr, prefix, atom_header, end);
    std::size_t profile_number = 0;
    std::optional<Coded> overall_b;
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
            pcr.zero(ext.values, 6, 7, "seventh single-crystal extinction coefficient");
            pcr.zero(ext.codes, 6, 7, "seventh single-crystal extinction code");
            const auto nonzero = [](const Row& values) {
                return std::any_of(values.begin(), values.begin() + 6, [](double value) { return value != 0.; });
            };
            if (nonzero(ext.values) || nonzero(ext.codes)) {
                if (ext.values.size() < 8 || (ext.values[7] != 1. && ext.values[7] != 4.)) {
                    pcr.fail("Unsupported FullProf single-crystal extinction law", begin);
                }
                pattern.reflection_extinction_model = static_cast<int>(ext.values[7]);
                const std::size_t size = pattern.reflection_extinction_model == 1 ? 1 : 6;
                pcr.zero(ext.values, size, 7, "extra single-crystal extinction coefficients");
                pcr.zero(ext.codes, size, 7, "extra single-crystal extinction codes");
                for (std::size_t coefficient = 0; coefficient < size; ++coefficient) {
                    pattern.reflection_extinction.push_back(ext.at(coefficient, occupancy_factor * occupancy_factor));
                }
            }
            if (pattern.model->linked_structures.size() != 1) {
                pcr.fail("A FullProf INT dataset requires one linked structure", begin);
            }
            for (std::size_t r = 0; r < 6; ++r) {
                pattern.reflection_scales.push_back(scale.at(r, occupancy_factor * occupancy_factor));
            }
            if (!multi && options[14] != 0.) {
                const auto extra = pcr.header("jvi ", phase + 1, atom_header);
                if (extra != atom_header) {
                    const auto values = pcr.after(extra, atom_header, 10);
                    if (values[7] > 0.) {
                        pattern.model->dataset_weight = values[7];
                    }
                    if (values[8] > 0.) {
                        pattern.model->reflns_threshold_sigma = values[8];
                    }
                    if (values[9] > 0.9) {
                        pcr.fail("Unsupported FullProf chi-squared weighting of single-crystal datasets", extra);
                    }
                }
            }
            continue;
        }
        const auto scale = pair_after(pcr, pcr.require("scale ", begin, limit), limit, 6, 5);
        pcr.zero(scale.values, 3, scale.values.size(), "phase strain");
        pcr.zero(scale.codes, 3, scale.codes.size(), "phase strain code");
        const auto bov = scale.at(2);
        if (pattern.enabled && overall_b &&
            (overall_b->value != bov.value || overall_b->code != bov.code)) {
            pcr.fail("FullProf overall B factor differs across the experiments of a structure", begin);
        }
        if (pattern.enabled) {
            overall_b = bov;
            pattern.overall_displacements.emplace(structure->name.value(), bov);
        }
        if (pattern.tof() && (scale.values[1] != 0. || scale.codes[1] != 0.)) {
            pcr.fail("Unsupported FullProf TOF extinction", begin);
        }
        refine.set(link->scale, scale.at(0, pattern.scale_factor * occupancy_factor * occupancy_factor));
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
    if (overall_b && (overall_b->value != 0. || overall_b->code != 0.)) {
        for (const auto& site : structure->atom_sites) {
            if (site->adp_type.value() != "Biso") {
                pcr.fail("FullProf overall B with anisotropic displacement needs a tensor conversion", phase);
            }
            auto& adp = site->adp_iso;
            if (overall_b->code != 0. && refine.codes.contains(&adp)) {
                pcr.fail("FullProf overall B and a site Biso both vary", phase);
            }
            refine.set(adp, {adp.value.get() + overall_b->value, overall_b->code});
        }
    }
}

void classic_magnetic_overlay(const PCR& pcr, Project& project, Pattern& pattern, Refinement& refine,
                              std::size_t phase, std::size_t end, const Row& options) {
    if (pattern.tof() || pattern.xray() || pattern.single_crystal() || options[7] != 0. ||
        options[8] != -1. || options[9] != 0. || options[12] != 0. ||
        options[1] != 0. || options[2] != 0.) {
        pcr.fail("FullProf magnetic phase requires a commensurate crystallographic overlay", phase);
    }
    const auto atom_header = pcr.require("atom ", phase + 1, end);
    const auto profile = pcr.require("profile parameters for pattern", atom_header + 1, end);
    const auto cell = pair_after(pcr, pcr.require("a ", profile, end), end, 6);
    const auto scale = pair_after(pcr, pcr.require("scale ", profile, end), end, 6, 5);
    const auto width = pair_after(pcr, pcr.require("u ", profile, end), end, 7);
    const auto shape = pair_after(pcr, pcr.require("pref1 ", profile, end), end, 6);
    auto signature = profile_signature(width, shape, {});
    signature.push_back({scale.values[1], scale.codes[1]});
    if (signature != pattern.profile_rows) {
        pcr.fail("FullProf magnetic and nuclear overlays use different powder profiles", profile);
    }
    pcr.zero(scale.values, 3, scale.values.size(), "magnetic overlay strain");
    pcr.zero(scale.codes, 3, scale.codes.size(), "magnetic overlay strain code");
    const auto bov = scale.at(2);
    const auto code_of = [&](Parameter& parameter) {
        const auto found = refine.codes.find(&parameter);
        return found == refine.codes.end() ? 0. : found->second.code;
    };
    Structure* matched = nullptr;
    for (const auto& structure : project.structures) {
        if (structure_magnetic(*structure)) {
            continue;
        }
        const auto link = std::find_if(pattern.model->linked_structures.begin(), pattern.model->linked_structures.end(),
                                       [&](const auto& held) { return held->structure_id.value() == structure->name.value(); });
        if (link == pattern.model->linked_structures.end() || (*link)->scale.value.get() != scale.values[0] ||
            code_of((*link)->scale) != scale.codes[0]) {
            continue;
        }
        const auto displacement = pattern.overall_displacements.find(structure->name.value());
        if (displacement == pattern.overall_displacements.end() ||
            displacement->second.value != bov.value || displacement->second.code != bov.code) {
            continue;
        }
        const auto parameters = structure->cell.parameters();
        bool equal = true;
        for (std::size_t i = 0; i < parameters.size(); ++i) {
            equal = equal && parameters[i]->value.get() == cell.values[i] && code_of(*parameters[i]) == cell.codes[i];
        }
        if (equal) {
            if (matched) {
                pcr.fail("Multiple nuclear phases match this FullProf magnetic overlay", phase);
            }
            matched = structure.get();
        }
    }
    if (!matched) {
        pcr.fail("FullProf magnetic overlay has no nuclear phase with matching scale, cell and overall B", phase);
    }
    auto& structure = *matched;
    const auto count_line = pcr.require("nsym cen laue magmat", phase + 1, atom_header);
    const auto counts = pcr.after(count_line, atom_header, 4);
    const int operations = integer(counts[0], pcr.path.string());
    if (operations < 1 || operations > 192 || (counts[1] != 1. && counts[1] != 2.) || counts[3] != 1.) {
        pcr.fail("Unsupported FullProf magnetic overlay operator counts", count_line);
    }
    MagneticDescription magnetic;
    magnetic.centerings.emplace_back("1", "x,y,z,+1");
    auto row = pcr.next(count_line + 1, atom_header);
    for (int operation = 0; operation < operations; ++operation) {
        row = pcr.next(row + 1, atom_header);
        const auto spatial = words(pcr.lines[row].text);
        row = pcr.next(row + 1, atom_header);
        const auto moment = words(pcr.lines[row].text);
        if (spatial.size() != 2 || lower(spatial[0]) != "symm" ||
            moment.size() != 2 || lower(moment[0]) != "msym") {
            pcr.fail("Expected a FullProf SYMM/MSYM operator pair", row);
        }
        const auto last_comma = moment[1].rfind(',');
        if (last_comma == std::string::npos || number(moment[1].substr(last_comma + 1), pcr.path.string()) != 0.) {
            pcr.fail("Unsupported FullProf magnetic operator phase", row);
        }
        add_magnetic_operation(magnetic,
            fullprof_signed_operator(lower(spatial[1]), lower(moment[1].substr(0, last_comma))), counts[1] == 2.);
    }
    struct SiteMoment {
        Row values;
        Row codes;
        MagneticType type;
        std::size_t line;
    };
    std::vector<SiteMoment> sites;
    row = atom_header;
    const int atoms = integer(options[0], pcr.path.string());
    for (int i = 0; i < atoms; ++i) {
        row = pcr.next(row + 1, profile);
        const auto fields = words(pcr.lines[row].text);
        if (fields.size() != 12) {
            pcr.fail("Incomplete FullProf magnetic overlay site", row);
        }
        auto values = numbers(Words(fields.begin() + 2, fields.end()), pcr.path.string());
        if (values[0] != 1. || values[1] != 0.) {
            pcr.fail("Unsupported FullProf magnetic operator or propagation vector", row);
        }
        auto type = magnetic_type(pcr, fields[1], row);
        row = pcr.next(row + 1, profile);
        auto codes = pcr.row(row, 8);
        if (!pcr.refinement_enabled) {
            std::fill(codes.begin(), codes.end(), 0.);
        }
        if (bov.code != 0.) {
            if (codes[3] != 0.) {
                pcr.fail("FullProf magnetic overlay varies both Biso and overall B", row);
            }
            codes[3] = bov.code;
        }
        const auto imaginary = pair_after(pcr, row, profile, 7);
        pcr.zero(imaginary.values, 0, 7, "imaginary magnetic moment or phase");
        pcr.zero(imaginary.codes, 0, 7, "imaginary magnetic moment code or phase");
        sites.push_back({std::move(values), std::move(codes), std::move(type), row});
        row = pcr.next(pcr.next(row + 1, profile) + 1, profile);
    }
    const auto positions = wyckoff_positions(structure);
    const bool enumerated = options[6] > 0. && magnetic.operations.size() == 1 &&
                            magnetic.operations.front().second == "x,y,z,+1" && positions.size() > 1;
    if (enumerated) {
        std::vector<FullProfEnumeratedMoment> moments;
        for (const auto& item : sites) {
            pcr.zero(item.codes, 0, 3, "moving coordinates in an enumerated magnetic overlay");
            pcr.zero(item.codes, 4, 5, "varying occupancy in an enumerated magnetic overlay");
            const auto& v = item.values;
            const auto& c = item.codes;
            const auto ion = (item.type.radial ? "J" : "M") + item.type.ion;
            moments.push_back({ion, {v[2], v[3], v[4]}, {v[7], v[8], v[9]}, {c[5], c[6], c[7]}, v[6], v[5], c[3]});
        }
        const auto inferred = fullprof_magnetic_overlay_group(structure, moments);
        if (!inferred) {
            pcr.fail("Enumerated FullProf moments do not preserve the nuclear site's symmetry and directions", phase);
        }
        magnetic = *inferred;
    }
    if (positions.empty()) {
        pcr.fail("FullProf magnetic overlay does not resolve nuclear Wyckoff positions", phase);
    }
    const int general = std::max_element(positions.begin(), positions.end(), [](const auto& a, const auto& b) {
        return a.multiplicity < b.multiplicity;
    })->multiplicity;
    structure.magnetic = std::move(magnetic);
    identify_declared_magnetic_family(structure);
    if (wyckoff_positions(structure).empty()) {
        pcr.fail("FullProf magnetic overlay does not preserve the nuclear symmetry", phase);
    }
    std::size_t represented = 0;
    for (const auto& item : sites) {
        const auto& values = item.values;
        const auto& codes = item.codes;
        const auto match = [&](const auto& site) {
            return site->type_symbol.value() == item.type.element &&
                std::abs(std::remainder(site->fract_x.value.get() - values[2], 1.)) < 1.e-5 &&
                std::abs(std::remainder(site->fract_y.value.get() - values[3], 1.)) < 1.e-5 &&
                std::abs(std::remainder(site->fract_z.value.get() - values[4], 1.)) < 1.e-5;
        };
        const auto site = std::find_if(structure.atom_sites.begin(), structure.atom_sites.end(), match);
        if (enumerated && site == structure.atom_sites.end()) {
            continue;  // Symmetry expansion of a representative supplies this observed moment.
        }
        if (site == structure.atom_sites.end() || std::count_if(structure.atom_sites.begin(), structure.atom_sites.end(), match) != 1 ||
            (*site)->adp_type.value() != "Biso" || (*site)->adp_iso.value.get() != values[5] + bov.value) {
            pcr.fail("FullProf magnetic overlay site does not match one nuclear site", item.line);
        }
        const auto wyckoff = std::find_if(positions.begin(), positions.end(), [&](const auto& position) {
            return position.letter == (*site)->wyckoff_letter.value();
        });
        if (wyckoff == positions.end()) {
            pcr.fail("FullProf magnetic overlay has an unknown nuclear Wyckoff position", item.line);
        }
        const auto chemical_occupancy = enumerated ? values[6] : values[6] * general / wyckoff->multiplicity;
        if (std::abs(chemical_occupancy - (*site)->occupancy.value.get()) > 1.e-5) {
            pcr.fail("FullProf magnetic overlay uses a different occupancy", item.line);
        }
        const std::array<Parameter*, 5> structural{&(*site)->fract_x, &(*site)->fract_y, &(*site)->fract_z,
                                                    &(*site)->adp_iso, &(*site)->occupancy};
        for (std::size_t field = 0; field < structural.size(); ++field) {
            if (codes[field] != code_of(*structural[field])) {
                pcr.fail("FullProf magnetic overlay refines a separate structural parameter", item.line);
            }
        }
        magnetic_moment(pcr, structure, **site, item.type, refine, Row(values.begin() + 7, values.end()),
                        Row(codes.begin() + 5, codes.end()), options[6] < 0., item.line);
        represented += enumerated ? static_cast<std::size_t>(wyckoff->multiplicity) : 1U;
    }
    if (represented != sites.size()) {
        pcr.fail("Enumerated FullProf magnetic orbits do not match the native sites", phase);
    }
    check_magnetic_acceptance(structure);
    complete_atom_site_moments(structure);
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
        for (const auto declaration : headers(pcr, "nat ", 1, pcr.lines.size())) {
            auto title = declaration;
            while (title > 1 && pcr.lines[--title].text.empty()) {
            }
            const auto& text = pcr.lines[title].text;
            if (title > 1 && !text.empty() && std::isalpha(static_cast<unsigned char>(text.front())) &&
                pcr.lines[title - 1].text.empty()) {
                phases.push_back(title - 1);
            }
        }
    }
    if (phases.empty()) {
        pcr.fail("No labelled FullProf phase blocks");
    }
    return phases;
}

std::vector<Pattern> patterns_from_header(const PCR& pcr, std::size_t end, bool multi, bool integrated,
                                         Project& project, Refinement& refine) {
    const auto job_header = pcr.require("job ", 0, end);
    const auto output_header = pcr.require("ipr ", job_header, end);
    const auto ncy = pcr.require("ncy ", output_header, end);
    const auto cycles = integer(pcr.after(ncy, end, 1)[0], pcr.path.string());
    if (cycles > 0) {
        project.minimizer_max_iterations = cycles;
    }
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
        if ((npatt.size() != 2 && npatt.size() < count + 2) || (!weights.empty() && weights.size() != count)) {
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
            const auto flag = npatt.size() == 2 ? std::string("1") : npatt[i + 2];
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
        const auto job = pcr.row(job_line, multi ? 12 : 19);
        const std::size_t uni = multi ? 10 : 15;
        pattern.job = integer(job[0], pcr.path.string());
        pattern.polarization_model = integer(job[multi ? 7 : 9], pcr.path.string());
        pattern.profile = integer(job[1], pcr.path.string());
        pattern.resolution_format = integer(job[multi ? 8 : 11], pcr.path.string());
        pattern.background = integer(job[multi ? 2 : 3], pcr.path.string());
        pattern.orientation = integer(job[multi ? 5 : 6], pcr.path.string());
        pattern.scattering_count = integer(job[multi ? 4 : 5], pcr.path.string());
        if (pattern.scattering_count < 0 || pattern.scattering_count > 99 ||
            (pattern.xray() && pattern.scattering_count != 0)) {
            pcr.fail("Unsupported FullProf tabulated or X-ray scattering factors", job_line);
        }
        pattern.exclusions = integer(job[multi ? 3 : 4], pcr.path.string());
        if (pattern.job < -3 || pattern.job == -2 || pattern.job > 3 ||
            job[uni] != (pattern.tof() && !integrated ? 1. : 0.) ||
            pattern.exclusions < 0 || pattern.background > 10000) {
            pcr.fail("Unsupported FullProf Job or axis Uni, or invalid point count", job_line);
        }
        output_line = pcr.next(output_line + 1, ncy);
        const auto output = pcr.row(output_line, multi ? 11 : 17);
        pattern.format = integer(output[multi ? 7 : 10], pcr.path.string());
        if (multi && job.size() > 13 && job[13] != 0.) {
            pcr.fail("FullProf joint powder and integrated-intensity refinement needs a mixed residual", job_line);
        }
        if (multi && job.size() > 12 && job[12] != 0.) {
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
            const auto comment = lower(pcr.lines[i].original_comment);
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

    auto resolution_row = job_line;
    for (auto& pattern : patterns) {
        if (pattern.resolution_format == 0) {
            continue;
        }
        const auto header = pcr.require("resolution file", resolution_row + 1, output_header);
        resolution_row = pcr.next(header + 1, output_header);
        if (pattern.tof() && pattern.profile == 9 && pattern.resolution_format == 5) {
            pattern.resolution = tof_resolution(pcr, resolution_row);
        } else if (!pattern.tof() && pattern.profile == 7 && pattern.resolution_format == 1) {
            pattern.cw_resolution = cw_resolution(pcr, pattern, resolution_row);
        } else {
            pcr.fail("Unsupported FullProf resolution model Res=" + std::to_string(pattern.resolution_format), header);
        }
    }

    auto source_range = ncy;
    auto setup = output_line;
    auto calibration = ncy;
    auto points = ncy;
    auto exclusions = ncy;
    auto coeffs = ncy;
    auto scattering_row = ncy;
    for (auto& pattern : patterns) {
        if (pattern.scattering_count != 0) {
            scattering_row = pcr.require("additional scattering factors", scattering_row + 1, end);
            for (int i = 0; i < pattern.scattering_count; ++i) {
                scattering_row = pcr.next(scattering_row + 1, end);
                const auto fields = words(pcr.lines[scattering_row].text);
                if (fields.size() != 4 || number(fields[2], pcr.path.string()) != 0. ||
                    number(fields[3], pcr.path.string()) != 0.) {
                    pcr.fail("FullProf neutron overrides must be real constant scattering lengths", scattering_row);
                }
                const auto type = element(fields[0]);
                if (!pattern.neutron_lengths.emplace(type, 10. * number(fields[1], pcr.path.string())).second) {
                    pcr.fail("Duplicate FullProf neutron scattering length for " + type, scattering_row);
                }
            }
        }
        if (pattern.single_crystal()) {
            configure_pattern(pcr, pattern, refine, 0, 0, 0, end, false);
            continue;
        }
        setup = pcr.require(pattern.tof() ? "bkpos " : "lambda1 ", setup + 1, ncy);
        calibration = pcr.require("zero ", calibration + 1, end);
        if (multi) {
            const auto labelled = pcr.header(pattern.tof() ? "tof-min " : "thmin ", source_range + 1, end);
            source_range = std::min(labelled, pcr.header("range minimum step maximum", source_range + 1, end));
            if (source_range == end) {
                pcr.fail("Missing FullProf calculation range", ncy);
            }
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

void neutron_scattering_tables(const PCR& pcr, Project& project, const std::vector<Pattern>& patterns) {
    const bool phase_overrides = std::any_of(project.structures.begin(), project.structures.end(),
                                             [](const auto& phase) { return !phase->scattering_lengths_fm.empty(); });
    if (!phase_overrides && std::none_of(patterns.begin(), patterns.end(),
                                       [](const auto& pattern) { return pattern.enabled && !pattern.neutron_lengths.empty(); })) {
        return;
    }
    std::map<Structure*, std::map<std::string, double>> tables;
    bool overrides = phase_overrides;
    for (const auto& phase : project.structures) {
        if (!phase->scattering_lengths_fm.empty()) {
            continue;  // A MAG_ONLY phase already has a zero nuclear scattering table.
        }
        for (const auto& pattern : patterns) {
            if (!pattern.enabled || pattern.xray() ||
                std::none_of(pattern.model->linked_structures.begin(), pattern.model->linked_structures.end(),
                             [&](const auto& link) { return link->structure_id.value() == phase->name.value(); })) {
                continue;
            }
            std::map<std::string, double> lengths;
            for (const auto& site : phase->atom_sites) {
                const auto& type = site->type_symbol.value();
                const auto standard = fullprof_default_neutron_length(type);
                const auto supplied = pattern.neutron_lengths.find(type);
                if (supplied != pattern.neutron_lengths.end()) {
                    lengths.emplace(type, supplied->second);
                    overrides = overrides || !standard || std::abs(supplied->second - *standard) > 1.e-12;
                } else if (standard) {
                    lengths.emplace(type, *standard);
                } else {
                    pcr.fail("No neutron scattering length is available for " + type);
                }
            }
            if (const auto previous = tables.find(phase.get()); previous != tables.end()) {
                if (previous->second != lengths) {
                    pcr.fail("FullProf neutron scattering lengths for a phase differ by pattern");
                }
            } else {
                tables.emplace(phase.get(), std::move(lengths));
            }
        }
    }
    if (overrides) {
        for (const auto& [phase, lengths] : tables) {
            phase->scattering_lengths_fm = lengths;
        }
        for (const auto& experiment : project.experiments) {
            experiment->neutron_scattering_length.reset();
        }
    }
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
    auto normalized = lower(symbol);
    if (normalized.empty()) {
        return std::nullopt;
    }
    normalized.front() = static_cast<char>(std::toupper(static_cast<unsigned char>(normalized.front())));
    for (const auto& [old_name, current_name] :
         {std::pair{"F d 3 m", "F d -3 m"}, std::pair{"F m 3 m", "F m -3 m"},
          std::pair{"P m 3 m", "P m -3 m"}}) {
        if (same_space_group_name(normalized, old_name)) {
            normalized = current_name;
        }
    }
    if (same_space_group_name(normalized, "F d -3 m")) {
        return space_group_setting_for_code(227, "2");
    }
    if (auto setting = space_group_setting_for_name(normalized)) {
        return setting;
    }
    const auto fields = words(normalized);
    if (fields.size() == 2 && fields[0].size() == 1) {
        // The short monoclinic FullProf symbols use the conventional unique b axis.
        if (auto setting = space_group_setting_for_name(fields[0] + " 1 " + fields[1] + " 1")) {
            return setting;
        }
    }
    return unambiguous_space_group_alias(normalized);
}

std::string fullprof_scattering_type(const std::string& type) {
    const auto nuclide_end = type.find_first_not_of("0123456789");
    if (nuclide_end != 0 && nuclide_end != std::string::npos) {
        return type.substr(nuclide_end) + type.substr(0, nuclide_end);
    }
    if (type.size() >= 3 && (type.back() == '+' || type.back() == '-')) {
        const auto last_element = type.find_last_not_of("0123456789", type.size() - 2);
        if (last_element != std::string::npos && last_element + 2 < type.size()) {
            return type.substr(0, last_element + 1) + type.back() +
                   type.substr(last_element + 1, type.size() - last_element - 2);
        }
    }
    return type;
}

std::optional<crysta::MagneticRadialCoefficients> fullprof_magnetic_radial(const std::string& label) {
    // Individual fitted dipole curves printed by FullProf.2k 8.40 in
    // the magnetic form-factor section of its calculation output.
    static const std::map<std::string, std::array<std::string_view, 7>> table{
        {"jce3", {"0.0512", "6.1154", "0.2777", "7.9525", "0.6541", "2.2870", "0.0164"}},
        {"jdy2", {"0.1756", "5.9381", "0.2289", "11.4640", "0.5833", "2.1676", "0.0112"}},
        {"jdy3", {"0.1235", "13.2240", "0.4881", "4.6409", "0.3943", "1.7345", "-0.0060"}},
        {"jho2", {"0.0232", "0.7032", "0.2707", "9.9935", "0.6776", "2.5214", "0.0271"}},
        {"jho3", {"0.0432", "0.9101", "0.2794", "8.6834", "0.6685", "2.4175", "0.0082"}},
        {"jnd3", {"0.0733", "4.4124", "0.3715", "4.0196", "0.5395", "1.5580", "0.0173"}},
        {"jtb2", {"0.0498", "18.7342", "0.2774", "10.0841", "0.6612", "2.7456", "0.0108"}},
        {"jtb3", {"0.0498", "15.1122", "0.2706", "9.1583", "0.6794", "2.8803", "-0.0001"}},
    };
    const auto found = table.find(lower(label));
    if (found == table.end()) {
        return std::nullopt;
    }
    crysta::MagneticRadialCoefficients result;
    std::copy(found->second.begin(), found->second.end(), result.values.begin());
    result.source = "FullProf.2k 8.40 internal " + found->first + " magnetic form factor";
    return result;
}

Project import_fullprof_project(const std::string& path) {
    PCR pcr(path);
    try {
        if (pcr.lines.empty() || pcr.lines.front().text.empty()) {
            pcr.fail("Expected a classic or multi-pattern FullProf PCR file");
        }
        for (std::size_t i = 0; i < pcr.lines.size(); ++i) {
            const auto command = lower(pcr.lines[i].text);
            if (command.starts_with("layer_c ")) {
                pcr.fail("Unsupported FullProf turbostratic layer calculation", i);
            }
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
        auto patterns = patterns_from_header(pcr, phase_end, multi, cry == 1., project, refine);
        if (patterns.front().single_crystal() != (cry == 1.)) {
            pcr.fail("FullProf integrated-intensity settings Cry and Irf disagree", phase_declaration);
        }
        std::vector<std::size_t> overlays;
        for (std::size_t i = 0; i < phases.size(); ++i) {
            const auto end = i + 1 < phases.size() ? phases[i + 1] : pcr.lines.size();
            if (!multi) {
                const auto flags_line = pcr.require("nat ", phases[i] + 1, end);
                if (std::abs(pcr.after(flags_line, end, 7)[6]) == 1.) {
                    overlays.push_back(i);
                    continue;
                }
            }
            structure_block(pcr, project, patterns, refine, phases[i], end, multi);
        }
        for (const auto i : overlays) {
            const auto end = i + 1 < phases.size() ? phases[i + 1] : pcr.lines.size();
            const auto flags_line = pcr.require("nat ", phases[i] + 1, end);
            classic_magnetic_overlay(pcr, project, patterns.front(), refine, flags_line, end,
                                     pcr.after(flags_line, end, 15));
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
                reflection_data(pcr, pattern, refine, project);
            } else {
                if (pattern.simulation()) {
                    exp.calculation_only = true;
                    Edit::data_range(exp, pattern.lo, pattern.hi, pattern.step)();
                } else {
                    powder_data(pcr, pattern);
                }
                project.experiments.push_back(pattern.model);
            }
        }
        if (project.experiments.empty()) {
            pcr.fail("No active FullProf patterns");
        }
        neutron_scattering_tables(pcr, project, patterns);
        refresh_relations(project);
        refinement_flags(pcr, project, refine, pcr.refinement_enabled);
        return project;
    } catch (const IoError&) {
        throw;
    } catch (const std::exception& error) {
        pcr.fail(error.what());
    }
}

}  // namespace edi::detail
