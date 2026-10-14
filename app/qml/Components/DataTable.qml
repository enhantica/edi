// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

EaComponents.ListView {
    id: table

    // The selection model needs an explicit empty model while a page is being attached.
    property var sourceModel: null
    model: sourceModel ?? null
    multiSelection: false
    // Rows are made when they come into view, never ahead of it: rows made ahead are built a few per frame in
    // the background, and a page's tables kept laying out for about a second after a project opened.
    cacheBuffer: 0
    readonly property real numberColumnWidth: Math.ceil(metrics.advanceWidth(String(Math.max(1, count)))) + AppSizes.fieldSpacing * 2
    property int modelRevision: 0
    // Long IDs and paths must leave room for the numeric cells and row controls.
    property real maximumTextColumnShare: 0.25
    // Each measured role's text width per row. An update measures only the rows it names, and the column
    // only changes when one of those widths did: a scan's rows update one by one, hundreds of times.
    property var rowWidths: ({})

    function textWidth(row: int, role: string): real {
        const text = typeof model.text === "function" ? model.text(row, role) : typeof model.get === "function" ? String(model.get(row)[role] ?? "") : "";
        return metrics.advanceWidth(text);
    }
    // The width of `text` in the table's font.
    function advance(text: string): real {
        return metrics.advanceWidth(text);
    }
    function textColumnWidth(role: string, title: string): real {
        const revision = modelRevision;
        let widths = rowWidths[role];
        if (!widths || widths.length !== count) {
            widths = [];
            for (let row = 0; model && row < count; ++row)
                widths.push(textWidth(row, role));
            rowWidths[role] = widths;
        }
        const result = widths.reduce((widest, measured) => Math.max(widest, measured), metrics.advanceWidth(title));
        return Math.min(Math.ceil(result) + AppSizes.fieldSpacing * 2, width * maximumTextColumnShare);
    }
    // Cleared in place: the bindings that read the cache depend on modelRevision, never on the cache itself.
    function forgetWidths() {
        for (const role in rowWidths)
            delete rowWidths[role];
    }
    function remeasure() {
        forgetWidths();
        modelRevision++;
    }

    onModelChanged: forgetWidths()

    FontMetrics {
        id: metrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        onFontChanged: table.remeasure()
    }
    Connections {
        target: table.model
        ignoreUnknownSignals: true
        function onDataChanged(topLeft, bottomRight) {
            let changed = false;
            for (const role in table.rowWidths) {
                const widths = table.rowWidths[role];
                for (let row = topLeft.row; row <= bottomRight.row && row < widths.length; ++row) {
                    const measured = table.textWidth(row, role);
                    if (measured !== widths[row]) {
                        widths[row] = measured;
                        changed = true;
                    }
                }
            }
            if (changed)
                table.modelRevision++;
        }
        function onCountChanged() {
            table.remeasure();
        }
        function onModelReset() {
            table.remeasure();
        }
        function onRowsMoved() {
            table.remeasure();
        }
        function onLayoutChanged() {
            table.remeasure();
        }
    }
}
