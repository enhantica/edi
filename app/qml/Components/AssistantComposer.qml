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
    property Item popupBoundary: composer.parent
    property Item previousFocusItem: toggleControl
    readonly property Item firstFocusItem: editor
    readonly property real actionSize: EaStyle.Sizes.toolButtonHeight * 0.75
    function closeChoices() { models.popup.close(); efforts.popup.close(); }
    function choiceX(control, menuWidth) {
        return Math.max(0, Math.min(popupBoundary.width - menuWidth, control.mapToItem(popupBoundary, 0, 0).x));
    }
    function choiceY(control, menuHeight) {
        return Math.max(0, Math.min(popupBoundary.height - menuHeight, control.mapToItem(popupBoundary, 0, 0).y - menuHeight));
    }
    onWidthChanged: closeChoices()
    Connections {
        target: Preferences
        function onSideBarOnLeftChanged() { composer.closeChoices(); }
    }
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
                x: editor.leftPadding
                width: Math.max(0, selectedFilesScroll.availableWidth - editor.leftPadding - editor.rightPadding)
                spacing: AppSizes.unit * 0.75
            Repeater {
                model: composer.assistant.selectedFiles
                delegate: RowLayout {
                    required property var model
                    objectName: "assistant.file." + model.id
                    spacing: AppSizes.unit * 0.125
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
                        id: removeFileButton
                        fontIcon: "times"
                        implicitWidth: composer.actionSize
                        implicitHeight: composer.actionSize
                        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.6
                        showBackground: false
                        contentItem: EaElements.Label {
                            text: removeFileButton.fontIcon
                            font.family: EaStyle.Fonts.iconsFamily
                            font.pixelSize: removeFileButton.font.pixelSize * 1.25
                            color: removeFileButton.foregroundColor()
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter
                        }
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
                KeyNavigation.backtab: composer.previousFocusItem
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
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                showBackground: false
                background: Rectangle {
                    implicitWidth: composer.actionSize
                    implicitHeight: implicitWidth
                    color: "transparent"
                    radius: width * 0.5
                    border.width: addFilesButton.activeFocus ? EaStyle.Sizes.borderThickness : 0
                    border.color: EaStyle.Colors.themeForeground
                }
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
                    return Math.min(measured, Math.max(0, composer.popupBoundary.width - AppSizes.unit * 2));
                }
                popup.parent: composer.popupBoundary
                popup.margins: 0
                popup.width: menuWidth
                popup.height: Math.min(models.popup.contentItem.implicitHeight + models.popup.topPadding + models.popup.bottomPadding,
                    Math.max(0, composer.popupBoundary.height - AppSizes.unit * 2))
                popup.x: composer.choiceX(models, models.popup.width)
                popup.y: composer.choiceY(models, models.popup.height)
                delegate: EaElements.MenuItem {
                    required property var model
                    id: modelOption
                    required property int index
                    width: models.popup.width
                    height: Math.max(EaStyle.Sizes.comboBoxHeight, implicitContentHeight + topPadding + bottomPadding)
                    text: model.displayName
                    contentItem: EaElements.Label {
                        text: modelOption.text
                        textFormat: Text.PlainText
                        wrapMode: Text.WrapAnywhere
                        font: modelOption.font
                        color: models.foregroundColor
                    }
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
                    border.color: EaStyle.Colors.themeForeground
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
                    return Math.min(measured, Math.max(0, composer.popupBoundary.width - AppSizes.unit * 2));
                }
                popup.parent: composer.popupBoundary
                popup.margins: 0
                popup.width: menuWidth
                popup.height: Math.min(efforts.popup.contentItem.implicitHeight + efforts.popup.topPadding + efforts.popup.bottomPadding,
                    Math.max(0, composer.popupBoundary.height - AppSizes.unit * 2))
                popup.x: composer.choiceX(efforts, efforts.popup.width)
                popup.y: composer.choiceY(efforts, efforts.popup.height)
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
                    border.color: EaStyle.Colors.themeForeground
                }
                delegate: EaElements.MenuItem {
                    id: effortOption
                    required property var modelData
                    required property int index
                    width: efforts.popup.width
                    height: Math.max(EaStyle.Sizes.comboBoxHeight, implicitContentHeight + topPadding + bottomPadding)
                    text: modelData
                    textFormat: Text.PlainText
                    highlighted: efforts.highlightedIndex === index
                    contentItem: EaElements.Label {
                        text: effortOption.text
                        textFormat: Text.PlainText
                        wrapMode: Text.WrapAnywhere
                        font: effortOption.font
                        color: efforts.foregroundColor
                    }
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
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                objectName: "assistant.previousUserMessage"
                fontIcon: "chevron-up"
                enabled: composer.hasPreviousUserMessage
                background: Rectangle {
                    implicitWidth: composer.actionSize
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: "transparent"
                    border.width: previousUserButton.activeFocus ? 1 : 0
                    border.color: EaStyle.Colors.themeForeground
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
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                objectName: "assistant.nextUserMessage"
                fontIcon: "chevron-down"
                enabled: composer.hasNextUserMessage
                background: Rectangle {
                    implicitWidth: composer.actionSize
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: "transparent"
                    border.width: nextUserButton.activeFocus ? 1 : 0
                    border.color: EaStyle.Colors.themeForeground
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
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                background: Rectangle {
                    implicitWidth: composer.actionSize
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
                implicitWidth: composer.actionSize
                implicitHeight: composer.actionSize
                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                background: Rectangle {
                    implicitWidth: composer.actionSize
                    implicitHeight: implicitWidth
                    radius: width * 0.5
                    color: sendButton.enabled ? (EaStyle.Colors.isDarkPalette ? "white" : "black") : EaStyle.Colors.themeBackgroundDisabled
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
