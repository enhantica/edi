// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Shapes

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The magnetic groups a propagation vector allows (crysta ADR-0137 A4), one block per level: a header with the level's
// count and a check box selecting all of it, then its groups as compact cards wrapped to the width. With Maximal only
// just the first level shows. The covering edges are drawn only for the group under the pointer or selected, so the
// levels stay readable (owner, 2026-11-27).
Flickable {
    id: graph

    // magneticGroupsFound's nodes: {bns, name, type, row, embedding, domains, netMoment, momentAllowed, transform,
    // moments, subgroups}.
    property var nodes: []
    property var selected: []
    property bool maximalOnly: true
    property int hovered: -1
    // A card whose body was clicked stays shown, with its relatives and its details, while the pointer moves and the
    // view scrolls; a click on it again, on another card's body or on an empty area, or Esc, unpins it (owner,
    // 2026-11-27). The check box keeps selecting for Add.
    property int pinned: -1
    onNodesChanged: pinned = -1
    readonly property int shownNode: pinned >= 0 ? pinned : hovered

    signal toggled(int index)

    // A card as wide as its longest name or second line needs, with its check box and inner margins, so more fit on
    // a line; as tall as its two lines with the same margin around and between them (owner, 2026-11-27).
    readonly property real cardMargin: AppSizes.tableCellMargin
    readonly property real cardSpacing: AppSizes.tableCellMargin * 0.5
    readonly property real checkWidth: EaStyle.Sizes.fontPixelSize * 1.6
    readonly property int nodeWidth: {
        let widest = 0;
        for (const n of nodes)
            widest = Math.max(widest, nameMetrics.advanceWidth(graph.nameOf(n)) + checkWidth, lineMetrics.advanceWidth(graph.lineOf(n)));
        return Math.ceil(Math.max(EaStyle.Sizes.fontPixelSize * 6, widest) + 2 * cardMargin + 2);
    }
    readonly property int nodeHeight: Math.ceil(2 * cardMargin + Math.max(nameMetrics.height, checkWidth) + cardSpacing + lineMetrics.height)
    // About twice the earlier spacing between cards.
    readonly property int gap: 20
    readonly property int headerHeight: 28
    readonly property int levelGap: 26
    readonly property int perLine: Math.max(1, Math.floor((width - gap) / (nodeWidth + gap)))

    function nameOf(n) {
        return n.bns === "" ? qsTr("not identified") : n.name;
    }
    function lineOf(n) {
        return n.bns === "" ? "" : `${n.bns}${n.embedding > 1 ? " #" + n.embedding : ""} · ${qsTr("type")} ${["", "I", "II", "III", "IV"][n.type] ?? ""}${n.netMoment ? " · FM" : ""}`;
    }
    FontMetrics {
        id: nameMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        font.bold: true
    }
    FontMetrics {
        id: lineMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
    }
    function shown(i) {
        return !maximalOnly || Math.max(1, nodes[i].row) === 1;
    }
    function selectable(i) {
        const n = nodes[i];
        return n !== undefined && n.bns !== "" && n.momentAllowed;
    }
    function lit(i) {
        return i === shownNode;
    }
    // The levels shown, each its node indices.
    readonly property var levels: {
        const out = [];
        for (let i = 0; i < nodes.length; ++i) {
            if (!shown(i))
                continue;
            const r = Math.max(1, nodes[i].row);
            while (out.length < r)
                out.push([]);
            out[r - 1].push(i);
        }
        return out.filter(level => level.length > 0);
    }
    // Each level's top, its header first and its cards in lines of perLine.
    readonly property var levelTops: {
        const out = [];
        let y = gap;
        for (const level of levels) {
            out.push(y);
            y += headerHeight + Math.ceil(level.length / perLine) * (nodeHeight + gap) + levelGap;
        }
        out.push(y);
        return out;
    }
    function positionOf(i) {
        for (let l = 0; l < levels.length; ++l) {
            const at = levels[l].indexOf(i);
            if (at < 0)
                continue;
            return Qt.point(gap + (at % perLine) * (nodeWidth + gap), levelTops[l] + headerHeight + Math.floor(at / perLine) * (nodeHeight + gap));
        }
        return Qt.point(0, 0);
    }
    // An edge's corners from parent i to child j, through the gaps only (conductor seq 51): down into the band above the
    // child's level, across to the gap left of the child's column, down that gap to the child's middle and onto its
    // left side (owner, 2026-11-27: shorter lines), so no edge crosses a card.
    function route(i, j) {
        const from = positionOf(i);
        const to = positionOf(j);
        let top = to.y;
        for (let l = 0; l < levels.length; ++l)
            if (levels[l].indexOf(j) >= 0)
                top = levelTops[l];
        const band = top - levelGap / 2;
        const lane = to.x - gap / 2;
        const middle = to.y + nodeHeight / 2;
        return [Qt.point(from.x + nodeWidth / 2, from.y + nodeHeight), Qt.point(from.x + nodeWidth / 2, band), Qt.point(lane, band), Qt.point(lane, middle), Qt.point(to.x, middle)];
    }
    function related(i, j) {
        return nodes[i].subgroups.indexOf(j) >= 0 || nodes[j].subgroups.indexOf(i) >= 0;
    }

    clip: true
    contentWidth: width
    contentHeight: levelTops.length > 0 ? levelTops[levelTops.length - 1] : 0
    ScrollBar.vertical: EaElements.ScrollBar {}

    // A click on an empty area unpins (owner, 2026-11-27).
    MouseArea {
        z: -2
        width: graph.contentWidth
        height: Math.max(graph.contentHeight, graph.height)
        onClicked: graph.pinned = -1
    }

    // Edges of the group under the pointer only, to its covering subgroups, behind every card.
    Repeater {
        model: graph.maximalOnly ? 0 : graph.nodes.length
        delegate: Item {
            id: edges
            required property int index
            z: -1
            readonly property point from: graph.positionOf(index)
            visible: graph.shown(index) && graph.lit(index)
            Repeater {
                model: graph.nodes[edges.index].subgroups
                delegate: Shape {
                    id: edge
                    required property int modelData
                    readonly property var corners: graph.route(edges.index, modelData)
                    visible: graph.shown(modelData)
                    ShapePath {
                        strokeColor: EaStyle.Colors.themeAccent
                        strokeWidth: 1.5
                        fillColor: "transparent"
                        startX: edge.corners[0].x
                        startY: edge.corners[0].y
                        PathPolyline {
                            path: edge.corners
                        }
                    }
                }
            }
        }
    }

    // A level's header: its name and its count.
    Repeater {
        model: graph.levels.length
        delegate: Row {
            id: header
            required property int index
            readonly property var members: graph.levels[index]
            x: graph.gap
            y: graph.levelTops[index] ?? 0
            height: graph.headerHeight
            spacing: graph.gap
            // The level's name and count in bold, on the cards' edge (owner, 2026-11-27: no per-level check box; the
            // footer's Select all and Clear choose).
            EaElements.Label {
                objectName: `magnetic.level.${header.index}`
                anchors.verticalCenter: parent.verticalCenter
                font.bold: true
                text: (header.index === 0 ? qsTr("Maximal") : qsTr("Level %1").arg(header.index + 1)) + " · " + (header.members.length === 1 ? qsTr("1 group") : qsTr("%1 groups").arg(header.members.length))
            }
        }
    }

    Repeater {
        model: graph.nodes.length
        delegate: Rectangle {
            id: node
            required property int index
            readonly property var data_: graph.nodes[index]
            readonly property bool chosen: graph.selected.indexOf(index) >= 0
            readonly property bool near: graph.shownNode >= 0 && graph.shownNode !== index && graph.related(graph.shownNode, index)
            readonly property point at: graph.positionOf(index)
            objectName: `magnetic.node.${index}`
            visible: graph.shown(index)
            x: at.x
            y: at.y
            width: graph.nodeWidth
            height: graph.nodeHeight
            // A card selects as the list's rows do, by its check box; its border marks the group under the pointer and
            // its covering relatives (conductor seq 48).
            radius: 2
            color: EaStyle.Colors.contentBackground
            border.width: near || graph.shownNode === index ? 2 : 1
            border.color: near || graph.shownNode === index ? EaStyle.Colors.themeAccent : EaStyle.Colors.chartAxis

            // The body: hovering shows the group's relatives and details, a click pins them. Below the check box, which
            // takes its own clicks.
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onEntered: graph.hovered = node.index
                onExited: if (graph.hovered === node.index)
                    graph.hovered = -1
                onClicked: graph.pinned = graph.pinned === node.index ? -1 : node.index
            }

            Column {
                anchors.fill: parent
                // One margin around the two lines and half of it between them; the check box starts at the margin,
                // where the second line's text does.
                anchors.margins: graph.cardMargin
                spacing: graph.cardSpacing
                // A group that cannot be chosen reads faded, while its card stays opaque over the edges.
                opacity: graph.selectable(node.index) ? 1.0 : 0.45
                Row {
                    width: parent.width
                    EaElements.CheckBox {
                        objectName: `magnetic.node.${node.index}.check`
                        width: graph.checkWidth
                        height: Math.max(nameLabel.implicitHeight, graph.checkWidth)
                        padding: 0
                        leftPadding: 0
                        enabled: graph.selectable(node.index)
                        checked: node.chosen
                        onClicked: graph.toggled(node.index)
                    }
                    EaElements.Label {
                        id: nameLabel
                        width: parent.width - parent.children[0].width
                        elide: Text.ElideRight
                        font.bold: true
                        anchors.verticalCenter: parent.children[0].verticalCenter
                        text: graph.nameOf(node.data_)
                    }
                }
                EaElements.Label {
                    width: parent.width
                    elide: Text.ElideRight
                    font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
                    text: graph.lineOf(node.data_)
                }
            }
        }
    }
}
