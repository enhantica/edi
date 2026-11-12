// SPDX-License-Identifier: BSD-3-Clause
#include "combo_box_metrics.hpp"

#include <QFontMetricsF>
#include <QtQml/qqmlinfo.h>
#include <algorithm>

namespace edi_app {

ComboBoxMetrics::ComboBoxMetrics(QObject* parent) : QObject(parent) {
    connect(this, &ComboBoxMetrics::comboBoxChanged, this, &ComboBoxMetrics::invalidate);
    connect(this, &ComboBoxMetrics::fontChanged, this, &ComboBoxMetrics::invalidate);
    connect(this, &ComboBoxMetrics::countChanged, this, &ComboBoxMetrics::invalidate);
    connect(this, &ComboBoxMetrics::textRoleChanged, this, &ComboBoxMetrics::invalidate);
    connect(this, &ComboBoxMetrics::displayTextChanged, this, &ComboBoxMetrics::schedule);
    connect(this, &ComboBoxMetrics::modelChanged, this, &ComboBoxMetrics::observeModel);
}

void ComboBoxMetrics::setComboBox(QObject* control) {
    if (control != control_) {
        control_ = control;
        emit comboBoxChanged();
    }
}

int ComboBoxMetrics::sampledCount() const {
    return count_ > 1000 ? 200 : std::max(count_, 0);
}

void ComboBoxMetrics::observeModel() {
    for (const auto& connection : model_connections_) {
        disconnect(connection);
    }
    model_connections_.clear();
    if (auto* model = qobject_cast<QAbstractItemModel*>(model_.value<QObject*>())) {
        model_connections_.append(connect(model, &QAbstractItemModel::dataChanged, this,
            [this, model](const QModelIndex& first, const QModelIndex& last, const QList<int>& roles) {
                if (first.row() >= sampledCount() || last.row() < 0) {
                    return;
                }
                const auto role_names = model->roleNames();
                const auto role = role_names.key(text_role_.toUtf8(), -1);
                if (roles.isEmpty() || role < 0 || roles.contains(role)) {
                    invalidate();
                }
            }));
        model_connections_.append(connect(model, &QAbstractItemModel::modelReset, this, &ComboBoxMetrics::invalidate));
        model_connections_.append(connect(model, &QAbstractItemModel::rowsInserted, this, &ComboBoxMetrics::invalidate));
        model_connections_.append(connect(model, &QAbstractItemModel::rowsRemoved, this, &ComboBoxMetrics::invalidate));
        model_connections_.append(connect(model, &QAbstractItemModel::rowsMoved, this, &ComboBoxMetrics::invalidate));
        model_connections_.append(connect(model, &QAbstractItemModel::layoutChanged, this, &ComboBoxMetrics::invalidate));
    }
    invalidate();
}

void ComboBoxMetrics::invalidate() {
    dirty_ = true;
    schedule();
}

void ComboBoxMetrics::schedule() {
    if (!pending_) {
        pending_ = true;
        QMetaObject::invokeMethod(this, &ComboBoxMetrics::refresh, Qt::QueuedConnection);
    }
}

void ComboBoxMetrics::refresh() {
    pending_ = false;
    const QFontMetricsF metrics(font_);
    const qreal display = metrics.horizontalAdvance(display_text_);
    if (dirty_) {
        dirty_ = false;
        qreal widest = 0.0;
        for (int row = 0; control_ && row < sampledCount(); ++row) {
            QString text;
            if (!QMetaObject::invokeMethod(control_, "textAt", Qt::DirectConnection,
                                          Q_RETURN_ARG(QString, text), Q_ARG(int, row))) {
                qmlWarning(this) << "Cannot read the combo box's option text";
                break;
            }
            widest = std::max(widest, metrics.horizontalAdvance(text));
        }
        if (widest != option_width_) {
            option_width_ = widest;
            emit optionTextWidthChanged();
        }
    }
    if (display != display_width_) {
        display_width_ = display;
        emit displayTextWidthChanged();
    }
}

}  // namespace edi_app
