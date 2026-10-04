// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// Experiments (N) (easydiffractionbeta Pages/Experiment/SideBarBasic/Experiments.qml): the project's
// experiments, one current; experiments enter only from `.edi` block files declaring their
// type, whenever a project is open — an edi project holds several.
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null

    objectName: "group.experiments"
    title: qsTr("Experiments (%1)").arg(project ? project.experiments.count : 0)
    icon: "microscope"
    last: SideBarGroups.isLast(group)

    Column {
        spacing: AppSizes.groupContentSpacing

        EaComponents.TableView {
            id: table
            objectName: "experiments.list"
            defaultInfoText: qsTr("No experiments defined")
            model: group.project ? group.project.experiments : null

            header: EaComponents.TableViewHeader {
                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                    text: qsTr("No.")
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
                required property ExperimentViewModel experiment

                objectName: `experiments.row.${index}`
                color: group.project && group.project.currentExperimentIndex === index ? EaStyle.Colors.tableHighlight : (index % 2 ? EaStyle.Colors.themeBackgroundHovered2 : EaStyle.Colors.themeBackgroundHovered1)
                mouseArea.onPressed: group.project.currentExperimentIndex = row.index

                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                // The block's icon in its colour (easydiffractionbeta's colour column; ADR-0017 §8).
                IconCell {
                    objectName: `experiments.color.${row.index}`
                    icon: "microscope"
                    iconColor: AppColors.experiment(row.index)
                    toolTip: qsTr("Measured pattern color")
                }
                // The datablock name, editable: a refused rename returns the cell to the stored name and shows why.
                // Editing a name also makes its row current, as a click on the row does.
                TextCell {
                    objectName: `experiments.name.${row.index}`
                    width: table.headerLabelItems.length > 2 ? table.headerLabelItems[2].width : 0
                    value: row.name
                    onActiveFocusChanged: if (activeFocus)
                        group.project.currentExperimentIndex = row.index
                    onCommitted: text => row.experiment.name = text
                }
                EaComponents.TableViewButton {
                    objectName: `experiments.remove.${row.index}`
                    fontIcon: "minus-circle"
                    ToolTip.text: qsTr("Remove this experiment")
                    onClicked: group.project.removeExperiment(row.index)
                }
            }
        }

        // Load and Define manually side by side, as easydiffractionbeta's; defining an experiment by hand is
        // not implemented, so its button is disabled (edi ADR-0017 §4).
        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                objectName: "experiments.load"
                enabled: group.project !== null
                fontIcon: "upload"
                text: qsTr("Load experiment(s) from file(s)")
                // In the browser the files come through the page (edi ADR-0023).
                onClicked: {
                    if (WebFiles.available) {
                        group.webRequestProject = group.project;
                        group.webRequest = WebFiles.openFiles(".edi", true);
                    } else {
                        loadDialog.open();
                    }
                }
            }
            EaElements.SideBarButton {
                objectName: "experiments.define"
                enabled: false
                fontIcon: "plus-circle"
                text: qsTr("Define experiment manually")
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
                group.project.loadExperiments(files);
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
        title: qsTr("Load experiments from .edi block files")
        fileMode: FileDialog.OpenFiles
        nameFilters: [qsTr("edi block files (*.edi)")]
        onAccepted: group.project.loadExperiments(selectedFiles)
    }
}
