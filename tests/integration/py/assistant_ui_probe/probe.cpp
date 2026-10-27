// Tests-owned real edi.app owner host. Services never replace the VM/controller/editor.
#include "fixture_services.hpp"
#include "session.hpp"
#include "assistant_view_model.hpp"
#include "assistant_native_tools.hpp"
#include "engine_setup.hpp"
#include "edi/io.hpp"
#include "edi/background_estimate.hpp"
#include "edi/parameter_walk.hpp"
#include <QDesktopServices>
#include <QDirIterator>
#include <QGuiApplication>
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

Q_IMPORT_QML_PLUGIN(edi_appPlugin)
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
    QGuiApplication app(argc,argv);
    QGuiApplication::setOrganizationName("EdiIndependentAcceptance");
    QGuiApplication::setApplicationName("assistant-"+QUuid::createUuid().toString(QUuid::WithoutBraces));
    edi_app::use_design_font();
    edi_app::use_fresh_settings();
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
    window->resize(1280,768);window->show();drain();
    auto* preferences=engine->singletonInstance<QObject*>("edi.app","Preferences");
    preferences->setProperty("assistantShown",true);
    Array disclosures;
    Array action_transitions;
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
    auto ui_snapshot=[&]()->Object {
        if(!observed) return {{"alive",false}};
        QQmlExpression expression(qmlContext(window),window,"Session.assistant");
        auto qml_assistant=expression.evaluate().value<QObject*>();
        Array texts,controls;
        for(auto* object:objects(window)) {
            if(auto* item=qobject_cast<QQuickItem*>(object); item && item->isVisible() && object->property("text").isValid())
                texts.push_back(text_observation(object));
            if(auto* item=qobject_cast<QQuickItem*>(object);item&&!object->objectName().isEmpty())
                controls.push_back(Object{{"name",object->objectName()},{"visible",item->isVisible()},
                    {"enabled",item->isEnabled()},{"width",item->width()},{"height",item->height()},
                    {"x",item->mapToScene(QPointF()).x()},{"y",item->mapToScene(QPointF()).y()}});
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
                        {"type",QString::fromStdString(site->type_symbol.get())},
                        {"wyckoff",QString::fromStdString(site->wyckoff_letter.get())},
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
                    {"value",p.value.get()},{"free",p.free.get()},{"refinable",entry.refinable},
                    {"fit_blocker",static_cast<int>(p.fit_blocker)},
                    {"fit_reason",QString::fromStdString(p.fit_reason)},
                    {"dependence",static_cast<int>(p.dependence)}});
            }
            for(const auto& alias:model.aliases)
                aliases.push_back(Object{{"id",QString::fromStdString(alias->id.value())},
                    {"parameter",QString::fromStdString(alias->parameter_unique_name.get())}});
            for(const auto& constraint:model.constraints)
                constraints.push_back(Object{{"id",QString::fromStdString(constraint->id.value())},
                    {"expression",QString::fromStdString(constraint->expression.get())},
                    {"enabled",constraint->enabled.get()}});
            for(const auto& bank:model.experiments) {
                Array points;
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
            }
            project={{"name",QString::fromStdString(model.metadata.name)},
                     {"path",observed->project()->path()},
                     {"structures",static_cast<int>(model.structures.size())},
                     {"structure_rows",structures},{"parameters",parameters},
                     {"aliases",aliases},{"constraints",constraints},
                     {"backgrounds",backgrounds},
                     {"calculating",observed->project()->calculating()},
                     {"cell_a",model.structures.empty()?QJsonValue():QJsonValue(model.structure().cell.length_a.value.get())},
                     {"cell_a_free",model.structures.empty()?QJsonValue():QJsonValue(model.structure().cell.length_a.free.get())},
                     {"report_embedded",observed->project()->report()->embedLibraries()},
                     {"can_undo",observed->project()->canUndo()}};
        }
        return {{"alive",true},{"singleton_identity",singleton==observed&&qml_assistant==observed->assistant()},
                {"engine_parent",observed->parent()==engine.get()},
                {"cpp_ownership",QJSEngine::objectOwnership(observed)==QJSEngine::CppOwnership},
                {"connected",assistant->connected()},{"state",assistant->state()},
                {"available_efforts",QJsonArray::fromStringList(assistant->availableEfforts())},
                {"selected_effort",assistant->selectedEffort()},
                {"last_error",assistant->lastError()},{"messages",model_rows(assistant->messages())},
                {"show_actions",assistant->showActions()},
                {"action_transitions",action_transitions},
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
    std::string line;
    while(std::getline(std::cin,line)) {
        try {
            auto input=decode(QByteArray::fromStdString(line)).toObject();
            auto op=input["op"].toString();Object result;
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
            auto output=fixture.snapshot();output["reply"]=result;output["ui"]=ui_snapshot();
            output["test_storage"]=storage.path();
            output["state"]=observed ? Object{{"last_error",observed->assistant()->lastError()}} : QJsonValue();
            output["image_requests"]=urls.image_requests;output["activated_urls"]=urls.activated;
            output["image_url"]=QString("http://127.0.0.1:%1/untrusted.png").arg(urls.images.serverPort());
            std::cout<<encode(output).toStdString()<<'\n'<<std::flush;
        } catch(const std::exception& error) {
            std::cout<<encode(Object{{"host_error",QString::fromUtf8(error.what())}}).toStdString()<<'\n'<<std::flush;
        }
    }
    engine.reset();
}
#include "probe.moc"
