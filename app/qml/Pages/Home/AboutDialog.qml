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
    visible: EaGlobals.Vars.showAppAboutDialog
    onClosed: EaGlobals.Vars.showAppAboutDialog = false

    title: qsTr("About")
    standardButtons: Dialog.Ok

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

                    objectName: `about.${modelData.name}`
                    anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined
                    color: EaStyle.Colors.link
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

        // The components the app links or bundles, each with its licence: the list the bundled notices give.
        EaComponents.TableView {
            id: components

            objectName: "about.components"
            anchors.horizontalCenter: parent.horizontalCenter
            width: AppSizes.aboutComponentsWidth
            height: AppSizes.aboutComponentsHeight
            clip: true
            defaultInfoText: ""
            model: ApplicationInfo.componentNames

            header: EaComponents.TableViewHeader {
                EaComponents.TableViewLabel {
                    flexibleWidth: true
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Component")
                }
                EaComponents.TableViewLabel {
                    width: AppSizes.aboutLicenceColumnWidth
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Licence")
                }
            }

            delegate: EaComponents.TableViewDelegate {
                id: row

                required property int index
                required property string modelData

                EaComponents.TableViewLabel {
                    width: components.headerLabelItems.length > 0 ? components.headerLabelItems[0].width : 0
                    horizontalAlignment: Text.AlignLeft
                    text: row.modelData
                    ToolTip.text: ApplicationInfo.componentUses[row.index]
                }
                EaComponents.TableViewLabel {
                    width: components.headerLabelItems.length > 1 ? components.headerLabelItems[1].width : 0
                    horizontalAlignment: Text.AlignLeft
                    text: ApplicationInfo.componentLicences[row.index]
                }
            }
        }

        // The footer, as easydiffractionbeta's, naming the copyright holder
        EaElements.Label {
            objectName: "about.copyright"
            anchors.horizontalCenter: parent.horizontalCenter
            text: "© %1-%2 %3 • All rights reserved".arg(ApplicationInfo.developerYearsFrom).arg(ApplicationInfo.developerYearsTo).arg(ApplicationInfo.copyrightHolder)
        }
    }

    LicenceTextDialog {
        id: licenceDialog
    }
}
