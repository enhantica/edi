// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_CHART_MODELS_HPP
#define EDI_APP_CHART_MODELS_HPP

#include <QAbstractListModel>
#include <QColor>
#include <QList>
#include <QString>
#include <QStringList>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// A chart's legend (edi ADR-0017 §15): one row per presented series, in the order the core's presentation
// lists them. Roles `label` (the series' name, or a structure's for its ticks), `color` (the series' colour
// in the current theme), `mark` (what is drawn before the name: a "line" or a "tick", in the series' width,
// or an element's "atom" icon), `markWidth` (a line's or tick's width in pixels, the series' own) and `bragg`
// (the row is a structure's Bragg ticks), and `labelTexts` and `labelColors` (the label as pieces, edi::legend_label:
// each piece's text and its colour's name, empty for a plain piece, index for index). Line marks are drawn shapes, never characters, so they look the same
// on every platform (edi ADR-0033).
class ChartLegendModel : public QAbstractListModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("A legend comes from its chart's controller")
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    enum Role {
        LabelRole = Qt::UserRole + 1,
        ColorRole,
        MarkRole,
        BraggRole,
        MarkWidthRole,
        LabelTextsRole,
        LabelColorsRole,
        SelectedRole,
        KeyRole,
        HiddenRole
    };
    struct Entry {
        QString label;
        QColor color;
        QString mark;
        bool bragg = false;
        double markWidth = 0.0;
        QStringList labelTexts, labelColors;
        // The selected dataset's entry, shown bold in the accent colour.
        bool selected = false;
        // What a click on the entry hides or shows (the series' id, or a listed row's label), and whether it is hidden.
        QString key;
        bool hidden = false;
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

// A legend whose rows its chart sets itself (the single-crystal charts, which have no controller): one row per label,
// a 3-pixel line in the colour of the same index (a colour name), and the row at `selected` shown bold in the accent
// colour (-1 for none).
class ListedLegendModel : public ChartLegendModel {
    Q_OBJECT
    QML_ELEMENT

   public:
    explicit ListedLegendModel(QObject* parent = nullptr) : ChartLegendModel(parent) {}
    // `hidden`: the labels of the rows hidden by a click (each row's key is its label).
    Q_INVOKABLE void setRows(const QStringList& labels, const QStringList& colors, int selected,
                             const QStringList& hidden = {});
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
