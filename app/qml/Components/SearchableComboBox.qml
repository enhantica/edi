// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material.impl
import QtQuick.Templates as T

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The base's combo box with a search field at the top of its list when it holds more than `searchThreshold`
// entries (edi ADR-0017 §7): every combo box that lists project items (blocks, parameters) is one of these. The
// field filters the list by any part of an entry's text, ignoring case; Enter picks the first entry left.
// A delegate of its own hides itself while it does not match, through `matches` (the list's attached view
// carries the filter): the base's own delegate does so here, and a combo box that brings its own delegate
// binds its `visible` the same way.
EaElements.ComboBox {
    id: control

    property int searchThreshold: 10
    readonly property bool searchable: count > searchThreshold
    readonly property string filter: searchable ? searchField.text.trim().toLowerCase() : ""

    // Whether an entry's text matches the search.
    function matches(text) {
        return filter === "" || String(text).toLowerCase().includes(filter);
    }

    delegate: EaElements.MenuItem {
        id: entry

        required property int index
        required property var model

        width: entry.parent !== null ? entry.parent.width : 0
        height: visible ? EaStyle.Sizes.comboBoxHeight : 0
        visible: control.matches(text)
        font.family: control.font.family
        textFormat: control.textFormat
        elide: control.elide
        text: control.textRole ? (Array.isArray(control.model) ? entry.model.modelData[control.textRole] : entry.model[control.textRole]) : entry.model.modelData
        highlighted: control.highlightedIndex === entry.index
        hoverEnabled: control.hoverEnabled
    }

    onActivated: searchField.clear()

    popup: T.Popup {
        y: 0
        width: control.width
        height: Math.min(contentItem.implicitHeight, control.Window.height - topMargin - bottomMargin)
        topMargin: EaStyle.Sizes.fontPixelSize
        bottomMargin: EaStyle.Sizes.fontPixelSize
        // The search field takes the keyboard while the list is open.
        focus: control.searchable

        onOpened: {
            searchField.clear();
            if (control.searchable)
                searchField.forceActiveFocus();
        }

        contentItem: Column {
            implicitHeight: (searchField.visible ? searchField.height : 0) + list.implicitHeight

            EaElements.TextField {
                id: searchField
                objectName: "comboBox.search"
                visible: control.searchable
                width: parent.width
                placeholderText: qsTr("Search")
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
            ListView {
                id: list
                width: parent.width
                height: Math.min(contentHeight, control.Window.height - control.popup.topMargin - control.popup.bottomMargin - (searchField.visible ? searchField.height : 0))
                implicitHeight: contentHeight
                clip: true
                model: control.delegateModel
                currentIndex: control.highlightedIndex
                highlightMoveDuration: 0

                T.ScrollIndicator.vertical: ScrollIndicator {}
            }
        }

        // The base's list background.
        background: Rectangle {
            radius: 2
            color: control.popupBackgroundColor
            layer.enabled: control.enabled
            layer.effect: ElevationEffect {
                elevation: 8
            }
        }
    }
}
