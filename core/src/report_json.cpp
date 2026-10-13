// SPDX-License-Identifier: BSD-3-Clause
#include <cmath>
#include <limits>
#include <stdexcept>

#include "edi/report_model.hpp"
#include "json.hpp"

// The report model's JSON (edi ADR-0035 §1): every field, in declaration order, so a model read from its JSON writes
// the same JSON again.

namespace edi {

namespace {

using json::Array;
using json::Object;
using json::Value;

Value strings(const std::vector<std::string>& texts) {
    Array items;
    items.reserve(texts.size());
    for (const std::string& text : texts) {
        items.emplace_back(text);
    }
    return items;
}

std::vector<std::string> strings_of(const Value& value, const char* what) {
    std::vector<std::string> out;
    for (const Value& item : value.array(what)) {
        out.push_back(item.string(what));
    }
    return out;
}

Value numbers(const std::vector<double>& values) {
    Array items;
    items.reserve(values.size());
    for (double number : values) {
        items.emplace_back(number);
    }
    return items;
}

std::vector<double> numbers_of(const Value& value, const char* what) {
    std::vector<double> out;
    for (const Value& item : value.array(what)) {
        out.push_back(item.number(what));
    }
    return out;
}

Value optional_number(const std::optional<double>& number) { return number.has_value() ? Value(*number) : Value(); }

std::optional<double> optional_number_of(const Value& value, const char* what) {
    if (value.is_null()) {
        return std::nullopt;
    }
    return value.number(what);
}

Value rows(const std::vector<ReportRow>& list) {
    Array items;
    for (const ReportRow& row : list) {
        items.emplace_back(Object{{"label", row.label}, {"text", row.text}, {"units", row.units}});
    }
    return items;
}

std::vector<ReportRow> rows_of(const Value& value, const char* what) {
    std::vector<ReportRow> out;
    for (const Value& item : value.array(what)) {
        out.push_back({item.at("label").string("label"), item.at("text").string("text"),
                       item.at("units").string("units")});
    }
    return out;
}

Value table(const ReportTable& data) {
    Array body;
    for (const std::vector<std::string>& row : data.rows) {
        body.push_back(strings(row));
    }
    return Object{{"columns", strings(data.columns)}, {"rows", std::move(body)}};
}

ReportTable table_of(const Value& value) {
    ReportTable out;
    out.columns = strings_of(value.at("columns"), "columns");
    for (const Value& row : value.at("rows").array("rows")) {
        out.rows.push_back(strings_of(row, "row"));
    }
    return out;
}

Value value_json(const ReportValue& number) {
    return Object{{"value", number.value}, {"su", optional_number(number.su)}, {"text", number.text}};
}

ReportValue value_of(const Value& value) {
    return {value.at("value").number("value"), optional_number_of(value.at("su"), "su"), value.at("text").string("text")};
}

}  // namespace

std::string report_to_json(const ReportModel& model) {
    Array sections;
    for (ReportSection section : model.sections) {
        sections.emplace_back(report_section_name(section));
    }
    Array parameters;
    for (const ReportParameter& parameter : model.parameters) {
        parameters.emplace_back(Object{{"name", parameter.name},
                                       {"label", parameter.label},
                                       {"units", parameter.units},
                                       {"value", value_json(parameter.value)},
                                       {"start", optional_number(parameter.start)},
                                       {"free", parameter.free}});
    }
    Value correlations;
    if (model.correlations.has_value()) {
        const ReportCorrelations& matrix = *model.correlations;
        correlations = Object{{"labels", strings(matrix.labels)},
                              {"values", numbers(matrix.values)},
                              {"level", matrix.level},
                              {"available", matrix.available},
                              {"empty_text", matrix.empty_text}};
    }
    Array structures;
    for (const ReportStructure& structure : model.structures) {
        structures.emplace_back(Object{{"id", structure.id},
                                       {"space_group", rows(structure.space_group)},
                                       {"cell", rows(structure.cell)},
                                       {"atom_sites", table(structure.atom_sites)},
                                       {"aniso", table(structure.aniso)}});
    }
    Array experiments;
    for (const ReportExperiment& experiment : model.experiments) {
        experiments.emplace_back(Object{{"id", experiment.id},
                                        {"type", rows(experiment.type)},
                                        {"instrument", rows(experiment.instrument)},
                                        {"peak", rows(experiment.peak)},
                                        {"background", table(experiment.background)},
                                        {"excluded_regions", table(experiment.excluded_regions)},
                                        {"linked_structures", table(experiment.linked_structures)}});
    }
    const Object document{{"schema_version", model.schema_version},
                          {"generated", model.generated},
                          {"sections", std::move(sections)},
                          {"name", model.name},
                          {"title", model.title},
                          {"authors", model.authors},
                          {"description", model.description},
                          {"structure_ids", strings(model.structure_ids)},
                          {"experiment_ids", strings(model.experiment_ids)},
                          {"software", rows(model.software)},
                          {"fitting_mode", model.fitting_mode},
                          {"fitted", model.fitted},
                          {"fit_result", rows(model.fit_result)},
                          {"parameters", std::move(parameters)},
                          {"correlations", std::move(correlations)},
                          {"structures", std::move(structures)},
                          {"experiments", std::move(experiments)}};
    return json::write(document);
}

ReportModel report_from_json(const std::string& text) {
    const Value document = json::parse(text);
    ReportModel model;
    const double version = document.at("schema_version").number("schema_version");
    if (version != kReportSchemaVersion) {
        throw std::invalid_argument("report JSON: schema version " + std::to_string(version) + ", this reader reads " +
                                    std::to_string(kReportSchemaVersion));
    }
    model.generated = document.at("generated").string("generated");
    for (const Value& name : document.at("sections").array("sections")) {
        const std::optional<ReportSection> section = report_section_from_name(name.string("section"));
        if (!section) {
            throw std::invalid_argument("report JSON: unknown section '" + name.string("section") + "'");
        }
        model.sections.push_back(*section);
    }
    model.name = document.at("name").string("name");
    model.title = document.at("title").string("title");
    model.authors = document.at("authors").string("authors");
    model.description = document.at("description").string("description");
    model.structure_ids = strings_of(document.at("structure_ids"), "structure_ids");
    model.experiment_ids = strings_of(document.at("experiment_ids"), "experiment_ids");
    model.software = rows_of(document.at("software"), "software");
    model.fitting_mode = document.at("fitting_mode").string("fitting_mode");
    model.fitted = document.at("fitted").boolean("fitted");
    model.fit_result = rows_of(document.at("fit_result"), "fit_result");
    for (const Value& item : document.at("parameters").array("parameters")) {
        model.parameters.push_back({item.at("name").string("name"), item.at("label").string("label"),
                                    item.at("units").string("units"), value_of(item.at("value")),
                                    optional_number_of(item.at("start"), "start"), item.at("free").boolean("free")});
    }
    const Value& correlations = document.at("correlations");
    if (!correlations.is_null()) {
        ReportCorrelations matrix;
        matrix.labels = strings_of(correlations.at("labels"), "labels");
        matrix.values = numbers_of(correlations.at("values"), "values");
        matrix.level = correlations.at("level").number("level");
        matrix.available = static_cast<int>(correlations.at("available").number("available"));
        matrix.empty_text = correlations.at("empty_text").string("empty_text");
        model.correlations = std::move(matrix);
    }
    for (const Value& item : document.at("structures").array("structures")) {
        model.structures.push_back({item.at("id").string("id"), rows_of(item.at("space_group"), "space_group"),
                                    rows_of(item.at("cell"), "cell"), table_of(item.at("atom_sites")),
                                    table_of(item.at("aniso"))});
    }
    for (const Value& item : document.at("experiments").array("experiments")) {
        model.experiments.push_back({item.at("id").string("id"), rows_of(item.at("type"), "type"),
                                     rows_of(item.at("instrument"), "instrument"), rows_of(item.at("peak"), "peak"),
                                     table_of(item.at("background")), table_of(item.at("excluded_regions")),
                                     table_of(item.at("linked_structures"))});
    }
    return model;
}

}  // namespace edi
