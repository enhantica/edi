// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

AppDialog {
    id: dialog
    required property AssistantViewModel assistant
    readonly property int selectedIndex: {
        for (let i = 0; i < assistant.skills.count; ++i)
            if (assistant.skills.text(i, "id") === assistant.selectedSkill) return i;
        return assistant.selectedSkill.length === 0 && assistant.skills.count > 0 ? Math.min(inspectedIndex, assistant.skills.count - 1) : -1;
    }
    readonly property real viewportHeight: Math.max(0, parent.height - AppSizes.unit * 2)
    title: qsTr("Edi skills")
    property int inspectedIndex: 0
    width: Math.min(AppSizes.unit * 44, Math.max(0, parent.width - AppSizes.unit * 2))
    height: Math.min(implicitHeight, viewportHeight)
    contentWidth: Math.max(0, width - leftPadding - rightPadding)
    contentHeight: Math.min(content.implicitHeight, Math.max(0, viewportHeight - topPadding - bottomPadding
        - (implicitHeaderHeight > 0 ? implicitHeaderHeight + spacing : 0)
        - (implicitFooterHeight > 0 ? implicitFooterHeight + spacing : 0)))
    standardButtons: Dialog.Close
    ScrollView {
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        id: scroll
        width: dialog.contentWidth
        height: dialog.contentHeight
        clip: true
        ScrollBar.vertical: EaElements.ScrollBar { policy: ScrollBar.AsNeeded; interactive: false }
        Column {
            id: content
            width: scroll.availableWidth
            spacing: AppSizes.unit
            EaElements.Label {
                width: parent.width
                wrapMode: Text.Wrap
                textFormat: Text.PlainText
                text: qsTr("The selected versioned guidance is included with the same current project context shown before sending. It cannot grant tools, approval or file access.")
            }
            Repeater {
                model: dialog.assistant.skills
                delegate: Column {
                    required property var model
                    required property int index
                    width: content.width
                    spacing: AppSizes.unit * 0.25
                    EaElements.Button {
                        width: parent.width
                        text: model.title + " · " + model.version
                        checkable: true
                        checked: dialog.assistant.selectedSkill.length === 0 ? index === dialog.selectedIndex : model.id === dialog.assistant.selectedSkill
                        enabled: dialog.assistant.selectedSkill.length === 0 || !dialog.assistant.canCancel
                        Accessible.name: text + (checked ? qsTr(" · selected") : "")
                        Accessible.checkable: checkable
                        Accessible.checked: checked
                        onClicked: { if (dialog.assistant.selectedSkill.length === 0) dialog.inspectedIndex = index; else dialog.assistant.selectSkill(model.id); }
                    }
                    EaElements.Label {
                        width: parent.width
                        text: model.summary + (model.available ? "" : "\n" + model.blocked_reason)
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                    }
                }
            }
            TextArea {
                objectName: "assistant.skillContent"
                width: parent.width
                text: dialog.selectedIndex < 0 ? qsTr("Workflow content is unavailable. Nothing will be sent.")
                    : dialog.assistant.skills.text(dialog.selectedIndex, "content")
                textFormat: TextEdit.PlainText
                readOnly: true
                selectByMouse: true
                persistentSelection: true
                selectionColor: EaStyle.Colors.themeAccent
                selectedTextColor: EaStyle.Colors.themeBackground
                wrapMode: TextEdit.WrapAnywhere
                Accessible.name: qsTr("Exact selected workflow content and published references")
            }
        }
    }
}
