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

    objectName: "fit.results"
    title: qsTr("Least-squares fit results")
    standardButtons: Dialog.Ok
    contentWidth: listArea.width
    contentHeight: listArea.height + (dialog.scan ? evolutionButton.height + EaStyle.Sizes.fontPixelSize : 0)

    EaElements.SideBarButton {
        id: evolutionButton

        objectName: "fit.results.evolution"
        visible: dialog.scan
        y: listArea.height + EaStyle.Sizes.fontPixelSize
        width: listArea.width
        fontIcon: "chart-line"
        text: qsTr("Show evolution")
        onClicked: {
            dialog.close();
            AppState.open(AppState.Page.Analysis);
            AppState.evolutionRequested();
        }
    }

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
                required property string outcome

                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                IconCell {
                    icon: row.outcome !== "" ? FitOutcomes.icon(row.outcome) : row.icon
                    iconColor: String(row.outcome !== "" ? FitOutcomes.color(row.outcome) : EaStyle.Colors.themeForegroundMinor)
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
                    color: row.outcome !== "" ? FitOutcomes.color(row.outcome) : EaStyle.Colors.themeForeground
                    text: row.outcome !== "" ? FitOutcomes.word(row.outcome) : row.value
                }
            }
        }
    }
}
