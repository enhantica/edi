// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

EaComponents.ListView {
    id: table

    property int modelRevision: 0
    readonly property real numberColumnWidth: Math.ceil(Math.max(metrics.advanceWidth("id"), metrics.advanceWidth(String(Math.max(1, count))))) + AppSizes.fieldSpacing * 2

    function textColumnWidth(role: string, title: string): real {
        const revision = modelRevision;
        let result = metrics.advanceWidth(title);
        if (model && typeof model.text === "function") {
            for (let row = 0; row < count; ++row)
                result = Math.max(result, metrics.advanceWidth(model.text(row, role)));
        }
        return Math.ceil(result) + AppSizes.fieldSpacing * 2;
    }

    multiSelection: false

    FontMetrics {
        id: metrics

        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }
    Connections {
        function onCountChanged() {
            table.modelRevision++;
        }
        function onDataChanged() {
            table.modelRevision++;
        }
        function onModelReset() {
            table.modelRevision++;
        }

        ignoreUnknownSignals: true
        target: table.model
    }
}
