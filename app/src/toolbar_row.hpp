// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QQuickItem>
#include <QString>
#include <QVariantList>
#include <QVariantMap>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// The controls row above every chart (ToolbarLines; edi ADR-0090 point 7): one centred row, and when it does not fit,
// controls leave it for a "More" (⋯) popup at its end, least important first, by one priority for every view.
class ToolbarRow : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON

   public:
    using QObject::QObject;
    // `units`, in row order, each {width, group, name, movable}: two neighbours of one group are `spacing` apart,
    // of different groups `groupSpacing`. Returns {shown, x} (one entry per unit; x of a shown one only), `more`
    // (whether the ⋯ button is needed) and `moreX`, the row centred between `left` and `right`.
    Q_INVOKABLE QVariantMap layout(const QVariantList& units, double left, double right, double spacing,
                                   double groupSpacing, double moreWidth) const;
    // Gathers the controls of `lines` (a ToolbarLines) into its `units`, taking a ChartToolbar's or StructureToolbar's
    // own controls into the row, then places them.
    Q_INVOKABLE void collect(QQuickItem* lines, QQuickItem* more) const;
    // Places the controls shown, moves the others out of sight and into `overflow`, and shows `more` when any moved.
    Q_INVOKABLE void place(QQuickItem* lines, QQuickItem* more) const;
    // The place of a control in the priority, from its object name's last part: lower leaves the row first.
    Q_INVOKABLE static int rank(const QString& name);
};

}  // namespace edi_app
