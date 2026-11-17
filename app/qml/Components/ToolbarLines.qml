// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

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
    // Nothing left to show: the popup closes rather than stay open empty.
    onOverflowChanged: if (overflow.length === 0) morePopup.close()
    Component.onCompleted: Qt.callLater(lines.collect)

    ChartToolButton {
        id: moreButton

        objectName: lines.objectName !== "" ? lines.objectName + ".more" : "toolbar.more"
        visible: false
        fontIcon: "ellipsis-h"
        toolTip: qsTr("More chart options")
        // By `visible`, not `opened`: a press on this button already closes the popup (a press outside it), and
        // `opened` turns false as the closing starts, so the click that follows opened it again.
        checked: morePopup.visible
        onClicked: morePopup.visible ? morePopup.close() : morePopup.open()
    }
    // The app's popup (EaElements.Menu: its frame and its open and close animation) in the chart's background colour,
    // holding one row of the controls that do not fit, as they look in the toolbar, each with its tooltip (the owner,
    // 2026-11-16). The control itself stays in the row, out of sight; its copy here acts on it.
    EaElements.Menu {
        id: morePopup

        objectName: moreButton.objectName + ".popup"
        x: Math.max(0, Math.min(moreButton.x + moreButton.width - width, lines.width - width))
        y: moreButton.y + moreButton.height + lines.spacing
        padding: lines.spacing * 2
        width: overflowRow.implicitWidth + leftPadding + rightPadding

        Binding {
            target: morePopup.background
            property: "color"
            value: EaStyle.Colors.chartBackground
        }

        // The row is the menu's one item: the menu takes the children of its own list as its items.
        Row {
            id: overflowRow

            spacing: lines.spacing

            // One copy per movable control, made once and shown while its control is in the popup: copies made and
            // destroyed on every resize left their tooltips binding to deleted controls (QML warnings).
            Repeater {
                model: lines.units.filter(unit => unit.movable)

                delegate: Item {
                    id: entry

                    required property var modelData
                    readonly property var control: modelData.item
                    readonly property bool box: control?.closedTexts !== undefined
                    // A colour map's box keeps its gradients in the popup too: copied as itself (the owner, 2026-11-17).
                    readonly property bool colourMap: box && control?.maps !== undefined

                    visible: !!control && lines.overflow.indexOf(control) >= 0
                    width: colourMap ? mapCopy.width : box ? boxCopy.width : buttonCopy.width
                    height: AppSizes.toolbarControlSize

                    ColourMapComboBox {
                        id: mapCopy

                        objectName: entry.colourMap ? entry.control.objectName + ".overflow" : ""
                        visible: entry.colourMap
                        enabled: entry.colourMap && entry.control.enabled
                        toolTip: entry.colourMap ? entry.control.toolTip ?? "" : ""
                        maps: entry.colourMap ? entry.control.maps : []
                        direction: entry.colourMap ? entry.control.direction : "auto"
                        chartBackground: entry.colourMap ? entry.control.chartBackground : "white"
                        dark: entry.colourMap && entry.control.dark
                        shownIndex: entry.colourMap ? entry.control.currentIndex : 0
                        onActivated: index => entry.control.activated(index)
                    }
                    ToolbarComboBox {
                        id: boxCopy

                        objectName: entry.box && !entry.colourMap ? entry.control?.objectName + ".overflow" : ""
                        visible: entry.box && !entry.colourMap
                        enabled: entry.control?.enabled ?? false
                        toolTip: entry.control?.toolTip ?? ""
                        model: entry.box ? entry.control.model : []
                        closedTexts: entry.box ? entry.control.closedTexts : []
                        closedOnly: entry.box && entry.control.closedOnly
                        shownIndex: entry.box ? entry.control.currentIndex : 0
                        onActivated: index => entry.control?.activated(index)
                    }
                    ChartToolButton {
                        id: buttonCopy

                        objectName: entry.box ? "" : entry.control?.objectName + ".overflow"
                        visible: !entry.box
                        enabled: entry.control?.enabled ?? false
                        available: entry.control?.available ?? true
                        fontIcon: entry.control?.fontIcon ?? ""
                        toolTip: entry.control?.toolTip ?? ""
                        checked: entry.control?.checked ?? false
                        onClicked: entry.control?.clicked()

                        // A button drawn with a letter (view along a, b, c) has no icon: its letter, in its colour.
                        EaElements.Label {
                            anchors.centerIn: parent
                            visible: buttonCopy.fontIcon === ""
                            font.family: EaStyle.Fonts.ptSansBold.name
                            font.bold: true
                            font.pixelSize: EaStyle.Sizes.fontPixelSize * 1.15
                            color: entry.control?.letterColor ?? EaStyle.Colors.themeForeground
                            text: String(entry.control?.objectName).split(".").pop()
                        }
                    }
                }
            }
        }
    }
}
