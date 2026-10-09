// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The About dialog (easydiffractionbeta Pages/Home/AboutDialog.qml), filled from ApplicationInfo. It follows
// the base's EaComponents.AboutDialog section for section, with the wordmark as the official logo lays it out
// (Components/Wordmark.qml) in place of the base's one-line name, which that dialog cannot stack. The
// wordmark and the version are composed as on Home, from the one component (WordmarkWithVersion; edi
// ADR-0017 §1).
AppDialog {
    standardButtons: Dialog.Ok
    title: qsTr("About")
    visible: EaGlobals.Vars.showAppAboutDialog

    onClosed: EaGlobals.Vars.showAppAboutDialog = false

    Column {
        spacing: EaStyle.Sizes.fontPixelSize * 2.0

        // The wordmark, then the version, each centred, as on Home
        WordmarkWithVersion {
            anchors.horizontalCenter: parent.horizontalCenter
            link: ApplicationInfo.homepageUrl
            versionObjectName: "about.version"
        }

        // The licences, each bundled in the app and opened in the viewer below: the app's own licence notice
        // (GPL-3.0 for the built app, BSD 3-Clause for its source; ADR-0015 §6), and the notices of every
        // component the app links or bundles.
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: EaStyle.Sizes.fontPixelSize * 0.5

            Repeater {
                model: [
                    {
                        "name": "licenceLink",
                        "title": qsTr("Licence"),
                        "url": ApplicationInfo.appLicenseUrl
                    },
                    {
                        "name": "noticesLink",
                        "title": qsTr("Dependent Open Source Licenses"),
                        "url": ApplicationInfo.noticesUrl
                    }
                ]

                delegate: EaElements.Label {
                    id: link

                    required property var modelData

                    anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                    color: EaStyle.Colors.link
                    objectName: `about.${modelData.name}`
                    text: modelData.title

                    HoverHandler {
                        cursorShape: Qt.PointingHandCursor
                    }
                    TapHandler {
                        onTapped: licenceDialog.showText(link.modelData.title, link.modelData.url)
                    }
                }
            }
        }

        // The description, wrapped to about three lines of similar width: a third of its one-line width,
        // with room for the words to break.
        EaElements.Label {
            id: descriptionLabel

            anchors.horizontalCenter: parent.horizontalCenter
            horizontalAlignment: Text.AlignHCenter
            objectName: "about.description"
            text: ApplicationInfo.description
            width: Math.ceil(descriptionMetrics.advanceWidth / 3 * 1.15)
            wrapMode: Text.WordWrap

            TextMetrics {
                id: descriptionMetrics

                font: descriptionLabel.font
                text: descriptionLabel.text
            }
        }

        // The components the app links or bundles, each with its licence: the list the bundled notices give.
        DataTable {
            id: components

            anchors.horizontalCenter: parent.horizontalCenter
            clip: true
            columnWidths: [-1, AppSizes.aboutLicenceColumnWidth]
            defaultInfoText: ""
            height: AppSizes.aboutComponentsHeight
            model: ApplicationInfo.componentNames
            objectName: "about.components"
            width: AppSizes.aboutComponentsWidth

            delegate: EaComponents.ListViewDelegate {
                id: row

                required property int index
                required property string modelData

                EaComponents.TableViewLabel {
                    ToolTip.text: ApplicationInfo.componentUses[row.index]
                    horizontalAlignment: Text.AlignLeft
                    text: row.modelData
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: ApplicationInfo.componentLicences[row.index]
                }
            }
            header: EaComponents.ListViewHeader {
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Component")
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Licence")
                }
            }
        }

        // The footer, as easydiffractionbeta's, naming the copyright holder
        EaElements.Label {
            anchors.horizontalCenter: parent.horizontalCenter
            objectName: "about.copyright"
            text: "© %1-%2 %3 • All rights reserved".arg(ApplicationInfo.developerYearsFrom).arg(ApplicationInfo.developerYearsTo).arg(ApplicationInfo.copyrightHolder)
        }
    }
    LicenceTextDialog {
        id: licenceDialog
    }
}
