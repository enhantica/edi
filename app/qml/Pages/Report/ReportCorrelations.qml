// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The report preview's correlation chart, from the model's `correlations`: the lower triangle the Correlations tab
// draws, each cell coloured from red at -1 through the background to blue at 1 and labelled with its value, the
// parameters numbered down the left and along the top. Every cell has a border, the empty ones on and above the
// diagonal too, and the labels and values are in the text colour (the owner, 2026-10-13).
Item {
    id: chart

    property var correlations: null
    readonly property var labels: correlations && correlations.labels ? correlations.labels : []
    readonly property var values: correlations && correlations.values ? correlations.values : []
    readonly property int count: labels.length
    readonly property real cell: EaStyle.Sizes.fontPixelSize * 3.2
    readonly property real labelWidth: {
        metrics.font;  // measured again when the font changes (a font that loads late)
        let widest = 0;
        for (const label of labels)
            widest = Math.max(widest, metrics.advanceWidth((labels.indexOf(label) + 1) + "  " + label));
        return Math.ceil(widest) + EaStyle.Sizes.fontPixelSize;
    }
    // diffraction-lib's colour scale, as the Correlations tab's (CorrelationChart).
    readonly property color negativeColor: "#d73027"
    readonly property color positiveColor: "#4575b4"

    function cellColor(value) {
        const background = EaStyle.Colors.chartBackground;
        const end = value < 0 ? negativeColor : positiveColor;
        const share = Math.min(1, Math.abs(value));
        return Qt.rgba(background.r + (end.r - background.r) * share, background.g + (end.g - background.g) * share, background.b + (end.b - background.b) * share, 1);
    }

    width: labelWidth + count * cell
    height: count > 0 ? (count + 1) * cell : empty.implicitHeight

    FontMetrics {
        id: metrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }

    EaElements.Label {
        id: empty
        visible: chart.count < 2
        color: EaStyle.Colors.themeForegroundMinor
        text: chart.correlations && chart.correlations.empty_text ? chart.correlations.empty_text : qsTr("No correlations yet")
    }
    // The lists themselves are the models, so a delegate holds its own label or value while a shorter list replaces it.
    Repeater {
        model: chart.labels
        delegate: EaElements.Label {
            required property string modelData
            required property int index
            y: chart.cell * (index + 1) + (chart.cell - height) / 2
            color: EaStyle.Colors.themeForeground
            text: (index + 1) + "  " + modelData
        }
    }
    Repeater {
        model: chart.labels
        delegate: EaElements.Label {
            required property int index
            x: chart.labelWidth + chart.cell * index + (chart.cell - width) / 2
            y: (chart.cell - height) / 2
            color: EaStyle.Colors.themeForeground
            text: index + 1
        }
    }
    Repeater {
        model: chart.values
        delegate: Rectangle {
            required property var modelData
            required property int index
            readonly property int row: Math.floor(index / chart.count)
            readonly property int column: index % chart.count
            readonly property var value: modelData
            readonly property bool shown: typeof value === "number" && isFinite(value)

            // One border width wider, so neighbours share a single line, as the report's tables have.
            x: chart.labelWidth + column * chart.cell
            y: (row + 1) * chart.cell
            width: chart.cell + EaStyle.Sizes.borderThickness
            height: chart.cell + EaStyle.Sizes.borderThickness
            color: shown ? chart.cellColor(value) : "transparent"
            border.width: EaStyle.Sizes.borderThickness
            border.color: EaStyle.Colors.appBorder

            // The text colour, light on the strongest cells' full colour.
            EaElements.Label {
                anchors.centerIn: parent
                color: Math.abs(parent.value) >= 0.5 ? "#f5f5f5" : EaStyle.Colors.themeForeground
                text: parent.shown ? parent.value.toFixed(2) : ""
            }
        }
    }
}
