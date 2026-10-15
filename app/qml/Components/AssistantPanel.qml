// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Popup {
    id: panel
    objectName: "assistant.popup"
    required property AssistantViewModel assistant
    required property Item toggleControl
    readonly property Item firstFocusItem: connectionButton
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
    // Clip the moving sheet at the fixed sidebar viewport, including intermediate frames.
    clip: true
    background: null
    enter: Transition {
        NumberAnimation {
            target: assistantSheet
            property: "x"
            from: Preferences.sideBarOnLeft ? -panel.width : panel.width
            to: 0
            duration: EaStyle.Times.translationChange
            easing.type: Easing.OutCirc
        }
    }
    exit: Transition {
        NumberAnimation {
            target: assistantSheet
            property: "x"
            to: Preferences.sideBarOnLeft ? -panel.width : panel.width
            duration: EaStyle.Times.translationChange
            easing.type: Easing.InCirc
        }
    }
    function focusComposer() {
        if (!ApplicationInfo.assistantAvailable || !visible || !shown)
            return;
        composer.focusEditor();
    }

    contentItem: Item {
        objectName: "assistant.panel"
        clip: true
        // The complete fixed strip remains covered until Popup's actual exit finishes.
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            preventStealing: true
            onWheel: wheel => wheel.accepted = true
        }
        Item {
            id: assistantSheet
            width: parent.width
            height: parent.height
            enabled: panel.shown
            Rectangle {
                anchors.fill: parent
                color: EaStyle.Colors.appBarBackground
                border.color: EaStyle.Colors.appBorder
            }
            Item {
                id: header
                width: parent.width
                height: EaStyle.Sizes.tabBarHeight
                EaElements.Label {
                    anchors.left: parent.left
                    anchors.leftMargin: EaStyle.Sizes.fontPixelSize * 0.5
                    anchors.verticalCenter: parent.verticalCenter
                    textFormat: Text.PlainText
                    text: qsTr("Assistant")
                    font.bold: true
                    color: EaStyle.Colors.themeForegroundHovered
                }
                RowLayout {
                    anchors.right: parent.right
                    anchors.rightMargin: EaStyle.Sizes.fontPixelSize * 0.5
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: AppSizes.unit * 0.5
                    EaElements.Button {
                        id: connectionButton
                        objectName: "assistant.connection"
                        KeyNavigation.priority: KeyNavigation.BeforeItem
                        KeyNavigation.backtab: panel.toggleControl
                        KeyNavigation.tab: signOutButton.visible && signOutButton.enabled ? signOutButton : clearButton
                        Layout.maximumWidth: header.width * 0.45
                        text: !panel.assistant.connected && panel.assistant.state !== "connecting" ? qsTr("Sign in") : panel.assistant.connectionLabel
                        Accessible.name: text
                        contentItem: EaElements.Label {
                            text: connectionButton.text
                            textFormat: Text.PlainText
                            font: connectionButton.font
                            color: connectionButton.foregroundColor()
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        EaElements.ToolTip {
                            text: connectionButton.text
                            visible: (connectionButton.hovered || connectionButton.activeFocus) && EaGlobals.Vars.showToolTips
                        }
                        onClicked: connectionDialog.open()
                    }
                    EaElements.ToolButton {
                        id: signOutButton
                        KeyNavigation.priority: KeyNavigation.BeforeItem
                        KeyNavigation.backtab: connectionButton
                        KeyNavigation.tab: clearButton
                        visible: panel.assistant.connected
                        fontIcon: "sign-out-alt"
                        ToolTip.text: qsTr("Sign out")
                        Accessible.name: ToolTip.text
                        onClicked: panel.assistant.signOut()
                    }
                    EaElements.ToolButton {
                        id: clearButton
                        KeyNavigation.priority: KeyNavigation.BeforeItem
                        KeyNavigation.backtab: signOutButton.visible && signOutButton.enabled ? signOutButton : connectionButton
                        fontIcon: "trash-alt"
                        ToolTip.text: qsTr("Clear conversation")
                        Accessible.name: ToolTip.text
                        onClicked: panel.assistant.clearHistory()
                    }
                }
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: EaStyle.Sizes.borderThickness
                    color: EaStyle.Colors.appBorder
                }
            }
            ColumnLayout {
                z: 1
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                anchors.bottom: parent.bottom
                anchors.margins: AppSizes.unit
                spacing: AppSizes.unit * 0.75
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
                    toggleControl: panel.toggleControl
                }
            }
        }
        AssistantConnectionDialog {
            id: connectionDialog
            assistant: panel.assistant
        }
    }
}
