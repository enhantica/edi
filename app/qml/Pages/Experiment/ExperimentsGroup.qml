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
// ⋯ to replace it once it has (the owner, 2026-11-16). A series of joint fits is one row, opened to a grid of its
// points × banks. Start marks the experiment a scan starts from. Create, Load and Load data are each one undoable step.
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
    // A series of joint fits (edi ADR-0088): one row, its grid opened under the table.
    readonly property bool series: project !== null && project.series
    property bool seriesOpen: true
    // One column per extract rule, with its unit, from the table's own model. The table lays a row's cells out
    // by their place among the header's, so the header and each row repeat over the same list.
    readonly property var scanColumns: project ? project.experiments.columns : []
    // The Fit column is as wide as its title or its icon, so the Fit icon sits as close to the colour icon as the
    // Structures table's icon to its name: one margin between them, not each column's own (the owner, 2026-10-11). A
    // right margin as wide as a table's edge margin then keeps the datablock names off it (the owner, 2026-10-24).
    // The Start column is as wide as its title.
    readonly property real startColumnWidth: Math.ceil(startTitle.advanceWidth) + EaStyle.Sizes.tableColumnSpacing * 2
    readonly property real fitColumnWidth: Math.ceil(Math.max(fitTitle.advanceWidth, EaStyle.Sizes.fontPixelSize * 1.15)) + EaStyle.Sizes.tableColumnSpacing

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
            currentRow: group.series ? 0 : group.project ? group.project.currentExperimentIndex : -1
            onRowActivated: row => ApplicationInfo.activateFormBlock(row, false)

            columns: [numberColumnWidth, group.scan ? group.startColumnWidth : 0.001, group.scan ? 0.001 : AppSizes.iconOnlyColumnWidth, group.scan ? AppSizes.iconOnlyColumnWidth : group.fitColumnWidth, -1, -1, group.scanColumns.length ? group.scanColumns.length * AppSizes.dataColumnWidth * 1.4 : 0.001, group.scan ? 0.001 : AppSizes.iconColumnWidth]

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    visible: group.scan
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
                    elide: Text.ElideRight
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
                                    elide: Text.ElideRight
                                    anchors.fill: parent
                                    horizontalAlignment: column.horizontalAlignment
                                    text: column.modelData
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
                Item {
                    property int horizontalAlignment: Text.AlignHCenter
                    height: parent ? parent.height : 0
                    EaElements.RadioButton {
                        objectName: `experiments.start.${row.index}`
                        anchors.centerIn: parent
                        visible: group.scan
                        enabled: !group.series
                        checked: group.series || row.isTemplate
                        EaElements.ToolTip {
                            text: group.series ? qsTr("Each point of the series starts from the previous point's fitted values") : qsTr("The sequential fit starts from this dataset's fitted values")
                            requested: parent.hovered
                        }
                        onClicked: {
                            if (!group.series && !row.isTemplate)
                                group.project.useAsTemplate(row.index);
                            checked = Qt.binding(() => group.series || row.isTemplate);
                        }
                    }
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
                    readOnly: group.series
                    onActiveFocusChanged: ApplicationInfo.finishUiEvent(12, undefined)
                    onCommitted: text => row.experiment.name = text
                }
                // The data's file: the experiment's own `.edi`, which holds its data, or a scan dataset's file with
                // "template" after the template's; Load data… ▾ without data, the file and ⋯ to replace it with data
                // (the owner, 2026-11-16). A series' row: its caret opening the grid, its summary and file counts.
                Item {
                    id: fileCell

                    property int horizontalAlignment: Text.AlignLeft
                    readonly property bool empty: !group.scan && row.experiment !== null && row.experiment.calculationOnly
                    height: parent ? parent.height : 0

                    Row {
                        height: parent.height
                        spacing: EaStyle.Sizes.fontPixelSize * 0.5
                        visible: !fileCell.empty

                        EaComponents.ListViewButton {
                            objectName: `experiments.seriesToggle.${row.index}`
                            visible: group.series
                            fontIcon: group.seriesOpen ? "caret-down" : "caret-right"
                            ToolTip.text: group.seriesOpen ? qsTr("Hide the series' points") : qsTr("Show the series' points and banks")
                            onClicked: group.seriesOpen = !group.seriesOpen
                        }
                        EaComponents.ListViewLabel {
                            objectName: `experiments.file.${row.index}`
                            width: Math.min(implicitWidth, fileCell.width - (templateTag.visible ? templateTag.width + parent.spacing : 0) - (counts.visible ? counts.width + parent.spacing : 0) - (moreButton.visible ? moreButton.width + parent.spacing : 0) - (group.series ? EaStyle.Sizes.tableRowHeight + parent.spacing : 0))
                            height: parent.height
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideRight
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
                            color: EaStyle.Colors.themeAccent
                            text: Session.label("sequential_fit.template_file")
                        }
                        // The series' files: loaded, changed since their fit, missing.
                        Row {
                            id: counts
                            readonly property var numbers: group.series && group.project && group.project.seriesRevision >= 0 ? group.project.seriesCounts() : [0, 0, 0]
                            visible: group.series
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: EaStyle.Sizes.fontPixelSize * 0.4
                            Repeater {
                                model: [{
                                        n: counts.numbers[0],
                                        color: EaStyle.Colors.green,
                                        word: qsTr("loaded")
                                    }, {
                                        n: counts.numbers[1],
                                        color: EaStyle.Colors.orange,
                                        word: qsTr("changed")
                                    }, {
                                        n: counts.numbers[2],
                                        color: EaStyle.Colors.red,
                                        word: qsTr("missing")
                                    }]
                                delegate: EaElements.Label {
                                    required property var modelData
                                    visible: modelData.n > 0
                                    color: modelData.color
                                    text: `${modelData.n} ${modelData.word}`
                                }
                            }
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

        // A series' points × banks (the owner, 2026-11-16): each bank's file at each point, loaded, changed since the
        // point's fit, or missing, and the point's fit. A cell shows its point and bank in the charts.
        Column {
            id: seriesGrid
            objectName: "experiments.seriesGrid"
            readonly property real cellWidth: EaStyle.Sizes.fontPixelSize * 3.2
            readonly property real pointWidth: EaStyle.Sizes.fontPixelSize * 9
            readonly property real fitWidth: EaStyle.Sizes.fontPixelSize * 7
            readonly property var banks: group.project ? group.project.bankLabels : []
            readonly property real rowWidth: pointWidth + banks.length * cellWidth + fitWidth
            visible: group.series && group.seriesOpen
            width: EaStyle.Sizes.sideBarContentWidth
            spacing: EaStyle.Sizes.fontPixelSize * 0.3

            Flickable {
                id: gridFlick
                width: parent.width
                height: gridHeader.height + gridList.height
                contentWidth: seriesGrid.rowWidth
                contentHeight: height
                flickableDirection: Flickable.HorizontalFlick
                boundsBehavior: Flickable.StopAtBounds
                clip: true
                ScrollBar.horizontal: ScrollBar {
                    policy: seriesGrid.rowWidth > gridFlick.width ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                }

                Column {
                    Row {
                        id: gridHeader
                        height: EaStyle.Sizes.tableRowHeight
                        EaElements.Label {
                            width: seriesGrid.pointWidth
                            anchors.verticalCenter: parent.verticalCenter
                            color: EaStyle.Colors.themeForegroundMinor
                            elide: Text.ElideRight
                            text: group.project ? group.project.seriesVariable : ""
                        }
                        Repeater {
                            model: seriesGrid.banks
                            delegate: EaElements.Label {
                                id: bankTitle
                                required property string modelData
                                required property int index
                                width: seriesGrid.cellWidth
                                anchors.verticalCenter: parent.verticalCenter
                                horizontalAlignment: Text.AlignHCenter
                                color: EaStyle.Colors.themeForegroundMinor
                                text: qsTr("Bank %1").arg(bankTitle.index + 1)
                                HoverHandler {
                                    id: bankHover
                                }
                                EaElements.ToolTip {
                                    text: bankTitle.modelData
                                    requested: bankHover.hovered
                                }
                            }
                        }
                        EaElements.Label {
                            width: seriesGrid.fitWidth
                            anchors.verticalCenter: parent.verticalCenter
                            leftPadding: EaStyle.Sizes.fontPixelSize * 0.5
                            color: EaStyle.Colors.themeForegroundMinor
                            text: qsTr("Fit")
                        }
                    }
                    ListView {
                        id: gridList
                        objectName: "experiments.seriesGrid.points"
                        width: seriesGrid.rowWidth
                        height: Math.min(count, 8) * EaStyle.Sizes.tableRowHeight
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        model: group.series ? group.project.seriesPointCount : 0
                        ScrollBar.vertical: ScrollBar {
                            policy: gridList.count > 8 ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                        }
                        delegate: Row {
                            id: pointRow
                            required property int index
                            readonly property int revision: group.project ? group.project.seriesRevision : 0
                            readonly property var cells: revision >= 0 ? group.project.pointCells(pointRow.index) : []
                            readonly property bool current: group.project !== null && group.project.currentExperimentIndex === pointRow.index
                            height: EaStyle.Sizes.tableRowHeight
                            EaElements.Label {
                                width: seriesGrid.pointWidth
                                anchors.verticalCenter: parent.verticalCenter
                                elide: Text.ElideRight
                                font.bold: pointRow.current
                                text: pointRow.revision >= 0 ? group.project.pointLabel(pointRow.index) : ""
                            }
                            Repeater {
                                model: pointRow.cells
                                delegate: Rectangle {
                                    id: cell
                                    required property int modelData
                                    required property int index
                                    objectName: `experiments.seriesCell.${pointRow.index}.${cell.index}`
                                    readonly property bool shown: pointRow.current && group.project.currentBank === cell.index
                                    width: seriesGrid.cellWidth
                                    height: EaStyle.Sizes.tableRowHeight
                                    color: "transparent"
                                    border.width: shown ? 2 : 0
                                    border.color: EaStyle.Colors.themeAccent
                                    radius: EaStyle.Sizes.fontPixelSize * 0.2
                                    // The app's icons, as the Fit column draws an outcome: loaded, changed, missing (a ring).
                                    IconCell {
                                        anchors.fill: parent
                                        icon: cell.modelData === 0 ? "circle" : cell.modelData === 1 ? "adjust" : ""
                                        ring: cell.modelData === 2
                                        iconColor: String(cell.modelData === 0 ? EaStyle.Colors.green : cell.modelData === 1 ? EaStyle.Colors.orange : EaStyle.Colors.red)
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: cell.modelData !== 2
                                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                        onClicked: group.project.showPointBank(pointRow.index, cell.index)
                                    }
                                }
                            }
                            EaElements.Label {
                                readonly property string problem: pointRow.revision >= 0 ? group.project.pointProblem(pointRow.index) : ""
                                readonly property string reliability: pointRow.revision >= 0 ? group.project.pointReliability(pointRow.index) : ""
                                width: seriesGrid.fitWidth
                                anchors.verticalCenter: parent.verticalCenter
                                leftPadding: EaStyle.Sizes.fontPixelSize * 0.5
                                elide: Text.ElideRight
                                color: problem !== "" ? EaStyle.Colors.red : reliability !== "" ? String(FitOutcomes.color(group.project.pointOutcome(pointRow.index))) : EaStyle.Colors.themeForegroundMinor
                                text: problem !== "" ? qsTr("not fitted") : reliability !== "" ? reliability : qsTr("not fitted")
                                HoverHandler {
                                    id: fitHover
                                }
                                EaElements.ToolTip {
                                    text: parent.problem
                                    requested: fitHover.hovered
                                }
                            }
                        }
                    }
                }
            }
            // The legend, with the cells' own icons.
            Flow {
                width: parent.width
                spacing: EaStyle.Sizes.fontPixelSize * 0.5
                Repeater {
                    model: [{
                            icon: "circle",
                            ring: false,
                            color: EaStyle.Colors.green,
                            word: qsTr("loaded")
                        }, {
                            icon: "adjust",
                            ring: false,
                            color: EaStyle.Colors.orange,
                            word: qsTr("changed since the fit")
                        }, {
                            icon: "",
                            ring: true,
                            color: EaStyle.Colors.red,
                            word: qsTr("missing")
                        }]
                    delegate: Row {
                        required property var modelData
                        height: EaStyle.Sizes.tableRowHeight * 0.8
                        spacing: EaStyle.Sizes.fontPixelSize * 0.25
                        IconCell {
                            width: EaStyle.Sizes.fontPixelSize * 1.2
                            icon: parent.modelData.icon
                            ring: parent.modelData.ring
                            iconColor: String(parent.modelData.color)
                        }
                        EaElements.Label {
                            anchors.verticalCenter: parent.verticalCenter
                            color: EaStyle.Colors.themeForegroundMinor
                            text: parent.modelData.word
                        }
                    }
                }
                EaElements.Label {
                    height: EaStyle.Sizes.tableRowHeight * 0.8
                    verticalAlignment: Text.AlignVCenter
                    color: EaStyle.Colors.themeForegroundMinor
                    text: qsTr("· a cell shows its point and bank in the charts")
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

            spacing: EaStyle.Sizes.fontPixelSize

            EaElements.SideBarButton {
                objectName: "experiments.create"
                width: buttons.buttonWidth
                enabled: group.project !== null && group.project.canCreateExperiment
                fontIcon: "plus-circle"
                text: qsTr("Create experiment")
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
                text: qsTr("Duplicate experiment")
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
        // As wide as its widest item, never the row's cell: every label and hint shows whole (LoadMenuItem).
        width: Math.max(EaStyle.Sizes.fontPixelSize * 24, implicitWidth)
        readonly property real labelWidth: Math.max(EaStyle.Sizes.fontPixelSize * 7.5, Math.ceil(dataLabels.advanceWidth) + EaStyle.Sizes.fontPixelSize * 0.25)
        TextMetrics {
            id: dataLabels
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            text: qsTr("Several files as a series…")
        }

        LoadMenuHeader {
            first: true
            text: dataMenu.replacing ? qsTr("Replace measured data") : qsTr("Measured data")
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
            toolTip: qsTr("Choose the files of every point: they are grouped by name into one experiment per bank")
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
            group.seriesWanted = false;  // one file is no series
            ApplicationInfo.acceptExperimentDataFile();
        }
        onRejected: ApplicationInfo.rejectExperimentDataFile()
    }

    FolderDialog {
        id: dataFolderDialog
        title: qsTr("Choose a folder of sequential-fit datasets")
        acceptLabel: qsTr("Use folder")
        onAccepted: ApplicationInfo.acceptDatasetFolder(dataFolderDialog, group.project, selectedFolder)
    }

    // Load N datasets as (the owner, 2026-11-04): separate experiments, each a copy of the selected experiment's setup
    // named after its file, or one experiment with a scan, the selected experiment its template and the files its
    // datasets. Up to five files default to separate experiments, more to a scan.
    // Set by Several files as a series…: the next choice of several files is asked with that answer first.
    property bool seriesWanted: false
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
            property bool copy: true
            property var origins: []
            // A scan's files are read from its folder, so a collection's files are copied for one (edi ADR-0069).
            // Separate experiments may keep their files linked, a powder pattern and a single crystal's reflections
            // alike; a file of several datasets is refused for linking when it is loaded.
            readonly property bool mustCopy: datasetsChoice.asScan && datasetsChoice.origins.length > 0
            title: qsTr("Load %1 datasets as").arg(files.length)
            standardButtons: Dialog.Ok | Dialog.Cancel
            contentWidth: AppSizes.messagesDialogContentWidth
            contentHeight: datasetsColumn.implicitHeight
            onClosed: destroy()
            onAccepted: {
                if (group.project !== null && datasetsChoice.experiment !== null && datasetsChoice.asSeries) {
                    group.project.loadSeriesOfJointFits(datasetsChoice.experiment, datasetsChoice.files);
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
                    width: datasetsColumn.width
                    wrapMode: Text.Wrap
                    visible: datasetsChoice.asSeries
                    text: qsTr("The files' folder is linked and each experiment shows its first point. Choose Sequential in Analysis to fit the points one after another.")
                }
                EaElements.CheckBox {
                    id: copyBox
                    visible: !datasetsChoice.asSeries
                    objectName: "datasets.copy"
                    // What the choice means is its tool tip (the owner, 2026-11-04).
                    ToolTip.text: datasetsChoice.asScan ? (datasetsChoice.copy ? qsTr("The files are copied into the project's folder; the project must be saved and hold this one experiment.") : qsTr("The scan reads the files where they are; the project keeps their folder's location.")) : (datasetsChoice.copy ? qsTr("Each experiment holds its data in the project.") : datasetsChoice.origins.length > 0 ? qsTr("Each experiment keeps its collection entry and downloads the file again when a fit needs it.") : qsTr("Each experiment reads its file where it is; the project keeps the file's location."))
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
