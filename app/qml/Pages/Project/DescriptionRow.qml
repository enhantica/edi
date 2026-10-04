// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// One label/value row of the Description tab (the original's Row of a bold name column and a value).
Row {
    id: row

    property string label: ""
    default property alias content: value.data

    spacing: AppSizes.descriptionInnerSpacing

    EaElements.Label {
        width: AppSizes.descriptionNameColumnWidth
        // PT Sans Bold, by its own loader's family and its style, never by a weight (ADR-0015 §10).
        font.family: EaStyle.Fonts.ptSansBold.name
        font.styleName: "Bold"
        text: row.label
    }
    Item {
        id: value
        width: childrenRect.width
        height: childrenRect.height
    }
}
