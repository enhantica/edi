// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Rectangle {
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
    implicitHeight: composerContent.implicitHeight + AppSizes.unit
    color: EaStyle.Colors.contentBackground
    border.color: EaStyle.Colors.appBorder
    radius: AppSizes.unit * 0.75
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
    Column {
        id: composerContent
        x: AppSizes.unit * 0.5
        y: AppSizes.unit * 0.5
        width: parent.width - AppSizes.unit
        spacing: AppSizes.unit * 0.25
        ScrollView {
            width: parent.width
            height: Math.min(AppSizes.unit * 10, Math.max(AppSizes.unit * 4, editor.implicitHeight))
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
                padding: AppSizes.unit * 0.25
                background: null
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
        RowLayout {
            width: parent.width
            spacing: AppSizes.unit * 0.25
            EaElements.ComboBox {
                id: models
                textFormat: Text.PlainText
                displayText: currentIndex < 0 ? qsTr("Model") : currentText
                currentIndex: {
                    const count = composer.assistant.models.count;
                    for (let i = 0; i < count; ++i)
                        if (composer.assistant.models.text(i, "id") === composer.assistant.selectedModel)
                            return i;
                    return -1;
                }
                delegate: EaElements.MenuItem {
                    required property var model
                    required property int index
                    width: models.width
                    height: EaStyle.Sizes.comboBoxHeight
                    text: model.displayName
                    textFormat: Text.PlainText
                    enabled: model.available
                    highlighted: models.highlightedIndex === index
                }
                objectName: "assistant.model"
                Layout.fillWidth: true
                model: composer.assistant.models
                textRole: "displayName"
                enabled: composer.assistant.connected && !composer.assistant.canCancel
                Accessible.name: qsTr("Assistant model")
                onActivated: index => composer.assistant.selectedModel = composer.assistant.models.text(index, "id")
            }
            EaElements.ComboBox {
                id: efforts
                textFormat: Text.PlainText
                readonly property var effortValues: [""].concat(composer.assistant.availableEfforts)
                function effortLabel(value) {
                    switch (value) {
                    case "": return qsTr("Default");
                    case "none": return qsTr("None");
                    case "low": return qsTr("Low");
                    case "medium": return qsTr("Medium");
                    case "high": return qsTr("High");
                    case "xhigh": return qsTr("Extra high");
                    case "max": return qsTr("Maximum");
                    default: return qsTr("Unavailable");
                    }
                }
                currentIndex: effortValues.indexOf(composer.assistant.selectedEffort)
                objectName: "assistant.effort"
                Layout.preferredWidth: AppSizes.unit * 7
                model: effortValues.map(value => effortLabel(value))
                enabled: composer.assistant.connected && !composer.assistant.canCancel
                ToolTip.text: composer.assistant.selectedEffort === "" ? qsTr("Provider default") : currentText
                Accessible.name: qsTr("Reasoning effort")
                onActivated: index => composer.assistant.selectedEffort = effortValues[index]
            }
            EaElements.ToolButton {
                objectName: "assistant.stop"
                fontIcon: "stop"
                text: qsTr("Stop")
                ToolTip.text: text
                visible: composer.assistant.canCancel
                enabled: visible
                Accessible.name: text
                onClicked: composer.assistant.cancel()
            }
            EaElements.ToolButton {
                objectName: "assistant.send"
                fontIcon: "arrow-up"
                text: qsTr("Send")
                ToolTip.text: text
                highlighted: true
                visible: !composer.assistant.canCancel
                enabled: composer.assistant.connected && !composer.assistant.canCancel && editor.text.trim().length > 0
                Accessible.name: text
                onClicked: composer.submit()
            }
        }
    }
}
