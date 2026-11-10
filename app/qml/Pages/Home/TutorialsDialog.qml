// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Templates as T

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// Tutorials (Home): one row per built-in tutorial (app/tutorials/manifest.json), the list growing as tutorials are
// added, drawn as the Examples list draws an example: number, title with its chips and a one-line description
// (ExampleCell), under the Examples list's filters (ExampleFilters), which filter the tutorials by text and by their
// tags. A click anywhere on a row starts its tutorial, as a click on an example opens it; the tutorial shows its
// steps one at a time (TutorialPanel).
AppDialog {
    id: dialog

    readonly property var tutorials: ApplicationInfo.tutorials()
    readonly property ExampleListModel catalogue: ApplicationInfo.tutorialCatalogue

    function tutorialNamed(id) {
        return dialog.tutorials.find(tutorial => tutorial.id === id);
    }

    // Wide enough for the longest description on one line (number column and cell margins included), up to about
    // 80 % of the window; below that a description wraps (the owner, 2026-11-10).
    readonly property real longestDetail: Math.max(0, ...dialog.tutorials.map(tutorial => detailMetrics.advanceWidth(tutorial.description ?? "")))
    readonly property real neededWidth: dialog.longestDetail + EaStyle.Sizes.fontPixelSize * 5
    property real widthCap: AppSizes.messagesDialogContentWidth
    readonly property bool wraps: dialog.neededWidth > dialog.widthCap

    objectName: "tutorials"
    title: qsTr("Tutorials")
    standardButtons: Dialog.Close
    contentWidth: Math.min(Math.max(AppSizes.messagesDialogContentWidth, dialog.neededWidth), dialog.widthCap)
    // The cap read from the window as the dialog opens, not bound to it: the dialog's own size feeds the window's
    // overlay, so a binding would loop.
    onAboutToShow: dialog.widthCap = Math.max(AppSizes.messagesDialogContentWidth, (Overlay.overlay ? Overlay.overlay.width : 0) * 0.8)
    contentHeight: content.implicitHeight

    // The descriptions' font, as a label draws it.
    FontMetrics {
        id: detailMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }

    Column {
        id: content

        width: dialog.contentWidth
        spacing: AppSizes.groupContentSpacing

        ExampleFilters {
            catalogue: dialog.catalogue
            namePrefix: "tutorials"
            searchHint: qsTr("Search tutorials")
            rowWidth: dialog.contentWidth
        }
        // The base list without the tables' column fitting: its rows are made once, as the list shows, never also for
        // measuring. Six and a half rows tall, the half row showing there is more, and it scrolls through the rest
        // (the owner, 2026-11-10); the height stays while filtering, so the dialog keeps its size.
        EaComponents.ListView {
            id: table

            objectName: "tutorials.list"
            width: dialog.contentWidth
            tableRowHeight: Math.ceil(EaStyle.Sizes.fontPixelSize * (dialog.wraps ? 7 : 5.5))
            maxRowCountShow: 6
            height: table.tableRowHeight * 6.5
            // Every row built, those below the fold too, so each tutorial's row can be found and scrolled to.
            cacheBuffer: table.tableRowHeight * Math.max(1, dialog.tutorials.length)
            selectable: false
            multiSelection: false
            defaultInfoText: qsTr("No matching tutorials")
            model: dialog.catalogue
            columnWidths: [EaStyle.Sizes.fontPixelSize * 2.5, EaStyle.Sizes.tableColumnFlex]
            delegate: TableRow {
                id: row

                required property string exampleId
                required property string name
                required property string detail
                required property list<string> tagLabels
                required property list<string> tagIcons
                required property list<string> tagColors
                required property list<string> tagDarkColors

                objectName: `tutorials.row.${exampleId}`
                Accessible.description: row.detail

                // The whole row is the tutorial's button: drawn by the row (its hover tint), with the pointing hand.
                T.AbstractButton {
                    objectName: `tutorials.open.${row.exampleId}`
                    parent: row
                    anchors.fill: parent
                    // One tutorial at a time (TutorialPanel).
                    enabled: !AppState.tutorialRunning
                    hoverEnabled: false
                    Accessible.name: row.name
                    HoverHandler {
                        cursorShape: Qt.PointingHandCursor
                    }
                    onClicked: {
                        const tutorial = dialog.tutorialNamed(row.exampleId);
                        dialog.close();
                        AppState.tutorialRequested(tutorial);
                    }
                }

                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                ExampleCell {
                    height: row.height
                    title: row.name
                    tagLabels: row.tagLabels
                    tagIcons: row.tagIcons
                    tagColors: row.tagColors
                    tagDarkColors: row.tagDarkColors
                    detail: row.detail
                    wrapDetail: dialog.wraps
                }
            }
        }
    }
}
