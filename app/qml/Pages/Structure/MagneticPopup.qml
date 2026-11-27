// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// Crystal → Magnetic (edi ADR-0078 "The magnetic popup", crysta ADR-0137): pick a propagation vector and the magnetic
// sites, then the magnetic groups to add; each picked group becomes a new structure linked where the parent is. The
// layout follows the owner's decision of 2026-11-27: at most about 90 % of the window, a fixed footer, Maximal only by
// default, a header per level, a Graph / List switch and a details strip. Cancel changes nothing.
AppDialog {
    id: popup
    objectName: "structures.magneticPopup"

    property ProjectViewModel project: null
    property int structureIndex: -1
    property StructureViewModel structure: null
    // A k to start from (the k-vector popup's choice), else the first preset.
    property string initialK: ""

    property var presets: []
    property var sites: []
    property var found: null
    property var selected: []
    property int hovered: -1
    property string refusal: ""
    property bool busy: false

    readonly property var nodes: found ? found.nodes : []

    title: qsTr("Magnetic structures from %1").arg(structure ? structure.name : "")
    width: parent ? Math.round(parent.width * 0.9) : 1000
    height: parent ? Math.round(parent.height * 0.9) : 800
    onClosed: destroy()

    readonly property string k: kChoice.currentIndex >= 0 && kChoice.currentIndex < presets.length ? presets[kChoice.currentIndex].k : [0, 1, 2].map(i => kFields.itemAt(i) ? (kFields.itemAt(i) as EaElements.TextField).text : "0").join(",")

    function selectable(i) {
        const n = nodes[i];
        return n !== undefined && n.bns !== "" && n.momentAllowed && (!maximalOnly.checked || Math.max(1, n.row) === 1);
    }
    function toggle(i) {
        if (!selectable(i))
            return;
        const next = selected.slice();
        const at = next.indexOf(i);
        if (at >= 0)
            next.splice(at, 1);
        else
            next.push(i);
        next.sort((a, b) => a - b);
        selected = next;
    }
    function setMany(indices, on) {
        const next = selected.filter(i => indices.indexOf(i) < 0);
        if (on)
            for (const i of indices)
                if (selectable(i))
                    next.push(i);
        next.sort((a, b) => a - b);
        selected = next;
    }
    function selectAll() {
        const all = [];
        for (let i = 0; i < nodes.length; ++i)
            all.push(i);
        setMany(all, true);
    }
    function setK(text) {
        const preset = presets.findIndex(p => p.k === text);
        if (preset >= 0) {
            kChoice.currentIndex = preset;
            return;
        }
        kChoice.currentIndex = presets.length;
        const parts = text.split(",");
        for (let i = 0; i < 3; ++i)
            (kFields.itemAt(i) as EaElements.TextField).text = parts[i];
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
        selected = [];
        hovered = -1;
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
        sites = project.magneticSites(structureIndex);
        Qt.callLater(() => {
            if (popup.initialK !== "")
                popup.setK(popup.initialK);
            popup.find();
        });
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
    }

    // The dialog's own area: the choices on top, the groups in the middle (the one part that scrolls), the details
    // strip and the footer at the bottom.
    ColumnLayout {
        id: content
        width: popup.availableWidth
        height: popup.availableHeight
        spacing: EaStyle.Sizes.fontPixelSize * 0.5

        // The propagation vector.
        RowLayout {
            spacing: EaStyle.Sizes.fontPixelSize * 0.6
            EaElements.Label {
                text: qsTr("Propagation vector k")
            }
            EaElements.ComboBox {
                id: kChoice
                objectName: "magnetic.k"
                Layout.preferredWidth: EaStyle.Sizes.fontPixelSize * 16
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
                    Layout.preferredWidth: EaStyle.Sizes.fontPixelSize * 5
                    placeholderText: ["k₁", "k₂", "k₃"][index]
                    text: "0"
                    onEditingFinished: popup.find()
                }
            }
            EaElements.Label {
                Layout.fillWidth: true
                elide: Text.ElideRight
                text: popup.found ? qsTr("Magnetic cell: %1").arg(popup.found.cell.replace(";0,0,0", "").split(",").join(", ")) : ""
            }
        }

        // The magnetic sites.
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

        // What is shown and how.
        Flow {
            Layout.fillWidth: true
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.CheckBox {
                id: maximalOnly
                objectName: "magnetic.maximalOnly"
                text: qsTr("Maximal only")
                checked: true
                onToggled: popup.selected = popup.selected.filter(i => popup.selectable(i))
            }
            EaElements.CheckBox {
                id: zeroMoment
                objectName: "magnetic.zeroMoment"
                text: qsTr("Show groups without moments")
                checked: false
                onToggled: popup.find()
            }
            EaElements.CheckBox {
                id: startMoments
                objectName: "magnetic.startMoments"
                text: qsTr("Add non-zero starting moments")
                checked: true
            }
            EaElements.RadioButton {
                id: graphMode
                objectName: "magnetic.graphView"
                text: qsTr("Graph")
                checked: true
            }
            EaElements.RadioButton {
                id: listMode
                objectName: "magnetic.listView"
                text: qsTr("List")
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

        // The groups, as a graph or a list; the only part that scrolls.
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: EaStyle.Sizes.fontPixelSize * 8
            currentIndex: listMode.checked ? 1 : 0

            MagneticSubgroupGraph {
                id: graphView
                nodes: popup.nodes
                selected: popup.selected
                maximalOnly: maximalOnly.checked
                onHoveredChanged: popup.hovered = hovered
                onToggled: index => popup.toggle(index)
                onLevelToggled: (level, on) => popup.setMany(graphView.levels[level], on)
            }

            ListView {
                id: listView
                objectName: "magnetic.list"
                clip: true
                ScrollBar.vertical: EaElements.ScrollBar {}
                model: {
                    const rows = [];
                    for (let i = 0; i < popup.nodes.length; ++i)
                        if (!maximalOnly.checked || Math.max(1, popup.nodes[i].row) === 1)
                            rows.push(i);
                    rows.sort((a, b) => Math.max(1, popup.nodes[a].row) - Math.max(1, popup.nodes[b].row) || a - b);
                    return rows;
                }
                delegate: Item {
                    id: listRow
                    required property int modelData
                    readonly property var data_: popup.nodes[modelData]
                    width: listView.width
                    height: EaStyle.Sizes.fontPixelSize * 2.2
                    Row {
                        x: (Math.max(1, listRow.data_.row) - 1) * EaStyle.Sizes.fontPixelSize * 1.5
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: EaStyle.Sizes.fontPixelSize * 0.8
                        EaElements.CheckBox {
                            objectName: `magnetic.row.${listRow.modelData}`
                            enabled: popup.selectable(listRow.modelData)
                            checked: popup.selected.indexOf(listRow.modelData) >= 0
                            onToggled: popup.toggle(listRow.modelData)
                            text: listRow.data_.bns === "" ? qsTr("not identified") : `${listRow.data_.name}  ${listRow.data_.bns}${listRow.data_.embedding > 1 ? " #" + listRow.data_.embedding : ""}`
                        }
                        EaElements.Label {
                            anchors.verticalCenter: parent.verticalCenter
                            text: `${qsTr("type")} ${["", "I", "II", "III", "IV"][listRow.data_.type] ?? ""} · ${Math.max(1, listRow.data_.row) === 1 ? qsTr("maximal") : qsTr("level %1").arg(listRow.data_.row)}${listRow.data_.netMoment ? " · FM" : ""} · ${listRow.data_.moments}`
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.NoButton
                        hoverEnabled: true
                        onEntered: popup.hovered = listRow.modelData
                    }
                }
            }
        }

        // The details strip: the group under the pointer.
        EaElements.Label {
            objectName: "magnetic.details"
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            maximumLineCount: 3
            elide: Text.ElideRight
            text: {
                const n = popup.nodes[popup.hovered];
                if (n === undefined)
                    return qsTr("Point at a group for its moments and transforms.");
                return `${n.name} ${n.bns} · ${qsTr("from the parent")} ${popup.found.cell} · ${qsTr("to the BNS standard")} ${n.transform} · ${qsTr("%n domain(s)", "", n.domains)}\n${n.moments}`;
            }
        }

        // The fixed footer.
        RowLayout {
            spacing: EaStyle.Sizes.fontPixelSize * 0.6
            EaElements.Button {
                objectName: "magnetic.selectAll"
                text: qsTr("Select all")
                enabled: popup.found !== null
                onClicked: popup.selectAll()
            }
            EaElements.Button {
                objectName: "magnetic.clear"
                text: qsTr("Clear")
                enabled: popup.selected.length > 0
                onClicked: popup.selected = []
            }
            Item {
                Layout.fillWidth: true
            }
            EaElements.Button {
                objectName: "magnetic.add"
                text: popup.selected.length > 1 ? qsTr("Add %1 structures").arg(popup.selected.length) : qsTr("Add")
                enabled: popup.selected.length > 0 && !popup.busy
                onClicked: {
                    if (popup.project.addMagneticCandidates(popup.structureIndex, popup.selected, startMoments.checked))
                        popup.close();
                    else
                        popup.refusal = popup.project.lastError;
                }
            }
            EaElements.Button {
                objectName: "magnetic.cancel"
                text: qsTr("Cancel")
                onClicked: popup.close()
            }
        }
    }
}
