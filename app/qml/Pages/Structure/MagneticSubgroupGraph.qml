// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Shapes

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// The magnetic groups a propagation vector allows, as rows of maximal groups and their subgroups with the covering
// edges between them (crysta ADR-0137 A4). The parent's grey group heads it, greyed. A node shows its BNS symbol,
// number, type, the allowed moment components per split site and FM; clicking toggles its selection.
Flickable {
    id: graph

    // magneticGroupsFound's nodes: {bns, name, type, row, embedding, domains, netMoment, momentAllowed, transform,
    // moments, subgroups}.
    property var nodes: []
    property string parentName: ""
    property string cell: ""
    property var selected: []
    property int hovered: -1
    // Off: the maximal groups only (row 1); on: every subgroup row.
    property bool showAll: false

    readonly property int nodeWidth: 220
    readonly property int nodeHeight: 84
    readonly property int gap: 16
    readonly property int rowGap: 44

    function shown(i) {
        return showAll || Math.max(1, nodes[i].row) === 1;
    }
    function selectable(i) {
        const n = nodes[i];
        return n !== undefined && n.bns !== "" && n.momentAllowed && shown(i);
    }
    // An edge is drawn only to or from the node under the pointer or a selected one, so the rows
    // stay readable however many covering edges a graph has.
    function lit(i) {
        return i === hovered || selected.indexOf(i) >= 0;
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
    function selectAll() {
        const next = [];
        for (let i = 0; i < nodes.length; ++i)
            if (selectable(i))
                next.push(i);
        selected = next;
    }

    // Row 0 is the grey group; rows 1.. hold the nodes, each row centred.
    readonly property var rows: {
        const out = [];
        for (let i = 0; i < nodes.length; ++i) {
            if (!shown(i))
                continue;
            const r = Math.max(1, nodes[i].row);
            while (out.length <= r)
                out.push([]);
            out[r].push(i);
        }
        return out;
    }
    readonly property int widest: {
        let w = 1;
        for (const r of rows)
            if (r)
                w = Math.max(w, r.length);
        return w;
    }
    readonly property real canvasWidth: widest * (nodeWidth + gap) + gap
    readonly property real canvasHeight: Math.max(2, rows.length) * (nodeHeight + rowGap) + gap

    function positionOf(i) {
        const r = Math.max(1, nodes[i].row);
        const row = rows[r];
        if (!shown(i) || row === undefined)
            return Qt.point(0, 0);
        const at = row.indexOf(i);
        const left = (canvasWidth - row.length * (nodeWidth + gap) + gap) / 2;
        return Qt.point(left + at * (nodeWidth + gap), gap + r * (nodeHeight + rowGap));
    }

    clip: true
    contentWidth: canvasWidth * zoom
    contentHeight: canvasHeight * zoom
    // Fitted to the view until the user zooms (Ctrl + wheel).
    property real userZoom: 0
    readonly property real fitZoom: Math.min(1.0, width / Math.max(1, canvasWidth), height / Math.max(1, canvasHeight))
    readonly property real zoom: userZoom > 0 ? userZoom : Math.max(0.3, fitZoom)
    ScrollBar.vertical: EaElements.ScrollBar {}
    ScrollBar.horizontal: EaElements.ScrollBar {}

    WheelHandler {
        acceptedModifiers: Qt.ControlModifier
        onWheel: event => graph.userZoom = Math.min(2.5, Math.max(0.3, graph.zoom * (event.angleDelta.y > 0 ? 1.1 : 1 / 1.1)))
    }

    Item {
        id: canvas
        width: graph.canvasWidth
        height: graph.canvasHeight
        scale: graph.zoom
        transformOrigin: Item.TopLeft

        // Edges: a node to each of its covering subgroups; row 1 to the grey group.
        Repeater {
            model: graph.nodes.length
            delegate: Item {
                id: edges
                required property int index
                readonly property point from: graph.positionOf(index)
                visible: graph.shown(edges.index)
                Shape {
                    visible: Math.max(1, graph.nodes[edges.index].row) === 1 && graph.lit(edges.index)
                    ShapePath {
                        strokeColor: EaStyle.Colors.themeForegroundDisabled
                        strokeWidth: 1
                        fillColor: "transparent"
                        startX: edges.from.x + graph.nodeWidth / 2
                        startY: edges.from.y
                        PathLine {
                            x: graph.canvasWidth / 2
                            y: graph.gap + graph.nodeHeight
                        }
                    }
                }
                Repeater {
                    model: graph.nodes[edges.index].subgroups
                    delegate: Shape {
                        id: edge
                        required property int modelData
                        visible: graph.showAll && graph.shown(modelData) && (graph.lit(edges.index) || graph.lit(modelData))
                        readonly property point to: graph.positionOf(modelData)
                        ShapePath {
                            strokeColor: EaStyle.Colors.themeForegroundMinor
                            strokeWidth: 1
                            fillColor: "transparent"
                            startX: edges.from.x + graph.nodeWidth / 2
                            startY: edges.from.y + graph.nodeHeight
                            PathLine {
                                x: edge.to.x + graph.nodeWidth / 2
                                y: edge.to.y
                            }
                        }
                    }
                }
            }
        }

        // The parent's grey group, greyed and not selectable.
        Rectangle {
            x: (graph.canvasWidth - graph.nodeWidth) / 2
            y: graph.gap
            width: graph.nodeWidth
            height: graph.nodeHeight
            radius: 4
            color: "transparent"
            border.color: EaStyle.Colors.themeForegroundDisabled
            EaElements.Label {
                anchors.centerIn: parent
                width: parent.width - 8
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                enabled: false
                text: qsTr("%1 1′ (paramagnetic)").arg(graph.parentName)
            }
        }

        Repeater {
            model: graph.nodes.length
            delegate: Rectangle {
                id: node
                required property int index
                readonly property var data_: graph.nodes[index]
                readonly property bool chosen: graph.selected.indexOf(index) >= 0
                readonly property point at: graph.positionOf(index)
                objectName: `magnetic.node.${index}`
                visible: graph.shown(index)
                x: at.x
                y: at.y
                width: graph.nodeWidth
                height: graph.nodeHeight
                radius: 4
                color: chosen ? EaStyle.Colors.themeAccentMinor : EaStyle.Colors.themeBackground
                border.color: chosen ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForegroundMinor
                opacity: graph.selectable(index) ? 1.0 : 0.45

                Column {
                    anchors.fill: parent
                    anchors.margins: 4
                    EaElements.Label {
                        width: parent.width
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        font.bold: true
                        text: node.data_.bns === "" ? qsTr("not identified") : `${node.data_.name}  ${node.data_.bns}#${node.data_.embedding}  ${qsTr("type")} ${["", "I", "II", "III", "IV"][node.data_.type] ?? ""}${node.data_.netMoment ? "  FM" : ""}${node.chosen ? "  ✓" : ""}`
                    }
                    EaElements.Label {
                        width: parent.width
                        wrapMode: Text.Wrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
                        text: node.data_.moments
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: graph.hovered = node.index
                    onExited: if (graph.hovered === node.index)
                        graph.hovered = -1
                    onClicked: graph.toggle(node.index)
                }
                EaElements.ToolTip {
                    visible: graph.hovered === node.index
                    text: qsTr("From the parent: %1\nTo the BNS standard: %2\nDomains: %3\n%4").arg(graph.cell).arg(node.data_.transform).arg(node.data_.domains).arg(node.data_.moments)
                }
            }
        }
    }
}
