// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

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
    }

    Column {
        id: content
        width: popup.availableWidth
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
        // 2. The magnetic sites; 3. starting moments; the zero-moment switch.
        Flow {
            width: parent.width
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
                id: zeroMoment
                objectName: "magnetic.zeroMoment"
                text: qsTr("Show groups without moments")
                checked: false
                onToggled: popup.find()
            }
        }

        EaElements.Label {
            width: parent.width
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
            width: parent.width
            height: popup.availableHeight - y - buttons.height - content.spacing
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
