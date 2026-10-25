// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A chart's toolbar (edi ADR-0041 §7; the owner, 2026-10-24), the one rule for the Pattern, Stacked and Map toolbars:
// every control on one line when they all fit; otherwise every combobox on the lines above, as many as fit on each,
// and every button on the last line. Each line is centred between `leftEdge` and `rightEdge`, the span of the block
// selector row above the chart, so the selector and every toolbar line share one centre (the owner, 2026-10-25). A child
// with `closedTexts` (ToolbarComboBox) is a combobox; any other visible child is a button, or a row of them kept
// whole.
Item {
    id: lines

    // The room the lines may take, in this item's coordinates, and its middle, where each line is centred.
    property real leftEdge: 0
    property real rightEdge: width
    readonly property real centre: (leftEdge + rightEdge) / 2
    readonly property real spacing: AppSizes.toolbarSpacing
    // Between the comboboxes and the buttons on one line.
    readonly property real groupSpacing: EaStyle.Sizes.fontPixelSize * 0.5 + 2 * AppSizes.toolbarSpacing
    // The controls shown, and every width the layout depends on.
    readonly property var units: Array.from(children).filter(child => child.visible)
    readonly property string measure: [centre, leftEdge, rightEdge].concat(units.map(unit => unit.width)).join(",")
    // How many lines the controls take.
    property int lineCount: 0

    function isComboBox(unit) {
        return unit.closedTexts !== undefined;
    }
    function widthOf(row, gap) {
        return row.reduce((sum, unit, index) => sum + unit.width + (index > 0 ? gap : 0), 0);
    }
    function layout() {
        const boxes = units.filter(unit => isComboBox(unit));
        const buttons = units.filter(unit => !isComboBox(unit));
        const room = rightEdge - leftEdge;
        const rows = [];
        const together = widthOf(boxes, spacing) + widthOf(buttons, spacing) + (boxes.length > 0 && buttons.length > 0 ? groupSpacing : 0);
        if (together <= room) {
            rows.push({
                "units": boxes.concat(buttons),
                "gaps": boxes.map((unit, index) => index > 0 ? spacing : 0).concat(buttons.map((unit, index) => index > 0 ? spacing : boxes.length > 0 ? groupSpacing : 0))
            });
        } else {
            // As many comboboxes as fit on each line, then the buttons on their own.
            let row = null;
            for (const box of boxes) {
                if (row === null || widthOf(row.units.concat([box]), spacing) > room) {
                    row = {
                        "units": [],
                        "gaps": []
                    };
                    rows.push(row);
                }
                row.gaps.push(row.units.length > 0 ? spacing : 0);
                row.units.push(box);
            }
            if (buttons.length > 0)
                rows.push({
                    "units": buttons,
                    "gaps": buttons.map((unit, index) => index > 0 ? spacing : 0)
                });
        }
        let top = 0;
        for (const each of rows) {
            const widthNow = each.units.reduce((sum, unit, index) => sum + unit.width + each.gaps[index], 0);
            let x = Math.round(Math.max(leftEdge, Math.min(rightEdge - widthNow, centre - widthNow / 2)));
            for (let i = 0; i < each.units.length; ++i) {
                x += each.gaps[i];
                each.units[i].x = x;
                each.units[i].y = top;
                x += each.units[i].width;
            }
            top += AppSizes.toolbarControlSize + AppSizes.toolbarSpacing;
        }
        lineCount = rows.length;
        implicitHeight = Math.max(0, top - AppSizes.toolbarSpacing);
    }

    onMeasureChanged: Qt.callLater(layout)
    Component.onCompleted: layout()
}
