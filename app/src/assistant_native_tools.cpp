// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_native_tools.hpp"
#include "assistant_recipe_refusal.hpp"
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
#include <algorithm>
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
    Object parameterPath=text;parameterPath["description"]="Copy the exact current parameters[].path returned by inspect_project or list_parameters. Do not use parameters[].unique_name or substitute a dataset/structure ID. Single-owner paths use experiment. or structure.; multiple owners use the actual offered experiments[ID]. or structures[ID]. path. Copy the returned string rather than constructing it.";
    const Object purpose{{"type", "string"}, {"minLength", 1},
        {"description", "A concise purpose for this action, not a claim that it succeeded"}};
    const auto add = [&](const char* name, const char* description, Object properties = {}, Array required = {}) {
        properties["purpose"] = purpose; required.append("purpose");
        tools.append(Object{{"type", "function"}, {"name", name}, {"description", description}, {"inputSchema", object(properties, required)}});
    };
    add("create_project", "Create an ordinary empty project in the CURRENT Edi session, only when no project is open. Uses the normal app Create API and current new-project preferences, with no scientific recipe, import or fit. Like the ordinary Create form, saves immediately under its remembered parent or Documents on desktop; existing destinations refuse. Name, title and description are metadata; choose all three meaningfully from the genuine task without inventing authors. Supplied fields preserve their literal values. Omitted metadata uses normal defaults (default basename project). Continue with normal load_structure/create_experiment/load_data using the actual retained file IDs. Both modes use the same native Session owner; Show actions opens the genuine normal Create dialog, enters the requested fields and confirms its ordinary Create button. Never discover another app or ask the user to create it for you.",
        {{"name",Object{{"type","string"},{"minLength",2},{"maxLength",31},{"pattern","^[A-Za-z][A-Za-z0-9_.-]{1,30}$"},
            {"description","Original normal Name identifier: 2–31 ASCII characters, letter first, then letters/digits/underscore/hyphen/period; human-readable wording belongs in title. Preserve an explicit user Name without silent renaming."}}},{"title",Object{{"type","string"},{"maxLength",32767},{"pattern","^[^\\u0000\\r\\n\\t]*$"},{"description","Original single-line Title field: at most 32767 UTF-16 units, with no NUL, newline, carriage-return or tab. The live original field validates before either action mode; supplied text is never truncated."}}},{"description",Object{{"type","string"}}}});
    add("show_report", "Open the CURRENT project's ordinary enabled Report preview through the same current-window tab navigation as the app. Both modes use the same owner; Show actions adds the existing tab cue. This navigates only; it does not generate/export/save a report or discover another application.");
    add("inspect_project", "Inspect Edi's actual currently displayed project/context, including native_state.interface_groups in actual current category-model/tier order (category groups only; admitted is compatibility, not enabled-control authority), and native_state.calculations: exact dataset published error/stale and calculated-column count/availability. Idle or available stale points do not prove success or viewport visibility. No mutation.");
    add("list_parameters", "Read actual native parameter paths/values/free flags and dependence. No mutation.");
    add("diagnostics", "Read actual available native physical diagnostics plus original app native_state.calculations for each exact dataset: published error/stale and calculated-column count/availability. Published old errors and idle are not current success; calculated availability is not legend/series visibility. No mutation.");
    add("set_parameters", "Set independent parameter values after complete native validation. Numeric cell/site/occupancy/ADP setup uses original current Structure controls; instrument/profile/background/linked-scale setup uses original current Experiment controls where exposed. Choose setup operations from actual native dependencies, admitted scientific evidence and explicit user scope. Map FullProf occupancy before writes: qraw=OccFP*M/m and, only for established common phase c, chemical occupancy=qraw/c with already-mapped scale times c*c once; preserve partial/shared fractions. Use fresh native_state.interface_groups to locate current controls, without imposing a universal scientific sequence. Preserve explicit values-array order. Normal mode follows the last changed requested member page and is one atomic edit/Undo; Show actions navigates/cues original exposed controls in order then calls their ordinary app parameter setters, with no scientific key/click input; separate Undo per change and actual applied/published receipts determine honest complete/partial/uncertain outcomes." EDI_ASSISTANT_CONTROL_GUIDANCE,
        {{"values", Object{{"type", "array"}, {"minItems", 1},
            {"items", object({{"path", parameterPath}, {"value", Object{{"type", "number"}}}}, {"path", "value"})}}}}, {"values"});
    add("set_free", "Choose actual independent fittable parameter flags with physical/symmetry validation. For a delegated whole eligible category whose requested flags are uniform, send its complete actual current eligible membership in ONE set_free flags array so the native Free menu can prove exact membership; do not split that group into per-point calls. Preserve explicit subsets, supplied flags-array order and per-call scope; never add unrequested members, merge separate mutations or replay equal/partial/uncertain work. For delegated refinement choose identifiable supported groups and inspect actual outcomes as the evidence warrants; preserve fill-only scope and explicit flags. Plan related requested flags category by category; use the existing Free header only for exactly the whole eligible displayed category with one common flag, and actual row checkboxes for subsets. Never reorder an explicit flags array. Normal mode is one atomic edit/Undo; Show actions navigates/cues original exposed controls then uses ordinary app free setters; exact whole eligible uniform groups show/cue the existing Free menu and invoke its ordinary action, subsets use their actual checkbox cues and ordinary per-row methods. Separate Undo and actual applied/published receipts determine honest complete/partial/uncertain outcomes." EDI_ASSISTANT_CONTROL_GUIDANCE,
        {{"flags", Object{{"type", "array"}, {"minItems", 1},
            {"items", object({{"path", parameterPath}, {"free", Object{{"type", "boolean"}}}}, {"path", "free"})}}}}, {"flags"});
    add("undo_fit", "Undo exactly the most recent adopted single/joint fit through the ordinary current-project Undo method. Inspect the actual adopted undesired fit first and use only within authorized refinement. native_state.fit_undo_available is a factual semantic observation, rechecked at use; a later failed/preflight/preparation attempt, intervening edit or non-fit history refuses without undoing earlier good science. Show actions cues the actual enabled appbar Undo; normal mode calls the same ordinary method. An applied but unconfirmed reversal is spent once: inspect actual state rather than retry. No generic history Undo, refit, reset or Save is performed." EDI_ASSISTANT_CONTROL_GUIDANCE);
    add("run_fit", "Run the displayed Edi project's real single/joint native fit only when fitting is authorized and the actual native data/type/model prerequisites hold. Inspect current free flags after any failed prerequisite and await actual publication/outcome. For powder detailed profile or structural fitting, establish scaled peak-position agreement: for CW use the justified cell/two-theta correction with known wavelength fixed, or retain already verified calibration/alignment. Do not force freeing a known zero or dependent term; choose only supported identifiable groups. Peak-position mismatch can make a scale-only fit suppress the calculated pattern instead of finding the intended match. Do not enforce scale then lattice then zero as an unconditional sequence. Inspect alignment first; keep or recover a physically justified scale while selecting the supported identifiable cell/two-theta correction, retaining supplied known wavelength and valid calibration. Inspect each adopted stage and use eligible ordinary fit Undo for a harmful scale collapse; an unadopted refusal must not undo earlier science. Choose supported identifiable variables from current evidence and explicit scope. Inspect actual status/adopted/converged facts, comparable objective and physical validity; retain good outcomes without a mandatory group/pass count. A converged cell or scale fit alone does not establish peak alignment. Judge the physical profile across the actual measured domain rather than coefficient signs alone. Undo an unacceptable adopted candidate immediately before any further fit, including a calibration attempt, replaces the only fit-Undo opportunity. A missing checkpoint bank does not prohibit supported explicit numerical repair from physically valid values recorded from the same native project; distinguish that repair from full rollback and re-establish alignment with the repaired profile fixed. For an adopted undesired fit use offered undo_fit only while native_state.fit_undo_available is true, then inspect actual state/free flags; its ordinary Undo rechecks the most recent adopted attempt and latest fit history. Never undo earlier science after an unadopted refusal. If restoration is unavailable, report that limit rather than claim rollback or continue from a rejected state. Unknown/uncertain effects require inspection, not blind retry. For ordinary sample-cell refinement retain the supplied known wavelength fixed; genuine wavelength calibration needs its known cell/anchor and objective. Preserve explicit constraints and resolve conflicts, never silently override flags. This is a live fit, not an isolated accepted-best trial. A returned fit_reason=unanchored_cw_dilation identifies the actual engine guard's refusal of a free uniform wavelength/cell scale direction, not general singularity. Choose the objective-appropriate supported anchor described above; in joint/phase fitting it must anchor the actual effective unanchored group. Zero is not this scale anchor. Ask about genuine objective conflicts and do not automatically retry. Unknown errors do not imply this cause. For the current project's Report preview, use show_report to open its existing enabled Report page; the optional [Open Report page](edi:report) link also permits user navigation. Do not discover or select a desktop/CUA app by name for this navigation. The link does not generate or save a report." EDI_ASSISTANT_CONTROL_GUIDANCE);
    { // One offered operation; exactly one admitted Structure input alternative.
        const auto common=Object{{"purpose",purpose},{"data_file_id",text},{"recipe",native_cwl_recipe_schema(include_profiles)}};
        auto cif=common;cif["cif_file_id"]=text;
        auto mapped=common;mapped["mapped_structure"]=native_mapped_structure_schema();
        tools.append(Object{{"type","function"},{"name","create_cwl_project"},
            {"description","Prepare a complete single-phase powder CW neutron setup from a genuine selected CIF ID by default, or a scientifically mapped_structure when the user explicitly requests manual construction, plus genuine data_file_id and the original recipe. Do not demand a manually supplied Wyckoff letter: omitted fields retain the native assignment/default; preserve explicit source declarations. This is an optional complete-setup alternative; normal create_project, CIF/data import and native Estimate remain the default ordinary route. When this operation is chosen, BOTH inputs validate the final native candidate/initial overrides first, then use the SAME actual sidebar category order: complete Structure, each full site row before the next, all ADPs afterward, then Experiment groups. Map source occupancies/scales BEFORE supplying the target. Preserve explicit source/user values and the current accepted native state. For unspecified optional numerical starts, retain the actual native app defaults; inspect offered native values/options instead of importing online, tutorial, sample-specific or remembered experiment constants or inventing a starting offset/profile coefficient. If a complete recipe requires an explicit unsupplied default, use only an actual default established through offered native context/actions; otherwise use supported individual setup or report the missing default rather than invent one. Required measurement/calibration facts, including a required wavelength, must come from genuine admitted input, calibration or the user; an arbitrary factory placeholder is not such evidence. Later changes may follow this experiment's actual authorized refinement/calibration evidence; cite the actual observation/result and distinguish a proposed change from an observed or fitted fact. Do not overwrite a supplied or genuinely fitted value merely because it matches an example. Keep a supplied known wavelength anchored unless the authorized calibration has a supported independent anchor. Omit recipe.background for native Estimate with current saved settings. Explicit recipe.background is a direct array of exact manual position/intensity rows, fixed implicitly: omit free, id and any anchors wrapper. Standalone edit_background instead requires explicit free for add/update; preserve those flags and explicit scope. No new parser, generated CIF, fit, save, aliases/constraints or refinement-flag stage is implied. Required source relations/flags are explicit subsequent ordinary actions; setup completion alone is not complete source reconstruction. Only no project or the SAME scientifically empty current project is accepted; metadata/path/history are preserved. OFF uses one prepared atomic population/Undo. ON uses original app controls/receipts with factual partial outcomes and ordinary Undo, not atomic GUI replay. CIF uses original Load; mapped uses original Create and reuses its actual initial atom. Explicit standalone action arrays remain in caller order. recipe names/description apply only when no project is open. A mapped-input refusal returns code-owned refusal_guidance from this same schema description: inspect current state, correct the request and continue only within unchanged input/owner authority after a proved prewrite refusal; never replay partial or uncertain work." EDI_ASSISTANT_CONTROL_GUIDANCE},
            {"inputSchema",Object{{"oneOf",Array{
                object(cif,{"purpose","cif_file_id","data_file_id","recipe"}),
                object(mapped,{"purpose","mapped_structure","data_file_id","recipe"})}}}}});
    }
    // Public canonical schemas apply only to these four new native actions.
    tools.append(Object{{"type","function"},{"name","load_structure"},{"description","Append one structure to the current project from an admitted immutable file_id through the original Structure Load reader/Undo. Show actions gives only the original Load pointer/click cue, not a dispatched click or file dialog. Original source identity must remain current. No recreation, path grant, fit or save." EDI_ASSISTANT_CONTROL_GUIDANCE},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1},"file_id":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","file_id"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","create_experiment"},{"description","Append one original default calculation-only experiment, preserving the current project and structures. Return actual member/type/links; keep actual native defaults for unspecified optional numerical starts and configure only needed type choices before data. Required measurement/calibration facts must come from genuine admitted input/calibration or the user, never an arbitrary factory placeholder. Choose creation and setup order from actual native dependencies, admitted scientific evidence and explicit user scope; no universal Structure/Experiment page sequence is required." EDI_ASSISTANT_CONTROL_GUIDANCE},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1}},"required":["purpose"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","set_experiment_type"},{"description","Set one original enabled sample-form/beam/probe choice on the exact calculation-only experiment, returning its actual replaced member. Equal type is a no-op. Replacement can reset settings, reported factually." EDI_ASSISTANT_CONTROL_GUIDANCE},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"oneOf":[{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"experiment":{"type":"string","minLength":1,"maxLength":256},"axis":{"const":"beamMode"},"token":{"enum":["constant wavelength","time-of-flight"]}},"required":["purpose","experiment","axis","token"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"experiment":{"type":"string","minLength":1,"maxLength":256},"axis":{"const":"radiationProbe"},"token":{"enum":["neutron","xray"]}},"required":["purpose","experiment","axis","token"],"additionalProperties":false}]})schema")).object()}});
    { // The same original type selector also owns powder/single-crystal routing.
        auto tool=tools.last().toObject();auto schema=tool.value("inputSchema").toObject();auto branches=schema.value("oneOf").toArray();
        branches.append(object({{"purpose",purpose},{"experiment",text},{"axis",Object{{"const","sampleForm"}}},
            {"token",Object{{"enum",Array{QString::fromLatin1(edi::token(edi::SampleFormEnum::POWDER)),QString::fromLatin1(edi::token(edi::SampleFormEnum::SINGLE_CRYSTAL))}}}}},
            {"purpose","experiment","axis","token"}));
        schema["oneOf"]=branches;tool["inputSchema"]=schema;tools[tools.size()-1]=tool;
    }
    tools.append(Object{{"type","function"},{"name","load_data"},{"description","Load an admitted immutable measurement into the exact calculation-only experiment through original Load data/readers/Undo. Show actions gives only the original Load pointer/click cue without a file dialog; original source identity must remain current. Return actual renamed member/reader facts; inspect native pattern summaries after loading. Read only a needed measurement header beforehand, not every numeric observation as conversation text. Do not replace measured data or implicitly change type." EDI_ASSISTANT_CONTROL_GUIDANCE},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1},"experiment":{"type":"string","minLength":1,"maxLength":256},"file_id":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","experiment","file_id"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","read_selected_file"},{"description","Read exact strict UTF-8 text from ONE current admitted file_id, never a path. offset/max_bytes are byte positions, at most the existing 65536-byte read bound. Returns selected_text with original collection/generation, total_bytes, exact start/end/next_offset, eof and complete. complete means this range covers the entire source, not just a finished chunk. A final later chunk can have eof=true and complete=false. max_bytes=0 probes a valid scalar boundary; a positive range too small for the next scalar refuses. No silent truncation/normalization, raw filesystem reader, converter or scientific edit. Same read in both Show-actions modes; no project required. For measurements, read only a header or ranges needed for format/source questions, then use load_data and native inspection for the full numeric dataset instead of streaming every observation into the conversation. Full source reads remain available when actually needed or requested; manual structure mapping may need the complete small structure text. Use subsequent explicit ranges against the same returned identity for partial text; do not ask to paste the same readable attachment again."},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1},"file_id":{"type":"string","minLength":1,"maxLength":256},"offset":{"type":"integer","minimum":0,"maximum":16777216},"max_bytes":{"type":"integer","minimum":0,"maximum":65536}},"required":["purpose","file_id","offset","max_bytes"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","create_structure"},{"description","Create one structure through the original app Create method. It provides ONE actual initial atom, not the requested target structure. Return actual structure/sites. Reuse/update the actual initial atom for the first target instead of duplicating it. Choose supported cell/site/ADP operations from actual symmetry/type dependencies, scientific evidence and explicit scope; no universal row/page sequence is required. Rename with edit_structure, and use existing parameter tools for numeric/free values. No generated CIF or copied factory. Same ordinary method both modes; ON gives genuine control cues." EDI_ASSISTANT_CONTROL_GUIDANCE},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"type":"object","properties":{"purpose":{"type":"string","minLength":1}},"required":["purpose"],"additionalProperties":false})schema")).object()}});
    tools.append(Object{{"type","function"},{"name","edit_structure"},{"description","Edit ONE exact structure through its original ordinary setter, or explicitly select it with operation=select and no value. Select uses the ordinary current-index UI method, no scientific Edit/Undo/dirty; actual non-scan member IDs only. Both modes call the same method; ON gives original row reveal/visual-only cue. Confirm native_state.selected_structure_id, not a row index or decorated label; no-op selection skips navigation/cue. Scientific operations remain: rename, space_group_name, space_group_number or space_group_setting. HM/number/setting are linked; inspect actual returned fields before the next edit. Number 0 clears its stored explicit number; an unknown typed name/setting can be stored unresolved just like manual input, never a calculation-success claim. Preserve original default-setting behavior, science and Undo. Equal canonical state skips setter/cue/Undo. No numeric shadow fields; use existing parameter tools." EDI_ASSISTANT_CONTROL_GUIDANCE},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"oneOf":[{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"rename"},"value":{"type":"string","minLength":1,"maxLength":256}},"required":["purpose","structure","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"space_group_name"},"value":{"type":"string","maxLength":256}},"required":["purpose","structure","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"space_group_number"},"value":{"type":"integer","minimum":0,"maximum":230}},"required":["purpose","structure","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1},"structure":{"type":"string","minLength":1,"maxLength":256},"operation":{"const":"space_group_setting"},"value":{"type":"string","maxLength":256}},"required":["purpose","structure","operation","value"],"additionalProperties":false}]})schema")).object()}});
    { // Extend the original structure union without changing its scientific branches.
        auto tool=tools.last().toObject();auto schema=tool.value("inputSchema").toObject();auto branches=schema.value("oneOf").toArray();
        branches.append(object({{"purpose",purpose},{"structure",text},{"operation",Object{{"const","select"}}}},{"purpose","structure","operation"}));
        schema["oneOf"]=branches;tool["inputSchema"]=schema;tools[tools.size()-1]=tool;
    }
    tools.append(Object{{"type","function"},{"name","edit_atom"},{"description","Edit ONE atom in an exact current structure through original atom-row methods: append returns actual generated atom_id/defaults; text changes only label/typeSymbol/wyckoffLetter; remove explicitly targets atom_id; adp_type uses original Biso/Uiso/Bani/Uani/beta conversion. Reuse Create's actual initial atom and preserve supplied coordinates/mapped chemical occupancy, with a Wyckoff declaration only when explicitly supplied. Choose later site/ADP operations from actual native dependencies and scientific evidence; explicit immediate operations remain exact. Use actual confirmed returned IDs; a refused rename establishes no new ID, and partial/uncertain effects need inspection before dependent calls. Coordinates/occupancy/ADP numbers/free use existing parameter tools with actual paths. Compare stored values and skip equal setter/cue/Undo; preserve ordinary validation and partial facts. Same original methods both modes, no keyboard scientific writer or generated file." EDI_ASSISTANT_CONTROL_GUIDANCE},
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
        {"description","Choose supported setup/refinement actions from native type/data dependencies, scientific evidence and explicit scope. A profile family must exist before editing its coefficients; inspect reset settings and actual IDs. No universal Structure/Experiment/Analysis page sequence is required. Change ONE exact experiment through original app methods, or explicitly select it with operation=select and no value/region/index. Selection uses the ordinary current-index UI setter, no scientific Edit/Undo/dirty, and refuses scan file-selection semantics. Confirm native_state.selected_experiment_id; no-op selection skips navigation/cue. Both modes use the same setter, ON adds original row reveal/visual-only cue. absorption_type, extinction_type, mosaic_distribution, cutoff_fwhm and dataset_weight require the CURRENT selected experiment. Single-crystal extinction selectors use actual extinction_type_options and mosaic_distribution_options; distribution is available only when the current type owns it. Type changes retain ordinary native defaults/Undo; crystal_radius/domain_radius/mosaic_spread use ordinary parameter paths/units, not a separate scalar setter. Absorption uses actual absorption_type_options and original coefficient family/default rules; cutoff is literal FWHM-window setting (nonpositive retains original full-window semantics); dataset weight is stored in all modes and affects the joint objective, not single-dataset calculated curves. Absorption/cutoff controls are Experiment Extras; weight is Analysis Extras Joint fit. Other operations retain original peak-profile/exclusion routing. Profile value must be an original option for its beam mode; changing profiles can add/drop optional settings at original defaults. Exclusion append keeps the ordinary generated ID/default bounds; use its actual returned region ID for later start/end/remove calls. Bounds are literal dataset-axis units, never automatically sorted/clamped. Equal stored profile/bound values skip setters/cues/Undo. Both modes use the same ordinary method/validation/history; Show actions adds original navigation/reveal and visual-only cues. Inspect actual IDs/settings and partial applied/published facts; do not retry uncertain writes. Phase operations require this CURRENT selected experiment: phase_append uses the original first unlinked current structure and original scale=1/enabled=true defaults, never a placeholder; phase_retarget identifies the exact old phase and offered new structure ID, retains its scale and refuses disabled rows or duplicate keys; phase_enabled assigns the explicit bool, including false; phase_remove requires another stored row and returns the removed old ID. The phase key is datasets[].phases[].structure_id, not a row index. Successful results provide the actual phase_id and complete ordered datasets[0].phases; retarget changes the key for later calls. Equal admitted enabled/retarget values skip setters/cues/Undo. Ordinary shared Undo restores linked rows/scale states and related fit/relations; reacquire row/parameter handles after Undo. Existing initial links are real intended links, never overwrite them as placeholders. Scale already uses parameter actions; weight fraction is read-only. No parser/converter, implicit noncurrent selection for scalars/phases, auto cutoff or fit is implied." EDI_ASSISTANT_CONTROL_GUIDANCE},
        {"inputSchema",Object{{"oneOf",experiment_branches}}}});
    add("acquire_inputs", "Capture immutable local input files only from an opaque scope_id in the current genuine user input_scopes. No path, URL, glob or command argument is accepted. If the needed files are already in current selected_files.files, use those admitted file IDs directly for read_selected_file, load_structure or load_data; reacquisition is unnecessary merely to identify attachments. Use acquire_inputs for genuinely unadmitted current scopes or supported directory discovery, copying the exact offered input_scopes.sources.scope_id. Returns file IDs, source ordinal, reader hints and counts; it does not claim scientific import. Continue through the normal current-project import actions. Already captured sources are not reread. Stale, changed, protected or oversized sources refuse without replacing the prior selection.",
        {{"scope_id",text}},{"scope_id"});
    add("save_project", "Save the settled current project using the ordinary app Save method for its existing owned directory; fresh Save As retains its original verified export path. Omitted destination saves its genuine already-owned Session directory, preserving its actual name/path and ignoring an unused fresh name. If it has no owned directory, omission completes the original Save As intent using its selected/default Folder/ZIP/copy format and ordinary suggested destination/current project basename. Explicit destination=fresh uses its provided basename through that same native intent; explicit current requires an owned directory and no name/path. Delegated routine saving accepts the original OK through the app without asking for repeat write permission or a human chooser step. Existing unrelated destinations are refused before a write; preserve explicit basenames rather than silently renaming them. For current saving both modes call the same ordinary Session Save; Show actions gives a visual-only cue at Save without dispatching a click or opening a form. saved/committed and active retain the actual ordinary result/owner facts. For successful ordinary saved=true and active=true with no failure or uncertainty, say 'Project saved.' Do not add unrequested UI-completion or reopen caveats for presentation_complete=false or reopened=false. Report genuine failure, uncertainty, owner change and explicitly requested verification truthfully. Fresh Save As retains the genuine format/OK controls and ordinary Session save implementation. Manual Save As keeps its original destination picker. Actual saved path/copy/owner/commit facts remain authoritative. Before quoting final fitted numbers after save, inspect authoritative current parameter values/uncertainties through offered native inspection and compare the relevant accepted pre-save state. Disclose material rounding or an undetermined parameter only when actually observed; if readback is unavailable, qualify the scientific numbers instead of inventing verification. This does not invalidate a successful ordinary Save or require a reopen, repeated save or a warning solely for presentation/reopen flags. No unrelated overwrite or model path authority." EDI_ASSISTANT_CONTROL_GUIDANCE,
        {{"destination", Object{{"type","string"},{"enum",Array{"fresh","current"}},{"description","Omit to save an already-owned Session directory, ignoring any unused fresh name; without one, omission uses fresh Save As. fresh explicitly requests Save As. current requires an owned directory and forbids name/path."}}},
         {"name", Object{{"type","string"},{"minLength",1},{"maxLength",static_cast<int>(edi::assistant::SelectedFileLimits::name_bytes)},
            {"description","Suggested fresh project directory basename for the one-operation original Save As chooser; spaces and Unicode are supported within the shared 512 UTF-8-byte Save As limit. No separators, dot components, NUL, trailing dot/space or existing destination. A chat path never grants access. Required only when a fresh destination is used; ignored for omitted destination with an owned directory, and forbidden for explicit current."}}}}, {});
    tools.append(Object{{"type","function"},{"name","edit_relation"},
        {"description","Edit ONE explicitly identified existing alias or constraint through its original app setter/remove, using actual current IDs and offered parameter paths. Rename returns the actual resulting ID. Existing relations/composition remain authoritative; validation may refuse a rename/removal referenced by enabled constraints. No automatic repair or expression rewriting. Equal stored values skip setter/cue/Undo. Both modes use the same ordinary method and recorded Undo; Show actions adds original Analysis Extra navigation/reveal/cue only. Preserve actual applied/published/partial/currentness facts and never replay uncertain edits. For action_error=control_unavailable with action_field=relation, the original visible relation control could not be reached; this does not establish an invalid expression or successful constraint activation. Inspect actual current relations and completed steps, retain the real partial prefix, and report the visible-control limit. Continue only from freshly confirmed state and unchanged authority after the actual control is accessible; never replay partial/uncertain edits, switch modes or bypass the original control/receipt/Undo path to force success. Does not append or infer ownership from default names." EDI_ASSISTANT_CONTROL_GUIDANCE},
        {"inputSchema",QJsonDocument::fromJson(QByteArrayLiteral(R"schema({"oneOf":[{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["alias_rename"]},"value":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."}},"required":["purpose","id","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["alias_target"]},"value":{"type":"string","minLength":1,"maxLength":256,"description":"Copy the exact current parameters[].path returned by inspect_project or list_parameters. Do not use parameters[].unique_name or substitute a dataset/structure ID. Single-owner paths use experiment. or structure.; multiple owners use the actual offered experiments[ID]. or structures[ID]. path. Copy the returned string rather than constructing it."}},"required":["purpose","id","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["alias_remove"]}},"required":["purpose","id","operation"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["constraint_rename"]},"value":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."}},"required":["purpose","id","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["constraint_expression"]},"value":{"type":"string","description":"Literal original single-line expression; empty is admitted only if the shared validator accepts it for the current row. Preserve actual Unicode/syntax/target and shared scientific validation; no parser or work-byte quota in the app."}},"required":["purpose","id","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["constraint_enabled"]},"value":{"type":"boolean"}},"required":["purpose","id","operation","value"],"additionalProperties":false},{"type":"object","properties":{"purpose":{"type":"string","minLength":1,"description":"Concise goal, not success. Plain text without control characters; no work quota."},"id":{"type":"string","minLength":1,"maxLength":256,"description":"Exact current ID or offered parameter path; strict Unicode, no NUL, at most existing 256 UTF-8 bytes."},"operation":{"type":"string","enum":["constraint_remove"]}},"required":["purpose","id","operation"],"additionalProperties":false}]})schema")).object()}});
    add("add_relations", "Append explicit affine alias/constraint declarations to the displayed project. Normal mode validates one atomic batch with one Undo; Show actions reveals and visually cues the original relation controls, then calls their same ordinary app model methods once with actual receipt/readback and ordinary Undo; no scientific keyboard or toggle/choice input is dispatched. Visible interruption may leave actual partial edits, reported with complete/atomic/steps_completed facts. For action_error=control_unavailable with action_field=relation, the original visible relation control could not be reached; this does not establish an invalid expression or successful constraint activation. Inspect actual current relations and completed steps, retain the real partial prefix, and report the visible-control limit. Continue only from freshly confirmed state and unchanged authority after the actual control is accessible; never replay partial/uncertain edits, switch modes or bypass the original control/receipt/Undo path to force success. Existing relations/composition are preserved; this is not a trial or fit. Complete supplied constraints use the current ordinary append model and shared validation once, retaining exact requested enabled state, actual row receipts and ordinary Undo. The manual editor is unchanged; no Draft or Confirm surface is required." EDI_ASSISTANT_CONTROL_GUIDANCE,
        {{"aliases", Object{{"type", "array"},
            {"items", object({{"id", text}, {"path", parameterPath}}, {"id", "path"})}}},
         {"constraints", Object{{"type", "array"}, {"minItems", 1},
            {"items", object({{"id", text}, {"expression", Object{{"type", "string"}, {"minLength", 1}}},
                {"enabled", Object{{"type", "boolean"}}}}, {"id", "expression", "enabled"})}}}}, {"aliases", "constraints"});
    add("estimate_background", "Estimate the CURRENT selected measured powder experiment background through the ordinary app Estimate method, using its saved mode, type and estimation settings. Both modes call that same native method once; Show actions reveals the existing Background Estimate control and gives a visual-only cue. Inspect the current mode/terms/anchors and eligibility afterward. Explicit user manual anchors remain exact; do not overwrite them without that request. This is a native estimate, not a fit or a guessed anchor recipe.",{{"experiment",text}},{"experiment"});
    add("edit_background", "Add, update or remove one explicit measured line-segment background anchor, or explicitly name all current anchors from their positions in the CURRENT selected experiment, through the shared background editor. Normal mode has one atomic Undo; Show actions has ordinary per-control Undo and factual complete/partial steps. Position uses native measured axis units (CW two-theta degrees or TOF microseconds). These standalone add/update calls require position, intensity and free; compound create_cwl_project.recipe.background instead uses exact position/intensity rows fixed implicitly, without free or an anchors wrapper. Add/update require position, intensity and free; add may omit id to retain the ordinary app Add identity, while an explicit custom id is honored. Update/remove require the actual existing id. Successful non-remove point edits return the actual background_id. Remove must omit position/intensity/free. For name_from_positions supply only purpose, experiment and operation: it invokes the original whole-table Ids from positions action once, with ordinary Undo. Use explicit manual anchors only when requested; preserve their supplied values and free flags. Otherwise use native Estimate with current saved settings and follow its actual mode/eligibility. Explicit incoming IDs/values/free and immediate user scope remain exact in their own call; naming is never inferred from later calls. Show actions uses original Add/position/explicit-ID/Remove and Ids controls; intensity and Analysis free controls give visual-only cues followed by their ordinary app parameter setters. It does not use a setup form or atomic sequence promise." EDI_ASSISTANT_CONTROL_GUIDANCE,
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
    return {"create_project","show_report","inspect_project","list_parameters","diagnostics","set_parameters","set_free","run_fit","undo_fit",
        "create_cwl_project","load_structure","create_experiment","set_experiment_type","load_data",
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
            const quint64 copies=mode==edi::BeamModeEnum::CONSTANT_WAVELENGTH?3:1;
            // Both closed creation alternatives carry the recipe enum; the
            // original edit_experiment enum is its third CW wire/owner role.
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
    return name=="show_report" || name=="create_project" || individual_app_action(name) || name == "read_selected_file" || name == "acquire_inputs" || name == "inspect_project" || name == "list_parameters" || name == "diagnostics" ||
        name == "set_parameters" || name == "set_free" || name == "run_fit" || name == "undo_fit" || name == "create_cwl_project" || name == "add_relations" || name == "edit_relation" || name == "save_project" || name == "edit_background" || name == "estimate_background";
}
QString assistant_native_purpose(const Object& args) {
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
        if (!aliasValue.isArray() || !constraintValue.isArray() || constraintValue.toArray().isEmpty())
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
