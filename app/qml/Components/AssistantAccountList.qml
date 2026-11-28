// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

// The Account dialog's accounts, grouped by provider (edi ADR-0108 §9). Each group has the provider's name, one row
// per recorded account (the active one checked) and Add account; the elements copy the dialog's own label and
// sign-out button.
Column {
    id: list
    required property AssistantViewModel assistant
    signal addRequested(string provider)
    spacing: AppSizes.unit
    component IconButton: EaElements.Button {
        id: iconButton
        contentItem: Row {
            spacing: AppSizes.unit * 0.5
            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                text: iconButton.fontIcon
                font.family: EaStyle.Fonts.iconsFamily
                color: iconButton.foregroundColor()
            }
            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                text: iconButton.text
                color: iconButton.foregroundColor()
            }
        }
        Accessible.name: text
    }
    Repeater {
        model: list.assistant.providers
        delegate: Column {
            id: group
            required property var modelData
            readonly property var accounts: list.assistant.accounts.filter(account => account.provider === group.modelData.provider)
            objectName: "assistant.accounts." + modelData.provider
            width: list.width
            spacing: AppSizes.unit * 0.25
            EaElements.Label {
                width: parent.width
                text: group.modelData.name
                font.bold: true
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }
            Repeater {
                model: group.accounts
                delegate: Row {
                    id: accountRow
                    required property var modelData
                    width: group.width
                    spacing: AppSizes.unit * 0.5
                    EaElements.Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: accountRow.modelData.active ? "check" : ""
                        font.family: EaStyle.Fonts.iconsFamily
                        width: AppSizes.unit
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, accountRow.width - AppSizes.unit * 1.5 - switchButton.width)
                        EaElements.Label {
                            width: parent.width
                            text: accountRow.modelData.email || qsTr("Account email unavailable")
                            textFormat: Text.PlainText
                            wrapMode: Text.WrapAnywhere
                        }
                        EaElements.Label {
                            width: parent.width
                            visible: text.length > 0
                            text: accountRow.modelData.plan || accountRow.modelData.host || ""
                            color: EaStyle.Colors.themeForegroundMinor
                            textFormat: Text.PlainText
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                    IconButton {
                        id: switchButton
                        objectName: "assistant.switchAccount"
                        anchors.verticalCenter: parent.verticalCenter
                        visible: !accountRow.modelData.active
                        enabled: accountRow.modelData.installed
                        fontIcon: "exchange-alt"
                        text: qsTr("Switch")
                        onClicked: list.assistant.switchAccount(accountRow.modelData.provider, accountRow.modelData.id)
                    }
                }
            }
            IconButton {
                objectName: "assistant.addAccount." + group.modelData.provider
                enabled: group.modelData.installed
                fontIcon: "plus-circle"
                text: qsTr("Add account")
                ToolTip.visible: hovered && !enabled
                // A provider this release does not offer has no Maintenance Tool route to point at.
                ToolTip.text: group.modelData.distributed ? qsTr("Add %1 with the Maintenance Tool first.").arg(group.modelData.name) : qsTr("Not included in this release.")
                onClicked: list.addRequested(group.modelData.provider)
            }
        }
    }
}
