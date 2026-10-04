// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The Home page (easydiffractionbeta Pages/Home/Page.qml, ported): the wordmark as the official logo lays it
// out and the version, composed as in About (WordmarkWithVersion), Start, and the links. The tutorials stay disabled, as in the original v0.9.9.
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

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: AppSizes.homeLinkColumnsSpacing

            Column {
                spacing: AppSizes.homeLinkSpacing

                EaElements.Button {
                    objectName: "home.about"
                    text: qsTr("About %1").arg(ApplicationInfo.name)
                    onClicked: EaGlobals.Vars.showAppAboutDialog = true
                }
                EaElements.Button {
                    text: qsTr("Online documentation")
                    onClicked: Qt.openUrlExternally(ApplicationInfo.docsUrl)
                }
                EaElements.Button {
                    text: qsTr("Get in touch online")
                    onClicked: Qt.openUrlExternally(ApplicationInfo.contactUrl)
                }
            }

            Column {
                spacing: AppSizes.homeLinkSpacing

                EaElements.Button {
                    enabled: false
                    text: qsTr("Tutorial") + " 1: " + qsTr("App interface")
                }
                EaElements.Button {
                    enabled: false
                    text: qsTr("Tutorial") + " 2: " + qsTr("Basic usage")
                }
                EaElements.Button {
                    enabled: false
                    text: qsTr("Tutorial") + " 3: " + qsTr("Advanced usage")
                }
            }
        }
    }

    AboutDialog {}
}
