// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The sidebar's width, chosen at the right end of its tab bar (the owner, 2026-11-22): Auto, by the window's width
// (edi ADR-0103 decision 3); Full, every column of every table; three narrower widths, each named by what it shows;
// Manual, the width the user drags the sidebar's edge to. The menu is the Load button's; the choice is a preference.
Item {
    id: control

    width: button.width
    height: button.height

    function choose(mode: string): void {
        // Manual starts from the width shown now.
        if (mode === "manual" && Preferences.sideBarManualWidth <= 0)
            Preferences.sideBarManualWidth = EaStyle.Sizes.sideBarWidth;
        Preferences.sideBarWidthMode = mode;
        menu.close();
    }

    // A bare icon, drawn as the groups' pins are: no border or background, in the text colour at a group title icon's
    // size, its centre on the pins' vertical line (the owner, 2026-11-23).
    EaElements.Label {
        id: button

        objectName: "sideBar.width"
        width: EaStyle.Sizes.fontPixelSize * 1.5
        height: Math.round(EaStyle.Sizes.fontPixelSize * 2)
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.family: EaStyle.Fonts.iconsFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        color: menu.opened ? EaStyle.Colors.themeAccent : buttonHover.hovered ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
        text: "arrows-alt-h"

        HoverHandler {
            id: buttonHover
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            onTapped: menu.opened ? menu.close() : menu.open()
        }
        EaElements.ToolTip {
            text: qsTr("Sidebar width")
            requested: buttonHover.hovered && !menu.opened
        }
    }

    EaElements.Menu {
        id: menu

        objectName: "sideBar.width.menu"
        x: button.width - width
        y: button.height
        bottomPadding: 0
        // As wide as its widest item, as the Load menus are: every label and hint whole.
        width: {
            let widest = 0;
            for (let i = 0; i < count; ++i) {
                const entry = itemAt(i);
                if (entry)
                    widest = Math.max(widest, entry.implicitWidth);
            }
            return Math.ceil(widest) + leftPadding + rightPadding;
        }
        readonly property real labelWidth: Math.max(EaStyle.Sizes.fontPixelSize * 7.5, Math.ceil(labels.advanceWidth) + EaStyle.Sizes.fontPixelSize * 0.25)
        TextMetrics {
            id: labels
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            text: qsTr("Fit values")
        }

        LoadMenuHeader {
            first: true
            text: qsTr("Sidebar width")
        }
        LoadMenuItem {
            labelWidth: menu.labelWidth
            objectName: "sideBar.width.auto"
            fontIcon: Preferences.sideBarWidthMode === "auto" ? "check" : ""
            text: qsTr("Auto")
            hint: qsTr("by window width")
            onTriggered: control.choose("auto")
        }
        LoadMenuItem {
            labelWidth: menu.labelWidth
            objectName: "sideBar.width.full"
            fontIcon: Preferences.sideBarWidthMode === "full" ? "check" : ""
            text: qsTr("Full")
            hint: AppSizes.sideBarModeProblem(control.Window.width, "full") || qsTr("every column")
            onTriggered: control.choose("full")
        }
        LoadMenuItem {
            labelWidth: menu.labelWidth
            objectName: "sideBar.width.bounds"
            fontIcon: Preferences.sideBarWidthMode === "bounds" ? "check" : ""
            text: qsTr("No change")
            hint: AppSizes.sideBarModeProblem(control.Window.width, "bounds") || qsTr("all but Change")
            onTriggered: control.choose("bounds")
        }
        LoadMenuItem {
            labelWidth: menu.labelWidth
            objectName: "sideBar.width.values"
            fontIcon: Preferences.sideBarWidthMode === "values" ? "check" : ""
            text: qsTr("Fit values")
            hint: AppSizes.sideBarModeProblem(control.Window.width, "values") || qsTr("start, value, s.u., free")
            onTriggered: control.choose("values")
        }
        LoadMenuItem {
            labelWidth: menu.labelWidth
            objectName: "sideBar.width.compact"
            fontIcon: Preferences.sideBarWidthMode === "compact" ? "check" : ""
            text: qsTr("Compact")
            hint: AppSizes.sideBarModeProblem(control.Window.width, "compact") || qsTr("name, value, free")
            onTriggered: control.choose("compact")
        }
        LoadMenuItem {
            labelWidth: menu.labelWidth
            objectName: "sideBar.width.manual"
            fontIcon: Preferences.sideBarWidthMode === "manual" ? "check" : ""
            text: qsTr("Manual")
            hint: qsTr("drag the sidebar's edge")
            onTriggered: control.choose("manual")
        }
    }
}
