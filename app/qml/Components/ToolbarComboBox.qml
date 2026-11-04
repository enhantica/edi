// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A drop-down in a view's toolbar (edi ADR-0017 §15, §16; the owner, 2026-10-02), one style for the structure
// view's colour scheme and the pattern chart's y scale: the base's combo box at the toolbar buttons' height, as
// narrow as its widest entry with the arrow and the padding, and with the sidebar drop-downs' background — the
// base's translucent combo-box colour over the content background the sidebar is drawn on — whatever the view
// behind it. The entries are a list of strings.
EaElements.ComboBox {
    id: box

    property string toolTip: ""
    // The toolbar group the box belongs to (ToolbarLines): boxes of different groups are a group's spacing apart.
    property string toolbarGroup: ""
    // The index the box shows, bound by its user to where the choice is kept (a preference, the project). A ComboBox's
    // own currentIndex binding ends at the first choice made in it, after which a choice made elsewhere (Preferences)
    // would no longer show here; the binding is made again after each choice, once the choice has been kept, so the
    // box always shows the kept choice, and a refused one goes back.
    property int shownIndex: 0
    currentIndex: shownIndex
    onActivated: ApplicationInfo.queueToolbarBinding(() => box.currentIndex = Qt.binding(() => box.shownIndex))
    // What the closed box shows for each entry (an axis box's "y: linear"), when it differs from the list's entry.
    property var closedTexts: []
    // The base's rich-text label leaves Qt's widest-text policy nothing to measure, so the entries, and the closed
    // texts, are measured here. advanceWidth() is a call the binding cannot follow, so the binding reads the font too,
    // and measures again once the style's font has loaded; before that it measured a wider fallback font.
    readonly property real widestEntry: ApplicationInfo.toolbarWidestEntry()

    displayText: box.closedTexts.length > box.currentIndex && box.currentIndex >= 0 ? box.closedTexts[box.currentIndex] : box.currentText

    width: widestEntry + contentItemLabel.leftPadding + contentItemLabel.rightPadding + leftPadding + rightPadding
    height: AppSizes.toolbarControlSize
    backgroundColor: Qt.tint(EaStyle.Colors.contentBackground, !box.hovered ? EaStyle.Colors.appBarComboBoxBackground : box.pressed ? EaStyle.Colors.appBarComboBoxBackgroundPressed : EaStyle.Colors.appBarComboBoxBackgroundHovered)

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }
    FontMetrics {
        id: metrics

        font: box.font
    }
    EaElements.ToolTip {
        text: box.toolTip
        visible: text !== "" && box.hovered && EaGlobals.Vars.showToolTips
    }
}
