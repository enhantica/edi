// Tests-owned real Session/VM component. No Main QML or alternate controller.
#include "fixture_services.hpp"
#include "session.hpp"
#include "assistant_view_model.hpp"
#include "engine_setup.hpp"
#include "edi/parameter_walk.hpp"
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QGuiApplication>
#include <QPointer>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QUuid>
#include <QtQml/qqmlextensionplugin.h>

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

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
    QTemporaryDir storage;
    if(!storage.isValid())return 97;
    qputenv("XDG_DATA_HOME",storage.path().toUtf8());
    qputenv("XDG_CONFIG_HOME",storage.path().toUtf8());
    QGuiApplication app(argc,argv);
    QGuiApplication::setOrganizationName("EdiIndependentAcceptance");
    QGuiApplication::setApplicationName("vm-"+QUuid::createUuid().toString(QUuid::WithoutBraces));
    edi_app::use_fresh_settings();
    FixtureServices fixture; // Outlives actual Session/VM/native callbacks and teardown.
    auto session=std::make_unique<edi_app::Session>(fixture.dependencies,nullptr);
    const auto history=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)+"/assistant/history.json";
    int model_changes=0;
    auto observe=[&] {
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
        }
        return {{"alive",true},{"connected",vm->connected()},{"state",vm->state()},
            {"last_error",vm->lastError()},{"messages",rows(vm->messages())},{"models",rows(vm->models())},
            {"selected_model",vm->selectedModel()},{"selected_effort",vm->selectedEffort()},
            {"available_efforts",QJsonArray::fromStringList(vm->availableEfforts())},
            {"pending_plan",QJsonObject::fromVariantMap(vm->pendingPlan())},
            {"pending_question",QJsonObject::fromVariantMap(vm->pendingQuestion())},
            {"active_job",vm->activeJobId()},{"can_cancel",vm->canCancel()},
            {"context_consent_required",vm->contextConsentRequired()},
            {"context",decode(vm->contextPreview().toUtf8())},{"project",project},
            {"model_count_changes",model_changes}};
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
            else if(op=="send_text")session->assistant()->send(input["text"].toString());
            else if(op=="answer")session->assistant()->answerQuestion(input["id"].toString(),input["answer"].toString());
            else if(op=="approve")session->assistant()->approvePlan(input["id"].toString());
            else if(op=="cancel")session->assistant()->cancel();
            else if(op=="clear_history")session->assistant()->clearHistory();
            else if(op=="select_model")session->assistant()->setSelectedModel(input["id"].toString());
            else if(op=="select_effort")session->assistant()->setSelectedEffort(input["id"].toString());
            else if(op=="open")result={{"opened",session->openProject(QUrl::fromLocalFile(input["path"].toString()))}};
            else if(op=="close_project")session->closeProject();
            else if(op=="destroy")session.reset();
            else if(op=="recreate") {
                if(session)throw std::invalid_argument("retire the real Session before recreation");
                session=std::make_unique<edi_app::Session>(fixture.dependencies,nullptr);observe();
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
