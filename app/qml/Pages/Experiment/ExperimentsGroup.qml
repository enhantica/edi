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
// experiments, one current, each with how the last fit ended on it (Fit) and the file its data is in; under
// the table the selected experiment's type (ExperimentTypeGroup), then Load experiment (`.edi` block files,
// several at once, each with its type, data and parameters) and Create experiment (a new experiment without
// data, a simulation). A row made with Create experiment has a Load data… button in its File cell until data is
// loaded into it: a plain two- or three-column file whose rows become its measured data. Create, Load and Load
// data are each one undoable step.
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null
    // A scan project lists its datasets: No. · Fit · Datablock · File · one column per extract rule, with no
    // colour column and no remove button (one template experiment shows them all).
    readonly property bool scan: project !== null && project.scan
    // One column per extract rule, with its unit, from the table's own model. The table lays a row's cells out
    // by their place among the header's, so the header and each row repeat over the same list.
    readonly property var scanColumns: project ? project.experiments.columns : []

    objectName: "group.experiments"
    title: qsTr("Experiments (%1)").arg(project ? project.experiments.count : 0)
    icon: "microscope"
    last: SideBarGroups.isLast(group)
    // Open at the start, unlike the category groups (owner, 2026-10-05; edi ADR-0017 §3).
    collapsed: false

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
                    width: group.scan ? 0 : EaStyle.Sizes.tableRowHeight
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.tableRowHeight
                    text: qsTr("Fit")
                }
                EaComponents.TableViewLabel {
                    flexibleWidth: true
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Datablock")
                }
                EaComponents.TableViewLabel {
                    width: group.scan ? AppSizes.datasetFileColumnWidth : AppSizes.fileColumnWidth
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("File")
                }
                // Each in a plain item: a repeated label has no parent while it is made, and the table copies a
                // header cell's alignment onto the row cell at its place, the repeater's own included while a row
                // has not made its cells yet.
                Repeater {
                    property int horizontalAlignment: Text.AlignHCenter
                    model: group.scanColumns
                    delegate: Item {
                        id: column
                        required property string modelData
                        property int horizontalAlignment: Text.AlignHCenter
                        width: AppSizes.dataColumnWidth * 1.4
                        height: EaStyle.Sizes.tableRowHeight
                        EaComponents.TableViewLabel {
                            anchors.fill: parent
                            horizontalAlignment: column.horizontalAlignment
                            text: column.modelData
                        }
                    }
                }
                EaComponents.TableViewLabel {
                    width: group.scan ? 0 : AppSizes.iconColumnWidth
                }
            }

            delegate: EaComponents.TableViewDelegate {
                id: row

                required property int index
                required property string name
                required property ExperimentViewModel experiment
                required property string fitOutcome
                required property string file
                required property var extracted
                required property bool isTemplate

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
                    visible: !group.scan
                    width: group.scan ? 0 : EaStyle.Sizes.tableRowHeight
                    icon: "microscope"
                    iconColor: AppColors.experiment(row.index)
                    toolTip: qsTr("Measured pattern color")
                }
                // How the project's last fit ended on this experiment; "Not fitted" when it took no part.
                IconCell {
                    objectName: `experiments.fit.${row.index}`
                    icon: FitOutcomes.icon(row.fitOutcome)
                    iconColor: String(FitOutcomes.color(row.fitOutcome))
                    ring: FitOutcomes.ring(row.fitOutcome)
                    toolTip: FitOutcomes.word(row.fitOutcome)
                }
                // The datablock name, editable: a refused rename returns the cell to the stored name and shows why.
                // Editing a name also makes its row current, as a click on the row does.
                TextCell {
                    objectName: `experiments.name.${row.index}`
                    width: table.headerLabelItems.length > 3 ? table.headerLabelItems[3].width : 0
                    value: row.name
                    onActiveFocusChanged: if (activeFocus)
                        group.project.currentExperimentIndex = row.index
                    onCommitted: text => row.experiment.name = text
                }
                // The data's file: the experiment's own `.edi`, which holds its data, or a scan dataset's data file,
                // the template dataset's with the word "template" in the accent blue; Load data… without data.
                Item {
                    width: group.scan ? AppSizes.datasetFileColumnWidth : AppSizes.fileColumnWidth
                    height: parent ? parent.height : 0

                    EaComponents.TableViewLabel {
                        visible: !loadData.visible
                        width: parent.width - (templateTag.visible ? templateTag.width : 0)
                        horizontalAlignment: Text.AlignLeft
                        elide: Text.ElideMiddle
                        text: row.file
                    }
                    EaComponents.TableViewLabel {
                        id: templateTag
                        objectName: `experiments.template.${row.index}`
                        visible: group.scan && row.isTemplate
                        anchors.right: parent.right
                        width: implicitWidth
                        elide: Text.ElideNone
                        color: EaStyle.Colors.themeAccent
                        text: qsTr("template")
                    }
                    EaElements.Button {
                        id: loadData
                        objectName: `experiments.loadData.${row.index}`
                        // An experiment made with Create experiment: Load data…, then the loaded file's name, which
                        // loads another file in its place. A simulation loaded from `.edi` shows it disabled; a scan's
                        // datasets and experiments loaded with their data show their file.
                        visible: !group.scan && row.experiment !== null && (row.experiment.canLoadData || row.experiment.calculationOnly)
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width
                        enabled: row.experiment !== null && row.experiment.canLoadData
                        text: row.experiment !== null && !row.experiment.calculationOnly ? row.file : qsTr("Load data…")
                        ToolTip.visible: hovered && row.experiment !== null && !row.experiment.calculationOnly
                        ToolTip.text: qsTr("Load another data file in place of this one")
                        onClicked: group.chooseData(row.index)
                    }
                }
                // What the scan's extract rules take from the dataset, with their units.
                Repeater {
                    property int horizontalAlignment: Text.AlignHCenter
                    model: group.scanColumns.length
                    delegate: Item {
                        id: value
                        required property int index
                        property int horizontalAlignment: Text.AlignHCenter
                        height: EaStyle.Sizes.tableRowHeight
                        EaComponents.TableViewLabel {
                            anchors.fill: parent
                            horizontalAlignment: value.horizontalAlignment
                            text: row.extracted && row.extracted.length > value.index ? row.extracted[value.index] : ""
                        }
                    }
                }
                EaComponents.TableViewButton {
                    objectName: `experiments.remove.${row.index}`
                    visible: !group.scan
                    width: group.scan ? 0 : AppSizes.iconColumnWidth
                    fontIcon: "minus-circle"
                    ToolTip.text: qsTr("Remove this experiment")
                    onClicked: group.project.removeExperiment(row.index)
                }
            }
        }

        ExperimentTypeGroup {
            visible: group.project !== null && group.project.currentExperiment !== null
            project: group.project
            experiment: group.project ? group.project.currentExperiment : null
            experimentIndex: group.project ? group.project.currentExperimentIndex : -1
        }

        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                objectName: "experiments.load"
                enabled: group.project !== null
                fontIcon: "upload"
                text: qsTr("Load experiment")
                ToolTip.text: qsTr("Load experiments from .edi files, each with its type, data and parameters")
                // In the browser the files come through the page (edi ADR-0023).
                onClicked: {
                    if (WebFiles.available) {
                        group.webRequestProject = group.project;
                        group.webDataIndex = -1;
                        group.webRequest = WebFiles.openFiles(".edi", true);
                    } else {
                        loadDialog.open();
                    }
                }
            }
            EaElements.SideBarButton {
                objectName: "experiments.create"
                enabled: group.project !== null && group.project.canCreateExperiment
                fontIcon: "plus-circle"
                text: qsTr("Create experiment")
                ToolTip.text: enabled ? qsTr("Add an experiment without data, to calculate its pattern or load data into") : qsTr("A scan project fits its one template experiment")
                onClicked: group.project.createExperiment()
            }
        }
    }

    // Load data… for experiment `index`: the file dialog, or in the browser the page's file chooser.
    readonly property string dataFilter: ".xye,.xy,.dat,.txt,.csv"
    function chooseData(index) {
        if (WebFiles.available) {
            group.webRequestProject = group.project;
            group.webDataIndex = index;
            group.webRequest = WebFiles.openFiles(group.dataFilter, false);
        } else {
            dataDialog.experimentIndex = index;
            dataDialog.project = group.project;
            dataDialog.open();
        }
    }

    // This page's browser file request and the project it was made for: only its own answer is used, and only
    // while that project is still open. `webDataIndex`: the experiment a Load data… request is for, or -1 for
    // Load experiment.
    property int webRequest: 0
    property var webRequestProject: null
    property int webDataIndex: -1
    Connections {
        target: WebFiles
        function onFilesOpened(request, files) {
            if (request !== group.webRequest)
                return;
            group.webRequest = 0;
            const index = group.webDataIndex;
            group.webDataIndex = -1;
            if (group.project !== null && group.project === group.webRequestProject) {
                if (index >= 0)
                    group.project.loadData(index, files[0]);
                else
                    group.project.loadExperiments(files);
            }
        }
        function onFailed(request) {
            if (request === group.webRequest) {
                group.webRequest = 0;
                group.webDataIndex = -1;
            }
        }
        function onCancelled(request) {
            if (request === group.webRequest) {
                group.webRequest = 0;
                group.webDataIndex = -1;
            }
        }
    }

    FileDialog {
        id: loadDialog
        title: qsTr("Load experiments from .edi block files")
        fileMode: FileDialog.OpenFiles
        nameFilters: [qsTr("edi block files (*.edi)")]
        onAccepted: group.project.loadExperiments(selectedFiles)
    }

    // The dialog's answer goes to the experiment and the project it was opened for, and only while that project
    // is still the open one.
    FileDialog {
        id: dataDialog
        property int experimentIndex: -1
        property var project: null
        title: qsTr("Load measured data from a plain two- or three-column file")
        nameFilters: [qsTr("Data files (*.xye *.xy *.dat *.txt *.csv)"), qsTr("All files (*)")]
        onAccepted: {
            if (dataDialog.project !== null && dataDialog.project === group.project)
                group.project.loadData(dataDialog.experimentIndex, dataDialog.selectedFile);
            dataDialog.project = null;
        }
        onRejected: dataDialog.project = null
    }
}
