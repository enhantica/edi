// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

// The theme colours a figure (a pattern chart, a structure view, their legends) draws with: EasyApp's, or with
// `light` set their light-theme values whatever the app's theme, as a PDF's figures are drawn for print.
QtObject {
    property bool light: false

    readonly property bool isDarkPalette: !light && EaStyle.Colors.isDarkPalette
    readonly property color themeForeground: light ? "#333" : EaStyle.Colors.themeForeground
    readonly property color themeForegroundMinor: light ? "#aaa" : EaStyle.Colors.themeForegroundMinor
    readonly property color themeForegroundDisabled: light ? "#bbb" : EaStyle.Colors.themeForegroundDisabled
    readonly property color appBorder: light ? "#ddd" : EaStyle.Colors.appBorder
    readonly property color mainContentBackgroundHalfTransparent: light ? "#E6ffffff" : EaStyle.Colors.mainContentBackgroundHalfTransparent
    readonly property color chartBackground: light ? "#fff" : EaStyle.Colors.chartBackground
    readonly property color chartAxis: light ? "#ddd" : EaStyle.Colors.chartAxis
    readonly property color chartGridLine: light ? "#eee" : EaStyle.Colors.chartGridLine
    readonly property color chartLabels: light ? "#333" : EaStyle.Colors.chartLabels
    readonly property color blue: light ? "#39abdf" : EaStyle.Colors.blue
    readonly property color red: light ? "#FF5722" : EaStyle.Colors.red
    readonly property color green: light ? "#7aaa42" : EaStyle.Colors.green
    readonly property color grey: light ? "#666" : EaStyle.Colors.grey
}
