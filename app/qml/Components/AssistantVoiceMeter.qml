// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import EasyApplication.Gui.Style as EaStyle
import edi.app

// The voice input indicator (edi ADR-0107 §8): a row of dots with a gentle ripple running from right to left, so they
// never look frozen in silence. The voice raises them into bars that move the same way. While the speech is recognised
// the ripple is slower and smaller. With animations off the dots do not move; they light from the left with the level.
Item {
    id: meter
    property real level: 0
    property bool running: false
    property bool recognising: false
    property color color: EaStyle.Colors.themeAccent
    readonly property int count: 16
    readonly property bool animated: EaStyle.Times.translationChange > 0
    readonly property real dot: Math.max(2, Math.round(AppSizes.unit * 0.15))
    property var history: []
    // The ripple's phase in radians; its crest moves towards the first dot as it grows.
    property real phase: 0
    function clear() {
        history = new Array(count).fill(0);
        phase = 0;
    }
    function ripple(index) {
        const amplitude = recognising ? 0.10 : 0.16;
        return 0.12 + amplitude * (0.5 + 0.5 * Math.sin(phase + index * 0.55));
    }
    implicitWidth: count * dot + (count - 1) * bars.spacing
    implicitHeight: AppSizes.unit
    Accessible.ignored: true
    onRunningChanged: clear()
    Component.onCompleted: clear()
    readonly property bool moving: running && animated && visible
    Timer {
        interval: 70
        repeat: true
        running: meter.moving
        // Recognising takes no new level, so the last bars run out to the left.
        onTriggered: meter.history = meter.history.slice(1).concat([meter.recognising ? 0 : meter.level])
    }
    FrameAnimation {
        running: meter.moving
        // 0.9 cycles a second, half that while recognising.
        onTriggered: meter.phase = (meter.phase + 2 * Math.PI * 0.9 * (meter.recognising ? 0.5 : 1) * frameTime) % (2 * Math.PI)
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
                objectName: "voiceDot"
                readonly property real value: meter.animated ? Math.max(meter.running ? meter.ripple(index) : 0, meter.history[index] ?? 0) : index < Math.round(meter.level * meter.count) ? 0.6 : 0
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
