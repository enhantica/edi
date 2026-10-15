// New real-QML component consumer; no Main replacement, fake VM or producer CPP inclusion.
#include "fixture_services.hpp"
#include "session.hpp"
#include "assistant_view_model.hpp"
#include "engine_setup.hpp"
#include <QAccessible>
#include <QClipboard>
#include <QDir>
#include <QGuiApplication>
#include <QFont>
#include <QFontInfo>
#include <QImage>
#include <QQuickTextDocument>
#include <QTextBlock>
#include <QTextFragment>
#include <QTextList>
#include <QJsonValue>
#include <QJSValue>
#include <QQmlApplicationEngine>
#include <QQuickItem>
#include <QQuickWindow>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QTest>
#include <QUuid>
#include <QtQml/qqmlextensionplugin.h>
#include <algorithm>

Q_IMPORT_QML_PLUGIN(edi_appPlugin)
namespace {
void drain(int ms=30) {
    QElapsedTimer elapsed;elapsed.start();
    do {QCoreApplication::processEvents(QEventLoop::AllEvents,1);} while(elapsed.elapsed()<ms);
}
QVariant invoke(QObject* root,const char* method) {
    QVariant value;
    if(!QMetaObject::invokeMethod(root,method,Q_RETURN_ARG(QVariant,value)))
        throw std::runtime_error("consent harness callable is unavailable");
    return value;
}
QJsonValue json_value(QVariant value) {
    if(value.canConvert<QJSValue>())value=value.value<QJSValue>().toVariant();
    return QJsonValue::fromVariant(value);
}
QQuickItem* action(QObject* root,bool accept) {
    const auto value=invoke(root,accept ? "acceptAction" : "cancelAction");
    auto* object=value.value<QObject*>();
    if(!object && value.canConvert<QJSValue>())object=value.value<QJSValue>().toQObject();
    auto* item=qobject_cast<QQuickItem*>(object);
    if(!item)throw std::runtime_error("actual standard dialog action is unavailable");
    return item;
}
QRectF scene_rect(QQuickItem* item) {
    return item->mapRectToScene(QRectF(0,0,item->width(),item->height()));
}
QRectF visible_rect(QQuickItem* item,QQuickWindow* window) {
    QRectF result(0,0,window->width(),window->height());
    for(auto* parent=item->parentItem();parent;parent=parent->parentItem())
        if(parent->clip())result=result.intersected(scene_rect(parent));
    return result;
}
Object geometry(QQuickItem* item,QQuickWindow* window) {
    const auto rect=scene_rect(item),visible=visible_rect(item,window);
    QString accessible;
    if(auto* interface=QAccessible::queryAccessibleInterface(item))accessible=interface->text(QAccessible::Name);
    return {{"x",rect.x()},{"y",rect.y()},{"width",rect.width()},{"height",rect.height()},
        {"visible",item->isVisible()},{"enabled",item->isEnabled()},
        {"center_reachable",visible.contains(rect.center())},
        {"whole_reachable",visible.adjusted(-1,-1,1,1).contains(rect)},
        {"text",item->property("text").toString()},{"accessible_name",accessible}};
}
bool reveal_edge(QQuickItem* item,QQuickWindow* window,bool bottom) {
    for(auto* parent=item->parentItem();parent;parent=parent->parentItem()) {
        if(!parent->property("contentY").isValid() || !parent->property("contentHeight").isValid())continue;
        if(parent->property("interactive").isValid() && !parent->property("interactive").toBool())return false;
        if(!parent->isVisible() || !parent->isEnabled())return false;
        const auto target=scene_rect(item),viewport=scene_rect(parent);
        const auto delta=bottom ? target.bottom()-viewport.bottom() : target.top()-viewport.top();
        const auto current=parent->property("contentY").toDouble();
        const auto maximum=std::max(0.0,parent->property("contentHeight").toDouble()-parent->height());
        parent->setProperty("contentY",std::clamp(current+delta,0.0,maximum));
        drain();
    }
    const auto target=scene_rect(item),viewport=visible_rect(item,window);
    const QPointF edge(target.center().x(),bottom ? target.bottom()-1 : target.top()+1);
    return item->isVisible() && viewport.adjusted(-1,-1,1,1).contains(edge);
}
void click(QQuickItem* item,QQuickWindow* window) {
    if(!item->isVisible() || !item->isEnabled() ||
       !visible_rect(item,window).contains(scene_rect(item).center()))
        throw std::runtime_error("actual dialog control is outside the reachable viewport");
    const auto point=scene_rect(item).center().toPoint();
    QTest::mouseClick(window,Qt::LeftButton,Qt::NoModifier,point,1);
    drain();
}
}
int main(int argc,char** argv) {
    if(argc!=2 && !(argc==3 && (QByteArray(argv[2])=="--submit" || QByteArray(argv[2])=="--markdown")))return 96;
    const bool submit_mode=argc==3 && QByteArray(argv[2])=="--submit";
    const bool markdown_mode=argc==3 && QByteArray(argv[2])=="--markdown";
    QTemporaryDir storage;if(!storage.isValid())return 97;
    qputenv("XDG_DATA_HOME",storage.path().toUtf8());
    qputenv("XDG_CONFIG_HOME",storage.path().toUtf8());
    QGuiApplication app(argc,argv);
    QGuiApplication::setOrganizationName("EdiIndependentConsent");
    QGuiApplication::setApplicationName("consent-"+QUuid::createUuid().toString(QUuid::WithoutBraces));
    QAccessible::setActive(true);
    edi_app::use_fresh_settings();edi_app::use_design_font();
    FixtureServices fixture;
    QQmlApplicationEngine engine;
    auto owned=std::make_unique<edi_app::Session>(fixture.dependencies,nullptr);
    auto* session=owned.get();
    edi_app::configure_engine(engine,std::move(owned));
    engine.load(QUrl::fromLocalFile(QString::fromLocal8Bit(argv[1])));
    if(engine.rootObjects().size()!=1)return 95;
    auto* root=engine.rootObjects().front();auto* window=qobject_cast<QQuickWindow*>(root);
    if(!window)return 94;
    drain();
    const auto find=[&](const char* name) {
        auto* object=root->findChild<QObject*>(QString::fromUtf8(name));
        auto* item=qobject_cast<QQuickItem*>(object);
        if(!item)throw std::runtime_error("actual production consent content is unavailable");
        return item;
    };
    const auto markdown_body=[&]() -> QQuickItem* {
        auto* row=root->findChild<QQuickItem*>("markdown.row");
        if(!row)throw std::runtime_error("actual message delegate missing");
        for(auto* item:row->findChildren<QQuickItem*>())
            if(item->isVisible() && item->property("readOnly").isValid())return item;
        throw std::runtime_error("actual visible message body missing");
    };
    const auto markdown_document=[&]() -> QTextDocument* {
        auto* wrapper=markdown_body()->property("textDocument").value<QQuickTextDocument*>();
        if(!wrapper || !wrapper->textDocument())throw std::runtime_error("actual Qt text document missing");
        return wrapper->textDocument();
    };
    const auto snapshot=[&] {
        if(markdown_mode) {
            auto* body=markdown_body();auto* document=markdown_document();
            Array fragments,blocks;
            for(auto block=document->begin();block.isValid();block=block.next()) {
                blocks.push_back(Object{{"text",block.text()},{"listed",block.textList()!=nullptr}});
                for(auto it=block.begin();!it.atEnd();++it) {
                    const auto fragment=it.fragment();if(!fragment.isValid())continue;
                    const auto format=fragment.charFormat();
                    fragments.push_back(Object{{"text",fragment.text()},
                        {"bold",format.fontWeight()>=QFont::DemiBold},
                        {"fixed_pitch",format.fontFixedPitch() || QFontInfo(format.font()).fixedPitch()}});
                }
            }
            return Object{{"ui",Object{{"original",root->findChild<QObject*>("markdown.row")->property("text").toString()},
                {"plain",document->toPlainText()},{"selected",body->property("selectedText").toString()},
                {"read_only",body->property("readOnly").toBool()},
                {"select_by_mouse",body->property("selectByMouse").toBool()},
                {"body",geometry(body,window)},{"fragments",fragments},{"blocks",blocks}}}};
        }

        Object vm{{"connected",session->assistant()->connected()},{"state",session->assistant()->state()},
            {"can_cancel",session->assistant()->canCancel()},{"last_error",session->assistant()->lastError()},
            {"consent_required",session->assistant()->contextConsentRequired()},
            {"context",session->assistant()->contextPreview()}};
        Object ui{{"window_width",window->width()},{"window_height",window->height()},
            {"dialog",json_value(invoke(root,"consentState"))}};
        if(root->findChild<QObject*>("assistant.contextSummary")) {
            ui["summary"]=geometry(find("assistant.contextSummary"),window);
            ui["details"]=geometry(find("assistant.contextDetailsToggle"),window);
            auto* preview=find("assistant.contextPreview");
            ui["preview"]=Object{{"text",preview->property("text").toString()},
                {"visible",preview->isVisible()},
                {"read_only",preview->property("readOnly").toBool()},
                {"select_by_mouse",preview->property("selectByMouse").toBool()},
                {"selected_text",preview->property("selectedText").toString()}};
            if(ui["dialog"].toObject()["visible"].toBool()) {
                ui["accept"]=geometry(action(root,true),window);
                ui["cancel"]=geometry(action(root,false),window);
            }
        }
        if(submit_mode) {
            ui["panel"]=json_value(invoke(root,"panelState"));
            auto* editor=find("assistant.composer");
            ui["composer"]=geometry(editor,window);
            ui["draft"]=editor->property("text").toString();
            ui["send"]=geometry(find("assistant.send"),window);
            Array messages;
            auto* model=session->assistant()->messages();
            for(int row=0;row<model->count();++row) {
                Object value;
                for(const auto& name:model->roleNames())
                    value[QString::fromUtf8(name)]=QJsonValue::fromVariant(model->get(row,QString::fromUtf8(name)));
                messages.push_back(value);
            }
            vm["messages"]=messages;
            vm["selected_model"]=session->assistant()->selectedModel();
            vm["selected_effort"]=session->assistant()->selectedEffort();
        }
        return Object{{"vm",vm},{"ui",ui}};
    };
    std::string line;
    while(std::getline(std::cin,line)) {
        try {
            const auto input=decode(QByteArray::fromStdString(line)).toObject();
            const auto op=input["op"].toString();Object result;
            if(markdown_mode && op=="markdown_row") {
                if(!QMetaObject::invokeMethod(root,"setRow",Q_ARG(QVariant,input["kind"].toString()),
                    Q_ARG(QVariant,input["text"].toString()),Q_ARG(QVariant,input["dark"].toBool())))
                    throw std::runtime_error("actual message harness action missing");
                window->update();drain();
            } else if(markdown_mode && op=="markdown_select") {
                auto* body=markdown_body();click(body,window);
                if(!QMetaObject::invokeMethod(body,"select",Q_ARG(int,input["start"].toInt()),Q_ARG(int,input["end"].toInt())))
                    throw std::runtime_error("actual TextEdit selection unavailable");
                if(input["type_x"].toBool())QTest::keyClick(window,Qt::Key_X);
            } else if(markdown_mode && op=="markdown_copy") {
                if(!QMetaObject::invokeMethod(markdown_body(),"copy"))
                    throw std::runtime_error("actual TextEdit copy unavailable");
                result={{"clipboard",QGuiApplication::clipboard()->text()}};
            } else if(markdown_mode && op=="fixture_image") {
                const auto path=storage.path()+"/original-image.png";
                QImage image(4,4,QImage::Format_ARGB32);image.fill(Qt::red);
                const bool saved=image.save(path,"PNG");QImage reread(path);
                result={{"url",QUrl::fromLocalFile(path).toString()},{"saved",saved},
                    {"valid_original_image",!reread.isNull()}};
            } else if(markdown_mode && op=="markdown_resource") {
                const auto resource=markdown_document()->resource(QTextDocument::ImageResource,QUrl(input["url"].toString()));
                result={{"resource_valid",resource.isValid() && !resource.isNull()}};
            } else if(submit_mode && op=="type_draft") {
                auto* editor=find("assistant.composer");click(editor,window);
                const auto text=input["text"].toString();
                for(const auto character:text) {
                    if(character.unicode()>126 || character.unicode()<32)
                        throw std::invalid_argument("original typing fixture uses printable ASCII");
                    QTest::keyClick(window,character.toLatin1(),Qt::NoModifier,1);
                }
            } else if(submit_mode && op=="clear_history")session->assistant()->clearHistory();
            else if(submit_mode && op=="close_project")session->closeProject();
            else if(submit_mode && op=="select_skill")session->assistant()->selectSkill(input["id"].toString());
            else if(submit_mode && op=="click_send")click(find("assistant.send"),window);
            else if(submit_mode && op=="press_enter") {
                auto* editor=find("assistant.composer");click(editor,window);
                QTest::keyClick(window,Qt::Key_Return,Qt::NoModifier,1);
            } else if(submit_mode && op=="select_effort")session->assistant()->setSelectedEffort(input["id"].toString());
            else if(op=="sign_in")session->assistant()->signIn();
            else if(op=="sign_out")session->assistant()->signOut();
            else if(op=="send_text")session->assistant()->send(input["text"].toString());
            else if(op=="cancel")session->assistant()->cancel();
            else if(op=="create_project")result={{"created",session->createProject(input["name"].toString(),"Independent consent fixture",storage.path()+"/project")}};
            else if(op=="viewport") {
                window->setWidth(input["width"].toInt());window->setHeight(input["height"].toInt());
                auto font=app.font();font.setPixelSize(input["font_pixels"].toInt());app.setFont(font);
                window->setProperty("font",font);
            } else if(op=="open_dialog")invoke(root,"openConsent");
            else if(op=="click_accept")click(action(root,true),window);
            else if(op=="click_cancel")click(action(root,false),window);
            else if(op=="toggle_details") {
                auto* details=find("assistant.contextDetailsToggle");
                result={{"reachable",reveal_edge(details,window,false)}};
                click(details,window);
            } else if(op=="summary_edges") {
                auto* summary=find("assistant.contextSummary");
                const bool top=reveal_edge(summary,window,false);
                const bool bottom=reveal_edge(summary,window,true);
                result={{"top_reachable",top},{"bottom_reachable",bottom}};
            } else if(op=="select_preview") {
                auto* preview=find("assistant.contextPreview");
                result={{"reachable",reveal_edge(preview,window,false)}};
                preview->forceActiveFocus();
                QMetaObject::invokeMethod(preview,"selectAll");
                result["selected_before_key"]=preview->property("selectedText").toString();
                QTest::keyClick(window,Qt::Key_X);
            } else if(op!="inspect")result=fixture.dispatch(input);
            drain();auto output=fixture.snapshot();output["reply"]=result;
            const auto state=snapshot();output["vm"]=state["vm"];output["ui"]=state["ui"];
            std::cout<<encode(output).toStdString()<<'\n'<<std::flush;
        } catch(const std::exception& error) {
            std::cout<<encode(Object{{"host_error",QString::fromUtf8(error.what())}}).toStdString()<<'\n'<<std::flush;
        }
    }
}
