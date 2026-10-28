// Tests-owned real edi.app owner host. Services never replace the VM/controller/editor.
#include "fixture_services.hpp"
#include "session.hpp"
#include "assistant_view_model.hpp"
#include "assistant_history.hpp"
#include <map>
#include <QSet>
#include <QMap>
#include "assistant_markdown.hpp"
#include <QAbstractTextDocumentLayout>
#include <QTextTable>
#include <QTextBlock>
#include <QTextFragment>
#include <QTextImageFormat>
#include <QImage>
#include <QFontMetricsF>
#include <QTextLayout>
#include "assistant_native_tools.hpp"
#include "assistant_outgoing.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include "codex_agent.hpp"
#include <chrono>
#include <cstdio>
#include <type_traits>
#include "engine_setup.hpp"
#include "edi/io.hpp"
#include "edi/worker.hpp"
#include "example_list_model.hpp"
#include <condition_variable>
#include <mutex>
#include <filesystem>
#include "edi/background_estimate.hpp"
#include "edi/parameter_walk.hpp"
#include "../../../../core/src/assistant_skills.hpp"
#include <new>
#include <QDesktopServices>
#include <QInputMethodEvent>
#include <QKeyEvent>
#include <QMouseEvent>
#include <QDirIterator>
#include <QGuiApplication>
#include <QSettings>
#include <QJSValue>
#include <QWheelEvent>
#include <QClipboard>
#include <QCryptographicHash>
#include <QElapsedTimer>
#include <QSocketNotifier>
#include <cerrno>
#if defined(Q_OS_UNIX)
#include <fcntl.h>
#include <unistd.h>
#endif
#include <QFile>
#include <QDir>
#include <QJsonValue>
#include <QMetaMethod>
#include <QPointer>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQmlComponent>
#include <set>
#include <QQmlExpression>
#include <QQuickItem>
#include <QQuickWindow>
#include <QStandardPaths>
#include <QTcpServer>
#include <QTemporaryDir>
#include <QTextDocument>
#include <QUuid>
#include <QtQml/qqmlextensionplugin.h>
#include <QtTest/QTest>
#include <QtTest/QSignalSpy>

namespace edi_app {
// One explicitly authorized friend, defined only in this tests-owned carrier.
struct CodexAgentTestAccess {
    static bool expiredAt(const CodexAgent& agent,qint64 now){return agent.operationExpired(now);}
    static qint64 future(const CodexAgent& agent){return std::max(agent.operation_start_,agent.last_activity_)+std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::hours(24)).count();}
    static Object timing(const CodexAgent& agent){return {{"active",agent.operation_start_>=0},{"total_ms",static_cast<double>(agent.total_ms_)},{"idle_ms",static_cast<double>(agent.idle_ms_)},{"expired_after_day",expiredAt(agent,future(agent))}};}
    static void receive(CodexAgent& agent,const Object& value){agent.receive(QJsonDocument(value).toJson(QJsonDocument::Compact));}
    static bool expireIssuedControl(CodexAgent& agent,const QString& id){
        if(!agent.pending_.contains(id)||!agent.pending_deadlines_.contains(id))return false;
        agent.pending_deadlines_[id]=0;agent.checkDeadline();return agent.failureActive();
    }
};
}
static_assert(!std::is_default_constructible_v<edi_app::Session>, "E11 I5 QML must resolve the prepared per-engine Session factory");
Q_IMPORT_QML_PLUGIN(edi_appPlugin)
// Observe actual window delivery; never replace or consume an app input.
class UiInputObserver final:public QObject {
public:
    std::function<void(const QString&,QEvent*)> observe;
    bool eventFilter(QObject*,QEvent* event) override {
        QString kind;
        if(event->type()==QEvent::MouseButtonPress)kind="mouse_press";
        else if(event->type()==QEvent::MouseButtonRelease)kind="mouse_release";
        else if(event->type()==QEvent::KeyPress)kind="key_press";
        else if(event->type()==QEvent::InputMethod)kind="input_method";
        if(!kind.isEmpty() && observe)observe(kind,event);
        return false;
    }
};
class UrlObserver:public QObject {
    Q_OBJECT
public:
    QTcpServer images;
    int image_requests=0;
    Array activated;
    UrlObserver() {
        if(!images.listen(QHostAddress::LocalHost,0)) throw std::runtime_error("isolated image observation listener unavailable");
        QObject::connect(&images,&QTcpServer::newConnection,this,[this]{
            while(auto* socket=images.nextPendingConnection()) {
                ++image_requests;
                QObject::connect(socket,&QTcpSocket::readyRead,socket,[socket]{
                    socket->readAll();socket->write("HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
                    socket->disconnectFromHost();
                });
                QObject::connect(socket,&QTcpSocket::disconnected,socket,&QObject::deleteLater);
            }
        });
        QDesktopServices::setUrlHandler("http",this,"activate");
        QDesktopServices::setUrlHandler("https",this,"activate");
    }
    ~UrlObserver() {QDesktopServices::unsetUrlHandler("http");QDesktopServices::unsetUrlHandler("https");}
public slots:
    void activate(const QUrl& url) {activated.push_back(url.toString(QUrl::FullyEncoded));}
};
void drain(int milliseconds=30) {
    QElapsedTimer timer;timer.start();
    do {QCoreApplication::processEvents(QEventLoop::AllEvents,1);} while(timer.elapsed()<milliseconds);
}
std::vector<QObject*> objects(QObject* root) {
    std::vector<QObject*> result;
    std::set<QObject*> visited;
    std::function<void(QObject*)> visit=[&](QObject* object) {
        if(!object || !visited.insert(object).second) return;
        result.push_back(object);
        for(auto* child:object->children()) visit(child);
        if(auto* item=qobject_cast<QQuickItem*>(object)) for(auto* child:item->childItems()) visit(child);
    };
    visit(root);return result;
}
Object text_observation(QObject* object) {
    auto* item=qobject_cast<QQuickItem*>(object);
    const auto text=object->property("text").toString();
    const auto format=object->property("textFormat");
    QString shown=text;
    if(format.isValid() && format.toInt()!=Qt::PlainText &&
       (format.toInt()!=Qt::AutoText || Qt::mightBeRichText(text))) {
        QTextDocument document;
        if(format.toInt()==Qt::MarkdownText) document.setMarkdown(text);
        else document.setHtml(text);
        shown=document.toPlainText();
    }
    QStringList ancestry;
    for(auto* parent=object;parent;parent=parent->parent()) if(!parent->objectName().isEmpty()) ancestry.push_back(parent->objectName());
    return {{"text",text},{"display",shown},{"format",format.isValid()?format.toInt():-1},
            {"visible",item&&item->isVisible()},{"name",object->objectName()},
            {"ancestry",QJsonArray::fromStringList(ancestry)},
            {"width",item?item->width():0},{"height",item?item->height():0}};
}
QRectF exposed_rect(QQuickItem* item) {
    if(!item || !item->isVisible())return {};
    QRectF rect=item->boundingRect();
    for(auto* parent=item->parentItem();parent;parent=parent->parentItem())
        if(parent->clip())rect=rect.intersected(item->mapRectFromItem(parent,parent->boundingRect()));
    if(item->window())rect=rect.intersected(item->mapRectFromScene(QRectF(QPointF(),item->window()->size())));
    return rect;
}
Array model_rows(edi_app::RowTableModel* model) {
    Array result;
    for(int row=0;row<model->count();++row) {
        Object value;
        for(const auto& role:model->roleNames()) value[QString::fromUtf8(role)]=QJsonValue::fromVariant(model->get(row,QString::fromUtf8(role)));
        result.push_back(value);
    }
    return result;
}
int main(int argc,char** argv) {
    const bool codex_mode=argc==2 && QByteArray(argv[1])=="--codex";
    QTemporaryDir storage;
    if(!storage.isValid()) return 97;
    qputenv("XDG_DATA_HOME",storage.path().toUtf8());
    qputenv("XDG_CONFIG_HOME",storage.path().toUtf8());
    // Isolate the normal OS Documents default; do not seed any project destination.
    const auto temporary_documents=storage.path()+"/Documents";
#ifdef Q_OS_LINUX
    if(!QDir().mkpath(temporary_documents))return 94;
    QFile user_dirs(storage.path()+"/user-dirs.dirs");
    if(!user_dirs.open(QIODevice::WriteOnly))return 93;
    const auto user_dirs_bytes=(QStringLiteral("XDG_DOCUMENTS_DIR=\"")+temporary_documents+"\"\n").toUtf8();
    if(user_dirs.write(user_dirs_bytes)!=user_dirs_bytes.size())return 92;
    user_dirs.close();
#endif
    QGuiApplication app(argc,argv);
    app.setQuitOnLastWindowClosed(false); // The owned stdin protocol, including EOF, owns this test host lifetime.
    QGuiApplication::setOrganizationName("EdiIndependentAcceptance");
    const auto test_application_name=qEnvironmentVariable("EDI_TEST_ASSISTANT_APPLICATION_NAME");
    if(!test_application_name.isEmpty() && qEnvironmentVariable("EDI_TEST_ASSISTANT_RESTORE_SETTINGS").isEmpty())return 78;
    QGuiApplication::setApplicationName(test_application_name.isEmpty()?"assistant-"+QUuid::createUuid().toString(QUuid::WithoutBraces):test_application_name);
    edi_app::use_design_font();
    edi_app::use_fresh_settings();
    Object settings_restore_info;
    const auto settings_restore_source=qEnvironmentVariable("EDI_TEST_ASSISTANT_RESTORE_SETTINGS");
    if(!settings_restore_source.isEmpty()) {
        QFile original(settings_restore_source);
        if(!QFileInfo(settings_restore_source).isAbsolute() || !original.open(QIODevice::ReadOnly))return 83;
        const auto bytes=original.readAll();original.close();
        const auto destination=QSettings().fileName();
        if(QFileInfo::exists(destination) || !QDir().mkpath(QFileInfo(destination).absolutePath()))return 82;
        QFile copy(destination);if(!copy.open(QIODevice::WriteOnly)||copy.write(bytes)!=bytes.size())return 81;copy.close();
        {QSettings reload;reload.sync();if(reload.status()!=QSettings::NoError)return 80;}
        QFile verify(destination);if(!verify.open(QIODevice::ReadOnly)||verify.readAll()!=bytes)return 79;
        settings_restore_info={{"source",settings_restore_source},{"destination",destination},
            {"source_application_name_from_actual_filename",QFileInfo(settings_restore_source).completeBaseName()},
            {"destination_application_name",QGuiApplication::applicationName()},
            {"bytes",static_cast<double>(bytes.size())},
            {"sha256",QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex())},
            {"exact_copy",true},{"keys_rewritten",false}};
    }
    Object history_restore_info;
    const auto history_restore_source=qEnvironmentVariable("EDI_TEST_ASSISTANT_RESTORE_HISTORY");
    if(!history_restore_source.isEmpty()) {
        QFile original(history_restore_source);
        if(!QFileInfo(history_restore_source).isAbsolute() || !original.open(QIODevice::ReadOnly))return 87;
        const auto bytes=original.readAll();original.close();
        const auto destination=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)+"/assistant/history.json";
        if(!QDir().mkpath(QFileInfo(destination).absolutePath()) || QFileInfo::exists(destination))return 86;
        QFile copy(destination);if(!copy.open(QIODevice::WriteOnly)||copy.write(bytes)!=bytes.size())return 85;copy.close();
        QFile verify(destination);if(!verify.open(QIODevice::ReadOnly)||verify.readAll()!=bytes)return 84;
        history_restore_info={{"source",history_restore_source},{"destination",destination},{"bytes",static_cast<double>(bytes.size())},{"sha256",QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex())},{"exact_copy",true}};
    }
    Object cache_restore_info;
    const auto cache_manifest_source=qEnvironmentVariable("EDI_TEST_ASSISTANT_RESTORE_CACHE_MANIFEST");
    if(!cache_manifest_source.isEmpty()) {
        if(!codex_mode || qEnvironmentVariable("EDI_TEST_CODEX_PEER_INPUT").isEmpty())return 77;
        QFile manifest(cache_manifest_source);if(!QFileInfo(cache_manifest_source).isAbsolute() || !manifest.open(QIODevice::ReadOnly))return 76;
        const auto manifest_bytes=manifest.readAll();QJsonParseError parse_error;
        const auto document=QJsonDocument::fromJson(manifest_bytes,&parse_error);
        if(parse_error.error!=QJsonParseError::NoError || !document.isObject() || !document.object()["files"].isArray())return 75;
        const auto capture_root=QFileInfo(cache_manifest_source).canonicalPath()+"/cache-files/";
        const auto app_root=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
        Array copied;QSet<QString> seen;
        for(const auto& row:document.object()["files"].toArray()) {
            if(!row.isObject())return 74;const auto entry=row.toObject();
            const auto relative=entry["relative"].toString();
            const auto source=QFileInfo(entry["source"].toString()).canonicalFilePath();
            const auto destination=QDir::cleanPath(app_root+"/"+relative);
            if(relative.isEmpty() || QDir::isAbsolutePath(relative) || relative.contains("..") || seen.contains(relative)
                || !(relative=="assistant/history.json" || relative.startsWith("assistant/history/") || (relative.startsWith("assistant/history-recovered-")&&relative.endsWith(".json")))
                || !source.startsWith(capture_root) || !destination.startsWith(app_root+"/assistant/") || QFileInfo::exists(destination))return 73;
            seen.insert(relative);QFile input(source);if(!input.open(QIODevice::ReadOnly))return 72;
            const auto bytes=input.readAll();const auto hash=QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex());
            if(hash!=entry["sha256"].toString() || bytes.size()!=entry["bytes"].toInteger(-1))return 71;
            if(!QDir().mkpath(QFileInfo(destination).absolutePath()))return 70;
            QFile output(destination);if(!output.open(QIODevice::WriteOnly)||!output.setPermissions(QFileDevice::ReadOwner|QFileDevice::WriteOwner)||output.write(bytes)!=bytes.size())return 69;output.close();
            QFile verify(destination);if(!verify.open(QIODevice::ReadOnly)||verify.readAll()!=bytes)return 68;
            copied.append(Object{{"relative",relative},{"source",source},{"original_source",entry["original_source"]},{"destination",destination},{"sha256",hash},{"bytes",static_cast<double>(bytes.size())},{"exact_copy",true}});
        }
        cache_restore_info={{"manifest",cache_manifest_source},{"manifest_sha256",QString::fromLatin1(QCryptographicHash::hash(manifest_bytes,QCryptographicHash::Sha256).toHex())},{"files",copied},{"keys_or_rows_rewritten",false}};
    }
    Object initial_cache_read_binding;
    const auto initial_read_relative=qEnvironmentVariable("EDI_TEST_ASSISTANT_INITIAL_CACHE_READ");
    if(!initial_read_relative.isEmpty()) {
        if(!codex_mode || cache_manifest_source.isEmpty() || qEnvironmentVariable("EDI_TEST_CODEX_PEER_INPUT").isEmpty())return 67;
        const auto app_root=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
        const auto target=QDir::cleanPath(app_root+"/"+initial_read_relative);
        const auto control=qEnvironmentVariable("EDI_TEST_HISTORY_CONTROL"),release=qEnvironmentVariable("EDI_TEST_HISTORY_RELEASE");
        const auto fixture_root=QFileInfo(qEnvironmentVariable("EDI_TEST_CODEX_PEER_INPUT")).dir().absolutePath();
        const auto fixture_parent=QFileInfo(fixture_root).dir().canonicalPath();
        const auto owned_parent=[&](const QString& file) {const auto parent=QFileInfo(file).dir().canonicalPath();return !fixture_parent.isEmpty() && (parent==fixture_parent || parent.startsWith(fixture_parent+"/"));};
        bool valid=false;const auto epoch=qEnvironmentVariable("EDI_TEST_HISTORY_EPOCH").toUInt(&valid);
        if(!valid || !epoch || !(initial_read_relative=="assistant/history.json" || initial_read_relative.startsWith("assistant/history/"))
            || initial_read_relative.contains("..") || !QFileInfo(target).isFile() || QFileInfo(target).isSymLink()
            || !target.startsWith(app_root+"/assistant/") || !QDir::isAbsolutePath(control) || !QDir::isAbsolutePath(release)
            || !owned_parent(control) || !owned_parent(release) || QFileInfo(control).isSymLink() || QFileInfo(release).isSymLink()
            || target.contains('\n') || release.contains('\n') || QFileInfo::exists(control) || QFileInfo::exists(release))return 66;
        QFile output(control);if(!output.open(QIODevice::WriteOnly|QIODevice::NewOnly))return 65;
        const auto bytes=("hold_read\n"+target+"\n"+release+"\n"+QString::number(epoch)+"\n").toUtf8();
        if(output.write(bytes)!=bytes.size())return 64;output.close();
        initial_cache_read_binding={{"target",target},{"control",control},{"release",release},{"epoch",static_cast<int>(epoch)},{"bytes_changed",false}};
    }
    FixtureServices fixture; // Outlives all engines, QML, Session, VM and operation teardown.
    UrlObserver urls;
    auto engine=std::make_unique<QQmlApplicationEngine>();
    auto owned=codex_mode ? std::make_unique<edi_app::Session>(nullptr)
                          : std::make_unique<edi_app::Session>(fixture.dependencies,nullptr);
    QPointer<edi_app::Session> observed=owned.get();
    edi_app::configure_engine(*engine,std::move(owned));
    auto* singleton=engine->singletonInstance<edi_app::Session*>("edi.app","Session");
    engine->loadFromModule("edi.app","Main");
    if(engine->rootObjects().isEmpty()) return 96;
    QPointer<QQuickWindow> window=qobject_cast<QQuickWindow*>(engine->rootObjects().front());
    if(!window) return 95;
    QQmlExpression initial_owner(qmlContext(window),window,"Session.assistant");
    auto* actual_main_assistant=initial_owner.evaluate().value<QObject*>();
    if(initial_owner.hasError() || singleton!=observed || actual_main_assistant!=observed->assistant()
        || observed->parent()!=engine.get() || QJSEngine::objectOwnership(observed)!=QJSEngine::CppOwnership) {
        std::fputs("E11 I5 prepared Session, module singleton and actual Main owner differ; refuse before bootstrap\n",stderr);
        return 90;
    }
    window->resize(1280,768);window->show();drain();
    auto* preferences=engine->singletonInstance<QObject*>("edi.app","Preferences");
    preferences->setProperty("assistantShown",true);
    Array disclosures;
    Array action_transitions;
    // Tests-only public model observation. No production history setter/cache.
    Array message_model_events;
    QPointer<edi_app::RowTableModel> message_model_watched;
    std::vector<QMetaObject::Connection> message_model_connections;
    bool capture_message_cells=false;
    Array message_model_cells;
    auto snapshot_message_cells=[&]() {
        Array rows;
        if(!message_model_watched)return rows;
        const auto roles=message_model_watched->roleNames();
        for(int row=0;row<message_model_watched->count();++row) {
            Object cells;
            for(auto it=roles.cbegin();it!=roles.cend();++it) {
                const auto encoded=encode(Object{{"value",QJsonValue::fromVariant(message_model_watched->data(message_model_watched->index(row),it.key()))}});
                cells[QString::fromUtf8(it.value())]=QString::fromLatin1(QCryptographicHash::hash(encoded,QCryptographicHash::Sha256).toHex());
            }
            rows.append(cells);
        }
        return rows;
    };
    QObject message_model_observer;
    auto stop_message_model_watch=[&] {
        for(const auto& connection:message_model_connections)QObject::disconnect(connection);
        message_model_connections.clear();message_model_watched.clear();
    };
    QMetaObject::Connection session_notification_fault;
    QMetaObject::Connection session_transport_failure_watch;
    Object session_fault_facts;
    unsigned session_notification_hits=0;
    QObject session_fault_observer;
    // Test-owned handles of the original public archive owner; no application
    // rows, receipts, permissions or provider data are manufactured here.
    struct PublicArchiveProbe {
        QObject receiver;
        edi_app::AssistantHistoryArchive::View latest;
        unsigned notices=0;
        std::unique_ptr<edi_app::AssistantHistoryArchive> archive;
    };
    std::map<QString,std::unique_ptr<PublicArchiveProbe>> public_archives;
    QObject public_archive_clear_receiver;
    std::vector<edi_app::AssistantHistoryArchive::ClearBarrier> public_archive_barriers;
 // Disconnect before the retained facts leave scope.
    QMetaObject::Connection publication_fault;
    int publication_fault_hits=0;
    bool publication_undo_seen=false;
    QObject::connect(observed->assistant(),&edi_app::AssistantViewModel::showingActionsChanged,
        [&] {action_transitions.push_back(observed->assistant()->showingActions());});
    auto find=[&](const QString& name)->QObject* {
        for(auto* object:objects(window)) if(object->objectName()==name) return object;
        return nullptr;
    };
    auto click=[&](QObject* object) {
        auto* item=qobject_cast<QQuickItem*>(object);
        if(!item || !item->isVisible() || !item->isEnabled()) throw std::runtime_error("requested real UI control is not reachable");
        const auto center=item->mapToScene(QPointF(item->width()/2,item->height()/2)).toPoint();
        QTest::mouseClick(window,Qt::LeftButton,Qt::NoModifier,center);drain();
    };
    auto activate_item_link=[&](QObject* object)->bool {
        auto* item=qobject_cast<QQuickItem*>(object);
        if(!item || !item->isVisible()) return false;
        QMetaMethod link_at;
        for(int index=0;index<object->metaObject()->methodCount();++index) {
            auto method=object->metaObject()->method(index);
            if(method.name()=="linkAt" && method.parameterCount()==2) {link_at=method;break;}
        }
        if(!link_at.isValid()) return false;
        auto types=link_at.parameterTypes();
        for(int y=2;y<std::min(160.,item->height());y+=4) for(int x=2;x<std::min(512.,item->width());x+=4) {
            QString link;qreal px=x,py=y;
            if(!link_at.invoke(object,Qt::DirectConnection,QGenericReturnArgument("QString",&link),QGenericArgument(types[0].constData(),&px),QGenericArgument(types[1].constData(),&py)))
                throw std::runtime_error("public Qt text link hit-test invocation failed");
            if(link.isEmpty()) continue;
            QTest::mouseClick(window,Qt::LeftButton,Qt::NoModifier,item->mapToScene(QPointF(x,y)).toPoint());
            drain();return true;
        }
        return false;
    };
    auto accept_dialog=[&] {
        for(auto* object:objects(window)) {
            if(!object->property("visible").toBool() || !object->property("title").isValid()) continue;
            if(object->metaObject()->indexOfMethod("accept()")<0) continue;
            Array texts;
            for(auto* child:objects(object)) if(child->property("text").isValid()) texts.push_back(text_observation(child));
            disclosures.push_back(Object{{"title",object->property("title").toString()},{"texts",texts}});
            QMetaObject::invokeMethod(object,"accept");drain();return true;
        }
        return false;
    };
    Array ui_sequence;
    UiInputObserver ui_inputs;
    auto ui_record=[&](const QString& kind,QEvent* event=nullptr) {
        if(!window || !observed)return;
        auto* panel=find("assistant.popup");auto* toggle=find("assistant.toggle");
        auto* dialog=find("createProject.dialog");auto* create=qobject_cast<QQuickItem*>(find("project.create"));
        Object row{{"kind",kind},{"project_present",observed->project()!=nullptr},
            {"assistant_preference",preferences->property("assistantShown").toBool()},
            {"assistant_selected",toggle&&toggle->property("assistantSelected").toBool()},
            {"assistant_visible",panel&&panel->property("visible").toBool()},
            {"create_visible",create&&create->isVisible()},
            {"create_exposed",create&&!exposed_rect(create).isEmpty()},
            {"dialog_visible",dialog&&dialog->property("visible").toBool()},
            {"dialog_opened",dialog&&dialog->property("opened").toBool()},
            {"dialog_name",dialog?dialog->property("projectName").toString():QString()},
            {"dialog_title",dialog?dialog->property("projectTitle").toString():QString()},
            {"dialog_description",dialog?dialog->property("projectDescription").toString():QString()},
            {"focus",QGuiApplication::focusObject()?QGuiApplication::focusObject()->objectName():QString()}};
        if(event && (event->type()==QEvent::MouseButtonPress || event->type()==QEvent::MouseButtonRelease)) {
            const auto point=static_cast<QMouseEvent*>(event)->position();
            row["create_contains_press"]=create&&exposed_rect(create).contains(create->mapFromScene(point));
            if(dialog&&dialog->property("visible").toBool()) {
                QQmlExpression expression(qmlContext(dialog),dialog,"standardButton(Dialog.Ok)");
                auto* button=qobject_cast<QQuickItem*>(expression.evaluate().value<QObject*>());
                row["confirm_contains_press"]=button&&button->isVisible()&&button->isEnabled()&&exposed_rect(button).contains(button->mapFromScene(point));
                if(expression.hasError())row["confirm_lookup_error"]=expression.error().toString();
            }
        }
        ui_sequence.push_back(row);
    };
    ui_inputs.observe=ui_record;window->installEventFilter(&ui_inputs);
    QObject::connect(observed->assistant(),&edi_app::AssistantViewModel::actionPointerShown,&ui_inputs,[&]{ui_record("pointer_shown");});
    QObject::connect(observed->assistant(),&edi_app::AssistantViewModel::actionPointerMoved,&ui_inputs,[&]{ui_record("pointer_moved");});
    QObject::connect(observed->assistant(),&edi_app::AssistantViewModel::actionPointerPressed,&ui_inputs,[&]{ui_record("pointer_pressed");});
    QObject::connect(observed->assistant(),&edi_app::AssistantViewModel::actionPointerHidden,&ui_inputs,[&]{ui_record("pointer_hidden");});
    QObject::connect(observed,&edi_app::Session::projectChanged,&ui_inputs,[&]{ui_record("project_changed");});
    auto ui_snapshot=[&]()->Object {
        if(!observed || !window) return {{"alive",false}};
        QQmlExpression expression(qmlContext(window),window,"Session.assistant");
        auto qml_assistant=expression.evaluate().value<QObject*>();
        Array texts,controls;
        for(auto* object:objects(window)) {
            if(auto* item=qobject_cast<QQuickItem*>(object); item && item->isVisible() && object->property("text").isValid())
                texts.push_back(text_observation(object));
            if(auto* item=qobject_cast<QQuickItem*>(object);item&&!object->objectName().isEmpty())
                controls.push_back(Object{{"name",object->objectName()},{"visible",item->isVisible()},
                    {"enabled",item->isEnabled()},{"width",item->width()},{"height",item->height()},
                    {"x",item->mapToScene(QPointF()).x()},{"y",item->mapToScene(QPointF()).y()},
                    {"exposed",!exposed_rect(item).isEmpty()},
                    {"fully_exposed",exposed_rect(item).contains(item->boundingRect())},
                    {"parameter_path",object->property("item").value<QObject*>()?
                        object->property("item").value<QObject*>()->property("path").toString():QString()}});
        }
        auto* assistant=observed->assistant();
        Object project;
        if(observed->project()) {
            const auto& model=observed->project()->project();
            Array backgrounds,structures,parameters,aliases,constraints;
            for(const auto& structure:model.structures) {
                Array sites;
                for(const auto& site:structure->atom_sites)
                    sites.push_back(Object{{"id",QString::fromStdString(site->id.value())},
                        {"type",QString::fromStdString(site->type_symbol.value())},
                        {"wyckoff",QString::fromStdString(site->wyckoff_letter.value())},
                        {"x",site->fract_x.value.get()},{"y",site->fract_y.value.get()},
                        {"z",site->fract_z.value.get()},{"occupancy",site->occupancy.value.get()}});
                structures.push_back(Object{{"id",QString::fromStdString(structure->name.value())},
                    {"length_a",structure->cell.length_a.value.get()},
                    {"length_b",structure->cell.length_b.value.get()},
                    {"length_c",structure->cell.length_c.value.get()},
                    {"gamma",structure->cell.angle_gamma.value.get()},
                    {"sites",static_cast<int>(structure->atom_sites.size())},{"atom_rows",sites}});
            }
            for(const auto& entry:edi::parameter_entries(const_cast<edi::Project&>(model))) {
                const auto& p=*entry.parameter;
                parameters.push_back(Object{{"path",QString::fromStdString(entry.path)},
                    {"category",QString::fromStdString(entry.category)},
                    {"field",QString::fromStdString(entry.name)},
                    {"row_label",QString::fromStdString(entry.row_label)},
                    {"value",p.value.get()},{"free",p.free.get()},{"refinable",entry.refinable},
                    {"fit_blocker",static_cast<int>(p.fit_blocker)},
                    {"fit_reason",QString::fromStdString(p.fit_reason)},
                    {"dependence",static_cast<int>(p.dependence)}});
            }
            for(const auto& alias:model.aliases)
                aliases.push_back(Object{{"id",QString::fromStdString(alias->id.value())},
                    {"parameter",QString::fromStdString(alias->parameter_unique_name.value())}});
            for(const auto& constraint:model.constraints)
                constraints.push_back(Object{{"id",QString::fromStdString(constraint->id.value())},
                    {"expression",QString::fromStdString(constraint->expression.value())},
                    {"enabled",constraint->enabled.get()}});
            for(const auto& bank:model.experiments) {
                Array points,input_rows;
                if(bank->data) {
                    const auto available=std::min({bank->data->axis().size(),bank->data->intensity_meas.size(),std::size_t{4}});
                    for(std::size_t i=0;i<available;++i)
                        input_rows.push_back(Array{bank->data->axis()[i],bank->data->intensity_meas[i],
                            i<bank->data->intensity_meas_su.size()?QJsonValue(bank->data->intensity_meas_su[i]):QJsonValue()});
                }
                for(const auto& point:bank->background)
                    points.push_back(Object{{"id",QString::fromStdString(point->id.value())},
                        {"position",point->position.get()},{"intensity",point->intensity.value.get()},
                        {"free",point->intensity.free.get()}});
                backgrounds.push_back(Object{{"id",QString::fromStdString(bank->name.value())},
                    {"type",QString::fromStdString(bank->background_type)},
                    {"mode",QString::fromStdString(edi::background_estimate_mode(*bank))},
                    {"reflection_count",bank->reflections?static_cast<double>(bank->reflections->size()):0.0},
                    {"reflection_sigma_count",bank->reflections?static_cast<double>(bank->reflections->intensity_meas_su.size()):0.0},
                    {"has_data",bank->data.has_value()},{"points",points}});
                auto row=backgrounds.last().toObject();
                row["input_count"]=bank->data?static_cast<double>(bank->data->axis().size()):0.0;
                row["calculation_only"]=bank->calculation_only;
                row["input_intensity_count"]=bank->data?static_cast<double>(bank->data->intensity_meas.size()):0.0;
                row["input_sigma_count"]=bank->data?static_cast<double>(bank->data->intensity_meas_su.size()):0.0;
                row["measured_columns_equal_length"]=bank->data?QJsonValue(bank->data->axis().size()==bank->data->intensity_meas.size() && bank->data->axis().size()==bank->data->intensity_meas_su.size()):QJsonValue();
                if(bank->reflections) {
                    const auto& data=*bank->reflections;
                    row["reflection_columns"]=Object{{"h",static_cast<double>(data.index_h.get().size())},{"k",static_cast<double>(data.index_k.get().size())},{"l",static_cast<double>(data.index_l.get().size())},
                        {"intensity",static_cast<double>(data.intensity_meas.get().size())},{"sigma",static_cast<double>(data.intensity_meas_su.get().size())},{"wavelength",static_cast<double>(data.wavelength.get().size())}};
                    row["reflection_columns_rectangular"]=data.rectangular();
                }
                Array terms;
                for(const auto& term:bank->background_terms) terms.push_back(Object{
                    {"id",QString::fromStdString(term->id.value())},{"order",term->order.get()},
                    {"coefficient",term->coef.value.get()},{"free",term->coef.free.get()},
                    {"uncertainty",term->coef.uncertainty.get()?QJsonValue(*term->coef.uncertainty.get()):QJsonValue()}});
                row["term_rows"]=terms;
                row["input_first"]=input_rows;backgrounds[backgrounds.size()-1]=row;
            }
            project={{"name",QString::fromStdString(model.metadata.name)},
                     {"path",observed->project()->path()},
                     {"structures",static_cast<int>(model.structures.size())},
                     {"structure_rows",structures},{"parameters",parameters},
                     {"aliases",aliases},{"constraints",constraints},
                     {"backgrounds",backgrounds},
                     {"calculating",observed->project()->calculating()},
                     {"cell_a",model.structures.size()!=1?QJsonValue():QJsonValue(model.structures.front()->cell.length_a.value.get())},
                     {"cell_a_free",model.structures.size()!=1?QJsonValue():QJsonValue(model.structures.front()->cell.length_a.free.get())},
                     {"report_embedded",observed->project()->report()->embedLibraries()},
                     {"can_undo",observed->project()->canUndo()}};
        }
        return {{"alive",true},
                {"environment",Object{{"documents_root",QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation)},
                    {"temporary_documents_root",temporary_documents},
                    {"policy","Temporary XDG user-dirs Documents parent; no project destination seeded; HOME/auth untouched"}}},
                {"singleton_identity",singleton==observed&&qml_assistant==observed->assistant()},
                {"engine_parent",observed->parent()==engine.get()},
                {"cpp_ownership",QJSEngine::objectOwnership(observed)==QJSEngine::CppOwnership},
                {"connected",assistant->connected()},{"state",assistant->state()},
                {"available_efforts",QJsonArray::fromStringList(assistant->availableEfforts())},
                {"selected_effort",assistant->selectedEffort()},
                {"last_error",assistant->lastError()},{"messages",model_rows(assistant->messages())},
                // Read the original current Session model without marking it viewed or dismissing history.
                {"app_messages",Object{{"rows",model_rows(observed->loadWarnings())},
                    {"count",observed->loadWarnings()->count()},
                    {"unviewed_count",observed->loadWarnings()->unviewedCount()}}},
                {"show_actions",assistant->showActions()},
                {"action_transitions",action_transitions},{"ui_sequence",ui_sequence},
                {"work_report",QJsonObject::fromVariantMap(assistant->workReportReceipt())},
                {"context",assistant->contextPreview()},
                {"context_consent_required",assistant->contextConsentRequired()},
                {"selected_files",model_rows(assistant->selectedFiles())},
                {"models",model_rows(assistant->models())},{"pending_plan",QJsonObject::fromVariantMap(assistant->pendingPlan())},
                {"pending_question",QJsonObject::fromVariantMap(assistant->pendingQuestion())},
                {"active_job",assistant->activeJobId()},{"can_cancel",assistant->canCancel()},
                {"project",project},{"texts",texts},{"controls",controls},
                {"disclosures",disclosures},{"width",window->width()},{"height",window->height()}};
    };
    auto close_owned_session_write=[&]() {
        if(!observed || !window || qEnvironmentVariable("EDI_TEST_CODEX_PEER_INPUT").isEmpty())
            throw std::runtime_error("controlled write fault requires the original scripted-fixture Main owner");
        QPointer<edi_app::AssistantViewModel> vm=observed->assistant();
        QPointer<edi_app::CodexAgent> agent;QPointer<QProcess> child;
        const auto expected=QFileInfo(qEnvironmentVariable("EDI_CODEX_DEVELOPMENT_EXECUTABLE")).canonicalFilePath();
        const auto fixture=QFileInfo(qEnvironmentVariable("EDI_TEST_CODEX_PEER_INPUT")).canonicalPath();
        if(expected.isEmpty() || fixture.isEmpty() || QFileInfo(expected).canonicalPath()!=fixture)
            throw std::runtime_error("write fault refuses any process outside the exact owned fixture directory");
        for(auto* candidate:vm->findChildren<edi_app::CodexAgent*>()) {
            if(candidate->parent()!=vm || candidate->outputOwnerState()!=edi_app::CodexAgent::OutputOwnerState::Live)continue;
            for(auto* process:candidate->findChildren<QProcess*>(QString(),Qt::FindDirectChildrenOnly)) {
                if(process->state()!=QProcess::Running || QFileInfo(process->program()).canonicalFilePath()!=expected)continue;
                if(child)throw std::runtime_error("ambiguous owned scripted runtime child");
                child=process;agent=candidate;
            }
        }
        if(!child || !agent || child->parent()!=agent || !vm || observed->assistant()!=vm)
            throw std::runtime_error("the original current scripted runtime child was not proved");
        const auto pid=child->processId();qlonglong parent=-1;
#if defined(Q_OS_LINUX)
        QFile status(QStringLiteral("/proc/")+QString::number(pid)+"/status");
        if(status.open(QIODevice::ReadOnly))for(const auto& line:status.readAll().split('\n'))
            if(line.startsWith("PPid:"))parent=line.mid(5).trimmed().toLongLong();
#endif
        if(parent!=QCoreApplication::applicationPid())throw std::runtime_error("actual owned child OS parent was not proved on this platform");
        session_fault_facts["write_child_pid"]=QString::number(pid);
        session_fault_facts["write_child_parent"]=QString::number(parent);
        session_fault_facts["script_path"]=expected;
        session_fault_facts["original_vm_child"]=true;
        QObject::disconnect(session_transport_failure_watch);
        session_transport_failure_watch=QObject::connect(agent.data(),&edi_app::CodexAgent::failed,&session_fault_observer,[&](const QString& error){
            session_fault_facts["actual_transport_error"]=error;
            session_fault_facts["actual_transport_failed_signal"]=true;
        },Qt::DirectConnection);
        child->closeWriteChannel();session_fault_facts["public_close_write_channel_invoked"]=true;
    };
    const auto execute_command=[&](const QByteArray& line) {
        try {
            auto input=decode(line).toObject();
            auto op=input["op"].toString();Object result;
            if((!observed || !window) && op!="inspect" && op!="destroy" && op!="session_fault_facts")throw std::runtime_error("the original Main owner has retired");
            if(op=="message_input") {
                const auto identity=input["row_id"].toString(),name=input["name"].toString();
                const auto action=input["action"].toString("click");
                if(identity.isEmpty() || (name!="assistant.activity.toggle" && name!="assistant.activity.copy"))
                    throw std::invalid_argument("exact original row identity and declared activity control required");
                QPointer<QQuickItem> target,original_row;
                for(auto* object:objects(window)) {
                    auto* item=qobject_cast<QQuickItem*>(object);
                    if(!item || item->objectName()!=name)continue;
                    for(auto* ancestor=item->parentItem();ancestor;ancestor=ancestor->parentItem())
                        if(ancestor->property("rowId").toString()==identity) {
                            if(target && target!=item)throw std::runtime_error("ambiguous realized original row control");
                            target=item;original_row=ancestor;break;
                        }
                }
                if(!target || !original_row) {
                    result={{"reached",false},{"reason","original row/control is not realized"},{"row_id",identity}};
                } else {
                    const auto scene=target->mapToScene(QPointF(target->width()/2,target->height()/2));
                    bool exposed=target->window()==window && target->isVisible() && target->isEnabled()
                        && target->width()>0 && target->height()>0 && QRectF(0,0,window->width(),window->height()).contains(scene);
                    for(auto* ancestor=target->parentItem();ancestor;ancestor=ancestor->parentItem())
                        if(!ancestor->isVisible() || !ancestor->isEnabled() || (ancestor->clip()
                            && !QRectF(0,0,ancestor->width(),ancestor->height()).contains(ancestor->mapFromScene(scene))))exposed=false;
                    if(!exposed)result={{"reached",false},{"reason","original control center is not exposed in its original window/clipping ancestors"},{"row_id",identity}};
                    else {
                        if(action=="hover") {QTest::mouseMove(window,scene.toPoint());drain();}
                        else if(action=="click")click(target);
                        else throw std::invalid_argument("only genuine mouse click/hover is supported");
                        result={{"reached",true},{"row_id",identity},{"name",name},{"action",action},
                            {"same_row_after",bool(original_row)&&original_row->property("rowId").toString()==identity},
                            {"same_window_after",bool(target)&&target->window()==window},
                            {"clipboard",QGuiApplication::clipboard()->text()}};
                    }
                }
            } else
            if(op=="messages_probe") {
                const auto model_name=input["model"].toString("messages");
                const auto property=observed->assistant()->property(model_name.toUtf8().constData());
                auto* model=qobject_cast<edi_app::RowTableModel*>(property.value<QObject*>());
                if(!model)throw std::invalid_argument("an actual public Assistant RowTableModel property is required");
                const auto mode=input["mode"].toString("snapshot");
                const auto role_names=model->roleNames();
                auto role_number=[&](const QString& name) {for(auto it=role_names.cbegin();it!=role_names.cend();++it)if(it.value()==name.toUtf8())return it.key();return -1;};
                if(mode=="watch") {
                    stop_message_model_watch();message_model_events=Array{};message_model_watched=model;capture_message_cells=input["capture_cells"].toBool();message_model_cells=capture_message_cells?snapshot_message_cells():Array{};
                    message_model_connections.push_back(QObject::connect(model,&QAbstractItemModel::dataChanged,&message_model_observer,
                        [&](const QModelIndex& first,const QModelIndex& last,const QList<int>& roles){
                            Array names,all;
                            const auto live=message_model_watched?message_model_watched->roleNames():QHash<int,QByteArray>{};
                            for(const auto role:roles)names.append(QString::fromUtf8(live.value(role,QByteArray::number(role))));
                            for(auto it=live.cbegin();it!=live.cend();++it)all.append(QString::fromUtf8(it.value()));
                            Object event{{"kind","dataChanged"},{"first",first.row()},{"last",last.row()},{"roles",names},{"all_role_names",all}};
                            if(capture_message_cells) {
                                const auto after=snapshot_message_cells();Array changed;
                                for(qsizetype row=0;row<after.size();++row) {
                                    const auto next=after[row].toObject();
                                    const auto before=row<message_model_cells.size()?message_model_cells[row].toObject():Object{};
                                    for(auto it=next.begin();it!=next.end();++it)
                                        if(before.value(it.key())!=it.value())changed.append(Object{{"row",static_cast<int>(row)},{"role",it.key()}});
                                }
                                event["changed_cells"]=changed;message_model_cells=after;
                            }
                            message_model_events.append(event);
                        }));
                    message_model_connections.push_back(QObject::connect(model,&QAbstractItemModel::rowsInserted,&message_model_observer,[&](const QModelIndex&,int first,int last){message_model_events.append(Object{{"kind","insert"},{"first",first},{"last",last}});if(capture_message_cells)message_model_cells=snapshot_message_cells();}));
                    message_model_connections.push_back(QObject::connect(model,&QAbstractItemModel::rowsRemoved,&message_model_observer,[&](const QModelIndex&,int first,int last){message_model_events.append(Object{{"kind","remove"},{"first",first},{"last",last}});if(capture_message_cells)message_model_cells=snapshot_message_cells();}));
                    message_model_connections.push_back(QObject::connect(model,&QAbstractItemModel::rowsMoved,&message_model_observer,[&](const QModelIndex&,int first,int last,const QModelIndex&,int destination){message_model_events.append(Object{{"kind","move"},{"first",first},{"last",last},{"destination",destination}});if(capture_message_cells)message_model_cells=snapshot_message_cells();}));
                    message_model_connections.push_back(QObject::connect(model,&QAbstractItemModel::modelReset,&message_model_observer,[&]{message_model_events.append(Object{{"kind","reset"}});if(capture_message_cells)message_model_cells=snapshot_message_cells();}));
                } else if(mode=="events") {
                    result["events"]=message_model_events;
                    if(input["clear"].toBool())message_model_events=Array{};
                } else if(mode=="stop") {
                    result["events"]=message_model_events;stop_message_model_watch();
                } else if(mode=="send") {
                    observed->assistant()->send(input["text"].toString());
                } else if(mode=="read" || mode=="roles") {
                    const int row=input["row"].toInt(-1);
                    if(row<0 || row>=model->count())throw std::invalid_argument("an existing public model row is required");
                    if(mode=="read") {
                        const auto role=input["role"].toString();const auto number=role_number(role);const auto api=input["api"].toString("data");
                        const int repetitions=input["repetitions"].toInt(1);
                        if((model_name=="messages" && !QStringList{"id","kind","text","status"}.contains(role)) || number<0 || (api!="data" && api!="get") || repetitions<1 || repetitions>4096)throw std::invalid_argument("finite public role read required");
                        const auto index=model->index(row);QVariant value;QElapsedTimer timer;timer.start();
                        for(int n=0;n<repetitions;++n)value=api=="data"?model->data(index,number):model->get(row,role);
                        const auto elapsed=timer.nsecsElapsed();
                        result["read"]=Object{{"api",api},{"role",role},{"repetitions",repetitions},{"elapsed_ns",static_cast<double>(elapsed)},{"type",QString::fromUtf8(value.typeName()?value.typeName():"")},{"scalar",QJsonValue::fromVariant(value)}};
                    } else {
                        Array roles;const auto marker=input["marker"].toString().toUtf8();
                        for(auto it=role_names.cbegin();it!=role_names.cend();++it) {
                            const auto value=model->data(model->index(row),it.key());
                            const auto encoded=encode(Object{{"value",QJsonValue::fromVariant(value)}});
                            roles.append(Object{{"name",QString::fromUtf8(it.value())},{"type",QString::fromUtf8(value.typeName()?value.typeName():"")},
                                {"encoded_bytes",static_cast<double>(encoded.size())},{"sha256",QString::fromLatin1(QCryptographicHash::hash(encoded,QCryptographicHash::Sha256).toHex())},
                                {"marker_present",!marker.isEmpty()&&encoded.contains(marker)}});
                        }
                        result["roles"]=roles;
                    }
                } else if(mode!="snapshot")throw std::invalid_argument("unknown finite messages probe mode");
                result["model"]=model_name;result["count"]=model->count();result["state"]=observed->assistant()->state();
                Array names;for(auto it=role_names.cbegin();it!=role_names.cend();++it)names.append(QString::fromUtf8(it.value()));result["role_names"]=names;
            } else
            if(op=="missing_constructor") {
                auto incomplete=fixture.dependencies;
                switch(input["index"].toInt()) {
                    case 0: incomplete.request={};break;
                    case 1: incomplete.open_browser={};break;
                    case 2: incomplete.read_record={};break;
                    case 3: incomplete.write_record={};break;
                    case 4: incomplete.erase_record={};break;
                    case 5: incomplete.list_registrations={};break;
                    case 6: incomplete.unix_seconds={};break;
                    case 7: incomplete.monotonic_ms={};break;
                }
                auto count=fixture.services.size();bool rejected=false;
                try {
                    if(input["owner"].toString()=="session") {edi_app::Session invalid(std::move(incomplete),nullptr);}
                    else {edi_app::AssistantViewModel invalid(std::move(incomplete),nullptr);}
                } catch(const std::invalid_argument&) {rejected=true;}
                result={{"rejected",rejected},{"service_calls",static_cast<double>(fixture.services.size()-count)}};
            } else if(op=="configure_refusal") {
                auto candidate=std::make_unique<edi_app::Session>(fixture.dependencies,nullptr);
                if(input["kind"].toString()=="null") candidate.reset();
                if(input["kind"].toString()=="parented") candidate->setParent(engine.get());
                bool rejected=false;
                try {edi_app::configure_engine(*engine,std::move(candidate));}
                catch(const std::invalid_argument&) {rejected=true;}
                result={{"rejected",rejected},{"original_preserved",engine->singletonInstance<edi_app::Session*>("edi.app","Session")==observed}};
            } else if(op=="sign_in") {click(find("assistant.connection"));if(!accept_dialog()) throw std::runtime_error("real connection disclosure dialog not available");}
            else if(op=="accept_context") observed->assistant()->signIn();
            else if(op=="refresh_usage") observed->assistant()->refreshUsage();
            else if(op=="tool_specs") result={{"tools",edi_app::assistant_native_tool_specs()}};
            else if(op=="embedded_skills") {
                Array resources;
                for(const auto& skill:edi::assistant::detail::skill_resource_data())
                    resources.push_back(Object{{"id",QString::fromUtf8(skill.id.data(),skill.id.size())},
                        {"sha256",QString::fromUtf8(skill.sha256.data(),skill.sha256.size())},
                        {"content",QString::fromUtf8(skill.content.data(),skill.content.size())}});
                const auto index=edi::assistant::detail::skill_index_data();
                result={{"index",QJsonDocument::fromJson(QByteArray(index.data(),index.size())).object()},
                    {"resources",resources}};
            }
            else if(op=="capture_frame") {
                const auto path=input["path"].toString();
                if(path.isEmpty()||!window->isExposed())throw std::runtime_error("current Main frame is not exposed");
                const auto image=window->grabWindow();
                result={{"saved",!image.isNull()&&image.save(path)},{"width",image.width()},{"height",image.height()}};
            }
            else if(op=="scientific_receipt") {
                if(!observed->project())throw std::runtime_error("scientific receipt requires current project");
                Array files;
                for(const auto& [path,text]:observed->project()->savedFiles())
                    files.append(Object{{"relative",QString::fromStdString(path)},{"text",QString::fromStdString(text)}});
                result={{"files",files}};
            }
            else if(op=="open_first_example") {
                const auto ids=edi_app::ExampleListModel::bundledIds();
                if(ids.empty())throw std::runtime_error("no actual bundled example available");
                result={{"id",ids.front()},{"opened",observed->openExample(ids.front())}};
            }
            else if(op=="pending_open_save_as") {
                const auto source=input["source"].toString(),destination=input["destination"].toString();
                auto read=[&]{QFile f(source);return f.open(QIODevice::ReadOnly)?f.readAll():QByteArray();};
                const auto original=read();
                if(original.isEmpty())throw std::runtime_error("pending Open source is absent before its native action");
                bool armed=true,hooked=false,saved=false,source_during=false;QString hook_error;
                QMetaObject::Connection path_connection;
                const auto changed=QObject::connect(observed,&edi_app::Session::projectChanged,observed,[&]{
                    if(!armed||!observed->project())return;
                    auto* owner=observed->project();
                    path_connection=QObject::connect(owner,&edi_app::ProjectViewModel::pathChanged,observed,[&,owner]{
                        if(!armed||observed->project()!=owner)return;
                        armed=false;hooked=true;
                        try {saved=observed->saveAs(QUrl::fromLocalFile(destination));source_during=read()==original;}
                        catch(const std::exception& e){hook_error=QString::fromUtf8(e.what());}
                    });
                });
                bool opened=false;
                try{opened=observed->openProject(QUrl::fromLocalFile(source));}
                catch(...){QObject::disconnect(changed);QObject::disconnect(path_connection);throw;}
                QObject::disconnect(changed);QObject::disconnect(path_connection);
                result={{"opened",opened},{"hooked",hooked},{"saved",saved},{"source_preserved_during_pending_save",source_during},
                    {"hook_error",hook_error},{"location",observed->locationText()},
                    {"current_path",observed->project()?observed->project()->path():QString()}};
            }
            else if(op=="live_worker_root_boundary") {
                const QPointer<edi_app::ProjectViewModel> original=observed->project();
                if(!original)throw std::runtime_error("live root witness requires original native owner");
                const auto root=original->project().scan_data_root.empty()?original->path():QString::fromStdString(original->project().scan_data_root);
                const auto files=QDir(root+"/experiments").entryList({"*.edi"},QDir::Files,QDir::Name);
                if(files.empty())throw std::runtime_error("live root witness requires real native experiment file");
                const auto file=root+"/experiments/"+files.front();
                QTemporaryDir links(QDir::tempPath()+"/edi-root-identity-XXXXXX");
                if(!links.isValid())throw std::runtime_error("root identity link directory unavailable");
                const auto link=links.filePath("original-native-inode");
                std::filesystem::create_hard_link(file.toStdString(),link.toStdString());
                struct Reader {std::mutex mutex;std::condition_variable cv;std::atomic<bool> entered{false},done{false},release{false};bool before=false,after=false;};
                const auto reader=std::make_shared<Reader>();
                original->assistantWorker().submit("tests.actual-root-reader",[reader,file,link](const edi::work::CancelToken& cancel,const edi::work::Emit&)->edi::work::Delivery{
                    auto read=[&]{QFile f(file);return f.open(QIODevice::ReadOnly)?f.readAll():QByteArray();};
                    const auto bytes=read();reader->before=!bytes.isEmpty();reader->entered=true;reader->cv.notify_all();
                    {std::unique_lock lock(reader->mutex);while(!cancel.cancelled()&&!reader->release)reader->cv.wait_for(lock,std::chrono::milliseconds(1));}
                    std::error_code error;
                    reader->after=read()==bytes&&std::filesystem::equivalent(file.toStdString(),link.toStdString(),error)&&!error;
                    reader->done=true;reader->cv.notify_all();return {};
                });
                {std::unique_lock lock(reader->mutex);if(!reader->cv.wait_for(lock,std::chrono::seconds(2),[&]{return reader->entered.load();})){reader->release=true;reader->cv.notify_all();throw std::runtime_error("actual model Worker did not enter native file read");}}
                auto preserved=[&]{std::error_code error;return std::filesystem::equivalent(file.toStdString(),link.toStdString(),error)&&!error;};
                const auto kind=input["kind"].toString();bool nested=false,nested_opened=false,about=false,protected_about=false,protected_nested=false;
                const auto about_connection=QObject::connect(observed,&edi_app::Session::projectAboutToChange,observed,[&]{
                    if(observed->project()==original){about=true;protected_about=preserved();}
                });
                QMetaObject::Connection changed;
                if(kind=="nested")changed=QObject::connect(observed,&edi_app::Session::projectChanged,observed,[&]{
                    if(nested)return;nested=true;
                    nested_opened=observed->openProject(QUrl::fromLocalFile(input["successor"].toString()));
                    protected_nested=reader->done.load()?reader->after:preserved();
                });
                bool opened=false;QString operation_error;
                try {
                    opened=kind=="example"?observed->openExample(input["target"].toString()):observed->openProject(QUrl::fromLocalFile(input["target"].toString()));
                }catch(const std::exception& e){operation_error=QString::fromUtf8(e.what());}
                QObject::disconnect(changed);QObject::disconnect(about_connection);drain(40);
                const bool retired_destroyed=original.isNull();
                const bool protected_while_live=reader->done.load()?reader->after:preserved();
                reader->release=true;reader->cv.notify_all();
                bool done=false;{std::unique_lock lock(reader->mutex);done=reader->cv.wait_for(lock,std::chrono::seconds(2),[&]{return reader->done.load();});}
                result={{"opened",opened},{"operation_error",operation_error},{"about_reached",about},{"file_identity_at_about",protected_about},
                    {"nested_reached",nested},{"nested_opened",nested_opened},{"file_preserved_after_nested",protected_nested},
                    {"original_destroyed",retired_destroyed},{"file_preserved_while_worker_live",protected_while_live},
                    {"actual_worker_entered",reader->entered.load()},{"actual_worker_finished",done},{"native_file_read_before",reader->before},{"native_file_read_after",reader->after},
                    {"native_fit_exercised",false},{"original_root",root}};
            }
            else if(op=="evaluate") {
                QQmlExpression expression(qmlContext(window),window,input["expression"].toString());
                const auto value=expression.evaluate();
                if(expression.hasError())throw std::runtime_error(expression.error().toString().toStdString());
                result={{"value",QJsonValue::fromVariant(value)}};
            } else if(op=="session_wheel") {
                QPointer<QQuickItem> target=qobject_cast<QQuickItem*>(find("assistant.sessions.list"));
                const int delta=input["angle_y"].toInt(-120);
                if(!target || target->window()!=window || !target->isVisible() || !target->isEnabled()
                    || target->width()<=0 || target->height()<=0 || (delta!=-120 && delta!=120))
                    throw std::runtime_error("original current sessions viewport is not exposed for one real wheel step");
                const auto scene=target->mapToScene(QPointF(target->width()/2,target->height()/2));
                bool clipped=!QRectF(0,0,window->width(),window->height()).contains(scene);
                for(auto* parent=target->parentItem();parent;parent=parent->parentItem())
                    if(!parent->isVisible() || !parent->isEnabled() || (parent->clip()
                        && !QRectF(0,0,parent->width(),parent->height()).contains(parent->mapFromScene(scene))))clipped=true;
                if(clipped)throw std::runtime_error("original sessions wheel center is clipped");
                const auto before=target->property("contentY").toDouble();
                auto current_source=[&]() -> QObject* {if(!target)return nullptr;const auto value=target->property("sourceModel");return value.metaType()==QMetaType::fromType<QJSValue>()?value.value<QJSValue>().toQObject():value.value<QObject*>();};
                QPointer<QObject> source=current_source();
                const auto count=target->property("count").toInt();
                QWheelEvent wheel(scene,window->mapToGlobal(scene.toPoint()),QPoint{},QPoint(0,delta),
                    Qt::NoButton,Qt::NoModifier,Qt::NoScrollPhase,false);
                wheel.setAccepted(false);QCoreApplication::sendEvent(window,&wheel);drain();
                result={{"name","assistant.sessions.list"},{"accepted",wheel.isAccepted()},
                    {"content_y_before",before},{"content_y_after",target?target->property("contentY").toDouble():before},
                    {"count_before",count},{"count_after",target?target->property("count").toInt():0},
                    {"same_window",bool(target)&&target->window()==window},
                    {"same_source_model",bool(target)&&source&&current_source()==source.data()}};
            }
            else if(op=="manual_key") {
                const auto key=input["key"].toString();
                if(key=="select_all")QTest::keyClick(window,Qt::Key_A,Qt::ControlModifier);
                else if(key=="return")QTest::keyClick(window,Qt::Key_Return);
                else if(key=="escape")QTest::keyClick(window,Qt::Key_Escape);
                else if(key=="tab")QTest::keyClick(window,Qt::Key_Tab);
                else throw std::invalid_argument("unsupported finite manual key");
            } else if(op=="manual_text") {
                for(const QChar character:input["text"].toString()) {
                    QKeyEvent press(QEvent::KeyPress,0,Qt::NoModifier,QString(character));
                    QKeyEvent release(QEvent::KeyRelease,0,Qt::NoModifier,QString(character));
                    QCoreApplication::sendEvent(window,&press);QCoreApplication::sendEvent(window,&release);
                }
            } else if(op=="manual_ime") {
                auto* focus=QGuiApplication::focusObject();
                if(!focus)throw std::runtime_error("actual focused input is missing");
                QInputMethodEvent event(input["preedit"].toString(),{});
                event.setCommitString(input["commit"].toString());
                QCoreApplication::sendEvent(focus,&event);
            } else if(op=="focused_input") {
                auto* focus=QGuiApplication::focusObject();
                result={{"name",focus?focus->objectName():QString()},
                    {"text",focus?focus->property("text").toString():QString()},
                    {"preedit",focus?focus->property("preeditText").toString():QString()}};
            } else if(op=="ui_property") {
                auto* object=find(input["name"].toString());
                if(!object)throw std::runtime_error("actual requested control is absent");
                if(input.contains("value") && !object->setProperty(input["property"].toString().toUtf8().constData(),input["value"].toVariant()))
                    throw std::runtime_error("actual control property is not writable");
                result={{"value",QJsonValue::fromVariant(object->property(input["property"].toString().toUtf8().constData()))}};
            } else if(op=="file_answer") {
                bool found=false;
                for(auto* object:objects(window)) {
                    if(!object->property("visible").toBool() || !object->property("selectedFile").isValid())continue;
                    if(input["reject"].toBool()) {
                        if(!QMetaObject::invokeMethod(object,"reject"))throw std::runtime_error("ordinary file dialog rejection unavailable");
                    } else {
                        if(!object->setProperty("selectedFile",QUrl::fromLocalFile(input["path"].toString())) ||
                           !QMetaObject::invokeMethod(object,"accept"))throw std::runtime_error("ordinary file dialog selection/acceptance unavailable");
                    }
                    found=true;break;
                }
                result={{"answered",found}};
            } else if(op=="arm_estimate_publication") {
                QObject::disconnect(publication_fault);publication_fault_hits=0;publication_undo_seen=false;
                auto* owner=observed->project();
                if(!owner)throw std::runtime_error("publication fixture requires current actual project");
                const auto mode=input["mode"].toString();
                const auto minimum=input["minimum_points"].toInt();
                const auto replacement=input["replacement"].toString();
                publication_fault=QObject::connect(owner,&edi_app::ProjectViewModel::projectEdited,owner,[&,mode,owner,minimum,replacement] {
                    if(minimum && (owner->project().experiments.empty() || owner->project().experiment().background.size()<static_cast<std::size_t>(minimum)))return;
                    if(publication_fault_hits++)return;
                    publication_undo_seen=owner->canUndo();
                    if(mode=="retire")observed->closeProject();
                    else if(mode=="replace")observed->openProject(QUrl::fromLocalFile(replacement));
                    else if(mode=="bad_alloc")throw std::bad_alloc();
                    else throw std::runtime_error("independent actual postwrite publication failure");
                },Qt::DirectConnection);
            } else if(op=="publication_fault") {
                result={{"hits",publication_fault_hits},{"undo_seen",publication_undo_seen}};
            } else if(op=="estimate_outcome") {
                const auto receipt=observed->project()->estimateBackgroundOutcome();
                result={{"applied",receipt.applied},{"published",receipt.published},{"message",receipt.message}};
            } else if(op=="capture_sequence") {
                Array receipts;
                receipts.push_back(QJsonObject::fromVariantMap(observed->assistant()->captureWorkReport()));
                if(input["move"].isString())
                    result["moved"]=observed->saveProjectAs(QUrl::fromLocalFile(input["move"].toString()),false,false);
                if(input["successor"].isString()) {
                    result["opened"]=observed->openProject(QUrl::fromLocalFile(input["successor"].toString()));
                    observed->assistant()->signIn();
                    observed->assistant()->send(input["text"].toString());
                }
                receipts.push_back(QJsonObject::fromVariantMap(observed->assistant()->captureWorkReport()));
                result["receipts"]=receipts;
            }
            else if(op=="show_actions") observed->assistant()->setShowActions(input["enabled"].toBool());
            else if(op=="selected_begin") result={{"token",observed->assistant()->beginFileSelection()}};
            else if(op=="selected_add") {
                QList<QUrl> files;
                for(const auto& path:input["paths"].toArray())files.push_back(QUrl::fromLocalFile(path.toString()));
                result={{"added",observed->assistant()->addSelectedFiles(input["token"].toString(),files)}};
            }
            else if(op=="send_text") {
                auto* composer=find("assistant.composer");
                if(!composer || !composer->setProperty("text",input["text"].toString())) throw std::runtime_error("actual composer text property unavailable");
                click(find("assistant.send"));
            } else if(op=="accept_dialog") result={{"accepted",accept_dialog()}};
            else if(op=="sc_input") {
                if(!observed->project())throw std::runtime_error("SC input witness requires actual current native project");
                auto& model=*observed->project()->assistantProject();
                if(model.experiments.empty()||!model.experiments.front()->reflections)throw std::runtime_error("published SC reflections unavailable");
                auto& bank=*model.experiments.front();auto& data=*bank.reflections;
                const auto mode=input["mode"].toString("snapshot"),field=input["field"].toString();
                if(mode!="snapshot"&&mode!="column"&&mode!="equal"&&mode!="replace"&&mode!="truncate")throw std::invalid_argument("finite SC witness mode required");
                if(mode!="snapshot") {
                    if(field=="sample_form") {
                        if(input["value"]!="powder"&&input["value"]!="single crystal")throw std::invalid_argument("finite declared sample form required");
                        bank.experiment_type.sample_form=input["value"]=="powder"?edi::SampleFormEnum::POWDER:edi::SampleFormEnum::SINGLE_CRYSTAL;
                    } else if(field=="computed") {
                        auto values=data.intensity_calc.values();if(values.empty())throw std::runtime_error("published calculated control unavailable");
                        values.front()+=input["value"].toDouble();data.intensity_calc=edi::ComputedColumn<double>(std::make_shared<const std::vector<double>>(std::move(values)));
                    } else {
                        const auto change=[&](auto& column) {
                            auto values=column.get();using Value=typename std::remove_cvref_t<decltype(values)>::value_type;
                            if(mode=="truncate") {
                                const auto count=input["count"].toInt(-1);
                                if(count<0 || static_cast<std::size_t>(count)>values.size())throw std::invalid_argument("an existing measured-column prefix is required");
                                values.resize(static_cast<std::size_t>(count));
                            } else if(values.empty())throw std::runtime_error("genuine measured column required");
                            else if(mode!="equal") {
                                const auto value=input["value"].toDouble(std::numeric_limits<double>::quiet_NaN());
                                if(!std::isfinite(value))throw std::invalid_argument("finite measured replacement required");
                                if constexpr(std::is_integral_v<Value>)if(value!=std::trunc(value)||value<std::numeric_limits<Value>::min()||value>std::numeric_limits<Value>::max())throw std::invalid_argument("int32 measured index required");
                                values.front()=static_cast<Value>(value);
                            }
                            column=std::move(values);
                        };
                        if(field=="h")change(data.index_h);else if(field=="k")change(data.index_k);else if(field=="l")change(data.index_l);
                        else if(field=="intensity")change(data.intensity_meas);else if(field=="sigma")change(data.intensity_meas_su);else if(field=="wavelength")change(data.wavelength);
                        else throw std::invalid_argument("unknown measured SC column");
                        if(mode=="replace") {auto replacement=data;bank.reflections.reset();bank.reflections.emplace(std::move(replacement));}
                    }
                }
                const auto facts=[](const auto& column) {
                    const auto& values=column.get();using Value=typename std::remove_cvref_t<decltype(values)>::value_type;
                    return Object{{"count",static_cast<double>(values.size())},{"element_bytes",static_cast<int>(sizeof(Value))},
                        {"first",values.empty()?QJsonValue():QJsonValue(static_cast<double>(values.front()))},
                        {"last",values.empty()?QJsonValue():QJsonValue(static_cast<double>(values.back()))}};
                };
                const auto& now=*bank.reflections;
                result={{"rectangular",now.rectangular()},{"sample_form",bank.experiment_type.effective_sample_form()==edi::SampleFormEnum::POWDER?"powder":"single crystal"},
                    {"columns",Object{{"h",facts(now.index_h)},{"k",facts(now.index_k)},{"l",facts(now.index_l)},
                        {"intensity",facts(now.intensity_meas)},{"sigma",facts(now.intensity_meas_su)},{"wavelength",facts(now.wavelength)}}}};
                // Deliberately no projectEdited/revision/selected-file mutation: isolate borrowed raw identity.
            }
            else if(op=="outgoing_projection_cases") {
                Array rows;
                for(const auto& value:input["cases"].toArray()) {
                    const auto entry=value.toObject();const auto source=entry.value("source").toObject();
                    const auto role=entry.value("role")=="diagnostic"?edi_app::outgoing::Role::Diagnostic:edi_app::outgoing::Role::Result;
                    try {
                        const auto admitted=edi_app::outgoing::size(source,role);
                        const auto projected=edi_app::outgoing::project(source,role,admitted);
                        const auto bytes=QJsonDocument(projected).toJson(QJsonDocument::Compact);
                        rows.append(Object{{"rejected",false},{"size",static_cast<double>(admitted)},
                            {"wire_bytes",bytes.size()},{"wire",QString::fromUtf8(bytes)},{"projected",projected}});
                    }catch(const std::exception&){rows.append(Object{{"rejected",true}});}
                }
                result={{"cases",rows}};
            }
            else if(op=="transport_timing") {
                auto* agent=observed->assistant()->findChild<edi_app::CodexAgent*>();
                result=agent?edi_app::CodexAgentTestAccess::timing(*agent):Object{{"active",false},{"agent_present",false}};
            }
            else if(op=="transport_clock") {
                if(qEnvironmentVariable("EDI_TEST_CODEX_PEER_INPUT").isEmpty())throw std::runtime_error("internal clock check requires the owned offline peer");
                Object checks;auto require=[&](bool ok,const char* label){checks[label]=ok;if(!ok)throw std::runtime_error(label);};
                const auto executable=edi_app::CodexAgent::executable();
                const auto workspace=QFileInfo(qEnvironmentVariable("EDI_TEST_CODEX_PEER_INPUT")).absolutePath();
                edi_app::CodexAgent agent;int failures=0;bool started=false;
                QObject::connect(&agent,&edi_app::CodexAgent::started,&agent,[&]{started=true;});
                QObject::connect(&agent,&edi_app::CodexAgent::failed,&agent,[&]{++failures;});
                require(agent.start(executable,workspace),"clock_peer_started");
                QElapsedTimer wait;wait.start();while(!started&&wait.elapsed()<1000)drain(1);
                require(started&&failures==0,"clock_transport_ready");
                // start() owns a bounded bootstrap operation; end that role before the inactive control.
                agent.settleOperation();
                const auto generation=agent.outputGeneration();
                const QJsonValue native("clock-native"),human("clock-human"),foreign("clock-foreign");
                edi_app::CodexAgentTestAccess::receive(agent,{{"id",native},{"method","item/tool/call"},{"params",Object{{"tool","inspect_project"},{"arguments",Object{{"purpose","finite clock role"}}}}}});
                edi_app::CodexAgentTestAccess::receive(agent,{{"id",human},{"method","item/tool/requestUserInput"},{"params",Object{}}});
                require(!agent.beginNativeWork(native,generation)&&!agent.beginHumanWait(human,generation),"inactive_operation_cannot_wait");
                agent.beginOperation(0,0);
                require(!edi_app::CodexAgentTestAccess::expiredAt(agent,edi_app::CodexAgentTestAccess::future(agent)),"active_task_has_no_day_expiry");
                require(!agent.beginNativeWork(foreign,generation)&&!agent.beginNativeWork(native,generation+1),"native_identity_guard_retained");
                require(agent.beginNativeWork(native,generation),"unlimited_native_work_accepted");
                require(!agent.setNativeWorkWaiting(foreign,generation,true)&&!agent.setNativeWorkWaiting(native,generation+1,true),"native_wait_identity_guard_retained");
                require(agent.setNativeWorkWaiting(native,generation,true),"unlimited_native_presentation_wait_accepted");
                require(!agent.beginHumanWait(foreign,generation)&&!agent.beginHumanWait(human,generation+1),"human_identity_guard_retained");
                require(agent.beginHumanWait(human,generation),"unlimited_human_wait_accepted");
                require(!edi_app::CodexAgentTestAccess::expiredAt(agent,edi_app::CodexAgentTestAccess::future(agent))&&failures==0,"overlapping_unlimited_waits_do_not_expire");
                require(agent.endHumanWait(human,generation)&&agent.setNativeWorkWaiting(native,generation,false)&&agent.endNativeWork(native,generation),"original_waits_end_normally");
                agent.settleOperation();require(!agent.beginNativeWork(native,generation),"settled_operation_cannot_restart_wait");
                agent.beginOperation(0,0);require(agent.beginNativeWork(native,generation),"later_unlimited_operation_usable");
                agent.retire();require(!agent.beginNativeWork(native,generation)&&!agent.endHumanWait(human,generation),"retired_generation_cannot_resume_wait");
                edi_app::CodexAgent control;bool control_started=false;int control_failures=0;
                QObject::connect(&control,&edi_app::CodexAgent::started,&control,[&]{control_started=true;});
                QObject::connect(&control,&edi_app::CodexAgent::failed,&control,[&]{++control_failures;});
                require(control.start(executable,workspace),"control_peer_started");wait.restart();while(!control_started&&wait.elapsed()<1000)drain(1);
                require(control_started,"control_transport_ready");
                control.beginOperation(0,0);const auto id=control.request("initialize",Object{{"clientInfo",Object{{"name","finite-clock-control"}}}});
                require(!id.isEmpty()&&edi_app::CodexAgentTestAccess::expireIssuedControl(control,id)&&control_failures==1&&control.failureKind()!=edi_app::CodexAgent::FailureKind::OperationDeadline,"individual_protocol_deadline_remains_bounded");
                edi_app::CodexAgent short_clock;int short_failures=0;bool short_started=false;
                QObject::connect(&short_clock,&edi_app::CodexAgent::failed,&short_clock,[&]{++short_failures;});
                QObject::connect(&short_clock,&edi_app::CodexAgent::started,&short_clock,[&]{short_started=true;});
                require(short_clock.start(executable,workspace),"short_clock_peer_started");wait.restart();while(!short_started&&wait.elapsed()<1000)drain(1);
                require(short_started,"short_clock_transport_ready");
                short_clock.beginOperation(5,5);drain(150);
                require(short_failures==1&&short_clock.failureKind()==edi_app::CodexAgent::FailureKind::OperationDeadline,"explicit_short_deadline_positive_control");
                result={{"checks",checks}};
            }
            else if(op=="clear_ui_sequence") ui_sequence=Array{};
            else if(op=="dialog_ok") {
                auto* dialog=find(input["name"].toString());
                if(!dialog)throw std::runtime_error("actual original dialog is absent");
                const auto role=input["role"].toString("ok");
                const QMap<QString,QString> expressions{{"ok","standardButton(Dialog.Ok)"},{"save","standardButton(Dialog.Save)"},
                    {"discard","standardButton(Dialog.Discard)"},{"cancel","standardButton(Dialog.Cancel)"}};
                if(!expressions.contains(role))throw std::invalid_argument("closed original standard dialog role required");
                QQmlExpression expression(qmlContext(dialog),dialog,expressions.value(role));
                const auto button=expression.evaluate().value<QObject*>();
                if(expression.hasError())throw std::runtime_error(expression.error().toString().toStdString());
                if(!button)throw std::runtime_error("actual original standard dialog button is absent");
                QPointer<QObject> original_dialog=dialog,original_button=button;
                std::unique_ptr<QSignalSpy> pressed;
                if(input.contains("role"))pressed=std::make_unique<QSignalSpy>(button,SIGNAL(pressedChanged()));
                click(button);
                if(input.contains("role"))result={{"role",role},{"actual_dialog_name",input["name"]},
                    {"pressed_changes",pressed?pressed->count():0},{"original_dialog_after",bool(original_dialog)},
                    {"original_button_after",bool(original_button)}};
            }
            else if(op=="click") click(find(input["name"].toString()));
            else if(op=="open") result={{"opened",observed->openProject(QUrl::fromLocalFile(input["path"].toString()))}};
            else if(op=="create") result={{"created",observed->createProject(input["name"].toString(),"independent fixture")}};
            else if(op=="close_project") observed->closeProject();
            else if(op=="save_as") result={{"saved",observed->saveAs(QUrl::fromLocalFile(input["path"].toString()))}};
            else if(op=="save_project_as") result={{"saved",observed->saveProjectAs(
                QUrl::fromLocalFile(input["path"].toString()),input["zip"].toBool(),input["copy"].toBool())}};
            else if(op=="save") result={{"saved",observed->save()}};
            else if(op=="report_toggle") observed->project()->report()->setEmbedLibraries(!observed->project()->report()->embedLibraries());
            else if(op=="undo") observed->project()->undo();
            else if(op=="session_row_click") {
                const auto id=input["thread_id"].toString();QPointer<QQuickItem> row,area;
                if(id.isEmpty())throw std::invalid_argument("exact original public session row ID required");
                for(auto* object:objects(window)) {
                    auto* item=qobject_cast<QQuickItem*>(object);
                    if(!item || item->property("threadId").toString()!=id || !item->isVisible())continue;
                    if(row && row!=item)throw std::runtime_error("ambiguous original realized session row");row=item;
                }
                if(row)for(auto* item:row->childItems()) {
                    if(!item->property("acceptedButtons").isValid() || !(item->property("acceptedButtons").toInt()&Qt::LeftButton)
                        || item->parentItem()!=row || item->width()<=0 || item->width()>=row->width()-1 || std::abs(item->height()-row->height())>1)continue;
                    if(area)throw std::runtime_error("ambiguous original row-owned session input area");area=item;
                }
                if(!row || !area)result={{"reached",false},{"reason","original session row/declared input area is not realized"},{"thread_id",id}};
                else {
                    const auto scene=area->mapToScene(QPointF(area->width()/2,area->height()/2));
                    bool exposed=area->window()==window && area->isVisible() && area->isEnabled()
                        && QRectF(0,0,window->width(),window->height()).contains(scene);
                    for(auto* parent=area->parentItem();parent;parent=parent->parentItem())
                        if(!parent->isVisible() || !parent->isEnabled() || (parent->clip()
                            && !QRectF(0,0,parent->width(),parent->height()).contains(parent->mapFromScene(scene))))exposed=false;
                    if(!exposed)result={{"reached",false},{"reason","original session row input center is clipped/inactive"},{"thread_id",id}};
                    else {
                        QSignalSpy pressed(area.data(),SIGNAL(pressedChanged()));
                        QTest::mouseClick(window,Qt::LeftButton,Qt::NoModifier,scene.toPoint());drain();
                        result={{"reached",true},{"thread_id",id},{"actual_pressed_changes",pressed.count()},
                            {"same_row_after",bool(row)&&row->property("threadId").toString()==id},
                            {"same_window_after",bool(area)&&area->window()==window}};
                    }
                }
            }
            else if(op=="archive_probe_open") {
                const auto key=input["key"].toString(),relative=input["relative"].toString();
                const auto root=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
                const auto path=QDir::cleanPath(root+"/"+relative);
                if(key.isEmpty() || public_archives.count(key) || relative.isEmpty() || QDir::isAbsolutePath(relative)
                    || !(relative=="assistant/history.json" || relative.startsWith("assistant/history/"))
                    || !path.startsWith(root+"/assistant/") || relative.contains(".."))
                    throw std::invalid_argument("unique test archive and original run-owned history namespace required");
                Object copied;
                const auto source=input["source"].toString();
                if(!source.isEmpty()) {
                    const auto owned=QFileInfo(qEnvironmentVariable("EDI_TEST_CODEX_PEER_INPUT")).canonicalPath();
                    const auto actual=QFileInfo(source).canonicalFilePath();
                    if(actual.isEmpty() || owned.isEmpty() || !actual.startsWith(owned+"/") || QFileInfo::exists(path))
                        throw std::runtime_error("archive preload requires an unchanged captured snapshot inside this exact fixture and an absent target");
                    QFile original(actual);if(!original.open(QIODevice::ReadOnly))throw std::runtime_error("captured archive snapshot unavailable");
                    const auto bytes=original.readAll();original.close();
                    if(!QDir().mkpath(QFileInfo(path).absolutePath()))throw std::runtime_error("run-owned archive parent unavailable");
                    QFile output(path);if(!output.open(QIODevice::WriteOnly)||!output.setPermissions(QFileDevice::ReadOwner|QFileDevice::WriteOwner)||output.write(bytes)!=bytes.size())throw std::runtime_error("exact archive snapshot copy failed");output.close();
                    copied={{"source",actual},{"bytes",static_cast<double>(bytes.size())},{"sha256",QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex())},{"exact_copy",true}};
                }
                auto handle=std::make_unique<PublicArchiveProbe>();auto* captured=handle.get();
                handle->archive=std::make_unique<edi_app::AssistantHistoryArchive>(&handle->receiver,path,
                    [captured](const edi_app::AssistantHistoryArchive::View& view){captured->latest=view;++captured->notices;},true);
                if(input["activate"].toBool(true))handle->archive->activate();
                public_archives.emplace(key,std::move(handle));
                result={{"opened",true},{"key",key},{"requested_path",path},{"copied",copied}};
            }
            else if(op=="archive_probe_retain") {
                const auto key=input["key"].toString();auto found=public_archives.find(key);
                if(found==public_archives.end())throw std::invalid_argument("original test archive handle required");
                const bool clear=input["logical_clear"].toBool();Array rows;Object captured;
                if(!clear) {
                    const auto source=input["source"].toString();const auto actual=QFileInfo(source).canonicalFilePath();
                    const auto owned=QFileInfo(qEnvironmentVariable("EDI_TEST_CODEX_PEER_INPUT")).canonicalPath();
                    if(actual.isEmpty() || owned.isEmpty() || !actual.startsWith(owned+"/"))throw std::runtime_error("retain requires a genuine byte-captured snapshot in this exact fixture");
                    QFile original(actual);if(!original.open(QIODevice::ReadOnly))throw std::runtime_error("genuine retained snapshot unavailable");
                    const auto bytes=original.readAll();QJsonParseError error;const auto parsed=QJsonDocument::fromJson(bytes,&error);
                    if(error.error!=QJsonParseError::NoError || !parsed.isArray())throw std::runtime_error("genuine archive source is not its original JSON array");
                    rows=parsed.array();captured={{"source",actual},{"bytes",static_cast<double>(bytes.size())},{"sha256",QString::fromLatin1(QCryptographicHash::hash(bytes,QCryptographicHash::Sha256).toHex())}};
                }
                const bool accepted=found->second->archive->retain(rows,input["includes_initial"].toBool(),clear);
                result={{"accepted",accepted},{"logical_clear",clear},{"captured",captured}};
            }
            else if(op=="archive_probe_view") {
                const auto key=input["key"].toString();auto found=public_archives.find(key);
                if(found==public_archives.end())throw std::invalid_argument("original test archive handle required");
                const auto view=found->second->archive->view();
                result={{"path",view.path},{"initial_rows",view.initial_rows},{"latest_rows",view.latest_rows},
                    {"accepted",static_cast<double>(view.accepted)},{"durable",static_cast<double>(view.durable)},
                    {"clear",static_cast<double>(view.clear)},{"failure_revision",static_cast<double>(view.failure_revision)},
                    {"failure_stage",view.failure_stage?QString::fromUtf8(view.failure_stage):QString()},
                    {"loaded",view.loaded},{"includes_initial",view.includes_initial},{"pending",view.pending},
                    {"recovered",view.recovered},{"working",view.working},{"notices",static_cast<int>(found->second->notices)}};
            }
            else if(op=="archive_probe_close") {
                const auto key=input["key"].toString();auto found=public_archives.find(key);
                if(found==public_archives.end())throw std::invalid_argument("original test archive handle required");
                found->second->archive->closeOwner();result={{"closed",true}};
            }
            else if(op=="archive_probe_clear") {
                public_archive_barriers=edi_app::AssistantHistoryArchive::clearCaches(&public_archive_clear_receiver,[](const edi_app::AssistantHistoryArchive::View&) {});
                result={{"barriers",static_cast<int>(public_archive_barriers.size())}};
            }
            else if(op=="archive_probe_clear_view") {
                Array barriers;for(const auto& barrier:public_archive_barriers) {
                    const auto view=barrier.view();
                    barriers.append(Object{{"path",view.path},{"revision",static_cast<double>(barrier.revision())},
                        {"accepted",static_cast<double>(view.accepted)},{"durable",static_cast<double>(view.durable)},
                        {"failure_revision",static_cast<double>(view.failure_revision)},
                        {"failure_stage",view.failure_stage?QString::fromUtf8(view.failure_stage):QString()},
                        {"pending",view.pending},{"working",view.working},{"recovered",view.recovered}});
                }
                result={{"barriers",barriers}};
            }
            else if(op=="archive_probe_clear_retry") {
                const auto index=input["index"].toInt(-1);
                if(index<0 || static_cast<std::size_t>(index)>=public_archive_barriers.size())throw std::invalid_argument("original clear-barrier receipt required");
                const auto revision=public_archive_barriers[index].revision();
                result={{"accepted",public_archive_barriers[index].retry()},{"original_revision",static_cast<double>(revision)}};
            }
            else if(op=="archive_probe_merge") {
                auto read=[&](const char* field) {
                    const auto actual=QFileInfo(input[field].toString()).canonicalFilePath();
                    const auto owned=QFileInfo(qEnvironmentVariable("EDI_TEST_CODEX_PEER_INPUT")).canonicalPath();
                    if(actual.isEmpty() || owned.isEmpty() || !actual.startsWith(owned+"/"))throw std::runtime_error("merge requires actual byte-captured snapshots in this fixture");
                    QFile file(actual);if(!file.open(QIODevice::ReadOnly))throw std::runtime_error("captured merge source unavailable");
                    QJsonParseError error;const auto value=QJsonDocument::fromJson(file.readAll(),&error);
                    if(error.error!=QJsonParseError::NoError || !value.isArray())throw std::runtime_error("original captured history array required");return value.array();
                };
                const auto initial=read("initial_source"),current=read("current_source");
                result={{"rows",edi_app::merge_assistant_history(initial,current)}};
            }
            else if(op=="archive_probe_drop") {
                const auto key=input["key"].toString();auto found=public_archives.find(key);
                if(found==public_archives.end())throw std::invalid_argument("original test archive handle required");
                public_archives.erase(found);result={{"dropped",true}};
            }
            else if(op=="markdown_probe") {
                const auto identity=input["row_id"].toString();
                QPointer<edi_app::AssistantMarkdown> presentation;QPointer<QQuickItem> original_row;
                if(identity.isEmpty())throw std::invalid_argument("original realized message row ID required");
                for(auto* object:objects(window)) {
                    auto* candidate=qobject_cast<edi_app::AssistantMarkdown*>(object);if(!candidate)continue;
                    for(auto* parent=candidate->parentItem();parent;parent=parent->parentItem())
                        if(parent->property("rowId").toString()==identity) {
                            if(presentation && presentation!=candidate)throw std::runtime_error("ambiguous original message document");
                            presentation=candidate;original_row=parent;break;
                        }
                }
                if(!presentation || !original_row || !presentation->document() || !presentation->document()->textDocument())
                    result={{"reached",false},{"reason","original message/document is not realized"},{"row_id",identity}};
                else {
                    auto* document=presentation->document()->textDocument();const auto center=presentation->mapToScene(QPointF(presentation->width()/2,presentation->height()/2));
                    bool exposed=presentation->window()==window && presentation->isVisible() && presentation->width()>0 && presentation->height()>0
                        && QRectF(0,0,window->width(),window->height()).contains(center);
                    for(auto* parent=presentation->parentItem();parent;parent=parent->parentItem())
                        if(!parent->isVisible() || (parent->clip() && !QRectF(0,0,parent->width(),parent->height()).contains(parent->mapFromScene(center))))exposed=false;
                    Array images,tables,anchors,blocks;
                    for(auto block=document->begin();block.isValid();block=block.next())blocks.append(Object{{"position",block.position()},{"text",block.text()},
                        {"heading",block.blockFormat().headingLevel()},{"list_item",block.textList()!=nullptr},{"list_object",block.blockFormat().objectIndex()}});
                    for(auto block=document->begin();block.isValid();block=block.next())for(auto it=block.begin();!it.atEnd();++it) {
                        const auto fragment=it.fragment();if(!fragment.isValid())continue;
                        if(fragment.charFormat().isAnchor())anchors.append(Object{{"href",fragment.charFormat().anchorHref()},{"text",fragment.text()},{"tooltip",fragment.charFormat().toolTip()}});
                        if(!fragment.charFormat().isImageFormat())continue;
                        const auto format=fragment.charFormat().toImageFormat();const auto resource=document->resource(QTextDocument::ImageResource,QUrl(format.name()));
                        const auto image=qvariant_cast<QImage>(resource);bool nontransparent=false;QRect ink;
                        const auto area=static_cast<quint64>(image.width())*static_cast<quint64>(image.height());
                        const auto frame_area=static_cast<quint64>(window->width())*static_cast<quint64>(window->height());
                        // Only a diagnostic scan bound for these tiny formula fixtures;
                        // no product input/render/resource is refused or truncated here.
                        const bool fixture_sized=area<=frame_area*16;
                        if(fixture_sized)for(int y=0;y<image.height();++y)for(int x=0;x<image.width();++x)
                            if(image.pixelColor(x,y).alpha()){nontransparent=true;ink=ink.united(QRect(x,y,1,1));}
                        const auto font=format.font().resolve(document->defaultFont());const auto font_descent=QFontMetricsF(font).descent();
                        const auto line=block.layout()?block.layout()->lineForTextPosition(fragment.position()-block.position()):QTextLine();
                        const auto baseline=line.isValid()?block.layout()->position().y()+line.y()+line.ascent():0;
                        const auto logical_height=format.height()>0?format.height():(image.devicePixelRatio()>0?image.height()/image.devicePixelRatio():0);
                        images.append(Object{{"position",fragment.position()},{"length",fragment.length()},{"name",format.name()},
                            {"width",format.width()},{"height",format.height()},{"resource_width",image.width()},{"resource_height",image.height()},
                            {"resource_dpr",image.devicePixelRatio()},{"resource_null",image.isNull()},{"nontransparent",nontransparent},
                            {"fixture_sized",fixture_sized},{"format_font_descent",font_descent},{"format_baseline_offset",format.baselineOffset()},
                            {"line_baseline",baseline},{"quick_baseline_top_from_consumer",baseline-(logical_height-font_descent)},
                            {"ink_x",ink.x()},{"ink_y",ink.y()},{"ink_width",ink.width()},{"ink_height",ink.height()},
                            {"selected_source",presentation->selectedSource(fragment.position(),fragment.position()+fragment.length())}});
                    }
                    std::function<void(QTextFrame*)> visit=[&](QTextFrame* frame) {
                        if(auto* table=qobject_cast<QTextTable*>(frame)) {
                            const auto rect=document->documentLayout()->frameBoundingRect(table);Array rows;
                            for(int r=0;r<table->rows();++r) {
                                QRectF bounds;for(int c=0;c<table->columns();++c) {
                                    const auto cell=table->cellAt(r,c);const auto first=cell.firstCursorPosition().block(),last=cell.lastCursorPosition().block();
                                    bounds=bounds.united(document->documentLayout()->blockBoundingRect(first)).united(document->documentLayout()->blockBoundingRect(last));
                                }
                                rows.append(Object{{"row",r},{"x",bounds.x()},{"y",bounds.y()},{"width",bounds.width()},{"height",bounds.height()}});
                            }
                            tables.append(Object{{"rows",table->rows()},{"columns",table->columns()},{"x",rect.x()},{"y",rect.y()},
                                {"width",rect.width()},{"height",rect.height()},{"row_geometry",rows}});
                        }
                        for(auto* child:frame->childFrames())visit(child);
                    };visit(document->rootFrame());
                    Object literal_copy;
                    if(input["literal"].isString()) {
                        const auto literal=input["literal"].toString();const auto found=document->find(literal);
                        literal_copy={{"found",!found.isNull()},{"literal",literal}};
                        if(!found.isNull())literal_copy["selected_source"]=presentation->selectedSource(found.selectionStart(),found.selectionEnd());
                    }
                    auto color=[](const QColor& value){return Array{value.red(),value.green(),value.blue(),value.alpha()};};
                    result={{"reached",true},{"row_id",identity},{"same_window",presentation->window()==window},{"center_exposed",exposed},
                        {"source",presentation->source()},{"literal_copy",literal_copy},{"plain_text",document->toPlainText()},{"whole_source_copy",presentation->selectedSource(0,std::max(0,document->characterCount()-1))},
                        {"markdown",presentation->markdown()},{"images",images},{"tables",tables},{"anchors",anchors},{"blocks",blocks},
                        {"chat_color",color(original_row->property("chatBackgroundColor").value<QColor>())},
                        {"base_color",color(presentation->tableBaseColor())},{"alternate_color",color(presentation->tableShadeColor())},
                        {"border_color",color(presentation->tableBorderColor())},{"document_scene_x",presentation->mapToScene(QPointF()).x()},{"document_scene_y",presentation->mapToScene(QPointF()).y()},{"body_font_family",presentation->bodyFont().family()},
                        {"mono_font_family",presentation->monoFontFamily()}};
                }
            }
            else if(op=="markdown_copy") {
                const auto identity=input["row_id"].toString(),mode=input["mode"].toString("public");
                if(mode!="public" && mode!="keyboard" && mode!="selection")throw std::invalid_argument("closed original TextEdit copy entrance required");
                QPointer<edi_app::AssistantMarkdown> presentation;QPointer<QQuickItem> body,original_row;
                for(auto* object:objects(window)) {
                    auto* candidate=qobject_cast<edi_app::AssistantMarkdown*>(object);if(!candidate)continue;
                    for(auto* parent=candidate->parentItem();parent;parent=parent->parentItem())
                        if(parent->property("rowId").toString()==identity) {
                            if(presentation && presentation!=candidate)throw std::runtime_error("ambiguous original math message");
                            presentation=candidate;body=candidate->parentItem();original_row=parent;break;
                        }
                }
                if(!presentation || !body || !presentation->document() || !presentation->document()->textDocument())throw std::runtime_error("original realized math TextEdit is unavailable");
                auto* document=presentation->document()->textDocument();int index=input["image_index"].toInt(),start=-1,end=-1;
                for(auto block=document->begin();block.isValid()&&start<0;block=block.next())for(auto it=block.begin();!it.atEnd();++it) {
                    const auto fragment=it.fragment();if(!fragment.isValid() || !fragment.charFormat().isImageFormat())continue;
                    if(index--==0){start=fragment.position();end=start+fragment.length();break;}
                }
                if(start<0)throw std::runtime_error("the requested original generated formula is not present");
                QRectF first,last;
                if(!QMetaObject::invokeMethod(body,"positionToRectangle",Qt::DirectConnection,Q_RETURN_ARG(QRectF,first),Q_ARG(int,start))
                    || !QMetaObject::invokeMethod(body,"positionToRectangle",Qt::DirectConnection,Q_RETURN_ARG(QRectF,last),Q_ARG(int,end)))
                    throw std::runtime_error("original TextEdit public position geometry is unavailable");
                const auto a=body->mapToScene(QPointF(first.left()+.25,first.center().y()));
                const auto b=body->mapToScene(QPointF(last.left()+.25,last.center().y()));
                auto exposed=[&](const QPointF& point) {
                    if(!body || body->window()!=window || !body->isVisible() || !body->isEnabled()
                        || !QRectF(0,0,window->width(),window->height()).contains(point))return false;
                    for(auto* parent=body->parentItem();parent;parent=parent->parentItem())
                        if(!parent->isVisible() || !parent->isEnabled() || (parent->clip() && !QRectF(0,0,parent->width(),parent->height()).contains(parent->mapFromScene(point))))return false;
                    return true;
                };
                if(!exposed(a)||!exposed(b))throw std::runtime_error("original formula selection endpoints are clipped in their current window");
                const auto source=presentation->source();QPointer<QQuickTextDocument> original_document=presentation->document();
                QTest::mouseMove(window,a.toPoint());QTest::mousePress(window,Qt::LeftButton,Qt::NoModifier,a.toPoint());
                QTest::mouseMove(window,b.toPoint());QTest::mouseRelease(window,Qt::LeftButton,Qt::NoModifier,b.toPoint());drain();
                if(!body || !presentation || !original_row || original_row->property("rowId").toString()!=identity
                    || presentation->document()!=original_document || presentation->source()!=source || body->window()!=window)
                    throw std::runtime_error("original formula copy receiver changed during real selection input");
                const auto selected_start=body->property("selectionStart").toInt(),selected_end=body->property("selectionEnd").toInt();
                if(std::min(selected_start,selected_end)>start || std::max(selected_start,selected_end)<end || selected_start==selected_end)
                    throw std::runtime_error("the actual original mouse drag did not select the requested formula");
                auto* clipboard=QGuiApplication::clipboard();QString copied;
                if(mode=="selection") {
                    if(!clipboard->supportsSelection() || !clipboard->ownsSelection())
                        throw std::runtime_error("this actual platform/gesture does not own its primary selection clipboard");
                    copied=clipboard->text(QClipboard::Selection);
                } else {
                    if(mode=="public") {
                        if(!QMetaObject::invokeMethod(body,"copy",Qt::DirectConnection))throw std::runtime_error("original TextEdit.copy entrance unavailable");
                    } else {
                        if(!body->hasActiveFocus())throw std::runtime_error("real formula selection did not give the original TextEdit keyboard focus");
                        QTest::keyClick(window,Qt::Key_C,Qt::ControlModifier);drain();
                    }
                    if(!clipboard->ownsClipboard())throw std::runtime_error("original copy did not own the current clipboard");
                    copied=clipboard->text();
                }
                result={{"reached",true},{"row_id",identity},{"mode",mode},{"clipboard",copied},
                    {"selected_start",selected_start},{"selected_end",selected_end},{"formula_start",start},{"formula_end",end},
                    {"same_row",original_row->property("rowId").toString()==identity},{"same_window",body->window()==window}};
            }
            else if(op=="arm_session_notification") {
                if(!observed || !window)throw std::runtime_error("actual original session notification owner required");
                QObject::disconnect(session_notification_fault);session_notification_hits=0;session_fault_facts=Object{};
                const auto signal=input["signal"].toString(),action=input["action"].toString();
                if((signal!="usage" && signal!="sessions") || (action!="close_project" && action!="destroy_engine"))
                    throw std::invalid_argument("declared public session notification/action required");
                QPointer<edi_app::AssistantViewModel> original=observed->assistant();
                const auto callback=[&,original,action,signal] {
                    if(session_notification_hits++)return;
                    session_fault_facts["notification"]=signal;session_fault_facts["action"]=action;
                    session_fault_facts["original_vm_before"]=bool(original)&&observed&&observed->assistant()==original;
                    if(action=="close_project")observed->closeProject();
                    else {engine.reset();singleton=nullptr;}
                    session_fault_facts["original_vm_after"]=bool(original)&&observed&&observed->assistant()==original;
                    session_fault_facts["project_present_after"]=bool(observed)&&bool(observed->project());
                };
                if(signal=="usage")session_notification_fault=QObject::connect(original.data(),&edi_app::AssistantViewModel::usageChanged,&session_fault_observer,callback,Qt::DirectConnection);
                else session_notification_fault=QObject::connect(original.data(),&edi_app::AssistantViewModel::sessionsChanged,&session_fault_observer,callback,Qt::DirectConnection);
                result={{"armed",true}};
            }
            else if(op=="session_operation") {
                if(!observed || !window)throw std::runtime_error("actual original session operation owner required");
                const auto operation=input["operation"].toString();QPointer<edi_app::AssistantViewModel> original=observed->assistant();
                if(operation=="refresh")original->refreshSessions(input["next_page"].toBool());
                else if(operation=="archive")original->archiveSession(input["thread_id"].toString());
                else throw std::invalid_argument("original public Refresh/Archive operation required");
                result={{"called",true},{"original_vm_after",bool(original)&&observed&&observed->assistant()==original}};
            }
            else if(op=="close_owned_transport_write") {close_owned_session_write();result=session_fault_facts;}
            else if(op=="session_fault_facts") {result=session_fault_facts;result["notification_hits"]=static_cast<int>(session_notification_hits);}
            else if(op=="clear_history") observed->assistant()->clearHistory();
            else if(op=="cancel") observed->assistant()->cancel();
            else if(op=="sign_out") observed->assistant()->signOut();
            else if(op=="select_model") observed->assistant()->setSelectedModel(input["id"].toString());
            else if(op=="select_effort") observed->assistant()->setSelectedEffort(input["id"].toString());
            else if(op=="owner_queue_escape") {
                const auto callbacks=input["callbacks"].toArray();
                Array phases;
                if(input["schedule"].toString()=="queued-transport") {
                    if(!QMetaObject::invokeMethod(observed,[&fixture,callbacks] {
                        for(const auto& value:callbacks) fixture.dispatch(value.toObject());
                    },Qt::QueuedConnection)) throw std::runtime_error("old transport callback not queued");
                    phases.push_back("old HTTP callbacks queued on actual owner");
                } else if(input["schedule"].toString()=="direct-native") {
                    for(const auto& value:callbacks) fixture.dispatch(value.toObject());
                    phases.push_back("old callbacks invoked and returned");
                } else throw std::invalid_argument("unknown independent callback schedule");
                const auto before_retire=model_rows(observed->assistant()->messages());
                if(input["retirement"].toString()=="project") {
                    if(!observed->openProject(QUrl::fromLocalFile(input["path"].toString())))
                        throw std::runtime_error("actual new project open failed");
                } else if(input["retirement"].toString()=="history") {
                    observed->assistant()->clearHistory();
                } else throw std::invalid_argument("unknown independent retirement");
                phases.push_back("actual scope retired");
                const auto old_operations=fixture.operations.size();
                observed->assistant()->send(input["text"].toString());
                bool accepted=false;
                if(observed->assistant()->contextConsentRequired()) {
                    auto* button=find("assistant.connection");
                    auto* item=qobject_cast<QQuickItem*>(button);
                    if(!item || !item->isVisible() || !item->isEnabled() ||
                       !QMetaObject::invokeMethod(button,"clicked",Qt::DirectConnection))
                        throw std::runtime_error("actual context inspection control unavailable");
                }
                for(auto* object:objects(window)) {
                    if(!object->property("visible").toBool() || !object->property("title").isValid()) continue;
                    if(object->metaObject()->indexOfMethod("accept()")<0) continue;
                    Array texts;
                    for(auto* child:objects(object)) if(child->property("text").isValid()) texts.push_back(text_observation(child));
                    disclosures.push_back(Object{{"title",object->property("title").toString()},{"texts",texts}});
                    if(!QMetaObject::invokeMethod(object,"accept",Qt::DirectConnection))
                        throw std::runtime_error("real disclosure acceptance did not execute");
                    accepted=true;break;
                }
                if(accepted) observed->assistant()->send(input["text"].toString());
                Array sent_before_drain;
                for(std::size_t index=old_operations;index<fixture.operations.size();++index)
                    if(fixture.operations[index]->request.url.path()=="/v1/responses")
                        sent_before_drain.push_back(static_cast<double>(index));
                phases.push_back("new actual public send before queue drain");
                bool admitted_before_drain=false;
                for(const auto& value:model_rows(observed->assistant()->messages())) {
                    const auto row=value.toObject();
                    if(row.value("kind")=="user" && row.value("text")==input.value("text"))
                        admitted_before_drain=observed->assistant()->canCancel();
                }
                result={{"phases",phases},{"before_retire",before_retire},
                        {"admitted_before_drain",admitted_before_drain},
                        {"sent_before_drain",sent_before_drain},{"accepted_dialog",accepted}};
            }
            else if(op=="callback_batch") {
                // Fixture scheduling bound, not a provider or production resource policy.
                const auto callbacks=input["callbacks"].toArray();
                if(callbacks.isEmpty() || callbacks.size()>16)
                    throw std::invalid_argument("fixture callback batch must contain one to sixteen callbacks");
                for(const auto& callback:callbacks) {
                    const auto name=callback.toObject()["op"].toString();
                    if(name!="headers" && name!="data" && name!="finish")
                        throw std::invalid_argument("fixture batch contains a non-transport command");
                }
                for(const auto& callback:callbacks) {
                    fixture.dispatch(callback.toObject());
                    QCoreApplication::processEvents(QEventLoop::AllEvents,1);
                }
            } else if(op=="callback_then_open") {
                fixture.dispatch(input["callback"].toObject());
                result={{"opened",observed->openProject(QUrl::fromLocalFile(input["path"].toString()))}};
            } else if(op=="resize") {window->setMinimumWidth(400);window->resize(input["width"].toInt(),768);}
            else if(op=="popup") {
                auto* control=find(input["name"].toString());
                auto* popup=control?control->property("popup").value<QObject*>():nullptr;
                if(!popup || !QMetaObject::invokeMethod(popup,"open")) throw std::runtime_error("real combo popup unavailable");
            } else if(op=="click_link") {
                bool found=false;
                for(auto* object:objects(window)) {
                    if(!object->property("text").toString().contains(input["marker"].toString())) continue;
                    if(activate_item_link(object)) {found=true;break;}
                }
                result={{"found",found}};
            } else if(op=="calibrate_observer") {
                QQmlComponent calibration(engine.get());
                calibration.setData("import QtQuick; import EasyApplication.Gui.Elements as EaElements; EaElements.Label { textFormat: Text.RichText; z: 10000; width: 200 }",QUrl());
                std::unique_ptr<QObject> text(calibration.createWithInitialProperties({{"text",QString("<a href='https://independent-fixture.invalid/calibration'>CALIBRATION</a><img src='http://127.0.0.1:%1/calibration.png'>").arg(urls.images.serverPort())}}));
                if(!text) throw std::runtime_error("independent renderer observation calibration unavailable");
                qobject_cast<QQuickItem*>(text.get())->setParentItem(window->contentItem());
                drain(100);
                bool reached_link=activate_item_link(text.get());
                drain();
                result={{"image_requests",urls.image_requests},{"url_activations",urls.activated.size()},{"link_hit",reached_link}};
                text.reset();drain(100);urls.image_requests=0;urls.activated=Array{};
            } else if(op=="destroy") {engine.reset();singleton=nullptr;}
            else result=fixture.dispatch(input);
            drain();
            auto output=fixture.snapshot();output["reply"]=result;
            output["ui"]=(op=="messages_probe" || op=="message_input") ? Object{{"alive",bool(observed)&&bool(window)},{"state",observed?observed->assistant()->state():QString()},{"connected",observed&&observed->assistant()->connected()},{"can_cancel",observed&&observed->assistant()->canCancel()}} : ui_snapshot();
            output["test_storage"]=storage.path();output["history_restore"]=history_restore_info;output["settings_restore"]=settings_restore_info;output["cache_restore"]=cache_restore_info;output["initial_cache_read_binding"]=initial_cache_read_binding;output["test_settings"]=Object{{"path",QSettings().fileName()},{"application_name",QGuiApplication::applicationName()},{"organization_name",QGuiApplication::organizationName()},{"application_name_override",test_application_name},{"app_local_data",QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)}};
            output["state"]=observed ? Object{{"last_error",observed->assistant()->lastError()}} : QJsonValue();
            output["image_requests"]=urls.image_requests;output["activated_urls"]=urls.activated;
            output["image_url"]=QString("http://127.0.0.1:%1/untrusted.png").arg(urls.images.serverPort());
            std::cout<<encode(output).toStdString()<<'\n'<<std::flush;
        } catch(const std::exception& error) {
            std::cout<<encode(Object{{"host_error",QString::fromUtf8(error.what())}}).toStdString()<<'\n'<<std::flush;
        }
    };
#if defined(Q_OS_UNIX)
    // stdin is this existing line protocol, not a second IPC server. Readiness
    // runs on the actual GUI owner event loop; a quiet driver cannot starve Qt.
    const int original_flags=::fcntl(STDIN_FILENO,F_GETFL);
    if(original_flags<0 || ::fcntl(STDIN_FILENO,F_SETFL,original_flags|O_NONBLOCK)<0)return 89;
    QByteArray input_buffer;
    QSocketNotifier input_ready(STDIN_FILENO,QSocketNotifier::Read,&app);
    QObject::connect(&input_ready,&QSocketNotifier::activated,&app,[&] {
        // Commands may drain events to settle real controls. Keep stdin delivery
        // nonreentrant so current receivers and FIFO command/reply remain exact.
        input_ready.setEnabled(false);
        bool eof=false,failed=false;
        char bytes[65536];
        for(;;) {
            const auto count=::read(STDIN_FILENO,bytes,sizeof(bytes));
            if(count>0) {input_buffer.append(bytes,count);continue;}
            if(count==0) {eof=true;break;}
            if(errno==EINTR)continue;
            if(errno==EAGAIN || errno==EWOULDBLOCK)break;
            failed=true;break;
        }
        for(;;) {
            const auto end=input_buffer.indexOf('\n');
            if(end<0)break;
            const auto command=input_buffer.first(end);input_buffer.remove(0,end+1);
            execute_command(command);
        }
        // Match the original getline behavior for a final line without LF.
        if(eof && !input_buffer.isEmpty()) {execute_command(input_buffer);input_buffer.clear();}
        if(failed) {std::fputs("Main test stdin readiness failed\n",stderr);app.exit(88);}
        else if(eof)app.quit();
        else input_ready.setEnabled(true);
    });
    const int result=app.exec();
    input_ready.setEnabled(false);
    (void)::fcntl(STDIN_FILENO,F_SETFL,original_flags);
    engine.reset();
    return result;
#else
    std::fputs("Main test host requires POSIX stdin readiness; this platform is not qualified by this carrier\n",stderr);
    engine.reset();
    return 87;
#endif
}
#include "probe.moc"
