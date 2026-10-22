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

    property var pickerLife: ({ alive: true })
    Component.onDestruction: pickerLife.alive = false
    property int webRequest: 0
    property var webIntent: null
    function chooseStructure() {
        const life = pickerLife;
        const originalProject = project;
        if (!life.alive || project !== originalProject || Session.project !== originalProject) return false;
        if (project === null || Session.project !== project || webIntent !== null || loadDialog.intent !== null || loadDialog.visible) return false;
        const original = { project: project };
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
        title: qsTr("Load a structure")
        nameFilters: [qsTr("Structure files (*.edi *.cif)"), qsTr("edi block files (*.edi)"), qsTr("CIF files (*.cif)")]
        onAccepted: {
            const life = group.pickerLife;
            const original = intent;
            const file = selectedFile;
            intent = null;
            if (life.alive && intent === null && original !== null && group.project === original.project && Session.project === original.project)
                original.project.loadStructure(file);
        }
        onRejected: intent = null
    }
}
