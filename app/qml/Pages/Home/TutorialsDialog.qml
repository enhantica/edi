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

    objectName: "tutorials"
    title: qsTr("Tutorials")
    standardButtons: Dialog.Close
    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: content.implicitHeight

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
        // measuring, and the three short tutorials need no fitted widths. As tall as the whole list, so the window
        // keeps its size while filtering.
        EaComponents.ListView {
            id: table

            objectName: "tutorials.list"
            width: dialog.contentWidth
            tableRowHeight: Math.ceil(EaStyle.Sizes.fontPixelSize * 5.5)
            maxRowCountShow: dialog.tutorials.length
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
                }
            }
        }
    }
}
