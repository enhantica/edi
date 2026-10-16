// Tests-owned real Session/VM component. No Main QML or alternate controller.
#include "fixture_services.hpp"
#include "session.hpp"
#include "assistant_view_model.hpp"
#include "engine_setup.hpp"
#include "edi/parameter_walk.hpp"
#include <QCryptographicHash>
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
public slots:
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
    auto observe=[&] {
#ifdef EDI_TEST_SELECTED_FILES
        QObject::connect(session->assistant(), &edi_app::AssistantViewModel::fileSelectionRetired,
            session.get(), [&](const QString& id){retired_selections.push_back(id);});
#endif
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
                parameters.push_back(Object{{"path",QString::fromStdString(entry.path)},
                    {"value",parameter.value.get()},{"free",parameter.free.get()},
                    {"uncertainty",parameter.uncertainty?QJsonValue(*parameter.uncertainty):QJsonValue()}});
            }
            project={{"parameters",parameters},{"mode",QString::fromStdString(value.fitting_mode)},
                {"objective",value.fit_result.objective_value}};
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
            if(op=="sign_in")session->assistant()->signIn();
            else if(op=="sign_out")session->assistant()->signOut();
#ifdef EDI_TEST_WORKFLOW_CONTEXT
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
            else if(op=="manual_value") {
                if(!session->project())throw std::invalid_argument("manual edit requires the real open project");
                auto* live=session->project()->assistantProject();
                const auto path=input["path"].toString().toStdString();
                edi::Parameter* selected=nullptr;
                for(const auto& entry:edi::parameter_entries(*live))
                    if(entry.path==path) {selected=entry.parameter;break;}
                if(!selected)throw std::invalid_argument("manual edit path is absent from the real project");
                const auto error=session->project()->apply(edi::Edit::value(*selected,input["value"].toDouble()),false);
                result={{"error",error}};
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
            auto output=fixture.snapshot();output["reply"]=result;output["vm"]=snapshot();output["archive"]=archive();
            std::cout<<encode(output).toStdString()<<'\n'<<std::flush;
        } catch(const std::exception& error) {
            std::cout<<encode(Object{{"host_error",QString::fromUtf8(error.what())}}).toStdString()<<'\n'<<std::flush;
        }
    }
    session.reset();
}

#include "probe.moc"
