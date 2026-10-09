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

        columnWidths: [numberColumnWidth, -1, -1, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("start")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("end")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int index
            required property real start
            required property real end

            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `excludedRegion.start.${row.index}`
                value: row.start
                accepts: "number"
                onCommitted: text => group.regions.setStart(row.index, Number(text))
            }
            TextCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `excludedRegion.end.${row.index}`
                value: row.end
                accepts: "number"
                onCommitted: text => group.regions.setEnd(row.index, Number(text))
            }
            EaComponents.TableViewButton {
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
