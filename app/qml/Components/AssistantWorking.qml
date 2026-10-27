// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.impl as ControlsImpl
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import edi.app

EaElements.Label {
    id: workStatus
    required property AssistantViewModel assistant
    property bool presented: true
    readonly property bool working: assistant !== null && assistant.state === "agent_active"
    visible: presented && working
    clip: true
    text: elapsedSeconds < 60
        ? qsTr("%1s · Agent working...").arg(elapsedSeconds)
        : qsTr("%1m %2s · Agent working...").arg(Math.floor(elapsedSeconds / 60)).arg(elapsedSeconds % 60)
    textFormat: Text.PlainText
    color: EaStyle.Colors.themeAccent
    Accessible.name: text
    property int variant: Math.floor(Math.random() * 3)
    property double workingSince: 0
    property int elapsedSeconds: 0
    property double rotationStartedAt: 0
    property double variantSwitchDeadline: 0
    readonly property bool animating: working && EaStyle.Times.translationChange > 0
    readonly property real iconExtent: AppSizes.assistantIconExtent
    readonly property real rotationExtent: variant === 2 ? iconExtent * Math.SQRT2 : iconExtent
    leftPadding: rotationExtent + AppSizes.unit * 0.5
    // Use the rendered Label baseline, including its actual padding/alignment.
    readonly property real textInkCenter: baselineOffset + textInk.tightBoundingRect.y + textInk.tightBoundingRect.height / 2
    readonly property real naturalTextInkCenter: textMetrics.ascent + textInk.tightBoundingRect.y + textInk.tightBoundingRect.height / 2
    topPadding: Math.max(0, rotationExtent / 2 - naturalTextInkCenter)
    bottomPadding: Math.max(0, rotationExtent / 2 - (contentHeight - naturalTextInkCenter))
    FontMetrics {
        id: textMetrics
        font: workStatus.font
    }
    // IconLine aligns inline symbols to capital ink, excluding descenders.
    TextMetrics {
        id: textInk
        font: workStatus.font
        renderType: workStatus.renderType
        text: "H"
    }
    onWorkingChanged: {
        workingSince = working ? Date.now() : 0
        elapsedSeconds = 0
    }
    onAnimatingChanged: if (!animating && peakSwitch.running) {
        peakSwitch.stop()
        changeVariant()
    }
    Component.onCompleted: {
        if (working)
            workingSince = Date.now()
        scheduleVariantChange()
    }
    function scheduleVariantChange() {
        variantSwitchDeadline = Date.now() + 60000
        variantCadence.interval = 30000 + Math.floor(Math.random() * 28001)
        variantCadence.start()
    }
    function changeVariant() {
        const wasLinear = variant === 0
        variant = (variant + 1 + Math.floor(Math.random() * 2)) % 3
        if (animating && wasLinear !== (variant === 0))
            rotationAnimator.restart()
        scheduleVariantChange()
    }
    Timer {
        interval: 1000
        repeat: true
        running: workStatus.working
        onTriggered: workStatus.elapsedSeconds = Math.max(0, Math.floor((Date.now() - workStatus.workingSince) / 1000))
    }
    Timer {
        id: variantCadence
        onTriggered: {
            const now = Date.now()
            if (workStatus.animating && workStatus.variant !== 0 && now < workStatus.variantSwitchDeadline) {
                // OutInElastic is fastest at its cycle boundary; see ADR-0041.
                const phase = ((now - workStatus.rotationStartedAt) % 2000 + 2000) % 2000
                peakSwitch.interval = Math.max(1, Math.ceil(Math.min(2000 - phase, workStatus.variantSwitchDeadline - now)))
                peakSwitch.start()
            } else {
                workStatus.changeVariant()
            }
        }
    }
    Timer {
        id: peakSwitch
        onTriggered: {
            const now = Date.now()
            if (workStatus.animating && workStatus.variant !== 0 && now < workStatus.variantSwitchDeadline) {
                const phase = ((now - workStatus.rotationStartedAt) % 2000 + 2000) % 2000
                // Seek the next fast phase only until the fixed switch deadline.
                if (phase > 32) {
                    peakSwitch.interval = Math.max(1, Math.ceil(Math.min(2000 - phase, workStatus.variantSwitchDeadline - now)))
                    peakSwitch.start()
                    return
                }
            }
            workStatus.changeVariant()
        }
    }
    Item {
        width: workStatus.rotationExtent
        height: width
        anchors.left: parent.left
        y: workStatus.textInkCenter - height / 2
        Item {
            id: workGlyph
            width: workStatus.iconExtent
            height: width
            anchors.centerIn: parent
            ControlsImpl.IconImage {
                anchors.fill: parent
                visible: workStatus.variant !== 2
                source: workStatus.variant === 1 ? "../../resources/logo/AssistantWorking.svg" : "../../resources/logo/AssistantSpinner.svg"
                sourceSize: Qt.size(width, height)
                color: EaStyle.Colors.themeAccent
                fillMode: Image.PreserveAspectFit
                Accessible.ignored: true
            }
            TextMetrics {
                id: robotMetrics
                text: robotGlyph.text
                font: robotGlyph.font
            }
            Item {
                anchors.centerIn: parent
                visible: workStatus.variant === 2
                width: robotMetrics.tightBoundingRect.width
                height: robotMetrics.tightBoundingRect.height
                // Keep accepted upright ink size; reserve its safe rotation
                // envelope outside the actual icon circle instead of shrinking it.
                scale: Math.max(width, height) > 0 ? workStatus.iconExtent / Math.max(width, height) : 1
                EaElements.Label {
                    id: robotGlyph
                    x: -robotMetrics.tightBoundingRect.x
                    y: -robotMetrics.tightBoundingRect.y - baselineOffset
                    text: "robot"
                    font.family: EaStyle.Fonts.iconsFamily
                    font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.75 * 1.25
                    color: EaStyle.Colors.themeAccent
                    Accessible.ignored: true
                }
            }
        }
    }

    RotationAnimator {
        id: rotationAnimator
        target: workGlyph
        onStarted: workStatus.rotationStartedAt = Date.now()
        running: workStatus.animating
        onStopped: if (!workStatus.animating)
            workGlyph.rotation = 0
        loops: Animation.Infinite
        from: 0
        to: workStatus.variant === 0 ? 360 : 360 * 6
        duration: workStatus.variant === 0 ? 1600 : 2000
        easing.type: workStatus.variant === 0 ? Easing.Linear : Easing.OutInElastic
        easing.amplitude: 1
        easing.period: 0.3
    }
}
