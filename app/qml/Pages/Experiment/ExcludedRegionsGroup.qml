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

    EaComponents.TableView {
        objectName: "excludedRegions.list"
        defaultInfoText: qsTr("No excluded regions")
        model: group.regions

        header: EaComponents.TableViewHeader {
            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
                text: qsTr("No.")
            }
            EaComponents.TableViewLabel {
                flexibleWidth: true
                text: qsTr("start")
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 12
                text: qsTr("end")
            }
            EaComponents.TableViewLabel {
                width: AppSizes.iconColumnWidth
            }
        }

        delegate: EaComponents.TableViewDelegate {
            id: row

            required property int index
            required property real start
            required property real end

            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                objectName: `excludedRegion.start.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 12
                value: row.start
                accepts: "number"
                onCommitted: text => group.regions.setStart(row.index, Number(text))
            }
            TextCell {
                objectName: `excludedRegion.end.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 12
                value: row.end
                accepts: "number"
                onCommitted: text => group.regions.setEnd(row.index, Number(text))
            }
            EaComponents.TableViewButton {
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
