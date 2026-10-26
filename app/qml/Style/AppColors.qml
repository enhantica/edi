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

    // A block's colour from the figure palette (edi ADR-0038): the palette's colour at the block's position, which the
    // open project holds (a block keeps its position; a new one takes the next free). `dark` picks the dark theme's
    // colour; without it, the app's theme decides (a PDF's figure asks for the light one).
    function positioned(positions, index, dark) {
        const project = Session.project;
        if (!project || index < 0 || index >= positions.length)
            return EaStyle.Colors.themeForegroundMinor;
        return ApplicationInfo.figureColour(Preferences.colourScheme, positions[index], project.colourPositionCount, dark === undefined ? EaStyle.Colors.isDarkPalette : dark);
    }
    function structure(index, dark) {
        return colors.positioned(Session.project ? Session.project.structureColourPositions : [], index, dark);
    }
    function experiment(index, dark) {
        return colors.positioned(Session.project ? Session.project.experimentColourPositions : [], index, dark);
    }

    // A block's colour by its kind ("structure" or "experiment") and place.
    function block(kind, index) {
        return kind === "structure" ? colors.structure(index) : kind === "experiment" ? colors.experiment(index) : EaStyle.Colors.themeForegroundMinor;
    }

    // The structure view's colour scheme ("jmol" or "vesta"), which every table's atom icons follow too.
    readonly property string elementScheme: Session.project && Session.project.structureViewOptions ? Session.project.structureViewOptions.colorScheme : "jmol"

    // An element's colour from a type symbol: the core's element table (edi ADR-0022 §4), the colour of the
    // symbol's element ("162Dy" is Dy, "Co2+" is Co, "2H" is H) in the structure view's scheme; the minor
    // foreground colour for an element the table does not have. Drawn flat, so made readable on `backgrounds`, by
    // default every underlay of a table cell: both alternating rows, the hover tint and the page behind the table
    // (edi ADR-0047).
    function element(typeSymbol, backgrounds) {
        const colour = ApplicationInfo.elementColor(String(typeSymbol), EaStyle.Colors.themeForegroundMinor, colors.elementScheme);
        return colors.readable(colour, backgrounds === undefined ? colors.tableUnderlays : backgrounds);
    }
    readonly property list<color> tableUnderlays: [EaStyle.Colors.themeBackgroundHovered1, EaStyle.Colors.themeBackgroundHovered2, EaStyle.Colors.themeRowHovered, EaStyle.Colors.mainContentBackground]

    // A colour drawn flat on any of `backgrounds`, moved to 2:1 contrast on each by its lightness (edi ADR-0047).
    function readable(colour, backgrounds) {
        return ApplicationInfo.readableColour(colour, backgrounds);
    }
}
