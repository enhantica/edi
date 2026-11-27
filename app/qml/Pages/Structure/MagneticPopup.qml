// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

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
    // After Add the first new structure becomes the Structure page's current one, from either origin; the page shown
    // stays as it is (owner, 2026-11-27).
    property bool selectAfterAdd: true
    // Opened from Find k: the snapshot the chosen k was found for; Add refuses once it is no longer current
    // (review 16, F4). Empty from the Structure page.
    property real kSnapshotId: 0
    // The ranked row of that search the analysis was opened for, and the k it set; a k typed or picked here instead
    // is a choice of the user's own, which leaves the Find k search (review 18, F4).
    property int kRow: -1
    property string openedK: ""
    // The graph search this popup made; it settles on that request's answer only, and Add names the graph shown.
    property int graphRequest: 0
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
    // As tall as its content, up to the height that keeps the navigation bar and the status bar clear, centred as the
    // app's other dialogs are (owner, 2026-11-27, conductor seq 48).
    readonly property real maximumHeight: parent ? parent.height - 2 * (EaStyle.Sizes.appBarHeight + EaStyle.Sizes.fontPixelSize) : 800
    width: parent ? Math.round(parent.width * 0.9) : 1000
    height: Math.round(Math.min(maximumHeight, implicitHeight))
    anchors.centerIn: parent
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
    // The shown graph and selection belong to the k they were found for: switching to Other, or typing a k not yet
    // committed, takes them away at once and ignores any answer still on its way (review 19, F4). A k other than the
    // Find k row's leaves that search.
    // One rule for every input (review 20, F4): the request in flight is retired and the shown graph and selection are
    // cleared before anything else happens, so no answer can arrive for inputs the controls no longer show; while a
    // search runs, the inputs themselves are disabled.
    function retireRequest() {
        found = null;
        selected = [];
        hovered = -1;
        busy = false;
        graphRequest = -1;
    }
    function invalidateGraph() {
        retireRequest();
        refusal = qsTr("Enter k and press Enter to find its magnetic groups.");
        if (kSnapshotId !== 0 && k !== openedK) {
            kSnapshotId = 0;
            kRow = -1;
        }
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
        retireRequest();
        refusal = "";
        const ticked = tickedSites();
        if (ticked.length === 0) {
            refusal = qsTr("tick at least one magnetic site");
            return;
        }
        busy = true;
        if (kSnapshotId !== 0 && k !== openedK) {
            kSnapshotId = 0;
            kRow = -1;
        }
        graphRequest = project.findMagneticGroups(structureIndex, k, ticked, zeroMoment.checked, kSnapshotId, kRow);
    }

    Component.onCompleted: {
        presets = project.magneticPresets(structureIndex);
        sites = project.magneticSites(structureIndex);
        Qt.callLater(() => {
            if (popup.initialK !== "")
                popup.setK(popup.initialK);
            popup.openedK = popup.k;
            popup.find();
        });
    }

    Connections {
        target: popup.project
        function onMagneticGroupsFound(graph) {
            if (graph.graphId !== popup.graphRequest)
                return;
            popup.busy = false;
            popup.found = graph;
        }
        function onMagneticGroupsRefused(message, request) {
            if (request !== popup.graphRequest)
                return;
            popup.busy = false;
            popup.refusal = message;
        }
    }

    // The dialog's own area: the choices on top, the groups in the middle (the one part that scrolls), the details
    // strip and the footer at the bottom.
    ColumnLayout {
        id: content
        anchors.fill: parent
        spacing: AppSizes.groupContentSpacing

        // The propagation vector.
        RowLayout {
            spacing: EaStyle.Sizes.fontPixelSize * 0.6
            EaElements.Label {
                text: qsTr("Propagation vector k")
            }
            EaElements.ComboBox {
                id: kChoice
                objectName: "magnetic.k"
                enabled: !popup.busy
                Layout.preferredWidth: EaStyle.Sizes.fontPixelSize * 16
                model: popup.presets.map(p => p.label === "" ? `(${p.k})` : `${p.label}  (${p.k})`).concat([qsTr("Other…")])
                onActivated: {
                    if (currentIndex < popup.presets.length)
                        popup.find();
                    else
                        popup.invalidateGraph();
                }
            }
            Repeater {
                id: kFields
                model: 3
                delegate: EaElements.TextField {
                    required property int index
                    enabled: !popup.busy
                    visible: kChoice.currentIndex === popup.presets.length
                    Layout.preferredWidth: EaStyle.Sizes.fontPixelSize * 5
                    placeholderText: ["k₁", "k₂", "k₃"][index]
                    text: "0"
                    onTextEdited: popup.invalidateGraph()
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
                    enabled: !popup.busy
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
                enabled: !popup.busy
                leftPadding: 0  // on the labels' edge, as the rows above
                text: qsTr("Maximal only")
                checked: true
                onToggled: popup.selected = popup.selected.filter(i => popup.selectable(i))
            }
            EaElements.CheckBox {
                id: zeroMoment
                objectName: "magnetic.zeroMoment"
                enabled: !popup.busy
                text: qsTr("Show groups without moments")
                checked: false
                onToggled: popup.find()
            }
            EaElements.CheckBox {
                id: startMoments
                objectName: "magnetic.startMoments"
                enabled: !popup.busy
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
            // Its content's own height, so the dialog fits what it shows.
            Layout.preferredHeight: listMode.checked ? listView.contentHeight + EaStyle.Sizes.tableRowHeight : graphView.contentHeight
            currentIndex: listMode.checked ? 1 : 0

            MagneticSubgroupGraph {
                id: graphView
                nodes: popup.nodes
                selected: popup.selected
                maximalOnly: maximalOnly.checked
                parentCell: popup.found ? popup.found.cell : ""
                onShownNodeChanged: popup.hovered = shownNode
                onToggled: index => popup.toggle(index)
            }

            // The list: one row per group in the app's table (DataTable, as Excluded regions and the parameter table),
            // a check box column to select, the group's values, then each site's moments in a column of its own
            // (conductor seq 33, 50).
            DataTable {
                id: listView
                objectName: "magnetic.list"
                clip: true
                // Each site's name, from the first group's moments (`Co1 0,0,0 · Co2 Mx,0,Mz`).
                readonly property var sites: popup.nodes.length > 0 ? String(popup.nodes[0].moments).split(" · ").map(m => m.split(" ")[0]) : []
                function columns(n) {
                    // A site split in a subgroup (`Co1_1`, `Co1_2`) goes under its parent site's column, its distinct
                    // forms joined.
                    return sites.map(site => {
                        const forms = [];
                        for (const m of String(n.moments).split(" · ")) {
                            const id = m.slice(0, m.indexOf(" "));
                            const form = m.slice(m.indexOf(" ") + 1);
                            if ((id === site || id.startsWith(site + "_")) && forms.indexOf(form) < 0)
                                forms.push(form);
                        }
                        return forms.join(" / ");
                    });
                }
                sourceModel: {
                    const rows = [];
                    for (let i = 0; i < popup.nodes.length; ++i)
                        if (!maximalOnly.checked || Math.max(1, popup.nodes[i].row) === 1)
                            rows.push(i);
                    rows.sort((a, b) => Math.max(1, popup.nodes[a].row) - Math.max(1, popup.nodes[b].row) || a - b);
                    return rows;
                }
                defaultInfoText: qsTr("No magnetic group")
                columnKinds: ["index", "control", "name", "short", "short", "short", "short"].concat(sites.map(() => "short"))
                header: EaComponents.ListViewHeader {
                    EaComponents.ListViewLabel {}
                    EaComponents.ListViewLabel {}
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("Group")
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("BNS")
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("Type")
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: qsTr("Level")
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: qsTr("Net moment")
                    }
                    Repeater {
                        model: listView.sites
                        delegate: EaComponents.ListViewLabel {
                            required property var modelData
                            horizontalAlignment: Text.AlignLeft
                            text: modelData
                        }
                    }
                }
                delegate: TableRow {
                    id: listRow
                    required property int modelData
                    readonly property var data_: popup.nodes[modelData]
                    objectName: `magnetic.listRow.${listRow.index}`
                    HoverHandler {
                        onHoveredChanged: if (hovered)
                            popup.hovered = listRow.modelData
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        marksCurrentRow: true
                        text: listRow.index + 1
                    }
                    Item {
                        property int horizontalAlignment: Text.AlignHCenter
                        height: parent.height
                        EaComponents.ListViewCheckBox {
                            anchors.fill: parent
                            horizontalAlignment: Text.AlignHCenter
                            objectName: `magnetic.row.${listRow.modelData}`
                            enabled: popup.selectable(listRow.modelData)
                            checked: popup.selected.indexOf(listRow.modelData) >= 0
                            onToggled: popup.toggle(listRow.modelData)
                        }
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        elide: Text.ElideRight
                        text: listRow.data_.bns === "" ? qsTr("not identified") : listRow.data_.name
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: listRow.data_.bns === "" ? "" : `${listRow.data_.bns}${listRow.data_.embedding > 1 ? " #" + listRow.data_.embedding : ""}`
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: ["", "I", "II", "III", "IV"][listRow.data_.type] ?? ""
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignLeft
                        text: Math.max(1, listRow.data_.row) === 1 ? qsTr("maximal") : qsTr("level %1").arg(listRow.data_.row)
                    }
                    EaComponents.ListViewLabel {
                        horizontalAlignment: Text.AlignHCenter
                        text: listRow.data_.netMoment ? qsTr("yes") : ""
                    }
                    Repeater {
                        model: listView.columns(listRow.data_)
                        delegate: EaComponents.ListViewLabel {
                            required property var modelData
                            horizontalAlignment: Text.AlignLeft
                            elide: Text.ElideRight
                            text: modelData
                        }
                    }
                }
            }
        }

    }

    // Esc unpins a pinned card before it would close the dialog.
    Shortcut {
        sequence: StandardKey.Cancel
        enabled: graphView.pinned >= 0
        onActivated: graphView.pinned = -1
    }

    // The fixed footer, as the app's other dialogs place their actions: the selection's own actions at the left, then
    // Cancel and the primary Add at the right.
    footer: Item {
        implicitHeight: actions.implicitHeight + 2 * EaStyle.Sizes.fontPixelSize
        Row {
            anchors.left: parent.left
            anchors.leftMargin: popup.leftPadding
            anchors.verticalCenter: parent.verticalCenter
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.Button {
                objectName: "magnetic.selectAll"
                fontIcon: "check-double"
                text: qsTr("Select all")
                enabled: popup.found !== null && !popup.busy
                onClicked: popup.selectAll()
            }
            EaElements.Button {
                objectName: "magnetic.clear"
                fontIcon: "eraser"
                text: qsTr("Clear")
                enabled: popup.selected.length > 0
                onClicked: popup.selected = []
            }
        }
        Row {
            id: actions
            anchors.right: parent.right
            anchors.rightMargin: popup.rightPadding
            anchors.verticalCenter: parent.verticalCenter
            spacing: EaStyle.Sizes.fontPixelSize
            EaElements.Button {
                objectName: "magnetic.cancel"
                fontIcon: "times"
                text: qsTr("Cancel")
                onClicked: popup.close()
            }
            EaElements.Button {
                objectName: "magnetic.add"
                fontIcon: "plus-circle"
                text: popup.selected.length > 1 ? qsTr("Add %1 structures").arg(popup.selected.length) : qsTr("Add")
                enabled: popup.selected.length > 0 && !popup.busy
                onClicked: {
                    const count = popup.selected.length;
                    if (popup.found !== null && popup.project.addMagneticCandidates(popup.found.graphId, popup.selected, startMoments.checked, popup.selectAfterAdd)) {
                        popup.added(count);
                        popup.close();
                    } else {
                        popup.refusal = popup.project.lastError;
                    }
                }
            }
        }
    }
}
