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
    // A main-view chart's toolbar starts after the block selector when the two share a row (AppSizes.selectorRowReserve,
    // measured from leftEdge, where the selector starts).
    property bool sharesSelectorRow: true
    readonly property real reservedLeft: sharesSelectorRow && EaStyle.Sizes.sideBarBelow ? AppSizes.selectorRowReserve : 0
    // The row's width with every control in it (ToolbarRow.place), and whether its chart is the one shown: the shown
    // one tells the block selector how much of a shared row it needs.
    property real naturalWidth: 0
    readonly property bool chartShown: isShown(lines.parent) && lines.visible
    function isShown(chart: var): bool {
        return chart !== null && chart.shown === true;
    }
    Binding {
        target: AppSizes
        property: "toolbarNaturalWidth"
        value: lines.naturalWidth
        when: lines.sharesSelectorRow && lines.chartShown && lines.naturalWidth > 0
        restoreMode: Binding.RestoreNone
    }
    property real rightEdge: width
    readonly property real centre: (leftEdge + rightEdge) / 2
    readonly property real spacing: AppSizes.toolbarSpacing
    readonly property real groupSpacing: EaStyle.Sizes.fontPixelSize * 0.5 + 2 * AppSizes.toolbarSpacing
    // Always one line now; kept for the views that read it.
    readonly property int lineCount: 1
    // Every control, in row order: {item, group, movable}; and those in the popup.
    property var units: []
    property var overflow: []
    readonly property string measure: [leftEdge, rightEdge, reservedLeft, visible].concat(units.map(unit => unit.item.visible ? unit.item.width : -1)).join(",")

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

            Repeater {
                model: lines.overflow

                delegate: Item {
                    id: entry

                    required property var modelData
                    readonly property bool box: modelData.closedTexts !== undefined
                    // A colour map's box keeps its gradients in the popup too: copied as itself (the owner, 2026-11-17).
                    readonly property bool colourMap: box && modelData.maps !== undefined

                    width: colourMap ? mapCopy.width : box ? boxCopy.width : buttonCopy.width
                    height: AppSizes.toolbarControlSize

                    ColourMapComboBox {
                        id: mapCopy

                        objectName: entry.colourMap ? entry.modelData.objectName + ".overflow" : ""
                        visible: entry.colourMap
                        enabled: entry.colourMap && entry.modelData.enabled
                        toolTip: entry.colourMap ? entry.modelData.toolTip ?? "" : ""
                        maps: entry.colourMap ? entry.modelData.maps : []
                        direction: entry.colourMap ? entry.modelData.direction : "auto"
                        chartBackground: entry.colourMap ? entry.modelData.chartBackground : "white"
                        dark: entry.colourMap && entry.modelData.dark
                        fitShown: entry.colourMap && entry.modelData.fitShown
                        shownIndex: entry.colourMap ? entry.modelData.currentIndex : 0
                        onActivated: index => entry.modelData.activated(index)
                    }
                    ToolbarComboBox {
                        id: boxCopy

                        objectName: entry.box && !entry.colourMap ? entry.modelData.objectName + ".overflow" : ""
                        visible: entry.box && !entry.colourMap
                        enabled: entry.modelData.enabled
                        toolTip: entry.modelData.toolTip ?? ""
                        model: entry.box ? entry.modelData.model : []
                        closedTexts: entry.box ? entry.modelData.closedTexts : []
                        closedOnly: entry.box && entry.modelData.closedOnly
                        fitShown: entry.box && entry.modelData.fitShown
                        shownIndex: entry.box ? entry.modelData.currentIndex : 0
                        onActivated: index => entry.modelData.activated(index)
                    }
                    ChartToolButton {
                        id: buttonCopy

                        objectName: entry.box ? "" : entry.modelData.objectName + ".overflow"
                        visible: !entry.box
                        enabled: entry.modelData.enabled
                        available: entry.modelData.available ?? true
                        fontIcon: entry.modelData.fontIcon ?? ""
                        toolTip: entry.modelData.toolTip ?? ""
                        checked: entry.modelData.checked ?? false
                        alert: entry.modelData.alert ?? false
                        onClicked: entry.modelData.clicked()

                        // A button drawn with a letter (view along a, b, c) has no icon: its letter, in its colour.
                        EaElements.Label {
                            anchors.centerIn: parent
                            visible: buttonCopy.fontIcon === ""
                            font.family: EaStyle.Fonts.ptSansBold.name
                            font.bold: true
                            font.pixelSize: EaStyle.Sizes.fontPixelSize * 1.15
                            color: entry.modelData.letterColor ?? EaStyle.Colors.themeForeground
                            text: String(entry.modelData.objectName).split(".").pop()
                        }
                    }
                }
            }
        }
    }
}
