// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// The colours edi gives datablocks and elements (edi ADR-0017 §8), all from the base's EaStyle tokens except
// the element colours, which are the core's element table (data/elements, Jmol or VESTA as the structure view
// shows them; edi ADR-0022 §4).
QtObject {
    id: colors

    // The hover highlight of a clickable status-bar item: the foreground at a tenth.
    readonly property color hoverHighlight: Qt.rgba(EaStyle.Colors.themeForeground.r, EaStyle.Colors.themeForeground.g, EaStyle.Colors.themeForeground.b, 0.1)

    // A structure's colour by its place among the project's, from the colour scheme's structure colours (edi ADR-0038):
    // the first ones in order, or past five a gradient along the order.
    function structure(index) {
        const count = Session.project ? Math.max(Session.project.structures.count, 1) : 1;
        return index >= 0 ? ApplicationInfo.structureColour(Preferences.structureColours, index, count, EaStyle.Colors.isDarkPalette) : EaStyle.Colors.themeForegroundMinor;
    }

    // An experiment's colour by its place among the project's, from the colour scheme's measured colours: the first
    // ones in order, or past five a gradient along the order. None is a structure's colour.
    // `dark` picks the dark theme's colour; without it, the app's theme decides (a PDF's figure asks for the light one).
    function experiment(index, dark) {
        const count = Session.project ? Math.max(Session.project.experiments.count, 1) : 1;
        const darkColour = dark === undefined ? EaStyle.Colors.isDarkPalette : dark;
        return index >= 0 ? ApplicationInfo.patternColour(Preferences.patternColours, index, count, darkColour) : EaStyle.Colors.themeForegroundMinor;
    }

    // A block's colour by its kind ("structure" or "experiment") and place.
    function block(kind, index) {
        return kind === "structure" ? colors.structure(index) : kind === "experiment" ? colors.experiment(index) : EaStyle.Colors.themeForegroundMinor;
    }

    // The structure view's colour scheme ("jmol" or "vesta"), which every table's atom icons follow too.
    readonly property string elementScheme: Session.project && Session.project.structureViewOptions ? Session.project.structureViewOptions.colorScheme : "jmol"

    // An element's colour from a type symbol: the core's element table (edi ADR-0022 §4), the colour of the
    // symbol's element ("162Dy" is Dy, "Co2+" is Co, "2H" is H) in the structure view's scheme; the minor
    // foreground colour for an element the table does not have. Drawn flat, so made readable on `background`, by
    // default the theme's main content background, which tables and lists sit on (edi ADR-0047).
    function element(typeSymbol, background) {
        const colour = ApplicationInfo.elementColor(String(typeSymbol), EaStyle.Colors.themeForegroundMinor, colors.elementScheme);
        return colors.readable(colour, background === undefined ? EaStyle.Colors.mainContentBackground : background);
    }

    // A colour drawn flat on `background`, moved to 3:1 contrast by its lightness alone (edi ADR-0047).
    function readable(colour, background) {
        return ApplicationInfo.readableColour(colour, background);
    }
}
