// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

Rectangle {
    id: row
    required property string kind
    required property string text
    property var payload: ({})
    property string status: ""
    property string rowId: ""
    property bool highlighted: false
    readonly property bool commandActivity: kind === "activity" && payload && payload.type === "commandExecution"
    readonly property string disclosureIdentity: rowId + "\n" + (payload && typeof payload.id === "string" ? payload.id : "")
    signal detailsChanging()
    function resetDetails() {
        if (commandDisclosure) commandDisclosure.checked = false;
        if (disclosure) disclosure.checked = false;
        for (const viewport of [commandViewport, technicalViewport])
            if (viewport && viewport.contentItem && viewport.contentItem.contentY !== undefined)
                viewport.contentItem.contentY = 0;
        for (const field of [body, commandText, directoryText, outputText, technicalText])
            if (field) field.deselect();
    }
    onDisclosureIdentityChanged: resetDetails()
    onCommandActivityChanged: resetDetails()
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
                return qsTr("Running command");
            let unconfirmed = qsTr("Command outcome unconfirmed");
            if (row.status === "interrupted") unconfirmed += qsTr(" · activity interrupted");
            else if (row.status === "failed") unconfirmed += qsTr(" · activity failed");
            else if (row.status === "completed") unconfirmed += qsTr(" · activity completed");
            else if (row.status === "refused" || row.status === "declined") unconfirmed += qsTr(" · activity refused");
            return unconfirmed;
        }
        let caption = actual === "completed" ? qsTr("Ran command · completed")
                    : actual === "failed" ? qsTr("Command failed")
                    : actual === "declined" ? qsTr("Command declined")
                    : qsTr("Command interrupted");
        if (payload && typeof payload.exitCode === "number" && Number.isFinite(payload.exitCode) && Number.isInteger(payload.exitCode))
            caption = qsTr("%1 · exit %2").arg(caption).arg(payload.exitCode);
        return caption;
    }
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
            visible: row.kind !== "user" && row.kind !== "assistant" && !row.commandActivity
            text: qsTr("Activity")
            font.bold: true
        }
        EaElements.Label {
            visible: row.kind !== "user" && row.kind !== "assistant" && !row.commandActivity && row.status.length > 0
            text: row.status
            textFormat: Text.PlainText
        }
        TextEdit {
            id: body
            width: parent.width
            visible: !row.commandActivity
            AssistantMarkdown {
                document: body.textDocument
                source: row.commandActivity ? "" : row.text
                markdown: row.kind === "assistant"
            }
            readOnly: true
            selectByMouse: true
            persistentSelection: true
            selectionColor: EaStyle.Colors.themeAccent
            selectedTextColor: EaStyle.Colors.themeBackground
            textFormat: TextEdit.PlainText
            onLinkActivated: link => {}
            wrapMode: TextEdit.Wrap
            color: EaStyle.Colors.themeForeground
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            Accessible.role: Accessible.StaticText
            Accessible.ignored: !visible
            Accessible.name: visible ? (row.kind === "user" ? qsTr("You") : row.kind === "assistant" ? qsTr("Assistant") : qsTr("Activity")) + ": " + row.text : ""
        }
        EaElements.Button {
            id: commandDisclosure
            objectName: "assistant.command.toggle"
            visible: row.commandActivity
            checkable: true
            text: row.commandCaption()
            Accessible.name: text
            Accessible.description: checked ? qsTr("Hide the literal command and its available output") : qsTr("Show the literal command and its available output")
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
        EaElements.Button {
            id: disclosure
            visible: row.kind !== "assistant" && row.kind !== "user" && Object.keys(row.payload || {}).length > 0 && (!row.commandActivity || commandDisclosure.checked)
            checkable: true
            text: row.commandActivity ? qsTr("Technical details") : checked ? qsTr("Hide details") : qsTr("Inspect details")
            onPressed: row.detailsChanging()
        }
        ScrollView {
            id: technicalViewport
            width: parent.width
            visible: disclosure.visible && disclosure.checked
            height: visible ? Math.min(technicalText.implicitHeight, AppSizes.unit * 18) : 0
            contentWidth: availableWidth
            contentHeight: technicalText.implicitHeight
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical: EaElements.ScrollBar { policy: ScrollBar.AsNeeded; interactive: false }
            LiteralDetails {
                id: technicalText
                width: technicalViewport.availableWidth
                fieldName: qsTr("Technical details")
                text: technicalViewport.visible ? JSON.stringify(row.payload, null, 2) : ""
            }
        }
    }
}
