// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The compact block selector (easydiffractionbeta Pages/*/SideBarText/Models.qml, Experiments.qml): the page's
// blocks in a combo box, the shown one current (edi ADR-0017 §7), with an up and a down button to its right
// that step through the list. Each block reads as there — its number, its icon in its colour (§8), its label
// (`name · file`), on one centre line (§10) — in the box and in the list.
Row {
    id: row

    // The blocks (a model with a `textRole`), their kind ("structure" or "experiment"), the shown one, and the
    // user's choice.
    property var blocks: null
    property string blocksTextRole: ""
    property string blockKind: ""
    property int blockIndex: 0
    signal blockActivated(int index)
    // The box's state, as a caller of the box itself reads it.
    readonly property alias currentIndex: selector.currentIndex
    readonly property alias count: selector.count
    readonly property alias currentText: selector.currentText
    readonly property alias popup: selector.popup

    // A step to the previous or next block, as a pick in the box; no step past either end.
    function step(offset) {
        const next = row.blockIndex + offset;
        if (next >= 0 && next < selector.count)
            row.blockActivated(next);
    }

    width: EaStyle.Sizes.sideBarContentWidth
    spacing: EaStyle.Sizes.fontPixelSize * 0.25

EaElements.ComboBox {
    id: selector

    property alias blocks: row.blocks
    property alias blocksTextRole: row.blocksTextRole
    property alias blockKind: row.blockKind
    property alias blockIndex: row.blockIndex

    // A block's line: its number, its icon in its colour, its name, on one centre line (IconLine, §10).
    function segments(index, name, nameColor) {
        if (index < 0)
            return [];
        const number = {
            "text": String(index + 1),
            "color": EaStyle.Colors.themeForegroundMinor
        };
        const icon = {
            "icon": ParameterNames.blockIcon(selector.blockKind),
            "color": AppColors.block(selector.blockKind, index)
        };
        const label = {
            "text": name,
            "color": nameColor
        };
        return [number, icon, label];
    }

    objectName: row.objectName ? `${row.objectName}.box` : ""
    width: row.width - 2 * (up.width + row.spacing)
    topInset: 0
    bottomInset: 0
    model: blocks
    textRole: blocksTextRole
    currentIndex: blockIndex
    // The choice goes to the one shared current index; the box then follows that index again, so every
    // selector over the same blocks shows the same one (edi ADR-0017 §7).
    onActivated: index => {
        row.blockActivated(index);
        selector.currentIndex = Qt.binding(() => selector.blockIndex);
    }

    // The shown block, as the base's content label places its text.
    contentItem: Item {
        clip: true

        IconLine {
            x: EaStyle.Sizes.fontPixelSize * 0.75
            anchors.verticalCenter: parent.verticalCenter
            segments: selector.segments(selector.currentIndex, selector.currentText, selector.foregroundColor)
        }
    }

    // The base's delegate, with the block's line for its content.
    delegate: EaElements.MenuItem {
        id: entry

        required property int index
        required property var model

        width: entry.parent !== null ? entry.parent.width : 0
        height: EaStyle.Sizes.comboBoxHeight
        // The base's padding of 16 on every side leaves a content area of no height in a row this tall; its
        // Label draws past that, but a clipped line would show nothing, so the line gets the row's full height
        // (edi ADR-0017 §10).
        topPadding: 0
        bottomPadding: 0
        highlighted: selector.highlightedIndex === entry.index
        hoverEnabled: selector.hoverEnabled
        text: entry.model[selector.blocksTextRole]

        contentItem: Item {
            clip: true

            IconLine {
                anchors.verticalCenter: parent.verticalCenter
                segments: selector.segments(entry.index, entry.text, EaStyle.Colors.themeForeground)
            }
        }
    }
}

EaElements.Button {
    id: up

    objectName: row.objectName ? `${row.objectName}.up` : ""
    width: EaStyle.Sizes.comboBoxHeight
    height: EaStyle.Sizes.comboBoxHeight
    enabled: row.blockIndex > 0
    text: "▲"
    ToolTip.visible: hovered
    ToolTip.text: qsTr("Previous")
    onClicked: row.step(-1)
}

EaElements.Button {
    id: down

    objectName: row.objectName ? `${row.objectName}.down` : ""
    width: EaStyle.Sizes.comboBoxHeight
    height: EaStyle.Sizes.comboBoxHeight
    enabled: row.blockIndex >= 0 && row.blockIndex < selector.count - 1
    text: "▼"
    ToolTip.visible: hovered
    ToolTip.text: qsTr("Next")
    onClicked: row.step(1)
}
}
