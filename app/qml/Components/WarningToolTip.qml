// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// Why a field's value is refused or outside its range: the base's tooltip, as every other tooltip in the app, with
// its border in the red of the warned text and its background tinted by it (the owner's note 6). Shown whatever the
// tooltip preference, since it explains a red value.
EaElements.ToolTip {
    borderColor: EaStyle.Colors.red
    backgroundColor: Qt.tint(EaStyle.Colors.toolTipBackground, Qt.rgba(EaStyle.Colors.red.r, EaStyle.Colors.red.g, EaStyle.Colors.red.b, 0.15))
}
