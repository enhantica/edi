// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Appearance (edi ADR-0017 §16; easydiffractionbeta's group of that name and place): the
// `structure_style` options of diffraction-lib that its modebar does not carry — the atom view (the radius
// model, or the ADP surfaces) and the atom scale, or the ADP probability in the ADP view — laid out and styled as the Instrument group (the owner, 2026-10-02): a muted
// caption above each field and the fields side by side in equal columns over the group's width, with the
// components that group and the selectors use. The elements whose radius was substituted are listed under them.
// View state of the open project, shared by every structure's view; not saved.
EaElements.GroupBox {
    id: group

    property StructureViewOptions options: null
    property StructureViewController controller: null

    objectName: "group.appearance"
    title: qsTr("Appearance")
    icon: "palette"
    last: SideBarGroups.isLast(group)

    Column {
        spacing: AppSizes.groupContentSpacing

        // Two fields in equal columns, as ParameterGrid lays out the instrument's.
        Grid {
            id: grid

            readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - grid.columnSpacing) / 2

            columns: 2
            columnSpacing: AppSizes.fieldSpacing

            SelectorField {
                objectName: "structure.appearance.atomView"
                width: grid.fieldWidth
                label: qsTr("Atom view")
                options: group.options ? group.options.atomViewOptions : null
                token: group.options ? group.options.atomView : ""
                onSelected: token => group.options.atomView = token
            }
            EaElements.ParamTextField {
                id: scale

                objectName: "structure.appearance.atomScale"
                visible: group.options === null || group.options.atomView !== "adp"
                width: grid.fieldWidth
                parameter: group.options ? {
                    "value": group.options.atomScale,
                    "error": 0,
                    "enabled": true,
                    "fittable": false,
                    "fit": false,
                    "name": "atom_scale",
                    "shortPrettyName": qsTr("Atom scale"),
                    "units": ""
                } : ({})

                // Above 0 and at most 1 (diffraction-lib's range); anything else leaves the scale as it was.
                function commit() {
                    if (group.options !== null && text !== scale.value) {
                        group.options.atomScale = Number(text);
                        text = Qt.binding(() => scale.value);
                    }
                }

                // Its title as every field's (edi ADR-0017 §5).
                Component.onCompleted: FieldTitles.align(scale)
                onAccepted: commit()
                onEditingFinished: commit()
            }
            // The ADP view sizes its ellipsoids by a probability, not a scale: its field takes the scale's place
            // (the owner, 2026-10-06; diffraction-lib's `adp_probability`, 0.99 by default).
            EaElements.ParamTextField {
                id: probability

                objectName: "structure.appearance.adpProbability"
                visible: group.options !== null && group.options.atomView === "adp"
                width: grid.fieldWidth
                parameter: group.options ? {
                    "value": group.options.adpProbability,
                    "error": 0,
                    "enabled": true,
                    "fittable": false,
                    "fit": false,
                    "name": "adp_probability",
                    "shortPrettyName": qsTr("Probability"),
                    "units": ""
                } : ({})

                // Above 0 and below 1 (diffraction-lib's range); anything else leaves the probability as it was.
                function commit() {
                    if (group.options !== null && text !== probability.value) {
                        group.options.adpProbability = Number(text);
                        text = Qt.binding(() => probability.value);
                    }
                }

                Component.onCompleted: FieldTitles.align(probability)
                onAccepted: commit()
                onEditingFinished: commit()
            }
        }
        EaElements.Label {
            objectName: "structure.appearance.substituted"
            visible: group.controller !== null && group.controller.substitutedElements !== ""
            color: EaStyle.Colors.themeForegroundMinor
            text: group.options && group.options.atomView === "ionic" ? qsTr("No ionic radius, the covalent radius or 1.0 Å used for: %1").arg(group.controller ? group.controller.substitutedElements : "") : qsTr("No radius, 1.0 Å used for: %1").arg(group.controller ? group.controller.substitutedElements : "")
        }
    }
}
