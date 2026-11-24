// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// `cell` (easydiffractionbeta Pages/Model/SideBarBasic/Cell.qml): the six cell parameters in one row, or three and
// three where one row would crop a value (AppSizes.fieldColumns; the owner, 2026-11-23).
Grid {
    id: row
    columns: AppSizes.fieldColumns(6, 6, EaStyle.Sizes.sideBarContentWidth, columnSpacing, "deg")
    columnSpacing: AppSizes.inputSpacing
    rowSpacing: AppSizes.groupContentSpacing
    readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - (columns - 1) * columnSpacing) / columns

    property StructureViewModel structure: null
    readonly property CellViewModel cell: structure ? structure.cell : null

    ParameterField {
        width: row.fieldWidth
        objectName: "cell.length_a"
        item: row.cell ? row.cell.lengthA : null
        label: "a"
    }
    ParameterField {
        width: row.fieldWidth
        objectName: "cell.length_b"
        item: row.cell ? row.cell.lengthB : null
        label: "b"
    }
    ParameterField {
        width: row.fieldWidth
        objectName: "cell.length_c"
        item: row.cell ? row.cell.lengthC : null
        label: "c"
    }
    ParameterField {
        width: row.fieldWidth
        objectName: "cell.angle_alpha"
        item: row.cell ? row.cell.angleAlpha : null
        label: "α"
    }
    ParameterField {
        width: row.fieldWidth
        objectName: "cell.angle_beta"
        item: row.cell ? row.cell.angleBeta : null
        label: "β"
    }
    ParameterField {
        width: row.fieldWidth
        objectName: "cell.angle_gamma"
        item: row.cell ? row.cell.angleGamma : null
        label: "γ"
    }
}
