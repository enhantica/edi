// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Rectangle {
    id: row
    required property string kind
    required property string text
    property var payload: ({})
    readonly property var inputFiles: {
        if (kind !== "user" || !payload || payload.type !== "ediInput" || !payload.files) return [];
        const files = payload.files;
        // Existing SelectedFileLimits::files/name_bytes and Limits::id_bytes.
        if (!Number.isInteger(files.length) || files.length < 0 || files.length > 32) return [];
        const result = [];
        for (let i = 0; i < files.length; ++i) {
            const file = files[i];
            if (!file || typeof file.id !== "string" || file.id.length === 0 || file.id.length > 256
                || typeof file.name !== "string" || file.name.length > 512
                || typeof file.bytes !== "number" || !Number.isFinite(file.bytes) || file.bytes < 0
                || typeof file.textReadable !== "boolean" || typeof file.format !== "string") return [];
            result.push(file); // Bounded presentation references, not copied source bytes or another archive.
        }
        return result;
    }
    property string status: ""
    property string rowId: ""
    property AssistantViewModel assistant: null
    property int filePresentationRevision: 0
    Connections {
        target: row.assistant ? row.assistant.selectedFiles : null
        function onCountChanged() { ++row.filePresentationRevision; }
        function onDataChanged() { ++row.filePresentationRevision; }
    }
    function fileIsSelected(id, revision) {
        if (!assistant) return false;
        for (let i = 0; i < assistant.selectedFiles.count; ++i)
            if (assistant.selectedFiles.text(i, "id") === id) return true;
        return false;
    }
    property bool highlighted: false
    readonly property bool commandActivity: kind === "activity" && payload && payload.type === "commandExecution"
    readonly property bool decisionActivity: kind === "activity" && payload && typeof payload.decision === "string" && typeof payload.item_id === "string"
    readonly property bool summarizedActivity: decisionActivity || kind === "activity" && payload &&
        ["commandExecution", "fileChange", "webSearch", "mcpToolCall", "dynamicToolCall", "collabAgentToolCall", "plan", "ediOutcome"].indexOf(payload.type) >= 0
    readonly property string disclosureIdentity: rowId + "\n" + (payload && typeof payload.id === "string" ? payload.id : "")
    property bool technicalCopied: false
    onPayloadChanged: { technicalCopied = false; if (copyFeedback) copyFeedback.stop(); }
    Timer { id: copyFeedback; interval: EaStyle.Times.introAnimation; onTriggered: row.technicalCopied = false }
    function copyTechnicalPayload() {
        const component = row, identity = row.disclosureIdentity, original = row.payload;
        const current = () => Qt.isQtObject(component) && component.disclosureIdentity === identity && component.payload === original;
        try {
            const literal = JSON.stringify(original, null, 2);
            if (typeof literal !== "string" || !current()) return;
            ApplicationInfo.copyText(literal);
            if (!current()) return;
            component.technicalCopied = true;
            copyFeedback.restart();
        } catch (error) { if (current()) component.technicalCopied = false; }
    }
    signal detailsChanging()
    signal reportRequested(string sourceRowId, string link)
    function resetDetails() {
        technicalCopied = false;
        if (copyFeedback) copyFeedback.stop();
        if (commandDisclosure) commandDisclosure.checked = false;
        if (disclosure) disclosure.checked = false;
        if (originalDisclosure) originalDisclosure.checked = false;
        for (const viewport of [commandViewport, activityViewport, technicalViewport])
            if (viewport && viewport.contentItem && viewport.contentItem.contentY !== undefined)
                viewport.contentItem.contentY = 0;
        for (const field of [body, commandText, directoryText, outputText, activityText, technicalText, originalText])
            if (field) field.deselect();
    }
    onDisclosureIdentityChanged: resetDetails()
    onCommandActivityChanged: resetDetails()
    onSummarizedActivityChanged: resetDetails()
    ListView.onPooled: resetDetails()
    ListView.onReused: resetDetails()
    function commandCaption() {
        const actual = payload && typeof payload.status === "string" ? payload.status : "";
        const settled = actual === "completed" || actual === "failed" || actual === "declined" || actual === "interrupted";
        // The immutable original can remain inProgress after the public activity
        // is interrupted/failed. Neither that older original nor an exit field
        // alone proves a settled command outcome.
        if (!settled || row.status !== actual) {
            if (actual === "inProgress" && row.status === "in_progress")
                return activityLabel(true);
            let unconfirmed = qsTr("Command outcome unconfirmed");
            if (row.status === "interrupted") unconfirmed += qsTr(" · activity interrupted");
            else if (row.status === "failed") unconfirmed += qsTr(" · activity failed");
            else if (row.status === "completed") unconfirmed += qsTr(" · activity completed");
            else if (row.status === "refused" || row.status === "declined") unconfirmed += qsTr(" · activity refused");
            return unconfirmed;
        }
        let caption = actual === "completed" ? activityLabel(false)
                    : actual === "failed" ? qsTr("Command failed")
                    : actual === "declined" ? qsTr("Command declined")
                    : qsTr("Command interrupted");
        return caption;
    }
    function activityLabel(running) {
        if (!commandActivity) {
            const names = {fileChange: qsTr("File changes"), webSearch: qsTr("Web search"),
                mcpToolCall: qsTr("Tool activity"), dynamicToolCall: qsTr("Tool activity"),
                collabAgentToolCall: qsTr("Agent activity"), plan: qsTr("Plan update")};
            return names[payload.type] || qsTr("Activity");
        }
        // Retained JSON arrays arrive as QVariantList/QML sequences, which
        // need not satisfy Array.isArray. Project this bounded JSON field only;
        // canonical payload bytes and shell text remain untouched.
        const actions = JSON.parse(JSON.stringify(payload.commandActions || []));
        let category = "";
        if (Array.isArray(actions) && actions.length > 0) {
            category = actions[0] && typeof actions[0].type === "string" ? actions[0].type : "";
            for (const action of actions)
                if (!action || action.type !== category) { category = ""; break; }
        }
        if (category === "read") return running ? qsTr("Reading files") : qsTr("Read files");
        if (category === "listFiles") return running ? qsTr("Listing files") : qsTr("Listed files");
        if (category === "search") return running ? qsTr("Searching files") : qsTr("Searched files");
        return running ? qsTr("Running command") : qsTr("Ran command");
    }
    function shortActionObject(value, path) {
        // Only the single-line presentation changes; the retained literal stays exact.
        if (typeof value !== "string") return "";
        return value.trim().replace(/\s+/g, " ");
    }
    function usableCommandAction(action) {
        if (!action || typeof action !== "object" || Array.isArray(action) ||
            typeof action.command !== "string") return false;
        if (action.type === "read") return typeof action.name === "string" && typeof action.path === "string";
        if (action.type === "listFiles" || action.type === "search") {
            if (action.path !== undefined && action.path !== null && typeof action.path !== "string") return false;
            return action.type !== "search" || action.query === undefined || action.query === null || typeof action.query === "string";
        }
        return action.type === "unknown";
    }
    function activityDescription() {
        const supplied = typeof payload.purpose === "string" ? payload.purpose
                       : typeof payload.description === "string" ? payload.description
                       : payload.arguments && typeof payload.arguments.purpose === "string" ? payload.arguments.purpose : "";
        if (supplied.trim().length) return shortActionObject(supplied, false);
        if (!commandActivity) return "";
        // Exact structured action metadata may supply a purpose when the pinned
        // runtime has no explicit one. Never parse shell text or infer an outcome.
        const actions = JSON.parse(JSON.stringify(payload.commandActions || []));
        if (!Array.isArray(actions) || actions.length === 0 || !actions.every(usableCommandAction)) return "";
        const labels = [];
        for (const action of actions) {
            if (action.type === "read") labels.push(qsTr("Read %1").arg(action.name || action.path));
            else if (action.type === "listFiles") labels.push(action.path ? qsTr("List %1").arg(action.path) : qsTr("List files"));
            else if (action.type === "search") labels.push(action.query ? qsTr("Search for %1").arg(action.query) : qsTr("Search files"));
        }
        return shortActionObject(labels.join(" · "), false);
    }
    function activityCaption() {
        if (payload.type === "ediOutcome" && payload.actor === "Edi" && typeof payload.title === "string") return shortActionObject(payload.title, false);
        const description = activityDescription();
        if (description.length) return description;
        if (decisionActivity) return qsTr("Request");
        if (commandActivity) return qsTr("Command");
        const names = {fileChange: qsTr("File changes"), webSearch: qsTr("Web search"),
            mcpToolCall: qsTr("Native operation"), dynamicToolCall: qsTr("Native operation"),
            collabAgentToolCall: qsTr("Agent operation"), plan: qsTr("Plan update")};
        return names[payload.type] || qsTr("Activity");
    }
    function activityState() {
        if (commandActivity) {
            const actual = typeof payload.status === "string" ? payload.status : "";
            if (["completed", "failed", "declined", "interrupted"].indexOf(actual) >= 0 && row.status === actual) return actual;
            return actual === "inProgress" && row.status === "in_progress" ? "in_progress" : "unconfirmed";
        }
        if (payload.nativeOutcome && ["unconfirmed", "applied_unconfirmed"].indexOf(payload.nativeOutcome.status) >= 0) return "unconfirmed";
        return ["completed", "failed", "refused", "declined", "interrupted", "in_progress"].indexOf(row.status) >= 0 ? row.status : "unconfirmed";
    }
    function activityExplanation() {
        if (commandActivity) return commandCaption();
        const state = activityState();
        const category = activityLabel(state === "in_progress");
        const statuses = {completed: qsTr("completed"), failed: qsTr("failed"), refused: qsTr("refused"),
            declined: qsTr("declined"), interrupted: qsTr("interrupted"), in_progress: qsTr("in progress")};
        const reported = statuses[row.status] || qsTr("unknown");
        const native = payload.nativeOutcome ? payload.nativeOutcome.status : "";
        if (native === "applied_unconfirmed")
            return qsTr("%1 · Activity status: %2 · Native changes applied; publication unconfirmed").arg(category).arg(reported);
        if (native === "unconfirmed")
            return qsTr("%1 · Activity status: %2 · Native outcome unconfirmed; inspect the actual project").arg(category).arg(reported);
        if (state === "unconfirmed")
            return qsTr("%1 · Activity status: %2 · Outcome unconfirmed").arg(category).arg(reported);
        return qsTr("%1 · %2").arg(category).arg(reported);
    }
    function activityOutcomeKey() {
        const state = activityState();
        return state === "completed" ? "success" : state === "failed" ? "failed"
             : state === "refused" || state === "declined" ? "refused" : state === "interrupted" ? "stopped" : "notConverged";
    }
    function activityCategoryIcon() {
        const icons = {commandExecution:"terminal",fileChange:"file",webSearch:"search",mcpToolCall:"cog",
            dynamicToolCall:"cog",collabAgentToolCall:"users",plan:"clipboard-list",ediOutcome:"info-circle"};
        return icons[payload.type] || "info-circle";
    }
    TextMetrics { id: technicalCaptionMetrics; font: technicalCaptionLabel.font; text: disclosure.text }
    TextMetrics { id: originalCaptionMetrics; font: originalCaptionLabel.font; text: originalDisclosure.text }
    color: "transparent"
    implicitHeight: content.implicitHeight + (kind === "user" ? AppSizes.unit * 1.5 : AppSizes.unit * 0.5)
    TextMetrics {
        id: userTextMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        text: row.kind === "user" ? row.text : ""
    }
    Rectangle {
        id: bubble
        x: row.kind === "user" ? row.width - width : 0
        width: row.kind === "user" ? Math.min(row.width - AppSizes.unit, Math.max(AppSizes.unit * 3, userTextMetrics.advanceWidth + AppSizes.unit * 2)) : row.width
        height: row.implicitHeight
        color: row.kind === "user" ? EaStyle.Colors.contentBackground : "transparent"
        radius: row.kind === "user" ? AppSizes.unit * 0.75 : 0
        border.width: row.highlighted ? EaStyle.Sizes.borderThickness : 0
        border.color: EaStyle.Colors.themeAccent
    }
    component LiteralDetails: TextEdit {
        property string fieldName: ""
        readOnly: true
        selectByMouse: true
        persistentSelection: true
        selectionColor: EaStyle.Colors.themeAccent
        selectedTextColor: EaStyle.Colors.themeBackground
        textFormat: TextEdit.PlainText
        wrapMode: TextEdit.WrapAnywhere
        color: EaStyle.Colors.themeForeground
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        Accessible.role: Accessible.StaticText
        Accessible.ignored: !visible
        Accessible.name: fieldName + ": " + text
    }
    Column {
        id: content
        x: bubble.x + (row.kind === "user" ? AppSizes.unit : 0)
        y: row.kind === "user" ? AppSizes.unit * 0.75 : AppSizes.unit * 0.25
        width: bubble.width - (row.kind === "user" ? AppSizes.unit * 2 : 0)
        spacing: AppSizes.unit * 0.4
        EaElements.Label {
            visible: row.kind !== "user" && row.kind !== "assistant" && !row.summarizedActivity
            text: qsTr("Activity")
            font.bold: true
        }
        EaElements.Label {
            visible: row.kind !== "user" && row.kind !== "assistant" && !row.summarizedActivity && row.status.length > 0
            text: row.status
            textFormat: Text.PlainText
        }
        TextEdit {
            id: body
            width: parent.width
            visible: !row.summarizedActivity
            AssistantMarkdown {
                anchors.fill: parent
                document: body.textDocument
                source: row.summarizedActivity ? "" : row.text
                accentColor: EaStyle.Colors.link
                bodyFont: body.font
                monoFontFamily: EaStyle.Fonts.monoFontFamily
                tableBorderColor: EaStyle.Colors.appBorder
                tableShadeColor: EaStyle.Colors.contentBackground
                markdown: row.kind === "assistant"
            }
            readOnly: true
            selectByMouse: true
            persistentSelection: true
            selectionColor: EaStyle.Colors.themeAccent
            selectedTextColor: EaStyle.Colors.themeBackground
            textFormat: TextEdit.PlainText
            onLinkActivated: link => row.reportRequested(row.rowId, link)
            HoverHandler { cursorShape: body.hoveredLink.length > 0 ? Qt.PointingHandCursor : Qt.IBeamCursor }
            wrapMode: TextEdit.Wrap
            color: EaStyle.Colors.themeForeground
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            Accessible.role: Accessible.StaticText
            Accessible.ignored: !visible
            Accessible.name: visible ? (row.kind === "user" ? qsTr("You") : row.kind === "assistant" ? qsTr("Assistant") : qsTr("Activity")) + ": " + row.text : ""
        }
        Flow {
            width: parent.width
            spacing: AppSizes.unit * 0.25
            visible: row.kind === "user" && row.status === "completed" && row.inputFiles.length > 0
            Repeater {
                model: row.inputFiles
                delegate: RowLayout {
                    required property var modelData
                    objectName: "assistant.sentFile." + modelData.id
                    width: Math.min(implicitWidth, parent.width)
                    spacing: AppSizes.unit * 0.125
                    EaElements.Label {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        text: qsTr("%1 (%2 bytes)%3").arg(modelData.name).arg(modelData.bytes)
                            .arg(modelData.textReadable ? "" : qsTr(" · text export required"))
                        textFormat: Text.PlainText
                        elide: Text.ElideMiddle
                        color: EaStyle.Colors.themeForegroundMinor
                        Accessible.name: qsTr("Sent file snapshot: %1, %2 bytes").arg(modelData.name).arg(modelData.bytes)
                    }
                    EaElements.ToolButton {
                        objectName: "assistant.sentFile.remove." + modelData.id
                        fontIcon: "times"
                        implicitWidth: EaStyle.Sizes.toolButtonHeight * 0.75
                        implicitHeight: implicitWidth
                        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.6
                        showBackground: false
                        visible: row.fileIsSelected(modelData.id, row.filePresentationRevision)
                        enabled: row.assistant !== null && !row.assistant.canCancel
                        ToolTip.text: qsTr("Remove %1 from future assistant requests").arg(modelData.name)
                        Accessible.name: ToolTip.text
                        onClicked: row.assistant.removeSelectedFile(modelData.id)
                    }
                }
            }
        }
        EaElements.Button {
            id: commandDisclosure
            objectName: row.commandActivity ? "assistant.command.toggle" : "assistant.activity.toggle"
            visible: row.summarizedActivity
            checkable: true
            text: row.activityCaption()
            width: parent.width
            contentItem: RowLayout {
                spacing: AppSizes.unit * 0.5
                EaElements.Label {
                    id: activityGlyph
                    text: row.activityCategoryIcon()
                    Layout.preferredWidth: AppSizes.unit
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                    font.family: EaStyle.Fonts.iconsFamily
                    color: EaStyle.Colors.themeForegroundMinor
                    Accessible.ignored: true
                }
                EaElements.Label {
                    text: row.activityState() === "in_progress" ? "hourglass-half" : FitOutcomes.icon(row.activityOutcomeKey())
                    Layout.preferredWidth: AppSizes.unit
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                    font.family: EaStyle.Fonts.iconsFamily
                    color: row.activityState() === "in_progress" ? EaStyle.Colors.themeAccent : FitOutcomes.color(row.activityOutcomeKey())
                    Accessible.ignored: true
                }
                EaElements.Label {
                    id: activityCaptionLabel
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: commandDisclosure.text
                    color: EaStyle.Colors.themeForegroundMinor
                    textFormat: Text.PlainText
                    wrapMode: Text.NoWrap
                    maximumLineCount: 1
                    elide: Text.ElideRight
                }
            }
            ToolTip.text: row.activityExplanation() + " · " + text
            EaElements.ToolTip {
                text: commandDisclosure.ToolTip.text
                visible: commandDisclosure.visible && commandDisclosure.hovered && EaGlobals.Vars.showToolTips && text !== ""
            }
            Accessible.name: ToolTip.text
            Accessible.checkable: true
            Accessible.checked: checked
            Accessible.description: checked ? qsTr("Hide activity details") : qsTr("Show activity details")
            onPressed: row.detailsChanging()
        }
        ScrollView {
            id: commandViewport
            objectName: "assistant.command.details"
            width: parent.width
            visible: row.commandActivity && commandDisclosure.checked
            height: visible ? Math.min(commandFields.implicitHeight, AppSizes.unit * 18) : 0
            contentWidth: availableWidth
            contentHeight: commandFields.implicitHeight
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical: EaElements.ScrollBar { policy: ScrollBar.AsNeeded; interactive: false }
            Column {
                id: commandFields
                width: commandViewport.availableWidth
                spacing: AppSizes.unit * 0.4
                LiteralDetails {
                    width: parent.width
                    fieldName: qsTr("Retained command status")
                    text: commandViewport.visible ? qsTr("Status: %1").arg(row.payload.status || qsTr("unavailable"))
                        + (typeof row.payload.exitCode === "number" && Number.isInteger(row.payload.exitCode)
                            ? qsTr(" · exit %1").arg(row.payload.exitCode) : "") : ""
                }
                EaElements.Label { text: qsTr("Command"); font.bold: true }
                LiteralDetails {
                    id: commandText
                    objectName: "assistant.command.literal"
                    width: parent.width
                    fieldName: qsTr("Command")
                    text: commandViewport.visible && typeof row.payload.command === "string" ? row.payload.command : ""
                }
                EaElements.Label { text: qsTr("Working directory"); font.bold: true }
                LiteralDetails {
                    id: directoryText
                    width: parent.width
                    fieldName: qsTr("Working directory")
                    text: commandViewport.visible && typeof row.payload.cwd === "string" ? row.payload.cwd : ""
                }
                EaElements.Label {
                    text: !row.payload || typeof row.payload.aggregatedOutput !== "string" ? qsTr("Output unavailable")
                          : row.payload.aggregatedOutput.length === 0 ? qsTr("Output (empty)") : qsTr("Output")
                    font.bold: true
                }
                LiteralDetails {
                    id: outputText
                    objectName: "assistant.command.output"
                    width: parent.width
                    fieldName: qsTr("Output")
                    text: commandViewport.visible && typeof row.payload.aggregatedOutput === "string" ? row.payload.aggregatedOutput : ""
                }
            }
        }
        ScrollView {
            id: activityViewport
            width: parent.width
            visible: row.summarizedActivity && !row.commandActivity && commandDisclosure.checked
                && !(row.payload.type === "dynamicToolCall" && row.text === "dynamicToolCall")
            height: visible ? Math.min(activityText.implicitHeight, AppSizes.unit * 18) : 0
            contentWidth: availableWidth
            contentHeight: activityText.implicitHeight
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical: EaElements.ScrollBar { policy: ScrollBar.AsNeeded; interactive: false }
            LiteralDetails {
                id: activityText
                width: activityViewport.availableWidth
                fieldName: qsTr("Activity")
                text: activityViewport.visible ? row.text : ""
            }
        }
        RowLayout {
            id: technicalHeader
            x: row.summarizedActivity ? AppSizes.unit * 1.5 : 0
            width: Math.max(0, parent.width - x)
            visible: row.kind !== "assistant" && row.kind !== "user" && Object.keys(row.payload || {}).length > 0 && (!row.summarizedActivity || commandDisclosure.checked)
            spacing: AppSizes.unit * 0.25
            EaElements.Button {
                id: disclosure
                checkable: true
                text: checked ? qsTr("Hide technical details") : qsTr("Technical details")
                implicitWidth: technicalGlyph.width + Math.ceil(technicalCaptionMetrics.advanceWidth) + AppSizes.unit * 0.5 + leftPadding + rightPadding
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                Layout.maximumWidth: implicitWidth
                contentItem: Row {
                    spacing: AppSizes.unit * 0.5
                    EaElements.Label { id: technicalGlyph; text: disclosure.checked ? "chevron-down" : "chevron-right"; width: AppSizes.unit; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75; font.family: EaStyle.Fonts.iconsFamily; color: EaStyle.Colors.themeForegroundMinor }
                    EaElements.Label { id: technicalCaptionLabel; width: Math.max(0, disclosure.availableWidth - technicalGlyph.width - parent.spacing); anchors.verticalCenter: parent.verticalCenter; verticalAlignment: Text.AlignVCenter; text: disclosure.text; color: EaStyle.Colors.themeForegroundMinor; textFormat: Text.PlainText; elide: Text.ElideRight }
                }
                Accessible.name: text
                Accessible.description: qsTr("Show or hide the original retained technical payload. The explanation and actual outcome remain above.")
                onPressed: row.detailsChanging()
            }
            EaElements.ToolButton {
                objectName: "assistant.activity.copyTechnical"
                fontIcon: row.technicalCopied ? "check" : "copy"
                showBackground: false
                ToolTip.text: row.technicalCopied ? qsTr("Copied") : qsTr("Copy technical details")
                Accessible.name: ToolTip.text
                onClicked: row.copyTechnicalPayload()
            }
        }
        ScrollView {
            id: technicalViewport
            x: technicalHeader.x
            width: Math.max(0, parent.width - x)
            visible: technicalHeader.visible && disclosure.checked
            height: visible ? Math.min(technicalFields.implicitHeight, AppSizes.unit * 18) : 0
            contentWidth: availableWidth
            contentHeight: technicalFields.implicitHeight
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical: EaElements.ScrollBar { policy: ScrollBar.AsNeeded; interactive: false }
            Column {
                id: technicalFields
                width: technicalViewport.availableWidth
                spacing: AppSizes.unit * 0.4
                LiteralDetails {
                    id: technicalText
                    width: parent.width
                    fieldName: qsTr("Technical details")
                    text: !technicalViewport.visible ? "" : row.decisionActivity
                        ? qsTr("Decision: %1\nAction reference: %2").arg(row.payload.decision === "decline" ? qsTr("Declined") : row.payload.decision).arg(row.payload.item_id)
                        : JSON.stringify(row.payload, null, 2)
                }
                EaElements.Button {
                    id: originalDisclosure
                    visible: row.decisionActivity
                    checkable: true
                    text: qsTr("Original payload")
                    implicitWidth: originalGlyph.width + Math.ceil(originalCaptionMetrics.advanceWidth) + AppSizes.unit * 0.5 + leftPadding + rightPadding
                    width: Math.min(parent.width, implicitWidth)
                    contentItem: Row {
                        spacing: AppSizes.unit * 0.5
                        EaElements.Label { id: originalGlyph; width: AppSizes.unit; anchors.verticalCenter: parent.verticalCenter; text: originalDisclosure.checked ? "chevron-down" : "chevron-right"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75; font.family: EaStyle.Fonts.iconsFamily; color: EaStyle.Colors.themeForegroundMinor }
                        EaElements.Label { id: originalCaptionLabel; width: Math.max(0, originalDisclosure.availableWidth - originalGlyph.width - parent.spacing); anchors.verticalCenter: parent.verticalCenter; verticalAlignment: Text.AlignVCenter; text: originalDisclosure.text; color: EaStyle.Colors.themeForegroundMinor; textFormat: Text.PlainText; elide: Text.ElideRight }
                    }
                    Accessible.name: text
                    onPressed: row.detailsChanging()
                }
                LiteralDetails {
                    id: originalText
                    width: parent.width
                    visible: row.decisionActivity && originalDisclosure.checked
                    fieldName: qsTr("Original payload")
                    text: visible && technicalViewport.visible ? JSON.stringify(row.payload, null, 2) : ""
                }
            }
        }
    }
}
