// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_native_tools.hpp"
#include "assistant_action_refusal.hpp"
#include <QJsonDocument>
#include "assistant_native_create.hpp"
#include "background_input.hpp"
#include "../../core/src/assistant_parameter_edits.hpp"
#include "../../core/src/assistant_relation_edits.hpp"
#include "edi/assistant_limits.hpp"
#include "edi/assistant_files.hpp"
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
    add("set_parameters", "Set independent parameter values after complete native validation. Normal mode is one atomic edit/Undo; Show actions uses original exposed controls in order, separate Undo per change and honest complete/partial/uncertain outcomes.",
        {{"values", Object{{"type", "array"}, {"minItems", 1}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"path", text}, {"value", Object{{"type", "number"}}}}, {"path", "value"})}}}}, {"values"});
    add("set_free", "Choose actual independent fittable parameter flags with physical/symmetry validation. Normal mode is one atomic edit/Undo; Show actions uses original exposed controls in order with separate Undo per change and honest complete/partial/uncertain outcomes.",
        {{"flags", Object{{"type", "array"}, {"minItems", 1}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"path", text}, {"free", Object{{"type", "boolean"}}}}, {"path", "free"})}}}}, {"flags"});
    add("run_fit", "Run the displayed Edi project's real single/joint native fit and await actual publication/outcome. This is a live fit, not an isolated accepted-best trial.");
    add("create_cwl_project", "Create a native single-phase powder CW neutron project from two genuine selected-file IDs and an explicit scientific recipe, or populate the SAME scientifically empty current project with one Undo while preserving its identity/metadata/settings/path. Never replaces a nonempty project. Show actions uses the existing Project Create, Experiment Create/type/instrument/profile/background and Analysis controls with factual per-step partial outcomes and ordinary Undo behavior. File loads show the original Load pointer/click cue without delivering input or opening a dialog, then perform the validated approved-file import; manual Load keeps its system dialog. No duplicate import form or atomic GUI batch is used. Normal mode uses the native preparation directly. recipe project_name/description apply only when no project is open. No fit or save is implied; existing-directory saving is not this operation.",
        {{"cif_file_id", text}, {"data_file_id", text}, {"recipe", native_cwl_recipe_schema()}}, {"cif_file_id", "data_file_id", "recipe"});
    // Public canonical schemas apply only to these four new native actions.
    tools.append(Object{{"type","function"},{"name","load_structure"},{"description","Append one structure to the current project from an admitted immutable file_id through the original Structure Load reader/Undo. Show actions gives only the original Load pointer/click cue, not a dispatched click or file dialog. Original source identity must remain current. No recreation, path grant, fit or save."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"file_id":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","file_id"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","create_experiment"},{"description","Append one original default calculation-only experiment, preserving the current project and structures. Return actual member/type/links; configure only needed type choices before data."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120}},"required":["purpose"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","set_experiment_type"},{"description","Set one original enabled beam/probe choice on the exact calculation-only experiment, returning its actual replaced member. Equal type is a no-op. Replacement can reset settings, reported factually."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"oneOf":[{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"experiment":{"type":"string","minLength":1,"maxLength":256},"axis":{"const":"beamMode"},"token":{"enum":["constant wavelength","time-of-flight"]}},"required":["purpose","experiment","axis","token"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"experiment":{"type":"string","minLength":1,"maxLength":256},"axis":{"const":"radiationProbe"},"token":{"enum":["neutron","xray"]}},"required":["purpose","experiment","axis","token"],"additionalProperties":false}]})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","load_data"},{"description","Load an admitted immutable measurement into the exact calculation-only experiment through original Load data/readers/Undo. Show actions gives only the original Load pointer/click cue without a file dialog; original source identity must remain current. Return actual renamed member/reader facts; do not replace measured data or implicitly change type."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"experiment":{"type":"string","minLength":1,"maxLength":256},"file_id":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","experiment","file_id"],"additionalProperties":false})schema")).object()}});
    add("acquire_inputs", "Capture immutable local input files only from an opaque scope_id in the current genuine user input_scopes. No path, URL, glob or command argument is accepted. Returns file IDs, source ordinal, reader hints and counts; it does not claim scientific import. Use returned IDs with create_cwl_project and inspect the actual native project afterward. Already captured sources are not reread. Stale, changed, protected or oversized sources refuse without replacing the prior selection.",
        {{"scope_id",text}},{"scope_id"});
    add("save_project", "Save the settled current single/joint native project, verify reopen and keep the same active owner. Omitted destination saves its genuine already-owned Session directory, preserving its actual name/path and ignoring an unused fresh name. If it has no owned directory, omission uses the original fresh-name human Save As choice. Explicit destination=fresh always uses that one-operation choice; explicit current requires an owned directory and no name/path. Show actions uses the genuine Save button and fresh-name Save As form; normal mode uses the same bounded writer directly. No unrelated overwrite, scan or external report assets.",
        {{"destination", Object{{"type","string"},{"enum",Array{"fresh","current"}},{"description","Omit to save an already-owned Session directory, ignoring any unused fresh name; without one, omission uses fresh Save As. fresh explicitly requests Save As. current requires an owned directory and forbids name/path."}}},
         {"name", Object{{"type","string"},{"minLength",1},{"maxLength",static_cast<int>(edi::assistant::SelectedFileLimits::name_bytes)},
            {"description","Suggested fresh project directory basename for the one-operation original Save As chooser; spaces and Unicode are supported within the shared 512 UTF-8-byte Save As limit. No separators, dot components, NUL, trailing dot/space or existing destination. A chat path never grants access. Required only when a fresh destination is used; ignored for omitted destination with an owned directory, and forbidden for explicit current."}}}}, {});
    add("add_relations", "Append explicit affine alias/constraint declarations to the displayed project. Normal mode validates one atomic batch with one Undo; Show actions uses the existing Aliases/Constraints append, ID, parameter, expression and enable controls, each with its ordinary Undo. Visible interruption may leave actual partial edits, reported with complete/atomic/steps_completed facts. Existing relations/composition are preserved; this is not a trial or fit.",
        {{"aliases", Object{{"type", "array"}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"id", text}, {"path", text}}, {"id", "path"})}}},
         {"constraints", Object{{"type", "array"}, {"minItems", 1}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"id", text}, {"expression", Object{{"type", "string"}, {"minLength", 1}, {"maxLength", static_cast<int>(edi::assistant::Limits::context_bytes)}}},
                {"enabled", Object{{"type", "boolean"}}}}, {"id", "expression", "enabled"})}}}}, {"aliases", "constraints"});
    add("edit_background", "Add, update or remove one explicit measured line-segment background anchor in the CURRENT selected experiment, through the shared background editor. Normal mode has one atomic Undo; Show actions has ordinary per-control Undo and factual complete/partial steps. Position uses native measured axis units (CW two-theta degrees or TOF microseconds). Add/update require position, intensity and free; remove must omit all three. Existing data, other anchors and declared relations remain unchanged. Show actions uses the original Background Add, row ID/position/intensity, parameter-menu refine and Remove controls. It does not use a setup form or atomic sequence promise.",
        {{"experiment", text}, {"operation", Object{{"type","string"},{"enum",Array{"add","update","remove"}}}}, {"id", text},
         {"position", Object{{"type","number"},{"description","Required for add/update only, within the measured axis"}}},
         {"intensity", Object{{"type","number"},{"description","Required for add/update only, actual measured intensity units"}}},
         {"free", Object{{"type","boolean"},{"description","Required for add/update only, refine this independent intensity"}}}}, {"experiment","operation","id"});
    return tools;
}
bool assistant_native_tool(const QString& name) {
    return individual_app_action(name) || name == "acquire_inputs" || name == "inspect_project" || name == "list_parameters" || name == "diagnostics" ||
        name == "set_parameters" || name == "set_free" || name == "run_fit" || name == "create_cwl_project" || name == "add_relations" || name == "save_project" || name == "edit_background";
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
    if(individual_app_action(name)) {
        if((name=="load_structure" || name=="load_data") && (!args.value("file_id").isString() || args.value("file_id").toString().isEmpty()))
            throw ActionRefusal("input_required","file_id");
        if((name=="load_data" || name=="set_experiment_type") && (!args.value("experiment").isString() || args.value("experiment").toString().isEmpty()))
            throw ActionRefusal("target_unavailable","experiment");
    }
    if(name=="load_structure") shape(args,{"purpose","file_id"});
    else if(name=="load_data") shape(args,{"purpose","experiment","file_id"});
    else if(name=="set_experiment_type") shape(args,{"purpose","experiment","axis","token"});
    else if(name=="acquire_inputs") shape(args,{"purpose","scope_id"});
    else if (name == "edit_background") {
        if (args.value("operation") == "remove") shape(args,{"purpose","experiment","operation","id"});
        else shape(args,{"purpose","experiment","operation","id","position","intensity","free"});
    } else if (name == "create_cwl_project") shape(args, {"purpose", "cif_file_id", "data_file_id", "recipe"});
    else if (name == "add_relations") shape(args, {"purpose", "aliases", "constraints"});
    else if(name=="save_project") {
        if (!args.contains("destination")) {
            if(args.contains("name"))shape(args,{"purpose","name"});
            else shape(args,{"purpose"});
        }
        else if (args.value("destination") == "current") shape(args,{"purpose","destination"});
        else if (args.value("destination") == "fresh") shape(args,{"purpose","destination","name"});
        else throw std::invalid_argument("Save destination must be fresh or current");
    }
    else if (name == "set_parameters") shape(args, {"purpose", "values"});
    else if (name == "set_free") shape(args, {"purpose", "flags"});
    else if (assistant_native_tool(name)) shape(args, {"purpose"});
    else throw std::invalid_argument("Native action is unavailable");
}
NativeBackgroundInput assistant_native_background(edi::Project& project, const Object& args) {
    assistant_native_arguments("edit_background", args);
    if (!args.value("experiment").isString() || !args.value("operation").isString() || !args.value("id").isString())
        throw std::invalid_argument("Invalid background operation text");
    const auto name = background_text(args.value("experiment").toString());
    const bool remove = args.value("operation") == "remove";
    if (!remove && (!args.value("position").isDouble() || !args.value("intensity").isDouble() || !args.value("free").isBool()))
        throw std::invalid_argument("Background add/update requires actual numeric values and a boolean free flag");
    auto input = background_input(args.value("operation").toString(), args.value("id").toString(),
        remove ? 0 : args.value("position").toDouble(), remove ? 0 : args.value("intensity").toDouble(), !remove && args.value("free").toBool());
    for (const auto& experiment : project.experiments) {
        if (experiment->name.value().size() > edi::assistant::Limits::id_bytes)
            throw std::length_error("The background experiment identity exceeds its admitted capacity");
        if (edi::KeyTraits<edi::BraggPdExperiment>::canonical(experiment->name.value()) == name) return {experiment.get(), std::move(input)};
    }
    throw std::invalid_argument("The original background experiment is unavailable");
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
