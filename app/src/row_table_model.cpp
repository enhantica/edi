// SPDX-License-Identifier: BSD-3-Clause
#include "row_table_model.hpp"

#include <QSet>

namespace edi_app {

RowTableModel::RowTableModel(const QStringList& roles, QObject* parent) : QAbstractListModel(parent), roles_(roles) {}

int RowTableModel::rowCount(const QModelIndex& parent) const { return parent.isValid() ? 0 : count(); }

QVariant RowTableModel::data(const QModelIndex& index, int role) const {
    const int column = roleIndex(role);
    if (!index.isValid() || index.row() >= rows_.size() || column < 0 || column >= roles_.size()) {
        return {};
    }
    return rowValues(index.row()).value(column);
}

QHash<int, QByteArray> RowTableModel::roleNames() const {
    QHash<int, QByteArray> names;
    for (int i = 0; i < roles_.size(); ++i) {
        names.insert(Qt::UserRole + 1 + i, roles_.at(i).toUtf8());
    }
    return names;
}

bool RowTableModel::setData(const QModelIndex& index, const QVariant& value, int role) {
    const int column = roleIndex(role);
    return index.isValid() && column >= 0 && column < roles_.size() && setRole(index.row(), roles_.at(column), value);
}

Qt::ItemFlags RowTableModel::flags(const QModelIndex& index) const {
    return QAbstractListModel::flags(index) | Qt::ItemIsEditable;
}

bool RowTableModel::setRole(int, const QString&, const QVariant&) { return false; }

QVariant RowTableModel::get(int row, const QString& role) const {
    const int column = static_cast<int>(roles_.indexOf(role));
    if (row < 0 || row >= rows_.size() || column < 0) {
        return {};
    }
    return rowValues(row).value(column);
}

void RowTableModel::setTableRows(const QList<Row>& target) {
    const qsizetype before = rows_.size();
    const auto find = [](const QList<Row>& rows, const void* key, qsizetype from) {
        for (qsizetype i = from; i < rows.size(); ++i) {
            if (rows.at(i).key == key) {
                return i;
            }
        }
        return qsizetype(-1);
    };
    // The rows no longer wanted, found through a set of the wanted keys: one pass, whatever the length.
    QSet<const void*> wanted;
    wanted.reserve(target.size());
    for (const Row& row : target) {
        wanted.insert(row.key);
    }
    for (qsizetype i = rows_.size() - 1; i >= 0; --i) {
        if (!wanted.contains(rows_.at(i).key)) {
            beginRemoveRows(QModelIndex(), static_cast<int>(i), static_cast<int>(i));
            rows_.removeAt(i);
            endRemoveRows();
        }
    }
    for (qsizetype i = 0; i < target.size(); ++i) {
        const int row = static_cast<int>(i);
        if (i >= rows_.size() || rows_.at(i).key != target.at(i).key) {
            const qsizetype found = find(rows_, target.at(i).key, i);
            if (found < 0) {
                beginInsertRows(QModelIndex(), row, row);
                rows_.insert(i, target.at(i));
                endInsertRows();
                continue;
            }
            beginMoveRows(QModelIndex(), static_cast<int>(found), static_cast<int>(found), QModelIndex(), row);
            rows_.move(found, i);
            endMoveRows();
        }
        QList<int> changed;
        for (int column = 0; column < roles_.size(); ++column) {
            if (rows_.at(i).values.value(column) != target.at(i).values.value(column)) {
                changed.append(Qt::UserRole + 1 + column);
            }
        }
        if (!changed.isEmpty()) {
            rows_[i].values = target.at(i).values;
            emit dataChanged(index(row), index(row), changed);
        }
    }
    if (rows_.size() != before) {
        emit countChanged();
    }
}

void RowTableModel::setTableRow(int row, const QList<QVariant>& values) {
    if (row < 0 || row >= rows_.size()) {
        return;
    }
    QList<int> changed;
    for (int column = 0; column < roles_.size(); ++column) {
        if (rows_.at(row).values.value(column) != values.value(column)) {
            changed.append(Qt::UserRole + 1 + column);
        }
    }
    if (!changed.isEmpty()) {
        rows_[row].values = values;
        emit dataChanged(index(row), index(row), changed);
    }
}

}  // namespace edi_app
