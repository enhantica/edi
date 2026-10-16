// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// One square button of a chart's toolbar (easydiffractionbeta's QtCharts1dTab.qml; edi ADR-0017 §15): a Font
// Awesome icon on the content background inside a border in the chart's axis colour, the icon in the accent
// colour while hovered or checked; disabled, both in the theme's disabled colours, as the toolbar's boxes. Shared by
// the pattern chart and, with, the structure view.
Rectangle {
    id: button

    property string fontIcon: ""
    property string toolTip: ""
    property bool checked: false
    signal clicked

    width: AppSizes.toolbarControlSize
    height: width
    color: EaStyle.Colors.contentBackground
    border.color: button.enabled ? EaStyle.Colors.chartAxis : EaStyle.Colors.themeBackgroundDisabled
    border.width: EaStyle.Sizes.borderThickness

    EaElements.Label {
        anchors.centerIn: parent
        font.family: EaStyle.Fonts.iconsFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize * 1.15
        color: !button.enabled ? EaStyle.Colors.themeForegroundDisabled : hover.hovered || button.checked ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
        text: button.fontIcon
    }
    HoverHandler {
        id: hover

        cursorShape: Qt.PointingHandCursor
    }
    TapHandler {
        readonly property var assistantGesture: ({ current: null })

        function sameGesture(point) {
            const retained = assistantGesture.current;
            return retained !== null && retained.device === point.device && retained.id === point.id && retained.press === point.pressTimestamp;
        }
        function discardGesture(point) {
            if (sameGesture(point)) {
                assistantGesture.current.closed = true;
                assistantGesture.current.proof = null;
            }
        }
        onGrabChanged: (transition, eventPoint) => {
            if (transition === PointerDevice.GrabPassive || transition === PointerDevice.GrabExclusive) {
                if (sameGesture(eventPoint))
                    return; // Passive/exclusive transitions cannot rearm this press.
                if (eventPoint.state !== EventPoint.Pressed)
                    return;
                const original = { device: eventPoint.device, id: eventPoint.id, press: eventPoint.pressTimestamp, proof: null, closed: false };
                const holder = assistantGesture;
                holder.current = original; // No QML notification before capture/cancellation.
                const proof = Session.assistant.beginManualControlInput(button, eventPoint, Session.project);
                if (holder.current === original && !original.closed)
                    original.proof = proof; // An old callback cannot overwrite a newer grab.
            } else if (transition === PointerDevice.UngrabPassive || transition === PointerDevice.UngrabExclusive || transition === PointerDevice.CancelGrabPassive || transition === PointerDevice.CancelGrabExclusive) {
                discardGesture(eventPoint);
            }
        }
        onCanceled: eventPoint => {
            if (sameGesture(eventPoint))
                discardGesture(eventPoint);
        }
        onTapped: eventPoint => {
            if (!sameGesture(eventPoint) || assistantGesture.current.closed)
                return;
            const original = assistantGesture.current;
            const proof = original.proof;
            original.closed = true;
            original.proof = null; // Consume BEFORE validation/action and any reentry.
            if (Session.assistant.completeManualControlInput(button, eventPoint, Session.project, proof))
                button.clicked();
        }
    }
    EaElements.ToolTip {
        text: button.toolTip
        visible: text !== "" && hover.hovered && EaGlobals.Vars.showToolTips
    }
}
