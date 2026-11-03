// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QQuickItem>
#include <QQuickWindow>
#include <QRectF>
#include <QString>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// Finding a window's control by its object name (ADR-0066). The tutorials' callouts use it, and anything else that
// points at or acts on a named control should too, so there is one way to find one.

// The first item named `objectName` that is shown, walking the window's items depth first in the order they are
// drawn; nullptr if none is.
QQuickItem* findNamedItem(QQuickWindow* window, const QString& objectName);
// The first item named `objectName` in the same walk, shown or not: a control on a hidden tab or in a folded group, to
// be revealed before it is pointed at. nullptr if the window has none (a tab not yet loaded holds none).
QQuickItem* findNamedItemAnywhere(QQuickWindow* window, const QString& objectName);
// The same within `root`: a page, whose controls may share names with another page's.
QQuickItem* findNamedItemUnder(QQuickItem* root, const QString& objectName);
// The part of `item` that can be seen, in its window's coordinates: its rectangle within the window and within every
// ancestor that clips its children, provided it and its ancestors are visible and not transparent; empty if none is.
QRectF visibleSceneRect(const QQuickItem* item);
// Whether some part of `item` can be seen (visibleSceneRect is not empty).
bool isItemShown(const QQuickItem* item);
// The item's rectangle in its window's coordinates.
QRectF itemSceneRect(const QQuickItem* item);

// The same for QML: `ItemLocator.find(Window.window, "appBar.tab.project")`.
class ItemLocator : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON

   public:
    using QObject::QObject;
    Q_INVOKABLE QQuickItem* find(QQuickWindow* window, const QString& objectName) const;
    Q_INVOKABLE QQuickItem* findAnywhere(QQuickWindow* window, const QString& objectName) const;
    Q_INVOKABLE QQuickItem* findUnder(QQuickItem* root, const QString& objectName) const;
    Q_INVOKABLE bool shown(QQuickItem* item) const;
    Q_INVOKABLE QRectF sceneRect(QQuickItem* item) const;
    Q_INVOKABLE QRectF visibleRect(QQuickItem* item) const;
};

}  // namespace edi_app
