// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// How to cite (Home): the citation as text and its DOI, both from CITATION.cff, copied as text or as BibTeX.
AppDialog {
    id: dialog

    property var citation: ({})

    objectName: "citation"
    title: qsTr("How to cite")
    standardButtons: Dialog.Close
    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: column.implicitHeight

    onAboutToShow: citation = ApplicationInfo.citation()

    Column {
        id: column

        width: dialog.contentWidth
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.Label {
            objectName: "citation.text"
            width: parent.width
            wrapMode: Text.WordWrap
            text: dialog.citation.text ?? ""
        }
        EaElements.Label {
            objectName: "citation.doi"
            width: parent.width
            wrapMode: Text.WordWrap
            textFormat: Text.StyledText
            // The base label opens its https link in the browser.
            text: dialog.citation.doiUrl ? `DOI: <a href="${dialog.citation.doiUrl}">${dialog.citation.doi}</a>` : ""
        }
        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                objectName: "citation.copy.text"
                width: (column.width - parent.spacing) / 2
                fontIcon: "copy"
                text: qsTr("Copy as text")
                onClicked: ApplicationInfo.copyText(dialog.citation.text ?? "")
            }
            EaElements.SideBarButton {
                objectName: "citation.copy.bibtex"
                width: (column.width - parent.spacing) / 2
                fontIcon: "copy"
                text: qsTr("Copy as BibTeX")
                onClicked: ApplicationInfo.copyText(dialog.citation.bibtex ?? "")
            }
        }
    }
}
