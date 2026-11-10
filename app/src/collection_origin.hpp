// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// Where a downloaded data file came from in the collection: its entry and the file's digest (edi ADR-0075), so a
// linked dataset is downloaded again when a fit needs it.
struct CollectionOrigin {
    Q_GADGET
    QML_VALUE_TYPE(collectionOrigin)
    Q_PROPERTY(QString id MEMBER id CONSTANT)
    Q_PROPERTY(QString digest MEMBER digest CONSTANT)

   public:
    QString id;
    QString digest;
};

}  // namespace edi_app
