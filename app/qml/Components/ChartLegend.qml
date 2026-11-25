// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A chart's legend (easydiffractionbeta's QtCharts1dTab.qml; edi ADR-0017 §15): one line per series in the
// series' colour — its mark and its name, and for a structure's ticks "Bragg peaks", the structure icon and
// the structure's name — in the order the core's presentation lists them.
Rectangle {
    id: legend

    // The rows: the chart controller's legend model, with the roles `label`, `color`, `mark`, `markWidth`, `bragg`,
    // `labelTexts` and `labelColors` (the label's pieces and their colours, drawn in place of `label` when there are
    // any).
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
    // A click on a row hides its curve or shows it again (the owner, 2026-10-25, as plotly's legend): `toggled` gives
    // the row's key, and a hidden row is drawn in the disabled colour. A legend without curves to hide leaves it off.
    // The widest an entry may be (0: as wide as it reads); a longer one is cut in its middle, its whole text in a tooltip.
    // The legend is as wide as its entries read (the owner, 2026-11-23): only a datablock's name longer than this many
    // characters is cut, in its middle, its full name in the entry's tooltip; a series' own label (Measured, Total
    // calculated, Background, Residual) never is.
    property int nameBudget: 20
    // A chart's own limit on every entry (0: none), as the Evolution chart's parameter names have.
    property real maximumLabelWidth: 0
    readonly property var fixedSeries: ["meas", "calc", "bkg", "resid"]
    FontMetrics {
        id: nameMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }
    property bool toggles: false

    signal toggled(string key)

    // A click at (x, y) in `item`, the chart's pointer area, on a row: its curve hidden or shown again. The legend takes
    // no press, so a drag that starts on it still zooms, and the pointer area passes its clicks here; true when a row
    // took the click.
    function toggleAt(item, x, y) {
        return ApplicationInfo.legendToggleAt(item, x, y);
    }

    // A label's pieces as one styled text, each coloured piece a span: spaced as the text itself, as the residual axis
    // title is, never by the line's gaps between pieces.
    function richLabel(pieces) {
        return ApplicationInfo.legendRichLabel(pieces);
    }

    // An entry's mark: an element's is the atom icon the Atom sites table shows, a series' a drawn line or tick.
    function markPiece(mark, width, color) {
        return ApplicationInfo.legendMarkPiece(mark, width, color);
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
            model: legend.visible ? legend.entries : null
            delegate: IconLine {
                id: entry

                required property string label
                required property color color
                required property string mark
                required property bool bragg
                required property bool magnetic
                required property real markWidth
                required property list<string> labelTexts
                required property list<string> labelColors
                required property bool selected
                required property string key
                required property bool hidden

                objectName: "chart.legend.entry"
                height: legend.rowHeight
                // The name the row carries (its last text), unless the row is a series' own label.
                readonly property string named: legend.fixedSeries.includes(key) ? "" : labelTexts.length > 0 ? labelTexts[labelTexts.length - 1] : label
                readonly property real nameLimit: named.length > legend.nameBudget ? otherWidth + Math.ceil(nameMetrics.advanceWidth(named.slice(0, legend.nameBudget / 2) + "…" + named.slice(-(legend.nameBudget / 2 - 1)))) : 0
                maximumWidth: legend.maximumLabelWidth > 0 && nameLimit > 0 ? Math.min(nameLimit, legend.maximumLabelWidth) : Math.max(nameLimit, legend.maximumLabelWidth)
                elide: Text.ElideMiddle
                textColor: hidden ? legend.colors.themeForegroundDisabled : color
                // A hidden entry keeps its own pieces, its mark or icon included, each in the disabled colour (the
                // owner, 2026-10-25).
                segments: ApplicationInfo.legendSegments()

                // The row's hover cue only: no button, so a press goes on to the chart's pointer area, which passes a
                // click back (toggleAt).
                MouseArea {
                    id: entryHover
                    objectName: "chart.legend.toggle"
                    anchors.fill: parent
                    enabled: legend.toggles
                    acceptedButtons: Qt.NoButton
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    EaElements.ToolTip {
                        requested: entryHover.containsMouse
                        text: (entry.fullWidth > entry.width + 0.5 ? entry.label + "\n" : "") + (entry.hidden ? qsTr("Click to show") : qsTr("Click to hide"))
                    }
                }
                // A cut name shows in full on hover whether or not the legend toggles (a report's legend does not).
                HoverHandler {
                    id: nameHover
                    enabled: !legend.toggles
                }
                EaElements.ToolTip {
                    requested: nameHover.hovered && entry.fullWidth > entry.width + 0.5
                    text: entry.label
                }
            }
        }
    }
}
