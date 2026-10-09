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

    // Load data… for `experiment`: the file dialog, or in the browser the page's file chooser. The answer goes to
    // that experiment wherever its row is by then, and is refused if it has gone.
    readonly property string dataFilter: ".xye,.xy,.dat,.txt,.csv"
    property ProjectViewModel project: null
    // A scan project lists its datasets: No. · Fit · Datablock · File · one column per extract rule, with no
    // colour column and no remove button (one template experiment shows them all).
    readonly property bool scan: project !== null && project.scan
    // One column per extract rule, with its unit, from the table's own model. The table lays a row's cells out
    // by their place among the header's, so the header and each row repeat over the same list.
    readonly property var scanColumns: project ? project.experiments.columns : []
    property var webDataExperiment: null

    // This page's browser file request and the project it was made for: only its own answer is used, and only
    // while that project is still open. `webDataExperiment`: the experiment a Load data… request is for, or null
    // for Load experiment.
    property int webRequest: 0
    property var webRequestProject: null

    function chooseData(experiment) {
        if (WebFiles.available) {
            group.webRequestProject = group.project;
            group.webDataExperiment = experiment;
            group.webRequest = WebFiles.openFiles(group.dataFilter, false);
        } else {
            dataDialog.experiment = experiment;
            dataDialog.project = group.project;
            dataDialog.open();
        }
    }

    // Open at the start, unlike the category groups (owner, 2026-10-05; edi ADR-0017 §3).
    collapsed: false
    icon: "microscope"
    last: SideBarGroups.isLast(group)
    objectName: "group.experiments"
    title: qsTr("Experiments (%1)").arg(project ? project.experiments.count : 0)

    Column {
        spacing: AppSizes.groupContentSpacing

        DataTable {
            id: table

            columnWidths: [numberColumnWidth, group.scan ? 0.001 : AppSizes.iconColumnWidth, AppSizes.iconColumnWidth, textColumnWidth("name", qsTr("Datablock")), -1, group.scanColumns.length ? group.scanColumns.length * AppSizes.dataColumnWidth * 1.4 : 0.001, group.scan ? 0.001 : AppSizes.iconColumnWidth]
            defaultInfoText: qsTr("No experiments defined")
            model: group.project ? group.project.experiments : null
            objectName: "experiments.list"

            delegate: EaComponents.ListViewDelegate {
                id: row

                required property ExperimentViewModel experiment
                required property var extracted
                required property string file
                required property string fitOutcome
                required property int index
                required property bool isTemplate
                required property string name

                color: group.project && group.project.currentExperimentIndex === index ? EaStyle.Colors.tableHighlight : (index % 2 ? EaStyle.Colors.themeBackgroundHovered2 : EaStyle.Colors.themeBackgroundHovered1)
                objectName: `experiments.row.${index}`

                TapHandler {
                    onTapped: group.project.currentExperimentIndex = row.index
                }
                EaComponents.TableViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                // The block's icon in its colour (easydiffractionbeta's colour column; ADR-0017 §8).
                IconCell {
                    icon: "microscope"
                    iconColor: AppColors.experiment(row.index)
                    objectName: `experiments.color.${row.index}`
                    toolTip: qsTr("Measured pattern color")
                    visible: !group.scan
                }
                // How the project's last fit ended on this experiment; "Not fitted" when it took no part.
                IconCell {
                    icon: FitOutcomes.icon(row.fitOutcome)
                    iconColor: String(FitOutcomes.color(row.fitOutcome))
                    objectName: `experiments.fit.${row.index}`
                    ring: FitOutcomes.ring(row.fitOutcome)
                    toolTip: FitOutcomes.word(row.fitOutcome)
                }
                // The datablock name, editable: a refused rename returns the cell to the stored name and shows why.
                // Editing a name also makes its row current, as a click on the row does.
                TextCell {
                    horizontalAlignment: Text.AlignLeft
                    objectName: `experiments.name.${row.index}`
                    value: row.name

                    onActiveFocusChanged: if (activeFocus)
                        group.project.currentExperimentIndex = row.index
                    onCommitted: text => row.experiment.name = text
                }
                // The data's file: the experiment's own `.edi`, which holds its data, or a scan dataset's data file,
                // the template dataset's with the word "template" in the accent blue; Load data… without data.
                Item {
                    height: parent ? parent.height : 0

                    EaComponents.TableViewLabel {
                        elide: Text.ElideMiddle
                        horizontalAlignment: Text.AlignLeft
                        text: row.file
                        visible: !loadData.visible
                    }
                    EaComponents.TableViewLabel {
                        id: templateTag

                        anchors.right: parent.right
                        color: EaStyle.Colors.themeAccent
                        elide: Text.ElideNone
                        objectName: `experiments.template.${row.index}`
                        text: qsTr("template")
                        visible: group.scan && row.isTemplate
                    }
                    EaElements.Button {
                        id: loadData

                        ToolTip.text: qsTr("Load another data file in place of this one")
                        ToolTip.visible: hovered && row.experiment !== null && !row.experiment.calculationOnly
                        anchors.verticalCenter: parent.verticalCenter
                        enabled: row.experiment !== null && row.experiment.canLoadData
                        objectName: `experiments.loadData.${row.index}`
                        text: row.experiment !== null && !row.experiment.calculationOnly ? row.file : qsTr("Load data…")
                        // An experiment made with Create experiment: Load data…, then the loaded file's name, which
                        // loads another file in its place. A simulation loaded from `.edi` shows it disabled; a scan's
                        // datasets and experiments loaded with their data show their file.
                        visible: !group.scan && row.experiment !== null && (row.experiment.canLoadData || row.experiment.calculationOnly)

                        onClicked: group.chooseData(row.experiment)
                    }
                }
                // What the scan's extract rules take from the dataset, with their units.
                Item {
                    height: parent.height
                    visible: group.scanColumns.length > 0

                    Row {
                        height: parent.height

                        Repeater {
                            property int horizontalAlignment: Text.AlignHCenter

                            model: group.scanColumns.length

                            delegate: Item {
                                id: value

                                property int horizontalAlignment: Text.AlignHCenter
                                required property int index

                                height: EaStyle.Sizes.tableRowHeight
                                width: AppSizes.dataColumnWidth * 1.4

                                EaComponents.TableViewLabel {
                                    anchors.fill: parent
                                    horizontalAlignment: value.horizontalAlignment
                                    text: row.extracted && row.extracted.length > value.index ? row.extracted[value.index] : ""
                                }
                            }
                        }
                    }
                }
                EaComponents.TableViewButton {
                    ToolTip.text: qsTr("Remove this experiment")
                    fontIcon: "minus-circle"
                    objectName: `experiments.remove.${row.index}`
                    visible: !group.scan

                    onClicked: group.project.removeExperiment(row.index)
                }
            }
            header: EaComponents.ListViewHeader {
                EaComponents.TableViewLabel {
                }
                EaComponents.TableViewLabel {
                }
                EaComponents.TableViewLabel {
                    text: qsTr("Fit")
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Datablock")
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("File")
                }
                // Each in a plain item: a repeated label has no parent while it is made, and the table copies a
                // header cell's alignment onto the row cell at its place, the repeater's own included while a row
                // has not made its cells yet.
                Item {
                    height: parent.height
                    visible: group.scanColumns.length > 0

                    Row {
                        height: parent.height

                        Repeater {
                            property int horizontalAlignment: Text.AlignHCenter

                            model: group.scanColumns

                            delegate: Item {
                                id: column

                                property int horizontalAlignment: Text.AlignHCenter
                                required property string modelData

                                height: EaStyle.Sizes.tableRowHeight
                                width: AppSizes.dataColumnWidth * 1.4

                                EaComponents.TableViewLabel {
                                    anchors.fill: parent
                                    horizontalAlignment: column.horizontalAlignment
                                    text: column.modelData
                                }
                            }
                        }
                    }
                }
                EaComponents.TableViewLabel {
                    visible: !group.scan
                }
            }
        }
        ExperimentTypeGroup {
            experiment: group.project ? group.project.currentExperiment : null
            experimentIndex: group.project ? group.project.currentExperimentIndex : -1
            project: group.project
            visible: group.project !== null && group.project.currentExperiment !== null
        }
        Row {
            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                ToolTip.text: qsTr("Load experiments from .edi files, each with its type, data and parameters")
                enabled: group.project !== null
                fontIcon: "upload"
                objectName: "experiments.load"
                text: qsTr("Load experiment")

                // In the browser the files come through the page (edi ADR-0023).
                onClicked: {
                    if (WebFiles.available) {
                        group.webRequestProject = group.project;
                        group.webDataExperiment = null;
                        group.webRequest = WebFiles.openFiles(".edi", true);
                    } else {
                        loadDialog.open();
                    }
                }
            }
            EaElements.SideBarButton {
                ToolTip.text: enabled ? qsTr("Add an experiment without data, to calculate its pattern or load data into") : qsTr("A scan project fits its one template experiment")
                enabled: group.project !== null && group.project.canCreateExperiment
                fontIcon: "plus-circle"
                objectName: "experiments.create"
                text: qsTr("Create experiment")

                onClicked: group.project.createExperiment()
            }
        }
    }
    Connections {
        function onCancelled(request) {
            if (request === group.webRequest) {
                group.webRequest = 0;
                group.webDataExperiment = null;
            }
        }
        function onFailed(request) {
            if (request === group.webRequest) {
                group.webRequest = 0;
                group.webDataExperiment = null;
            }
        }
        function onFilesOpened(request, files) {
            if (request !== group.webRequest)
                return;
            group.webRequest = 0;
            const experiment = group.webDataExperiment;
            const forData = experiment !== null;
            group.webDataExperiment = null;
            if (group.project !== null && group.project === group.webRequestProject) {
                if (forData)
                    group.project.loadDataInto(experiment, files[0]);
                else
                    group.project.loadExperiments(files);
            }
        }

        target: WebFiles
    }
    FileDialog {
        id: loadDialog

        fileMode: FileDialog.OpenFiles
        nameFilters: [qsTr("edi block files (*.edi)")]
        title: qsTr("Load experiments from .edi block files")

        onAccepted: group.project.loadExperiments(selectedFiles)
    }

    // The dialog's answer goes to the experiment and the project it was opened for, and only while that project
    // is still the open one.
    FileDialog {
        id: dataDialog

        property var experiment: null
        property var project: null

        nameFilters: [qsTr("Data files (*.xye *.xy *.dat *.txt *.csv)"), qsTr("All files (*)")]
        title: qsTr("Load measured data from a plain two- or three-column file")

        onAccepted: {
            if (dataDialog.project !== null && dataDialog.project === group.project)
                group.project.loadDataInto(dataDialog.experiment, dataDialog.selectedFile);
            dataDialog.project = null;
            dataDialog.experiment = null;
        }
        onRejected: {
            dataDialog.project = null;
            dataDialog.experiment = null;
        }
    }
}
