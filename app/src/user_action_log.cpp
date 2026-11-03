// SPDX-License-Identifier: BSD-3-Clause
#include "user_action_log.hpp"

#include <QCoreApplication>
#include <QEvent>
#include <QKeyEvent>
#include <QMetaMethod>
#include <QMouseEvent>
#include <QQuickItem>
#include <QQuickWindow>
#include <QRegularExpression>
#include <QTouchEvent>

#include <algorithm>
#include <functional>
#include <memory>

#include "run_log.hpp"

namespace edi_app {

namespace {

// Runs its action once, on the first signal connected to it, then goes.
class Once : public QObject {
    Q_OBJECT

   public:
    Once(std::function<void()> action, QObject* parent) : QObject(parent), action_(std::move(action)) {}

   public slots:
    void fire() {
        if (action_) {
            auto action = std::exchange(action_, nullptr);
            action();
        }
        deleteLater();
    }

   private:
    std::function<void()> action_;
};

bool is(const QObject* object, const char* className) { return object != nullptr && object->inherits(className); }

bool isTextField(const QQuickItem* item) { return is(item, "QQuickTextInput") || is(item, "QQuickTextEdit"); }

bool hasSignal(const QObject* object, const char* name) {
    const QMetaObject* meta = object->metaObject();
    for (int i = 0; i < meta->methodCount(); ++i) {
        const QMetaMethod method = meta->method(i);
        if (method.methodType() == QMetaMethod::Signal && method.name() == name) {
            return true;
        }
    }
    return false;
}

// Connects the first signal of `object` named `name` to `once`.
bool connectNamed(QObject* object, const char* name, Once* once) {
    const QMetaObject* meta = object->metaObject();
    const QMetaMethod fire = once->metaObject()->method(once->metaObject()->indexOfSlot("fire()"));
    for (int i = 0; i < meta->methodCount(); ++i) {
        const QMetaMethod method = meta->method(i);
        if (method.methodType() == QMetaMethod::Signal && method.name() == name) {
            return QObject::connect(object, method, once, fire);
        }
    }
    return false;
}

// The children in the order they are drawn, last on top.
QList<QQuickItem*> drawnOrder(const QQuickItem* item) {
    QList<QQuickItem*> children = item->childItems();
    std::stable_sort(children.begin(), children.end(), [](const QQuickItem* a, const QQuickItem* b) { return a->z() < b->z(); });
    return children;
}

// The topmost item under `scenePoint`, drawn last, below `item`.
QQuickItem* itemAt(QQuickItem* item, const QPointF& scenePoint) {
    if (!item->isVisible() || item->opacity() <= 0.0) {
        return nullptr;
    }
    const bool inside = item->contains(item->mapFromScene(scenePoint));
    if (item->clip() && !inside) {
        return nullptr;
    }
    const QList<QQuickItem*> children = drawnOrder(item);
    for (auto child = children.crbegin(); child != children.crend(); ++child) {
        if (QQuickItem* found = itemAt(*child, scenePoint)) {
            return found;
        }
    }
    // A layer over the whole window (the popups' overlay) is not what is pressed.
    return inside && !is(item, "QQuickOverlay") && item->parentItem() != nullptr ? item : nullptr;
}

// The control `item` belongs to: a button, a combo box, a field, or anything a click acts on.
QQuickItem* controlOf(QQuickItem* item) {
    for (QQuickItem* ancestor = item; ancestor != nullptr; ancestor = ancestor->parentItem()) {
        if (is(ancestor, "QQuickAbstractButton") || is(ancestor, "QQuickComboBox") || isTextField(ancestor) ||
            is(ancestor, "QQuickMouseArea") || hasSignal(ancestor, "clicked")) {
            return ancestor;
        }
    }
    return nullptr;
}

// A combo box's list: its choice is written by the combo box itself.
bool inComboBoxList(const QQuickItem* item) {
    for (const QQuickItem* ancestor = item; ancestor != nullptr; ancestor = ancestor->parentItem()) {
        if (is(ancestor, "QQuickPopupItem")) {
            const QObject* popup = ancestor->parent();
            return popup != nullptr && is(popup->parent(), "QQuickComboBox");
        }
    }
    return false;
}

QString typeName(const QObject* object) {
    static const QRegularExpression generated(QStringLiteral("_QMLTYPE_\\d+$|_QML_\\d+$"));
    QString name = QString::fromLatin1(object->metaObject()->className());
    name.remove(generated);
    if (name.startsWith(QStringLiteral("QQuick"))) {
        name = name.mid(6);
    }
    return name;
}

// The page or window the control is in: a workflow page by name, a dialog or popup by its objectName.
QString placeOf(const QQuickItem* control) {
    static const QRegularExpression page(QStringLiteral("^workflow\\.([^.]+)\\."));
    for (const QQuickItem* ancestor = control; ancestor != nullptr; ancestor = ancestor->parentItem()) {
        const QRegularExpressionMatch match = page.match(ancestor->objectName());
        if (match.hasMatch()) {
            return match.captured(1);
        }
        if (is(ancestor, "QQuickPopupItem") && ancestor->parent() != nullptr && !ancestor->parent()->objectName().isEmpty()) {
            return ancestor->parent()->objectName();
        }
    }
    return QStringLiteral("app");
}

bool isNumber(const QString& text) {
    bool ok = false;
    text.trimmed().toDouble(&ok);
    return ok;
}

// Whether `field` is made for a number: a parameter's value, a field or cell that accepts a number or an integer, or
// one with a number validator. Decided by what the field is for, never by what it holds: a message, a name or a title
// that happens to read as a number is free text, and free text is never written.
bool isNumericField(const QQuickItem* field) {
    if (!is(field, "QQuickTextInput")) {
        return false;  // a text area is always free text
    }
    const QObject* validator = field->property("validator").value<QObject*>();
    if (is(validator, "QDoubleValidator") || is(validator, "QIntValidator")) {
        return true;
    }
    int depth = 0;
    for (const QQuickItem* ancestor = field; ancestor != nullptr && depth < 4; ancestor = ancestor->parentItem(), ++depth) {
        const QString accepts = ancestor->property("accepts").toString();
        if (accepts == QLatin1String("number") || accepts == QLatin1String("integer")) {
            return true;
        }
        if (is(ancestor->property("item").value<QObject*>(), "edi_app::ParameterItem")) {
            return true;
        }
    }
    return false;
}

void note(const QString& line) { qCInfo(lcApp).noquote() << line; }

}  // namespace

UserActionLog::UserActionLog(QObject* parent) : QObject(parent) {}

void UserActionLog::install() {
    static bool installed = false;
    if (installed || QCoreApplication::instance() == nullptr) {
        return;
    }
    installed = true;
    QCoreApplication::instance()->installEventFilter(new UserActionLog(QCoreApplication::instance()));
}

QString UserActionLog::nameOf(const QQuickItem* control) {
    if (!control->objectName().isEmpty()) {
        return control->objectName();
    }
    // A field's or a button's own item is often unnamed inside its named wrapper (a labelled field, a cell).
    int depth = 0;
    for (const QQuickItem* ancestor = control->parentItem(); ancestor != nullptr && depth < 3;
         ancestor = ancestor->parentItem(), ++depth) {
        if (!ancestor->objectName().isEmpty() && !ancestor->objectName().startsWith(QStringLiteral("workflow."))) {
            return ancestor->objectName();
        }
    }
    return typeName(control) + QLatin1Char('@') + placeOf(control);
}

void UserActionLog::watchWindow(QQuickWindow* window) {
    if (window->property("_ediActionsWatched").toBool()) {
        return;
    }
    window->setProperty("_ediActionsWatched", true);
    connect(window, &QQuickWindow::activeFocusItemChanged, this, [this, window] { focusChanged(window); });
}

void UserActionLog::focusChanged(QQuickWindow* window) {
    QQuickItem* field = window->activeFocusItem();
    if (!isTextField(field) || field->property("_ediEditWatched").toBool()) {
        return;
    }
    // A field's value is written when it is committed: Return, Enter or leaving it.
    field->setProperty("_ediEditWatched", true);
    // Written only when the value changed: passing through a field commits nothing.
    const QString before = field->property("text").toString();
    QPointer<QQuickItem> guarded(field);
    auto* once = new Once(
        [guarded, before] {
            if (!guarded) {
                return;
            }
            guarded->setProperty("_ediEditWatched", false);
            const QString text = guarded->property("text").toString();
            if (guarded->property("readOnly").toBool() || text == before) {
                return;
            }
            const QString name = nameOf(guarded);
            note(isNumericField(guarded) && isNumber(text) ? QStringLiteral("set %1 = %2").arg(name, text.trimmed())
                                                            : QStringLiteral("edit %1").arg(name));
        },
        this);
    connectNamed(field, "editingFinished", once);
    // A text area may commit nothing of its own: its value is also taken when it loses the focus, whichever comes
    // first, as the one line.
    if (is(field, "QQuickTextEdit")) {
        QPointer<Once> pending(once);
        auto connection = std::make_shared<QMetaObject::Connection>();
        *connection = connect(field, &QQuickItem::activeFocusChanged, this, [pending, connection](bool focused) {
            if (focused) {
                return;
            }
            QObject::disconnect(*connection);
            if (pending) {
                pending->fire();
            }
        });
    }
}

void UserActionLog::await(QQuickItem* control) {
    delete waiting_;
    QPointer<QQuickItem> guarded(control);
    Once* once = nullptr;
    if (is(control, "QQuickComboBox")) {
        once = new Once(
            [guarded] {
                if (guarded) {
                    note(QStringLiteral("choose %1 = %2").arg(nameOf(guarded), guarded->property("currentText").toString()));
                }
            },
            this);
        connectNamed(control, "activated", once);
    } else if (is(control, "QQuickAbstractButton")) {
        once = new Once(
            [guarded] {
                if (!guarded) {
                    return;
                }
                // A tab is chosen by a click; a check box or toggle shows its new state.
                if (guarded->property("checkable").toBool() && !is(guarded, "QQuickTabButton")) {
                    note(QStringLiteral("check %1 = %2").arg(nameOf(guarded), guarded->property("checked").toBool() ? QStringLiteral("on") : QStringLiteral("off")));
                } else {
                    note(QStringLiteral("click %1").arg(nameOf(guarded)));
                }
            },
            this);
        connectNamed(control, "clicked", once);
    } else if (!isTextField(control)) {
        once = new Once(
            [guarded] {
                if (guarded) {
                    note(QStringLiteral("click %1").arg(nameOf(guarded)));
                }
            },
            this);
        connectNamed(control, "clicked", once);
    }
    waiting_ = once;
}

bool UserActionLog::eventFilter(QObject* watched, QEvent* event) {
    // The press as Qt delivers it to the items under the pointer, topmost first, until one takes it: the control of
    // the last one is the control pressed.
    if (auto* item = qobject_cast<QQuickItem*>(watched)) {
        if (event->type() == QEvent::MouseButtonPress || event->type() == QEvent::TouchBegin) {
            QQuickItem* control = controlOf(item);
            if (control != nullptr && !inComboBoxList(control)) {
                await(control);
            }
        }
        return false;
    }
    auto* window = qobject_cast<QQuickWindow*>(watched);
    if (window == nullptr) {
        return false;
    }
    watchWindow(window);
    QPointF point;
    bool press = false;
    if (event->type() == QEvent::MouseButtonPress) {
        point = static_cast<QMouseEvent*>(event)->scenePosition();
        press = true;
    } else if (event->type() == QEvent::TouchBegin) {
        const auto* touch = static_cast<QTouchEvent*>(event);
        if (!touch->points().isEmpty()) {
            point = touch->points().constFirst().scenePosition();
            press = true;
        }
    } else if (event->type() == QEvent::KeyPress) {
        const int key = static_cast<QKeyEvent*>(event)->key();
        QQuickItem* focused = window->activeFocusItem();
        // Typing in a field that had the focus before it was watched.
        if (isTextField(focused)) {
            focusChanged(window);
        }
        if ((key == Qt::Key_Space || key == Qt::Key_Return || key == Qt::Key_Enter) && focused != nullptr &&
            !isTextField(focused) && !static_cast<QKeyEvent*>(event)->isAutoRepeat()) {
            if (QQuickItem* control = controlOf(focused)) {
                await(control);
            }
        }
        return false;
    }
    if (!press || window->contentItem() == nullptr) {
        return false;
    }
    QQuickItem* hit = itemAt(window->contentItem(), point);
    QQuickItem* control = hit != nullptr ? controlOf(hit) : nullptr;
    if (control != nullptr && !inComboBoxList(control)) {
        await(control);
    }
    return false;
}

}  // namespace edi_app

#include "user_action_log.moc"
