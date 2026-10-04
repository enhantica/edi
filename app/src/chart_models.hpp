// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_CHART_MODELS_HPP
#define EDI_APP_CHART_MODELS_HPP

#include <QAbstractListModel>
#include <QColor>
#include <QList>
#include <QString>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// A chart's legend (edi ADR-0017 §15): one row per presented series, in the order the core's presentation
// lists them. Roles `label` (the series' name, or a structure's for its ticks), `color` (the series' colour
// in the current theme), `mark` (the line or tick glyph before the name) and `bragg` (the row is a
// structure's Bragg ticks).
class ChartLegendModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("A legend comes from its chart's controller")
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    enum Role { LabelRole = Qt::UserRole + 1, ColorRole, MarkRole, BraggRole };
    struct Entry {
        QString label;
        QColor color;
        QString mark;
        bool bragg = false;
        friend bool operator==(const Entry&, const Entry&) = default;
    };

    explicit ChartLegendModel(QObject* parent = nullptr);

    void setEntries(const QList<Entry>& entries);
    int count() const { return static_cast<int>(entries_.size()); }

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

   signals:
    void countChanged();

   private:
    QList<Entry> entries_;
};

// A chart's excluded regions inside its view (edi ADR-0021 §4): one row per band. Roles `xMin` and `xMax`,
// on the chart's x axis.
class ChartBandModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("The bands come from their chart's controller")
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    enum Role { XMinRole = Qt::UserRole + 1, XMaxRole };
    struct Band {
        double x_min = 0.0;
        double x_max = 0.0;
        friend bool operator==(const Band&, const Band&) = default;
    };

    explicit ChartBandModel(QObject* parent = nullptr);

    void setBands(const QList<Band>& bands);
    int count() const { return static_cast<int>(bands_.size()); }

    int rowCount(const QModelIndex& parent = QModelIndex()) const override;
    QVariant data(const QModelIndex& index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

   signals:
    void countChanged();

   private:
    QList<Band> bands_;
};

}  // namespace edi_app

#endif  // EDI_APP_CHART_MODELS_HPP
