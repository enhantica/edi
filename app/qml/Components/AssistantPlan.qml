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
            text: {
                const plan = card.assistant.pendingPlan;
                if (!plan.budget)
                    return "";
                const groups = (plan.groups || []).map(group => group.id + ": " + group.paths.join(", ")).join("\n");
                return groups + "\n" + qsTr("Budget: %1 trials, %2 iterations, %3 seconds").arg(plan.budget.max_trials).arg(plan.budget.max_iterations).arg(plan.budget.max_elapsed_ms / 1000) + "\n" + qsTr("Improvement tolerance: absolute %1, relative %2").arg(plan.objective.absolute_tolerance).arg(plan.objective.relative_tolerance);
            }
        }
    }
    EaElements.Button {
        objectName: "assistant.plan.approve"
        text: qsTr("Approve plan")
        Accessible.name: text
        onClicked: card.assistant.approvePlan(card.assistant.pendingPlan.plan_id)
    }
}
