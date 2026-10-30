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
    text: ApplicationInfo.workingText()
    textFormat: Text.PlainText
    color: EaStyle.Colors.themeAccent
    Accessible.name: text
    property int variant: ApplicationInfo.workingInitialVariant()
    property double workingSince: 0
    property int elapsedSeconds: 0
    property double rotationStartedAt: 0
    property double variantSwitchDeadline: 0
    readonly property bool animating: working && EaStyle.Times.translationChange > 0
    readonly property real iconExtent: AppSizes.assistantIndicatorExtent
    readonly property real rotationExtent: iconExtent
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
    onWorkingChanged: ApplicationInfo.workingStateChanged(0)
    onAnimatingChanged: ApplicationInfo.workingStateChanged(1)
    Component.onCompleted: ApplicationInfo.workingStateChanged(2)
    function scheduleVariantChange() { ApplicationInfo.workingScheduleVariant(); }
    function changeVariant() { ApplicationInfo.workingChangeVariant(); }
    Timer {
        interval: 1000
        repeat: true
        running: workStatus.working
        onTriggered: ApplicationInfo.workingElapsed()
    }
    Timer {
        id: variantCadence
        onTriggered: ApplicationInfo.workingCadence(false)
    }
    Timer {
        id: peakSwitch
        onTriggered: ApplicationInfo.workingCadence(true)
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
                // The ink rectangle's diagonal bounds every rotated extent,
                // so the whole cycle stays inside the same borderless circle.
                scale: width > 0 || height > 0 ? workStatus.iconExtent / Math.sqrt(width * width + height * height) : 1
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
        onStarted: ApplicationInfo.workingAnimation(true)
        running: workStatus.animating
        onStopped: ApplicationInfo.workingAnimation(false)
        loops: Animation.Infinite
        from: 0
        to: workStatus.variant === 0 ? 360 : 360 * 6
        duration: workStatus.variant === 0 ? 1600 : 2000
        easing.type: workStatus.variant === 0 ? Easing.Linear : Easing.OutInElastic
        easing.amplitude: 1
        easing.period: 0.3
    }
}
