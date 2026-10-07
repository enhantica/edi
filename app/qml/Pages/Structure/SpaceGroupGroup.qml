// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `space_group` (easydiffractionbeta Pages/Model/SideBarBasic/SpaceGroup.qml): the crystal system,
// derived through crysta, then the editable setting — IT number, Hermann–Mauguin name, coordinate
// system code — which always agree with one another.
EaElements.GroupRow {
    id: row

    property StructureViewModel structure: null
    readonly property SpaceGroupViewModel spaceGroup: structure ? structure.spaceGroup : null
    // Four fields side by side, as the base sizes a row's fields.
    readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - 3 * EaStyle.Sizes.fontPixelSize * 0.5) / 4

    ValueField {
        objectName: "spaceGroup.crystalSystem"
        label: qsTr("crystal system")
        editable: false
        fieldValue: row.spaceGroup ? row.spaceGroup.crystalSystem : ""
    }
    ValueField {
        objectName: "spaceGroup.itNumber"
        label: qsTr("number")
        fieldValue: row.spaceGroup && row.spaceGroup.hasItNumber ? row.spaceGroup.itNumber : ""
        accepts: "integer"
        // The 230 space-group types (the owner, 2026-10-06).
        admits: text => /^\s*\d+\s*$/.test(text) && Number(text) >= 1 && Number(text) <= 230
        admitsRule: qsTr("A space-group number is a whole number from 1 to 230")
        clearable: true
        onCommitted: text => row.spaceGroup.itNumber = text === "" ? 0 : Number(text)
    }
    // The name and the code are picked from crysta's table or typed into the list's search field (the owner,
    // 2026-10-06); a new name or number takes that group's default setting, a new code that setting's name.
    SearchableComboBox {
        objectName: "spaceGroup.nameHM"
        width: row.fieldWidth
        title: qsTr("name")
        searchThreshold: 0
        model: row.spaceGroup ? row.spaceGroup.names : []
        currentIndex: row.spaceGroup ? row.spaceGroup.names.indexOf(row.spaceGroup.nameHM) : -1
        displayText: row.spaceGroup ? row.spaceGroup.nameHM : ""
        // The choice goes to the model; the box then follows the model's name again.
        onActivated: index => {
            row.spaceGroup.nameHM = textAt(index);
            currentIndex = Qt.binding(() => row.spaceGroup ? row.spaceGroup.names.indexOf(row.spaceGroup.nameHM) : -1);
        }
    }
    SearchableComboBox {
        objectName: "spaceGroup.coordSystemCode"
        width: row.fieldWidth
        title: qsTr("code")
        searchThreshold: 0
        enabled: count > 0
        model: row.spaceGroup ? row.spaceGroup.codes : []
        currentIndex: row.spaceGroup ? row.spaceGroup.codes.indexOf(row.spaceGroup.coordSystemCode) : -1
        displayText: row.spaceGroup ? row.spaceGroup.coordSystemCode : ""
        onActivated: index => {
            row.spaceGroup.coordSystemCode = textAt(index);
            currentIndex = Qt.binding(() => row.spaceGroup ? row.spaceGroup.codes.indexOf(row.spaceGroup.coordSystemCode) : -1);
        }
    }
}
