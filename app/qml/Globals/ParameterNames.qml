// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A parameter's iconified name on the Analysis page, as easydiffractionbeta's shortest name with icons and
// pretty labels (Globals/Proxies.qml paramName; ADR-0017 §8), as the pieces of one
// IconLine (§10): the block's icon in the block's colour; the category's icon, for an atom site in its element's
// colour; the row (an atom's label, a loop row's number) in the category icon's colour; the parameter's icon;
// then its short name, never bold.
QtObject {
    id: names

    // A block kind's icon, as the block tables show it.
    function blockIcon(kind) { return ApplicationInfo.nameBlockIcon(kind); }

    // easydiffractionbeta's parameter icons (Logic/Calculators.py), by `.edi` item name or its prefix; none
    // for a parameter the original had no icon for.
    function parameterIcon(name) { return ApplicationInfo.nameParameterIcon(name); }

    // A ParameterItem's name as IconLine pieces (§10).
    function segments(item) { return ApplicationInfo.nameSegments(item); }
}
