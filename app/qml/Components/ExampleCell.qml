// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A table cell of three lines, as the Examples list draws an example: the title, its tag chips in their tones
// (app/examples/tags.json) and a grey description, each on as many lines as it needs. The
// Tutorials list draws its rows with the same cell.
Item {
    id: cell

    property string title: ""
    property list<string> tagLabels: []
    property list<string> tagIcons: []
    property list<string> tagColors: []
    property list<string> tagDarkColors: []
    property string detail: ""
    // The description on as many lines as it needs, never cut short: a fixed text is not cut (N1, the owner's contract,
    // 2026-11-23); the row grows with it.
    property bool wrapDetail: true

    // Its lines' height, tags wrapped included, for a row sized by its content.
    implicitHeight: content.implicitHeight

    Column {
        id: content
        // The cell margin every text cell has: the table pads only cells that are one text (T1).
        x: AppSizes.tableCellMargin
        anchors.verticalCenter: parent.verticalCenter
        width: Math.max(0, parent.width - 2 * x)
        spacing: EaStyle.Sizes.fontPixelSize * 0.25
        EaElements.Label {
            id: identityLabel
            width: parent.width
            horizontalAlignment: Text.AlignLeft
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            // PT Sans lacks several subscript digits; one bundled face keeps formula weights uniform. Regular
            // weight: only Noto Sans Regular is bundled, and a synthesised bold showed in the browser and on
            // Linux where macOS draws the regular face (the owner, 2026-10-13).
            font.family: "Noto Sans"
            text: cell.title
        }
        // The tags on one line when they fit, else on the next ones, never cut short: the list sizes itself for the
        // widest row (TagRowsWidth).
        Flow {
            id: tagRow
            width: parent.width
            spacing: AppSizes.fieldSpacing / 2
            Repeater {
                model: cell.tagLabels
                delegate: TagChip {
                    required property string modelData
                    required property int index
                    ink: EaStyle.Colors.isDarkPalette ? cell.tagDarkColors[index] : cell.tagColors[index]
                    icon: cell.tagIcons[index] ?? ""
                    label: modelData
                }
            }
        }
        EaElements.Label {
            id: detailLabel
            width: parent.width
            horizontalAlignment: Text.AlignLeft
            elide: cell.wrapDetail ? Text.ElideNone : Text.ElideRight
            wrapMode: cell.wrapDetail ? Text.WordWrap : Text.NoWrap
            textFormat: Text.PlainText
            color: EaStyle.Colors.themeForegroundMinor
            text: cell.detail
        }
    }
    HoverHandler {
        id: hover
    }
    EaElements.ToolTip {
        // The cut-short text in full: data, shown whatever the tooltip level.
        data: true
        requested: hover.hovered
        text: [identityLabel.truncated ? identityLabel.text : "", detailLabel.truncated ? cell.detail : ""].filter(line => line !== "").join("\n")
    }
}
