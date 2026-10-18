// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "codex_agent.hpp"
#include "assistant_recipe_refusal.hpp"
#include "assistant_action_refusal.hpp"
#include <QJsonArray>
#include <QJsonObject>
#include <QStringView>
#include <iterator>
#include <array>
#include <string_view>
#include <string>
#include <cmath>
#include <stdexcept>

namespace edi_app::outgoing {
// Closed roles over already-owned native data. Never recursively copy an
// unknown object or string, and never encode the unprojected native result.
enum class Role { Context, Project, Structure, SpaceGroup, Site, Dataset, Axis,
    Observations, Region, Phase, Background, Anchor, Relations, Alias, Constraint,
    Parameter, Diagnostic, Selection, File, Skill, InputScopes, InputSource,
    NativeState, Result, Fit, ReaderFacts };
inline constexpr std::string_view wire_schema="edi.assistant.outgoing/1";
enum class ResultCode { Refused, Unavailable, Cancelled, Uncertain, ResourceExhausted, InputChanged, PolicyMismatch };
inline constexpr std::array<std::string_view,7> result_codes={
    "refused","unavailable","cancelled","uncertain","resource_exhausted","input_changed","policy_mismatch"};
inline constexpr std::string_view result_code(ResultCode code) {return result_codes[static_cast<std::size_t>(code)];}
inline constexpr std::string_view maximum_result_code() {
    std::string_view maximum;
    for(const auto code:result_codes)if(code.size()>maximum.size())maximum=code;
    return maximum;
}
// Internal bound only. Keep unprojected synthetic padding, but include every
// field the actual closed projection can ADD before nesting it as response text.
inline void complete_result_maximum(QJsonObject& maximum) {
    maximum.insert("schema",QLatin1StringView(wire_schema.data(),static_cast<qsizetype>(wire_schema.size())));
    constexpr auto code=maximum_result_code();
    maximum.insert("code",QLatin1StringView(code.data(),static_cast<qsizetype>(code.size())));
}
enum class Type { Text, ActionError, ActionField, RecipeField, RecipeReason, Number, Boolean, Object, Array, TextArray };
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
    case Role::Dataset: { ROWS(T("id"),T("beam_mode"),T("probe"),B("calculation_only"),T("data_status"),O("axis",Axis),O("observations",Observations),N("dataset_weight"),A("excluded_regions",Region),A("phases",Phase),O("background",Background)); }
    case Role::Axis: { ROWS(T("kind"),T("unit"),N("count"),N("min"),N("max")); }
    case Role::Observations: { ROWS(N("intensity_count"),N("sigma_count"),T("weighting")); }
    case Role::Region: { ROWS(T("id"),N("first"),N("second")); }
    case Role::Phase: { ROWS(T("structure_id"),B("enabled")); }
    case Role::Background: { ROWS(T("type"),N("origin"),N("x_min"),N("x_max"),A("anchors",Anchor)); }
    case Role::Anchor: { ROWS(T("id"),N("position"),N("intensity"),N("uncertainty"),B("free"),T("dependence")); }
    case Role::Relations: { ROWS(A("aliases",Alias),A("constraints",Constraint)); }
    case Role::Alias: { ROWS(T("id"),T("parameter_unique_name")); }
    case Role::Constraint: { ROWS(T("id"),T("expression"),B("enabled")); }
    case Role::Parameter: { ROWS(T("path"),T("unique_name"),N("value"),N("uncertainty"),B("free"),T("dependence"),T("unit")); }
    case Role::Diagnostic: { ROWS(T("code"),T("severity"),T("path"),B("actionable")); }
    case Role::Selection: { ROWS(T("collection_id"),T("generation"),A("files",File)); }
    case Role::File: { ROWS(T("id"),T("file_id"),N("ordinal"),N("bytes"),T("format"),T("reader_hint"),B("textReadable")); }
    // Only the deliberately shared instruction declaration digest is public;
    // input-content hashes and source configuration/path fingerprints are not.
    case Role::Skill: { ROWS(T("id"),T("sha256")); }
    case Role::InputScopes: { ROWS(A("sources",InputSource)); }
    case Role::InputSource: { ROWS(T("scope_id"),N("ordinal"),T("source_kind"),B("already_admitted")); }
    case Role::NativeState: { ROWS(T("status"),B("calculating"),B("fitting"),B("show_actions")); }
    case Role::Fit: { ROWS(T("status"),B("converged"),N("reduced_chi_square"),N("iterations"),B("objective_unavailable")); }
    case Role::ReaderFacts: { ROWS(N("points"),N("skipped"),N("nonpositive"),N("duplicates"),N("reordered"),N("derived_sigma")); }
    case Role::Result: { ROWS(T("status"),Field{"action_error",Type::ActionError},Field{"action_field",Type::ActionField},Field{"refusal_field",Type::RecipeField},Field{"refusal_reason",Type::RecipeReason},N("minimum_items"),N("maximum_items"),B("applied"),B("published"),B("adopted"),B("committed"),B("reopened"),B("active"),B("complete"),B("atomic"),B("presentation_complete"),B("request_retired"),B("calculation_pending"),B("completed_existing"),B("saved"),B("converged"),B("objective_unavailable"),B("uncertain"),N("steps_completed"),N("iterations"),N("reduced_chi_square"),N("points"),N("skipped"),N("nonpositive"),N("duplicates"),N("reordered"),N("derived_sigma"),N("files_count"),N("supported_count"),N("unsupported_count"),N("discovered"),N("admitted"),N("ignored"),T("scope_id"),A("files",File),A("parameters",Parameter),A("diagnostics",Diagnostic),O("fit",Fit),O("reader_facts",ReaderFacts),O("project",Project),A("structures",Structure),A("datasets",Dataset),O("relations",Relations),O("selected_files",Selection),A("skills",Skill),Field{"native_actions",Type::TextArray},O("native_state",NativeState),O("input_scopes",InputScopes)); }
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
    if(size>edi::assistant::Limits::context_bytes || growth>edi::assistant::Limits::context_bytes-size)throw std::length_error("Outgoing projection exceeds capacity");size+=growth;
}
inline quint64 scalar_size(const QJsonValue& value) {
    quint64 size=0;
    if(!codex_encoded_size(value,edi::assistant::Limits::context_bytes,size))throw std::length_error("Outgoing scalar exceeds capacity");
    return size;
}
// Count the same closed walk before constructing even the output JSON owners.
// Primitive Qt JSON strings are shared from the original immutable native value.
inline QJsonValue walk(const QJsonValue& value, Role role, quint64& size, bool materialize);
inline QJsonValue field_value(const QJsonValue& value,const Field& field,quint64& size,bool materialize) {
    if(value.isNull()) {
        if(field.type==Type::RecipeField || field.type==Type::RecipeReason || field.type==Type::ActionError || field.type==Type::ActionField)throw std::invalid_argument("Outgoing recipe refusal is unavailable");
        add(size,4);return QJsonValue(QJsonValue::Null);
    }
    switch(field.type) {
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
    const auto source=value.toObject();QJsonObject result;add(size,2);bool comma=false;
    if(role==Role::Result && source.contains("refusal_field")!=source.contains("refusal_reason"))
        throw std::invalid_argument("Outgoing recipe refusal is incomplete");
    if(role==Role::Result && source.contains("action_error")!=source.contains("action_field"))
        throw std::invalid_argument("Outgoing action refusal is incomplete");
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
        const auto status=source.value("status");const char* code=nullptr;
        if(status=="refused" || status=="unavailable" || status=="error")code=result_code(status=="refused"?ResultCode::Refused:ResultCode::Unavailable).data();
        else if(status=="cancelled" || status=="interrupted" || status=="superseded")code=result_code(ResultCode::Cancelled).data();
        else if(status=="unconfirmed" || status=="applied_unconfirmed" || source.value("uncertain").toBool())code=result_code(ResultCode::Uncertain).data();
        if(source.value("code")=="resource_exhausted" || source.value("code")=="input_capacity")code=result_code(ResultCode::ResourceExhausted).data();
        else if(source.value("code")=="source_changed")code=result_code(ResultCode::InputChanged).data();
        else if(source.value("code")=="policy_mismatch")code=result_code(ResultCode::PolicyMismatch).data();
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
