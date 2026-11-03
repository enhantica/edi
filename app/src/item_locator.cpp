// SPDX-License-Identifier: BSD-3-Clause
#include "item_locator.hpp"

#include <QQuickItem>
#include <QQuickWindow>

#include <algorithm>
#include <cmath>

namespace edi_app {

namespace {

// The children in the order they are drawn: by z, and in their own order among equal z.
QList<QQuickItem*> drawnOrder(const QQuickItem* item) {
    QList<QQuickItem*> children = item->childItems();
    std::stable_sort(children.begin(), children.end(),
                     [](const QQuickItem* a, const QQuickItem* b) { return a->z() < b->z(); });
    return children;
}

QQuickItem* findAnyIn(QQuickItem* item, const QString& objectName) {
    if (item->objectName() == objectName) {
        return item;
    }
    for (QQuickItem* child : drawnOrder(item)) {
        if (QQuickItem* found = findAnyIn(child, objectName)) {
            return found;
        }
    }
    return nullptr;
}

QQuickItem* findIn(QQuickItem* item, const QString& objectName) {
    // A hidden item hides everything inside it.
    if (!item->isVisible()) {
        return nullptr;
    }
    if (item->objectName() == objectName && isItemShown(item)) {
        return item;
    }
    for (QQuickItem* child : drawnOrder(item)) {
        if (QQuickItem* found = findIn(child, objectName)) {
            return found;
        }
    }
    return nullptr;
}

}  // namespace

QQuickItem* findNamedItem(QQuickWindow* window, const QString& objectName) {
    if (window == nullptr || window->contentItem() == nullptr || objectName.isEmpty()) {
        return nullptr;
    }
    return findIn(window->contentItem(), objectName);
}

QQuickItem* findNamedItemAnywhere(QQuickWindow* window, const QString& objectName) {
    if (window == nullptr || window->contentItem() == nullptr || objectName.isEmpty()) {
        return nullptr;
    }
    return findAnyIn(window->contentItem(), objectName);
}

QRectF visibleSceneRect(const QQuickItem* item) {
    if (item == nullptr || item->window() == nullptr) {
        return {};
    }
    QRectF visible = item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
    visible &= QRectF(0, 0, item->window()->width(), item->window()->height());
    for (const QQuickItem* ancestor = item; ancestor != nullptr && !visible.isEmpty(); ancestor = ancestor->parentItem()) {
        if (!ancestor->isVisible() || ancestor->opacity() <= 0) {
            return {};
        }
        if (ancestor->clip()) {
            visible &= ancestor->mapRectToScene(ancestor->clipRect());
        }
    }
    // Less than a pixel either way is not something to point at.
    return visible.width() >= 1 && visible.height() >= 1 ? visible : QRectF();
}

QQuickItem* findNamedItemUnder(QQuickItem* root, const QString& objectName) {
    return root == nullptr || objectName.isEmpty() ? nullptr : findAnyIn(root, objectName);
}

bool isItemShown(const QQuickItem* item) { return !visibleSceneRect(item).isEmpty(); }

QRectF itemSceneRect(const QQuickItem* item) {
    if (item == nullptr) {
        return {};
    }
    return item->mapRectToScene(QRectF(0, 0, item->width(), item->height()));
}

QQuickItem* ItemLocator::find(QQuickWindow* window, const QString& objectName) const {
    return findNamedItem(window, objectName);
}

QQuickItem* ItemLocator::findAnywhere(QQuickWindow* window, const QString& objectName) const {
    return findNamedItemAnywhere(window, objectName);
}

QQuickItem* ItemLocator::findUnder(QQuickItem* root, const QString& objectName) const {
    return findNamedItemUnder(root, objectName);
}

bool ItemLocator::shown(QQuickItem* item) const { return isItemShown(item); }

QRectF ItemLocator::sceneRect(QQuickItem* item) const { return itemSceneRect(item); }

QRectF ItemLocator::visibleRect(QQuickItem* item) const { return visibleSceneRect(item); }

}  // namespace edi_app
