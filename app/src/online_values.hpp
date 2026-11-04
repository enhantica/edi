// SPDX-License-Identifier: BSD-3-Clause
#pragma once
// The From web popup's fixed-shape values as QML reads them, typed (ADR-0015 §2).
#include <QMetaType>
#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

/// One entry a search found, as handed to the loaders with its downloaded file.
struct OnlineEntry {
    Q_GADGET
    QML_VALUE_TYPE(onlineEntry)
    Q_PROPERTY(QString id MEMBER id CONSTANT)
    Q_PROPERTY(QString kind MEMBER kind CONSTANT)
    Q_PROPERTY(QString name MEMBER name CONSTANT)
    Q_PROPERTY(QString formula MEMBER formula CONSTANT)
    Q_PROPERTY(QString spaceGroup MEMBER spaceGroup CONSTANT)
    Q_PROPERTY(QString radiation MEMBER radiation CONSTANT)
    Q_PROPERTY(QString technique MEMBER technique CONSTANT)
    Q_PROPERTY(QString instrument MEMBER instrument CONSTANT)
    Q_PROPERTY(QString source MEMBER source CONSTANT)
    Q_PROPERTY(QString format MEMBER format CONSTANT)
   public:
    QString id, kind, name, formula, spaceGroup, radiation, technique, instrument, source, format;
    bool operator==(const OnlineEntry&) const = default;
};

}  // namespace edi_app
