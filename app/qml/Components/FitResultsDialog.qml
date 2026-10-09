// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The fit has finished: diffraction-lib's "Least-squares fit results" table — numbered rows of an icon, the
// metric and its value (FitResultListModel) — as the Messages dialog's framed table, as tall as its rows. The
// Overall status row shows the outcome as the status bar does (FitOutcomes): its icon, word and colour.
// Opened when a fit ends with a result the project holds: finished, cancelled or stopped early; a refusal
// opens the error dialog instead.
AppDialog {
    id: dialog

    readonly property FitResultListModel results: Session.project ? Session.project.fit.results : null
    // After a scan the table is the run's summary, with a button to the Evolution tab (edi ADR-0017 §19).
    readonly property bool scan: Session.project !== null && Session.project.fit.scanSummary

    contentHeight: listArea.height + (dialog.scan ? evolutionButton.height + EaStyle.Sizes.fontPixelSize : 0)
    contentWidth: listArea.width
    objectName: "fit.results"
    standardButtons: Dialog.Ok
    title: qsTr("Least-squares fit results")

    EaElements.SideBarButton {
        id: evolutionButton

        fontIcon: "chart-line"
        objectName: "fit.results.evolution"
        text: qsTr("Show evolution")
        visible: dialog.scan
        width: listArea.width
        y: listArea.height + EaStyle.Sizes.fontPixelSize

        onClicked: {
            dialog.close();
            AppState.open(AppState.Page.Analysis);
            AppState.evolutionRequested();
        }
    }
    Item {
        id: listArea

        height: table.contentHeight
        width: AppSizes.messagesDialogContentWidth

        DataTable {
            id: table

            anchors.fill: parent
            columnWidths: [numberColumnWidth, EaStyle.Sizes.tableRowHeight, -1, EaStyle.Sizes.fontPixelSize * 10]
            defaultInfoText: ""
            interactive: false
            model: dialog.results
            objectName: "fit.results.list"

            delegate: EaComponents.ListViewDelegate {
                id: row

                required property string icon
                required property int index
                required property string metric
                required property string outcome
                required property string value

                EaComponents.TableViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                IconCell {
                    icon: row.outcome !== "" ? FitOutcomes.icon(row.outcome) : row.icon
                    iconColor: String(row.outcome !== "" ? FitOutcomes.color(row.outcome) : EaStyle.Colors.themeForegroundMinor)
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    objectName: `fit.results.metric.${row.index}`
                    text: row.metric
                }
                EaComponents.TableViewLabel {
                    color: row.outcome !== "" ? FitOutcomes.color(row.outcome) : EaStyle.Colors.themeForeground
                    horizontalAlignment: Text.AlignRight
                    objectName: `fit.results.value.${row.index}`
                    rightPadding: EaStyle.Sizes.fontPixelSize
                    text: row.outcome !== "" ? FitOutcomes.word(row.outcome) : row.value
                }
            }
            header: EaComponents.ListViewHeader {
                EaComponents.TableViewLabel {
                }
                EaComponents.TableViewLabel {
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Metric")
                }
                // The value column is padded on the right as the metric column is on the left (the owner,
                // 2026-10-02), as diffraction-lib's table is.
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignRight
                    rightPadding: EaStyle.Sizes.fontPixelSize
                    text: qsTr("Value")
                }
            }
        }
    }
}
