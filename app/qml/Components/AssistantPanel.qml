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
    function usageWindowLabel(bucket, window) {
        const label = window.windowDurationMins === 300 ? qsTr("Session limit")
                    : window.windowDurationMins === 10080 ? qsTr("Weekly") : qsTr("Other allowance");
        const name = bucket.limitName || bucket.limitId || bucket.id || "";
        return name.length ? name + " · " + label : label;
    }
    function usageCaption() {
        if (usageWindow) return qsTr("%1 · %2% used").arg(usageWindow.label).arg(usageWindow.usedPercent);
        return qsTr("Usage unavailable");
    }
    function allowanceWindow(minutes) {
        let selected = null;
        for (const bucket of usageData.buckets || []) for (const window of bucket.windows || [])
            if (window.windowDurationMins === minutes && (!selected || window.usedPercent > selected.usedPercent)) selected = window;
        return selected;
    }
    function usageResetLabel(value, now) {
        if (typeof value !== "number" || !isFinite(new Date(value * 1000).getTime())) return qsTr("Reset unavailable");
        const minutes = Math.ceil((value * 1000 - now) / 60000);
        if (minutes <= 0) return qsTr("Reset time reached");
        const days = Math.floor(minutes / 1440);
        const hours = Math.floor((minutes % 1440) / 60);
        if (days > 0) return qsTr("Resets in %1d %2h").arg(days).arg(hours);
        if (hours > 0) return qsTr("Resets in %1h %2 min").arg(hours).arg(minutes % 60);
        return qsTr("Resets in %1 min").arg(minutes);
    }
    readonly property string accountPlanLabel: accountPlan.split(/[_ -]+/).map(word => word.length ? word[0].toUpperCase() + word.slice(1) : "").join(" ")
    readonly property color actionBackground: EaStyle.Colors.sideBarButtonBackgroundHovered
    readonly property real headerActionExtent: EaStyle.Sizes.toolButtonHeight * 0.75
    property var noticeState: null
    property var noticeProjection: ({})
    function captureNotice() {
        const component = panel, original = panel.assistant;
        if (!Qt.isQtObject(component) || !Qt.isQtObject(original)) return;
        const previous = component.noticeState;
        const message = original.lastError;
        if (!Qt.isQtObject(component) || !Qt.isQtObject(original) || component.assistant !== original) return;
        if (!message.length) {
            if (component.noticeState === previous) component.noticeState = null;
            return;
        }
        if (previous && previous.owner === original && previous.text === message) return;
        const rows = original.messages, count = rows.count;
        const anchor = count > 0 ? rows.text(count - 1, "id") : "";
        if (!Qt.isQtObject(component) || !Qt.isQtObject(original) || component.assistant !== original
            || component.noticeState !== previous || original.lastError !== message) return;
        component.noticeState = { owner: original, text: message, anchor: anchor };
    }
    readonly property bool noticeAnchorPresent: {
        const revision = noticeProjection;
        const notice = noticeState;
        if (revision === null) return false;
        if (!notice || notice.owner !== assistant || !notice.anchor.length) return false;
        for (let i = 0; i < assistant.messages.count; ++i)
            if (assistant.messages.text(i, "id") === notice.anchor) return true;
        return false;
    }
    onAssistantChanged: { noticeState = null; captureNotice(); }
    Component.onCompleted: captureNotice()
    component EdiNotice: Item {
        id: notice
        required property string noticeText
        objectName: noticeText.length > 0 ? "assistant.currentNotice" : ""
        visible: noticeText.length > 0
        implicitHeight: visible ? noticeContent.implicitHeight + AppSizes.unit * 0.5 : 0
        height: implicitHeight
        Column {
            id: noticeContent
            y: AppSizes.unit * 0.5
            width: parent.width
            spacing: AppSizes.unit * 0.25
            TextEdit {
                width: parent.width
                text: notice.noticeText
                textFormat: TextEdit.PlainText
                readOnly: true
                selectByMouse: true
                persistentSelection: true
                wrapMode: TextEdit.Wrap
                color: EaStyle.Colors.themeForeground
                selectionColor: EaStyle.Colors.themeAccent
                selectedTextColor: EaStyle.Colors.themeBackground
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
                Accessible.role: Accessible.StaticText
                Accessible.name: qsTr("Edi notice: %1").arg(text)
            }
        }
    }
    property var consentSend: null
    function retireConsentSend() { consentSend = null; }
    function ownsConsentSend(intent) {
        const component = panel, original = panel.assistant, draftComponent = composer, dialog = connectionDialog;
        if (!Qt.isQtObject(dialog) || intent === null || consentSend !== intent || intent.owner !== original
            || intent.offer !== dialog.approvalOwner) return false;
        const draftOwned = draftComponent.ownsConsentDraft(intent.draft);
        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant || !draftOwned
            || !Qt.isQtObject(dialog) || intent.offer !== dialog.approvalOwner) return false;
        const context = original.contextPreview;
        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant
            || !Qt.isQtObject(dialog) || component.consentSend !== intent || intent.owner !== original
            || intent.offer !== dialog.approvalOwner) return false;
        if (intent.project !== Session.project || !original.connected || context !== intent.context
            || original.selectedModel !== intent.model || original.selectedEffort !== intent.effort) return false;
        const stillDraftOwned = draftComponent.ownsConsentDraft(intent.draft);
        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant) return false;
        return stillDraftOwned && component.consentSend === intent && Qt.isQtObject(dialog) && intent.offer === dialog.approvalOwner;
    }
    function resumeConsentSend() {
        const component = panel, original = panel.assistant, draftComponent = composer;
        const intent = component.consentSend;
        if (!intent) return;
        const owned = component.ownsConsentSend(intent);
        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant) return;
        if (!owned) { if (component.consentSend === intent) component.retireConsentSend(); return; }
        if (!intent.approved) return;
        const required = original.contextConsentRequired;
        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant) return;
        const stillOwned = component.ownsConsentSend(intent);
        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant || !stillOwned) return;
        if (required || original.state !== "idle" || original.canCancel) return;
        // Consume before submission: queued readiness notifications cannot send twice.
        component.consentSend = null;
        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant
            || component.consentSend !== null) return;
        draftComponent.submitApprovedDraft(intent.draft);
    }
    function scheduleConsentSend() { Qt.callLater(resumeConsentSend); }
    Connections {
        target: panel.assistant
        function onConversationRetired() { panel.retireConsentSend(); panel.noticeState = null; panel.captureNotice(); }
        function onConnectedChanged() { panel.retireConsentSend(); }
        function onAccountChanged() { panel.retireConsentSend(); panel.noticeState = null; panel.captureNotice(); }
        function onSelectedModelChanged() { panel.retireConsentSend(); }
        function onSelectedEffortChanged() { panel.retireConsentSend(); }
        function onStateChanged() { panel.scheduleConsentSend(); }
        function onCanCancelChanged() { panel.scheduleConsentSend(); }
        function onLastErrorChanged() { panel.captureNotice(); }
        function onContextPreviewChanged() {
            const component = panel, original = panel.assistant;
            const intent = component.consentSend;
            const owned = intent ? component.ownsConsentSend(intent) : true;
            if (!Qt.isQtObject(component) || !Qt.isQtObject(original) || original !== component.assistant) return;
            if (!owned) { if (component.consentSend === intent) component.retireConsentSend(); }
            else if (component.consentSend === intent) component.scheduleConsentSend();
        }
    }
    Connections {
        target: Session
        function onProjectChanged() { panel.retireConsentSend(); }
    }
    Connections {
        target: composer
        function onTextRevisionChanged() { panel.retireConsentSend(); }
        function onDraftOwnerRevisionChanged() { panel.retireConsentSend(); }
    }
    Connections {
        target: panel.assistant.selectedFiles
        function onCountChanged() { panel.retireConsentSend(); }
        function onDataChanged() { panel.retireConsentSend(); }
    }
    Component.onDestruction: retireConsentSend()
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
                Rectangle {
                    anchors.fill: parent
                    color: EaStyle.Colors.contentBackground
                }
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
                    spacing: AppSizes.unit * 0.5
                    EaElements.Button {
                        id: clearButton
                        visible: panel.assistant.connected
                        objectName: "assistant.clear"
                        text: qsTr("Clear")
                        leftPadding: AppSizes.unit * 0.75
                        rightPadding: leftPadding
                        implicitHeight: usageButton.implicitHeight
                        contentItem: RowLayout {
                            spacing: AppSizes.unit * 0.4
                            EaElements.Label {
                                text: "eraser"
                                font.family: EaStyle.Fonts.iconsFamily
                                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                                color: EaStyle.Colors.themeForegroundMinor
                                Accessible.ignored: true
                            }
                            EaElements.Label { text: clearButton.text; color: EaStyle.Colors.themeForegroundMinor }
                        }
                        background: Rectangle {
                            border.width: 0
                            implicitHeight: EaStyle.Sizes.toolButtonHeight * 0.75
                            radius: height * 0.5
                            color: clearButton.visualFocus ? EaStyle.Colors.themeRowHovered : panel.actionBackground
                        }
                        ToolTip.text: qsTr("Start a new conversation for this project. Your ChatGPT account stays connected.")
                        Accessible.name: qsTr("Clear conversation")
                        KeyNavigation.priority: KeyNavigation.BeforeItem
                        KeyNavigation.backtab: panel.toggleControl
                        KeyNavigation.tab: usageButton
                        onClicked: panel.assistant.clearHistory()
                    }
                    EaElements.Button {
                        id: usageButton
                        visible: panel.assistant.connected
                        objectName: "assistant.usage"
                        text: !panel.usageWindow ? "–" : qsTr("%1% used").arg(panel.usageWindow.usedPercent)
                        font.bold: false
                        leftPadding: AppSizes.unit * 0.75
                        rightPadding: AppSizes.unit * 0.75
                        background: Rectangle {
                            border.width: 0
                            implicitHeight: EaStyle.Sizes.toolButtonHeight * 0.75
                            radius: height * 0.5
                            color: usageButton.visualFocus ? EaStyle.Colors.themeRowHovered : panel.actionBackground
                        }
                        contentItem: EaElements.Label {
                            text: usageButton.text
                            font: usageButton.font
                            color: !usageButton.enabled ? EaStyle.Colors.themeForegroundDisabled
                                : usageButton.hovered || usageButton.down || usageButton.visualFocus
                                    ? EaStyle.Colors.themeAccent : panel.allowanceColor(panel.remainingPercent)
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
                        readonly property bool pendingConnection: panel.assistant.state === "connecting"
                        readonly property bool accountView: !pendingConnection && panel.assistant.connected
                        text: pendingConnection ? qsTr("Cancel connection")
                            : accountView ? panel.accountInitial : qsTr("Connect ChatGPT")
                        enabled: !pendingConnection || panel.assistant.canCancel
                        leftPadding: connectionButton.accountView ? 0 : AppSizes.unit * 0.75
                        rightPadding: leftPadding
                        contentItem: RowLayout {
                            spacing: AppSizes.unit * 0.4
                            EaElements.Label {
                                visible: !connectionButton.accountView
                                text: connectionButton.pendingConnection ? "times" : "comment-dots"
                                font.family: EaStyle.Fonts.iconsFamily
                                color: EaStyle.Colors.isDarkPalette ? "black" : "white"
                                Accessible.ignored: true
                            }
                            EaElements.Label {
                                text: connectionButton.accountView ? (panel.accountInitial.length ? panel.accountInitial : "user") : connectionButton.text
                                font.family: connectionButton.accountView && !panel.accountInitial.length ? EaStyle.Fonts.iconsFamily : EaStyle.Fonts.fontFamily
                                font.pixelSize: EaStyle.Sizes.fontPixelSize
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                color: !connectionButton.enabled ? EaStyle.Colors.themeForegroundDisabled : EaStyle.Colors.isDarkPalette ? "black" : "white"
                            }
                        }
                        Layout.preferredWidth: connectionButton.accountView ? panel.headerActionExtent : implicitWidth
                        Layout.minimumWidth: connectionButton.accountView ? panel.headerActionExtent : 0
                        Layout.maximumWidth: connectionButton.accountView ? panel.headerActionExtent : Math.max(0, header.width - AppSizes.unit)
                        Layout.preferredHeight: EaStyle.Sizes.toolButtonHeight
                        Layout.minimumHeight: EaStyle.Sizes.toolButtonHeight
                        Layout.maximumHeight: EaStyle.Sizes.toolButtonHeight
                        background: Item {
                            implicitWidth: connectionButton.accountView ? panel.headerActionExtent : EaStyle.Sizes.toolButtonHeight
                            implicitHeight: implicitWidth
                            Rectangle {
                                border.width: 0
                                objectName: "assistant.avatarCircle"
                                anchors.centerIn: parent
                                width: connectionButton.accountView ? EaStyle.Sizes.toolButtonHeight * 0.75 : parent.width
                                height: EaStyle.Sizes.toolButtonHeight * 0.75
                                radius: height * 0.5
                                color: !connectionButton.enabled ? panel.actionBackground
                                    : connectionButton.hovered || connectionButton.down || connectionButton.visualFocus ? EaStyle.Colors.themeAccent
                                    : (EaStyle.Colors.isDarkPalette ? "white" : "black")
                            }
                        }
                        ToolTip.text: connectionButton.accountView ? qsTr("Account") : text
                        Accessible.name: ToolTip.text
                        KeyNavigation.priority: KeyNavigation.BeforeItem
                        KeyNavigation.backtab: connectionButton.accountView ? usageButton : panel.toggleControl
                        KeyNavigation.tab: connectionButton.accountView ? composer.firstFocusItem : panel.toggleControl
                        onClicked: {
                            if (connectionButton.pendingConnection) {
                                const component = panel, original = panel.assistant;
                                if (!Qt.isQtObject(component) || !Qt.isQtObject(original) || component.assistant !== original
                                    || original.state !== "connecting" || !original.canCancel) return;
                                original.cancel();
                            } else if (connectionButton.accountView) accountDialog.open();
                            else if (panel.assistant.resumeConnection()) { /* Original approved session owns reconnection. */ }
                            else {
                                const component = panel, original = panel.assistant, dialog = connectionDialog;
                                const offer = dialog.beginOffer();
                                if (!Qt.isQtObject(component) || !Qt.isQtObject(original) || !Qt.isQtObject(dialog)
                                    || component.assistant !== original || dialog.assistant !== original || dialog.approvalOwner !== offer) return;
                                component.retireConsentSend();
                                if (!Qt.isQtObject(component) || !Qt.isQtObject(original) || !Qt.isQtObject(dialog)
                                    || component.assistant !== original || dialog.assistant !== original || dialog.approvalOwner !== offer || original.connected) return;
                                dialog.presentOffer(offer);
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
                ListView {
                    id: conversation
                    objectName: "assistant.messages"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: AppSizes.unit * 0.5
                    model: panel.assistant.messages
                    reuseItems: true
                    footer: Column {
                        width: conversation.width
                        spacing: chatBody.spacing
                        onPositioningComplete: conversation.followOutput()
                        AssistantPlan {
                            width: parent.width
                            assistant: panel.assistant
                        }
                        AssistantQuestion {
                            width: parent.width
                            assistant: panel.assistant
                        }
                        AssistantTrial {
                            width: parent.width
                            assistant: panel.assistant
                        }
                        Item {
                            width: parent.width
                            visible: workingCue.working && workingCue.presented
                            height: visible ? workingCue.height + chatBody.spacing : 0
                            AssistantWorking {
                                id: workingCue
                                objectName: "assistant.working"
                                y: chatBody.spacing
                                width: parent.width
                                height: Math.max(implicitHeight, iconExtent)
                                assistant: panel.assistant
                                presented: panel.shown && panel.visible
                            }
                        }
                    }
                    header: EdiNotice {
                        width: conversation.width
                        noticeText: panel.noticeState && panel.noticeState.owner === panel.assistant && !panel.noticeAnchorPresent
                            ? panel.noticeState.text : ""
                    }
                    delegate: Column {
                        id: messageDelegate
                        required property var model
                        required property int index
                        readonly property string rowId: model.id
                        readonly property string kind: model.kind
                        readonly property string text: model.text
                        readonly property var payload: model.payload
                        readonly property string status: model.status
                        width: conversation.width
                        spacing: chatBody.spacing
                        onPositioningComplete: conversation.followOutput()
                        ListView.onPooled: messageItem.resetDetails()
                        ListView.onReused: messageItem.resetDetails()
                        AssistantMessage {
                            id: messageItem
                            assistant: panel.assistant
                            width: parent.width
                            kind: messageDelegate.kind
                            text: messageDelegate.text
                            payload: messageDelegate.payload
                            status: messageDelegate.status
                            rowId: messageDelegate.rowId
                            stepNumber: messageDelegate.index + 1
                            onReportRequested: (sourceRowId, link) => panel.openReportLink(sourceRowId, link)
                            onDetailsChanging: {
                                conversation.cancelFlick();
                                conversation.followsTail = false;
                                conversation.jumpedUserId = "";
                            }
                            highlighted: kind === "user" && rowId === conversation.jumpedUserId
                        }
                        EdiNotice {
                            width: parent.width
                            noticeText: panel.noticeState && panel.noticeState.owner === panel.assistant
                                && panel.noticeAnchorPresent && panel.noticeState.anchor === messageDelegate.rowId
                                ? panel.noticeState.text : ""
                        }
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
                    function revealCurrentNotice() {
                        const original = panel.assistant, notice = panel.noticeState;
                        if (!notice || notice.owner !== original || !notice.text.length) return;
                        let anchor = -1;
                        for (let i = 0; i < original.messages.count; ++i)
                            if (original.messages.text(i, "id") === notice.anchor) { anchor = i; break; }
                        if (!Qt.isQtObject(panel) || !Qt.isQtObject(original) || original !== panel.assistant || panel.noticeState !== notice) return;
                        cancelFlick(); followsTail = false; jumpedUserId = "";
                        if (anchor >= 0) positionViewAtIndex(anchor, ListView.End);
                        else positionViewAtBeginning();
                    }
                    function positionAtTail() {
                        if (!followsTail || moving || historyScrollBar.pressed || height <= 0)
                            return;
                        // Columns report after their child geometry settles;
                        // resolve the view's pending layout before using its end.
                        forceLayout();
                        if (followsTail && !moving && !historyScrollBar.pressed)
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
                    onHeightChanged: followOutput()
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
                        function onDataChanged() { panel.noticeProjection = ({}); conversation.observeUserAdmission(); conversation.followOutput(); }
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
                    popupBoundary: panel.contentItem
                    previousFocusItem: composer.actionsControl.enabled ? composer.actionsControl : usageButton
                    hasPreviousUserMessage: conversation.previousUserIndex >= 0
                    hasNextUserMessage: conversation.nextUserIndex >= 0
                    onPreviousUserRequested: conversation.jumpToUser(-1)
                    onNextUserRequested: conversation.jumpToUser(1)
                    onSubmissionBlocked: {
                        const component = panel, view = conversation, original = panel.assistant;
                        component.captureNotice();
                        if (Qt.isQtObject(component) && Qt.isQtObject(view) && Qt.isQtObject(original)
                            && original === component.assistant && original.contextApprovalBlocked) view.revealCurrentNotice();
                    }
                    onSubmissionRequested: draft => {
                        const intent = panel.consentSend;
                        if (intent && draft && intent.draft.owner === draft.owner
                            && intent.draft.revision === draft.revision && intent.draft.ownerRevision === draft.ownerRevision
                            && intent.draft.files === draft.files && intent.draft.project === draft.project)
                            panel.retireConsentSend();
                    }
                    onContextApprovalRequested: draft => {
                        const component = panel, original = panel.assistant, draftComponent = composer, dialog = connectionDialog;
                        const previous = component.consentSend;
                        // Retire A before draft capture/getters can reenter, even
                        // when this same dialog is already visible or entering.
                        const offer = dialog.beginOffer();
                        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || !Qt.isQtObject(dialog)
                            || component.assistant !== original || dialog.assistant !== original
                            || dialog.approvalOwner !== offer || component.consentSend !== previous) return;
                        const captured = draftComponent.captureConsentDraft();
                        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant
                            || !Qt.isQtObject(dialog) || dialog.assistant !== original || dialog.approvalOwner !== offer
                            || !captured || captured.text !== draft || captured.owner !== original) return;
                        const owned = draftComponent.ownsConsentDraft(captured);
                        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant
                            || !Qt.isQtObject(dialog) || dialog.assistant !== original || dialog.approvalOwner !== offer
                            || !owned || component.consentSend !== previous) return;
                        const intent = { owner: original, project: captured.project, draft: captured,
                            context: captured.context, model: captured.model,
                            effort: captured.effort, offer: offer, approved: false };
                        component.consentSend = intent;
                        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant
                            || !Qt.isQtObject(dialog) || dialog.approvalOwner !== offer || component.consentSend !== intent) return;
                        const stillOwned = component.ownsConsentSend(intent);
                        if (!Qt.isQtObject(component) || !Qt.isQtObject(draftComponent) || !Qt.isQtObject(original) || original !== component.assistant
                            || !Qt.isQtObject(dialog) || dialog.approvalOwner !== offer || !stillOwned) return;
                        dialog.presentOffer(offer);
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
                Flickable {
                    id: signedOutNoticeViewport
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: AppSizes.unit
                    height: Math.min(contentHeight, Math.max(0, signInPrompt.y - AppSizes.unit * 2))
                    clip: true
                    contentWidth: width
                    contentHeight: signedOutControls.height
                    flickableDirection: Flickable.VerticalFlick
                    boundsBehavior: Flickable.StopAtBounds
                    interactive: contentHeight > height
                    visible: signedOutNotice.noticeText.length > 0
                        || (panel.assistant.canCancel && panel.assistant.state !== "connecting")
                    Column {
                        id: signedOutControls
                        width: parent.width
                        spacing: AppSizes.unit
                        EdiNotice {
                            id: signedOutNotice
                            width: parent.width
                            visible: noticeText.length > 0
                            noticeText: panel.noticeState && panel.noticeState.owner === panel.assistant
                                ? panel.noticeState.text : ""
                        }
                        EaElements.Button {
                            id: authCancel
                            objectName: "assistant.authCancel"
                            visible: panel.assistant.canCancel && panel.assistant.state !== "connecting"
                            anchors.horizontalCenter: parent.horizontalCenter
                            leftPadding: panel.assistant.state === "connecting" ? AppSizes.unit * 0.75 : 0
                            rightPadding: leftPadding
                            text: panel.assistant.state === "connecting" ? qsTr("Cancel connection") : qsTr("Stop")
                            background: Rectangle {
                                visible: panel.assistant.state === "connecting"
                                implicitHeight: panel.assistant.state === "connecting" ? EaStyle.Sizes.toolButtonHeight * 0.75 : 0
                                radius: height * 0.5
                                border.width: 0
                                color: !authCancel.enabled ? panel.actionBackground
                                    : authCancel.hovered || authCancel.down || authCancel.visualFocus ? EaStyle.Colors.themeAccent
                                    : (EaStyle.Colors.isDarkPalette ? "white" : "black")
                            }
                            contentItem: EaElements.Label {
                                text: authCancel.text
                                font: authCancel.font
                                color: panel.assistant.state === "connecting" && authCancel.enabled
                                    ? (EaStyle.Colors.isDarkPalette ? "black" : "white") : authCancel.foregroundColor()
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            onClicked: panel.assistant.cancel()
                        }
                    }
                    ScrollBar.vertical: ScrollBar {}
                }
                EmptyStateLabel {
                    id: signInPrompt
                    objectName: "assistant.signInPrompt"
                    anchors.centerIn: parent
                    width: Math.max(0,parent.width-AppSizes.unit*2)
                    text: qsTr("No ChatGPT connection")
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
            property real resetClock: Date.now()
            readonly property real viewportHeight: Math.max(0, parent.height - AppSizes.unit * 2)
            width: Math.min(AppSizes.unit * 30, Math.max(0, parent.width - AppSizes.unit * 2))
            height: Math.min(implicitHeight, viewportHeight)
            contentWidth: Math.max(0, width-leftPadding-rightPadding)
            contentHeight: Math.min(usageContent.implicitHeight, Math.max(0, viewportHeight-topPadding-bottomPadding
                -(implicitHeaderHeight > 0 ? implicitHeaderHeight+spacing : 0)-(implicitFooterHeight > 0 ? implicitFooterHeight+spacing : 0)))
            onOpened: { resetClock = Date.now(); panel.assistant.refreshUsage(); }
            Timer {
                interval: 60000
                repeat: true
                running: usageDialog.visible && panel.assistant.connected
                onTriggered: usageDialog.resetClock = Date.now()
            }
            ScrollView {
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                width: usageDialog.contentWidth
                height: usageDialog.contentHeight
                clip: true
                ScrollBar.vertical: EaElements.ScrollBar { policy: ScrollBar.AsNeeded; interactive: false }
                Column {
                    id: usageContent
                    width: Math.max(0, usageDialog.contentWidth-AppSizes.unit)
                    spacing: AppSizes.unit * 1.5
                    EaElements.Label {
                        objectName: "assistant.usageUnavailable"
                        visible: usageAllowances.count === 0
                        width: parent.width
                        text: qsTr("Session and weekly usage unavailable")
                        wrapMode: Text.WordWrap
                    }
                    Repeater {
                        id: usageAllowances
                        model: [{title: qsTr("Session limit"), minutes: 300, key: "session"}, {title: qsTr("Weekly"), minutes: 10080, key: "weekly"}]
                            .filter(row => panel.allowanceWindow(row.minutes) !== null)
                        Column {
                            id: allowance
                            required property var modelData
                            readonly property var window: panel.allowanceWindow(modelData.minutes)
                            objectName: "assistant.usage."+modelData.key
                            width: usageContent.width
                            spacing: AppSizes.unit * 0.35
                            RowLayout {
                                width: parent.width
                                EaElements.Label { text: allowance.modelData.title; Layout.fillWidth: true }
                                EaElements.Label {
                                    objectName: allowance.objectName+".percent"
                                    text: allowance.window ? qsTr("%1% used").arg(allowance.window.usedPercent) : qsTr("Unavailable")
                                }
                            }
                            Rectangle {
                                objectName: allowance.objectName+".bar"
                                width: parent.width
                                height: AppSizes.unit * 0.5
                                radius: height * 0.5
                                color: EaStyle.Colors.themeBackground
                                border.width: EaStyle.Sizes.borderThickness
                                border.color: EaStyle.Colors.appBorder
                                Rectangle {
                                    objectName: allowance.objectName+".fill"
                                    x: parent.border.width
                                    y: parent.border.width
                                    width: allowance.window ? Math.max(0,parent.width-parent.border.width*2) * Math.max(0,Math.min(1,allowance.window.usedPercent/100)) : 0
                                    height: Math.max(0,parent.height-parent.border.width*2)
                                    radius: height * 0.5
                                    color: allowance.window && 100-allowance.window.usedPercent < 5 ? EaStyle.Colors.red
                                         : allowance.window && 100-allowance.window.usedPercent < 25 ? EaStyle.Colors.orange : EaStyle.Colors.themeAccent
                                }
                            }
                            EaElements.Label {
                                objectName: allowance.objectName+".reset"
                                visible: allowance.window !== null
                                text: allowance.window ? panel.usageResetLabel(allowance.window.resetsAt,usageDialog.resetClock) : ""
                                color: EaStyle.Colors.themeForegroundMinor
                                textFormat: Text.PlainText
                                wrapMode: Text.WordWrap
                            }
                        }
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
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                width: accountDialog.contentWidth
                height: accountDialog.contentHeight
                clip: true
                Column {
                    id: accountContent
                    width: Math.max(0, accountDialog.contentWidth-AppSizes.unit)
                    spacing: 0
                    Column {
                        width: parent.width
                        spacing: AppSizes.unit * 0.25
                        EaElements.Label {
                            objectName: "assistant.accountIdentity"
                            width: parent.width
                            text: panel.accountData.email || qsTr("Account email unavailable")
                            textFormat: Text.PlainText
                            wrapMode: Text.WrapAnywhere
                        }
                        EaElements.Label {
                            objectName: "assistant.accountPlan"
                            width: parent.width
                            visible: panel.accountPlanLabel.length > 0
                            text: panel.accountPlanLabel
                            color: EaStyle.Colors.themeForegroundMinor
                            textFormat: Text.PlainText
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                    Item { width: 1; height: AppSizes.unit * 1.5 }
                    EaElements.Button {
                        id: signOutButton
                        objectName: "assistant.signOut"
                        text: qsTr("Sign out")
                        contentItem: Row {
                            spacing: AppSizes.unit * 0.5
                            EaElements.Label {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "sign-out-alt"
                                font.family: EaStyle.Fonts.iconsFamily
                                color: signOutButton.foregroundColor()
                            }
                            EaElements.Label { anchors.verticalCenter: parent.verticalCenter; text: signOutButton.text; color: signOutButton.foregroundColor() }
                        }
                        width: Math.min(implicitWidth,parent.width)
                        enabled: panel.assistant.connected
                        Accessible.name: text
                        onClicked: panel.assistant.signOut()
                    }
                }
            }
        }
        AssistantConnectionDialog {
            id: connectionDialog
            assistant: panel.assistant
            onRejected: panel.retireConsentSend()
            onContextApproved: offer => {
                const component = panel, original = panel.assistant, dialog = connectionDialog;
                const intent = component.consentSend;
                if (!intent || !Qt.isQtObject(dialog) || intent.offer !== offer || dialog.approvalOwner !== offer) return;
                const owned = component.ownsConsentSend(intent);
                if (!Qt.isQtObject(component) || !Qt.isQtObject(original) || original !== component.assistant) return;
                if (!owned) { if (component.consentSend === intent) component.retireConsentSend(); return; }
                if (!Qt.isQtObject(dialog) || component.consentSend !== intent || intent.offer !== offer || dialog.approvalOwner !== offer) return;
                intent.approved = true;
                component.scheduleConsentSend();
            }
        }
    }
}
