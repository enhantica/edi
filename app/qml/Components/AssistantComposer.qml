// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Column {
    id: composer
    required property AssistantViewModel assistant
    property string submittedText: ""
    property var previousMessageIds: []
    function acknowledgeVisiblePrompt() {
        if (submittedText.length === 0)
            return;
        for (let i = 0; i < assistant.messages.count; ++i) {
            if (previousMessageIds.indexOf(assistant.messages.text(i, "id")) < 0 && assistant.messages.text(i, "kind") === "user" && assistant.messages.text(i, "text") === submittedText) {
                if (editor.text === submittedText)
                    editor.clear();
                submittedText = "";
                return;
            }
        }
    }
    Connections {
        target: composer.assistant.messages
        function onCountChanged() { composer.acknowledgeVisiblePrompt(); }
        function onDataChanged() { composer.acknowledgeVisiblePrompt(); }
    }
    spacing: AppSizes.unit * 0.5
    function focusEditor() {
        editor.forceActiveFocus();
    }
    function submit() {
        if (!assistant.connected || assistant.canCancel || editor.text.trim().length === 0)
            return;
        submittedText = editor.text;
        const ids = [];
        for (let i = 0; i < assistant.messages.count; ++i)
            ids.push(assistant.messages.text(i, "id"));
        previousMessageIds = ids;
        assistant.send(submittedText);
        acknowledgeVisiblePrompt();
    }
    ScrollView {
        width: parent.width
        height: Math.min(AppSizes.unit * 10, Math.max(AppSizes.unit * 5, editor.implicitHeight))
        TextArea {
            id: editor
            objectName: "assistant.composer"
            placeholderText: qsTr("Ask about your project or describe a refinement plan…")
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            color: EaStyle.Colors.themeForeground
            placeholderTextColor: EaStyle.Colors.themeForegroundMinor
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            padding: AppSizes.unit * 0.75
            background: Rectangle {
                color: EaStyle.Colors.contentBackground
                border.color: EaStyle.Colors.appBorder
                radius: AppSizes.unit * 0.5
            }
            Accessible.name: qsTr("Message to the assistant")
            Keys.onReturnPressed: event => {
                if (event.modifiers & Qt.ShiftModifier) {
                    event.accepted = false;
                } else {
                    composer.submit();
                    event.accepted = true;
                }
            }
        }
    }
    Row {
        anchors.right: parent.right
        spacing: AppSizes.unit * 0.5
        EaElements.Button {
            objectName: "assistant.stop"
            text: qsTr("Stop")
            enabled: composer.assistant.canCancel
            Accessible.name: text
            onClicked: composer.assistant.cancel()
        }
        EaElements.Button {
            objectName: "assistant.send"
            text: qsTr("Send")
            highlighted: true
            enabled: composer.assistant.connected && !composer.assistant.canCancel && editor.text.trim().length > 0
            Accessible.name: text
            onClicked: composer.submit()
        }
    }
}
