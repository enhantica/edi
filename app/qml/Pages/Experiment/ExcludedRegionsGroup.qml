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
        columnWidths: [numberColumnWidth, -1, -1, AppSizes.iconColumnWidth]
        defaultInfoText: qsTr("No excluded regions")
        model: group.regions
        objectName: "excludedRegions.list"

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property real end
            required property int index
            required property real start

            EaComponents.TableViewLabel {
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                accepts: "number"
                objectName: `excludedRegion.start.${row.index}`
                value: row.start

                onCommitted: text => group.regions.setStart(row.index, Number(text))
            }
            TextCell {
                accepts: "number"
                objectName: `excludedRegion.end.${row.index}`
                value: row.end

                onCommitted: text => group.regions.setEnd(row.index, Number(text))
            }
            EaComponents.TableViewButton {
                ToolTip.text: qsTr("Remove this region")
                fontIcon: "minus-circle"
                objectName: `excludedRegion.remove.${row.index}`

                onClicked: group.regions.remove(row.index)
            }
        }
        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
                text: qsTr("id")
            }
            EaComponents.TableViewLabel {
                text: qsTr("start")
            }
            EaComponents.TableViewLabel {
                text: qsTr("end")
            }
            EaComponents.TableViewLabel {
            }
        }
    }
    EaElements.SideBarButton {
        fontIcon: "plus-circle"
        objectName: "excludedRegions.append"
        text: qsTr("Append new region")
        wide: true  // the row to itself, as the original's append actions fill theirs

        onClicked: group.regions.append()
    }
}
