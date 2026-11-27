// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Crystal → Magnetic (edi ADR-0078 "The magnetic popup", crysta ADR-0137): pick a propagation vector, the magnetic
// sites and the magnetic groups to add; each picked group becomes a new structure linked where the parent is. Cancel
// changes nothing.
AppDialog {
    id: popup
    objectName: "structures.magneticPopup"

    property ProjectViewModel project: null
    property int structureIndex: -1
    property StructureViewModel structure: null

    property var presets: []
    property var sites: []
    property var found: null
    property string refusal: ""
    property bool busy: false

    title: qsTr("Magnetic structures from %1").arg(structure ? structure.name : "")
    standardButtons: Dialog.Cancel
    width: Math.min(parent ? parent.width - 80 : 1000, 1100)
    height: Math.min(parent ? parent.height - 80 : 800, 860)
    onClosed: destroy()

    readonly property string k: kChoice.currentIndex >= 0 && kChoice.currentIndex < presets.length ? presets[kChoice.currentIndex].k : [0, 1, 2].map(i => kFields.itemAt(i) ? (kFields.itemAt(i) as EaElements.TextField).text : "0").join(",")

    // Find k from data (crysta ADR-0137 A11): the experiments a kept fit covers, its unexplained peaks and the
    // ranked k.
    property var dataChoices: []
    property var peaks: []
    property var peakTicks: []
    property var kRows: []
    property bool searching: false
    property bool findKShown: false
    property string kRefusal: ""

    function setK(text) {
        const parts = text.split(",");
        const preset = presets.findIndex(p => p.k === text);
        if (preset >= 0) {
            kChoice.currentIndex = preset;
        } else {
            kChoice.currentIndex = presets.length;
            for (let i = 0; i < 3; ++i)
                (kFields.itemAt(i) as EaElements.TextField).text = parts[i];
        }
        find();
    }
    function loadPeaks() {
        kRows = [];
        kRefusal = "";
        peaks = [];
        peakTicks = [];
        if (dataChoice.currentIndex < 0 || dataChoice.currentIndex >= dataChoices.length)
            return;
        const choice = dataChoices[dataChoice.currentIndex];
        if (!choice.eligible) {
            kRefusal = choice.reason;
            return;
        }
        peaks = project.magneticPeaks(structureIndex, choice.index);
        if (peaks.length === 0)
            kRefusal = project.lastError !== "" ? project.lastError : qsTr("the fit leaves no peak unexplained");
        peakTicks = peaks.map(() => true);
    }
    function searchK() {
        kRows = [];
        kRefusal = "";
        const ticked = [];
        for (let i = 0; i < peakTicks.length; ++i)
            if (peakTicks[i])
                ticked.push(i);
        searching = true;
        project.findPropagationVectors(structureIndex, dataChoices[dataChoice.currentIndex].index, ticked);
    }
    function chooseRow(row) {
        if (!project.propagationSearchCurrent(dataChoices[dataChoice.currentIndex].index)) {
            kRefusal = qsTr("the data or the peaks changed; search again");
            return;
        }
        setK(row.k);
    }

    function tickedSites() {
        const out = [];
        for (let i = 0; i < siteRepeater.count; ++i) {
            const box = siteRepeater.itemAt(i) as EaElements.CheckBox;
            if (box && box.checked)
                out.push(sites[i].id);
        }
        return out;
    }
    function find() {
        found = null;
        refusal = "";
        graphView.selected = [];
        const ticked = tickedSites();
        if (ticked.length === 0) {
            refusal = qsTr("tick at least one magnetic site");
            return;
        }
        busy = true;
        project.findMagneticGroups(structureIndex, k, ticked, zeroMoment.checked);
    }

    Component.onCompleted: {
        presets = project.magneticPresets(structureIndex);
        dataChoices = project.magneticDataChoices(structureIndex);
        sites = project.magneticSites(structureIndex);
        Qt.callLater(find);
    }

    Connections {
        target: popup.project
        function onMagneticGroupsFound(graph) {
            popup.busy = false;
            popup.found = graph;
        }
        function onMagneticGroupsRefused(message) {
            popup.busy = false;
            popup.refusal = message;
        }
        function onPropagationVectorsFound(rows) {
            popup.searching = false;
            popup.kRows = rows;
            if (rows.length === 0)
                popup.kRefusal = qsTr("No k explains the ticked peaks (not found by this search).");
        }
        function onPropagationVectorsRefused(message) {
            popup.searching = false;
            popup.kRefusal = message;
        }
    }

    // Bounded to the dialog's own area, so the graph takes what the other rows leave and the
    // footer stays inside the dialog.
    ColumnLayout {
        id: content
        width: popup.availableWidth
        height: popup.availableHeight
        spacing: EaStyle.Sizes.fontPixelSize * 0.6

        // 1. The propagation vector.
        Row {
            spacing: EaStyle.Sizes.fontPixelSize * 0.6
            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("Propagation vector k")
            }
            EaElements.ComboBox {
                id: kChoice
                objectName: "magnetic.k"
                width: EaStyle.Sizes.fontPixelSize * 16
                model: popup.presets.map(p => p.label === "" ? `(${p.k})` : `${p.label}  (${p.k})`).concat([qsTr("Other…")])
                onActivated: if (currentIndex < popup.presets.length)
                    popup.find()
            }
            Repeater {
                id: kFields
                model: 3
                delegate: EaElements.TextField {
                    required property int index
                    visible: kChoice.currentIndex === popup.presets.length
                    width: EaStyle.Sizes.fontPixelSize * 5
                    placeholderText: ["k₁", "k₂", "k₃"][index]
                    text: "0"
                    onEditingFinished: popup.find()
                }
            }
            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                text: popup.found ? qsTr("Magnetic cell: %1").arg(popup.found.cell.replace(";0,0,0", "").split(",").join(", ")) : ""
            }
        }
        // Find k from data.
        Row {
            spacing: EaStyle.Sizes.fontPixelSize * 0.6
            visible: popup.dataChoices.length > 0
            EaElements.Button {
                id: findK
                objectName: "magnetic.findK"
                text: popup.findKShown ? qsTr("Hide Find k") : qsTr("Find k from data")
                onClicked: {
                    popup.findKShown = !popup.findKShown;
                    if (popup.findKShown)
                        popup.loadPeaks();
                }
            }
            EaElements.Label {
                anchors.verticalCenter: parent.verticalCenter
                visible: popup.findKShown
                text: qsTr("Data")
            }
            EaElements.ComboBox {
                id: dataChoice
                objectName: "magnetic.data"
                visible: popup.findKShown
                width: EaStyle.Sizes.fontPixelSize * 14
                model: popup.dataChoices.map(c => c.eligible ? c.name : `${c.name} (${c.reason})`)
                currentIndex: {
                    const eligible = popup.dataChoices.filter(c => c.eligible);
                    return eligible.length === 1 ? popup.dataChoices.indexOf(eligible[0]) : 0;
                }
                onActivated: popup.loadPeaks()
            }
            EaElements.Button {
                objectName: "magnetic.searchK"
                visible: popup.findKShown
                enabled: popup.peaks.length > 0 && !popup.searching
                text: popup.searching ? qsTr("Searching…") : qsTr("Search")
                onClicked: popup.searchK()
            }
        }
        Flow {
            Layout.fillWidth: true
            visible: popup.findKShown && popup.peaks.length > 0
            spacing: EaStyle.Sizes.fontPixelSize * 0.4
            EaElements.Label {
                text: qsTr("Unexplained peaks")
            }
            Repeater {
                model: popup.peaks
                delegate: EaElements.CheckBox {
                    required property var modelData
                    required property int index
                    objectName: `magnetic.peak.${index}`
                    text: `${modelData.x.toFixed(3)} (d ${modelData.d.toFixed(4)} Å)`
                    checked: popup.peakTicks[index] ?? true
                    onToggled: {
                        const next = popup.peakTicks.slice();
                        next[index] = checked;
                        popup.peakTicks = next;
                        popup.kRows = [];
                    }
                }
            }
        }
        EaElements.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: popup.findKShown && text !== ""
            color: EaStyle.Colors.red
            text: popup.kRefusal
        }
        ListView {
            id: kList
            objectName: "magnetic.kRows"
            visible: popup.findKShown && popup.kRows.length > 0
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, EaStyle.Sizes.fontPixelSize * 9)
            clip: true
            model: popup.kRows
            delegate: EaElements.Label {
                id: kRow
                required property var modelData
                required property int index
                readonly property bool choosable: modelData.verdict === "buildable"
                width: kList.width
                enabled: choosable
                text: {
                    const r = modelData;
                    const name = r.label === "" ? `(${r.k})` : `${r.label} (${r.k})`;
                    const state = r.verdict === "buildable" ? "" : r.verdict === "over the limit" ? qsTr(" · needs %1 parent cells: not built").arg(r.parentCells) : r.verdict === "underdetermined" ? qsTr(" · underdetermined in %1 directions").arg(r.undetermined) : qsTr(" · incommensurate at this resolution");
                    return `${name} · ${qsTr("%1 peaks explained").arg(r.explained)} · ${qsTr("worst misfit %1").arg(r.misfit.toFixed(2))}${r.equallyGood ? qsTr(" · equally good") : ""}${state}`;
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: kRow.choosable
                    onClicked: popup.chooseRow(kRow.modelData)
                }
            }
        }

        // 2. The magnetic sites; 3. starting moments; the zero-moment switch.
        Flow {
            Layout.fillWidth: true
            spacing: EaStyle.Sizes.fontPixelSize * 0.6
            EaElements.Label {
                text: qsTr("Magnetic sites")
            }
            Repeater {
                id: siteRepeater
                model: popup.sites
                delegate: EaElements.CheckBox {
                    required property var modelData
                    required property int index
                    objectName: `magnetic.site.${index}`
                    text: `${modelData.id} (${modelData.type})`
                    checked: modelData.magnetic
                    onToggled: popup.find()
                }
            }
        }
        Row {
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.CheckBox {
                id: startMoments
                objectName: "magnetic.startMoments"
                text: qsTr("Add non-zero starting moments")
                checked: true
            }
            EaElements.CheckBox {
                id: allSubgroups
                objectName: "magnetic.allSubgroups"
                text: qsTr("Show all subgroups")
                checked: false
            }
            EaElements.CheckBox {
                id: zeroMoment
                objectName: "magnetic.zeroMoment"
                text: qsTr("Show groups without moments")
                checked: false
                onToggled: popup.find()
            }
        }

        EaElements.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            visible: text !== ""
            color: EaStyle.Colors.red
            text: popup.refusal
        }
        EaElements.Label {
            visible: popup.busy
            text: qsTr("Finding the magnetic groups…")
        }

        // 4. The graph.
        MagneticSubgroupGraph {
            id: graphView
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: EaStyle.Sizes.fontPixelSize * 8
            showAll: allSubgroups.checked
            nodes: popup.found ? popup.found.nodes : []
            cell: popup.found ? popup.found.cell : ""
            parentName: popup.structure ? popup.structure.spaceGroup.nameHM : ""
        }

        // 5. Select all, Clear, Add.
        Row {
            id: buttons
            spacing: EaStyle.Sizes.fontPixelSize * 0.6
            EaElements.Button {
                text: qsTr("Select all")
                enabled: popup.found !== null
                onClicked: graphView.selectAll()
            }
            EaElements.Button {
                text: qsTr("Clear")
                enabled: graphView.selected.length > 0
                onClicked: graphView.selected = []
            }
            EaElements.Button {
                objectName: "magnetic.add"
                text: graphView.selected.length > 1 ? qsTr("Add %1 structures").arg(graphView.selected.length) : qsTr("Add")
                enabled: graphView.selected.length > 0 && !popup.busy
                onClicked: {
                    if (popup.project.addMagneticCandidates(popup.structureIndex, graphView.selected, startMoments.checked))
                        popup.close();
                    else
                        popup.refusal = popup.project.lastError;
                }
            }
        }
    }
}
