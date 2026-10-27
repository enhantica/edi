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
            onRowActivated: row => {
                if (group.project)
                    group.project.currentStructureIndex = row;
            }

            columns: [numberColumnWidth, AppSizes.iconOnlyColumnWidth, -1, AppSizes.iconColumnWidth]

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Name")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            delegate: TableRow {
                id: row

                required property string name
                required property StructureViewModel structure

                objectName: `structures.row.${index}`
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
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
                EaComponents.ListViewButton {
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
                enabled: group.project !== null && group.project.canLoadStructure
                fontIcon: "upload"
                text: qsTr("Load structure from file")
                // In the browser the files come through the page (edi ADR-0023).
                onClicked: {
                    if (WebFiles.available) {
                        group.webRequestProject = group.project;
                        group.webRequest = WebFiles.openFiles(".cif,.edi", false);
                    } else {
                        loadDialog.open();
                    }
                }
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
            if (request !== group.webRequest)
                return;
            group.webRequest = 0;
            if (group.project !== null && group.project === group.webRequestProject)
                group.project.loadStructure(files[0]);
        }
        function onFailed(request) {
            if (request === group.webRequest)
                group.webRequest = 0;
        }
        function onCancelled(request) {
            if (request === group.webRequest)
                group.webRequest = 0;
        }
    }

    FileDialog {
        id: loadDialog
        title: qsTr("Load a structure from a CIF or .edi file")
        nameFilters: [qsTr("Structure files (*.cif *.edi)"), qsTr("CIF files (*.cif)"), qsTr("edi block files (*.edi)")]
        onAccepted: group.project.loadStructure(selectedFile)
    }
}
