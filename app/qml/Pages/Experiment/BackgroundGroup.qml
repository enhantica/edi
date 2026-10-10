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
    readonly property BackgroundListModel points: experiment ? experiment.background : null
    // A background type's content by token: a new type needs only its layout here.
    readonly property var layouts: ({
            "line-segment": lineSegmentLayout
        })

    spacing: AppSizes.groupContentSpacing

    EaElements.GroupRow {
        spacing: AppSizes.inputSpacing
        SelectorField {
            objectName: "background.type"
            label: qsTr("type")
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
                objectName: "background.list"
                // At most four rows, then it scrolls (the owner, 2026-10-04; edi ADR-0017 §3).
                maxRowCountShow: 4
                defaultInfoText: qsTr("No background points")
                sourceModel: group.points

                columnWidths: [numberColumnWidth, Math.min(textColumnWidth("id", qsTr("id")), width * 0.25), -1, -1, AppSizes.iconColumnWidth]

                header: EaComponents.ListViewHeader {
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("id")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("position")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("intensity")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                delegate: EaComponents.ListViewDelegate {
                    id: row

                    required property int index
                    required property var model
                    required property real position
                    required property ParameterItem intensity

                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        color: EaStyle.Colors.themeForegroundMinor
                        text: row.index + 1
                    }
                    TextCell {
                        horizontalAlignment: Text.AlignLeft
                        objectName: `background.id.${row.index}`
                        value: row.model.id
                        onCommitted: text => group.points.setId(row.index, text)
                    }
                    TextCell {
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.position.${row.index}`
                        value: row.position
                        accepts: "number"
                        onCommitted: text => group.points.setPosition(row.index, Number(text))
                    }
                    ParameterCell {
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.intensity.${row.index}`
                        item: row.intensity
                    }
                    EaComponents.TableViewButton {
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `background.remove.${row.index}`
                        fontIcon: "minus-circle"
                        ToolTip.text: qsTr("Remove this background point")
                        onClicked: group.points.remove(row.index)
                    }
                }
            }

            // Append, and reset to the autodetected background — not implemented yet, so disabled (edi
            // ADR-0017 §4).
            Row {
                spacing: EaStyle.Sizes.fontPixelSize

                EaElements.SideBarButton {
                    objectName: "background.append"
                    fontIcon: "plus-circle"
                    text: qsTr("Append new point")
                    onClicked: group.points.append()
                }
                EaElements.SideBarButton {
                    objectName: "background.autodetect"
                    enabled: false
                    fontIcon: "undo-alt"
                    text: qsTr("Reset to autodetected background")
                }
            }
        }
    }
}
