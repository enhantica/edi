// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The About window (easydiffractionbeta Pages/Home/AboutDialog.qml), filled from ApplicationInfo, without tabs: the
// wordmark with the version, the description, two links, then the copyright (the owner, 2026-10-21). The first link
// names edi's own licences by their identifiers, each opening its text; the second opens the third-party components
// this build bundles (ADR-0015 §6). The links have the space around them that the description and the copyright had
// between them.
AppDialog {
    id: dialog

    // A licence text, plain and read-only, scrolling within the space it is given.
    component LicenceText: Flickable {
        id: flickable

        property alias text: textArea.text
        property alias textObjectName: textArea.objectName

        contentHeight: textArea.implicitHeight
        clip: true
        ScrollBar.vertical: EaElements.ScrollBar {
            policy: ScrollBar.AsNeeded
        }

        EaElements.TextArea {
            id: textArea

            width: flickable.width
            readOnly: true
            wrapMode: TextEdit.Wrap
            textFormat: TextEdit.PlainText
            font.family: EaStyle.Fonts.monoFontFamily
        }
    }
    // A link-coloured label that runs `activated` on a click.
    component LinkLabel: EaElements.Label {
        id: link

        signal activated

        color: EaStyle.Colors.link
        HoverHandler {
            cursorShape: Qt.PointingHandCursor
        }
        TapHandler {
            onTapped: link.activated()
        }
    }

    objectName: "about"
    visible: EaGlobals.Vars.showAppAboutDialog
    onClosed: EaGlobals.Vars.showAppAboutDialog = false

    title: qsTr("About")
    standardButtons: Dialog.Ok

    // Only as wide as its content, with a margin of the base's font size either side (the owner, 2026-10-21).
    contentWidth: aboutColumn.implicitWidth

    Column {
        id: aboutColumn

        width: implicitWidth
        leftPadding: EaStyle.Sizes.fontPixelSize
        rightPadding: EaStyle.Sizes.fontPixelSize
        spacing: EaStyle.Sizes.fontPixelSize * 2.0
        topPadding: EaStyle.Sizes.fontPixelSize

        WordmarkWithVersion {
            anchors.horizontalCenter: parent.horizontalCenter
            link: ApplicationInfo.homepageUrl
            versionObjectName: "about.version"
        }
        // The description, wrapped to about three lines of similar width: a third of its one-line width, with room for
        // the words to break.
        EaElements.Label {
            id: descriptionLabel

            objectName: "about.description"
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.ceil(descriptionMetrics.advanceWidth / 3 * 1.15)
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: ApplicationInfo.description

            TextMetrics {
                id: descriptionMetrics

                font: descriptionLabel.font
                text: descriptionLabel.text
            }
        }
        // The two links, one under the other, each after the licence icon.
        Column {
            objectName: "about.links"
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: EaStyle.Sizes.fontPixelSize * 0.5

            Row {
                objectName: "about.licences"
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: EaStyle.Sizes.fontPixelSize * 0.5

                IconLine {
                    segments: [
                        {
                            "icon": "balance-scale",
                            "color": EaStyle.Colors.themeForeground
                        }
                    ]
                }
                // The identifiers, a dot in the text colour between them: "BSD-3-Clause · GPL-3.0-only".
                Repeater {
                    model: ApplicationInfo.appLicences

                    Row {
                        id: licenceEntry

                        required property var modelData
                        required property int index

                        spacing: EaStyle.Sizes.fontPixelSize * 0.5

                        EaElements.Label {
                            visible: licenceEntry.index > 0
                            text: "·"
                        }
                        LinkLabel {
                            objectName: "about.licence." + licenceEntry.modelData.id
                            text: licenceEntry.modelData.id
                            onActivated: {
                                licencePopup.title = licenceEntry.modelData.id;
                                licencePopup.licence = ApplicationInfo.licenceText(licenceEntry.modelData.url);
                                licencePopup.open();
                            }
                        }
                    }
                }
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: EaStyle.Sizes.fontPixelSize * 0.5

                IconLine {
                    segments: [
                        {
                            "icon": "balance-scale",
                            "color": EaStyle.Colors.themeForeground
                        }
                    ]
                }
                LinkLabel {
                    objectName: "about.thirdParty"
                    text: qsTr("Third-party licences")
                    onActivated: thirdPartyPopup.open()
                }
            }
        }
        EaElements.Label {
            objectName: "about.copyright"
            anchors.horizontalCenter: parent.horizontalCenter
            text: "© %1-%2 %3".arg(ApplicationInfo.developerYearsFrom).arg(ApplicationInfo.developerYearsTo).arg(ApplicationInfo.copyrightHolder)
        }
    }

    // One of edi's own licences as plain text (LICENSE, COPYING).
    AppDialog {
        id: licencePopup

        property string licence: ""

        objectName: "about.licencePopup"
        parent: Overlay.overlay
        standardButtons: Dialog.Ok
        contentWidth: AppSizes.aboutWidth
        contentHeight: AppSizes.aboutHeight

        LicenceText {
            anchors.fill: parent
            textObjectName: "about.licence.text"
            text: licencePopup.licence
        }
    }

    // The third-party components this build bundles: component, version and licence. The table is as wide as its
    // columns, each cell keeps a cell's margins, and the rows look enabled and select nothing.
    AppDialog {
        id: thirdPartyPopup

        objectName: "about.thirdPartyPopup"
        parent: Overlay.overlay
        title: qsTr("Third-party licences")
        standardButtons: Dialog.Ok
        // The table sets its size, not an implicit one, so the popup is told how large its content is. The width is
        // set, not implicit: the OK button's box takes the popup's width, and an implicit width read it back.
        contentWidth: components.width
        contentHeight: components.height
        width: contentWidth + leftPadding + rightPadding

        ListModel {
            id: componentRows

            Component.onCompleted: {
                for (let index = 0; index < ApplicationInfo.componentNames.length; ++index)
                    append({
                        "component": ApplicationInfo.componentNames[index],
                        "version": ApplicationInfo.componentVersions[index],
                        "licence": ApplicationInfo.componentLicences[index]
                    });
            }
        }
        DataTable {
            id: components

            objectName: "about.components"
            readonly property var naturalWidths: [naturalTextColumnWidth("component", qsTr("Component")), naturalTextColumnWidth("version", qsTr("Version")), naturalTextColumnWidth("licence", qsTr("Licence"))]

            width: naturalWidths.reduce((sum, column) => sum + column, 0) + EaStyle.Sizes.tableColumnSpacing * (naturalWidths.length - 1) + EaStyle.Sizes.borderThickness * 2 + rowPadding * 2
            // As many rows as fit in the window with the popup's title and OK button, so the popup is never taller than
            // the window and stays centred in it; the rest scroll.
            maxRowCountShow: Math.max(3, Math.floor(((thirdPartyPopup.parent ? thirdPartyPopup.parent.height : 0) - EaStyle.Sizes.fontPixelSize * 14) / tableRowHeight) - 1)
            defaultInfoText: ""
            selectable: false
            sourceModel: componentRows

            columnWidths: naturalWidths

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    leftPadding: AppSizes.fieldSpacing
                    rightPadding: AppSizes.fieldSpacing
                    text: qsTr("Component")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    leftPadding: AppSizes.fieldSpacing
                    rightPadding: AppSizes.fieldSpacing
                    text: qsTr("Version")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    leftPadding: AppSizes.fieldSpacing
                    rightPadding: AppSizes.fieldSpacing
                    text: qsTr("Licence")
                }
            }

            delegate: TableRow {
                id: row

                highlightsHover: false

                required property string component
                required property string version
                required property string licence

                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    leftPadding: AppSizes.fieldSpacing
                    rightPadding: AppSizes.fieldSpacing
                    text: row.component
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    leftPadding: AppSizes.fieldSpacing
                    rightPadding: AppSizes.fieldSpacing
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.version
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    leftPadding: AppSizes.fieldSpacing
                    rightPadding: AppSizes.fieldSpacing
                    text: row.licence
                }
            }
        }
    }
}
