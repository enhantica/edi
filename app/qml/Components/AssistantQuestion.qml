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
        width: parent.width
        wrapMode: Text.Wrap
        text: card.assistant.pendingQuestion.text || ""
    }
    Repeater {
        model: card.assistant.pendingQuestion.options || []
        EaElements.Button {
            required property var modelData
            text: modelData.label
            highlighted: modelData.id === card.assistant.pendingQuestion.recommended
            onClicked: card.assistant.answerQuestion(card.assistant.pendingQuestion.question_id, modelData.id)
        }
    }
    EaElements.TextField {
        id: answer
        objectName: "assistant.question.answer"
        width: parent.width
        placeholderText: qsTr("Or write your answer")
        Accessible.name: placeholderText
        onAccepted: card.assistant.answerQuestion(card.assistant.pendingQuestion.question_id, text)
    }
}
