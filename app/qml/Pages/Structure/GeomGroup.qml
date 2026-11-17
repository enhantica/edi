// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `geom`, the bond settings: the minimum distance and the increment over the two sites' covalent radii, side by side
// as the Appearance fields, and the bonds crysta finds with them (`_geom_bond`), the same the structure view draws.
Column {
    id: group

    property StructureViewModel structure: null

    spacing: AppSizes.groupContentSpacing

    Grid {
        id: grid

        readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - grid.columnSpacing) / 2

        columns: 2
        columnSpacing: AppSizes.inputSpacing
        rowSpacing: AppSizes.groupContentSpacing

        EaElements.ParamTextField {
            id: minimum

            objectName: "geom.min_bond_distance_cutoff"
            width: grid.fieldWidth
            enabled: group.structure !== null
            parameter: ({
                    "value": group.structure ? group.structure.minBondDistance : 0,
                    "error": 0,
                    "enabled": true,
                    "fittable": false,
                    "fit": false,
                    "name": "min_bond_distance_cutoff",
                    "shortPrettyName": Session.label("geom.min_bond_distance_cutoff"),
                    "units": Session.units("geom.min_bond_distance_cutoff")
                })

            // A negative or unreadable distance leaves the cutoff as it was; the field shows the held value again.
            function commit() {
                if (group.structure)
                    group.structure.minBondDistance = Number(text);
                text = Qt.binding(() => minimum.value);
            }

            Component.onCompleted: FieldTitles.align(minimum)
            onAccepted: commit()
            onEditingFinished: commit()
        }
        EaElements.ParamTextField {
            id: increment

            objectName: "geom.bond_distance_inc"
            width: grid.fieldWidth
            enabled: group.structure !== null
            parameter: ({
                    "value": group.structure ? group.structure.bondDistanceIncrement : 0,
                    "error": 0,
                    "enabled": true,
                    "fittable": false,
                    "fit": false,
                    "name": "bond_distance_inc",
                    "shortPrettyName": Session.label("geom.bond_distance_inc"),
                    "units": Session.units("geom.bond_distance_inc")
                })

            function commit() {
                if (group.structure)
                    group.structure.bondDistanceIncrement = Number(text);
                text = Qt.binding(() => increment.value);
            }

            Component.onCompleted: FieldTitles.align(increment)
            onAccepted: commit()
            onEditingFinished: commit()
        }
    }

    DataTable {
        objectName: "geom.bonds"
        width: EaStyle.Sizes.sideBarContentWidth
        defaultInfoText: qsTr("No bonds within the cutoffs, or the structure is not calculated yet.")
        sourceModel: group.structure ? group.structure.bonds : []

        columns: [numberColumnWidth, -1, -1, -1]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "geom_bond.atom_site_label_1"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "geom_bond.atom_site_label_2"
            }
            HeaderLabel {
                uid: "geom_bond.distance"
                withUnits: true
            }
        }

        delegate: TableRow {
            id: row

            required property var modelData

            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            EaComponents.ListViewLabel {
                objectName: `geom.bonds.site1.${row.index}`
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignLeft
                text: row.modelData.site1
            }
            EaComponents.ListViewLabel {
                objectName: `geom.bonds.site2.${row.index}`
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignLeft
                text: row.modelData.site2
            }
            EaComponents.ListViewLabel {
                objectName: `geom.bonds.distance.${row.index}`
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                text: Session.display("geom_bond.distance", row.modelData.distance)
            }
        }
    }
}
