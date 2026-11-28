// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The compact block selector (easydiffractionbeta Pages/*/SideBarText/Models.qml, Experiments.qml): the page's
// blocks in a combo box, the shown one current, as a row at the top of the main area (MainAreaBlockSelector; edi
// ADR-0017 §7), with a previous and a next button on its right that step through the list. A long list has a
// search field (SearchableComboBox). Each block reads as there — its number, its icon in its colour (§8), its label
// (`name · file`), on one centre line (§10) — in the box and in the list. An experiment's line shows how the last
// fit ended on it (FitOutcomes) before its name, as the Experiments table's Fit column does.
Row {
    id: row

    // The blocks (a model with a `textRole`), their kind ("structure" or "experiment"), the shown one, and the
    // user's choice.
    property var blocks: null
    property string blocksTextRole: ""
    property string blockKind: ""
    property int blockIndex: 0
    // Told of each row the list draws and stops drawing (the experiments' scan values are read for those, edi ADR-0102
    // rule 6); null for blocks that need nothing.
    property var rowWatcher: null
    signal blockActivated(int index)
    // The box's state, as a caller of the box itself reads it.
    readonly property alias currentIndex: selector.currentIndex
    readonly property alias count: selector.count
    readonly property alias currentText: selector.currentText
    readonly property alias popup: selector.popup
    property alias backgroundColor: selector.backgroundColor
    // The blocks' fit-outcome role (experiments: `fitOutcome`) and the shown block's outcome; empty: no slot.
    property string outcomeRole: ""
    property string currentOutcome: ""
    // The blocks' role that marks the template dataset (a scan's `isTemplate`) and whether the shown one is it: its
    // line carries the word "template" in the accent blue after its name, which the line elides when long.
    property string templateRole: ""
    property bool currentTemplate: false
    // A word before the greyed number, greyed with it and followed by a dot ("Run 6 · p005"), the block's icon after it:
    // a series' run and bank selectors (the owner, 2026-11-16, 2026-11-17).
    property string numberPrefix: ""
    // An entry's line drawn by the caller, `lineFor(index, text)`, in place of the block's (a parameter picker:
    // ParameterNames.pickerLine); such a line's full name is cut at its start, where it names the block the line's icons
    // and the group's header show already, so its row and name stay; an entry cut shows the whole on hover. The list
    // widens to its widest line.
    property var lineFor: null
    // The blocks' role that names the group a row belongs to; empty: no groups. A group's title is drawn over its first
    // entry the list shows, in that entry's own item, so the list's rows stay the blocks'. A typed search ranks the
    // entries within each group and keeps the groups in their order.
    property string groupRole: ""
    // The width that shows the chosen entry's whole line: its line, the box's padding and arrow, and the two step buttons.
    // A row with room gives the selector this width (Evolution's parameter selector, the owner, 2026-11-17).
    readonly property real contentWidth: Math.ceil(shownLine.fullWidth + EaStyle.Sizes.fontPixelSize * 2.5 + (selector.indicator ? selector.indicator.width : 0)) + 2 * (up.width + spacing)
    property real lineExtraWidth: EaStyle.Sizes.fontPixelSize * 7

    // A step to the previous or next block, as a pick in the box; no step past either end.
    function step(offset) {
        ApplicationInfo.stepBlock(offset);
    }

    width: EaStyle.Sizes.sideBarContentWidth
    // The gap between buttons in a chart toolbar group, between the box and each button (owner, 2026-10-05).
    spacing: AppSizes.toolbarSpacing

    FontMetrics {
        id: lineMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }

    SearchableComboBox {
        id: selector

        property alias blocks: row.blocks
        property alias blocksTextRole: row.blocksTextRole
        property alias blockKind: row.blockKind
        property alias blockIndex: row.blockIndex

        // A block's line, in the Experiments table's column order: its number, its icon in its colour, its fit
        // outcome, its name and a scan's template mark, on one centre line (IconLine, §10).
        function segments(index, name, nameColor, outcome, isTemplate, room) {
            if (row.lineFor)
                return row.lineFor(index, name);
            const line = ApplicationInfo.blockSegments(index, name, nameColor, outcome, isTemplate);
            // A name of parts ("d20 · file · Rwp 4.69 % · 497.379 K") cuts its file only: a cut through a number dropped
            // its digits (the owner's sweep, 2026-11-22). A value with no room is left out whole, the last one kept longest,
            // before the file is cut to fewer than ten characters, half a dozen at each end and the ellipsis (T10).
            const at = line.findIndex(piece => piece.elides === true);
            const parts = at >= 0 ? String(line[at].text).split(" · ") : [];
            if (parts.length >= 3) {
                const piece = line[at];
                const gap = EaStyle.Sizes.fontPixelSize * 0.5;
                const advance = text => lineMetrics.advanceWidth(text);
                const others = line.reduce((sum, each) => sum + (each === piece ? 0 : gap + (each.icon !== undefined ? EaStyle.Sizes.fontPixelSize * 1.25 : advance(each.text ?? ""))), 0);
                const file = parts[1].length > 12 ? Math.min(advance(parts[1]), advance(parts[1].slice(0, 6) + "…" + parts[1].slice(-6))) : advance(parts[1]);
                const need = () => others + file + (parts.length - 1) * (2 * gap + advance("·")) + parts.reduce((sum, part, n) => sum + (n === 1 ? 0 : advance(part)), 0);
                while (parts.length > 2 && need() > room)
                    parts.splice(Math.max(2, parts.length - 2), 1);
                // Each dot a piece, so the line's one spacing stands on both its sides, as a space does. The file is plain
                // text, which Qt can shorten.
                const dot = Object.assign({}, piece, {
                    "text": "·",
                    "elides": false
                });
                const pieces = [];
                parts.forEach((part, n) => pieces.push(...(n > 0 ? [dot] : []), Object.assign({}, piece, {
                        "text": part,
                        "elides": n === 1,
                        "factors": n > 1
                    })));
                line.splice(at, 1, ...pieces);
            }
            // The scan's starting dataset reads "Start" in the accent, as the Experiments table's file cell
            // names it (the owner, 2026-11-16).
            if (isTemplate && line.length > 0) {
                line[line.length - 1].text = qsTr("Start");
                line[line.length - 1].color = String(EaStyle.Colors.themeAccent);
            }
            if (row.numberPrefix === "" || line.length < 2)
                return line;
            // The word before the number, the icon kept after it, coloured as the run's or bank's curve (the owner,
            // 2026-11-17).
            line[0].text = `${row.numberPrefix} ${line[0].text} ·`;
            return line;
        }

        // The rows whose entry carries its group's title: each shown entry that follows one of another group, or none,
        // in the order the list draws them (a typed search reorders the list).
        readonly property var groupOpeners: {
            const openers = new Set();
            if (row.groupRole === "" || row.blocks === null)
                return openers;
            let previous = null;
            for (const shown of selector.shownRows()) {
                const group = row.blocks.text(shown, row.groupRole);
                if (group !== previous)
                    openers.add(shown);
                previous = group;
            }
            return openers;
        }
        // The titles the list shows, which its height is not counted from: only those of the groups the search leaves.
        listExtra: () => selector.groupOpeners.size * EaStyle.Sizes.comboBoxHeight

        groupOf: row.groupRole !== "" ? (index => row.blocks.text(index, row.groupRole)) : null
        objectName: row.objectName ? `${row.objectName}.box` : ""
        width: row.width - 2 * (up.width + row.spacing)
        topInset: 0
        bottomInset: 0
        model: blocks
        textRole: blocksTextRole
        currentIndex: blockIndex
        // A drawn line's list as wide as its widest entry and its icons, within the window.
        popup.width: row.lineFor ? Math.min(Math.max(selector.width, selector.optionWidth + row.lineExtraWidth), selector.Window.width - popup.leftMargin - popup.rightMargin) : selector.width
        // The box follows the shared index again whenever its rows come and go: emptied for a moment (the one
        // experiment replaced by Load data, every structure put back by an Undo) it drops to no entry, and the
        // shared index, unchanged, would never set it back.
        onCountChanged: selector.currentIndex = Qt.binding(() => selector.blockIndex)
        // The choice goes to the one shared current index; the box then follows that index again, so every
        // selector over the same blocks shows the same one (edi ADR-0017 §7).
        onActivated: index => ApplicationInfo.activateBlock(index, () => {
                selector.currentIndex = Qt.binding(() => selector.blockIndex);
            })

        // The shown block, as the base's content label places its text.
        contentItem: Item {
            clip: true

            IconLine {
                id: shownLine
                x: EaStyle.Sizes.fontPixelSize * 0.75
                anchors.verticalCenter: parent.verticalCenter
                segments: selector.segments(selector.currentIndex, selector.currentText, selector.foregroundColor, row.currentOutcome, row.currentTemplate, maximumWidth)
                // Keep the arrow's hit area clear even when the label and its marks are too wide.
                width: Math.max(0, Math.min(parent.width - x, selector.indicator && selector.indicator.visible && !selector.mirrored ? selector.indicator.x - parent.x - x - EaStyle.Sizes.fontPixelSize * 0.5 : parent.width - x))
                maximumWidth: Math.max(1, width)
                clip: true
                elide: row.lineFor ? Text.ElideLeft : Text.ElideMiddle
            }
        }

        // The base's delegate, with the block's line for its content.
        delegate: EaElements.MenuItem {
            id: entry

            // Watched while it passes the search (a filtered entry is folded away) and lies in the list's visible part
            // (a delegate kept outside it is not drawn), under its index now; released through the watcher it was
            // registered with, so a new project's watcher never releases the old one's row.
            readonly property ListView ownList: ListView.view
            readonly property bool inView: ownList !== null && height > 0 && y + height > ownList.contentY && y < ownList.contentY + ownList.height
            readonly property bool watched: row.rowWatcher !== null && matching && inView
            property int watching: -1
            property var watcher: null
            function rewatch(): void {
                if (watching >= 0 && watcher)
                    watcher(watching, false);
                watching = watched ? entry.index : -1;
                watcher = watched ? row.rowWatcher : null;
                if (watching >= 0)
                    watcher(watching, true);
            }
            onWatchedChanged: rewatch()
            onIndexChanged: rewatch()
            Connections {
                target: row
                function onRowWatcherChanged() {
                    entry.rewatch();
                }
            }
            Component.onCompleted: rewatch()
            Component.onDestruction: if (watching >= 0 && watcher)
                watcher(watching, false)

            required property int index
            required property var model

            // Whether the entry passes the search. One that does not is folded to no height and not drawn; its `visible`
            // is left to the list, which hides the entries of a closed one.
            readonly property bool matching: selector.matches(text)
            readonly property string groupTitle: row.groupRole !== "" ? entry.model[row.groupRole] : ""
            readonly property real titleHeight: matching && groupTitle !== "" && selector.groupOpeners.has(entry.index) ? EaStyle.Sizes.comboBoxHeight : 0

            width: entry.parent !== null ? entry.parent.width : 0
            height: matching ? EaStyle.Sizes.comboBoxHeight + titleHeight : 0
            opacity: matching ? 1 : 0
            // The base's padding of 16 on every side leaves a content area of no height in a row this tall; its
            // Label draws past that, but a clipped line would show nothing, so the line gets the row's full height
            // (edi ADR-0017 §10).
            topPadding: titleHeight
            topInset: titleHeight
            bottomPadding: 0
            highlighted: selector.highlightedIndex === entry.index
            hoverEnabled: selector.hoverEnabled
            text: entry.model[selector.blocksTextRole]

            contentItem: Item {
                clip: true

                IconLine {
                    id: entryLine
                    anchors.verticalCenter: parent.verticalCenter
                    segments: selector.segments(entry.index, entry.text, EaStyle.Colors.themeForeground, row.outcomeRole !== "" ? entry.model[row.outcomeRole] : "", row.templateRole !== "" && entry.model[row.templateRole] === true, maximumWidth)
                    maximumWidth: Math.max(1, parent.width)
                    elide: row.lineFor ? Text.ElideLeft : Text.ElideMiddle
                }
            }
            Loader {
                active: entry.hovered && row.lineFor !== null && entryLine.fullWidth > entryLine.maximumWidth + 0.5
                anchors.fill: parent
                sourceComponent: Component {
                    EaElements.ToolTip {
                        text: entry.text
                        requested: entry.hovered
                    }
                }
            }
            // The title is no entry: it takes the clicks on it.
            Loader {
                active: entry.titleHeight > 0
                width: entry.width
                height: entry.titleHeight
                sourceComponent: Component {
                    MouseArea {
                        EaElements.Label {
                            objectName: row.objectName ? `${row.objectName}.group.${entry.index}` : ""
                            x: entry.leftPadding
                            width: parent.width - 2 * x
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideMiddle
                            font.family: EaStyle.Fonts.ptSansBold.name
                            font.styleName: "Bold"
                            color: EaStyle.Colors.themeForegroundMinor
                            text: entry.groupTitle
                        }
                    }
                }
            }
        }
    }

    // The previous and next buttons, on the right: the base's sidebar button, square, with the arrow icons Continue
    // uses. Held, they repeat at about the keyboard's rate, as the arrow keys do (Qt's button auto-repeat).
    EaElements.SideBarButton {
        id: up

        objectName: row.objectName ? `${row.objectName}.up` : ""
        width: EaStyle.Sizes.comboBoxHeight
        height: EaStyle.Sizes.comboBoxHeight
        spacing: 0
        enabled: row.blockIndex > 0
        fontIcon: "arrow-circle-up"
        ToolTip.text: row.blockKind === "experiment" ? qsTr("Previous experiment") : row.blockKind === "parameter" ? qsTr("Previous parameter") : row.blockKind === "run" ? qsTr("Previous run") : row.blockKind === "bank" ? qsTr("Previous experiment") : qsTr("Previous structure")
        autoRepeat: true
        autoRepeatDelay: 300
        autoRepeatInterval: 50
        onClicked: row.step(-1)
    }

    EaElements.SideBarButton {
        id: down

        objectName: row.objectName ? `${row.objectName}.down` : ""
        width: EaStyle.Sizes.comboBoxHeight
        height: EaStyle.Sizes.comboBoxHeight
        spacing: 0
        enabled: row.blockIndex >= 0 && row.blockIndex < selector.count - 1
        fontIcon: "arrow-circle-down"
        ToolTip.text: row.blockKind === "experiment" ? qsTr("Next experiment") : row.blockKind === "parameter" ? qsTr("Next parameter") : row.blockKind === "run" ? qsTr("Next run") : row.blockKind === "bank" ? qsTr("Next experiment") : qsTr("Next structure")
        autoRepeat: true
        autoRepeatDelay: 300
        autoRepeatInterval: 50
        onClicked: row.step(1)
    }
}
