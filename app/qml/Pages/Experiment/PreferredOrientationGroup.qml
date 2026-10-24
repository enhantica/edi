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
        sourceModel: group.rows

        columnWidths: [numberColumnWidth, textColumnWidth("structureId", Session.label("preferred_orientation.structure_id")), -1, -1, -1, -1, -1, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "preferred_orientation.structure_id"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "h"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "k"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "l"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "r"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("random")
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            required property string structureId
            required property int indexH
            required property int indexK
            required property int indexL
            required property ParameterItem marchR
            required property ParameterItem marchRandomFract

            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            TextCell {
                objectName: `preferredOrientation.structureId.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.structureId
                onCommitted: text => group.rows.setStructureId(row.index, text)
            }
            TextCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `preferredOrientation.indexH.${row.index}`
                value: row.indexH
                accepts: "integer"
                onCommitted: text => group.rows.setIndex(row.index, "h", Number(text))
            }
            TextCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `preferredOrientation.indexK.${row.index}`
                value: row.indexK
                accepts: "integer"
                onCommitted: text => group.rows.setIndex(row.index, "k", Number(text))
            }
            TextCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `preferredOrientation.indexL.${row.index}`
                value: row.indexL
                accepts: "integer"
                onCommitted: text => group.rows.setIndex(row.index, "l", Number(text))
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `preferredOrientation.marchR.${row.index}`
                item: row.marchR
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `preferredOrientation.marchRandomFract.${row.index}`
                item: row.marchRandomFract
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
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
