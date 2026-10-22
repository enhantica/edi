// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The fit has finished: diffraction-lib's "Least-squares fit results" table — numbered rows of an icon, the
// metric and its value (FitResultListModel), down to the reduced χ² — as the Messages dialog's framed table, as tall
// as its rows, and below it the agreement factors, one column per factor and one row per dataset (edi ADR-0045). The
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
    contentWidth: Math.max(listArea.width, agreementArea.width)
    // From the content alone. The base also takes the title's and the buttons' widths, which follow the dialog's own
    // width, so a content width that changes as results arrive was a binding loop. Both are narrower than the tables.
    implicitWidth: contentWidth + leftPadding + rightPadding
    contentHeight: agreementArea.y + agreementArea.height + (dialog.scan ? evolutionButton.height + EaStyle.Sizes.fontPixelSize : 0)

    // The agreement factors (edi ADR-0045), below the summary: one column per factor, one row per dataset.
    readonly property FitAgreementModel agreement: dialog.results ? dialog.results.agreement : null
    readonly property var factorColumns: dialog.agreement ? dialog.agreement.columns : []
    readonly property real factorWidth: EaStyle.Sizes.fontPixelSize * 4.5
    readonly property bool structureHeaders: dialog.factorColumns.some(column => column.structure !== "")

    // The summary table is as wide as its content (the owner, 2026-10-21): each text column its widest entry.
    property int resultsRevision: 0
    Connections {
        target: dialog.results
        function onDataChanged() {
            dialog.resultsRevision++;
        }
        function onCountChanged() {
            dialog.resultsRevision++;
        }
    }
    // A read-only row takes no hover: the base row tints itself from its own hover handler, which a disabled row keeps.
    function passive(row) {
        for (const handler of row.resources) {
            if (handler instanceof HoverHandler)
                handler.enabled = false;
        }
    }
    function widestSummaryText(title, cell) {
        const revision = dialog.resultsRevision;
        let widest = table.advance(title);
        for (let row = 0; dialog.results && row < dialog.results.count; ++row)
            widest = Math.max(widest, table.advance(cell(row)));
        return Math.ceil(widest) + AppSizes.fieldSpacing * 2;
    }
    readonly property real metricColumnWidth: widestSummaryText(qsTr("Metric"), row => dialog.results.text(row, "metric"))
    readonly property real valueColumnWidth: widestSummaryText(qsTr("Value"), row => {
        const outcome = dialog.results.text(row, "outcome");
        return outcome !== "" ? FitOutcomes.word(outcome) : dialog.results.text(row, "value");
    }) + EaStyle.Sizes.fontPixelSize

    EaElements.SideBarButton {
        id: evolutionButton

        objectName: "fit.results.evolution"
        visible: dialog.scan
        y: agreementArea.y + agreementArea.height + EaStyle.Sizes.fontPixelSize
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

        width: table.numberColumnWidth + AppSizes.iconOnlyColumnWidth + dialog.metricColumnWidth + dialog.valueColumnWidth + 3 * EaStyle.Sizes.tableColumnSpacing + 2 * table.rowPadding
        height: table.contentHeight

        DataTable {
            id: table

            objectName: "fit.results.list"
            anchors.fill: parent
            interactive: false
            defaultInfoText: ""
            sourceModel: dialog.results

            columnWidths: [numberColumnWidth, AppSizes.iconOnlyColumnWidth, dialog.metricColumnWidth, dialog.valueColumnWidth]

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Metric")
                }
                // The value column is padded on the right as the metric column is on the left (the owner,
                // 2026-10-02), as diffraction-lib's table is.
                EaComponents.ListViewLabel {
                    rightPadding: EaStyle.Sizes.fontPixelSize
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("Value")
                }
            }

            delegate: TableRow {
                id: row

                required property string icon
                required property string metric
                required property string value
                required property string outcome

                // Read-only (the owner, 2026-10-21): no hover, no selection, no click; the colours are set, not the
                // disabled ones.
                enabled: false
                Component.onCompleted: dialog.passive(row)

                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                IconCell {
                    horizontalAlignment: Text.AlignHCenter
                    icon: row.outcome !== "" ? FitOutcomes.icon(row.outcome) : row.icon
                    iconColor: String(row.outcome !== "" ? FitOutcomes.color(row.outcome) : EaStyle.Colors.themeForegroundMinor)
                }
                EaComponents.ListViewLabel {
                    objectName: `fit.results.metric.${row.index}`
                    horizontalAlignment: Text.AlignLeft
                    color: EaStyle.Colors.themeForeground
                    text: row.metric
                }
                EaComponents.ListViewLabel {
                    objectName: `fit.results.value.${row.index}`
                    rightPadding: EaStyle.Sizes.fontPixelSize
                    horizontalAlignment: Text.AlignRight
                    color: row.outcome !== "" ? FitOutcomes.color(row.outcome) : EaStyle.Colors.themeForeground
                    text: row.outcome !== "" ? FitOutcomes.word(row.outcome) : row.value
                }
            }
        }
    }

    Item {
        id: agreementArea

        readonly property bool shown: agreementTable.count > 0
        // A long dataset list scrolls inside the table, so the dialog stays on the screen.
        readonly property real tableHeight: Math.min(agreementTable.contentHeight, agreementTable.headerItem ? agreementTable.headerItem.height + EaStyle.Sizes.tableRowHeight * 8 : agreementTable.contentHeight)

        y: listArea.height + (shown ? EaStyle.Sizes.fontPixelSize : 0)
        width: shown ? Math.max(AppSizes.messagesDialogContentWidth, AppSizes.iconOnlyColumnWidth + EaStyle.Sizes.fontPixelSize * 8 + dialog.factorColumns.length * dialog.factorWidth + EaStyle.Sizes.fontPixelSize * 2) : 0
        height: shown ? tableHeight + unitNote.height + EaStyle.Sizes.fontPixelSize * 0.5 : 0
        visible: shown

        DataTable {
            id: agreementTable

            objectName: "fit.results.agreement"
            width: parent.width
            height: agreementArea.tableHeight
            interactive: contentHeight > height
            defaultInfoText: ""
            sourceModel: dialog.agreement

            // The icon, the dataset, then one real column per factor.
            columnWidths: [AppSizes.iconOnlyColumnWidth, -1].concat(dialog.factorColumns.map(() => dialog.factorWidth))

            header: EaComponents.ListViewHeader {
                height: (dialog.structureHeaders ? 2 : 1) * EaStyle.Sizes.tableRowHeight

                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    id: datasetHeader

                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Dataset")
                }
                // The factor headers join the row as its own cells, after the dataset's (an Instantiator adds no
                // item of its own, so each header is the row's cell of its column).
                Instantiator {
                    model: dialog.factorColumns
                    onObjectAdded: (index, object) => object.parent = datasetHeader.parent
                    delegate: Item {
                        id: factorHeader

                        required property var modelData
                        required property int index

                        width: dialog.factorWidth
                        height: datasetHeader.height

                        EaComponents.ListViewLabel {
                            objectName: `fit.results.agreement.header.${factorHeader.index}`
                            width: parent.width
                            height: EaStyle.Sizes.tableRowHeight
                            horizontalAlignment: Text.AlignHCenter
                            textFormat: Text.RichText
                            text: factorHeader.modelData.factor
                        }
                        // The structure a phase factor belongs to, under its header, with its coloured icon.
                        Row {
                            visible: factorHeader.modelData.structure !== ""
                            y: EaStyle.Sizes.tableRowHeight
                            anchors.horizontalCenter: parent.horizontalCenter
                            height: EaStyle.Sizes.tableRowHeight
                            spacing: EaStyle.Sizes.fontPixelSize * 0.25

                            IconCell {
                                width: EaStyle.Sizes.fontPixelSize * 1.2
                                icon: "layer-group"
                                iconColor: factorHeader.modelData.place >= 0 ? AppColors.structure(factorHeader.modelData.place) : ""
                            }
                            EaComponents.ListViewLabel {
                                objectName: `fit.results.agreement.structure.${factorHeader.index}`
                                height: parent.height
                                width: Math.min(implicitWidth, dialog.factorWidth - EaStyle.Sizes.fontPixelSize * 1.5)
                                elide: Text.ElideRight
                                // The structure's chart colour, as its icon (the owner, 2026-10-21).
                                color: factorHeader.modelData.place >= 0 ? AppColors.structure(factorHeader.modelData.place) : EaStyle.Colors.themeForeground
                                text: factorHeader.modelData.structure
                            }
                        }
                    }
                }
            }

            delegate: TableRow {
                id: datasetRow

                required property string label
                required property int place
                required property var values

                // Read-only, as the summary (no hover, no selection, no click).
                enabled: false
                Component.onCompleted: dialog.passive(datasetRow)

                // The global row keeps an empty icon cell, so its cells stay in the dataset rows' columns.
                IconCell {
                    horizontalAlignment: Text.AlignHCenter
                    icon: datasetRow.place >= 0 ? "microscope" : ""
                    iconColor: datasetRow.place >= 0 ? AppColors.experiment(datasetRow.place) : ""
                }
                EaComponents.ListViewLabel {
                    id: datasetName

                    objectName: `fit.results.agreement.dataset.${datasetRow.index}`
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    color: EaStyle.Colors.themeForeground
                    text: datasetRow.label
                }
                Instantiator {
                    model: datasetRow.values
                    onObjectAdded: (index, object) => object.parent = datasetName.parent
                    delegate: NumberLabel {
                        required property string modelData
                        required property int index

                        objectName: `fit.results.agreement.value.${datasetRow.index}.${index}`
                        width: dialog.factorWidth
                        height: datasetName.height
                        horizontalAlignment: Text.AlignHCenter
                        color: EaStyle.Colors.themeForeground
                        number: modelData
                    }
                }
            }
        }
        EaElements.Label {
            id: unitNote

            objectName: "fit.results.agreement.note"
            y: agreementTable.height + EaStyle.Sizes.fontPixelSize * 0.5
            color: EaStyle.Colors.themeForegroundMinor
            text: qsTr("All R values are in %.")
        }
    }
}
