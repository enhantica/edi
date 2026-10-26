// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `excluded_region`: the axis ranges left out of a fit, editable, with append and remove.
Column {
    id: group

    property ExperimentViewModel experiment: null
    readonly property ExcludedRegionListModel regions: experiment ? experiment.excludedRegions : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        objectName: "excludedRegions.list"
        defaultInfoText: qsTr("No excluded regions")
        sourceModel: group.regions

        columnWidths: [numberColumnWidth, Math.min(textColumnWidth("id", Session.label("excluded_region.id")), width * 0.25), -1, -1, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
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
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            required property var model
            required property real start
            required property real end

            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            TextCell {
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
