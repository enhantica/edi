// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Style as EaStyle
import edi.app

// Staging is presentation only. The existing complete relation validator and
// recorded editor see this batch exactly once, on the ordinary Apply button.
EaElements.GroupBox {
    id: group
    property ProjectViewModel project: null
    property string assistantStage: ""
    property bool manualDraft: false
    property string outcome: ""
    property bool loading: false
    property int revision: 0
    readonly property bool assistantManualDraft: manualDraft
    readonly property int aliasCount: aliases.count
    readonly property int constraintCount: constraints.count
    readonly property bool constraintsSelected: sections.currentIndex === 1
    readonly property int selectedRow: rows.currentIndex
    readonly property var selectedModel: constraintsSelected ? constraints : aliases
    objectName: "relations.stage"
    title: qsTr("Append relation batch")
    collapsible: false
    enabled: project !== null && !project.fit.running && !project.calculating
    ListModel { id: aliases }
    ListModel { id: constraints }
    function reset() {
        ++revision;
        loading = true;
        aliases.clear(); constraints.clear(); rows.currentIndex = -1;
        identity.text = ""; definition.text = ""; enabledRule.checked = true;
        identity.assistantEditing = false; definition.assistantEditing = false;
        assistantStage = ""; manualDraft = false; loading = false;
    }
    function beginAssistantStage(key) {
        if (!project || key === "" || assistantStage !== "" || manualDraft || aliasCount || constraintCount)
            return false;
        assistantStage = key; outcome = "";
        return true;
    }
    function cancelAssistantStage(key) {
        if (assistantStage === key && !manualDraft) reset();
    }
    function takeAssistantStage(key) {
        if (assistantStage !== key) return;
        // A real manual event keeps its exact enabled editor/row/geometry.
        // This staged text has no blur commit; it becomes a genuine manual
        // draft, never an unobserved scientific edit or a newer RPC's input.
        assistantStage = ""; manualDraft = true;
        identity.assistantEditing = false; definition.assistantEditing = false;
    }
    function loadRow() {
        if (!rows || !identity || !definition || !enabledRule) return;
        loading = true;
        const valid = selectedRow >= 0 && selectedRow < selectedModel.count;
        const row = valid ? selectedModel.get(selectedRow) : null;
        identity.text = row ? row.id : "";
        definition.text = row ? row.definition : "";
        enabledRule.checked = row ? row.enabled : true;
        identity.assistantEditing = false; definition.assistantEditing = false;
        loading = false;
    }
    function put(key, value, own) {
        if (loading || selectedRow < 0 || selectedRow >= selectedModel.count) return;
        ++revision;
        selectedModel.setProperty(selectedRow, key, value);
        if (!own) manualDraft = true;
    }
    function addRow() {
        if (selectedModel.count >= 256) return;
        ++revision;
        selectedModel.append({id: "", definition: "", enabled: true});
        rows.currentIndex = selectedModel.count - 1;
        if (assistantStage === "") manualDraft = true;
        loadRow();
    }
    function apply() {
        const original = project;
        if (!original) return;
        const aliasRows = [], constraintRows = [];
        for (let i = 0; i < aliases.count; ++i) {
            const row = aliases.get(i); aliasRows.push({id: row.id, path: row.definition});
        }
        for (let i = 0; i < constraints.count; ++i) {
            const row = constraints.get(i);
            constraintRows.push({id: row.id, expression: row.definition, enabled: row.enabled});
        }
        const originalRevision = revision; const originalStage = assistantStage;
        const result = original.appendRelationForm(aliasRows, constraintRows);
        if (project !== original || revision !== originalRevision || assistantStage !== originalStage) return;
        outcome = result.message;
        if (result.applied) reset();
    }
    onProjectChanged: reset()
    Column {
        width: parent.width
        spacing: EaStyle.Sizes.fontPixelSize * 0.5
        Label {
            width: parent.width; wrapMode: Text.Wrap
            text: qsTr("Stage aliases with exact parameter paths and affine constraints. Existing declarations stay unchanged. Only Apply changes the project.")
        }
        TabBar {
            id: sections
            width: parent.width
            onCurrentIndexChanged: { rows.currentIndex = group.selectedModel.count ? 0 : -1; group.loadRow(); }
            TabButton { objectName: "relations.stage.aliases"; text: qsTr("Aliases (%1)").arg(group.aliasCount) }
            TabButton { objectName: "relations.stage.constraints"; text: qsTr("Constraints (%1)").arg(group.constraintCount) }
        }
        Row {
            width: parent.width
            spacing: EaStyle.Sizes.fontPixelSize * 0.5
            ComboBox {
                id: rows
                width: (parent.width - 2 * parent.spacing) * 0.5
                objectName: "relations.stage.row"
                model: group.selectedModel
                textRole: "id"
                displayText: currentIndex < 0 ? qsTr("No staged rows") : qsTr("Row %1: %2").arg(currentIndex + 1).arg(currentText)
                onCurrentIndexChanged: group.loadRow()
            }
            EaElements.SideBarButton {
                objectName: "relations.stage.add"
                width: (parent.width - 2 * parent.spacing) * 0.25
                text: qsTr("Add row")
                enabled: group.selectedModel.count < 256
                onClicked: group.addRow()
            }
            EaElements.SideBarButton {
                width: (parent.width - 2 * parent.spacing) * 0.25
                text: qsTr("Remove")
                enabled: rows.currentIndex >= 0
                onClicked: {
                    ++group.revision;
                    group.selectedModel.remove(rows.currentIndex);
                    rows.currentIndex = Math.min(rows.currentIndex, group.selectedModel.count - 1);
                    group.manualDraft = true; group.loadRow();
                }
            }
        }
        EaElements.TextInput {
            id: identity
            width: parent.width
            objectName: "relations.stage.id"
            enabled: rows.currentIndex >= 0
            maximumLength: 256
            placeholderText: group.constraintsSelected ? qsTr("Constraint ID") : qsTr("Alias ID")
            Accessible.name: placeholderText
            property bool assistantEditing: false
            readonly property string editText: text
            readonly property bool assistantManualDraft: group.manualDraft
            onTextChanged: group.put("id", text, assistantEditing)
            onInputMethodComposingChanged: if (inputMethodComposing && !assistantEditing) group.manualDraft = true
            // Staging has no editingFinished scientific commit.
            function beginAssistantEdit() { assistantEditing = true; }
            function allowAssistantCommit() { assistantEditing = false; }
            function cancelAssistantEdit() { assistantEditing = false; }
        }
        TextArea {
            id: definition
            width: parent.width
            height: EaStyle.Sizes.fontPixelSize * 3
            objectName: "relations.stage.definition"
            enabled: rows.currentIndex >= 0
            wrapMode: TextEdit.Wrap
            placeholderText: group.constraintsSelected ? qsTr("Affine expression: left = right") : qsTr("Exact parameter path")
            Accessible.name: placeholderText
            property bool assistantEditing: false
            readonly property string editText: text
            readonly property bool assistantManualDraft: group.manualDraft
            // Manual text remains a draft even when native Apply will refuse
            // its size. Never silently truncate or retain a different old row.
            onTextChanged: group.put("definition", text, assistantEditing)
            onInputMethodComposingChanged: if (inputMethodComposing && !assistantEditing) group.manualDraft = true
            Keys.onTabPressed: event => { insert(cursorPosition, "\t"); event.accepted = true; }
            function beginAssistantEdit() { assistantEditing = true; }
            function allowAssistantCommit() { assistantEditing = false; }
            function cancelAssistantEdit() { assistantEditing = false; }
        }
        EaElements.CheckBox {
            id: enabledRule
            objectName: "relations.stage.enabled"
            visible: group.constraintsSelected
            enabled: rows.currentIndex >= 0
            text: qsTr("Enable constraint")
            checked: true
            onClicked: group.put("enabled", checked, group.assistantStage !== "")
        }
        Row {
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.SideBarButton {
                objectName: "relations.stage.apply"
                text: qsTr("Apply relation batch")
                enabled: constraints.count > 0 && identity.text.length <= 256 && definition.text.length <= 1048576
                onClicked: group.apply()
            }
            EaElements.SideBarButton {
                objectName: "relations.stage.reset"
                text: qsTr("Clear form")
                onClicked: { group.reset(); group.outcome = ""; }
            }
        }
        Label { width: parent.width; text: group.outcome; wrapMode: Text.Wrap; visible: text !== "" }
    }
}
