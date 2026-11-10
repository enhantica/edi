// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import edi.app

// How to cite (Home), an information window (InfoDialog): the citation from CITATION.cff in the text panel, and the
// bottom row's DOI link, with the external-resource icon, then Copy as text and Copy as BibTeX, left of Close (the
// owner, 2026-11-10).
InfoDialog {
    id: dialog

    property var citation: ({})

    objectName: "citation"
    title: qsTr("How to cite")
    standardButtons: Dialog.Close
    textObjectName: "citation.text"
    text: citation.text ?? ""

    onAboutToShow: citation = ApplicationInfo.citation()

    actions: [
        InfoDialog.InfoButton {
            objectName: "citation.doi"
            visible: (dialog.citation.doiUrl ?? "") !== ""
            fontIcon: "external-link-alt"
            text: qsTr("DOI")
            ToolTip.text: dialog.citation.doiUrl ?? ""
            onClicked: Qt.openUrlExternally(dialog.citation.doiUrl)
        },
        InfoDialog.InfoButton {
            objectName: "citation.copy.text"
            fontIcon: "copy"
            text: qsTr("Copy as text")
            onClicked: ApplicationInfo.copyText(dialog.citation.text ?? "")
        },
        InfoDialog.InfoButton {
            objectName: "citation.copy.bibtex"
            fontIcon: "copy"
            text: qsTr("Copy as BibTeX")
            onClicked: ApplicationInfo.copyText(dialog.citation.bibtex ?? "")
        }
    ]
}
