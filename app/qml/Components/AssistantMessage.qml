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
    readonly property var inputFiles: ApplicationInfo.assistantHistoryInputFiles(kind, payload)
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
    readonly property var compactPresentation: ApplicationInfo.assistantActivityPresentation(kind, status, payload, assistant)
    readonly property bool commandActivity: compactPresentation.commandActivity
    readonly property bool decisionActivity: compactPresentation.decisionActivity
    readonly property bool summarizedActivity: compactPresentation.summarizedActivity
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
        const short = compactPresentation.caption;
        const description = activityDescription(true, payload);
        if (description.trim().length && ApplicationInfo.assistantSingleLineText(description) !== short) add(description);
        // Only established human producers use row.text as a description.
        // Generic/command activity text may contain shell or protocol bytes.
        const humanRow = ["error", "plan", "question", "tool", "trial"].indexOf(kind) >= 0
            || (decisionActivity && typeof payload.type === "undefined");
        if (humanRow && ApplicationInfo.assistantSingleLineText(text) !== short) add(text);
        if (!lines.some(line => ApplicationInfo.assistantSingleLineText(line).length > short.length)) {
            if (payload && payload.type === "dynamicToolCall" && assistant)
                add(assistant.nativeActionDescription(typeof payload.tool === "string" ? payload.tool : "", ""));
            else if (payload && payload.type === "webSearch") add(qsTr("Find or read public sources relevant to the current task."));
            else if (commandActivity) add(qsTr("Use the reported operation to support the current task."));
            else add(qsTr("Carry out the requested assistant action for the current task."));
        }
        add(detail.provenance);
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
        const short = compactPresentation.caption, full = fullHumanDescription(detail);
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
    function activityDescription(full, source) {
        const payload = source || row.payload;
        if (!payload || typeof payload !== "object") return "";
        const supplied = typeof payload.purpose === "string" ? payload.purpose
                       : typeof payload.description === "string" ? payload.description
                       : payload.arguments && typeof payload.arguments.purpose === "string" ? payload.arguments.purpose : "";
        if (payload.type === "dynamicToolCall" && (supplied === "Edi native action"
                || supplied === "Edi native action: " + payload.tool)) return ApplicationInfo.assistantNativeActivityCaption(row.payload, row.assistant);
        if (supplied.trim().length) return full ? supplied : ApplicationInfo.assistantSingleLineText(supplied);
        if (payload.type === "webSearch") return ApplicationInfo.assistantWebSearchCaption(payload);
        if (!commandActivity) return "";
        return typeof payload.commandDescription === "string" ? payload.commandDescription : "";
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
                id: markdownPresentation
                anchors.fill: parent
                document: body.textDocument
                editor: body
                source: row.summarizedActivity ? "" : row.text
                textColor: body.color
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
            Keys.onPressed: event => {
                if(event.matches(StandardKey.Copy) && body.selectionStart!==body.selectionEnd) {
                    ApplicationInfo.copyText(markdownPresentation.selectedSource(body.selectionStart,body.selectionEnd));event.accepted=true;
                }
            }
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
                text: row.compactPresentation.caption
                contentItem: RowLayout {
                    spacing: AppSizes.unit * 0.5
                    EaElements.Label {
                        text: row.compactPresentation.state === "in_progress" ? "hourglass-half" : FitOutcomes.icon(row.compactPresentation.outcomeKey)
                        Layout.preferredWidth: AppSizes.unit
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75
                        font.family: EaStyle.Fonts.iconsFamily
                        color: row.compactPresentation.state === "in_progress" ? EaStyle.Colors.themeAccent : FitOutcomes.color(row.compactPresentation.outcomeKey)
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
                ToolTip.text: row.compactPresentation.explanation + " · " + text
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
