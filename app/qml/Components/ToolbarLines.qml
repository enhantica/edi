// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The controls row above every chart and the structure view (edi ADR-0090 point 7; the owner, 2026-11-16): one row,
// centred between `leftEdge` and `rightEdge`, the span of the selector row above it. When the row does not fit, its
// controls move into a "More" (⋯) popup at the row's end, least important first, by one priority on every view
// (ToolbarRow.rank). A child with `closedTexts` (ToolbarComboBox) is a combobox, one with `fontIcon` (ChartToolButton) a
// button; a child with `toolbarUnits` (ChartToolbar, StructureToolbar) gives its own comboboxes and buttons, a spacer
// among them starting a new group. Comboboxes of different `toolbarGroup`, and buttons of different groups, are a group's
// spacing apart; any other child (a row of buttons) stays whole in the row.
Item {
    id: lines

    property real leftEdge: 0
    property real rightEdge: width
    readonly property real centre: (leftEdge + rightEdge) / 2
    readonly property real spacing: AppSizes.toolbarSpacing
    readonly property real groupSpacing: EaStyle.Sizes.fontPixelSize * 0.5 + 2 * AppSizes.toolbarSpacing
    // Always one line now; kept for the views that read it.
    readonly property int lineCount: 1
    // Every control, in row order: {item, group, movable}; and those in the popup.
    property var units: []
    property var overflow: []
    readonly property string measure: [leftEdge, rightEdge, visible].concat(units.map(unit => unit.item.visible ? unit.item.width : -1)).join(",")

    implicitHeight: AppSizes.toolbarControlSize

    function collect() {
        ToolbarRow.collect(lines, moreButton);
    }
    function layout() {
        ToolbarRow.place(lines, moreButton);
    }

    onMeasureChanged: Qt.callLater(lines.layout)
    Component.onCompleted: Qt.callLater(lines.collect)

    ChartToolButton {
        id: moreButton

        objectName: lines.objectName !== "" ? lines.objectName + ".more" : "toolbar.more"
        visible: false
        fontIcon: "ellipsis-h"
        toolTip: qsTr("More chart options")
        checked: morePopup.opened
        onClicked: morePopup.opened ? morePopup.close() : morePopup.open()
    }
    Popup {
        id: morePopup

        x: Math.max(0, Math.min(moreButton.x + moreButton.width - width, lines.width - width))
        y: moreButton.y + moreButton.height + lines.spacing
        padding: EaStyle.Sizes.fontPixelSize * 0.5

        Column {
            spacing: lines.spacing

            Repeater {
                model: lines.overflow

                // The control itself stays in the row, out of sight; here a copy acts on it.
                delegate: Row {
                    id: entry

                    required property var modelData
                    readonly property bool box: modelData.closedTexts !== undefined

                    spacing: EaStyle.Sizes.fontPixelSize * 0.5

                    ToolbarComboBox {
                        objectName: entry.box ? entry.modelData.objectName + ".overflow" : ""
                        visible: entry.box
                        enabled: entry.modelData.enabled
                        toolTip: entry.modelData.toolTip ?? ""
                        model: entry.box ? entry.modelData.model : []
                        closedTexts: entry.box ? entry.modelData.closedTexts : []
                        shownIndex: entry.box ? entry.modelData.currentIndex : 0
                        onActivated: index => entry.modelData.activated(index)
                    }
                    ChartToolButton {
                        id: copy

                        objectName: entry.box ? "" : entry.modelData.objectName + ".overflow"
                        visible: !entry.box
                        enabled: entry.modelData.enabled
                        available: entry.modelData.available ?? true
                        fontIcon: entry.modelData.fontIcon ?? ""
                        checked: entry.modelData.checked ?? false
                        onClicked: entry.modelData.clicked()

                        // A button drawn with a letter (view along a, b, c) has no icon: its name's last part.
                        EaElements.Label {
                            anchors.centerIn: parent
                            visible: copy.fontIcon === ""
                            font.bold: true
                            text: String(entry.modelData.objectName).split(".").pop()
                        }
                    }
                    EaElements.Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: entry.modelData.toolTip ?? ""
                    }
                }
            }
        }
    }
}
