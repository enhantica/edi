// New real-QML component consumer; no Main replacement, fake VM or producer CPP inclusion.
#include "fixture_services.hpp"
#include "session.hpp"
#include "assistant_view_model.hpp"
#include "engine_setup.hpp"
#include <QAccessible>
#include <QCryptographicHash>
#include <QWheelEvent>
#include <QAbstractTextDocumentLayout>
#include <QClipboard>
#include <QColor>
#include <QDir>
#include <QFile>
#include <QDesktopServices>
#include <QStringList>
#include <QGuiApplication>
#include <QFont>
#include <QFontInfo>
#include <QFontMetricsF>
#include <QImage>
#include <QQuickTextDocument>
#include <QScopeGuard>
#include <QTextBlock>
#include <QTextFragment>
#include <QTextList>
#include <QTextLayout>
#include <QTextTable>
#include <QTextCursor>
#include <QScreen>
#include <QJsonValue>
#include <QJSValue>
#include <QQmlApplicationEngine>
#include <QQmlExpression>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickWindow>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QTest>
#include <QUuid>
#include <QtQml/qqmlextensionplugin.h>
#include <algorithm>

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
class ProviderControlDocument final : public QTextDocument {
protected:
    QVariant loadResource(int, const QUrl&) override { return {}; }
};
// Ordinary Qt Markdown reference for header semantics; never permit resource IO.
class NoResourceReferenceDocument final : public QTextDocument {
protected:
    QVariant loadResource(int, const QUrl&) override { return QVariant::fromValue(QImage{}); }
};
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
    if(argc!=2 && !(argc==3 && (QByteArray(argv[2])=="--submit" || QByteArray(argv[2])=="--markdown" || QByteArray(argv[2])=="--usage")))return 96;
    const bool submit_mode=argc==3 && QByteArray(argv[2])=="--submit";
    const bool usage_mode=argc==3 && QByteArray(argv[2])=="--usage";
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
    auto owned=usage_mode ? std::make_unique<edi_app::Session>(nullptr)
        : std::make_unique<edi_app::Session>(fixture.dependencies,nullptr);
    auto* session=owned.get();
    edi_app::configure_engine(engine,std::move(owned));
    engine.load(QUrl::fromLocalFile(QString::fromLocal8Bit(argv[1])));
    if(engine.rootObjects().size()!=1)return 95;
    auto* root=engine.rootObjects().front();auto* window=qobject_cast<QQuickWindow*>(root);
    if(!window)return 94;
    drain();
    OwnedUrlRecorder report_urls;
    const QStringList observed_schemes{QStringLiteral("file"),QStringLiteral("http"),
        QStringLiteral("https"),QStringLiteral("javascript"),QStringLiteral("data"),
        QStringLiteral("report-invalid")};
    if(markdown_mode)for(const auto& scheme:observed_schemes)QDesktopServices::setUrlHandler(scheme,&report_urls,"record");
    const auto restore_urls=qScopeGuard([&] {
        if(markdown_mode)for(const auto& scheme:observed_schemes)QDesktopServices::unsetUrlHandler(scheme);
    });
    if(usage_mode && session->assistant()->metaObject()->indexOfSignal("usageChanged()")>=0)
        QObject::connect(session->assistant(),SIGNAL(usageChanged()),&report_urls,SLOT(changed()));
    bool activity_observation=false;
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
    const auto json_property=[](QObject* object,const char* name) {
        const auto value=object->property(name);
        return QJsonValue::fromVariant(value.metaType()==QMetaType::fromType<QJSValue>()
            ? value.value<QJSValue>().toVariant() : value);
    };
    const auto usage_button=[&]() -> QQuickItem* {
        auto* button=root->findChild<QQuickItem*>("assistant.usage");
        if(!button)throw std::runtime_error("actual usage control unavailable");
        return button;
    };
    Array usage_dialog_candidates;
    const auto usage_dialog=[&]() -> QObject* {
        QObject* found=nullptr;usage_dialog_candidates=Array{};
        for(auto* object:root->findChildren<QObject*>()) {
            if(object->property("title").toString()!="Usage" || !object->property("contentItem").isValid())continue;
            Array ancestry;
            for(auto* parent=object->parent();parent;parent=parent->parent())
                ancestry.push_back(Object{{"class",parent->metaObject()->className()},
                    {"name",parent->objectName()},
                    {"identity",QString::number(reinterpret_cast<quintptr>(parent),16)}});
            const bool actual_dialog=object->inherits("QQuickDialog")
                && object->metaObject()->indexOfProperty("opened")>=0
                && object->metaObject()->indexOfProperty("standardButtons")>=0;
            usage_dialog_candidates.push_back(Object{
                {"class",object->metaObject()->className()},{"name",object->objectName()},
                {"identity",QString::number(reinterpret_cast<quintptr>(object),16)},
                {"actual_dialog",actual_dialog},{"ancestry",ancestry}});
            if(!actual_dialog)continue;
            if(found && found!=object)throw std::runtime_error((QString("actual usage dialog is not unique: ")
                +QString::fromUtf8(encode(usage_dialog_candidates))).toStdString());
            found=object;
        }
        if(!found)throw std::runtime_error((QString("actual usage dialog unavailable: ")
            +QString::fromUtf8(encode(usage_dialog_candidates))).toStdString());
        return found;
    };
    const auto usage_ui=[&]() -> Object {
        auto* button=usage_button(); QQuickItem* canvas=nullptr;
        for(auto* item:button->findChildren<QQuickItem*>())
            if(QString::fromLatin1(item->metaObject()->className()).contains("Canvas")) {
                if(canvas)throw std::runtime_error("actual usage Canvas is not unique");canvas=item;
            }
        if(!canvas)throw std::runtime_error("actual usage Canvas unavailable");
        window->update();drain();
        const auto actual=window->grabWindow();
        const auto region=scene_rect(canvas).toAlignedRect();
        const auto pixels=actual.copy(region).convertToFormat(QImage::Format_RGBA8888);
        if(actual.isNull() || pixels.isNull())throw std::runtime_error("actual usage framebuffer unavailable");
        Object image{{"width",pixels.width()},{"height",pixels.height()},
            {"sha256",QString::fromLatin1(QCryptographicHash::hash(
                QByteArrayView(reinterpret_cast<const char*>(pixels.constBits()),pixels.sizeInBytes()),
                QCryptographicHash::Sha256).toHex())}};
        auto* dialog=usage_dialog();auto* content=dialog->property("contentItem").value<QQuickItem*>();
        auto* outer=content?content->parentItem():nullptr;
        if(!content || !outer)throw std::runtime_error("actual usage popup item unavailable");
        Array labels,scrollables,bars;
        for(auto* item:content->findChildren<QQuickItem*>()) {
            if(item->property("text").isValid()) {
                auto observed=geometry(item,window);
                observed["pixel_size"]=item->property("font").value<QFont>().pixelSize();
                labels.push_back(observed);
            }
            if(item->property("contentHeight").isValid() && item->property("contentY").isValid()) {
                auto observed=geometry(item,window);
                observed["content_height"]=item->property("contentHeight").toDouble();
                observed["content_y"]=item->property("contentY").toDouble();
                scrollables.push_back(observed);
            }
            if(QString::fromLatin1(item->metaObject()->className()).contains("ScrollBar")) {
                auto observed=geometry(item,window);
                auto* context=qmlContext(item);
                observed["component_url"]=context?context->baseUrl().toString():QString();
                observed["position"]=item->property("position").toDouble();
                observed["size"]=item->property("size").toDouble();
                bars.push_back(observed);
            }
        }
        return {{"button",geometry(button,window)},{"dialog_candidates",usage_dialog_candidates},
            {"canvas",Object{{"geometry",geometry(canvas,window)},
                {"window_available",json_value(canvas->property("windowAvailable"))},{"frame",image}}},
            {"popup",Object{{"visible",dialog->property("visible").toBool()},
                {"opened",dialog->property("opened").toBool()},{"geometry",geometry(outer,window)},
                {"labels",labels},{"scrollables",scrollables},{"scrollbars",bars}}}};
    };
    const auto snapshot=[&] {
        if(markdown_mode && activity_observation) {
            auto* row=root->findChild<QQuickItem*>("markdown.row");
            QString visible_text;
            const auto collect=[&](auto&& self,QQuickItem* item)->void {
                if(!item || !item->isVisible())return;
                if(item->property("text").isValid())visible_text+=item->property("text").toString()+"\n";
                for(auto* child:item->childItems())self(self,child);
            };
            collect(collect,row);
            return Object{{"ui",Object{{"visible_text",visible_text},
                {"payload",json_property(row,"payload")},
                {"desktop_urls",report_urls.urls}}}};
        }
        if(markdown_mode) {
            auto* body=markdown_body();auto* document=markdown_document();
            if(!window->screen())throw std::runtime_error("actual Markdown display DPI unavailable");
            const auto font_facts=[&](const QFont& supplied) {
                const auto effective=supplied.resolve(document->defaultFont());
                const QFontInfo info(effective); const QFontMetricsF metrics(effective);
                return Object{{"family",info.family()},{"pixel_size",info.pixelSize()},
                    {"point_size",info.pointSizeF()},{"height",metrics.height()},
                    {"x_height",metrics.xHeight()},{"cap_height",metrics.capHeight()}};
            };
            const auto table_facts=[](QTextDocument* source) {
                Array tables;
                for(auto* frame:source->rootFrame()->childFrames()) {
                    auto* table=qobject_cast<QTextTable*>(frame);if(!table)continue;
                    const auto format=table->format(); Array cells;
                    for(int row=0;row<table->rows();++row)for(int column=0;column<table->columns();++column) {
                        const auto cell=table->cellAt(row,column);
                        auto cursor=cell.firstCursorPosition();
                        cursor.setPosition(cell.lastCursorPosition().position(),QTextCursor::KeepAnchor);
                        const auto cell_format=cell.format().toTableCellFormat();
                        const auto first=cell.firstCursorPosition().block().begin().fragment();
                        Array paragraph_alignments;
                        for(auto block=cell.firstCursorPosition().block();block.isValid()
                            && block.position()<=cell.lastCursorPosition().position();block=block.next()) {
                            paragraph_alignments.push_back(Object{{"text",block.text()},
                                {"left",block.blockFormat().alignment().testFlag(Qt::AlignLeft)
                                    && !(block.blockFormat().alignment()&(Qt::AlignRight|Qt::AlignHCenter|Qt::AlignJustify))}});
                        }
                        cells.push_back(Object{{"row",row},{"column",column},{"text",cursor.selectedText()},
                            {"row_span",cell.rowSpan()},{"column_span",cell.columnSpan()},
                            {"paragraph_alignments",paragraph_alignments},
                            {"top_padding",cell_format.hasProperty(QTextFormat::TableCellTopPadding)
                                ? cell_format.topPadding() : format.cellPadding()},
                            {"bottom_padding",cell_format.hasProperty(QTextFormat::TableCellBottomPadding)
                                ? cell_format.bottomPadding() : format.cellPadding()},
                            {"left_padding",cell_format.hasProperty(QTextFormat::TableCellLeftPadding)
                                ? cell_format.leftPadding() : format.cellPadding()},
                            {"right_padding",cell_format.hasProperty(QTextFormat::TableCellRightPadding)
                                ? cell_format.rightPadding() : format.cellPadding()},
                            {"first_bold",first.isValid() && first.charFormat().fontWeight()>=QFont::DemiBold},
                            {"background",cell_format.background().style()==Qt::NoBrush ? QJsonValue(QJsonValue::Null)
                                : QJsonValue(cell_format.background().color().name(QColor::HexArgb))},
                            {"top_border",cell_format.topBorder()},{"bottom_border",cell_format.bottomBorder()},
                            {"left_border",cell_format.leftBorder()},{"right_border",cell_format.rightBorder()}});
                    }
                    tables.push_back(Object{{"rows",table->rows()},{"columns",table->columns()},
                        {"header_rows",format.headerRowCount()},{"border",format.border()},
                        {"border_style",static_cast<int>(format.borderStyle())},
                        {"collapsed",format.borderCollapse()},{"padding",format.cellPadding()},
                        {"spacing",format.cellSpacing()},{"cells",cells}});
                }
                return tables;
            };
            const auto qml_value=[&](const char* expression) {
                QQmlExpression value(qmlContext(root),root,QString::fromLatin1(expression));
                const auto result=value.evaluate();
                if(value.hasError())throw std::runtime_error("actual shared font/theme observation unavailable");
                return result;
            };
            const auto original=root->findChild<QObject*>("markdown.row")->property("text").toString();
            const auto tables=table_facts(document); Array reference_tables;
            if(!tables.empty()) {
                NoResourceReferenceDocument reference;
                reference.setMarkdown(original,QTextDocument::MarkdownFeatures(QTextDocument::MarkdownDialectGitHub)
                    |QTextDocument::MarkdownNoHTML);
                reference_tables=table_facts(&reference);
            }
            Array fragments,blocks,lines;
            for(auto block=document->begin();block.isValid();block=block.next()) {
                const auto* list=block.textList();
                blocks.push_back(Object{{"text",block.text()},{"listed",list!=nullptr},
                    {"list_indent",list ? list->format().indent() : 0}});
                const auto bounds=document->documentLayout()->blockBoundingRect(block);
                if(const auto* layout=block.layout())for(int index=0;index<layout->lineCount();++index) {
                    const auto line=layout->lineAt(index);
                    lines.push_back(Object{{"start",block.position()+line.textStart()},
                        {"length",line.textLength()},{"x",bounds.x()+line.x()},
                        {"width",line.naturalTextWidth()}});
                }
                for(auto it=block.begin();!it.atEnd();++it) {
                    const auto fragment=it.fragment();if(!fragment.isValid())continue;
                    const auto format=fragment.charFormat();
                    fragments.push_back(Object{{"text",fragment.text()},
                        {"bold",format.fontWeight()>=QFont::DemiBold},
                        {"fixed_pitch",format.fontFixedPitch() || QFontInfo(format.font()).fixedPitch()},
                        {"effective_font",font_facts(format.font())},
                        {"anchor",format.isAnchor()},{"href",format.anchorHref()},
                        {"foreground",format.foreground().color().name(QColor::HexArgb)}});
                }
            }
            QQmlExpression accent(qmlContext(root),root,"EaStyle.Colors.themeAccent");
            const auto accent_value=accent.evaluate();
            if(accent.hasError() || !accent_value.canConvert<QColor>())
                throw std::runtime_error("actual application theme accent is unavailable");
            return Object{{"ui",Object{{"original",root->findChild<QObject*>("markdown.row")->property("text").toString()},
                {"plain",document->toPlainText()},{"selected",body->property("selectedText").toString()},
                {"read_only",body->property("readOnly").toBool()},
                {"select_by_mouse",body->property("selectByMouse").toBool()},
                {"body",geometry(body,window)},{"fragments",fragments},{"blocks",blocks},
                {"lines",lines},{"theme_accent",accent_value.value<QColor>().name(QColor::HexArgb)},
                {"body_font",font_facts(body->property("font").value<QFont>())},
                {"font_resources",Object{{"body_family",qml_value("EaStyle.Fonts.fontFamily").toString()},
                    {"mono_family",qml_value("EaStyle.Fonts.monoFontFamily").toString()},
                    {"body_loaded",qml_value("EaStyle.Fonts.ptSansRegular.status === FontLoader.Ready").toBool()},
                    {"mono_loaded",qml_value("EaStyle.Fonts.ptMono.status === FontLoader.Ready").toBool()},
                    {"mono_source",qml_value("EaStyle.Fonts.ptMono.source").toString()}}},
                {"tables",tables},{"qt_reference_tables",reference_tables},
                {"logical_dpi_y",window->screen()->logicalDotsPerInchY()},
                {"theme_background",window->color().name(QColor::HexArgb)},
                {"report_signal_present",root->findChild<QObject*>("markdown.row")->metaObject()
                    ->indexOfSignal("reportRequested(QString,QString)")>=0},
                {"report_events",json_property(root,"reportEvents")},
                {"desktop_urls",report_urls.urls},
                {"cursor_shape",static_cast<int>(window->cursor().shape())},
                {"pointing_hand",window->cursor().shape()==Qt::PointingHandCursor}}}};

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
        if(submit_mode || usage_mode) {
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
        if(usage_mode) {
            auto* actual=session->assistant();
            const auto present=actual->metaObject()->indexOfProperty("usage")>=0;
            vm["usage_observer"]=Object{{"property_present",present},
                {"refresh_present",actual->metaObject()->indexOfMethod("refreshUsage()")>=0},
                {"changes",report_urls.usage_changes},
                {"value",present?json_property(actual,"usage"):QJsonValue()}};
            ui["usage"]=usage_ui();
        }
        return Object{{"vm",vm},{"ui",ui}};
    };
    std::string line;
    while(std::getline(std::cin,line)) {
        try {
            const auto input=decode(QByteArray::fromStdString(line)).toObject();
            const auto op=input["op"].toString();Object result;
            if(usage_mode && op=="refresh_usage") {
                result={{"invoked",QMetaObject::invokeMethod(session->assistant(),"refreshUsage",Qt::DirectConnection)}};
            } else if(usage_mode && op=="click_usage")click(usage_button(),window);
            else if(usage_mode && op=="usage_scale") {
                // Existing EA public sizing knob; observe actual changed fonts before claiming enlarged-font coverage.
                auto* button=usage_button();
                QQmlExpression expression(qmlContext(button),button,
                    QString("EaStyle.Sizes.defaultScale = %1").arg(input["percent"].toInt()));
                expression.evaluate();
                if(expression.hasError())throw std::runtime_error("actual EA scale preference unavailable");
                window->update();drain();
            } else if(usage_mode && op=="usage_wheel") {
                auto* dialog=usage_dialog();auto* content=dialog->property("contentItem").value<QQuickItem*>();
                if(!dialog->property("visible").toBool() || !content)
                    throw std::runtime_error("actual Usage dialog must be visibly open before wheel input");
                const QPointF local=scene_rect(content).center();
                QWheelEvent event(local,window->mapToGlobal(local.toPoint()),QPoint(),QPoint(0,-120),
                    Qt::NoButton,Qt::NoModifier,Qt::ScrollUpdate,false);
                QCoreApplication::sendEvent(window,&event);window->update();drain();
            } else if(usage_mode && op=="clear_history")session->assistant()->clearHistory();
            else if(markdown_mode && op=="desktop_control") {
                const auto path=storage.path()+"/original-url-handler-control.txt";
                QFile control(path);if(!control.open(QIODevice::WriteOnly)
                    || control.write("Original harmless Qt URL control")<0)
                    throw std::runtime_error("owned URL control unavailable");
                control.close();const auto url=QUrl::fromLocalFile(path);
                const bool ok=QDesktopServices::openUrl(url);
                result={{"ok",ok},{"control_url",url.toString(QUrl::FullyEncoded)}};
            } else if(markdown_mode && op=="report_observer_reset")report_urls.urls=Array{};
            else if(markdown_mode && op=="markdown_activity") {
                activity_observation=true;
                if(!QMetaObject::invokeMethod(root,"setActivityRow",
                    Q_ARG(QVariant,input["row"].toObject().toVariantMap())))
                    throw std::runtime_error("actual activity presentation action missing");
                window->update();drain();
            } else if(markdown_mode && op=="markdown_report_row") {
                activity_observation=false;
                if(!QMetaObject::invokeMethod(root,"setReportRow",
                    Q_ARG(QVariant,input["row_id"].toString()),Q_ARG(QVariant,input["text"].toString())))
                    throw std::runtime_error("actual report row presentation action missing");
                window->update();drain();
            } else if(markdown_mode && (op=="markdown_hover_link" || op=="markdown_click_link")) {
                auto* body=markdown_body();QRectF caret;
                if(!QMetaObject::invokeMethod(body,"positionToRectangle",Q_RETURN_ARG(QRectF,caret),
                    Q_ARG(int,input["position"].toInt())))
                    throw std::runtime_error("actual Qt character position unavailable");
                const QPointF point=body->mapToScene(QPointF(caret.x()+1,caret.y()+caret.height()/2));
                QTest::mouseMove(window,point.toPoint());window->update();drain();
                if(op=="markdown_click_link")QTest::mouseClick(window,Qt::LeftButton,Qt::NoModifier,point.toPoint());
            } else if(markdown_mode && op=="markdown_row") {
                activity_observation=false;
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
                const QImage original(storage.path()+"/original-image.png");
                if(original.isNull())throw std::runtime_error("owned image resource control missing");
                auto* document=markdown_document();
                const auto prior_document_provider=document->resourceProvider();
                const auto prior_global_provider=QTextDocument::defaultResourceProvider();
                const auto restore=qScopeGuard([&] {
                    document->setResourceProvider(prior_document_provider);
                    QTextDocument::setDefaultResourceProvider(prior_global_provider);
                });
                int document_calls=0,global_calls=0;
                document->setResourceProvider([&](const QUrl&) -> QVariant {
                    ++document_calls;return original;
                });
                QTextDocument::setDefaultResourceProvider([&](const QUrl&) -> QVariant {
                    ++global_calls;return original;
                });
                const auto resource=document->resource(QTextDocument::ImageResource,QUrl(input["url"].toString()));
                auto image=resource.value<QImage>();
                if(image.isNull() && resource.metaType().id()==QMetaType::QByteArray)
                    image=QImage::fromData(resource.toByteArray());
                const int subject_document_calls=document_calls,subject_global_calls=global_calls;

                // Independent Qt controls: an invalid loader must reach each fallback.
                ProviderControlDocument document_control;
                document_control.setResourceProvider([&](const QUrl&) -> QVariant {
                    ++document_calls;return original;
                });
                const auto document_image=document_control.resource(QTextDocument::ImageResource,
                    QUrl("edi-test-resource:document-control")).value<QImage>();
                const int document_control_calls=document_calls-subject_document_calls;
                const int document_control_global_calls=global_calls-subject_global_calls;
                ProviderControlDocument global_control;
                const auto global_image=global_control.resource(QTextDocument::ImageResource,
                    QUrl("edi-test-resource:global-control")).value<QImage>();
                result={{"resource_valid",resource.isValid() && !resource.isNull()},
                    {"resource_type",QString::fromLatin1(resource.metaType().name())},
                    {"image_null",image.isNull()},{"image_width",image.width()},
                    {"image_height",image.height()},
                    {"document_provider_calls",subject_document_calls},
                    {"global_provider_calls",subject_global_calls},
                    {"document_control_calls",document_control_calls},
                    {"document_control_global_calls",document_control_global_calls},
                    {"global_control_calls",global_calls-subject_global_calls-document_control_global_calls},
                    {"document_control_image",!document_image.isNull() && document_image.size()==original.size()},
                    {"global_control_image",!global_image.isNull() && global_image.size()==original.size()}};
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

#include "probe.moc"
