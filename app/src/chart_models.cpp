// SPDX-License-Identifier: BSD-3-Clause
#include "chart_models.hpp"

namespace edi_app {

ChartLegendModel::ChartLegendModel(QObject* parent) : QAbstractListModel(parent) {}

void ListedLegendModel::setRows(const QStringList& labels, const QStringList& colors, int selected,
                                const QStringList& hidden) {
    QList<Entry> entries;
    for (qsizetype i = 0; i < labels.size(); ++i) {
        Entry entry;
        entry.label = labels.at(i);
        entry.color = QColor(i < colors.size() ? colors.at(i) : QString());
        entry.mark = QStringLiteral("line");
        entry.markWidth = 3.0;  // the sample's thickness, pixels
        entry.selected = i == selected;
        entry.key = entry.label;
        entry.hidden = hidden.contains(entry.key);
        entries.append(entry);
    }
    setEntries(entries);
}

void ChartLegendModel::setEntries(const QList<Entry>& entries) {
    if (entries == entries_) {
        return;
    }
    const bool count_changed = entries.size() != entries_.size();
    beginResetModel();  // a handful of rows, replaced when the series or the theme change
    entries_ = entries;
    endResetModel();
    if (count_changed) {
        emit countChanged();
    }
}

int ChartLegendModel::rowCount(const QModelIndex& parent) const {
    return parent.isValid() ? 0 : static_cast<int>(entries_.size());
}

QVariant ChartLegendModel::data(const QModelIndex& index, int role) const {
    if (!index.isValid() || index.row() >= entries_.size()) {
        return {};
    }
    const Entry& entry = entries_.at(index.row());
    switch (role) {
        case LabelRole:
        case Qt::DisplayRole: return entry.label;
        case ColorRole: return entry.color;
        case MarkRole: return entry.mark;
        case BraggRole: return entry.bragg;
        case MarkWidthRole: return entry.markWidth;
        case LabelTextsRole: return entry.labelTexts;
        case LabelColorsRole: return entry.labelColors;
        case SelectedRole: return entry.selected;
        case KeyRole: return entry.key;
        case HiddenRole: return entry.hidden;
        default: return {};
    }
}

QHash<int, QByteArray> ChartLegendModel::roleNames() const {
    return {{LabelRole, "label"},
            {ColorRole, "color"},
            {MarkRole, "mark"},
            {BraggRole, "bragg"},
            {MarkWidthRole, "markWidth"},
            {LabelTextsRole, "labelTexts"},
            {LabelColorsRole, "labelColors"},
            {SelectedRole, "selected"},
            {KeyRole, "key"},
            {HiddenRole, "hidden"}};
}

ChartBandModel::ChartBandModel(QObject* parent) : QAbstractListModel(parent) {}

void ChartBandModel::setBands(const QList<Band>& bands) {
    if (bands == bands_) {
        return;
    }
    const bool count_changed = bands.size() != bands_.size();
    beginResetModel();  // a handful of rows, replaced when the regions or the view change
    bands_ = bands;
    endResetModel();
    if (count_changed) {
        emit countChanged();
    }
}

int ChartBandModel::rowCount(const QModelIndex& parent) const {
    return parent.isValid() ? 0 : static_cast<int>(bands_.size());
}

QVariant ChartBandModel::data(const QModelIndex& index, int role) const {
    if (!index.isValid() || index.row() >= bands_.size()) {
        return {};
    }
    const Band& band = bands_.at(index.row());
    switch (role) {
        case XMinRole: return band.x_min;
        case XMaxRole: return band.x_max;
        default: return {};
    }
}

QHash<int, QByteArray> ChartBandModel::roleNames() const {
    return {{XMinRole, "xMin"}, {XMaxRole, "xMax"}};
}

}  // namespace edi_app
