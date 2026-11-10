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
#include <QVariantList>
#include <QTemporaryDir>
#include <QSettings>
#include <QQmlContext>
#include <vector>
#include <QScopeGuard>
#include <QtQml/qqml.h>
#include <memory>

class TooltipClock final : public QObject {
    Q_OBJECT
    QQmlEngine* caller_;
    QPointer<QObject> target_;
    int timer_ = 0;
    int remaining_ = 0;
    struct PendingTimer { QPointer<QObject> target; int id; int remaining; };
    std::vector<PendingTimer> pending_;
    std::vector<std::unique_ptr<QTemporaryDir>> settings_;
public:
    explicit TooltipClock(QQmlEngine* caller) : caller_(caller) {}
    Q_INVOKABLE QString isolateSettings() {
        QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);
        auto directory = std::make_unique<QTemporaryDir>();
        if (!directory->isValid()) return {};
        QSettings::setPath(QSettings::IniFormat, QSettings::UserScope, directory->path());
        const auto url = QUrl::fromLocalFile(edi_app::settings_store_path()).toString();
        caller_->rootContext()->setContextProperty("pySettingsPath", url);
        settings_.push_back(std::move(directory));
        return url;
    }
    Q_INVOKABLE bool movePointer(QObject* object, qreal x, qreal y) const {
        auto* item = qobject_cast<QQuickItem*>(object);
        if (!item || !item->window()) return false;
        QTest::mouseMove(item->window(), item->mapToScene(QPointF(x, y)).toPoint(), 0);
        QCoreApplication::processEvents();
        return true;
    }
    Q_INVOKABLE bool isTooltip(QObject* object) const {
        return object && object->inherits("QQuickToolTip");
    }
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
    Q_INVOKABLE int armAll(const QVariantList& tooltips) {
        pending_.clear();
        for (const auto& value : tooltips) {
            auto* tooltip = value.value<QObject*>();
            if (!tooltip) continue;
            const int delay = tooltip->property("delay").toInt();
            for (const auto& timer : QAbstractEventDispatcher::instance()->registeredTimers(tooltip)) {
                if (timer.interval == delay && delay > 0)
                    pending_.push_back({tooltip, timer.timerId, delay});
            }
        }
        return static_cast<int>(pending_.size());
    }
    Q_INVOKABLE bool advanceAll(int milliseconds) {
        if (milliseconds < 0) return false;
        for (auto& timer : pending_) {
            if (!timer.target || !timer.id) continue;
            timer.remaining -= milliseconds;
            if (timer.remaining <= 0) {
                QTimerEvent event(timer.id);
                QCoreApplication::sendEvent(timer.target, &event);
                timer.id = 0;
            }
        }
        return true;
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
