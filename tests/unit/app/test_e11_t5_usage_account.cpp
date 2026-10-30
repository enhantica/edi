// SPDX-License-Identifier: BSD-3-Clause
// First finite usage layer: real Panel pure relations; canonical/UI/timer gates remain separate.
#include <QtCore/qtestsupport_core.h>
#include <QtQml/qqml.h>
#include <QtTest/qtestcase.h>

#include <QColor>
#include <QCoreApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QMetaProperty>
#include <QPointer>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQmlEngine>
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
    UsagePanelLease panel(QObject* applicationInfo) const {
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
            e11_usage_phase::color("unitRemaining") + "; }";
        QQmlComponent component(engine_);
        component.setData(code.toUtf8(), QUrl("qrc:/tests/UsageAccountOriginalOwner.qml"));
        if (component.isError()) throw std::runtime_error(component.errorString().toStdString());
        std::unique_ptr<QObject> created(component.createWithInitialProperties({
            {"parent", QVariant::fromValue(owner.host.get())},
            {"toggleControl", QVariant::fromValue(owner.toggle.get())},
        }));
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
};

static void registerUsageAccountProof() {
    qmlRegisterSingletonType<UsageAccountProof>(
        "UsageAccountAcceptance", 1, 0, "UsageAccountProof",
        [](QQmlEngine* engine, QJSEngine*) -> QObject* { return new UsageAccountProof(engine); });
}
Q_COREAPP_STARTUP_FUNCTION(registerUsageAccountProof)
#include "test_e11_t5_usage_account.moc"
