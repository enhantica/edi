// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Popup {
    id: panel
    objectName: "assistant.popup"
    required property AssistantViewModel assistant
    property bool shown: Preferences.assistantShown
    visible: ApplicationInfo.assistantAvailable && shown
    x: 0
    y: 0
    width: parent ? parent.width : 0
    height: parent ? parent.height : 0
    padding: 0
    margins: 0
    modal: false
    dim: false
    focus: true
    popupType: Popup.Item
    closePolicy: Popup.NoAutoClose
    background: Rectangle {
        color: EaStyle.Colors.appBarBackground
        border.color: EaStyle.Colors.appBorder
    }
    function focusComposer() {
        if (!ApplicationInfo.assistantAvailable || !visible)
            return;
        composer.focusEditor();
    }

    contentItem: Item {
        objectName: "assistant.panel"
        clip: true
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            preventStealing: true
            onWheel: wheel => wheel.accepted = true
        }
        ColumnLayout {
            z: 1
            anchors.fill: parent
            anchors.margins: AppSizes.unit
            spacing: AppSizes.unit * 0.75
            RowLayout {
                Layout.fillWidth: true
                EaElements.Label {
                textFormat: Text.PlainText
                    text: qsTr("Assistant")
                    font.bold: true
                    Layout.fillWidth: true
                }
                EaElements.ToolButton {
                    fontIcon: "trash-alt"
                    ToolTip.text: qsTr("Clear conversation")
                    Accessible.name: ToolTip.text
                    onClicked: panel.assistant.clearHistory()
                }
            }
            RowLayout {
                Layout.fillWidth: true
                EaElements.Button {
                    id: connectionButton
                    objectName: "assistant.connection"
                    contentItem: EaElements.Label {
                        text: connectionButton.text
                        textFormat: Text.PlainText
                        font: connectionButton.font
                        color: connectionButton.foregroundColor()
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                    Layout.fillWidth: true
                    text: !panel.assistant.connected && panel.assistant.state !== "connecting" ? qsTr("Sign in with ChatGPT") : panel.assistant.connectionLabel
                    onClicked: connectionDialog.open()
                }
                EaElements.ToolButton {
                    visible: panel.assistant.connected
                    fontIcon: "sign-out-alt"
                    ToolTip.text: qsTr("Sign out")
                    Accessible.name: ToolTip.text
                    onClicked: panel.assistant.signOut()
                }
            }
            EaElements.Label {
                textFormat: Text.PlainText
                Layout.fillWidth: true
                visible: !panel.assistant.connected
                wrapMode: Text.Wrap
                text: qsTr("Ask about the open project, inspect parameters, and refine through an agreed plan. Connect your ChatGPT subscription to start.")
            }
            ListView {
                id: conversation
                objectName: "assistant.messages"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: AppSizes.unit * 0.5
                model: panel.assistant.messages
                reuseItems: true
                delegate: AssistantMessage {
                    required property var model
                    width: conversation.width
                    kind: model.kind
                    text: model.text
                    payload: model.payload
                    status: model.status
                }
                property bool followsTail: true
                property string lastUserId: ""
                function observeUserAdmission() {
                    let latest = "";
                    for (let i = panel.assistant.messages.count - 1; i >= 0; --i) {
                        if (panel.assistant.messages.text(i, "kind") === "user") {
                            latest = panel.assistant.messages.text(i, "id");
                            break;
                        }
                    }
                    if (latest !== lastUserId) {
                        if (latest.length > 0)
                            followsTail = true;
                        lastUserId = latest;
                    }
                }
                function positionAtTail() {
                    if (followsTail)
                        positionViewAtEnd();
                }
                function followOutput() {
                    if (followsTail)
                        Qt.callLater(positionAtTail);
                }
                onCountChanged: {
                    observeUserAdmission();
                    followOutput();
                }
                onContentHeightChanged: followOutput()
                onContentYChanged: {
                    if (moving || historyScrollBar.pressed)
                        followsTail = atYEnd;
                }
                onMovementEnded: followsTail = atYEnd
                Component.onCompleted: {
                    observeUserAdmission();
                    followOutput();
                }
                Connections {
                    target: panel.assistant.messages
                    function onDataChanged() { conversation.observeUserAdmission(); conversation.followOutput(); }
                }
                ScrollBar.vertical: ScrollBar {
                    id: historyScrollBar
                    onPressedChanged: {
                        if (!pressed)
                            conversation.followsTail = conversation.atYEnd;
                    }
                    onPositionChanged: {
                        if (activeFocus) {
                            Qt.callLater(() => {
                                if (historyScrollBar.activeFocus)
                                    conversation.followsTail = conversation.atYEnd;
                            });
                        }
                    }
                }
            }
            AssistantPlan {
                Layout.fillWidth: true
                assistant: panel.assistant
            }
            AssistantQuestion {
                Layout.fillWidth: true
                assistant: panel.assistant
            }
            AssistantTrial {
                Layout.fillWidth: true
                assistant: panel.assistant
            }
            EaElements.Label {
                textFormat: Text.PlainText
                Layout.fillWidth: true
                visible: panel.assistant.lastError.length > 0
                text: panel.assistant.lastError
                wrapMode: Text.Wrap
            }
            EaElements.Button {
                Layout.fillWidth: true
                visible: panel.assistant.connected && panel.assistant.contextConsentRequired
                text: qsTr("Inspect outgoing project context")
                onClicked: connectionDialog.open()
            }
            AssistantComposer {
                id: composer
                Layout.fillWidth: true
                assistant: panel.assistant
            }
        }
        AssistantConnectionDialog {
            id: connectionDialog
            assistant: panel.assistant
        }
    }
}
