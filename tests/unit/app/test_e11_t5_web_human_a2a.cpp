// SPDX-License-Identifier: BSD-3-Clause
// A2a: FIRST component value/caller characterization, never canonical-row injection.
#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaProperty>
#include <QPointer>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQmlExpression>
#include <QScopeGuard>
#include <QSignalSpy>
#include <QStringList>
#include <QTranslator>
#include <QtQml/qqml.h>
#include <QtTest/qtestcase.h>
#include <QtCore/qtestsupport_core.h>
#include <memory>
#include <stdexcept>
#include <utility>
#include <vector>

namespace {
struct A2aChecks {
    int count = 0, failures = 0;
    void require(bool ok, const QString& message) {
        ++count;
        if (ok) return;
        ++failures;
        QTest::qFail(message.toUtf8().constData(), __FILE__, __LINE__);
    }
    QVariantMap result() const {
        return {{"ok", failures == 0}, {"checks", count},
                {"error", QStringLiteral("%1 individual A2a failures").arg(failures)}};
    }
};
struct A2aWebCase {
    QString name;
    QJsonObject payload;
    QString caption;
};
class A2aTranslator final : public QTranslator {
public:
    bool isEmpty() const override { return false; }
    QString translate(const char* context, const char* source, const char*, int) const override {
        if (QByteArray(context) != "AssistantMessage") return {};
        const QByteArray text(source);
        if (text == "Search the web") return QString::fromUtf8("Sources β");
        if (text == "Search the web for %1") return QString::fromUtf8("Chercher %1 β");
        if (text == "Open web page %1") return QString::fromUtf8("Ouvrir %1 β");
        if (text == "Find %1 on %2") return QString::fromUtf8("Trouver %1 dans %2 β");
        if (text == "Find %1 on a web page") return QString::fromUtf8("Trouver %1 sur une page β");
        if (text == "Find text on %1") return QString::fromUtf8("Texte dans %1 β");
        if (text == "Find or read public sources relevant to the current task.")
            return QString::fromUtf8("Sources publiques β");
        return {};
    }
};
}

class WebHumanA2aProof final : public QObject {
    Q_OBJECT
    QQmlEngine* engine_;
    static QVariant evaluate(QObject* owner, const QString& source) {
        QQmlExpression expression(QQmlEngine::contextForObject(owner), owner, source);
        const auto value = expression.evaluate();
        if (expression.hasError())
            throw std::runtime_error(expression.error().toString().toStdString());
        return value;
    }
    static QString literal(const QJsonValue& value) {
        const auto bytes = QJsonDocument(QJsonArray{value}).toJson(QJsonDocument::Compact);
        return QString::fromUtf8(bytes.mid(1).chopped(1));
    }
    static void exact(A2aChecks& check, QObject* owner, const QString& expression,
                      const QString& expected, const QString& name) {
        const auto result = evaluate(owner, expression);
        check.require(result.metaType() == QMetaType::fromType<QString>() &&
                          result.toString() == expected,
                      name + ": exact original typed text; expected=" + literal(expected) +
                          "; actual=" + literal(result.toString()));
    }
    std::unique_ptr<QObject> row() const {
        QQmlComponent component(engine_);
        component.setData("import QtQuick\nimport edi.app\n"
                          "AssistantMessage { assistant: Session.assistant }\n",
                          QUrl("qrc:/tests/A2aOriginalOwner.qml"));
        if (component.isError()) throw std::runtime_error(component.errorString().toStdString());
        std::unique_ptr<QObject> value(component.createWithInitialProperties({
            {"kind", QStringLiteral("activity")}, {"status", QStringLiteral("completed")},
            {"text", QString::fromUtf8("RAW_ONLY_shell_json_β🧪\n{private:true}")},
            {"rowId", QStringLiteral("A2a-absent-public-presentation-row")},
            {"payload", QVariantMap{{"type", "webSearch"}, {"query", "original fallback"}}},
            {"width", 640}}));
        if (!value) throw std::runtime_error(component.errorString().toStdString());
        return value;
    }
    static QObject* only(A2aChecks& check, QObject* owner, const QString& name) {
        const auto candidates = owner->findChildren<QObject*>(name);
        check.require(candidates.size() == 1, "A2a exactly one actual original " + name);
        return candidates.size() == 1 ? candidates.front() : nullptr;
    }
    static void cold(A2aChecks& check, QObject* owner, QObject* header, QObject* field) {
        check.require(!header->property("checked").toBool() &&
                          evaluate(owner, "humanDetailsSnapshot === null").toBool(),
                      "A2a collapsed value composition retains no human-detail snapshot");
        check.require(!field->property("visible").toBool() &&
                          field->property("text").toString().isEmpty(),
                      "A2a collapsed original full-body field remains empty and hidden");
        check.require(!owner->property("technicalCopied").toBool(),
                      "A2a composition does not claim a clipboard write or copy feedback");
    }
    static QJsonObject payload(QJsonObject fields) {
        fields.insert("type", "webSearch");
        fields.insert("arguments", QJsonObject{{"shell", "RAW_ONLY_never_human"}});
        return fields;
    }
public:
    explicit WebHumanA2aProof(QQmlEngine* engine) : QObject(engine), engine_(engine) {}
    Q_INVOKABLE QVariantMap normalizationLiteralSemantics() const {
        A2aChecks check;
        try {
            auto owner = row();
            auto* header = only(check, owner.get(), "assistant.activity.toggle");
            auto* field = only(check, owner.get(), "assistant.activity.details");
            if (!header || !field) return check.result();
            cold(check, owner.get(), header, field);
            struct Example { QString name, expression, expected; };
            const std::vector<Example> typed{
                {"missing", "undefined", ""}, {"null", "null", ""},
                {"false", "false", ""}, {"true", "true", ""},
                {"zero", "0", ""}, {"number", "12.5", ""},
                {"array", "['alpha','beta']", ""}, {"object", "({value:'alpha'})", ""},
                {"boxed-string", "new String(' alpha ')", ""},
                {"no-implicit-coercion", "({toString:function(){throw new Error('must not coerce');}})", ""}
            };
            // Stable ORIGINAL consumed producer carriers, not dead private
            // formatting procedures. The same seam exists before/after A2a.
            const std::vector<std::pair<QString, QString>> carriers{
                {"purpose:", "}"}, {"description:", "}"}, {"arguments:{purpose:", "}}"}};
            for (const auto& item : typed)
                for (const auto& carrier : carriers)
                    exact(check, owner.get(), "activityDescription(false,{" + carrier.first +
                              item.expression + carrier.second + ")",
                          item.expected, item.name + "/" + carrier.first);
            struct Text { QString name, source, expected; };
            const std::vector<Text> strings{
                {"empty", "", ""},
                {"ascii-runs", " \t alpha\r\n beta\v\f gamma  ", "alpha beta gamma"},
                {"all-ECMAScript-whitespace", QString::fromUtf8(
                    " \t\r\n\v\f\u00A0\u1680\u2000\u2001\u2002\u2003\u2004\u2005"
                    "\u2006\u2007\u2008\u2009\u200A\u2028\u2029\u202F\u205F\u3000\uFEFF"), ""},
                {"BOM-NBSP-lines", QString::fromUtf8("\uFEFF\u00A0α\u2028β\u2029🧪\u00A0"),
                    QString::fromUtf8("α β 🧪")},
                {"NEL-is-not-JS-space", QString::fromUtf8(" \u0085keep\u0085 "),
                    QString::fromUtf8("\u0085keep\u0085")},
                {"zero-width-is-not-JS-space", QString::fromUtf8(" \u200Bα\u180Eβ\u200E "),
                    QString::fromUtf8("\u200Bα\u180Eβ\u200E")},
                {"supplementary-combining-case", QString::fromUtf8("  A\u030A β🧪\nÉ  "),
                    QString::fromUtf8("A\u030A β🧪 É")},
                {"path-argument-no-redaction", "  folder / original sample.cif  ",
                    "folder / original sample.cif"},
                {"embedded-null", QString::fromLatin1(" A\0B ", 5), QString::fromLatin1("A\0B", 3)}
            };
            for (const auto& item : strings)
                for (const auto& carrier : carriers)
                    exact(check, owner.get(), "activityDescription(false,{" + carrier.first +
                              literal(item.source) + carrier.second + ")",
                          item.expected, item.name + "/" + carrier.first);
            cold(check, owner.get(), header, field);
        } catch (const std::exception& error) {
            check.require(false, "A2a normalization prerequisite/caller: " + QString::fromUtf8(error.what()));
        }
        return check.result();
    }
    Q_INVOKABLE QVariantMap webShapesAndConsumedCallers() const {
        A2aChecks check;
        const QString webFallback = "Find or read public sources relevant to the current task.";
        const QJsonValue null(QJsonValue::Null);
        const std::vector<A2aWebCase> cases{
            {"top-query-no-action", payload({{"query", "  alpha\n beta "}}), "Search the web for alpha beta"},
            {"null-action", payload({{"action", null}, {"query", "fallback"}}), "Search the web for fallback"},
            {"false-action-refuses-fallback", payload({{"action", false}, {"query", "must not leak"}}), ""},
            {"string-action-refuses-fallback", payload({{"action", "search"}, {"query", "must not leak"}}), ""},
            {"empty-string-action-refuses-fallback", payload({{"action", ""}, {"query", "must not leak"}}), ""},
            {"zero-action-refuses-fallback", payload({{"action", 0}, {"query", "must not leak"}}), ""},
            {"number-action-refuses-fallback", payload({{"action", 17}, {"query", "must not leak"}}), ""},
            {"array-action-refuses-fallback", payload({{"action", QJsonArray{}}, {"query", "must not leak"}}), ""},
            {"empty-object-is-not-search", payload({{"action", QJsonObject{}}, {"query", "must not leak"}}), ""},
            {"query-before-list", payload({{"action", QJsonObject{{"type", "search"}, {"query", "first"},
                {"queries", QJsonArray{"ignored"}}}}}), "Search the web for first"},
            {"list-normalizes-drops-blank", payload({{"action", QJsonObject{{"type", "search"}, {"query", 7},
                {"queries", QJsonArray{QString::fromUtf8("\uFEFF α\nβ "), "  ", QString::fromUtf8("γ 🧪")}}}}}),
                QString::fromUtf8("Search the web for α β · γ 🧪")},
            {"list-keeps-literal-duplicates", payload({{"action", QJsonObject{{"type", "search"},
                {"queries", QJsonArray{"alpha", "alpha"}}}}}), QString::fromUtf8("Search the web for alpha · alpha")},
            {"blank-list-falls-back", payload({{"action", QJsonObject{{"type", "search"},
                {"queries", QJsonArray{" ", "\n"}}}}, {"query", "outer"}}), "Search the web for outer"},
            {"null-list-falls-back", payload({{"action", QJsonObject{{"type", "search"}, {"queries", null}}},
                {"query", "outer"}}), "Search the web for outer"},
            {"string-list-is-not-list", payload({{"action", QJsonObject{{"type", "search"}, {"queries", "alpha"}}},
                {"query", "must not leak"}}), ""},
            {"boolean-list-is-not-list", payload({{"action", QJsonObject{{"type", "search"}, {"queries", false}}},
                {"query", "must not leak"}}), ""},
            {"object-list-is-not-list", payload({{"action", QJsonObject{{"type", "search"},
                {"queries", QJsonObject{{"0", "alpha"}, {"length", 1}}}}}, {"query", "must not leak"}}), ""},
            {"mixed-list-does-not-coerce", payload({{"action", QJsonObject{{"type", "search"},
                {"queries", QJsonArray{"alpha", 3}}}}, {"query", "must not leak"}}), ""},
            {"null-member-does-not-coerce", payload({{"action", QJsonObject{{"type", "search"},
                {"queries", QJsonArray{"alpha", null}}}}}), ""},
            {"unknown-action", payload({{"action", QJsonObject{{"type", "unrecognized"}, {"query", "alpha"}}}}), ""},
            {"typed-action-type", payload({{"action", QJsonObject{{"type", 7}}}, {"query", "must not leak"}}), ""},
            {"open-normalizes", payload({{"action", QJsonObject{{"type", "openPage"},
                {"url", "  https://example.invalid/\n original "}}}}), "Open web page https://example.invalid/ original"},
            {"open-missing-url", payload({{"action", QJsonObject{{"type", "openPage"}}}, {"query", "must not leak"}}), ""},
            {"find-both", payload({{"action", QJsonObject{{"type", "findInPage"},
                {"url", " https://example.invalid/reference "}, {"pattern", QString::fromUtf8(" α\nβ ")}}}}),
                QString::fromUtf8("Find α β on https://example.invalid/reference")},
            {"find-pattern-only", payload({{"action", QJsonObject{{"type", "findInPage"},
                {"pattern", " original pattern "}}}}), "Find original pattern on a web page"},
            {"find-url-only", payload({{"action", QJsonObject{{"type", "findInPage"},
                {"url", "https://example.invalid/reference"}, {"pattern", false}}}}),
                "Find text on https://example.invalid/reference"},
            {"find-empty", payload({{"action", QJsonObject{{"type", "findInPage"}, {"url", null}, {"pattern", " "}}}}), ""}
        };
        for (const auto& item : cases) try {
            auto owner = row();
            auto* header = only(check, owner.get(), "assistant.activity.toggle");
            auto* field = only(check, owner.get(), "assistant.activity.details");
            if (!header || !field) continue;
            const bool assigned = owner->setProperty("payload", item.payload.toVariantMap());
            check.require(assigned, item.name + ": original public payload accepts exact typed input");
            if (!assigned) continue;
            const auto before = evaluate(owner.get(), "JSON.stringify(payload)").toString();
            cold(check, owner.get(), header, field);
            check.require(header->property("text").toString() == "Search the web",
                          item.name + ": the actual compact header stays human-short, never a query or technical body");
            exact(check, owner.get(), "activityDescription(false)", item.caption, item.name + "/Qt-variant-owner");
            exact(check, owner.get(), "activityDescription(false," + literal(item.payload) + ")",
                  item.caption, item.name + "/ordinary-JS-source");
            exact(check, owner.get(), "activityDescription(true," + literal(item.payload) + ")",
                  item.caption, item.name + "/explicit-full-description");
            exact(check, owner.get(), "activityDescription(true)", item.caption, item.name + "/full-description");
            const QString body = item.caption.isEmpty() ? webFallback : item.caption;
            const QString detail = "({payload:payload,text:text,provenance:''})";
            exact(check, owner.get(), "fullHumanDescription(" + detail + ")", body,
                  item.name + "/expanded-composition-caller");
            exact(check, owner.get(), "humanActivityText(" + detail + ")", "Search the web\n" + body,
                  item.name + "/default-copy-composition-caller");
            check.require(evaluate(owner.get(), "JSON.stringify(payload)").toString() == before &&
                              QJsonDocument::fromJson(before.toUtf8()).object() == item.payload,
                          item.name + ": every original typed payload/list/string stays unchanged");
            check.require(owner->property("text").toString() == QString::fromUtf8(
                              "RAW_ONLY_shell_json_β🧪\n{private:true}"),
                          item.name + ": presentation never rewrites retained literal row text");
            check.require(!body.contains("RAW_ONLY_") && !body.contains("must not leak"),
                          item.name + ": generic/technical or refused fallback carriers never enter human composition");
            cold(check, owner.get(), header, field);
        } catch (const std::exception& error) {
            check.require(false, item.name + ": " + QString::fromUtf8(error.what()));
        }
        try {
            auto owner = row();
            exact(check, owner.get(), "activityDescription(false,null)", "Search the web for original fallback", "null-source-falls-back");
            exact(check, owner.get(), "activityDescription(false,false)", "Search the web for original fallback", "false-source-falls-back");
            exact(check, owner.get(), "activityDescription(false,{type:'webSearch',query:17})", "", "typed-top-query");
            const QVariantMap wrapped{{"type", "webSearch"}, {"action", QVariantMap{{"type", "search"},
                {"queries", QStringList{QString::fromUtf8(" α\nβ "), QString::fromUtf8("γ 🧪")}}}}};
            const bool assigned = owner->setProperty("payload", wrapped);
            check.require(assigned, "Actual original public Qt QStringList projection is accepted; suffix UNREACHED otherwise");
            if (assigned)
                exact(check, owner.get(), "activityDescription(false)", QString::fromUtf8("Search the web for α β · γ 🧪"),
                      "actual-QStringList-JSON-projection");
            const QString full = QString::fromUtf8("  Compare the original α\nβ source rows  ");
            const auto supplied = payload({{"purpose", full}, {"action", QJsonObject{{"type", "search"}, {"query", "ignored purpose fallback"}}}});
            const bool purposeAssigned = owner->setProperty("payload", supplied.toVariantMap());
            check.require(purposeAssigned, "Original supplied human-purpose carrier remains a public row input");
            if (purposeAssigned) {
                exact(check, owner.get(), "activityDescription(false)", QString::fromUtf8("Compare the original α β source rows"), "short-purpose-normalized");
                exact(check, owner.get(), "activityDescription(true)", full, "full-purpose-literal");
                exact(check, owner.get(), "fullHumanDescription({payload:payload})", full, "expanded-purpose-literal");
                exact(check, owner.get(), "humanActivityText({payload:payload})", "Search the web\n" + full, "default-copy-purpose-literal");
            }
        } catch (const std::exception& error) {
            check.require(false, "A2a wrappers/retained-purpose: " + QString::fromUtf8(error.what()));
        }
        return check.result();
    }
    Q_INVOKABLE QVariantMap serializationDependenciesAndColdBoundary() const {
        A2aChecks check;
        try {
            auto owner = row();
            auto* header = only(check, owner.get(), "assistant.activity.toggle");
            auto* field = only(check, owner.get(), "assistant.activity.details");
            if (!header || !field) return check.result();
            cold(check, owner.get(), header, field);
            for (const auto& call : {QStringLiteral("activityDescription(false,p)"),
                                    QStringLiteral("activityDescription(true,p)"),
                                    QStringLiteral("fullHumanDescription({payload:p})"),
                                    QStringLiteral("humanActivityText({payload:p})")}) {
                const auto probe = [&](const QString& setup) {
                    return "(() => {" + setup + ";const p={type:'webSearch',action:{type:'search',queries:q}};"
                        "try {" + call + ";return JSON.stringify({threw:false});}"
                        "catch(e){return JSON.stringify({threw:true,name:e.name,message:e.message});}})()";
                };
                const auto cyclic = QJsonDocument::fromJson(evaluate(owner.get(), probe("const q=[];q.push(q)")).toString().toUtf8()).object();
                check.require(cyclic.value("threw").toBool() && cyclic.value("name").toString() == "TypeError",
                              call + ": original cyclic JSON serialization failure propagates through the actual caller");
                const auto thrown = QJsonDocument::fromJson(evaluate(owner.get(), probe(
                    "const q={toJSON:function(){throw new Error('A2a original serializer sentinel');}}"))
                    .toString().toUtf8()).object();
                check.require(thrown.value("threw").toBool() && thrown.value("name").toString() == "Error" &&
                                  thrown.value("message").toString() == "A2a original serializer sentinel",
                              call + ": original serializer callback exception is not swallowed or replaced by empty text");
                // ECMAScript throw carries ANY value, not only an Error.
                // Each expectation is literal; no candidate helper is an oracle.
                struct Thrown { QString name, setup, type; };
                const std::vector<Thrown> values{
                    {"Error-object", "const thrown=new Error('original Error identity')", "object"},
                    {"valid-JSON-array-string", "const thrown='[\"not successful serialization\"]'", "string"},
                    {"ordinary-object", "const thrown={token:'original thrown object'}", "object"},
                    {"null", "const thrown=null", "object"},
                    {"undefined", "const thrown=undefined", "undefined"},
                    {"false", "const thrown=false", "boolean"},
                    {"true", "const thrown=true", "boolean"},
                    {"number", "const thrown=17", "number"}
                };
                for (const auto& value : values) {
                    const QString source = "(() => {" + value.setup +
                        ";let calls=0,receiver=false,key='not-called';"
                        "const q={toJSON:function(k){++calls;receiver=this===q;key=k;throw thrown;}};"
                        "const p={type:'webSearch',action:{type:'search',queries:q}};"
                        "try {" + call + ";return JSON.stringify({threw:false});}"
                        "catch(e){return JSON.stringify({threw:true,same:e===thrown,type:typeof e,"
                        "calls:calls,receiver:receiver,key:key});}})()";
                    const auto observed = QJsonDocument::fromJson(
                        evaluate(owner.get(), source).toString().toUtf8()).object();
                    check.require(observed.value("threw").toBool() &&
                                      observed.value("same").toBool() &&
                                      observed.value("type").toString() == value.type &&
                                      observed.value("calls").toInt() == 1 &&
                                      observed.value("receiver").toBool() &&
                                      observed.value("key").isString() &&
                                      observed.value("key").toString().isEmpty(),
                                  call + "/" + value.name +
                                      ": original toJSON receiver and exact thrown value propagate, never friendly output");
                }
                // An ordinary undefined RETURN differs from throwing undefined:
                // original JSON.parse rejects the missing serialized text.
                const auto undefinedReturn = QJsonDocument::fromJson(evaluate(owner.get(),
                    "(() => {const p={type:'webSearch',action:{type:'search',queries:{toJSON:function(){return undefined;}}}};"
                    "try {" + call + ";return JSON.stringify({threw:false});}"
                    "catch(e){return JSON.stringify({threw:true,isSyntaxError:e instanceof SyntaxError});}})()")
                    .toString().toUtf8()).object();
                check.require(undefinedReturn.value("threw").toBool() &&
                                  undefinedReturn.value("isSyntaxError").toBool(),
                              call + ": original undefined serialization return retains its actual parse exception");
                const QString emptyResult = call == "fullHumanDescription({payload:p})"
                    ? QStringLiteral("Find or read public sources relevant to the current task.")
                    : call == "humanActivityText({payload:p})"
                        ? QStringLiteral("Search the web\nFind or read public sources relevant to the current task.")
                        : QString();
                for (const auto& returned : {QStringLiteral("null"), QStringLiteral("false"),
                                            QStringLiteral("'not an array'"), QStringLiteral("({item:'not an array'})"),
                                            QStringLiteral("new Error('returned, not thrown')")})
                    exact(check, owner.get(),
                          "(() => {const p={type:'webSearch',query:'must not leak',action:{type:'search',"
                          "queries:{toJSON:function(){return " + returned + ";}}}};return " + call + ";})()",
                          emptyResult, call + "/normal-invalid-list-return");
                const QString priorityResult = call == "humanActivityText({payload:p})"
                    ? QStringLiteral("Search the web\nSearch the web for priority")
                    : QStringLiteral("Search the web for priority");
                const auto priorityObserved = QJsonDocument::fromJson(evaluate(owner.get(),
                      "(() => {let reads=0;const a={type:'search',query:'priority'};"
                      "const p={type:'webSearch',action:a};"
                      "Object.defineProperty(a,'queries',{get:function(){++reads;throw null;}});"
                      "Object.defineProperty(p,'query',{get:function(){++reads;throw undefined;}});"
                      "const value=" + call + ";return JSON.stringify({value:value,reads:reads});})()")
                      .toString().toUtf8()).object();
                check.require(priorityObserved.value("value").isString() &&
                                  priorityObserved.value("value").toString() == priorityResult &&
                                  priorityObserved.value("reads").isDouble() &&
                                  priorityObserved.value("reads").toInt() == 0,
                              call + ": primary query never reads unused list or fallback getters");
                const QString fallbackResult = call == "humanActivityText({payload:p})"
                    ? QStringLiteral("Search the web\nSearch the web for outer")
                    : QStringLiteral("Search the web for outer");
                exact(check, owner.get(),
                      "(() => {const a={type:'search'};const p={type:'webSearch',action:a,query:'outer'};"
                      "Object.defineProperty(a,'queries',{get:function(){return undefined;}});return " + call + ";})()",
                      fallbackResult, call + ": ordinary getter undefined is absence, distinct from throwing undefined");
                struct Getter { QString name, setup; int count; };
                const QString getterThrown = "const thrown='[\"not a getter result\"]';let reads=0,receiver=true;";
                const std::vector<Getter> getters{
                    {"payload.action", "const p={type:'webSearch'};"
                        "Object.defineProperty(p,'action',{get:function(){++reads;receiver=receiver&&this===p;throw thrown;}});", 1},
                    {"action.type", "const a={};const p={type:'webSearch',action:a};"
                        "Object.defineProperty(a,'type',{get:function(){++reads;receiver=receiver&&this===a;throw thrown;}});", 1},
                    {"action.type-open-second", "const a={};const p={type:'webSearch',action:a};"
                        "Object.defineProperty(a,'type',{get:function(){++reads;receiver=receiver&&this===a;if(reads===2)throw thrown;return 'openPage';}});", 2},
                    {"action.type-find-third", "const a={};const p={type:'webSearch',action:a};"
                        "Object.defineProperty(a,'type',{get:function(){++reads;receiver=receiver&&this===a;if(reads===3)throw thrown;return 'findInPage';}});", 3},
                    {"action.query", "const a={type:'search'};const p={type:'webSearch',action:a};"
                        "Object.defineProperty(a,'query',{get:function(){++reads;receiver=receiver&&this===a;throw thrown;}});", 1},
                    {"action.queries-first", "const a={type:'search'};const p={type:'webSearch',action:a};"
                        "Object.defineProperty(a,'queries',{get:function(){++reads;receiver=receiver&&this===a;throw thrown;}});", 1},
                    {"action.queries-second", "const a={type:'search'};const p={type:'webSearch',action:a};"
                        "Object.defineProperty(a,'queries',{get:function(){++reads;receiver=receiver&&this===a;if(reads===2)throw thrown;return ['alpha'];}});", 2},
                    {"action.queries-serialization-read", "const a={type:'search'};const p={type:'webSearch',action:a};"
                        "Object.defineProperty(a,'queries',{get:function(){++reads;receiver=receiver&&this===a;if(reads===3)throw thrown;return ['alpha'];}});", 3},
                    {"payload.query", "const a={type:'search'};const p={type:'webSearch',action:a};"
                        "Object.defineProperty(p,'query',{get:function(){++reads;receiver=receiver&&this===p;throw thrown;}});", 1},
                    {"action.url", "const a={type:'openPage'};const p={type:'webSearch',action:a};"
                        "Object.defineProperty(a,'url',{get:function(){++reads;receiver=receiver&&this===a;throw thrown;}});", 1},
                    {"action.pattern", "const a={type:'findInPage',url:'page'};const p={type:'webSearch',action:a};"
                        "Object.defineProperty(a,'pattern',{get:function(){++reads;receiver=receiver&&this===a;throw thrown;}});", 1},
                    {"queries.toJSON-getter", "const q={};const p={type:'webSearch',action:{type:'search',queries:q}};"
                        "Object.defineProperty(q,'toJSON',{get:function(){++reads;receiver=receiver&&this===q;throw thrown;}});", 1}
                };
                for (const auto& getter : getters) {
                    const auto observed = QJsonDocument::fromJson(evaluate(owner.get(),
                        "(() => {" + getterThrown + getter.setup + "try {" + call +
                        ";return JSON.stringify({threw:false});}catch(e){return JSON.stringify("
                        "{threw:true,same:e===thrown,reads:reads,receiver:receiver});}})()")
                        .toString().toUtf8()).object();
                    check.require(observed.value("threw").toBool() && observed.value("same").toBool() &&
                                      observed.value("reads").toInt() == getter.count &&
                                      observed.value("receiver").toBool(),
                                  call + "/" + getter.name +
                                      ": original property access preserves receiver, sequencing and exact thrown value");
                }
            }
            exact(check, owner.get(),
                  "(() => {let reads=0;const q={toJSON:function(){++reads;return [' alpha ','beta'];}};"
                  "const caption=activityDescription(false,{type:'webSearch',action:{type:'search',queries:q}});"
                  "return JSON.stringify({caption:caption,reads:reads});})()",
                  QStringLiteral("{\"caption\":\"Search the web for alpha · beta\",\"reads\":1}"),
                  "ordinary-toJSON-projection-once");
            exact(check, owner.get(),
                  "activityDescription(false,{type:'webSearch',action:{type:'search',query:'priority',queries:{toJSON:function(){throw new Error('unused');}}}})",
                  "Search the web for priority", "unused-serializer-is-not-read");
            QQmlExpression dependency(QQmlEngine::contextForObject(owner.get()), owner.get(), "activityDescription(false)");
            dependency.setNotifyOnValueChanged(true);
            QSignalSpy changes(&dependency, &QQmlExpression::valueChanged);
            const auto initial = dependency.evaluate();
            const bool dependent = initial.metaType() == QMetaType::fromType<QString>() &&
                initial.toString() == "Search the web for original fallback" &&
                !dependency.hasError() && changes.isValid();
            check.require(dependent,
                          "A2a dependency begins at the actual original component payload; suffix UNREACHED otherwise");
            if (!dependent) return check.result();
            const bool changed = owner->setProperty("payload", payload({{"action", QJsonObject{{"type", "openPage"},
                {"url", "https://example.invalid/current"}}}}).toVariantMap());
            check.require(changed, "A2a current payload changes through its original public property");
            if (!changed) return check.result();
            const bool notified = QTest::qWaitFor([&] { return !changes.isEmpty(); });
            check.require(notified,
                          "A2a normal expression observes original payload dependency without new timers or owner state; suffix UNREACHED otherwise");
            if (!notified) return check.result();
            check.require(!dependency.hasError() && dependency.evaluate().toString() ==
                              "Open web page https://example.invalid/current",
                          "A2a same current row reflects the changed actual web action");
            const auto originalOwner = owner->property("assistant");
            QPointer<QObject> original(originalOwner.value<QObject*>());
            const auto index = owner->metaObject()->indexOfProperty("assistant");
            const bool typed = original && index >= 0 && originalOwner.metaType().flags().testFlag(QMetaType::PointerToQObject) &&
                owner->metaObject()->property(index).metaType() == originalOwner.metaType();
            check.require(typed, "A2a typed original Session assistant is required for null-owner suffix; otherwise UNREACHED");
            if (!typed) return check.result();
            const auto ownerIs = [&](QObject* expected) {
                const auto actual = owner->property("assistant");
                return actual.isValid() && actual.metaType() == originalOwner.metaType() && actual.value<QObject*>() == expected;
            };
            bool restored = false;
            const auto cleanupOwner = qScopeGuard([&] {
                if (!restored) check.require(original && owner->setProperty("assistant", originalOwner) && ownerIs(original.data()),
                    "A2a restores the actual original typed owner after an incomplete prerequisite");
            });
            const QVariant typedNull(originalOwner.metaType());
            const bool nullSet = typedNull.isValid() && typedNull.isNull() &&
                owner->setProperty("assistant", typedNull) && ownerIs(nullptr);
            check.require(nullSet, "A2a actual typed-null owner is read back before language suffix; otherwise UNREACHED");
            if (!nullSet) return check.result();
            exact(check, owner.get(), "activityDescription(false)", "Open web page https://example.invalid/current", "null-owner-pure-caption");
            A2aTranslator translator;
            const bool installed = QCoreApplication::installTranslator(&translator);
            const auto cleanupTranslator = qScopeGuard([&] {
                if (installed) { QCoreApplication::removeTranslator(&translator); engine_->retranslate(); }
            });
            check.require(installed, "A2a ordinary Qt translator installation precedes translated expectations");
            if (!installed) return check.result();
            engine_->retranslate();
            check.require(header->property("text").toString() == QString::fromUtf8("Sources β"),
                          "A2a original compact binding retranslates in its existing AssistantMessage context");
            exact(check, owner.get(), "activityDescription(false)", QString::fromUtf8("Ouvrir https://example.invalid/current β"),
                  "original-AssistantMessage-open-translation-context");
            exact(check, owner.get(), "activityDescription(false,{type:'webSearch',action:{type:'search',query:'α'}})",
                  QString::fromUtf8("Chercher α β"), "original-search-translation-context");
            exact(check, owner.get(), "activityDescription(false,{type:'webSearch',action:{type:'findInPage',pattern:'α',url:'page'}})",
                  QString::fromUtf8("Trouver α dans page β"), "original-find-both-translation-context");
            exact(check, owner.get(), "activityDescription(false,{type:'webSearch',action:{type:'findInPage',pattern:'α'}})",
                  QString::fromUtf8("Trouver α sur une page β"), "original-find-pattern-translation-context");
            exact(check, owner.get(), "activityDescription(false,{type:'webSearch',action:{type:'findInPage',url:'page'}})",
                  QString::fromUtf8("Texte dans page β"), "original-find-url-translation-context");
            exact(check, owner.get(), "humanActivityText({payload:payload})",
                  QString::fromUtf8("Sources β\nOuvrir https://example.invalid/current β"),
                  "same-original-default-copy-caller-live-language");
            restored = original && owner->setProperty("assistant", originalOwner) && ownerIs(original.data());
            check.require(restored, "A2a original typed Session owner is restored with exact identity readback");
            if (!restored) return check.result();
            cold(check, owner.get(), header, field);
            check.require(evaluate(owner.get(), "JSON.stringify(assistant.activityHumanDetails(rowId,kind,status))").toString() == "{}" &&
                              evaluate(owner.get(), "readHumanDetails() === null").toBool(),
                          "A2a real original VM has no invented admitted row; collapsed canonical/copy membership is not fabricated");
        } catch (const std::exception& error) {
            check.require(false, "A2a serialization/dependency/ownership prerequisite: " + QString::fromUtf8(error.what()));
        }
        return check.result();
    }
};
static void registerWebHumanA2aProof() {
    qmlRegisterSingletonType<WebHumanA2aProof>("WebHumanA2aAcceptance", 1, 0, "WebHumanA2aProof",
        [](QQmlEngine* engine, QJSEngine*) -> QObject* { return new WebHumanA2aProof(engine); });
}
Q_COREAPP_STARTUP_FUNCTION(registerWebHumanA2aProof)
#include "test_e11_t5_web_human_a2a.moc"
