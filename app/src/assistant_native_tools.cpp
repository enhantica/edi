// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_native_tools.hpp"
#include "assistant_action_refusal.hpp"
#include "codex_agent.hpp"
#include "../../core/src/assistant_json.hpp"
#include <QJsonDocument>
#include "assistant_native_create.hpp"
#include "background_input.hpp"
#include "edi/selectors.hpp"
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
namespace {
QJsonArray native_tool_specs(bool include_profiles) {
    Array tools;
    const Object text{{"type", "string"}, {"minLength", 1}, {"maxLength", 256}};
    const Object purpose{{"type", "string"}, {"minLength", 1}, {"maxLength", 120},
        {"description", "A concise purpose for this action, not a claim that it succeeded"}};
    const auto add = [&](const char* name, const char* description, Object properties = {}, Array required = {}) {
        properties["purpose"] = purpose; required.append("purpose");
        tools.append(Object{{"type", "function"}, {"name", name}, {"description", description}, {"inputSchema", object(properties, required)}});
    };
    add("inspect_project", "Inspect Edi's actual currently displayed project/context, including native_state.calculations: exact dataset published error/stale and calculated-column count/availability. Idle or available stale points do not prove success or viewport visibility. No mutation.");
    add("list_parameters", "Read actual native parameter paths/values/free flags and dependence. No mutation.");
    add("diagnostics", "Read actual available native physical diagnostics plus original app native_state.calculations for each exact dataset: published error/stale and calculated-column count/availability. Published old errors and idle are not current success; calculated availability is not legend/series visibility. No mutation.");
    add("set_parameters", "Set independent parameter values after complete native validation. Normal mode is one atomic edit/Undo; Show actions navigates/cues original exposed controls in order then calls their ordinary app parameter setters, with no scientific key/click input; separate Undo per change and actual applied/published receipts determine honest complete/partial/uncertain outcomes.",
        {{"values", Object{{"type", "array"}, {"minItems", 1}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"path", text}, {"value", Object{{"type", "number"}}}}, {"path", "value"})}}}}, {"values"});
    add("set_free", "Choose actual independent fittable parameter flags with physical/symmetry validation. Normal mode is one atomic edit/Undo; Show actions navigates/cues original exposed controls then uses ordinary app free setters; exact whole eligible uniform groups show/cue the existing Free menu and invoke its ordinary action, subsets use their actual checkbox cues and ordinary per-row methods. Separate Undo and actual applied/published receipts determine honest complete/partial/uncertain outcomes.",
        {{"flags", Object{{"type", "array"}, {"minItems", 1}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"path", text}, {"free", Object{{"type", "boolean"}}}}, {"path", "free"})}}}}, {"flags"});
    add("run_fit", "Run the displayed Edi project's real single/joint native fit and await actual publication/outcome. This is a live fit, not an isolated accepted-best trial. For the current project's Report preview, offer [Open Report page](edi:report): only the user's click navigates to the existing enabled Report page. Do not discover or select a desktop/CUA app by name for this navigation. The link does not generate or save a report.");
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
    tools.append(Object{{"type","function"},{"name","read_selected_file"},{"description","Read exact strict UTF-8 text from ONE current admitted file_id, never a path. offset/max_bytes are byte positions, at most the existing 65536-byte read bound. Returns selected_text with original collection/generation, total_bytes, exact start/end/next_offset, eof and complete. complete means this range covers the entire source, not just a finished chunk. A final later chunk can have eof=true and complete=false. max_bytes=0 probes a valid scalar boundary; a positive range too small for the next scalar refuses. No silent truncation/normalization, raw filesystem reader, converter or scientific edit. Same read in both Show-actions modes; no project required. Use subsequent explicit ranges against the same returned identity for partial text; do not ask to paste the same readable attachment again."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"file_id":{"type":"string","minLength":1,"maxLength":256},"offset":{"type":"integer","minimum":0,"maximum":16777216},"max_bytes":{"type":"integer","minimum":0,"maximum":65536}},"required":["purpose","file_id","offset","max_bytes"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","create_structure"},{"description","Create one structure through the original app Create method. It provides ONE actual initial atom, not the requested target structure. Return actual structure/sites. Reuse/update that first atom for the first target; append only subsequent required atoms. Rename with edit_structure, and use existing parameter tools for numeric/free values. No generated CIF or copied factory. Same ordinary method both modes; ON gives genuine control cues."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120}},"required":["purpose"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","edit_structure"},{"description","Edit ONE exact current structure through its original ordinary setter: rename, space_group_name, space_group_number or space_group_setting. HM/number/setting are linked; inspect actual returned fields before the next edit. Number 0 clears its stored explicit number; an unknown typed name/setting can be stored unresolved just like manual input, never a calculation-success claim. Preserve original default-setting behavior, science and Undo. Equal canonical state skips setter/cue/Undo. No numeric shadow fields; use existing parameter tools."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"oneOf":[{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"rename"},"value":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","structure","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"space_group_name"},"value":{"type":"string","maxLength":256}},"required":["purpose","structure","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"space_group_number"},"value":{"type":"integer","minimum":0,"maximum":230}},"required":["purpose","structure","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"space_group_setting"},"value":{"type":"string","maxLength":256}},"required":["purpose","structure","operation","value"],"additionalProperties":false}]})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","edit_atom"},{"description","Edit ONE atom in an exact current structure through original atom-row methods: append returns actual generated atom_id/defaults; text changes only label/typeSymbol/wyckoffLetter; remove explicitly targets atom_id; adp_type uses original Biso/Uiso/Bani/Uani/beta conversion. Reuse Create's initial atom before appending later required atoms. Explicit renamed IDs must be used subsequently. Coordinates/occupancy/ADP numbers/free use existing parameter tools with actual paths. Compare stored values and skip equal setter/cue/Undo; preserve ordinary validation and partial facts. Same original methods both modes, no keyboard scientific writer or generated file."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"oneOf":[{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"append"}},"required":["purpose","structure","operation"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"remove"},"atom":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","structure","operation","atom"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"text"},"atom":{"type":"string","minLength":1,"maxLength":256},"field":{"const":"label"},"value":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","structure","operation","atom","field","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"text"},"atom":{"type":"string","minLength":1,"maxLength":256},"field":{"const":"typeSymbol"},"value":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","structure","operation","atom","field","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"text"},"atom":{"type":"string","minLength":1,"maxLength":256},"field":{"const":"wyckoffLetter"},"value":{"type":"string","maxLength":256}},"required":["purpose","structure","operation","atom","field","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"maxLength":120},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"adp_type"},"atom":{"type":"string","minLength":1,"maxLength":256},"value":{"enum":["Biso","Uiso","Bani","Uani","beta"]}},"required":["purpose","structure","operation","atom","value"],"additionalProperties":false}]})schema")).object()}});
    Array profile_tokens;
    if(include_profiles)for (const auto mode : {edi::BeamModeEnum::CONSTANT_WAVELENGTH, edi::BeamModeEnum::TIME_OF_FLIGHT})
        edi::visit_supported_peak_profiles(mode,[&](const std::string& token) {
            // Original mode-specific visitor emits each supported token once;
            // the registry gives each extension one beam mode.
            profile_tokens.append(QString::fromUtf8(token.data(),static_cast<qsizetype>(token.size())));
        });
    Object experiment_purpose=purpose;experiment_purpose.remove("description");
    Array experiment_branches;
    for (const auto* operation : {"peak_profile","exclusion_append","exclusion_start","exclusion_end","exclusion_remove"}) {
        Object fields{{"purpose",experiment_purpose},{"experiment",text},{"operation",Object{{"const",operation}}}};
        Array required{"purpose","experiment","operation"};
        const auto op=QLatin1StringView(operation);
        if (op==QLatin1StringView("peak_profile")) {
            fields["value"]=Object{{"type","string"},{"enum",profile_tokens}};required.append("value");
        } else if (op!=QLatin1StringView("exclusion_append")) {
            fields["region"]=text;required.append("region");
            if (op!=QLatin1StringView("exclusion_remove")) {fields["value"]=Object{{"type","number"}};required.append("value");}
        }
        experiment_branches.append(object(fields,required));
    }
    tools.append(Object{{"type","function"},{"name","edit_experiment"},
        {"description","Change ONE exact current experiment through original peak-profile or exclusion-row app methods. Profile value must be an original option for its beam mode; changing profiles can add/drop optional settings at original defaults. Exclusion append keeps the ordinary generated ID/default bounds; use its actual returned region ID for later start/end/remove calls. Bounds are literal dataset-axis units, never automatically sorted/clamped. Equal stored profile/bound values skip setters/cues/Undo. Both modes use the same ordinary method/validation/history; Show actions adds original navigation/reveal and visual-only cues. Inspect actual IDs/settings and partial applied/published facts; do not retry uncertain writes. No parser/converter, absorption/weight/link/window setting or fit is implied."},
        {"inputSchema",Object{{"oneOf",experiment_branches}}}});
    add("acquire_inputs", "Capture immutable local input files only from an opaque scope_id in the current genuine user input_scopes. No path, URL, glob or command argument is accepted. Returns file IDs, source ordinal, reader hints and counts; it does not claim scientific import. Use returned IDs with create_cwl_project and inspect the actual native project afterward. Already captured sources are not reread. Stale, changed, protected or oversized sources refuse without replacing the prior selection.",
        {{"scope_id",text}},{"scope_id"});
    add("save_project", "Save the settled current project using the ordinary app Save method for its existing owned directory; fresh Save As retains its original verified export path. Omitted destination saves its genuine already-owned Session directory, preserving its actual name/path and ignoring an unused fresh name. If it has no owned directory, omission uses the original fresh-name human Save As choice. Explicit destination=fresh always uses that one-operation choice; explicit current requires an owned directory and no name/path. For current saving both modes call the same ordinary Session Save; Show actions gives a visual-only cue at Save without dispatching a click or opening a form. saved/committed and active retain the actual ordinary result/owner facts. For successful ordinary saved=true and active=true with no failure or uncertainty, say 'Project saved.' Do not add unrequested UI-completion or reopen caveats for presentation_complete=false or reopened=false. Report genuine failure, uncertainty, owner change and explicitly requested verification truthfully. Fresh Save As retains its genuine button/name form and protected export. No unrelated overwrite or model path authority.",
        {{"destination", Object{{"type","string"},{"enum",Array{"fresh","current"}},{"description","Omit to save an already-owned Session directory, ignoring any unused fresh name; without one, omission uses fresh Save As. fresh explicitly requests Save As. current requires an owned directory and forbids name/path."}}},
         {"name", Object{{"type","string"},{"minLength",1},{"maxLength",static_cast<int>(edi::assistant::SelectedFileLimits::name_bytes)},
            {"description","Suggested fresh project directory basename for the one-operation original Save As chooser; spaces and Unicode are supported within the shared 512 UTF-8-byte Save As limit. No separators, dot components, NUL, trailing dot/space or existing destination. A chat path never grants access. Required only when a fresh destination is used; ignored for omitted destination with an owned directory, and forbidden for explicit current."}}}}, {});
    add("add_relations", "Append explicit affine alias/constraint declarations to the displayed project. Normal mode validates one atomic batch with one Undo; Show actions uses the existing Aliases/Constraints append, ID, parameter, expression and enable controls, each with its ordinary Undo. Visible interruption may leave actual partial edits, reported with complete/atomic/steps_completed facts. Existing relations/composition are preserved; this is not a trial or fit.",
        {{"aliases", Object{{"type", "array"}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"id", text}, {"path", text}}, {"id", "path"})}}},
         {"constraints", Object{{"type", "array"}, {"minItems", 1}, {"maxItems", static_cast<int>(edi::assistant::Limits::stream_items)},
            {"items", object({{"id", text}, {"expression", Object{{"type", "string"}, {"minLength", 1}, {"maxLength", static_cast<int>(edi::assistant::Limits::context_bytes)}}},
                {"enabled", Object{{"type", "boolean"}}}}, {"id", "expression", "enabled"})}}}}, {"aliases", "constraints"});
    add("edit_background", "Add, update or remove one explicit measured line-segment background anchor, or explicitly name all current anchors from their positions in the CURRENT selected experiment, through the shared background editor. Normal mode has one atomic Undo; Show actions has ordinary per-control Undo and factual complete/partial steps. Position uses native measured axis units (CW two-theta degrees or TOF microseconds). Add/update require position, intensity and free; add may omit id to retain the ordinary app Add identity, while an explicit custom id is honored. Update/remove require the actual existing id. Successful non-remove point edits return the actual background_id. Remove must omit position/intensity/free. For name_from_positions supply only purpose, experiment and operation: it invokes the original whole-table Ids from positions action once, with ordinary Undo. Existing add/update/remove IDs and values stay explicit; naming is never inferred from later calls. Show actions uses original Add/position/explicit-ID/Remove and Ids controls; intensity and Analysis free controls give visual-only cues followed by their ordinary app parameter setters. It does not use a setup form or atomic sequence promise.",
        {{"experiment", text}, {"operation", Object{{"type","string"},{"enum",Array{"add","update","remove","name_from_positions"}}}}, {"id", text},
         {"position", Object{{"type","number"},{"description","Required for add/update only, within the measured axis"}}},
         {"intensity", Object{{"type","number"},{"description","Required for add/update only, actual measured intensity units"}}},
         {"free", Object{{"type","boolean"},{"description","Required for add/update only, refine this independent intensity"}}}}, {"experiment","operation"});
    // Each operation shape is closed; only Add may omit its ID.
    auto tool=tools.last().toObject();auto schema=tool.value("inputSchema").toObject();
    const auto properties=schema.value("properties").toObject();
    const auto branch=[&](Array operations,Array fields) {
        Object selected;
        for(const auto& field:fields)selected[field.toString()]=properties.value(field.toString());
        selected["operation"]=Object{{"type","string"},{"enum",operations}};
        return object(selected,fields);
    };
    schema["oneOf"]=Array{
        branch(Array{"add","update"},Array{"purpose","experiment","operation","id","position","intensity","free"}),
        branch(Array{"add"},Array{"purpose","experiment","operation","position","intensity","free"}),
        branch(Array{"remove"},Array{"purpose","experiment","operation","id"}),
        branch(Array{"name_from_positions"},Array{"purpose","experiment","operation"})};
    tool["inputSchema"]=schema;tools[tools.size()-1]=tool;
    return tools;
}
} // namespace
QJsonArray assistant_native_tool_names() {
    return {"inspect_project","list_parameters","diagnostics","set_parameters","set_free","run_fit",
        "create_cwl_project","load_structure","create_experiment","set_experiment_type","load_data",
        "read_selected_file","create_structure","edit_structure","edit_atom","edit_experiment",
        "acquire_inputs","save_project","add_relations","edit_background"};
}
quint64 assistant_native_tool_specs_preparation_bytes() {
    using Limits=edi::assistant::Limits;
    // Only fixed source literals are built here. The unbounded enum is absent.
    const auto fixed=native_tool_specs(false);
    quint64 encoded=0;
    if(!codex_encoded_size(fixed,Limits::context_bytes,encoded))
        throw std::length_error("Native catalogue exceeds capacity");
    // Finite schema's decoded strings/keys fit its encoded UTF-8 spelling.
    quint64 retained=encoded*sizeof(QChar)+fixed.size()*sizeof(QJsonValue);
    const auto charge=[&](quint64 bytes) {
        if(bytes>Limits::stream_retained_bytes-retained)throw std::length_error("Native catalogue exceeds capacity");
        retained+=bytes;
    };
    bool first=true;
    for(const auto mode:{edi::BeamModeEnum::CONSTANT_WAVELENGTH,edi::BeamModeEnum::TIME_OF_FLIGHT})
        edi::visit_supported_peak_profiles(mode,[&](const std::string& token) {
            if(!edi::assistant::detail::utf8(token))throw std::invalid_argument("Native profile option is not UTF-8");
            const auto bytes=edi::json::encoded_string_size(token,Limits::context_bytes);
            const auto comma=first?0u:1u;
            if(bytes>Limits::context_bytes-encoded || comma>Limits::context_bytes-encoded-bytes)
                throw std::length_error("Native catalogue exceeds capacity");
            encoded+=bytes+comma;first=false;
            // QString conversion and the independent Qt JSON string can overlap.
            // Valid UTF-8 has no more UTF-16 units than input bytes. Admit both
            // before either allocation, plus its enum entry and encoded role.
            if(token.size()>Limits::stream_retained_bytes/(2*sizeof(QChar)))
                throw std::length_error("Native catalogue exceeds capacity");
            charge(2*token.size()*sizeof(QChar));charge(sizeof(QJsonValue));
        });
    charge(encoded); // Actual complete catalogue payload, also held during encoding.
    return retained;
}
QJsonArray assistant_native_tool_specs() {
    // Every full builder entrance first checks the same existing finite limits;
    // State additionally owns this role in the joint disclosure account.
    (void)assistant_native_tool_specs_preparation_bytes();
    return native_tool_specs(true);
}
bool assistant_native_tool(const QString& name) {
    return individual_app_action(name) || name == "read_selected_file" || name == "acquire_inputs" || name == "inspect_project" || name == "list_parameters" || name == "diagnostics" ||
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
    if(name=="edit_experiment") {
        const auto id_ok=[](const QJsonValue& value) {
            return value.isString() && !value.toString().isEmpty() && !value.toString().contains(QChar(0)) &&
                value.toString().toUtf8().size()<=edi::assistant::Limits::id_bytes;
        };
        if(!id_ok(args.value("experiment")))throw ActionRefusal("target_unavailable","experiment");
        const auto op=args.value("operation").toString();
        if(op=="peak_profile") {
            shape(args,{"purpose","experiment","operation","value"});
            if(!args.value("value").isString())throw ActionRefusal("unsupported_type","value");
        } else if(op=="exclusion_append")shape(args,{"purpose","experiment","operation"});
        else if(op=="exclusion_start" || op=="exclusion_end") {
            shape(args,{"purpose","experiment","operation","region","value"});
            if(!id_ok(args.value("region")))throw ActionRefusal("target_unavailable","region");
            if(!args.value("value").isDouble() || !std::isfinite(args.value("value").toDouble()))throw ActionRefusal("invalid_range","value");
        } else if(op=="exclusion_remove") {
            shape(args,{"purpose","experiment","operation","region"});
            if(!id_ok(args.value("region")))throw ActionRefusal("target_unavailable","region");
        } else throw ActionRefusal("unsupported_input","field");
        return;
    }
    if(structure_app_action(name)) {
        if(name=="create_structure")shape(args,{"purpose"});
        else {
            if(!args.value("structure").isString() || args.value("structure").toString().isEmpty())throw ActionRefusal("target_unavailable","structure");
            if(name=="edit_structure")shape(args,{"purpose","structure","operation","value"});
            else if(args.value("operation")=="append")shape(args,{"purpose","structure","operation"});
            else if(args.value("operation")=="remove")shape(args,{"purpose","structure","operation","atom"});
            else if(args.value("operation")=="adp_type")shape(args,{"purpose","structure","operation","atom","value"});
            else shape(args,{"purpose","structure","operation","atom","field","value"});
        }
        return;
    }
    if(name=="read_selected_file") {
        shape(args,{"purpose","file_id","offset","max_bytes"});
        if(!args.value("file_id").isString() || args.value("file_id").toString().isEmpty())throw ActionRefusal("input_required","file_id");
        for(const auto* field:{"offset","max_bytes"}) {
            const auto n=args.value(QLatin1StringView(field));
            const double maximum=QLatin1StringView(field)==QLatin1StringView("offset")?edi::assistant::SelectedFileLimits::file_bytes:edi::assistant::SelectedFileLimits::read_bytes;
            if(!n.isDouble() || !std::isfinite(n.toDouble()) || n.toDouble()<0 || std::floor(n.toDouble())!=n.toDouble() || n.toDouble()>maximum)
                throw ActionRefusal("invalid_range",field);
        }
    }
    else if(name=="load_structure") shape(args,{"purpose","file_id"});
    else if(name=="load_data") shape(args,{"purpose","experiment","file_id"});
    else if(name=="set_experiment_type") shape(args,{"purpose","experiment","axis","token"});
    else if(name=="acquire_inputs") shape(args,{"purpose","scope_id"});
    else if (name == "edit_background") {
        if(args.value("operation")=="name_from_positions")shape(args,{"purpose","experiment","operation"});
        else if(args.value("operation")=="add" && !args.contains("id"))shape(args,{"purpose","experiment","operation","position","intensity","free"});
        else if (args.value("operation") == "remove") shape(args,{"purpose","experiment","operation","id"});
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
    const bool names=args.value("operation")=="name_from_positions";
    const bool default_id=args.value("operation")=="add" && !args.contains("id");
    if (!args.value("experiment").isString() || !args.value("operation").isString() || (!names && !default_id && !args.value("id").isString()))
        throw std::invalid_argument("Invalid background operation text");
    const auto name = background_text(args.value("experiment").toString());
    const bool remove = args.value("operation") == "remove";
    if (!remove && !names && (!args.value("position").isDouble() || !args.value("intensity").isDouble() || !args.value("free").isBool()))
        throw std::invalid_argument("Background add/update requires actual numeric values and a boolean free flag");
    edi::BackgroundPointInput input;
    if(!names && !default_id)input = background_input(args.value("operation").toString(), args.value("id").toString(),
        remove ? 0 : args.value("position").toDouble(), remove ? 0 : args.value("intensity").toDouble(), !remove && args.value("free").toBool());
    for (const auto& experiment : project.experiments) {
        if (experiment->name.value().size() > edi::assistant::Limits::id_bytes)
            throw std::length_error("The background experiment identity exceeds its admitted capacity");
        if (edi::KeyTraits<edi::BraggPdExperiment>::canonical(experiment->name.value()) == name) {
            if(default_id) {
                if(experiment->background.size()>=edi::assistant::Limits::stream_items)
                    throw std::length_error("Background rows exceed the original admitted capacity");
                const auto ordinary=background_append_input(*experiment);
                input=background_input(QStringLiteral("add"),QString::fromStdString(ordinary.id),
                    args.value("position").toDouble(),args.value("intensity").toDouble(),args.value("free").toBool());
            }
            if(names && (experiment->background_type!="line-segment" || !experiment->data || experiment->calculation_only || experiment->background.empty()))
                throw std::invalid_argument("Position IDs require an existing measured line-segment background");
            if(names && experiment->background.size()>edi::assistant::Limits::stream_items)
                throw std::length_error("Background rows exceed the original admitted capacity");
            if(names)for(const auto& point:experiment->background)
                if(point->id.value().size()>edi::assistant::Limits::id_bytes || !std::isfinite(point->position.get()))
                    throw std::invalid_argument("The original background member is unavailable");
            return {experiment.get(), std::move(input),names};
        }
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
