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

    // diffraction-lib's colour scale (plotly.py _correlation_colorscale_for_background).
    readonly property color negativeColor: "#d73027"
    readonly property color positiveColor: "#4575b4"

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

    // The toolbar: the correlation level and the number of parameters, each a box with its icon, name and an editable
    // number, set apart as the pattern chart's axis boxes are and at the row's right end, as its buttons are (owner,
    // 2026-10-11).
    Row {
        id: toolbar

        x: chart.width - chart.toolbarRightInset - width
        y: chart.em
        height: AppSizes.toolbarControlSize
        spacing: AppSizes.toolbarSpacing

        NumberBox {
            objectName: "correlations.toolbar.level"
            icon: "filter"
            label: qsTr("Correlation level:")
            toolTip: qsTr("The smallest absolute correlation shown, 0 to 1: weaker pairs are left blank")
            widestText: "0.00"
            shown: chart.correlations ? chart.correlations.level.toFixed(2) : ""
            validator: DoubleValidator {
                bottom: 0
                top: 1
                decimals: 2
                notation: DoubleValidator.StandardNotation
                locale: "C"
            }
            onCommitted: text => {
                const level = Number(text);
                if (!isNaN(level))
                    chart.correlations.level = level;
            }
        }
        NumberBox {
            objectName: "correlations.toolbar.parameters"
            icon: "list-ol"
            label: qsTr("Parameters:")
            toolTip: qsTr("The most parameters shown: those most correlated with another")
            widestText: "999"
            suffix: chart.correlations && chart.correlations.available > 0 ? qsTr("of %1").arg(chart.correlations.available) : ""
            shown: chart.correlations ? String(chart.correlations.maxParameters) : ""
            validator: IntValidator {
                bottom: 2
                top: 999
            }
            onCommitted: text => {
                const count = parseInt(text);
                if (!isNaN(count))
                    chart.correlations.maxParameters = count;
            }
        }
    }

    // A toolbar box as the pattern chart's axis boxes look (ToolbarComboBox): its name, then its number, which alone
    // is edited; a hover colours the number and the border only.
    component NumberBox: Rectangle {
        id: box

        // A Font Awesome name, drawn before the label.
        property string icon: ""
        property string label: ""
        property string toolTip: ""
        // The widest number the box shows, for its width.
        property string widestText: ""
        // The model's number as text; an edit is committed on Return or on leaving the number.
        property string shown: ""
        // Grey text after the number ("of 16"); empty: none.
        property string suffix: ""
        property alias validator: number.validator
        readonly property bool hovered: hover.hovered
        signal committed(string text)

        width: content.implicitWidth + chart.em * 1.75
        height: AppSizes.toolbarControlSize
        radius: 2
        enabled: chart.correlations !== null
        color: Qt.tint(EaStyle.Colors.contentBackground, EaStyle.Colors.appBarComboBoxBackground)
        border.color: !enabled ? EaStyle.Colors.themeBackgroundDisabled : box.hovered || number.activeFocus ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.appBarComboBoxBorder

        HoverHandler {
            id: hover
        }
        FontMetrics {
            id: numberMetrics

            font: number.font
        }
        Row {
            id: content

            x: chart.em * 0.75
            anchors.verticalCenter: parent.verticalCenter
            spacing: AppSizes.toolbarSpacing * 2

            // The name, the number and the count share the name's text baseline (owner, 2026-10-11).
            IconLine {
                id: name

                anchors.verticalCenter: parent.verticalCenter
                baselineOffset: numberMetrics.ascent
                textColor: box.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
                segments: [
                    {
                        "icon": box.icon
                    },
                    {
                        "text": box.label
                    }
                ]
            }
            TextInput {
                id: number

                objectName: box.objectName + ".number"
                width: Math.ceil(numberMetrics.advanceWidth(box.widestText))
                anchors.baseline: name.baseline
                horizontalAlignment: TextInput.AlignRight
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
                selectByMouse: true
                selectionColor: EaStyle.Colors.themeAccent
                selectedTextColor: EaStyle.Colors.themeBackground
                color: !box.enabled ? EaStyle.Colors.themeForegroundDisabled : box.hovered || activeFocus ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
                text: box.shown
                onEditingFinished: {
                    if (text !== box.shown)
                        box.committed(text);
                    text = Qt.binding(() => box.shown);
                }

                // The text cursor over the number, which is what is edited (owner, 2026-10-11).
                HoverHandler {
                    cursorShape: Qt.IBeamCursor
                }
            }
            EaElements.Label {
                anchors.baseline: name.baseline
                visible: box.suffix !== ""
                color: EaStyle.Colors.themeForegroundMinor
                text: box.suffix
            }
        }
        EaElements.ToolTip {
            text: box.toolTip
            visible: text !== "" && box.hovered && EaGlobals.Vars.showToolTips
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
        // Every k-th name on each axis, k as small as keeps neighbours a line apart: a row's names stand a cell apart,
        // the slanted column names a cell times sin 45° apart (owner, 2026-10-11). The tool tip names every cell.
        readonly property int rowLabelStep: cell > 0 ? Math.max(1, Math.ceil(metrics.height / cell)) : 1
        readonly property int columnLabelStep: cell > 0 && slanted ? Math.max(1, Math.ceil(metrics.height / (cell * Math.SQRT1_2))) : 1

        x: chart.sideMargin
        y: Math.round(toolbar.y + toolbar.height + chart.sideMargin)
        width: parent.width - 2 * chart.sideMargin
        height: parent.height - y - chart.em
        visible: chart.count >= 2 && cell > 0

        Item {
            id: grid

            objectName: "correlations.grid"
            x: Math.round(area.rowLabelWidth + (area.gridWidth - area.side) / 2)
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
            // The lines between the cells and the frame over them, as the pattern chart's grid and border (owner,
            // 2026-10-11).
            Repeater {
                model: Math.max(0, chart.count - 1)
                delegate: Item {
                    required property int index
                    Rectangle {
                        x: Math.round((parent.index + 1) * area.cell)
                        width: EaStyle.Sizes.borderThickness
                        height: grid.height
                        color: EaStyle.Colors.chartGridLine
                    }
                    Rectangle {
                        y: Math.round((parent.index + 1) * area.cell)
                        width: grid.width
                        height: EaStyle.Sizes.borderThickness
                        color: EaStyle.Colors.chartGridLine
                    }
                }
            }
            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: EaStyle.Colors.chartAxis
                border.width: EaStyle.Sizes.borderThickness
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
                visible: index % area.rowLabelStep === 0
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
                visible: index % area.columnLabelStep === 0
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

        // The colour bar: 1 at the top, -1 at the bottom, as high as the matrix and framed as it is, the frame drawn
        // over the gradient so it shows.
        Item {
            id: colourBar

            x: grid.x + area.side + Math.round(chart.em * 1.5)
            y: grid.y
            width: Math.round(chart.em)
            height: area.side

            Rectangle {
                anchors.fill: parent
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
            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: EaStyle.Colors.chartAxis
                border.width: EaStyle.Sizes.borderThickness
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
