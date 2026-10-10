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

    readonly property int fieldCount: fields ? fields.usedCount : 0

    columns: fillRows && fieldCount > 0 ? Math.ceil(fieldCount / Math.ceil(fieldCount / maxColumns)) : maxColumns
    columnSpacing: AppSizes.inputSpacing
    rowSpacing: AppSizes.groupContentSpacing

    Repeater {
        model: grid.fields
        delegate: ParameterField {
            required property var model

            objectName: `${grid.prefix}.${model.name}`
            item: model.parameter
            visible: model.usedByProfile
            label: model.shortName
            width: (EaStyle.Sizes.sideBarContentWidth - (grid.columns - 1) * grid.columnSpacing) / grid.columns
        }
    }
}
