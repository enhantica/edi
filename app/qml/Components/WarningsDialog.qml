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
// base ListView, headerless and framed as Examples and Recent projects), over every message of the session's
// one list — the loader's warnings and the calculation's refusals — each marked by its kind (a warning's
// orange triangle; an error's red cross and red text), wrapped to as many lines as it needs, with its own
// dismiss button. Empty, it shows a muted icon and "No messages" in one row. Dismiss all sits in the dialog's
// button row beside OK. Opening the dialog marks the messages viewed, so the status bar's count stops being
// red.
AppDialog {
    id: dialog

    readonly property WarningListModel messages: Session.loadWarnings

    objectName: "warnings"
    title: qsTr("Messages")
    standardButtons: Dialog.Ok
    // The table's height fits its rows (the header is hidden, as Examples' and Recent projects'): at least one
    // one-line row, at most what keeps the dialog inside the window between the app bar and the status bar
    // less a margin at each, above which it scrolls. The width is fixed. The content is sized explicitly, as
    // AppPreferencesDialog's is: a ListView has no implicit size (edi ADR-0017 §14).
    readonly property real chromeHeight: implicitHeaderHeight + implicitFooterHeight + topPadding + bottomPadding + 2 * spacing
    readonly property real maximumListHeight: Math.max(EaStyle.Sizes.tableRowHeight, (parent ? parent.height : 0) - EaStyle.Sizes.appBarHeight - EaStyle.Sizes.statusBarHeight - 2 * EaStyle.Sizes.fontPixelSize - chromeHeight)

    contentWidth: listArea.width
    contentHeight: listArea.height

    onOpened: if (dialog.messages)
        dialog.messages.markViewed()

    footer: EaElements.DialogButtonBox {
        EaElements.Button {
            objectName: "warnings.dismissAll"
            enabled: dialog.messages !== null && dialog.messages.count > 0
            text: qsTr("Dismiss all")
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            onClicked: if (dialog.messages)
                dialog.messages.dismissAll()
        }
    }

    // The table, its empty state, and the table's frame drawn again above both, so rows and the empty state
    // never cover its edges.
    Item {
        id: listArea

        width: AppSizes.messagesDialogContentWidth
        height: Math.min(dialog.maximumListHeight, Math.max(table.tableRowHeight, table.contentHeight))

        DataTable {
            id: table

            objectName: "warnings.list"
            anchors.fill: parent
            clip: true
            defaultInfoText: ""
            sourceModel: dialog.messages

            columnWidths: [EaStyle.Sizes.tableRowHeight, -1, AppSizes.iconColumnWidth]

            header: EaComponents.ListViewHeader {
                visible: false
                implicitHeight: 0
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            delegate: EaComponents.ListViewDelegate {
                id: row

                required property int index
                required property string message
                required property string severity
                readonly property bool isError: severity === "error"

                height: Math.max(table.tableRowHeight, messageCell.implicitHeight + EaStyle.Sizes.fontPixelSize)

                IconCell {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `warnings.kind.${row.index}`
                    icon: row.isError ? "times-circle" : "exclamation-triangle"
                    iconColor: String(row.isError ? EaStyle.Colors.red : EaStyle.Colors.orange)
                    toolTip: row.isError ? qsTr("Error") : qsTr("Warning")
                }
                EaComponents.TableViewLabel {
                    id: messageCell
                    objectName: `warnings.message.${row.index}`
                    // Wrapping determines the row height, so its initial width must not depend on that height.
                    width: table.resolvedColumnWidths[1] ?? 0
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideNone
                    wrapMode: Text.Wrap
                    color: row.isError ? EaStyle.Colors.red : EaStyle.Colors.themeForeground
                    text: row.message
                }
                EaComponents.TableViewButton {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `warnings.dismiss.${row.index}`
                    anchors.verticalCenter: parent.verticalCenter
                    fontIcon: "minus-circle"
                    ToolTip.text: qsTr("Dismiss this message")
                    onClicked: if (dialog.messages)
                        dialog.messages.dismiss(row.index)
                }
            }
        }

        // Empty: a muted icon and "No messages" on one line in the middle of the one-row area.
        Rectangle {
            anchors.fill: parent
            visible: table.count === 0
            color: EaStyle.Colors.themeBackground

            Row {
                anchors.centerIn: parent
                spacing: EaStyle.Sizes.fontPixelSize * 0.5

                EaElements.Label {
                    anchors.verticalCenter: parent.verticalCenter
                    font.family: EaStyle.Fonts.iconsFamily
                    color: EaStyle.Colors.themeForegroundDisabled
                    text: "inbox"
                }
                EaElements.Label {
                    objectName: "warnings.empty"
                    anchors.verticalCenter: parent.verticalCenter
                    color: EaStyle.Colors.themeForegroundDisabled
                    text: qsTr("No messages")
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.color: EaStyle.Colors.appBarComboBoxBorder
        }
    }
}
