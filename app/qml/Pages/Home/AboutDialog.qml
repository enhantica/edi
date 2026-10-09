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
                        "title": qsTr("Dependent Open Source Libraries"),
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
                        onTapped: {
                            if (link.modelData.name === "noticesLink")
                                librariesDialog.open();
                            else
                                licenceDialog.showText(link.modelData.title, link.modelData.url);
                        }
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

        // The footer, as easydiffractionbeta's, naming the copyright holder
        EaElements.Label {
            objectName: "about.copyright"
            anchors.horizontalCenter: parent.horizontalCenter
            text: "© %1-%2 %3".arg(ApplicationInfo.developerYearsFrom).arg(ApplicationInfo.developerYearsTo).arg(ApplicationInfo.copyrightHolder)
        }
    }

    AppDialog {
        id: librariesDialog
        objectName: "about.librariesDialog"
        parent: Overlay.overlay
        title: qsTr("Dependent Open Source Libraries")
        standardButtons: Dialog.Ok
        contentWidth: AppSizes.aboutComponentsWidth
        contentHeight: AppSizes.aboutComponentsHeight + EaStyle.Sizes.tableRowHeight + AppSizes.groupContentSpacing

        ListModel {
            id: libraryRows
            Component.onCompleted: {
                for (let index = 0; index < ApplicationInfo.componentNames.length; ++index)
                    append({
                        "component": ApplicationInfo.componentNames[index],
                        "licence": ApplicationInfo.componentLicences[index],
                        "use": ApplicationInfo.componentUses[index]
                    });
            }
        }
        Column {
            spacing: AppSizes.groupContentSpacing
            DataTable {
                id: components

                objectName: "about.components"
                width: AppSizes.aboutComponentsWidth
                height: AppSizes.aboutComponentsHeight
                clip: true
                defaultInfoText: ""
                model: libraryRows

                columnWidths: [-1, textColumnWidth("licence", qsTr("Licence"))]

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

                delegate: EaComponents.ListViewDelegate {
                    id: row

                    required property int index
                    required property string component
                    required property string licence
                    required property string use

                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: row.component
                        ToolTip.text: row.use
                    }
                    EaComponents.TableViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: row.licence
                        ToolTip.text: row.licence
                    }
                }
            }

            EaElements.Label {
                text: qsTr("Licences and notices")
                color: EaStyle.Colors.link
                HoverHandler {
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler {
                    onTapped: licenceDialog.showText(qsTr("Dependent Open Source Licenses"), ApplicationInfo.noticesUrl)
                }
            }
        }
    }

    LicenceTextDialog {
        id: licenceDialog
    }
}
