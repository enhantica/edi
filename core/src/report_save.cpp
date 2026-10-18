// SPDX-License-Identifier: BSD-3-Clause
#include "edi/report_save.hpp"

#include <ctime>
#include <filesystem>
#include <functional>
#include <iomanip>
#include <locale>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <system_error>
#include <vector>

#include "crysta/project_output.hpp"
#include "edi/io.hpp"
#include "edi/model.hpp"

namespace edi {

namespace {

namespace fs = std::filesystem;

std::string iso_utc(std::time_t time) {
    std::tm utc{};
    gmtime_r(&time, &utc);
    char buffer[32];
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &utc);
    return buffer;
}

// The report the project makes with `overrides`, its time now unless the options give one.
ReportModel report_of(const Project& project, const ReportOverrides& overrides) {
    return build_report(project, effective_report_options(project, overrides));
}

// The libraries the HTML is written with: the vendored ones when the options embed them, else none (online).
const ReportLibraries& html_libraries(const ReportOptions& options, const ReportLibraries& libraries) {
    static const ReportLibraries kOnline;
    return options.embed_libraries ? libraries : kOnline;
}

}  // namespace

ReportOptions report_file_options(ReportOptions options) {
    options.colour_scheme = kDefaultColourScheme;
    options.correlation_experiment = 0;
    return options;
}

bool chooses_presentation(const ReportOptions& options) {
    return options.colour_scheme != kDefaultColourScheme || options.correlation_experiment != 0;
}

std::string iso_utc_from_star(const std::string& stamp) {
    std::tm parsed{};
    std::istringstream in(stamp);
    in.imbue(std::locale::classic());
    in >> std::get_time(&parsed, "%d %b %Y %H:%M:%S");
    return in.fail() ? stamp : iso_utc(timegm(&parsed));
}

void write_report_file(const std::string& project_path, const std::string& name, const std::string& bytes) {
    // Project output (ADR-0039), written by the engine's writer; a report it refuses is a runtime_error here.
    try {
        crysta::output::replace_file(project_path, (fs::path(project_path) / "reports" / name).string(), bytes);
    } catch (const std::invalid_argument& refusal) {
        throw std::runtime_error(refusal.what());
    }
}

ReportSaveResult save_report(Project& project, const ReportOverrides& overrides, const ReportLibraries& libraries) {
    if (project.path.empty()) {
        throw std::invalid_argument("save the project before its report: it has no folder");
    }
    ReportSaveResult result;
    const ReportOptions options = effective_report_options(project, overrides);
    const ReportModel model = build_report(project, options);
    // The row's digest is of the report in report_file_options: the same model unless this run chose otherwise.
    std::optional<ReportModel> judged;
    if (chooses_presentation(options)) {
        judged = build_report(project, report_file_options(options));
    }
    const fs::path reports = fs::path(project.path) / "reports";
    if (project.report_pdf.value_or(false)) {
        result.pdf_left = true;
    }
    // The open project's rows change with reports/report.edi, or not at all.
    const ItemVec<ReportFile> before = project.report_files;
    if (project.report_html.value_or(true)) {
        const ReportLibraries& used = html_libraries(options, libraries);
        const std::string name = (model.name.empty() ? std::string("report") : model.name) + ".html";
        write_report_file(project.path, name, report_html(model, used));
        result.written.push_back((reports / name).string());
        ReportFile row;
        row.name = name;
        row.format = std::string("html");
        row.saved = iso_utc(std::time(nullptr));
        row.project_last_modified = iso_utc_from_star(project.metadata.last_modified);
        row.digest = report_digest(judged ? *judged : model, "html", used);
        std::size_t at = 0;
        for (const auto& file : project.report_files) {
            if (file->name.value() == name) {
                break;
            }
            ++at;
        }
        if (at < project.report_files.size()) {
            project.report_files.replace_at(at, std::make_shared<ReportFile>(std::move(row)));
        } else {
            project.report_files.push_back(std::move(row));
        }
    }
    try {
        save_report_settings(project, project.path);
    } catch (...) {
        project.report_files = before;
        throw;
    }
    return result;
}

std::vector<ReportFileState> report_file_states(const Project& project, const ReportLibraries& libraries) {
    std::vector<ReportFileState> states;
    if (project.report_files.empty()) {
        return states;
    }
    const ReportOptions options = report_file_options(effective_report_options(project));
    const ReportModel model = build_report(project, options);
    const fs::path reports = fs::path(project.path) / "reports";
    for (const auto& file : project.report_files) {
        ReportFileState state{file->name.value(), file->format.value(), "current"};
        if (!fs::is_regular_file(reports / state.name)) {
            state.state = "missing";
        } else if (report_digest(model, state.format, state.format == "html" ? html_libraries(options, libraries)
                                                                           : ReportLibraries{}) !=
                   file->digest.value()) {
            state.state = "out of date";
        }
        states.push_back(std::move(state));
    }
    return states;
}

}  // namespace edi
