// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The base's combo box with a search field at the top of its list when it holds more than `searchThreshold`
// entries (edi ADR-0017 §7): every combo box that lists project items (blocks, parameters) or a long vocabulary
// (atom types, space groups) is one of these. The field filters the list by any part of an entry's text, ignoring
// case and spaces; Enter picks the entry spelled as typed, else the first entry left. The typed text is red while
// it matches no entry, in every such combo box (the owner, 2026-10-06). The list is the base's own popup, with the
// field as its list's header. A delegate folds itself away while it does not match, through `matches`: the base's
// own delegate does so here, and a combo box that brings its own delegate binds its height and opacity the same
// way.
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
    function positionPopup(opening) { ApplicationInfo.searchPositionPopup(opening); }
    // In a table, as wide as its widest option (or what it shows), a small gap and the arrow, the arrow right after
    // the text (the owner, 2026-10-27); a wider column keeps the space after it.
    readonly property real fittedWidth: ApplicationInfo.searchMeasuredWidth(false)
    readonly property real optionWidth: ApplicationInfo.searchMeasuredWidth(true)
    FontMetrics {
        id: optionMetrics
        font.family: control.listFontFamily
        font.pixelSize: control.font.pixelSize
    }
    // The family the list's entries are drawn in: the box's own, unless its entries need characters only another
    // bundled font has (the Wyckoff positions' fractions; never a platform fallback).
    property string listFontFamily: font.family
    popup.width: inTable ? Math.min(Math.max(width, optionWidth), Math.max(width, control.Window.width - popup.leftMargin - popup.rightMargin)) : width
    readonly property bool searchable: count > searchThreshold
    property string searchText: ""
    readonly property string filter: searchable ? control.folded(searchText) : ""
    // Some entry matches the search (true while there is none).
    readonly property bool anyMatch: ApplicationInfo.searchAnyMatch()

    // The form a search compares: lower case, without spaces ("P 1 21/c 1" and "p121/c1" are one).
    function folded(text) { return ApplicationInfo.searchFolded(text); }
    // The list opens below the box, or above it where there is more room, never over it, so the box keeps
    // showing its value while one searches; it is as tall as its entries or the room allows, and keeps that
    // height while a search shortens it. A list wider than the box is moved left where it would pass the
    // window's right edge.
    function placePopup(opening) { ApplicationInfo.searchPlacePopup(opening); }
    // Whether an entry's text matches the search.
    function matches(text) { return ApplicationInfo.searchMatches(text); }
    // The entry Enter picks: the one spelled as typed, else the first that matches; -1 when none does.
    function pickedIndex() { return ApplicationInfo.searchPickedIndex(); }

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
            height: control.searchable ? field.implicitHeight : 0
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
                anchors.fill: parent
                horizontalAlignment: TextInput.AlignLeft
                placeholderText: qsTr("Search")
                // Red while the text matches no entry, until it does.
                warned: !control.anyMatch
                onTextChanged: control.searchText = text
                onAccepted: ApplicationInfo.searchAccepted()
            }
        }
    }

    Component.onCompleted: ApplicationInfo.searchCompleted(
        () => { control.contentItemLabel.horizontalAlignment = Qt.binding(() => control.inTable ? control.horizontalAlignment : Text.AlignLeft); },
        () => { control.popup.contentItem.model = Qt.binding(() => control.popup.visible ? control.delegateModel : null); },
        () => { control.popup.focus = Qt.binding(() => control.searchable); })

    Timer {
        id: popupLayout
        interval: 0
        property var opening: null
        property var request: null
        function schedule(original) { ApplicationInfo.searchSchedule(original); }
        onTriggered: ApplicationInfo.searchTriggered()
    }
    Connections {
        target: control.popup
        function onAboutToShow() { ApplicationInfo.searchAboutToShow(); }
        function onAboutToHide() { ApplicationInfo.searchAboutToHide(); }
        function onOpened() { ApplicationInfo.searchOpened(); }
    }
}
