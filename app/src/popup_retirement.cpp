// SPDX-License-Identifier: BSD-3-Clause
#include "popup_retirement.hpp"

#include <QtQuickTemplates2/private/qquickoverlay_p.h>
#include <QtQuickTemplates2/private/qquickoverlay_p_p.h>
#include <QtQuickTemplates2/private/qquickpopup_p.h>
#include <QtQuickTemplates2/private/qquickpopup_p_p.h>

namespace edi_app {

void PopupRetirement::retire(QObject* object) const {
    auto* popup = qobject_cast<QQuickPopup*>(object);
    if (popup == nullptr) {
        return;
    }
    QQuickPopupPrivate* d = QQuickPopupPrivate::get(popup);
    if (d->transitionState == QQuickPopupPrivate::ExitTransition) {
        // Stopped before its end, the animation finishes nothing itself; the check guards against a second finish.
        d->transitionManager.cancel();
        if (d->transitionState == QQuickPopupPrivate::ExitTransition) {
            d->finalizeExitTransition();
        }
    }
    // Qt's close above already lets the overlay pass the target on or forget it; this makes sure no later popup returns
    // the focus to what this one saved.
    if (QQuickOverlay* overlay = QQuickOverlay::overlay(d->window, d->parentItem)) {
        QQuickOverlayPrivate* od = QQuickOverlayPrivate::get(overlay);
        if (od->lastActiveFocusItemPopup == popup) {
            od->lastActiveFocusItem = nullptr;
            od->lastActiveFocusItemPopup = nullptr;
        }
    }
    d->lastActiveFocusItem = nullptr;
}

}  // namespace edi_app
