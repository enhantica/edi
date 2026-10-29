// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_native_tools.hpp"
#include "assistant_recipe_refusal.hpp"
#include "assistant_action_refusal.hpp"
#include "codex_agent.hpp"
#include "../../core/src/assistant_json.hpp"
#include <QJsonDocument>
#include <QCoreApplication>
#include "assistant_native_create.hpp"
#include "background_input.hpp"
#include "edi/selectors.hpp"
#include "../../core/src/assistant_parameter_edits.hpp"
#include "../../core/src/assistant_relation_edits.hpp"
#include "edi/assistant_limits.hpp"
#include "edi/assistant_files.hpp"
#include <QSet>
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace edi_app {
namespace {
using Object = QJsonObject;
using Array = QJsonArray;
Object object(Object properties, Array required) {
    return {{"type", "object"}, {"properties", properties}, {"required", required}, {"additionalProperties", false}};
}
void shape(const Object& value, const QSet<QString>& keys) {
    const auto expected=keys.size()-(keys.contains("purpose") && !value.contains("purpose")?1:0);
    if (value.size() != expected) throw std::invalid_argument("Native action fields are missing or unsupported");
    for (auto i = value.constBegin(); i != value.constEnd(); ++i) if (!keys.contains(i.key()))
        throw std::invalid_argument("Unsupported native action field");
}
}
namespace {
QJsonArray native_tool_specs(bool include_profiles) {
    Array tools;
    const Object text{{"type", "string"}, {"minLength", 1}, {"maxLength", 256}};
    Object parameterPath=text;parameterPath["description"]="Copy the exact current parameters[].path returned by inspect_project or list_parameters. Do not use parameters[].unique_name or substitute a dataset/structure ID. Single-owner paths use experiment. or structure.; multiple owners use the actual offered experiments[ID]. or structures[ID]. path. Copy the returned string rather than constructing it.";
    const Object purpose{{"type", "string"}, {"minLength", 1},
        {"description", "Optional concise action purpose, not success. If omitted, Edi labels the action itself and records native-fallback provenance"}};
    const auto add = [&](const char* name, const char* description, Object properties = {}, Array required = {}) {
        properties["purpose"] = purpose; required.append("purpose");
        tools.append(Object{{"type", "function"}, {"name", name}, {"description", description}, {"inputSchema", object(properties, required)}});
    };
    add("create_project", "Create a NEW ordinary empty project in the current Edi window, including replacing an existing project when the user requested a new one. The normal unsaved-work guard preserves the original project through ordinary Save/Cancel; it never auto-discards. Uses the normal app Create API and current new-project preferences, with no scientific recipe, import or fit. Like the ordinary Create form, saves immediately under its remembered parent or Documents on desktop; existing destinations refuse. That saved receipt covers only the created state; later imports/edits require ordinary save_project before claiming them saved. Name, title and description are metadata; choose all three meaningfully from the genuine task without inventing authors. Supplied fields preserve their literal values. Omitted metadata uses normal defaults (default basename project). Continue with normal load_structure/create_experiment/load_data using the actual retained file IDs. Both modes use the same native Session owner; Show actions opens the genuine normal Create dialog, enters the requested fields and confirms its ordinary Create button. Never discover another app or ask the user to create it for you.",
        {{"name",Object{{"type","string"},{"minLength",2},{"maxLength",31},{"pattern","^[A-Za-z][A-Za-z0-9_.-]{1,30}$"},
            {"description","Original normal Name identifier: 2–31 ASCII characters, letter first, then letters/digits/underscore/hyphen/period; human-readable wording belongs in title. Preserve an explicit user Name without silent renaming."}}},{"title",Object{{"type","string"},{"maxLength",32767},{"pattern","^[^\\u0000\\r\\n\\t]*$"},{"description","Original single-line Title field: at most 32767 UTF-16 units, with no NUL, newline, carriage-return or tab. The live original field validates before either action mode; supplied text is never truncated."}}},{"description",Object{{"type","string"}}}});
    add("show_report", "Open the CURRENT project's ordinary enabled Report preview through the same current-window tab navigation as the app. Both modes use the same owner; Show actions adds the existing tab cue. This navigates only; it does not generate/export/save a report or discover another application.");
    add("inspect_project", "Inspect Edi's actual currently displayed project/context. native_state.project_modified is the original captured project's GUI dirty flag, not a disk-verification receipt. Read native_state.interface_groups in actual current category-model/tier order (category groups only; admitted is compatibility, not enabled-control authority), and native_state.calculations: exact dataset published error/stale and calculated-column count/availability. Idle or available stale points do not prove success or viewport visibility. No mutation. inspect_project and diagnostics report native_state.calculations for each actual dataset. Pattern availability, published stale/error and last-published calculated point count are original app facts: idle is not success, an old stale error is not a new failure, and nonempty calculated points do not prove viewport/legend visibility or a current successful fit. Read calculation_error_present and bounded calculation_error (complete=false means omitted text) before proposing a scientific correction; do not silently clamp axes/change zero/wavelength or reinterpret exclusions to conceal a refusal. ");
    add("inspect_data", "Read an explicit slice of one exact current datasets[].id without changing the project, selection, calculation, fit, free flags or Undo. Native powder x/measured/sigma/calculated/background/residual columns are not display-decimated or transformed; single-crystal rows use original reflection order and F-squared values with actual native fit-use flags. Missing or nonfinite cells are null, distinct from zero. Read each column's independent availability, length and unit; a live fit_frame is not an adopted current result. source=bragg returns separate phase reflection slices with their own extents and source-row mapping, never rows zipped to measurement points. Copy the exact dataset_id from inspect_project, and supply start/count explicitly. Default project context intentionally contains no curve arrays.",
        {{"dataset_id",text},{"start",Object{{"type","integer"},{"minimum",0}}},{"count",Object{{"type","integer"},{"minimum",0}}},
         {"source",Object{{"enum",Array{"data","bragg"}}}}},{"dataset_id","start","count"});
    add("list_parameters", "Read actual native parameter paths/values/free flags, dependence and native refinable/fittable/fit_reason. These eligibility facts govern freeing a flag, not whether a supported independent numeric setup value can be set. Optional file_value/file_su are the already-published current native file spelling; when file_su is present, quote that pair verbatim as value ± SU instead of inventing parenthetic digits. Raw value/uncertainty remain available; null file_su means that spelling carries no SU, not zero. No mutation.");
    add("diagnostics", "Read actual available native physical diagnostics plus original app native_state.calculations for each exact dataset: published error/stale and calculated-column count/availability. Published old errors and idle are not current success; calculated availability is not legend/series visibility. Optional developer_feedback records concise observed app/tool/skill improvement suggestions only in the diagnostic work report, as unverified agent assessment; never put those suggestions in purpose, chat or the scientific report. Scientific caveats and user-needed errors remain public. No scientific mutation.",
        {{"developer_feedback",Object{{"type","string"},{"minLength",1},
            {"description","Optional diagnostic-only observed gap, proposed improvement and supporting call/source references. Not scientific conclusions or hidden reasoning."}}}});
    add("set_parameters", "Set independent parameter values after complete native validation. When Analysis is already the current project workflow, refinable values prefer its original Value table, with its actual category/filter and virtual-row reveal. Original Structure or Experiment setup controls remain the fallback for descriptors or values not supported by that table. Choose setup operations from actual native dependencies, admitted scientific evidence and explicit user scope. Map FullProf occupancy before writes: qraw=OccFP*M/m and, only for established common phase c, chemical occupancy=qraw/c with already-mapped scale times c*c once; preserve partial/shared fractions. Use fresh native_state.interface_groups to locate current controls, without imposing a universal scientific sequence. Preserve explicit values-array order. Normal mode follows the last changed requested member page and is one atomic edit/Undo; Show actions navigates/cues original exposed controls in order then calls their ordinary app parameter setters, with no scientific key/click input; separate Undo per change and actual applied/published receipts determine honest complete/partial/uncertain outcomes.",
        {{"values", Object{{"type", "array"}, {"minItems", 1},
            {"items", object({{"path", parameterPath}, {"value", Object{{"type", "number"}}}}, {"path", "value"})}}}}, {"values"});
    add("set_free", "Choose actual independent fittable parameter flags with physical/symmetry validation. For a delegated whole eligible category whose requested flags are uniform, send its complete actual current eligible membership in ONE set_free flags array so the native Free menu can prove exact membership; do not split that group into per-point calls. Preserve explicit subsets, supplied flags-array order and per-call scope; never add unrequested members, merge separate mutations or replay equal/partial/uncertain work. For delegated refinement choose identifiable supported groups and inspect actual outcomes as the evidence warrants; preserve fill-only scope and explicit flags. Plan related requested flags category by category; use the existing Free header only for exactly the whole eligible displayed category with one common flag, and actual row checkboxes for subsets. Never reorder an explicit flags array. Normal mode is one atomic edit/Undo; Show actions navigates/cues original exposed controls then uses ordinary app free setters; exact whole eligible uniform groups open the existing Free menu and physically click its visible Free/Fixed choice through the prearmed ordinary action once, subsets use their actual checkbox cues and ordinary per-row methods. Separate Undo and actual applied/published receipts determine honest complete/partial/uncertain outcomes.",
        {{"flags", Object{{"type", "array"}, {"minItems", 1},
            {"items", object({{"path", parameterPath}, {"free", Object{{"type", "boolean"}}}}, {"path", "free"})}}}}, {"flags"});
    add("undo_fit", "Undo exactly the most recent adopted single/joint fit through the ordinary current-project Undo method. Inspect the actual adopted undesired fit first and use only within authorized refinement. native_state.fit_undo_available is a factual semantic observation, rechecked at use; a later failed/preflight/preparation attempt, intervening edit or non-fit history refuses without undoing earlier good science. Show actions cues the actual enabled appbar Undo; normal mode calls the same ordinary method. An applied but unconfirmed reversal is spent once: inspect actual state rather than retry. No generic history Undo, refit, reset or Save is performed.");
    add("run_fit", "Run the real current single/joint fit within authorized scope and native type/data/eligibility prerequisites. Use current measured/calculated residual/alignment evidence (inspect_data if absent) and the supplied Evidence → Choice → Assessment strategy. This is a live adopted fit, not an isolated accepted-best trial. Read actual status/adopted/converged/objective; none alone establishes adequacy. Existing diagnostics/matching parameter rows are optional, not complete physical validation. The returned statistic belongs to THIS trial, not a later edited/saved model. Assess actual residuals, physics and weak identifiability before another fit consumes the sole Undo; use undo_fit only for the actual latest adopted candidate with native_state.fit_undo_available. Refused/unadopted attempts do not authorize undoing earlier science; uncertain effects require inspection, not replay. Preserve user calibration/chemical constraints/explicit flags. Only actual fit_reason=unanchored_cw_dilation identifies the free uniform wavelength/cell-scale guard; choose a supported objective-appropriate anchor without changing known calibration. Unknown errors do not prove that cause. Assistant-origin results do not automatically open a dialog; ordinary Report/status results controls expose them.");
    // Public canonical schemas apply only to these four new native actions.
    tools.append(Object{{"type","function"},{"name","load_structure"},{"description","Append one structure to the current project from an admitted immutable file_id through the original Structure Load reader/Undo. Show actions gives only the original Load pointer/click cue, not a dispatched click or file dialog. Original source identity must remain current. No recreation, path grant, fit or save."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1},"file_id":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","file_id"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","create_experiment"},{"description","Append one original default calculation-only experiment, preserving the current project and structures. Return actual member/type/links; keep actual native defaults for unspecified optional numerical starts and configure only needed type choices before data. Required measurement/calibration facts must come from genuine admitted input/calibration or the user, never an arbitrary factory placeholder. Choose creation and setup order from actual native dependencies, admitted scientific evidence and explicit user scope; no universal Structure/Experiment page sequence is required."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1}},"required":["purpose"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","set_experiment_type"},{"description","Set one original enabled sample-form/beam/probe choice on the exact calculation-only experiment, returning its actual replaced member. Equal type is a no-op. Replacement can reset settings, reported factually."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"oneOf":[{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"experiment":{"type":"string","minLength":1,"maxLength":256},"axis":{"const":"beamMode"},"token":{"enum":["constant wavelength","time-of-flight"]}},"required":["purpose","experiment","axis","token"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"experiment":{"type":"string","minLength":1,"maxLength":256},"axis":{"const":"radiationProbe"},"token":{"enum":["neutron","xray"]}},"required":["purpose","experiment","axis","token"],"additionalProperties":false}]})schema")).object()}});
    { // The same original type selector also owns powder/single-crystal routing.
        auto tool=tools.last().toObject();auto schema=tool.value("inputSchema").toObject();auto branches=schema.value("oneOf").toArray();
        branches.append(object({{"purpose",purpose},{"experiment",text},{"axis",Object{{"const","sampleForm"}}},
            {"token",Object{{"enum",Array{QString::fromLatin1(edi::token(edi::SampleFormEnum::POWDER)),QString::fromLatin1(edi::token(edi::SampleFormEnum::SINGLE_CRYSTAL))}}}}},
            {"purpose","experiment","axis","token"}));
        schema["oneOf"]=branches;tool["inputSchema"]=schema;tools[tools.size()-1]=tool;
    }
    tools.append(Object{{"type","function"},{"name","load_data"},{"description","Load an admitted immutable measurement into the exact calculation-only experiment through original Load data/readers/Undo. Show actions gives only the original Load pointer/click cue without a file dialog; original source identity must remain current. Return actual renamed member/reader facts; inspect native pattern summaries after loading. Read only a needed measurement header beforehand, not every numeric observation as conversation text. Do not replace measured data or implicitly change type."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1},"experiment":{"type":"string","minLength":1,"maxLength":256},"file_id":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","experiment","file_id"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","read_selected_file"},{"description","Read exact strict UTF-8 text from ONE current admitted file_id, never a path. offset/max_bytes are byte positions, at most the existing 65536-byte read bound. Returns selected_text with original collection/generation, total_bytes, exact start/end/next_offset, eof and complete. complete means this range covers the entire source, not just a finished chunk. A final later chunk can have eof=true and complete=false. max_bytes=0 probes a valid scalar boundary; a positive range too small for the next scalar refuses. No silent truncation/normalization, raw filesystem reader, converter or scientific edit. Same read in both Show-actions modes; no project required. For measurements, read only a header or ranges needed for format/source questions, then use load_data and native inspection for the full numeric dataset instead of streaming every observation into the conversation. Full source reads remain available when actually needed or requested; manual structure mapping may need the complete small structure text. Use subsequent explicit ranges against the same returned identity for partial text; do not ask to paste the same readable attachment again."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1},"file_id":{"type":"string","minLength":1,"maxLength":256},"offset":{"type":"integer","minimum":0,"maximum":16777216},"max_bytes":{"type":"integer","minimum":0,"maximum":65536}},"required":["purpose","file_id","offset","max_bytes"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","create_structure"},{"description","Create one structure through the original app Create method. It provides ONE actual initial atom, not the requested target structure. Return actual structure/sites. Reuse/update the actual initial atom for the first target instead of duplicating it. Choose supported cell/site/ADP operations from actual symmetry/type dependencies, scientific evidence and explicit scope; no universal row/page sequence is required. Rename with edit_structure, and use existing parameter tools for numeric/free values. No generated CIF or copied factory. Same ordinary method both modes; ON gives genuine control cues."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1}},"required":["purpose"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","edit_structure"},{"description","Edit ONE exact structure through its original ordinary setter, or explicitly select it with operation=select and no value. Select uses the ordinary current-index UI method, no scientific Edit/Undo/dirty; actual non-scan member IDs only. Both modes call the same method; ON gives original row reveal/visual-only cue. Confirm native_state.selected_structure_id, not a row index or decorated label; no-op selection skips navigation/cue. Scientific operations remain: rename, space_group_name, space_group_number or space_group_setting. HM/number/setting are linked; inspect actual returned fields before the next edit. Number 0 clears its stored explicit number; an unknown typed name/setting can be stored unresolved just like manual input, never a calculation-success claim. Preserve original default-setting behavior, science and Undo. Equal canonical state skips setter/cue/Undo. No numeric shadow fields; use existing parameter tools."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"oneOf":[{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"rename"},"value":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","structure","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"space_group_name"},"value":{"type":"string","maxLength":256}},"required":["purpose","structure","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"space_group_number"},"value":{"type":"integer","minimum":0,"maximum":230}},"required":["purpose","structure","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"space_group_setting"},"value":{"type":"string","maxLength":256}},"required":["purpose","structure","operation","value"],"additionalProperties":false}]})schema")).object()}});
    { // Extend the original structure union without changing its scientific branches.
        auto tool=tools.last().toObject();auto schema=tool.value("inputSchema").toObject();auto branches=schema.value("oneOf").toArray();
        branches.append(object({{"purpose",purpose},{"structure",text},{"operation",Object{{"const","select"}}}},{"purpose","structure","operation"}));
        schema["oneOf"]=branches;tool["inputSchema"]=schema;tools[tools.size()-1]=tool;
    }
    tools.append(Object{{"type","function"},{"name","edit_atom"},{"description","Edit ONE atom in an exact current structure through original atom-row methods: append returns actual generated atom_id/defaults; text changes only label/typeSymbol/wyckoffLetter; remove explicitly targets atom_id; adp_type uses original Biso/Uiso/Bani/Uani/beta conversion. Reuse Create's actual initial atom and preserve supplied coordinates/mapped chemical occupancy, with a Wyckoff declaration only when explicitly supplied. Choose later site/ADP operations from actual native dependencies and scientific evidence; explicit immediate operations remain exact. Use actual confirmed returned IDs; a refused rename establishes no new ID, and partial/uncertain effects need inspection before dependent calls. Coordinates/occupancy/ADP numbers/free use existing parameter tools with actual paths. Compare stored values and skip equal setter/cue/Undo; preserve ordinary validation and partial facts. Same original methods both modes, no keyboard scientific writer or generated file."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"oneOf":[{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"append"}},"required":["purpose","structure","operation"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"remove"},"atom":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","structure","operation","atom"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"text"},"atom":{"type":"string","minLength":1,"maxLength":256},"field":{"const":"label"},"value":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","structure","operation","atom","field","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"text"},"atom":{"type":"string","minLength":1,"maxLength":256},"field":{"const":"typeSymbol"},"value":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","structure","operation","atom","field","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"text"},"atom":{"type":"string","minLength":1,"maxLength":256},"field":{"const":"wyckoffLetter"},"value":{"type":"string","maxLength":256}},"required":["purpose","structure","operation","atom","field","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"adp_type"},"atom":{"type":"string","minLength":1,"maxLength":256},"value":{"enum":["Biso","Uiso","Bani","Uani","beta"]}},"required":["purpose","structure","operation","atom","value"],"additionalProperties":false}]})schema")).object()}});
    Array profile_tokens;
    if(include_profiles)for (const auto mode : {edi::BeamModeEnum::CONSTANT_WAVELENGTH, edi::BeamModeEnum::TIME_OF_FLIGHT})
        edi::visit_supported_peak_profiles(mode,[&](const std::string& token) {
            // Original mode-specific visitor emits each supported token once;
            // the registry gives each extension one beam mode.
            profile_tokens.append(QString::fromUtf8(token.data(),static_cast<qsizetype>(token.size())));
        });
    Array absorption_tokens;
    if(include_profiles)for(const auto mode:{edi::BeamModeEnum::CONSTANT_WAVELENGTH,edi::BeamModeEnum::TIME_OF_FLIGHT})
        for(const auto& token:edi::supported_absorption_families(mode)) {
            if(!edi::assistant::detail::utf8(token))throw std::invalid_argument("Native absorption option is not UTF-8");
            const auto value=QString::fromUtf8(token.data(),static_cast<qsizetype>(token.size()));
            if(!absorption_tokens.contains(value))absorption_tokens.append(value);
        }
    Array extinction_tokens,mosaic_tokens;
    if(include_profiles){for(const auto& token:edi::extinction_type_tokens())extinction_tokens.append(QString::fromStdString(token));
        for(const auto& token:edi::mosaic_distribution_tokens())mosaic_tokens.append(QString::fromStdString(token));}
    Object experiment_purpose=purpose;experiment_purpose.remove("description");
    Array experiment_branches;
    for (const auto* operation : {"select","peak_profile","absorption_type","extinction_type","mosaic_distribution","cutoff_fwhm","dataset_weight","exclusion_append","exclusion_start","exclusion_end","exclusion_remove","phase_append","phase_retarget","phase_enabled","phase_remove"}) {
        Object fields{{"purpose",experiment_purpose},{"experiment",text},{"operation",Object{{"const",operation}}}};
        Array required{"purpose","experiment","operation"};
        const auto op=QLatin1StringView(operation);
        if(op==QLatin1StringView("select")) {} // UI-only; no value/region/index.
        else if (op==QLatin1StringView("peak_profile")) {
            fields["value"]=Object{{"type","string"},{"enum",profile_tokens}};required.append("value");
        } else if(op==QLatin1StringView("absorption_type")) {
            fields["value"]=Object{{"type","string"},{"enum",absorption_tokens}};required.append("value");
        } else if(op==QLatin1StringView("extinction_type") || op==QLatin1StringView("mosaic_distribution")) {
            fields["value"]=Object{{"type","string"},{"enum",op==QLatin1StringView("extinction_type")?extinction_tokens:mosaic_tokens}};required.append("value");
        } else if(op==QLatin1StringView("cutoff_fwhm") || op==QLatin1StringView("dataset_weight")) {
            fields["value"]=Object{{"type","number"}};required.append("value");
        } else if(op==QLatin1StringView("phase_retarget") || op==QLatin1StringView("phase_enabled") || op==QLatin1StringView("phase_remove")) {
            fields["phase"]=text;required.append("phase");
            if(op!=QLatin1StringView("phase_remove")){fields["value"]=op==QLatin1StringView("phase_enabled")?Object{{"type","boolean"}}:text;required.append("value");}
        } else if (op!=QLatin1StringView("exclusion_append") && op!=QLatin1StringView("phase_append")) {
            fields["region"]=text;required.append("region");
            if (op!=QLatin1StringView("exclusion_remove")) {fields["value"]=Object{{"type","number"}};required.append("value");}
        }
        experiment_branches.append(object(fields,required));
    }
    tools.append(Object{{"type","function"},{"name","edit_experiment"},
        {"description","Choose supported setup/refinement actions from native type/data dependencies, scientific evidence and explicit scope. A profile family must exist before editing its coefficients; inspect reset settings and actual IDs. No universal Structure/Experiment/Analysis page sequence is required. Change ONE exact experiment through original app methods, or explicitly select it with operation=select and no value/region/index. Selection uses the ordinary current-index UI setter, no scientific Edit/Undo/dirty, and refuses scan file-selection semantics. Confirm native_state.selected_experiment_id; no-op selection skips navigation/cue. Both modes use the same setter, ON adds original row reveal/visual-only cue. absorption_type, extinction_type, mosaic_distribution, cutoff_fwhm and dataset_weight require the CURRENT selected experiment. Single-crystal extinction and mosaic selectors use Experiment Basic with actual extinction_type_options and mosaic_distribution_options; distribution is available only when the current type owns it. Type changes retain ordinary native defaults/Undo; crystal_radius/domain_radius/mosaic_spread use ordinary parameter paths/units, not a separate scalar setter. Absorption uses actual absorption_type_options and original coefficient family/default rules; cutoff is literal FWHM-window setting (nonpositive retains original full-window semantics); dataset weight is stored in all modes and affects the joint objective, not single-dataset calculated curves. Absorption/cutoff controls are Experiment Extras; weight is Analysis Extras Joint fit. Other operations retain original peak-profile/exclusion routing. Profile value must be an original option for its beam mode; changing profiles can add/drop optional settings at original defaults. Exclusion append keeps the ordinary generated ID/default bounds; use its actual returned region ID for later start/end/remove calls. Bounds are literal dataset-axis units, never automatically sorted/clamped. Equal stored profile/bound values skip setters/cues/Undo. Both modes use the same ordinary method/validation/history; Show actions reveals original controls and physically selects offered choice rows when required, with their sole prearmed ordinary apply. Other controls retain their existing cue/setter path. Inspect actual IDs/settings and partial applied/published facts; do not retry uncertain writes. Phase operations require this CURRENT selected experiment: phase_append uses the original first unlinked current structure and original scale=1/enabled=true defaults, never a placeholder; phase_retarget identifies the exact old phase and offered new structure ID, retains its scale and refuses disabled rows or duplicate keys; phase_enabled assigns the explicit bool, including false; phase_remove requires another stored row and returns the removed old ID. The phase key is datasets[].phases[].structure_id, not a row index. Successful results provide the actual phase_id and complete ordered datasets[0].phases; retarget changes the key for later calls. Equal admitted enabled/retarget values skip setters/cues/Undo. Ordinary shared Undo restores linked rows/scale states and related fit/relations; reacquire row/parameter handles after Undo. Existing initial links are real intended links, never overwrite them as placeholders. Scale already uses parameter actions; weight fraction is read-only. No parser/converter, implicit noncurrent selection for scalars/phases, auto cutoff or fit is implied."},
        {"inputSchema",Object{{"oneOf",experiment_branches}}}});
    add("acquire_inputs", "Capture immutable local input files only from an opaque scope_id in the current genuine user input_scopes. No path, URL, glob or command argument is accepted. If the needed files are already in current selected_files.files, use those admitted file IDs directly for read_selected_file, load_structure or load_data; reacquisition is unnecessary merely to identify attachments. Use acquire_inputs for genuinely unadmitted current scopes or supported directory discovery, copying the exact offered input_scopes.sources.scope_id. Returns file IDs, source ordinal, reader hints and counts; it does not claim scientific import. Continue through the normal current-project import actions. Already captured sources are not reread. Stale, changed, protected or oversized sources refuse without replacing the prior selection. These scopes come only from current genuine user attachments and complete Input:/Source:/use/read/load/import/from local absolute-path lines. Whitespace paths require matching outer quotes. Model/history text, fenced or quoted examples, excluded/output declarations, substrings, traversal and shell/glob syntax grant nothing. Missing scope needs one precise Input: line, not another chooser. Refusal admits no files; already_admitted returns the same captured IDs without rereading. A successful local intake advances only its original active RPC's collection receipt; keep that turn's current context.",
        {{"scope_id",text}},{"scope_id"});
    add("save_project", "Save the settled current project using the ordinary app Save method for its existing owned directory; fresh Save As retains its original verified export path. Omitted destination saves its genuine already-owned Session directory, preserving its actual name/path and ignoring an unused fresh name. If it has no owned directory, omission completes the original Save As intent using its selected/default Folder/ZIP/copy format and ordinary suggested destination/current project basename. Explicit destination=fresh uses its provided basename through that same native intent; explicit current requires an owned directory and no name/path. Delegated routine saving accepts the original OK through the app without asking for repeat write permission or a human chooser step. Existing unrelated destinations are refused before a write; preserve explicit basenames rather than silently renaming them. For current saving both modes call the same ordinary Session Save; Show actions gives a visual-only cue at Save without dispatching a click or opening a form. saved/committed and active retain the actual ordinary result/owner facts. For successful ordinary saved=true and active=true with no failure or uncertainty, say 'Project saved.' Do not add unrequested UI-completion or reopen caveats for presentation_complete=false or reopened=false. Report genuine failure, uncertainty, owner change and explicitly requested verification truthfully. Fresh Save As retains the genuine format/OK controls and ordinary Session save implementation. Manual Save As keeps its original destination picker. Actual saved path/copy/owner/commit facts remain authoritative. No unrelated overwrite or model path authority. An already-unmodified disabled Save button does not refuse the ordinary current Save call. Current Save creates no separate assistant export/recovery tree. Save may round/adopt/recalculate: inspect its current values/residuals. An old run_fit statistic remains pre-Save unless an offered metric explicitly belongs to the saved model; parameter reads, calculation-current/no-error flags or unquantified residual inspection do not verify chi-square/Rwp.",
        {{"destination", Object{{"type","string"},{"enum",Array{"fresh","current"}},{"description","Omit to save an already-owned Session directory, ignoring any unused fresh name; without one, omission uses fresh Save As. fresh explicitly requests Save As. current requires an owned directory and forbids name/path."}}},
         {"name", Object{{"type","string"},{"minLength",1},{"maxLength",static_cast<int>(edi::assistant::SelectedFileLimits::name_bytes)},
            {"description","Suggested fresh project directory basename for the one-operation original Save As chooser; spaces and Unicode are supported within the shared 512 UTF-8-byte Save As limit. No separators, dot components, NUL, trailing dot/space or existing destination. A chat path never grants access. Required only when a fresh destination is used; ignored for omitted destination with an owned directory, and forbidden for explicit current."}}}}, {});
    tools.append(Object{{"type","function"},{"name","edit_relation"},
        {"description","Edit ONE explicitly identified existing alias or constraint through its original app setter/remove, using actual current IDs and offered parameter paths. Rename returns the actual resulting ID. Existing relations/composition remain authoritative; validation may refuse a rename/removal referenced by enabled constraints. No automatic repair or expression rewriting. Equal stored values skip setter/cue/Undo. Both modes use the same ordinary method and recorded Undo; Show actions uses original Analysis Extra navigation/reveal and the actual offered target choice when needed; its prearmed ordinary action commits exactly once. Preserve actual applied/published/partial/currentness facts and never replay uncertain edits. action_error=control_unavailable with action_field=relation reports UI reachability, not expression invalidity or successful constraint activation. The common original-owner/partial/uncertain control contract applies. Does not append or infer ownership from default names."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"oneOf":[{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["alias_rename"]},"value":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."}},"required":["purpose","id","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["alias_target"]},"value":{"type":"string","minLength":1,"maxLength":256,"description":"Copy the exact current parameters[].path returned by inspect_project or list_parameters. Do not use parameters[].unique_name or substitute a dataset/structure ID. Single-owner paths use experiment. or structure.; multiple owners use the actual offered experiments[ID]. or structures[ID]. path. Copy the returned string rather than constructing it."}},"required":["purpose","id","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["alias_remove"]}},"required":["purpose","id","operation"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["constraint_rename"]},"value":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."}},"required":["purpose","id","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["constraint_expression"]},"value":{"type":"string","description":"Literal original single-line expression; empty is admitted only if the shared validator accepts it for the current row. Preserve actual Unicode/syntax/target and shared scientific validation; no parser or work-byte quota in the app."}},"required":["purpose","id","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["constraint_enabled"]},"value":{"type":"boolean"}},"required":["purpose","id","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["constraint_remove"]}},"required":["purpose","id","operation"],"additionalProperties":false}]})schema")).object()}});
    add("add_relations", "Append explicit affine alias/constraint declarations to the displayed project. Normal mode validates one atomic batch with one Undo; Show actions reveals the original relation controls and physically selects the actual offered alias target through its original popup when needed. That prearmed ordinary action commits once; other text/scalar stages retain their original ordinary methods, receipts/readback and Undo. No second setter or Return commit follows a physical choice. Visible interruption may leave actual partial edits, reported with complete/atomic/steps_completed facts. action_error=control_unavailable with action_field=relation reports UI reachability, not expression invalidity or successful constraint activation. The common original-owner/partial/uncertain control contract applies. Existing relations/composition are preserved; this is not a trial or fit. Complete supplied constraints use the current ordinary append model and shared validation once, retaining exact requested enabled state, actual row receipts and ordinary Undo. The manual editor is unchanged; no Draft or Confirm surface is required.",
        {{"aliases", Object{{"type", "array"},
            {"items", object({{"id", text}, {"path", parameterPath}}, {"id", "path"})}}},
         {"constraints", Object{{"type", "array"},
            {"items", object({{"id", text}, {"expression", Object{{"type", "string"}, {"minLength", 1}}},
                {"enabled", Object{{"type", "boolean"}}}}, {"id", "expression", "enabled"})}}}}, {"aliases", "constraints"});
    {
        auto tool=tools.last().toObject();auto schema=tool.value("inputSchema").toObject();
        schema["anyOf"]=Array{Object{{"properties",Object{{"aliases",Object{{"minItems",1}}}}}},
                              Object{{"properties",Object{{"constraints",Object{{"minItems",1}}}}}}};
        tool["inputSchema"]=schema;tools.last()=tool;
    }
    add("estimate_background", "Estimate the CURRENT selected measured powder experiment background through the ordinary app Estimate method, using its saved mode, type and estimation settings. Both modes call that same native method once; Show actions reveals the existing Background Estimate control and gives a visual-only cue. A successful manual line-segment Estimate then performs the original Id from position action, with a genuine control cue/click in Show actions. These are separate ordinary Undo steps: naming failure returns the actual estimated partial prefix. Inspect the current mode/terms/anchors and actual position-derived IDs afterward before addressing points. Explicit user manual anchors remain exact; do not overwrite them without that request. This is a native estimate, not a fit or a guessed anchor recipe.",{{"experiment",text}},{"experiment"});
    add("edit_background", "Add, update or remove one explicit measured line-segment background anchor, or explicitly name all current anchors from their positions in the CURRENT selected experiment, through the shared background editor. Normal mode has one atomic Undo; Show actions has ordinary per-control Undo and factual complete/partial steps. Position uses native measured axis units (CW two-theta degrees or TOF microseconds). Add/update require position, intensity and free; add may omit id to retain the ordinary app Add identity, while an explicit custom id is honored. Update/remove require the actual existing id. Successful non-remove point edits return the actual background_id. Remove must omit position/intensity/free. For name_from_positions supply only purpose, experiment and operation: it invokes the original whole-table Ids from positions action once, with ordinary Undo. Use explicit manual anchors only when requested; preserve their supplied values and free flags. Otherwise use native Estimate with current saved settings and follow its actual mode/eligibility. Explicit incoming IDs/values/free and immediate user scope remain exact in their own call; naming is never inferred from later calls. Show actions uses original Add/position/explicit-ID/Remove and Ids controls; intensity and Analysis free controls give visual-only cues followed by their ordinary app parameter setters. It does not use a setup form or atomic sequence promise.",
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
    // Common optional presentation metadata, for both original root schemas
    // and their owned oneOf alternatives; scientific fields stay required.
    const auto optionalPurpose=[](Object schema) {
        if(schema.value("required").isArray()) {
            Array fields;
            for(const auto& field:schema.value("required").toArray())if(field!="purpose")fields.append(field);
            schema["required"]=fields;
        }
        return schema;
    };
    for(qsizetype i=0;i<tools.size();++i) {
        auto spec=tools[i].toObject();auto schema=optionalPurpose(spec.value("inputSchema").toObject());
        if(schema.value("oneOf").isArray()) {
            Array branches;
            for(const auto& branch:schema.value("oneOf").toArray())branches.append(optionalPurpose(branch.toObject()));
            schema["oneOf"]=branches;
        }
        spec["inputSchema"]=schema;tools[i]=spec;
    }
    return tools;
}
} // namespace
QJsonArray assistant_native_tool_names() {
    return {"create_project","show_report","inspect_project","inspect_data","list_parameters","diagnostics","set_parameters","set_free","run_fit","undo_fit",
        "load_structure","create_experiment","set_experiment_type","load_data",
        "read_selected_file","create_structure","edit_structure","edit_atom","edit_experiment",
        "acquire_inputs","save_project","add_relations","edit_relation","edit_background","estimate_background"};
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
            const quint64 copies=1; // Only the original edit_experiment profile enum is advertised.
            const auto commas=first?0u:copies;
            if(bytes>(Limits::context_bytes-encoded)/copies || commas>Limits::context_bytes-encoded-copies*bytes)
                throw std::length_error("Native catalogue exceeds capacity");
            encoded+=copies*bytes+commas;first=false;
            // QString conversion and the independent Qt JSON string can overlap.
            // Valid UTF-8 has no more UTF-16 units than input bytes. Admit both
            // before either allocation, plus its enum entry and encoded role.
            if(token.size()>Limits::stream_retained_bytes/(2*sizeof(QChar)))
                throw std::length_error("Native catalogue exceeds capacity");
            charge(copies*2*token.size()*sizeof(QChar));charge(copies*sizeof(QJsonValue));
        });
    // The original pinned SDK creates its finite owning option vectors before
    // Qt conversion; reserve every such scratch owner plus both modes' Qt enums.
    charge(edi::absorption_options_preparation_bytes+2*sizeof(Array)+2*sizeof(Object));
    constexpr quint64 n=2*edi::absorption_option_count_bound;
    constexpr quint64 token=edi::absorption_option_bytes_bound;
    charge(n*(2*sizeof(QString)+sizeof(QJsonValue)+2*token*sizeof(QChar)));
    constexpr quint64 escaped=n*(6*token+3);
    if(escaped>Limits::context_bytes-encoded)throw std::length_error("Native catalogue exceeds capacity");
    encoded+=escaped;
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
    return name=="show_report" || name=="create_project" || individual_app_action(name) || name == "read_selected_file" || name == "acquire_inputs" || name == "inspect_project" || name == "inspect_data" || name == "list_parameters" || name == "diagnostics" ||
        name == "set_parameters" || name == "set_free" || name == "run_fit" || name == "undo_fit" || name == "create_cwl_project" || name == "add_relations" || name == "edit_relation" || name == "save_project" || name == "edit_background" || name == "estimate_background";
}
namespace {
struct NativeActionText { const char* name; const char* label; const char* description; };
constexpr NativeActionText nativeActionTexts[] = {
    {"create_project",QT_TRANSLATE_NOOP("AssistantActions","Create a project"),QT_TRANSLATE_NOOP("AssistantActions","Set up a new project with its name, title and description using the normal creation form.")},
    {"show_report",QT_TRANSLATE_NOOP("AssistantActions","Show the project report"),QT_TRANSLATE_NOOP("AssistantActions","Open the current project report in the app.")},
    {"inspect_project",QT_TRANSLATE_NOOP("AssistantActions","Inspect the current project"),QT_TRANSLATE_NOOP("AssistantActions","Read the current structures, experiments and model state to decide the next useful action.")},
    {"inspect_data",QT_TRANSLATE_NOOP("AssistantActions","Inspect diffraction data"),QT_TRANSLATE_NOOP("AssistantActions","Read the requested measured and calculated diffraction rows to assess the current model.")},
    {"list_parameters",QT_TRANSLATE_NOOP("AssistantActions","Inspect model parameters"),QT_TRANSLATE_NOOP("AssistantActions","Read current parameter values, uncertainties and refinement eligibility.")},
    {"diagnostics",QT_TRANSLATE_NOOP("AssistantActions","Check the current model"),QT_TRANSLATE_NOOP("AssistantActions","Read the app's current model and calculation diagnostics.")},
    {"set_parameters",QT_TRANSLATE_NOOP("AssistantActions","Update parameter values"),QT_TRANSLATE_NOOP("AssistantActions","Enter the requested values in the current model through the app's parameter editors.")},
    {"set_free",QT_TRANSLATE_NOOP("AssistantActions","Choose parameters to refine"),QT_TRANSLATE_NOOP("AssistantActions","Change the requested parameters' free flags for refinement, preserving all flags not included in this action.")},
    {"run_fit",QT_TRANSLATE_NOOP("AssistantActions","Refine the current model"),QT_TRANSLATE_NOOP("AssistantActions","Fit the selected free parameters to the measured data and inspect the resulting model.")},
    {"undo_fit",QT_TRANSLATE_NOOP("AssistantActions","Undo the latest refinement"),QT_TRANSLATE_NOOP("AssistantActions","Restore the model state retained by the latest available refinement Undo.")},
    {"load_structure",QT_TRANSLATE_NOOP("AssistantActions","Load a structure"),QT_TRANSLATE_NOOP("AssistantActions","Import the selected structure file into the current project using the normal structure loader.")},
    {"create_experiment",QT_TRANSLATE_NOOP("AssistantActions","Add an experiment"),QT_TRANSLATE_NOOP("AssistantActions","Add an experiment to the current project using the app's experiment controls.")},
    {"set_experiment_type",QT_TRANSLATE_NOOP("AssistantActions","Choose the experiment type"),QT_TRANSLATE_NOOP("AssistantActions","Select the experiment's sample form, measurement mode or radiation using the available native options.")},
    {"load_data",QT_TRANSLATE_NOOP("AssistantActions","Load diffraction data"),QT_TRANSLATE_NOOP("AssistantActions","Load the selected measurements into the requested current experiment.")},
    {"read_selected_file",QT_TRANSLATE_NOOP("AssistantActions","Read an attached file"),QT_TRANSLATE_NOOP("AssistantActions","Read the admitted attached file to understand its contents before using it.")},
    {"create_structure",QT_TRANSLATE_NOOP("AssistantActions","Create a structure"),QT_TRANSLATE_NOOP("AssistantActions","Create the ordinary initial structure and atom; enter target cell values and atomic-site information with the subsequent editing actions.")},
    {"edit_structure",QT_TRANSLATE_NOOP("AssistantActions","Edit the structure"),QT_TRANSLATE_NOOP("AssistantActions","Change the requested structure information through the app's ordinary editors.")},
    {"edit_atom",QT_TRANSLATE_NOOP("AssistantActions","Edit an atomic site"),QT_TRANSLATE_NOOP("AssistantActions","Change the requested atomic-site information while retaining the model's scientific constraints.")},
    {"edit_experiment",QT_TRANSLATE_NOOP("AssistantActions","Edit the experiment"),QT_TRANSLATE_NOOP("AssistantActions","Change the requested experiment setting using its current available options.")},
    {"acquire_inputs",QT_TRANSLATE_NOOP("AssistantActions","Inspect input files"),QT_TRANSLATE_NOOP("AssistantActions","Discover or admit the requested input files within the selected input scope.")},
    {"save_project",QT_TRANSLATE_NOOP("AssistantActions","Save the project"),QT_TRANSLATE_NOOP("AssistantActions","Save the current project through the app's normal save operation and report its actual outcome.")},
    {"add_relations",QT_TRANSLATE_NOOP("AssistantActions","Add parameter relationships"),QT_TRANSLATE_NOOP("AssistantActions","Add the requested aliases or mathematical constraints between current model parameters.")},
    {"edit_relation",QT_TRANSLATE_NOOP("AssistantActions","Edit a parameter relationship"),QT_TRANSLATE_NOOP("AssistantActions","Update the requested existing parameter relationship through the normal controls.")},
    {"edit_background",QT_TRANSLATE_NOOP("AssistantActions","Edit the background"),QT_TRANSLATE_NOOP("AssistantActions","Change the requested background model entries through the app's current background controls.")},
    {"estimate_background",QT_TRANSLATE_NOOP("AssistantActions","Estimate the background"),QT_TRANSLATE_NOOP("AssistantActions","Estimate the experiment background using its current native method and saved settings.")},
    {"create_cwl_project",QT_TRANSLATE_NOOP("AssistantActions","Prepare a diffraction project"),QT_TRANSLATE_NOOP("AssistantActions","Prepare the supplied diffraction project through the supported project-setup operation.")},
};
QString native_action_text(const QString& action,bool full) {
    for(const auto& text:nativeActionTexts)if(action==QLatin1StringView(text.name))
        return QCoreApplication::translate("AssistantActions",full?text.description:text.label);
    return full ? QCoreApplication::translate("AssistantActions","Carry out the requested work using the app's supported project actions.")
                : QCoreApplication::translate("AssistantActions","Work on the current project");
}
} // namespace
QString assistant_native_description(const QString& action,const QString& code) {
    if(code=="project_required")return QCoreApplication::translate("AssistantActions","This action needs an open project. Create or open a project before trying it.");
    return native_action_text(action,true);
}
QString assistant_native_purpose(const Object& args,const QString& action) {
    if(!args.contains("purpose"))return native_action_text(action,false);
    const auto value = args.value("purpose");
    if (!value.isString()) throw std::invalid_argument("Native action requires its purpose");
    const auto text = value.toString();
    if (text.trimmed().isEmpty())
        throw std::invalid_argument("Native action requires a nonempty purpose");
    for (const auto c : text) if (c.unicode() < 32 || c.unicode() == 127)
        throw std::invalid_argument("Native action purpose contains control characters");
    return text;
}
void assistant_native_arguments(const QString& name, const Object& args) {
    (void)assistant_native_purpose(args);
    if(name=="show_report"){shape(args,{"purpose"});return;}
    if(name=="diagnostics") {
        QSet<QString> fields{"purpose"};if(args.contains("developer_feedback"))fields.insert("developer_feedback");shape(args,fields);
        if(args.contains("developer_feedback")) {
            const auto feedback=args.value("developer_feedback");quint64 encoded=0;
            if(!feedback.isString() || feedback.toString().trimmed().isEmpty() || !codex_measured_size(feedback,encoded))
                throw std::invalid_argument("Diagnostic developer feedback must be nonempty valid text");
        }
        return;
    }
    if(name=="inspect_data") {
        QSet<QString> keys{"purpose","dataset_id","start","count"};if(args.contains("source"))keys.insert("source");shape(args,keys);
        if(!args.value("dataset_id").isString() || args.value("dataset_id").toString().isEmpty())
            edi::assistant::detail::refuse("invalid_argument","Numerical inspection requires an exact current dataset_id");
        for(const char* field:{"start","count"}) {
            const auto value=args.value(field);const auto n=value.toDouble(-1);
            const auto exact=std::ldexp(1.0,std::numeric_limits<double>::digits)-1;
            if(!value.isDouble() || !std::isfinite(n) || n<0 || n!=std::floor(n) || n>exact ||
               static_cast<long double>(n)>static_cast<long double>(std::numeric_limits<std::size_t>::max()))
                edi::assistant::detail::refuse("invalid_argument","Numerical inspection start and count must be exactly representable nonnegative native indices");
        }
        if(args.contains("source") && args.value("source")!="data" && args.value("source")!="bragg")
            edi::assistant::detail::refuse("invalid_argument","Numerical inspection source must be data or bragg");
        return;
    }
    if(name=="create_project") {
        QSet<QString> fields{"purpose"};if(args.contains("name"))fields.insert("name");if(args.contains("description"))fields.insert("description");if(args.contains("title"))fields.insert("title");shape(args,fields);
        if((args.contains("name") && (!args.value("name").isString() || args.value("name").toString().isEmpty())) ||
           (args.contains("description") && (!args.value("description").isString())) ||
           (args.contains("title") && (!args.value("title").isString())))
            throw ActionRefusal("unsupported_input","field");
        return;
    }
    if(name=="estimate_background") {
        shape(args,{"purpose","experiment"});
        if(!args.value("experiment").isString() || args.value("experiment").toString().isEmpty())
            throw ActionRefusal("target_unavailable","experiment");
        return;
    }
    if(individual_app_action(name)) {
        if((name=="load_structure" || name=="load_data") && (!args.value("file_id").isString() || args.value("file_id").toString().isEmpty()))
            throw ActionRefusal("input_required","file_id");
        if((name=="load_data" || name=="set_experiment_type") && (!args.value("experiment").isString() || args.value("experiment").toString().isEmpty()))
            throw ActionRefusal("target_unavailable","experiment");
    }
    if(name=="edit_relation") {
        const auto op=args.value("operation").toString();
        const bool remove=op=="alias_remove" || op=="constraint_remove";
        const bool enabled=op=="constraint_enabled";
        const bool expression=op=="constraint_expression";
        if(!remove && !enabled && !expression && op!="alias_rename" && op!="alias_target" && op!="constraint_rename")
            throw std::invalid_argument("Unsupported native relation operation");
        if(remove)shape(args,{"purpose","id","operation"});else shape(args,{"purpose","id","operation","value"});
        const auto text=[](const QJsonValue& value,std::optional<quint64> cap,bool empty) {
            if(!value.isString())throw std::invalid_argument("Native relation text is unavailable");
            const auto s=value.toString();
            if((!empty && s.isEmpty()) || (cap && static_cast<quint64>(s.size())>*cap) ||
                std::any_of(s.cbegin(),s.cend(),[](QChar c){return c.unicode()<32 || c.unicode()==127;}))
                throw std::invalid_argument("Native relation text is unavailable");
            quint64 encoded=0,bytes=0;
            if(!codex_measured_size(value,encoded))throw std::invalid_argument("Native relation Unicode is unavailable");
            for(qsizetype at=0;at<s.size();++at) {
                const auto c=s[at].unicode();
                bytes+=c<0x80?1:c<0x800?2:QChar::isHighSurrogate(c)?(++at,4):3;
                if(cap && bytes>*cap)throw std::invalid_argument("Native relation text is unavailable");
            }
        };
        text(args.value("id"),edi::assistant::Limits::id_bytes,false);
        if(enabled) {if(!args.value("value").isBool())throw std::invalid_argument("Native relation flag must be boolean");}
        else if(!remove)text(args.value("value"),expression?std::optional<quint64>{}:std::optional<quint64>{edi::assistant::Limits::id_bytes},expression);
        return;
    }
    if(name=="edit_experiment") {
        const auto id_ok=[](const QJsonValue& value) {
            return value.isString() && !value.toString().isEmpty() && !value.toString().contains(QChar(0)) &&
                value.toString().toUtf8().size()<=edi::assistant::Limits::id_bytes;
        };
        if(!id_ok(args.value("experiment")))throw ActionRefusal("target_unavailable","experiment");
        const auto op=args.value("operation").toString();
        if(op=="select")shape(args,{"purpose","experiment","operation"});
        else if(op=="peak_profile" || op=="absorption_type" || op=="extinction_type" || op=="mosaic_distribution") {
            shape(args,{"purpose","experiment","operation","value"});
            if(!args.value("value").isString())throw ActionRefusal("unsupported_type","value");
        } else if(op=="cutoff_fwhm" || op=="dataset_weight") {
            shape(args,{"purpose","experiment","operation","value"});
            if(!args.value("value").isDouble() || !std::isfinite(args.value("value").toDouble()))throw ActionRefusal("invalid_range","value");
        } else if(op=="phase_append")shape(args,{"purpose","experiment","operation"});
        else if(op=="phase_retarget" || op=="phase_enabled" || op=="phase_remove") {
            if(op=="phase_remove")shape(args,{"purpose","experiment","operation","phase"});
            else shape(args,{"purpose","experiment","operation","phase","value"});
            if(!id_ok(args.value("phase")))throw ActionRefusal("target_unavailable","phase");
            if(op=="phase_retarget" && !id_ok(args.value("value")))throw ActionRefusal("target_unavailable","value");
            if(op=="phase_enabled" && !args.value("value").isBool())throw ActionRefusal("unsupported_input","value");
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
            if(name=="edit_structure" && args.value("operation")=="select")shape(args,{"purpose","structure","operation"});
            else if(name=="edit_structure")shape(args,{"purpose","structure","operation","value"});
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
    } else if (name == "create_cwl_project") {
        if(args.contains("mapped_structure")) {
            shape(args,{"purpose","mapped_structure","data_file_id","recipe"});
            if(!args.value("mapped_structure").isObject())throw RecipeRefusal(RecipeField::MappedStructure,RecipeReason::ObjectRequired);
        } else shape(args,{"purpose","cif_file_id","data_file_id","recipe"});
    }
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
                const auto ordinary=background_append_input(*experiment);
                input=background_input(QStringLiteral("add"),QString::fromStdString(ordinary.id),
                    args.value("position").toDouble(),args.value("intensity").toDouble(),args.value("free").toBool());
            }
            if(names && (experiment->background_type!="line-segment" || !experiment->data || experiment->calculation_only || experiment->background.empty()))
                throw std::invalid_argument("Position IDs require an existing measured line-segment background");
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
        if (!aliasValue.isArray() || !constraintValue.isArray() || (aliasValue.toArray().isEmpty() && constraintValue.toArray().isEmpty()))
            throw std::invalid_argument("Invalid native relation batch");
        std::vector<edi::assistant::detail::NativeAliasInput> aliases;
        std::vector<edi::assistant::detail::NativeConstraintInput> constraints;
        const auto text = [](const Object& row, const char* key, std::optional<quint64> limit) {
            const auto field = row.value(key);
            if (!field.isString() || !field.toString().isValidUtf16() || field.toString().isEmpty() || (limit && static_cast<quint64>(field.toString().size()) > *limit))
                throw std::invalid_argument("Invalid native relation text");
            const auto bytes = field.toString().toUtf8();
            if ((limit && static_cast<quint64>(bytes.size()) > *limit) || bytes.contains('\0')) throw std::invalid_argument("Invalid native relation text");
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
            constraints.push_back({text(row, "id", edi::assistant::Limits::id_bytes), text(row, "expression", std::nullopt), row.value("enabled").toBool()});
        }
        return edi::assistant::detail::prepare_relation_append(project, aliases, constraints);
    }
    if (name != "set_parameters" && name != "set_free") return {};
    const bool values = name == "set_parameters";
    const auto field = args.value(values ? "values" : "flags");
    if (!field.isArray() || field.toArray().isEmpty())
        throw std::invalid_argument("Native parameter batch must be a nonempty array");
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
