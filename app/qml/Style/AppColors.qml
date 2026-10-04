// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// The colours edi gives datablocks and elements (edi ADR-0017 §8), all from the base's EaStyle tokens except
// the element colours, which are the core's element table (data/elements, the Jmol colours; edi ADR-0022 §4).
QtObject {
    id: colors

    // A structure's colour by its place in the project: the base's model colours, as easydiffractionbeta
    // colours its models (orange, teal, pink), round again after the third.
    function structure(index) {
        const palette = EaStyle.Colors.models;
        return index >= 0 ? palette[index % palette.length] : EaStyle.Colors.themeForegroundMinor;
    }

    // An experiment's colour by its place in the project: easydiffractionbeta's measured-data light blue
    // first, then the base's brown and green, none of them a structure's colour.
    function experiment(index) {
        const extra = EaStyle.Colors.chartForegroundsExtra;
        const palette = [extra[2], extra[3], extra[1]];
        return index >= 0 ? palette[index % palette.length] : EaStyle.Colors.themeForegroundMinor;
    }

    // A block's colour by its kind ("structure" or "experiment") and place.
    function block(kind, index) {
        return kind === "structure" ? colors.structure(index) : kind === "experiment" ? colors.experiment(index) : EaStyle.Colors.themeForegroundMinor;
    }

    // An element's colour from a type symbol: the core's element table (edi ADR-0022 §4), its Jmol colour of
    // the symbol's element ("162Dy" is Dy, "Co2+" is Co, "2H" is H); the minor foreground colour for an element
    // the table does not have.
    function element(typeSymbol) {
        return ApplicationInfo.elementColor(String(typeSymbol), EaStyle.Colors.themeForegroundMinor);
    }
}
