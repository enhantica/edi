// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A chart's legend (easydiffractionbeta's QtCharts1dTab.qml; edi ADR-0017 §15): one line per series in the
// series' colour — its mark and its name, and for a structure's ticks "Bragg peaks", the structure icon and
// the structure's name — in the order the core's presentation lists them.
Rectangle {
    id: legend

    // The rows: the chart controller's legend model, with the roles `label`, `color`, `mark`, `markWidth`, `bragg`
    // and `labelSegments` (the label's coloured pieces, drawn in place of `label` when there are any).
    property ChartLegendModel entries: null
    // The theme colours of the chart it belongs to.
    property FigureColors colors: FigureColors {}
    // The name in the series' colour too, as a chart's legend shows it; the structure view's legend colours only
    // the mark, as a pale element colour (Ce, S) cannot be read on the view's background.
    property bool labelInColor: true
    // The box is at least this tall, its rows centred in it (the structure legend: a toolbar control's height).
    property real minimumHeight: 0
    // Each row's height.
    property real rowHeight: AppSizes.legendRowHeight

    // An entry's mark: an element's is the atom icon the Atom sites table shows, a series' a drawn line or tick.
    function markPiece(mark, width, color) {
        return mark === "atom" ? {
            "icon": "atom",
            "color": color
        } : {
            "mark": mark,
            "width": width,
            "color": color
        };
    }

    width: column.width
    height: Math.max(column.height, minimumHeight)
    color: legend.colors.mainContentBackgroundHalfTransparent
    border.color: legend.colors.chartGridLine
    border.width: EaStyle.Sizes.borderThickness

    Column {
        id: column

        anchors.verticalCenter: parent.verticalCenter
        leftPadding: EaStyle.Sizes.fontPixelSize
        rightPadding: EaStyle.Sizes.fontPixelSize
        topPadding: EaStyle.Sizes.fontPixelSize * 0.5
        bottomPadding: EaStyle.Sizes.fontPixelSize * 0.5

        Repeater {
            model: legend.entries
            delegate: IconLine {
                id: entry

                required property string label
                required property color color
                required property string mark
                required property bool bragg
                required property real markWidth
                required property var labelSegments

                objectName: "chart.legend.entry"
                height: legend.rowHeight
                textColor: color
                segments: bragg ? [legend.markPiece(mark, markWidth, color),
                    {
                        "text": qsTr("Bragg peaks")
                    },
                    {
                        "icon": "layer-group",
                        "color": color
                    },
                    {
                        "text": label
                    }
                ] : [legend.markPiece(mark, markWidth, color)].concat((labelSegments.length > 0 ? labelSegments : [{
                                "text": label,
                                "color": color
                            }]).map(piece => ({
                                "text": piece.text,
                                "color": legend.labelInColor && piece.color ? piece.color : legend.colors.themeForeground
                            })))
            }
        }
    }
}
