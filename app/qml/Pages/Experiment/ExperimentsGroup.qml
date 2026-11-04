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
// data, a simulation). A row made with Create experiment reads Load data… in its Data file cell until data is loaded
// into it: a plain two- or three-column file whose rows become its measured data. Clicking a file name loads another
// file in its place. Create, Load and Load data are each one undoable step.
SideBarGroup {
    id: group
    property var pickerLife: ({
            alive: true
        })
    Component.onDestruction: ApplicationInfo.formPickerDestroyed()

    property ProjectViewModel project: null
    // A scan project lists its datasets: No. · Fit · Datablock · File · one column per extract rule, with no
    // colour column and no remove button (one template experiment shows them all).
    readonly property bool scan: project !== null && project.scan
    // One column per extract rule, with its unit, from the table's own model. The table lays a row's cells out
    // by their place among the header's, so the header and each row repeat over the same list.
    readonly property var scanColumns: project ? project.experiments.columns : []
    // The Fit column is as wide as its title or its icon, so the Fit icon sits as close to the colour icon as the
    // Structures table's icon to its name: one margin between them, not each column's own (the owner, 2026-10-11). A
    // right margin as wide as a table's edge margin then keeps the datablock names off it (the owner, 2026-10-24).
    readonly property real fitColumnWidth: Math.ceil(Math.max(fitTitle.advanceWidth, EaStyle.Sizes.fontPixelSize * 1.15)) + EaStyle.Sizes.tableColumnSpacing

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
            onRowActivated: row => ApplicationInfo.activateFormBlock(row, false)

            columns: [numberColumnWidth, group.scan ? 0.001 : AppSizes.iconOnlyColumnWidth, group.scan ? AppSizes.iconOnlyColumnWidth : group.fitColumnWidth, -1, -1, group.scanColumns.length ? group.scanColumns.length * AppSizes.dataColumnWidth * 1.4 : 0.001, group.scan ? 0.001 : AppSizes.iconColumnWidth]

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
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
                    horizontalAlignment: Text.AlignLeft
                    objectName: `experiments.fit.${row.index}`
                    icon: FitOutcomes.icon(row.fitOutcome)
                    iconColor: String(FitOutcomes.color(row.fitOutcome))
                    ring: FitOutcomes.ring(row.fitOutcome)
                    toolTip: FitOutcomes.word(row.fitOutcome)
                }
                // The datablock name, editable: a refused rename returns the cell to the stored name and shows why.
                // Editing a name also makes its row current, as a click on the row does.
                TextCell {
                    editMember: row
                    editModel: group.project ? group.project.experiments : null
                    editIndex: row.index
                    objectName: `experiments.name.${row.index}`
                    horizontalAlignment: Text.AlignLeft
                    value: row.name
                    onActiveFocusChanged: ApplicationInfo.finishUiEvent(12, undefined)
                    onCommitted: text => row.experiment.name = text
                }
                // The data's file: the experiment's own `.edi`, which holds its data, or a scan dataset's data file,
                // the template dataset's followed by the word "template" in the accent blue, as in the selector;
                // Load data… without data.
                Item {
                    id: fileCell

                    property int horizontalAlignment: Text.AlignLeft
                    height: parent ? parent.height : 0

                    // The data file's name, or that there is none yet: loading moved to the Load menu below (the
                    // owner, 2026-11-03).
                    Row {
                        height: parent.height
                        spacing: EaStyle.Sizes.fontPixelSize * 0.5

                        EaComponents.ListViewLabel {
                            readonly property bool empty: row.experiment !== null && row.experiment.calculationOnly

                            objectName: `experiments.file.${row.index}`
                            width: Math.min(implicitWidth, fileCell.width - (templateTag.visible ? templateTag.width + parent.spacing : 0))
                            height: parent.height
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideMiddle
                            color: empty ? EaStyle.Colors.themeForegroundMinor : EaStyle.Colors.themeForeground
                            text: empty ? qsTr("— no data yet") : row.file
                            ToolTip.text: empty ? qsTr("Load measured data with the Load button below") : row.file
                        }
                        EaComponents.ListViewLabel {
                            id: templateTag
                            objectName: `experiments.template.${row.index}`
                            visible: group.scan && row.isTemplate
                            width: implicitWidth
                            height: parent.height
                            elide: Text.ElideNone
                            color: EaStyle.Colors.themeAccent
                            text: Session.label("sequential_fit.template_file")
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

        // With no experiment selected the selectors show the type a new one takes with its measured data.
        ExperimentTypeGroup {
            visible: group.project !== null && (group.project.currentExperiment !== null || (!group.scan && group.project.canCreateExperiment))
            project: group.project
            experiment: group.project ? group.project.currentExperiment : null
            experimentIndex: group.project ? group.project.currentExperimentIndex : -1
        }

        // Load ▾, Create and Duplicate side by side at equal widths (the owner, 2026-10-11, 2026-11-03). The Load menu
        // holds a full experiment and measured data for the selected experiment, each from a file or from the web.
        Row {
            id: buttons

            readonly property real buttonWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * spacing) / 3

            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                id: loadButton
                objectName: "experiments.load"
                width: buttons.buttonWidth
                enabled: group.project !== null
                fontIcon: "upload"
                text: qsTr("Load")

                // The menu's caret, from the icon font: the text fonts have no such character.
                EaElements.Label {
                    anchors.right: parent.right
                    anchors.rightMargin: EaStyle.Sizes.fontPixelSize * 0.75
                    anchors.verticalCenter: parent.verticalCenter
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.9
                    color: loadButton.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
                    text: "caret-down"
                }
                ToolTip.text: qsTr("Load a full experiment, or measured data into the selected one, from a file or from the web")
                onClicked: loadMenu.open()

                EaElements.Menu {
                    id: loadMenu
                    objectName: "experiments.load.menu"
                    y: loadButton.height
                    width: Math.max(loadButton.width, EaStyle.Sizes.fontPixelSize * 24)

                    readonly property ExperimentViewModel selected: group.project ? group.project.currentExperiment : null

                    LoadMenuHeader {
                        text: qsTr("Full experiment")
                    }
                    LoadMenuItem {
                        objectName: "experiments.load.experimentFile"
                        fontIcon: "file"
                        text: qsTr("From file…")
                        hint: ".edi .cif"
                        toolTip: qsTr("Load experiments from .edi or CIF files, each with its type, data and parameters")
                        // In the browser the files come through the page (edi ADR-0023).
                        onTriggered: ApplicationInfo.loadFormFiles(true)
                    }
                    LoadMenuItem {
                        objectName: "experiments.load.experimentWeb"
                        fontIcon: "globe"
                        text: qsTr("From web…")
                        hint: "EasyDiffraction"
                        toolTip: qsTr("Search EasyDiffraction's collection for a full experiment and open it")
                        onTriggered: onlineLoad.openFor("experiment", null)
                    }
                    LoadMenuHeader {
                        text: loadMenu.selected !== null ? qsTr("Measured data into %1").arg(loadMenu.selected.name) : qsTr("Measured data into a new experiment")
                    }
                    LoadMenuItem {
                        objectName: "experiments.load.dataFile"
                        enabled: !group.scan && (loadMenu.selected === null ? group.project !== null && group.project.canCreateExperiment : loadMenu.selected.canLoadData)
                        fontIcon: "file"
                        text: qsTr("From file…")
                        hint: ".xye .xy .dat .txt .csv · .int .hkl"
                        toolTip: loadMenu.selected !== null ? qsTr("Load a measured pattern or reflection list into %1").arg(loadMenu.selected.name) : qsTr("Create an experiment from the type selectors and load its measured data")
                        onTriggered: group.chooseDataForSelected()
                    }
                    LoadMenuItem {
                        objectName: "experiments.load.dataWeb"
                        enabled: !group.scan && (loadMenu.selected === null ? group.project !== null && group.project.canCreateExperiment : loadMenu.selected.canLoadData)
                        fontIcon: "globe"
                        text: qsTr("From web…")
                        hint: "EasyDiffraction"
                        toolTip: qsTr("Search EasyDiffraction's collection for measured data")
                        onTriggered: onlineLoad.openFor("data", loadMenu.selected)
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

    OnlineLoadDialog {
        id: onlineLoad
        project: group.project
    }

    // Measured data from a file for the selected experiment, or for a new one when none is selected: the new
    // experiment is made only once a file is chosen and read, so a cancelled picker or a refused file leaves the
    // project as it was.
    function chooseDataForSelected() {
        if (project === null)
            return;
        if (project.currentExperiment !== null) {
            chooseData(project.currentExperiment);
            return;
        }
        if (WebFiles.available) {
            newDataRequest = WebFiles.openFiles(dataFilter, false);
            newDataProject = project;
        } else {
            newDataDialog.project = project;
            newDataDialog.open();
        }
    }

    // The browser's answer for a new experiment's data: only this request's, and only for the project it was
    // made for while that project is still the open one.
    property int newDataRequest: 0
    property var newDataProject: null
    Connections {
        target: WebFiles
        function onFilesOpened(request, files) {
            if (request !== group.newDataRequest || request === 0)
                return;
            group.newDataRequest = 0;
            if (group.project !== null && group.project === group.newDataProject && files.length > 0)
                group.project.loadDataIntoNewExperiment(files[0]);
            group.newDataProject = null;
        }
        function onCancelled(request) {
            if (request === group.newDataRequest) {
                group.newDataRequest = 0;
                group.newDataProject = null;
            }
        }
    }
    FileDialog {
        id: newDataDialog
        property var project: null
        title: group.project !== null && group.project.newExperimentSampleFormToken === "single crystal" ? qsTr("Load measured reflections for a new experiment") : qsTr("Load measured data for a new experiment")
        nameFilters: group.project !== null && group.project.newExperimentSampleFormToken === "single crystal" ? [qsTr("Reflection files (*.int *.hkl *.dat *.txt)")] : [qsTr("Pattern files (*.xye *.xy *.dat *.txt *.csv)")]
        onAccepted: {
            if (group.project !== null && group.project === newDataDialog.project)
                group.project.loadDataIntoNewExperiment(selectedFile);
            newDataDialog.project = null;
        }
        onRejected: newDataDialog.project = null
    }

    // Load data… for `experiment`: the file dialog, or in the browser the page's file chooser. The answer goes to
    // that experiment wherever its row is by then, and is refused if it has gone.
    readonly property string dataFilter: ".xye,.xy,.dat,.txt,.csv,.int,.hkl"
    function chooseData(experiment) {
        ApplicationInfo.chooseExperimentData(experiment);
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
            ApplicationInfo.formFilesOpened(request, files, true);
        }
        function onFailed(request) {
            ApplicationInfo.formFilesCancelled(request, true);
        }
        function onCancelled(request) {
            ApplicationInfo.formFilesCancelled(request, true);
        }
    }

    FileDialog {
        id: loadDialog
        title: qsTr("Load experiments from CIF or .edi files")
        fileMode: FileDialog.OpenFiles
        nameFilters: [qsTr("Experiment files (*.cif *.edi)"), qsTr("CIF files (*.cif)"), qsTr("edi block files (*.edi)")]
        onAccepted: group.project.loadExperiments(selectedFiles)
    }

    // The dialog's answer goes to the experiment and the project it was opened for, and only while that project
    // is still the open one.
    FileDialog {
        id: dataDialog
        property var intent: null
        property var experiment: null
        property var project: null
        title: dataDialog.experiment && dataDialog.experiment.sampleForm === ExperimentViewModel.SingleCrystal ? qsTr("Load measured reflections from FullProf's .int or a plain h k l F² su file (.hkl, .dat or any other)") : qsTr("Load measured data from a plain two- or three-column file")
        nameFilters: dataDialog.experiment && dataDialog.experiment.sampleForm === ExperimentViewModel.SingleCrystal ? [qsTr("Reflection files (*.int *.hkl *.dat *.txt)"), qsTr("All files (*)")] : [qsTr("Data files (*.xye *.xy *.dat *.txt *.csv)"), qsTr("All files (*)")]
        onAccepted: ApplicationInfo.acceptExperimentDataFile()
        onRejected: ApplicationInfo.rejectExperimentDataFile()
    }
}
