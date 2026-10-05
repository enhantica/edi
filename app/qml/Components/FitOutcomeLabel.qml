// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A fit outcome as an icon and a word in the outcome's colour (FitOutcomes), with no underline. A clickable one
// highlights on hover, as the status bar's Messages item does, and emits `clicked`.
Item {
    id: label

    property string outcome: ""
    property bool clickable: false
    property real pixelSize: EaStyle.Sizes.fontPixelSize
    property string toolTipText: ""
    signal clicked

    implicitWidth: line.implicitWidth
    implicitHeight: line.implicitHeight

    Rectangle {
        anchors.fill: parent
        anchors.margins: -label.pixelSize * 0.25
        radius: 2
        visible: label.clickable && hover.hovered
        color: AppColors.hoverHighlight
    }

    IconLine {
        id: line
        pixelSize: label.pixelSize
        segments: [
            {
                "icon": FitOutcomes.icon(label.outcome),
                "color": FitOutcomes.color(label.outcome)
            },
            {
                "text": FitOutcomes.word(label.outcome),
                "color": FitOutcomes.color(label.outcome)
            }
        ]
    }

    HoverHandler {
        id: hover
        cursorShape: label.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: label.clickable
        onTapped: label.clicked()
    }

    EaElements.ToolTip {
        text: label.toolTipText
        visible: text !== "" && hover.hovered && EaGlobals.Vars.showToolTips
    }
}
