// SPDX-License-Identifier: BSD-3-Clause
// First finite usage layer: real Panel pure relations; canonical/UI/timer gates remain separate.
#include <QtCore/qtestsupport_core.h>
#include <QtQml/qqml.h>
#include <QtQml/qqmllist.h>
#include <QtTest/qtestcase.h>
#include <private/qjsvalue_p.h>
#include <private/qqmlcontextdata_p.h>
#include <private/qqmllistwrapper_p.h>
#include <private/qv4engine_p.h>
#include <private/qv4persistent_p.h>

#include "e11_t5_test_inputs.hpp"

#include <QColor>
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDebug>
#include <QFile>
#include <QJSValue>
#include <QJSValueIterator>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMetaProperty>
#include <QPointer>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQmlEngine>
#include <QQmlError>
#include <QQmlExpression>
#include <QQuickItem>
#include <QQuickWindow>
#include <QScopeGuard>
#include <QSignalSpy>
#include <QSizeF>
#include <QStringList>
#include <QTranslator>
#include <QUrl>
#include <QVariantMap>
#include <functional>
#include <limits>
#include <memory>
#include <stdexcept>
#include <utility>

#include "e11_t5_usage_account_phase.hpp"
#include "engine_setup.hpp"

namespace {
struct UsageChecks {
    int checks = 0;
    int failures = 0;
    void require(bool condition, const QString& name) {
        ++checks;
        if (condition) return;
        ++failures;
        QTest::qFail(name.toUtf8().constData(), __FILE__, __LINE__);
    }
    QVariantMap result() const {
        return {{"ok", failures == 0},
                {"checks", checks},
                {"error", QStringLiteral("%1 usage relation failures").arg(failures)}};
    }
};
// Members are destroyed in reverse: Popup/queued context, then toggle, then host.
struct UsagePopupDelete {
    QPointer<QObject> guarded;
    void operator()(QObject*) const { delete guarded.data(); }
};
struct UsagePanelLease {
    std::unique_ptr<QQuickItem> host;
    std::unique_ptr<QQuickItem> toggle;
    std::unique_ptr<QObject, UsagePopupDelete> component;
    QObject* get() const {
        auto* value = component.get_deleter().guarded.data();
        if (!value) throw std::runtime_error("the actual unit Panel was destroyed");
        return value;
    }
    QObject* operator->() const { return get(); }
};
class UsageTranslator final : public QTranslator {
   public:
    bool isEmpty() const override { return false; }
    QString translate(const char* context, const char* source, const char*, int) const override {
        if (QByteArray(context) != "AssistantPanel") return {};
        const QByteArray text(source);
        if (text == "Reset unavailable") return QString::fromUtf8("Indisponible β");
        if (text == "Reset time reached") return QString::fromUtf8("Échéance β");
        if (text == "Resets in %1d %2h") return QString::fromUtf8("Retour β heures=%2 jours=%1");
        if (text == "Resets in %1h %2 min") return QString::fromUtf8("Retour β %1h %2m");
        if (text == "Resets in %1 min") return QString::fromUtf8("Retour β %1m");
        return {};
    }
};
void prerequisite(bool condition, const char* name) {
    if (!condition) throw std::runtime_error(name);
}
QVariantMap usageValueKind(const QJSValue& value) {
    QVariantMap facts{{"object", value.isObject()}, {"callable", value.isCallable()},
                      {"error", value.isError()},   {"undefined", value.isUndefined()},
                      {"null", value.isNull()},     {"number", value.isNumber()},
                      {"string", value.isString()}, {"bool", value.isBool()}};
    if (value.isError()) {
        facts.insert("error_name", value.property("name").toString());
        facts.insert("error_message", value.property("message").toString());
        facts.insert("error_stack", value.property("stack").toString());
    }
    return facts;
}
void retainUsageContextAdmission(QVariantList& trace, QVariantMap facts) {
    facts.insert("trace_index", trace.size());
    trace.append(facts);
    // Retain obtainable facts BEFORE Panel creation/teardown or any failing assertion.
    qInfo().noquote() << "E11_USAGE_CONTEXT_ADMISSION"
                      << QJsonDocument::fromVariant(facts).toJson(QJsonDocument::Compact);
}
void requireUsageContextBundle(QQmlEngine* engine, const QJSValue& value, const char* tag,
                               bool objectMode, QVariantList& trace) {
    QVariantMap facts{{"stage", "bundle-admission"},
                      {"tag", QString::fromLatin1(tag)},
                      {"object_context", objectMode},
                      {"value", usageValueKind(value)},
                      {"pending_engine_error", engine->hasError()}};
    const QStringList names{QStringLiteral("Array"),    QStringLiteral("Date"),
                            QStringLiteral("JSON"),     QStringLiteral("Math"),
                            QStringLiteral("isFinite"), QStringLiteral("state")};
    bool valid =
        value.isObject() && !value.isCallable() && !value.isError() && !engine->hasError();
    QStringList actualNames;
    QVariantMap members;
    if (valid) {
        QJSValueIterator iterator(value);
        while (iterator.hasNext()) {
            iterator.next();
            if (value.hasOwnProperty(iterator.name())) actualNames.append(iterator.name());
        }
        actualNames.sort();
        valid = actualNames == names;
        for (const auto& name : names) {
            const auto member = value.property(name);
            auto kind = usageValueKind(member);
            kind.insert("own", value.hasOwnProperty(name));
            members.insert(name, kind);
            const bool function = name == "Array" || name == "Date" || name == "isFinite";
            valid = valid && value.hasOwnProperty(name) && !member.isError() &&
                    (function ? member.isCallable() : member.isObject() && !member.isCallable());
        }
        for (const auto& pair : {qMakePair(QStringLiteral("JSON"), QStringLiteral("parse")),
                                 qMakePair(QStringLiteral("JSON"), QStringLiteral("stringify")),
                                 qMakePair(QStringLiteral("Math"), QStringLiteral("ceil")),
                                 qMakePair(QStringLiteral("Date"), QStringLiteral("now")),
                                 qMakePair(QStringLiteral("Array"), QStringLiteral("from"))}) {
            const auto receiver = value.property(pair.first);
            const bool objectReceiver = receiver.isObject() || receiver.isCallable();
            const auto method = objectReceiver ? receiver.property(pair.second) : QJSValue();
            auto kind = usageValueKind(method);
            kind.insert("own", objectReceiver && receiver.hasOwnProperty(pair.second));
            members.insert(pair.first + "." + pair.second, kind);
            valid = valid && objectReceiver && receiver.hasOwnProperty(pair.second) &&
                    method.isCallable() && !method.isError();
        }
    }
    facts.insert("own_names", actualNames);
    facts.insert("members", members);
    facts.insert("admitted", valid);
    retainUsageContextAdmission(trace, facts);
    if (!valid)
        throw std::runtime_error(
            (QStringLiteral("context factory bundle refused before assignment: ") +
             QString::fromLatin1(tag))
                .toStdString());
}
void requireUsageContextReadback(QQmlContext* context, const QString& name,
                                 const QJSValue& expected, bool objectMode, QVariantList& trace) {
    const auto actual = context->contextProperty(name);
    const bool typed = actual.metaType() == QMetaType::fromType<QJSValue>();
    const auto script = typed ? actual.value<QJSValue>() : QJSValue();
    const bool same = typed && script.strictlyEquals(expected);
    retainUsageContextAdmission(
        trace, {{"stage", "context-property-readback"},
                {"name", name},
                {"object_context", objectMode},
                {"variant_type",
                 QString::fromLatin1(actual.typeName() ? actual.typeName() : "<invalid>")},
                {"variant_valid", actual.isValid()},
                {"variant_null", actual.isNull()},
                {"exact_qjsvalue_type", typed},
                {"strict_same_value", same},
                {"actual", usageValueKind(script)},
                {"expected", usageValueKind(expected)}});
    if (!same)
        throw std::runtime_error(
            (QStringLiteral("actual QQmlContext readback differs before use: ") + name)
                .toStdString());
}
}  // namespace

// Test-owned notify properties, never a production context API or backend substitute.
class UsageLookupContext final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QJSValue JSON READ jsonValue NOTIFY jsonChanged)
    Q_PROPERTY(QJSValue Array READ arrayValue NOTIFY arrayChanged)
    Q_PROPERTY(QJSValue Date READ dateValue NOTIFY dateChanged)
    Q_PROPERTY(QJSValue Math READ mathValue NOTIFY mathChanged)
    Q_PROPERTY(QJSValue isFinite READ finiteValue NOTIFY finiteChanged)
    QJSValue json_, array_, date_, math_, finite_;

   public:
    QJSValue jsonValue() const { return json_; }
    QJSValue arrayValue() const { return array_; }
    QJSValue dateValue() const { return date_; }
    QJSValue mathValue() const { return math_; }
    QJSValue finiteValue() const { return finite_; }
    void set(const QString& name, const QJSValue& value) {
        if (name == "JSON") {
            json_ = value;
            emit jsonChanged();
        } else if (name == "Array") {
            array_ = value;
            emit arrayChanged();
        } else if (name == "Date") {
            date_ = value;
            emit dateChanged();
        } else if (name == "Math") {
            math_ = value;
            emit mathChanged();
        } else if (name == "isFinite") {
            finite_ = value;
            emit finiteChanged();
        } else
            throw std::runtime_error("unknown test context member");
    }
   signals:
    void jsonChanged();
    void arrayChanged();
    void dateChanged();
    void mathChanged();
    void finiteChanged();
};

// Writable test-owned context name; direct calls read the current value.
// Replacement deliberately emits no notify: dependency/rebinding is gated separately.
class UsageCallLookupContext final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QJSValue Math READ math WRITE setMath NOTIFY mathChanged)
    Q_PROPERTY(QJSValue JSON READ json WRITE setJson NOTIFY jsonChanged)
    Q_PROPERTY(QJSValue Date READ date WRITE setDate NOTIFY dateChanged)
    Q_PROPERTY(QJSValue isFinite READ finite WRITE setFinite NOTIFY finiteChanged)
    QJSEngine* engine_;
    QJSValue math_, json_, date_, finite_, defaultJson_;
    QPointer<QObject> separateJsonConsumer_;
    mutable int separateJsonReads_ = 0;

   public:
    explicit UsageCallLookupContext(QJSEngine* engine)
        : engine_(engine),
          math_(engine->globalObject().property("Math")),
          json_(engine->globalObject().property("JSON")),
          date_(engine->globalObject().property("Date")),
          finite_(engine->globalObject().property("isFinite")),
          defaultJson_(json_) {}
    QJSValue json() const {
        // One usage projection is the counted subject. The original connection
        // dialog independently parses its disclosure in the same creation context.
        // Keep that real binding active with its ordinary JSON receiver; never
        // filter, deduplicate or forgive any operation on the Panel's receiver.
        if (separateJsonConsumer_ &&
            engine_->handle()->qmlScopeObject() == separateJsonConsumer_.data()) {
            ++separateJsonReads_;
            return defaultJson_;
        }
        return json_;
    }
    void separateJsonConsumer(QObject* consumer) { separateJsonConsumer_ = consumer; }
    int separateJsonReads() const { return separateJsonReads_; }
    void setJson(const QJSValue& value) { json_ = value; }
    QJSValue date() const { return date_; }
    QJSValue finite() const { return finite_; }
    void setDate(const QJSValue& value) { date_ = value; }
    void setFinite(const QJSValue& value) { finite_ = value; }
    QJSValue math() const { return math_; }
    void setMath(const QJSValue& value) { math_ = value; }
   signals:
    void mathChanged();
    void jsonChanged();
    void dateChanged();
    void finiteChanged();
};

// The reserved QML function name is legal as an ordinary native meta-object member.
// Non-final: qmlRegisterType creates the normal QQmlElement subclass.
class UsageScopeItem : public QQuickItem {
    Q_OBJECT
    Q_PROPERTY(QVariantMap unitScopeStats READ scopeStats)
    int calls_ = 0;
    QObject* receiver_ = nullptr;
    QJSValue argument_;

   public:
    explicit UsageScopeItem(QQuickItem* parent = nullptr) : QQuickItem(parent) {}
    Q_INVOKABLE bool isFinite(const QJSValue& value) {
        ++calls_;
        receiver_ = this;
        argument_ = value;
        return false;
    }
    QVariantMap scopeStats() const {
        return {{"calls", calls_},
                {"receiver", receiver_ == this},
                {"argument", argument_.isNumber() && argument_.toNumber() == 60000}};
    }
};

// Per-case recorder, kept alive across the genuine QML destruction handler.
class UsageContextResult final : public QObject {
    Q_OBJECT
   public:
    int calls = 0;
    QJSValue value;
    Q_INVOKABLE void recordResult(const QJSValue& result) {
        ++calls;
        value = result;
    }
};
// An ordinary QObject getter may replace/retire its context during a real lookup.
class UsageContextSwitch final : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool equalColumns READ equalColumns NOTIFY equalColumnsChanged)
   public:
    mutable int reads = 0;
    mutable std::function<void()> effect;
    bool equalColumns() const {
        ++reads;
        if (effect) {
            auto once = std::move(effect);
            once();
        }
        return true;
    }
   signals:
    void equalColumnsChanged();
};

class UsageAccountProof final : public QObject {
    Q_OBJECT
    QQmlEngine* engine_;
    QPointer<QQuickItem> host_;

    static QVariant evaluate(QObject* owner, const QString& source) {
        QQmlExpression expression(QQmlEngine::contextForObject(owner), owner, source);
        const auto result = expression.evaluate();
        if (expression.hasError())
            throw std::runtime_error(expression.error().toString().toStdString());
        return result;
    }
    UsagePanelLease panel(QObject* applicationInfo, QQmlContext* creationContext = nullptr,
                          const QString& scopeMembers = {}) const {
        prerequisite(e11_test_inputs::phase("EDI_E11_USAGE_ACCOUNT_PHASE") == e11_usage_phase::phase(),
                     "selected usage phase must match its compiled source adapter");
        const auto root = e11_test_inputs::sourceRoot("EDI_E11_USAGE_ACCOUNT_SOURCE_ROOT");
        QFile source(root + "/app/qml/Components/AssistantPanel.qml");
        prerequisite(source.open(QIODevice::ReadOnly), "cannot read exact selected Panel source");
        prerequisite(
            QCryptographicHash::hash(source.readAll(), QCryptographicHash::Sha256).toHex() ==
                e11_usage_phase::panelHash(),
            "selected phase Panel preimage differs");
        prerequisite(
            applicationInfo && qjsEngine(applicationInfo) == engine_ && !engine_->hasError(),
            "actual imported singleton and clean proof engine must be identical");
        prerequisite(host_ && host_->window() && host_->window()->isVisible() &&
                         QQmlEngine::contextForObject(host_) &&
                         QQmlEngine::contextForObject(host_)->engine() == engine_,
                     "genuine current QuickTest Item/window/context is required");
        UsagePanelLease owner;
        owner.host = std::make_unique<QQuickItem>();
        owner.host->setParentItem(host_);
        owner.host->setSize(QSizeF(640, 600));
        QQmlComponent toggleComponent(engine_);
        toggleComponent.setData(
            "import QtQuick\nimport EasyApplication.Gui.Elements as EaElements\n"
            "EaElements.ToolButton { objectName: 'e11.usage.unit.toggle'; fontIcon: 'robot' }",
            QUrl("qrc:/tests/UsageAccountToggle.qml"));
        if (toggleComponent.isError())
            throw std::runtime_error(toggleComponent.errorString().toStdString());
        std::unique_ptr<QObject> toggleObject(toggleComponent.createWithInitialProperties({
            {"parent", QVariant::fromValue(owner.host.get())},
        }));
        if (!toggleObject) throw std::runtime_error(toggleComponent.errorString().toStdString());
        auto* toggle = qobject_cast<QQuickItem*>(toggleObject.get());
        prerequisite(toggle && toggle->width() > 0 && toggle->height() > 0 &&
                         QQmlEngine::contextForObject(toggle) &&
                         QQmlEngine::contextForObject(toggle)->engine() == engine_,
                     "genuine original ToolButton Item/context/geometry required");
        toggleObject.release();
        owner.toggle.reset(toggle);
        prerequisite(
            owner.host->window() == host_->window() && owner.toggle->window() == host_->window(),
            "supplied Item host and toggle must already belong to the genuine window");
        const QString code =
            "import QtQuick\nimport QtQuick.Window\nimport QtQuick.Controls\n"
            "import edi.app\nimport EasyApplication.Gui.Style as EaStyle\n"
            "AssistantPanel { assistant: Session.assistant; width: 640; height: 600;"
            "property var unitResetValue: 60; property real unitNow: 0;"
            "readonly property string unitResetText: " +
            e11_usage_phase::reset("unitResetValue", "unitNow") +
            "; property real unitRemaining: 0; readonly property color unitColor: " +
            e11_usage_phase::color("unitRemaining") + "; " + scopeMembers + "}";
        QQmlComponent component(engine_);
        component.setData(code.toUtf8(), QUrl("qrc:/tests/UsageAccountOriginalOwner.qml"));
        if (component.isError()) throw std::runtime_error(component.errorString().toStdString());
        std::unique_ptr<QObject> created(component.createWithInitialProperties(
            {
                {"parent", QVariant::fromValue(owner.host.get())},
                {"toggleControl", QVariant::fromValue(owner.toggle.get())},
            },
            creationContext));
        if (!created) throw std::runtime_error(component.errorString().toStdString());
        const QPointer<QObject> guarded(created.get());
        owner.component = std::unique_ptr<QObject, UsagePopupDelete>(created.release(),
                                                                     UsagePopupDelete{guarded});
        prerequisite(
            owner->property("parent").value<QQuickItem*>() == owner.host.get() &&
                owner->property("toggleControl").value<QQuickItem*>() == owner.toggle.get(),
            "actual required toggle and visual parent are read back, never null substitutes");
        prerequisite(evaluate(owner.get(),
                              "Overlay.overlay !== null && "
                              "Overlay.overlay.Window.window === parent.Window.window")
                         .toBool(),
                     "actual Popup overlay must belong to the same genuine window");
        prerequisite(QQmlEngine::contextForObject(owner.get()) &&
                         QQmlEngine::contextForObject(owner.get())->engine() == engine_,
                     "actual Panel component context must use the same engine");
        prerequisite(
            evaluate(owner.get(), "Qt.isQtObject(assistant) && assistant === Session.assistant")
                .toBool(),
            "actual typed Session assistant is retained, never replaced with a fixture");
        return owner;
    }
    static void text(UsageChecks& check, QObject* owner, const QString& call,
                     const QString& expected, const QString& name) {
        const auto actual = evaluate(owner, call);
        check.require(
            actual.metaType() == QMetaType::fromType<QString>() && actual.toString() == expected,
            name + ": expected '" + expected + "', actual '" + actual.toString() + "'");
    }
    static void boolean(UsageChecks& check, QObject* owner, const QString& call,
                        const QString& name) {
        const auto actual = evaluate(owner, call);
        check.require(actual.metaType() == QMetaType::fromType<bool>() && actual.toBool(), name);
    }

   public:
    explicit UsageAccountProof(QQmlEngine* engine) : QObject(engine), engine_(engine) {}
    Q_INVOKABLE bool bindHost(QObject* candidate) {
        auto* item = qobject_cast<QQuickItem*>(candidate);
        auto* context = item ? QQmlEngine::contextForObject(item) : nullptr;
        if (!item || !item->window() || !item->window()->isVisible() || !context ||
            context->engine() != engine_)
            return false;
        host_ = item;
        return true;
    }

    Q_INVOKABLE QVariantMap resetLiterals(QObject* applicationInfo) const {
        UsageChecks check;
        try {
            const auto owner = panel(applicationInfo);
            struct ResetCase {
                const char* value;
                const char* now;
                const char* expected;
            };
            const ResetCase cases[] = {
                {"undefined", "0", "Reset unavailable"},
                {"null", "0", "Reset unavailable"},
                {"false", "0", "Reset unavailable"},
                {"true", "0", "Reset unavailable"},
                {"'60'", "0", "Reset unavailable"},
                {"new Number(60)", "0", "Reset unavailable"},
                {"NaN", "0", "Reset unavailable"},
                {"Infinity", "0", "Reset unavailable"},
                {"-Infinity", "0", "Reset unavailable"},
                {"8640000000001", "0", "Reset unavailable"},
                {"-8640000000001", "0", "Reset unavailable"},
                {"8640000000000", "8640000000000000", "Reset time reached"},
                {"-8640000000000", "0", "Reset time reached"},
                {"-1", "0", "Reset time reached"},
                {"0", "0", "Reset time reached"},
                {"0.001", "0", "Resets in 1 min"},
                {"60", "0", "Resets in 1 min"},
                {"60.001", "0", "Resets in 2 min"},
                {"3599", "0", "Resets in 1h 0 min"},
                {"3600", "0", "Resets in 1h 0 min"},
                {"3600.001", "0", "Resets in 1h 1 min"},
                {"86340", "0", "Resets in 23h 59 min"},
                {"86400", "0", "Resets in 1d 0h"},
                {"90000", "0", "Resets in 1d 1h"},
                {"172800", "0", "Resets in 2d 0h"},
                {"60", "59999", "Resets in 1 min"},
                {"60", "60000", "Reset time reached"},
                {"60", "60001", "Reset time reached"},
                {"60", "'0'", "Resets in 1 min"},
                {"60", "null", "Resets in 1 min"},
                {"60", "undefined", "Resets in nan min"},
            };
            for (const auto& row : cases)
                text(check, owner.get(), e11_usage_phase::reset(row.value, row.now), row.expected,
                     QStringLiteral("reset value=%1 now=%2").arg(row.value, row.now));
            boolean(check, owner.get(),
                    "(function(){let reads=0;const poison={valueOf:function(){++reads;throw 17;}};"
                    "const result=" +
                        e11_usage_phase::reset("poison", "poison") +
                        ";return result==='Reset unavailable'&&reads===0;})()",
                    "non-number reset rejects before either coercion, without calling valueOf");
            boolean(check, owner.get(),
                    "(function(){let reads=0;const now={valueOf:function(){++reads;throw 17;}};"
                    "const result=" +
                        e11_usage_phase::reset("Infinity", "now") +
                        ";return result==='Reset unavailable'&&reads===0;})()",
                    "invalid Date returns before now coercion");
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        return check.result();
    }

    Q_INVOKABLE QVariantMap colorsAndThrows(QObject* applicationInfo) const {
        UsageChecks check;
        try {
            const auto owner = panel(applicationInfo);
            struct ColorCase {
                const char* value;
                const char* color;
            };
            const ColorCase cases[] = {
                {"-Infinity", "themeForeground"},
                {"-1", "themeForeground"},
                {"-0", "red"},
                {"0", "red"},
                {"4.999", "red"},
                {"5", "orange"},
                {"24.999", "orange"},
                {"25", "themeForeground"},
                {"Infinity", "themeForeground"},
                {"NaN", "themeForeground"},
                {"null", "red"},
                {"undefined", "themeForeground"},
                {"false", "red"},
                {"true", "red"},
                {"'4'", "red"},
                {"'5'", "orange"},
                {"'25'", "themeForeground"},
            };
            for (const auto& row : cases) {
                const auto actual = evaluate(owner.get(), e11_usage_phase::color(row.value));
                const auto expected =
                    evaluate(owner.get(), "EaStyle.Colors." + QString(row.color));
                check.require(
                    actual.canConvert<QColor>() && expected.canConvert<QColor>() &&
                        actual.value<QColor>() == expected.value<QColor>(),
                    QStringLiteral("allowance color strict threshold/coercion %1").arg(row.value));
            }
            // Sentinels are created, thrown, and caught in ONE expression in the imported Panel
            // engine.
            const QStringList sentinels = {"new Error('usage sentinel')",
                                           "({token:17})",
                                           "null",
                                           "undefined",
                                           "false",
                                           "'literal throw'",
                                           "17"};
            for (const auto& sentinel : sentinels) {
                boolean(check, owner.get(),
                        "(function(){const thrown=" + sentinel +
                            ";let reads=0;const now={valueOf:function(){++reads;throw thrown;}};"
                            "try{" +
                            e11_usage_phase::reset("60", "now") +
                            ";return false;}catch(e){return e===thrown&&reads===1;}})()",
                        "reset now coercion retains exact thrown value and one read: " + sentinel);
                boolean(check, owner.get(),
                        "(function(){const thrown=" + sentinel +
                            ";let reads=0;const value={valueOf:function(){++reads;if(reads===2)"
                            "throw thrown;return 0;}};try{" +
                            e11_usage_phase::color("value") +
                            ";return false;}catch(e){return e===thrown&&reads===2;}})()",
                        "color comparison order retains exact second-read throw: " + sentinel);
            }
            for (const auto& row :
                 {std::pair{"-1", 2}, std::pair{"0", 2}, std::pair{"5", 4}, std::pair{"25", 4}}) {
                boolean(check, owner.get(),
                        "(function(){let reads=0;const value={valueOf:function(){++reads;return " +
                            QString(row.first) + ";}};" + e11_usage_phase::color("value") +
                            ";return reads===" + QString::number(row.second) + ";})()",
                        "original short-circuit read count " + QString(row.first));
            }
            check.require(!engine_->hasError(), "caught sentinels leave no pending engine error");
            text(check, owner.get(), e11_usage_phase::reset("60", "0"), "Resets in 1 min",
                 "unrelated subsequent ordinary relation is not poisoned by caught errors");
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        return check.result();
    }

    Q_INVOKABLE QVariantMap translationAndBindings(QObject* applicationInfo) const {
        UsageChecks check;
        try {
            const auto owner = panel(applicationInfo);
            const auto resetProperty = owner->metaObject()->property(
                owner->metaObject()->indexOfProperty("unitResetText"));
            const auto colorProperty =
                owner->metaObject()->property(owner->metaObject()->indexOfProperty("unitColor"));
            prerequisite(resetProperty.hasNotifySignal() && colorProperty.hasNotifySignal(),
                         "actual test-owned bindings need their notify signals");
            QSignalSpy resetChanges(owner.get(), resetProperty.notifySignal());
            QSignalSpy colorChanges(owner.get(), colorProperty.notifySignal());
            prerequisite(resetChanges.isValid() && colorChanges.isValid(),
                         "binding spies must be valid");
            check.require(owner->property("unitResetText").toString() == "Resets in 1 min",
                          "actual bound reset begins in original language");
            UsageTranslator translator;
            const bool installed = QCoreApplication::installTranslator(&translator);
            const auto cleanup = qScopeGuard([&] {
                if (installed) {
                    QCoreApplication::removeTranslator(&translator);
                    engine_->retranslate();
                }
            });
            prerequisite(installed, "nonempty translator installation is mandatory");
            check.require(
                translator.translate("UsageAccountOriginalOwner", "Resets in %1 min", nullptr, -1)
                    .isNull(),
                "test wrapper context cannot satisfy actual AssistantPanel translation");
            engine_->retranslate();
            check.require(
                QTest::qWaitFor([&] {
                    return !resetChanges.isEmpty() &&
                           owner->property("unitResetText").toString() ==
                               QString::fromUtf8("Retour β 1m");
                }),
                "actual reset binding retranslates through AssistantPanel, not wrapper context");
            text(check, owner.get(), e11_usage_phase::reset("undefined", "0"),
                 QString::fromUtf8("Indisponible β"), "translated unavailable");
            text(check, owner.get(), e11_usage_phase::reset("0", "0"),
                 QString::fromUtf8("Échéance β"), "translated reached");
            text(check, owner.get(), e11_usage_phase::reset("90000", "0"),
                 QString::fromUtf8("Retour β heures=1 jours=1"),
                 "translated days and hours original witness");
            text(check, owner.get(), e11_usage_phase::reset("176400", "0"),
                 QString::fromUtf8("Retour β heures=1 jours=2"),
                 "translated reordered unequal day/hour placeholders detect argument swaps");
            prerequisite(owner->setProperty("unitResetValue", 7200),
                         "actual reset input property changes");
            check.require(QTest::qWaitFor([&] {
                              return owner->property("unitResetText").toString() ==
                                     QString::fromUtf8("Retour β 2h 0m");
                          }),
                          "same actual binding observes reset input dependency");
            prerequisite(owner->setProperty("unitNow", 7200000),
                         "actual now input property changes");
            check.require(QTest::qWaitFor([&] {
                              return owner->property("unitResetText").toString() ==
                                     QString::fromUtf8("Échéance β");
                          }),
                          "same actual binding observes now input dependency");
            prerequisite(owner->setProperty("unitRemaining", 5),
                         "actual color input property changes");
            const auto orange = evaluate(owner.get(), "EaStyle.Colors.orange").value<QColor>();
            check.require(QTest::qWaitFor([&] {
                              return !colorChanges.isEmpty() &&
                                     owner->property("unitColor").value<QColor>() == orange;
                          }),
                          "same actual color binding observes threshold input dependency");
            prerequisite(owner->setProperty("unitRemaining", 25),
                         "actual color foreground input changes");
            check.require(
                owner->property("unitColor").value<QColor>() ==
                    evaluate(owner.get(), "EaStyle.Colors.themeForeground").value<QColor>(),
                "same actual binding returns current theme foreground at threshold");
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        return check.result();
    }
    Q_INVOKABLE QVariantMap projectionAndOwnerLifetime(QObject* applicationInfo) const {
        UsageChecks check;
        QVariantList trace;
        try {
            // Two genuine engine-owned Sessions supply distinct typed AVMs. Neither is
            // a test subclass, fake QObject map, direct canonical edit, or new app API.
            auto foreignEngine = std::make_unique<QQmlEngine>();
            edi_app::configure_engine(*foreignEngine);
            QSignalSpy foreignWarnings(foreignEngine.get(), &QQmlEngine::warnings);
            prerequisite(foreignWarnings.isValid(), "foreign engine warning observer is valid");
            auto foreignComponent = std::make_unique<QQmlComponent>(foreignEngine.get());
            foreignComponent->setData(
                "import QtQuick\nimport edi.app\n"
                "QtObject { property AssistantViewModel actualAssistant: Session.assistant }",
                QUrl("qrc:/tests/UsageForeignSession273.qml"));
            prerequisite(!foreignComponent->isError(), "genuine second Session component imports");
            std::unique_ptr<QObject> foreignContext(foreignComponent->create());
            prerequisite(foreignContext != nullptr, "genuine second Session owner exists");
            QPointer<QObject> foreign =
                foreignContext->property("actualAssistant").value<QObject*>();
            prerequisite(foreign && QQmlEngine::contextForObject(foreignContext.get())->engine() ==
                                        foreignEngine.get(),
                         "second AVM is obtained only from its actual imported Session");
            UsageCallLookupContext jsonContext(engine_);
            QJSEngine::setObjectOwnership(&jsonContext, QJSEngine::CppOwnership);
            QQmlContext context(engine_->rootContext());
            context.setContextObject(&jsonContext);
            const auto contextOwner = engine_->newQObject(&jsonContext);
            requireUsageContextReadback(&context, "JSON", jsonContext.json(), true, trace);
            auto owner = panel(applicationInfo, &context);
            auto scriptOwner = engine_->newQObject(owner.get());
            QList<QObject*> disclosureConsumers;
            for (auto* child : owner->findChildren<QObject*>())
                if (child->metaObject()->indexOfProperty("disclosedContext") >= 0 &&
                    child->metaObject()->indexOfProperty("disclosedContextText") >= 0)
                    disclosureConsumers.append(child);
            prerequisite(disclosureConsumers.size() == 1,
                         "the real Panel owns one distinct disclosure JSON consumer");
            const QPointer<QObject> disclosureConsumer = disclosureConsumers.front();
            jsonContext.separateJsonConsumer(disclosureConsumer);
            const auto scriptDisclosure = engine_->newQObject(disclosureConsumer);
            QPointer<QObject> original = scriptOwner.property("assistant").toQObject();
            prerequisite(original && foreign != original, "genuine Session AVMs are distinct");
            const auto usageProperty =
                owner->metaObject()->property(owner->metaObject()->indexOfProperty("usageData"));
            const auto assistantProperty =
                owner->metaObject()->property(owner->metaObject()->indexOfProperty("assistant"));
            prerequisite(usageProperty.hasNotifySignal() && assistantProperty.hasNotifySignal(),
                         "original usage and actual typed owner have notify signals");
            QSignalSpy usageChanges(owner.get(), usageProperty.notifySignal());
            QSignalSpy assistantChanges(owner.get(), assistantProperty.notifySignal());
            QSignalSpy warnings(engine_, &QQmlEngine::warnings);
            prerequisite(
                usageChanges.isValid() && assistantChanges.isValid() && warnings.isValid(),
                "actual publication and engine warning observers are valid");
            const auto engineGlobal = engine_->globalObject();
            const auto globalJSON = engineGlobal.property("JSON");
            const auto install = engine_->evaluate(QStringLiteral(R"JS(
(function(engineGlobal, contextOwner, owner, mode, thrown) {
    const previousJSON = contextOwner.JSON;
    const json = Object.create(engineGlobal.JSON);
    const parse = engineGlobal.JSON.parse, stringify = engineGlobal.JSON.stringify;
    const proof = {events:[], throws:0, parseReceiver:false, stringifyReceiver:false,
                   seenOwner:null, raw:undefined, reentered:0, replacement:null,
                   coercions:0,coercionReceiver:true};
    function coerce(hint) {
        ++proof.coercions;
        proof.coercionReceiver=proof.coercionReceiver && this===json;
        proof.events.push('receiver-coerce:'+hint);
        return 'owned-json378';
    }
    Object.defineProperty(json, 'toString', {configurable:true,value:function(){
        return coerce.call(this,'string');
    }});
    const primitive=engineGlobal.Symbol.toPrimitive;
    Object.defineProperty(json, primitive, {configurable:true,value:function(hint){
        return coerce.call(this,hint);
    }});
    proof.coercionsOwned=typeof primitive==='symbol'
        && typeof Object.getOwnPropertyDescriptor(json,'toString').value==='function'
        && typeof Object.getOwnPropertyDescriptor(json,primitive).value==='function';
    // NoThrow can consume a pending error, then convert the THROWN object.
    // These hooks observe that separate interval, not the blocked receiver.
    proof.managedThrown=thrown!==null && typeof thrown==='object';
    proof.sentinelCoercions=0;
    proof.sentinelReceiver=true;
    function sentinelCoerce(hint) {
        ++proof.sentinelCoercions;
        proof.sentinelReceiver=proof.sentinelReceiver && this===thrown;
        proof.events.push('sentinel-coerce:'+hint);
        return 'owned-thrown380';
    }
    if(proof.managedThrown) {
        Object.defineProperty(thrown,'toString',{configurable:true,value:function(){
            return sentinelCoerce.call(this,'string');
        }});
        Object.defineProperty(thrown,primitive,{configurable:true,value:function(hint){
            return sentinelCoerce.call(this,hint);
        }});
    }
    proof.sentinelHooksOwned=!proof.managedThrown || (
        typeof Object.getOwnPropertyDescriptor(thrown,'toString').value==='function'
        && typeof Object.getOwnPropertyDescriptor(thrown,primitive).value==='function');
    proof.sentinelControl=function(channel){
        if(!proof.managedThrown)return null;
        if(channel==='symbol')return String(thrown);
        if(channel==='toString')return thrown.toString();
        throw new Error('unknown managed sentinel control channel');
    };
    function step(name) {
        proof.events.push(name);
        if (mode === name + '-throw') { ++proof.throws; throw thrown; }
    }
    function stringifyCall(value) {
        proof.stringifyReceiver = this === json;
        proof.seenOwner = owner.assistant;
        proof.raw = value;
        step('stringify-call');
        if (mode === 'reenter-color') {
            ++proof.reentered;
            owner.unitRemaining = 5;
            proof.reentrantColor = owner.unitColor;
        }
        return stringify.call(this, value);
    }
    Object.defineProperty(json, 'stringify', {
        configurable:true,
        get:function() {
            step('stringify-get');
            if(mode==='stringify-noncallable')return false;
            return stringifyCall;
        }
    });
    Object.defineProperty(json, 'parse', {
        configurable:true,
        get:function() {
            step('parse-get');
            if(mode==='parse-noncallable')return false;
            if (mode === 'replace-json') {
                const replacement = {};
                Object.defineProperty(replacement, 'stringify', {
                    configurable:true,
                    get:function() { step('stringify-get'); return stringifyCall; }
                });
                proof.replacement = replacement;
                contextOwner.JSON = replacement;
            }
            return function(value) {
                proof.parseReceiver = this === json;
                step('parse-call');
                return parse.call(this, value);
            };
        }
    });
    proof.json = json;
    proof.gettersOwned = typeof Object.getOwnPropertyDescriptor(json, 'parse').get === 'function'
        && typeof Object.getOwnPropertyDescriptor(json, 'stringify').get === 'function';
    // Direct Qt-JS contrast after the real projection; never another production call.
    proof.noncallableControl=function(){
        try {
            if(mode==='parse-noncallable')json.parse('null');
            else if(mode==='stringify-noncallable')json.stringify({});
            else return null;
        } catch(error) { return {name:error.name,description:String(error)}; }
        return null;
    };
    proof.restore = function() { contextOwner.JSON = previousJSON; };
    return proof;
})
)JS"));
            prerequisite(install.isCallable() && !engine_->hasError(),
                         "same-engine global JSON instrument is callable");
            const auto plainCopy = engine_->evaluate(QStringLiteral(R"JS(
(function(value, source) {
    if (Object.getPrototypeOf(value) !== Object.prototype || !Array.isArray(value.buckets))
        return false;
    value.unitCopyMarker273 = 17;
    const isolated = source.usage.unitCopyMarker273 === undefined;
    delete value.unitCopyMarker273;
    return isolated;
})
)JS"));
            prerequisite(plainCopy.isCallable(), "plain-copy independence observer is callable");
            const QStringList sentinels = {"new Error('projection273')",
                                           "({token:273})",
                                           "null",
                                           "undefined",
                                           "false",
                                           "'literal projection'",
                                           "17"};
            const QStringList throwModes = {"parse-get-throw", "stringify-get-throw",
                                            "stringify-call-throw", "parse-call-throw"};
            QObject* next = foreign.data();
            const QJsonDocument fallback(
                QJsonObject{{"available", false}, {"stale", false}, {"buckets", QJsonArray{}}});
            const QStringList completeOrder = {"stringify-get", "stringify-call", "parse-get",
                                               "parse-call"};
            const auto exercise = [&](const QString& mode, const QJSValue& thrown,
                                      int expectedSteps, bool catches,
                                      const QString& sourceLabel) {
                const auto previousJSON = jsonContext.json();
                auto proof = install.call(
                    {engineGlobal, contextOwner, scriptOwner, QJSValue(mode), thrown});
                const auto json = proof.property("json");
                retainUsageContextAdmission(
                    trace, {{"stage", "owned-projection-admission"},
                            {"mode", mode},
                            {"proof", usageValueKind(proof)},
                            {"json", usageValueKind(json)},
                            {"restore", usageValueKind(proof.property("restore"))},
                            {"pending_engine_error", engine_->hasError()}});
                prerequisite(
                    proof.isObject() && !proof.isError() && !engine_->hasError() &&
                        proof.hasOwnProperty("json") && json.isObject() && !json.isCallable() &&
                        !json.isError() && proof.hasOwnProperty("restore") &&
                        proof.property("restore").isCallable() &&
                        proof.hasOwnProperty("gettersOwned") &&
                        proof.property("gettersOwned").isBool() &&
                        proof.property("gettersOwned").toBool() &&
                        proof.hasOwnProperty("events") && proof.property("events").isArray() &&
                        proof.hasOwnProperty("throws") && proof.property("throws").isNumber() &&
                        proof.property("throws").toInt() == 0 &&
                        proof.property("coercionsOwned").toBool() &&
                        proof.property("coercions").isNumber() &&
                        proof.property("coercions").toInt() == 0 &&
                        proof.property("noncallableControl").isCallable() &&
                        proof.property("sentinelHooksOwned").toBool() &&
                        proof.property("managedThrown").isBool() &&
                        proof.property("sentinelCoercions").isNumber() &&
                        proof.property("sentinelCoercions").toInt() == 0 &&
                        proof.property("sentinelControl").isCallable(),
                    "same-engine own JSON getters and restore admit before live use");
                const auto restore = qScopeGuard([&] {
                    const auto restored = proof.property("restore").callWithInstance(proof);
                    check.require(
                        !restored.isError() && !engine_->hasError() &&
                            jsonContext.json().strictlyEquals(previousJSON) &&
                            engine_->globalObject().property("JSON").strictlyEquals(globalJSON),
                        "owned JSON restoration leaves the actual locked global unchanged");
                });
                jsonContext.setJson(json);
                requireUsageContextReadback(&context, "JSON", json, true, trace);
                // Exercise the actual other binding while this exact throwing
                // receiver is installed. Scope is by concrete QML owner, never by
                // event prefix, value, mode, sentinel or a timing/settling window.
                const int separateReads = jsonContext.separateJsonReads();
                const int disclosureValue = trace.size() + 17;
                prerequisite(disclosureConsumer->setProperty(
                                 "disclosedContextText",
                                 QStringLiteral("{\"usageScopeControl\":%1}")
                                     .arg(disclosureValue)),
                             "the separate real disclosure input changes ordinarily");
                const auto disclosure = scriptDisclosure.property("disclosedContext");
                check.require(
                    disclosure.property("usageScopeControl").toInt() == disclosureValue &&
                        jsonContext.separateJsonReads() > separateReads &&
                        proof.property("events").property("length").toInt() == 0 &&
                        proof.property("throws").toInt() == 0 && !engine_->hasError(),
                    "the original disclosure binding parses its own input without entering "
                    "the armed usage-projection receiver");
                const int publications = usageChanges.count();
                scriptOwner.setProperty("assistant", engine_->newQObject(next));
                prerequisite(scriptOwner.property("assistant").toQObject() == next,
                             "the actual typed Panel owner changes through its ordinary setter");
                const auto value = scriptOwner.property("usageData");
                trace.append(QVariantMap{
                    {"mode", mode},
                    {"sentinel", sourceLabel},
                    {"events", proof.property("events").toVariant()},
                    {"throws", proof.property("throws").toInt()},
                    {"coercions", proof.property("coercions").toInt()},
                    {"coercion_receiver", proof.property("coercionReceiver").toBool()},
                    {"managed_thrown", proof.property("managedThrown").toBool()},
                    {"sentinel_coercions", proof.property("sentinelCoercions").toInt()},
                    {"sentinel_receiver", proof.property("sentinelReceiver").toBool()},
                    {"separate_json_reads", jsonContext.separateJsonReads() - separateReads},
                    {"value", value.toVariant()},
                    {"owner_current", scriptOwner.property("assistant").toQObject() == next},
                    {"parse_receiver", proof.property("parseReceiver").toBool()},
                    {"stringify_receiver", proof.property("stringifyReceiver").toBool()}});
                check.require(usageChanges.count() > publications,
                              "owner replacement actually recomputes the production projection");
                check.require(
                    proof.property("events").toVariant().toStringList() ==
                        completeOrder.mid(0, expectedSteps),
                    "original Qt resolves stringify before parse on its captured JSON receiver");
                check.require(proof.property("throws").toInt() == (catches ? 1 : 0),
                              "the armed original boundary really throws exactly once");
                check.require(proof.property("coercions").toInt() == 0 &&
                                  proof.property("coercionReceiver").toBool(),
                              "a first thrown getter never reaches receiver coercion or "
                              "secondary noncallable error formatting");
                check.require(proof.property("sentinelCoercions").toInt() == 0 &&
                                  proof.property("sentinelReceiver").toBool(),
                              "the first managed thrown sentinel is never converted by a "
                              "secondary error formatter before the presentation catch");
                check.require(!engine_->hasError(),
                              "the original JSON presentation catch consumes any thrown value");
                if (catches) {
                    check.require(
                        QJsonDocument::fromVariant(value.toVariant()) == fallback,
                        "all caught projection failures publish exactly the original fallback");
                } else {
                    check.require(
                        QJsonDocument::fromVariant(value.toVariant()) ==
                            QJsonDocument::fromVariant(next->property("usage")),
                        "ordinary projection preserves the actual current owner JSON values");
                    check.require(
                        plainCopy.call({value, engine_->newQObject(next)}).toBool(),
                        "projection is a plain mutable copy independent of canonical usage");
                    check.require(
                        proof.property("parseReceiver").toBool() &&
                            proof.property("stringifyReceiver").toBool() &&
                            proof.property("seenOwner").toQObject() == next,
                        "original method receivers and then-current genuine owner are retained");
                    if (mode == "replace-json")
                        check.require(
                            jsonContext.json().strictlyEquals(proof.property("replacement")),
                            "the late parse getter replaces context JSON without "
                            "retargeting prior stringify");
                    if (mode == "reenter-color") {
                        check.require(
                            proof.property("reentered").toInt() == 1 &&
                                owner->property("unitColor").value<QColor>() ==
                                    evaluate(owner.get(), "EaStyle.Colors.orange").value<QColor>(),
                            "an unrelated actual color binding completes inside stringify "
                            "reentry");
                    }
                }
                next = next == foreign.data() ? original.data() : foreign.data();
            };
            for (int mode = 0; mode < throwModes.size(); ++mode)
                for (const auto& source : sentinels)
                    exercise(
                        throwModes[mode], engine_->evaluate(source),
                        static_cast<int>(completeOrder.indexOf(throwModes[mode].chopped(6))) + 1,
                        true, source);
            for (const auto& mode : {"ordinary", "replace-json", "reenter-color"})
                exercise(QString::fromLatin1(mode), QJSValue(QJSValue::UndefinedValue), 4, false,
                         QStringLiteral("ordinary control"));
            // Independent Qt-JS positive controls arm both coercion channels without
            // another migrated procedure call, owner publication, or trace row.
            for (const auto* member : {"parse", "stringify"}) {
                const auto control =
                    install.call({engineGlobal, contextOwner, scriptOwner,
                                  QJSValue(QString::fromLatin1(member) + "-noncallable"),
                                  QJSValue(QJSValue::UndefinedValue)});
                prerequisite(control.isObject() && !control.isError() && !engine_->hasError() &&
                                 control.property("coercionsOwned").toBool() &&
                                 control.property("coercions").toInt() == 0 &&
                                 control.property("throws").toInt() == 0 &&
                                 control.property("noncallableControl").isCallable(),
                             "the direct Qt-JS noncallable source control admits before use");
                const auto direct =
                    control.property("noncallableControl").callWithInstance(control);
                const auto description =
                    QStringLiteral(
                        "TypeError: Property '%1' of object owned-json378 is not a function")
                        .arg(QString::fromLatin1(member));
                const QStringList expected{QString::fromLatin1(member) + "-get",
                                           QStringLiteral("receiver-coerce:string")};
                check.require(
                    direct.isObject() && !direct.isError() &&
                        direct.property("name").toString() == "TypeError" &&
                        direct.property("description").toString() == description &&
                        control.property("events").toVariant().toStringList() == expected &&
                        control.property("coercions").toInt() == 1 &&
                        control.property("coercionReceiver").toBool() &&
                        control.property("throws").toInt() == 0 && !engine_->hasError(),
                    "the owned receiver's direct Qt-JS false-callee contrast has its "
                    "source-declared description and actual receiver coercion");
            }
            // Fresh instances of the existing Error/object source sentinels calibrate
            // BOTH conversion hooks outside the production exercise and trace roster.
            for (const auto& source : {sentinels.at(0), sentinels.at(1)}) {
                const auto thrown = engine_->evaluate(source);
                prerequisite(thrown.isObject() && !engine_->hasError(),
                             "the managed source-control sentinel is real and same-engine");
                const auto control = install.call({engineGlobal, contextOwner, scriptOwner,
                                                   QJSValue(QStringLiteral("ordinary")), thrown});
                prerequisite(control.isObject() && !control.isError() && !engine_->hasError() &&
                                 control.property("managedThrown").toBool() &&
                                 control.property("sentinelHooksOwned").toBool() &&
                                 control.property("sentinelCoercions").toInt() == 0 &&
                                 control.property("sentinelControl").isCallable(),
                             "managed sentinel hooks are admitted before their direct controls");
                int conversions = 0;
                QStringList expected;
                for (const auto* channel : {"symbol", "toString"}) {
                    const auto converted =
                        control.property("sentinelControl")
                            .callWithInstance(control, {QJSValue(QString::fromLatin1(channel))});
                    ++conversions;
                    expected.append(QStringLiteral("sentinel-coerce:string"));
                    check.require(
                        converted.isString() && converted.toString() == "owned-thrown380" &&
                            control.property("sentinelCoercions").toInt() == conversions &&
                            control.property("sentinelReceiver").toBool() &&
                            control.property("events").toVariant().toStringList() == expected &&
                            control.property("throws").toInt() == 0 &&
                            control.property("coercions").toInt() == 0 && !engine_->hasError(),
                        "direct managed sentinel conversion reaches its exact owned "
                        "hook and receiver without a migrated call or pending error");
                }
            }
            // Detach before destroying the genuine former Session. Old-owner cleanup must
            // not clear or republish the now-current original owner.
            scriptOwner.setProperty("assistant", engine_->newQObject(original.data()));
            prerequisite(scriptOwner.property("assistant").toQObject() == original.data(),
                         "actual original owner is restored before the foreign Session retires");
            const int ownerNotifies = assistantChanges.count();
            prerequisite(!foreignEngine->hasError(), "foreign engine has no pending error");
            foreignContext.reset();
            foreignComponent.reset();
            foreignEngine.reset();
            check.require(foreign.isNull(),
                          "the detached genuine foreign AVM really reaches destruction");
            check.require(assistantChanges.count() == ownerNotifies &&
                              scriptOwner.property("assistant").toQObject() == original.data(),
                          "detached old-owner destruction cannot clear the current Panel owner");
            check.require(
                QJsonDocument::fromVariant(scriptOwner.property("usageData").toVariant()) ==
                    QJsonDocument::fromVariant(original->property("usage")),
                "the retained current projection survives actual former-owner destruction");
            check.require(
                warnings.isEmpty() && foreignWarnings.isEmpty() && !engine_->hasError(),
                "supported owner/catch/reentry controls leave no unrelated QML or pending error");
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        auto result = check.result();
        result.insert("projection_trace", trace);
        return result;
    }
    Q_INVOKABLE QVariantMap nullMemberReceivers(QObject* applicationInfo) const {
        UsageChecks check;
        QVariantList trace;
        try {
            // Ordinary real Panel admission is retained; adversaries use the public operand domain
            // below.
            auto ordinaryPanel = panel(applicationInfo);
            check.require(ordinaryPanel->property("accountPlanLabel").toString().isEmpty(),
                          "the actual disconnected Panel keeps its ordinary empty plan label");
            const auto phase = e11_usage_phase::phase();
            prerequisite(phase == "native" || phase == "original",
                         "the public operand gate has an explicit closed source phase");
            const QString source =
                phase == "native"
                    ? QStringLiteral("ApplicationInfo.assistantAccountPlanLabel(unitOwner)")
                    : QStringLiteral(
                          "accountPlan.split(/[_ -]+/).map(word => word.length ? "
                          "word[0].toUpperCase() + word.slice(1) : \"\").join(\" \")");
            const auto make = engine_->evaluate(QStringLiteral(R"JS(
(function(stage, receiver) {
    const proof = {splits:0, maps:0, splitReceiver:true, mapReceiver:true, separator:true};
    const plan = {};
    Object.defineProperty(plan, 'split', {configurable:true, enumerable:true, writable:true,
        value:function(separator) {
            'use strict';
            ++proof.splits;
            proof.splitReceiver = proof.splitReceiver && this === plan;
            proof.separator = proof.separator && separator instanceof RegExp
                && separator.source === '[_ -]+';
            if (stage === 'ordinary') return String.prototype.split.call('plus_pro', separator);
            if (stage === 'map') return receiver;
            const mapped = {map:function() {
                'use strict'; ++proof.maps;
                proof.mapReceiver = proof.mapReceiver && this === mapped;
                return receiver;
            }};
            return mapped;
        }
    });
    proof.plan = plan;
    return proof;
})
)JS"));
            prerequisite(make.isCallable() && !engine_->hasError(),
                         "test-owned public operand factory is callable in the actual engine");
            QSignalSpy warnings(engine_, &QQmlEngine::warnings);
            prerequisite(warnings.isValid(), "unrelated QML warnings remain observed");
            const auto exercise = [&](const char* member, const char* receiver) {
                auto proof = make.call({QJSValue(QString::fromLatin1(member)),
                                        engine_->evaluate(QString::fromLatin1(receiver))});
                const auto plan = proof.property("plan");
                retainUsageContextAdmission(trace,
                                            {{"stage", "public-plan-operand-admission"},
                                             {"phase", QString::fromLatin1(phase)},
                                             {"member", QString::fromLatin1(member)},
                                             {"receiver", QString::fromLatin1(receiver)},
                                             {"proof", usageValueKind(proof)},
                                             {"plan", usageValueKind(plan)},
                                             {"pending_engine_error", engine_->hasError()}});
                prerequisite(
                    proof.isObject() && !proof.isError() && !engine_->hasError() &&
                        proof.hasOwnProperty("plan") && plan.isObject() && !plan.isError() &&
                        !plan.isCallable() && plan.hasOwnProperty("split") &&
                        plan.property("split").isCallable() &&
                        proof.property("splits").isNumber() &&
                        proof.property("splits").toInt() == 0 &&
                        proof.property("maps").isNumber() && proof.property("maps").toInt() == 0,
                    "own callable operand and zero live counters admit before use");
                const QUrl location(QStringLiteral("qrc:/tests/UsagePublicPlanOperand.qml"));
                QQmlComponent component(engine_);
                component.setData(
                    "import QtQml\nimport edi.app\n"
                    "QtObject { id: operand; property var accountPlan; "
                    "readonly property var unitOwner: operand }",
                    location);
                prerequisite(!component.isError(), "real public operand component imports");
                std::unique_ptr<QObject> owner(component.createWithInitialProperties(
                    {{"accountPlan", QVariant::fromValue(plan)}}));
                prerequisite(
                    owner && QQmlEngine::contextForObject(owner.get()) &&
                        QQmlEngine::contextForObject(owner.get())->engine() == engine_ &&
                        engine_->newQObject(owner.get()).property("unitOwner").toQObject() ==
                            owner.get() &&
                        engine_->newQObject(owner.get())
                            .property("accountPlan")
                            .strictlyEquals(plan),
                    "actual same-engine QML owner holds the exact admitted var operand");
                QQmlExpression expression(QQmlEngine::contextForObject(owner.get()), owner.get(),
                                          source);
                expression.setSourceLocation(location.toString(), 1);
                const auto value = expression.evaluate();
                const auto error = expression.error();
                const bool ordinary = QByteArray(member) == "ordinary";
                const QString expected =
                    QStringLiteral("TypeError: Cannot call method '%1' of %2")
                        .arg(QString::fromLatin1(member), QString::fromLatin1(receiver));
                trace.append(
                    QVariantMap{{"scope",
                                 "public bridge operand / frozen original expression; not "
                                 "readonly Panel adversary"},
                                {"phase", QString::fromLatin1(phase)},
                                {"member", QString::fromLatin1(member)},
                                {"receiver", QString::fromLatin1(receiver)},
                                {"source", source},
                                {"value", value},
                                {"has_error", expression.hasError()},
                                {"description", error.description()},
                                {"url", error.url().toString()},
                                {"line", error.line()},
                                {"splits", proof.property("splits").toInt()},
                                {"maps", proof.property("maps").toInt()},
                                {"split_receiver", proof.property("splitReceiver").toBool()},
                                {"map_receiver", proof.property("mapReceiver").toBool()}});
                const bool armed =
                    proof.property("splits").toInt() == 1 &&
                    proof.property("maps").toInt() == (QByteArray(member) == "join" ? 1 : 0) &&
                    proof.property("splitReceiver").toBool() &&
                    proof.property("mapReceiver").toBool() && proof.property("separator").toBool();
                check.require(
                    armed, "the real public expression reaches exact operand calls and receivers");
                if (ordinary) {
                    const bool positive = !expression.hasError() && value.toString() == "Plus Pro";
                    check.require(positive,
                                  "the admitted ordinary operand retains the original plan label");
                    prerequisite(
                        positive && armed,
                        "null-member gates require an actual positive public invocation first");
                } else {
                    check.require(expression.hasError() && error.description() == expected &&
                                      error.url() == location && error.line() > 0,
                                  "the public inherited-context call boundary retains its exact "
                                  "method-call TypeError");
                }
                check.require(!engine_->hasError(),
                              "the actual QQmlExpression holds the reported error without a "
                              "pending exception");
            };
            exercise("ordinary", "undefined");
            for (const auto& member : {"map", "join"})
                for (const auto& receiver : {"null", "undefined"}) exercise(member, receiver);
            check.require(warnings.isEmpty(),
                          "supported public operand expressions add no unrelated QML warning");
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        auto result = check.result();
        result.insert("member_receiver_scope",
                      "public operand boundary, not readonly actual Panel binding");
        result.insert("member_receiver_trace", trace);
        return result;
    }

    Q_INVOKABLE QVariantMap actualContextLookups(QObject* applicationInfo,
                                                 bool retirementCharacterization = false) const {
        UsageChecks check;
        QVariantList trace;
        try {
            const auto phase = e11_usage_phase::phase();
            prerequisite((phase == "native" || phase == "original") &&
                             e11_test_inputs::phase("EDI_E11_USAGE_ACCOUNT_PHASE") == phase,
                         "actual context matrix requires its selected compiled source phase");
            const auto selected = qgetenv("EDI_E11_CONTEXT_RETIREMENT_CHARACTERIZATION");
            prerequisite(
                retirementCharacterization ? selected == "selected" : selected.isEmpty(),
                "retirement characterization is a separate explicitly selected invocation");
            retainUsageContextAdmission(
                trace,
                {{"stage", "context-validation-mode"},
                 {"phase", QString::fromLatin1(phase)},
                 {"mode",
                  retirementCharacterization ? "external-retirement-characterization" : "live"}});
            const auto engineGlobal = engine_->globalObject();
            const auto make = engine_->evaluate(QStringLiteral(R"JS(
(function(engineGlobal, tag, minutes, invalidDate, finiteMode, expectedReceiver) {
    const originalJSON=engineGlobal.JSON, originalDate=engineGlobal.Date;
    const originalMath=engineGlobal.Math, originalArray=engineGlobal.Array;
    const originalFinite=engineGlobal.isFinite;
    const state={json:0,jsonReceiver:true,mathReceiver:true,date:0,constructed:0,finite:0,receiver:true,reentered:0,array:0,owner:null};
    const json=Object.create(originalJSON);
    Object.defineProperty(json, 'stringify', {configurable:true, enumerable:true, writable:true,
        value:function() { 'use strict'; ++state.json; state.jsonReceiver=state.jsonReceiver&&this===json; return originalJSON.stringify.apply(originalJSON,arguments); }});
    Object.defineProperty(json, 'parse', {configurable:true, enumerable:true, writable:true,
        value:function(value) {
        'use strict'; state.jsonReceiver=state.jsonReceiver&&this===json;
        const result=originalJSON.parse.apply(originalJSON,arguments);
        if(result && Array.isArray(result.buckets) && typeof result.available==='boolean')
            result.unitContextTag=tag;
        return result;
    }});
    function ContextArray() { return originalArray.apply(null,arguments); }
    Object.setPrototypeOf(ContextArray,originalArray);
    ContextArray.prototype=originalArray.prototype;
    Object.defineProperty(ContextArray, 'from', {configurable:true, enumerable:true, writable:true,
        value:function() { ++state.array; return originalArray.from.apply(this,arguments); }});
    function ContextDate(value) {
        const target=arguments.length===1 && value===60000;
        if(target)++state.date;
        if(!new.target)return originalDate.apply(null,arguments);
        if(target && new.target===ContextDate)++state.constructed;
        return invalidDate ? {getTime:function(){return NaN;}}
                           : Reflect.construct(originalDate,originalArray.from(arguments));
    }
    ContextDate.now=function(){return originalDate.now();};
    const math=Object.create(originalMath);
    Object.defineProperty(math, 'ceil', {configurable:true, enumerable:true, writable:true,
        value:function(value){'use strict';state.mathReceiver=state.mathReceiver&&this===math;return value===1 ? minutes : originalMath.ceil(value);}});
    const finite=function(value){
        'use strict';
        ++state.finite;
        state.receiver=state.receiver && this===expectedReceiver;
        if(state.owner){++state.reentered;state.owner.unitRemaining=5;}
        return finiteMode==='false' ? false : finiteMode==='true' ? true : originalFinite(value);
    };
    return {JSON:json,Array:ContextArray,Date:ContextDate,Math:math,isFinite:finite,state:state};
})
)JS"));
            retainUsageContextAdmission(trace, {{"stage", "factory-admission"},
                                                {"value", usageValueKind(make)},
                                                {"pending_engine_error", engine_->hasError()}});
            prerequisite(make.isCallable(), "context aliases delegate to real original builtins");
            for (const bool objectMode : {false, true}) {
                UsageLookupContext object;
                QJSEngine::setObjectOwnership(&object, QJSEngine::CppOwnership);
                auto context = std::make_unique<QQmlContext>(engine_->rootContext());
                const auto receiver =
                    objectMode ? engine_->newQObject(&object) : QJSValue(QJSValue::UndefinedValue);
                const auto bundle = [&](const char* tag, int minutes, bool invalid,
                                        const char* finite) {
                    const auto value = make.call(
                        {engineGlobal, QJSValue(QString::fromLatin1(tag)), QJSValue(minutes),
                         QJSValue(invalid), QJSValue(QString::fromLatin1(finite)), receiver});
                    requireUsageContextBundle(engine_, value, tag, objectMode, trace);
                    return value;
                };
                const auto a = bundle("context-A", 37, false, "delegate");
                const auto b = bundle("context-B", 38, true, "delegate");
                const auto no = bundle("context-false", 38, false, "false");
                const auto yes = bundle("context-true", 38, false, "true");
                if (objectMode) context->setContextObject(&object);
                const auto assign = [&](const QString& name, const QJSValue& value) {
                    if (objectMode)
                        object.set(name, value);
                    else
                        context->setContextProperty(name, QVariant::fromValue(value));
                    requireUsageContextReadback(context.get(), name, value, objectMode, trace);
                };
                for (const auto& name : {"JSON", "Array", "Date", "Math", "isFinite"})
                    assign(QString::fromLatin1(name), a.property(QString::fromLatin1(name)));
                QSignalSpy warnings(engine_, &QQmlEngine::warnings);
                prerequisite(warnings.isValid(), "actual context binding warnings are observed");
                // Declare restoration before the lease so every Panel is destroyed first,
                // including when a later fixture prerequisite throws.
                QPointer<QObject> presentationPreferences;
                QVariant savedPresentation;
                bool restorePresentation = false;
                const auto restoreShown = qScopeGuard([&] {
                    if (!restorePresentation) return;
                    const bool restored =
                        presentationPreferences &&
                        presentationPreferences->setProperty("assistantShown", savedPresentation);
                    check.require(
                        restored && presentationPreferences &&
                            presentationPreferences->property("assistantShown") ==
                                savedPresentation,
                        "the real public shown preference is restored after Panel teardown");
                    check.require(warnings.isEmpty() && !engine_->hasError(),
                                  "shown-state restoration adds no unrelated QML error");
                });
                auto owner = panel(applicationInfo, context.get());
                if (!retirementCharacterization) {
                    auto* actualPreferences = engine_->singletonInstance<QObject*>(
                        QStringLiteral("edi.app"), QStringLiteral("Preferences"));
                    prerequisite(
                        actualPreferences && QQmlEngine::contextForObject(actualPreferences) &&
                            QQmlEngine::contextForObject(actualPreferences)->engine() == engine_,
                        "shown setup uses the real same-engine Preferences singleton");
                    const auto previous = actualPreferences->property("assistantShown");
                    prerequisite(previous.metaType() == QMetaType::fromType<bool>(),
                                 "the public presentation preference has its declared bool type");
                    savedPresentation = previous;
                    presentationPreferences = actualPreferences;
                    restorePresentation = true;
                    prerequisite(presentationPreferences->setProperty("assistantShown", true),
                                 "the real public shown preference admits the live Panel");
                    prerequisite(
                        owner->property("shown").toBool() && owner->property("visible").toBool(),
                        "unchanged Panel bindings enter the ordinary shown lifecycle");
                    const QPointer<QQuickItem> content =
                        owner->property("contentItem").value<QQuickItem*>();
                    prerequisite(
                        content && content->window() == host_->window() && content->parentItem() &&
                            content->parentItem()->window() == host_->window(),
                        "normal Popup entry attaches content and PopupItem to the real window");
                }
                auto scriptOwner = engine_->newQObject(owner.get());
                const auto counters = [](const QJSValue& state) {
                    return QVariantMap{{"json", state.property("json").toInt()},
                                       {"json_receiver", state.property("jsonReceiver").toBool()},
                                       {"math_receiver", state.property("mathReceiver").toBool()},
                                       {"date", state.property("date").toInt()},
                                       {"constructed", state.property("constructed").toInt()},
                                       {"finite", state.property("finite").toInt()},
                                       {"receiver", state.property("receiver").toBool()},
                                       {"reentered", state.property("reentered").toInt()},
                                       {"array", state.property("array").toInt()}};
                };
                const auto snapshot = [&](const char* stage) {
                    trace.append(QVariantMap{
                        {"object_context", objectMode},
                        {"stage", QString::fromLatin1(stage)},
                        {"text", owner->property("unitResetText")},
                        {"tag",
                         scriptOwner.property("usageData").property("unitContextTag").toString()},
                        {"A", counters(a.property("state"))},
                        {"B", counters(b.property("state"))},
                        {"false", counters(no.property("state"))},
                        {"true", counters(yes.property("state"))}});
                };
                snapshot("created");
                check.require(owner->property("unitResetText").toString() == "Resets in 37 min",
                              "actual original reset resolves context Date/Math/isFinite names");
                check.require(
                    scriptOwner.property("usageData").property("unitContextTag").toString() ==
                        "context-A",
                    "actual original usage projection calls context JSON, not global JSON");
                check.require(
                    a.property("state").property("json").toInt() > 0 &&
                        a.property("state").property("jsonReceiver").toBool() &&
                        a.property("state").property("mathReceiver").toBool(),
                    "context JSON and Math member calls retain their real method receivers");
                assign("Math", b.property("Math"));
                snapshot("math-notify");
                check.require(owner->property("unitResetText").toString() == "Resets in 38 min",
                              "Math context notification updates the existing reset binding");
                assign("JSON", b.property("JSON"));
                snapshot("json-notify");
                check.require(
                    scriptOwner.property("usageData").property("unitContextTag").toString() ==
                        "context-B",
                    "JSON context notification updates the existing projection binding");
                check.require(b.property("state").property("json").toInt() > 0 &&
                                  b.property("state").property("jsonReceiver").toBool() &&
                                  b.property("state").property("mathReceiver").toBool(),
                              "replacement context objects receive their own member calls");
                assign("Date", b.property("Date"));
                snapshot("date-invalid");
                check.require(owner->property("unitResetText").toString() == "Reset unavailable",
                              "the context Date constructor, including invalid time, is honored");
                assign("Date", a.property("Date"));
                snapshot("date-restored");
                check.require(
                    owner->property("unitResetText").toString() == "Resets in 38 min",
                    "the actual Date dependency returns to its valid context constructor");
                assign("isFinite", no.property("isFinite"));
                snapshot("finite-false");
                check.require(owner->property("unitResetText").toString() == "Reset unavailable",
                              "an actual context isFinite function controls the original guard");
                assign("isFinite", yes.property("isFinite"));
                yes.property("state").setProperty("owner", scriptOwner);
                prerequisite(owner->setProperty("unitResetValue", 120),
                             "existing bound reset input changes");
                snapshot("finite-reentry");
                check.require(
                    owner->property("unitResetText").toString() == "Resets in 2 min" &&
                        owner->property("unitColor").value<QColor>() ==
                            evaluate(owner.get(), "EaStyle.Colors.orange").value<QColor>(),
                    "context call reentry completes an unrelated actual color binding");
                for (const auto& value : {a, no, yes})
                    check.require(value.property("state").property("finite").toInt() > 0 &&
                                      value.property("state").property("receiver").toBool(),
                                  "context properties and context objects retain their distinct "
                                  "strict call bases");
                check.require(a.property("state").property("date").toInt() > 0 &&
                                  a.property("state").property("constructed").toInt() ==
                                      a.property("state").property("date").toInt(),
                              "the context Date function is called as a constructor");
                check.require(yes.property("state").property("reentered").toInt() > 0,
                              "the context callback really reaches its armed reentry");
                if (objectMode) {
                    prerequisite(owner->setProperty("unitResetValue", 60),
                                 "normal reset input returns");
                    const auto explicitMath = bundle("explicit-Math", 39, false, "delegate");
                    context->setContextProperty(
                        "Math", QVariant::fromValue(explicitMath.property("Math")));
                    requireUsageContextReadback(context.get(), "Math",
                                                explicitMath.property("Math"), true, trace);
                    snapshot("explicit-over-object");
                    check.require(
                        owner->property("unitResetText").toString() == "Resets in 39 min",
                        "explicit context properties outrank same-name context object properties");
                    object.set("Math", a.property("Math"));
                    requireUsageContextReadback(context.get(), "Math",
                                                explicitMath.property("Math"), true, trace);
                    snapshot("shadowed-object-notify");
                    check.require(
                        owner->property("unitResetText").toString() == "Resets in 39 min",
                        "the shadowed context object cannot override an explicit context "
                        "property");
                }
                check.require(
                    owner->property("accountInitial").toString().isEmpty(),
                    "the genuine disconnected account keeps the original empty-email branch");
                check.require(warnings.isEmpty() && !engine_->hasError(),
                              "the complete live context matrix adds no unrelated QML error");
                if (retirementCharacterization) {
                    retainUsageContextAdmission(
                        trace, {{"stage", "external-retirement-characterization-begin"},
                                {"object_context", objectMode}});
                    // No unsupported direct method call is made after context destruction.
                    // The public context contract invalidates existing bindings without destroying
                    // objects.
                    trace.append(QVariantMap{{"stage", "before-context-destroy"},
                                             {"text", owner->property("unitResetText")}});
                    const int calls = yes.property("state").property("finite").toInt();
                    QPointer<QObject> retainedOwner(owner.get());
                    context.reset();
                    prerequisite(owner->setProperty("unitResetValue", 180),
                                 "a surviving object input remains writable");
                    object.set("Math", a.property("Math"));
                    snapshot("context-destroyed");
                    check.require(
                        retainedOwner && yes.property("state").property("finite").toInt() == calls,
                        "destroyed creation context stops bindings while the genuine object "
                        "survives");
                    check.require(warnings.isEmpty() && !engine_->hasError(),
                                  "supported context updates/reentry/invalidation add no "
                                  "unrelated QML errors");
                } else {
                    // This live control chooses an enclosing context lifetime; Qt's public
                    // surviving-object contract remains independently characterized below.
                    QPointer<QObject> closedOwner(owner.get());
                    owner.component.reset();
                    prerequisite(closedOwner.isNull(), "ordinary live Panel teardown completes");
                    context.reset();
                    check.require(warnings.isEmpty() && !engine_->hasError(),
                                  "ordinary live fixture teardown adds no unrelated QML error");
                    retainUsageContextAdmission(trace,
                                                {{"stage", "live-context-normal-teardown"},
                                                 {"object_context", objectMode},
                                                 {"panel_destroyed", closedOwner.isNull()}});
                }
            }
            // Legal native scope method versus context/global function at the public reset
            // bridge / frozen-original procedure boundary; not a Panel-declared QML method.
            UsageLookupContext object;
            QJSEngine::setObjectOwnership(&object, QJSEngine::CppOwnership);
            QQmlContext context(engine_->rootContext());
            const auto values = make.call(
                {engineGlobal, QJSValue(QStringLiteral("scope-context")), QJSValue(37),
                 QJSValue(false), QJSValue(QStringLiteral("true")), engine_->newQObject(&object)});
            requireUsageContextBundle(engine_, values, "scope-context", true, trace);
            context.setContextObject(&object);
            for (const auto& name : {"JSON", "Array", "Date", "Math", "isFinite"}) {
                const auto expected = values.property(QString::fromLatin1(name));
                object.set(QString::fromLatin1(name), expected);
                requireUsageContextReadback(&context, QString::fromLatin1(name), expected, true,
                                            trace);
            }
            QSignalSpy scopeWarnings(engine_, &QQmlEngine::warnings);
            prerequisite(scopeWarnings.isValid(), "scope-method warning observer is valid");
            const auto scopePhase = e11_usage_phase::phase();
            prerequisite(scopePhase == "native" || scopePhase == "original",
                         "scope invocation has an explicit source phase");
            const QString scopeMethod =
                scopePhase == "native"
                    ? QStringLiteral(
                          "function usageResetLabel(value, now) { return "
                          "ApplicationInfo.assistantUsageResetLabel(value, now); }")
                    : QStringLiteral(R"QML(
    function usageResetLabel(value, now) {
        if (typeof value !== "number" || !isFinite(new Date(value * 1000).getTime())) return qsTr("Reset unavailable");
        const minutes = Math.ceil((value * 1000 - now) / 60000);
        if (minutes <= 0) return qsTr("Reset time reached");
        const days = Math.floor(minutes / 1440);
        const hours = Math.floor((minutes % 1440) / 60);
        if (days > 0) return qsTr("Resets in %1d %2h").arg(days).arg(hours);
        if (hours > 0) return qsTr("Resets in %1h %2 min").arg(hours).arg(minutes % 60);
        return qsTr("Resets in %1 min").arg(minutes);
    }
)QML");
            QQmlComponent scopeComponent(engine_);
            scopeComponent.setData(
                ("import QtQuick\nimport edi.app\nimport UsageAccountAcceptance 1.0\n"
                 "UsageScopeItem { property var unitResetValue: 60; property real unitNow: 0;"
                 "readonly property string unitResetText: usageResetLabel(unitResetValue, "
                 "unitNow);" +
                 scopeMethod + "}")
                    .toUtf8(),
                QUrl("qrc:/tests/UsageNativeScopeOperand.qml"));
            if (scopeComponent.isError())
                throw std::runtime_error(scopeComponent.errorString().toStdString());
            std::unique_ptr<QObject> owner(scopeComponent.createWithInitialProperties(
                {{"parent", QVariant::fromValue(host_.data())}}, &context));
            if (!owner) throw std::runtime_error(scopeComponent.errorString().toStdString());
            auto* scope = qobject_cast<UsageScopeItem*>(owner.get());
            prerequisite(scope && scope->parentItem() == host_ &&
                             scope->window() == host_->window() &&
                             QQmlEngine::contextForObject(scope) &&
                             QQmlEngine::contextForObject(scope)->engine() == engine_,
                         "real native scope Item belongs to the genuine host/window/engine");
            const auto stats = engine_->newQObject(owner.get()).property("unitScopeStats");
            trace.append(QVariantMap{{"stage", "scope-method"},
                                     {"stats", stats.toVariant()},
                                     {"text", owner->property("unitResetText")}});
            check.require(owner->property("unitResetText").toString() == "Reset unavailable" &&
                              stats.property("calls").toInt() > 0 &&
                              stats.property("receiver").toBool(),
                          "native scope member wins and receives its real QObject base");
            check.require(
                stats.property("argument").toBool() &&
                    values.property("state").property("finite").toInt() == 0,
                "the actual scope receives the Date value without calling context isFinite");
            check.require(scopeWarnings.isEmpty() && !engine_->hasError(),
                          "the supported scope member adds no unrelated QML error");
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        auto result = check.result();
        result.insert("context_lookup_trace", trace);
        result.insert("context_lookup_mode", retirementCharacterization
                                                 ? "external-retirement-characterization"
                                                 : "live");
        result.insert("retirement_qualification",
                      retirementCharacterization ? "characterization only; consult actual "
                                                   "terminal outcome, never expected-crash success"
                                                 : "not exercised here; separate external "
                                                   "characterization remains FAILED/UNQUALIFIED");
        return result;
    }
    Q_INVOKABLE QVariantMap contextStorageLifetime(QObject* applicationInfo,
                                                   const QString& scenario) const {
        UsageChecks check;
        QVariantList trace;
        try {
            prerequisite(
                applicationInfo && qjsEngine(applicationInfo) == engine_ && !engine_->hasError(),
                "the actual imported singleton and proof engine are identical and clean");
            prerequisite(e11_test_inputs::phase("EDI_E11_USAGE_ACCOUNT_PHASE") == e11_usage_phase::phase(),
                         "the storage fixture uses its explicit actual selected usage phase");
            const QStringList admitted{"scalar-known-retired",   "scalar-found-undefined",
                                       "scalar-absent-global",   "id-precedence",
                                       "scalar-reentry-replace", "list-replace",
                                       "list-negative-index",    "list-at-end",
                                       "list-maximum-index",     "list-shrink",
                                       "list-type-change",       "list-type-change-pending",
                                       "list-owner-destroyed"};
            prerequisite(admitted.contains(scenario), "unknown context-storage scenario refuses");
            UsageContextResult recorder;
            UsageContextSwitch switcher;
            QJSEngine::setObjectOwnership(&recorder, QJSEngine::CppOwnership);
            QJSEngine::setObjectOwnership(&switcher, QJSEngine::CppOwnership);
            auto context = std::make_unique<QQmlContext>(engine_->rootContext());
            QPointer<QQmlContext> publicOwner(context.get());
            const auto originalData = QQmlContextData::get(context.get());
            prerequisite(originalData && originalData->publicContext() == context.get(),
                         "the retained original data names the actual live public owner");
            const bool listCase = scenario.startsWith("list-");
            const bool reentry = scenario.startsWith("scalar-reentry-");
            QObject first, second, replacement;
            context->setContextProperty("paddingSlot", 91);
            if (listCase)
                context->setContextProperty("columns",
                                            QVariant::fromValue(QList<QObject*>{&first, &second}));
            else if (scenario != "scalar-absent-global")
                context->setContextProperty("columns", 37);
            if (reentry) context->setContextObject(&switcher);
            const auto offered = context->contextProperty("columns");
            prerequisite(
                listCase ? offered.metaType() == QMetaType::fromType<QList<QObject*>>()
                : scenario == "scalar-absent-global" ? !offered.isValid()
                                                     : offered.toInt() == 37,
                "the original public external slot contains its exact offered live value");
            if (reentry)
                prerequisite(context->contextProperty("equalColumns").toBool(),
                             "the real context object's original equal-columns getter is live");
            // A scoped global sentinel arms no-fallback without changing any builtin.
            auto global = engine_->globalObject();
            prerequisite(!global.hasOwnProperty("columns"),
                         "the owned columns sentinel requires an originally absent global name");
            auto sentinel = engine_->newObject();
            sentinel.setProperty("tag", "forbidden-global-fallback");
            global.setProperty("columns", sentinel);
            const auto restoreGlobal = qScopeGuard([&] { global.deleteProperty("columns"); });
            QQmlComponent component(engine_);
            const QByteArray id = scenario == "id-precedence" ? "columns" : "storageHost";
            component.setData(
                "import QtQml\nimport edi.app\nQtObject { id: " + id +
                    "; required property var proof; property bool recordDestruction: false;"
                    "property var fittedWidths: []; " +
                    (reentry ? QByteArray() : QByteArray("property bool equalColumns: true; ")) +
                    "property var captureColumns: function() { return "
                    "ApplicationInfo.tableColumnWidths(); }"
                    "Component.onDestruction: if (recordDestruction) "
                    "proof.recordResult(ApplicationInfo.tableColumnWidths());"
                    "}",
                QUrl("file:///e11-context-storage-lifetime.qml"));
            QSignalSpy warnings(engine_, &QQmlEngine::warnings);
            prerequisite(warnings.isValid(), "context-storage warnings have an actual observer");
            std::unique_ptr<QObject> owner(component.createWithInitialProperties(
                {{"proof", QVariant::fromValue(engine_->newQObject(&recorder))}}, context.get()));
            if (!owner) {
                QStringList errors;
                for (const auto& error : component.errors()) errors.append(error.toString());
                throw std::runtime_error(errors.join('\n').toStdString());
            }
            auto scriptOwner = engine_->newQObject(owner.get());
            const auto capture = scriptOwner.property("captureColumns");
            prerequisite(capture.isCallable(), "the real QML creation-scope callable exists");
            const auto live = capture.callWithInstance(scriptOwner);
            if (scenario == "id-precedence") {
                check.require(
                    live.toQObject() == owner.get(),
                    "the declared QML id wins over a same-name external slot and global sentinel");
            } else if (scenario == "scalar-absent-global") {
                check.require(live.strictlyEquals(sentinel),
                              "a genuinely absent context name still uses the original real "
                              "global fallback");
            } else if (!listCase) {
                const bool positive = live.isNumber() && live.toInt() == 37;
                check.require(positive,
                              "the actual native resolver returns the original live scalar before "
                              "any negative");
                prerequisite(positive,
                             "the scalar negative requires its genuine live positive first");
            }
            retainUsageContextAdmission(trace,
                                        {{"stage", "storage-live-positive"},
                                         {"scenario", scenario},
                                         {"public_owner_alive", !publicOwner.isNull()},
                                         {"live_kind", usageValueKind(live)},
                                         {"global_sentinel", live.strictlyEquals(sentinel)}});
            if (!listCase && scenario != "id-precedence" && scenario != "scalar-absent-global") {
                if (scenario == "scalar-known-retired") {
                    prerequisite(
                        owner->setProperty("recordDestruction", true),
                        "actual destruction will call the existing public native procedure");
                    context.reset();
                    check.require(
                        originalData->publicContext() == nullptr,
                        "real public-owner retirement leaves no replacement public context");
                    check.require(publicOwner.isNull(),
                                  "the original public creation context really died");
                    QPointer<QObject> object(owner.get());
                    owner.reset();
                    check.require(originalData->publicContext() == nullptr,
                                  "the actual destruction lookup does not recreate its retired "
                                  "public owner");
                    trace.append(QVariantMap{{"scenario", scenario},
                                             {"calls", recorder.calls},
                                             {"undefined", recorder.value.isUndefined()},
                                             {"global", recorder.value.strictlyEquals(sentinel)}});
                    check.require(object.isNull() && recorder.calls == 1 &&
                                      recorder.value.isUndefined() &&
                                      !recorder.value.strictlyEquals(sentinel),
                                  "a genuine destruction call reaches found-retired storage as "
                                  "undefined without global fallback or recreation");
                } else {
                    if (scenario == "scalar-found-undefined")
                        context->setContextProperty(
                            "columns", QVariant::fromValue(QJSValue(QJSValue::UndefinedValue)));
                    else if (scenario == "scalar-reentry-replace")
                        switcher.effect = [&] { context->setContextProperty("columns", 73); };
                    const int reads = switcher.reads;
                    const auto current = capture.callWithInstance(scriptOwner);
                    trace.append(QVariantMap{{"scenario", scenario},
                                             {"undefined", current.isUndefined()},
                                             {"value", current.isNumber() ? current.toInt() : -1},
                                             {"getter_reads", switcher.reads - reads},
                                             {"global", current.strictlyEquals(sentinel)}});
                    check.require(!current.strictlyEquals(sentinel),
                                  "a selected external name never borrows the armed global value");
                    if (scenario == "scalar-reentry-replace")
                        check.require(
                            current.isNumber() && current.toInt() == 73 && switcher.reads > reads,
                            "ordinary getter reentry exposes the current replacement rather than "
                            "a cached scalar");
                    else
                        check.require(
                            current.isUndefined(),
                            "a found undefined known slot remains undefined without fallback");
                }
            }
            if (listCase) {
                // Extract THAT actual returned native wrapper, never a copied callback
                // implementation.
                const auto* wrapper = QJSValuePrivate::asManagedType<QV4::QmlListWrapper>(&live);
                prerequisite(
                    wrapper,
                    "the existing native public procedure returned its actual QmlListWrapper");
                auto callbacks = *wrapper->d()->property();
                prerequisite(callbacks.count && callbacks.at,
                             "the actual native wrapper offers count and at callback entrances");
                const auto liveCount = callbacks.count(&callbacks);
                retainUsageContextAdmission(trace, {{"stage", "storage-list-count"},
                                                    {"scenario", scenario},
                                                    {"count", liveCount}});
                prerequisite(liveCount == 2,
                             "the actual count must admit the initial live indices");
                const bool positive = callbacks.at(&callbacks, 0) == &first &&
                                      callbacks.at(&callbacks, 1) == &second;
                retainUsageContextAdmission(trace, {{"stage", "storage-list-positive"},
                                                    {"scenario", scenario},
                                                    {"current_values_match", positive}});
                check.require(positive,
                              "the real native list callbacks return their original live owner "
                              "values before every negative");
                prerequisite(positive,
                             "list negatives require the real wrapper and live callbacks first");
                engine_->collectGarbage();
                const bool postGcPositive = callbacks.count(&callbacks) == 2 &&
                                            callbacks.at(&callbacks, 0) == &first &&
                                            callbacks.at(&callbacks, 1) == &second &&
                                            originalData->publicContext() == context.get();
                check.require(postGcPositive,
                              "the actual retained wrapper and descriptor preserve live "
                              "identities across GC");
                prerequisite(postGcPositive,
                             "the adverse list state requires the genuine post-GC positive first");
                if (scenario == "list-replace" || scenario == "list-shrink") {
                    context->setContextProperty(
                        "columns", QVariant::fromValue(QList<QObject*>{&replacement}));
                    check.require(callbacks.count(&callbacks) == 1 &&
                                      callbacks.at(&callbacks, 0) == &replacement,
                                  "the held wrapper rereads current replacement storage rather "
                                  "than snapshotting its list");
                    if (scenario == "list-shrink")
                        check.require(callbacks.at(&callbacks, 1) == nullptr,
                                      "an earlier count cannot authorize a stale index after "
                                      "legal owner list shrink");
                } else if (scenario == "list-type-change") {
                    context->setContextProperty("columns", QStringLiteral("not-a-QObject-list"));
                    check.require(
                        callbacks.count(&callbacks) == 0 && callbacks.at(&callbacks, 0) == nullptr,
                        "a current non-list slot refuses count and at rather than using cached "
                        "list storage");
                    context->setContextProperty(
                        "columns", QVariant::fromValue(QList<QObject*>{&replacement}));
                    check.require(callbacks.count(&callbacks) == 1 &&
                                      callbacks.at(&callbacks, 0) == &replacement,
                                  "returning to a live typed list restores the same wrapper's "
                                  "current values");
                } else if (scenario == "list-type-change-pending") {
                    context->setContextProperty("columns", QStringLiteral("not-a-QObject-list"));
                    const auto firstError =
                        engine_->newErrorObject(QJSValue::TypeError, "owned first context error");
                    engine_->throwError(firstError);
                    prerequisite(
                        engine_->hasError(),
                        "the first same-engine exception is genuinely pending before callbacks");
                    const auto count = callbacks.count(&callbacks);
                    const auto item = callbacks.at(&callbacks, 0);
                    const bool pending = engine_->hasError();
                    const auto caught = engine_->catchError();
                    check.require(count == 0 && item == nullptr && pending &&
                                      caught.strictlyEquals(firstError),
                                  "actual unavailable-list callbacks retain the exact "
                                  "already-pending first exception");
                } else if (scenario == "list-owner-destroyed") {
                    context.reset();
                    check.require(
                        originalData->publicContext() == nullptr,
                        "real public-owner retirement leaves no replacement public context");
                    check.require(publicOwner.isNull(),
                                  "the list's original public storage owner really died");
                    check.require(
                        callbacks.count(&callbacks) == 0 && callbacks.at(&callbacks, 0) == nullptr,
                        "actual held callbacks safely refuse a dead original owner even when raw "
                        "callback storage remains");
                    check.require(
                        originalData->publicContext() == nullptr,
                        "actual dead-owner list callbacks do not recreate the public context");
                } else {
                    const qsizetype index = scenario == "list-negative-index" ? -1
                                            : scenario == "list-at-end"
                                                ? 2
                                                : (std::numeric_limits<qsizetype>::max)();
                    check.require(callbacks.at(&callbacks, index) == nullptr,
                                  "the actual live at callback refuses negative, end and maximum "
                                  "out-of-range indices");
                }
                trace.append(QVariantMap{{"scenario", scenario},
                                         {"public_owner_alive", !publicOwner.isNull()}});
            }
            check.require(warnings.isEmpty() && !engine_->hasError(),
                          "the admitted context lifetime/refusal controls add no unrelated QML or "
                          "engine error");
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        auto result = check.result();
        result.insert("context_storage_trace", trace);
        return result;
    }

    Q_INVOKABLE QVariantMap contextConversionLifetime(QObject* applicationInfo,
                                                      const QString& scenario) const {
        UsageChecks check;
        QVariantList trace;
        try {
            prerequisite(
                applicationInfo && qjsEngine(applicationInfo) == engine_ && !engine_->hasError(),
                "conversion uses the actual imported singleton and clean proof engine");
            prerequisite(e11_test_inputs::phase("EDI_E11_USAGE_ACCOUNT_PHASE") == e11_usage_phase::phase(),
                         "conversion uses the explicit actual selected usage phase");
            prerequisite(scenario == "default-conversion" || scenario == "native-reference-gc",
                         "unknown Edi conversion scenario refuses");
            QObject first, second, replacement;
            auto context = std::make_unique<QQmlContext>(engine_->rootContext());
            QPointer<QQmlContext> publicOwner(context.get());
            const auto originalData = QQmlContextData::get(context.get());
            prerequisite(originalData && originalData->publicContext() == context.get(),
                         "original data/public owner identity is captured while live");
            context->setContextProperty("paddingSlot", 91);
            context->setContextProperty("columns",
                                        QVariant::fromValue(QList<QObject*>{&first, &second}));
            prerequisite(context->contextProperty("columns").metaType() ==
                             QMetaType::fromType<QList<QObject*>>(),
                         "the offered external value is the real typed QObject list");
            QQmlComponent component(engine_);
            component.setData(
                "import QtQml\nimport edi.app\nQtObject { property var fittedWidths: [];"
                "property bool equalColumns: true;"
                "property var captureColumns: function() { return "
                "ApplicationInfo.tableColumnWidths(); } }",
                QUrl("file:///e11-context-conversion-lifetime.qml"));
            QSignalSpy warnings(engine_, &QQmlEngine::warnings);
            prerequisite(warnings.isValid(), "actual conversion warnings are observed");
            std::unique_ptr<QObject> owner(component.create(context.get()));
            if (!owner) {
                QStringList errors;
                for (const auto& error : component.errors()) errors.append(error.toString());
                throw std::runtime_error(errors.join('\n').toStdString());
            }
            const auto scriptOwner = engine_->newQObject(owner.get());
            const auto capture = scriptOwner.property("captureColumns");
            prerequisite(capture.isCallable(), "the actual QML creation-scope callable exists");
            auto live = capture.callWithInstance(scriptOwner);
            auto* wrapper = QJSValuePrivate::asManagedType<QV4::QmlListWrapper>(&live);
            prerequisite(wrapper && wrapper->d()->object(),
                         "the actual Edi bridge returned a wrapper with a live owner");
            QObject* const nativeOwner = wrapper->d()->property()->object;
            prerequisite(nativeOwner && wrapper->d()->object() == nativeOwner,
                         "the actual wrapper guard and callback owner match");
            QPointer<QObject> nativeOwnerGuard(nativeOwner);
            auto converted = live.toVariant();
            prerequisite(
                converted.metaType() == QMetaType::fromType<QQmlListReference>(),
                "Qt default conversion of the live bridge wrapper is a native list reference");
            auto defaultReference = converted.value<QQmlListReference>();
            const bool liveDefault =
                defaultReference.isValid() && defaultReference.object() == nativeOwner &&
                defaultReference.count() == 2 && defaultReference.at(0) == &first &&
                defaultReference.at(1) == &second;
            check.require(liveDefault,
                          "default conversion retains exact live owner and element identities");
            prerequisite(liveDefault,
                         "conversion negatives require the genuine live positive first");
            retainUsageContextAdmission(
                trace, {{"stage", "conversion-live-positive"},
                        {"scenario", scenario},
                        {"public_owner_same", originalData->publicContext() == context.get()},
                        {"default_type", QString::fromLatin1(converted.typeName())}});
            if (scenario == "native-reference-gc") {
                auto direct = wrapper->toListReference();
                QQmlListReference copied(direct);
                prerequisite(copied == direct && copied.isValid() &&
                                 copied.object() == nativeOwner && copied.count() == 2 &&
                                 copied.at(0) == &first && copied.at(1) == &second,
                             "the copied direct bridge reference is genuine before GC");
                QV4::WeakValue weak;
                weak.set(QJSValuePrivate::engine(&live), QJSValuePrivate::asReturnedValue(&live));
                prerequisite(!weak.isUndefined(),
                             "the weak witness names the actual live wrapper");
                direct = QQmlListReference();
                defaultReference = QQmlListReference();
                converted = QVariant();
                live = QJSValue();
                wrapper = nullptr;
                engine_->collectGarbage();
                retainUsageContextAdmission(trace,
                                            {{"stage", "conversion-wrapper-gc"},
                                             {"wrapper_collected", weak.isUndefined()},
                                             {"native_owner_alive", !nativeOwnerGuard.isNull()}});
                check.require(weak.isUndefined(),
                              "dropping JS roots really permits wrapper collection");
                prerequisite(weak.isUndefined(),
                             "post-GC checks require actual wrapper collection");
                const bool survived = nativeOwnerGuard && copied.isValid() &&
                                      copied.object() == nativeOwnerGuard.data() &&
                                      copied.count() == 2 && copied.at(0) == &first &&
                                      copied.at(1) == &second;
                check.require(survived,
                              "the genuine copied native reference survives wrapper GC with exact "
                              "live values");
                prerequisite(survived, "owner-death checks require a true live post-GC reference");
                context->setContextProperty("columns",
                                            QVariant::fromValue(QList<QObject*>{&replacement}));
                check.require(copied.count() == 1 && copied.at(0) == &replacement,
                              "the post-GC native reference reads current replacement storage, "
                              "not a snapshot");
                context.reset();
                check.require(publicOwner.isNull() && originalData->publicContext() == nullptr,
                              "original owner death is observed without a lazy getter");
                engine_->collectGarbage();
                check.require(copied.count() == 0 && copied.at(0) == nullptr &&
                                  originalData->publicContext() == nullptr,
                              "the native reference is empty/unavailable after owner death and GC "
                              "without context recreation");
            } else {
                engine_->collectGarbage();
                const bool survived = defaultReference.count() == 2 &&
                                      defaultReference.at(0) == &first &&
                                      defaultReference.at(1) == &second &&
                                      originalData->publicContext() == context.get();
                check.require(
                    survived,
                    "actual default conversion stays live across GC while its owner exists");
                prerequisite(survived,
                             "post-death conversion requires the true post-GC live positive");
                context.reset();
                check.require(
                    publicOwner.isNull() && originalData->publicContext() == nullptr,
                    "original public owner is actually absent before default conversion");
                engine_->collectGarbage();
                const bool guardAlive = wrapper->d()->object() != nullptr;
                const auto after = live.toVariant();
                bool unavailable = false;
                if (guardAlive) {
                    prerequisite(
                        after.metaType() == QMetaType::fromType<QQmlListReference>(),
                        "the witnessed live guard selects Qt native-reference conversion");
                    const auto reference = after.value<QQmlListReference>();
                    unavailable = reference.count() == 0 && reference.at(0) == nullptr;
                } else {
                    prerequisite(after.metaType() == QMetaType::fromType<QObjectList>(),
                                 "the witnessed absent guard selects Qt QObjectList conversion");
                    unavailable = after.value<QObjectList>().isEmpty();
                }
                retainUsageContextAdmission(
                    trace, {{"stage", "conversion-after-owner-death"},
                            {"wrapper_guard_alive", guardAlive},
                            {"default_type", QString::fromLatin1(after.typeName())},
                            {"unavailable", unavailable},
                            {"public_owner_absent", originalData->publicContext() == nullptr}});
                check.require(unavailable && originalData->publicContext() == nullptr,
                              "default conversion is empty/unavailable after owner death and "
                              "never recreates public storage");
            }
            check.require(warnings.isEmpty() && !engine_->hasError(),
                          "actual Edi default/native conversion and GC add no unrelated error");
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        auto result = check.result();
        result.insert("context_conversion_trace", trace);
        return result;
    }

    Q_INVOKABLE QVariantMap callLookupOrder(QObject* applicationInfo) const {
        UsageChecks check;
        QVariantList trace;
        try {
            const auto mathPhase = e11_usage_phase::phase();
            prerequisite((mathPhase == "native" || mathPhase == "original") &&
                             e11_test_inputs::phase("EDI_E11_USAGE_ACCOUNT_PHASE") == mathPhase,
                         "Math characterization requires the explicit selected source phase");
            // These aliases expose lookup/call effects; they do not implement the relation.
            const auto make = engine_->evaluate(QStringLiteral(R"JS(
(function(kind, mode, nativeMath, context) {
    const s={events:[],receiver:true,argument:true,effects:0,reentered:0,
             sentinel:{tag:'math-capture'},armed:false,paused:false,context:context};
    const math=Object.create(nativeMath), next=Object.create(nativeMath);
    const member=kind==='reset' ? 'ceil' : 'floor';
    const expected=kind==='reset' ? 1 : 14000.5;
    function replacement(value) {
        'use strict'; s.events.push('replacement.call');
        s.receiver=s.receiver && this===math;
        s.argument=s.argument && value===expected;return 0;
    }
    next[member]=replacement;
    function captured(value) {
        'use strict'; s.events.push(member+'.call');
        s.receiver=s.receiver && this===math;
        s.argument=s.argument && value===expected;
        if(mode==='call-throw')throw s.sentinel;
        return nativeMath[member](value);
    }
    Object.defineProperty(math,member,{configurable:true,get:function(){
        if(!s.armed || s.paused)return nativeMath[member];
        s.events.push(member+'.get');
        if(mode==='getter-throw')throw s.sentinel;
        return captured;
    }});
    function argumentEffect() {
        ++s.effects;
        if(mode==='argument-throw')throw s.sentinel;
        if(mode==='replace-method')
            Object.defineProperty(math,member,{configurable:true,value:replacement});
        if(mode==='replace-receiver')context.Math=next;
        if(mode==='reentry') {
            s.events.push('reentry.enter'); s.paused=true;
            try { s.inner=s.reenter(); ++s.reentered; }
            finally {s.paused=false;}
            s.events.push('reentry.exit');
        }
    }
    s.now={valueOf:function(){s.events.push('now');argumentEffect();return 0;}};
    Object.defineProperty(math,'random',{configurable:true,get:function(){
        if(!s.armed || s.paused)return function(){return 0.5;};
        s.events.push('random.get');
        return function(){
            'use strict'; s.events.push('random.call');
            s.receiver=s.receiver && this===math;
            argumentEffect();return 0.5;
        };
    }});
    s.math=math;s.next=next;return s;
})
)JS"));
            prerequisite(make.isCallable(), "test aliases are created in the actual proof engine");
            for (const QString& kind : {QStringLiteral("reset"), QStringLiteral("schedule")}) {
                UsageCallLookupContext object(engine_);
                QJSEngine::setObjectOwnership(&object, QJSEngine::CppOwnership);
                object.setMath(engine_->globalObject().property("Math"));
                QQmlContext context(engine_->rootContext());
                context.setContextObject(&object);
                QSignalSpy warnings(engine_, &QQmlEngine::warnings);
                prerequisite(warnings.isValid(), "math-call warnings are observed");
                auto owner =
                    panel(applicationInfo, &context, "property var unitMathCapture: null;");
                std::unique_ptr<QObject> working;
                QObject* target = owner.get();
                if (kind == "schedule") {
                    QQmlComponent component(engine_);
                    component.setData(
                        "import QtQuick\nimport edi.app\n"
                        "AssistantWorking { assistant: Session.assistant;"
                        "property var unitMathCapture: null; }",
                        QUrl("qrc:/tests/UsageMathActualWorking.qml"));
                    prerequisite(!component.isError(), "actual Working component compiles");
                    working.reset(component.createWithInitialProperties(
                        {{"parent", QVariant::fromValue(owner.host.get())}}, &context));
                    prerequisite(working != nullptr, "actual Working with typed Session exists");
                    auto* item = qobject_cast<QQuickItem*>(working.get());
                    prerequisite(item && item->window() == host_->window() &&
                                     QQmlEngine::contextForObject(item) &&
                                     QQmlEngine::contextForObject(item)->engine() == engine_,
                                 "actual Working uses the same genuine Item/window/engine");
                    target = working.get();
                }
                for (const auto& mode :
                     {"ordinary", "replace-method", "replace-receiver", "getter-throw",
                      "argument-throw", "call-throw", "reentry"}) {
                    const auto state = make.call(
                        {QJSValue(kind), QJSValue(QString::fromLatin1(mode)),
                         engine_->globalObject().property("Math"), engine_->newQObject(&object)});
                    prerequisite(state.isObject() && !engine_->hasError(),
                                 "armed math fixture exists without pending error");
                    prerequisite(
                        target->setProperty("unitMathCapture", QVariant::fromValue(state)),
                        "only the test-owned carrier is assigned");
                    object.setMath(state.property("math"));
                    const QString call = kind == "reset"
                                             ? e11_usage_phase::reset("60", "s.now")
                                             : QStringLiteral("scheduleVariantChange()");
                    const QString nested =
                        kind == "reset"
                            ? "return " + e11_usage_phase::reset("120", "0")
                            : QStringLiteral("scheduleVariantChange();return 'scheduled'");
                    const auto completed =
                        evaluate(target,
                                 "(function(){const s=unitMathCapture;"
                                 "s.reenter=function(){" +
                                     nested +
                                     ";};s.armed=true;"
                                     "let result,caught,thrown=false,same=false;try{result=" +
                                     call +
                                     ";}catch(error){caught=error;thrown=true;same=error===s.sentinel;}"
                                     "finally{s.armed=false;}s.caught=caught;s.facts={events:s.events,"
                                     "receiver:s.receiver,argument:s.argument,effects:s.effects,"
                                     "reentered:s.reentered,inner:s.inner,thrown:thrown,same:same,"
                                     "result:result,replaced:Math===s.next};return true;})()");
                    const auto facts = state.property("facts").toVariant().toMap();
                    trace.append(QVariantMap{
                        {"caller", kind}, {"mode", QString::fromLatin1(mode)}, {"facts", facts}});
                    check.require(
                        completed.metaType() == QMetaType::fromType<bool>() && completed.toBool(),
                        "actual caller observation completes");
                    QStringList expected;
                    const bool getterThrow = QByteArray(mode) == "getter-throw";
                    const bool argumentThrow = QByteArray(mode) == "argument-throw";
                    const bool callThrow = QByteArray(mode) == "call-throw";
                    const bool reentry = QByteArray(mode) == "reentry";
                    if (kind == "reset")
                        expected << "now";
                    else
                        expected << "random.get" << "random.call";
                    if (reentry) expected << "reentry.enter" << "reentry.exit";
                    if (!argumentThrow) {
                        if (QByteArray(mode) == "replace-method")
                            expected << "replacement.call";
                        else {
                            expected << (kind == "reset" ? "ceil.get" : "floor.get");
                            if (!getterThrow)
                                expected << (kind == "reset" ? "ceil.call" : "floor.call");
                        }
                    }
                    QStringList actual;
                    for (const auto& event : facts.value("events").toList())
                        actual.append(event.toString());
                    const auto label = kind + "/" + QString::fromLatin1(mode);
                    check.require(
                        actual == expected,
                        label +
                            ": original dot-call getter follows arguments on captured receiver");
                    check.require(
                        facts.value("effects").toInt() == 1,
                        label + ": original member getter cannot suppress prior argument effects");
                    const bool throws = getterThrow || argumentThrow || callThrow;
                    if (getterThrow && mathPhase == "original") {
                        // Qt 6.11.2's legacy noncallable formatter consumes the pending
                        // plain-object sentinel; this is not native first-error safety.
                        const auto caught = state.property("caught");
                        const bool ownMessage = caught.isError() && caught.hasOwnProperty("message");
                        const auto message = ownMessage ? caught.property("message") : QJSValue();
                        const auto descriptor =
                            QStringLiteral("Property '%1' of object [object Object] is not a function")
                                .arg(kind == "reset" ? QStringLiteral("ceil")
                                                     : QStringLiteral("floor"));
                        check.require(facts.value("thrown").toBool() &&
                                          !facts.value("same").toBool() && caught.isError() &&
                                          caught.errorType() == QJSValue::TypeError && ownMessage &&
                                          message.isString() && message.toString() == descriptor,
                                      label + ": original getter has the exact legacy Qt TypeError");
                    } else {
                        check.require(facts.value("thrown").toBool() == throws &&
                                          facts.value("same").toBool() == throws,
                                      label + ": exact same-engine sentinel is preserved");
                    }
                    check.require(
                        facts.value("receiver").toBool() && facts.value("argument").toBool(),
                        label + ": original receiver and evaluated argument are exact");
                    check.require(facts.value("replaced").toBool() ==
                                      (QByteArray(mode) == "replace-receiver"),
                                  label + ": replacement changes the actual context Math name");
                    check.require(facts.value("reentered").toInt() == (reentry ? 1 : 0),
                                  label + ": genuine synchronous reentry completes once");
                    if (kind == "reset" && !throws)
                        check.require(
                            facts.value("result").toString() ==
                                (QByteArray(mode) == "replace-method" ? "Reset time reached"
                                                                      : "Resets in 1 min"),
                            label + ": original literal reflects actual selected callee");
                    if (reentry)
                        check.require(facts.value("inner").toString() ==
                                          (kind == "reset" ? "Resets in 2 min" : "scheduled"),
                                      label + ": nested real caller retains its own result");
                    object.setMath(engine_->globalObject().property("Math"));
                }
                if (mathPhase == "native") {
                    const auto reference = make.call(
                        {QJSValue(kind), QJSValue(QStringLiteral("getter-throw")),
                         engine_->globalObject().property("Math"), engine_->newQObject(&object)});
                    prerequisite(reference.isObject() && !engine_->hasError(),
                                 "legacy Math reference has a clean actual Qt engine");
                    prerequisite(
                        target->setProperty("unitMathCapture", QVariant::fromValue(reference)),
                        "legacy Math reference uses only the test-owned carrier");
                    object.setMath(reference.property("math"));
                    const auto member = kind == "reset" ? QStringLiteral("ceil")
                                                        : QStringLiteral("floor");
                    // These literal legacy calls characterize the pinned Qt formatter.
                    const auto thrown = evaluate(
                        target, "(function(){const s=unitMathCapture;s.armed=true;"
                                "try{Math." + member + "(1);}catch(error){s.caught=error;"
                                "s.same=error===s.sentinel;return true;}"
                                "finally{s.armed=false;}return false;})()");
                    const auto caught = reference.property("caught");
                    const bool ownMessage = caught.isError() && caught.hasOwnProperty("message");
                    const auto message = ownMessage ? caught.property("message") : QJSValue();
                    const auto descriptor =
                        QStringLiteral("Property '%1' of object [object Object] is not a function")
                            .arg(member);
                    check.require(
                        thrown.metaType() == QMetaType::fromType<bool>() && thrown.toBool() &&
                            !reference.property("same").toBool() && caught.isError() &&
                            caught.errorType() == QJSValue::TypeError && ownMessage &&
                            message.isString() && message.toString() == descriptor,
                        kind + ": literal legacy getter has the exact pinned Qt TypeError");
                    trace.append(QVariantMap{{"caller", kind}, {"mode", "legacy-getter-reference"},
                                             {"caught", usageValueKind(caught)}});
                    object.setMath(engine_->globalObject().property("Math"));
                }
                check.require(warnings.isEmpty() && !engine_->hasError(),
                              kind + ": caught sentinels add no unrelated warning/pending error");
            }
            // Original unqualified isFinite lookup is after its Date/getTime argument.
            const auto makeName = engine_->evaluate(QStringLiteral(R"JS(
(function(mode, nativeDate, nativeFinite, context) {
    const s={events:[],receiver:true,argument:true,effects:0,reentered:0,
             sentinel:{tag:'name-lookup'},paused:false};
    function replacement(value) {
        'use strict';s.events.push('finite.replacement');
        s.receiver=s.receiver && this===context;s.argument=s.argument && value===60000;
        return false;
    }
    s.first=function(value) {
        'use strict';if(s.paused)return nativeFinite(value);
        s.events.push('finite.first');s.receiver=s.receiver && this===context;
        s.argument=s.argument && value===60000;
        if(mode==='call-throw')throw s.sentinel;
        return true;
    };
    s.Date=function(value) {
        if(s.paused)return Reflect.construct(nativeDate,[value]);
        s.argument=s.argument && value===60000 && new.target===s.Date;
        const date={getTime:function(){
            'use strict';s.events.push('date.argument');++s.effects;
            s.receiver=s.receiver && this===date;
            if(mode==='argument-throw')throw s.sentinel;
            if(mode==='replace-name')context.isFinite=replacement;
            if(mode==='reentry') {
                s.events.push('reentry.enter');s.paused=true;
                try{s.inner=s.reenter();++s.reentered;}
                finally{s.paused=false;}
                s.events.push('reentry.exit');
            }
            return value;
        }};
        return date;
    };
    return s;
})
)JS"));
            prerequisite(makeName.isCallable(), "actual-engine name argument fixture exists");
            UsageCallLookupContext names(engine_);
            QJSEngine::setObjectOwnership(&names, QJSEngine::CppOwnership);
            QQmlContext nameContext(engine_->rootContext());
            nameContext.setContextObject(&names);
            QSignalSpy nameWarnings(engine_, &QQmlEngine::warnings);
            prerequisite(nameWarnings.isValid(), "actual name-call warnings are observed");
            auto nameOwner =
                panel(applicationInfo, &nameContext, "property var unitNameCapture: null;");
            for (const auto& mode :
                 {"ordinary", "replace-name", "argument-throw", "call-throw", "reentry"}) {
                const auto state = makeName.call(
                    {QJSValue(QString::fromLatin1(mode)), engine_->globalObject().property("Date"),
                     engine_->globalObject().property("isFinite"), engine_->newQObject(&names)});
                prerequisite(state.isObject() && !engine_->hasError(),
                             "same-engine name fixture exists without pending error");
                prerequisite(nameOwner->setProperty("unitNameCapture", QVariant::fromValue(state)),
                             "only the test-owned name carrier is assigned");
                names.setDate(state.property("Date"));
                names.setFinite(state.property("first"));
                const auto completed = evaluate(
                    nameOwner.get(),
                    "(function(){const s=unitNameCapture;s.reenter=function(){return " +
                        e11_usage_phase::reset("120", "0") +
                        ";};let result,thrown=false,same=false;try{result=" +
                        e11_usage_phase::reset("60", "0") +
                        ";}catch(error){thrown=true;same=error===s.sentinel;}"
                        "s.facts={events:s.events,receiver:s.receiver,argument:s.argument,"
                        "effects:s.effects,reentered:s.reentered,inner:s.inner,result:result,"
                        "thrown:thrown,same:same};return true;})()");
                const auto facts = state.property("facts").toVariant().toMap();
                trace.append(QVariantMap{
                    {"caller", "name"}, {"mode", QString::fromLatin1(mode)}, {"facts", facts}});
                check.require(
                    completed.metaType() == QMetaType::fromType<bool>() && completed.toBool(),
                    "actual unqualified function-name call completes observation");
                QStringList expected{"date.argument"};
                const bool reentry = QByteArray(mode) == "reentry";
                const bool argumentThrow = QByteArray(mode) == "argument-throw";
                const bool throws = argumentThrow || QByteArray(mode) == "call-throw";
                if (reentry) expected << "reentry.enter" << "reentry.exit";
                if (!argumentThrow)
                    expected << (QByteArray(mode) == "replace-name" ? "finite.replacement"
                                                                    : "finite.first");
                QStringList actual;
                for (const auto& event : facts.value("events").toList())
                    actual.append(event.toString());
                const auto label = "name/" + QString::fromLatin1(mode);
                check.require(actual == expected && facts.value("effects").toInt() == 1,
                              label + ": original name lookup honors the argument's replacement");
                check.require(facts.value("receiver").toBool() && facts.value("argument").toBool(),
                              label + ": actual context-object and Date receivers are preserved");
                check.require(facts.value("thrown").toBool() == throws &&
                                  facts.value("same").toBool() == throws,
                              label + ": exact sentinel survives argument and callable throws");
                check.require(facts.value("reentered").toInt() == (reentry ? 1 : 0),
                              label + ": nested real formatter completes exactly once");
                if (!throws)
                    check.require(
                        facts.value("result").toString() == (QByteArray(mode) == "replace-name"
                                                                 ? "Reset unavailable"
                                                                 : "Resets in 1 min"),
                        label + ": original literal follows the selected named function");
                if (reentry)
                    check.require(
                        facts.value("inner").toString() == "Resets in 2 min",
                        label + ": nested call retains its independent original literal");
                names.setDate(engine_->globalObject().property("Date"));
                names.setFinite(engine_->globalObject().property("isFinite"));
            }
            check.require(nameWarnings.isEmpty() && !engine_->hasError(),
                          "caught named-call sentinels add no unrelated warning or pending error");
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        auto result = check.result();
        result.insert("math_capture_trace", trace);
        return result;
    }
};

static void registerUsageAccountProof() {
    qmlRegisterType<UsageScopeItem>("UsageAccountAcceptance", 1, 0, "UsageScopeItem");
    qmlRegisterSingletonType<UsageAccountProof>(
        "UsageAccountAcceptance", 1, 0, "UsageAccountProof",
        [](QQmlEngine* engine, QJSEngine*) -> QObject* { return new UsageAccountProof(engine); });
}
Q_COREAPP_STARTUP_FUNCTION(registerUsageAccountProof)
#include "test_e11_t5_usage_account.moc"
