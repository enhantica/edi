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
        ++laidOut;
    }
    // The lines' outer edges once laid out, in this item's coordinates: where the block selector row above lines up
    // (the owner, 2026-11-16). Counted up after each layout, so the edges are read again.
    property int laidOut: 0
    // Over the placed controls and the More button: a control moved into the popup is no longer the row's.
    function extent() {
        let low = Infinity, high = -Infinity;
        const items = units.map(unit => unit.item).concat([moreButton]);
        for (const item of items) {
            // A control in the popup stays a child, parked far to the left (ToolbarRow.place).
            if (!item || !item.visible || item.width <= 0 || item.parent !== lines || item.x < -1000 || overflow.indexOf(item) >= 0)
                continue;
            low = Math.min(low, item.x);
            high = Math.max(high, item.x + item.width);
        }
        return isFinite(low) && high > low ? [low, high] : [leftEdge, rightEdge];
    }
    readonly property var contentSpan: laidOut >= 0 && units.length >= 0 && overflow.length >= 0 && width >= 0 ? extent() : [leftEdge, rightEdge]

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
                    // The copy is of the control's own kind, so it looks and sizes as it does in the row: the Map's
                    // colour-map box keeps its colour bars.
                    readonly property bool colourMap: control?.maps !== undefined
                    readonly property bool box: control?.closedTexts !== undefined && !colourMap

                    visible: !!control && lines.overflow.indexOf(control) >= 0
                    width: colourMap ? mapCopy.width : box ? boxCopy.width : buttonCopy.width
                    height: AppSizes.toolbarControlSize

                    ToolbarComboBox {
                        id: boxCopy

                        objectName: entry.box ? entry.control?.objectName + ".overflow" : ""
                        visible: entry.box
                        enabled: entry.control?.enabled ?? false
                        toolTip: entry.control?.toolTip ?? ""
                        model: entry.box ? entry.control.model : []
                        closedTexts: entry.box ? entry.control.closedTexts : []
                        closedOnly: entry.box && entry.control.closedOnly
                        fitShown: entry.box && entry.control.fitShown
                        shownIndex: entry.box ? entry.control.currentIndex : 0
                        onActivated: index => entry.control?.activated(index)
                    }
                    ColourMapComboBox {
                        id: mapCopy

                        objectName: entry.colourMap ? entry.control?.objectName + ".overflow" : ""
                        visible: entry.colourMap
                        enabled: entry.control?.enabled ?? false
                        toolTip: entry.control?.toolTip ?? ""
                        model: entry.colourMap ? entry.control.model : []
                        closedTexts: entry.colourMap ? entry.control.closedTexts : []
                        closedOnly: entry.colourMap && entry.control.closedOnly
                        fitShown: entry.colourMap && entry.control.fitShown
                        maps: entry.colourMap ? entry.control.maps : []
                        direction: entry.colourMap ? entry.control.direction : "auto"
                        chartBackground: entry.colourMap ? entry.control.chartBackground : "white"
                        dark: entry.colourMap && entry.control.dark
                        shownIndex: entry.colourMap ? entry.control.currentIndex : 0
                        onActivated: index => entry.control?.activated(index)
                    }
                    ChartToolButton {
                        id: buttonCopy

                        objectName: entry.box || entry.colourMap ? "" : entry.control?.objectName + ".overflow"
                        visible: !entry.box && !entry.colourMap
                        enabled: entry.control?.enabled ?? false
                        available: entry.control?.available ?? true
                        fontIcon: entry.control?.fontIcon ?? ""
                        toolTip: entry.control?.toolTip ?? ""
                        checked: entry.control?.checked ?? false
                        alert: entry.control?.alert ?? false
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
