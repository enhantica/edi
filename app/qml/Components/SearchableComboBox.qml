// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQml.Models
import QtQuick.Templates as T

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The base's combo box with a search field at the top of its list when it holds more than `searchThreshold`
// entries (edi ADR-0017 §7): every combo box that lists project items (blocks, parameters) or a long vocabulary
// (atom types, space groups) is one of these. The field filters the list by any part of an entry's text, ignoring
// case and spaces. A typed search lists the entry spelled as typed first, then those starting with the text, then
// the others; Enter picks the entry spelled as typed, else the text itself when the box takes it as typed
// (`typedEntry`), else the first entry. While the text matches no entry and is not taken as typed it is red (the
// owner, 2026-10-06) and a line under it says so. The list is the base's own popup, with the field as its list's
// header. A delegate folds itself away while it does not match, through `matches`: the base's own delegate does so
// here, and a combo box that brings its own delegate binds its height and opacity the same way.
EaElements.ComboBox {
    id: control

    // A field's title above the box, drawn as the base's ParamComboBox draws its own and aligned as every
    // field's title (FieldTitles, edi ADR-0017 §5); none when empty.
    property string title: ""
    // In a table row: no border and no background, as the base's TableViewComboBox, which every other table
    // cell picker is (the owner, 2026-10-06).
    property bool inTable: false
    // Table cells declare the same alignment as their header.
    property int horizontalAlignment: Text.AlignHCenter
    property int searchThreshold: 10
    // Filters start with their current selection; a fully visible list starts at its first option.
    // A typed search starts at its first match.
    function positionPopup(opening) {
        if (filter === "")
            ApplicationInfo.searchPositionPopup(opening);
        else if (typedFilter === filter)
            (popup.contentItem as ListView)?.positionViewAtBeginning();
    }
    // In a table, as wide as what it shows (its value and any icons), a small gap and the arrow, the arrow right after
    // the value (the owner, 2026-10-27 and 2026-11-22); a longer option opens in the popup, which has its own width, and
    // a wider column keeps the space after the box. Plain text where the shown text has no markup: rich text cannot
    // elide, and a long name ran under the arrow; a name with markup (a coloured part) stays rich.
    textFormat: displayText.indexOf("<") >= 0 ? Text.RichText : Text.PlainText
    readonly property real fittedWidth: Math.ceil(Math.max(inTable ? 0 : widthMetrics.optionTextWidth, widthMetrics.displayTextWidth) + Math.max(contentItemLabel ? contentItemLabel.leftPadding + contentItemLabel.rightPadding : 0, contentItem ? contentItem.implicitWidth - widthMetrics.displayTextWidth : 0) + font.pixelSize * (inTable ? 0.45 : 0.5)) + leftPadding + rightPadding
    readonly property real optionWidth: Math.ceil(Math.max(widthMetrics.optionTextWidth, widthMetrics.displayTextWidth)) + font.pixelSize * 3
    ComboBoxMetrics {
        id: widthMetrics
        comboBox: control
        count: control.count
        textRole: control.textRole
        displayText: control.displayText
        font.family: control.listFontFamily
        font.pixelSize: control.font.pixelSize
    }
    // The family the list's entries are drawn in: the box's own, unless its entries need characters only another
    // bundled font has (the Wyckoff positions' fractions; never a platform fallback).
    property string listFontFamily: font.family
    popup.width: inTable ? Math.min(Math.max(width, optionWidth), Math.max(width, control.Window.width - popup.leftMargin - popup.rightMargin)) : width
    readonly property bool searchable: count > searchThreshold
    // What the list says when the search matches no entry.
    property string noMatchText: qsTr("No entry matches")
    property string searchText: ""
    // The search text when the box takes it as a value its list does not hold, else empty: set by a box whose
    // value need not be an entry (a site's type takes any isotope of a listed element). Enter then gives it to
    // typedAccepted, unless an entry is spelled as typed.
    property string typedEntry: ""
    property Item searchField: null
    readonly property string filter: searchable ? control.folded(searchText) : ""
    // Some entry matches the search, or the box takes it as typed (true while there is none).
    readonly property bool anyMatch: ApplicationInfo.searchAnyMatch()
    signal typedAccepted(string text)

    // The form a search compares: lower case, without spaces ("P 1 21/c 1" and "p121/c1" are one).
    function folded(text) {
        return ApplicationInfo.searchFolded(text);
    }
    // The list opens below the box, or above it where there is more room, never over it, so the box keeps
    // showing its value while one searches; it is as tall as its entries or the room allows, follows the entries a
    // search leaves, and stays on its side of the box meanwhile. A list wider than the box is moved left where it
    // would pass the window's right edge.
    function placePopup(opening) {
        ApplicationInfo.searchPlacePopup(opening);
        const extra = listExtra && control.Window.window ? listExtra() : 0;
        if (extra <= 0)
            return;
        // On the side it was placed, as far as that side has room.
        const top = control.mapToItem(null, 0, 0).y;
        if (popup.y < 0) {
            popup.height = Math.min(popup.height + extra, top - popup.topMargin);
            popup.y = -popup.height;
        } else {
            popup.height = Math.min(popup.height + extra, control.Window.window.height - top - height - popup.bottomMargin);
        }
    }
    // The height the list draws beyond one line per entry (its groups' titles), as a function; null for none.
    property var listExtra: null
    // Whether an entry's text matches the search.
    function matches(text) {
        return ApplicationInfo.searchMatches(text);
    }
    // The entry Enter picks: the one spelled as typed, else the first that starts with the text, else the first that
    // holds it; -1 when none does. A clicked entry of the ordered list comes the same way.
    function pickedIndex() {
        const clicked = clickedEntry;
        clickedEntry = -1;
        if (clicked >= 0)
            return clicked;
        if (groupOf === null || filter === "")
            return ApplicationInfo.searchPickedIndex();
        // A list in groups ranks within each group, so the best match need not be on top: Enter takes the top entry.
        const shown = shownRows();
        return shown.length > 0 ? shown[0] : -1;
    }
    property int clickedEntry: -1
    // A row's group, `groupOf(index)`, for a list drawn in groups; null for none. A typed search then ranks the entries
    // of each group apart and keeps the groups whole and in the list's order, so every entry stays under its title.
    property var groupOf: null
    // The model's rows the list shows, in the order it draws them.
    function shownRows() {
        const order = ordered !== null ? ordered.rows : Array.from({
            "length": count
        }, (_, row) => row);
        return filter === "" ? order : order.filter(row => matches(textAt(row)));
    }

    // The list in the order of a typed search, where that differs from the model's: the same entries through a model
    // of their own, as the box reads its choice by its own model's rows. Made by the first such search of an opening,
    // dropped with the list. Text set by the program leaves the model's order, which the assistant finds its row in.
    property var ordered: null
    property string typedFilter: ""
    // The model's rows as the search lists them; null when that is the model's own order.
    function searchOrder() {
        // One set of ranks per group, the groups in the order their first match comes.
        const groups = new Map();
        const others = [];
        for (let i = 0; i < count; ++i) {
            const text = folded(textAt(i));
            const rank = text === filter ? 0 : text.startsWith(filter) ? 1 : text.includes(filter) ? 2 : 3;
            if (rank === 3) {
                others.push(i);
                continue;
            }
            const group = groupOf !== null ? groupOf(i) : "";
            if (!groups.has(group))
                groups.set(group, [[], [], []]);
            groups.get(group)[rank].push(i);
        }
        let found = [];
        for (const ranks of groups.values())
            found = found.concat(ranks[0], ranks[1], ranks[2]);
        return found.every((row, at) => at === 0 || found[at - 1] < row) ? null : found.concat(others);
    }
    function orderEntries() {
        typedFilter = filter;
        const order = popup.visible && filter !== "" ? searchOrder() : null;
        if (order === null) {
            dropOrder();
            return;
        }
        if (ordered === null)
            ordered = orderedEntries.createObject(control);
        ordered.arrange(order);
        keepTyping();
    }
    function dropOrder() {
        const old = ordered;
        ordered = null;
        if (old !== null) {
            old.destroy();
            keepTyping();
        }
    }
    // The order belongs to the typed text only.
    function keepTypedOrder() {
        if (typedFilter !== filter)
            dropOrder();
    }
    // The model's own rows changed under an ordered list.
    function reorder() {
        if (ordered === null)
            return;
        dropOrder();
        if (typedFilter === filter)
            orderEntries();
    }
    onFilterChanged: {
        if (ordered !== null)
            Qt.callLater(control.keepTypedOrder);
        if (popupLayout.opening) {
            control.placePopup(popupLayout.opening);
            popupLayout.schedule(popupLayout.opening);
        }
    }
    // A list makes its first entry the current one, and gives it the keyboard, when its model changes. While one types
    // the field keeps the keyboard and the list has no current entry.
    function keepTyping() {
        const list = popup.contentItem as ListView;
        if (list === null || !popup.opened)
            return;
        list.currentIndex = -1;
        searchField?.forceActiveFocus();
    }
    Component {
        id: orderedEntries

        DelegateModel {
            id: entries

            // The model's row of each entry, as placed here.
            property var rows: []
            property bool arranging: false
            property bool ready: false

            function arrange(order) {
                arranging = true;
                // Arranged in a copy and set whole, so what reads the order (the groups' titles) hears of it.
                const placed = rows.slice();
                for (let to = 0; to < order.length; ++to) {
                    if (placed[to] === order[to])
                        continue;
                    const from = placed.indexOf(order[to], to);
                    let run = 1;
                    while (from + run < placed.length && placed[from + run] === order[to + run])
                        ++run;
                    entries.items.move(from, to, run);
                    placed.splice(to, 0, ...placed.splice(from, run));
                }
                rows = placed;
                arranging = false;
            }
            model: control.model
            delegate: control.delegate
            items.onChanged: if (ready && !arranging)
                Qt.callLater(control.reorder)
            // The box connects the clicks of its own model's entries only.
            onCreatedItem: (index, object) => {
                const button = object as T.AbstractButton;
                button?.clicked.connect(() => {
                    control.clickedEntry = entries.rows[button.DelegateModel.itemsIndex];
                    ApplicationInfo.searchAccepted();
                });
            }
            Component.onCompleted: {
                rows = Array.from({
                    "length": entries.items.count
                }, (_, row) => row);
                ready = true;
            }
        }
    }

    borderColor: inTable ? "transparent" : _borderColor()
    backgroundColor: inTable ? "transparent" : _backgroundColor()
    topInset: title === "" ? 0 : EaStyle.Sizes.fontPixelSize * 1.5
    topPadding: topInset + padding

    EaElements.Label {
        visible: control.title !== ""
        anchors.left: control.left
        anchors.leftMargin: FieldTitles.inset
        width: control.width - FieldTitles.inset
        elide: Text.ElideRight
        color: EaStyle.Colors.themeForegroundMinor
        text: control.title
    }

    delegate: EaElements.MenuItem {
        id: entry

        required property int index
        required property var model

        // Whether the entry passes the search; one that does not is folded to no height and not drawn.
        readonly property bool matching: control.matches(text)

        width: entry.parent !== null ? entry.parent.width : 0
        height: matching ? EaStyle.Sizes.comboBoxHeight : 0
        opacity: matching ? 1 : 0
        font.family: control.listFontFamily
        textFormat: control.textFormat
        elide: control.elide
        text: control.textRole ? (Array.isArray(control.model) ? entry.model.modelData[control.textRole] : entry.model[control.textRole]) : entry.model.modelData
        highlighted: control.highlightedIndex === entry.index
        hoverEnabled: control.hoverEnabled
    }

    // The search field, the header of the base popup's list: on the popup's own colour, so the entries the list
    // scrolls under it never show through, and above them.
    Component {
        id: searchHeader

        Rectangle {
            z: 2
            width: ListView.view ? ListView.view.width : 0
            height: control.searchable ? field.implicitHeight + (control.anyMatch ? 0 : noMatch.implicitHeight) : 0
            visible: control.searchable
            color: control.popupBackgroundColor

            function clear() {
                field.clear();
            }
            function focusField() {
                field.forceActiveFocus();
            }

            EaElements.TextField {
                id: field

                objectName: "comboBox.search"
                Component.onCompleted: control.searchField = field
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                horizontalAlignment: TextInput.AlignLeft
                placeholderText: qsTr("Search")
                // Red while the text matches no entry and is not taken as typed, until it is.
                warned: !control.anyMatch
                onTextChanged: control.searchText = text
                onTextEdited: {
                    // Told before the text itself is; the order is of what was typed.
                    control.searchText = text;
                    control.orderEntries();
                }
                onAccepted: ApplicationInfo.searchAccepted()
            }
            EaElements.Label {
                id: noMatch

                objectName: "comboBox.noMatch"
                anchors.top: field.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                padding: field.leftPadding
                visible: control.searchable && !control.anyMatch
                wrapMode: Text.WordWrap
                color: EaStyle.Colors.themeForegroundMinor
                text: control.noMatchText
            }
        }
    }

    // In a table the shown value starts where its column's header does (the owner, 2026-10-24) and at the box's left
    // edge, and the arrow sits in the padding kept for it: the base draws it over the end of the text's room (the
    // owner, 2026-10-27); the list keeps its own padding.
    Component.onCompleted: ApplicationInfo.searchCompleted(() => {
        control.contentItemLabel.horizontalAlignment = Qt.binding(() => control.inTable ? control.horizontalAlignment : Text.AlignLeft);
    }, () => {
        // A short list has no search field, and its header is not made: every box in a table row made one before.
        control.popup.contentItem.header = Qt.binding(() => control.searchable ? searchHeader : null);
        control.popup.contentItem.model = Qt.binding(() => control.popup.visible ? (control.ordered ?? control.delegateModel) : null);
    }, () => {
        control.popup.focus = Qt.binding(() => control.searchable);
    }, () => {
        control.indicator.x = Qt.binding(() => control.width - control.indicator.width - control.padding);
    })

    Timer {
        id: popupLayout
        interval: 0
        property var opening: null
        property var request: null
        function schedule(original) {
            ApplicationInfo.searchSchedule(original);
        }
        onTriggered: ApplicationInfo.searchTriggered()
    }
    Connections {
        target: control.popup
        function onAboutToShow() {
            ApplicationInfo.searchAboutToShow();
        }
        function onAboutToHide() {
            ApplicationInfo.searchAboutToHide();
        }
        function onOpened() {
            ApplicationInfo.searchOpened();
        }
        function onClosed() {
            control.dropOrder();
            control.popup.contentItem.currentIndex = Qt.binding(() => control.highlightedIndex);
            control.typedFilter = "";
        }
    }
}
