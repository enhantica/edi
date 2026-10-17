// Tests-owned real Session/VM component. No Main QML or alternate controller.
#include "fixture_services.hpp"
#include "session.hpp"
#include "assistant_view_model.hpp"
#ifdef EDI_TEST_WORKFLOW_CONTEXT
#include "codex_agent.hpp"
#endif
#include "engine_setup.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/selectors.hpp"
#include "edi/calculation.hpp"
#include "fit_view_model.hpp"
#include "experiment_view_model.hpp"
#include "pattern_model.hpp"
#include <QCryptographicHash>
#include <QJsonDocument>
#include <QAbstractItemModel>
#include <QEvent>
#include <QDesktopServices>
#include <QScopeGuard>
#include <QStringList>
#include "edi/assistant_files.hpp"
#include "edi/assistant_limits.hpp"
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QGuiApplication>
#ifdef EDI_TEST_WORKFLOW_CONTEXT
#include <QMetaProperty>
#endif
#include <QPointer>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QUuid>
#include <QtQml/qqmlextensionplugin.h>

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

class OwnedUrlRecorder final : public QObject {
    Q_OBJECT
public:
    Array urls;
    int usage_changes=0;
public slots:
    void changed() { ++usage_changes; }
    void record(const QUrl& url) { urls.push_back(url.toString(QUrl::FullyEncoded)); }
};
namespace {
void drain(int milliseconds=30) {
    QElapsedTimer timer;timer.start();
    do {QCoreApplication::processEvents(QEventLoop::AllEvents,1);} while(timer.elapsed()<milliseconds);
}
Array rows(edi_app::RowTableModel* model) {
    Array result;
    for(int row=0;row<model->count();++row) {
        Object value;
        for(const auto& name:model->roleNames())
            value[QString::fromUtf8(name)]=QJsonValue::fromVariant(model->get(row,QString::fromUtf8(name)));
        result.push_back(value);
    }
    return result;
}
}
// Test-only passive original core metadata. No ownership/state is changed here.
Object background285_image(edi_app::ProjectViewModel* owner) {
    Object image;if(!owner)return image;
    const auto pointer=[](const void* p) {return QString::number(static_cast<qulonglong>(reinterpret_cast<quintptr>(p)),16);};
    const auto number=[](const std::optional<double>& v)->QJsonValue {return v?QJsonValue(*v):QJsonValue(QJsonValue::Null);};
    Array banks,parameters;
    auto* project=owner->assistantProject();
    for(const auto& entry:edi::parameter_entries(*project)) {
        const auto& p=*entry.parameter;Object spec;
        if(p.spec) {
            Array edi_names,cif_names;
            for(const auto* name:p.spec->edi_names)edi_names.push_back(QString::fromUtf8(name));
            for(const auto* name:p.spec->cif_names)cif_names.push_back(QString::fromUtf8(name));
            spec={{"identity",pointer(p.spec)},{"category",QString::fromUtf8(p.spec->category)},
                {"name",QString::fromUtf8(p.spec->name)},{"units",QString::fromUtf8(p.spec->units)},
                {"description",QString::fromUtf8(p.spec->description)},
                {"display_name",QString::fromUtf8(p.spec->display_name)},
                {"display_units",QString::fromUtf8(p.spec->display_units)},
                {"latex_name",QString::fromUtf8(p.spec->latex_name)},
                {"latex_units",QString::fromUtf8(p.spec->latex_units)},
                {"minimum",p.spec->range.min},{"maximum",p.spec->range.max},
                {"edi_names",edi_names},{"cif_names",cif_names}};
        }
        parameters.push_back(Object{{"path",QString::fromStdString(entry.path)},
            {"value",p.value.get()},{"free",p.free.get()},{"uncertainty",number(p.uncertainty.get())},
            {"start_value",number(p.start_value.get())},{"start_uncertainty",number(p.start_uncertainty.get())},
            {"dependence",static_cast<int>(p.dependence)},{"spec",spec}});
    }
    for(const auto& bank:project->experiments) {
        Array points,excluded,links,axis,measured,sigma;Object raw;
        for(const auto& row:bank->background)points.push_back(Object{
            {"id",QString::fromStdString(row->id.value())},{"identity",pointer(row.get())},
            {"position",row->position.get()},{"value",row->intensity.value.get()},
            {"free",row->intensity.free.get()},{"uncertainty",number(row->intensity.uncertainty.get())},
            {"start_value",number(row->intensity.start_value.get())},
            {"start_uncertainty",number(row->intensity.start_uncertainty.get())},
            {"dependence",static_cast<int>(row->intensity.dependence)},
            {"spec_identity",pointer(row->intensity.spec)}});
        for(const auto& row:bank->excluded_regions)excluded.push_back(Array{row->first.get(),row->second.get()});
        for(const auto& row:bank->linked_structures)links.push_back(Array{
            QString::fromStdString(row->structure_id.value()),row->enabled.get(),row->scale.value.get()});
        if(bank->data) {
            const auto& data=*bank->data;
            if(data.two_theta)for(auto x:*data.two_theta)axis.push_back(x);
            if(data.time_of_flight)for(auto x:*data.time_of_flight)axis.push_back(x);
            for(auto x:data.intensity_meas.get())measured.push_back(x);
            for(auto x:data.intensity_meas_su.get())sigma.push_back(x);
            raw={{"identity",pointer(&data)},{"aggregate",QString::number(static_cast<qulonglong>(data.written.value()))},
                {"two_theta",QString::number(static_cast<qulonglong>(data.two_theta.written()))},
                {"time_of_flight",QString::number(static_cast<qulonglong>(data.time_of_flight.written()))},
                {"intensity",QString::number(static_cast<qulonglong>(data.intensity_meas.written()))},
                {"sigma",QString::number(static_cast<qulonglong>(data.intensity_meas_su.written()))}};
        }
        banks.push_back(Object{{"id",QString::fromStdString(bank->name.value())},
            {"identity",pointer(bank.get())},{"calculation_only",bank->calculation_only},
            {"has_data",bank->data.has_value()},{"background_type",QString::fromStdString(bank->background_type)},
            {"origin",number(bank->background_origin)},{"x_min",number(bank->background_x_min)},
            {"x_max",number(bank->background_x_max)},{"anchors",points},
            {"axis",axis},{"measured",measured},{"sigma",sigma},{"raw_identity",raw},
            {"exclusions",excluded},{"links",links},{"weight",bank->dataset_weight}});
    }
    image={{"owner",pointer(owner)},{"core",pointer(project)},{"banks",banks},{"parameters",parameters},
        {"mode",QString::fromStdString(project->fitting_mode)},{"path",owner->path()},
        {"selected_index",owner->currentExperimentIndex()},
        {"can_undo",owner->canUndo()}};
    return image;
}

#ifdef EDI_TEST_WORKFLOW_CONTEXT
// Test-owned public caller in the existing native target. No production member
// access. Its app-context observers remain alive if the genuine facade dies.
struct PublicTransport304 {
    using Agent=edi_app::CodexAgent;
    std::unique_ptr<Agent> facade;
    std::vector<QMetaObject::Connection> connections;
    Object facts;
    Array events;
    QString root,trigger,action;
    bool enabled=false,armed=false,closing=false;
    int depth=0;
    QElapsedTimer operation;
    static QString identity(QObject* p) {
        return QString::number(static_cast<qulonglong>(reinterpret_cast<quintptr>(p)),16);
    }
    void disconnect() {
        for(const auto& connection:connections)QObject::disconnect(connection);
        connections.clear();
    }
    ~PublicTransport304() {closing=true;disconnect();facade.reset();}
    QString targetSignal() const {return trigger.startsWith("failed-")?QStringLiteral("failed"):trigger;}
    void boundary(const QString& name,const QString& label,QPointer<Agent> original,Object extra={}) {
        if(closing)return;
        if(events.size()>=32) {facts["observer_overflow"]=true;return;}
        ++depth;
        const auto leave=qScopeGuard([&]{--depth;});
        Object record{{"signal",name},{"label",label},{"depth",depth},
            {"receiver",identity(original.data())},{"original_alive_at_entry",!original.isNull()},
            {"elapsed_operation_ms",operation.isValid()?static_cast<double>(operation.elapsed()):-1.}};
        for(auto i=extra.begin();i!=extra.end();++i)record[i.key()]=i.value();
        const int index=events.size();events.push_back(record);
        if(label=="A" && armed && name==targetSignal()) {
            armed=false;facts["boundary_reached"]=true;facts["boundary_event_index"]=index;
            facts["boundary_in_callback_depth"]=depth;
            if(facade.get()!=original.data()) {facts["observer_error"]="original receiver not current fixture-owned facade";return;}
            if(action=="restart") {
                disconnect();original->retire();
                attach("B",false);
                facts["replacement_start_returned"]=facade->start(Agent::executable(),root+"/B");
            } else {
                disconnect();facade.reset();
                if(action=="recreate") {
                    attach("B",true);
                    facts["replacement_start_returned"]=facade->start(Agent::executable(),root+"/B");
                }
            }
            auto after=events[index].toObject();
            after["original_alive_after_action"]=!original.isNull();
            after["active_receiver_after_action"]=identity(facade.get());
            after["returned_from_action_in_same_callback"]=true;
            events[index]=after;
        }
    }
    void initialize(const QString& label,QPointer<Agent> original) {
        if(!original)return;
        const Object params{{"clientInfo",Object{{"name","independent-public-"+label},{"version","1"}}},
                            {"capabilities",Object{{"experimentalApi",true}}}};
        if(label=="A" && trigger=="failed-deadline") {
            operation.start();original->beginOperation(100,100);
            facts["declared_total_ms"]=100;facts["declared_idle_ms"]=100;
        }
        QString id;
        if(label=="A" && trigger=="before-write") {
            id=original->request("initialize",params,[this,original](const QString& request_id) {
                facts["original_prepared_id"]=request_id;
                boundary("before-write","A",original,Object{{"request_id",request_id},{"method","initialize"}});
                return true; // The callback's original facade may have been destroyed.
            });
        } else id=original->request("initialize",params);
        auto issued=facts.value("issued").toObject();issued[label]=id;facts["issued"]=issued;
    }
    void attach(const QString& label,bool create) {
        if(create)facade=std::make_unique<Agent>();
        QPointer<Agent> original=facade.get();
        auto* context=QCoreApplication::instance();
        connections.push_back(QObject::connect(original.data(),&Agent::started,context,[=,this] {
            boundary("started",label,original);
            if(original && (label=="B" || trigger!="started"))initialize(label,original);
        },Qt::DirectConnection));
        connections.push_back(QObject::connect(original.data(),&Agent::response,context,
            [=,this](const QString& id,const QString& method,const Object& envelope) {
                boundary("response",label,original,Object{{"request_id",id},{"method",method},{"envelope",envelope}});
            },Qt::DirectConnection));
        connections.push_back(QObject::connect(original.data(),&Agent::event,context,
            [=,this](const QString& method,const Object& params) {
                boundary("event",label,original,Object{{"method",method},{"params",params}});
            },Qt::DirectConnection));
        connections.push_back(QObject::connect(original.data(),&Agent::failed,context,
            [=,this](const QString& explanation) {
                boundary("failed",label,original,Object{{"explanation",explanation}});
            },Qt::DirectConnection));
        connections.push_back(QObject::connect(original.data(),&Agent::serverRequest,context,
            [=,this](const QJsonValue& id,const QString& method,const Object&) {
                boundary("serverRequest",label,original,Object{{"original_id",id},{"method",method}});
            },Qt::DirectConnection));
    }
    Object start(const Object& input,const QString& temporary) {
        if(enabled)throw std::invalid_argument("one original public facade case per probe process");
        trigger=input["trigger"].toString();action=input["action"].toString();
        if(!QStringList{"started","response","event","failed-record","failed-eof","failed-deadline","before-write"}.contains(trigger)
            || !QStringList{"destroy","recreate","restart"}.contains(action))
            throw std::invalid_argument("finite public transport boundary/action required");
        const auto executable=Agent::executable();
        if(executable!=qEnvironmentVariable("EDI_CODEX_DEVELOPMENT_EXECUTABLE") || !QFileInfo(executable).isAbsolute()
            || !QFileInfo(executable).isExecutable())throw std::invalid_argument("actual owned absolute executable required");
        root=temporary+"/public-transport304";
        if(!QDir().mkpath(root+"/A") || !QDir().mkpath(root+"/B"))throw std::runtime_error("owned original workspaces unavailable");
        enabled=true;armed=true;attach("A",true);
        facts={{"trigger",trigger},{"action",action},{"original_receiver",identity(facade.get())},
               {"owned_executable",executable},{"workspace_A",root+"/A"},{"workspace_B",root+"/B"}};
        facts["initial_start_returned"]=facade->start(executable,root+"/A");
        return {{"armed",true}};
    }
    Object snapshot() const {
        Object result=facts;result["events"]=events;result["active_receiver"]=identity(facade.get());
        result["in_callback_now"]=depth;return result;
    }
};
#endif

int main(int argc,char** argv) {
    const bool codex_mode=argc==2 && QByteArray(argv[1])=="--codex";
    QTemporaryDir storage;
    if(!storage.isValid())return 97;
    qputenv("XDG_DATA_HOME",storage.path().toUtf8());
    qputenv("XDG_CONFIG_HOME",storage.path().toUtf8());
    QGuiApplication app(argc,argv);
    QGuiApplication::setOrganizationName("EdiIndependentAcceptance");
    QGuiApplication::setApplicationName("vm-"+QUuid::createUuid().toString(QUuid::WithoutBraces));
    edi_app::use_fresh_settings();
    FixtureServices fixture; // Outlives actual Session/VM/native callbacks and teardown.
    const auto make_session=[&]() -> std::unique_ptr<edi_app::Session> {
        if(codex_mode)return std::make_unique<edi_app::Session>(nullptr);
        return std::make_unique<edi_app::Session>(fixture.dependencies,nullptr);
    };
    auto session=make_session();
#ifdef EDI_TEST_WORKFLOW_CONTEXT
    PublicTransport304 public_transport304;
#endif
    OwnedUrlRecorder report_urls;
    const QStringList observed_schemes{QStringLiteral("file"),QStringLiteral("http"),
        QStringLiteral("https"),QStringLiteral("javascript"),QStringLiteral("data"),
        QStringLiteral("report-invalid")};
    if(codex_mode)for(const auto& scheme:observed_schemes)QDesktopServices::setUrlHandler(scheme,&report_urls,"record");
    const auto restore_urls=qScopeGuard([&] {
        if(codex_mode)for(const auto& scheme:observed_schemes)QDesktopServices::unsetUrlHandler(scheme);
    });

    const auto history=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)+"/assistant/history.json";
    int model_changes=0;
#ifdef EDI_TEST_SELECTED_FILES
    Array retired_selections;
#endif
    bool arm_notice_barrier=false;
    QString notice_intent;
    Object notice_barrier;
    auto observe=[&] {
        QObject::connect(session.get(),&edi_app::Session::projectChanged,session.get(),[&] {
            if(!arm_notice_barrier || !session || !session->hasProject())return;
            arm_notice_barrier=false;
            notice_barrier={{"intent",notice_intent},{"project_present",true},
                {"fresh_save_as",session->needsFreshSaveAs()},
                {"project_name",session->project()->name()}};
            // Read only after real public project publication; never fault terminal retention.
            try {
                QFile retained(history);
                if(!retained.open(QIODevice::ReadOnly))throw std::runtime_error("actual retained archive unreadable");
                const auto bytes=retained.readAll();retained.close();
                notice_barrier["retained_rows"]=decode(bytes);
                notice_barrier["retained_sha256"]=QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex());
                const auto backup=history+".post-adoption-preserved";
                if(!QFile::rename(history,backup) || !QDir().mkpath(history))
                    throw std::runtime_error("owned post-adoption archive barrier unavailable");
                QFile saved(backup);if(!saved.open(QIODevice::ReadOnly))
                    throw std::runtime_error("owned retained archive backup unreadable");
                notice_barrier["preserved_sha256"]=QString::fromLatin1(QCryptographicHash::hash(saved.readAll(),QCryptographicHash::Sha256).toHex());
                notice_barrier["is_directory"]=QFileInfo(history).isDir();
            } catch(const std::exception& error) {
                notice_barrier["observer_error"]=QString::fromUtf8(error.what());
            }
        });
#ifdef EDI_TEST_SELECTED_FILES
        QObject::connect(session->assistant(), &edi_app::AssistantViewModel::fileSelectionRetired,
            session.get(), [&](const QString& id){retired_selections.push_back(id);});
#endif
        if(codex_mode && session->assistant()->metaObject()->indexOfSignal("usageChanged()")>=0)
            QObject::connect(session->assistant(),SIGNAL(usageChanged()),&report_urls,SLOT(changed()));
        QObject::connect(session->assistant()->messages(),&edi_app::RowTableModel::countChanged,
            session.get(),[&]{++model_changes;});
    };
    observe();
    auto archive=[&]()->Object {
        QFile file(history);QByteArray bytes;
        if(QFileInfo(history).isFile() && file.open(QIODevice::ReadOnly))bytes=file.readAll();
        return {{"exists",QFileInfo::exists(history)},{"is_file",QFileInfo(history).isFile()},
            {"is_directory",QFileInfo(history).isDir()},{"bytes",static_cast<double>(bytes.size())},
            {"sha256",QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex())}};
    };
    bool native_science_enabled=false;
    bool background285_enabled=false;
    bool named_empty_observation=false;
    QPointer<edi_app::ProjectViewModel> named_empty_owner;
    const void* named_empty_core=nullptr;
    Object terminal_selection_observer;
    bool terminal_selection_armed=false;
    QMetaObject::Connection terminal_selection_connection;
    Object retirement_observer;
    bool retirement_armed=false;
    QMetaObject::Connection retirement_connection;
    Object publication_observer;
    QPointer<edi_app::ProjectViewModel> publication_owner;
    bool publication_armed=false;
    QMetaObject::Connection publication_connection;
    const auto publication_values=[](edi_app::ProjectViewModel* owner) {
        Object facts;if(!owner)return facts;
        const auto& project=owner->project();Array parameters,patterns;
        edi::Project captured(project);
        for(const auto& entry:edi::parameter_entries(captured)) {
            const auto& parameter=*entry.parameter;
            parameters.push_back(Object{{"path",QString::fromStdString(entry.path)},
                {"value",parameter.value.get()},{"free",parameter.free.get()},
                {"uncertainty",parameter.uncertainty?QJsonValue(*parameter.uncertainty):QJsonValue()}});
        }
        for(auto* experiment:owner->experimentModels()) {
            auto* pattern=experiment->pattern();Array actual;
            for(int row=0;row<pattern->rowCount();++row) {
                const auto index=pattern->index(row);
                actual.push_back(Array{QJsonValue::fromVariant(pattern->data(index,edi_app::PatternModel::IntensityCalcRole)),
                    QJsonValue::fromVariant(pattern->data(index,edi_app::PatternModel::IntensityBkgRole)),
                    QJsonValue::fromVariant(pattern->data(index,edi_app::PatternModel::ResidualRole))});
            }
            patterns.push_back(Object{{"rows",pattern->rowCount()},{"stale",pattern->stale()},
                {"sha256",QString::fromLatin1(QCryptographicHash::hash(encode(actual),QCryptographicHash::Sha256).toHex())}});
        }
        const auto optional_bool=[](const std::optional<bool>& value) {
            return value?QJsonValue(*value):QJsonValue(QJsonValue::Null);
        };
        facts={{"parameters",parameters},{"patterns",patterns},{"path",QString::fromStdString(project.path)},
            {"report_pdf",optional_bool(project.report_pdf)},
            {"report_html_offline",optional_bool(project.report_html_offline)},
            {"can_undo",owner->canUndo()},{"calculating",owner->calculating()},
            {"error",owner->lastError()},{"scan",owner->scan()},
            {"selected_experiment",owner->currentExperimentIndex()},
            {"fit_running",owner->fit()->running()},{"can_reset",owner->fit()->canReset()},
            {"scan_processed",owner->fit()->scanProcessed()},{"scan_fitted",owner->fit()->scanFitted()}};
        return facts;
    };
    // Opt-in real public VM callbacks. Receipts outlive original Session/receiver.
    Object callback319;
    bool callback319_armed=false;
    int callback319_depth=0;
    QMetaObject::Connection callback319_model,callback319_state,callback319_error;
    auto snapshot=[&]()->Object {
        if(!session)return {{"alive",false}};
        auto* vm=session->assistant();Object project;
#ifdef EDI_TEST_WORKFLOW_CONTEXT
        const auto* meta=vm->metaObject();
        const auto catalog_index=meta->indexOfProperty("skills");
        const auto selection_index=meta->indexOfProperty("selectedSkill");
        const auto catalog_property=catalog_index>=0 ? meta->property(catalog_index) : QMetaProperty();
        const auto selection_property=selection_index>=0 ? meta->property(selection_index) : QMetaProperty();
        auto* catalog=catalog_property.isValid()
            ? vm->property("skills").value<edi_app::RowTableModel*>() : nullptr;
#endif
        if(session->project()) {
            const auto& value=session->project()->project();Array parameters;
            edi::Project captured(value);
            for(const auto& entry:edi::parameter_entries(captured)) {
                const auto& parameter=*entry.parameter;
                Object observed{{"path",QString::fromStdString(entry.path)},
                    {"value",parameter.value.get()},{"free",parameter.free.get()},
                    {"uncertainty",parameter.uncertainty?QJsonValue(*parameter.uncertainty):QJsonValue()}};
                if(codex_mode) {
                    observed["independent"]=parameter.dependence==edi::Dependence::Independent;
                    observed["refinable"]=entry.refinable;observed["fittable"]=entry.fittable;
                    observed["used_by_profile"]=entry.used_by_profile;
                }
                parameters.push_back(observed);
            }
            if(codex_mode) {
                auto* fit=session->project()->fit();
                project["native_observer"]=Object{
                    {"can_undo",session->project()->canUndo()},
                    {"edits_at",QString::number(edi::work_stamps(value).edits_at)},
                    {"fit_running",fit->running()},{"fit_available",fit->available()},
                    {"fit_unavailable_reason",fit->unavailableReason()},
                    {"fit_outcome",fit->outcome()},{"fit_status",fit->status()},
                    {"fit_can_undo",fit->canUndo()},{"fit_results",rows(fit->results())},
                    {"record",Object{{"kind",QString::fromStdString(value.fit_result.result_kind)},
                        {"exit_reason",QString::fromStdString(value.fit_result.exit_reason)},
                        {"success",value.fit_result.success},{"iterations",value.fit_result.iterations},
                        {"reduced_chi_square",value.fit_result.reduced_chi_square}}}};
            }
            Object science;
            if(codex_mode && native_science_enabled) {
                Array structures,aliases,constraints,calculations;
                for(const auto& structure:value.structures) {
                    Array sites,expanded;
                    for(const auto& site:structure->atom_sites)sites.push_back(Object{
                        {"id",QString::fromStdString(site->id.value())},
                        {"type_symbol",QString::fromStdString(site->type_symbol.value())},
                        {"wyckoff",QString::fromStdString(site->wyckoff_letter.value())},
                        {"adp_type",QString::fromStdString(site->adp_type.value())},
                        {"fractional",Array{site->fract_x.value.get(),site->fract_y.value.get(),site->fract_z.value.get()}},
                        {"occupancy",site->occupancy.value.get()},{"adp_iso",site->adp_iso.value.get()}});
                    const bool current=structure->geometry_current();
                    if(current) {
                        const auto& atoms=structure->geometry.expanded_atom_sites;
                        for(std::size_t i=0;i<atoms.size();++i)expanded.push_back(Object{
                            {"site_id",QString::fromStdString(atoms.atom_site_id[i])},
                            {"fractional",Array{atoms.fract_x[i],atoms.fract_y[i],atoms.fract_z[i]}},
                            {"occupancy",atoms.occupancy[i]},{"u_iso",atoms.u_iso[i]}});
                    }
                    structures.push_back(Object{{"id",QString::fromStdString(structure->name.value())},
                        {"space_group",QString::fromStdString(structure->space_group.name_h_m.value())},
                        {"sites",sites},{"geometry_current",current},{"expanded",expanded}});
                }
                for(const auto& alias:value.aliases)aliases.push_back(Object{
                    {"id",QString::fromStdString(alias->id.value())},
                    {"parameter_unique_name",QString::fromStdString(alias->parameter_unique_name.value())}});
                for(const auto& constraint:value.constraints)constraints.push_back(Object{
                    {"id",QString::fromStdString(constraint->id.value())},
                    {"expression",QString::fromStdString(constraint->expression.value())},
                    {"enabled",constraint->enabled.get()}});
                for(const auto& experiment:value.experiments)calculations.push_back(Object{
                    {"name",QString::fromStdString(experiment->name.value())},
                    {"current",experiment->computed_current()},
                    {"calculation_only",experiment->calculation_only},
                    {"peak_profile",QString::fromStdString(edi::effective_peak_type(*experiment))},
                    {"wavelength",experiment->instrument.setup_wavelength
                        ?QJsonValue(experiment->instrument.setup_wavelength->value.get()):QJsonValue()}});
                Array pattern_errors;
                for (auto* model : session->project()->experimentModels())
                    pattern_errors.push_back(Object{{"name",model->name()},
                        {"calculation_error",model->pattern()->calculationError()}});
                science={{"structures",structures},{"aliases",aliases},{"constraints",constraints},
                    {"calculations",calculations},{"calculating",session->project()->calculating()},
                    {"owner_identity",QString::number(static_cast<qulonglong>(reinterpret_cast<quintptr>(session->project())),16)},
                    {"project_last_error",session->project()->lastError()},
                    {"session_last_error",session->lastError()},
                    {"pattern_errors",pattern_errors},{"session_warnings",rows(session->loadWarnings())}};
            }
            const auto native_observer=project.value("native_observer");
            project={{"parameters",parameters},{"mode",QString::fromStdString(value.fitting_mode)},
                {"objective",value.fit_result.objective_value}};
            if(codex_mode)project["native_observer"]=native_observer;
            if(codex_mode && named_empty_observation) {
                const auto text=[](const std::optional<std::string>& v) {
                    return v?QJsonValue(QString::fromStdString(*v)):QJsonValue(QJsonValue::Null);
                };
                const auto boolean=[](const std::optional<bool>& v) {
                    return v?QJsonValue(*v):QJsonValue(QJsonValue::Null);
                };
                project["empty_completion_observer"]=Object{
                    {"owner_identity",QString::number(static_cast<qulonglong>(reinterpret_cast<quintptr>(session->project())),16)},
                    {"core_identity",QString::number(static_cast<qulonglong>(reinterpret_cast<quintptr>(&value)),16)},
                    {"same_owner",named_empty_owner && session->project()==named_empty_owner},
                    {"same_core",named_empty_owner && session->project()==named_empty_owner && &value==named_empty_core},
                    {"structures",static_cast<int>(value.structures.size())},
                    {"experiments",static_cast<int>(value.experiments.size())},
                    {"metadata",Object{{"name",QString::fromStdString(value.metadata.name)},
                        {"title",session->project()->title()},{"description",session->project()->description()},
                        {"authors",session->project()->authors()},
                        {"created",QString::fromStdString(value.metadata.created)}}},
                    {"settings",Object{{"su_rule",session->project()->suRule()},
                        {"html",boolean(value.report_html)},{"pdf",boolean(value.report_pdf)},
                        {"cif",boolean(value.report_cif)},{"html_offline",boolean(value.report_html_offline)},
                        {"excluded",text(value.report_excluded)},{"x_axis",text(value.pattern_x_axis)},
                        {"correlation_threshold",value.correlation_threshold?QJsonValue(*value.correlation_threshold):QJsonValue(QJsonValue::Null)}}},
                    {"path",session->project()->path()},
                    {"metadata_path",QString::fromStdString(value.metadata.path)}};
            }
            if(codex_mode && native_science_enabled)project["science_observer"]=science;
            if(codex_mode && background285_enabled)project["background285"]=background285_image(session->project());
#ifdef EDI_TEST_WORKFLOW_CONTEXT
            if(codex_mode) {
                Array experiments;
                for(const auto& experiment:value.experiments) {
                    Array axis,intensity,sigma,exclusions,phases;
                    if(experiment->data) {
                        const auto& data=*experiment->data;
                        if(const auto values=data.two_theta.get())
                            for(const auto item:*values)axis.push_back(item);
                        for(const auto item:data.intensity_meas.get())intensity.push_back(item);
                        for(const auto item:data.intensity_meas_su.get())sigma.push_back(item);
                    }
                    for(const auto& region:experiment->excluded_regions)
                        exclusions.push_back(Array{region->first.get(),region->second.get()});
                    for(const auto& phase:experiment->linked_structures)
                        phases.push_back(QString::fromStdString(phase->structure_id.value()));
                    experiments.push_back(Object{{"name",QString::fromStdString(experiment->name)},
                        {"axis",axis},{"intensity",intensity},{"sigma",sigma},
                        {"exclusions",exclusions},{"phases",phases},{"weight",experiment->dataset_weight}});
                }
                project["host_snapshot"]=Object{{"name",session->project()->name()},
                    {"path",session->project()->path()},{"modified",session->project()->modified()},
                    {"experiments",experiments}};
            }
#endif
        }
        Object result{{"alive",true},{"connected",vm->connected()},{"state",vm->state()},
#ifdef EDI_TEST_SELECTED_FILES
            {"selected_files",rows(vm->selectedFiles())},{"retired_selections",retired_selections},
            {"project_present",session->project()!=nullptr},
#endif
#ifdef EDI_TEST_WORKFLOW_CONTEXT
            {"workflow_surface",Object{
                {"catalog_property",catalog_property.isValid() && catalog_property.isReadable()},
                {"catalog_readonly",catalog_property.isValid() && !catalog_property.isWritable()},
                {"catalog_constant",catalog_property.isValid() && catalog_property.isConstant()},
                {"selected_property",selection_property.isValid() && selection_property.isReadable()},
                {"selected_readonly",selection_property.isValid() && !selection_property.isWritable()},
                {"selected_notify",selection_property.isValid() && selection_property.hasNotifySignal()},
                {"select_method",meta->indexOfMethod("selectSkill(QString)")>=0}}},
            {"skills",catalog ? QJsonValue(rows(catalog)) : QJsonValue(QJsonValue::Null)},
            {"selected_skill",selection_property.isValid()
                ? QJsonValue::fromVariant(vm->property("selectedSkill")) : QJsonValue(QJsonValue::Null)},
#endif
            {"last_error",vm->lastError()},{"messages",rows(vm->messages())},{"models",rows(vm->models())},
            {"selected_model",vm->selectedModel()},{"selected_effort",vm->selectedEffort()},
            {"available_efforts",QJsonArray::fromStringList(vm->availableEfforts())},
            {"pending_plan",QJsonObject::fromVariantMap(vm->pendingPlan())},
            {"pending_question",QJsonObject::fromVariantMap(vm->pendingQuestion())},
            {"active_job",vm->activeJobId()},{"can_cancel",vm->canCancel()},
            {"context_consent_required",vm->contextConsentRequired()},
            {"context",decode(vm->contextPreview().toUtf8())},{"project",project},
            {"model_count_changes",model_changes}};
#ifdef EDI_TEST_WORKFLOW_CONTEXT
        if(codex_mode)result["handoff"]=Object{
            {"location",session->projectLocation()},{"needs_save_as",session->needsSaveAs()},
            {"account_label",vm->connectionLabel()},
            {"needs_fresh_save_as",QJsonValue::fromVariant(session->property("needsFreshSaveAs"))},
            {"last_error",session->lastError()},
            {"begin_method",session->metaObject()->indexOfMethod("beginSaveAs()")>=0},
            {"complete_method",session->metaObject()->indexOfMethod("completeSaveAs(QString,QUrl,QString)")>=0},
            {"cancel_method",session->metaObject()->indexOfMethod("cancelSaveAs(QString)")>=0}};
#endif
#ifdef EDI_TEST_WORKFLOW_CONTEXT
        if(codex_mode) {
            if(publication_owner || !publication_observer.isEmpty()) {
                result["publication_observer"]=publication_observer;
                result["publication_owner_alive"]=!publication_owner.isNull();
                result["publication_current"]=publication_values(session->project());
            }
            if(!terminal_selection_observer.isEmpty())result["terminal_selection_observer"]=terminal_selection_observer;
            if(!retirement_observer.isEmpty())result["retirement_observer"]=retirement_observer;
            result["message_model"]=Object{{"count",vm->messages()->count()},
                {"row_count",vm->messages()->rowCount()},
                {"role_count",vm->messages()->roleNames().size()}};
            result["policy"]=Object{
                {"record_bytes",static_cast<double>(edi::assistant::Limits::record_bytes)},
                {"message_bytes",static_cast<double>(edi::assistant::Limits::message_bytes)},
                {"stream_items",static_cast<double>(edi::assistant::Limits::stream_items)},
                {"stream_retained_bytes",static_cast<double>(edi::assistant::Limits::stream_retained_bytes)},
                {"stream_wire_bytes",static_cast<double>(edi::assistant::Limits::stream_wire_bytes)},
                {"retained_record_bytes",static_cast<double>(edi::assistant::Limits::retained_record_bytes)},
                {"context_bytes",static_cast<double>(edi::assistant::Limits::context_bytes)},
                {"stream_calls",static_cast<double>(edi::assistant::Limits::stream_calls)},
                {"http_operations",static_cast<double>(edi::assistant::Limits::http_operations)}};
            result["native_context"]=vm->contextPreview();
            Array cwl_profiles;
            for(const auto& token:edi::supported_peak_profiles(edi::BeamModeEnum::CONSTANT_WAVELENGTH))
                cwl_profiles.push_back(QString::fromStdString(token));
            result["native_profile_catalog"]=Object{{"beam_mode","constant wavelength"},{"profiles",cwl_profiles}};
            const auto usage_index=vm->metaObject()->indexOfProperty("usage");
            result["usage_observer"]=Object{{"property_present",usage_index>=0},
                {"refresh_present",vm->metaObject()->indexOfMethod("refreshUsage()")>=0},
                {"changes",report_urls.usage_changes},
                {"value",usage_index>=0?QJsonValue::fromVariant(vm->property("usage")):QJsonValue()}};
        }
        if(codex_mode)result["report_observer"]=Object{
            {"urls",report_urls.urls},
            {"method_present",vm->metaObject()->indexOfMethod("openReport(QString,QString)")>=0},
            {"limits",Object{
                {"name_bytes",static_cast<double>(edi::assistant::SelectedFileLimits::name_bytes)},
                {"file_bytes",static_cast<double>(edi::assistant::SelectedFileLimits::file_bytes)},
                {"collection_bytes",static_cast<double>(edi::assistant::SelectedFileLimits::collection_bytes)},
                {"files",static_cast<double>(edi::assistant::SelectedFileLimits::files)},
                {"json_depth",static_cast<double>(edi::assistant::Limits::json_depth)},
                {"ui_messages",static_cast<double>(edi::assistant::Limits::ui_messages)}}}};
#endif
        if(!callback319.isEmpty())result["callback319"]=callback319;
        return result;
    };
    auto callback=[&](const Object& value) {
        const auto name=value["op"].toString();
        if(name!="headers" && name!="data" && name!="finish")
            throw std::invalid_argument("only genuine fixture transport callbacks may be queued");
        fixture.dispatch(value);
    };
    std::string line;
    while(std::getline(std::cin,line)) {
        try {
            const auto input=decode(QByteArray::fromStdString(line)).toObject();
            const auto op=input["op"].toString();Object result;
#ifdef EDI_TEST_WORKFLOW_CONTEXT
            if(codex_mode && op=="codex304_start")result=public_transport304.start(input,storage.path());
            else if(codex_mode && op=="codex304_inspect") {
                if(!public_transport304.enabled)throw std::invalid_argument("public facade not started");
                result=public_transport304.snapshot();
            }
            else
#endif
            if(op=="sign_in")session->assistant()->signIn();
            else if(op=="sign_out")session->assistant()->signOut();
#ifdef EDI_TEST_WORKFLOW_CONTEXT
            else if(codex_mode && op=="refresh_usage") {
                result={{"invoked",QMetaObject::invokeMethod(session->assistant(),"refreshUsage",Qt::DirectConnection)}};
            }
            else if(codex_mode && op=="report_observer_reset")report_urls.urls=Array{};
            else if(codex_mode && op=="desktop_control") {
                const auto path=storage.path()+"/original-url-handler-control.txt";
                QFile control(path);if(!control.open(QIODevice::WriteOnly)
                    || control.write("Original harmless Qt URL control")<0)
                    throw std::runtime_error("owned URL control unavailable");
                control.close();const auto url=QUrl::fromLocalFile(path);
                const bool ok=QDesktopServices::openUrl(url);
                result={{"ok",ok},{"control_url",url.toString(QUrl::FullyEncoded)}};
            } else if(codex_mode && op=="open_report") {
                auto* vm=session->assistant();
                const bool present=vm->metaObject()->indexOfMethod("openReport(QString,QString)")>=0;
                result={{"method_present",present},{"invoked",present && QMetaObject::invokeMethod(vm,
                    "openReport",Qt::DirectConnection,Q_ARG(QString,input["row_id"].toString()),
                    Q_ARG(QString,input["href"].toString()))}};
            } else if(codex_mode && op=="save_as_begin") {
                QString intent;
                const bool invoked=QMetaObject::invokeMethod(session.get(),"beginSaveAs",Qt::DirectConnection,
                    Q_RETURN_ARG(QString,intent));
                result={{"invoked",invoked},{"intent",intent}};
            } else if(codex_mode && op=="save_as_complete") {
                bool accepted=false;
                const bool invoked=QMetaObject::invokeMethod(session.get(),"completeSaveAs",Qt::DirectConnection,
                    Q_RETURN_ARG(bool,accepted),Q_ARG(QString,input["intent"].toString()),
                    Q_ARG(QUrl,QUrl::fromLocalFile(input["parent"].toString())),Q_ARG(QString,input["leaf"].toString()));
                result={{"invoked",invoked},{"accepted",accepted}};
            } else if(codex_mode && op=="save_as_cancel") {
                result={{"invoked",QMetaObject::invokeMethod(session.get(),"cancelSaveAs",Qt::DirectConnection,
                    Q_ARG(QString,input["intent"].toString()))}};
            }
            else if(op=="select_skill") {
                auto* vm=session->assistant();
                const bool present=vm->metaObject()->indexOfMethod("selectSkill(QString)")>=0;
                const bool invoked=present && QMetaObject::invokeMethod(vm,"selectSkill",Qt::DirectConnection,
                    Q_ARG(QString,input["id"].toString()));
                // Invocation is only an observation of the public Qt method, not admission success.
                result={{"method_present",present},{"invoked",invoked}};
            }
#endif
            else if(codex_mode && op=="selected_after_terminal_arm") {
                QObject::disconnect(terminal_selection_connection);
                terminal_selection_armed=true;terminal_selection_observer={{"armed",true}};
                const auto draft=input["text"].toString();
                if(draft.isEmpty())throw std::invalid_argument("original admitted draft required");
                terminal_selection_connection=QObject::connect(session->assistant(),
                    &edi_app::AssistantViewModel::stateChanged,session.get(),[&,draft] {
                    auto* vm=session->assistant();
                    if(!terminal_selection_armed || !vm->connected() || vm->state()!="idle")return;
                    QFile file(history);if(!file.open(QIODevice::ReadOnly))return;
                    const auto bytes=file.readAll();file.close();
                    const auto retained=decode(bytes).toArray();
                    QString user_id;bool completed_reply=false;
                    for(const auto& entry:retained) {
                        const auto row=entry.toObject();
                        if(row["kind"].toString()=="user" && row["text"].toString()==draft && row["status"].toString()=="completed")
                            user_id=row["id"].toString();
                        else if(!user_id.isEmpty() && row["kind"].toString()=="assistant" && row["status"].toString()=="completed")
                            completed_reply=true;
                    }
                    if(user_id.isEmpty() || !completed_reply)return;
                    // Actual successful terminal retention and idle notification, before queued adoption.
                    // Disarm before the real public call's own notification; never synthesize an event.
                    terminal_selection_armed=false;
                    terminal_selection_observer={{"armed",true},{"entered",true},
                        {"original_user_id",user_id},{"retained_rows",retained},
                        {"retained_sha256",QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex())},
                        {"state_at_entry",vm->state()},{"connected_at_entry",vm->connected()},
                        {"project_present_at_entry",session->hasProject()}};
                    const auto request=vm->beginFileSelection();
                    terminal_selection_observer["request_id"]=request;
                    terminal_selection_observer["last_error"]=vm->lastError();
                    terminal_selection_observer["returned"]=true;
                },Qt::DirectConnection);
                result={{"armed",true}};
            }
            else if(codex_mode && op=="retirement_arm") {
                QObject::disconnect(retirement_connection);
                retirement_armed=true;retirement_observer={{"armed",true},{"calls",0}};
                const auto action=input["action"].toString(),replacement=input["replacement"].toString();
                const auto signal=input["signal"].toString("conversationRetired");
                const bool queued=input["queued"].toBool();
                if(action!="close" && action!="replace" && action!="clear" && action!="clear-archive-refusal")throw std::invalid_argument("finite retirement action required");
                auto callback=[&,action,replacement,signal,queued] {
                    if(!retirement_armed)return;retirement_armed=false;
                    QPointer<edi_app::ProjectViewModel> entering=session->project();
                    retirement_observer["calls"]=retirement_observer["calls"].toInt()+1;
                    retirement_observer["entered"]=true;
                    retirement_observer["entering_present"]=!entering.isNull();
                    retirement_observer["entering_path"]=entering?entering->path():QString{};
                    retirement_observer["signal"]=signal;
                    retirement_observer["queued"]=queued;
                    retirement_observer["connected_at_entry"]=session->assistant()->connected();
                    retirement_observer["message_count_at_entry"]=session->assistant()->messages()->count();
                    if(action=="close")session->closeProject();
                    else if(action=="clear")session->assistant()->clearHistory();
                    else if(action=="clear-archive-refusal") {
                        try {
                            retirement_observer["host_published_before_clear"]=session->hasProject();
                            retirement_observer["archive_before_clear"]=archive();
                            QFile retained(history);
                            if(!retained.open(QIODevice::ReadOnly))throw std::runtime_error("retained terminal archive unavailable");
                            const auto bytes=retained.readAll();retained.close();
                            retirement_observer["retained_rows"]=decode(bytes);
                            const auto backup=history+".preserved";
                            if(!QFile::rename(history,backup) || !QDir().mkpath(history))
                                throw std::runtime_error("ordinary owned archive write barrier unavailable");
                            QFile saved(backup);if(!saved.open(QIODevice::ReadOnly))throw std::runtime_error("preserved archive unavailable");
                            retirement_observer["preserved_sha256"]=QString::fromLatin1(QCryptographicHash::hash(saved.readAll(),QCryptographicHash::Sha256).toHex());
                            retirement_observer["archive_is_directory"]=QFileInfo(history).isDir();
                            session->assistant()->clearHistory();
                            retirement_observer["clear_called"]=true;
                            retirement_observer["clear_error"]=session->assistant()->lastError();
                        } catch(const std::exception& error) {
                            retirement_observer["barrier_error"]=QString::fromUtf8(error.what());
                        }
                    }

                    else retirement_observer["replacement_opened"]=session->openProject(QUrl::fromLocalFile(replacement));
                    retirement_observer["entering_alive_after_callback"]=!entering.isNull();
                    retirement_observer["current_present_after_callback"]=session->project()!=nullptr;
                    retirement_observer["current_path_after_callback"]=session->project()?session->project()->path():QString{};
                    retirement_observer["connected_after_callback"]=session->assistant()->connected();
                    retirement_observer["returned"]=true;
                };
                const auto type=queued?Qt::QueuedConnection:Qt::DirectConnection;
                if(signal=="conversationRetired")retirement_connection=QObject::connect(session->assistant(),
                    &edi_app::AssistantViewModel::conversationRetired,session.get(),callback,type);
                else if(signal=="fileSelectionRetired")retirement_connection=QObject::connect(session->assistant(),
                    &edi_app::AssistantViewModel::fileSelectionRetired,session.get(),callback,type);
                else if(signal=="rowsAboutToBeRemoved")retirement_connection=QObject::connect(session->assistant()->messages(),
                    &QAbstractItemModel::rowsAboutToBeRemoved,session.get(),callback,type);
                else if(signal=="rowsRemoved")retirement_connection=QObject::connect(session->assistant()->messages(),
                    &QAbstractItemModel::rowsRemoved,session.get(),callback,type);
                else if(signal=="countChanged")retirement_connection=QObject::connect(session->assistant()->messages(),
                    &edi_app::RowTableModel::countChanged,session.get(),callback,type);
                else if(signal=="rowsAboutToBeInserted")retirement_connection=QObject::connect(session->assistant()->messages(),
                    &QAbstractItemModel::rowsAboutToBeInserted,session.get(),callback,type);
                else if(signal=="rowsInserted")retirement_connection=QObject::connect(session->assistant()->messages(),
                    &QAbstractItemModel::rowsInserted,session.get(),callback,type);
                else if(signal=="dataChanged")retirement_connection=QObject::connect(session->assistant()->messages(),
                    &QAbstractItemModel::dataChanged,session.get(),callback,type);
                else throw std::invalid_argument("actual retirement or message notification signal required");
                result={{"armed",true}};
            }
            else if(codex_mode && op=="publication_inspect")result=publication_values(session->project());
            else if(codex_mode && op=="publication_seed_undo") {
                auto* owner=session->project();if(!owner)throw std::runtime_error("real project required");
                publication_owner=owner;
                auto* live=owner->assistantProject();
                const auto path=std::string("structure.cell.length_a");
                edi::Parameter* parameter=nullptr;
                for(const auto& entry:edi::parameter_entries(*live))if(entry.path==path)parameter=entry.parameter;
                if(!parameter)throw std::runtime_error("original independent cell parameter unavailable");
                std::string unique_name;
                for(const auto& slot:edi::named_slots(*live))
                    if(slot.parameter==parameter)unique_name=slot.unique_name;
                if(unique_name.empty())throw std::runtime_error("original parameter has no actual refinable unique name");
                const bool before=parameter->free.get();
                const auto change=edi::Edit::set_free(*live,{{unique_name,!before}});
                const auto outcome=owner->applyRecordedEdit(change,false);
                result={{"error",outcome.message}};
            }
            else if(codex_mode && op=="publication_scan_start") {
                if(!session->project())throw std::runtime_error("real scan project required");
                publication_owner=session->project();
                // Ordinary Follow checkbox policy: no fabricated renderer receipt.
                session->project()->fit()->setFollowing(false);
                session->project()->fit()->start();
            }
            else if(codex_mode && op=="publication_arm") {
                auto* owner=session->project();if(!owner)throw std::runtime_error("real project required");
                QObject::disconnect(publication_connection);
                publication_owner=owner;publication_observer=Object{};publication_armed=true;
                const auto action=input["action"].toString(),signal=input["signal"].toString();
                const auto destination=input["destination"].toString();
                const auto replacement=input["replacement"].toString();
                auto callback=[&,owner=QPointer<edi_app::ProjectViewModel>(owner),action,signal,destination,replacement] {
                    if(!publication_armed)return;publication_armed=false;
                    publication_observer={{"entered",true},{"action",action},{"signal",signal},
                        {"same_owner_at_entry",owner && session->project()==owner},
                        {"before",publication_values(owner)}};
                    if(!owner)throw std::runtime_error("actual publication owner vanished before callback");
                    QString refusal;
                    if(action=="report-setting")owner->setReportFormat("pdf",!owner->project().report_pdf.value_or(false));
                    else if(action=="save")refusal=owner->saveTo(destination);
                    else if(action=="undo")owner->undo();
                    else if(action=="fit-start")owner->fit()->start();
                    else if(action=="fit-reset")owner->fit()->reset();
                    else if(action=="restore-patterns")owner->restorePatterns();
                    else if(action=="scan-prepare")refusal=owner->prepareScan(true);
                    else if(action=="scan-reset")refusal=owner->resetScan();
                    else if(action=="close")session->closeProject();
                    else if(action=="replace")publication_observer["replacement_opened"]=session->openProject(QUrl::fromLocalFile(replacement));
                    else throw std::invalid_argument("undeclared finite publication action");
                    publication_observer["method_refusal"]=refusal;
                    publication_observer["after"]=publication_values(owner);
                    publication_observer["owner_alive_after_callback"]=!owner.isNull();
                    publication_observer["current_owner_is_original"]=owner && session->project()==owner;
                    publication_observer["destination_exists"]=QFileInfo::exists(destination);
                    publication_observer["returned"]=true;
                };
                if(signal=="projectEdited")publication_connection=QObject::connect(owner,&edi_app::ProjectViewModel::projectEdited,session.get(),callback);
                else if(signal=="modifiedChanged")publication_connection=QObject::connect(owner,&edi_app::ProjectViewModel::modifiedChanged,session.get(),callback);
                else if(signal=="rowsInserted")publication_connection=QObject::connect(owner->structures(),&QAbstractItemModel::rowsInserted,session.get(),callback);
                else throw std::invalid_argument("undeclared finite publication signal");
                result={{"armed",true}};
            }
            else if(codex_mode && op=="publication_flush_retired") {
                // This manual command loop has no top-level exec(). Process the
                // ordinary DeferredDelete event only AFTER the public call returned.
                QCoreApplication::sendPostedEvents(nullptr,QEvent::DeferredDelete);
            }
            else if(codex_mode && op=="publication_create_structure") {
                if(!session->project())throw std::runtime_error("real project required");
                result={{"created",session->project()->createStructure()}};
            }
            else if(codex_mode && op=="ux319_arm") {
                QObject::disconnect(callback319_model);QObject::disconnect(callback319_state);QObject::disconnect(callback319_error);
                const auto trigger=input["trigger"].toString(),action=input["action"].toString(),text=input["text"].toString();
                if((trigger!="completed-user" && trigger!="failure") ||
                   (action!="clear" && action!="replace-project" && action!="recreate-session" && action!="refused-input") ||
                   (trigger=="completed-user" && text.isEmpty()) ||
                   (trigger=="failure" && action!="refused-input"))
                    throw std::invalid_argument("319 finite original callback declaration required");
                QPointer<edi_app::AssistantViewModel> original=session->assistant();
                QPointer<edi_app::Session> original_session=session.get();
                QPointer<edi_app::ProjectViewModel> original_project=session->project();
                const auto identity=[](const void* value) {return QString::number(static_cast<qulonglong>(reinterpret_cast<quintptr>(value)),16);};
                const auto receiver_id=identity(original.data()),session_id=identity(original_session.data());
                auto* original_model=original->messages();
                const auto model_id=identity(original_model);
                callback319={{"armed",true},{"trigger",trigger},{"action",action},{"original_receiver",receiver_id},
                    {"original_session",session_id},{"original_model",model_id},{"original_text",text},
                    {"notices",Array{}},{"callbacks",0},{"sequence",0}};
                callback319_armed=true;
                auto action319=[&,original,original_session,original_project,receiver_id,session_id,model_id,trigger,action,text,identity](const QString& signal,int first,int last,const QList<int>& roles) {
                    if(!callback319_armed || !original || !original_session || session.get()!=original_session.data())return;
                    Object user;int user_index=-1;Array role_names;
                    if(trigger=="completed-user") {
                        if(first<0 || last<first)return;
                        const auto published=rows(original->messages());
                        const auto names=original->messages()->roleNames();
                        bool status_announced=roles.isEmpty();
                        for(const int role:roles) {
                            const auto name=QString::fromUtf8(names.value(role));role_names.push_back(name);
                            if(name=="status")status_announced=true;
                        }
                        if(!status_announced)return;
                        for(int index=first;index<=last && index<published.size();++index) {
                            const auto row=published.at(index).toObject();
                            if(row["kind"].toString()=="user" && row["text"].toString()==text && row["status"].toString()=="completed") {
                                if(!user.isEmpty()) {callback319["observer_error"]="Original notification has multiple completed identities";callback319_armed=false;return;}
                                user=row;user_index=index;
                            }
                        }
                        if(user.isEmpty())return;
                        QFile retained(history);
                        if(!retained.open(QIODevice::ReadOnly)) {callback319["observer_error"]="Original completed archive unavailable";callback319_armed=false;return;}
                        const auto bytes=retained.readAll();retained.close();
                        const auto persisted=QJsonDocument::fromJson(bytes);
                        if(!persisted.isArray()) {callback319["observer_error"]="Original completed archive is not an array";callback319_armed=false;return;}
                        int matches=0;Object retained_user;
                        for(const auto& entry:persisted.array()) {
                            const auto row=entry.toObject();
                            if(row["id"]==user["id"] && row["kind"].toString()=="user" && row["text"].toString()==text && row["status"].toString()=="completed") {++matches;retained_user=row;}
                        }
                        if(matches!=1) {callback319["observer_error"]="Original completed public row lacks exact unique durable identity";callback319_armed=false;return;}
                        callback319["archive_user_at_entry"]=retained_user;
                        callback319["archive_sha256_at_entry"]=QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex());
                    } else if(original->connected() || original->lastError().isEmpty())return;
                    callback319_armed=false;++callback319_depth;
                    callback319["callbacks"]=callback319["callbacks"].toInt()+1;
                    callback319["entered"]=true;callback319["signal"]=signal;
                    callback319["sequence"]=callback319["sequence"].toInt()+1;
                    callback319["entry_sequence"]=callback319["sequence"];
                    callback319["receiver_at_entry"]=identity(original.data());
                    callback319["session_at_entry"]=identity(original_session.data());
                    callback319["model_at_entry"]=identity(original->messages());
                    callback319["original_alive_at_entry"]=!original.isNull();
                    callback319["depth_at_entry"]=callback319_depth;
                    callback319["user_at_entry"]=user;
                    callback319["error_at_entry"]=original->lastError();
                    callback319["message_count_at_entry"]=original->messages()->count();
                    callback319["changed_first"]=first;callback319["changed_last"]=last;
                    callback319["changed_user_index"]=user_index;callback319["changed_roles"]=role_names;
                    callback319["all_roles_changed"]=roles.isEmpty();
                    if(action=="clear")original->clearHistory();
                    else if(action=="replace-project") {
                        session->closeProject();
                        callback319["replacement_created"]=session->createProject("Original319 B","Actual public notification successor");
                    } else if(action=="recreate-session") {
                        session.reset();session=make_session();observe();
                        callback319["replacement_present"]=session && session->assistant();
                        // Explicit real B account admission happens IN original A callback.
                        session->assistant()->signIn();callback319["replacement_signin_returned"]=true;
                    } else {
                        QString returned;
                        callback319["submit_invoked"]=QMetaObject::invokeMethod(original,"submitDraft",Qt::DirectConnection,
                            Q_RETURN_ARG(QString,returned),Q_ARG(QString,QStringLiteral("   ")));
                        callback319["refused_row"]=returned;
                    }
                    callback319["returned_inside_callback"]=true;
                    callback319["depth_after_action"]=callback319_depth;
                    callback319["original_alive_after_action"]=!original.isNull();
                    callback319["original_session_alive_after_action"]=!original_session.isNull();
                    callback319["original_project_alive_after_action"]=!original_project.isNull();
                    callback319["current_receiver_after_action"]=identity(session->assistant());
                    callback319["current_session_after_action"]=identity(session.get());
                    --callback319_depth;
                };
                if(trigger=="completed-user")callback319_model=QObject::connect(original_model,&QAbstractItemModel::dataChanged,
                    &app,[action319](const QModelIndex& first,const QModelIndex& last,const QList<int>& roles) {action319("messages.dataChanged",first.row(),last.row(),roles);},Qt::DirectConnection);
                else callback319_state=QObject::connect(original,&edi_app::AssistantViewModel::stateChanged,
                    &app,[action319] {action319("stateChanged",-1,-1,{});},Qt::DirectConnection);
                callback319_error=QObject::connect(original,&edi_app::AssistantViewModel::lastErrorChanged,&app,[&,original,receiver_id] {
                    if(!original)return;
                    auto notices=callback319["notices"].toArray();
                    if(notices.size()>=16) {callback319["overflow"]=true;return;}
                    callback319["sequence"]=callback319["sequence"].toInt()+1;
                    notices.push_back(Object{{"sequence",callback319["sequence"]},{"signal","lastErrorChanged"},{"receiver",receiver_id},
                        {"error",original->lastError()},{"inside_action_depth",callback319_depth}});
                    callback319["notices"]=notices;
                },Qt::DirectConnection);
                result={{"armed",true},{"receiver",receiver_id},{"session",session_id},{"model",model_id}};
            } else if(codex_mode && op=="ux319_submit") {
                QString returned;
                const bool invoked=QMetaObject::invokeMethod(session->assistant(),"submitDraft",Qt::DirectConnection,
                    Q_RETURN_ARG(QString,returned),Q_ARG(QString,input["text"].toString()));
                result={{"invoked",invoked},{"row_id",returned}};
            }
            else if(op=="send_text")session->assistant()->send(input["text"].toString());
            else if(op=="answer")session->assistant()->answerQuestion(input["id"].toString(),input["answer"].toString());
            else if(op=="approve")session->assistant()->approvePlan(input["id"].toString());
            else if(op=="cancel")session->assistant()->cancel();
            else if(op=="clear_history")session->assistant()->clearHistory();
#ifdef EDI_TEST_SELECTED_FILES
            else if(op=="selected_begin") {
                result={{"request_id",session->assistant()->beginFileSelection()}};
            } else if(op=="selected_cancel") {
                session->assistant()->cancelFileSelection(input["request_id"].toString());
            } else if(op=="selected_add") {
                QList<QUrl> urls;
                for(const auto& value:input["urls"].toArray()) urls.push_back(QUrl(value.toString()));
                result={{"accepted",session->assistant()->addSelectedFiles(input["request_id"].toString(),urls)}};
            } else if(op=="selected_remove") {
                result={{"accepted",session->assistant()->removeSelectedFile(input["id"].toString())}};
            }
#endif
            else if(op=="select_model")session->assistant()->setSelectedModel(input["id"].toString());
            else if(op=="select_effort")session->assistant()->setSelectedEffort(input["id"].toString());
            else if(op=="open")result={{"opened",session->openProject(QUrl::fromLocalFile(input["path"].toString()))}};
            else if(codex_mode && op=="named_empty_create") {
                if(session->hasProject())throw std::invalid_argument("new empty setup requires no prior owner");
                const bool created=session->createProject(input["name"].toString(),input["description"].toString(),
                    input["location"].toString(),input["su_rule"].toString(),input["title"].toString(),
                    input["authors"].toString(),input["report_libraries"].toBool());
                named_empty_observation=true;
                named_empty_owner=session->project();
                named_empty_core=named_empty_owner?static_cast<const void*>(&named_empty_owner->project()):nullptr;
                result={{"created",created},{"error",session->lastError()}};
            }
            else if(codex_mode && op=="background285_observe") {
                background285_enabled=true;result={{"enabled",true}};
            }
            else if(codex_mode && op=="background285_simulation") {
                if(!session->project())throw std::invalid_argument("actual owner required");
                const bool created=session->project()->createExperiment();
                if(created)session->project()->setCurrentExperimentIndex(
                    static_cast<int>(session->project()->experimentModels().size())-1);
                result={{"created",created},{"selected",session->project()->currentExperimentIndex()}};
            }
            else if(codex_mode && op=="background285_manual") {
                if(!session->project())throw std::invalid_argument("actual owner required");
                const auto models=session->project()->experimentModels();
                const auto index=session->project()->currentExperimentIndex();
                if(index<0 || index>=models.size())throw std::invalid_argument("actual current bank required");
                auto* model=models[index]->background();const auto action=input["action"].toString();
                if(action=="defined") {
                    result=QJsonObject::fromVariantMap(model->changeDefined(
                        input["operation"].toString(),input["id"].toString(),
                        input["position"].toDouble(),input["intensity"].toDouble(),input["free"].toBool()));
                } else if(action=="position") {
                    result={{"accepted",model->setPosition(input["row"].toInt(),input["position"].toDouble())}};
                } else if(action=="remove") {
                    const auto count=model->count();model->remove(input["row"].toInt());
                    result={{"removed",model->count()==count-1}};
                } else if(action=="rename") {
                    result={{"accepted",model->setId(input["row"].toInt(),input["id"].toString())}};
                } else throw std::invalid_argument("declared public model operation required");
            }
            else if(codex_mode && op=="native_science_enable") {
                native_science_enabled=true;result={{"enabled",true}};
            }
            else if(codex_mode && op=="native_remove_structure") {
                if(!session->project())throw std::invalid_argument("actual current project required");
                session->project()->removeStructure(input["index"].toInt());
                result={{"remaining",static_cast<int>(session->project()->project().structures.size())},
                    {"error",session->project()->lastError()}};
            }
            else if(codex_mode && op=="native_undo") {
                if(!session->project())throw std::invalid_argument("Undo requires actual project");
                const bool available=session->project()->canUndo();
                session->project()->undo();result={{"was_available",available}};
            }
            else if(op=="manual_value") {
                if(!session->project())throw std::invalid_argument("manual edit requires the real open project");
                auto* live=session->project()->assistantProject();
                const auto path=input["path"].toString().toStdString();
                edi::Parameter* selected=nullptr;
                for(const auto& entry:edi::parameter_entries(*live))
                    if(entry.path==path) {selected=entry.parameter;break;}
                if(!selected)throw std::invalid_argument("manual edit path is absent from the real project");
                const bool fitting_at_entry=session->project()->fit()->running();
                const auto actual_values=[&] {
                    Array values;
                    for(const auto& entry:edi::parameter_entries(*live)) {
                        const auto& parameter=*entry.parameter;
                        values.push_back(Object{{"path",QString::fromStdString(entry.path)},
                            {"value",parameter.value.get()},{"free",parameter.free.get()},
                            {"uncertainty",parameter.uncertainty?QJsonValue(*parameter.uncertainty):QJsonValue()}});
                    }
                    return values;
                };
                const auto before_values=codex_mode?actual_values():Array{};
                const auto error=session->project()->apply(edi::Edit::value(*selected,input["value"].toDouble()),false);
                result={{"error",error}};
                if(codex_mode) {
                    result["fit_running_at_entry"]=fitting_at_entry;
                    result["parameters_before"]=before_values;
                    result["parameters_after"]=actual_values();
                }
            }
            else if(op=="close_project")session->closeProject();
            else if(op=="destroy")session.reset();
            else if(op=="recreate") {
                if(session)throw std::invalid_argument("retire the real Session before recreation");
                session=make_session();observe();
            } else if(op=="archive_seed") {
                if(session)throw std::invalid_argument("seed isolated persisted history only without a live VM");
                QDir().mkpath(QFileInfo(history).absolutePath());QFile file(history);
                const auto bytes=encode(input["rows"].toArray());
                if(!file.open(QIODevice::WriteOnly|QIODevice::Truncate) || file.write(bytes)!=bytes.size())
                    throw std::runtime_error("isolated history seed could not be written");
                file.close();
            } else if(op=="archive") {
                QFile file(history);if(!file.open(QIODevice::ReadOnly))throw std::runtime_error("isolated archive not readable");
                result={{"rows",decode(file.readAll())}};
            } else if(codex_mode && op=="arm_post_adoption_barrier") {
                if(session->hasProject() || input["intent"].toString().isEmpty())
                    throw std::invalid_argument("arm requires actual empty owner and original intent");
                notice_intent=input["intent"].toString();notice_barrier=Object{};arm_notice_barrier=true;
                result={{"armed",true},{"archive_untouched",true}};
            } else if(op=="persistence_barrier") {
                // A real task-owned directory blocks QSaveFile replacement under every uid.
                // Keep preexisting archive bytes at a separately observed task-owned backup.
                const auto backup=history+".preserved";
                if(QFileInfo(history).isFile() && !QFile::rename(history,backup))
                    throw std::runtime_error("isolated preservation backup failed");
                if(!QDir().mkpath(history))throw std::runtime_error("isolated write refusal path unavailable");
                QFile saved(backup);QByteArray bytes;
                if(saved.open(QIODevice::ReadOnly))bytes=saved.readAll();
                result={{"preserved_sha256",QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex())}};
            } else if(op=="persistence_restore") {
                const auto backup=history+".preserved";
                if(!QFileInfo(history).isDir() || !QDir().rmdir(history) ||
                   !QFile::rename(backup,history))
                    throw std::runtime_error("isolated history restoration failed");
            } else if(op=="callback_batch") {
                const auto callbacks=input["callbacks"].toArray();
                if(callbacks.isEmpty() || callbacks.size()>16)throw std::invalid_argument("bounded fixture callback batch");
                for(const auto& value:callbacks) {callback(value.toObject());QCoreApplication::processEvents(QEventLoop::AllEvents,1);}
            } else if(op=="send_then_stop") {
                const auto count=fixture.operations.size();
                session->assistant()->send(input["text"].toString());
                result={{"before_stop",snapshot()},{"physical_before_stop",static_cast<double>(fixture.operations.size()-count)}};
                if(input["stop"].toBool())session->assistant()->cancel();
            } else if(op=="answer_then_stop") {
                session->assistant()->answerQuestion(input["id"].toString(),input["answer"].toString());
                result={{"before_stop",snapshot()}};
                if(input["stop"].toBool())session->assistant()->cancel();
            } else if(op=="queued_callbacks_retire") {
                const auto callbacks=input["callbacks"].toArray();
                QMetaObject::invokeMethod(&app,[&,callbacks]{
                    for(const auto& value:callbacks)callback(value.toObject());
                },Qt::QueuedConnection);
                const auto retire=input["retirement"].toString();
                if(retire=="clear")session->assistant()->clearHistory();
                else if(retire=="project")session->closeProject();
                else if(retire=="account")session->assistant()->signOut();
                else if(retire=="session")session.reset();
                else throw std::invalid_argument("unknown explicit real-owner retirement");
            } else result=fixture.dispatch(input);
            drain();
            auto output=fixture.snapshot();output["reply"]=result;output["vm"]=snapshot();output["archive"]=archive();output["notice_barrier"]=notice_barrier;
#ifdef EDI_TEST_WORKFLOW_CONTEXT
            if(public_transport304.enabled)output["public_transport304"]=public_transport304.snapshot();
#endif
            std::cout<<encode(output).toStdString()<<'\n'<<std::flush;
        } catch(const std::exception& error) {
            std::cout<<encode(Object{{"host_error",QString::fromUtf8(error.what())}}).toStdString()<<'\n'<<std::flush;
        }
    }
    session.reset();
}

#include "probe.moc"
