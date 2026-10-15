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
    property bool sendAfterConsent: false
    property string consentDraft: ""
    property string consentContext: ""
    function retireConsentSend() { sendAfterConsent = false; consentDraft = ""; consentContext = ""; }
    Connections {
        target: panel.assistant
        function onConversationRetired() { panel.retireConsentSend(); }
        function onConnectedChanged() { panel.retireConsentSend(); }
        function onConnectionLabelChanged() { panel.retireConsentSend(); }
        function onSelectedModelChanged() { panel.retireConsentSend(); }
        function onSelectedEffortChanged() { panel.retireConsentSend(); }
        function onContextPreviewChanged() {
            if (panel.sendAfterConsent && panel.assistant.contextPreview !== panel.consentContext) panel.retireConsentSend();
        }
    }
    required property Item toggleControl
    readonly property Item firstFocusItem: connectionButton
    property bool shown: Preferences.assistantShown
    onShownChanged: {
        if (!shown) { panel.retireConsentSend(); connectionDialog.close(); }
    }
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
            }
            Rectangle {
                width: EaStyle.Sizes.borderThickness
                height: parent.height
                x: Preferences.sideBarOnLeft ? parent.width - width : 0
                color: EaStyle.Colors.appBorder
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
                    spacing: AppSizes.unit
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
                    EaElements.Button {
                        id: clearButton
                        KeyNavigation.priority: KeyNavigation.BeforeItem
                        KeyNavigation.backtab: signOutButton.visible && signOutButton.enabled ? signOutButton : connectionButton
                        text: qsTr("Clear")
                        KeyNavigation.tab: usageButton
                        ToolTip.text: qsTr("Clear conversation")
                        Accessible.name: ToolTip.text
                        EaElements.ToolTip {
                            text: clearButton.ToolTip.text
                            visible: (clearButton.hovered || clearButton.activeFocus) && EaGlobals.Vars.showToolTips
                        }
                        onClicked: panel.assistant.clearHistory()
                    }
                    EaElements.ToolButton {
                        id: usageButton
                        objectName: "assistant.usage"
                        KeyNavigation.priority: KeyNavigation.BeforeItem
                        KeyNavigation.backtab: clearButton
                        ToolTip.text: qsTr("Usage data unavailable")
                        Accessible.name: qsTr("Usage data unavailable")
                        Accessible.description: qsTr("This connection does not provide context or subscription usage metrics.")
                        contentItem: Item {
                            implicitWidth: AppSizes.unit * 0.85 * 1.5
                            implicitHeight: AppSizes.unit * 0.85 * 1.5
                            Rectangle {
                                anchors.centerIn: parent
                                width: AppSizes.unit * 0.85 * 1.5
                                height: width
                                radius: width * 0.5
                                color: "transparent"
                                border.width: 2
                                border.color: EaStyle.Colors.themeForegroundDisabled
                            }
                        }
                        onClicked: usageDialog.open()
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
                id: chatBody
                z: 1
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                anchors.bottom: parent.bottom
                anchors.margins: AppSizes.unit
                spacing: AppSizes.unit * 0.855
                EaElements.Button {
                    objectName: "assistant.workflow"
                    Layout.fillWidth: true
                    text: {
                        for (let i = 0; i < panel.assistant.skills.count; ++i)
                            if (panel.assistant.skills.text(i, "id") === panel.assistant.selectedSkill)
                                return qsTr("Workflow: %1 · %2").arg(panel.assistant.skills.text(i, "title")).arg(panel.assistant.skills.text(i, "version"));
                        return qsTr("Skills · %1 available").arg(panel.assistant.skills.count);
                    }
                    Accessible.name: text
                    onClicked: skillsDialog.open()
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
                        highlighted: model.kind === "user" && model.id === conversation.jumpedUserId
                    }
                    property bool followsTail: true
                    property string jumpedUserId: ""
                    readonly property int previousUserIndex: userTarget(-1)
                    readonly property int nextUserIndex: userTarget(1)
                    function userTarget(direction) {
                        const count = panel.assistant.messages.count;
                        const position = contentY;
                        const layoutHeight = contentHeight;
                        if (count === 0 || layoutHeight <= 0) return -1;
                        // An explicit boundary remains the cursor even when the final row clamps at the end.
                        if (jumpedUserId.length > 0) {
                            let current = -1;
                            for (let i = 0; i < count; ++i)
                                if (panel.assistant.messages.text(i, "id") === jumpedUserId) { current = i; break; }
                            if (current >= 0) {
                                for (let i = current + direction; i >= 0 && i < count; i += direction)
                                    if (panel.assistant.messages.text(i, "kind") === "user") return i;
                                return -1;
                            }
                        }
                        let first = indexAt(1, position + 1);
                        if (first < 0) first = indexAt(1, position + spacing + 2);
                        if (first < 0) first = atYEnd ? count - 1 : 0;
                        let candidate = -1;
                        for (let i = 0; i < count; ++i) {
                            if (panel.assistant.messages.text(i, "kind") !== "user") continue;
                            const item = itemAtIndex(i);
                            const before = item ? item.y < position - 0.5 : i < first;
                            const after = item ? item.y > position + 0.5 : i > first;
                            if (direction < 0 && before) candidate = i;
                            if (direction > 0 && after) return i;
                        }
                        return direction < 0 ? candidate : -1;
                    }
                    function jumpToUser(direction) {
                        const target = direction < 0 ? previousUserIndex : nextUserIndex;
                        if (target < 0) return;
                        jumpedUserId = panel.assistant.messages.text(target, "id");
                        followsTail = false;
                        cancelFlick();
                        positionViewAtIndex(target, ListView.Beginning);
                    }
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
                            if (latest.length > 0) {
                                followsTail = true;
                                jumpedUserId = "";
                            }
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
                        if (moving || historyScrollBar.pressed) {
                            jumpedUserId = "";
                            followsTail = atYEnd;
                        }
                    }
                    onMovementStarted: jumpedUserId = ""
                    onMovementEnded: { if (jumpedUserId.length === 0) followsTail = atYEnd; }
                    Component.onCompleted: {
                        observeUserAdmission();
                        followOutput();
                    }
                    Connections {
                        target: panel.assistant.messages
                        function onDataChanged() { conversation.observeUserAdmission(); conversation.followOutput(); }
                    }
                    ScrollBar.vertical: EaElements.ScrollBar {
                        id: historyScrollBar
                        policy: ScrollBar.AsNeeded
                        interactive: false
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
                Rectangle {
                    Layout.fillWidth: true
                    Layout.leftMargin: -AppSizes.unit
                    Layout.rightMargin: -AppSizes.unit
                    implicitHeight: EaStyle.Sizes.borderThickness
                    color: EaStyle.Colors.appBorder
                }
                AssistantComposer {
                    id: composer
                    Layout.fillWidth: true
                    assistant: panel.assistant
                    toggleControl: panel.toggleControl
                    hasPreviousUserMessage: conversation.previousUserIndex >= 0
                    hasNextUserMessage: conversation.nextUserIndex >= 0
                    onPreviousUserRequested: conversation.jumpToUser(-1)
                    onNextUserRequested: conversation.jumpToUser(1)
                    onContextApprovalRequested: draft => {
                        panel.consentDraft = draft; panel.consentContext = panel.assistant.contextPreview; panel.sendAfterConsent = true;
                        connectionDialog.open();
                    }
                }
            }
            // One real file boundary covers transcript and composer, not ordinary text or the header.
            DropArea {
                id: chatFilesDrop
                anchors.fill: chatBody
                z: 2
                enabled: panel.visible && panel.shown && ApplicationInfo.assistantAvailable && !WebFiles.available
                onEntered: drag => drag.accepted = drag.hasUrls && !panel.assistant.canCancel
                onDropped: drop => {
                    if (!chatFilesDrop.enabled || !drop.hasUrls || panel.assistant.canCancel) { drop.accepted = false; return; }
                    const request = panel.assistant.beginFileSelection();
                    drop.accepted = request.length > 0 && panel.assistant.addSelectedFiles(request, drop.urls);
                }
            }
        }
        AppDialog {
            id: usageDialog
            title: qsTr("Usage")
            standardButtons: Dialog.Close
            width: Math.min(AppSizes.unit * 27, Math.max(0, parent.width - AppSizes.unit * 2))
            Column {
                width: parent.width
                spacing: AppSizes.unit
                EaElements.Label {
                    width: parent.width
                    text: qsTr("Context window: unavailable")
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                }
                EaElements.Label {
                    width: parent.width
                    text: qsTr("Subscription session and weekly limits: unavailable")
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                }
                EaElements.Label {
                    width: parent.width
                    text: qsTr("This connection does not supply these metrics. No usage percentage is inferred from conversation length or elapsed time.")
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                }
            }
        }
        AssistantSkillsDialog {
            id: skillsDialog
            assistant: panel.assistant
        }
        AssistantConnectionDialog {
            id: connectionDialog
            assistant: panel.assistant
            onRejected: panel.retireConsentSend()
            onContextApproved: {
                const send = panel.sendAfterConsent;
                const draft = panel.consentDraft;
                panel.retireConsentSend();
                if (send) composer.submitApprovedDraft(draft);
            }
        }
    }
}
