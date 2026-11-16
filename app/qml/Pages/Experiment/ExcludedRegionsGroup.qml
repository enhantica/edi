// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `excluded_region`: the axis ranges left out of a fit, editable, with append and remove. A single crystal's ranges are
// in d or sin(θ)/λ, named in each row's axis column; a powder's are on its pattern's axis.
Column {
    id: group

    property ExperimentViewModel experiment: null
    readonly property ExcludedRegionListModel regions: experiment ? experiment.excludedRegions : null
    readonly property bool singleCrystal: experiment !== null && experiment.sampleForm === ExperimentViewModel.SingleCrystal
    readonly property var axisTokens: ["d_spacing", "sin_theta_over_lambda"]
    readonly property var axisLabels: ["d (Å)", "sin(θ)/λ (Å⁻¹)"]

    spacing: AppSizes.groupContentSpacing

    DataTable {
        objectName: "excludedRegions.list"
        defaultInfoText: qsTr("No excluded regions yet")
        sourceModel: group.regions

        columns: [numberColumnWidth, -1, -1, -1].concat(group.singleCrystal ? [-1] : []).concat([AppSizes.iconColumnWidth])

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "excluded_region.id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "excluded_region.start"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "excluded_region.end"
            }
            HeaderLabel {
                visible: group.singleCrystal
                horizontalAlignment: Text.AlignLeft
                uid: "excluded_region.axis"
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            required property var model
            required property real start
            required property real end
            required property string axis

            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            TextCell {
                editMember: row
                editModel: group.regions
                editIndex: row.index
                horizontalAlignment: Text.AlignLeft
                objectName: `excludedRegion.id.${row.index}`
                value: row.model.id
                onCommitted: text => group.regions.setId(row.index, text)
            }
            TextCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `excludedRegion.start.${row.index}`
                uid: "excluded_region.start"
                value: row.start
                accepts: "number"
                onCommitted: text => group.regions.setStart(row.index, Number(text))
            }
            TextCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `excludedRegion.end.${row.index}`
                uid: "excluded_region.end"
                value: row.end
                accepts: "number"
                onCommitted: text => group.regions.setEnd(row.index, Number(text))
            }
            ComboCell {
                visible: group.singleCrystal
                SearchableComboBox {
                    horizontalAlignment: Text.AlignLeft
                    objectName: `excludedRegion.axis.${row.index}`
                    inTable: true
                    anchors.verticalCenter: parent.verticalCenter
                    model: group.axisLabels
                    currentIndex: group.axisTokens.indexOf(row.axis)
                    onActivated: index => group.regions.setAxis(row.index, group.axisTokens[index])
                }
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `excludedRegion.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this region")
                onClicked: group.regions.remove(row.index)
            }
        }
    }

    EaElements.SideBarButton {
        objectName: "excludedRegions.append"
        wide: true  // the row to itself, as the original's append actions fill theirs
        fontIcon: "plus-circle"
        text: qsTr("Append new region")
        onClicked: group.regions.append()
    }
}
