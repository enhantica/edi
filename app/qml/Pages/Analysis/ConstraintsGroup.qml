// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// Confirmed disabled rows retain participation; provisional rows are unsaved Drafts (ADR-0024).
Column {
    id: group

    objectName: "relations.constraints"
    property AnalysisViewModel analysis: null
    readonly property ConstraintListModel constraints: analysis ? analysis.constraints : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "constraints.list"
        defaultInfoText: qsTr("No constraints")
        sourceModel: group.constraints

        columnWidths: [numberColumnWidth, EaStyle.Sizes.fontPixelSize * 7, -1, AppSizes.iconColumnWidth, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("id")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("expression")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int index
            // The roles by the model: `id` cannot be a property name.
            required property var model

            function focusDraft(token: string) {
                if (row.model.draft && row.model.draftToken === token)
                    idCell.forceActiveFocus();
            }

            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                editMember: row
                editModel: group.constraints
                id: idCell
                editIndex: row.index
                editIdentity: row.model.draftToken
                objectName: `constraint.id.${row.index}`
                horizontalAlignment: Text.AlignLeft
                color: row.model.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundMinor
                value: row.model.id
                onCommitted: text => group.constraints.setText(row.index, "id", text)
            }
            TextCell {
                editMember: row
                editModel: group.constraints
                editIndex: row.index
                editIdentity: row.model.draftToken
                objectName: `constraint.expression.${row.index}`
                horizontalAlignment: Text.AlignLeft
                color: row.model.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundMinor
                value: row.model.expression
                onCommitted: text => group.constraints.setText(row.index, "expression", text)
            }
            EaComponents.TableViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `constraint.enabled.${row.index}`
                fontIcon: row.model.draft ? "check" : row.model.enabled ? "toggle-on" : "toggle-off"
                ToolTip.text: row.model.draft ? qsTr("Draft — not saved. Confirm this constraint") + (group.constraints.lastError ? ": " + group.constraints.lastError : "") : row.model.enabled ? qsTr("Disable this constraint") : qsTr("Enable this constraint")
                onClicked: {
                    if (row.model.draft)
                        group.constraints.commitDraft(row.model.draftToken);
                    else
                        group.constraints.setEnabled(row.index, !row.model.enabled);
                }
            }
            EaComponents.TableViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `constraint.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this constraint")
                onClicked: group.constraints.remove(row.index)
            }
        }
    }

    Connections {
        target: group.constraints
        function onFocusDraftRequested(token: string) {
            const model = group.constraints;
            if (!model)
                return;
            for (let index = 0; index < model.count; ++index) {
                if (model.text(index, "draftToken") !== token)
                    continue;
                if (!table.revealRow(index) || group.constraints !== model)
                    return;
                const item = table.itemAtIndex(index);
                if (item && typeof item.focusDraft === "function" && model.text(index, "draftToken") === token)
                    item.focusDraft(token);
                return;
            }
        }
    }

    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "constraints.append"
            fontIcon: "plus-circle"
            text: qsTr("Append new constraint")
            onClicked: group.constraints.append()
        }
        EaElements.SideBarButton {
            objectName: "constraints.duplicate"
            enabled: table.currentIndex >= 0 || (group.constraints && group.constraints.count > 0)
            fontIcon: "clone"
            text: qsTr("Duplicate selected constraint")
            onClicked: group.constraints.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
