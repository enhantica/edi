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
    // Opened from the Structure page, the first new structure becomes the current one; from Experiment → Pattern the
    // page stays as it is (the popup never moves the user, owner 2026-11-27).
    property bool selectAfterAdd: true
    signal added(int count)

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
        anchors.fill: parent
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

        // What is shown and how, on one line, centred vertically.
        RowLayout {
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

            // The list: one row per group, its values in columns as the k table has them, each site's moments in
            // its own column (conductor seq 33).
            ColumnLayout {
                id: listPane
                spacing: 0
                // Each site's name, from the first group's moments (`Co1 0,0,0 · Co2 Mx,0,Mz`).
                readonly property var sites: popup.nodes.length > 0 ? String(popup.nodes[0].moments).split(" · ").map(m => m.split(" ")[0]) : []
                readonly property var widths: [0.2, 0.11, 0.07, 0.1, 0.05]
                function siteWidth() {
                    return sites.length > 0 ? 0.47 / sites.length : 0;
                }
                function columns(n) {
                    // A site split in a subgroup (`Co1_1`, `Co1_2`) goes under its parent site's column, its
                    // distinct forms joined.
                    const moments = sites.map(site => {
                        const forms = [];
                        for (const m of String(n.moments).split(" · ")) {
                            const id = m.slice(0, m.indexOf(" "));
                            const form = m.slice(m.indexOf(" ") + 1);
                            if ((id === site || id.startsWith(site + "_")) && forms.indexOf(form) < 0)
                                forms.push(form);
                        }
                        return forms.join(" / ");
                    });
                    return [n.bns === "" ? "" : `${n.bns}${n.embedding > 1 ? " #" + n.embedding : ""}`, ["", "I", "II", "III", "IV"][n.type] ?? "", Math.max(1, n.row) === 1 ? qsTr("maximal") : qsTr("level %1").arg(n.row), n.netMoment ? "FM" : ""].concat(moments);
                }
                Row {
                    Layout.fillWidth: true
                    Repeater {
                        model: [qsTr("Group"), qsTr("BNS"), qsTr("Type"), qsTr("Level"), ""].concat(listPane.sites)
                        delegate: EaElements.Label {
                            required property var modelData
                            required property int index
                            width: listView.width * (index < listPane.widths.length ? listPane.widths[index] : listPane.siteWidth())
                            leftPadding: EaStyle.Sizes.fontPixelSize * 0.5
                            elide: Text.ElideRight
                            color: EaStyle.Colors.themeForegroundMinor
                            text: modelData
                        }
                    }
                }
                ListView {
                    id: listView
                    objectName: "magnetic.list"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
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
                    delegate: Rectangle {
                        id: listRow
                        required property int modelData
                        readonly property var data_: popup.nodes[modelData]
                        readonly property bool chosen: popup.selected.indexOf(modelData) >= 0
                        width: listView.width
                        height: EaStyle.Sizes.fontPixelSize * 2.2
                        color: chosen ? EaStyle.Colors.contentBackground : popup.hovered === modelData ? EaStyle.Colors.themeRowHovered : "transparent"
                        Row {
                            anchors.verticalCenter: parent.verticalCenter
                            EaElements.CheckBox {
                                objectName: `magnetic.row.${listRow.modelData}`
                                width: listView.width * listPane.widths[0]
                                enabled: popup.selectable(listRow.modelData)
                                checked: listRow.chosen
                                onToggled: popup.toggle(listRow.modelData)
                                text: listRow.data_.bns === "" ? qsTr("not identified") : listRow.data_.name
                            }
                            Repeater {
                                model: listPane.columns(listRow.data_)
                                delegate: EaElements.Label {
                                    required property var modelData
                                    required property int index
                                    // A Repeater's label has no parent while it is created, so it centres by its
                                    // own height, not an anchor.
                                    height: listRow.height
                                    verticalAlignment: Text.AlignVCenter
                                    width: listView.width * (index + 1 < listPane.widths.length ? listPane.widths[index + 1] : listPane.siteWidth())
                                    leftPadding: EaStyle.Sizes.fontPixelSize * 0.5
                                    elide: Text.ElideRight
                                    text: modelData
                                }
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
                return `${n.name} ${n.bns} · ${qsTr("from the parent")} ${popup.found.cell} · ${qsTr("to the BNS standard")} ${n.transform} · ${(n.domains === 1 ? qsTr("1 domain") : qsTr("%1 domains").arg(n.domains))}\n${n.moments}`;
            }
        }
    }

    // The fixed footer, as the app's other dialogs have it.
    footer: EaElements.DialogButtonBox {
        EaElements.Button {
            objectName: "magnetic.selectAll"
            fontIcon: "check-double"
            text: qsTr("Select all")
            enabled: popup.found !== null
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            onClicked: popup.selectAll()
        }
        EaElements.Button {
            objectName: "magnetic.clear"
            fontIcon: "eraser"
            text: qsTr("Clear")
            enabled: popup.selected.length > 0
            DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
            onClicked: popup.selected = []
        }
        EaElements.Button {
            objectName: "magnetic.add"
            fontIcon: "plus-circle"
            text: popup.selected.length > 1 ? qsTr("Add %1 structures").arg(popup.selected.length) : qsTr("Add")
            enabled: popup.selected.length > 0 && !popup.busy
            DialogButtonBox.buttonRole: DialogButtonBox.ApplyRole
            onClicked: {
                const count = popup.selected.length;
                if (popup.project.addMagneticCandidates(popup.structureIndex, popup.selected, startMoments.checked, popup.selectAfterAdd)) {
                    popup.added(count);
                    popup.close();
                } else {
                    popup.refusal = popup.project.lastError;
                }
            }
        }
        EaElements.Button {
            objectName: "magnetic.cancel"
            text: qsTr("Cancel")
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
        }
    }
}
