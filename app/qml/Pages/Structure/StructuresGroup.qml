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
// one current; a structure enters only from a `.edi` block file, while the project holds none — an
// edi project holds one structure.
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null

    // This page's browser file request and the project it was made for: only its own answer is used, and only
    // while that project is still open.
    property int webRequest: 0
    property var webRequestProject: null

    // Open at the start, unlike the category groups (owner, 2026-10-05; edi ADR-0017 §3).
    collapsed: false
    icon: "layer-group"
    last: SideBarGroups.isLast(group)
    objectName: "group.structures"
    title: qsTr("Structures (%1)").arg(project ? project.structures.count : 0)

    Column {
        spacing: AppSizes.groupContentSpacing

        DataTable {
            id: table

            columnWidths: [numberColumnWidth, EaStyle.Sizes.tableRowHeight, -1, AppSizes.iconColumnWidth]
            defaultInfoText: qsTr("No structures defined")
            model: group.project ? group.project.structures : null
            objectName: "structures.list"

            delegate: EaComponents.ListViewDelegate {
                id: row

                required property int index
                required property string name
                required property StructureViewModel structure

                color: group.project && group.project.currentStructureIndex === index ? EaStyle.Colors.tableHighlight : (index % 2 ? EaStyle.Colors.themeBackgroundHovered2 : EaStyle.Colors.themeBackgroundHovered1)
                objectName: `structures.row.${index}`

                TapHandler {
                    onTapped: group.project.currentStructureIndex = row.index
                }
                EaComponents.TableViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                // The block's icon in its colour (easydiffractionbeta's colour column; ADR-0017 §8).
                IconCell {
                    icon: "layer-group"
                    iconColor: AppColors.structure(row.index)
                    objectName: `structures.color.${row.index}`
                    toolTip: qsTr("Calculated pattern color")
                }
                // The datablock name, editable: a refused rename returns the cell to the stored name and shows why.
                // Editing a name also makes its row current, as a click on the row does.
                TextCell {
                    objectName: `structures.name.${row.index}`
                    value: row.name

                    onActiveFocusChanged: if (activeFocus)
                        group.project.currentStructureIndex = row.index
                    onCommitted: text => row.structure.name = text
                }
                EaComponents.TableViewButton {
                    ToolTip.text: qsTr("Remove this structure")
                    fontIcon: "minus-circle"
                    objectName: `structures.remove.${row.index}`

                    onClicked: group.project.removeStructure(row.index)
                }
            }
            header: EaComponents.ListViewHeader {
                EaComponents.TableViewLabel {
                }
                EaComponents.TableViewLabel {
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Name")
                }
                EaComponents.TableViewLabel {
                }
            }
        }

        // Load and Create side by side, as easydiffractionbeta's Load and Define manually: Create adds
        // easydiffractionbeta's default phase as structure1, structure2, … (edi ADR-0017 §4).
        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                enabled: group.project !== null && group.project.canLoadStructure
                fontIcon: "upload"
                objectName: "structures.load"
                text: qsTr("Load structure from file")

                // In the browser the files come through the page (edi ADR-0023).
                onClicked: {
                    if (WebFiles.available) {
                        group.webRequestProject = group.project;
                        group.webRequest = WebFiles.openFiles(".edi", false);
                    } else {
                        loadDialog.open();
                    }
                }
            }
            EaElements.SideBarButton {
                ToolTip.text: qsTr("Add a structure with one atom site, to edit into the one you need")
                enabled: group.project !== null
                fontIcon: "plus-circle"
                objectName: "structures.create"
                text: qsTr("Create structure")

                onClicked: group.project.createStructure()
            }
        }
    }
    Connections {
        function onCancelled(request) {
            if (request === group.webRequest)
                group.webRequest = 0;
        }
        function onFailed(request) {
            if (request === group.webRequest)
                group.webRequest = 0;
        }
        function onFilesOpened(request, files) {
            if (request !== group.webRequest)
                return;
            group.webRequest = 0;
            if (group.project !== null && group.project === group.webRequestProject)
                group.project.loadStructure(files[0]);
        }

        target: WebFiles
    }
    FileDialog {
        id: loadDialog

        nameFilters: [qsTr("edi block files (*.edi)")]
        title: qsTr("Load a structure from an .edi block file")

        onAccepted: group.project.loadStructure(selectedFile)
    }
}
