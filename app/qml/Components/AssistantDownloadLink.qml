// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import edi.app

IconLink {
    objectName: "assistant.desktopOnly.download"
    fontIcon: "external-link-alt"
    text: qsTr("Open the desktop download page")
    onClicked: Qt.openUrlExternally("https://enhantica.github.io/edi/application/desktop/")
}
