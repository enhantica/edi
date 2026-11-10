// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Home page (easydiffractionbeta Pages/Home/Page.qml, ported): the wordmark as the official logo lays it
// out and the version, composed as in About (WordmarkWithVersion), Start, and two columns of light links with icons:
// tutorials, documentation and what's new, then Help and feedback, How to cite and About.
Item {
    Column {
        anchors.centerIn: parent

        WordmarkWithVersion {
            anchors.horizontalCenter: parent.horizontalCenter
            versionObjectName: "home.version"
        }

        Item {
            width: 1
            height: AppSizes.homeBlockSpacer
        }

        EaElements.SideBarButton {
            objectName: "home.start"
            anchors.horizontalCenter: parent.horizontalCenter
            fontIcon: "rocket"
            text: qsTr("Start")
            onClicked: AppState.open(AppState.Page.Project)
        }

        Item {
            width: 1
            height: AppSizes.homeBlockSpacer
        }

        // Two columns of three links, left-aligned, each with its icon: learning the app, and getting in touch.
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: AppSizes.homeLinkColumnsSpacing

            Column {
                objectName: "home.learn"
                spacing: AppSizes.homeLinkSpacing

                IconLink {
                    objectName: "home.tutorials"
                    fontIcon: "graduation-cap"
                    text: qsTr("Tutorials")
                    onClicked: tutorialsDialog.open()
                }
                IconLink {
                    objectName: "home.changes"
                    fontIcon: "bullhorn"
                    text: qsTr("What's new")
                    onClicked: AppState.whatsNewRequested()
                }
                // A web page: the icon says it opens outside the app.
                IconLink {
                    objectName: "home.documentation"
                    fontIcon: "external-link-alt"
                    text: qsTr("Documentation")
                    onClicked: Qt.openUrlExternally(ApplicationInfo.docsUrl)
                }
            }

            Column {
                objectName: "home.contact"
                spacing: AppSizes.homeLinkSpacing

                IconLink {
                    objectName: "home.feedback"
                    fontIcon: "comments"
                    text: qsTr("Help and feedback")
                    onClicked: AppState.feedbackRequested("feedback", "")
                }
                IconLink {
                    objectName: "home.cite"
                    fontIcon: "quote-right"
                    text: qsTr("How to cite")
                    onClicked: citationDialog.open()
                }
                IconLink {
                    objectName: "home.about"
                    fontIcon: "info-circle"
                    text: qsTr("About %1").arg(ApplicationInfo.name)
                    onClicked: EaGlobals.Vars.showAppAboutDialog = true
                }
            }
        }
    }

    CitationDialog {
        id: citationDialog
    }
    TutorialsDialog {
        id: tutorialsDialog
    }
    AboutDialog {}
}
