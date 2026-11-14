// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A sidebar group: the base's GroupBox, whose height animates only when it folds or unfolds where it can be seen. The
// base animates every change of its height, also content arriving and groups folding while a page is built in the
// background, which kept every sidebar laying out for seconds after a project opened.
//
// Opening a group folds the others of its tab (Preferences, Interface), except the pinned ones: the pin at the right
// end of the title keeps a group open (the owner, 2026-11-10). The app folds them here, so the base's own folding is
// off (Preferences.qml).
EaElements.GroupBox {
    id: group

    // The name a pin is remembered by, between sessions.
    property string pinKey: objectName
    readonly property bool pinned: pinKey !== "" && Preferences.pinnedGroups.split(",").includes(pinKey)
    function togglePin() {
        const keys = Preferences.pinnedGroups.split(",").filter(key => key !== "" && key !== pinKey);
        if (!pinned)
            keys.push(pinKey);
        Preferences.pinnedGroups = keys.join(",");
    }

    // The height the base animates towards (its implicitHeight without the animation).
    readonly property real restingHeight: collapsed ? titleArea.height : titleArea.height + spacing + contentHeight + bottomPadding
    property bool folding: false

    height: folding ? implicitHeight : restingHeight
    onCollapsedChanged: {
        if (!collapsed && Preferences.autoCollapse) {
            for (const other of parent.children) {
                if (other !== group && other.pinned === false && other.collapsible && !other.collapsed)
                    other.collapsed = true;
            }
        }
        if (!onScreen)
            return;
        folding = true;
        foldEnd.restart();
    }
    // On the current item of every SwipeView it is in (its page and its sidebar tab): a SwipeView keeps the others
    // visible.
    readonly property bool onScreen: {
        const chain = [];
        for (let item = group; item !== null; item = item.parent) {
            if (item instanceof SwipeView && !chain.includes((item as SwipeView).currentItem))
                return false;
            chain.push(item);
        }
        return true;
    }

    // The base's fold animation takes 500 ms.
    Timer {
        id: foldEnd
        interval: 550
        onTriggered: group.folding = false
    }

    // The pin, at the title's right end, the content's right padding from the edge: grey, the accent colour when on.
    // Held by a property and drawn on the group itself, so it is not part of the content, whose one child sizes it.
    readonly property Item pin: EaElements.Label {
        parent: group
        objectName: group.objectName + ".pin"
        visible: group.collapsible && group.title !== "" && Preferences.autoCollapse
        x: group.width - group.rightPadding - width
        y: (group.titleArea.height - height) / 2
        width: EaStyle.Sizes.fontPixelSize * 1.5
        height: group.titleArea.height
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.family: EaStyle.Fonts.iconsFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
        rotation: group.pinned ? 0 : 45
        color: group.pinned ? EaStyle.Colors.themeAccent : pinHover.hovered ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForegroundDisabled
        text: "thumbtack"

        HoverHandler {
            id: pinHover
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            onTapped: group.togglePin()
        }
        EaElements.ToolTip {
            text: group.pinned ? qsTr("Unpin: fold this group when another opens") : qsTr("Pin: keep this group open when another opens")
            requested: pinHover.hovered
        }
    }
}
