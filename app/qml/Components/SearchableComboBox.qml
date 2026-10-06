// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

// The base's combo box with a search field at the top of its list when it holds more than `searchThreshold`
// entries (edi ADR-0017 §7): every combo box that lists project items (blocks, parameters) is one of these. The
// field filters the list by any part of an entry's text, ignoring case; Enter picks the first entry left. The
// list is the base's own popup, with the field as its list's header. A delegate folds itself away while it does
// not match, through `matches`: the base's own delegate does so here, and a combo box that brings its own
// delegate binds its height and opacity the same way.
EaElements.ComboBox {
    id: control

    property int searchThreshold: 10
    readonly property bool searchable: count > searchThreshold
    property string searchText: ""
    readonly property string filter: searchable ? searchText.trim().toLowerCase() : ""

    // Whether an entry's text matches the search.
    function matches(text) {
        return filter === "" || String(text).toLowerCase().includes(filter);
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
        font.family: control.font.family
        textFormat: control.textFormat
        elide: control.elide
        text: control.textRole ? (Array.isArray(control.model) ? entry.model.modelData[control.textRole] : entry.model[control.textRole]) : entry.model.modelData
        highlighted: control.highlightedIndex === entry.index
        hoverEnabled: control.hoverEnabled
    }

    // The search field, the header of the base popup's list.
    Component {
        id: searchHeader

        EaElements.TextField {
            objectName: "comboBox.search"
            width: ListView.view ? ListView.view.width : 0
            height: control.searchable ? implicitHeight : 0
            visible: control.searchable
            horizontalAlignment: TextInput.AlignLeft
            placeholderText: qsTr("Search")
            onTextChanged: control.searchText = text
            // Enter picks the first entry the search leaves.
            onAccepted: {
                for (let i = 0; i < control.count; ++i) {
                    if (control.matches(control.textAt(i))) {
                        control.currentIndex = i;
                        control.activated(i);
                        control.popup.close();
                        return;
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        control.popup.contentItem.header = searchHeader;
        // The field takes the keyboard while the list is open.
        control.popup.focus = Qt.binding(() => control.searchable);
    }

    Connections {
        target: control.popup
        function onAboutToShow() {
            const field = (control.popup.contentItem as ListView)?.headerItem;
            if (field)
                field.clear();
            control.searchText = "";
        }
        function onOpened() {
            const field = (control.popup.contentItem as ListView)?.headerItem;
            if (field && control.searchable)
                field.forceActiveFocus();
        }
    }
}
