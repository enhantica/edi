// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtGraphs

import EasyApplication.Gui.Style as EaStyle

// Every Qt Graphs chart's theme (edi ADR-0017 §15): Qt Graphs draws the series and nothing else. A chart draws its
// background, grid and border itself; Qt Graphs' own tick marks, axis lines and grid are shader effects two pixels
// wide, over the labels and the points, so they are transparent here on every axis. (The offscreen platform's
// software renderer never draws them, so only a capture on an OpenGL platform shows whether they are gone.) The
// colour scheme is fixed: every colour a chart shows is its own and follows the app's theme, while a scheme change
// makes Qt Graphs restore its own axis colours (the owner, 2026-10-02).
//
// The tick labels are in the app's font and size, as the axis titles are (the owner, 2026-10-26). Qt Graphs draws an
// axis's labels, and keeps room for them, in that axis's label font, not in `labelFont`: left unset, it is the
// platform's default font, larger in a browser than the app's.
GraphsTheme {
    colorScheme: GraphsTheme.ColorScheme.Light
    backgroundVisible: false
    plotAreaBackgroundVisible: false
    labelFont.family: EaStyle.Fonts.fontFamily
    labelFont.pixelSize: EaStyle.Sizes.fontPixelSize
    axisXLabelFont.family: EaStyle.Fonts.fontFamily
    axisXLabelFont.pixelSize: EaStyle.Sizes.fontPixelSize
    axisYLabelFont.family: EaStyle.Fonts.fontFamily
    axisYLabelFont.pixelSize: EaStyle.Sizes.fontPixelSize
    axisX.mainColor: "transparent"
    axisX.subColor: "transparent"
    axisY.mainColor: "transparent"
    axisY.subColor: "transparent"
    grid.mainColor: "transparent"
    grid.subColor: "transparent"
}
