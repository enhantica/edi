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
    readonly property PrefOrientListModel rows: experiment ? experiment.preferredOrientation : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        objectName: "preferredOrientation.list"
        defaultInfoText: qsTr("No preferred orientation")
        model: group.rows

        columnWidths: [numberColumnWidth, textColumnWidth("structureId", qsTr("structure")), -1, -1, -1, -1, -1, AppSizes.iconColumnWidth]

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
            EaComponents.TableViewLabel {}
        }

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int index
            required property string structureId
            required property int indexH
            required property int indexK
            required property int indexL
            required property ParameterItem marchR
            required property ParameterItem marchRandomFract

            EaComponents.TableViewLabel {
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                objectName: `preferredOrientation.structureId.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.structureId
                onCommitted: text => group.rows.setStructureId(row.index, text)
            }
            TextCell {
                objectName: `preferredOrientation.indexH.${row.index}`
                value: row.indexH
                accepts: "integer"
                onCommitted: text => group.rows.setIndex(row.index, "h", Number(text))
            }
            TextCell {
                objectName: `preferredOrientation.indexK.${row.index}`
                value: row.indexK
                accepts: "integer"
                onCommitted: text => group.rows.setIndex(row.index, "k", Number(text))
            }
            TextCell {
                objectName: `preferredOrientation.indexL.${row.index}`
                value: row.indexL
                accepts: "integer"
                onCommitted: text => group.rows.setIndex(row.index, "l", Number(text))
            }
            ParameterCell {
                objectName: `preferredOrientation.marchR.${row.index}`
                item: row.marchR
            }
            ParameterCell {
                objectName: `preferredOrientation.marchRandomFract.${row.index}`
                item: row.marchRandomFract
            }
            EaComponents.TableViewButton {
                objectName: `preferredOrientation.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this row")
                onClicked: group.rows.remove(row.index)
            }
        }
    }

    EaElements.SideBarButton {
        objectName: "preferredOrientation.append"
        wide: true  // the row to itself, as the original's append actions fill theirs
        enabled: group.rows !== null && group.rows.canAppend
        fontIcon: "plus-circle"
        text: qsTr("Add preferred orientation")
        onClicked: group.rows.append()
    }
}
