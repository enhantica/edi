// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import EasyApplication.Gui.Style as EaStyle
import edi.app

// The microphone level while voice input listens (edi ADR-0107): a row of dots that rise into bars with the voice and
// move from right to left. With animations off the dots do not move; they light from the left with the current level.
Item {
    id: meter
    property real level: 0
    property bool running: false
    property color color: EaStyle.Colors.themeAccent
    readonly property int count: 16
    readonly property bool animated: EaStyle.Times.translationChange > 0
    readonly property real dot: Math.max(2, Math.round(AppSizes.unit * 0.15))
    property var history: []
    function clear() {
        history = new Array(count).fill(0);
    }
    implicitWidth: count * dot + (count - 1) * bars.spacing
    implicitHeight: AppSizes.unit
    Accessible.ignored: true
    onRunningChanged: clear()
    Component.onCompleted: clear()
    Timer {
        interval: 70
        repeat: true
        running: meter.running && meter.animated && meter.visible
        onTriggered: meter.history = meter.history.slice(1).concat([meter.level])
    }
    Row {
        id: bars
        anchors.centerIn: parent
        height: meter.height
        spacing: meter.dot * 2
        Repeater {
            model: meter.count
            delegate: Rectangle {
                required property int index
                readonly property real value: meter.animated ? (meter.history[index] ?? 0) : index < Math.round(meter.level * meter.count) ? 0.6 : 0
                anchors.verticalCenter: parent.verticalCenter
                width: meter.dot
                height: Math.max(meter.dot, Math.round(value * meter.height))
                radius: width / 2
                color: meter.color
                opacity: value > 0.05 ? 1 : 0.5
            }
        }
    }
}
