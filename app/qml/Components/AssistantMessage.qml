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
    property int stepNumber: 0
    property AssistantViewModel assistant: null
    property color chatBackgroundColor: EaStyle.Colors.appBarBackground
    function tableTone(lift) {
        const base=chatBackgroundColor;
        return Qt.rgba(Math.min(1,base.r+lift/255),Math.min(1,base.g+lift/255),Math.min(1,base.b+lift/255),base.a);
    }
    property bool highlighted: false
    readonly property bool commandActivity: kind === "activity" && payload && payload.type === "commandExecution"
    readonly property bool decisionActivity: kind === "activity" && payload && typeof payload.decision === "string" && typeof payload.item_id === "string"
    readonly property bool summarizedActivity: decisionActivity || kind === "activity" && payload &&
        ["commandExecution", "fileChange", "webSearch", "mcpToolCall", "dynamicToolCall", "collabAgentToolCall", "plan", "ediOutcome"].indexOf(payload.type) >= 0
    readonly property string disclosureIdentity: rowId + "\n" + (payload && typeof payload.id === "string" ? payload.id : "")
    property var humanDetailsSnapshot: null
    property bool technicalCopied: false
    onPayloadChanged: { technicalCopied = false; humanDetailsSnapshot = null; if (copyFeedback) copyFeedback.stop(); if (commandDisclosure && commandDisclosure.checked) refreshHumanDetails(); }
    onTextChanged: { technicalCopied = false; if (copyFeedback) copyFeedback.stop(); }
    onStatusChanged: { humanDetailsSnapshot = null; if (commandDisclosure && commandDisclosure.checked) refreshHumanDetails(); }
    Timer { id: copyFeedback; interval: EaStyle.Times.introAnimation; onTriggered: row.technicalCopied = false }
    function readHumanDetails() {
        const component = row, original = row.assistant, id = row.rowId, kind = row.kind, status = row.status;
        if (!original) return null;
        const value = original.activityHumanDetails(id, kind, status);
        return Qt.isQtObject(component) && component.assistant === original && component.rowId === id
            && component.kind === kind && component.status === status && value.row_id === id
            && value.kind === kind && value.status === status ? value : null;
    }
    function refreshHumanDetails() {
        const detail = readHumanDetails();
        if (commandDisclosure && commandDisclosure.checked) humanDetailsSnapshot = detail;
    }
    function fullHumanDescription(detail) {
        if (!detail) return qsTr("This step's description is currently unavailable.");
        const payload = detail.payload || {}, text = typeof detail.text === "string" ? detail.text : "";
        const lines = [];
        const add = value => { if (typeof value === "string" && value.trim().length && lines.indexOf(value) < 0) lines.push(value); };
        const short = activityCaption();
        const description = activityDescription(true, payload);
        if (description.trim().length && shortActionObject(description, false) !== short) add(description);
        // Only established human producers use row.text as a description.
        // Generic/command activity text may contain shell or protocol bytes.
        const humanRow = ["error", "plan", "question", "tool", "trial"].indexOf(kind) >= 0
            || (decisionActivity && typeof payload.type === "undefined");
        if (humanRow && shortActionObject(text, false) !== short) add(text);
        if (!lines.some(line => shortActionObject(line, false).length > short.length)) {
            if (payload && payload.type === "dynamicToolCall" && assistant)
                add(assistant.nativeActionDescription(typeof payload.tool === "string" ? payload.tool : "", ""));
            else if (payload && payload.type === "webSearch") add(qsTr("Find or read public sources relevant to the current task."));
            else if (commandActivity) add(qsTr("Use the reported operation to support the current task."));
            else add(qsTr("Carry out the requested assistant action for the current task."));
        }
        const outcome = payload && payload.nativeOutcome;
        const message = outcome && typeof outcome.message === "string" ? outcome.message
                      : payload && payload.error && typeof payload.error.message === "string" ? payload.error.message : "";
        add(message);
        if (humanRow && payload) add(payload.message);
        const code = outcome && typeof outcome.action_error === "string" ? outcome.action_error
                   : outcome && typeof outcome.code === "string" ? outcome.code
                   : payload && typeof payload.code === "string" ? payload.code : "";
        if (!message.trim().length && code === "project_required" && assistant)
            add(assistant.nativeActionDescription(payload && typeof payload.tool === "string" ? payload.tool : "", code));
        return lines.join("\n");
    }
    function humanActivityText(detail) {
        const short = activityCaption(), full = fullHumanDescription(detail);
        return short === full ? full : short + "\n" + full;
    }
    function copyActivity() {
        const component = row, identity = row.disclosureIdentity, original = row.payload, owner = row.assistant;
        const originalText = row.text, originalKind = row.kind, originalStatus = row.status;
        const detail = row.readHumanDetails();
        if (!detail) return;
        const human = row.humanActivityText(detail);
        const current = () => Qt.isQtObject(component) && component.disclosureIdentity === identity
            && component.payload === original && component.assistant === owner && component.text === originalText
            && component.kind === originalKind && component.status === originalStatus;
        try {
            let literal = human;
            if (Preferences.assistantCopyTechnicalDetails) {
                const technical = owner.activityTechnicalDetails(row.rowId, originalKind, originalStatus);
                if (!technical.length || !current()) return;
                literal += "\n\n" + technical;
            }
            if (typeof literal !== "string" || !current()) return;
            ApplicationInfo.copyText(literal);
            if (!current()) return;
            component.technicalCopied = true;
            copyFeedback.restart();
        } catch (error) { if (current()) component.technicalCopied = false; }
    }
    function copyUserText() {
        const component = row, identity = row.disclosureIdentity, original = row.text;
        const originalPayload = row.payload, owner = row.assistant;
        const current = () => Qt.isQtObject(component) && component.kind === "user"
            && component.status === "completed" && component.disclosureIdentity === identity
            && component.text === original && component.payload === originalPayload && component.assistant === owner;
        try {
            if (!current()) return;
            ApplicationInfo.copyText(original);
            if (!current()) return;
            component.technicalCopied = true;
            copyFeedback.restart();
        } catch (error) { if (current()) component.technicalCopied = false; }
    }
    signal detailsChanging()
    signal reportRequested(string sourceRowId, string link)
    function resetDetails() {
        technicalCopied = false;
        humanDetailsSnapshot = null;
        if (copyFeedback) copyFeedback.stop();
        if (commandDisclosure) commandDisclosure.checked = false;
        if (body) body.deselect();
        if (humanDetails) humanDetails.deselect();
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
                mcpToolCall: qsTr("Tool activity"), dynamicToolCall: qsTr("Project action"),
                collabAgentToolCall: qsTr("Agent activity"), plan: qsTr("Plan update")};
            return names[payload && payload.type] || qsTr("Activity");
        }
        const category = payload && typeof payload.commandCategory === "string" ? payload.commandCategory : "";
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
    function webSearchCaption(source) {
        const payload = source || row.payload;
        const action = payload.action;
        if (action !== undefined && action !== null && (typeof action !== "object" || Array.isArray(action))) return "";
        if (!action || action.type === "search") {
            let query = shortActionObject(action ? action.query : "", false);
            if (!query.length && action && action.queries !== undefined && action.queries !== null) {
                // Retained QVariantList fields use the same JSON projection as command actions.
                const queries = JSON.parse(JSON.stringify(action.queries));
                if (!Array.isArray(queries) || !queries.every(value => typeof value === "string")) return "";
                query = queries.map(value => shortActionObject(value, false)).filter(value => value.length).join(" · ");
            }
            if (!query.length) query = shortActionObject(payload.query, false);
            return query.length ? qsTr("Search the web for %1").arg(query) : "";
        }
        if (action.type === "openPage") {
            const url = shortActionObject(action.url, false);
            return url.length ? qsTr("Open web page %1").arg(url) : "";
        }
        if (action.type === "findInPage") {
            const url = shortActionObject(action.url, false), pattern = shortActionObject(action.pattern, false);
            if (url.length && pattern.length) return qsTr("Find %1 on %2").arg(pattern).arg(url);
            if (pattern.length) return qsTr("Find %1 on a web page").arg(pattern);
            if (url.length) return qsTr("Find text on %1").arg(url);
        }
        return "";
    }
    function nativeActionCaption() {
        const action = payload && typeof payload.tool === "string" ? payload.tool : "";
        return assistant ? assistant.nativeActionLabel(action) : qsTr("Work on the current project");
    }
    function activityDescription(full, source) {
        const payload = source || row.payload;
        if (!payload || typeof payload !== "object") return "";
        const supplied = typeof payload.purpose === "string" ? payload.purpose
                       : typeof payload.description === "string" ? payload.description
                       : payload.arguments && typeof payload.arguments.purpose === "string" ? payload.arguments.purpose : "";
        if (payload.type === "dynamicToolCall" && (supplied === "Edi native action"
                || supplied === "Edi native action: " + payload.tool)) return nativeActionCaption();
        if (supplied.trim().length) return full ? supplied : shortActionObject(supplied, false);
        if (payload.type === "webSearch") return webSearchCaption(payload);
        if (!commandActivity) return "";
        return typeof payload.commandDescription === "string" ? payload.commandDescription : "";
    }
    function activityCaption() {
        const kinds = {error: qsTr("Assistant error"), plan: qsTr("Review work plan"), question: qsTr("Assistant question"),
            tool: qsTr("Project action"), trial: qsTr("Review refinement trial")};
        if (Object.prototype.hasOwnProperty.call(kinds, kind)) return kinds[kind];
        if (decisionActivity) return qsTr("Review requested action");
        if (commandActivity) return activityLabel(false);
        if (payload && payload.type === "dynamicToolCall") return nativeActionCaption();
        const names = {fileChange: qsTr("Update files"), webSearch: qsTr("Search the web"),
            mcpToolCall: qsTr("Use external tool"), collabAgentToolCall: qsTr("Coordinate assistant task"),
            plan: qsTr("Update work plan"), ediOutcome: qsTr("Report project action")};
        return payload && Object.prototype.hasOwnProperty.call(names, payload.type) ? names[payload.type] : qsTr("Perform assistant action");
    }
    function activityState() {
        if (commandActivity) {
            const actual = typeof payload.status === "string" ? payload.status : "";
            if (["completed", "failed", "declined", "interrupted"].indexOf(actual) >= 0 && row.status === actual) return actual;
            return actual === "inProgress" && row.status === "in_progress" ? "in_progress" : "unconfirmed";
        }
        if (payload && payload.nativeOutcome && ["unconfirmed", "applied_unconfirmed"].indexOf(payload.nativeOutcome.status) >= 0) return "unconfirmed";
        return ["completed", "failed", "refused", "declined", "interrupted", "in_progress"].indexOf(row.status) >= 0 ? row.status : "unconfirmed";
    }
    function activityExplanation() {
        const state = activityState();
        const native = payload && payload.nativeOutcome ? payload.nativeOutcome.status : "";
        if (native === "applied_unconfirmed")
            return qsTr("Changes were made, but completion could not be confirmed.");
        if (native === "unconfirmed" || state === "unconfirmed")
            return qsTr("The result could not be confirmed. Inspect the project before continuing.");
        const statuses = {completed: qsTr("Completed"), failed: qsTr("Failed"), refused: qsTr("Refused"),
            declined: qsTr("Declined"), interrupted: qsTr("Stopped"), in_progress: qsTr("In progress")};
        return statuses[state] || qsTr("Result unavailable");
    }
    function activityOutcomeKey() {
        const state = activityState();
        return state === "completed" ? "success" : state === "failed" ? "failed"
             : state === "refused" || state === "declined" ? "refused" : state === "interrupted" ? "stopped" : "notConverged";
    }
    color: "transparent"
    function sentFileLabel(file) {
        return qsTr("%1 (%2)%3").arg(file.name).arg(ApplicationInfo.fileSizeKilobytes(file.bytes))
            .arg(file.textReadable ? "" : qsTr(" · text export required"));
    }
    readonly property real widestSentFile: {
        if (kind !== "user" || status !== "completed") return 0;
        // advanceWidth is a method: read its actual font to track font/theme changes.
        const metricsFont = historyCopyMetrics.font;
        let widest = 0;
        for (const file of inputFiles)
            widest = Math.max(widest, Math.ceil(historyCopyMetrics.advanceWidth(sentFileLabel(file))));
        return widest;
    }
    readonly property real historyCopyExtent: Math.ceil(historyCopyMetrics.height)
    readonly property real historyCopyGutter: kind === "user" ? historyCopyExtent + AppSizes.unit : 0
    implicitHeight: Math.max(content.implicitHeight + (kind === "user" ? AppSizes.unit * 1.5 : AppSizes.unit * 0.5),
        kind === "user" ? historyCopyExtent + AppSizes.unit * 1.5 : 0)
    FontMetrics {
        id: historyCopyMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }
    TextMetrics {
        id: userTextMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        text: row.kind === "user" ? row.text : ""
    }
    Rectangle {
        id: bubble
        x: row.kind === "user" ? Math.max(0, row.width - row.historyCopyGutter - width) : 0
        width: row.kind === "user" ? Math.min(Math.max(0, row.width - row.historyCopyGutter - AppSizes.unit), Math.max(AppSizes.unit * 3, Math.max(userTextMetrics.advanceWidth, row.widestSentFile) + AppSizes.unit * 2)) : row.width
        height: row.implicitHeight
        color: row.kind === "user" ? EaStyle.Colors.contentBackground : "transparent"
        radius: row.kind === "user" ? AppSizes.unit * 0.75 : 0
        border.width: row.kind === "user" || row.highlighted ? EaStyle.Sizes.borderThickness : 0
        border.color: row.highlighted ? EaStyle.Colors.themeAccent : EaStyle.Colors.appBorder
    }
    HoverHandler {
        id: userHistoryHover
        enabled: row.kind === "user"
        acceptedDevices: PointerDevice.AllDevices
        blocking: false
        readonly property bool overHistory: hovered
            && point.position.x >= bubble.x && point.position.x <= row.width
            && point.position.y >= 0 && point.position.y <= row.height
    }
    EaElements.ToolButton {
        id: userCopy
        objectName: "assistant.user.copyText"
        x: bubble.x + bubble.width + AppSizes.unit * 0.5
        y: AppSizes.unit * 0.75
        implicitWidth: row.historyCopyExtent
        implicitHeight: row.historyCopyExtent
        visible: row.kind === "user" && row.status === "completed" && row.width >= row.historyCopyGutter
        opacity: userHistoryHover.overHistory || activeFocus ? 1 : 0
        focusPolicy: Qt.TabFocus
        fontIcon: row.technicalCopied ? "check" : "copy"
        showBackground: false
        contentItem: EaElements.Label {
            text: userCopy.fontIcon
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
            color: !userCopy.enabled ? EaStyle.Colors.themeForegroundDisabled
                : userCopy.hovered || userCopy.down ? EaStyle.Colors.themeForegroundHovered
                : EaStyle.Colors.themeForegroundMinor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            Accessible.ignored: true
        }
        ToolTip.text: row.technicalCopied ? qsTr("Copied") : qsTr("Copy sent message")
        Accessible.name: ToolTip.text
        onClicked: if (userHistoryHover.overHistory || activeFocus) row.copyUserText()
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
        width: Math.max(0, bubble.width - (row.kind === "user" ? AppSizes.unit * 2 : 0))
        spacing: AppSizes.unit * 0.4
        TextEdit {
            id: body
            width: parent.width
            visible: (row.kind === "user" || row.kind === "assistant") && row.text.length > 0
            AssistantMarkdown {
                anchors.fill: parent
                document: body.textDocument
                source: row.summarizedActivity ? "" : row.text
                accentColor: EaStyle.Colors.link
                bodyFont: body.font
                monoFontFamily: EaStyle.Fonts.monoFontFamily
                tableBorderColor: EaStyle.Colors.appBorder
                tableBaseColor: row.tableTone(5)
                tableShadeColor: row.tableTone(13)
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
        Column {
            id: sentFiles
            width: parent.width
            topPadding: row.text.length > 0 ? AppSizes.unit * 0.5 : 0
            spacing: 0
            visible: row.kind === "user" && row.status === "completed" && row.inputFiles.length > 0
            Repeater {
                model: row.inputFiles
                delegate: RowLayout {
                    required property var modelData
                    objectName: "assistant.sentFile." + modelData.id
                    width: sentFiles.width
                    spacing: AppSizes.unit * 0.125
                    EaElements.Label {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        text: row.sentFileLabel(modelData)
                        font: historyCopyMetrics.font
                        textFormat: Text.PlainText
                        elide: Text.ElideMiddle
                        color: EaStyle.Colors.themeForegroundMinor
                        Accessible.name: qsTr("Sent file snapshot: %1, %2").arg(modelData.name).arg(ApplicationInfo.fileSizeKilobytes(modelData.bytes))
                    }
                }
            }
        }
        RowLayout {
            id: activityHeader
            width: parent.width
            visible: row.kind !== "assistant" && row.kind !== "user"
            spacing: AppSizes.unit * 0.5
            HoverHandler {
                id: activityHeaderHover
                acceptedDevices: PointerDevice.AllDevices
                blocking: false
            }
            EaElements.Button {
                id: commandDisclosure
                objectName: row.commandActivity ? "assistant.command.toggle" : "assistant.activity.toggle"
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                checkable: true
                text: row.activityCaption()
                contentItem: RowLayout {
                    spacing: AppSizes.unit * 0.5
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
                        text: row.stepNumber > 0 ? row.stepNumber + "." : ""
                        color: EaStyle.Colors.themeForegroundMinor
                        textFormat: Text.PlainText
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
                onCheckedChanged: {
                    if (checked) row.refreshHumanDetails();
                    else row.humanDetailsSnapshot = null;
                }
            }
            EaElements.ToolButton {
                id: activityCopy
                objectName: "assistant.activity.copy"
                implicitWidth: commandDisclosure.implicitHeight
                implicitHeight: commandDisclosure.implicitHeight
                opacity: activityHeaderHover.hovered || activeFocus ? 1 : 0
                focusPolicy: Qt.TabFocus
                fontIcon: row.technicalCopied ? "check" : "copy"
                showBackground: false
                contentItem: EaElements.Label {
                    text: activityCopy.fontIcon
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                    color: !activityCopy.enabled ? EaStyle.Colors.themeForegroundDisabled
                        : activityCopy.hovered || activityCopy.down ? EaStyle.Colors.themeForegroundHovered
                        : EaStyle.Colors.themeForegroundMinor
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Accessible.ignored: true
                }
                ToolTip.text: row.technicalCopied ? qsTr("Copied") : qsTr("Copy step")
                Accessible.name: ToolTip.text
                onClicked: if (activityHeaderHover.hovered || activeFocus) row.copyActivity()
            }
        }
        Rectangle {
            width: parent.width
            visible: row.kind !== "assistant" && row.kind !== "user" && commandDisclosure.checked
            height: visible ? humanDetails.implicitHeight + AppSizes.unit * 1.5 : 0
            color: EaStyle.Colors.contentBackground
            radius: AppSizes.unit * 0.75
            TextEdit {
                id: humanDetails
                objectName: "assistant.activity.details"
                x: AppSizes.unit
                y: AppSizes.unit * 0.75
                width: Math.max(0, parent.width - AppSizes.unit * 2)
                text: visible ? row.fullHumanDescription(row.humanDetailsSnapshot) : ""
                textFormat: TextEdit.PlainText
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
                color: EaStyle.Colors.themeForegroundMinor
            }
        }
    }
}
