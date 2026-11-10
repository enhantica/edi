// SPDX-License-Identifier: BSD-3-Clause
#include "view_rows.hpp"

#include <QVariant>
#include <QtQmlModels/private/qqmlobjectmodel_p.h>
#include <QtQuick/private/qquickitemview_p.h>
#include <QtQuick/private/qquickitemview_p_p.h>

namespace edi_app {

bool ViewRows::refill(QQuickItem* view) const {
    auto* list = qobject_cast<QQuickItemView*>(view);
    if (list == nullptr) {
        return false;
    }
    const auto* d = static_cast<const QQuickItemViewPrivate*>(QQuickItemPrivate::get(list));
    const QQmlInstanceModel* model = d->model;
    // A row being made is placed when it is ready; only a view waiting for nothing is stuck.
    if (model == nullptr || model->count() == 0 || !d->visibleItems.isEmpty() || d->requestedIndex != -1) {
        return false;
    }
    // Set from C++, the model keeps its QML binding.
    const QVariant source = list->model();
    list->setModel(QVariant());
    list->setModel(source);
    list->forceLayout();
    return true;
}

}  // namespace edi_app
