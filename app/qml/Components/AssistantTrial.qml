// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import EasyApplication.Gui.Elements as EaElements
import edi.app

EaElements.Label {
    required property AssistantViewModel assistant
    visible: assistant.activeJobId.length > 0
    text: qsTr("Refinement trial running · %1").arg(assistant.activeJobId)
    wrapMode: Text.Wrap
}
