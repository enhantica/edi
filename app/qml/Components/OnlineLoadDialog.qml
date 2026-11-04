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
    // The selected result, the table's own single selection, -1 for none; Load acts on it.
    readonly property int selectedRow: results.selectedIndexes !== undefined && results.selectedIndexes.length === 1 ? results.selectedIndexes[0].row : -1
    readonly property bool canLoad: selectedRow >= 0 && selectedRow < search.results.count && !search.busy && project !== null

    objectName: "onlineLoad"
    title: kind === "structure" ? qsTr("Load structure from web") : kind === "experiment" ? qsTr("Load experiment from web") : qsTr("Load measured data from web")
    // Wide enough for the results' columns, up to about nine tenths of the window.
    contentWidth: Math.min(parent ? Math.floor(parent.width * 0.9) - 2 * EaStyle.Sizes.fontPixelSize : 0, EaStyle.Sizes.fontPixelSize * 96)
    contentHeight: column.implicitHeight

    function openFor(kind, experiment) {
        dialog.kind = kind;
        dialog.targetExperiment = experiment ?? null;
        dialog.values = {};
        dialog.deliveryMessage = "";
        results.clearSelection();
        search.kind = kind;
        const remembered = dialog.lastSource[kind];
        if (search.sources.count > 0)
            search.sourceId = search.sources.indexOfKey(remembered) >= 0 ? remembered : search.sources.keyAt(0);
        search.reset();
        dialog.visible = true;
    }

    function runSearch() {
        results.clearSelection();
        for (let row = 0; row < search.fields.count; ++row) {
            const key = search.fields.keyAt(row);
            search.setField(key, dialog.values[key] ?? "");
        }
        search.search();
    }

    function loadSelected() {
        if (dialog.canLoad)
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

    // The cell as the bridge displays each length and angle, compact: "3.89 3.89 3.89 90 90 90".
    function cellText(row) {
        if (!row.hasCell)
            return "";
        return [Session.display("cell.length_a", row.cellA), Session.display("cell.length_b", row.cellB), Session.display("cell.length_c", row.cellC), Session.display("cell.angle_alpha", row.cellAlpha), Session.display("cell.angle_beta", row.cellBeta), Session.display("cell.angle_gamma", row.cellGamma)].join(" ");
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
        function onFileReady(kind, file, entry, project, target, newTarget) {
            if (!dialog.visible || dialog.project === null)
                return;
            if (project !== dialog.project) {
                dialog.deliveryMessage = qsTr("The project changed while the download was running; nothing was loaded");
                return;
            }
            let done = false;
            if (kind === "structure")
                done = dialog.project.loadStructure(file);
            else if (kind === "experiment")
                done = dialog.project.loadExperiments([file]);
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
            else
                dialog.deliveryMessage = dialog.project.lastError;
        }
    }
    contentItem: Column {
        id: column
        width: dialog.contentWidth
        spacing: EaStyle.Sizes.fontPixelSize

        // The source: a row of its own, as a form's first line.
        Row {
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.Label {
                width: column.labelWidth
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignRight
                text: qsTr("Source") + ":"
            }
            EaElements.ComboBox {
                id: sourceBox
                objectName: "onlineLoad.source"
                width: column.fieldWidth
                textRole: "name"
                valueRole: "key"
                model: dialog.search.sources
                currentIndex: Math.max(0, dialog.search.sources.indexOfKey(dialog.search.sourceId))
                // The shown name follows the chosen source, also after the kind's source list was rebuilt.
                displayText: Session.onlineSources.nameOf(dialog.search.sourceId)
                onActivated: index => {
                    dialog.values = {};
                    dialog.deliveryMessage = "";
                    results.clearSelection();
                    dialog.search.sourceId = dialog.search.sources.keyAt(index);
                    const remembered = Object.assign({}, dialog.lastSource);
                    remembered[dialog.kind] = dialog.search.sourceId;
                    dialog.lastSource = remembered;
                }
                // The base combo box has no tool tip of its own; this one follows the preference as the others do.
                EaElements.ToolTip {
                    text: qsTr("Where to search: the online sources enabled in Preferences")
                    visible: sourceBox.hovered && EaGlobals.Vars.showToolTips
                }
            }
        }
        readonly property real labelWidth: EaStyle.Sizes.fontPixelSize * 7
        readonly property real fieldWidth: Math.min(EaStyle.Sizes.fontPixelSize * 28, dialog.contentWidth - labelWidth - EaStyle.Sizes.fontPixelSize)

        // The fields of the chosen source, ID first, one per line.
        Column {
            id: fieldColumn
            spacing: EaStyle.Sizes.fontPixelSize * 0.5
            Repeater {
                model: dialog.search.fields
                delegate: Row {
                    id: fieldRow
                    required property string key
                    required property string hint
                    spacing: EaStyle.Sizes.fontPixelSize
                    EaElements.Label {
                        width: column.labelWidth
                        anchors.verticalCenter: parent.verticalCenter
                        horizontalAlignment: Text.AlignRight
                        text: dialog.fieldLabel(fieldRow.key) + ":"
                    }
                    EaElements.TextField {
                        objectName: "onlineLoad.field." + fieldRow.key
                        width: column.fieldWidth
                        horizontalAlignment: TextInput.AlignLeft
                        placeholderText: fieldRow.hint
                        text: dialog.values[fieldRow.key] ?? ""
                        onTextEdited: {
                            const next = Object.assign({}, dialog.values);
                            next[fieldRow.key] = text;
                            dialog.values = next;
                        }
                        onAccepted: dialog.runSearch()
                    }
                }
            }
        }

        Row {
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.SideBarButton {
                objectName: "onlineLoad.search"
                width: EaStyle.Sizes.fontPixelSize * 12
                fontIcon: "search"
                text: dialog.search.busy && dialog.selectedRow < 0 ? qsTr("Searching…") : qsTr("Search")
                enabled: !dialog.search.busy && dialog.search.sourceId !== ""
                ToolTip.text: qsTr("Search the selected source with the fields above; empty fields do not filter")
                onClicked: dialog.runSearch()
            }
            EaElements.Label {
                id: messageLabel
                objectName: "onlineLoad.message"
                anchors.verticalCenter: parent.verticalCenter
                width: dialog.contentWidth - EaStyle.Sizes.fontPixelSize * 13 - (alternative.visible ? alternative.width + parent.spacing : 0)
                visible: text !== ""
                wrapMode: Text.Wrap
                color: dialog.search.message !== "" || dialog.deliveryMessage !== "" ? EaStyle.Colors.themeForegroundHighlight : EaStyle.Colors.themeForegroundMinor
                text: dialog.search.message !== "" ? dialog.search.message : dialog.deliveryMessage !== "" ? dialog.deliveryMessage : dialog.search.searched && dialog.search.results.count === 0 ? qsTr("Nothing found") : ""
                HoverHandler {
                    id: messageHover
                }
                EaElements.ToolTip {
                    text: dialog.search.detail
                    visible: text !== "" && messageHover.hovered && EaGlobals.Vars.showToolTips
                }
            }
            // An unreachable source offers the next one that holds this kind.
            EaElements.SideBarButton {
                id: alternative
                objectName: "onlineLoad.alternative"
                visible: dialog.search.unreachable && dialog.search.alternativeId !== ""
                width: EaStyle.Sizes.fontPixelSize * 16
                fontIcon: "cloud-download-alt"
                text: qsTr("Search %1 instead").arg(dialog.search.alternativeName)
                onClicked: {
                    dialog.search.useAlternative();
                    dialog.runSearch();
                }
            }
        }

        // The results, this kind only, fitted to the popup: the flexible column takes what the fixed ones leave.
        DataTable {
            id: results
            objectName: "onlineLoad.results"
            width: dialog.contentWidth
            maxRowCountShow: 8
            sourceModel: dialog.search.results
            defaultInfoText: dialog.search.searched ? qsTr("No entries") : qsTr("Search to list entries")
            readonly property bool structures: dialog.kind === "structure"
            // Name and Reference share what the fixed columns leave; the cell shows six displayed values.
            columns: structures ? [numberColumnWidth, AppSizes.dataColumnWidth * 1.3, -1, AppSizes.dataColumnWidth * 1.7, AppSizes.dataColumnWidth * 1.3, AppSizes.dataColumnWidth * 3.6, -1] : [numberColumnWidth, AppSizes.dataColumnWidth * 1.6, -1, AppSizes.dataColumnWidth * 1.6, AppSizes.dataColumnWidth * 2.2]
            spreadColumns: structures ? [2, 6] : [2]
            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {}
                EaComponents.ListViewLabel {
                    text: qsTr("ID")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    text: qsTr("Name")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    text: results.structures ? qsTr("Formula") : Session.categoryTitle("instrument")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    text: results.structures ? Session.categoryTitle("space_group") : qsTr("Technique")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    visible: results.structures
                    text: Session.categoryTitle("cell")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    visible: results.structures
                    text: qsTr("Reference")
                    horizontalAlignment: Text.AlignLeft
                }
            }
            delegate: TableRow {
                id: row
                required property var model
                required property string name
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
                required property string referenceUrl
                objectName: `onlineLoad.row.${row.index}`
                // A click selects the row through the table's own selection; a double click loads it. Beneath the
                // cells, so the reference's link keeps its own click.
                MouseArea {
                    parent: row
                    anchors.fill: parent
                    z: -1
                    onClicked: mouse => results.selectWithModifiers(row.index, mouse.modifiers)
                    onDoubleClicked: {
                        results.selectWithModifiers(row.index, Qt.NoModifier);
                        dialog.loadSelected();
                    }
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: row.index + 1
                }
                EaComponents.ListViewLabel {
                    objectName: `onlineLoad.id.${row.index}`
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideMiddle
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
                    text: results.structures ? row.formula : row.instrument
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: results.structures ? row.spaceGroup : [row.radiation, row.technique].filter(s => s !== "").join(", ")
                }
                EaComponents.ListViewLabel {
                    visible: results.structures
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: dialog.cellText(row)
                }
                EaComponents.ListViewLabel {
                    id: referenceCell
                    objectName: `onlineLoad.reference.${row.index}`
                    visible: results.structures
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: row.reference
                    color: row.referenceUrl !== "" ? EaStyle.Colors.themeForegroundHighlight : EaStyle.Colors.themeForeground
                    // The DOI opens in the browser; a click elsewhere on the row selects it as any click does.
                    TapHandler {
                        enabled: row.referenceUrl !== ""
                        acceptedButtons: Qt.LeftButton
                        onTapped: Qt.openUrlExternally(row.referenceUrl)
                    }
                }
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
                enabled: dialog.canLoad
                text: dialog.search.busy && dialog.selectedRow >= 0 ? qsTr("Loading…") : qsTr("Load")
                ToolTip.text: dialog.kind === "structure" ? qsTr("Load the selected structure into the project") : dialog.kind === "experiment" ? qsTr("Open the selected experiment in the project") : dialog.targetExperiment !== null ? qsTr("Load the selected pattern into %1").arg(dialog.targetExperiment.name) : qsTr("Create an experiment from the selected data")
                onClicked: dialog.loadSelected()
            }
        }
    }
}
