// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The fit has finished: diffraction-lib's "Least-squares fit results" table — numbered rows of an icon, the
// metric and its value (FitResultListModel) — as the Messages dialog's framed table, as tall as its rows.
// Opened when a fit ends with a result the project holds: finished, cancelled or stopped early; a refusal
// opens the error dialog instead.
AppDialog {
    id: dialog

    readonly property FitResultListModel results: Session.project ? Session.project.fit.results : null

    objectName: "fit.results"
    title: qsTr("Least-squares fit results")
    standardButtons: Dialog.Ok
    contentWidth: listArea.width
    contentHeight: listArea.height

    Item {
        id: listArea

        width: AppSizes.messagesDialogContentWidth
        height: table.contentHeight

        EaComponents.TableView {
            id: table

            objectName: "fit.results.list"
            anchors.fill: parent
            interactive: false
            defaultInfoText: ""
            model: dialog.results

            header: EaComponents.TableViewHeader {
                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.tableRowHeight
                }
                EaComponents.TableViewLabel {
                    flexibleWidth: true
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Metric")
                }
                // The value column is padded on the right as the metric column is on the left (the owner,
                // 2026-10-02), as diffraction-lib's table is.
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 10
                    rightPadding: EaStyle.Sizes.fontPixelSize
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("Value")
                }
            }

            delegate: EaComponents.TableViewDelegate {
                id: row

                required property int index
                required property string icon
                required property string metric
                required property string value

                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                IconCell {
                    icon: row.icon
                    iconColor: String(row.icon === "check-circle" ? EaStyle.Colors.green : row.icon === "times-circle" ? EaStyle.Colors.red : EaStyle.Colors.themeForegroundMinor)
                }
                EaComponents.TableViewLabel {
                    objectName: `fit.results.metric.${row.index}`
                    width: table.headerLabelItems.length > 2 ? table.headerLabelItems[2].width : 0
                    horizontalAlignment: Text.AlignLeft
                    text: row.metric
                }
                EaComponents.TableViewLabel {
                    objectName: `fit.results.value.${row.index}`
                    width: EaStyle.Sizes.fontPixelSize * 10
                    rightPadding: EaStyle.Sizes.fontPixelSize
                    horizontalAlignment: Text.AlignRight
                    text: row.value
                }
            }
        }
    }
}
