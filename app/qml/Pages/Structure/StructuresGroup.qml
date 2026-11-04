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
SideBarGroup {
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
            onRowActivated: row => ApplicationInfo.activateFormBlock(row, true)

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
                    onActiveFocusChanged: ApplicationInfo.finishUiEvent(10, undefined)
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

        // Load ▾, Create and Duplicate side by side at equal widths (the owner, 2026-11-03): Create adds
        // easydiffractionbeta's default phase as structure1, structure2, … (edi ADR-0017 §4). The Load menu takes a
        // structure from a file or from the web (COD or EasyDiffraction's collection).
        Row {
            id: buttons

            readonly property real buttonWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * spacing) / 3

            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                id: loadButton
                objectName: "structures.load"
                width: buttons.buttonWidth
                enabled: group.project !== null && group.project.canLoadStructure
                fontIcon: "upload"
                text: qsTr("Load") + " ▾"
                ToolTip.text: qsTr("Load a structure from a file or from the web")
                onClicked: loadMenu.open()

                EaElements.Menu {
                    id: loadMenu
                    objectName: "structures.load.menu"
                    y: loadButton.height
                    width: Math.max(loadButton.width, EaStyle.Sizes.fontPixelSize * 20)

                    LoadMenuHeader {
                        text: qsTr("Structure")
                    }
                    LoadMenuItem {
                        objectName: "structures.load.file"
                        fontIcon: "file"
                        text: qsTr("From file…")
                        hint: ".cif .edi"
                        toolTip: qsTr("Load a structure from a CIF or .edi file")
                        // In the browser the files come through the page (edi ADR-0023).
                        onTriggered: ApplicationInfo.loadFormFiles(false)
                    }
                    LoadMenuItem {
                        objectName: "structures.load.web"
                        fontIcon: "globe"
                        text: qsTr("From web…")
                        hint: "COD · EasyDiffraction"
                        toolTip: qsTr("Search the Crystallography Open Database or EasyDiffraction's collection for a structure")
                        onTriggered: onlineLoad.openFor("structure", null)
                    }
                }
            }
            EaElements.SideBarButton {
                objectName: "structures.create"
                width: buttons.buttonWidth
                enabled: group.project !== null
                fontIcon: "plus-circle"
                text: qsTr("Create structure")
                ToolTip.text: qsTr("Add a structure with one atom site, to edit into the one you need")
                onClicked: group.project.createStructure()
            }
            EaElements.SideBarButton {
                objectName: "structures.duplicate"
                width: buttons.buttonWidth
                enabled: group.project !== null && group.project.currentStructure !== null
                fontIcon: "clone"
                text: qsTr("Duplicate structure")
                ToolTip.text: qsTr("Add a copy of the selected structure, linked to no experiment")
                onClicked: group.project.duplicateStructure()
            }
        }
    }

    OnlineLoadDialog {
        id: onlineLoad
        project: group.project
    }

    property var pickerLife: ({
            alive: true
        })
    Component.onDestruction: ApplicationInfo.formPickerDestroyed()
    // This page's browser file request and the project it was made for: only its own answer is used, and only
    // while that project is still open.
    property int webRequest: 0
    property var webRequestProject: null
    property var webIntent: null
    function chooseStructure() {
        return ApplicationInfo.chooseStructureFile();
    }
    function takeWebIntent(request) {
        return ApplicationInfo.takeStructureWebIntent(request);
    }
    Connections {
        target: WebFiles
        function onFilesOpened(request, files) {
            ApplicationInfo.formFilesOpened(request, files, false);
        }
        function onFailed(request) {
            ApplicationInfo.formFilesCancelled(request, false);
        }
        function onCancelled(request) {
            ApplicationInfo.formFilesCancelled(request, false);
        }
    }

    FileDialog {
        id: loadDialog
        title: qsTr("Load a structure from a CIF or .edi file")
        nameFilters: [qsTr("Structure files (*.cif *.edi)"), qsTr("CIF files (*.cif)"), qsTr("edi block files (*.edi)")]
        onAccepted: group.project.loadStructure(selectedFile)
    }
}
