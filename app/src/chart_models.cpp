// SPDX-License-Identifier: BSD-3-Clause
#include "chart_models.hpp"

namespace edi_app {

ChartLegendModel::ChartLegendModel(QObject* parent) : QAbstractListModel(parent) {}

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
        default: return {};
    }
}

QHash<int, QByteArray> ChartLegendModel::roleNames() const {
    return {{LabelRole, "label"}, {ColorRole, "color"}, {MarkRole, "mark"}, {BraggRole, "bragg"}};
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
