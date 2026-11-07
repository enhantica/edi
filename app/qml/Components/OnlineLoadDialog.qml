// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// From web…: one popup for structures, full experiments and measured data (ADR-0068), laid out as the app's other
// dialogs: the source, the fields of the chosen source in a column, Search, and a results table of this kind only. A
// click selects a row, Load at the bottom (or a double click) loads the selected entry through the project's ordinary
// loaders (the owner, 2026-11-04).
AppDialog {
    id: dialog

    // structure, experiment or data: which sources are offered and where a loaded file goes.
    property string kind: "structure"
    property ProjectViewModel project: null
    // The experiment measured data goes into; null creates one from the entry's radiation and technique.
    property ExperimentViewModel targetExperiment: null
    readonly property OnlineSearch search: Session.onlineSearch
    property var values: ({})
    // The source last used for each kind; a kind opens at its first source until one is chosen.
    property var lastSource: ({})
    // The selected result, the table's own single selection, -1 for none; Load acts on it. Measured data takes
    // several at once (the owner, 2026-11-04): Ctrl or Shift adds rows, and Load downloads them all.
    readonly property var selectedRows: results.selectedIndexes !== undefined ? results.selectedIndexes.map(i => i.row).sort((a, b) => a - b) : []
    readonly property int selectedRow: selectedRows.length === 1 ? selectedRows[0] : -1
    readonly property bool canLoad: (selectedRow >= 0 || (kind === "data" && selectedRows.length > 1)) && !search.busy && project !== null
    // Several measured data files downloaded for the page to ask how to load (Load N datasets as).
    signal datasetsReady(var files, var experiment)

    objectName: "onlineLoad"
    title: kind === "structure" ? qsTr("Load structure from web") : kind === "experiment" ? qsTr("Load experiment from web") : qsTr("Load measured data from web")
    // Three field columns, each as wide as its longest placeholder needs (the owner, 2026-11-04), the same for every kind;
    // the results table fills that width. Never wider than the window.
    TextMetrics {
        id: widestPlaceholder
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        text: qsTr("Space group, Hermann-Mauguin: P m -3 m")
    }
    readonly property real fieldColumnWidth: Math.ceil(widestPlaceholder.advanceWidth) + 2 * EaStyle.Sizes.fontPixelSize
    // A structure's table needs more: its ID and cell in full and a reference about half as wide again (the owner,
    // 2026-11-04).
    contentWidth: Math.min(parent ? Math.floor(parent.width * 0.95) - 2 * EaStyle.Sizes.fontPixelSize : 0, (kind === "structure" ? 1.3 : 1) * (3 * fieldColumnWidth + 2 * EaStyle.Sizes.fontPixelSize))
    contentHeight: column.implicitHeight

    // Moves whenever the fields are rebuilt (a source change, the collection's values arriving), so each field reads
    // its options again.
    property int fieldsRevision: 0
    Connections {
        target: dialog.search
        function onFieldsChanged() {
            dialog.fieldsRevision += 1;
        }
    }

    function openFor(kind, experiment) {
        dialog.kind = kind;
        dialog.targetExperiment = experiment ?? null;
        dialog.deliveryMessage = "";
        results.clearSelection();
        search.kind = kind;
        const remembered = dialog.lastSource[kind];
        if (search.sources.count > 0)
            search.sourceId = search.sources.indexOfKey(remembered) >= 0 ? remembered : search.sources.keyAt(0);
        dialog.recall();
        search.prepare();
        dialog.visible = true;
    }

    // This kind and source's last search, for the session: its fields, results and selected row come back.
    function recall() {
        results.clearSelection();
        search.recall();
        dialog.values = search.fieldValues();
        const row = search.rememberedSelection();
        if (row >= 0)
            Qt.callLater(() => {
                if (dialog.visible && row < search.results.count && dialog.selectedRow < 0)
                    results.selectWithModifiers(row, Qt.NoModifier);
            });
    }

    function runSearch() {
        results.clearSelection();
        dialog.deliveryMessage = "";
        for (let row = 0; row < search.fields.count; ++row) {
            const key = search.fields.keyAt(row);
            search.setField(key, dialog.values[key] ?? "");
        }
        search.search();
    }

    function clearSearch() {
        results.clearSelection();
        dialog.deliveryMessage = "";
        dialog.values = {};
        search.clear();
    }

    function loadSelected() {
        if (!dialog.canLoad)
            return;
        if (dialog.selectedRows.length > 1)
            dialog.search.loadMany(dialog.selectedRows, dialog.project, dialog.targetExperiment);
        else
            dialog.search.load(dialog.selectedRow, dialog.project, dialog.targetExperiment);
    }

    // A field's name: the dictionary's for an item it holds, the popup's own for the rest.
    function fieldLabel(key) {
        switch (key) {
        case "id":
            return qsTr("ID");
        case "name":
            return qsTr("Name");
        case "formula":
            return qsTr("Formula");
        case "elements":
            return qsTr("Elements");
        case "space_group":
            return Session.categoryTitle("space_group");
        case "radiation":
            return qsTr("Radiation");
        case "technique":
            return qsTr("Technique");
        case "instrument":
            return Session.categoryTitle("instrument");
        }
        return key;
    }
    // The title inside the field, with its short hint: "Formula, any order: LaCoO3, La Co O3".
    function placeholder(key) {
        const row = search.fields.indexOfKey(key);
        const hint = row >= 0 ? search.fields.hintAt(row) : "";
        return hint === "" ? fieldLabel(key) : fieldLabel(key) + ", " + hint;
    }
    function fieldOptions(key) {
        const row = search.fields.indexOfKey(key);
        return row >= 0 ? search.fields.optionsAt(row) : [];
    }

    // The cell, compact: lengths with two decimals, angles with one (the owner, 2026-11-04).
    function cellText(row) {
        if (!row.hasCell)
            return "";
        return [row.cellA.toFixed(2), row.cellB.toFixed(2), row.cellC.toFixed(2), row.cellAlpha.toFixed(1), row.cellBeta.toFixed(1), row.cellGamma.toFixed(1)].join(" ");
    }

    // How many entries the search matched, and how many of them the table holds while a long answer loads.
    function countText() {
        if (search.total < 0)
            return "";
        const total = Number(search.total).toLocaleString(Qt.locale(), "f", 0);
        if (search.results.count < search.total)
            return qsTr("%1 entries, %2 loaded").arg(total).arg(search.results.count);
        return search.total === 1 ? qsTr("1 entry") : qsTr("%1 entries").arg(total);
    }

    // A new experiment's type from the entry: its technique and radiation when it states them, else the page's
    // pending selectors (ProjectViewModel.newExperiment…); the project refuses an impossible pair before anything
    // is created.
    function typeTokens(entry) {
        const technique = String(entry.technique || "").toLowerCase();
        const radiation = String(entry.radiation || "").toLowerCase();
        return {
            sampleForm: technique === "" ? "" : technique.indexOf("single") >= 0 ? "single crystal" : "powder",
            beamMode: technique === "" ? "" : (technique.indexOf("time") >= 0 || technique.indexOf("tof") >= 0) ? "time-of-flight" : "constant wavelength",
            radiationProbe: radiation === "" ? "" : radiation.indexOf("x") === 0 ? "xray" : "neutron"
        };
    }

    // A late answer is refused when its project is no longer the open one, or its measured-data target has gone.
    property string deliveryMessage: ""

    Connections {
        target: dialog.search
        function onFilesReady(files, project, target) {
            if (!dialog.visible || dialog.project === null || project !== dialog.project)
                return;
            dialog.close();
            dialog.datasetsReady(files, target);
        }
        function onFileReady(kind, file, entry, project, target, newTarget) {
            if (!dialog.visible || dialog.project === null)
                return;
            if (project !== dialog.project) {
                dialog.deliveryMessage = qsTr("The project changed while the download was running; nothing was loaded");
                return;
            }
            // A refused load says why in the window's dialog (the project's refusal), once (the owner, 2026-11-04).
            let done = false;
            if (kind === "structure")
                done = dialog.project.loadStructure(file);
            else if (kind === "experiment")
                done = dialog.project.loadExperimentWithStructures(file, entry.structureFiles, entry.name !== "" ? entry.name : entry.id);
            else if (!newTarget && target === null) {
                dialog.deliveryMessage = qsTr("The experiment the data was for is no longer in the project; nothing was loaded");
                return;
            } else if (!newTarget)
                done = dialog.project.loadDataInto(target, file);
            else {
                const type = dialog.typeTokens(entry);
                done = dialog.project.loadDataIntoNewExperiment(file, type.sampleForm, type.beamMode, type.radiationProbe);
            }
            if (done)
                dialog.close();
        }
    }
    // One field of the form: a text field with its title and hint inside, or, for a field with values to choose from
    // (radiation, technique), a selector with "Any" first (the owner, 2026-11-04).
    component FieldSlot: Item {
        id: fieldSlot
        property string key: ""
        readonly property var options: dialog.fieldsRevision >= 0 ? dialog.fieldOptions(key) : []
        readonly property var choices: [""].concat(options)
        width: column.cellWidth
        height: options.length > 0 ? box.height : textField.height
        EaElements.TextField {
            id: textField
            objectName: "onlineLoad.field." + fieldSlot.key
            visible: fieldSlot.options.length === 0
            width: parent.width
            horizontalAlignment: TextInput.AlignLeft
            placeholderText: dialog.fieldsRevision >= 0 ? dialog.placeholder(fieldSlot.key) : ""
            text: dialog.values[fieldSlot.key] ?? ""
            onTextEdited: {
                const next = Object.assign({}, dialog.values);
                next[fieldSlot.key] = text;
                dialog.values = next;
            }
            onAccepted: dialog.runSearch()
        }
        EaElements.ComboBox {
            id: box
            objectName: "onlineLoad.choice." + fieldSlot.key
            visible: fieldSlot.options.length > 0
            width: parent.width
            model: fieldSlot.choices.map(value => value === "" ? qsTr("Any %1").arg(dialog.fieldLabel(fieldSlot.key).toLowerCase()) : value)
            currentIndex: Math.max(0, fieldSlot.choices.indexOf(dialog.values[fieldSlot.key] ?? ""))
            onActivated: index => {
                const next = Object.assign({}, dialog.values);
                next[fieldSlot.key] = fieldSlot.choices[index];
                dialog.values = next;
            }
        }
    }

    contentItem: Column {
        id: column
        width: dialog.contentWidth
        spacing: EaStyle.Sizes.fontPixelSize

        // The form in rows of three equal columns (the owner, 2026-11-04): the source, ID and Name; Formula, Elements and
        // the kind's third field; for experiments and data Technique and Instrument; then Search and Clear, each as wide
        // as a column, and the search's message.
        readonly property real cellWidth: (width - 2 * EaStyle.Sizes.fontPixelSize) / 3
        Row {
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.ComboBox {
                id: sourceBox
                objectName: "onlineLoad.source"
                width: column.cellWidth
                ToolTip.text: qsTr("Where to search: the online sources enabled in Preferences")
                ToolTip.visible: sourceBox.hovered && EaGlobals.Vars.showToolTips
                textRole: "name"
                valueRole: "key"
                model: dialog.search.sources
                currentIndex: Math.max(0, dialog.search.sources.indexOfKey(dialog.search.sourceId))
                // The shown name follows the chosen source, also after the kind's source list was rebuilt.
                displayText: Session.onlineSources.nameOf(dialog.search.sourceId)
                onActivated: index => {
                    dialog.deliveryMessage = "";
                    dialog.search.sourceId = dialog.search.sources.keyAt(index);
                    const remembered = Object.assign({}, dialog.lastSource);
                    remembered[dialog.kind] = dialog.search.sourceId;
                    dialog.lastSource = remembered;
                    dialog.recall();
                    dialog.search.prepare();
                }
            }
            FieldSlot {
                key: "id"
            }
            FieldSlot {
                key: "name"
            }
        }
        Row {
            spacing: EaStyle.Sizes.fontPixelSize
            FieldSlot {
                key: "formula"
            }
            FieldSlot {
                key: "elements"
            }
            FieldSlot {
                visible: dialog.kind === "structure"
                key: "space_group"
            }
        }
        // Experiments and measured data: Radiation, Technique and Instrument on one row (the owner, 2026-11-04).
        Row {
            visible: dialog.kind !== "structure"
            spacing: EaStyle.Sizes.fontPixelSize
            FieldSlot {
                key: "radiation"
            }
            FieldSlot {
                key: "technique"
            }
            FieldSlot {
                key: "instrument"
            }
        }
        Row {
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.SideBarButton {
                objectName: "onlineLoad.search"
                // Search and Clear share the first column (the owner, 2026-11-04).
                width: (column.cellWidth - EaStyle.Sizes.fontPixelSize) / 2
                fontIcon: "search"
                text: dialog.search.busy && dialog.selectedRow < 0 ? qsTr("Searching…") : qsTr("Search")
                enabled: !dialog.search.busy && dialog.search.sourceId !== ""
                ToolTip.text: qsTr("Search the selected source with the fields above; empty fields do not filter")
                onClicked: dialog.runSearch()
            }
            EaElements.SideBarButton {
                objectName: "onlineLoad.clear"
                width: (column.cellWidth - EaStyle.Sizes.fontPixelSize) / 2
                fontIcon: "eraser"
                text: qsTr("Clear")
                enabled: !dialog.search.busy
                ToolTip.text: qsTr("Empty the fields and the results; the next search starts afresh")
                onClicked: dialog.clearSearch()
            }
            // The search's message, or for an unreachable source the next one that holds this kind, over the other two
            // columns.
            Item {
                width: 2 * column.cellWidth + EaStyle.Sizes.fontPixelSize
                height: alternative.visible ? alternative.height : messageLabel.implicitHeight
                anchors.verticalCenter: parent.verticalCenter
                EaElements.Label {
                    id: messageLabel
                    objectName: "onlineLoad.message"
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width
                    visible: text !== "" && !alternative.visible
                    elide: Text.ElideRight
                    color: dialog.search.message !== "" || dialog.deliveryMessage !== "" ? EaStyle.Colors.themeForegroundHighlight : EaStyle.Colors.themeForegroundMinor
                    text: dialog.search.message !== "" ? dialog.search.message : dialog.deliveryMessage !== "" ? dialog.deliveryMessage : dialog.search.searched && dialog.search.results.count === 0 && dialog.search.total <= 0 ? qsTr("Nothing found") : ""
                    HoverHandler {
                        id: messageHover
                    }
                    EaElements.ToolTip {
                        text: dialog.search.detail !== "" ? dialog.search.detail : messageLabel.text
                        visible: messageHover.hovered && EaGlobals.Vars.showToolTips
                    }
                }
                EaElements.SideBarButton {
                    id: alternative
                    objectName: "onlineLoad.alternative"
                    visible: dialog.search.unreachable && dialog.search.alternativeId !== ""
                    width: parent.width
                    fontIcon: "cloud-download-alt"
                    text: qsTr("%1 cannot be reached: search %2").arg(dialog.search.sourceName).arg(dialog.search.alternativeName)
                    onClicked: {
                        dialog.search.useAlternative();
                        dialog.runSearch();
                    }
                }
            }
        }

        // The count above the table, for every search (the owner, 2026-11-04).
        EaElements.Label {
            objectName: "onlineLoad.count"
            visible: text !== ""
            color: EaStyle.Colors.themeForegroundMinor
            text: dialog.countText()
        }

        // The results, this kind only. Every column fits its content after each answer; the one named in
        // spreadColumns takes what is left and elides (Reference for structures, Description otherwise).
        DataTable {
            id: results
            objectName: "onlineLoad.results"
            width: column.width
            maxRowCountShow: 8
            multiSelection: dialog.kind === "data"
            sourceModel: dialog.search.results
            defaultInfoText: dialog.search.searched ? qsTr("No entries") : qsTr("Search to list entries")
            readonly property bool structures: dialog.kind === "structure"
            // Eight columns for every kind, so header and cells pair up; structures show no Description (a column the
            // width of nothing, as the Experiments table hides one) and give Reference what is left, the other kinds
            // give it to Description. Never wider than the popup: a row too narrow narrows its texts.
            columns: structures ? [numberColumnWidth, -1, -1, 0.001, -1, -1, -1, -1] : [numberColumnWidth, -1, -1, -1, -1, -1, -1, -1]
            spreadColumns: structures ? [7] : [3]
            clip: true
            // A long COD answer loads 100 at a time: the next chunk is asked for one chunk ahead of the end.
            onContentYChanged: {
                if (dialog.search.moreAvailable && !dialog.search.loadingMore && dialog.search.chunkError === "" && count > 0) {
                    const rowHeight = contentHeight / count;
                    if (contentHeight - (contentY + height) < 100 * rowHeight)
                        dialog.search.loadMore();
                }
            }
            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {}
                EaComponents.ListViewLabel {
                    elide: Text.ElideNone
                    text: qsTr("ID")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    text: qsTr("Name")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    text: results.structures ? "" : qsTr("Description")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideNone
                    text: qsTr("Formula")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideNone
                    text: results.structures ? Session.categoryTitle("space_group") : qsTr("Radiation")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideNone
                    text: results.structures ? Session.categoryTitle("cell") : qsTr("Technique")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideNone
                    text: results.structures ? qsTr("Reference") : Session.categoryTitle("instrument")
                    horizontalAlignment: Text.AlignLeft
                }
            }
            delegate: TableRow {
                id: row
                required property var model
                required property string name
                required property string description
                required property string formula
                required property string spaceGroup
                required property bool hasCell
                required property double cellA
                required property double cellB
                required property double cellC
                required property double cellAlpha
                required property double cellBeta
                required property double cellGamma
                required property string radiation
                required property string technique
                required property string instrument
                required property string source
                required property string reference
                required property string referenceStyled
                required property string referenceUrl
                objectName: `onlineLoad.row.${row.index}`
                // A click loads the row's entry (the owner, 2026-11-04); in the measured-data popup Ctrl or Shift selects
                // several rows instead, for Load N. Beneath the cells, so the reference's link keeps its own click.
                MouseArea {
                    parent: row
                    anchors.fill: parent
                    z: -1
                    cursorShape: Qt.PointingHandCursor
                    onClicked: mouse => {
                        const adding = dialog.kind === "data" && (mouse.modifiers & (Qt.ControlModifier | Qt.ShiftModifier));
                        results.selectWithModifiers(row.index, adding ? mouse.modifiers : Qt.NoModifier);
                        dialog.search.rememberSelection(row.index);
                        if (!adding)
                            dialog.loadSelected();
                    }
                }
                // The row number as the app's other tables show it: greyed, highlighted with the selected row.
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                EaComponents.ListViewLabel {
                    objectName: `onlineLoad.id.${row.index}`
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideNone  // ID, Formula, Space group or Radiation, Cell and Instrument show in full (the owner, 2026-11-04)
                    text: row.model.id
                    ToolTip.text: row.source
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: row.name
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: results.structures ? "" : row.description
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideNone
                    text: row.formula
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideNone
                    text: results.structures ? row.spaceGroup : row.radiation
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: results.structures ? Text.ElideNone : Text.ElideRight
                    text: results.structures ? dialog.cellText(row) : row.technique
                }
                EaComponents.ListViewLabel {
                    id: referenceCell
                    objectName: `onlineLoad.reference.${row.index}`
                    horizontalAlignment: Text.AlignLeft
                    elide: results.structures ? Text.ElideRight : Text.ElideNone
                    // The reference with its authors in italic, in the ordinary colour; a DOI shows as a link only under
                    // the pointer and opens in the browser (the owner, 2026-11-04). The whole reference is its tool tip.
                    readonly property bool linked: results.structures && row.referenceUrl !== ""
                    textFormat: results.structures ? Text.StyledText : Text.PlainText
                    text: results.structures ? row.referenceStyled : row.instrument
                    color: linked && referenceHover.hovered ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
                    font.underline: linked && referenceHover.hovered
                    ToolTip.text: results.structures ? row.reference : row.instrument
                    HoverHandler {
                        id: referenceHover
                        cursorShape: referenceCell.linked ? Qt.PointingHandCursor : Qt.ArrowCursor
                    }
                    TapHandler {
                        enabled: referenceCell.linked
                        acceptedButtons: Qt.LeftButton
                        onTapped: Qt.openUrlExternally(row.referenceUrl)
                    }
                }
            }
        }
        // A chunk of a long answer that did not arrive: the rows shown stay, this line offers it again.
        Row {
            objectName: "onlineLoad.chunk"
            visible: dialog.search.chunkError !== "" || dialog.search.loadingMore
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                width: column.width - (retry.visible ? retry.width + parent.spacing : 0)
                elide: Text.ElideRight
                color: dialog.search.chunkError !== "" ? EaStyle.Colors.themeForegroundHighlight : EaStyle.Colors.themeForegroundMinor
                text: dialog.search.chunkError !== "" ? qsTr("The next entries could not be loaded: %1").arg(dialog.search.chunkError) : qsTr("Loading the next entries…")
            }
            EaElements.Button {
                id: retry
                objectName: "onlineLoad.retry"
                visible: dialog.search.chunkError !== ""
                text: qsTr("Retry")
                onClicked: dialog.search.loadMore()
            }
        }

        // Close and Load, as the app's dialogs place their actions.
        Row {
            id: actions
            anchors.right: parent.right
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.Button {
                objectName: "onlineLoad.close"
                text: qsTr("Close")
                onClicked: dialog.close()
            }
            EaElements.Button {
                objectName: "onlineLoad.load"
                visible: dialog.selectedRows.length > 1
                enabled: dialog.canLoad
                text: dialog.search.busy ? qsTr("Loading…") : qsTr("Load %1").arg(dialog.selectedRows.length)
                ToolTip.text: dialog.kind === "structure" ? qsTr("Load the selected structure into the project") : dialog.kind === "experiment" ? qsTr("Open the selected experiment in the project, with the structures it links") : dialog.targetExperiment !== null ? qsTr("Load the selected pattern into %1").arg(dialog.targetExperiment.name) : qsTr("Create an experiment from the selected data")
                onClicked: dialog.loadSelected()
            }
        }
    }
}
