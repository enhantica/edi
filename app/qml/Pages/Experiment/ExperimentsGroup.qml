// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

import EasyApplication.Gui.Globals as EaGlobals
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

        ExperimentTypeGroup {
            visible: group.project !== null && group.project.currentExperiment !== null
            project: group.project
            experiment: group.project ? group.project.currentExperiment : null
            experimentIndex: group.project ? group.project.currentExperimentIndex : -1
        }
        // A scan's template is chosen here: the selected dataset becomes it (the owner, 2026-11-04).
        EaElements.SideBarButton {
            objectName: "experiments.useAsTemplate"
            visible: group.scan
            width: EaStyle.Sizes.sideBarContentWidth
            enabled: group.project !== null && group.project.currentExperimentIndex >= 0 && group.project.currentExperimentIndex !== group.project.templateIndex
            fontIcon: "star"
            text: qsTr("Use as template")
            ToolTip.text: qsTr("Make the selected dataset the scan's template: the template experiment takes its data")
            onClicked: group.project.useAsTemplate(group.project.currentExperimentIndex)
        }

        // A scan whose data folder cannot be found (ADR-0069): the project still opens; this line says which folder
        // and Locate folder… points the scan at its new place.
        Row {
            objectName: "experiments.dataNotFound"
            visible: group.project !== null && group.project.missingDataFolder !== ""
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                width: EaStyle.Sizes.sideBarContentWidth - locateButton.width - parent.spacing
                wrapMode: Text.Wrap
                color: EaStyle.Colors.red
                text: group.project !== null ? qsTr("Data not found: %1").arg(group.project.missingDataFolder) : ""
            }
            EaElements.Button {
                id: locateButton
                objectName: "experiments.locateFolder"
                text: qsTr("Locate folder…")
                onClicked: locateDialog.open()
            }
        }
        FolderDialog {
            id: locateDialog
            title: qsTr("Locate the scan's data folder")
            onAccepted: {
                if (group.project !== null)
                    group.project.locateDataFolder(selectedFolder);
            }
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
                EaElements.ToolTip {
                    text: qsTr("Load a full experiment, or measured data into the selected one, from a file or from the web")
                    visible: loadButton.hovered && EaGlobals.Vars.showToolTips
                }
                onClicked: loadMenu.open()

                EaElements.Menu {
                    id: loadMenu
                    objectName: "experiments.load.menu"
                    y: loadButton.height
                    // Nothing below the last item (the owner, 2026-11-04).
                    bottomPadding: 0
                    width: Math.max(loadButton.width, EaStyle.Sizes.fontPixelSize * 24)

                    readonly property ExperimentViewModel selected: group.project ? group.project.currentExperiment : null

                    LoadMenuHeader {
                        first: true
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
                    // Measured data goes into the selected experiment, or replaces what it holds (the owner, 2026-11-04):
                    // a new experiment always starts from Create experiment. With none selected the line says so and
                    // the two items are greyed.
                    readonly property bool dataIntoSelected: loadMenu.selected !== null && loadMenu.selected.canLoadData
                    readonly property bool replacing: loadMenu.selected !== null && !loadMenu.selected.calculationOnly
                    LoadMenuHeader {
                        objectName: "experiments.load.dataHeader"
                        // Guidance in the warning orange, as the Messages count (the owner, 2026-11-04).
                        color: loadMenu.selected === null ? EaStyle.Colors.red : EaStyle.Colors.themeForeground
                        text: loadMenu.selected === null ? qsTr("Create an experiment first to load data into it") : loadMenu.replacing ? qsTr("Replace measured data of %1").arg(loadMenu.selected.name) : qsTr("Load measured data into %1").arg(loadMenu.selected.name)
                    }
                    LoadMenuItem {
                        objectName: "experiments.load.dataFile"
                        enabled: loadMenu.dataIntoSelected
                        fontIcon: "file"
                        text: qsTr("From file…")
                        hint: ".xye .xy .dat .txt .csv · .int .hkl"
                        toolTip: loadMenu.selected === null ? qsTr("Create an experiment first to load data into it") : loadMenu.replacing ? qsTr("Replace the measured data of %1 with a file's; its type and parameters stay, Undo brings the data back").arg(loadMenu.selected.name) : qsTr("Load a measured pattern or reflection list into %1").arg(loadMenu.selected.name)
                        onTriggered: group.confirmScanReplacement(() => group.chooseDataForSelected())
                    }
                    LoadMenuItem {
                        objectName: "experiments.load.dataWeb"
                        enabled: loadMenu.dataIntoSelected
                        fontIcon: "globe"
                        text: qsTr("From web…")
                        hint: "EasyDiffraction"
                        toolTip: loadMenu.selected === null ? qsTr("Create an experiment first to load data into it") : qsTr("Search EasyDiffraction's collection for measured data for %1").arg(loadMenu.selected.name)
                        onTriggered: {
                            const target = loadMenu.selected;
                            group.confirmScanReplacement(() => onlineLoad.openFor("data", target));
                        }
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
        onDatasetsReady: (files, experiment) => {
            if (experiment !== null && group.project !== null)
                group.askDatasets(experiment, files);
        }
    }

    // Measured data goes into the selected experiment (the owner, 2026-11-04); the menu offers it only then.
    // Measured data loaded into a scan project replaces its scan (the owner, 2026-11-04): asked first, then `proceed`.
    function confirmScanReplacement(proceed) {
        if (!group.scan) {
            proceed();
            return;
        }
        const dialog = scanReplaceComponent.createObject(Overlay.overlay, {
            proceed: proceed
        }) as AppDialog;
        dialog.open();
    }

    function chooseDataForSelected() {
        if (project !== null && project.currentExperiment !== null)
            chooseData(project.currentExperiment);
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
        // Several files at once (the owner, 2026-11-04): more than one asks how to load them.
        fileMode: FileDialog.OpenFiles
        onAccepted: {
            if (selectedFiles.length > 1 && dataDialog.experiment !== null && dataDialog.project === group.project) {
                const experiment = dataDialog.experiment;
                const files = selectedFiles;
                dataDialog.intent = null;
                group.askDatasets(experiment, files);
                return;
            }
            ApplicationInfo.acceptExperimentDataFile();
        }
        onRejected: ApplicationInfo.rejectExperimentDataFile()
    }

    // Load N datasets as (the owner, 2026-11-04): separate experiments, each a copy of the selected experiment's setup
    // named after its file, or one experiment with a scan, the selected experiment its template and the files its
    // datasets. Up to five files default to separate experiments, more to a scan.
    function askDatasets(experiment, files) {
        // Copied by default for a small set, linked above 20 files or 50 MB (the owner, 2026-11-04).
        const dialog = datasetsComponent.createObject(Overlay.overlay, {
            experiment: experiment,
            files: files,
            asScan: files.length > 5,
            copy: files.length <= 20 && group.project.filesBytes(files) <= 50 * 1024 * 1024
        }) as AppDialog;
        dialog.open();
    }

    // Made only while it is asked and destroyed once closed. A Component is no item of the group: the group sizes to
    // its one content column, and a second item (a Loader) left it an empty strip.
    Component {
        id: scanReplaceComponent
        AppDialog {
            id: scanReplace
            objectName: "datasets.replaceScan"
            property var proceed: null
            title: qsTr("Replace the scan")
            standardButtons: Dialog.Ok | Dialog.Cancel
            contentWidth: AppSizes.messagesDialogContentWidth
            onClosed: destroy()
            onAccepted: if (scanReplace.proceed)
                scanReplace.proceed()

            EaElements.Label {
                width: scanReplace.contentWidth
                wrapMode: Text.Wrap
                text: qsTr("This project is a scan. Loading measured data replaces its scan; Undo brings it back.")
            }
        }
    }
    Component {
        id: datasetsComponent
        AppDialog {
            id: datasetsChoice
            objectName: "datasets.choice"
            property var files: []
            property ExperimentViewModel experiment: null
            property bool asScan: false
            property bool copy: true
            title: qsTr("Load %1 datasets as").arg(files.length)
            standardButtons: Dialog.Ok | Dialog.Cancel
            contentWidth: AppSizes.messagesDialogContentWidth
            contentHeight: datasetsColumn.implicitHeight
            onClosed: destroy()
            onAccepted: {
                if (group.project !== null && datasetsChoice.experiment !== null)
                    group.project.loadDatasets(datasetsChoice.experiment, datasetsChoice.files, datasetsChoice.asScan, datasetsChoice.copy);
            }

            Column {
                id: datasetsColumn
                width: datasetsChoice.contentWidth
                spacing: EaStyle.Sizes.fontPixelSize * 0.5

                ChoiceRadioButton {
                    id: jointChoice
                    objectName: "datasets.separate"
                    // Named by the fit each choice is for (the owner, 2026-11-04).
                    text: qsTr("Joint fit: one experiment per file, fitted together")
                    checked: !datasetsChoice.asScan
                    onClicked: datasetsChoice.asScan = false
                }
                ChoiceRadioButton {
                    objectName: "datasets.scan"
                    text: qsTr("Sequential fit: the first dataset is the template for the initial fit. When it is ready, switch to sequential mode yourself.")
                    checked: datasetsChoice.asScan
                    onClicked: datasetsChoice.asScan = true
                }
                EaElements.CheckBox {
                    id: copyBox
                    objectName: "datasets.copy"
                    // What the choice means is its tool tip, shown when tool tips are on (the owner, 2026-11-04).
                    ToolTip.text: datasetsChoice.copy ? qsTr("The files are copied into the project's folder; the project must be saved and hold this one experiment.") : qsTr("The scan reads the files where they are; the project keeps their folder's location.")
                    ToolTip.visible: copyBox.hovered && EaGlobals.Vars.showToolTips
                    visible: datasetsChoice.asScan
                    // The same spacing as between the two choices.
                    height: jointChoice.height
                    text: qsTr("Copy data into the project")
                    checked: datasetsChoice.copy
                    onToggled: datasetsChoice.copy = checked
                }
            }
        }
    }
}
