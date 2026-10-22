// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Components as EaComponents

// Compatibility row type; alternating paint and the current marker are shared
// ListView/ListViewDelegate defaults (ADR-0017 §11), without another local highlight.
EaComponents.ListViewDelegate {
    required property int index
}
