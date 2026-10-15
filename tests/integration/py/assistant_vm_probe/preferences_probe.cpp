// PRIVATE tests-owned native settings consumer. No production implementation inclusion.
#include "fixture_services.hpp"
#include "session.hpp"
#include "assistant_view_model.hpp"
#include "engine_setup.hpp"
#include <QDir>
#include <QFileInfo>
#include <QGuiApplication>
#include <QQmlEngine>
#include <QSettings>
#include <QtQml/qqmlextensionplugin.h>
#ifdef Q_OS_UNIX
#include <unistd.h>
#endif

Q_IMPORT_QML_PLUGIN(edi_appPlugin)

namespace {
Array rows(edi_app::RowTableModel* model) {
    Array result;
    for (int index=0;index<model->count();++index) {
        Object row;
        for (const auto& role:model->roleNames())
            row[QString::fromUtf8(role)]=QJsonValue::fromVariant(model->get(index,QString::fromUtf8(role)));
        result.push_back(row);
    }
    return result;
}
void deliver() {
    QElapsedTimer elapsed; elapsed.start();
    do {QCoreApplication::processEvents(QEventLoop::AllEvents,1);} while(elapsed.elapsed()<30);
}
}

int main(int argc,char** argv) {
    // The Python case creates this existing private root. Refuse before any default settings access.
    const auto root=QString::fromUtf8(qgetenv("EDI_TEST_SETTINGS_ROOT"));
    if(root.isEmpty() || !QDir::isAbsolutePath(root) || !QFileInfo(root).isDir())return 97;
    for(const auto* name:{"data","config","cache","settings"})
        if(!QDir().mkpath(root+"/"+name))return 98;
    qputenv("XDG_DATA_HOME",(root+"/data").toUtf8());
    qputenv("XDG_CONFIG_HOME",(root+"/config").toUtf8());
    qputenv("XDG_CACHE_HOME",(root+"/cache").toUtf8());
    QSettings::setDefaultFormat(QSettings::IniFormat);
    QSettings::setPath(QSettings::IniFormat,QSettings::UserScope,root+"/settings");
    QGuiApplication app(argc,argv);
    QCoreApplication::setOrganizationName("EasyScience");
    QCoreApplication::setApplicationName("EasyDiffraction");
    const auto arguments=QCoreApplication::arguments();
    if(arguments.size()==3 && arguments[1]=="--settings-read-qualifier") {
        // Separate process only: no Session/native construction or subject QSettings cache observer.
        const QFileInfo info(arguments[2]);
        const auto parent=info.dir().canonicalPath();
        const auto owned=QFileInfo(root).canonicalFilePath();
        if(!info.isAbsolute() || info.isSymLink() ||
           (info.exists() && !info.isFile()) ||
           (parent!=owned && !parent.startsWith(owned+"/")))return 96;
        QFile file(info.absoluteFilePath());
        const bool opened=file.open(QIODevice::ReadOnly);
        const auto file_error=file.error();
        QSettings settings(info.absoluteFilePath(),QSettings::IniFormat);
        const auto count=settings.allKeys().size();
        Object result{{"path",info.absoluteFilePath()},{"exists",info.exists()},
            {"qfile_opened",opened},{"qfile_error",static_cast<int>(file_error)},
            {"qsettings_status",static_cast<int>(settings.status())},
            {"key_count",static_cast<double>(count)}};
#ifdef Q_OS_UNIX
        result["effective_uid"]=static_cast<double>(geteuid());
#endif
        std::cout<<encode(result).toStdString()<<'\n'<<std::flush;
        return 0;
    }
    if(arguments.size()!=1)return 96;
    FixtureServices fixture; // Actual immutable native dependencies outlive engine/Session teardown.
    auto engine=std::make_unique<QQmlEngine>();
    auto owned=std::make_unique<edi_app::Session>(fixture.dependencies,nullptr);
    auto* session=owned.get();
    edi_app::configure_engine(*engine,std::move(owned));
    const auto configured=QFileInfo(edi_app::settings_file_path()).absoluteFilePath();
    if(!configured.startsWith(QDir(root).absolutePath()+"/"))return 99;
    auto snapshot=[&] {
        auto* vm=session->assistant();
        return Object{{"connected",vm->connected()},{"state",vm->state()},
            {"selected_model",vm->selectedModel()},{"selected_effort",vm->selectedEffort()},
            {"models",rows(vm->models())},{"available_efforts",QJsonArray::fromStringList(vm->availableEfforts())},
            {"messages",rows(vm->messages())},{"can_cancel",vm->canCancel()},
            {"last_error",vm->lastError()},{"context_consent_required",vm->contextConsentRequired()}};
    };
    std::string line;
    while(std::getline(std::cin,line)) {
        try {
            const auto input=decode(QByteArray::fromStdString(line)).toObject();
            const auto op=input["op"].toString();Object reply;
            auto* vm=session->assistant();
            if(op=="inspect") {}
            else if(op=="sign_in")vm->signIn();
            else if(op=="sign_out")vm->signOut();
            else if(op=="clear_history")vm->clearHistory();
            else if(op=="cancel")vm->cancel();
            else if(op=="send_text")vm->send(input["text"].toString());
            else if(op=="select_model")vm->setSelectedModel(input["id"].toString());
            else if(op=="select_effort")vm->setSelectedEffort(input["id"].toString());
            else if(op=="callback_batch") {
                const auto batch=input["callbacks"].toArray();
                if(batch.isEmpty() || batch.size()>16)throw std::invalid_argument("bounded fixture callback batch");
                for(const auto& value:batch) {
                    const auto callback=value.toObject();const auto kind=callback["op"].toString();
                    if(kind!="headers" && kind!="data" && kind!="finish")
                        throw std::invalid_argument("actual dependency callbacks only");
                    fixture.dispatch(callback);QCoreApplication::processEvents(QEventLoop::AllEvents,1);
                }
            } else reply=fixture.dispatch(input);
            deliver();
            auto output=fixture.snapshot();output["reply"]=reply;output["vm"]=snapshot();
            output["settings_file"]=configured;
            std::cout<<encode(output).toStdString()<<'\n'<<std::flush;
        } catch(const std::exception& error) {
            std::cout<<encode(Object{{"host_error",QString::fromUtf8(error.what())}}).toStdString()<<'\n'<<std::flush;
        }
    }
    engine.reset(); // Genuine Session destruction; no shared/hidden default profile survives.
}
