// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// How the current structure is described: by its atom sites, or by symmetry modes of a parent structure. Only atom
// sites can be chosen for now; Symmetry modes is listed, greyed, with a tooltip saying it is coming. Nothing is
// stored: the choice holds no model yet.
EaElements.ParamComboBox {
    id: selector

    readonly property var choices: [
        {
            "token": "atom_sites",
            "label": qsTr("Atom sites"),
            "available": true,
            "toolTip": qsTr("Describe the structure by its atom sites")
        },
        {
            "token": "symmetry_modes",
            "label": qsTr("Symmetry modes"),
            "available": false,
            "toolTip": qsTr("Coming soon: describe the structure by symmetry modes of a parent structure")
        }
    ]

    width: EaStyle.Sizes.sideBarContentWidth
    parameter: ({
            "value": "atom_sites",
            "shortPrettyName": qsTr("Description")
        })
    model: choices
    textRole: "label"
    valueRole: "token"
    currentIndex: 0
    ToolTip.text: qsTr("How the structure is described")
    Component.onCompleted: FieldTitles.align(selector)

    // The base box's right-click menu shows a `.edi` item's name; this choice is none.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
    }

    // An unavailable choice is greyed and cannot be taken, but still explains itself on hover: the hover is read by
    // the row around its item, which stays enabled.
    delegate: Item {
        id: entry

        required property int index
        required property var modelData

        objectName: `structureDescription.${modelData.token}`
        width: parent !== null ? parent.width : 0
        height: EaStyle.Sizes.comboBoxHeight

        EaElements.MenuItem {
            anchors.fill: parent
            enabled: entry.modelData.available
            font.family: selector.font.family
            text: entry.modelData.label
            highlighted: selector.highlightedIndex === entry.index
            hoverEnabled: selector.hoverEnabled
            onClicked: {
                selector.currentIndex = entry.index;
                selector.popup.close();
            }
        }
        HoverHandler {
            id: hover
        }
        EaElements.ToolTip {
            text: entry.modelData.toolTip
            requested: hover.hovered
        }
    }
}
