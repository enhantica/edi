// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The About window (easydiffractionbeta Pages/Home/AboutDialog.qml), filled from ApplicationInfo: one dialog with
// three tabs, as Preferences has, so nothing opens on top of it (the owner, 2026-10-10). About shows the wordmark
// with the version, the description and the copyright; Licence a short text for users, with either full licence
// text below it on request; Third-party software the components the app links or bundles, from the notices'
// list, with the selected one's licence text below.
AppDialog {
    id: dialog

    // A licence text: read-only, in the monospaced font, scrolling within the space it is given.
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

    contentWidth: AppSizes.aboutWidth
    contentHeight: AppSizes.aboutHeight

    EaElements.TabBar {
        id: bar

        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right

        background: Rectangle {
            z: 2
            anchors.fill: parent
            color: "transparent"
            border.color: EaStyle.Colors.appBarBorder
        }

        EaElements.AppBarTabButton {
            objectName: "about.tab.about"
            fontIcon: "info-circle"
            text: qsTr("About")
        }
        EaElements.AppBarTabButton {
            objectName: "about.tab.licence"
            fontIcon: "balance-scale"
            text: qsTr("Licence")
        }
        EaElements.AppBarTabButton {
            objectName: "about.tab.thirdParty"
            fontIcon: "cubes"
            text: qsTr("Third-party software")
        }
    }

    SwipeView {
        anchors.top: bar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        topPadding: EaStyle.Sizes.fontPixelSize
        currentIndex: bar.currentIndex
        interactive: false
        clip: true

        // About: the wordmark, then the version, each centred, as on Home (WordmarkWithVersion; edi ADR-0017
        // §1), the description and the copyright.
        Column {
            spacing: EaStyle.Sizes.fontPixelSize * 2.0
            topPadding: EaStyle.Sizes.fontPixelSize

            WordmarkWithVersion {
                anchors.horizontalCenter: parent.horizontalCenter
                link: ApplicationInfo.homepageUrl
                versionObjectName: "about.version"
            }
            // The description, wrapped to about three lines of similar width: a third of its one-line width,
            // with room for the words to break.
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
            EaElements.Label {
                objectName: "about.copyright"
                anchors.horizontalCenter: parent.horizontalCenter
                text: "© %1-%2 %3".arg(ApplicationInfo.developerYearsFrom).arg(ApplicationInfo.developerYearsTo).arg(ApplicationInfo.copyrightHolder)
            }
        }

        // Licence: what a user may do, in a few lines, and the full texts on request (ADR-0015 §6).
        Column {
            id: licencePage

            // The full text shown below the summary: none, the app's (GPL-3.0) or the source code's (BSD 3-Clause).
            property string shownUrl: ""

            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.Label {
                objectName: "about.licence.summary"
                width: parent.width
                wrapMode: Text.WordWrap
                textFormat: Text.MarkdownText
                text: qsTr("**EasyDiffraction is free software.** You may:\n\n- use it for any purpose;\n- share copies of it;\n- change it, and share your changes under the same licence, the GNU General Public License, version 3.\n\nIts source code is also available under the BSD 3-Clause License, so a part of it can be reused on its own.")
            }
            Row {
                spacing: EaStyle.Sizes.fontPixelSize * 2

                LinkLabel {
                    objectName: "about.licence.gpl"
                    text: qsTr("GNU General Public License")
                    onActivated: licencePage.shownUrl = ApplicationInfo.copyingUrl
                }
                LinkLabel {
                    objectName: "about.licence.bsd"
                    text: qsTr("BSD 3-Clause License")
                    onActivated: licencePage.shownUrl = ApplicationInfo.licenseUrl
                }
            }
            LicenceText {
                textObjectName: "about.licence.text"
                visible: licencePage.shownUrl !== ""
                width: parent.width
                height: licencePage.height - y
                text: licencePage.shownUrl ? ApplicationInfo.licenceText(licencePage.shownUrl) : ""
            }
        }

        // Third-party software: the notices' component list, columns as wide as their contents, and the selected
        // component's licence text below.
        Column {
            id: thirdPartyPage

            readonly property int selectedRow: components.selectedIndexes.length > 0 ? components.selectedIndexes[0].row : 0

            spacing: EaStyle.Sizes.fontPixelSize

            ListModel {
                id: componentRows

                Component.onCompleted: {
                    for (let index = 0; index < ApplicationInfo.componentNames.length; ++index)
                        append({
                            "component": ApplicationInfo.componentNames[index],
                            "version": ApplicationInfo.componentVersions[index],
                            "licence": ApplicationInfo.componentLicences[index],
                            "use": ApplicationInfo.componentUses[index]
                        });
                }
            }
            DataTable {
                id: components

                objectName: "about.components"
                width: parent.width
                maxRowCountShow: 8
                maximumTextColumnShare: 0.4
                defaultInfoText: ""
                sourceModel: componentRows

                columnWidths: [textColumnWidth("component", qsTr("Component")), textColumnWidth("version", qsTr("Version")), textColumnWidth("licence", qsTr("Licence")), -1]

                header: EaComponents.ListViewHeader {
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("Component")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("Version")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("Licence")
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("Used for")
                    }
                }

                delegate: EaComponents.ListViewDelegate {
                    id: row

                    required property int index
                    required property string component
                    required property string version
                    required property string licence
                    required property string use

                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: row.component
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        color: EaStyle.Colors.themeForegroundMinor
                        text: row.version
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: row.licence
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: row.use
                        ToolTip.text: row.use
                    }
                }
            }
            LicenceText {
                textObjectName: "about.components.licence"
                width: parent.width
                height: thirdPartyPage.height - y
                text: ApplicationInfo.componentLicenceText(thirdPartyPage.selectedRow)
            }
        }
    }
}
