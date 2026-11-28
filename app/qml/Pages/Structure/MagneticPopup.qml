// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// Crystal → Magnetic (ADR-0078): pick a propagation vector and the magnetic sites, then the magnetic groups to add;
// each picked group becomes a new structure linked where the parent is. The layout follows the owner's decision of
// 2026-11-27: at most about 90 % of the window, a fixed footer, Maximal only by default, a header per level, a Graph /
// List switch and a details strip. Cancel changes nothing.
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
    // Opened from Find k: the snapshot the chosen k was found for; Add refuses once it is no longer
    // current. Empty from the Structure page.
    property real kSnapshotId: 0
    // The ranked row of that search the analysis was opened for, and the k it set; a k typed or picked here instead
    // is a choice of the user's own, which leaves the Find k search.
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
    // The toolbar's choices (owner, 2026-11-28, header design B): the magnetic sites by id, the levels, the net moment
    // (0 any, 1 ferromagnetic, 2 zero), the starting moments and the view.
    property var chosenSites: []
    property bool maximalOnly: true
    property int netMoment: 0
    property bool startMoments: true
    property bool listMode: false

    readonly property var nodes: found ? found.nodes : []

    title: qsTr("Magnetic structures from %1").arg(structure ? structure.name : "")
    // As tall as its content, up to the height that keeps the navigation bar and the status bar clear, centred as the
    // app's other dialogs are.
    readonly property real maximumHeight: parent ? parent.height - 2 * (EaStyle.Sizes.appBarHeight + EaStyle.Sizes.fontPixelSize) : 800
    width: parent ? Math.round(parent.width * 0.9) : 1000
    height: Math.round(Math.min(maximumHeight, implicitHeight))
    // Centred on whole pixels by AppDialog, as the app's other dialogs are, so its text is sharp (owner, Retina).
    onClosed: destroy()

    // The chosen k's place in the list (a preset, or presets.length for Other): the one owner of the choice, which the
    // box shows, the fields follow and every search reads.
    property int kIndex: 0
    readonly property string k: kIndex >= 0 && kIndex < presets.length ? presets[kIndex].k : [0, 1, 2].map(i => kFields.itemAt(i) ? (kFields.itemAt(i) as EaElements.TextField).text : "0").join(",")

    function selectable(i) {
        const n = nodes[i];
        return n !== undefined && n.bns !== "" && n.momentAllowed && (!maximalOnly || Math.max(1, n.row) === 1) && netShown(n);
    }
    // The net-moment filter: ferromagnetic groups (FM on the cards), or the others.
    function netShown(n) {
        return netMoment === 0 || (netMoment === 1) === (n.netMoment === true);
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
            kIndex = preset;
            return;
        }
        kIndex = presets.length;
        const parts = text.split(",");
        for (let i = 0; i < 3; ++i)
            (kFields.itemAt(i) as EaElements.TextField).text = parts[i];
    }
    // The shown graph and selection belong to the k they were found for: switching to Other, or typing a k not yet
    // committed, takes them away at once and ignores any answer still on its way. A k other than the Find k row's
    // leaves that search. One rule for every input: the request in flight is retired and the shown graph and selection
    // are cleared before anything else happens, so no answer can arrive for inputs the controls no longer show; while
    // a search runs, the inputs themselves are disabled.
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
        return chosenSites.slice();
    }
    // A site's check in the sites list: at least one stays chosen.
    function setSite(id, on) {
        const next = chosenSites.filter(s => s !== id);
        if (on)
            next.push(id);
        if (next.length === 0)
            return;
        chosenSites = sites.map(s => s.id).filter(s => next.indexOf(s) >= 0);
        find();
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
        // A group in which every chosen site must carry no moment is never shown (owner, 2026-11-28).
        graphRequest = project.findMagneticGroups(structureIndex, k, ticked, false, kSnapshotId, kRow);
    }

    Component.onCompleted: {
        presets = project.magneticPresets(structureIndex);
        sites = project.magneticSites(structureIndex);
        chosenSites = sites.filter(s => s.magnetic).map(s => s.id);
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

        // One toolbar row, built from the chart toolbar's own boxes and buttons and spaced as Experiment → Pattern's
        // (owner, 2026-11-28, header design B), in groups a toolbar group's gap apart: what is analysed (k with its
        // magnetic cell, the sites), which groups are shown (levels, net moment), what Add creates (the starting
        // moments), and how the groups are shown (Graph, List).
        Row {
            id: toolbar
            objectName: "magnetic.toolbar"
            spacing: AppSizes.toolbarSpacing
            // The chart toolbar's gap between groups (ToolbarLines.groupSpacing), less the spacing around the gap item.
            // Whole pixels, so the boxes after it sit on the pixel grid and their text stays sharp (owner, Retina).
            readonly property real groupGap: Math.round(EaStyle.Sizes.fontPixelSize * 0.5 + 2 * AppSizes.toolbarSpacing - 2 * spacing)

            readonly property var kEntries: popup.presets.map(p => {
                const k = p.k.split(",").join(", ");
                const named = p.label === "" ? `(${k})` : `${p.label} (${k})`;
                return p.cell === undefined || p.cell === "" ? named : `${named} · ${p.cell.split(",").join(", ")}`;
            }).concat([qsTr("Other…")])
            // Other, closed: the k typed and, once found, its magnetic cell, as a preset shows its own.
            readonly property string otherShown: popup.found !== null && popup.kIndex === popup.presets.length
                ? `(${popup.k.split(",").join(", ")}) · ${popup.found.cell.replace(";0,0,0", "").split(",").join(", ")}`
                : qsTr("Other…")

            ToolbarComboBox {
                id: kChoice
                objectName: "magnetic.k"
                enabled: !popup.busy
                toolTip: qsTr("Propagation vector k and its magnetic cell")
                model: toolbar.kEntries
                closedTexts: toolbar.kEntries.map((e, i) => qsTr("k: %1").arg(i === popup.presets.length ? toolbar.otherShown : e))
                fitShown: true
                shownIndex: popup.kIndex
                onActivated: index => {
                    popup.kIndex = index;
                    if (index < popup.presets.length)
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
                    visible: popup.kIndex === popup.presets.length
                    width: EaStyle.Sizes.fontPixelSize * 4
                    height: AppSizes.toolbarControlSize
                    placeholderText: ["k₁", "k₂", "k₃"][index]
                    text: "0"
                    onTextEdited: popup.invalidateGraph()
                    onEditingFinished: popup.find()
                }
            }
            MagneticSitesBox {
                objectName: "magnetic.sites"
                enabled: !popup.busy
                structure: popup.structure
                sites: popup.sites
                chosen: popup.chosenSites
                onToggled: (id, on) => popup.setSite(id, on)
            }
            Item {
                width: toolbar.groupGap
                height: 1
            }
            ToolbarComboBox {
                // Levels, net moment and start filter or set up what a search shows, so they stay open while it runs:
                // a click on one ends a k edit, which starts the search, and must still open it.
                objectName: "magnetic.levels"
                toolTip: qsTr("Which levels of groups are shown")
                model: [qsTr("All"), qsTr("Maximal only")]
                closedTexts: [qsTr("levels: All"), qsTr("levels: Maximal only")]
                fitShown: true
                shownIndex: popup.maximalOnly ? 1 : 0
                onActivated: index => {
                    popup.maximalOnly = index === 1;
                    popup.selected = popup.selected.filter(i => popup.selectable(i));
                }
            }
            ToolbarComboBox {
                objectName: "magnetic.netMoment"
                toolTip: qsTr("Groups by their net moment: ferromagnetic (FM on the cards) or zero")
                model: [qsTr("Any"), qsTr("Ferromagnetic"), qsTr("Zero")]
                closedTexts: [qsTr("net moment: Any"), qsTr("net moment: Ferromagnetic"), qsTr("net moment: Zero")]
                fitShown: true
                shownIndex: popup.netMoment
                onActivated: index => {
                    popup.netMoment = index;
                    popup.selected = popup.selected.filter(i => popup.selectable(i));
                }
            }
            Item {
                width: toolbar.groupGap
                height: 1
            }
            // What Add creates, a group of its own (owner, 2026-11-28).
            ToolbarComboBox {
                objectName: "magnetic.startMoments"
                toolTip: qsTr("The moments each new structure starts with: 2 to 3 μB along the allowed components, or zero")
                model: [qsTr("Non-zero"), qsTr("Zero")]
                closedTexts: [qsTr("start: Non-zero"), qsTr("start: Zero")]
                fitShown: true
                shownIndex: popup.startMoments ? 0 : 1
                onActivated: index => popup.startMoments = index === 0
            }
            Item {
                width: toolbar.groupGap
                height: 1
            }
            ChartToolButton {
                objectName: "magnetic.graphView"
                fontIcon: "project-diagram"
                toolTip: qsTr("Graph")
                checked: !popup.listMode
                onClicked: popup.listMode = false
            }
            ChartToolButton {
                objectName: "magnetic.listView"
                fontIcon: "list"
                toolTip: qsTr("List")
                checked: popup.listMode
                onClicked: popup.listMode = true
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
            Layout.preferredHeight: popup.listMode ? listView.contentHeight + EaStyle.Sizes.tableRowHeight : graphView.contentHeight
            currentIndex: popup.listMode ? 1 : 0

            // The graph's cards and level titles start one gap in, where the edges into the first column run: the
            // graph sits that gap further left, so they line up with the controls above and those edges run in the
            // dialog's padding (owner, 2026-11-27).
            Item {
                MagneticSubgroupGraph {
                    id: graphView
                    objectName: "magnetic.graph"
                    x: -gap
                    width: parent.width + gap
                    height: parent.height
                    nodes: popup.nodes
                    selected: popup.selected
                    maximalOnly: popup.maximalOnly
                    netMoment: popup.netMoment
                    parentCell: popup.found ? popup.found.cell : ""
                    onShownNodeChanged: popup.hovered = shownNode
                    onToggled: index => popup.toggle(index)
                }
            }

            // The list: one row per group in the app's table (DataTable, as Excluded regions and the parameter table),
            // a check box column to select, the group's values, then each site's moments in a column of its own.
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
                        if ((!popup.maximalOnly || Math.max(1, popup.nodes[i].row) === 1) && popup.netShown(popup.nodes[i]))
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

    // Esc unpins a pinned card before it would close the dialog: while a lineage is pinned the dialog itself does not
    // take Esc, so it reaches the shortcut below.
    closePolicy: graphView.pinned >= 0 ? Popup.CloseOnPressOutside : Popup.CloseOnEscape | Popup.CloseOnPressOutside
    // Application-wide, as a window shortcut does not reach this modal dialog, and taking no focus from its controls.
    Shortcut {
        sequences: [StandardKey.Cancel]
        context: Qt.ApplicationShortcut
        enabled: popup.opened && graphView.pinned >= 0
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
                    if (popup.found !== null && popup.project.addMagneticCandidates(popup.found.graphId, popup.selected, popup.startMoments, popup.selectAfterAdd)) {
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
