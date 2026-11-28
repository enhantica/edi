// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QObject>
#include <QtQml/qqmlregistration.h>

namespace edi_app {

// Closes a popup of the project being replaced for good before the next project shows (edi ADR-0052). Qt ends a
// popup's closing only when its exit animation stops: only then does it restore the focus and let the overlay forget
// the popup, by which time the next project may be on screen and the user in another popup.
class PopupRetirement : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON

   public:
    using QObject::QObject;
    // Ends `popup`'s running exit now, as the animation's end would, and drops the focus target the overlay still
    // keeps for it. A popup that is open or closed is left as it is.
    Q_INVOKABLE void retire(QObject* popup) const;
};

}  // namespace edi_app
