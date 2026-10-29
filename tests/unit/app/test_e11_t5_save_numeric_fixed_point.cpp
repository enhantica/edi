// SPDX-License-Identifier: BSD-3-Clause
// Independent persistence properties; no second formatter or fitted reference.
#include <crysta/su_format.hpp>
#include "../../fixtures/native_edi_document/edi.hpp"
#include "../../fixtures/native_edi_document/version.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "project_view_model.hpp"
#include "session.hpp"
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDebug>
#include <QJsonDocument>
#include <QtTest/qtestcase.h>
#include <QDir>
#include <QEventLoop>
#include <QFileInfo>
#include <QObject>
#include <QPointer>
#include <QTemporaryDir>
#include <QTimer>
#include <QStringList>
#include <QUrl>
#include <QVariantMap>
#include <QJsonArray>
#include <QJsonObject>
#include <QtQml/qqml.h>
#include <algorithm>
#include <charconv>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace {
double decimal(const std::string& text) {
    double value=0;
    const auto parsed=std::from_chars(text.data(),text.data()+text.size(),value);
    if(parsed.ec!=std::errc() || parsed.ptr!=text.data()+text.size() || !std::isfinite(value))
        throw std::runtime_error("Native numeric spelling is not a complete finite decimal");
    return value;
}
std::string bytes(const std::filesystem::path& path) {
    std::ifstream input(path,std::ios::binary);
    if(!input)throw std::runtime_error("Ordinary saved file is unavailable: "+path.string());
    std::ostringstream result;result<<input.rdbuf();return result.str();
}
void fact(const QString& stage,QJsonObject value) {
    value["stage"]=stage;
    qInfo().noquote()<<QJsonDocument(value).toJson(QJsonDocument::Compact);
}
struct Checks {
    QStringList errors;
    int count=0;
    void require(bool value,const QString& message) {
        ++count;if(value)return;
        errors.push_back(message);
        // One normal QtTest incident per failed condition, not one lossy joined
        // Description across every input/stage. C++ continues the finite sweep.
        QTest::qFail(message.toUtf8().constData(),__FILE__,__LINE__);
    }
    QVariantMap result() const {
        fact(QStringLiteral("method_complete"),{{"sweep_returned",true},{"checks",count},{"failures",static_cast<qint64>(errors.size())}});
        return {{"ok",errors.isEmpty()},{"checks",count},{"error",errors.isEmpty()?QString():QStringLiteral("%1 individual failures; see case/stage QtTest incidents and messages").arg(errors.size())}};
    }
};
using State=std::tuple<double,std::optional<double>,bool,edi::Dependence>;
std::map<std::string,State> states(edi::Project& project) {
    std::map<std::string,State> result;
    for(const auto& row:edi::parameter_entries(project)) {
        const auto& p=*row.parameter;
        if(!result.emplace(row.path,State{p.value.get(),p.uncertainty.get(),p.free.get(),p.dependence}).second)
            throw std::runtime_error("Duplicate actual parameter path in persistence witness");
    }
    return result;
}
edi::ParameterEntry adp(edi::Project& project) {
    std::optional<edi::ParameterEntry> result;
    for(const auto& row:edi::parameter_entries(project))if(row.category=="atom_site" && row.name=="adp_iso") {
        if(result)throw std::runtime_error("Fixture must expose exactly one original isotropic ADP");
        result=row;
    }
    if(!result)throw std::runtime_error("Original independent ADP owner is unavailable");
    return *result;
}
bool idle(edi_app::ProjectViewModel& project) {
    if(!project.calculating())return true;
    QEventLoop loop;QTimer deadline;deadline.setSingleShot(true);
    QObject::connect(&project,&edi_app::ProjectViewModel::calculatingChanged,&loop,[&]{if(!project.calculating())loop.quit();});
    QObject::connect(&deadline,&QTimer::timeout,&loop,&QEventLoop::quit);
    // A readiness bound, not a latency target. The outer cohort still owns174s.
    deadline.start(5000);loop.exec();return !project.calculating();
}
}

class SaveNumericFixedPointProof final : public QObject {
    Q_OBJECT
    static QString root() {return QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()).absoluteFilePath("../../..");}
    static void persistedCalculation(Checks& check,edi::Project& current,edi::Project& reopened,
                                     const std::filesystem::path& destination,const QString& stage) {
        check.require(current.experiment().data.has_value() && reopened.experiment().data.has_value(),stage+": original measured support exists in current and reopened models");
        if(!current.experiment().data || !reopened.experiment().data)return;
        const auto& measured=*reopened.experiment().data;
        const auto& currentMeasured=*current.experiment().data;
        const auto& readAxis=measured.two_theta.get()?*measured.two_theta.get():*measured.time_of_flight.get();
        const auto& currentAxis=currentMeasured.two_theta.get()?*currentMeasured.two_theta.get():*currentMeasured.time_of_flight.get();
        const auto path=edi::entity_path(destination.string(),"experiment",reopened.experiment().name.value());
        const auto original=bytes(path);
        const auto document=crysta::parse_edi(original);
        const auto block=document.only_block();
        const auto loop=block->loop_with("_data.intensity_calc");
        check.require(bool(loop),stage+": FIRST parser finds the actual persisted calculated-intensity column");
        if(!loop) {fact(stage,{{"kind","original_persisted_calculation"},{"column_present",false},{"file",QString::fromStdString(path)}});return;}
        const std::string axisName=measured.two_theta.get()?"_data.two_theta":"_data.time_of_flight";
        const auto axisPosition=std::find(loop->keys().begin(),loop->keys().end(),axisName);
        const auto calcPosition=std::find(loop->keys().begin(),loop->keys().end(),"_data.intensity_calc");
        check.require(axisPosition!=loop->keys().end(),stage+": persisted calc rows carry the original measured-axis column");
        check.require(!loop->rows().empty() && loop->rows().size()==readAxis.size() && readAxis==currentAxis && readAxis.size()==current.experiment().data->intensity_calc.size(),stage+": original persisted row count and measured support agree with current calculation");
        const auto statusPosition=std::find(loop->keys().begin(),loop->keys().end(),"_data.calc_status");
        const auto& currentValues=currentMeasured.intensity_calc.values();
        const auto& currentStatuses=currentMeasured.calc_status.values();
        check.require(statusPosition!=loop->keys().end() && currentStatuses.size()==readAxis.size(),stage+": original persisted/current calculation-status support exists");
        bool supportEqual=axisPosition!=loop->keys().end() && loop->rows().size()==readAxis.size();
        bool statusEqual=statusPosition!=loop->keys().end() && currentStatuses.size()==readAxis.size();
        std::size_t available=0,numeric=0,excluded=0,missing=0,badCells=0;
        QByteArray calcTokens;
        if(axisPosition!=loop->keys().end()) {
            const auto axisIndex=static_cast<std::size_t>(axisPosition-loop->keys().begin());
            const auto calcIndex=static_cast<std::size_t>(calcPosition-loop->keys().begin());
            const auto statusIndex=static_cast<std::size_t>(statusPosition-loop->keys().begin());
            for(std::size_t i=0;i<loop->rows().size();++i) {
                const auto& row=loop->rows()[i];
                if(axisIndex>=row.size() || calcIndex>=row.size())throw std::runtime_error("FIRST parser returned a ragged persisted data row");
                if(i>=readAxis.size() || crysta::parse_edi_number(row[axisIndex])!=readAxis[i])supportEqual=false;
                const auto& token=row[calcIndex];
                calcTokens.append(token.data(),static_cast<qsizetype>(token.size()));calcTokens.append('\0');
                if(statusPosition==loop->keys().end() || statusIndex>=row.size() || i>=currentStatuses.size() || i>=currentValues.size()) {++badCells;continue;}
                const auto& status=currentStatuses[i];
                if(row[statusIndex]!=status || (status!="incl" && status!="excl"))statusEqual=false;
                if(status=="excl") {++excluded;if(token!=".")++badCells;}
                else if(std::isfinite(currentValues[i])) {
                    ++available;
                    // FIRST numeric parsing accepts genuine zero; '.' is missing,
                    // never an available calculation reconstructed by later Open.
                    try {if(std::isfinite(crysta::parse_edi_number(token)))++numeric;else ++badCells;}
                    catch(const std::exception&) {++badCells;}
                } else {++missing;if(!std::isnan(currentValues[i]) || token!=".")++badCells;}
            }
        }
        check.require(supportEqual,stage+": FIRST-parsed original calc rows retain every measured-axis position");
        check.require(statusEqual,stage+": original persisted statuses agree with the actual current included/excluded rows");
        check.require(badCells==0 && numeric==available && available>0,stage+": actual available included calculations are finite numeric disk cells, retaining legitimate zero and excluded/uncomputed missing cells");
        fact(stage,{{"kind","original_persisted_calculation"},{"column_present",true},{"rows",static_cast<qint64>(loop->rows().size())},
            {"measured_rows",static_cast<qint64>(readAxis.size())},{"support_equal",supportEqual},{"status_equal",statusEqual},
            {"available_current_cells",static_cast<qint64>(available)},{"finite_numeric_disk_cells",static_cast<qint64>(numeric)},
            {"excluded_cells",static_cast<qint64>(excluded)},{"uncomputed_cells",static_cast<qint64>(missing)},{"invalid_or_missing_cells",static_cast<qint64>(badCells)},
            {"original_file_sha256",QString::fromLatin1(QCryptographicHash::hash(QByteArray::fromStdString(original),QCryptographicHash::Sha256).toHex())},
            {"raw_calc_cells_sha256",QString::fromLatin1(QCryptographicHash::hash(calcTokens,QCryptographicHash::Sha256).toHex())},
            {"qualification","literal original document cells, not the ordinary unhydrated live cache; no quantization oracle"}});
    }
    static void agreement(Checks& check,edi_app::ProjectViewModel& owner,const std::filesystem::path& destination,const QString& stage,double originalValue,double originalSu) {
        auto& current=*owner.assistantProject();
        const auto before=states(current);
        auto reopened=edi::load_project(destination.string());
        check.require(before==states(reopened),stage+": all current values/SUs/free/dependency states equal a genuine ordinary Open");
        int dependent=0;for(const auto& [path,state]:before)if(std::get<3>(state)!=edi::Dependence::Independent)++dependent;
        check.require(dependent>0,stage+": actual symmetry-dependent parameters were exercised");
        const auto target=adp(current);
        const auto& parameter=*target.parameter;
        const auto literalTarget=adp(reopened);
        fact(stage,{{"kind","current_literal_pairs"},{"original_value",originalValue},{"original_su",originalSu},
            {"current_value",parameter.value.get()},{"current_su",parameter.uncertainty.get()?QJsonValue(*parameter.uncertainty.get()):QJsonValue(QJsonValue::Null)},
            {"literal_value",literalTarget.parameter->value.get()},{"literal_su",literalTarget.parameter->uncertainty.get()?QJsonValue(*literalTarget.parameter->uncertainty.get()):QJsonValue(QJsonValue::Null)},
            {"all_parameter_states_equal",before==states(reopened)}});
        const auto keepsOriginalMeaning=[&](const edi::Parameter& value) {
            return std::isfinite(value.value.get()) && value.value.get()!=0 && std::signbit(value.value.get())==std::signbit(originalValue) &&
                value.uncertainty.get() && *value.uncertainty.get()>=std::abs(originalSu);
        };
        check.require(originalValue!=0 && keepsOriginalMeaning(parameter),stage+": FIRST Save preserves original nonzero/sign and conservative SU meaning in current model");
        check.require(keepsOriginalMeaning(*literalTarget.parameter),stage+": FIRST Save preserves original nonzero/sign and conservative SU meaning in literal disk model");
        QJsonArray rows{QJsonObject{{"path",QString::fromStdString(target.path)},{"value",parameter.value.get()},
            {"uncertainty",parameter.uncertainty.get()?QJsonValue(*parameter.uncertainty.get()):QJsonValue(QJsonValue::Null)},
            {"free",parameter.free.get()},{"dependence","independent"}}};
        check.require(parameter.dependence==edi::Dependence::Independent,stage+": original ADP remains independent");
        const auto projected=owner.assistantParameterText(rows);
        check.require(projected.size()==1,stage+": optional native spelling projection retains the original row");
        const auto row=projected.size()==1?projected[0].toObject():QJsonObject{};
        const bool spellingOffered=row.contains("file_value");
        fact(stage,{{"kind","optional_native_spelling"},{"offered",spellingOffered},
            {"current_value",parameter.value.get()},{"current_su",parameter.uncertainty.get()?QJsonValue(*parameter.uncertainty.get()):QJsonValue(QJsonValue::Null)},
            {"file_value",row.value("file_value")},{"file_su",row.value("file_su")},
            {"qualification",spellingOffered?"actual native publication offered spelling":"omitted by native owner; exact failed currentness guard not observed"}});
        if(spellingOffered) {
            check.require(row["file_value"].isString(),stage+": offered file_value is a numerical string");
            if(row["file_value"].isString())
                check.require(decimal(row["file_value"].toString().toStdString())==parameter.value.get(),stage+": file_value means the current numerical value");
            check.require(parameter.uncertainty.get().has_value() && row["file_su"].isString(),stage+": offered original nonzero SU has an actual file_su spelling");
            if(parameter.uncertainty.get() && row["file_su"].isString())
                check.require(decimal(row["file_su"].toString().toStdString())==*parameter.uncertainty.get(),stage+": file_su means the current numerical SU");
        }
        int structureFiles=0,experimentFiles=0;
        for(const auto& [path,text]:owner.savedFiles())if(path.starts_with("structures/") || path.starts_with("experiments/")) {
            if(path.starts_with("structures/"))++structureFiles;else ++experimentFiles;
            // The existing Text-edit owner parses this scratch projection. Its
            // computed categories need not be byte-identical to original disk.
            try {
                auto fromText=edi::project_with_file_text(current,path,text);
                check.require(states(fromText)==before && states(fromText)==states(reopened),stage+": original parser gives Text the same parameter meanings as current and literal disk");
                fact(stage,{{"kind","text_semantics"},{"path",QString::fromStdString(path)},
                    {"text_sha256",QString::fromLatin1(QCryptographicHash::hash(QByteArray::fromStdString(text),QCryptographicHash::Sha256).toHex())},
                    {"disk_sha256",QString::fromLatin1(QCryptographicHash::hash(QByteArray::fromStdString(bytes(destination/path)),QCryptographicHash::Sha256).toHex())},
                    {"parameter_meanings_equal",states(fromText)==before && states(fromText)==states(reopened)}});
            }catch(const std::exception& error) {check.require(false,stage+": original Text parser: "+QString::fromUtf8(error.what()));}
        }
        check.require(structureFiles==1 && experimentFiles==1,stage+": genuine structure and measured-dataset Text meanings were checked");
        check.require(states(current)==before,stage+": read-only Text/file spelling consumers do not change current pairs");
        check.require(current.experiment().computed_current(),stage+": successful Save leaves a current native calculation");
        check.require(current.experiment().data.has_value(),stage+": actual measured dataset retained");
        if(current.experiment().data) {
            const auto actual=current.experiment().data->intensity_calc.values();
            check.require(!actual.empty(),stage+": actual current calculated curve is nonempty");
            fact(stage,{{"kind","ordinary_open_cache"},{"calculated_live_rows",static_cast<qint64>(reopened.experiment().data?reopened.experiment().data->intensity_calc.size():0)},
                {"carried_calculation",reopened.experiment().carried_calculation},
                {"qualification","ordinary Open does not hydrate live calculated columns; original document is checked separately"}});
            persistedCalculation(check,current,reopened,destination,stage);
            // Recalculate only the independently reopened copy, never repair/refit current.
            reopened.refresh_calculated_pattern(edi::DueEstimates::Defer);
            check.require(reopened.experiment().computed_current() && reopened.experiment().data.has_value(),stage+": literal disk model recalculates normally");
            if(reopened.experiment().data)
                check.require(actual==reopened.experiment().data->intensity_calc.values(),stage+": current curve agrees with fresh native calculation of literal disk inputs");
        }
        fact(stage,{{"kind","agreement_stage_complete"},{"complete",true},{"checks_so_far",check.count},{"failures_so_far",static_cast<qint64>(check.errors.size())}});
    }
public:
    using QObject::QObject;
    Q_INVOKABLE QVariantMap pairFixedPoint() const {
        Checks check;
        struct Pair {const char* name;double value,su;bool exactControl=false;};
        // The first two are review126's literal pre/adopted pairs. The neighbors,
        // signs and powers of ten vary that boundary, not a scientific target.
        const std::vector<Pair> pairs{
            {"observed-before-save",0.49532748491751605,82.27336204291247},
            {"observed-adopted-half",0.5,83},
            {"below-half",std::nextafter(0.5,0.0),83},
            {"above-half",std::nextafter(0.5,1.0),83},
            {"negative-before-save",-0.49532748491751605,82.27336204291247},
            {"negative-half",-0.5,83},
            {"tenfold-boundary",4.9532748491751605,822.7336204291247},
            // Exact-decimal example declared in FIRST su_format.hpp, not a
            // spelling read back from the candidate or an unresolved fit.
            {"published-precise-pair",2.164,0.005,true}
        };
        for(const auto rule:{crysta::SuRule::Iucr19,crysta::SuRule::Iucr99})for(const auto& input:pairs) {
            const QString label=QString::fromLatin1(input.name)+":"+QString::fromLatin1(crysta::su_rule_name(rule));
            fact(label,{{"kind","pair_case_begin"},{"original_value",input.value},{"original_su",input.su}});
            try {
                const auto first=crysta::round_value_su(input.value,input.su,rule);
                const double value=decimal(first.value),su=decimal(first.su);
                const auto second=crysta::round_value_su(value,su,rule);
                fact(label,{{"kind","pair_fixed_point"},{"original_value",input.value},{"original_su",input.su},
                    {"first_value",QString::fromStdString(first.value)},{"first_su",QString::fromStdString(first.su)},
                    {"second_value",QString::fromStdString(second.value)},{"second_su",QString::fromStdString(second.su)}});
                check.require(value!=0 && std::signbit(value)==std::signbit(input.value),label+": original nonzero value and sign survive the FIRST spelling");
                check.require(su>=std::abs(input.su),label+": original SU is retained or conservatively rounded up");
                check.require(decimal(second.value)==value && decimal(second.su)==su,label+": serialize/parse is a numerical fixed point");
                check.require(first.value==second.value && first.su==second.su && first.bracket==second.bracket,label+": canonical numeric/SU spelling is stable after parse");
                if(input.exactControl)check.require(value==input.value && su==input.su,label+": declared precise pair retains its independent literal meaning");
                fact(label,{{"kind","pair_case_complete"},{"complete",true}});
            }catch(const std::exception& error) {
                fact(label,{{"kind","pair_case_exception"},{"complete",false},{"error",QString::fromUtf8(error.what())}});
                check.require(false,label+": "+QString::fromUtf8(error.what()));
            }
        }
        return check.result();
    }
    Q_INVOKABLE QVariantMap ordinarySaveAgreement() const {
        Checks check;
        const auto* reportedSource=crysta::build_commit();
        const std::string nativeSource=reportedSource?reportedSource:"";
        const bool parserCompatible=nativeSource=="79010b0c73ddec01abf80ce00037d138ec7c1b8d" || nativeSource=="c815d994d132fc31d10e26aaf4ac8385a965e518";
        fact(QStringLiteral("native_parser_abi"),{{"linked_source",QString::fromStdString(nativeSource)},
            {"linked_version",QString::fromLatin1(crysta::version())},{"compatible",parserCompatible},
            {"snapshot_header_sha256","fee5a54128a7359ba7dd98e675ba5957958ec46f17ed8733257ec03d8aaba29a"}});
        check.require(parserCompatible,QStringLiteral("UNREACHED: linked native revision has no proved compatible FIRST document-header snapshot"));
        if(!parserCompatible)return check.result();
        struct Input {const char* name;const char* token;double value,su;const char* rule;};
        const Input inputs[]{
            {"observed","0.49532748491751605(82.27336204291247)",0.49532748491751605,82.27336204291247,"iucr_99"},
            {"already-adopted-half","0.5(83.)",0.5,83,"iucr_99"},
            {"precise-control","2.164(0.005)",2.164,0.005,"iucr_99"},
            {"negative-observed","-0.49532748491751605(82.27336204291247)",-0.49532748491751605,82.27336204291247,"iucr_99"},
            {"tenfold-observed","4.9532748491751605(822.7336204291247)",4.9532748491751605,822.7336204291247,"iucr_99"},
            {"observed-other-rule","0.49532748491751605(82.27336204291247)",0.49532748491751605,82.27336204291247,"iucr_19"}
        };
        for(const auto& input:inputs)try {
            fact(QString::fromLatin1(input.name),{{"kind","ordinary_case_begin"},{"original_value",input.value},{"original_su",input.su},{"rule",input.rule}});
            QTemporaryDir temporary;
            if(!temporary.isValid())throw std::runtime_error("Run-owned temporary directory unavailable");
            const auto base=std::filesystem::path(temporary.path().toStdString());
            const auto fixture=std::filesystem::path(root().toStdString())/"tests/fixtures/background_estimate/projects/hrpt";
            std::filesystem::copy(fixture,base/"input",std::filesystem::copy_options::recursive);
            const auto structure=base/"input/structures/phase.edi";
            auto text=bytes(structure);const std::string original="Si Si a Biso 0 0 0 1 0.5";
            const auto position=text.find(original);
            if(position==std::string::npos || text.find(original,position+1)!=std::string::npos)
                throw std::runtime_error("Declared original one-atom fixture changed before numeric input construction");
            text.replace(position,original.size(),std::string("Si Si a Biso 0 0 0 1 ")+input.token);
            {std::ofstream output(structure,std::ios::binary);output<<text;if(!output)throw std::runtime_error("Isolated numeric input could not be written");}
            {std::ofstream output(base/"input/project.edi",std::ios::app);output<<"\n_su_format.rule "<<input.rule<<"\n";if(!output)throw std::runtime_error("Isolated declared SU rule could not be written");}
            edi_app::Session session(nullptr);
            if(!session.openProject(QUrl::fromLocalFile(QString::fromStdString((base/"input").string()))))
                throw std::runtime_error("Ordinary Open refused isolated numeric input: "+session.lastError().toStdString());
            const QPointer<edi_app::ProjectViewModel> owner=session.project();
            if(!owner || !idle(*owner))throw std::runtime_error("Original normal Open calculation never settled");
            const auto admitted=adp(*owner->assistantProject());
            check.require(owner->project().su_rule==input.rule,QString::fromLatin1(input.name)+": normal loader admitted the original declared SU rule");
            check.require(admitted.parameter->value.get()==input.value && admitted.parameter->uncertainty.get()==std::optional<double>(input.su),QString::fromLatin1(input.name)+": normal loader admitted exact declared fixture pair");
            const auto destination=base/"saved";
            const bool savedAs=session.saveAs(QUrl::fromLocalFile(QString::fromStdString(destination.string())));
            check.require(savedAs,QString::fromLatin1(input.name)+": genuine Session SaveAs succeeds: "+session.lastError());
            if(!savedAs || !owner || session.project()!=owner || !idle(*owner))throw std::runtime_error("SaveAs owner/readiness unavailable; agreement entrance unreached");
            agreement(check,*owner,destination,QString::fromLatin1(input.name)+":SaveAs",input.value,input.su);
            const auto savedPairs=states(*owner->assistantProject());
            const bool saved=session.save();
            check.require(saved,QString::fromLatin1(input.name)+": genuine subsequent Session Save succeeds: "+session.lastError());
            if(!saved || !owner || session.project()!=owner || !idle(*owner))throw std::runtime_error("Save owner/readiness unavailable; agreement entrance unreached");
            check.require(states(*owner->assistantProject())==savedPairs,QString::fromLatin1(input.name)+": a second ordinary Save cannot advance the already-adopted numerical pairs");
            agreement(check,*owner,destination,QString::fromLatin1(input.name)+":Save",input.value,input.su);
            session.closeProject();
            fact(QString::fromLatin1(input.name),{{"kind","ordinary_case_complete"},{"complete",true},{"checks_so_far",check.count},{"failures_so_far",static_cast<qint64>(check.errors.size())}});
        }catch(const std::exception& error) {fact(QString::fromLatin1(input.name),{{"kind","ordinary_case_exception"},{"complete",false},{"error",QString::fromUtf8(error.what())}});check.require(false,QString::fromLatin1(input.name)+": "+QString::fromUtf8(error.what()));}
        return check.result();
    }
};
static void registerSaveNumericFixedPointProof() {
    qmlRegisterSingletonType<SaveNumericFixedPointProof>("SaveNumericAcceptance",1,0,"SaveNumericProof",
        [](QQmlEngine*,QJSEngine*)->QObject* {return new SaveNumericFixedPointProof;});
}
Q_COREAPP_STARTUP_FUNCTION(registerSaveNumericFixedPointProof)
#include "test_e11_t5_save_numeric_fixed_point.moc"
