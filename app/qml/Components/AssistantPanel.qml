// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Rectangle {
    id: panel
    objectName: "assistant.panel"
    required property AssistantViewModel assistant
    property bool shown: Preferences.assistantShown
    property real panelWidth: Preferences.assistantWidth
    property bool onLeft: !Preferences.sideBarOnLeft
    property bool overlayMode: false
    visible: shown
    width: Math.min(panelWidth, parent ? parent.width : panelWidth)
    color: EaStyle.Colors.appBarBackground
    border.color: EaStyle.Colors.appBorder
    function focusComposer() {
        composer.focusEditor();
    }

    ColumnLayout {
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
                enabled: !panel.assistant.canCancel
                onClicked: panel.assistant.clearHistory()
            }
            EaElements.ToolButton {
                fontIcon: "times"
                ToolTip.text: qsTr("Hide assistant")
                Accessible.name: ToolTip.text
                onClicked: Preferences.assistantShown = false
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
                text: panel.assistant.connectionLabel
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
        RowLayout {
            Layout.fillWidth: true
            EaElements.ComboBox {
                id: models
                textFormat: Text.PlainText
                currentIndex: {
                    const count = panel.assistant.models.count;
                    for (let i = 0; i < count; ++i)
                        if (panel.assistant.models.text(i, "id") === panel.assistant.selectedModel)
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
                model: panel.assistant.models
                textRole: "displayName"
                enabled: panel.assistant.connected && !panel.assistant.canCancel
                Accessible.name: qsTr("Assistant model")
                onActivated: index => panel.assistant.selectedModel = panel.assistant.models.text(index, "id")
            }
            EaElements.ComboBox {
                id: efforts
                textFormat: Text.PlainText
                currentIndex: panel.assistant.availableEfforts.indexOf(panel.assistant.selectedEffort)
                objectName: "assistant.effort"
                Layout.preferredWidth: AppSizes.unit * 7
                model: panel.assistant.availableEfforts
                enabled: panel.assistant.connected && !panel.assistant.canCancel
                Accessible.name: qsTr("Reasoning effort")
                onActivated: index => panel.assistant.selectedEffort = panel.assistant.availableEfforts[index]
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
            onCountChanged: positionViewAtEnd()
            ScrollBar.vertical: ScrollBar {}
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
    MouseArea {
        objectName: "assistant.resizeHandle"
        width: AppSizes.unit * 0.5
        height: parent.height
        x: panel.onLeft ? parent.width - width : 0
        cursorShape: Qt.SizeHorCursor
        property real startX: 0
        property real startWidth: 0
        onPressed: mouse => {
            startX = mapToGlobal(mouse.x, mouse.y).x;
            startWidth = Preferences.assistantWidth;
        }
        onPositionChanged: mouse => {
            if (!pressed)
                return;
            const delta = mapToGlobal(mouse.x, mouse.y).x - startX;
            Preferences.assistantWidth = Math.max(AppSizes.assistantMinimumWidth, Math.min(AppSizes.assistantMaximumWidth, startWidth + (panel.onLeft ? delta : -delta)));
        }
        Accessible.name: qsTr("Resize assistant")
    }
    AssistantConnectionDialog {
        id: connectionDialog
        assistant: panel.assistant
    }
}
