// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

// A drop-down in a view's toolbar (edi ADR-0017 §15, §16; the owner, 2026-10-02), one style for the structure
// view's colour scheme and the pattern chart's y scale: the base's combo box at the toolbar buttons' height, as
// narrow as its widest entry with the arrow and the padding, and with the sidebar drop-downs' background — the
// base's translucent combo-box colour over the content background the sidebar is drawn on — whatever the view
// behind it. The entries are a list of strings.
EaElements.ComboBox {
    id: box

    property string toolTip: ""
    // The base's rich-text label leaves Qt's widest-text policy nothing to measure, so the entries are measured here.
    readonly property real widestEntry: {
        let widest = 0;
        const entries = box.model || [];
        for (let i = 0; i < entries.length; ++i)
            widest = Math.max(widest, metrics.advanceWidth(String(entries[i])));
        return Math.ceil(widest);
    }

    width: widestEntry + contentItemLabel.leftPadding + contentItemLabel.rightPadding + leftPadding + rightPadding
    height: Math.round(EaStyle.Sizes.fontPixelSize * 2.5)
    backgroundColor: Qt.tint(EaStyle.Colors.contentBackground, !box.hovered ? EaStyle.Colors.appBarComboBoxBackground : box.pressed ? EaStyle.Colors.appBarComboBoxBackgroundPressed : EaStyle.Colors.appBarComboBoxBackgroundHovered)

    FontMetrics {
        id: metrics

        font: box.font
    }
    EaElements.ToolTip {
        text: box.toolTip
        visible: text !== "" && box.hovered && EaGlobals.Vars.showToolTips
    }
}
