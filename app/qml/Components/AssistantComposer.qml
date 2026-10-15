// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Rectangle {
    id: composer
    required property AssistantViewModel assistant
    required property Item toggleControl
    property bool hasPreviousUserMessage: false
    property bool hasNextUserMessage: false
    signal previousUserRequested()
    signal nextUserRequested()
    signal contextApprovalRequested(string draft)
    property int textRevision: 0
    property int selectionRevision: -1
    property int savedSelectionStart: 0
    property int savedSelectionEnd: 0
    property string submittedText: ""
    readonly property bool canSteer: assistant.state === "agent_active"
    readonly property bool hasDraft: editor.text.trim().length > 0
    property var previousMessageIds: []
    function chooseFiles() {
        if (WebFiles.available || assistant.canCancel) return;
        const request = assistant.beginFileSelection();
        if (request.length === 0) return;
        nativeFiles.requestId = request;
        nativeFiles.open();
    }
    FileDialog {
        id: nativeFiles
        objectName: "assistant.files.dialog"
        property string requestId: ""
        title: qsTr("Add files to the assistant")
        fileMode: FileDialog.OpenFiles
        onAccepted: {
            const request = requestId;
            requestId = "";
            composer.assistant.addSelectedFiles(request, selectedFiles);
        }
        onRejected: {
            const request = requestId;
            requestId = "";
            composer.assistant.cancelFileSelection(request);
        }
    }
    Connections {
        target: composer.assistant
        function onFileSelectionRetired(requestId) {
            if (nativeFiles.requestId === requestId) {
                nativeFiles.requestId = "";
                nativeFiles.reject();
            }
        }
    }
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
    implicitHeight: composerContent.implicitHeight + AppSizes.unit * 1.5
    color: EaStyle.Colors.contentBackground
    border.color: EaStyle.Colors.appBorder
    radius: AppSizes.unit
    function rememberSelection() {
        if (editor.activeFocus) {
            savedSelectionStart = editor.selectionStart;
            savedSelectionEnd = editor.selectionEnd;
            selectionRevision = textRevision;
        }
    }
    function focusEditor() {
        const restore = selectionRevision === textRevision;
        const start = savedSelectionStart;
        const end = savedSelectionEnd;
        editor.forceActiveFocus();
        if (restore)
            editor.select(start, end);
    }
    function submitApprovedDraft(draft) {
        if (editor.text !== draft || !assistant.connected || assistant.contextConsentRequired)
            return;
        submit();
    }
    function submit() {
        if (!assistant.connected || (assistant.canCancel && !canSteer) || !hasDraft)
            return;
        if (assistant.contextConsentRequired) {
            contextApprovalRequested(editor.text);
            return;
        }
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
        x: AppSizes.unit * 0.75
        y: AppSizes.unit * 0.75
        width: parent.width - AppSizes.unit * 1.5
        spacing: AppSizes.unit * 0.25
        ScrollView {
            ScrollBar.vertical: EaElements.ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: false
            }
            id: selectedFilesScroll
            width: parent.width
            height: visible ? Math.min(selectedChips.implicitHeight, AppSizes.unit * 5) : 0
            visible: composer.assistant.selectedFiles.count > 0
            clip: true
            Flow {
                id: selectedChips
                width: selectedFilesScroll.availableWidth
                spacing: AppSizes.unit * 0.25
            Repeater {
                model: composer.assistant.selectedFiles
                delegate: RowLayout {
                    required property var model
                    objectName: "assistant.file." + model.id
                    spacing: AppSizes.unit * 0.25
                    EaElements.Label {
                        Layout.maximumWidth: composerContent.width * 0.6
                        text: qsTr("%1 (%2 bytes)%3").arg(model.name).arg(model.bytes)
                            .arg(model.textReadable ? "" : qsTr(" · text export required"))
                        textFormat: Text.PlainText
                        elide: Text.ElideMiddle
                        Accessible.name: qsTr("Selected file: %1, %2 bytes. %3").arg(model.name).arg(model.bytes)
                            .arg(model.textReadable ? qsTr("Available for consented text reads") : qsTr("Unsupported binary; text export required"))
                    }
                    EaElements.ToolButton {
                        fontIcon: "times"
                        enabled: !composer.assistant.canCancel
                        ToolTip.text: qsTr("Remove %1").arg(model.name)
                        Accessible.name: ToolTip.text
                        onClicked: composer.assistant.removeSelectedFile(model.id)
                    }
                }
            }
            }
        }
        ScrollView {
            ScrollBar.vertical: EaElements.ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: false
            }
            width: parent.width
            height: Math.min(AppSizes.unit * 10, Math.max(editor.font.pixelSize * 2.5 + editor.topPadding + editor.bottomPadding, editor.implicitHeight))
            TextArea {
                id: editor
                objectName: "assistant.composer"
                placeholderText: qsTr("Ask about your project or describe a refinement plan…")
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                persistentSelection: true
                selectionColor: EaStyle.Colors.themeAccent
                selectedTextColor: EaStyle.Colors.themeBackground
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.tab: addFilesButton
                KeyNavigation.backtab: composer.toggleControl
                onTextChanged: ++composer.textRevision
                onSelectionStartChanged: composer.rememberSelection()
                onSelectionEndChanged: composer.rememberSelection()
                color: EaStyle.Colors.themeForeground
                placeholderTextColor: EaStyle.Colors.themeForegroundMinor
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
                padding: AppSizes.unit * 0.4
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
            id: composerToolbar
            readonly property real choiceWidth: Math.max(0, width - addFilesButton.implicitWidth
                - (sendButton.visible ? sendButton.implicitWidth : 0) - (stopButton.visible ? stopButton.implicitWidth : 0)
                - previousUserButton.implicitWidth - nextUserButton.implicitWidth - spacing * 6)
            width: parent.width
            spacing: AppSizes.unit * 0.5
            FontMetrics { id: menuFontMetrics; font: models.font }
            TextMetrics {
                id: modelLabelMetrics
                font: models.font
                text: models.displayText
            }
            TextMetrics {
                id: effortLabelMetrics
                font: efforts.font
                text: efforts.displayText
            }
            EaElements.ToolButton {
                id: addFilesButton
                objectName: "assistant.files.add"
                fontIcon: "plus"
                enabled: !WebFiles.available && !composer.assistant.canCancel
                ToolTip.text: WebFiles.available ? qsTr("Browser file selection is not available yet") : qsTr("Add files")
                Accessible.name: qsTr("Add files")
                Accessible.description: ToolTip.text
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.backtab: editor
                KeyNavigation.tab: models
                onClicked: composer.chooseFiles()
            }
            EaElements.ComboBox {
                id: models
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.tab: efforts
                KeyNavigation.backtab: addFilesButton
                textFormat: Text.PlainText
                displayText: currentIndex < 0 ? qsTr("Model") : currentText
                currentIndex: {
                    const count = composer.assistant.models.count;
                    for (let i = 0; i < count; ++i)
                        if (composer.assistant.models.text(i, "id") === composer.assistant.selectedModel)
                            return i;
                    return -1;
                }
                readonly property real menuWidth: {
                    let measured = width;
                    for (let i = 0; i < composer.assistant.models.count; ++i)
                        measured = Math.max(measured, menuFontMetrics.advanceWidth(composer.assistant.models.text(i, "displayName")) + AppSizes.unit * 3);
                    return Math.min(measured, Math.max(width, Window.width - AppSizes.unit * 2));
                }
                popup.width: menuWidth
                popup.x: Math.min(0, Window.width - mapToItem(null, 0, 0).x - menuWidth - AppSizes.unit)
                delegate: EaElements.MenuItem {
                    required property var model
                    required property int index
                    width: models.popup.width
                    height: EaStyle.Sizes.comboBoxHeight
                    text: model.displayName
                    textFormat: Text.PlainText
                    enabled: model.available
                    highlighted: models.highlightedIndex === index
                }
                objectName: "assistant.model"
                Layout.preferredWidth: modelLabelMetrics.advanceWidth + AppSizes.unit * 2.5
                Layout.maximumWidth: composerToolbar.choiceWidth * 0.5
                background: Rectangle {
                    implicitHeight: EaStyle.Sizes.comboBoxHeight
                    color: "transparent"
                    radius: AppSizes.unit * 0.25
                    border.width: models.activeFocus ? EaStyle.Sizes.borderThickness : 0
                    border.color: EaStyle.Colors.appBarComboBoxBorder
                }
                model: composer.assistant.models
                textRole: "displayName"
                enabled: composer.assistant.connected && !composer.assistant.canCancel
                Accessible.name: qsTr("Assistant model")
                onActivated: index => composer.assistant.selectedModel = composer.assistant.models.text(index, "id")
            }
            EaElements.ComboBox {
                id: efforts
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.tab: previousUserButton
                KeyNavigation.backtab: models
                textFormat: Text.PlainText
                readonly property var effortValues: [""].concat(composer.assistant.availableEfforts)
                readonly property real menuWidth: {
                    let measured = width;
                    for (const value of effortValues)
                        measured = Math.max(measured, menuFontMetrics.advanceWidth(effortLabel(value)) + AppSizes.unit * 3);
                    return Math.min(measured, Math.max(width, Window.width - AppSizes.unit * 2));
                }
                popup.width: menuWidth
                popup.x: Math.min(0, Window.width - mapToItem(null, 0, 0).x - menuWidth - AppSizes.unit)
                function effortLabel(value) {
                    switch (value) {
                    case "": return qsTr("Auto");
                    case "none": return qsTr("None");
                    case "low": return qsTr("Low");
                    case "medium": return qsTr("Medium");
                    case "high": return qsTr("High");
                    case "xhigh": return qsTr("Extra high");
                    case "max": return qsTr("Maximum");
                    default: return qsTr("Unavailable");
                    }
                }
                displayText: !composer.assistant.connected || composer.assistant.models.count === 0
                    || models.currentIndex < 0 || currentIndex < 0 ? qsTr("Effort") : currentText
                currentIndex: effortValues.indexOf(composer.assistant.selectedEffort)
                objectName: "assistant.effort"
                Layout.preferredWidth: effortLabelMetrics.advanceWidth + AppSizes.unit * 2.5
                Layout.maximumWidth: composerToolbar.choiceWidth * 0.5
                background: Rectangle {
                    implicitHeight: EaStyle.Sizes.comboBoxHeight
                    color: "transparent"
                    radius: AppSizes.unit * 0.25
                    border.width: efforts.activeFocus ? EaStyle.Sizes.borderThickness : 0
                    border.color: EaStyle.Colors.appBarComboBoxBorder
                }
                model: effortValues.map(value => effortLabel(value))
                enabled: composer.assistant.connected && !composer.assistant.canCancel
                ToolTip.text: !composer.assistant.connected || composer.assistant.models.count === 0 ? qsTr("Reasoning effort is available after sign-in and model discovery") : composer.assistant.selectedEffort === "" ? qsTr("Provider default: the model or provider chooses the reasoning effort") : qsTr("Reasoning effort: %1").arg(currentText)
                EaElements.ToolTip {
                    text: efforts.ToolTip.text
                    visible: (efforts.hovered || efforts.activeFocus) && EaGlobals.Vars.showToolTips && text !== ""
                }
                Accessible.name: qsTr("Reasoning effort")
                onActivated: index => composer.assistant.selectedEffort = effortValues[index]
            }
            Item { Layout.fillWidth: true }
            EaElements.ToolButton {
                id: previousUserButton
                objectName: "assistant.previousUserMessage"
                fontIcon: "chevron-up"
                enabled: composer.hasPreviousUserMessage
                background: Rectangle {
                    implicitWidth: addFilesButton.implicitWidth
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: previousUserButton.backgroundColor()
                    border.width: previousUserButton.activeFocus ? 1 : 0
                    border.color: EaStyle.Colors.themeForegroundHighlight
                }
                ToolTip.text: qsTr("Previous user message")
                Accessible.name: ToolTip.text
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.backtab: efforts
                KeyNavigation.tab: nextUserButton
                onClicked: composer.previousUserRequested()
            }
            EaElements.ToolButton {
                id: nextUserButton
                objectName: "assistant.nextUserMessage"
                fontIcon: "chevron-down"
                enabled: composer.hasNextUserMessage
                background: Rectangle {
                    implicitWidth: addFilesButton.implicitWidth
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: nextUserButton.backgroundColor()
                    border.width: nextUserButton.activeFocus ? 1 : 0
                    border.color: EaStyle.Colors.themeForegroundHighlight
                }
                ToolTip.text: qsTr("Next user message")
                Accessible.name: ToolTip.text
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.backtab: previousUserButton
                KeyNavigation.tab: stopButton.visible ? stopButton : sendButton
                onClicked: composer.nextUserRequested()
            }
            EaElements.ToolButton {
                id: stopButton
                background: Rectangle {
                    implicitWidth: addFilesButton.implicitWidth
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: composer.canSteer && composer.hasDraft ? stopButton.backgroundColor() : (EaStyle.Colors.isDarkPalette ? "white" : "black")
                }
                contentItem: EaElements.Label {
                    opacity: stopButton.enabled ? 1 : 0.35
                    text: stopButton.fontIcon
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: stopButton.font.pixelSize * 1.25
                    color: composer.canSteer && composer.hasDraft ? stopButton.foregroundColor() : (EaStyle.Colors.isDarkPalette ? "black" : "white")
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.tab: sendButton.visible ? sendButton : composer.toggleControl
                KeyNavigation.backtab: nextUserButton
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
                id: sendButton
                background: Rectangle {
                    implicitWidth: addFilesButton.implicitWidth
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: sendButton.enabled ? (EaStyle.Colors.isDarkPalette ? "white" : "black") : sendButton.backgroundColor()
                }
                contentItem: EaElements.Label {
                    text: sendButton.fontIcon
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: sendButton.font.pixelSize * 1.25
                    color: sendButton.enabled ? (EaStyle.Colors.isDarkPalette ? "black" : "white") : sendButton.foregroundColor()
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                KeyNavigation.priority: KeyNavigation.BeforeItem
                KeyNavigation.tab: composer.toggleControl
                KeyNavigation.backtab: nextUserButton
                objectName: "assistant.send"
                fontIcon: "arrow-up"
                text: qsTr("Send")
                ToolTip.text: text
                highlighted: true
                visible: !composer.assistant.canCancel || (composer.canSteer && composer.hasDraft)
                enabled: composer.assistant.connected && (!composer.assistant.canCancel || composer.canSteer) && composer.hasDraft
                Accessible.name: text
                onClicked: composer.submit()
            }
        }
    }
}
