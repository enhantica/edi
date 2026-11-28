// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

// The Account dialog's accounts, grouped by provider (edi ADR-0108 §9). Each account is listed once, in its
// provider's group, with its action beside it: the active one is marked and signs out, the others switch.
Column {
    id: list
    required property AssistantViewModel assistant
    // What the connected account reports about itself, shown on the active row only.
    property string activeEmail: ""
    property string activePlan: ""
    property string activeCredential: ""
    signal addRequested(string provider)
    signal signOutRequested
    spacing: AppSizes.unit * 1.5
    Repeater {
        model: list.assistant.providers
        delegate: Column {
            id: group
            required property var modelData
            readonly property var accounts: list.assistant.accounts.filter(account => account.provider === group.modelData.provider)
            objectName: "assistant.accounts." + modelData.provider
            width: list.width
            spacing: AppSizes.unit * 0.5
            EaElements.Label {
                width: parent.width
                text: group.modelData.name
                font.bold: true
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }
            Repeater {
                model: group.accounts
                delegate: RowLayout {
                    id: accountRow
                    required property var modelData
                    readonly property bool active: modelData.active
                    width: group.width
                    spacing: AppSizes.unit
                    EaElements.Label {
                        Layout.preferredWidth: AppSizes.unit
                        Layout.alignment: Qt.AlignTop
                        text: accountRow.active ? "check" : ""
                        font.family: EaStyle.Fonts.iconsFamily
                        Accessible.ignored: true
                    }
                    Column {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        EaElements.Label {
                            objectName: accountRow.active ? "assistant.accountIdentity" : ""
                            width: parent.width
                            // The pre-update ChatGPT sign-in has no id; its e-mail is known once it is read.
                            text: (accountRow.active && list.activeEmail) || accountRow.modelData.email || (accountRow.modelData.id === "" ? qsTr("Earlier ChatGPT sign-in") : qsTr("Account email unavailable"))
                            textFormat: Text.PlainText
                            wrapMode: Text.WrapAnywhere
                        }
                        EaElements.Label {
                            objectName: accountRow.active ? "assistant.accountPlan" : ""
                            width: parent.width
                            visible: text.length > 0
                            text: (accountRow.active && list.activePlan) || accountRow.modelData.plan || accountRow.modelData.host || ""
                            color: EaStyle.Colors.themeForegroundMinor
                            textFormat: Text.PlainText
                            wrapMode: Text.WrapAnywhere
                        }
                        EaElements.Label {
                            objectName: "assistant.accountCredential"
                            width: parent.width
                            visible: accountRow.active && text.length > 0
                            text: accountRow.active ? list.activeCredential : ""
                            color: EaStyle.Colors.themeForegroundMinor
                            textFormat: Text.PlainText
                            wrapMode: Text.WordWrap
                        }
                    }
                    EaElements.Button {
                        objectName: accountRow.active ? "assistant.signOut" : "assistant.switchAccount"
                        Layout.alignment: Qt.AlignVCenter
                        padding: EaStyle.Sizes.fontPixelSize * 0.5
                        enabled: accountRow.active ? list.assistant.connected : accountRow.modelData.installed
                        fontIcon: accountRow.active ? "sign-out-alt" : "exchange-alt"
                        // Copilot's sign-out is not yet qualified, so the account is removed from edi instead.
                        text: !accountRow.active ? qsTr("Switch") : accountRow.modelData.provider === "copilot" ? qsTr("Remove from edi") : qsTr("Sign out")
                        Accessible.name: text
                        onClicked: accountRow.active ? list.signOutRequested() : list.assistant.switchAccount(accountRow.modelData.provider, accountRow.modelData.id)
                    }
                }
            }
            EaElements.Button {
                objectName: "assistant.addAccount." + group.modelData.provider
                padding: EaStyle.Sizes.fontPixelSize * 0.5
                enabled: group.modelData.installed
                fontIcon: "plus-circle"
                text: qsTr("Add account")
                Accessible.name: text
                ToolTip.visible: hovered && !enabled
                // A provider this release does not offer has no Maintenance Tool route to point at.
                ToolTip.text: group.modelData.distributed ? qsTr("Add %1 with the Maintenance Tool first.").arg(group.modelData.name) : qsTr("Not included in this release.")
                onClicked: list.addRequested(group.modelData.provider)
            }
        }
    }
}
