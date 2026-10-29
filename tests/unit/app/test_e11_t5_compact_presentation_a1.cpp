// SPDX-License-Identifier: BSD-3-Clause
// A1 only: the original public rendered compact row, not a replacement formatter.
#include <QCoreApplication>
#include <QColor>
#include <QJsonArray>
#include <QScopeGuard>
#include <QSignalSpy>
#include <QList>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJSValue>
#include <QPointer>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQmlEngine>
#include <QQmlExpression>
#include <QQuickItem>
#include <QTranslator>
#include <QtQml/qqml.h>
#include <QtTest/qtestcase.h>
#include <functional>
#include <memory>
#include <stdexcept>
#include <vector>

namespace {
struct Checks {
    int count=0,failures=0;
    void require(bool ok,const QString& message) {
        ++count;if(ok)return;++failures;
        QTest::qFail(message.toUtf8().constData(),__FILE__,__LINE__);
    }
    QVariantMap result() const {return {{"ok",failures==0},{"checks",count},{"error",QStringLiteral("%1 individual A1 failures").arg(failures)}};}
};
struct Expected {
    QString name,kind,status,caption,explanation,icon;
    QJsonObject payload;
};
class ContextTranslator final : public QTranslator {
public:
    explicit ContextTranslator(QObject* parent=nullptr):QTranslator(parent){}
    bool isEmpty() const override {return false;}
    QString translate(const char* context,const char* source,const char*,int) const override {
        const QByteArray c(context),s(source);
        if(c=="AssistantMessage" && s=="Assistant error")return QString::fromUtf8("Erreur Å\u00a0β 🧪");
        if(c=="AssistantMessage" && s=="Failed")return QString::fromUtf8("Échec β");
        if(c=="AssistantActions" && s=="Create a project")return QString::fromUtf8("Créer Å\u00a0β 🧪");
        if(c=="AssistantMessage" && s=="Work on the current project")return QString::fromUtf8("Projet sans propriétaire β🧪");
        if(c=="AssistantActions" && s=="Work on the current project")return QString::fromUtf8("Projet natif inconnu β🧪");
        return {};
    }
};
}

class CompactPresentationA1Proof final : public QObject {
    Q_OBJECT
    QQmlEngine* engine_;
    static QString expression(QObject* object,const char* source) {
        QQmlExpression value(QQmlEngine::contextForObject(object),object,QString::fromLatin1(source));
        const auto result=value.evaluate();
        if(value.hasError())throw std::runtime_error(value.error().toString().toStdString());
        return result.toString();
    }
    void checkRow(Checks& check,const Expected& expected,
                  const std::function<void(QObject*,QObject*)>& inspect={}) const {
        QSignalSpy warnings(engine_,&QQmlEngine::warnings);
        QQmlComponent component(engine_);
        component.setData("import QtQuick\nimport edi.app\nAssistantMessage { assistant: Session.assistant }\n",QUrl("qrc:/tests/A1OriginalOwner.qml"));
        if(component.isError())throw std::runtime_error(component.errorString().toStdString());
        const QString raw=QString::fromUtf8("RAW_ONLY_\uFEFF\u00a0β🧪\n{\"shell\":\"private-id\"}");
        const QVariantMap inputs{{"kind",expected.kind},{"text",raw},{"status",expected.status},
            {"payload",expected.payload.toVariantMap()},{"width",600},{"stepNumber",7}};
        std::unique_ptr<QObject> row(component.createWithInitialProperties(inputs));
        if(!row)throw std::runtime_error(component.errorString().toStdString());
        const auto prefix=expected.name+QStringLiteral(": ");
        const bool command=expected.payload.value("type")=="commandExecution" && expected.kind=="activity";
        const QString name=command?QStringLiteral("assistant.command.toggle"):QStringLiteral("assistant.activity.toggle");
        const auto candidates=row->findChildren<QObject*>(name);
        check.require(candidates.size()==1,prefix+"one original rendered disclosure owns this compact row");
        if(candidates.size()!=1)return;
        auto* header=candidates.front();
        check.require(header->property("visible").toBool(),prefix+"actual compact header is visible");
        check.require(header->property("text").toString()==expected.caption,prefix+"actual rendered caption has the independent human wording");
        const auto tooltip=expression(header,"ToolTip.text");
        check.require(tooltip==expected.explanation+QStringLiteral(" · ")+expected.caption,prefix+"actual tooltip preserves explanation and precedence");
        check.require(expression(header,"Accessible.name")==tooltip,prefix+"accessible explanation equals the original visible control meaning");
        auto* content=qobject_cast<QQuickItem*>(header->property("contentItem").value<QObject*>());
        check.require(content,prefix+"the original control's rendered status content exists");
        QStringList texts;
        if(content)for(auto* child:content->findChildren<QObject*>())if(child->metaObject()->indexOfProperty("text")>=0)texts.push_back(child->property("text").toString());
        check.require(texts.count(expected.icon)==1,prefix+"one rendered status mark preserves the truthful outcome");
        check.require(texts.count(expected.caption)==1 && texts.count(QStringLiteral("7."))==1,prefix+"one caption and one numbered step remain separate from status");
        check.require(!tooltip.contains("RAW_ONLY_") && !header->property("text").toString().contains("private-id"),prefix+"technical row text never enters compact human presentation");
        check.require(row->property("text").toString()==raw,prefix+"literal Unicode/whitespace/raw row text is not rewritten by presentation");
        const auto retained=QJsonDocument::fromJson(expression(row.get(),"JSON.stringify(payload)").toUtf8()).object();
        check.require(retained==expected.payload,prefix+"public compact input is unchanged, including technical/error carriers");
        check.require(!header->property("checked").toBool() && !row->property("technicalCopied").toBool(),prefix+"characterization never expands or copies the row");
        if(inspect)inspect(row.get(),header);
        check.require(warnings.isValid() && warnings.isEmpty(),prefix+"the original typed compact input emits no QML binding/JavaScript errors");
    }
    static void checkOutcome(Checks& check,QObject* row,QObject* header,
                             const QString& caption,const QString& explanation,
                             const QString& icon,const QString& key) {
        check.require(header->property("text").toString()==caption,
                      "A1 current original compact control retains the literal human caption");
        const auto accessible=explanation+QStringLiteral(" · ")+caption;
        check.require(expression(header,"ToolTip.text")==accessible &&
                      expression(header,"Accessible.name")==accessible,
                      "A1 current tooltip and accessibility retain the independent truthful explanation");
        auto* content=qobject_cast<QQuickItem*>(header->property("contentItem").value<QObject*>());
        check.require(content,"A1 original compact status content remains present");
        QList<QObject*> marks;
        if(content)for(auto* child:content->findChildren<QObject*>())
            if(child->property("text").toString()==icon)marks.push_back(child);
        check.require(marks.size()==1,"A1 has one truthful current rendered status mark");
        if(marks.size()==1) {
            const auto expected=key=="running"?expression(header,"String(EaStyle.Colors.themeAccent)"):
                expression(header,("String(FitOutcomes.color("+QJsonDocument(QJsonArray{key}).toJson(QJsonDocument::Compact).mid(1).chopped(1)+"))").constData());
            check.require(marks.front()->property("color").value<QColor>()==QColor(expected),
                          "A1 status mark uses the existing independent semantic outcome colour owner");
        }
        const auto details=row->findChildren<QObject*>(QStringLiteral("assistant.activity.details"));
        check.require(details.size()==1,"A1 original lazy human-detail field remains identifiable");
        if(details.size()==1)check.require(!details.front()->property("visible").toBool() &&
            details.front()->property("text").toString().isEmpty(),
            "Collapsed A1 never renders or retains full human/technical detail text");
        check.require(expression(row,"humanDetailsSnapshot === null")=="true" &&
                      !header->property("checked").toBool() && !row->property("technicalCopied").toBool(),
                      "A1 compact observation stays collapsed with no human snapshot or copy feedback");
    }
    void malformedFieldsAndColdBoundary(Checks& check) const {
        const QString unknown=QStringLiteral("The result could not be confirmed. Inspect the project before continuing.");
        const std::vector<Expected> rows{
            {"running-mark-colour","activity","in_progress","Read files","In progress","hourglass-half",
                {{"type","commandExecution"},{"commandCategory","read"},{"status","inProgress"}}},
            {"stopped-neutral-colour","activity","interrupted","Perform assistant action","Stopped","stop-circle",{}},
            {"refused-mark-colour","activity","refused","Perform assistant action","Refused","times-circle",{}},
            {"native-uncertain-before-running","activity","in_progress","Perform assistant action",unknown,"exclamation-circle",
                {{"nativeOutcome",QJsonObject{{"status","unconfirmed"}}}}},
            {"native-applied-before-failure","activity","failed","Perform assistant action","Changes were made, but completion could not be confirmed.","exclamation-circle",
                {{"nativeOutcome",QJsonObject{{"status","applied_unconfirmed"}}}}},
            {"typed-native-status-ignored","activity","failed","Perform assistant action","Failed","times-circle",
                {{"nativeOutcome",QJsonObject{{"status",true},{"message","RAW_ONLY_native"}}}}},
            {"typed-native-array-ignored","activity","failed","Perform assistant action","Failed","times-circle",
                {{"nativeOutcome",QJsonArray{QStringLiteral("unconfirmed")}}}},
            {"unknown-public-state","activity","inProgress","Perform assistant action",unknown,"exclamation-circle",{}},
            {"empty-public-state","activity","","Perform assistant action",unknown,"exclamation-circle",{}},
            {"public-state-not-trimmed","activity",QString::fromUtf8("completed\u00a0"),"Perform assistant action",unknown,"exclamation-circle",{}},
            {"old-command-with-exit-zero","activity","failed","Read files",unknown,"exclamation-circle",
                {{"type","commandExecution"},{"commandCategory","read"},{"status","inProgress"},{"exitCode",0}}},
            {"terminal-command-not-success-from-exit","activity","failed","Searched files","Failed","times-circle",
                {{"type","commandExecution"},{"commandCategory","search"},{"status","failed"},{"exitCode",0}}},
            {"terminal-refusal-not-renamed","activity","refused","Listed files",unknown,"exclamation-circle",
                {{"type","commandExecution"},{"commandCategory","listFiles"},{"status","declined"}}},
            {"typed-command-status","activity","completed","Ran command",unknown,"exclamation-circle",
                {{"type","commandExecution"},{"status",0},{"exitCode",0}}},
            {"typed-command-category","activity","completed","Ran command","Completed","check-circle",
                {{"type","commandExecution"},{"commandCategory",QJsonArray{QStringLiteral("read")}},{"status","completed"}}},
            {"decision-really-precedes-command-caption","activity","completed","Review requested action","Completed","check-circle",
                {{"type","commandExecution"},{"status","completed"},{"commandCategory","read"},{"decision","deny"},{"item_id","original-compact-id"}}},
            {"typed-decision-does-not-shadow-native","activity","completed","Create a project","Completed","check-circle",
                {{"type","dynamicToolCall"},{"tool","create_project"},{"decision",false},{"item_id","original-compact-id"}}},
            {"typed-item-id-does-not-shadow-native","activity","completed","Create a project","Completed","check-circle",
                {{"type","dynamicToolCall"},{"tool","create_project"},{"decision","deny"},{"item_id",7}}},
            {"prototype-name-is-not-human-label","activity","completed","Perform assistant action","Completed","check-circle",{{"type","constructor"}}},
            {"typed-native-tool-fallback","activity","completed","Work on the current project","Completed","check-circle",
                {{"type","dynamicToolCall"},{"tool",QJsonArray{QStringLiteral("create_project")}}}},
            {"native-name-is-literal","activity","completed","Work on the current project","Completed","check-circle",
                {{"type","dynamicToolCall"},{"tool",QString::fromUtf8("create_project\u00a0β🧪")}}},
            {"unconfirmed-error-kind-before-label","error","failed","Assistant error",unknown,"exclamation-circle",
                {{"type","dynamicToolCall"},{"tool","create_project"},{"nativeOutcome",QJsonObject{{"status","unconfirmed"},{"action_error","project_required"},{"message","RAW_ONLY_native_error"}}}}}
        };
        for(const auto& expected:rows)try {
            checkRow(check,expected,[&](QObject* row,QObject* header){
                const QString key=expected.icon=="times-circle"?(expected.status=="refused"?"refused":"failed"):
                    expected.icon=="check-circle"?"success":expected.icon=="stop-circle"?"stopped":
                    expected.icon=="hourglass-half"?"running":"notConverged";
                checkOutcome(check,row,header,expected.caption,expected.explanation,expected.icon,key);
            });
        }catch(const std::exception& error){check.require(false,expected.name+": "+QString::fromUtf8(error.what()));}
        // Public compact payload is var. Wrong JSON root shapes are observed as
        // presentation inputs, never injected into canonical native history.
        const std::vector<QJsonValue> malformed{QJsonValue(QJsonValue::Null),false,17.5,
            QStringLiteral("RAW_ONLY_scalar"),QJsonArray{QStringLiteral("RAW_ONLY_array")}};
        for(const auto& value:malformed)try {
            checkRow(check,{"typed-root-payload","activity","mystery","Perform assistant action",unknown,"exclamation-circle",{}},
                [&](QObject* row,QObject* header){
                    check.require(row->setProperty("payload",value.toVariant()),
                                  "The original public var payload accepts the explicit typed input");
                    checkOutcome(check,row,header,"Perform assistant action",unknown,"exclamation-circle","notConverged");
                    const auto retained=QJsonDocument::fromJson(expression(row,"JSON.stringify([payload])").toUtf8()).array();
                    check.require(retained==QJsonArray{value},"A1 never rewrites malformed/Unicode literal payload input to manufacture a label");
                });
        }catch(const std::exception& error){check.require(false,"typed-root-payload: "+QString::fromUtf8(error.what()));}
    }
    void liveOwnerAndLanguage(Checks& check) const {
        try {
            checkRow(check,{"live-owner-language","activity","completed","Create a project","Completed","check-circle",
                {{"type","dynamicToolCall"},{"tool","create_project"}}},[&](QObject* row,QObject* header){
                const auto original=row->property("assistant");
                check.require(original.value<QObject*>(),"A1 native label starts with the original actual Session assistant");
                check.require(row->setProperty("assistant",QVariant::fromValue<QObject*>(nullptr)),
                              "A1 null owner is the original public component property, not a replacement controller");
                checkOutcome(check,row,header,"Work on the current project","Completed","check-circle","success");
                ContextTranslator translator;
                bool installed=QCoreApplication::installTranslator(&translator);
                const auto cleanup=qScopeGuard([&]{if(installed){QCoreApplication::removeTranslator(&translator);engine_->retranslate();}});
                check.require(installed,"A1 installs an independent ordinary Qt translator");
                engine_->retranslate();
                checkOutcome(check,row,header,QString::fromUtf8("Projet sans propriétaire β🧪"),"Completed","check-circle","success");
                check.require(row->setProperty("assistant",original),"A1 original owner can be rebound through its normal public property");
                checkOutcome(check,row,header,QString::fromUtf8("Créer Å\u00a0β 🧪"),"Completed","check-circle","success");
                check.require(row->setProperty("payload",QJsonObject{{"type","dynamicToolCall"},{"tool","unknown-native-action"}}.toVariantMap()),
                              "A1 unknown native action uses ordinary compact input");
                checkOutcome(check,row,header,QString::fromUtf8("Projet natif inconnu β🧪"),"Completed","check-circle","success");
                QCoreApplication::removeTranslator(&translator);installed=false;engine_->retranslate();
                checkOutcome(check,row,header,"Work on the current project","Completed","check-circle","success");
                check.require(row->setProperty("kind",QStringLiteral("error")) && row->setProperty("status",QStringLiteral("failed")),
                              "A1 current row kind/status invalidation uses original presentation properties");
                checkOutcome(check,row,header,"Assistant error","Failed","times-circle","failed");
                installed=QCoreApplication::installTranslator(&translator);engine_->retranslate();
                checkOutcome(check,row,header,QString::fromUtf8("Erreur Å\u00a0β 🧪"),QString::fromUtf8("Échec β"),"times-circle","failed");
                QCoreApplication::removeTranslator(&translator);installed=false;engine_->retranslate();
                checkOutcome(check,row,header,"Assistant error","Failed","times-circle","failed");
            });
        }catch(const std::exception& error){check.require(false,"live-owner-language: "+QString::fromUtf8(error.what()));}
    }
public:
    explicit CompactPresentationA1Proof(QQmlEngine* engine):QObject(engine),engine_(engine){}
    Q_INVOKABLE QVariantMap captionsAndWhitelist() const {
        Checks check;
        const QJsonObject technical{{"type","unknownType"},{"message","RAW_ONLY_message"},{"error",QJsonObject{{"message","RAW_ONLY_error"}}},
            {"purpose",QString::fromUtf8("\uFEFF\u00a0目的 β\n private-id ")},{"arguments",QJsonObject{{"shell","private-id"}}}};
        std::vector<Expected> rows{
            {"error-kind-wins-native-label","error","failed","Assistant error","Failed","times-circle",QJsonObject{{"type","dynamicToolCall"},{"tool","create_project"}}},
            {"plan-kind","plan","completed","Review work plan","Completed","check-circle",technical},
            {"question-kind","question","in_progress","Assistant question","In progress","hourglass-half",technical},
            {"tool-kind","tool","completed","Project action","Completed","check-circle",technical},
            {"trial-kind","trial","interrupted","Review refinement trial","Stopped","stop-circle",technical},
            {"decision-before-command","activity","refused","Review requested action","Refused","times-circle",QJsonObject{{"decision","deny"},{"item_id","actual-presentation-id"}}},
            {"unknown-payload","activity","completed","Perform assistant action","Completed","check-circle",technical},
            {"file-change","activity","completed","Update files","Completed","check-circle",QJsonObject{{"type","fileChange"}}},
            {"web-search","activity","completed","Search the web","Completed","check-circle",QJsonObject{{"type","webSearch"},{"action",QJsonObject{{"type","search"},{"query","RAW_ONLY_search"}}}}},
            {"mcp","activity","completed","Use external tool","Completed","check-circle",QJsonObject{{"type","mcpToolCall"}}},
            {"collaboration","activity","completed","Coordinate assistant task","Completed","check-circle",QJsonObject{{"type","collabAgentToolCall"}}},
            {"payload-plan","activity","completed","Update work plan","Completed","check-circle",QJsonObject{{"type","plan"}}},
            {"native-result","activity","completed","Report project action","Completed","check-circle",QJsonObject{{"type","ediOutcome"}}}
        };
        for(const auto& row:rows)try {checkRow(check,row);}catch(const std::exception& e){check.require(false,row.name+": "+QString::fromUtf8(e.what()));}
        return check.result();
    }
    Q_INVOKABLE QVariantMap statusAndCommandPrecedence() const {
        Checks check;
        malformedFieldsAndColdBoundary(check);
        const std::vector<Expected> rows{
            {"complete","activity","completed","Perform assistant action","Completed","check-circle",{}},
            {"failed","activity","failed","Perform assistant action","Failed","times-circle",{}},
            {"refused","activity","refused","Perform assistant action","Refused","times-circle",{}},
            {"declined","activity","declined","Perform assistant action","Declined","times-circle",{}},
            {"stopped","activity","interrupted","Perform assistant action","Stopped","stop-circle",{}},
            {"running","activity","in_progress","Perform assistant action","In progress","hourglass-half",{}},
            {"unknown","activity","mystery","Perform assistant action","The result could not be confirmed. Inspect the project before continuing.","exclamation-circle",{}},
            {"native-applied-unconfirmed-before-completed","activity","completed","Perform assistant action","Changes were made, but completion could not be confirmed.","exclamation-circle",QJsonObject{{"nativeOutcome",QJsonObject{{"status","applied_unconfirmed"},{"message","RAW_ONLY_message"}}}}},
            {"native-unconfirmed-before-failed","activity","failed","Perform assistant action","The result could not be confirmed. Inspect the project before continuing.","exclamation-circle",QJsonObject{{"nativeOutcome",QJsonObject{{"status","unconfirmed"},{"action_error","project_required"}}}}},
            {"old-inProgress-plus-completed-exit-is-not-confirmed","activity","completed","Read files","The result could not be confirmed. Inspect the project before continuing.","exclamation-circle",QJsonObject{{"type","commandExecution"},{"commandCategory","read"},{"status","inProgress"},{"exitCode",0}}},
            {"settled-command-read","activity","completed","Read files","Completed","check-circle",QJsonObject{{"type","commandExecution"},{"commandCategory","read"},{"status","completed"}}},
            {"running-command-caption-is-not-dead-commandCaption","activity","in_progress","Searched files","In progress","hourglass-half",QJsonObject{{"type","commandExecution"},{"commandCategory","search"},{"status","inProgress"}}},
            {"list-command-declined","activity","declined","Listed files","Declined","times-circle",QJsonObject{{"type","commandExecution"},{"commandCategory","listFiles"},{"status","declined"}}},
            {"unknown-command-failed","activity","failed","Ran command","Failed","times-circle",QJsonObject{{"type","commandExecution"},{"commandCategory","unrecognized"},{"status","failed"}}},
            {"mismatched-terminal-command","activity","interrupted","Ran command","The result could not be confirmed. Inspect the project before continuing.","exclamation-circle",QJsonObject{{"type","commandExecution"},{"status","completed"},{"exitCode",0}}}
        };
        for(const auto& row:rows)try {checkRow(check,row);}catch(const std::exception& e){check.require(false,row.name+": "+QString::fromUtf8(e.what()));}
        return check.result();
    }
    Q_INVOKABLE QVariantMap nativeLabelsAndTranslationContexts() const {
        Checks check;
        // Independent fixed human labels, never generated by nativeActionLabel under test.
        const std::vector<std::pair<QString,QString>> labels{
            {"create_project","Create a project"},{"show_report","Show the project report"},{"inspect_project","Inspect the current project"},
            {"inspect_data","Inspect diffraction data"},{"list_parameters","Inspect model parameters"},{"diagnostics","Check the current model"},
            {"set_parameters","Update parameter values"},{"set_free","Choose parameters to refine"},{"run_fit","Refine the current model"},
            {"undo_fit","Undo the latest refinement"},{"load_structure","Load a structure"},{"create_experiment","Add an experiment"},
            {"set_experiment_type","Choose the experiment type"},{"load_data","Load diffraction data"},{"read_selected_file","Read an attached file"},
            {"create_structure","Create a structure"},{"edit_structure","Edit the structure"},{"edit_atom","Edit an atomic site"},
            {"edit_experiment","Edit the experiment"},{"acquire_inputs","Inspect input files"},{"save_project","Save the project"},
            {"add_relations","Add parameter relationships"},{"edit_relation","Edit a parameter relationship"},{"edit_background","Edit the background"},
            {"estimate_background","Estimate the background"},{"create_cwl_project","Prepare a diffraction project"},{"not_a_registered_action","Work on the current project"}
        };
        for(const auto& [tool,label]:labels)try {
            checkRow(check,{"native-"+tool,"activity","completed",label,"Completed","check-circle",
                QJsonObject{{"type","dynamicToolCall"},{"tool",tool},{"purpose","RAW_ONLY_supplied-purpose"}}});
        }catch(const std::exception& e){check.require(false,tool+": "+QString::fromUtf8(e.what()));}
        liveOwnerAndLanguage(check);
        ContextTranslator translator;
        QCoreApplication::installTranslator(&translator);
        try {
            checkRow(check,{"original-AssistantMessage-context","error","failed",QString::fromUtf8("Erreur Å\u00a0β 🧪"),QString::fromUtf8("Échec β"),"times-circle",{}});
            checkRow(check,{"original-AssistantActions-context","activity","completed",QString::fromUtf8("Créer Å\u00a0β 🧪"),"Completed","check-circle",QJsonObject{{"type","dynamicToolCall"},{"tool","create_project"}}});
        }catch(const std::exception& e){check.require(false,"original-translation-context: "+QString::fromUtf8(e.what()));}
        QCoreApplication::removeTranslator(&translator);
        return check.result();
    }
};
static void registerCompactPresentationA1Proof() {
    qmlRegisterSingletonType<CompactPresentationA1Proof>("CompactPresentationA1Acceptance",1,0,"CompactPresentationA1Proof",
        [](QQmlEngine* engine,QJSEngine*)->QObject* {return new CompactPresentationA1Proof(engine);});
}
Q_COREAPP_STARTUP_FUNCTION(registerCompactPresentationA1Proof)
#include "test_e11_t5_compact_presentation_a1.moc"
