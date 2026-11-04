// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Templates as T
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

// The assistant's pending question: its text is the conversation row just above, so the card holds only the answers.
// Each choice is a numbered box framed like the answer field below it; a click, Enter or Space sends it.
Column {
    id: card
    required property AssistantViewModel assistant
    visible: assistant.pendingQuestion.question_id !== ""
    spacing: AppSizes.unit * 0.5
    Repeater {
        model: card.assistant.pendingQuestion.options || []
        T.AbstractButton {
            id: choice
            required property var modelData
            required property int index
            readonly property bool lit: hovered || visualFocus
            objectName: "assistant.question.option." + index
            width: card.width
            implicitHeight: implicitContentHeight + topPadding + bottomPadding
            padding: EaStyle.Sizes.fontPixelSize * 0.5 + 1
            hoverEnabled: true
            focusPolicy: Qt.StrongFocus
            Accessible.role: Accessible.Button
            Accessible.name: (index + 1) + ". " + modelData.label
            Accessible.description: modelData.description
            Keys.onReturnPressed: clicked()
            Keys.onEnterPressed: clicked()
            onClicked: card.assistant.answerQuestion(card.assistant.pendingQuestion.question_id, modelData.id)
            HoverHandler {
                cursorShape: Qt.PointingHandCursor
            }
            contentItem: Column {
                spacing: AppSizes.unit * 0.25
                EaElements.Label {
                    id: choiceText
                    width: parent.width
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    font.bold: true
                    color: choice.lit ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
                    text: (choice.index + 1) + ".  " + choice.modelData.label
                }
                EaElements.Label {
                    width: parent.width
                    visible: text !== ""
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: choice.lit ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForegroundMinor
                    text: choice.modelData.description
                }
            }
            background: Rectangle {
                color: choice.lit ? EaStyle.Colors.appBarComboBoxBackgroundHovered : EaStyle.Colors.appBarComboBoxBackground
                border.color: choice.lit ? EaStyle.Colors.themeForegroundHovered : choice.modelData.id === card.assistant.pendingQuestion.recommended ? EaStyle.Colors.themeAccent : EaStyle.Colors.appBarComboBoxBorder
            }
        }
    }
    EaElements.TextField {
        id: answer
        visible: card.assistant.pendingQuestion.allow_free_text === true
        objectName: "assistant.question.answer"
        text: card.assistant.pendingQuestion.draftText || ""
        width: parent.width
        horizontalAlignment: TextInput.AlignLeft
        placeholderText: qsTr("Or write your answer")
        Accessible.name: placeholderText
        onAccepted: card.assistant.answerQuestion(card.assistant.pendingQuestion.question_id, text)
    }
}
