// SPDX-License-Identifier: BSD-3-Clause
// First finite usage layer: real Panel pure relations; canonical/UI/timer gates remain separate.
#include <QtCore/qtestsupport_core.h>
#include <QtQml/qqml.h>
#include <QtTest/qtestcase.h>

#include <QColor>
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QJSValue>
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
    Q_PROPERTY(QJSValue Date READ date WRITE setDate NOTIFY dateChanged)
    Q_PROPERTY(QJSValue isFinite READ finite WRITE setFinite NOTIFY finiteChanged)
    QJSValue math_, date_, finite_;

   public:
    explicit UsageCallLookupContext(QJSEngine* engine)
        : math_(engine->globalObject().property("Math")),
          date_(engine->globalObject().property("Date")),
          finite_(engine->globalObject().property("isFinite")) {}
    QJSValue date() const { return date_; }
    QJSValue finite() const { return finite_; }
    void setDate(const QJSValue& value) { date_ = value; }
    void setFinite(const QJSValue& value) { finite_ = value; }
    QJSValue math() const { return math_; }
    void setMath(const QJSValue& value) { math_ = value; }
   signals:
    void mathChanged();
    void dateChanged();
    void finiteChanged();
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
        prerequisite(qgetenv("EDI_E11_USAGE_ACCOUNT_PHASE") == e11_usage_phase::phase(),
                     "explicit selected usage phase is mandatory");
        const auto root = qgetenv("EDI_E11_USAGE_ACCOUNT_SOURCE_ROOT");
        prerequisite(!root.isEmpty(), "actual source root is mandatory");
        QFile source(QString::fromUtf8(root) + "/app/qml/Components/AssistantPanel.qml");
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
            auto owner = panel(applicationInfo);
            auto scriptOwner = engine_->newQObject(owner.get());
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
            const auto install = engine_->evaluate(QStringLiteral(R"JS(
(function(owner, mode, thrown) {
    const json = globalThis.JSON;
    const globalDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'JSON');
    const parseDescriptor = Object.getOwnPropertyDescriptor(json, 'parse');
    const stringifyDescriptor = Object.getOwnPropertyDescriptor(json, 'stringify');
    const parse = json.parse, stringify = json.stringify;
    const proof = {events:[], throws:0, parseReceiver:false, stringifyReceiver:false,
                   seenOwner:null, raw:undefined, reentered:0, replacement:null};
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
        get:function() { step('stringify-get'); return stringifyCall; }
    });
    Object.defineProperty(json, 'parse', {
        configurable:true,
        get:function() {
            step('parse-get');
            if (mode === 'replace-json') {
                const replacement = {};
                Object.defineProperty(replacement, 'stringify', {
                    configurable:true,
                    get:function() { step('stringify-get'); return stringifyCall; }
                });
                proof.replacement = replacement;
                globalThis.JSON = replacement;
            }
            return function(value) {
                proof.parseReceiver = this === json;
                step('parse-call');
                return parse.call(this, value);
            };
        }
    });
    proof.restore = function() {
        Object.defineProperty(json, 'parse', parseDescriptor);
        Object.defineProperty(json, 'stringify', stringifyDescriptor);
        Object.defineProperty(globalThis, 'JSON', globalDescriptor);
    };
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
                auto proof = install.call({scriptOwner, QJSValue(mode), thrown});
                prerequisite(proof.isObject() && !engine_->hasError(),
                             "same-engine instrument installed without a pending error");
                const auto restore =
                    qScopeGuard([&] { proof.property("restore").callWithInstance(proof); });
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
                        check.require(engine_->globalObject().property("JSON").strictlyEquals(
                                          proof.property("replacement")),
                                      "the late parse getter replaces global JSON without "
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
            const auto install = engine_->evaluate(QStringLiteral(R"JS(
(function(stage, receiver) {
    const descriptor = Object.getOwnPropertyDescriptor(String.prototype, 'split');
    const original = descriptor.value;
    const proof = {splits:0, maps:0};
    Object.defineProperty(String.prototype, 'split', {
        configurable:descriptor.configurable, enumerable:descriptor.enumerable, writable:descriptor.writable,
        value:function(separator) {
            if (String(this) !== '' || !(separator instanceof RegExp) || separator.source !== '[_ -]+')
                return original.apply(this, arguments);
            ++proof.splits;
            if (stage === 'map') return receiver;
            return {map:function() { ++proof.maps; return receiver; }};
        }
    });
    proof.restore = function() { Object.defineProperty(String.prototype, 'split', descriptor); };
    return proof;
})
)JS"));
            prerequisite(install.isCallable(), "same-engine split receiver control is callable");
            for (const auto& member : {"map", "join"}) {
                for (const auto& value : {"null", "undefined"}) {
                    // A scope guard restores the exact prototype descriptor on all exits.
                    // For a completed lease, restoration precedes Panel teardown.
                    UsagePanelLease owner;
                    auto proof = install.call({QJSValue(QString::fromLatin1(member)),
                                               engine_->evaluate(QString::fromLatin1(value))});
                    prerequisite(proof.isObject() && !engine_->hasError(),
                                 "the original String split receiver fixture installs cleanly");
                    const auto restore =
                        qScopeGuard([&] { proof.property("restore").callWithInstance(proof); });
                    QSignalSpy warnings(engine_, &QQmlEngine::warnings);
                    prerequisite(warnings.isValid(), "actual binding warnings are observed");
                    owner = panel(applicationInfo);
                    QStringList descriptions;
                    QVariantList locations;
                    bool actualPanelLocations = true;
                    for (const auto& notification : warnings)
                        for (const auto& error : notification.at(0).value<QList<QQmlError>>()) {
                            descriptions.append(error.description());
                            locations.append(QVariantMap{{"url", error.url().toString()},
                                                         {"line", error.line()},
                                                         {"column", error.column()}});
                            actualPanelLocations =
                                actualPanelLocations &&
                                error.url().fileName() == "AssistantPanel.qml" && error.line() > 0;
                        }
                    const QString expected =
                        QStringLiteral("TypeError: Cannot read property '%1' of %2")
                            .arg(QString::fromLatin1(member), QString::fromLatin1(value));
                    trace.append(QVariantMap{{"member", QString::fromLatin1(member)},
                                             {"receiver", QString::fromLatin1(value)},
                                             {"descriptions", descriptions},
                                             {"locations", locations},
                                             {"splits", proof.property("splits").toInt()},
                                             {"maps", proof.property("maps").toInt()}});
                    check.require(actualPanelLocations,
                                  "the actual original Panel binding reports its failure");
                    check.require(
                        proof.property("splits").toInt() == 1 &&
                            proof.property("maps").toInt() ==
                                (QString::fromLatin1(member) == "join" ? 1 : 0),
                        "the actual split/map chain reaches its independently armed receiver");
                    check.require(
                        descriptions == QStringList{expected},
                        "CallPropertyLookup retains the first exact read-property TypeError");
                    check.require(!engine_->hasError(),
                                  "the ordinary QML binding reporter consumes the reported error");
                }
            }
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        auto result = check.result();
        result.insert("member_receiver_trace", trace);
        return result;
    }

    Q_INVOKABLE QVariantMap actualContextLookups(QObject* applicationInfo) const {
        UsageChecks check;
        QVariantList trace;
        try {
            const auto make = engine_->evaluate(QStringLiteral(R"JS(
(function(tag, minutes, invalidDate, finiteMode, expectedReceiver) {
    const originalJSON=globalThis.JSON, originalDate=globalThis.Date;
    const originalMath=globalThis.Math, originalArray=globalThis.Array;
    const originalFinite=globalThis.isFinite;
    const state={json:0,jsonReceiver:true,mathReceiver:true,date:0,constructed:0,finite:0,receiver:true,reentered:0,array:0,owner:null};
    const json=Object.create(originalJSON);
    json.stringify=function() { 'use strict'; ++state.json; state.jsonReceiver=state.jsonReceiver&&this===json; return originalJSON.stringify.apply(originalJSON,arguments); };
    json.parse=function(value) {
        'use strict'; state.jsonReceiver=state.jsonReceiver&&this===json;
        const result=originalJSON.parse.apply(originalJSON,arguments);
        if(result && Array.isArray(result.buckets) && typeof result.available==='boolean')
            result.unitContextTag=tag;
        return result;
    };
    function ContextArray() { return originalArray.apply(null,arguments); }
    Object.setPrototypeOf(ContextArray,originalArray);
    ContextArray.prototype=originalArray.prototype;
    ContextArray.from=function() { ++state.array; return originalArray.from.apply(this,arguments); };
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
    math.ceil=function(value){'use strict';state.mathReceiver=state.mathReceiver&&this===math;return value===1 ? minutes : originalMath.ceil(value);};
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
            prerequisite(make.isCallable(), "context aliases delegate to real original builtins");
            for (const bool objectMode : {false, true}) {
                UsageLookupContext object;
                QJSEngine::setObjectOwnership(&object, QJSEngine::CppOwnership);
                auto context = std::make_unique<QQmlContext>(engine_->rootContext());
                if (objectMode) context->setContextObject(&object);
                const auto receiver =
                    objectMode ? engine_->newQObject(&object) : QJSValue(QJSValue::UndefinedValue);
                const auto bundle = [&](const char* tag, int minutes, bool invalid,
                                        const char* finite) {
                    return make.call({QJSValue(QString::fromLatin1(tag)), QJSValue(minutes),
                                      QJSValue(invalid), QJSValue(QString::fromLatin1(finite)),
                                      receiver});
                };
                const auto a = bundle("context-A", 37, false, "delegate");
                const auto b = bundle("context-B", 38, true, "delegate");
                const auto no = bundle("context-false", 38, false, "false");
                const auto yes = bundle("context-true", 38, false, "true");
                const auto assign = [&](const QString& name, const QJSValue& value) {
                    if (objectMode)
                        object.set(name, value);
                    else
                        context->setContextProperty(name, QVariant::fromValue(value));
                };
                for (const auto& name : {"JSON", "Array", "Date", "Math", "isFinite"})
                    assign(QString::fromLatin1(name), a.property(QString::fromLatin1(name)));
                QSignalSpy warnings(engine_, &QQmlEngine::warnings);
                prerequisite(warnings.isValid(), "actual context binding warnings are observed");
                auto owner = panel(applicationInfo, context.get());
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
                    snapshot("explicit-over-object");
                    check.require(
                        owner->property("unitResetText").toString() == "Resets in 39 min",
                        "explicit context properties outrank same-name context object properties");
                    object.set("Math", a.property("Math"));
                    snapshot("shadowed-object-notify");
                    check.require(
                        owner->property("unitResetText").toString() == "Resets in 39 min",
                        "the shadowed context object cannot override an explicit context "
                        "property");
                }
                check.require(
                    owner->property("accountInitial").toString().isEmpty(),
                    "the genuine disconnected account keeps the original empty-email branch");
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
                    "destroyed creation context stops bindings while the genuine object survives");
                check.require(
                    warnings.isEmpty() && !engine_->hasError(),
                    "supported context updates/reentry/invalidation add no unrelated QML errors");
            }
            // A real scope method outranks the surrounding context/global function.
            UsageLookupContext object;
            QJSEngine::setObjectOwnership(&object, QJSEngine::CppOwnership);
            QQmlContext context(engine_->rootContext());
            context.setContextObject(&object);
            const auto values = make.call({QJSValue(QStringLiteral("scope-context")), QJSValue(37),
                                           QJSValue(false), QJSValue(QStringLiteral("true")),
                                           engine_->newQObject(&object)});
            for (const auto& name : {"JSON", "Array", "Date", "Math", "isFinite"})
                object.set(QString::fromLatin1(name), values.property(QString::fromLatin1(name)));
            QSignalSpy scopeWarnings(engine_, &QQmlEngine::warnings);
            prerequisite(scopeWarnings.isValid(), "scope-method warning observer is valid");
            auto owner = panel(
                applicationInfo, &context,
                "id: unitLookupScope; property var unitScopeStats: ({calls:0,receiver:true});"
                "function isFinite(value) { const s=unitScopeStats; ++s.calls;"
                "s.receiver=s.receiver&&(this===unitLookupScope); return false; }");
            const auto stats = engine_->newQObject(owner.get()).property("unitScopeStats");
            trace.append(QVariantMap{{"stage", "scope-method"},
                                     {"stats", stats.toVariant()},
                                     {"text", owner->property("unitResetText")}});
            check.require(owner->property("unitResetText").toString() == "Reset unavailable" &&
                              stats.property("calls").toInt() > 0 &&
                              stats.property("receiver").toBool(),
                          "actual Panel scope function wins and receives its real QObject base");
            check.require(scopeWarnings.isEmpty() && !engine_->hasError(),
                          "the supported scope member adds no unrelated QML error");
        } catch (const std::exception& error) {
            check.require(false, QString::fromUtf8(error.what()));
        }
        auto result = check.result();
        result.insert("context_lookup_trace", trace);
        return result;
    }
    Q_INVOKABLE QVariantMap callLookupOrder(QObject* applicationInfo) const {
        UsageChecks check;
        QVariantList trace;
        try {
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
                                     "let result,thrown=false,same=false;try{result=" +
                                     call +
                                     ";}catch(error){thrown=true;same=error===s.sentinel;}"
                                     "finally{s.armed=false;}s.facts={events:s.events,"
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
                    check.require(facts.value("thrown").toBool() == throws &&
                                      facts.value("same").toBool() == throws,
                                  label + ": exact same-engine sentinel is preserved");
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
    qmlRegisterSingletonType<UsageAccountProof>(
        "UsageAccountAcceptance", 1, 0, "UsageAccountProof",
        [](QQmlEngine* engine, QJSEngine*) -> QObject* { return new UsageAccountProof(engine); });
}
Q_COREAPP_STARTUP_FUNCTION(registerUsageAccountProof)
#include "test_e11_t5_usage_account.moc"
