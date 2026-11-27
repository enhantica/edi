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

    signal toggled(int index)
    signal levelToggled(int level, bool on)

    readonly property int nodeWidth: 168
    readonly property int nodeHeight: 46
    readonly property int gap: 10
    readonly property int headerHeight: 28
    readonly property int levelGap: 26
    readonly property int perLine: Math.max(1, Math.floor((width - gap) / (nodeWidth + gap)))

    function shown(i) {
        return !maximalOnly || Math.max(1, nodes[i].row) === 1;
    }
    function selectable(i) {
        const n = nodes[i];
        return n !== undefined && n.bns !== "" && n.momentAllowed;
    }
    function lit(i) {
        return i === hovered;
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
    // child's level, across to the gap beside the child's column, down that gap to just above the child's row, across
    // to the child's centre and down onto its top edge, so no edge crosses a card.
    function route(i, j) {
        const from = positionOf(i);
        const to = positionOf(j);
        let top = to.y;
        for (let l = 0; l < levels.length; ++l)
            if (levels[l].indexOf(j) >= 0)
                top = levelTops[l];
        const band = top - levelGap / 2;
        const lane = to.x - gap / 2;
        const above = to.y - gap / 2;
        const centre = to.x + nodeWidth / 2;
        return [Qt.point(from.x + nodeWidth / 2, from.y + nodeHeight), Qt.point(from.x + nodeWidth / 2, band), Qt.point(lane, band), Qt.point(lane, above), Qt.point(centre, above), Qt.point(centre, to.y)];
    }
    function related(i, j) {
        return nodes[i].subgroups.indexOf(j) >= 0 || nodes[j].subgroups.indexOf(i) >= 0;
    }

    clip: true
    contentWidth: width
    contentHeight: levelTops.length > 0 ? levelTops[levelTops.length - 1] : 0
    ScrollBar.vertical: EaElements.ScrollBar {}

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

    // A level's header: its name, its count and a check box selecting all of its selectable groups.
    Repeater {
        model: graph.levels.length
        delegate: Row {
            id: header
            required property int index
            readonly property var members: graph.levels[index]
            readonly property var choosable: members.filter(i => graph.selectable(i))
            x: graph.gap
            y: graph.levelTops[index] ?? 0
            height: graph.headerHeight
            spacing: graph.gap
            EaElements.CheckBox {
                objectName: `magnetic.level.${header.index}`
                leftPadding: 0  // on the cards' edge
                anchors.verticalCenter: parent.verticalCenter
                enabled: header.choosable.length > 0
                checked: header.choosable.length > 0 && header.choosable.every(i => graph.selected.indexOf(i) >= 0)
                text: (header.index === 0 ? qsTr("Maximal") : qsTr("Level %1").arg(header.index + 1)) + " · " + (header.members.length === 1 ? qsTr("1 group") : qsTr("%1 groups").arg(header.members.length))
                onToggled: graph.levelToggled(header.index, checked)
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
            readonly property bool near: graph.hovered >= 0 && graph.hovered !== index && graph.related(graph.hovered, index)
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
            border.width: near || graph.hovered === index ? 2 : 1
            border.color: near || graph.hovered === index ? EaStyle.Colors.themeAccent : EaStyle.Colors.chartAxis

            Column {
                anchors.fill: parent
                // The inner margin of the app's table cells, so the check box is not on the border.
                anchors.margins: AppSizes.tableCellMargin
                // A group that cannot be chosen reads faded, while its card stays opaque over the edges.
                opacity: graph.selectable(node.index) ? 1.0 : 0.45
                Row {
                    width: parent.width
                    EaElements.CheckBox {
                        objectName: `magnetic.node.${node.index}.check`
                        height: nameLabel.implicitHeight
                        enabled: graph.selectable(node.index)
                        checked: node.chosen
                    }
                    EaElements.Label {
                        id: nameLabel
                        width: parent.width - parent.children[0].width
                        elide: Text.ElideRight
                        font.bold: true
                        text: node.data_.bns === "" ? qsTr("not identified") : node.data_.name
                    }
                }
                EaElements.Label {
                    width: parent.width
                    elide: Text.ElideRight
                    font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
                    text: node.data_.bns === "" ? "" : `${node.data_.bns}${node.data_.embedding > 1 ? " #" + node.data_.embedding : ""} · ${qsTr("type")} ${["", "I", "II", "III", "IV"][node.data_.type] ?? ""}${node.data_.netMoment ? " · FM" : ""}`
                }
            }
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onEntered: graph.hovered = node.index
                onExited: if (graph.hovered === node.index)
                    graph.hovered = -1
                onClicked: graph.toggled(node.index)
            }
        }
    }
}
