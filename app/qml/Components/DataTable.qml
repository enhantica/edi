// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

EaComponents.ListView {
    id: table

    multiSelection: false
    readonly property real numberColumnWidth: Math.ceil(Math.max(metrics.advanceWidth("id"), metrics.advanceWidth(String(Math.max(1, count))))) + AppSizes.fieldSpacing * 2
    property int modelRevision: 0

    function textColumnWidth(role: string, title: string): real {
        const revision = modelRevision;
        let result = metrics.advanceWidth(title);
        if (model) {
            for (let row = 0; row < count; ++row) {
                const text = typeof model.text === "function" ? model.text(row, role) : typeof model.get === "function" ? String(model.get(row)[role] ?? "") : "";
                result = Math.max(result, metrics.advanceWidth(text));
            }
        }
        return Math.ceil(result) + AppSizes.fieldSpacing * 2;
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
