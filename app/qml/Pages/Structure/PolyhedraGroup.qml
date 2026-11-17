// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Polyhedra (the owner, 2026-11-16), beside Bond settings in Extra: what the view's toolbar button draws, defined as VESTA
// and Jmol define it. The centre atoms and the corner atoms by element (empty: cations as centres, anions as corners)
// and the longest centre-corner distance (0: the bond cut-offs), then the colour, opacity and extent. Kept for the
// session: the structure file has no item for them yet.
SideBarGroup {
    id: group

    property StructureViewOptions options: null

    readonly property string openKey: "Extras:polyhedra"

    objectName: "group.polyhedra"
    collapsed: !SideBarGroups.isOpen(openKey, group)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed, group)
    title: qsTr("Polyhedra")
    icon: "dice-d20"
    last: SideBarGroups.isLast(group)

    Grid {
        id: grid

        readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - grid.columnSpacing) / 2

        columns: 2
        columnSpacing: AppSizes.inputSpacing
        rowSpacing: AppSizes.groupContentSpacing

        ValueField {
            objectName: "structure.polyhedra.centres"
            width: grid.fieldWidth
            label: qsTr("Centre atoms")
            clearable: true
            enabled: group.options !== null
            fieldValue: group.options ? group.options.polyhedraCentres : ""
            ToolTip.text: qsTr("Element symbols, such as Co, Si; empty takes every cation")
            onCommitted: text => group.options.polyhedraCentres = text
        }
        ValueField {
            objectName: "structure.polyhedra.corners"
            width: grid.fieldWidth
            label: qsTr("Corner atoms")
            clearable: true
            enabled: group.options !== null
            fieldValue: group.options ? group.options.polyhedraCorners : ""
            ToolTip.text: qsTr("Element symbols, such as O; empty takes the anions N, O, F, S, Cl, Se, Br, Te and I")
            onCommitted: text => group.options.polyhedraCorners = text
        }
        ValueField {
            objectName: "structure.polyhedra.maxDistance"
            width: grid.fieldWidth
            label: qsTr("Max distance")
            unit: "Å"
            accepts: "number"
            admits: text => Number(text) >= 0
            admitsRule: qsTr("A distance is 0 or more")
            enabled: group.options !== null
            fieldValue: group.options ? group.options.polyhedraMaxDistance : 0
            ToolTip.text: qsTr("The longest centre-to-corner distance; 0 takes the bond cut-offs")
            onCommitted: text => group.options.polyhedraMaxDistance = Number(text)
        }
        SelectorField {
            objectName: "structure.polyhedra.colour"
            width: grid.fieldWidth
            label: qsTr("Colour")
            options: group.options ? group.options.polyhedraColourOptions : null
            token: group.options ? group.options.polyhedraColour : ""
            onSelected: token => group.options.polyhedraColour = token
        }
        EaElements.ParamTextField {
            id: opacity

            objectName: "structure.polyhedra.opacity"
            width: grid.fieldWidth
            parameter: group.options ? {
                "value": group.options.polyhedraOpacity,
                "error": 0,
                "enabled": true,
                "fittable": false,
                "fit": false,
                "name": "polyhedra_opacity",
                "shortPrettyName": qsTr("Opacity"),
                "units": ""
            } : ({})

            // From 0 (clear) to 1 (solid); a value outside is brought to the nearest end.
            function commit() {
                if (group.options !== null && text !== opacity.value) {
                    group.options.polyhedraOpacity = Number(text);
                    text = Qt.binding(() => opacity.value);
                }
            }

            Component.onCompleted: FieldTitles.align(opacity)
            onAccepted: commit()
            onEditingFinished: commit()
        }
        SelectorField {
            objectName: "structure.polyhedra.extent"
            width: grid.fieldWidth
            label: qsTr("Extent")
            options: group.options ? group.options.polyhedraExtentOptions : null
            token: group.options ? group.options.polyhedraExtent : ""
            onSelected: token => group.options.polyhedraExtent = token
        }
    }
}
