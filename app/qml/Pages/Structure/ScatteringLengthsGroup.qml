// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `scattering_length` (edi ADR-0014, no upstream counterpart): the structure's custom neutron
// scattering lengths, editable, with append and remove.
Column {
    id: group

    property StructureViewModel structure: null
    readonly property ScatteringLengthListModel lengths: structure ? structure.scatteringLengths : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        objectName: "scatteringLengths.list"
        defaultInfoText: qsTr("No custom scattering lengths: the built-in table applies")
        sourceModel: group.lengths

        columns: [numberColumnWidth, -1, -1, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "scattering_length.type_symbol"
            }
            HeaderLabel {
                uid: "scattering_length.length_fm"
                withUnits: true
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            required property string typeSymbol
            required property real lengthFm

            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            TextCell {
                objectName: `scatteringLength.typeSymbol.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.typeSymbol
                onCommitted: text => group.lengths.setTypeSymbol(row.index, text)
            }
            TextCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `scatteringLength.lengthFm.${row.index}`
                uid: "scattering_length.length_fm"
                value: row.lengthFm
                accepts: "number"
                onCommitted: text => group.lengths.setLengthFm(row.index, Number(text))
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `scatteringLength.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this scattering length")
                onClicked: group.lengths.remove(row.index)
            }
        }
    }

    EaElements.SideBarButton {
        objectName: "scatteringLengths.append"
        wide: true  // the row to itself, as the original's append actions fill theirs
        fontIcon: "plus-circle"
        text: qsTr("Append a scattering length")
        onClicked: group.lengths.append()
    }
}
