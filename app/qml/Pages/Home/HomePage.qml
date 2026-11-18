// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Home page (easydiffractionbeta Pages/Home/Page.qml, ported): the wordmark as the official logo lays it
// out and the version, composed as in About (WordmarkWithVersion), Start, and two columns of light links with icons:
// tutorials, documentation and what's new, then Help and feedback, How to cite and About.
Item {
    id: home

    // The wordmark the intro lands in (HomeIntro), and whether the intro is playing.
    readonly property Wordmark wordmark: wordmarkBlock.wordmark
    property bool introRunning: false

    // The idle spin: after 30 s on Home without input, the logo turns twice, and again after each further 30 s
    // (the owner, 2026-11-14). Always on, apart from demo and test runs, whose images stay still.
    Timer {
        id: idleWait

        interval: 30000
        running: ApplicationInfo.homeIntroAllowed && !home.introRunning && EaGlobals.Vars.appBarCurrentIndex === 0 && home.Window.active
        repeat: true
        onTriggered: home.wordmark.spin()
    }
    Connections {
        target: ApplicationInfo
        function onUserInput() {
            if (idleWait.running)
                idleWait.restart();
        }
    }

    Column {
        anchors.centerIn: parent

        WordmarkWithVersion {
            id: wordmarkBlock
            anchors.horizontalCenter: parent.horizontalCenter
            versionObjectName: "home.version"
        }
        // A newer release, said here because Home has no status bar (owner, 2026-11-17).
        IconLink {
            objectName: "home.update"
            anchors.horizontalCenter: parent.horizontalCenter
            visible: DesktopUpdates.available
            fontIcon: "arrow-circle-up"
            text: qsTr("Update available")
            onClicked: AppState.updateDialogRequested()
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

        // Two columns of four links, left-aligned, each with its icon: using the app, and talking to the developers
        // (owner, 2026-11-17).
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
                // A web page: the icon says it opens outside the app.
                IconLink {
                    objectName: "home.documentation"
                    fontIcon: "external-link-alt"
                    text: qsTr("Documentation")
                    onClicked: Qt.openUrlExternally(ApplicationInfo.docsUrl)
                }
                IconLink {
                    objectName: "home.changes"
                    fontIcon: "bullhorn"
                    text: qsTr("What's new")
                    onClicked: AppState.whatsNewRequested()
                }
                IconLink {
                    objectName: "home.cite"
                    fontIcon: "quote-right"
                    text: qsTr("How to cite")
                    onClicked: citationDialog.open()
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
                // The likes bar on demand, whatever its timing rule.
                IconLink {
                    objectName: "home.likes"
                    fontIcon: "heart"
                    text: qsTr("Enjoying %1?").arg(ApplicationInfo.name)
                    onClicked: AppState.likesRequested()
                }
                IconLink {
                    objectName: "home.survey"
                    fontIcon: "external-link-alt"
                    text: qsTr("Take the user survey")
                    ToolTip.text: qsTr("About 10–15 minutes")
                    onClicked: Qt.openUrlExternally(ApplicationInfo.docsUrl + "about/survey/")
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
