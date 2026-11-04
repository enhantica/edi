// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `parent_propagation_vector` (edi ADR-0070; the owner, 2026-11-03): the structure's commensurate k vectors, edited,
// added and removed as Excluded regions are. crysta checks every change against the cell and the signed group, and
// a vector they cannot carry, or one already listed, is refused with its reason. The last vector stays.
Column {
    id: group

    property StructureViewModel structure: null
    readonly property PropagationVectorListModel vectors: structure ? structure.propagationVectors : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        objectName: "propagationVectors.list"
        defaultInfoText: qsTr("No propagation vectors")
        sourceModel: group.vectors

        columns: [numberColumnWidth, -1, -1, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "parent_propagation_vector.id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "parent_propagation_vector.kxkykz"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            required property var model
            required property string vector

            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            TextCell {
                horizontalAlignment: Text.AlignLeft
                objectName: `propagationVector.id.${row.index}`
                value: row.model.id
                onCommitted: text => group.vectors.setId(row.index, text)
            }
            TextCell {
                horizontalAlignment: Text.AlignLeft
                objectName: `propagationVector.vector.${row.index}`
                value: row.vector
                onCommitted: text => group.vectors.setVector(row.index, text)
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `propagationVector.remove.${row.index}`
                fontIcon: "minus-circle"
                enabled: group.vectors !== null && group.vectors.count > 1
                ToolTip.text: qsTr("Remove this vector")
                onClicked: group.vectors.remove(row.index)
            }
        }
    }

    // Why the last change was not made, until one is.
    EaElements.Label {
        objectName: "propagationVectors.refusal"
        visible: group.vectors !== null && group.vectors.refusal !== ""
        width: EaStyle.Sizes.sideBarContentWidth
        wrapMode: Text.WordWrap
        color: EaStyle.Colors.red
        text: group.vectors ? group.vectors.refusal : ""
    }

    EaElements.SideBarButton {
        objectName: "propagationVectors.append"
        wide: true
        fontIcon: "plus-circle"
        text: qsTr("Add vector")
        onClicked: group.vectors.append()
    }
}
