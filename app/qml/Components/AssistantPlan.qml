// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Elements as EaElements
import edi.app

Column {
    id: card
    required property AssistantViewModel assistant
    visible: Object.keys(assistant.pendingPlan).length > 0
    spacing: AppSizes.unit * 0.5
    EaElements.Label {
            textFormat: Text.PlainText
        width: parent.width
        wrapMode: Text.Wrap
        text: card.assistant.pendingPlan.summary || ""
    }
    EaElements.Label {
            textFormat: Text.PlainText
        width: parent.width
        wrapMode: Text.Wrap
        text: qsTr("Approve the listed parameter groups and budget. Each isolated trial fixes all other parameters; only the chosen group is free. The accepted project changes only after a converged comparable improvement.")
    }
    ScrollView {
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical: EaElements.ScrollBar {
            policy: ScrollBar.AsNeeded
            interactive: false
        }
        width: parent.width
        height: Math.min(details.implicitHeight, AppSizes.unit * 14)
        clip: true
        contentWidth: availableWidth
        EaElements.Label {
            id: details
            width: parent.width
            wrapMode: Text.WrapAnywhere
            textFormat: Text.PlainText
            text: ApplicationInfo.assistantPlanDescription()
        }
    }
    EaElements.Button {
        objectName: "assistant.plan.approve"
        text: qsTr("Approve plan")
        Accessible.name: text
        onClicked: card.assistant.approvePlan(card.assistant.pendingPlan.plan_id)
    }
}
