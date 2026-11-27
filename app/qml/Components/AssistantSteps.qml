// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

// The finished steps between two replies of the assistant as one line: their icons in order and how many there are. A
// click shows or hides the steps; the model holds which are shown, so a reused row shows the right ones (edi ADR-0057).
Item {
    id: steps

    property var payload: null
    readonly property var icons: payload?.icons ?? []
    readonly property bool open: payload?.open === true
    signal toggled(string group, bool shown)

    implicitHeight: toggle.implicitHeight + AppSizes.unit * 0.5

    EaElements.Button {
        id: toggle

        objectName: "assistant.steps.toggle"
        y: AppSizes.unit * 0.25
        width: steps.width
        text: qsTr("%1 steps").arg(steps.icons.length)
        contentItem: Item {
            implicitHeight: line.implicitHeight
            IconLine {
                id: line
                anchors.verticalCenter: parent.verticalCenter
                maximumWidth: parent.width
                minimumTextWidth: parent.width
                textColor: EaStyle.Colors.themeForegroundMinor
                segments: steps.icons.map(key => ({
                            "icon": FitOutcomes.icon(key),
                            "color": FitOutcomes.color(key)
                        })).concat([
                    {
                        "text": toggle.text,
                        "elides": true
                    }
                ])
            }
        }
        ToolTip.text: steps.open ? qsTr("Hide the steps") : qsTr("Show the steps")
        Accessible.name: text
        Accessible.checkable: true
        Accessible.checked: steps.open
        Accessible.description: ToolTip.text
        onClicked: steps.toggled(steps.payload.group, !steps.open)
    }
}
