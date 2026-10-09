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

    readonly property ScatteringLengthListModel lengths: structure ? structure.scatteringLengths : null
    property StructureViewModel structure: null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        columnWidths: [numberColumnWidth, -1, EaStyle.Sizes.fontPixelSize * 10, AppSizes.iconColumnWidth]
        defaultInfoText: qsTr("No custom scattering lengths: the built-in table applies")
        model: group.lengths
        objectName: "scatteringLengths.list"

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int index
            required property real lengthFm
            required property string typeSymbol

            EaComponents.TableViewLabel {
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                objectName: `scatteringLength.typeSymbol.${row.index}`
                value: row.typeSymbol

                onCommitted: text => group.lengths.setTypeSymbol(row.index, text)
            }
            TextCell {
                accepts: "number"
                objectName: `scatteringLength.lengthFm.${row.index}`
                value: row.lengthFm

                onCommitted: text => group.lengths.setLengthFm(row.index, Number(text))
            }
            EaComponents.TableViewButton {
                ToolTip.text: qsTr("Remove this scattering length")
                fontIcon: "minus-circle"
                objectName: `scatteringLength.remove.${row.index}`

                onClicked: group.lengths.remove(row.index)
            }
        }
        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
            }
            EaComponents.TableViewLabel {
                text: qsTr("type")
            }
            EaComponents.TableViewLabel {
                text: qsTr("b (fm)")
            }
            EaComponents.TableViewLabel {
            }
        }
    }
    EaElements.SideBarButton {
        fontIcon: "plus-circle"
        objectName: "scatteringLengths.append"
        text: qsTr("Append a scattering length")
        wide: true  // the row to itself, as the original's append actions fill theirs

        onClicked: group.lengths.append()
    }
}
