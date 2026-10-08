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

    objectName: "group.structures"
    title: qsTr("Structures (%1)").arg(project ? project.structures.count : 0)
    icon: "layer-group"
    last: SideBarGroups.isLast(group)
    // Open at the start, unlike the category groups (owner, 2026-10-05; edi ADR-0017 §3).
    collapsed: false

    Column {
        spacing: AppSizes.groupContentSpacing

        EaComponents.TableView {
            id: table
            objectName: "structures.list"
            defaultInfoText: qsTr("No structures defined")
            model: group.project ? group.project.structures : null

            header: EaComponents.TableViewHeader {
                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.tableRowHeight
                }
                EaComponents.TableViewLabel {
                    flexibleWidth: true
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Name")
                }
                EaComponents.TableViewLabel {
                    width: AppSizes.iconColumnWidth
                }
            }

            delegate: EaComponents.TableViewDelegate {
                id: row

                required property int index
                required property string name
                required property StructureViewModel structure

                objectName: `structures.row.${index}`
                color: group.project && group.project.currentStructureIndex === index ? EaStyle.Colors.tableHighlight : (index % 2 ? EaStyle.Colors.themeBackgroundHovered2 : EaStyle.Colors.themeBackgroundHovered1)
                mouseArea.onPressed: group.project.currentStructureIndex = row.index

                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                // The block's icon in its colour (easydiffractionbeta's colour column; ADR-0017 §8).
                IconCell {
                    objectName: `structures.color.${row.index}`
                    icon: "layer-group"
                    iconColor: AppColors.structure(row.index)
                    toolTip: qsTr("Calculated pattern color")
                }
                // The datablock name, editable: a refused rename returns the cell to the stored name and shows why.
                // Editing a name also makes its row current, as a click on the row does.
                TextCell {
                    objectName: `structures.name.${row.index}`
                    width: table.headerLabelItems.length > 2 ? table.headerLabelItems[2].width : 0
                    value: row.name
                    onActiveFocusChanged: if (activeFocus)
                        group.project.currentStructureIndex = row.index
                    onCommitted: text => row.structure.name = text
                }
                EaComponents.TableViewButton {
                    objectName: `structures.remove.${row.index}`
                    fontIcon: "minus-circle"
                    ToolTip.text: qsTr("Remove this structure")
                    onClicked: group.project.removeStructure(row.index)
                }
            }
        }

        // Load and Create side by side, as easydiffractionbeta's Load and Define manually: Create adds
        // easydiffractionbeta's default phase as structure1, structure2, … (edi ADR-0017 §4).
        Row {
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
                        group.webRequest = WebFiles.openFiles(".edi", false);
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
        }
    }

    // This page's browser file request and the project it was made for: only its own answer is used, and only
    // while that project is still open.
    property int webRequest: 0
    property var webRequestProject: null
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
        title: qsTr("Load a structure from an .edi block file")
        nameFilters: [qsTr("edi block files (*.edi)")]
        onAccepted: group.project.loadStructure(selectedFile)
    }
}
