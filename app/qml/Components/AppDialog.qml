// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

// The base's Dialog, centred on whole pixels (edi ADR-0017 §14). The base centres with a half, so a dialog of
// odd height sat on a half pixel and each platform drew its edges and its table's lines differently (edi PR
// 97: the three-row Messages dialog, 239 high, at y 264.5). Every dialog of edi's is one of these.
EaElements.Dialog {
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
}
