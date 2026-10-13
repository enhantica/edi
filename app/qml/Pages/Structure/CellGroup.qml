// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `cell` (easydiffractionbeta Pages/Model/SideBarBasic/Cell.qml): the six cell parameters in one row.
EaElements.GroupRow {
    id: row
    spacing: AppSizes.inputSpacing

    property StructureViewModel structure: null
    readonly property CellViewModel cell: structure ? structure.cell : null

    ParameterField {
        objectName: "cell.length_a"
        item: row.cell ? row.cell.lengthA : null
        label: "a"
    }
    ParameterField {
        objectName: "cell.length_b"
        item: row.cell ? row.cell.lengthB : null
        label: "b"
    }
    ParameterField {
        objectName: "cell.length_c"
        item: row.cell ? row.cell.lengthC : null
        label: "c"
    }
    ParameterField {
        objectName: "cell.angle_alpha"
        item: row.cell ? row.cell.angleAlpha : null
        label: "α"
    }
    ParameterField {
        objectName: "cell.angle_beta"
        item: row.cell ? row.cell.angleBeta : null
        label: "β"
    }
    ParameterField {
        objectName: "cell.angle_gamma"
        item: row.cell ? row.cell.angleGamma : null
        label: "γ"
    }
}
