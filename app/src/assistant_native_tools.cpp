// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_native_tools.hpp"
#include "assistant_native_create.hpp"
#include "../../core/src/assistant_parameter_edits.hpp"
#include "../../core/src/assistant_relation_edits.hpp"
#include "edi/assistant_limits.hpp"
#include <QSet>
#include <cmath>
#include <stdexcept>
namespace edi_app {
namespace {
using Object = QJsonObject;
using Array = QJsonArray;
Object object(Object properties, Array required) {
    return {{"type", "object"}, {"properties", properties}, {"required", required}, {"additionalProperties", false}};
}
void shape(const Object& value, const QSet<QString>& keys) {
    if (value.size() != keys.size()) throw std::invalid_argument("Native action fields are missing or unsupported");
    for (auto i = value.constBegin(); i != value.constEnd(); ++i) if (!keys.contains(i.key()))
        throw std::invalid_argument("Unsupported native action field");
}
}
QJsonArray assistant_native_tool_specs() {
    Array tools;
    const Object text{{"type", "string"}, {"minLength", 1}, {"maxLength", 256}};
    const Object purpose{{"type", "string"}, {"minLength", 1}, {"maxLength", 120},
        {"description", "A concise purpose for this action, not a claim that it succeeded"}};
    const auto add = [&](const char* name, const char* description, Object properties = {}, Array required = {}) {
        properties["purpose"] = purpose; required.append("purpose");
        tools.append(Object{{"type", "function"}, {"name", name}, {"description", description}, {"inputSchema", object(properties, required)}});
    };
    add("inspect_project", "Inspect Edi's actual currently displayed project/context. No mutation.");
    add("list_parameters", "Read actual native parameter paths/values/free flags and dependence. No mutation.");
    add("diagnostics", "Read actual available native physical diagnostics. No mutation.");
    add("set_parameters", "Atomically set independent parameter values in the displayed project through Edi's validated native editor.",
        {{"values", Object{{"type", "array"}, {"minItems", 1}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"path", text}, {"value", Object{{"type", "number"}}}}, {"path", "value"})}}}}, {"values"});
    add("set_free", "Atomically choose actual independent fittable native parameter flags; preserves physical/symmetry validation.",
        {{"flags", Object{{"type", "array"}, {"minItems", 1}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"path", text}, {"free", Object{{"type", "boolean"}}}}, {"path", "free"})}}}}, {"flags"});
    add("run_fit", "Run the displayed Edi project's real single/joint native fit and await actual publication/outcome. This is a live fit, not an isolated accepted-best trial.");
    add("create_cwl_project", "Create and display a NEW native single-phase powder CW neutron project from two genuine selected-file IDs and an explicit scientific recipe; never replaces an existing project. No fit or save is implied.",
        {{"cif_file_id", text}, {"data_file_id", text}, {"recipe", native_cwl_recipe_schema()}}, {"cif_file_id", "data_file_id", "recipe"});
    add("save_project", "Save the actual settled current fitted single/joint native project into a fresh child of the genuinely chosen working folder, verify reopen and make it the active saved project. Normal mode only; no overwrite, scan or external report assets.",
        {{"name", Object{{"type","string"},{"minLength",1},{"maxLength",120},{"pattern","^[A-Za-z0-9_-]+$"},
            {"description","Fresh child directory basename under the actual chosen working folder. A chat path never grants access."}}}}, {"name"});
    add("add_relations", "Append a complete validated affine alias/constraint batch to the displayed project through the native relation editor and Undo. Existing relations/composition are preserved; this edit is not a trial or fit.",
        {{"aliases", Object{{"type", "array"}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"id", text}, {"path", text}}, {"id", "path"})}}},
         {"constraints", Object{{"type", "array"}, {"minItems", 1}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"id", text}, {"expression", Object{{"type", "string"}, {"minLength", 1}, {"maxLength", static_cast<int>(edi::assistant::Limits::context_bytes)}}},
                {"enabled", Object{{"type", "boolean"}}}}, {"id", "expression", "enabled"})}}}}, {"aliases", "constraints"});
    return tools;
}
bool assistant_native_tool(const QString& name) {
    return name == "inspect_project" || name == "list_parameters" || name == "diagnostics" ||
        name == "set_parameters" || name == "set_free" || name == "run_fit" || name == "create_cwl_project" || name == "add_relations" || name == "save_project";
}
QString assistant_native_purpose(const Object& args) {
    const auto value = args.value("purpose");
    if (!value.isString()) throw std::invalid_argument("Native action requires its purpose");
    const auto text = value.toString();
    if (text.trimmed().isEmpty() || text.size() > 120 || text.toUtf8().size() > 480)
        throw std::invalid_argument("Native action purpose exceeds its limit");
    for (const auto c : text) if (c.unicode() < 32 || c.unicode() == 127)
        throw std::invalid_argument("Native action purpose contains control characters");
    return text;
}
void assistant_native_arguments(const QString& name, const Object& args) {
    (void)assistant_native_purpose(args);
    if (name == "create_cwl_project") shape(args, {"purpose", "cif_file_id", "data_file_id", "recipe"});
    else if (name == "add_relations") shape(args, {"purpose", "aliases", "constraints"});
    else if(name=="save_project") shape(args,{"purpose","name"});
    else if (name == "set_parameters") shape(args, {"purpose", "values"});
    else if (name == "set_free") shape(args, {"purpose", "flags"});
    else if (assistant_native_tool(name)) shape(args, {"purpose"});
    else throw std::invalid_argument("Native action is unavailable");
}
std::optional<edi::Edit> assistant_native_edit(edi::Project& project, const QString& name, const Object& args, std::vector<std::pair<std::string, bool>>& beforeFlags) {
    assistant_native_arguments(name, args);
    if (name == "add_relations") {
        const auto aliasValue = args.value("aliases"), constraintValue = args.value("constraints");
        if (!aliasValue.isArray() || !constraintValue.isArray() || aliasValue.toArray().size() > static_cast<qsizetype>(edi::assistant::Limits::stream_items) ||
            constraintValue.toArray().isEmpty() || constraintValue.toArray().size() > static_cast<qsizetype>(edi::assistant::Limits::stream_items))
            throw std::invalid_argument("Invalid native relation batch");
        std::vector<edi::assistant::detail::NativeAliasInput> aliases;
        std::vector<edi::assistant::detail::NativeConstraintInput> constraints;
        const auto text = [](const Object& row, const char* key, quint64 limit) {
            const auto field = row.value(key);
            if (!field.isString() || field.toString().isEmpty() || static_cast<quint64>(field.toString().size()) > limit)
                throw std::invalid_argument("Invalid native relation text");
            const auto bytes = field.toString().toUtf8();
            if (static_cast<quint64>(bytes.size()) > limit || bytes.contains('\0')) throw std::invalid_argument("Invalid native relation text");
            return bytes.toStdString();
        };
        for (const auto& value : aliasValue.toArray()) {
            if (!value.isObject()) throw std::invalid_argument("Invalid native alias row");
            const auto row = value.toObject(); shape(row, {"id", "path"});
            aliases.push_back({text(row, "id", edi::assistant::Limits::id_bytes), text(row, "path", edi::assistant::Limits::id_bytes)});
        }
        for (const auto& value : constraintValue.toArray()) {
            if (!value.isObject()) throw std::invalid_argument("Invalid native constraint row");
            const auto row = value.toObject(); shape(row, {"id", "expression", "enabled"});
            if (!row.value("enabled").isBool()) throw std::invalid_argument("Native constraint enabled must be boolean");
            constraints.push_back({text(row, "id", edi::assistant::Limits::id_bytes), text(row, "expression", edi::assistant::Limits::context_bytes), row.value("enabled").toBool()});
        }
        return edi::assistant::detail::prepare_relation_append(project, aliases, constraints);
    }
    if (name != "set_parameters" && name != "set_free") return {};
    const bool values = name == "set_parameters";
    const auto field = args.value(values ? "values" : "flags");
    if (!field.isArray() || field.toArray().isEmpty() || field.toArray().size() > static_cast<qsizetype>(edi::assistant::Limits::stream_items))
        throw std::invalid_argument("Native parameter batch exceeds its limit");
    std::vector<std::pair<std::string, double>> edits;
    std::vector<std::pair<std::string, bool>> flags;
    for (const auto& item : field.toArray()) {
        if (!item.isObject()) throw std::invalid_argument("Invalid native parameter batch");
        const auto row = item.toObject();
        shape(row, values ? QSet<QString>{"path", "value"} : QSet<QString>{"path", "free"});
        const auto pathValue = row.value("path");
        if (!pathValue.isString() || pathValue.toString().isEmpty() || pathValue.toString().toUtf8().size() > static_cast<qsizetype>(edi::assistant::Limits::id_bytes))
            throw std::invalid_argument("Invalid native parameter path");
        const auto path = pathValue.toString().toStdString();
        if (values) {
            if (!row.value("value").isDouble() || !std::isfinite(row.value("value").toDouble())) throw std::invalid_argument("Native parameter value must be finite");
            edits.emplace_back(path, row.value("value").toDouble());
        } else {
            if (!row.value("free").isBool()) throw std::invalid_argument("Native free flag must be boolean");
            flags.emplace_back(path, row.value("free").toBool());
        }
    }
    if (values) return edi::assistant::detail::prepare_parameter_edit(project, edits);
    return edi::assistant::detail::prepare_parameter_edit(project, flags, nullptr, &beforeFlags);
}
} // namespace edi_app
