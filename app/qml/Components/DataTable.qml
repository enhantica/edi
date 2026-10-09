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
    readonly property real numberColumnWidth: Math.ceil(Math.max(metrics.advanceWidth("id"), metrics.advanceWidth(String(Math.max(1, count))))) + AppSizes.fieldSpacing * 2
    property int modelRevision: 0
    // Long IDs and paths must leave room for the numeric cells and row controls.
    property real maximumTextColumnShare: 0.25

    function textColumnWidth(role: string, title: string): real {
        const revision = modelRevision;
        let result = metrics.advanceWidth(title);
        if (model) {
            for (let row = 0; row < count; ++row) {
                const text = typeof model.text === "function" ? model.text(row, role) : typeof model.get === "function" ? String(model.get(row)[role] ?? "") : "";
                result = Math.max(result, metrics.advanceWidth(text));
            }
        }
        return Math.min(Math.ceil(result) + AppSizes.fieldSpacing * 2, width * maximumTextColumnShare);
    }

    FontMetrics {
        id: metrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }
    Connections {
        target: table.model
        ignoreUnknownSignals: true
        function onDataChanged() {
            table.modelRevision++;
        }
        function onCountChanged() {
            table.modelRevision++;
        }
        function onModelReset() {
            table.modelRevision++;
        }
    }
}
