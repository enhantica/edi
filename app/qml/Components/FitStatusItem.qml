// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

import edi.app

// One item of the status bar's fit area, as the bar's other items look (StatusBarItem: an icon, the key while the bar
// has room for every key, the value; the owner, 2026-10-13), its value's digits in fixed-width cells (DigitText). A
// framed item is a button: the fit status and the status bar's fit buttons (the owner, 2026-10-26), with one padding
// and its icon and word centred in the frame.
Control {
    id: control

    property string keyIcon: ""
    property string keyText: ""
    property string valueText: ""
    property color iconColor: EaStyle.Colors.statusBarIconForeground
    property color valueColor: EaStyle.Colors.themeForeground
    // The key is shown only while every item of the bar fits with its key (StatusBar.keysFit).
    property bool showKey: true
    property bool clickable: false
    // A framed item shows its frame all the time, as a button: `frameColor`, and `frameHoverColor` while a clickable one
    // is hovered. With `tintsOnHover` its icon and word turn the accent on hover instead. An `outlined` frame has a 1 px
    // `frameBorderColor` border outside its body, so every button's body is `frameHeight` tall (the owner, 2026-10-26).
    property bool framed: false
    property color frameColor: AppColors.statusButtonBackground
    property color frameHoverColor: frameColor
    property color frameBorderColor: AppColors.statusButtonBorder
    property bool tintsOnHover: true
    property bool outlined: true
    readonly property bool hoverTinted: framed && tintsOnHover && clickable && hover.hovered
    // A framed item's word, which one that `dropsWord` gives up while the bar is short of room (`showWord` false),
    // before the Fit button gives up its own (the owner, 2026-10-26).
    property bool showWord: true
    property bool dropsWord: false
    property bool shown: valueText !== ""
    // The hover frame's height, which the fit's progress bar shares (the owner, 2026-10-13): two font sizes, so a
    // framed item that shows its icon alone is a circle (the owner, 2026-10-26).
    readonly property real frameHeight: Math.round(font.pixelSize * 2)
    readonly property bool wordShown: framed && (showWord || !dropsWord)
    readonly property bool iconOnly: framed && !wordShown
    // A framed item's padding before its icon and after its word.
    readonly property real sidePadding: Math.round(font.pixelSize * 0.5)
    readonly property real afterWordPadding: Math.round(font.pixelSize * 0.65)
    // The item's width with its key shown, whether or not it is, and with its icon and value only: what the bar
    // measures. A framed item has no key; its word goes in the compact width unless it drops it, when it is a circle.
    readonly property real valueWidth: framed ? word.implicitWidth : value.implicitWidth
    readonly property real labelledWidth: framed ? iconLabel.implicitWidth + contentRow.spacing + word.implicitWidth + sidePadding + afterWordPadding : iconLabel.implicitWidth + keyLabel.implicitWidth + valueWidth + 2 * contentRow.spacing + leftPadding + rightPadding
    readonly property real compactWidth: !framed ? iconLabel.implicitWidth + valueWidth + contentRow.spacing + leftPadding + rightPadding : dropsWord ? frameHeight : iconLabel.implicitWidth + valueWidth + contentRow.spacing + sidePadding + afterWordPadding
    signal clicked

    visible: shown
    anchors.verticalCenter: parent ? parent.verticalCenter : undefined
    // Whole pixels, so the fit area's items, the round buttons among them, sit on the pixel grid.
    implicitWidth: Math.ceil(Math.max(implicitBackgroundWidth + leftInset + rightInset, implicitContentWidth + leftPadding + rightPadding))
    padding: 0
    // A clickable or framed item keeps its frame clear of its icon and text (the owner, 2026-10-13). A framed one has
    // less space between its icon and word and more after the word, so the three look even, and with its icon alone it
    // is as wide as it is tall, the icon centred (the owner, 2026-10-26).
    leftPadding: iconOnly ? (frameHeight - iconLabel.implicitWidth) / 2 : clickable || framed ? sidePadding : 0
    rightPadding: iconOnly ? leftPadding : wordShown ? afterWordPadding : leftPadding
    font.family: EaStyle.Fonts.fontFamily
    font.pixelSize: EaStyle.Sizes.fontPixelSize

    contentItem: Row {
        id: contentRow
        spacing: control.framed ? Math.round(control.font.pixelSize * 0.4) : control.font.pixelSize * 0.5

        EaElements.Label {
            id: iconLabel
            anchors.verticalCenter: parent.verticalCenter
            height: font.pixelSize
            verticalAlignment: Text.AlignVCenter
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: control.font.pixelSize
            color: control.hoverTinted ? EaStyle.Colors.themeAccent : control.iconColor
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: control.keyIcon
        }
        EaElements.Label {
            id: keyLabel
            visible: control.showKey && !control.framed
            anchors.verticalCenter: parent.verticalCenter
            height: font.pixelSize
            verticalAlignment: Text.AlignVCenter
            font.family: control.font.family
            font.pixelSize: control.font.pixelSize
            color: EaStyle.Colors.statusBarTextForeground
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: control.keyText
        }
        DigitText {
            id: value
            objectName: "statusBar.fit.value"
            visible: !control.framed
            anchors.verticalCenter: parent.verticalCenter
            font: control.font
            color: control.valueColor
            text: control.valueText
        }
        // A framed item's word, a plain label centred as its icon is: DigitText sets its digits on the font's
        // ascent, which leaves a word a pixel low in the frame.
        EaElements.Label {
            id: word
            visible: control.wordShown
            anchors.verticalCenter: parent.verticalCenter
            font: control.font
            color: control.hoverTinted ? EaStyle.Colors.themeAccent : control.valueColor
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            text: control.valueText
        }
    }

    // A clickable item highlights on hover, as the bar's Messages item does; a framed one is a pill as tall as the
    // progress bar.
    background: Item {
        Rectangle {
            readonly property int outline: control.framed && control.outlined ? 1 : 0

            anchors.verticalCenter: parent.verticalCenter
            x: -outline
            width: parent.width + 2 * outline
            height: control.frameHeight + 2 * outline
            radius: control.framed ? height / 2 : 2
            visible: control.framed || (control.clickable && hover.hovered)
            color: !control.framed ? AppColors.hoverHighlight : control.clickable && hover.hovered ? control.frameHoverColor : control.frameColor
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            border.width: outline
            border.color: control.frameBorderColor
        }
    }

    HoverHandler {
        id: hover
        cursorShape: control.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: control.clickable
        onTapped: control.clicked()
    }

    EaElements.ToolTip {
        text: control.ToolTip.text
        visible: text !== "" && hover.hovered && EaGlobals.Vars.showToolTips
    }
}
