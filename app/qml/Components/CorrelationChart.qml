// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Correlations tab's chart: the last fit's parameter correlations for the shown experiment, drawn as
// diffraction-lib's correlation heatmap (display/plotters/plotly.py plot_correlation_heatmap): the lower triangle of
// square cells with the diagonal left blank, coloured on a diverging scale from red at -1 through the chart's
// background at 0 to blue at 1, with lines between the cells, a frame, the parameters' names along both edges and a
// colour bar. A cell shows its value when there is room, and as a tool tip. The toolbar sets the smallest absolute
// correlation shown and the most parameters shown (CorrelationViewModel).
Item {
    id: chart

    objectName: "correlations"

    property ProjectViewModel project: null
    readonly property CorrelationViewModel correlations: project ? project.correlations : null
    property bool shown: true

    readonly property real em: EaStyle.Sizes.fontPixelSize
    readonly property real sideMargin: AppSizes.mainAreaMargin
    readonly property real toolbarRightInset: sideMargin

    // diffraction-lib's colour scale (plotly.py _correlation_colorscale_for_background) and its cell lines.
    readonly property color negativeColor: "#d73027"
    readonly property color positiveColor: "#4575b4"
    readonly property color lineColor: EaStyle.Colors.chartAxis

    readonly property var labels: correlations ? correlations.labels : []
    readonly property var values: correlations ? correlations.values : []
    readonly property int count: labels.length

    // A cell's value; NaN outside the values, which can trail the labels by one change.
    function valueAt(index: int): real {
        return index >= 0 && index < values.length ? values[index] : NaN;
    }

    // The colour of a coefficient: the background mixed towards red or blue by its size.
    function cellColor(value: real): color {
        const background = EaStyle.Colors.chartBackground;
        const end = value < 0 ? negativeColor : positiveColor;
        const share = Math.min(1, Math.abs(value));
        return Qt.rgba(background.r + (end.r - background.r) * share, background.g + (end.g - background.g) * share, background.b + (end.b - background.b) * share, 1);
    }

    Rectangle {
        anchors.fill: parent
        color: EaStyle.Colors.chartBackground
    }

    // The toolbar: the correlation level and the number of parameters.
    Row {
        id: toolbar

        x: chart.sideMargin
        y: chart.em
        height: AppSizes.toolbarControlSize
        spacing: AppSizes.toolbarSpacing * 2

        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            color: EaStyle.Colors.chartLabels
            text: qsTr("Correlation level")
        }
        EaElements.TextField {
            id: levelField

            objectName: "correlations.toolbar.level"
            width: chart.em * 4
            height: AppSizes.toolbarControlSize
            horizontalAlignment: TextInput.AlignRight
            enabled: chart.correlations !== null
            validator: DoubleValidator {
                bottom: 0
                top: 1
                decimals: 2
                notation: DoubleValidator.StandardNotation
                locale: "C"
            }
            text: chart.correlations ? chart.correlations.level.toFixed(2) : ""
            onEditingFinished: {
                const level = Number(text);
                if (!isNaN(level))
                    chart.correlations.level = level;
                text = Qt.binding(() => chart.correlations ? chart.correlations.level.toFixed(2) : "");
            }
            EaElements.ToolTip {
                text: qsTr("The smallest absolute correlation shown, 0 to 1: weaker pairs are left blank")
                visible: levelField.hovered && EaGlobals.Vars.showToolTips
            }
        }
        Item {
            width: chart.em
            height: 1
        }
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            color: EaStyle.Colors.chartLabels
            text: qsTr("Parameters")
        }
        EaElements.TextField {
            id: countField

            objectName: "correlations.toolbar.parameters"
            width: chart.em * 3
            height: AppSizes.toolbarControlSize
            horizontalAlignment: TextInput.AlignRight
            enabled: chart.correlations !== null
            validator: IntValidator {
                bottom: 2
                top: 999
            }
            text: chart.correlations ? String(chart.correlations.maxParameters) : ""
            onEditingFinished: {
                const count = parseInt(text);
                if (!isNaN(count))
                    chart.correlations.maxParameters = count;
                text = Qt.binding(() => chart.correlations ? String(chart.correlations.maxParameters) : "");
            }
            EaElements.ToolTip {
                text: qsTr("The most parameters shown: those most correlated with another")
                visible: countField.hovered && EaGlobals.Vars.showToolTips
            }
        }
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            visible: chart.correlations !== null && chart.correlations.available > 0
            color: EaStyle.Colors.themeForegroundMinor
            text: chart.correlations ? qsTr("of %1").arg(chart.correlations.available) : ""
        }
    }

    FontMetrics {
        id: metrics

        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }

    // The matrix's place: the names on the left and below, the colour bar on the right, square cells as large as fit.
    Item {
        id: area

        readonly property real widestLabel: {
            let widest = 0;
            for (let i = 0; i < chart.count; ++i)
                widest = Math.max(widest, metrics.advanceWidth(chart.labels[i]));
            return Math.ceil(widest);
        }
        readonly property real rowLabelWidth: Math.min(widestLabel, width * 0.4) + chart.em * 0.5
        readonly property real colourBarWidth: chart.em * 4.5
        readonly property real flatLabelHeight: chart.em * 2
        readonly property real gridWidth: width - rowLabelWidth - colourBarWidth
        readonly property real flatCell: chart.count > 0 ? Math.floor(Math.min(gridWidth, height - flatLabelHeight) / chart.count) : 0
        // The column names stand level when each fits its cell, else at 45 degrees, as long as the widest needs.
        readonly property bool slanted: widestLabel > flatCell * 0.95
        readonly property real columnLabelHeight: slanted ? Math.min(widestLabel, width * 0.4) * Math.SQRT1_2 + chart.em * 1.5 : flatLabelHeight
        readonly property real cell: chart.count > 0 ? Math.max(0, Math.floor(Math.min(gridWidth, height - columnLabelHeight) / chart.count)) : 0
        readonly property real side: cell * chart.count

        x: chart.sideMargin
        y: toolbar.y + toolbar.height + chart.sideMargin
        width: parent.width - 2 * chart.sideMargin
        height: parent.height - y - chart.em
        visible: chart.count >= 2 && cell > 0

        Item {
            id: grid

            objectName: "correlations.grid"
            x: area.rowLabelWidth + (area.gridWidth - area.side) / 2
            width: area.side
            height: area.side

            Repeater {
                objectName: "correlations.cells"
                model: chart.count * chart.count
                delegate: Rectangle {
                    required property int index
                    readonly property int row: Math.floor(index / chart.count)
                    readonly property int column: index % chart.count
                    readonly property real value: chart.valueAt(index)

                    x: column * area.cell
                    y: row * area.cell
                    width: area.cell
                    height: area.cell
                    color: isNaN(value) ? "transparent" : chart.cellColor(value)

                    EaElements.Label {
                        anchors.centerIn: parent
                        visible: !isNaN(parent.value) && area.cell >= chart.em * 2.6
                        color: Math.abs(parent.value) >= 0.5 ? "#f5f5f5" : EaStyle.Colors.chartLabels
                        text: isNaN(parent.value) ? "" : parent.value.toFixed(2)
                    }
                }
            }
            // The lines between the cells, then the frame, twice as wide.
            Repeater {
                model: Math.max(0, chart.count - 1)
                delegate: Item {
                    required property int index
                    Rectangle {
                        x: Math.round((parent.index + 1) * area.cell)
                        width: 1
                        height: grid.height
                        color: chart.lineColor
                    }
                    Rectangle {
                        y: Math.round((parent.index + 1) * area.cell)
                        width: grid.width
                        height: 1
                        color: chart.lineColor
                    }
                }
            }
            Rectangle {
                anchors.fill: parent
                anchors.margins: -1
                color: "transparent"
                border.color: chart.lineColor
                border.width: 2
            }

            // The value of the cell under the pointer.
            MouseArea {
                id: pointer

                readonly property int row: containsMouse ? Math.min(chart.count - 1, Math.floor(mouseY / area.cell)) : -1
                readonly property int column: containsMouse ? Math.min(chart.count - 1, Math.floor(mouseX / area.cell)) : -1
                readonly property real value: row >= 0 && column >= 0 ? chart.valueAt(row * chart.count + column) : NaN

                objectName: "correlations.pointer"
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton

                Item {
                    x: (pointer.column + 0.5) * area.cell
                    y: pointer.row * area.cell

                    EaElements.ToolTip {
                        objectName: "correlations.toolTip"
                        visible: pointer.containsMouse && !isNaN(pointer.value)
                        text: visible ? qsTr("%1\n%2\ncorrelation: %3").arg(chart.labels[pointer.column]).arg(chart.labels[pointer.row]).arg(pointer.value.toFixed(2)) : ""
                    }
                }
            }
        }

        // The rows' names, right-aligned against the matrix.
        Repeater {
            model: chart.count
            delegate: EaElements.Label {
                required property int index
                x: grid.x - width - chart.em * 0.5
                y: grid.y + (index + 0.5) * area.cell - height / 2
                width: Math.min(implicitWidth, area.rowLabelWidth - chart.em * 0.5)
                elide: Text.ElideLeft
                horizontalAlignment: Text.AlignRight
                color: EaStyle.Colors.chartLabels
                text: chart.labels[index] ?? ""
            }
        }
        // The columns' names below the matrix, level or slanted down to the left from under their cell.
        Repeater {
            model: chart.count
            delegate: EaElements.Label {
                required property int index
                width: Math.min(implicitWidth, area.width * 0.4)
                elide: Text.ElideLeft
                color: EaStyle.Colors.chartLabels
                text: chart.labels[index] ?? ""
                transformOrigin: Item.TopRight
                rotation: area.slanted ? -45 : 0
                x: area.slanted ? grid.x + (index + 0.5) * area.cell - width : grid.x + (index + 0.5) * area.cell - width / 2
                y: grid.y + area.side + chart.em * 0.5
            }
        }

        // The colour bar: 1 at the top, -1 at the bottom.
        Item {
            id: colourBar

            x: grid.x + area.side + chart.em * 1.5
            width: chart.em
            height: area.side

            Rectangle {
                anchors.fill: parent
                border.color: chart.lineColor
                border.width: 1
                gradient: Gradient {
                    GradientStop {
                        position: 0
                        color: chart.positiveColor
                    }
                    GradientStop {
                        position: 0.5
                        color: EaStyle.Colors.chartBackground
                    }
                    GradientStop {
                        position: 1
                        color: chart.negativeColor
                    }
                }
            }
            Repeater {
                model: [1, 0.5, 0, -0.5, -1]
                delegate: EaElements.Label {
                    required property real modelData
                    x: colourBar.width + chart.em * 0.4
                    y: (1 - modelData) / 2 * colourBar.height - height / 2
                    color: EaStyle.Colors.chartLabels
                    text: modelData.toFixed(1)
                }
            }
        }
    }

    EaElements.Label {
        objectName: "correlations.empty"
        anchors.centerIn: parent
        visible: !area.visible
        width: Math.min(implicitWidth, parent.width - 2 * chart.sideMargin)
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
        color: EaStyle.Colors.themeForegroundMinor
        text: chart.correlations ? chart.correlations.emptyText : ""
    }
}
