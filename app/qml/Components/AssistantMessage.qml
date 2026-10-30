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
        return ApplicationInfo.assistantMessageTableTone(lift);
    }
    property bool highlighted: false
    readonly property var compactPresentation: ApplicationInfo.assistantActivityPresentation(kind, status, payload, assistant)
    readonly property bool commandActivity: compactPresentation.commandActivity
    readonly property bool decisionActivity: compactPresentation.decisionActivity
    readonly property bool summarizedActivity: compactPresentation.summarizedActivity
    readonly property string disclosureIdentity: rowId + "\n" + (payload && typeof payload.id === "string" ? payload.id : "")
    property var humanDetailsSnapshot: null
    property bool technicalCopied: false
    property alias detailsDisclosure: commandDisclosure
    property alias detailsBody: body
    property alias detailsEditor: humanDetails
    property alias detailsFeedback: copyFeedback
    onPayloadChanged: ApplicationInfo.assistantMessageChanged(row, "payload")
    onTextChanged: ApplicationInfo.assistantMessageChanged(row, "text")
    onStatusChanged: ApplicationInfo.assistantMessageChanged(row, "status")
    Timer {
        id: copyFeedback
        interval: EaStyle.Times.introAnimation
        onTriggered: ApplicationInfo.assistantMessageClearFeedback(row, false)
    }
    signal detailsChanging
    signal reportRequested(string sourceRowId, string link)
    onDisclosureIdentityChanged: ApplicationInfo.assistantMessageReset(row)
    onCommandActivityChanged: ApplicationInfo.assistantMessageReset(row)
    onSummarizedActivityChanged: ApplicationInfo.assistantMessageReset(row)
    ListView.onPooled: ApplicationInfo.assistantMessageReset(row)
    ListView.onReused: ApplicationInfo.assistantMessageReset(row)
    color: "transparent"
    function sentFileLabel(file) {
        return ApplicationInfo.assistantSentFileLabel(file);
    }
    readonly property real widestSentFile: ApplicationInfo.assistantWidestSentFile()
    readonly property real historyCopyExtent: Math.ceil(historyCopyMetrics.height)
    readonly property real historyCopyGutter: kind === "user" ? historyCopyExtent + AppSizes.unit : 0
    implicitHeight: Math.max(content.implicitHeight + (kind === "user" ? AppSizes.unit * 1.5 : AppSizes.unit * 0.5), kind === "user" ? historyCopyExtent + AppSizes.unit * 1.5 : 0)
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
        readonly property bool overHistory: hovered && point.position.x >= bubble.x && point.position.x <= row.width && point.position.y >= 0 && point.position.y <= row.height
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
            color: !userCopy.enabled ? EaStyle.Colors.themeForegroundDisabled : userCopy.hovered || userCopy.down ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForegroundMinor
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            Accessible.ignored: true
        }
        ToolTip.text: row.technicalCopied ? qsTr("Copied") : qsTr("Copy sent message")
        Accessible.name: ToolTip.text
        onClicked: ApplicationInfo.assistantCopyUserText(row, userHistoryHover.overHistory || activeFocus)
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
            Keys.onPressed: event => ApplicationInfo.assistantMessageCopyKey(event)
            onLinkActivated: link => row.reportRequested(row.rowId, link)
            HoverHandler {
                cursorShape: body.hoveredLink.length > 0 ? Qt.PointingHandCursor : Qt.IBeamCursor
            }
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
                    id: sentFileChip
                    required property var modelData
                    objectName: "assistant.sentFile." + sentFileChip.modelData.id
                    width: sentFiles.width
                    spacing: AppSizes.unit * 0.125
                    EaElements.Label {
                        Layout.fillWidth: true
                        Layout.minimumWidth: 0
                        text: row.sentFileLabel(sentFileChip.modelData)
                        font: historyCopyMetrics.font
                        textFormat: Text.PlainText
                        elide: Text.ElideMiddle
                        color: EaStyle.Colors.themeForegroundMinor
                        Accessible.name: qsTr("Sent file snapshot: %1, %2").arg(sentFileChip.modelData.name).arg(ApplicationInfo.fileSizeKilobytes(sentFileChip.modelData.bytes))
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
                onCheckedChanged: ApplicationInfo.assistantMessageDisclosureChanged(row, checked)
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
                    color: !activityCopy.enabled ? EaStyle.Colors.themeForegroundDisabled : activityCopy.hovered || activityCopy.down ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForegroundMinor
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    Accessible.ignored: true
                }
                ToolTip.text: row.technicalCopied ? qsTr("Copied") : qsTr("Copy step")
                Accessible.name: ToolTip.text
                onClicked: ApplicationInfo.assistantCopyActivity(row, Preferences.assistantCopyTechnicalDetails, activityHeaderHover.hovered || activeFocus)
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
                text: visible ? ApplicationInfo.assistantActivityDescription(row.humanDetailsSnapshot, row.kind, row.compactPresentation, row.payload, row.assistant) : ""
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
