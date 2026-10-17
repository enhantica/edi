// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// Structures (N) (easydiffractionbeta Pages/Model/SideBarBasic/Models.qml): the project's structures,
// one current. The original Load accepts native .edi and the already supported
// single-structure CIF vocabulary; all additions use the same editor/Undo.
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null

    objectName: "group.structures"
    title: qsTr("Structures (%1)").arg(project ? project.structures.count : 0)
    icon: "layer-group"
    last: SideBarGroups.isLast(group)
    // Open at the start, unlike the category groups (owner, 2026-10-05; edi ADR-0017 §3).
    collapsed: false

    Column {
        spacing: AppSizes.groupContentSpacing

        DataTable {
            id: table
            objectName: "structures.list"
            defaultInfoText: qsTr("No structures defined")
            sourceModel: group.project ? group.project.structures : null
            marksCurrentRow: true
            currentRow: group.project ? group.project.currentStructureIndex : -1

            columnWidths: [numberColumnWidth, AppSizes.iconOnlyColumnWidth, -1, AppSizes.iconColumnWidth]

            header: EaComponents.ListViewHeader {
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Name")
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            delegate: TableRow {
                id: row

                required property string name
                required property StructureViewModel structure

                objectName: `structures.row.${index}`
                TapHandler {
                    readonly property var assistantGesture: ({ current: null })

                    function sameGesture(point) {
                        const retained = assistantGesture.current;
                        return retained !== null && retained.device === point.device && retained.id === point.id && retained.press === point.pressTimestamp;
                    }
                    function discardGesture(point) {
                        if (sameGesture(point)) {
                            assistantGesture.current.closed = true;
                            assistantGesture.current.proof = null;
                        }
                    }
                    onGrabChanged: (transition, eventPoint) => {
                        if (transition === PointerDevice.GrabPassive || transition === PointerDevice.GrabExclusive) {
                            if (sameGesture(eventPoint))
                                return; // Passive/exclusive transitions cannot rearm this press.
                            if (eventPoint.state !== EventPoint.Pressed)
                                return;
                            const original = { device: eventPoint.device, id: eventPoint.id, press: eventPoint.pressTimestamp, proof: null, closed: false };
                            const holder = assistantGesture;
                            holder.current = original; // No QML notification before capture/cancellation.
                            const proof = Session.assistant.beginManualControlInput(row, eventPoint, row.structure);
                            if (holder.current === original && !original.closed)
                                original.proof = proof; // An old callback cannot overwrite a newer grab.
                        } else if (transition === PointerDevice.UngrabPassive || transition === PointerDevice.UngrabExclusive || transition === PointerDevice.CancelGrabPassive || transition === PointerDevice.CancelGrabExclusive) {
                            discardGesture(eventPoint);
                        }
                    }
                    onCanceled: eventPoint => {
                        if (sameGesture(eventPoint))
                            discardGesture(eventPoint);
                    }
                    onTapped: eventPoint => {
                        if (!sameGesture(eventPoint) || assistantGesture.current.closed)
                            return;
                        const original = assistantGesture.current;
                        const proof = original.proof;
                        original.closed = true;
                        original.proof = null; // Consume BEFORE validation/action and any reentry.
                        if (Session.assistant.completeManualControlInput(row, eventPoint, row.structure, proof))
                            group.project.currentStructureIndex = row.index;
                    }
                }

                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                // The block's icon in its colour (easydiffractionbeta's colour column; ADR-0017 §8).
                IconCell {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `structures.color.${row.index}`
                    icon: "layer-group"
                    iconColor: AppColors.structure(row.index)
                    toolTip: qsTr("Calculated pattern color")
                }
                // The datablock name, editable: a refused rename returns the cell to the stored name and shows why.
                // Editing a name also makes its row current, as a click on the row does.
                TextCell {
                    editMember: row
                    editModel: group.project ? group.project.structures : null
                    editIndex: row.index
                    horizontalAlignment: Text.AlignLeft
                    objectName: `structures.name.${row.index}`
                    value: row.name
                    onActiveFocusChanged: if (activeFocus)
                        group.project.currentStructureIndex = row.index
                    onCommitted: text => row.structure.name = text
                }
                EaComponents.TableViewButton {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `structures.remove.${row.index}`
                    fontIcon: "minus-circle"
                    ToolTip.text: qsTr("Remove this structure")
                    onClicked: group.project.removeStructure(row.index)
                }
            }
        }

        // Load and Create side by side, as easydiffractionbeta's Load and Define manually: Create adds
        // easydiffractionbeta's default phase as structure1, structure2, … (edi ADR-0017 §4). Under them Duplicate,
        // and Load from COD, not available yet (the owner, 2026-10-11).
        Grid {
            columns: 2
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                objectName: "structures.load"
                enabled: group.project !== null && group.project.canLoadStructure &&
                         group.webIntent === null && loadDialog.intent === null
                fontIcon: "upload"
                text: qsTr("Load structure from file")
                // Native and browser answers retain the same original owner.
                onClicked: group.chooseStructure()

            }
            EaElements.SideBarButton {
                objectName: "structures.create"
                enabled: group.project !== null
                fontIcon: "plus-circle"
                text: qsTr("Create structure")
                ToolTip.text: qsTr("Add a structure with one atom site, to edit into the one you need")
                onClicked: group.project.createStructure()
            }
            EaElements.SideBarButton {
                objectName: "structures.duplicate"
                enabled: group.project !== null && group.project.currentStructure !== null
                fontIcon: "clone"
                text: qsTr("Duplicate structure")
                ToolTip.text: qsTr("Add a copy of the selected structure, linked to no experiment")
                onClicked: group.project.duplicateStructure()
            }
            EaElements.SideBarButton {
                objectName: "structures.loadCod"
                enabled: false
                fontIcon: "cloud-download-alt"
                text: qsTr("Load from COD")
                ToolTip.text: qsTr("Loading from the Crystallography Open Database is not available yet")
            }
        }
    }

    // Only an original visible request configures this SAME ordinary picker.
    // A retired request never restores over a newer human/dialog intent.
    property var assistantPicker: null
    readonly property string assistantPickerId: assistantPicker !== null ? assistantPicker.id : ""
    function prepareAssistantPicker(id) {
        const life = pickerLife;
        const originalProject = project;
        if (!restoreRetiredAssistantPicker() || !life.alive || project !== originalProject || Session.project !== originalProject) return false;
        if (id.length === 0 || WebFiles.available || project === null || Session.project !== project ||
            assistantPicker !== null || loadDialog.intent !== null || loadDialog.visible || webIntent !== null) return false;
        const original = { id: id, project: project, options: loadDialog.options, popupType: loadDialog.popupType,
            ownedOptions: loadDialog.options | FileDialog.DontUseNativeDialog, retired: false, cancelled: false };
        assistantPicker = original;
        if (!life.alive || assistantPicker !== original) return false;
        loadDialog.popupType = Popup.Item;
        if (!life.alive || assistantPicker !== original) return false;
        loadDialog.options = original.ownedOptions;
        if (!life.alive || assistantPicker !== original) return false;
        if (project !== original.project || Session.project !== original.project) {
            original.retired = true;
            Qt.callLater(() => { if (life.alive) group.restoreAssistantPicker(original); });
            return false;
        }
        return true;
    }
    function restoreAssistantPicker(original) {
        if (original === null || original.restoring || assistantPicker !== original || loadDialog.visible || loadDialog.intent !== null
            || (loadDialog.cleanupOwner !== null && loadDialog.cleanupOwner !== original)) return;
        const life = pickerLife;
        original.restoring = true;
        try {
            if (loadDialog.popupType === Popup.Item) loadDialog.popupType = original.popupType;
            if (!life.alive || assistantPicker !== original || loadDialog.visible || loadDialog.intent !== null) return;
            if (loadDialog.options === original.ownedOptions) loadDialog.options = original.options;
            if (!life.alive || assistantPicker !== original || loadDialog.visible || loadDialog.intent !== null) return;
            if (loadDialog.cleanupOwner === original) loadDialog.cleanupOwner = null;
            if (!life.alive || assistantPicker !== original || loadDialog.visible || loadDialog.intent !== null
                || loadDialog.cleanupOwner !== null) return;
            assistantPicker = null; // Terminal: a newer configuration may now be admitted.
        } finally { original.restoring = false; }
    }
    function restoreRetiredAssistantPicker() {
        const life = pickerLife;
        const original = assistantPicker;
        if (original === null || !original.retired) return true;
        restoreAssistantPicker(original);
        return life.alive && assistantPicker === null;
    }
    function retireAssistantPicker(id, manual) {
        const original = assistantPicker;
        if (original === null || original.id !== id) return;
        const life = pickerLife;
        original.retired = true;
        original.cancelled = true;
        const pending = loadDialog.intent;
        const controls = pending !== null && pending.assistant === original;
        if (controls) {
            if (manual) pending.assistant = null;
            // close() need not emit rejected. Consume only A's still-owned
            // unopened/cancelled intent; an open manual picker keeps its target.
            if (!manual || !loadDialog.visible) loadDialog.intent = null;
        }
        if (!life.alive) return;
        Qt.callLater(() => { if (life.alive) group.restoreAssistantPicker(original); });
        // A later retirement cannot close a picker already handed to a human.
        if (!manual && controls && assistantPicker === original && loadDialog.intent === null &&
            (loadDialog.cleanupOwner === null || loadDialog.cleanupOwner === original)) loadDialog.close();
    }
    property var pickerLife: ({ alive: true })
    Component.onDestruction: pickerLife.alive = false
    property int webRequest: 0
    property var webIntent: null
    function chooseStructure() {
        const life = pickerLife;
        const originalProject = project;
        if (!restoreRetiredAssistantPicker() || !life.alive || project !== originalProject || Session.project !== originalProject) return false;
        if (project === null || Session.project !== project || webIntent !== null || loadDialog.intent !== null || loadDialog.visible ||
            (assistantPicker !== null && assistantPicker.retired)) return false;
        const original = { project: project, assistant: assistantPicker, configuration: assistantPicker };
        if (WebFiles.available) {
            webIntent = original;
            if (!life.alive || webIntent !== original) return false;
            if (project !== original.project || Session.project !== original.project) { webIntent = null; return false; }
            const request = WebFiles.openFiles(".edi,.cif", false);
            if (!life.alive || webIntent !== original) return false;
            if (request === 0 || project !== original.project || Session.project !== original.project) { webIntent = null; return false; }
            webRequest = request;
        } else {
            loadDialog.intent = original;
            if (!life.alive || loadDialog.intent !== original) return false;
            loadDialog.cleanupOwner = original.configuration;
            if (!life.alive || loadDialog.intent !== original) return false;
            if (project !== original.project || Session.project !== original.project) { loadDialog.intent = null; return false; }
            loadDialog.open();
        }
        return true;
    }
    function takeWebIntent(request) {
        if (request !== webRequest || webIntent === null) return null;
        const life = pickerLife;
        const original = webIntent;
        webRequest = 0;
        if (!life.alive || webIntent !== original) return null;
        webIntent = null; // Consume before any scientific callback or reentry.
        if (!life.alive || webIntent !== null || project !== original.project || Session.project !== original.project) return null;
        return original;
    }
    Connections {
        target: WebFiles
        function onFilesOpened(request, files) {
            const original = group.takeWebIntent(request);
            if (original !== null && files.length === 1) original.project.loadStructure(files[0]);
        }
        function onFailed(request) { group.takeWebIntent(request); }
        function onCancelled(request) { group.takeWebIntent(request); }
    }
    FileDialog {
        id: loadDialog
        objectName: "structures.fileDialog"
        property var intent: null
        property var cleanupOwner: null
        onVisibleChanged: {
            const original = cleanupOwner;
            const life = group.pickerLife;
            if (!visible && original !== null)
                Qt.callLater(() => { if (life.alive) group.restoreAssistantPicker(original); });
        }
        readonly property string assistantIntentId: intent !== null && intent.assistant !== null ? intent.assistant.id : ""
        title: qsTr("Load a structure")
        nameFilters: [qsTr("Structure files (*.edi *.cif)"), qsTr("edi block files (*.edi)"), qsTr("CIF files (*.cif)")]
        onAccepted: {
            const life = group.pickerLife;
            const original = intent;
            const file = selectedFile;
            const picker = original !== null ? original.assistant : null;
            const configuration = original !== null ? original.configuration : null;
            if (configuration !== null) {
                configuration.retired = true;
                Qt.callLater(() => { if (life.alive) group.restoreAssistantPicker(configuration); });
            }
            intent = null;
            if (life.alive && intent === null && original !== null && group.project === original.project && Session.project === original.project &&
                (picker === null || (!picker.cancelled && group.assistantPicker === picker)))
                original.project.loadStructure(file);
        }
        onRejected: {
            const life = group.pickerLife;
            const original = intent;
            const picker = original !== null ? original.assistant : null;
            const configuration = original !== null ? original.configuration : null;
            if (configuration !== null) {
                configuration.retired = true;
                Qt.callLater(() => { if (life.alive) group.restoreAssistantPicker(configuration); });
            }
            intent = null;
        }
    }
}
