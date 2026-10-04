// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import EasyApplication.Gui.Elements as EaElements

// Every field's title the same way (edi ADR-0017 §5): the base's ParamTextField and ParamComboBox each draw
// their `shortPrettyName` as a label with no width, the text field's right-aligned, the combo box's inset from
// the left by its content label's padding. `align` sets them all as the combo box does — left, inset by the
// base combo box's own content padding (read from one here, never a number of edi's), as wide as the field
// less that inset, ending in "…" when longer — so no title runs past its field or over a neighbour. The
// vertical gap, font and colour are the base's and the same for both. The base names the label nowhere, so
// it is found as the field's child whose text is the name.
QtObject {
    id: titles

    // A base combo box, never shown, to read its content padding from.
    property EaElements.ComboBox probe: EaElements.ComboBox {}
    readonly property real inset: titles.probe.contentItemLabel ? titles.probe.contentItemLabel.leftPadding : 0

    function align(field) {
        for (let i = 0; i < field.children.length; ++i) {
            const child = field.children[i];
            if (child.text !== undefined && child.elide !== undefined && child.text === field.shortPrettyName && child.text !== "") {
                child.anchors.right = undefined;
                child.anchors.left = field.left;
                child.anchors.leftMargin = Qt.binding(() => titles.inset);
                child.rightPadding = 0;
                child.width = Qt.binding(() => field.width - titles.inset);
                child.elide = Text.ElideRight;
                return;
            }
        }
    }
}
