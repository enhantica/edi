// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import edi.app

Item {
    id: recorder
    objectName: "referenceIndicatorRecorder"
    property var indicator
    property var samples: []
    property bool overflow: false
    function sample(phase) {
        if (samples.length >= 50000) { overflow = true; return; }
        const active = Session.assistant.state === "agent_active";
        samples.push({phase: phase, active: active,
            fitting: Session.project && Session.project.fit.running,
            visible: indicator && indicator.visible && indicator.opacity > 0,
            working: indicator && indicator.working,
            animating: indicator && indicator.animating,
            text: indicator ? indicator.text : ""});
    }
    Timer { interval: 5; running: true; repeat: true
        onTriggered: recorder.sample("timer") }
    Connections {
        target: recorder.indicator
        function onVisibleChanged() { Qt.callLater(function() { recorder.sample("visibility"); }); }
        function onAnimatingChanged() { Qt.callLater(function() { recorder.sample("animation"); }); }
    }
    Connections {
        target: Session.project ? Session.project.fit : null
        function onRunningChanged() { recorder.sample(Session.project.fit.running
            ? "native-fit-start" : "native-fit-end"); }
        function onFinished() { recorder.sample("native-fit-finished"); }
    }
    Connections {
        target: Session.assistant
        function onActionPointerShown() { recorder.sample("action-pointer-shown"); }
        function onActionPointerMoved() { recorder.sample("action-pointer-moved"); }
        function onActionPointerPressed() { recorder.sample("action-pointer-pressed"); }
        function onActionPointerHidden() { recorder.sample("action-pointer-hidden"); }
        function onStateChanged() { Qt.callLater(function() { recorder.sample("state"); }); }
    }
}
