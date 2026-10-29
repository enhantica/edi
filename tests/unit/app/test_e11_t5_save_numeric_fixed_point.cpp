// SPDX-License-Identifier: BSD-3-Clause
// Independent persistence properties; no second formatter or fitted reference.
#include <crysta/su_format.hpp>
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "project_view_model.hpp"
#include "session.hpp"
#include <QCoreApplication>
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
struct Checks {
    QStringList errors;
    int count=0;
    void require(bool value,const QString& message) {++count;if(!value)errors.push_back(message);}
    QVariantMap result() const {return {{"ok",errors.isEmpty()},{"checks",count},{"error",errors.join(QStringLiteral("; "))}};}
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
        check.require(projected.size()==1 && projected[0].toObject().value("file_value").isString(),stage+": current optional native file spelling is genuinely published");
        if(projected.size()==1 && projected[0].toObject().value("file_value").isString()) {
            const auto row=projected[0].toObject();
            check.require(decimal(row["file_value"].toString().toStdString())==parameter.value.get(),stage+": file_value means the current numerical value");
            check.require(parameter.uncertainty.get().has_value() && row["file_su"].isString(),stage+": original nonzero SU has an actual file_su spelling");
            if(parameter.uncertainty.get() && row["file_su"].isString())
                check.require(decimal(row["file_su"].toString().toStdString())==*parameter.uncertainty.get(),stage+": file_su means the current numerical SU");
        }
        int structureFiles=0,experimentFiles=0;
        for(const auto& [path,text]:owner.savedFiles())if(path.starts_with("structures/") || path.starts_with("experiments/")) {
            if(path.starts_with("structures/"))++structureFiles;else ++experimentFiles;
            check.require(text==bytes(destination/path),stage+": original Text source equals original disk structure/experiment bytes");
        }
        check.require(structureFiles==1 && experimentFiles==1,stage+": genuine structure and calculated-dataset Text sources were checked");
        check.require(states(current)==before,stage+": read-only Text/file spelling consumers do not change current pairs");
        check.require(current.experiment().computed_current(),stage+": successful Save leaves a current native calculation");
        check.require(current.experiment().data.has_value(),stage+": actual measured dataset retained");
        if(current.experiment().data) {
            const auto actual=current.experiment().data->intensity_calc.values();
            check.require(!actual.empty(),stage+": actual current calculated curve is nonempty");
            check.require(reopened.experiment().data.has_value() && !reopened.experiment().data->intensity_calc.empty(),stage+": original saved file actually carries calculated values");
            if(reopened.experiment().data)
                check.require(reopened.experiment().data->intensity_calc.size()==actual.size(),stage+": literal saved/current curves have the same measured support");
            // Recalculate only the independently reopened copy, never repair/refit current.
            reopened.refresh_calculated_pattern(edi::DueEstimates::Defer);
            check.require(reopened.experiment().computed_current() && reopened.experiment().data.has_value(),stage+": literal disk model recalculates normally");
            if(reopened.experiment().data)
                check.require(actual==reopened.experiment().data->intensity_calc.values(),stage+": current curve agrees with fresh native calculation of literal disk inputs");
        }
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
        try {
            for(const auto rule:{crysta::SuRule::Iucr19,crysta::SuRule::Iucr99})for(const auto& input:pairs) {
                const auto first=crysta::round_value_su(input.value,input.su,rule);
                const double value=decimal(first.value),su=decimal(first.su);
                const auto second=crysta::round_value_su(value,su,rule);
                const QString label=QString::fromLatin1(input.name)+":"+QString::fromLatin1(crysta::su_rule_name(rule));
                check.require(value!=0 && std::signbit(value)==std::signbit(input.value),label+": original nonzero value and sign survive the FIRST spelling");
                check.require(su>=std::abs(input.su),label+": original SU is retained or conservatively rounded up");
                check.require(decimal(second.value)==value && decimal(second.su)==su,label+": serialize/parse is a numerical fixed point");
                check.require(first.value==second.value && first.su==second.su && first.bracket==second.bracket,label+": canonical numeric/SU spelling is stable after parse");
                if(input.exactControl)check.require(value==input.value && su==input.su,label+": declared precise pair retains its independent literal meaning");
            }
        }catch(const std::exception& error) {check.require(false,QString::fromUtf8(error.what()));}
        return check.result();
    }
    Q_INVOKABLE QVariantMap ordinarySaveAgreement() const {
        Checks check;
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
        }catch(const std::exception& error) {check.require(false,QString::fromLatin1(input.name)+": "+QString::fromUtf8(error.what()));}
        return check.result();
    }
};
static void registerSaveNumericFixedPointProof() {
    qmlRegisterSingletonType<SaveNumericFixedPointProof>("SaveNumericAcceptance",1,0,"SaveNumericProof",
        [](QQmlEngine*,QJSEngine*)->QObject* {return new SaveNumericFixedPointProof;});
}
Q_COREAPP_STARTUP_FUNCTION(registerSaveNumericFixedPointProof)
#include "test_e11_t5_save_numeric_fixed_point.moc"
