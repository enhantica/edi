// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

// The Account dialog's accounts (edi ADR-0108 §9): the active account on a light panel with its sign-out, every other
// signed-in account under "Switch to", then one Add account row naming the installed providers.
Column {
    id: list
    required property AssistantViewModel assistant
    // What the connected account reports about itself, shown on the active panel.
    property string activeEmail: ""
    property string activePlan: ""
    property string activeUsage: ""
    property string activeCredential: ""
    signal addRequested
    signal signOutRequested
    readonly property var activeAccount: assistant.accounts.find(account => account.active) ?? null
    readonly property var otherAccounts: assistant.accounts.filter(account => !account.active)
    readonly property var installedProviders: assistant.providers.filter(entry => entry.installed)
    // The leading icon's slot, shared by the Switch to rows and Add account.
    readonly property real iconWidth: EaStyle.Sizes.fontPixelSize * 1.5
    // "<Provider> <Plan>", as the provider names its plans ("ChatGPT Plus", "Claude Max").
    function planLabel(provider, plan) {
        if (!plan)
            return "";
        const words = plan.split(/[_ -]+/).filter(word => word.length > 0).map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
        const brand = provider === "chatgpt" ? "ChatGPT" : provider === "claude" ? "Claude" : "";
        return brand && !words.startsWith(brand) ? brand + " " + words : words;
    }
    // The pre-update ChatGPT sign-in is named by the e-mail its saved conversations carry; without one, by what it is.
    function emailLabel(account) {
        return account.email || (account.provider === "chatgpt" ? qsTr("Earlier ChatGPT sign-in") : account.host || qsTr("Account email unavailable"));
    }
    spacing: AppSizes.unit
    Rectangle {
        objectName: "assistant.activeAccount"
        width: list.width
        visible: list.activeAccount !== null
        height: activeRow.implicitHeight + AppSizes.unit * 1.5
        radius: EaStyle.Sizes.fontPixelSize * 0.25
        color: EaStyle.Colors.themeRowHovered
        RowLayout {
            id: activeRow
            x: AppSizes.unit
            width: parent.width - AppSizes.unit * 1.5
            anchors.verticalCenter: parent.verticalCenter
            spacing: AppSizes.unit
            Column {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                Row {
                    width: parent.width
                    EaElements.Label {
                        id: activeProviderName
                        text: list.activeAccount ? list.activeAccount.providerName + " · " : ""
                        font.bold: true
                        textFormat: Text.PlainText
                    }
                    EaElements.Label {
                        objectName: "assistant.accountIdentity"
                        width: Math.max(0, parent.width - activeProviderName.width)
                        text: list.activeAccount ? list.activeEmail || list.emailLabel(list.activeAccount) : ""
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                    }
                }
                EaElements.Label {
                    objectName: "assistant.accountPlan"
                    width: parent.width
                    visible: text.length > 0
                    text: list.activeAccount ? [list.planLabel(list.activeAccount.provider, list.activePlan || list.activeAccount.plan) || list.activeAccount.host, list.activeUsage].filter(part => part).join(" · ") : ""
                    color: EaStyle.Colors.themeForegroundMinor
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
                EaElements.Label {
                    objectName: "assistant.accountCredential"
                    width: parent.width
                    visible: text.length > 0
                    text: list.activeCredential
                    color: EaStyle.Colors.themeForegroundMinor
                    textFormat: Text.PlainText
                    wrapMode: Text.WordWrap
                }
            }
            EaElements.Button {
                objectName: "assistant.signOut"
                Layout.alignment: Qt.AlignVCenter
                padding: EaStyle.Sizes.fontPixelSize * 0.5
                enabled: list.assistant.connected
                fontIcon: "sign-out-alt"
                // Copilot's sign-out is not yet qualified, so the account is removed from edi instead.
                text: list.activeAccount && list.activeAccount.provider === "copilot" ? qsTr("Remove from edi") : qsTr("Sign out")
                Accessible.name: text
                onClicked: list.signOutRequested()
            }
        }
    }
    EaElements.Label {
        width: list.width
        visible: list.otherAccounts.length > 0
        text: qsTr("Switch to")
        font.bold: true
        textFormat: Text.PlainText
    }
    Repeater {
        model: list.otherAccounts
        delegate: AbstractButton {
            id: switchRow
            required property var modelData
            objectName: "assistant.switchAccount"
            width: list.width
            enabled: modelData.installed
            hoverEnabled: true
            padding: AppSizes.unit * 0.25
            Accessible.role: Accessible.Button
            Accessible.name: qsTr("Switch to %1, %2").arg(modelData.providerName).arg(list.emailLabel(modelData))
            ToolTip.visible: hovered && !enabled
            ToolTip.text: qsTr("%1 is not installed.").arg(modelData.providerName)
            background: Rectangle {
                radius: EaStyle.Sizes.fontPixelSize * 0.25
                color: switchRow.hovered || switchRow.visualFocus ? EaStyle.Colors.themeRowHovered : "transparent"
            }
            contentItem: RowLayout {
                spacing: 0
                EaElements.Label {
                    Layout.preferredWidth: list.iconWidth
                    Layout.alignment: Qt.AlignVCenter
                    text: "exchange-alt"
                    font.family: EaStyle.Fonts.iconsFamily
                    color: switchRow.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
                    Accessible.ignored: true
                }
                Column {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    EaElements.Label {
                        width: parent.width
                        text: switchRow.modelData.providerName + " · " + list.emailLabel(switchRow.modelData)
                        color: switchRow.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                    }
                    EaElements.Label {
                        width: parent.width
                        visible: text.length > 0
                        text: list.planLabel(switchRow.modelData.provider, switchRow.modelData.plan) || (switchRow.modelData.email ? switchRow.modelData.host : "")
                        color: EaStyle.Colors.themeForegroundMinor
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                    }
                }
            }
            onClicked: list.assistant.switchAccount(modelData.provider, modelData.id)
        }
    }
    Rectangle {
        width: list.width
        height: 1
        color: EaStyle.Colors.appBorder
    }
    AbstractButton {
        id: addRow
        objectName: "assistant.addAccount"
        width: list.width
        enabled: list.installedProviders.length > 0
        hoverEnabled: true
        padding: AppSizes.unit * 0.25
        Accessible.role: Accessible.Button
        Accessible.name: qsTr("Add account")
        background: Rectangle {
            radius: EaStyle.Sizes.fontPixelSize * 0.25
            color: addRow.hovered || addRow.visualFocus ? EaStyle.Colors.themeRowHovered : "transparent"
        }
        contentItem: RowLayout {
            spacing: 0
            EaElements.Label {
                Layout.preferredWidth: list.iconWidth
                Layout.alignment: Qt.AlignVCenter
                text: "plus-circle"
                font.family: EaStyle.Fonts.iconsFamily
                Accessible.ignored: true
            }
            EaElements.Label {
                Layout.alignment: Qt.AlignVCenter
                text: qsTr("Add account")
                textFormat: Text.PlainText
            }
            // The providers an account can be added for: the installed ones.
            EaElements.Label {
                Layout.fillWidth: true
                Layout.leftMargin: AppSizes.unit * 0.75
                Layout.alignment: Qt.AlignVCenter
                text: list.installedProviders.map(entry => entry.name).join(", ")
                color: EaStyle.Colors.themeForegroundMinor
                textFormat: Text.PlainText
                elide: Text.ElideRight
            }
        }
        onClicked: list.addRequested()
    }
}
