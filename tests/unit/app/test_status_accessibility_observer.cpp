// Test-owned native accessibility observation/action, linked into the existing app runner.
#include <QtQml/qqml.h>

#include <QAccessible>
#include <QCoreApplication>
#include <QJSEngine>
#include <QPointer>
#include <QQmlEngine>
#include <QVariantMap>

class StatusAccessibilityProof final : public QObject {
    Q_OBJECT
   public:
    using QObject::QObject;

    Q_INVOKABLE bool watchLifetime(QObject* object) {
        stopLifetimeWatch();
        if (!object) return false;
        watched_ = object;
        lifetimeConnection_ =
            QObject::connect(object, &QObject::destroyed, this, [this] { ++destroyedCount_; });
        return static_cast<bool>(lifetimeConnection_) && !watched_.isNull();
    }

    Q_INVOKABLE void stopLifetimeWatch() {
        QObject::disconnect(lifetimeConnection_);
        lifetimeConnection_ = {};
        watched_.clear();
        destroyedCount_ = 0;
    }

    Q_INVOKABLE QVariantMap lifetimeFacts() const {
        return {{"alive", !watched_.isNull()}, {"destroyed", destroyedCount_}};
    }

    Q_INVOKABLE QVariantMap observe(QObject* object) const {
        auto* iface = object ? QAccessible::queryAccessibleInterface(object) : nullptr;
        if (!iface || !iface->isValid()) {
            return {{"valid", false}, {"button", false}, {"press", false}};
        }
        const auto state = iface->state();
        const auto* actions = iface->actionInterface();
        return {{"valid", true},
                {"id", QAccessible::uniqueId(iface)},
                {"role", static_cast<int>(iface->role())},
                {"button", iface->role() == QAccessible::Button},
                {"staticText", iface->role() == QAccessible::StaticText},
                {"name", iface->text(QAccessible::Name)},
                {"description", iface->text(QAccessible::Description)},
                {"disabled", static_cast<bool>(state.disabled)},
                {"focusable", static_cast<bool>(state.focusable)},
                {"invisible", static_cast<bool>(state.invisible)},
                {"press", actions && actions->actionNames().contains(
                                         QAccessibleActionInterface::pressAction())}};
    }

    Q_INVOKABLE QVariantMap press(quint32 id) const {
        auto* iface = QAccessible::accessibleInterface(id);
        if (!iface || !iface->isValid()) {
            return {{"valid", false}, {"attempted", false}};
        }
        auto* actions = iface->actionInterface();
        if (!actions) {
            return {{"valid", true}, {"attempted", false}};
        }
        // Attempt the actual Qt action even when it is not advertised or the item
        // is disabled/hidden. The production door must enforce its own guards.
        // Do not touch iface/object/actions after dispatch: the callback can retire them.
        actions->doAction(QAccessibleActionInterface::pressAction());
        return {{"valid", true}, {"attempted", true}};
    }

   private:
    QPointer<QObject> watched_;
    QMetaObject::Connection lifetimeConnection_;
    int destroyedCount_ = 0;
};

static void registerStatusAccessibilityProof() {
    qmlRegisterSingletonType<StatusAccessibilityProof>(
        "StatusAccessibilityAcceptance", 1, 0, "StatusAccessibilityProof",
        [](QQmlEngine*, QJSEngine*) -> QObject* { return new StatusAccessibilityProof; });
}
Q_COREAPP_STARTUP_FUNCTION(registerStatusAccessibilityProof)
#include "test_status_accessibility_observer.moc"
