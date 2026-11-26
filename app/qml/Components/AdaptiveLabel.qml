// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A fixed label in the widest of its forms that fits its width: the long text, else the short one, else its icon alone
// (the label registry, app/data/labels.tsv). It is never cut; while it shows another form, its tooltip holds the long
// text. The forms' widths come from the font alone, so a table can reserve a column for a label before it is made.
EaComponents.ListViewLabel {
    id: label

    // The registry row, and the token its forms depend on (an ADP's type). A caller may give the forms itself instead.
    property string key: ""
    property string variant: ""
    readonly property var forms: key !== "" ? Session.labelForms(key, variant) : ({})
    property string longText: forms.long ?? ""
    property string shortText: forms.short ?? ""
    property string icon: forms.icon ?? ""

    // Each form's width with the label's padding; a missing form takes the next wider one's.
    readonly property real longWidth: Math.ceil(longMetrics.advanceWidth) + leftPadding + rightPadding
    readonly property real shortWidth: shortText !== "" ? Math.ceil(shortMetrics.advanceWidth) + leftPadding + rightPadding : longWidth
    readonly property real iconWidth: icon !== "" ? Math.ceil(iconGlyph.implicitWidth) + leftPadding + rightPadding : shortWidth

    // The form shown in `room` pixels: "long", "short" or "icon". With room for none, the narrowest there is.
    function formFor(room: real): string {
        if (longWidth <= room + 0.5)
            return "long";
        if (shortText !== "" && shortWidth <= room + 0.5)
            return "short";
        if (icon !== "")
            return "icon";
        return shortText !== "" ? "short" : "long";
    }
    // The form is chosen on the next turn after the width or the forms change, never inside that change: a label whose
    // width follows its text would otherwise choose again from the width its text gave, without end. Such a label settles
    // on the long form.
    property string form: "long"
    function choose() {
        form = width > 0 ? formFor(width) : "long";
    }
    onWidthChanged: Qt.callLater(choose)
    onLongWidthChanged: Qt.callLater(choose)
    onShortWidthChanged: Qt.callLater(choose)
    onIconWidthChanged: Qt.callLater(choose)
    Component.onCompleted: choose()

    text: form === "long" ? longText : form === "short" ? shortText : ""
    fullText: longText
    shortened: form !== "long"
    elide: Text.ElideNone

    TextMetrics {
        id: longMetrics
        font: label.font
        text: label.longText
    }
    TextMetrics {
        id: shortMetrics
        font: label.font
        text: label.shortText
    }
    // The icon in the label's place and colour, drawn only while it is the form shown.
    Text {
        id: iconGlyph
        visible: label.form === "icon"
        anchors.verticalCenter: parent.verticalCenter
        x: label.horizontalAlignment === Text.AlignLeft ? label.leftPadding : label.horizontalAlignment === Text.AlignRight ? label.width - label.rightPadding - width : (label.width - width) / 2
        font.family: EaStyle.Fonts.iconsFamily
        font.pixelSize: label.font.pixelSize
        color: label.color
        text: label.icon
    }
}
