// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import EasyApplication.Gui.Elements as EaElements
import edi.app

Column {
    id: card
    required property AssistantViewModel assistant
    visible: Object.keys(assistant.pendingQuestion).length > 0
    spacing: AppSizes.unit * 0.5
    EaElements.Label {
        textFormat: Text.PlainText
        width: parent.width
        wrapMode: Text.Wrap
        text: card.assistant.pendingQuestion.text || ""
    }
    Repeater {
        model: card.assistant.pendingQuestion.options || []
        Column {
            id: optionRow
            required property var modelData
            width: card.width
            EaElements.Button {
                id: optionButton
                width: parent.width
                contentItem: EaElements.Label {
                    text: optionButton.text
                    textFormat: Text.PlainText
                    font: optionButton.font
                    color: optionButton.foregroundColor()
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignLeft
                }
                text: optionRow.modelData.label
                highlighted: optionRow.modelData.id === card.assistant.pendingQuestion.recommended
                onClicked: card.assistant.answerQuestion(card.assistant.pendingQuestion.question_id, optionRow.modelData.id)
            }
            EaElements.Label {
                width: parent.width
                text: optionRow.modelData.description
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
            }
        }
    }
    EaElements.TextField {
        id: answer
        visible: card.assistant.pendingQuestion.allow_free_text === true
        objectName: "assistant.question.answer"
        text: card.assistant.pendingQuestion.draftText || ""
        width: parent.width
        placeholderText: qsTr("Or write your answer")
        Accessible.name: placeholderText
        onAccepted: card.assistant.answerQuestion(card.assistant.pendingQuestion.question_id, text)
    }
}
