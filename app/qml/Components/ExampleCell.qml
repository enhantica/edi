// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A table cell of three lines, as the Examples list draws an example: the title, its tag chips in their tones
// (app/examples/tags.json) and a grey one-line description, each cut short with a tooltip giving it whole. The
// Tutorials list draws its rows with the same cell.
Item {
    id: cell

    property string title: ""
    property list<string> tagLabels: []
    property list<string> tagIcons: []
    property list<string> tagColors: []
    property list<string> tagDarkColors: []
    property string detail: ""

    Column {
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        spacing: EaStyle.Sizes.fontPixelSize * 0.25
        EaElements.Label {
            id: identityLabel
            width: parent.width
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            textFormat: Text.PlainText
            // PT Sans lacks several subscript digits; one bundled face keeps formula weights uniform. Regular
            // weight: only Noto Sans Regular is bundled, and a synthesised bold showed in the browser and on
            // Linux where macOS draws the regular face (the owner, 2026-10-13).
            font.family: "Noto Sans"
            text: cell.title
        }
        Item {
            width: parent.width
            height: EaStyle.Sizes.fontPixelSize * 1.65
            clip: true
            Row {
                id: tagRow
                spacing: AppSizes.fieldSpacing / 2
                Repeater {
                    model: cell.tagLabels
                    delegate: Rectangle {
                        id: badge
                        required property string modelData
                        required property int index
                        readonly property color ink: EaStyle.Colors.isDarkPalette ? cell.tagDarkColors[index] : cell.tagColors[index]
                        radius: 3
                        color: Qt.rgba(ink.r, ink.g, ink.b, 0.13)
                        width: badgeContent.implicitWidth + 2 * AppSizes.fieldSpacing
                        height: EaStyle.Sizes.fontPixelSize * 1.65
                        Row {
                            id: badgeContent
                            anchors.centerIn: parent
                            spacing: AppSizes.fieldSpacing / 2
                            EaElements.Label {
                                visible: text !== ""
                                anchors.verticalCenter: parent.verticalCenter
                                font.family: EaStyle.Fonts.iconsFamily
                                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.8
                                color: badge.ink
                                text: cell.tagIcons[badge.index] ?? ""
                            }
                            EaElements.Label {
                                anchors.verticalCenter: parent.verticalCenter
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.9
                                color: badge.ink
                                text: badge.modelData
                            }
                        }
                    }
                }
            }
        }
        EaElements.Label {
            id: detailLabel
            width: parent.width
            horizontalAlignment: Text.AlignLeft
            elide: Text.ElideRight
            textFormat: Text.PlainText
            color: EaStyle.Colors.themeForegroundMinor
            text: cell.detail
        }
    }
    HoverHandler {
        id: hover
    }
    EaElements.ToolTip {
        requested: hover.hovered
        text: [identityLabel.truncated ? identityLabel.text : "", tagRow.width > cell.width ? cell.tagLabels.join(", ") : "", detailLabel.truncated ? cell.detail : ""].filter(line => line !== "").join("\n")
    }
}
