// SPDX-License-Identifier: BSD-3-Clause
#include "list_model_mirror.hpp"

#include <algorithm>

namespace edi_app {

void ListModelMirror::setSource(QAbstractItemModel* source) {
    if (source == source_) return;
    for (const auto& connection : std::as_const(connections_)) disconnect(connection);
    connections_.clear();
    const int before = rows_;
    const int after = source != nullptr ? source->rowCount() : 0;
    // The first source names the roles: a view that read none before reads them again from a reset.
    if (roles_.isEmpty() && source != nullptr) {
        beginResetModel();
        roles_ = source->roleNames();
        source_ = source;
        rows_ = after;
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
        rows_ = after;
        endRemoveRows();
    } else if (after > before) {
        beginInsertRows(QModelIndex(), before, after - 1);
        source_ = source;
        rows_ = after;
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
    const auto forward = [this](auto signal, auto slot) { connections_.append(connect(source_, signal, this, slot)); };
    forward(&QAbstractItemModel::dataChanged, [this](const QModelIndex& first, const QModelIndex& last, const QList<int>& roles) {
        emit dataChanged(index(first.row()), index(last.row()), roles);
    });
    forward(&QAbstractItemModel::rowsAboutToBeInserted,
          [this](const QModelIndex&, int first, int last) { beginInsertRows(QModelIndex(), first, last); });
    forward(&QAbstractItemModel::rowsInserted, [this](const QModelIndex&, int first, int last) {
        rows_ += last - first + 1;
        endInsertRows();
        emit countChanged();
    });
    forward(&QAbstractItemModel::rowsAboutToBeRemoved,
          [this](const QModelIndex&, int first, int last) { beginRemoveRows(QModelIndex(), first, last); });
    forward(&QAbstractItemModel::rowsRemoved, [this](const QModelIndex&, int first, int last) {
        rows_ -= last - first + 1;
        endRemoveRows();
        emit countChanged();
    });
    forward(&QAbstractItemModel::rowsAboutToBeMoved, [this](const QModelIndex&, int first, int last, const QModelIndex&, int to) {
        beginMoveRows(QModelIndex(), first, last, QModelIndex(), to);
    });
    forward(&QAbstractItemModel::rowsMoved, [this](const QModelIndex&, int, int, const QModelIndex&, int) { endMoveRows(); });
    forward(&QAbstractItemModel::modelAboutToBeReset, [this] { beginResetModel(); });
    forward(&QAbstractItemModel::modelReset, [this] {
        rows_ = source_ ? source_->rowCount() : 0;
        // A proxy takes its role names from its own source, which may be set only now (the Parameters table's filter):
        // they are read again with the reset, so rows made from here on have every role.
        if (source_) roles_ = source_->roleNames();
        endResetModel();
        emit countChanged();
    });
    forward(&QAbstractItemModel::layoutAboutToBeChanged, [this] { emit layoutAboutToBeChanged(); });
    forward(&QAbstractItemModel::layoutChanged, [this] { emit layoutChanged(); });
    // A source destroyed before it is replaced leaves the mirror empty, its rows removed as any others.
    connections_.append(connect(source, &QObject::destroyed, this, [this] {
        // The source is gone; its rows, as the views were told of them, are removed.
        source_.clear();
        if (rows_ > 0) {
            beginRemoveRows(QModelIndex(), 0, rows_ - 1);
            rows_ = 0;
            endRemoveRows();
            emit countChanged();
        }
        emit sourceChanged();
    }));
}

int ListModelMirror::rowCount(const QModelIndex& parent) const {
    return parent.isValid() ? 0 : rows_;
}

QVariant ListModelMirror::data(const QModelIndex& index, int role) const {
    if (!source_ || !index.isValid() || index.row() >= rows_) return {};
    return source_->data(source_->index(index.row(), 0), role);
}

bool ListModelMirror::setData(const QModelIndex& index, const QVariant& value, int role) {
    return source_ && index.isValid() && source_->setData(source_->index(index.row(), 0), value, role);
}

QHash<int, QByteArray> ListModelMirror::roleNames() const {
    return !roles_.isEmpty() ? roles_ : source_ ? source_->roleNames() : QHash<int, QByteArray>{};
}

}  // namespace edi_app
