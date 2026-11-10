// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QQuickItem>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// Qt's ListView can stop filling: when all its rows are removed and new ones inserted before it lays out again, it
// keeps the fill position of the rows it had and makes none of the new ones. It then shows at most one stale row of
// what its count promises (a table filtered in quick succession, or refreshed by a fit). This puts such a view right.
class ViewRows : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON

   public:
    using QObject::QObject;
    // If `view` (a ListView) places no row while its model has rows and none is being made, sets its model again,
    // which rebuilds its rows. Returns whether it did.
    Q_INVOKABLE bool refill(QQuickItem* view) const;
};

}  // namespace edi_app
