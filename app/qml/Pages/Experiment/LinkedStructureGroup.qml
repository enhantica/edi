// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `linked_structure` (easydiffractionbeta's Associated phases): the structures (phases) this experiment's
// pattern sums, each with its scale. A loop in `.edi`, so a table. As easydiffractionbeta's Associated phases,
// each row shows the structure's icon in that structure's colour before its name (edi ADR-0017 §8). The name
// is picked from the project's structures; a row can be added for a structure not yet linked, removed while
// another remains, and switched off: a disabled row is kept and saved but neither calculated nor fitted.
// The weight fraction beside the scale is derived from the scales (Hill-Howard) and cannot be edited; a single
// enabled structure shows 1.
Column {
    id: group

    property ExperimentViewModel experiment: null
    property ProjectViewModel project: null
    readonly property LinkedStructureListModel rows: experiment ? experiment.linkedStructures : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table

        objectName: "linkedStructure.list"
        defaultInfoText: qsTr("No linked structure")
        sourceModel: group.rows

        columns: [numberColumnWidth, AppSizes.iconOnlyColumnWidth, -1, -1, -1, AppSizes.iconColumnWidth, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "linked_structure.structure_id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "linked_structure.scale"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "linked_structure.weight_fraction"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            required property string structureId
            required property int colorIndex
            // The Hill-Howard weight fraction: `value` and `uncertainty` (0 without one), empty when there is none.
            required property var weightFraction
            // `scale` and `enabled` are Item properties, so these two roles are read through the model.
            required property var model

            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            IconCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.color.${row.index}`
                icon: "layer-group"
                iconColor: AppColors.structure(row.colorIndex)
                toolTip: qsTr("Calculated pattern color")
            }
            // The structure, picked from the project's structures as the aliases table picks a parameter. A link to a
            // structure the project does not hold (an experiment loaded from another project) shows that name in red
            // until another is picked; nothing is calculated for the experiment meanwhile.
            Item {
                property int horizontalAlignment: Text.AlignLeft
                height: parent.height
                SearchableComboBox {
                    readonly property bool missing: group.rows !== null && group.rows.structureNames.indexOf(row.structureId) < 0

                    width: Math.min(parent.width, fittedWidth)
                    x: parent.horizontalAlignment === Text.AlignRight ? parent.width - width : parent.horizontalAlignment === Text.AlignLeft ? 0 : (parent.width - width) / 2
                    inTable: true
                    horizontalAlignment: Text.AlignLeft
                    anchors.verticalCenter: parent.verticalCenter
                    objectName: `linkedStructure.structureId.${row.index}`
                    enabled: row.model.enabled
                    model: group.rows ? group.rows.structureNames : []
                    currentIndex: group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1
                    displayText: row.structureId
                    foregroundColor: missing ? EaStyle.Colors.red : _foregroundColor()
                    ToolTip.text: missing ? qsTr("The project holds no structure '%1'; pick one of its structures").arg(row.structureId) : row.structureId
                    onActivated: index => ApplicationInfo.scientificSelectorChanged(index, 4, () => { currentIndex = Qt.binding(() => group.rows ? group.rows.structureNames.indexOf(row.structureId) : -1); })
                }
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `linkedStructure.scale.${row.index}`
                enabled: row.model.enabled && refinable
                item: row.model.scale
            }
            // Read-only, as a parameter the scales imply: the dictionary's weight fraction, rounded by its s.u. under the
            // project's rule, else by its display format, the s.u. in the value's menu, never edited or fitted.
            EaComponents.ListViewParameter {
                id: fraction

                errorTitle: qsTr("s.u.")
                fitTitle: qsTr("free")
                readonly property bool known: row.weightFraction !== undefined && row.weightFraction.value !== undefined
                readonly property real fractionValue: known ? row.weightFraction.value : 0
                readonly property real fractionError: known ? row.weightFraction.uncertainty : 0

                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.weightFraction.${row.index}`
                enabled: row.model.enabled
                readOnly: true
                // One map whose values depend on `known`: a choice between two maps, compiled ahead of time, is
                // undefined while the cell is made, and the base component's bindings warn on it.
                parameter: ({
                        "value": known ? Session.valueText("linked_structure.weight_fraction", fractionValue, fractionError) : "",
                        "error": known ? Session.suText("linked_structure.weight_fraction", fractionValue, fractionError) : "",
                        "enabled": true,
                        "fittable": false,
                        "fit": false,
                        "category": "linked_structure",
                        "name": "weight_fraction",
                        "units": ""
                    })
                color: EaStyle.Colors.themeForegroundMinor
                ToolTip.text: Session.tooltip("linked_structure.weight_fraction")
            }
            // Disabled as a constraint is: kept and saved, but neither calculated nor fitted.
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.enabled.${row.index}`
                fontIcon: row.model.enabled ? "toggle-on" : "toggle-off"
                ToolTip.text: row.model.enabled ? qsTr("Disable this linked structure") : qsTr("Enable this linked structure")
                onClicked: group.rows.setEnabled(row.index, !row.model.enabled)
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `linkedStructure.remove.${row.index}`
                enabled: group.rows !== null && group.rows.canRemove
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this linked structure")
                onClicked: group.rows.remove(row.index)
            }
        }
    }

    EaElements.SideBarButton {
        objectName: "linkedStructure.append"
        wide: true
        enabled: group.rows !== null && group.rows.canAppend
        fontIcon: "plus-circle"
        text: qsTr("Add linked structure")
        onClicked: group.rows.append()
    }
}
