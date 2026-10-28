// Tests-owned real edi.app owner host. Services never replace the VM/controller/editor.
#include "fixture_services.hpp"
#include "session.hpp"
#include "assistant_view_model.hpp"
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
    QGuiApplication::setApplicationName("assistant-"+QUuid::createUuid().toString(QUuid::WithoutBraces));
    edi_app::use_design_font();
    edi_app::use_fresh_settings();
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
    QObject message_model_observer;
    auto stop_message_model_watch=[&] {
        for(const auto& connection:message_model_connections)QObject::disconnect(connection);
        message_model_connections.clear();message_model_watched.clear();
    };
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
    const auto execute_command=[&](const QByteArray& line) {
        try {
            auto input=decode(line).toObject();
            auto op=input["op"].toString();Object result;
            if((!observed || !window) && op!="inspect" && op!="destroy")throw std::runtime_error("the original Main owner has retired");
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
                    stop_message_model_watch();message_model_events=Array{};message_model_watched=model;
                    message_model_connections.push_back(QObject::connect(model,&QAbstractItemModel::dataChanged,&message_model_observer,
                        [&](const QModelIndex& first,const QModelIndex& last,const QList<int>& roles){Array names;const auto live=message_model_watched?message_model_watched->roleNames():QHash<int,QByteArray>{};for(const auto role:roles)names.append(QString::fromUtf8(live.value(role,QByteArray::number(role))));message_model_events.append(Object{{"kind","dataChanged"},{"first",first.row()},{"last",last.row()},{"roles",names}});}));
                    message_model_connections.push_back(QObject::connect(model,&QAbstractItemModel::rowsInserted,&message_model_observer,[&](const QModelIndex&,int first,int last){message_model_events.append(Object{{"kind","insert"},{"first",first},{"last",last}});}));
                    message_model_connections.push_back(QObject::connect(model,&QAbstractItemModel::rowsRemoved,&message_model_observer,[&](const QModelIndex&,int first,int last){message_model_events.append(Object{{"kind","remove"},{"first",first},{"last",last}});}));
                    message_model_connections.push_back(QObject::connect(model,&QAbstractItemModel::rowsMoved,&message_model_observer,[&](const QModelIndex&,int first,int last,const QModelIndex&,int destination){message_model_events.append(Object{{"kind","move"},{"first",first},{"last",last},{"destination",destination}});}));
                    message_model_connections.push_back(QObject::connect(model,&QAbstractItemModel::modelReset,&message_model_observer,[&]{message_model_events.append(Object{{"kind","reset"}});}));
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
            } else if(op=="manual_key") {
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
                QQmlExpression expression(qmlContext(dialog),dialog,"standardButton(Dialog.Ok)");
                const auto button=expression.evaluate().value<QObject*>();
                if(expression.hasError())throw std::runtime_error(expression.error().toString().toStdString());
                click(button);
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
            output["test_storage"]=storage.path();output["history_restore"]=history_restore_info;
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
