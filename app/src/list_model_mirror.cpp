// SPDX-License-Identifier: BSD-3-Clause
#include "list_model_mirror.hpp"

#include <algorithm>

namespace edi_app {

void ListModelMirror::setSource(QAbstractItemModel* source) {
    if (source == source_) return;
    for (const auto& connection : std::as_const(connections_)) disconnect(connection);
    connections_.clear();
    const int before = rowCount();
    const int after = source != nullptr ? source->rowCount() : 0;
    // The first source names the roles: a view that read none before reads them again from a reset.
    if (roles_.isEmpty() && source != nullptr) {
        beginResetModel();
        roles_ = source->roleNames();
        source_ = source;
        endResetModel();
        if (before != after) emit countChanged();
        follow();
        emit sourceChanged();
        return;
    }
    // Only the rows the lists do not share come or go; the shared ones keep their delegates and are announced below.
    if (after < before) {
        beginRemoveRows(QModelIndex(), after, before - 1);
        source_ = source;
        endRemoveRows();
    } else if (after > before) {
        beginInsertRows(QModelIndex(), before, after - 1);
        source_ = source;
        endInsertRows();
    } else {
        source_ = source;
    }
    const int shared = std::min(before, after);
    if (shared > 0) emit dataChanged(index(0), index(shared - 1));
    if (before != after) emit countChanged();
    follow();
    emit sourceChanged();
}

void ListModelMirror::follow() {
    if (!source_) return;
    QAbstractItemModel* source = source_;
    const auto relay = [this](auto signal, auto slot) { connections_.append(connect(source_, signal, this, slot)); };
    relay(&QAbstractItemModel::dataChanged, [this](const QModelIndex& first, const QModelIndex& last, const QList<int>& roles) {
        emit dataChanged(index(first.row()), index(last.row()), roles);
    });
    relay(&QAbstractItemModel::rowsAboutToBeInserted,
          [this](const QModelIndex&, int first, int last) { beginInsertRows(QModelIndex(), first, last); });
    relay(&QAbstractItemModel::rowsInserted, [this](const QModelIndex&, int, int) {
        endInsertRows();
        emit countChanged();
    });
    relay(&QAbstractItemModel::rowsAboutToBeRemoved,
          [this](const QModelIndex&, int first, int last) { beginRemoveRows(QModelIndex(), first, last); });
    relay(&QAbstractItemModel::rowsRemoved, [this](const QModelIndex&, int, int) {
        endRemoveRows();
        emit countChanged();
    });
    relay(&QAbstractItemModel::rowsAboutToBeMoved, [this](const QModelIndex&, int first, int last, const QModelIndex&, int to) {
        beginMoveRows(QModelIndex(), first, last, QModelIndex(), to);
    });
    relay(&QAbstractItemModel::rowsMoved, [this](const QModelIndex&, int, int, const QModelIndex&, int) { endMoveRows(); });
    relay(&QAbstractItemModel::modelAboutToBeReset, [this] { beginResetModel(); });
    relay(&QAbstractItemModel::modelReset, [this] {
        endResetModel();
        emit countChanged();
    });
    relay(&QAbstractItemModel::layoutAboutToBeChanged, [this] { emit layoutAboutToBeChanged(); });
    relay(&QAbstractItemModel::layoutChanged, [this] { emit layoutChanged(); });
    // A source destroyed before it is replaced leaves the mirror empty, its rows removed as any others.
    connections_.append(connect(source, &QObject::destroyed, this, [this] {
        const int rows = rowCount();
        if (rows > 0) {
            beginRemoveRows(QModelIndex(), 0, rows - 1);
            source_.clear();
            endRemoveRows();
            emit countChanged();
        }
        emit sourceChanged();
    }));
}

int ListModelMirror::rowCount(const QModelIndex& parent) const {
    return parent.isValid() || !source_ ? 0 : source_->rowCount();
}

QVariant ListModelMirror::data(const QModelIndex& index, int role) const {
    if (!source_ || !index.isValid()) return {};
    return source_->data(source_->index(index.row(), 0), role);
}

bool ListModelMirror::setData(const QModelIndex& index, const QVariant& value, int role) {
    return source_ && index.isValid() && source_->setData(source_->index(index.row(), 0), value, role);
}

QHash<int, QByteArray> ListModelMirror::roleNames() const {
    return !roles_.isEmpty() ? roles_ : source_ ? source_->roleNames() : QHash<int, QByteArray>{};
}

}  // namespace edi_app
