// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// How to cite (Home): the citation as text and its DOI as a link, both from CITATION.cff. The buttons left of Close
// copy it as text or as BibTeX.
AppDialog {
    id: dialog

    property var citation: ({})

    objectName: "citation"
    title: qsTr("How to cite")
    standardButtons: Dialog.Close
    contentWidth: AppSizes.messagesDialogContentWidth
    contentHeight: column.implicitHeight

    onAboutToShow: citation = ApplicationInfo.citation()

    footer: EaElements.DialogButtonBox {
        EaElements.Button {
            objectName: "citation.copy.text"
            fontIcon: "copy"
            text: qsTr("Copy as text")
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            onClicked: ApplicationInfo.copyText(dialog.citation.text ?? "")
        }
        EaElements.Button {
            objectName: "citation.copy.bibtex"
            fontIcon: "copy"
            text: qsTr("Copy as BibTeX")
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            onClicked: ApplicationInfo.copyText(dialog.citation.bibtex ?? "")
        }
    }

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
        // The DOI as a light link with the external-resource icon, as About's licence links are.
        IconLink {
            objectName: "citation.doi"
            visible: (dialog.citation.doiUrl ?? "") !== ""
            fontIcon: "external-link-alt"
            text: "DOI: " + (dialog.citation.doi ?? "")
            onClicked: Qt.openUrlExternally(dialog.citation.doiUrl)
        }
    }
}
