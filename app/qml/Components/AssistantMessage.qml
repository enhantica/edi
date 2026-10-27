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
    property bool highlighted: false
    readonly property bool commandActivity: kind === "activity" && payload && payload.type === "commandExecution"
    readonly property bool decisionActivity: kind === "activity" && payload && typeof payload.decision === "string" && typeof payload.item_id === "string"
    readonly property bool summarizedActivity: decisionActivity || kind === "activity" && payload &&
        ["commandExecution", "fileChange", "webSearch", "mcpToolCall", "dynamicToolCall", "collabAgentToolCall", "plan", "ediOutcome"].indexOf(payload.type) >= 0
    readonly property string disclosureIdentity: rowId + "\n" + (payload && typeof payload.id === "string" ? payload.id : "")
    property bool technicalCopied: false
    onPayloadChanged: { technicalCopied = false; if (copyFeedback) copyFeedback.stop(); }
    onTextChanged: { technicalCopied = false; if (copyFeedback) copyFeedback.stop(); }
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
        if (copyFeedback) copyFeedback.stop();
        if (commandDisclosure) commandDisclosure.checked = false;
        for (const viewport of [technicalViewport])
            if (viewport && viewport.contentItem && viewport.contentItem.contentY !== undefined)
                viewport.contentItem.contentY = 0;
        for (const field of [body, commandText, directoryText, outputText, activityText, technicalText, decisionText])
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
            return names[payload && payload.type] || qsTr("Activity");
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
    function guidanceReadCaption(workflow, refinement) {
        return workflow && refinement ? qsTr("Read assistant workflow and refinement instructions")
             : workflow ? qsTr("Read assistant workflow instructions")
             : refinement ? qsTr("Read assistant refinement instructions") : "";
    }
    function knownGuidanceCommandCaption(command) {
        // Closed whole-command identities only; never tokenize or execute shell text.
        const workflow = "cat .agents/skills/project-assistance/SKILL.md";
        const refinement = "cat .agents/skills/refinement-strategy/SKILL.md";
        if (command === workflow) return guidanceReadCaption(true, false);
        if (command === refinement) return guidanceReadCaption(false, true);
        if (command === workflow + " .agents/skills/refinement-strategy/SKILL.md"
            || command === refinement + " .agents/skills/project-assistance/SKILL.md") return guidanceReadCaption(true, true);
        return "";
    }
    function declaredCommandPurpose(command) {
        const marker = "# Edi purpose: ";
        if (typeof command !== "string" || !command.startsWith(marker)) return "";
        // Existing native-purpose bounds; never scan or copy the whole script.
        const first = command.slice(0, marker.length + 120 + 2);
        const newline = first.indexOf("\n");
        if (newline < 0) return "";
        let goal = first.slice(marker.length, newline);
        if (goal.endsWith("\r")) goal = goal.slice(0, -1);
        if (!goal.length || goal.length > 120 || !goal.trim().length || goal.endsWith("\\")) return "";
        let utf8 = 0;
        for (let i = 0; i < goal.length; ++i) {
            const c = goal.charCodeAt(i);
            if (c < 0x20 || c >= 0x7f && c <= 0x9f || c === 0x2028 || c === 0x2029
                || c === 0xfeff || c === 0x061c || c === 0x200e || c === 0x200f
                || c >= 0x202a && c <= 0x202e || c >= 0x2066 && c <= 0x2069) return "";
            if (c >= 0xd800 && c <= 0xdbff) {
                if (++i >= goal.length) return "";
                const low = goal.charCodeAt(i);
                if (low < 0xdc00 || low > 0xdfff) return "";
                utf8 += 4;
            } else if (c >= 0xdc00 && c <= 0xdfff) return "";
            else utf8 += c < 0x80 ? 1 : c < 0x800 ? 2 : 3;
            if (utf8 > 480) return "";
        }
        return goal; // Supplied goal only; never status, authority or verified intent.
    }
    function webSearchCaption() {
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
    function activityDescription() {
        if (!payload || typeof payload !== "object") return "";
        const supplied = typeof payload.purpose === "string" ? payload.purpose
                       : typeof payload.description === "string" ? payload.description
                       : payload.arguments && typeof payload.arguments.purpose === "string" ? payload.arguments.purpose : "";
        if (supplied.trim().length) return shortActionObject(supplied, false);
        if (payload.type === "webSearch") return webSearchCaption();
        if (!commandActivity) return "";
        const guidance = knownGuidanceCommandCaption(payload.command);
        if (guidance.length) return guidance;
        // Exact structured action metadata may supply a purpose when the pinned
        // runtime has no explicit one. Never parse shell text or infer an outcome.
        const actions = JSON.parse(JSON.stringify(payload.commandActions || []));
        if (!Array.isArray(actions) || actions.length === 0 || !actions.every(usableCommandAction)) return "";
        if (actions.length === 1 && actions[0].type === "unknown") {
            const declared = declaredCommandPurpose(actions[0].command);
            if (declared.length) return declared;
        }
        const labels = [];
        for (const action of actions) {
            if (action.type === "read") {
                const path = action.path.replace(/\\/g, "/");
                if (/(^|\/)project-assistance\/SKILL\.md$/.test(path)) labels.push(guidanceReadCaption(true, false));
                else if (/(^|\/)refinement-strategy\/SKILL\.md$/.test(path)) labels.push(guidanceReadCaption(false, true));
                else if (action.name === "SKILL.md") labels.push(qsTr("Read assistant instructions"));
                else labels.push(qsTr("Read %1").arg(action.name || action.path));
            }
            else if (action.type === "listFiles") labels.push(action.path ? qsTr("List %1").arg(action.path) : qsTr("List files"));
            else if (action.type === "search") labels.push(action.query ? qsTr("Search for %1").arg(action.query) : qsTr("Search files"));
            else if (action.type === "unknown") labels.push(qsTr("Run shell command"));
        }
        return shortActionObject(labels.join(" · "), false);
    }
    function activityCaption() {
        if (payload && payload.type === "ediOutcome" && payload.actor === "Edi" && typeof payload.title === "string" && payload.title.trim().length) return shortActionObject(payload.title, false);
        const description = activityDescription();
        if (description.length) return description;
        if (decisionActivity) return qsTr("Review requested action");
        if (commandActivity) return qsTr("Run shell command");
        if (payload && payload.type === "dynamicToolCall") {
            const tools = {inspect_project: qsTr("Inspect project"), list_parameters: qsTr("Inspect parameters"),
                diagnostics: qsTr("Check refinement diagnostics"), set_parameters: qsTr("Update parameter values"),
                set_free: qsTr("Select refinement parameters"), run_fit: qsTr("Refine project"),
                create_cwl_project: qsTr("Create diffraction project"), acquire_inputs: qsTr("Inspect input files"),
                save_project: qsTr("Save project"), add_relations: qsTr("Edit parameter relationships"),
                edit_background: qsTr("Edit experiment background")};
            return Object.prototype.hasOwnProperty.call(tools, payload.tool) ? tools[payload.tool] : qsTr("Use project tool");
        }
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
        if (commandActivity) return commandCaption();
        const state = activityState();
        const category = activityLabel(state === "in_progress");
        const statuses = {completed: qsTr("completed"), failed: qsTr("failed"), refused: qsTr("refused"),
            declined: qsTr("declined"), interrupted: qsTr("interrupted"), in_progress: qsTr("in progress")};
        const reported = statuses[row.status] || qsTr("unknown");
        const native = payload && payload.nativeOutcome ? payload.nativeOutcome.status : "";
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
        return icons[payload && payload.type] || "info-circle";
    }
    color: "transparent"
    function sentFileLabel(file) {
        return qsTr("%1 (%2 bytes)%3").arg(file.name).arg(file.bytes)
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
        border.width: row.highlighted ? EaStyle.Sizes.borderThickness : 0
        border.color: EaStyle.Colors.themeAccent
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
            visible: row.kind !== "activity"
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
            id: sentFiles
            width: parent.width
            spacing: AppSizes.unit * 0.25
            visible: row.kind === "user" && row.status === "completed" && row.inputFiles.length > 0
            Repeater {
                model: row.inputFiles
                delegate: RowLayout {
                    required property var modelData
                    objectName: "assistant.sentFile." + modelData.id
                    width: Math.min(implicitWidth, sentFiles.width)
                    spacing: AppSizes.unit * 0.125
                    EaElements.Label {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        text: row.sentFileLabel(modelData)
                        font: historyCopyMetrics.font
                        textFormat: Text.PlainText
                        elide: Text.ElideMiddle
                        color: EaStyle.Colors.themeForegroundMinor
                        Accessible.name: qsTr("Sent file snapshot: %1, %2 bytes").arg(modelData.name).arg(modelData.bytes)
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
            EaElements.ToolButton {
                id: activityCopy
                objectName: "assistant.activity.copyTechnical"
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
                ToolTip.text: row.technicalCopied ? qsTr("Copied") : qsTr("Copy activity details")
                Accessible.name: ToolTip.text
                onClicked: if (activityHeaderHover.hovered || activeFocus) row.copyTechnicalPayload()
            }
        }
        Rectangle {
            width: parent.width
            visible: row.kind !== "assistant" && row.kind !== "user" && commandDisclosure.checked
            height: visible ? technicalViewport.height + AppSizes.unit * 1.5 : 0
            color: EaStyle.Colors.contentBackground
            radius: AppSizes.unit * 0.75
            ScrollView {
                id: technicalViewport
                objectName: row.commandActivity ? "assistant.command.details" : "assistant.activity.details"
                x: AppSizes.unit
                y: AppSizes.unit * 0.75
                width: Math.max(0, parent.width - AppSizes.unit * 2)
                height: Math.min(technicalFields.implicitHeight, AppSizes.unit * 18)
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical: EaElements.ScrollBar { policy: ScrollBar.AsNeeded; interactive: false }
                contentItem: Flickable {
                    id: technicalContent
                    boundsBehavior: Flickable.StopAtBounds
                    flickableDirection: Flickable.VerticalFlick
                    contentWidth: width
                    contentHeight: technicalFields.implicitHeight
                    Column {
                        id: technicalFields
                        width: technicalContent.width
                        spacing: AppSizes.unit * 0.4
                        Column {
                            width: parent.width
                            visible: row.commandActivity
                            spacing: AppSizes.unit * 0.4
                            LiteralDetails {
                                width: parent.width
                                fieldName: qsTr("Retained command status")
                                text: technicalViewport.visible && row.commandActivity ? qsTr("Status: %1").arg(row.payload.status || qsTr("unavailable"))
                                    + (typeof row.payload.exitCode === "number" && Number.isInteger(row.payload.exitCode)
                                        ? qsTr(" · exit %1").arg(row.payload.exitCode) : "") : ""
                            }
                            EaElements.Label { text: qsTr("Command"); font.bold: true }
                            LiteralDetails {
                                id: commandText
                                objectName: "assistant.command.literal"
                                width: parent.width
                                fieldName: qsTr("Command")
                                text: technicalViewport.visible && row.commandActivity && typeof row.payload.command === "string" ? row.payload.command : ""
                            }
                            EaElements.Label { text: qsTr("Working directory"); font.bold: true }
                            LiteralDetails {
                                id: directoryText
                                width: parent.width
                                fieldName: qsTr("Working directory")
                                text: technicalViewport.visible && row.commandActivity && typeof row.payload.cwd === "string" ? row.payload.cwd : ""
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
                                text: technicalViewport.visible && row.commandActivity && typeof row.payload.aggregatedOutput === "string" ? row.payload.aggregatedOutput : ""
                            }
                        }
                        LiteralDetails {
                            id: activityText
                            width: parent.width
                            visible: !row.commandActivity && !(row.payload && row.payload.type === "dynamicToolCall" && row.text === "dynamicToolCall")
                            fieldName: qsTr("Activity")
                            text: visible && technicalViewport.visible ? row.text : ""
                        }
                        LiteralDetails {
                            id: decisionText
                            width: parent.width
                            visible: row.decisionActivity
                            fieldName: qsTr("Decision")
                            text: visible && technicalViewport.visible
                                ? qsTr("Decision: %1\nAction reference: %2").arg(row.payload.decision === "decline" ? qsTr("Declined") : row.payload.decision).arg(row.payload.item_id) : ""
                        }
                        LiteralDetails {
                            id: technicalText
                            width: parent.width
                            fieldName: qsTr("Retained item")
                            text: technicalViewport.visible ? JSON.stringify(row.payload, null, 2) : ""
                        }
                    }
                }
            }
        }
    }
}
