// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `parent_propagation_vector` (edi ADR-0078; the owner, 2026-11-03): the structure's commensurate k vectors, edited,
// added and removed as Excluded regions are. crysta checks every change against the cell and the signed group, and
// a vector they cannot carry, or one already listed, is refused with its reason. The last vector stays.
Column {
    id: group

    property StructureViewModel structure: null
    readonly property PropagationVectorListModel vectors: structure ? structure.propagationVectors : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        objectName: "propagationVectors.list"
        // Never blank for a Magnetic structure (the owner, 2026-11-19): without a vector in the file, the one its
        // magnetic group gives.
        defaultInfoText: group.structure && group.structure.derivedPropagationVector !== "" ? qsTr("k = %1, from the magnetic group (its parent's cell)").arg(group.structure.derivedPropagationVector) : group.structure && group.structure.propagationNotDerived !== "" ? group.structure.propagationNotDerived : qsTr("No propagation vectors yet")
        sourceModel: group.vectors

        columns: [numberColumnWidth, -1, -1, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
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
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            required property var model
            required property string vector

            EaComponents.ListViewLabel {
                elide: Text.ElideRight
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

    // A vector the structure cannot carry is not taken: the row keeps its value and the reason shows in plain words in
    // the app's error popup and the Messages center, not as a lasting label (the owner, 2026-11-19).
    Connections {
        target: group.vectors
        function onRefusalChanged() {
            if (group.vectors && group.vectors.refusal !== "") {
                Session.reportRefusal(group.vectors.refusal);
                group.vectors.clearRefusal();
            }
        }
    }

    EaElements.SideBarButton {
        objectName: "propagationVectors.append"
        wide: true
        fontIcon: "plus-circle"
        text: qsTr("Add vector")
        onClicked: group.vectors.append()
    }
}
