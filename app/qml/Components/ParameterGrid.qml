// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A category's shown parameter fields laid out as the original's GroupRows: up to `maxColumns`
// fields a row, each named `<prefix>.<edi item name>`. With
// `fillRows` the fields share each row evenly instead (the original's Diffractometer group;
// note 4): the fewest rows of at most `maxColumns`, and as many columns as fill them, so two constant-
// wavelength instrument fields take half the row each and four a quarter. A field the profile does not use
// (shown by the core because it is free) is not shown here: it stays in the Analysis table, where it can be
// fixed (edi ADR-0017 §5; the base Grid skips a hidden item, so the others close up).
Grid {
    id: grid

    property ParameterListModel fields: null
    property string prefix: ""
    property int maxColumns: 5
    property bool fillRows: false
    // A field's label in place of its symbol, by `.edi` item name (the instrument's "Wavelength 1").
    property var labels: ({})
    // A field's hover hint, by `.edi` item name.
    property var hints: ({})

    readonly property int fieldCount: fields ? fields.usedCount : 0

    // At most `maxColumns` (fewer to fill the rows evenly), and fewer still where a field would be too narrow for its
    // value at four significant digits (AppSizes.fieldColumns).
    readonly property int widestColumns: fillRows && fieldCount > 0 ? Math.ceil(fieldCount / Math.ceil(fieldCount / maxColumns)) : maxColumns
    // The widest unit its fields show (the peak widths' deg²).
    property string widestUnit: "deg\u00b2"
    // A group's grids share one column count (sharedColumns, set by the group), so its fields line up row under row
    // ("one grid per group").
    property int sharedColumns: 0
    columns: sharedColumns > 0 ? sharedColumns : AppSizes.fieldColumns(Math.max(1, fieldCount), widestColumns, EaStyle.Sizes.sideBarContentWidth, columnSpacing, widestUnit)
    columnSpacing: AppSizes.inputSpacing
    rowSpacing: AppSizes.groupContentSpacing

    Repeater {
        // The fields through a mirror: another block's fields of the same kind (the next experiment's) keep the
        // fields made for the last one, each reading its new row (ADR-0102 rule 2).
        model: ListModelMirror {
            source: grid.fields
        }
        delegate: ParameterField {
            required property var model

            objectName: `${grid.prefix}.${model.name}`
            item: model.parameter
            visible: model.usedByProfile
            label: grid.labels[model.name] ?? model.shortName
            hint: grid.hints[model.name] ?? ""
            width: (EaStyle.Sizes.sideBarContentWidth - (grid.columns - 1) * grid.columnSpacing) / grid.columns
        }
    }
}
