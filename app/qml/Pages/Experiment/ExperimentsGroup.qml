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
// the table the selected experiment's type (ExperimentTypeGroup), then Create experiment (a new experiment without
// data, a simulation) and Load experiment (`.edi` block files, several at once, each with its type, data and
// parameters). Each row's Data file cell loads its measured data: Load data… ▾ while it has none, the file's name and
// ⋯ to replace it once it has (the owner, 2026-11-16). A series of joint fits lists a row per run, "5 banks" in its
// Data file cell; its banks are chosen with the Bank selector in the main view. Start marks the experiment a scan starts from. Create, Load and Load data are each one undoable step.
SideBarGroup {
    id: group
    property var pickerLife: ({
            alive: true
        })

    property ProjectViewModel project: null
    // Its page and sidebar tab are current; open, its table is on screen and a scan's rows get their values read
    // (ProjectViewModel.setExperimentListShown, edi ADR-0102 rule 6).
    property bool pageShown: false
    readonly property bool listShown: pageShown && !collapsed
    function reportListShown(): void {
        if (project)
            project.setExperimentListShown(group, listShown);
    }
    onListShownChanged: reportListShown()
    onProjectChanged: reportListShown()
    Component.onDestruction: {
        ApplicationInfo.formPickerDestroyed();
        if (project)
            project.setExperimentListShown(group, false);
    }
    // A scan project lists its datasets: No. · Fit · Datablock · File · one column per extract rule, with no
    // colour column and no remove button (one template experiment shows them all).
    readonly property bool scan: project !== null && project.scan
    // A series of joint fits (edi ADR-0088): a row per run, as a scan's files; its banks are chosen in the main view.
    readonly property bool series: project !== null && project.series
    // One column per extract rule, with its unit, from the table's own model. The table lays a row's cells out
    // by their place among the header's, so the header and each row repeat over the same list.
    readonly property var scanColumns: project ? project.experiments.columns : []
    // The Start and Fit columns are as wide as their titles or their boxes, with a cell's margin on both sides (T1).
    readonly property real startColumnWidth: Math.ceil(startTitle.advanceWidth) + AppSizes.tableCellMargin * 2
    // Its header or its check box, whichever is wider (the check box replaced the outcome icon, the owner, 2026-11-17).
    readonly property real fitColumnWidth: Math.ceil(Math.max(fitTitle.advanceWidth, EaStyle.Sizes.fontPixelSize * 1.7)) + AppSizes.tableCellMargin * 2

    objectName: "group.experiments"
    title: qsTr("Experiments (%1)").arg(project ? project.experiments.count : 0)
    icon: "microscope"
    last: SideBarGroups.isLast(group)
    // Open at the start, unlike the category groups (owner, 2026-10-05; edi ADR-0017 §3).
    collapsed: false

    TextMetrics {
        id: startTitle
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        text: qsTr("Start")
    }
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
            defaultInfoText: qsTr("No experiments yet")
            sourceModel: group.project ? group.project.experiments : null
            marksCurrentRow: true
            currentRow: group.project ? group.project.currentExperimentIndex : -1
            onRowActivated: row => ApplicationInfo.activateFormBlock(row, false)

            // A rename or loaded data measures the names again; a scan's other changes, hundreds of them, do not.
            property var rowTexts: []
            function readRow(row: int): string {
                const rows = group.project.experiments;
                return rows.text(row, "name") + "\n" + rows.text(row, "file") + (table.empty(row) ? "\n" : "");
            }
            onCountChanged: rowTexts = group.project ? Array.from({
                length: count
            }, (_, row) => readRow(row)) : []
            Connections {
                target: group.project ? group.project.experiments : null
                function onDataChanged(topLeft, bottomRight) {
                    let changed = false;
                    for (let row = topLeft.row; row <= bottomRight.row; ++row) {
                        const text = table.readRow(row);
                        changed = changed || table.rowTexts[row] !== text;
                        table.rowTexts[row] = text;
                    }
                    if (changed)
                        table.remeasure();
                }
            }
            // The row's room beside the columns of one width: what the name, the data file and the scan values share.
            readonly property real sharedRoom: {
                const own = [numberColumnWidth, group.scan && !group.series ? group.startColumnWidth : 0, AppSizes.tableControlWidth, group.fitColumnWidth, group.scan ? 0 : controlColumnWidth].filter(column => column > 0);
                const columns = own.length + 2 + (group.scanColumns.length > 0 ? 1 : 0);
                return width - 2 * rowPadding - own.reduce((sum, column) => sum + column, 0) - (columns - 1) * EaStyle.Sizes.tableColumnSpacing;
            }
            // Whether a row shows the Load data button rather than its file.
            function empty(row: int): bool {
                const experiment = group.project && !group.scan ? group.project.experiments.item(row, "experiment") as ExperimentViewModel : null;
                return experiment !== null && experiment.calculationOnly;
            }
            // The widest of the first rows' names or files, each cut in its middle to ten characters (T10), half a dozen at
            // each end and the ellipsis, or whole.
            function widestText(role: string, title: string, cut: bool): real {
                let widest = modelRevision >= 0 ? advance(title) : 0;
                for (let row = 0; row < Math.min(count, measuredAtOnce); ++row) {
                    const text = group.project ? group.project.experiments.text(row, role) : "";
                    const whole = advance(text);
                    const shown = cut && text.length > 12 ? Math.min(whole, advance(text.slice(0, 6) + "…" + text.slice(-6))) : whole;
                    // A file's More button after it, less the gap round its box, or the button that loads one.
                    const tail = role === "name" || group.scan ? 0 : EaStyle.Sizes.fontPixelSize * 0.5 + EaStyle.Sizes.tableRowHeight - 2;
                    widest = Math.max(widest, role === "file" && table.empty(row) ? advance(qsTr("Load data…")) + EaStyle.Sizes.fontPixelSize * 1.2 : shown + tail);
                }
                return Math.ceil(widest) + 2 * AppSizes.tableCellMargin;
            }
            readonly property real nameLeast: widestText("name", qsTr("Datablock"), true)
            // The data file column at its narrowest, and with every file's name whole (T5), a scan's Start word after it too.
            readonly property real fileLeast: widestText("file", qsTr("Data file"), true)
            readonly property real fileNatural: widestText("file", qsTr("Data file"), false) + (group.scan ? Math.ceil(EaStyle.Sizes.fontPixelSize * 0.5 + advance(qsTr("Start"))) : 0)
            // The row's room as the names, the data files and the scan values take it, the values one em apart (T1). Where it
            // does not hold them all, the values narrow first, their numbers with fewer digits, then the files and then the
            // names give way down to ten characters (T10). A row narrower than that closes the gaps between the values,
            // then shortens the files and the names further, since a number is never cut (T8); nothing passes the edge.
            readonly property var shares: {
                const values = group.scanColumns.length;
                let gap = contentGap;
                const room = () => sharedRoom - (values > 0 ? 2 * AppSizes.tableCellMargin + (values - 1) * gap : 0);
                const most = Math.ceil(Math.max(...group.scanColumns.concat("0000.000 K").map(text => advance(text))));
                const names = naturalTextColumnWidth("name", qsTr("Datablock"));
                let value = values > 0 ? Math.min(most, Math.max(Math.ceil(advance("000 K")), Math.floor((room() - names - fileNatural) / values))) : 0;
                let file = Math.max(fileLeast, Math.min(fileNatural, room() - values * value - names));
                let name = Math.max(nameLeast, Math.min(names, room() - values * value - file));
                const over = () => Math.max(0, name + file + values * value - room());
                if (values > 1)
                    gap = Math.max(EaStyle.Sizes.tableColumnSpacing, gap - Math.ceil(over() / (values - 1)));
                const shortest = EaStyle.Sizes.fontPixelSize * 3;
                file = Math.max(Math.min(file, shortest), file - over());
                name = Math.max(Math.min(name, shortest), name - over());
                if (values > 0)
                    value = Math.max(0, value - Math.ceil(over() / values));
                file = Math.max(0, file - over());
                return {
                    "name": name,
                    "file": file,
                    "value": value,
                    "gap": gap,
                    "values": values > 0 ? values * value + (values - 1) * gap + 2 * AppSizes.tableCellMargin : 0
                };
            }
            onSharesChanged: Qt.callLater(combineWidths)
            readonly property real nameColumnWidth: shares.name
            readonly property real fileColumnWidth: shares.file
            readonly property real valueWidth: shares.value
            readonly property real valuesWidth: shares.values
            insetButtons: true
            // The columns above are whole, their margins included.
            autoColumnPadding: 0
            // Datablock as wide as its widest name (ADR-0103 T5): a narrow row cuts the data file, never the datablock, and
            // the room goes to the data file and the scan values.
            columns: [numberColumnWidth, group.scan && !group.series ? group.startColumnWidth : 0.001, AppSizes.tableControlWidth, group.fitColumnWidth, nameColumnWidth, group.scanColumns.length ? fileColumnWidth : -1, group.scanColumns.length ? -1 : 0.001, group.scan ? 0.001 : controlColumnWidth]
            // No column is measured from its rows, so a scan's rows changing one by one never measure rows again (ADR-0103
            // rule 4); the data file's long paths elide.
            columnTypes: ["", "", "", "", "", "", "", ""]

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }
                // Shown with its cells and hidden with them where there is no Start, so neither row places a spacing
                // for a column of no width (the owner, 2026-11-17).
                EaComponents.ListViewLabel {
                    visible: group.scan && !group.series
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Start")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Fit")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Datablock")
                }
                EaComponents.ListViewLabel {
                    readonly property real reservedWidth: table.fileColumnWidth
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Data file")
                }
                // Keep the scan's repeated cells in one width-controlled column (ADR-0029).
                Item {
                    readonly property real reservedWidth: table.valuesWidth
                    property int horizontalAlignment: Text.AlignHCenter
                    visible: group.scanColumns.length > 0
                    height: parent.height
                    Row {
                        x: AppSizes.tableCellMargin
                        height: parent.height
                        spacing: table.shares.gap
                        Repeater {
                            property int horizontalAlignment: Text.AlignHCenter
                            model: group.scanColumns
                            delegate: Item {
                                id: column
                                required property string modelData
                                property int horizontalAlignment: Text.AlignHCenter
                                width: table.valueWidth
                                height: EaStyle.Sizes.tableRowHeight
                                // A scan value fitted to its column, in full on hover (NumberLabel).
                                NumberLabel {
                                    anchors.fill: parent
                                    horizontalAlignment: column.horizontalAlignment
                                    number: column.modelData
                                }
                            }
                        }
                    }
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    visible: !group.scan
                }
            }

            delegate: TableRow {
                id: row

                // A row in the table's visible part has its scan values read while the group shows
                // (watchExperimentRow, rule 6), under its index now, released with the project it was registered with.
                readonly property ListView ownList: ListView.view
                readonly property bool inView: ownList !== null && y + height > ownList.contentY && y < ownList.contentY + ownList.height
                property int watching: -1
                property var watchedProject: null
                function rewatch(): void {
                    if (watchedProject && watching >= 0)
                        watchedProject.watchExperimentRow(group, watching, false);
                    watchedProject = inView ? group.project : null;
                    watching = watchedProject ? row.index : -1;
                    if (watchedProject)
                        watchedProject.watchExperimentRow(group, watching, true);
                }
                onIndexChanged: rewatch()
                onInViewChanged: rewatch()
                Connections {
                    target: group
                    function onProjectChanged() {
                        row.rewatch();
                    }
                }
                Component.onCompleted: rewatch()
                Component.onDestruction: if (watchedProject && watching >= 0)
                    watchedProject.watchExperimentRow(group, watching, false)

                required property string name
                required property ExperimentViewModel experiment
                required property string fitOutcome
                required property string file
                required property var extracted
                required property bool isTemplate

                objectName: `experiments.row.${index}`
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                // The experiment a scan starts from (replaces Use as template; the owner, 2026-11-16): a scan's
                // template dataset; a series starts from its experiments' own values, its one row always marked.
                // Left-aligned under its header (the owner, 2026-11-17).
                Item {
                    property int horizontalAlignment: Text.AlignLeft
                    visible: group.scan && !group.series
                    height: parent ? parent.height : 0
                    EaElements.RadioButton {
                        id: startButton
                        objectName: `experiments.start.${row.index}`
                        anchors.left: parent.left
                        anchors.leftMargin: AppSizes.tableCellMargin
                        anchors.verticalCenter: parent.verticalCenter
                        visible: group.scan && !group.series
                        checked: row.isTemplate
                        EaElements.ToolTip {
                            text: qsTr("The sequential fit starts from this dataset's fitted values")
                            requested: startButton.hovered
                        }
                        onClicked: {
                            if (!row.isTemplate)
                                group.project.useAsTemplate(row.index);
                            checked = Qt.binding(() => row.isTemplate);
                        }
                    }
                }
                // The block's icon in its colour (easydiffractionbeta's colour column; ADR-0017 §8).
                IconCell {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `experiments.color.${row.index}`
                    // A scan's or a series' rows too, each in its colour as the selectors show it (the owner, 2026-11-17).
                    icon: "microscope"
                    iconColor: AppColors.experiment(row.index)
                    toolTip: qsTr("Measured pattern color")
                }
                // How the project's last fit ended on this experiment: the app's check box, ticked in the outcome's colour
                // (green converged, orange a warning, red failed) and empty when it took no part (the owner, 2026-11-17).
                // Nobody sets it: it takes no focus, no hover highlight, and its clicks go nowhere, but it keeps its
                // colour, which a disabled check box would draw grey. An experiment without measured data cannot be
                // fitted, so its box is drawn disabled and says why (the owner, 2026-11-17).
                Item {
                    property int horizontalAlignment: Text.AlignLeft
                    height: parent ? parent.height : 0

                    EaElements.CheckBox {
                        id: fitBox
                        objectName: `experiments.fit.${row.index}`
                        anchors.left: parent.left
                        anchors.leftMargin: AppSizes.tableCellMargin
                        anchors.verticalCenter: parent.verticalCenter
                        padding: 0
                        focusPolicy: Qt.NoFocus
                        hoverEnabled: false
                        enabled: !fileCell.empty
                        checked: row.fitOutcome !== "" && !FitOutcomes.ring(row.fitOutcome)
                        color: FitOutcomes.color(row.fitOutcome)
                    }
                    // Beside the box, not in it: a disabled box takes no hover, and its tooltip still has to show.
                    MouseArea {
                        id: fitHover
                        anchors.fill: fitBox
                        hoverEnabled: true
                        acceptedButtons: Qt.AllButtons
                    }
                    EaElements.ToolTip {
                        parent: fitBox
                        text: fileCell.empty ? qsTr("Load data to include this experiment in the fit") : FitOutcomes.word(row.fitOutcome)
                        requested: fitHover.containsMouse && text !== ""
                    }
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
                    readOnly: group.series
                    onActiveFocusChanged: ApplicationInfo.finishUiEvent(12, undefined)
                    onCommitted: text => row.experiment.name = text
                }
                // The data's file: the experiment's own `.edi`, which holds its data, or a scan dataset's file with
                // "template" after the template's; Load data… ▾ without data, the file and ⋯ to replace it with data
                // (the owner, 2026-11-16). A series' row: its summary.
                Item {
                    id: fileCell

                    property int horizontalAlignment: Text.AlignLeft
                    readonly property bool empty: !group.scan && row.experiment !== null && row.experiment.calculationOnly
                    height: parent ? parent.height : 0

                    Row {
                        x: AppSizes.tableCellMargin
                        height: parent.height
                        spacing: EaStyle.Sizes.fontPixelSize * 0.5
                        visible: !fileCell.empty

                        EaComponents.ListViewLabel {
                            objectName: `experiments.file.${row.index}`
                            width: Math.min(implicitWidth, fileCell.width - 2 * AppSizes.tableCellMargin - (templateTag.visible ? templateTag.width + parent.spacing : 0) - (moreButton.visible ? moreButton.width + parent.spacing : 0))
                            height: parent.height
                            horizontalAlignment: Text.AlignLeft
                            // A long file name keeps its distinguishing end, its number and extension (the owner, 2026-11-17).
                            elide: Text.ElideMiddle
                            text: row.file
                            ToolTip.text: row.file
                        }
                        EaComponents.ListViewLabel {
                            id: templateTag
                            objectName: `experiments.template.${row.index}`
                            visible: group.scan && !group.series && row.isTemplate
                            width: implicitWidth
                            height: parent.height
                            elide: Text.ElideRight
                            // In the accent, as the run selectors show it (the owner, 2026-11-17).
                            color: EaStyle.Colors.themeAccent
                            text: qsTr("Start")
                        }
                        // ⋯: replace the data with another file, folder or collection entry.
                        EaComponents.ListViewButton {
                            id: moreButton
                            objectName: `experiments.dataMore.${row.index}`
                            visible: !group.scan && row.experiment !== null && row.experiment.canLoadData
                            fontIcon: "ellipsis-h"
                            ToolTip.text: qsTr("Replace the measured data")
                            onClicked: group.openDataMenu(row.experiment, moreButton, true)
                        }
                    }
                    // Load data… ▾ in an empty experiment's cell (the owner, 2026-11-16).
                    EaElements.Button {
                        id: loadDataButton
                        objectName: `experiments.loadData.${row.index}`
                        visible: fileCell.empty
                        x: AppSizes.tableCellMargin
                        anchors.verticalCenter: parent.verticalCenter
                        height: parent.height * 0.85
                        enabled: row.experiment !== null && row.experiment.canLoadData
                        text: qsTr("Load data…")
                        rightPadding: loadDataCaret.width + EaStyle.Sizes.fontPixelSize * 1.25
                        // The app's caret, as the Load button below draws it (the owner, 2026-11-16).
                        EaElements.Label {
                            id: loadDataCaret
                            anchors.right: parent.right
                            anchors.rightMargin: EaStyle.Sizes.fontPixelSize * 0.75
                            anchors.verticalCenter: parent.verticalCenter
                            font.family: EaStyle.Fonts.iconsFamily
                            font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.9
                            color: loadDataButton.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
                            text: "caret-down"
                        }
                        ToolTip.text: qsTr("Load measured data into %1 from a file, a folder of a series or the web").arg(row.name)
                        onClicked: group.openDataMenu(row.experiment, loadDataButton, false)
                    }
                }
                // What the scan's extract rules take from the dataset, with their units.
                Item {
                    property int horizontalAlignment: Text.AlignHCenter
                    visible: group.scanColumns.length > 0
                    height: parent.height
                    Row {
                        x: AppSizes.tableCellMargin
                        height: parent.height
                        spacing: table.shares.gap
                        Repeater {
                            property int horizontalAlignment: Text.AlignHCenter
                            model: group.scanColumns.length
                            delegate: Item {
                                id: value
                                required property int index
                                property int horizontalAlignment: Text.AlignHCenter
                                width: table.valueWidth
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

        DataStatusRows {
            width: EaStyle.Sizes.sideBarContentWidth
            project: group.project
        }

        ExperimentTypeGroup {
            visible: group.project !== null && group.project.currentExperiment !== null
            project: group.project
            experiment: group.project ? group.project.currentExperiment : null
            experimentIndex: group.project ? group.project.currentExperimentIndex : -1
        }
        // Create, Load ▾ and Duplicate side by side at equal widths, Create first (the owner, 2026-10-11, 2026-11-03,
        // 2026-11-14). Load brings a full experiment from a file or from the web; measured data goes in through each
        // row's Data file cell.
        Row {
            id: buttons

            readonly property real buttonWidth: (EaStyle.Sizes.sideBarContentWidth - 2 * spacing) / 3
            // Whole labels where the longest fits beside its icon, else the short ones, the same on every button
            // (the owner, 2026-11-23: no label runs out of its button).
            readonly property bool wholeLabels: labelMetrics.advanceWidth + EaStyle.Sizes.fontPixelSize * 4 <= buttonWidth
            TextMetrics {
                id: labelMetrics
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
                text: qsTr("Duplicate experiment")
            }

            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                objectName: "experiments.create"
                width: buttons.buttonWidth
                enabled: group.project !== null && group.project.canCreateExperiment
                fontIcon: "plus-circle"
                text: buttons.wholeLabels ? qsTr("Create experiment") : qsTr("Create")
                ToolTip.text: enabled ? qsTr("Add an experiment without data, to calculate its pattern or load data into") : qsTr("A scan project fits its one template experiment")
                onClicked: group.project.createExperiment()
            }
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
                ToolTip.text: qsTr("Load a full experiment, with its type, data and parameters, from a file or from the web")
                onClicked: loadMenu.open()

                EaElements.Menu {
                    id: loadMenu
                    objectName: "experiments.load.menu"
                    y: loadButton.height
                    // Nothing below the last item (the owner, 2026-11-04).
                    bottomPadding: 0
                    width: Math.max(loadButton.width, EaStyle.Sizes.fontPixelSize * 24)

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
                }
            }
            // A copy of the selected experiment with its data, named <name>_copy; its Data file cell then loads
            // another file in place of the copied one.
            EaElements.SideBarButton {
                objectName: "experiments.duplicate"
                width: buttons.buttonWidth
                enabled: group.project !== null && group.project.canCreateExperiment && group.project.currentExperiment !== null
                fontIcon: "clone"
                text: buttons.wholeLabels ? qsTr("Duplicate experiment") : qsTr("Duplicate")
                ToolTip.text: group.scan ? qsTr("A scan project fits its one template experiment") : qsTr("Add a copy of the selected experiment, with its data")
                onClicked: group.project.duplicateExperiment()
            }
        }
    }

    // One Load data menu for every row (the owner, 2026-11-16): the same choices as before, into the row's experiment.
    function openDataMenu(experiment, anchor, replacing) {
        dataMenu.target = experiment;
        dataMenu.replacing = replacing;
        dataMenu.popup(anchor, 0, anchor.height);
    }
    EaElements.Menu {
        id: dataMenu
        objectName: "experiments.load.dataMenu"
        property ExperimentViewModel target: null
        property bool replacing: false
        bottomPadding: 0
        // As wide as its widest item, never the row's cell: every label and hint shows whole (LoadMenuItem's
        // implicitWidth; a Menu's own does not follow its items').
        width: {
            let widest = EaStyle.Sizes.fontPixelSize * 24;
            for (let i = 0; i < count; ++i) {
                const entry = itemAt(i);
                if (entry)
                    widest = Math.max(widest, entry.implicitWidth);
            }
            return Math.ceil(widest) + leftPadding + rightPadding;
        }
        readonly property real labelWidth: Math.max(EaStyle.Sizes.fontPixelSize * 7.5, Math.ceil(dataLabels.advanceWidth) + EaStyle.Sizes.fontPixelSize * 0.25)
        TextMetrics {
            id: dataLabels
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            text: qsTr("Several files as a series…")
        }

        LoadMenuHeader {
            first: true
            text: dataMenu.replacing ? qsTr("Replace measured data") : Session.categoryTitle("data")
        }
        LoadMenuItem {
            objectName: "experiments.load.dataFile"
            labelWidth: dataMenu.labelWidth
            fontIcon: "file"
            text: qsTr("File…")
            hint: ".xye .xy .dat .txt .csv · .int .hkl"
            toolTip: qsTr("One file, or several: several ask whether they are separate experiments, a scan or a series")
            onTriggered: {
                const target = dataMenu.target;
                group.confirmScanReplacement(() => group.chooseData(target));
            }
        }
        // Several files, asked as a series of joint fits first (the owner, 2026-11-16).
        LoadMenuItem {
            objectName: "experiments.load.dataSeries"
            labelWidth: dataMenu.labelWidth
            fontIcon: "clone"
            text: qsTr("Several files as a series…")
            hint: qsTr("Series of joint fits")
            toolTip: qsTr("Choose the files of every point: they are grouped by name, one experiment for each name pattern")
            onTriggered: {
                const target = dataMenu.target;
                group.seriesWanted = true;
                group.confirmScanReplacement(() => group.chooseData(target));
            }
        }
        LoadMenuItem {
            objectName: "experiments.load.dataFolder"
            labelWidth: dataMenu.labelWidth
            enabled: group.project !== null && !group.project.listingDatasetFolder
            fontIcon: "folder-open"
            text: qsTr("Folder as a series…")
            hint: Session.optionLabel("fitting_mode.type", "sequential")
            toolTip: qsTr("Load every dataset in a folder, then choose Sequential in Analysis")
            onTriggered: {
                const target = dataMenu.target;
                group.confirmScanReplacement(() => ApplicationInfo.chooseDatasetFolder(dataFolderDialog, group.project, target));
            }
        }
        LoadMenuItem {
            objectName: "experiments.load.dataWeb"
            labelWidth: dataMenu.labelWidth
            fontIcon: "globe"
            text: qsTr("From the web…")
            hint: "EasyDiffraction"
            toolTip: qsTr("Search EasyDiffraction's collection for measured data")
            onTriggered: {
                const target = dataMenu.target;
                group.confirmScanReplacement(() => onlineLoad.openFor("data", target));
            }
        }
    }

    OnlineLoadDialog {
        id: onlineLoad
        project: group.project
        onDatasetsReady: (files, experiment, origins) => {
            if (experiment !== null && group.project !== null)
                group.askDatasets(experiment, files, origins);
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

    // Measured data for the selected experiment from a folder of datasets or from the web.
    function chooseFolderForSelected() {
        if (project !== null && project.currentExperiment !== null)
            ApplicationInfo.chooseDatasetFolder(dataFolderDialog, project, project.currentExperiment);
    }
    function chooseWebDataForSelected() {
        if (project !== null && project.currentExperiment !== null) {
            const target = project.currentExperiment;
            confirmScanReplacement(() => onlineLoad.openFor("data", target));
        }
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
        function onFolderOpened(request, folder) {
            ApplicationInfo.formDatasetFolderOpened(request, folder);
        }
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
        currentFolder: DialogFolders.folder("loadExperiment", "")
        onAccepted: {
            DialogFolders.remember("loadExperiment", selectedFiles[0]);
            group.project.loadExperiments(selectedFiles);
        }
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
        currentFolder: DialogFolders.folder("loadData", "")
        onAccepted: {
            DialogFolders.remember("loadData", selectedFiles[0]);
            if (selectedFiles.length > 1 && dataDialog.experiment !== null && dataDialog.project === group.project) {
                const experiment = dataDialog.experiment;
                const files = selectedFiles;
                dataDialog.intent = null;
                group.askDatasets(experiment, files);
                return;
            }
            group.seriesWanted = false;  // one file is no series
            ApplicationInfo.acceptExperimentDataFile();
        }
        onRejected: ApplicationInfo.rejectExperimentDataFile()
    }

    FolderDialog {
        id: dataFolderDialog
        title: qsTr("Choose a folder of sequential-fit datasets")
        acceptLabel: qsTr("Use folder")
        currentFolder: DialogFolders.folder("loadData", "")
        onAccepted: {
            DialogFolders.remember("loadData", selectedFolder);
            ApplicationInfo.acceptDatasetFolder(dataFolderDialog, group.project, selectedFolder);
        }
    }

    // Load N datasets as (the owner, 2026-11-04): separate experiments, each a copy of the selected experiment's setup
    // named after its file, or one experiment with a scan, the selected experiment its template and the files its
    // datasets. Up to five files default to separate experiments, more to a scan.
    // Set by Several files as a series…: the next choice of several files is asked with that answer first.
    property bool seriesWanted: false
    // The datasets dialog for `files` (URLs) as a series, as Several files as a series… then a choice of files opens it.
    function askSeries(files) {
        if (group.project === null || group.project.currentExperiment === null)
            return;
        group.seriesWanted = true;
        group.askDatasets(group.project.currentExperiment, files);
    }
    function askDatasets(experiment, files, origins = []) {
        const series = group.seriesWanted;
        group.seriesWanted = false;
        // Copied by default for a small set, linked above 20 files or 50 MB (the owner, 2026-11-04). Files from a data
        // collection carry their entry and digest (`origins`): linked, they are downloaded again when a fit needs them.
        const dialog = datasetsComponent.createObject(Overlay.overlay, {
            experiment: experiment,
            files: files,
            origins: origins,
            asScan: !series && files.length > 5,
            asSeries: series,
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
            // A series of joint fits (edi ADR-0088 point 1): the files grouped by name into one experiment each, fitted
            // point by point; its folder is linked.
            property bool asSeries: false
            // The series' groups as a worker found them (previewSeriesGroups), shown before loading; OK waits for them.
            property int previewRequest: 0
            property string previewText: ""
            property bool previewValid: false
            function previewGroups() {
                datasetsChoice.previewText = "";
                datasetsChoice.previewValid = false;
                if (datasetsChoice.asSeries && group.project !== null)
                    datasetsChoice.previewRequest = group.project.previewSeriesGroups(datasetsChoice.files);
            }
            onAsSeriesChanged: previewGroups()
            // Made already a series (Several files as a series…): grouped at once, and OK waits for it.
            Component.onCompleted: {
                previewGroups();
                const ok = datasetsChoice.standardButton(Dialog.Ok);
                if (ok)
                    ok.enabled = datasetsChoice.acceptable;
            }
            Connections {
                target: group.project
                function onSeriesGroupsPreviewed(request, text, valid) {
                    if (request !== datasetsChoice.previewRequest)
                        return;
                    datasetsChoice.previewText = text;
                    datasetsChoice.previewValid = valid;
                }
            }
            readonly property bool acceptable: !datasetsChoice.asSeries || datasetsChoice.previewValid
            onAcceptableChanged: {
                const ok = datasetsChoice.standardButton(Dialog.Ok);
                if (ok)
                    ok.enabled = datasetsChoice.acceptable;
            }
            property bool copy: true
            property var origins: []
            // A scan's files are read from its folder, so a collection's files are copied for one (edi ADR-0069).
            // Separate experiments may keep their files linked, a powder pattern and a single crystal's reflections
            // alike; a file of several datasets is refused for linking when it is loaded.
            readonly property bool mustCopy: (datasetsChoice.asScan || datasetsChoice.asSeries) && datasetsChoice.origins.length > 0
            title: qsTr("Load %1 datasets as").arg(files.length)
            standardButtons: Dialog.Ok | Dialog.Cancel
            contentWidth: AppSizes.messagesDialogContentWidth
            contentHeight: datasetsColumn.implicitHeight
            onClosed: destroy()
            onAccepted: {
                if (group.project !== null && datasetsChoice.experiment !== null && datasetsChoice.asSeries) {
                    group.project.loadSeriesOfJointFits(datasetsChoice.experiment, datasetsChoice.files, datasetsChoice.copy || datasetsChoice.mustCopy);
                    return;
                }
                if (group.project !== null && datasetsChoice.experiment !== null)
                    group.project.loadDatasets(datasetsChoice.experiment, datasetsChoice.files, datasetsChoice.asScan, datasetsChoice.copy || datasetsChoice.mustCopy, datasetsChoice.origins);
            }

            Column {
                id: datasetsColumn
                width: datasetsChoice.contentWidth
                spacing: EaStyle.Sizes.fontPixelSize * 0.5

                ChoiceRadioButton {
                    id: jointChoice
                    objectName: "datasets.separate"
                    width: datasetsColumn.width
                    // Named by the fit each choice is for (the owner, 2026-11-04).
                    text: qsTr("Joint fit: one experiment per file, fitted together")
                    checked: !datasetsChoice.asScan && !datasetsChoice.asSeries
                    onClicked: {
                        datasetsChoice.asScan = false;
                        datasetsChoice.asSeries = false;
                    }
                }
                ChoiceRadioButton {
                    objectName: "datasets.scan"
                    width: datasetsColumn.width
                    text: qsTr("Sequential fit: one experiment for all datasets")
                    checked: datasetsChoice.asScan && !datasetsChoice.asSeries
                    onClicked: {
                        datasetsChoice.asScan = true;
                        datasetsChoice.asSeries = false;
                    }
                }
                ChoiceRadioButton {
                    objectName: "datasets.series"
                    width: datasetsColumn.width
                    text: qsTr("Series of joint fits: one experiment per file name pattern, each point fitted jointly")
                    checked: datasetsChoice.asSeries
                    onClicked: {
                        datasetsChoice.asSeries = true;
                        datasetsChoice.asScan = false;
                    }
                }
                EaElements.Label {
                    width: datasetsColumn.width
                    wrapMode: Text.Wrap
                    visible: datasetsChoice.asScan
                    text: qsTr("First fit the template dataset in Single mode. When it is ready, choose Sequential in Analysis to fit the folder. Evolution is available as soon as the scan is loaded.")
                }
                EaElements.Label {
                    objectName: "datasets.series.groups"
                    width: datasetsColumn.width
                    wrapMode: Text.Wrap
                    visible: datasetsChoice.asSeries
                    color: datasetsChoice.previewValid || datasetsChoice.previewText === "" ? EaStyle.Colors.themeForeground : EaStyle.Colors.red
                    text: datasetsChoice.previewText === "" ? qsTr("Grouping the files by name") : datasetsChoice.previewText
                }
                EaElements.Label {
                    width: datasetsColumn.width
                    wrapMode: Text.Wrap
                    visible: datasetsChoice.asSeries
                    text: qsTr("Each experiment shows its first point. Choose Sequential in Analysis to fit the points one after another.")
                }
                EaElements.CheckBox {
                    id: copyBox
                    objectName: "datasets.copy"
                    // What the choice means is its tool tip (the owner, 2026-11-04).
                    ToolTip.text: datasetsChoice.asSeries ? (datasetsChoice.copy ? qsTr("The files are copied into the project's folder, a folder of the series' own.") : qsTr("The series reads the files where they are; the project keeps their folder's location.")) : datasetsChoice.asScan ? (datasetsChoice.copy ? qsTr("The files are copied into the project's folder; the project must be saved and hold this one experiment.") : qsTr("The scan reads the files where they are; the project keeps their folder's location.")) : (datasetsChoice.copy ? qsTr("Each experiment holds its data in the project.") : datasetsChoice.origins.length > 0 ? qsTr("Each experiment keeps its collection entry and downloads the file again when a fit needs it.") : qsTr("Each experiment reads its file where it is; the project keeps the file's location."))
                    // The same spacing as between the two choices.
                    height: jointChoice.height
                    text: qsTr("Copy data into the project")
                    enabled: !datasetsChoice.mustCopy
                    checked: datasetsChoice.copy || datasetsChoice.mustCopy
                    onToggled: datasetsChoice.copy = checked
                }
            }
        }
    }
}
