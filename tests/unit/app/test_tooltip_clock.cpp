#include <QAbstractEventDispatcher>
#include <QCoreApplication>
#include <QPointer>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQuickWindow>
#include <QQuickItem>
#include <QtTest/qtestmouse.h>
#include "engine_setup.hpp"
#include <QTimerEvent>
#include <QScopeGuard>
#include <QtQml/qqml.h>
#include <memory>

class TooltipClock final : public QObject {
    Q_OBJECT
    QQmlEngine* caller_;
    QPointer<QObject> target_;
    int timer_ = 0;
    int remaining_ = 0;
public:
    explicit TooltipClock(QQmlEngine* caller) : caller_(caller) {}
    Q_INVOKABLE QVariantMap restartAndClick() {
        auto* controller = caller_->incubationController();
        const auto restore = qScopeGuard([&] { caller_->setIncubationController(controller); });
        QQmlEngine engine;
        edi_app::configure_engine(engine);
        QQmlComponent component(&engine);
        component.setData("import QtQuick; import edi.app; Main { visible: true; width: 1280; height: 720 }", QUrl("file:///tooltip-restart.qml"));
        std::unique_ptr<QObject> app(component.create());
        auto* window = qobject_cast<QQuickWindow*>(app.get());
        if (!window) return {{"error", component.errorString()}};
        QCoreApplication::processEvents();
        QQuickItem* button = nullptr;
        for (auto* item : window->findChildren<QQuickItem*>())
            if (item->objectName().contains("tooltip", Qt::CaseInsensitive) && item->property("fontIcon").isValid()) {
                if (button) return {{"error", "The restarted window has several tooltip buttons"}};
                button = item;
            }
        if (!button || !button->isVisible() || !button->isEnabled()) return {{"error", "The restarted window has no available tooltip button"}};
        const QPoint at = button->mapToScene(QPointF(button->width()/2, button->height()/2)).toPoint();
        QTest::mouseClick(window, Qt::LeftButton, Qt::NoModifier, at, 0);
        QQmlComponent snapshot(&engine);
        snapshot.setData("import QtQuick; import edi.app; QtObject { property var level: { const k = Object.keys(Preferences).find(k => /^tooltips?level$/i.test(k)); return Preferences[k]; } }", QUrl("file:///tooltip-snapshot.qml"));
        std::unique_ptr<QObject> value(snapshot.create());
        if (!value) return {{"error", snapshot.errorString()}};
        return {{"level", value->property("level")}, {"clicked", true}};
    }
    Q_INVOKABLE bool arm(QObject* tooltip) {
        target_ = tooltip;
        timer_ = 0;
        if (!tooltip) return false;
        const int delay = tooltip->property("delay").toInt();
        for (const auto& timer : QAbstractEventDispatcher::instance()->registeredTimers(tooltip)) {
            if (timer.interval == delay && delay > 0) {
                timer_ = timer.timerId;
                remaining_ = delay;
                return true;
            }
        }
        return false;
    }
    Q_INVOKABLE bool advance(int milliseconds) {
        if (!target_ || !timer_ || milliseconds < 0) return false;
        remaining_ -= milliseconds;
        if (remaining_ <= 0) {
            QTimerEvent event(timer_);
            QCoreApplication::sendEvent(target_, &event);
            timer_ = 0;
        }
        return true;
    }
};
static void register_tooltip_clock() {
    qmlRegisterSingletonType<TooltipClock>("TooltipAcceptance", 1, 0, "TooltipClock",
        [](QQmlEngine* engine, QJSEngine*) -> QObject* { return new TooltipClock(engine); });
}
Q_COREAPP_STARTUP_FUNCTION(register_tooltip_clock)
#include "test_tooltip_clock.moc"
