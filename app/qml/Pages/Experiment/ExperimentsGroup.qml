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

            columnWidths: [numberColumnWidth, group.scan ? 0.001 : AppSizes.iconOnlyColumnWidth, group.scan ? AppSizes.iconOnlyColumnWidth : group.fitColumnWidth, textColumnWidth("name", qsTr("Datablock")), -1, group.scanColumns.length ? group.scanColumns.length * AppSizes.dataColumnWidth * 1.4 : 0.001, group.scan ? 0.001 : AppSizes.iconColumnWidth]

            header: EaComponents.ListViewHeader {
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("Fit")
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Datablock")
                }
                EaComponents.TableViewLabel {
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
                TapHandler {
                    readonly property var assistantGesture: ({ current: null })

                    function sameGesture(point) {
                        const retained = assistantGesture.current;
                        return retained !== null && retained.device === point.device && retained.id === point.id && retained.press === point.pressTimestamp;
                    }
                    function discardGesture(point) {
                        if (sameGesture(point)) {
                            assistantGesture.current.closed = true;
                            assistantGesture.current.proof = null;
                        }
                    }
                    onGrabChanged: (transition, eventPoint) => {
                        if (transition === PointerDevice.GrabPassive || transition === PointerDevice.GrabExclusive) {
                            if (sameGesture(eventPoint))
                                return; // Passive/exclusive transitions cannot rearm this press.
                            if (eventPoint.state !== EventPoint.Pressed)
                                return;
                            const original = { device: eventPoint.device, id: eventPoint.id, press: eventPoint.pressTimestamp, proof: null, closed: false };
                            const holder = assistantGesture;
                            holder.current = original; // No QML notification before capture/cancellation.
                            const proof = Session.assistant.beginManualControlInput(row, eventPoint, row.experiment);
                            if (holder.current === original && !original.closed)
                                original.proof = proof; // An old callback cannot overwrite a newer grab.
                        } else if (transition === PointerDevice.UngrabPassive || transition === PointerDevice.UngrabExclusive || transition === PointerDevice.CancelGrabPassive || transition === PointerDevice.CancelGrabExclusive) {
                            discardGesture(eventPoint);
                        }
                    }
                    onCanceled: eventPoint => {
                        if (sameGesture(eventPoint))
                            discardGesture(eventPoint);
                    }
                    onTapped: eventPoint => {
                        if (!sameGesture(eventPoint) || assistantGesture.current.closed)
                            return;
                        const original = assistantGesture.current;
                        const proof = original.proof;
                        original.closed = true;
                        original.proof = null; // Consume BEFORE validation/action and any reentry.
                        if (Session.assistant.completeManualControlInput(row, eventPoint, row.experiment, proof))
                            group.project.currentExperimentIndex = row.index;
                    }
                }

                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    color: EaStyle.Colors.themeForegroundMinor
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
                    editMember: row
                    editModel: group.project ? group.project.experiments : null
                    editIndex: row.index
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

                        EaComponents.TableViewLabel {
                            width: Math.min(implicitWidth, fileCell.width - (templateTag.visible ? templateTag.width + parent.spacing : 0))
                            height: parent.height
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideMiddle
                            text: row.file
                        }
                        EaComponents.TableViewLabel {
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
                    EaComponents.TableViewLabel {
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
                            readonly property var assistantGesture: ({ current: null })

                            function sameGesture(point) {
                                const retained = assistantGesture.current;
                                return retained !== null && retained.device === point.device && retained.id === point.id && retained.press === point.pressTimestamp;
                            }
                            function discardGesture(point) {
                                if (sameGesture(point)) {
                                    assistantGesture.current.closed = true;
                                    assistantGesture.current.proof = null;
                                }
                            }
                            onGrabChanged: (transition, eventPoint) => {
                                if (transition === PointerDevice.GrabPassive || transition === PointerDevice.GrabExclusive) {
                                    if (sameGesture(eventPoint))
                                        return; // Passive/exclusive transitions cannot rearm this press.
                                    if (eventPoint.state !== EventPoint.Pressed)
                                        return;
                                    const original = { device: eventPoint.device, id: eventPoint.id, press: eventPoint.pressTimestamp, proof: null, closed: false };
                                    const holder = assistantGesture;
                                    holder.current = original; // No QML notification before capture/cancellation.
                                    const proof = Session.assistant.beginManualControlInput(loadData, eventPoint, row.experiment);
                                    if (holder.current === original && !original.closed)
                                        original.proof = proof; // An old callback cannot overwrite a newer grab.
                                } else if (transition === PointerDevice.UngrabPassive || transition === PointerDevice.UngrabExclusive || transition === PointerDevice.CancelGrabPassive || transition === PointerDevice.CancelGrabExclusive) {
                                    discardGesture(eventPoint);
                                }
                            }
                            onCanceled: eventPoint => {
                                if (sameGesture(eventPoint))
                                    discardGesture(eventPoint);
                            }
                            onTapped: eventPoint => {
                                if (!sameGesture(eventPoint) || assistantGesture.current.closed)
                                    return;
                                const original = assistantGesture.current;
                                const proof = original.proof;
                                original.closed = true;
                                original.proof = null; // Consume BEFORE validation/action and any reentry.
                                if (Session.assistant.completeManualControlInput(loadData, eventPoint, row.experiment, proof))
                                    loadData.clicked();
                            }
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
                onClicked: group.chooseExperimentFiles()

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

    // Original ordinary pickers; a chosen file never retargets a later owner.
    // Only an original visible request configures this SAME ordinary picker.
    // A retired request never restores over a newer human/dialog intent.
    property var assistantPicker: null
    readonly property string assistantPickerId: assistantPicker !== null ? assistantPicker.id : ""
    function prepareAssistantPicker(id, experiment) {
        const life = pickerLife;
        const originalProject = project;
        if (!restoreRetiredAssistantPicker() || !life.alive || project !== originalProject || Session.project !== originalProject) return false;
        if (id.length === 0 || WebFiles.available || project === null || experiment === null || Session.project !== project ||
            assistantPicker !== null || dataDialog.intent !== null || dataDialog.visible || webIntent !== null) return false;
        const original = { id: id, project: project, experiment: experiment, options: dataDialog.options, popupType: dataDialog.popupType,
            ownedOptions: dataDialog.options | FileDialog.DontUseNativeDialog, retired: false, cancelled: false };
        assistantPicker = original;
        if (!life.alive || assistantPicker !== original) return false;
        dataDialog.popupType = Popup.Item;
        if (!life.alive || assistantPicker !== original) return false;
        dataDialog.options = original.ownedOptions;
        if (!life.alive || assistantPicker !== original) return false;
        if (project !== original.project || Session.project !== original.project) {
            original.retired = true;
            Qt.callLater(() => { if (life.alive) group.restoreAssistantPicker(original); });
            return false;
        }
        return true;
    }
    function restoreAssistantPicker(original) {
        if (original === null || original.restoring || assistantPicker !== original || dataDialog.visible || dataDialog.intent !== null
            || (dataDialog.cleanupOwner !== null && dataDialog.cleanupOwner !== original)) return;
        const life = pickerLife;
        original.restoring = true;
        try {
            if (dataDialog.popupType === Popup.Item) dataDialog.popupType = original.popupType;
            if (!life.alive || assistantPicker !== original || dataDialog.visible || dataDialog.intent !== null) return;
            if (dataDialog.options === original.ownedOptions) dataDialog.options = original.options;
            if (!life.alive || assistantPicker !== original || dataDialog.visible || dataDialog.intent !== null) return;
            if (dataDialog.cleanupOwner === original) dataDialog.cleanupOwner = null;
            if (!life.alive || assistantPicker !== original || dataDialog.visible || dataDialog.intent !== null
                || dataDialog.cleanupOwner !== null) return;
            assistantPicker = null; // Terminal: a newer configuration may now be admitted.
        } finally { original.restoring = false; }
    }
    function restoreRetiredAssistantPicker() {
        const life = pickerLife;
        const original = assistantPicker;
        if (original === null || !original.retired) return true;
        restoreAssistantPicker(original);
        return life.alive && assistantPicker === null;
    }
    function retireAssistantPicker(id, manual) {
        const original = assistantPicker;
        if (original === null || original.id !== id) return;
        const life = pickerLife;
        original.retired = true;
        original.cancelled = true;
        const pending = dataDialog.intent;
        const controls = pending !== null && pending.assistant === original;
        if (controls) {
            if (manual) pending.assistant = null;
            // close() need not emit rejected. Consume only A's still-owned
            // unopened/cancelled intent; an open manual picker keeps its target.
            if (!manual || !dataDialog.visible) dataDialog.intent = null;
        }
        if (!life.alive) return;
        Qt.callLater(() => { if (life.alive) group.restoreAssistantPicker(original); });
        // A later retirement cannot close a picker already handed to a human.
        if (!manual && controls && assistantPicker === original && dataDialog.intent === null &&
            (dataDialog.cleanupOwner === null || dataDialog.cleanupOwner === original)) dataDialog.close();
    }
    property var pickerLife: ({ alive: true })
    Component.onDestruction: pickerLife.alive = false
    readonly property string dataFilter: ".xye,.xy,.dat,.txt,.csv"
    property int webRequest: 0
    property var webIntent: null
    function chooseFiles(experiment) {
        const life = pickerLife;
        const originalProject = project;
        if (!restoreRetiredAssistantPicker() || !life.alive || project !== originalProject || Session.project !== originalProject) return false;
        if (project === null || Session.project !== project || webIntent !== null ||
            loadDialog.intent !== null || dataDialog.intent !== null || loadDialog.visible || dataDialog.visible ||
            (assistantPicker !== null && (assistantPicker.retired || experiment !== assistantPicker.experiment))) return false;
        const original = { project: project, experiment: experiment, assistant: assistantPicker, configuration: assistantPicker };
        if (WebFiles.available) {
            webIntent = original;
            if (!life.alive || webIntent !== original) return false;
            if (project !== original.project || Session.project !== original.project) { webIntent = null; return false; }
            const request = WebFiles.openFiles(experiment !== null ? dataFilter : ".edi", experiment === null);
            if (!life.alive || webIntent !== original) return false;
            if (request === 0 || project !== original.project || Session.project !== original.project) { webIntent = null; return false; }
            webRequest = request;
        } else {
            const dialog = experiment !== null ? dataDialog : loadDialog;
            dialog.intent = original;
            if (!life.alive || dialog.intent !== original) return false;
            if (dialog === dataDialog) dialog.cleanupOwner = original.configuration;
            if (!life.alive || dialog.intent !== original) return false;
            if (project !== original.project || Session.project !== original.project) { dialog.intent = null; return false; }
            dialog.open();
        }
        return true;
    }
    function chooseData(experiment) { return experiment !== null && chooseFiles(experiment); }
    function chooseExperimentFiles() { return chooseFiles(null); }
    function takeWebIntent(request) {
        if (request !== webRequest || webIntent === null) return null;
        const life = pickerLife;
        const original = webIntent;
        webRequest = 0;
        if (!life.alive || webIntent !== original) return null;
        webIntent = null;
        if (!life.alive || webIntent !== null || project !== original.project || Session.project !== original.project) return null;
        return original;
    }
    Connections {
        target: WebFiles
        function onFilesOpened(request, files) {
            const original = group.takeWebIntent(request);
            if (original === null) return;
            if (original.experiment !== null) {
                if (files.length === 1) original.project.loadDataInto(original.experiment, files[0]);
            } else original.project.loadExperiments(files);
        }
        function onFailed(request) { group.takeWebIntent(request); }
        function onCancelled(request) { group.takeWebIntent(request); }
    }
    FileDialog {
        id: loadDialog
        objectName: "experiments.fileDialog"
        property var intent: null
        title: qsTr("Load experiments from .edi block files")
        fileMode: FileDialog.OpenFiles
        nameFilters: [qsTr("edi block files (*.edi)")]
        onAccepted: {
            const life = group.pickerLife;
            const original = intent;
            const files = selectedFiles;
            intent = null;
            if (life.alive && intent === null && original !== null && group.project === original.project && Session.project === original.project)
                original.project.loadExperiments(files);
        }
        onRejected: intent = null
    }
    FileDialog {
        id: dataDialog
        objectName: "experiments.dataDialog"
        property var intent: null
        property var cleanupOwner: null
        onVisibleChanged: {
            const original = cleanupOwner;
            const life = group.pickerLife;
            if (!visible && original !== null)
                Qt.callLater(() => { if (life.alive) group.restoreAssistantPicker(original); });
        }
        readonly property string assistantIntentId: intent !== null && intent.assistant !== null ? intent.assistant.id : ""
        readonly property var experiment: intent !== null ? intent.experiment : null
        readonly property var project: intent !== null ? intent.project : null
        title: qsTr("Load measured data from a plain two- or three-column file")
        nameFilters: [qsTr("Data files (*.xye *.xy *.dat *.txt *.csv)"), qsTr("All files (*)")]
        onAccepted: {
            const life = group.pickerLife;
            const original = intent;
            const file = selectedFile;
            const picker = original !== null ? original.assistant : null;
            const configuration = original !== null ? original.configuration : null;
            if (configuration !== null) {
                configuration.retired = true;
                Qt.callLater(() => { if (life.alive) group.restoreAssistantPicker(configuration); });
            }
            intent = null;
            if (life.alive && intent === null && original !== null && group.project === original.project && Session.project === original.project &&
                (picker === null || (!picker.cancelled && group.assistantPicker === picker)))
                original.project.loadDataInto(original.experiment, file);
        }
        onRejected: {
            const life = group.pickerLife;
            const original = intent;
            const picker = original !== null ? original.assistant : null;
            const configuration = original !== null ? original.configuration : null;
            if (configuration !== null) {
                configuration.retired = true;
                Qt.callLater(() => { if (life.alive) group.restoreAssistantPicker(configuration); });
            }
            intent = null;
        }
    }
}
