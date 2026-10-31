// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "experiment_view_model.hpp"
#include "experiment_models.hpp"
#include "assistant_data_summary.hpp"
#include <array>
#include <QVariant>
#include "../../core/src/assistant_json.hpp"
#include "edi/display.hpp"
#include "edi/presentation.hpp"
#include <QJsonArray>
#include <QJsonObject>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <utility>

namespace edi_app::assistant_data {
// Original native publication owners, without calculation or GUI publication.
// ADR-0057 owns the scalar column contract.
inline double index_number(std::size_t value) {
    if constexpr (std::numeric_limits<std::size_t>::digits > std::numeric_limits<double>::digits) {
        if (static_cast<std::uintmax_t>(value) > ((quint64{1} << std::numeric_limits<double>::digits) - 1))
            edi::assistant::detail::refuse("invalid_argument","The requested native row index is not exactly representable in JSON");
    }
    return static_cast<double>(value);
}
inline std::size_t index(const QJsonValue& value) {
    if(!value.isDouble())edi::assistant::detail::refuse("invalid_argument","The data slice needs integer start and count fields");
    const double number=value.toDouble();
    if(!std::isfinite(number) || number<0 || std::floor(number)!=number || number>std::ldexp(1.0,std::numeric_limits<double>::digits)-1 ||
       static_cast<long double>(number)>static_cast<long double>(std::numeric_limits<std::size_t>::max()))
        edi::assistant::detail::refuse("invalid_argument","The data slice start and count must be nonnegative exactly representable native indices");
    return static_cast<std::size_t>(number);
}
inline QJsonValue number(double value) {return std::isfinite(value)?QJsonValue(value):QJsonValue(QJsonValue::Null);}
inline QString unit(const char* item) {
    return edi::has_item(item)?QString::fromStdString(edi::units_label(item)):QString{};
}
inline QJsonValue sample(const edi::PatternSource::Column& column,std::size_t row) {
    return column && row<column->size()?number((*column)[row]):QJsonValue(QJsonValue::Null);
}
inline QJsonObject column(const char* name,const char* item,std::size_t length,bool available,bool current,
                          QString quantity={}) {
    return {{"name",name},{"item",item},{"unit",unit(item)},{"quantity",quantity},
        {"length",index_number(length)},{"available",available},{"current",current}};
}
struct Slice {std::size_t first=0,end=0;};
inline Slice slice(std::size_t start,std::size_t count,std::size_t total) {
    if(start>total)edi::assistant::detail::refuse("invalid_argument","The data slice starts beyond the actual native row extent");
    return {start,start+std::min(count,total-start)};
}
inline QJsonObject extent(std::size_t total,Slice selected) {
    return {{"total",index_number(total)},{"start",index_number(selected.first)},
        {"count",index_number(selected.end-selected.first)},{"end",index_number(selected.end)},
        {"eof",selected.end==total}};
}
inline QJsonObject powder(const edi::PatternSource& source,std::size_t start,std::size_t count) {
    const auto total=source.x?source.x->size():std::size_t{};
    const auto selected=slice(start,count,total);
    QJsonObject out=extent(total,selected);
    out["row_space"]="native_data";
    out["publication"]="native";
    out["current"]=source.current;
    out["available"]=bool(source.x);
    out["axis_kind"]=QString::fromStdString(source.x_item);
    out["axis_unit"]=unit(source.x_item.c_str());
    QJsonArray columns;
    const auto append=[&](const char* name,const char* item,const edi::PatternSource::Column& values,bool computed) {
        columns.append(column(name,item,values?values->size():0,bool(values),!computed || source.current));
    };
    append("x",source.x_item.c_str(),source.x,false);
    append("measured","data.intensity_meas",source.meas,false);
    append("sigma","data.intensity_meas_su",source.su,false);
    append("calculated","data.intensity_calc",source.calc,true);
    append("background","data.intensity_bkg",source.bkg,true);
    append("residual","data.residual",source.resid,true);
    out["columns"]=columns;
    QJsonArray rows;
    for(auto i=selected.first;i<selected.end;++i)rows.append(QJsonObject{
        {"row",index_number(i)},{"source_row",index_number(i)},
        {"x",sample(source.x,i)},{"measured",sample(source.meas,i)},{"sigma",sample(source.su,i)},
        {"calculated",sample(source.calc,i)},{"background",sample(source.bkg,i)},{"residual",sample(source.resid,i)}});
    out["rows"]=rows;
    return out;
}
inline QJsonObject reflections(const edi::ExperimentBase& experiment,const SingleCrystalReflectionModel& model,
                               std::size_t start,std::size_t count) {
    const auto& native=experiment.reflections;
    const auto total=static_cast<std::size_t>(model.fileRowCount());
    const auto selected=slice(start,count,total);
    const bool shaped=native && native->rectangular();
    const bool frame=model.showingFrame();
    const bool current=!frame && experiment.computed_current();
    const bool calculated=shaped && model.calculatedShown();
    QJsonObject out=extent(total,selected);
    out["row_space"]="native_reflection";
    out["publication"]=frame?"fit_frame":"native";
    out["current"]=current;
    out["shape_valid"]=shaped;
    out["available"]=shaped;
    out["native_row_count"]=index_number(native?native->size():0);
    out["axis_kind"]="miller_indices";
    out["axis_unit"]="dimensionless";
    QJsonArray columns;
    const auto add=[&](const char* name,const char* item,std::size_t length,bool available,bool computed,QString quantity={}) {
        columns.append(column(name,item,length,available,!computed || current,std::move(quantity)));
    };
    add("h","refln.index_h",native?native->index_h.size():0,bool(native),false);
    add("k","refln.index_k",native?native->index_k.size():0,bool(native),false);
    add("l","refln.index_l",native?native->index_l.size():0,bool(native),false);
    add("measured","refln.intensity_meas",native?native->intensity_meas.size():0,bool(native),false,"F_squared");
    add("sigma","refln.intensity_meas_su",native?native->intensity_meas_su.size():0,bool(native),false,"F_squared");
    add("calculated","refln.intensity_calc",calculated?total:0,calculated,true,"F_squared");
    add("residual","",calculated?total:0,calculated,true,"normalized_F_squared_residual");
    add("d_spacing","refln.d_spacing",native?native->d_spacing.size():0,calculated,true);
    add("sin_theta_over_lambda","refln.sin_theta_over_lambda",native?native->sin_theta_over_lambda.size():0,calculated,true);
    add("wavelength","refln.wavelength",native?native->wavelength.size():0,native && !native->wavelength.empty(),false);
    add("used","",shaped?total:0,shaped,false,"fit_inclusion");
    out["columns"]=columns;
    QJsonArray rows;
    for(auto i=selected.first;i<selected.end;++i) {
        const auto value=[&](const char* role) {const auto v=model.fileValue(static_cast<qsizetype>(i),QString::fromLatin1(role));return v.isValid()?number(v.toDouble()):QJsonValue(QJsonValue::Null);};
        const auto used=model.fileValue(static_cast<qsizetype>(i),QStringLiteral("fitUse"));
        rows.append(QJsonObject{{"row",index_number(i)},{"source_row",index_number(i)},
            {"h",value("h")},{"k",value("k")},{"l",value("l")},
            {"measured",value("intensityMeas")},{"sigma",value("intensityMeasSu")},
            {"calculated",value("intensityCalc")},{"residual",value("residual")},
            {"d_spacing",value("dSpacing")},{"sin_theta_over_lambda",value("sinThetaOverLambda")},
            {"wavelength",value("wavelength")},{"used",used.isValid()?QJsonValue(used.toDouble()!=0):QJsonValue(QJsonValue::Null)}});
    }
    out["rows"]=rows;
    return out;
}
inline QJsonObject bragg(const edi::PatternSource& source,std::size_t start,std::size_t count) {
    QJsonArray phases;
    for(const auto& phase:source.phases) {
        const auto total=phase.position?phase.position->size():std::size_t{};
        const auto selected=slice(std::min(start,total),count,total);
        QJsonObject out=extent(total,selected);
        out["requested_start"]=index_number(start);
        out["structure_id"]=QString::fromStdString(phase.structure_id);
        out["label"]=QString::fromStdString(phase.label);
        out["row_space"]="phase_reflection";
        out["current"]=source.current;
        out["columns"]=QJsonArray{column("x",source.x_item.c_str(),total,bool(phase.position),source.current),
            column("h","refln.index_h",phase.hkl?phase.hkl->size():0,bool(phase.hkl),source.current),
            column("k","refln.index_k",phase.hkl?phase.hkl->size():0,bool(phase.hkl),source.current),
            column("l","refln.index_l",phase.hkl?phase.hkl->size():0,bool(phase.hkl),source.current)};
        QJsonArray rows;
        for(auto i=selected.first;i<selected.end;++i) {
            QJsonObject row{{"row",index_number(i)},{"source_row",phase.rows.empty()?QJsonValue(index_number(i)):
                (i<phase.rows.size()?QJsonValue(index_number(phase.rows[i])):QJsonValue(QJsonValue::Null))},
                {"x",sample(phase.position,i)}};
            for(std::size_t h=0;h<3;++h)row[h==0?"h":h==1?"k":"l"]=phase.hkl && i<phase.hkl->size()?
                QJsonValue((*phase.hkl)[i][h]):QJsonValue(QJsonValue::Null);
            rows.append(row);
        }
        out["rows"]=rows;phases.append(out);
    }
    return {{"publication","native"},{"current",source.current},{"available",!source.phases.empty()},{"requested_start",index_number(start)},
        {"requested_count",index_number(count)},{"axis_kind",QString::fromStdString(source.x_item)},
        {"axis_unit",unit(source.x_item.c_str())},{"phases",phases}};
}
namespace compact_detail {
inline const char* mask_name(summary::MaskSource value) {
    switch(value) {
    case summary::MaskSource::NativeCalcStatus:return "native_calc_status";
    case summary::MaskSource::SingleCrystalFileFitUse:return "single_crystal_file_fitUse";
    case summary::MaskSource::NotApplicable:return "not_applicable";
    }
    throw std::logic_error("Unknown summary mask source");
}
inline const char* order_name(summary::AxisOrder value) {
    switch(value) {
    case summary::AxisOrder::StrictlyIncreasing:return "strictly_increasing";
    case summary::AxisOrder::StrictlyDecreasing:return "strictly_decreasing";
    case summary::AxisOrder::Nondecreasing:return "nondecreasing";
    case summary::AxisOrder::Nonincreasing:return "nonincreasing";
    case summary::AxisOrder::Constant:return "constant";
    case summary::AxisOrder::Unordered:return "unordered";
    case summary::AxisOrder::Unknown:return "unknown";
    case summary::AxisOrder::NotApplicable:return "not_applicable";
    }
    throw std::logic_error("Unknown summary axis order");
}
inline const char* moment_name(summary::MomentState value) {
    switch(value) {
    case summary::MomentState::Ok:return "ok";
    case summary::MomentState::EmptyRange:return "empty_range";
    case summary::MomentState::UnavailableColumn:return "unavailable_column";
    case summary::MomentState::NoFiniteValues:return "no_finite_values";
    case summary::MomentState::NoKnownIncludedFiniteValues:return "no_known_included_finite_values";
    case summary::MomentState::ArithmeticUnavailable:return "arithmetic_unavailable";
    }
    throw std::logic_error("Unknown summary moment state");
}
inline QJsonValue count_value(const std::optional<std::size_t>& value) {
    return value?QJsonValue(index_number(*value)):QJsonValue(QJsonValue::Null);
}
inline QJsonValue finite_value(const std::optional<double>& value) {
    if(!value)return QJsonValue(QJsonValue::Null);
    if(!std::isfinite(*value))throw std::logic_error("Nonfinite summary result");
    return *value;
}
inline QJsonValue witness_value(const std::optional<summary::Witness>& value) {
    if(!value)return QJsonValue(QJsonValue::Null);
    return QJsonObject{{"value",finite_value(value->value)},{"row",index_number(value->row)},
        {"source_row",count_value(value->source_row)}};
}
inline QJsonValue moment_value(const std::optional<summary::Moments>& value) {
    if(!value)return QJsonValue(QJsonValue::Null);
    const char* population=nullptr;
    switch(value->population) {
    case summary::Population::AllFinite:population="all_finite";break;
    case summary::Population::KnownIncludedFinite:population="known_included_finite";break;
    }
    if(!population)throw std::logic_error("Unknown summary population");
    return QJsonObject{{"population",population},{"count",index_number(value->count)},
        {"population_complete",value->population_complete},{"state",moment_name(value->state)},
        {"mean",finite_value(value->mean)},{"rms",finite_value(value->rms)}};
}
inline QJsonObject range_value(const summary::RangeSummary& value) {
    QJsonObject mask{{"source",mask_name(value.mask.source)},{"applicable",value.mask.applicable},
        {"current",value.mask.current},{"included",count_value(value.mask.included)},
        {"excluded",count_value(value.mask.excluded)},{"unknown",count_value(value.mask.unknown)}};
    QJsonArray columns;
    for(const auto& c:value.columns) {
        const auto& m=c.metadata;
        QJsonObject row{{"name",QString::fromStdString(m.name)},{"item",QString::fromStdString(m.item)},
            {"unit",QString::fromStdString(m.unit)},{"quantity",QString::fromStdString(m.quantity)},
            {"length",index_number(m.length)},{"available",m.available},{"current",m.current},
            {"finite",index_number(c.coverage.finite)},{"missing",index_number(c.coverage.missing)},
            {"nan",index_number(c.coverage.nan)},{"positive_infinity",index_number(c.coverage.positive_infinity)},
            {"negative_infinity",index_number(c.coverage.negative_infinity)},
            {"minimum",witness_value(c.minimum)},{"maximum",witness_value(c.maximum)},
            {"first",witness_value(c.first)},{"last",witness_value(c.last)},
            {"all_finite",moment_value(c.all_finite)},{"included_finite",moment_value(c.included_finite)}};
        if(c.sigma_quality)row["sigma_quality"]=QJsonObject{{"positive",index_number(c.sigma_quality->positive)},
            {"zero",index_number(c.sigma_quality->zero)},{"negative",index_number(c.sigma_quality->negative)}};
        columns.append(row);
    }
    return {{"start",index_number(value.range.first)},{"count",index_number(value.range.count())},
        {"end",index_number(value.range.end)},{"mask",mask},{"axis_order",order_name(value.axis_order)},{"columns",columns}};
}
inline QJsonObject summary_value(const summary::Summary& value) {
    QJsonArray bins;for(const auto& bin:value.bins)bins.append(range_value(bin));
    return {{"schema","edi.assistant.data-summary/1"},{"partitioning","contiguous_native_rows"},
        {"requested_partitions",index_number(value.requested_partitions)},{"partitions",index_number(value.bins.size())},
        {"physical_components",QJsonObject{{"available",false},{"reason","not_exposed_by_this_inspection"}}},
        {"overall",range_value(value.overall)},{"bins",bins}};
}
inline summary::ColumnKind column_kind(const QString& name) {
    using K=summary::ColumnKind;
    if(name=="x")return K::X;if(name=="h")return K::H;if(name=="k")return K::K;if(name=="l")return K::L;
    if(name=="measured")return K::Measured;if(name=="sigma")return K::Sigma;if(name=="calculated")return K::Calculated;
    if(name=="background")return K::Background;if(name=="residual")return K::Residual;
    if(name=="d_spacing")return K::DSpacing;if(name=="sin_theta_over_lambda")return K::SinThetaOverLambda;
    if(name=="wavelength")return K::Wavelength;
    throw std::logic_error("Unsupported original summary column");
}
inline summary::ColumnMetadata metadata(const QJsonObject& original) {
    return {column_kind(original.value("name").toString()),original.value("name").toString().toStdString(),
        original.value("item").toString().toStdString(),original.value("unit").toString().toStdString(),
        original.value("quantity").toString().toStdString(),index(original.value("length")),
        original.value("available").toBool(),original.value("current").toBool()};
}
inline QJsonObject attach(QJsonObject out,const summary::Input& input,bool withView=true) {
    const auto value=summary::summarize(input);
    const auto bounds=extent(input.total,{value.overall.range.first,value.overall.range.end});
    for(auto i=bounds.begin();i!=bounds.end();++i)out.insert(i.key(),i.value());
    out.remove("rows");if(withView)out["view"]="summary";
    out["summary"]=summary_value(value);return out;
}
inline std::optional<double> native_cell(const QVariant& value) {
    if(!value.isValid() || value.isNull())return {};
    switch(value.metaType().id()) {
    case QMetaType::Double:case QMetaType::Float:case QMetaType::Int:case QMetaType::UInt:
    case QMetaType::LongLong:case QMetaType::ULongLong:break;
    default:throw std::invalid_argument("The original reflection cell is not numeric");
    }
    bool ok=false;const auto result=value.toDouble(&ok);
    if(!ok)throw std::invalid_argument("The original reflection cell could not be read");
    return result; // Present NaN/Inf survive until explicit coverage accounting.
}
inline const char* file_role(const QString& name) {
    if(name=="h")return "h";if(name=="k")return "k";if(name=="l")return "l";
    if(name=="measured")return "intensityMeas";if(name=="sigma")return "intensityMeasSu";
    if(name=="calculated")return "intensityCalc";if(name=="residual")return "residual";
    if(name=="d_spacing")return "dSpacing";if(name=="sin_theta_over_lambda")return "sinThetaOverLambda";
    if(name=="wavelength")return "wavelength";
    throw std::logic_error("Unsupported original reflection summary role");
}
} // namespace compact_detail

// Summary adapters reuse original zero-row metadata, never already-null JSON cells.
inline QJsonObject powder_summary(const edi::PatternSource& source,
        const edi::ComputedColumn<std::string>::Buffer& status,bool maskCurrent,
        std::size_t start,std::size_t count,std::size_t partitions) {
    auto out=powder(source,start,0);const auto total=source.x?source.x->size():0;
    const auto selected=summary::select_range(start,count,total);
    const auto original=out.value("columns").toArray();
    std::array<bool,6> seen{};
    if(original.size()!=static_cast<qsizetype>(seen.size()))throw std::logic_error("Powder summary metadata changed");
    std::vector<summary::ColumnInput> columns;columns.reserve(seen.size());std::optional<std::size_t> axis;
    for(const auto& entry:original) {
        const auto m=compact_detail::metadata(entry.toObject());edi::PatternSource::Column values;std::size_t slot=0;
        switch(m.kind) {
        case summary::ColumnKind::X:values=source.x;slot=0;axis=columns.size();break;
        case summary::ColumnKind::Measured:values=source.meas;slot=1;break;
        case summary::ColumnKind::Sigma:values=source.su;slot=2;break;
        case summary::ColumnKind::Calculated:values=source.calc;slot=3;break;
        case summary::ColumnKind::Background:values=source.bkg;slot=4;break;
        case summary::ColumnKind::Residual:values=source.resid;slot=5;break;
        default:throw std::logic_error("Unexpected original powder summary column");
        }
        if(seen[slot])throw std::logic_error("Duplicate original powder summary column");seen[slot]=true;
        columns.push_back({m,0,values?std::span<const double>(*values):std::span<const double>{}});
    }
    const bool current=maskCurrent && source.current && bool(status);
    std::vector<summary::Inclusion> mask;
    if(current)for(auto row=selected.first;row<selected.end && row<status->size();++row) {
        const auto& value=(*status)[row];mask.push_back(value=="incl"?summary::Inclusion::Included:
            value=="excl"?summary::Inclusion::Excluded:summary::Inclusion::Unknown);
    }
    return compact_detail::attach(std::move(out),summary::Input{summary::RowSpace::Powder,total,start,count,partitions,columns,
        {summary::MaskSource::NativeCalcStatus,current,selected.first,mask},summary::IdentityMapping{},axis});
}
inline QJsonObject reflection_summary(const edi::ExperimentBase& experiment,const SingleCrystalReflectionModel& model,
        std::size_t start,std::size_t count,std::size_t partitions) {
    auto out=reflections(experiment,model,start,0);const auto total=static_cast<std::size_t>(model.fileRowCount());
    const auto selected=summary::select_range(start,count,total);
    const auto original=out.value("columns").toArray();
    std::vector<std::vector<std::optional<double>>> cells;cells.reserve(static_cast<std::size_t>(original.size()));
    std::vector<summary::ColumnInput> columns;columns.reserve(static_cast<std::size_t>(original.size()));
    for(const auto& entry:original) {
        const auto m=entry.toObject();const auto name=m.value("name").toString();if(name=="used")continue;
        auto& values=cells.emplace_back();
        if(m.value("available").toBool()) {
            const auto role=QString::fromLatin1(compact_detail::file_role(name));values.reserve(selected.count());
            for(auto row=selected.first;row<selected.end;++row)values.push_back(compact_detail::native_cell(model.fileValue(static_cast<qsizetype>(row),role)));
        }
        columns.push_back({compact_detail::metadata(m),selected.first,std::span<const std::optional<double>>(values)});
    }
    const bool maskCurrent=experiment.reflections && experiment.reflections->rectangular() && experiment.reflections->size()==total;
    std::vector<summary::Inclusion> mask;
    if(maskCurrent)for(auto row=selected.first;row<selected.end;++row) {
        const auto value=compact_detail::native_cell(model.fileValue(static_cast<qsizetype>(row),QStringLiteral("fitUse")));
        mask.push_back(value && *value==1?summary::Inclusion::Included:value && *value==0?summary::Inclusion::Excluded:summary::Inclusion::Unknown);
    }
    return compact_detail::attach(std::move(out),summary::Input{summary::RowSpace::SingleCrystal,total,start,count,partitions,columns,
        {summary::MaskSource::SingleCrystalFileFitUse,maskCurrent,selected.first,mask},summary::IdentityMapping{},std::nullopt});
}
inline QJsonObject bragg_summary(const edi::PatternSource& source,std::size_t start,std::size_t count,std::size_t partitions) {
    auto out=bragg(source,start,0);auto phases=out.value("phases").toArray();
    if(phases.size()!=static_cast<qsizetype>(source.phases.size()))throw std::logic_error("Bragg summary metadata changed");
    for(std::size_t phaseIndex=0;phaseIndex<source.phases.size();++phaseIndex) {
        const auto& phase=source.phases[phaseIndex];auto original=phases.at(static_cast<qsizetype>(phaseIndex)).toObject();
        const auto total=phase.position?phase.position->size():0;const auto first=std::min(start,total);
        const auto selected=summary::select_range(first,count,total);const auto meta=original.value("columns").toArray();
        if(meta.size()!=4)throw std::logic_error("Bragg summary columns changed");
        std::vector<summary::ColumnInput> columns;columns.reserve(4);std::optional<std::size_t> axis;
        std::array<std::vector<std::optional<double>>,3> hkl;std::array<bool,3> seen{};
        for(const auto& entry:meta) {
            const auto m=compact_detail::metadata(entry.toObject());
            if(m.kind==summary::ColumnKind::X) {
                if(axis)throw std::logic_error("Duplicate original Bragg axis");axis=columns.size();
                columns.push_back({m,0,phase.position?std::span<const double>(*phase.position):std::span<const double>{}});continue;
            }
            std::size_t component=0;
            switch(m.kind) {
            case summary::ColumnKind::H:component=0;break;
            case summary::ColumnKind::K:component=1;break;
            case summary::ColumnKind::L:component=2;break;
            default:throw std::logic_error("Unexpected original Bragg summary column");
            }
            if(seen[component])throw std::logic_error("Duplicate original Bragg index column");seen[component]=true;
            if(phase.hkl)for(auto row=selected.first;row<selected.end && row<phase.hkl->size();++row)
                hkl[component].push_back(static_cast<double>((*phase.hkl)[row][component]));
            columns.push_back({m,selected.first,std::span<const std::optional<double>>(hkl[component])});
        }
        std::vector<std::optional<std::size_t>> sourceRows;
        summary::RowMapping mapping=summary::IdentityMapping{};
        if(!phase.rows.empty()) {
            for(auto row=selected.first;row<selected.end && row<phase.rows.size();++row)sourceRows.push_back(phase.rows[row]);
            mapping=summary::ExplicitMapping{selected.first,sourceRows};
        }
        phases[static_cast<qsizetype>(phaseIndex)]=compact_detail::attach(std::move(original),summary::Input{
            summary::RowSpace::BraggPhase,total,first,count,partitions,columns,
            {summary::MaskSource::NotApplicable,false,0,{}},mapping,axis},false);
    }
    out["phases"]=phases;out["requested_count"]=index_number(count);out["view"]="summary";return out;
}

} // namespace edi_app::assistant_data
