// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// A main view's empty state, as the base page draws its own ("No structures defined"; EasyApp's ContentPage): plain
// text in the second font family, three font units, extra light, in the disabled colour, centred and wrapped. Every
// chart's empty state uses it (owner, 2026-10-11).
EaElements.Label {
    enabled: false
    horizontalAlignment: Text.AlignHCenter
    wrapMode: Text.WordWrap
    font.family: EaStyle.Fonts.secondFontFamily
    font.pixelSize: EaStyle.Sizes.fontPixelSize * 3
    font.weight: Font.ExtraLight
}
