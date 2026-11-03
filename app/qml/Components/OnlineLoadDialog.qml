// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// From web…: one popup for structures, full experiments and measured data (ADR-0068). A source selector at the
// top, from the Preferences table; the fields of the chosen source, ID first; Search; a results table with a
// Kind column and Load per row. Loading hands the downloaded file to the project's ordinary loaders.
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

    objectName: "onlineLoad"
    title: kind === "structure" ? qsTr("Load structure from web") : kind === "experiment" ? qsTr("Load experiment from web") : qsTr("Load measured data from web")
    standardButtons: Dialog.Close
    width: Math.min(parent ? parent.width - 2 * EaStyle.Sizes.fontPixelSize : 0, EaStyle.Sizes.fontPixelSize * 62)

    function openFor(kind, experiment) {
        dialog.kind = kind;
        dialog.targetExperiment = experiment ?? null;
        dialog.values = {};
        search.kind = kind;
        const offered = search.sources.map(s => s.id);
        const remembered = dialog.lastSource[kind];
        if (offered.length > 0)
            search.sourceId = offered.indexOf(remembered) >= 0 ? remembered : offered[0];
        search.reset();
        dialog.visible = true;
    }

    function runSearch() {
        search.search(dialog.values);
    }

    // The entry's radiation and technique choose a new experiment's probe and beam mode when none is selected.
    function experimentFor(entry) {
        if (dialog.targetExperiment !== null)
            return dialog.targetExperiment;
        if (dialog.project === null || !dialog.project.createExperiment())
            return null;
        const index = dialog.project.currentExperimentIndex;
        const technique = String(entry.technique || "").toLowerCase();
        const radiation = String(entry.radiation || "").toLowerCase();
        if (technique.indexOf("single") >= 0)
            dialog.project.setExperimentType(index, "sampleForm", "single crystal");
        if (technique.indexOf("time") >= 0 || technique.indexOf("tof") >= 0)
            dialog.project.setExperimentType(index, "beamMode", "time-of-flight");
        if (radiation.indexOf("x") === 0)
            dialog.project.setExperimentType(index, "radiationProbe", "xray");
        return dialog.project.currentExperiment;
    }

    Connections {
        target: dialog.search
        function onFileReady(kind, file, entry) {
            if (!dialog.visible || dialog.project === null)
                return;
            let done = false;
            if (kind === "structure")
                done = dialog.project.loadStructure(file);
            else if (kind === "experiment")
                done = dialog.project.loadExperiments([file]);
            else {
                const experiment = dialog.experimentFor(entry);
                done = experiment !== null && dialog.project.loadDataInto(experiment, file);
            }
            if (done)
                dialog.close();
        }
    }

    contentItem: Column {
        spacing: EaStyle.Sizes.fontPixelSize

        Row {
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("Source") + ":"
            }
            EaElements.ComboBox {
                id: sourceBox
                objectName: "onlineLoad.source"
                width: EaStyle.Sizes.fontPixelSize * 18
                textRole: "name"
                valueRole: "id"
                model: dialog.search.sources
                currentIndex: Math.max(0, dialog.search.sources.findIndex(s => s.id === dialog.search.sourceId))
                onActivated: index => {
                    dialog.values = {};
                    dialog.search.sourceId = dialog.search.sources[index].id;
                    const remembered = Object.assign({}, dialog.lastSource);
                    remembered[dialog.kind] = dialog.search.sourceId;
                    dialog.lastSource = remembered;
                }
                ToolTip.text: qsTr("Where to search: the online sources enabled in Preferences")
            }
        }

        // The fields of the chosen source, ID first.
        Column {
            id: fieldColumn
            spacing: EaStyle.Sizes.fontPixelSize * 0.5
            readonly property real labelWidth: EaStyle.Sizes.fontPixelSize * 7
            Repeater {
                model: dialog.search.fields
                delegate: Row {
                    id: fieldRow
                    required property var modelData
                    spacing: EaStyle.Sizes.fontPixelSize
                    EaElements.Label {
                        width: fieldColumn.labelWidth
                        anchors.verticalCenter: parent.verticalCenter
                        horizontalAlignment: Text.AlignRight
                        text: fieldRow.modelData.label + ":"
                    }
                    EaElements.TextField {
                        objectName: "onlineLoad.field." + fieldRow.modelData.key
                        width: EaStyle.Sizes.fontPixelSize * 24
                        horizontalAlignment: TextInput.AlignLeft
                        placeholderText: fieldRow.modelData.hint
                        text: dialog.values[fieldRow.modelData.key] ?? ""
                        onTextEdited: {
                            const next = Object.assign({}, dialog.values);
                            next[fieldRow.modelData.key] = text;
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
                width: EaStyle.Sizes.fontPixelSize * 10
                fontIcon: "search"
                text: dialog.search.busy ? qsTr("Searching…") : qsTr("Search")
                enabled: !dialog.search.busy && dialog.search.sourceId !== ""
                ToolTip.text: qsTr("Search the selected source with the fields above; empty fields do not filter")
                onClicked: dialog.runSearch()
            }
            EaElements.Label {
                objectName: "onlineLoad.message"
                anchors.verticalCenter: parent.verticalCenter
                width: dialog.width - EaStyle.Sizes.fontPixelSize * 14 - (alternative.visible ? alternative.width + parent.spacing : 0)
                visible: text !== ""
                wrapMode: Text.Wrap
                color: dialog.search.message !== "" ? EaStyle.Colors.themeForegroundHighlight : EaStyle.Colors.themeForegroundMinor
                text: dialog.search.message !== "" ? dialog.search.message : dialog.search.searched && dialog.search.results.count === 0 ? qsTr("Nothing found") : ""
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

        DataTable {
            id: results
            objectName: "onlineLoad.results"
            width: dialog.width - 2 * EaStyle.Sizes.fontPixelSize
            maxRowCountShow: 8
            sourceModel: dialog.search.results
            defaultInfoText: dialog.search.searched ? qsTr("No entries") : qsTr("Search to list entries")
            columns: [numberColumnWidth, AppSizes.dataColumnWidth, AppSizes.dataColumnWidth * 1.6, AppSizes.dataColumnWidth * 2.8, AppSizes.dataColumnWidth * 1.4, -1, AppSizes.iconColumnWidth]
            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {}
                EaComponents.ListViewLabel {
                    text: qsTr("Kind")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    text: qsTr("ID")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    text: qsTr("Name")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    text: dialog.kind === "structure" ? qsTr("Formula") : qsTr("Instrument")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {
                    text: dialog.kind === "structure" ? qsTr("Space group") : qsTr("Technique")
                    horizontalAlignment: Text.AlignLeft
                }
                EaComponents.ListViewLabel {}
            }
            delegate: TableRow {
                id: row
                required property string id
                required property string kind
                required property string name
                required property string formula
                required property string spaceGroup
                required property string cell
                required property string radiation
                required property string technique
                required property string instrument
                required property string source
                objectName: `onlineLoad.row.${row.index}`
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: row.index + 1
                }
                EaComponents.ListViewLabel {
                    objectName: `onlineLoad.kind.${row.index}`
                    horizontalAlignment: Text.AlignLeft
                    text: row.kind === "structure" ? qsTr("Structure") : row.kind === "experiment" ? qsTr("Experiment") : qsTr("Data")
                }
                EaComponents.ListViewLabel {
                    objectName: `onlineLoad.id.${row.index}`
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideMiddle
                    text: row.id
                    ToolTip.text: row.source
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: row.name
                    ToolTip.text: row.cell !== "" ? qsTr("Cell") + ": " + row.cell : ""
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: dialog.kind === "structure" ? row.formula : row.instrument
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    elide: Text.ElideRight
                    text: dialog.kind === "structure" ? row.spaceGroup : [row.radiation, row.technique].filter(s => s !== "").join(", ")
                }
                EaComponents.ListViewButton {
                    objectName: `onlineLoad.load.${row.index}`
                    horizontalAlignment: Text.AlignHCenter
                    fontIcon: "download"
                    enabled: !dialog.search.busy && dialog.project !== null
                    ToolTip.text: row.kind === "structure" ? qsTr("Load this structure into the project") : row.kind === "experiment" ? qsTr("Open this experiment in the project") : dialog.targetExperiment !== null ? qsTr("Load this data into %1").arg(dialog.targetExperiment.name) : qsTr("Load this data into a new experiment")
                    onClicked: dialog.search.load(row.index)
                }
            }
        }
    }
}
