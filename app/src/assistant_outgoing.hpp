// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "codex_agent.hpp"
#include "assistant_recipe_refusal.hpp"
#include "assistant_action_refusal.hpp"
#include "assistant_selected_text.hpp"
#include <QJsonArray>
#include <QJsonObject>
#include <QStringView>
#include <iterator>
#include <array>
#include <string_view>
#include <string>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace edi_app::outgoing {
// Closed roles over already-owned native data. Never recursively copy an
// unknown object or string, and never encode the unprojected native result.
enum class Role { Context, Project, Structure, SpaceGroup, Site, Dataset, Axis,
    Observations, Region, Phase, Background, Anchor, BackgroundTerm, BackgroundEstimate, Relations, Alias, Constraint,
    Parameter, Diagnostic, Selection, File, Skill, InputScopes, InputSource,
    NativeState, Calculation, InterfaceGroup, Result, Fit, ReaderFacts, SelectedText, DataInspection, DataColumn, DataRow, DataPhase };
inline constexpr std::string_view wire_schema="edi.assistant.outgoing/1";
inline constexpr std::string_view unanchored_cw_dilation="unanchored_cw_dilation";
// One fixed field: JSON punctuation/token and the existing encoding walk's
// two QJsonValue owners plus UTF-16 key/value storage; no synthetic payload.
inline constexpr quint64 fit_reason_json_bytes=sizeof(R"(,"fit_reason":"")")-1+unanchored_cw_dilation.size();
inline constexpr quint64 fit_reason_owned_bytes=2*sizeof(QJsonValue)+
    (sizeof("fit_reason")-1+unanchored_cw_dilation.size())*sizeof(QChar);
inline constexpr quint64 recipe_guidance_json_bytes=sizeof(R"(,"refusal_guidance":"")")-1+mapped_structure_guidance.size();
inline constexpr quint64 recipe_guidance_owned_bytes=2*sizeof(QJsonValue)+
    (sizeof("refusal_guidance")-1+mapped_structure_guidance.size())*sizeof(QChar);
template<std::size_t N> inline constexpr quint64 longest_action_literal(const std::array<const char*,N>& names) {
    quint64 longest=0;for(const auto* name:names){const auto size=std::char_traits<char>::length(name);if(size>longest)longest=size;}return longest;
}
inline constexpr quint64 control_pair_json_bytes=sizeof(R"(,"action_error":"","action_field":"")")-1+
    longest_action_literal(action_errors)+longest_action_literal(action_fields);
inline constexpr quint64 control_pair_owned_bytes=4*sizeof(QJsonValue)+
    (sizeof("action_error")-1+sizeof("action_field")-1+longest_action_literal(action_errors)+longest_action_literal(action_fields))*sizeof(QChar);
inline constexpr quint64 control_pair_role=control_pair_json_bytes>control_pair_owned_bytes?control_pair_json_bytes:control_pair_owned_bytes;
enum class ResultCode { Refused, Unavailable, Cancelled, Uncertain, ResourceExhausted, InputChanged, PolicyMismatch, RequestStale, ContextUnready, OwnerUnavailable, PendingOperation, ItemMismatch, DuplicateCall, InvalidArguments, CalculationBusy, VisibleUnmapped, ProjectRequired, Unclassified, OwnerRetired, RetentionBlocked, AttachmentsClearing, PublicationPaused, AccountUnready, OwnerRetiring, ConsentRevoked, HistoryUnretained, AgentInterrupted, ContextPending, HistoryClearing, QuestionPending, SelectionPending, InputStaging };
inline constexpr std::array<std::string_view,32> result_codes={
    "refused","unavailable","cancelled","uncertain","resource_exhausted","input_changed","policy_mismatch",
    "request_stale","context_unready","owner_unavailable","pending_operation","item_mismatch","duplicate_call","invalid_arguments","calculation_busy","visible_unmapped","project_required","unclassified",
    "owner_retired","retention_blocked","attachments_clear","publication_paused","account_unready","owner_retiring","consent_revoked",
    "history_unretained","agent_interrupted","context_pending","history_clearing","question_pending","selection_pending","input_staging"};
inline constexpr std::string_view result_code(ResultCode code) {return result_codes[static_cast<std::size_t>(code)];}
inline constexpr std::string_view maximum_result_code() {
    std::string_view maximum;
    for(const auto code:result_codes)if(code.size()>maximum.size())maximum=code;
    return maximum;
}
// Known direct-refusal codes fit the original longest code role; no response
// allowance or wire-field family grows for this diagnostic correction.
static_assert(maximum_result_code()==result_code(ResultCode::ResourceExhausted));
// Internal bound only. Keep unprojected synthetic padding, but include every
// field the actual closed projection can ADD before nesting it as response text.
inline void complete_result_maximum(QJsonObject& maximum) {
    maximum.insert("schema",QLatin1StringView(wire_schema.data(),static_cast<qsizetype>(wire_schema.size())));
    constexpr auto code=maximum_result_code();
    maximum.insert("code",QLatin1StringView(code.data(),static_cast<qsizetype>(code.size())));
}
enum class Type { Text, FitReason, ActionError, ActionField, RecipeField, RecipeReason, RecipeGuidance, Number, Boolean, Object, Array, TextArray };
struct Field { const char* name; Type type; Role child=Role::Result; };
inline const Field* fields(Role role, std::size_t& count) {
#define ROWS(...) static constexpr Field rows[]={__VA_ARGS__}; count=std::size(rows); return rows
#define T(n) Field{n,Type::Text}
#define N(n) Field{n,Type::Number}
#define B(n) Field{n,Type::Boolean}
#define O(n,r) Field{n,Type::Object,Role::r}
#define A(n,r) Field{n,Type::Array,Role::r}
    switch(role) {
    case Role::Context: { ROWS(T("schema"),O("project",Project),A("structures",Structure),A("datasets",Dataset),O("relations",Relations),A("parameters",Parameter),A("diagnostics",Diagnostic),O("selected_files",Selection),A("skills",Skill),Field{"native_actions",Type::TextArray},O("native_state",NativeState),O("input_scopes",InputScopes)); }
    case Role::Project: { ROWS(T("id"),T("revision"),T("fitting_mode")); }
    case Role::Structure: { ROWS(T("id"),O("space_group",SpaceGroup),A("sites",Site),Field{"anisotropic_site_ids",Type::TextArray}); }
    case Role::SpaceGroup: { ROWS(T("hm"),T("setting"),N("it_number")); }
    case Role::Site: { ROWS(T("id"),T("type_symbol"),T("wyckoff"),T("adp_type")); }
    case Role::Dataset: { ROWS(T("id"),T("sample_form"),T("beam_mode"),T("probe"),B("calculation_only"),T("data_status"),T("peak_profile"),Field{"peak_profile_options",Type::TextArray},O("axis",Axis),O("observations",Observations),T("absorption_type"),Field{"absorption_type_options",Type::TextArray},T("extinction_type"),Field{"extinction_type_options",Type::TextArray},T("mosaic_distribution"),Field{"mosaic_distribution_options",Type::TextArray},N("cutoff_fwhm"),N("dataset_weight"),A("excluded_regions",Region),A("phases",Phase),O("background",Background)); }
    case Role::Axis: { ROWS(T("kind"),T("unit"),N("count"),N("min"),N("max")); }
    case Role::Observations: { ROWS(N("intensity_count"),N("sigma_count"),T("weighting")); }
    case Role::Region: { ROWS(T("id"),N("first"),N("second")); }
    case Role::Phase: { ROWS(T("structure_id"),B("enabled")); }
    case Role::Background: { ROWS(T("type"),N("origin"),N("x_min"),N("x_max"),A("anchors",Anchor),A("terms",BackgroundTerm),O("estimate",BackgroundEstimate)); }
    case Role::BackgroundTerm: { ROWS(T("id"),N("order"),N("coefficient"),N("uncertainty"),B("free"),T("dependence")); }
    case Role::BackgroundEstimate: { ROWS(T("mode"),T("method"),N("width"),N("smoothness"),N("n_points"),N("tolerance"),T("in_peaks"),T("use_model"),N("max_terms")); }
    case Role::Anchor: { ROWS(T("id"),N("position"),N("intensity"),N("uncertainty"),B("free"),T("dependence")); }
    case Role::Relations: { ROWS(A("aliases",Alias),A("constraints",Constraint)); }
    case Role::Alias: { ROWS(T("id"),T("parameter_unique_name")); }
    case Role::Constraint: { ROWS(T("id"),T("expression"),B("enabled")); }
    case Role::Parameter: { ROWS(T("path"),T("unique_name"),N("value"),N("uncertainty"),T("file_value"),T("file_su"),B("free"),T("dependence"),B("refinable"),B("fittable"),T("fit_reason"),T("unit")); }
    case Role::Diagnostic: { ROWS(T("message"),T("code"),T("severity"),T("path"),B("actionable")); }
    case Role::Selection: { ROWS(T("collection_id"),T("generation"),A("files",File)); }
    case Role::File: { ROWS(T("id"),T("file_id"),N("ordinal"),N("bytes"),T("format"),T("reader_hint"),B("textReadable")); }
    // Only the deliberately shared instruction declaration digest is public;
    // input-content hashes and source configuration/path fingerprints are not.
    case Role::Skill: { ROWS(T("id"),T("sha256")); }
    case Role::InputScopes: { ROWS(A("sources",InputSource)); }
    case Role::InputSource: { ROWS(T("scope_id"),N("ordinal"),T("source_kind"),B("already_admitted")); }
    case Role::NativeState: { ROWS(T("creation_timestamp_utc"),T("selected_structure_id"),T("selected_experiment_id"),T("status"),B("calculating"),B("fitting"),B("fit_undo_available"),B("show_actions"),A("calculations",Calculation),A("interface_groups",InterfaceGroup)); }
    case Role::InterfaceGroup: { ROWS(T("page"),T("member_id"),T("category_id"),T("tier"),B("admitted")); }
    case Role::Calculation: { ROWS(T("dataset_id"),B("pattern_available"),B("stale"),N("calculated_points"),B("calculated_available"),B("calculation_error_present"),T("calculation_error"),B("calculation_error_complete")); }
    case Role::Fit: { ROWS(T("status"),B("converged"),N("reduced_chi_square"),N("iterations"),B("objective_unavailable")); }
    case Role::ReaderFacts: { ROWS(N("points"),N("skipped"),N("nonpositive"),N("duplicates"),N("reordered"),N("derived_sigma")); }
    case Role::SelectedText: { ROWS(T("file_id"),T("collection_id"),T("generation"),T("encoding"),T("text"),N("total_bytes"),N("start"),N("end"),N("next_offset"),B("eof"),B("complete")); }
    case Role::DataInspection: { ROWS(T("dataset_id"),T("sample_form"),T("source"),T("captured_revision"),T("publication_generation"),T("row_space"),T("publication"),B("current"),B("available"),B("shape_valid"),N("native_row_count"),N("requested_start"),N("requested_count"),B("calculating"),B("fitting"),T("calculation_error"),B("calculation_error_present"),B("calculation_error_complete"),T("axis_kind"),T("axis_unit"),N("total"),N("start"),N("count"),N("end"),B("eof"),A("columns",DataColumn),A("rows",DataRow),A("phases",DataPhase)); }
    case Role::DataColumn: { ROWS(T("name"),T("item"),T("unit"),T("quantity"),N("length"),B("available"),B("current")); }
    case Role::DataRow: { ROWS(N("row"),N("source_row"),N("x"),N("measured"),N("sigma"),N("calculated"),N("background"),N("residual"),N("h"),N("k"),N("l"),N("d_spacing"),N("sin_theta_over_lambda"),N("wavelength"),B("used")); }
    case Role::DataPhase: { ROWS(T("structure_id"),T("label"),T("row_space"),B("current"),N("requested_start"),N("total"),N("start"),N("count"),N("end"),B("eof"),A("columns",DataColumn),A("rows",DataRow)); }
    case Role::Result: { ROWS(O("data",DataInspection),T("name"),T("title"),T("description"),T("path"),T("message"),T("target"),T("stage"),T("page"),B("shown"),B("generated"),T("phase_id"),T("relation_id"),T("peak_profile"),T("exclusion_id"),O("excluded_region",Region),T("atom_id"),B("removed"),O("selected_text",SelectedText),T("status"),Field{"fit_reason",Type::FitReason},T("background_id"),Field{"action_error",Type::ActionError},Field{"action_field",Type::ActionField},Field{"refusal_field",Type::RecipeField},Field{"refusal_reason",Type::RecipeReason},Field{"refusal_guidance",Type::RecipeGuidance},N("minimum_items"),N("maximum_items"),B("applied"),B("published"),B("adopted"),B("committed"),B("reopened"),B("active"),B("complete"),B("atomic"),B("presentation_complete"),B("request_retired"),B("calculation_pending"),B("completed_existing"),B("saved"),B("converged"),B("objective_unavailable"),B("uncertain"),N("steps_completed"),N("iterations"),N("reduced_chi_square"),N("points"),N("skipped"),N("nonpositive"),N("duplicates"),N("reordered"),N("derived_sigma"),N("files_count"),N("supported_count"),N("unsupported_count"),N("discovered"),N("admitted"),N("ignored"),T("scope_id"),A("files",File),A("parameters",Parameter),A("diagnostics",Diagnostic),O("fit",Fit),O("reader_facts",ReaderFacts),O("project",Project),A("structures",Structure),A("datasets",Dataset),O("relations",Relations),O("selected_files",Selection),A("skills",Skill),Field{"native_actions",Type::TextArray},O("native_state",NativeState),O("input_scopes",InputScopes)); }
    }
#undef ROWS
#undef T
#undef N
#undef B
#undef O
#undef A
    throw std::invalid_argument("Outgoing role is unavailable");
}
inline void add(quint64& size, quint64 growth) {
    if(growth>std::numeric_limits<quint64>::max()-size)throw std::overflow_error("Outgoing byte count overflow");size+=growth;
}
inline quint64 scalar_size(const QJsonValue& value) {
    quint64 size=0;
    if(!codex_measured_size(value,size))throw std::length_error("Outgoing scalar exceeds capacity");
    return size;
}
// Count the same closed walk before constructing even the output JSON owners.
// Size/validation borrow the immutable JSON string views. Materializing a
// projected JSON object has its own admitted payload storage.
inline QJsonValue walk(const QJsonValue& value, Role role, quint64& size, bool materialize);
inline QJsonValue field_value(const QJsonValue& value,const Field& field,quint64& size,bool materialize) {
    if(value.isNull()) {
        if(field.type==Type::Object && field.child==Role::SelectedText)throw std::invalid_argument("Selected text is unavailable");
        if(field.type==Type::RecipeGuidance || field.type==Type::FitReason || field.type==Type::RecipeField || field.type==Type::RecipeReason || field.type==Type::ActionError || field.type==Type::ActionField)throw std::invalid_argument("Outgoing recipe refusal is unavailable");
        add(size,4);return QJsonValue(QJsonValue::Null);
    }
    switch(field.type) {
    case Type::RecipeGuidance: {
        if(!value.isString() || value.toStringView()!=QLatin1StringView(mapped_structure_guidance.data(),static_cast<qsizetype>(mapped_structure_guidance.size())))
            throw std::invalid_argument("Outgoing mapped guidance is not app-owned");
        add(size,scalar_size(value));return materialize?value:QJsonValue();
    }
    case Type::FitReason: {
        if(!value.isString() || value.toStringView()!=QLatin1StringView(unanchored_cw_dilation.data(),static_cast<qsizetype>(unanchored_cw_dilation.size())))
            throw std::invalid_argument("Outgoing fit reason is not app-owned");
        add(size,scalar_size(value));return materialize?value:QJsonValue();
    }
    case Type::ActionError:case Type::ActionField: {
        if(!value.isString())throw std::invalid_argument("Outgoing action refusal has an invalid type");
        bool known=false;
        if(field.type==Type::ActionError)for(const auto* token:action_errors)known=known || value.toString()==QLatin1StringView(token);
        else for(const auto* token:action_fields)known=known || value.toString()==QLatin1StringView(token);
        if(!known)throw std::invalid_argument("Outgoing action refusal is not app-owned");
        add(size,scalar_size(value));return materialize?value:QJsonValue();
    }
    case Type::RecipeField:case Type::RecipeReason: {
        if(!value.isString())throw std::invalid_argument("Outgoing recipe refusal has an invalid native type");
        bool known=false;
        if(field.type==Type::RecipeField)for(const auto* token:recipe_fields)known=known || value.toString()==QLatin1StringView(token);
        else for(const auto* token:recipe_reasons)known=known || value.toString()==QLatin1StringView(token);
        if(!known)throw std::invalid_argument("Outgoing recipe refusal is not app-owned");
        add(size,scalar_size(value));return materialize?value:QJsonValue();
    }
    case Type::Text:
        if(!value.isString())throw std::invalid_argument("Outgoing text has an invalid native type");
        add(size,scalar_size(value));return materialize?value:QJsonValue();
    case Type::Number:
        if(!value.isDouble() || !std::isfinite(value.toDouble()))throw std::invalid_argument("Outgoing number is not finite");
        add(size,scalar_size(value));return materialize?value:QJsonValue();
    case Type::Boolean:
        if(!value.isBool())throw std::invalid_argument("Outgoing fact has an invalid native type");
        add(size,value.toBool()?4:5);return materialize?value:QJsonValue();
    case Type::Object:return walk(value,field.child,size,materialize);
    case Type::Array:case Type::TextArray: {
        if(!value.isArray())throw std::invalid_argument("Outgoing rows have an invalid native type");
        QJsonArray result;add(size,2);bool comma=false;
        for(const auto& item:value.toArray()) {
            if(comma)add(size,1);comma=true;
            const auto projected=field.type==Type::TextArray?field_value(item,Field{"",Type::Text},size,materialize):walk(item,field.child,size,materialize);
            if(materialize)result.append(projected);
        }
        return materialize?QJsonValue(result):QJsonValue();
    }}
    throw std::invalid_argument("Outgoing type is unavailable");
}
inline QJsonValue walk(const QJsonValue& value,Role role,quint64& size,bool materialize) {
    if(!value.isObject())throw std::invalid_argument("Outgoing native object is unavailable");
    const auto source=value.toObject();
    if(role==Role::SelectedText)validate_selected_text(source);
    QJsonObject result;add(size,2);bool comma=false;
    if(role==Role::Result && source.contains("refusal_field")!=source.contains("refusal_reason"))
        throw std::invalid_argument("Outgoing recipe refusal is incomplete");
    if(role==Role::Result && source.contains("action_error")!=source.contains("action_field"))
        throw std::invalid_argument("Outgoing action refusal is incomplete");
    if(role==Role::Result && source.contains("action_error")) {
        const auto error=source.value("action_error").toStringView();
        for(std::size_t i=13;i<action_errors.size();++i)
            if(error==QLatin1StringView(action_errors[i]) && source.value("complete").toBool())
                throw std::invalid_argument("Outgoing control failure contradicts completed work");
    }
    if(role==Role::Result && source.contains("refusal_guidance")) {
        if(source.value("status")!="refused" || source.value("refusal_field")!="mapped_structure" || !source.contains("refusal_reason") ||
            source.value("applied").toBool() || source.value("published").toBool() || source.value("adopted").toBool() ||
            source.value(QLatin1StringView("committed")).toBool() || source.value(QLatin1StringView("saved")).toBool() || source.value(QLatin1StringView("reopened")).toBool() ||
            source.value(QLatin1StringView("active")).toBool() || source.value(QLatin1StringView("removed")).toBool() ||
            source.value("complete").toBool() || source.value(QLatin1StringView("presentation_complete")).toBool() || source.value(QLatin1StringView("converged")).toBool() ||
            source.value(QLatin1StringView("steps_completed")).toDouble() > 0 || source.value("uncertain").toBool())
            throw std::invalid_argument("Outgoing mapped guidance contradicts the actual refusal");
    }
    if(role==Role::Result && source.contains("fit_reason")) {
        const auto adopted=source.value("adopted"),converged=source.value("converged");
        if(source.value("status")!="error" || !adopted.isBool() || adopted.toBool() || !converged.isBool() || converged.toBool())
            throw std::invalid_argument("Outgoing fit reason contradicts the actual outcome");
    }
    const bool top=role==Role::Context || role==Role::Result;
    if(top) {
        add(size,sizeof("\"schema\":")-1+wire_schema.size()+2);
        if(materialize)result.insert("schema",QLatin1StringView(wire_schema.data(),static_cast<qsizetype>(wire_schema.size())));
        comma=true;
    }
    std::size_t count=0;const auto* schema=fields(role,count);
    for(std::size_t i=0;i<count;++i) {
        const auto& field=schema[i];
        if(top && QLatin1StringView(field.name)==QLatin1StringView("schema"))continue;
        const auto member=source.constFind(QLatin1StringView(field.name));
        if(member==source.constEnd())continue;
        if(comma)add(size,1);comma=true;
        // All field keys are fixed ASCII identifiers with no JSON escapes.
        add(size,std::char_traits<char>::length(field.name)+3);
        const auto projected=field_value(*member,field,size,materialize);
        if(materialize)result.insert(QLatin1StringView(field.name),projected);
    }
    if(role==Role::Result) {
        // This closed mapping is the sole Result code owner in both passes.
        // Counting a fixed code field as well would charge a duplicate that
        // QJsonObject overwrites, invalidating actual response byte identity.
        const auto status=source.value("status");const char* code=nullptr;
        if(status=="refused" || status=="unavailable" || status=="error")code=result_code(status=="refused"?ResultCode::Refused:ResultCode::Unavailable).data();
        else if(status=="cancelled" || status=="interrupted" || status=="superseded")code=result_code(ResultCode::Cancelled).data();
        else if(status=="unconfirmed" || status=="applied_unconfirmed" || source.value("uncertain").toBool())code=result_code(ResultCode::Uncertain).data();
        if(source.value("code")=="resource_exhausted" || source.value("code")=="input_capacity")code=result_code(ResultCode::ResourceExhausted).data();
        else if(source.value("code")=="source_changed")code=result_code(ResultCode::InputChanged).data();
        else if(source.value("code")=="policy_mismatch")code=result_code(ResultCode::PolicyMismatch).data();
        else if(!source.value("uncertain").toBool() && (status=="refused" || status=="unavailable" || status=="busy")) {
            // Only app-owned closed first-gate codes survive. Unknown source
            // messages/codes keep the original generic status projection.
            for(std::size_t i=static_cast<std::size_t>(ResultCode::RequestStale);i<result_codes.size();++i)
                if(source.value("code")==QLatin1StringView(result_codes[i].data())) {code=result_codes[i].data();break;}
        }
        if(code) {if(comma)add(size,1);add(size,sizeof("\"code\":")-1+std::char_traits<char>::length(code)+2);if(materialize)result.insert("code",QLatin1StringView(code));}
    }
    return materialize?QJsonValue(result):QJsonValue();
}
inline quint64 size(const QJsonObject& source,Role role) {quint64 n=0;(void)walk(source,role,n,false);return n;}
inline QJsonObject project(const QJsonObject& source,Role role,quint64 admitted) {
    quint64 n=0;auto result=walk(source,role,n,true).toObject();
    if(n!=admitted)throw std::logic_error("Outgoing source changed after admission");
    return result;
}
} // namespace edi_app::outgoing
