// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `background`: the type selector over the
// core's supported types, then that type's content — for `line-segment` the point list (position,
// intensity), with append and remove, and a reset to the autodetected background (disabled).
Column {
    id: group

    property ExperimentViewModel experiment: null
    // A background type's content by token: a new type needs only its layout here.
    readonly property var layouts: ({
            "line-segment": lineSegmentLayout
        })
    readonly property BackgroundListModel points: experiment ? experiment.background : null

    spacing: AppSizes.groupContentSpacing

    EaElements.GroupRow {
        SelectorField {
            label: qsTr("type")
            objectName: "background.type"
            options: group.experiment ? group.experiment.backgroundTypeOptions : null
            token: group.experiment ? group.experiment.backgroundType : ""
        }
    }
    Loader {
        sourceComponent: group.experiment ? group.layouts[group.experiment.backgroundType] ?? null : null
    }
    Component {
        id: lineSegmentLayout

        Column {
            spacing: AppSizes.groupContentSpacing

            DataTable {
                columnWidths: [numberColumnWidth, -1, -1, AppSizes.iconColumnWidth]
                defaultInfoText: qsTr("No background points")
                // At most four rows, then it scrolls (the owner, 2026-10-04; edi ADR-0017 §3).
                maxRowCountShow: 4
                model: group.points
                objectName: "background.list"

                delegate: EaComponents.ListViewDelegate {
                    id: row

                    required property int index
                    required property ParameterItem intensity
                    required property real position

                    EaComponents.TableViewLabel {
                        color: EaStyle.Colors.themeForegroundMinor
                        text: row.index + 1
                    }
                    TextCell {
                        accepts: "number"
                        objectName: `background.position.${row.index}`
                        value: row.position

                        onCommitted: text => group.points.setPosition(row.index, Number(text))
                    }
                    ParameterCell {
                        item: row.intensity
                        objectName: `background.intensity.${row.index}`
                    }
                    EaComponents.TableViewButton {
                        ToolTip.text: qsTr("Remove this background point")
                        fontIcon: "minus-circle"
                        objectName: `background.remove.${row.index}`

                        onClicked: group.points.remove(row.index)
                    }
                }
                header: EaComponents.ListViewHeader {
                    EaComponents.TableViewLabel {
                        text: qsTr("id")
                    }
                    EaComponents.TableViewLabel {
                        text: qsTr("position")
                    }
                    EaComponents.TableViewLabel {
                        text: qsTr("intensity")
                    }
                    EaComponents.TableViewLabel {
                    }
                }
            }

            // Append, and reset to the autodetected background — not implemented yet, so disabled (edi
            // ADR-0017 §4).
            Row {
                spacing: EaStyle.Sizes.fontPixelSize

                EaElements.SideBarButton {
                    fontIcon: "plus-circle"
                    objectName: "background.append"
                    text: qsTr("Append new point")

                    onClicked: group.points.append()
                }
                EaElements.SideBarButton {
                    enabled: false
                    fontIcon: "undo-alt"
                    objectName: "background.autodetect"
                    text: qsTr("Reset to autodetected background")
                }
            }
        }
    }
}
