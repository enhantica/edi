// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include "experiment_view_model.hpp"
#include "experiment_models.hpp"
#include "../../core/src/assistant_json.hpp"
#include "edi/display.hpp"
#include "edi/presentation.hpp"
#include <QJsonArray>
#include <QJsonObject>
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>

namespace edi_app::assistant_data {
// Original native publication owners, without calculation or GUI publication.
// ADR-0057 owns the scalar column contract.
inline double index_number(std::size_t value) {
    if(value>((quint64{1}<<std::numeric_limits<double>::digits)-1))edi::assistant::detail::refuse("invalid_argument","The requested native row index is not exactly representable in JSON");
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
} // namespace edi_app::assistant_data
