// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.impl as ControlsImpl
import QtQuick.Layouts
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Popup {
    id: panel
    objectName: "assistant.popup"
    signal chooseWorkingFolderRequested()
    required property AssistantViewModel assistant
    // One bounded JSON-domain presentation copy handles Qt QVariant lists.
    readonly property var usageData: {
        try { return JSON.parse(JSON.stringify(assistant.usage)); }
        catch (error) { return { available: false, stale: false, buckets: [] }; }
    }
    readonly property var usageWindow: {
        let selected = null;
        const buckets = usageData.buckets || [];
        for (const bucket of buckets) for (const window of bucket.windows || [])
            if (!selected || window.usedPercent > selected.usedPercent)
                selected = { usedPercent: window.usedPercent, label: usageWindowLabel(bucket, window) };
        return selected;
    }
    readonly property real remainingPercent: usageWindow ? Math.max(0, Math.min(100, 100 - usageWindow.usedPercent)) : -1
    function allowanceColor(remaining) {
        return remaining >= 0 && remaining < 5 ? EaStyle.Colors.red
             : remaining >= 0 && remaining < 25 ? EaStyle.Colors.orange : EaStyle.Colors.themeForeground;
    }
    readonly property var accountData: panel.assistant.account
    readonly property string accountPlan: {
        if (accountData.planType) return accountData.planType;
        const known=[];
        for (const bucket of usageData.buckets || []) if (bucket.planType && known.indexOf(bucket.planType)<0) known.push(bucket.planType);
        return known.join(", ");
    }
    readonly property string accountInitial: accountData.email ? Array.from(accountData.email)[0].toUpperCase() : ""
    function usageResetLabel(value) {
        if (typeof value !== "number") return "";
        const reset = new Date(value*1000);
        return isNaN(reset.getTime()) ? qsTr("Reset timestamp: %1").arg(value) : qsTr("Resets: %1").arg(reset.toISOString());
    }
    function usageWindowLabel(bucket, window) {
        const name = bucket.limitName || bucket.limitId || bucket.id || qsTr("Allowance");
        const kind = window.kind === "primary" ? qsTr("Primary window") : qsTr("Secondary window");
        const duration = typeof window.windowDurationMins === "number" ? qsTr(" · %1 minutes").arg(window.windowDurationMins) : "";
        return name + " · " + kind + duration;
    }
    function usageCaption() {
        const prefix = usageData.stale ? qsTr("Last observed: ") : "";
        if (usageWindow) return prefix + qsTr("%1 · %2% remaining").arg(usageWindow.label).arg(Math.max(0, 100 - usageWindow.usedPercent));
        return usageData.available ? prefix + qsTr("Usage details available") : qsTr("Usage data unavailable");
    }
    function usageBucketText(bucket) {
        let lines = [];
        for (const window of bucket.windows || []) {
            let line = usageWindowLabel(bucket, window) + "\n" + qsTr("%1% used · %2% remaining").arg(window.usedPercent).arg(Math.max(0, 100 - window.usedPercent));
            if (typeof window.resetsAt === "number") {
                const reset = new Date(window.resetsAt * 1000);
                line += "\n" + (isNaN(reset.getTime()) ? qsTr("Reset timestamp: %1").arg(window.resetsAt) : qsTr("Resets: %1").arg(reset.toISOString()));
            }
            lines.push(line);
        }
        if (bucket.credits) {
            const name = bucket.limitName || bucket.limitId || bucket.id || qsTr("Allowance");
            let credits = name + " · " + (bucket.credits.unlimited ? qsTr("Credits: unlimited") : bucket.credits.hasCredits ? qsTr("Credits available") : qsTr("No credits available"));
            if (typeof bucket.credits.balance === "string") credits += "\n" + qsTr("Balance: %1").arg(bucket.credits.balance);
            lines.push(credits);
        }
        return lines.join("\n\n");
    }
    function workingFolderCaption(path) {
        if (path.length === 0) return qsTr("Temporary workspace");
        const normalized = path.replace(/\\/g, "/");
        const trimmed = normalized.replace(/\/+$/, "");
        if (trimmed.length === 0) return path; // A filesystem root remains visible.
        return trimmed.substring(trimmed.lastIndexOf("/") + 1);
    }
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
    // A user navigation link always refers to the current project's normal
    // Report page. Other links retain their completed-row/file ownership checks.
    function openReportLink(sourceRowId, link) {
        if (link === "edi:report") {
            if (Session.project !== null && AppState.reportPageEnabled) {
                AppState.open(AppState.Page.Report);
                return true;
            }
            reportPageUnavailable.open();
            return false;
        }
        return panel.assistant.openReport(sourceRowId, link);
    }
    required property Item toggleControl
    readonly property Item firstFocusItem: connectionButton
    property bool shown: Preferences.assistantShown
    onShownChanged: {
        if (!shown) { panel.retireConsentSend(); connectionDialog.close(); composer.closeChoices(); }
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
        if (panel.assistant.connected) composer.focusEditor();
        else connectionButton.forceActiveFocus();
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
                z: 3
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
                    width: Math.max(0,parent.width-headerActions.implicitWidth-AppSizes.unit*2)
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                    text: qsTr("Assistant")
                    font.bold: true
                    color: EaStyle.Colors.themeForegroundHovered
                }
                RowLayout {
                    id: headerActions
                    anchors.right: parent.right
                    anchors.rightMargin: EaStyle.Sizes.fontPixelSize * 0.5
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: AppSizes.unit
                    EaElements.ToolButton {
                        id: clearButton
                        visible: panel.assistant.connected
                        objectName: "assistant.clear"
                        fontIcon: "eraser"
                        showBackground: false
                        ToolTip.text: qsTr("Clear conversation")
                        Accessible.name: ToolTip.text
                        KeyNavigation.priority: KeyNavigation.BeforeItem
                        KeyNavigation.backtab: panel.toggleControl
                        KeyNavigation.tab: usageButton
                        onClicked: panel.assistant.clearHistory()
                    }
                    EaElements.Button {
                        id: usageButton
                        visible: panel.assistant.connected
                        objectName: "assistant.usage"
                        text: panel.remainingPercent < 0 ? "–" : qsTr("%1%").arg(panel.remainingPercent)+(panel.usageData.stale ? " · "+qsTr("stale") : "")
                        font.bold: false
                        contentItem: EaElements.Label {
                            text: usageButton.text
                            font: usageButton.font
                            color: panel.allowanceColor(panel.remainingPercent)
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        ToolTip.text: panel.usageCaption()
                        Accessible.name: ToolTip.text
                        KeyNavigation.priority: KeyNavigation.BeforeItem
                        KeyNavigation.backtab: clearButton
                        KeyNavigation.tab: connectionButton
                        onClicked: usageDialog.open()
                    }
                    EaElements.Button {
                        id: connectionButton
                        objectName: "assistant.connection"
                        text: panel.assistant.connected ? panel.accountInitial : qsTr("Sign in")
                        enabled: panel.assistant.connected || panel.assistant.state !== "connecting"
                        contentItem: EaElements.Label {
                            text: panel.assistant.connected ? (panel.accountInitial.length ? panel.accountInitial : "user") : qsTr("Sign in")
                            font.family: panel.assistant.connected && !panel.accountInitial.length ? EaStyle.Fonts.iconsFamily : EaStyle.Fonts.fontFamily
                            font.pixelSize: EaStyle.Sizes.fontPixelSize
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            color: connectionButton.foregroundColor()
                        }
                        Layout.maximumWidth: header.width * 0.4
                        ToolTip.text: panel.assistant.connected ? qsTr("Account") : text
                        Accessible.name: ToolTip.text
                        KeyNavigation.priority: KeyNavigation.BeforeItem
                        KeyNavigation.backtab: panel.assistant.connected ? usageButton : panel.toggleControl
                        KeyNavigation.tab: panel.assistant.connected ? composer.firstFocusItem : panel.toggleControl
                        onClicked: {
                            if (panel.assistant.connected) accountDialog.open();
                            else {
                                panel.retireConsentSend();
                                connectionDialog.open();
                            }
                        }
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
                visible: panel.assistant.connected
                enabled: visible
                z: 1
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                anchors.bottom: parent.bottom
                anchors.margins: AppSizes.unit
                spacing: AppSizes.unit * 0.855
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: AppSizes.unit * 0.25
                    Flow {
                        Layout.fillWidth: true
                        spacing: AppSizes.unit * 0.25
                        EaElements.Button {
                            id: chooseWorkingFolderButton
                            objectName: "assistant.chooseWorkingFolder"
                            KeyNavigation.priority: KeyNavigation.BeforeItem
                            KeyNavigation.backtab: usageButton
                            KeyNavigation.tab: temporaryWorkingFolderButton.visible && temporaryWorkingFolderButton.enabled
                                ? temporaryWorkingFolderButton : composer.actionsControl.enabled ? composer.actionsControl : composer.firstFocusItem
                            text: qsTr("Choose working folder")
                            enabled: !panel.assistant.canCancel
                            Accessible.name: text
                            onClicked: panel.chooseWorkingFolderRequested()
                        }
                        EaElements.Button {
                            id: temporaryWorkingFolderButton
                            objectName: "assistant.temporaryWorkingFolder"
                            KeyNavigation.priority: KeyNavigation.BeforeItem
                            KeyNavigation.backtab: chooseWorkingFolderButton.visible && chooseWorkingFolderButton.enabled
                                ? chooseWorkingFolderButton : usageButton
                            KeyNavigation.tab: composer.actionsControl.enabled ? composer.actionsControl : composer.firstFocusItem
                            text: qsTr("Use temporary folder")
                            visible: panel.assistant.workingFolder.length > 0
                            enabled: !panel.assistant.canCancel
                            Accessible.name: text
                            onClicked: panel.assistant.useTemporaryWorkingFolder()
                        }
                    }
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
                        assistant: panel.assistant
                        required property var model
                        width: conversation.width
                        kind: model.kind
                        text: model.text
                        payload: model.payload
                        status: model.status
                        rowId: model.id
                        onReportRequested: (sourceRowId, link) => panel.openReportLink(sourceRowId, link)
                        onDetailsChanging: {
                            conversation.cancelFlick();
                            conversation.followsTail = false;
                            conversation.jumpedUserId = "";
                        }
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
                AssistantWorking {
                    objectName: "assistant.working"
                    Layout.fillWidth: true
                    Layout.minimumHeight: iconExtent
                    assistant: panel.assistant
                    presented: panel.shown && panel.visible
                }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.leftMargin: -AppSizes.unit
                    Layout.rightMargin: -AppSizes.unit
                    implicitHeight: EaStyle.Sizes.borderThickness
                    color: EaStyle.Colors.appBorder
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: AppSizes.unit * 0.5

                    EaElements.Label {
                        objectName: "assistant.workingFolder.caption"
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        Layout.preferredWidth: 0
                        text: panel.workingFolderCaption(panel.assistant.workingFolder)
                        textFormat: Text.PlainText
                        elide: Text.ElideMiddle
                        horizontalAlignment: Text.AlignRight
                        color: EaStyle.Colors.themeForegroundMinor
                        ToolTip.text: panel.assistant.workingFolder.length ? panel.assistant.workingFolder : qsTr("App-owned temporary workspace")
                        ToolTip.visible: folderHover.hovered
                        Accessible.name: qsTr("Working folder: %1").arg(ToolTip.text)
                        HoverHandler { id: folderHover }
                    }
                }
                AssistantComposer {
                    id: composer
                    Layout.fillWidth: true
                    assistant: panel.assistant
                    toggleControl: panel.toggleControl
                    popupBoundary: panel.contentItem
                    previousFocusItem: composer.actionsControl.enabled ? composer.actionsControl : temporaryWorkingFolderButton.visible && temporaryWorkingFolderButton.enabled ? temporaryWorkingFolderButton
                        : chooseWorkingFolderButton.visible && chooseWorkingFolderButton.enabled ? chooseWorkingFolderButton : usageButton
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
            Rectangle {
                objectName: "assistant.signedOut"
                visible: !panel.assistant.connected
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                anchors.bottom: parent.bottom
                color: EaStyle.Colors.contentBackground
                EmptyStateLabel {
                    objectName: "assistant.signInPrompt"
                    anchors.centerIn: parent
                    width: Math.max(0,parent.width-AppSizes.unit*2)
                    text: qsTr("Sign in to use the assistant")
                }
                EaElements.Button {
                    objectName: "assistant.authCancel"
                    visible: panel.assistant.canCancel
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: AppSizes.unit
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: panel.assistant.state === "connecting" ? qsTr("Cancel sign in") : qsTr("Stop")
                    onClicked: panel.assistant.cancel()
                }
            }
            // One real file boundary covers transcript and composer, not ordinary text or the header.
            DropArea {
                id: chatFilesDrop
                anchors.fill: chatBody
                z: 2
                enabled: panel.visible && panel.shown && panel.assistant.connected && ApplicationInfo.assistantAvailable && !WebFiles.available
                onEntered: drag => drag.accepted = drag.hasUrls && !panel.assistant.canCancel
                onDropped: drop => {
                    if (!chatFilesDrop.enabled || !drop.hasUrls || panel.assistant.canCancel) { drop.accepted = false; return; }
                    const original=panel.assistant;
                    const files=drop.urls;
                    const request=original.beginFileSelection(true);
                    if (!Qt.isQtObject(panel) || !Qt.isQtObject(original) || original!==panel.assistant || !original.connected) {
                        if (Qt.isQtObject(original)) original.cancelFileSelection(request);
                        drop.accepted=false;return;
                    }
                    drop.accepted=request.length>0 && original.addSelectedFiles(request,files);
                }
            }
        }
        AppDialog {
            id: usageDialog
            objectName: "assistant.usageDialog"
            title: qsTr("Usage")
            standardButtons: Dialog.Close
            readonly property real viewportHeight: Math.max(0, parent.height - AppSizes.unit * 2)
            width: Math.min(AppSizes.unit * 30, Math.max(0, parent.width - AppSizes.unit * 2))
            height: Math.min(implicitHeight, viewportHeight)
            contentWidth: Math.max(0, width - leftPadding - rightPadding)
            contentHeight: Math.min(usageContent.implicitHeight, Math.max(0, viewportHeight - topPadding - bottomPadding
                - (implicitHeaderHeight > 0 ? implicitHeaderHeight + spacing : 0)
                - (implicitFooterHeight > 0 ? implicitFooterHeight + spacing : 0)))
            onOpened: panel.assistant.refreshUsage()
            ScrollView {
                id: usageScroll
                width: usageDialog.contentWidth
                height: usageDialog.contentHeight
                clip: true
                ScrollBar.vertical: EaElements.ScrollBar { id: usageBar; policy: ScrollBar.AsNeeded; interactive: false }
                Column {
                    id: usageContent
                    width: Math.max(0, usageDialog.contentWidth - usageBar.implicitWidth)
                    spacing: AppSizes.unit
                    EaElements.Label {
                        width: parent.width
                        text: panel.usageCaption()
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                    }
                    EaElements.Label {
                        width: parent.width
                        text: qsTr("Context window occupancy: unavailable")
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                    }
                    Repeater {
                        model: panel.usageData.buckets || []
                        Column {
                            id: bucketView
                            required property var modelData
                            width: usageContent.width
                            spacing: AppSizes.unit * 0.5
                            Repeater {
                                model: bucketView.modelData.windows || []
                                Column {
                                    id: windowView
                                    required property var modelData
                                    width: bucketView.width
                                    spacing: AppSizes.unit * 0.25
                                    EaElements.Label {
                                        width: parent.width
                                        text: panel.usageWindowLabel(bucketView.modelData, windowView.modelData)
                                        textFormat: Text.PlainText
                                        wrapMode: Text.WrapAnywhere
                                    }
                                    ProgressBar {
                                        objectName: "assistant.usage.windowBar"
                                        width: parent.width
                                        from: 0; to: 100
                                        value: Math.max(0, Math.min(100, windowView.modelData.usedPercent))
                                        contentItem: Rectangle {
                                            implicitHeight: AppSizes.unit * 0.35
                                            color: EaStyle.Colors.themeBackgroundDisabled
                                            Rectangle {
                                                width: parent.width * Math.max(0, Math.min(1, windowView.modelData.usedPercent / 100))
                                                height: parent.height
                                                color: panel.allowanceColor(Math.max(0, 100-windowView.modelData.usedPercent))
                                            }
                                        }
                                        Accessible.name: panel.usageWindowLabel(bucketView.modelData, windowView.modelData)
                                    }
                                    EaElements.Label {
                                        width: parent.width
                                        text: qsTr("%1% used · %2% remaining").arg(windowView.modelData.usedPercent).arg(Math.max(0, 100-windowView.modelData.usedPercent))
                                            + (typeof windowView.modelData.resetsAt === "number" ? "\n" + panel.usageResetLabel(windowView.modelData.resetsAt) : "")
                                        textFormat: Text.PlainText
                                        wrapMode: Text.WrapAnywhere
                                    }
                                }
                            }
                            EaElements.Label {
                                width: parent.width
                                visible: !!bucketView.modelData.credits
                                text: bucketView.modelData.credits ? (bucketView.modelData.credits.unlimited ? qsTr("Credits: unlimited") : bucketView.modelData.credits.hasCredits ? qsTr("Credits available") : qsTr("No credits available"))+(typeof bucketView.modelData.credits.balance === "string" ? "\n"+qsTr("Balance: %1").arg(bucketView.modelData.credits.balance) : "") : ""
                                textFormat: Text.PlainText
                                wrapMode: Text.WrapAnywhere
                            }
                        }
                    }
                    EaElements.Label {
                        width: parent.width
                        text: panel.usageData.observedAt ? qsTr("Read at %1. Different allowance windows are listed separately; the percentage shows the most constrained supplied window.").arg(panel.usageData.observedAt)
                            : qsTr("No account usage snapshot is available. No quota or context percentage is inferred from conversation length or time.")
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
        AppDialog {
            id: reportPageUnavailable
            objectName: "assistant.reportPageUnavailable"
            title: qsTr("Report page unavailable")
            width: Math.min(AppSizes.unit * 28, Math.max(0, parent.width - AppSizes.unit * 2))
            standardButtons: Dialog.Close
            contentWidth: Math.max(0, width - leftPadding - rightPadding)
            contentHeight: reportPageUnavailableText.implicitHeight
            EaElements.Label {
                id: reportPageUnavailableText
                width: reportPageUnavailable.contentWidth
                text: qsTr("The current project's Report page is unavailable. Open a project with a structure and an experiment to use its report preview and export controls.")
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
            }
        }
        AppDialog {
            id: accountDialog
            objectName: "assistant.accountDialog"
            title: qsTr("Account")
            standardButtons: Dialog.Close
            readonly property real viewportHeight: Math.max(0, parent.height - AppSizes.unit * 2)
            width: Math.min(AppSizes.unit * 24, Math.max(0, parent.width - AppSizes.unit * 2))
            height: Math.min(implicitHeight, viewportHeight)
            contentWidth: Math.max(0, width - leftPadding - rightPadding)
            contentHeight: Math.min(accountContent.implicitHeight, Math.max(0, viewportHeight-topPadding-bottomPadding
                -(implicitHeaderHeight > 0 ? implicitHeaderHeight+spacing : 0)-(implicitFooterHeight > 0 ? implicitFooterHeight+spacing : 0)))
            Connections {
                target: panel.assistant
                function onConnectedChanged() { if (!panel.assistant.connected) accountDialog.close(); }
            }
            ScrollView {
                width: accountDialog.contentWidth
                height: accountDialog.contentHeight
                clip: true
                Column {
                    id: accountContent
                    width: Math.max(0, accountDialog.contentWidth-AppSizes.unit)
                    spacing: AppSizes.unit
                    EaElements.Label {
                        objectName: "assistant.accountIdentity"
                        width: parent.width
                        text: panel.accountData.email || qsTr("Account email unavailable")
                        textFormat: Text.PlainText
                        wrapMode: Text.WrapAnywhere
                    }
                    EaElements.Label {
                        width: parent.width
                        visible: panel.accountPlan.length>0
                        text: panel.accountPlan
                        textFormat: Text.PlainText
                        wrapMode: Text.WrapAnywhere
                    }
                    EaElements.Button {
                        id: signOutButton
                        objectName: "assistant.signOut"
                        text: qsTr("Sign out")
                        width: Math.min(implicitWidth,parent.width)
                        enabled: panel.assistant.connected
                        onClicked: panel.assistant.signOut()
                    }
                }
            }
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
