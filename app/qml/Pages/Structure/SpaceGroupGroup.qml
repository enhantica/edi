// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `space_group` (easydiffractionbeta Pages/Model/SideBarBasic/SpaceGroup.qml): the crystal system,
// derived through crysta, then the editable setting — IT number, Hermann–Mauguin name, coordinate
// system code.
EaElements.GroupRow {
    id: row

    property StructureViewModel structure: null
    readonly property SpaceGroupViewModel spaceGroup: structure ? structure.spaceGroup : null

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
        clearable: true
        onCommitted: text => row.spaceGroup.itNumber = text === "" ? 0 : Number(text)
    }
    ValueField {
        objectName: "spaceGroup.nameHM"
        label: qsTr("name")
        fieldValue: row.spaceGroup ? row.spaceGroup.nameHM : ""
        onCommitted: text => row.spaceGroup.nameHM = text
    }
    ValueField {
        objectName: "spaceGroup.coordSystemCode"
        label: qsTr("code")
        fieldValue: row.spaceGroup ? row.spaceGroup.coordSystemCode : ""
        onCommitted: text => row.spaceGroup.coordSystemCode = text
    }
}
