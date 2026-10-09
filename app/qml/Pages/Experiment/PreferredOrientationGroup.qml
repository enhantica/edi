// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `preferred_orientation` (March–Dollase, constant wavelength): the structure it
// corrects, the texture axis [h k l], r and the random fraction; at most one row.
Column {
    id: group

    property ExperimentViewModel experiment: null
    readonly property real indexWidth: EaStyle.Sizes.fontPixelSize * 2.5
    readonly property PrefOrientListModel rows: experiment ? experiment.preferredOrientation : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        columnWidths: [numberColumnWidth, textColumnWidth("structureId", qsTr("structure")), -1, -1, -1, -1, -1, AppSizes.iconColumnWidth]
        defaultInfoText: qsTr("No preferred orientation")
        model: group.rows
        objectName: "preferredOrientation.list"

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int index
            required property int indexH
            required property int indexK
            required property int indexL
            required property ParameterItem marchR
            required property ParameterItem marchRandomFract
            required property string structureId

            EaComponents.TableViewLabel {
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                horizontalAlignment: Text.AlignLeft
                objectName: `preferredOrientation.structureId.${row.index}`
                value: row.structureId

                onCommitted: text => group.rows.setStructureId(row.index, text)
            }
            TextCell {
                accepts: "integer"
                objectName: `preferredOrientation.indexH.${row.index}`
                value: row.indexH

                onCommitted: text => group.rows.setIndex(row.index, "h", Number(text))
            }
            TextCell {
                accepts: "integer"
                objectName: `preferredOrientation.indexK.${row.index}`
                value: row.indexK

                onCommitted: text => group.rows.setIndex(row.index, "k", Number(text))
            }
            TextCell {
                accepts: "integer"
                objectName: `preferredOrientation.indexL.${row.index}`
                value: row.indexL

                onCommitted: text => group.rows.setIndex(row.index, "l", Number(text))
            }
            ParameterCell {
                item: row.marchR
                objectName: `preferredOrientation.marchR.${row.index}`
            }
            ParameterCell {
                item: row.marchRandomFract
                objectName: `preferredOrientation.marchRandomFract.${row.index}`
            }
            EaComponents.TableViewButton {
                ToolTip.text: qsTr("Remove this row")
                fontIcon: "minus-circle"
                objectName: `preferredOrientation.remove.${row.index}`

                onClicked: group.rows.remove(row.index)
            }
        }
        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
                text: qsTr("id")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("structure")
            }
            EaComponents.TableViewLabel {
                text: "h"
            }
            EaComponents.TableViewLabel {
                text: "k"
            }
            EaComponents.TableViewLabel {
                text: "l"
            }
            EaComponents.TableViewLabel {
                text: "r"
            }
            EaComponents.TableViewLabel {
                text: qsTr("random")
            }
            EaComponents.TableViewLabel {
            }
        }
    }
    EaElements.SideBarButton {
        enabled: group.rows !== null && group.rows.canAppend
        fontIcon: "plus-circle"
        objectName: "preferredOrientation.append"
        text: qsTr("Add preferred orientation")
        wide: true  // the row to itself, as the original's append actions fill theirs

        onClicked: group.rows.append()
    }
}
