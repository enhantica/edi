// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
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
    // Hovering a card shows its relatives; its pin (shown on the hovered card) keeps them shown while other cards are
    // hovered, until the pin is clicked again or Esc is pressed (owner, 2026-11-27). Pinning does not select.
    property int pinned: -1
    // The transform from the parent to the groups' magnetic cell, for each card's tooltip.
    property string parentCell: ""
    // A card's details, label then value for each row, for its tooltip (owner, 2026-11-27): the group, its type and net moment, the two
    // transforms, the domains, then each magnetic site's allowed moment components.
    function detailsOf(n) {
        const cells = [qsTr("BNS"), `${n.name} ${n.bns}${n.embedding > 1 ? " #" + n.embedding : ""}`,
                       qsTr("Type"), ["", "I", "II", "III", "IV"][n.type] ?? ""];
        if (n.netMoment)
            cells.push(qsTr("Net moment"), qsTr("yes"));
        cells.push(qsTr("From the parent"), parentCell, qsTr("To the BNS standard"), n.transform,
                   qsTr("Domains"), String(n.domains));
        for (const site of String(n.moments ?? "").split(" · ")) {
            const at = site.indexOf(" ");
            if (at > 0)
                cells.push(site.slice(0, at), site.slice(at + 1));
        }
        return cells;
    }
    onNodesChanged: pinned = -1
    readonly property int shownNode: pinned >= 0 ? pinned : hovered

    signal toggled(int index)

    // A card as wide as its longest name or second line needs, with its inner margins, so more fit on a line; as tall
    // as its two lines with the same margin around and between them (owner, 2026-11-27).
    readonly property real cardMargin: AppSizes.tableCellMargin
    readonly property real cardSpacing: AppSizes.tableCellMargin * 0.5
    // The text's own room above its capitals: the visible gap at the top is the margin plus it, so the left side and
    // the bottom (less the second line's descent) take the same visible gap (owner, 2026-11-27).
    readonly property real capRoom: Math.max(0, nameMetrics.ascent + nameMetrics.tightBoundingRect("H").y)
    readonly property real cardPadding: cardMargin + capRoom
    // The width of a highlighted card's border and of the lines between cards (owner, 2026-11-27).
    readonly property real lineWidth: 1.5
    readonly property int nodeWidth: {
        let widest = 0;
        for (const n of nodes)
            widest = Math.max(widest, nameMetrics.advanceWidth(graph.nameOf(n)), lineMetrics.advanceWidth(graph.lineOf(n)));
        return Math.ceil(Math.max(EaStyle.Sizes.fontPixelSize * 6, widest) + 2 * cardPadding + 2);
    }
    readonly property int nodeHeight: Math.ceil(cardMargin + nameMetrics.height + cardSpacing + lineMetrics.height +
                                                Math.max(0, cardPadding - lineMetrics.descent))
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
    // The shown card's whole lineage (owner, 2026-11-27): every ancestor up to the maximal level and every descendant
    // down to the last, each as a set of node indices, the card itself in both.
    readonly property var parentsOf: {
        const up = nodes.map(() => []);
        nodes.forEach((n, i) => n.subgroups.forEach(j => up[j].push(i)));
        return up;
    }
    function reach(start, next) {
        const seen = {};
        if (start < 0)
            return seen;
        const queue = [start];
        seen[start] = true;
        while (queue.length > 0) {
            const at = queue.shift();
            for (const j of next(at))
                if (!seen[j]) {
                    seen[j] = true;
                    queue.push(j);
                }
        }
        return seen;
    }
    readonly property var ancestors: shownNode >= 0 && shownNode < nodes.length ? reach(shownNode, i => parentsOf[i]) : ({})
    readonly property var descendants: shownNode >= 0 && shownNode < nodes.length ? reach(shownNode, i => nodes[i].subgroups) : ({})
    function related(i, j) {
        return ancestors[j] === true || descendants[j] === true;
    }
    // An edge along the lineage: both ends above the shown card, or both below it.
    function onLineage(i, j) {
        return (ancestors[i] === true && ancestors[j] === true) || (descendants[i] === true && descendants[j] === true);
    }

    clip: true
    contentWidth: width
    contentHeight: levelTops.length > 0 ? levelTops[levelTops.length - 1] : 0
    ScrollBar.vertical: EaElements.ScrollBar {}

    // The edges of the shown group's lineage, between every pair of adjacent levels along it, behind every card.
    Repeater {
        model: graph.maximalOnly ? 0 : graph.nodes.length
        delegate: Item {
            id: edges
            required property int index
            z: -1
            readonly property point from: graph.positionOf(index)
            visible: graph.shown(index) && (graph.ancestors[index] === true || graph.descendants[index] === true)
            Repeater {
                model: graph.nodes[edges.index].subgroups
                delegate: Shape {
                    id: edge
                    required property int modelData
                    readonly property var corners: graph.route(edges.index, modelData)
                    visible: graph.shown(modelData) && graph.onLineage(edges.index, modelData)
                    ShapePath {
                        strokeColor: EaStyle.Colors.themeAccent
                        strokeWidth: graph.lineWidth
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
            // A click on the card selects it, filled with the app's blue and white text; unselected it takes the chart's
            // background. Its border marks the group shown and its covering relatives (owner, 2026-11-27).
            radius: 2
            readonly property color textColor: chosen ? "white" : EaStyle.Colors.themeForeground
            color: chosen ? EaStyle.Colors.themeAccent : EaStyle.Colors.chartBackground
            border.width: near || graph.shownNode === index ? graph.lineWidth : 1
            border.color: near || graph.shownNode === index ? EaStyle.Colors.themeAccent : EaStyle.Colors.chartAxis


            Column {
                anchors.fill: parent
                // The same visible gap on every side, and half the margin between the two lines.
                anchors.topMargin: graph.cardMargin
                anchors.leftMargin: graph.cardPadding
                anchors.rightMargin: graph.cardPadding
                spacing: graph.cardSpacing
                // A group that cannot be chosen reads faded, while its card stays opaque over the edges.
                opacity: graph.selectable(node.index) ? 1.0 : 0.45
                EaElements.Label {
                    id: nameLabel
                    width: parent.width
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignLeft
                    color: node.textColor
                    text: graph.nameOf(node.data_)
                }
                EaElements.Label {
                    width: parent.width
                    elide: Text.ElideRight
                    font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
                    horizontalAlignment: Text.AlignLeft
                    color: node.textColor
                    text: graph.lineOf(node.data_)
                }
            }
            MouseArea {
                id: cardArea
                objectName: `magnetic.node.${node.index}.card`
                anchors.fill: parent
                hoverEnabled: true
                enabled: true
                onEntered: graph.hovered = node.index
                onExited: if (graph.hovered === node.index)
                    graph.hovered = -1
                onClicked: if (graph.selectable(node.index))
                    graph.toggled(node.index)

                // The sidebar groups' pin, in the card's top-right corner while the card is hovered, and always while
                // it is pinned: grey, upright in the accent colour when on.
                EaElements.Label {
                    id: pin
                    objectName: `magnetic.node.${node.index}.pin`
                    readonly property bool on: graph.pinned === node.index
                    visible: on || graph.hovered === node.index
                    x: parent.width - width - graph.cardMargin * 0.5
                    y: graph.cardMargin * 0.5
                    width: EaStyle.Sizes.fontPixelSize * 1.25
                    height: width
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.8
                    rotation: on ? 0 : 45
                    // On a selected (blue) card always white: faded until hovered or pinned, so it never sinks into
                    // the fill (owner, 2026-11-27).
                    color: node.chosen ? "white" : on ? EaStyle.Colors.themeAccent : pinArea.containsMouse ? EaStyle.Colors.themeForegroundHovered : node.textColor
                    opacity: node.chosen && !on && !pinArea.containsMouse ? 0.6 : 1.0
                    text: "thumbtack"
                    MouseArea {
                        id: pinArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: graph.pinned = pin.on ? -1 : node.index
                    }
                }
                // The app's own tooltip (EaElements.ToolTip): its style, below the card or above it, never over it;
                // data, so at once (owner, 2026-11-27).
                EaElements.ToolTip {
                    id: details
                    objectName: `magnetic.node.${node.index}.tooltip`
                    requested: graph.hovered === node.index && node.data_.bns !== ""
                    data: true
                    text: node.data_.bns !== "" ? graph.detailsOf(node.data_).join(" ") : ""
                    contentItem: GridLayout {
                        columns: 2
                        columnSpacing: EaStyle.Sizes.fontPixelSize
                        rowSpacing: EaStyle.Sizes.fontPixelSize * 0.2
                        Repeater {
                            model: graph.hovered === node.index ? graph.detailsOf(node.data_) : []
                            delegate: EaElements.Label {
                                required property string modelData
                                required property int index
                                color: details.textColor
                                font: details.font
                                text: modelData
                            }
                        }
                    }
                }
            }
        }
    }
}
