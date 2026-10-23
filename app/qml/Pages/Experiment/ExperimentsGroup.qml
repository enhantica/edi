// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// Experiments (N) (easydiffractionbeta Pages/Experiment/SideBarBasic/Experiments.qml): the project's
// experiments, one current, each with how the last fit ended on it (Fit) and the file its data is in; under
// the table the selected experiment's type (ExperimentTypeGroup), then Load experiment (`.edi` block files,
// several at once, each with its type, data and parameters) and Create experiment (a new experiment without
// data, a simulation). A row made with Create experiment reads Load data… in its Data file cell until data is loaded
// into it: a plain two- or three-column file whose rows become its measured data. Clicking a file name loads another
// file in its place. Create, Load and Load data are each one undoable step.
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null
    // A scan project lists its datasets: No. · Fit · Datablock · File · one column per extract rule, with no
    // colour column and no remove button (one template experiment shows them all).
    readonly property bool scan: project !== null && project.scan
    // One column per extract rule, with its unit, from the table's own model. The table lays a row's cells out
    // by their place among the header's, so the header and each row repeat over the same list.
    readonly property var scanColumns: project ? project.experiments.columns : []
    // The Fit column is as wide as its title or its icon, so the Fit icon sits as close to the colour icon as the
    // Structures table's icon to its name: one margin between them, not each column's own (the owner, 2026-10-11).
    readonly property real fitColumnWidth: Math.ceil(Math.max(fitTitle.advanceWidth, EaStyle.Sizes.fontPixelSize * 1.15))

    objectName: "group.experiments"
    title: qsTr("Experiments (%1)").arg(project ? project.experiments.count : 0)
    icon: "microscope"
    last: SideBarGroups.isLast(group)
    // Open at the start, unlike the category groups (owner, 2026-10-05; edi ADR-0017 §3).
    collapsed: false

    TextMetrics {
        id: fitTitle
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        text: qsTr("Fit")
    }

    Column {
        spacing: AppSizes.groupContentSpacing

        DataTable {
            id: table
            objectName: "experiments.list"
            defaultInfoText: qsTr("No experiments defined")
            sourceModel: group.project ? group.project.experiments : null
            marksCurrentRow: true
            currentRow: group.project ? group.project.currentExperimentIndex : -1
            onRowActivated: row => {
                if (group.project)
                    group.project.currentExperimentIndex = row;
            }

            columnWidths: [numberColumnWidth, group.scan ? 0.001 : AppSizes.iconOnlyColumnWidth, group.scan ? AppSizes.iconOnlyColumnWidth : group.fitColumnWidth, textColumnWidth("name", qsTr("Datablock")), -1, group.scanColumns.length ? group.scanColumns.length * AppSizes.dataColumnWidth * 1.4 : 0.001, group.scan ? 0.001 : AppSizes.iconColumnWidth]

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("Fit")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Datablock")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Data file")
                }
                // Keep the scan's repeated cells in one width-controlled column (ADR-0029).
                Item {
                    property int horizontalAlignment: Text.AlignHCenter
                    visible: group.scanColumns.length > 0
                    height: parent.height
                    Row {
                        height: parent.height
                        Repeater {
                            property int horizontalAlignment: Text.AlignHCenter
                            model: group.scanColumns
                            delegate: Item {
                                id: column
                                required property string modelData
                                property int horizontalAlignment: Text.AlignHCenter
                                width: AppSizes.dataColumnWidth * 1.4
                                height: EaStyle.Sizes.tableRowHeight
                                EaComponents.ListViewLabel {
                                    anchors.fill: parent
                                    horizontalAlignment: column.horizontalAlignment
                                    text: column.modelData
                                }
                            }
                        }
                    }
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    visible: !group.scan
                }
            }

            delegate: TableRow {
                id: row

                required property string name
                required property ExperimentViewModel experiment
                required property string fitOutcome
                required property string file
                required property var extracted
                required property bool isTemplate

                objectName: `experiments.row.${index}`
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                // The block's icon in its colour (easydiffractionbeta's colour column; ADR-0017 §8).
                IconCell {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `experiments.color.${row.index}`
                    visible: !group.scan
                    icon: "microscope"
                    iconColor: AppColors.experiment(row.index)
                    toolTip: qsTr("Measured pattern color")
                }
                // How the project's last fit ended on this experiment; "Not fitted" when it took no part.
                IconCell {
                    horizontalAlignment: Text.AlignHCenter
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
                    horizontalAlignment: Text.AlignLeft
                    value: row.name
                    onActiveFocusChanged: if (activeFocus)
                        group.project.currentExperimentIndex = row.index
                    onCommitted: text => row.experiment.name = text
                }
                // The data's file: the experiment's own `.edi`, which holds its data, or a scan dataset's data file,
                // the template dataset's followed by the word "template" in the accent blue, as in the selector;
                // Load data… without data.
                Item {
                    id: fileCell

                    property int horizontalAlignment: Text.AlignLeft
                    height: parent ? parent.height : 0

                    Row {
                        height: parent.height
                        spacing: EaStyle.Sizes.fontPixelSize * 0.5
                        visible: !loadData.visible

                        EaComponents.ListViewLabel {
                            width: Math.min(implicitWidth, fileCell.width - (templateTag.visible ? templateTag.width + parent.spacing : 0))
                            height: parent.height
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideMiddle
                            text: row.file
                        }
                        EaComponents.ListViewLabel {
                            id: templateTag
                            objectName: `experiments.template.${row.index}`
                            visible: group.scan && row.isTemplate
                            width: implicitWidth
                            height: parent.height
                            elide: Text.ElideNone
                            color: EaStyle.Colors.themeAccent
                            text: qsTr("template")
                        }
                    }
                    // The file name as left-aligned text that loads another file in its place: the accent blue and a
                    // pointing hand on hover, and "Load data…" in the accent blue before any data (the owner,
                    // 2026-10-11). Every experiment but a scan's dataset can load data.
                    EaComponents.ListViewLabel {
                        id: loadData

                        readonly property bool empty: row.experiment !== null && row.experiment.calculationOnly

                        signal clicked

                        objectName: `experiments.loadData.${row.index}`
                        visible: !group.scan && row.experiment !== null && row.experiment.canLoadData
                        width: Math.min(implicitWidth, fileCell.width)
                        height: parent.height
                        horizontalAlignment: Text.AlignLeft
                        elide: Text.ElideMiddle
                        color: empty || loadDataHover.hovered ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
                        text: empty ? qsTr("Load data…") : row.file
                        onClicked: group.chooseData(row.experiment)

                        HoverHandler {
                            id: loadDataHover
                            cursorShape: Qt.PointingHandCursor
                        }
                        TapHandler {
                            onTapped: loadData.clicked()
                        }
                        EaElements.ToolTip {
                            text: qsTr("Load another data file in place of this one")
                            visible: loadDataHover.hovered && EaGlobals.Vars.showToolTips
                        }
                    }
                }
                // What the scan's extract rules take from the dataset, with their units.
                Item {
                    property int horizontalAlignment: Text.AlignHCenter
                    visible: group.scanColumns.length > 0
                    height: parent.height
                    Row {
                        height: parent.height
                        Repeater {
                            property int horizontalAlignment: Text.AlignHCenter
                            model: group.scanColumns.length
                            delegate: Item {
                                id: value
                                required property int index
                                property int horizontalAlignment: Text.AlignHCenter
                                width: AppSizes.dataColumnWidth * 1.4
                                height: EaStyle.Sizes.tableRowHeight
                                NumberLabel {
                                    anchors.fill: parent
                                    horizontalAlignment: value.horizontalAlignment
                                    number: row.extracted && row.extracted.length > value.index ? row.extracted[value.index] : ""
                                }
                            }
                        }
                    }
                }
                EaComponents.ListViewButton {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `experiments.remove.${row.index}`
                    visible: !group.scan
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

        // Load, Create and Duplicate side by side at equal widths (the owner, 2026-10-11).
        Row {
            id: buttons

            readonly property real buttonWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * spacing) / 3

            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                objectName: "experiments.load"
                width: buttons.buttonWidth
                enabled: group.project !== null
                fontIcon: "upload"
                text: qsTr("Load experiment")
                ToolTip.text: qsTr("Load experiments from .edi files, each with its type, data and parameters")
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
                objectName: "experiments.create"
                width: buttons.buttonWidth
                enabled: group.project !== null && group.project.canCreateExperiment
                fontIcon: "plus-circle"
                text: qsTr("Create experiment")
                ToolTip.text: enabled ? qsTr("Add an experiment without data, to calculate its pattern or load data into") : qsTr("A scan project fits its one template experiment")
                onClicked: group.project.createExperiment()
            }
            // A copy of the selected experiment with its data, named <name>_copy; its Data file cell then loads
            // another file in place of the copied one.
            EaElements.SideBarButton {
                objectName: "experiments.duplicate"
                width: buttons.buttonWidth
                enabled: group.project !== null && group.project.canCreateExperiment && group.project.currentExperiment !== null
                fontIcon: "clone"
                text: qsTr("Duplicate experiment")
                ToolTip.text: group.scan ? qsTr("A scan project fits its one template experiment") : qsTr("Add a copy of the selected experiment, with its data")
                onClicked: group.project.duplicateExperiment()
            }
        }
    }

    // Load data… for `experiment`: the file dialog, or in the browser the page's file chooser. The answer goes to
    // that experiment wherever its row is by then, and is refused if it has gone.
    readonly property string dataFilter: ".xye,.xy,.dat,.txt,.csv,.int"
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

    // This page's browser file request and the project it was made for: only its own answer is used, and only
    // while that project is still open. `webDataExperiment`: the experiment a Load data… request is for, or null
    // for Load experiment.
    property int webRequest: 0
    property var webRequestProject: null
    property var webDataExperiment: null
    Connections {
        target: WebFiles
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
        function onFailed(request) {
            if (request === group.webRequest) {
                group.webRequest = 0;
                group.webDataExperiment = null;
            }
        }
        function onCancelled(request) {
            if (request === group.webRequest) {
                group.webRequest = 0;
                group.webDataExperiment = null;
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
        property var experiment: null
        property var project: null
        title: dataDialog.experiment && dataDialog.experiment.sampleForm === ExperimentViewModel.SingleCrystal ? qsTr("Load measured reflections from FullProf's .int or a plain h k l F² su file (.hkl, .dat or any other)") : qsTr("Load measured data from a plain two- or three-column file")
        nameFilters: dataDialog.experiment && dataDialog.experiment.sampleForm === ExperimentViewModel.SingleCrystal ? [qsTr("Reflection files (*.int *.hkl *.dat *.txt)"), qsTr("All files (*)")] : [qsTr("Data files (*.xye *.xy *.dat *.txt *.csv)"), qsTr("All files (*)")]
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
