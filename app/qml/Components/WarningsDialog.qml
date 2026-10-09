// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The messages, opened from the status bar's messages item (edi ADR-0017 §14): the same dialog as About and
// Preferences, of a fixed width, as tall as its rows need within the window. Its list is a sidebar table (the
// base TableView, headerless and framed as Examples and Recent projects), over every message of the session's
// one list — the loader's warnings and the calculation's refusals — each marked by its kind (a warning's
// orange triangle; an error's red cross and red text), wrapped to as many lines as it needs, with its own
// dismiss button. Empty, it shows a muted icon and "No messages" in one row. Dismiss all sits in the dialog's
// button row beside OK. Opening the dialog marks the messages viewed, so the status bar's count stops being
// red.
AppDialog {
    id: dialog

    // The table's height fits its rows (the header is hidden, as Examples' and Recent projects'): at least one
    // one-line row, at most what keeps the dialog inside the window between the app bar and the status bar
    // less a margin at each, above which it scrolls. The width is fixed. The content is sized explicitly, as
    // AppPreferencesDialog's is: a ListView has no implicit size (edi ADR-0017 §14).
    readonly property real chromeHeight: implicitHeaderHeight + implicitFooterHeight + topPadding + bottomPadding + 2 * spacing
    readonly property real maximumListHeight: Math.max(EaStyle.Sizes.tableRowHeight, (parent ? parent.height : 0) - EaStyle.Sizes.appBarHeight - EaStyle.Sizes.statusBarHeight - 2 * EaStyle.Sizes.fontPixelSize - chromeHeight)
    readonly property WarningListModel messages: Session.loadWarnings

    contentHeight: listArea.height
    contentWidth: listArea.width
    objectName: "warnings"
    standardButtons: Dialog.Ok
    title: qsTr("Messages")

    footer: EaElements.DialogButtonBox {
        EaElements.Button {
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            enabled: dialog.messages !== null && dialog.messages.count > 0
            objectName: "warnings.dismissAll"
            text: qsTr("Dismiss all")

            onClicked: if (dialog.messages)
                dialog.messages.dismissAll()
        }
    }

    onOpened: if (dialog.messages)
        dialog.messages.markViewed()

    // The table, its empty state, and the table's frame drawn again above both, so rows and the empty state
    // never cover its edges.
    Item {
        id: listArea

        height: Math.min(dialog.maximumListHeight, Math.max(table.tableRowHeight, table.contentHeight))
        width: AppSizes.messagesDialogContentWidth

        DataTable {
            id: table

            anchors.fill: parent
            clip: true
            columnWidths: [EaStyle.Sizes.tableRowHeight, -1, AppSizes.iconColumnWidth]
            defaultInfoText: ""
            model: dialog.messages
            objectName: "warnings.list"

            delegate: EaComponents.ListViewDelegate {
                id: row

                required property int index
                readonly property bool isError: severity === "error"
                required property string message
                required property string severity

                height: Math.max(table.tableRowHeight, messageCell.implicitHeight + EaStyle.Sizes.fontPixelSize)

                IconCell {
                    icon: row.isError ? "times-circle" : "exclamation-triangle"
                    iconColor: String(row.isError ? EaStyle.Colors.red : EaStyle.Colors.orange)
                    objectName: `warnings.kind.${row.index}`
                    toolTip: row.isError ? qsTr("Error") : qsTr("Warning")
                }
                EaComponents.TableViewLabel {
                    id: messageCell

                    color: row.isError ? EaStyle.Colors.red : EaStyle.Colors.themeForeground
                    elide: Text.ElideNone
                    horizontalAlignment: Text.AlignLeft
                    objectName: `warnings.message.${row.index}`
                    text: row.message
                    wrapMode: Text.Wrap
                }
                EaComponents.TableViewButton {
                    ToolTip.text: qsTr("Dismiss this message")
                    anchors.verticalCenter: parent.verticalCenter
                    fontIcon: "minus-circle"
                    objectName: `warnings.dismiss.${row.index}`

                    onClicked: if (dialog.messages)
                        dialog.messages.dismiss(row.index)
                }
            }
            header: EaComponents.ListViewHeader {
                implicitHeight: 0
                visible: false

                EaComponents.TableViewLabel {
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.TableViewLabel {
                }
            }
        }

        // Empty: a muted icon and "No messages" on one line in the middle of the one-row area.
        Rectangle {
            anchors.fill: parent
            color: EaStyle.Colors.themeBackground
            visible: table.count === 0

            Row {
                anchors.centerIn: parent
                spacing: EaStyle.Sizes.fontPixelSize * 0.5

                EaElements.Label {
                    anchors.verticalCenter: parent.verticalCenter
                    color: EaStyle.Colors.themeForegroundDisabled
                    font.family: EaStyle.Fonts.iconsFamily
                    text: "inbox"
                }
                EaElements.Label {
                    anchors.verticalCenter: parent.verticalCenter
                    color: EaStyle.Colors.themeForegroundDisabled
                    objectName: "warnings.empty"
                    text: qsTr("No messages")
                }
            }
        }
        Rectangle {
            anchors.fill: parent
            border.color: EaStyle.Colors.appBarComboBoxBorder
            color: "transparent"
        }
    }
}
