// SPDX-License-Identifier: BSD-3-Clause
// TestDrop (QML singleton, import edi.app.test): files dragged onto and dropped on an item as the system delivers
// them, with their URLs as text/uri-list, so a case can check a drop target without a real drag.
#include <QCoreApplication>
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QMimeData>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickWindow>
#include <QUrl>

namespace {

class TestDrop : public QObject {
    Q_OBJECT

   public:
    using QObject::QObject;

    // Drags `urls` over `item` at its local point (x, y); true when a target accepted them.
    Q_INVOKABLE bool enter(QQuickItem* item, qreal x, qreal y, const QList<QUrl>& urls) {
        if (!item || !item->window()) return false;
        mime_.setUrls(urls);
        QDragEnterEvent enter(item->mapToScene({x, y}).toPoint(), Qt::CopyAction, &mime_, Qt::LeftButton, Qt::NoModifier);
        QCoreApplication::sendEvent(item->window(), &enter);
        QDragMoveEvent move(item->mapToScene({x, y}).toPoint(), Qt::CopyAction, &mime_, Qt::LeftButton, Qt::NoModifier);
        QCoreApplication::sendEvent(item->window(), &move);
        return move.isAccepted();
    }
    // Drops what enter() dragged at the same kind of point; true when a target took it.
    Q_INVOKABLE bool drop(QQuickItem* item, qreal x, qreal y) {
        if (!item || !item->window()) return false;
        QDropEvent drop(item->mapToScene({x, y}), Qt::CopyAction, &mime_, Qt::LeftButton, Qt::NoModifier);
        QCoreApplication::sendEvent(item->window(), &drop);
        return drop.isAccepted();
    }

   private:
    QMimeData mime_;
};

void register_test_drop() {
    qmlRegisterSingletonType<TestDrop>("edi.app.test", 1, 0, "TestDrop",
                                       [](QQmlEngine*, QJSEngine*) -> QObject* { return new TestDrop; });
}
Q_COREAPP_STARTUP_FUNCTION(register_test_drop)

}  // namespace

#include "test_drop_events.moc"
