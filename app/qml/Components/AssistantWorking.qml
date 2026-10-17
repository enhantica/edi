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
        && Object.keys(assistant.pendingQuestion).length === 0
        && Object.keys(assistant.pendingPlan).length === 0
    visible: presented && working
    clip: true
    text: qsTr("AI working...")
    textFormat: Text.PlainText
    color: EaStyle.Colors.themeAccent
    Accessible.name: text
    property int variant: 0
    readonly property bool animating: visible && EaStyle.Times.translationChange > 0
    onAnimatingChanged: if (!animating) workGlyph.rotation = 0
    readonly property real iconExtent: EaStyle.Sizes.fontPixelSize * 0.75 * 1.75
    leftPadding: iconExtent + AppSizes.unit * 0.5
    onVisibleChanged: {
        if (visible) variant = Math.floor(Math.random() * 3);
        else workGlyph.rotation = 0;
    }
    Item {
        width: workStatus.iconExtent
        height: width
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
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
            EaElements.Label {
                anchors.centerIn: parent
                visible: workStatus.variant === 2
                text: "robot"
                font.family: EaStyle.Fonts.iconsFamily
                font.pixelSize: workStatus.iconExtent
                color: EaStyle.Colors.themeAccent
                Accessible.ignored: true
            }
        }
    }

    RotationAnimation {
        target: workGlyph
        property: "rotation"
        running: workStatus.animating && workStatus.variant !== 0
        loops: Animation.Infinite
        from: 0
        to: 360 * 6
        duration: 2000
        easing.type: Easing.OutInElastic
        easing.amplitude: 1
        easing.period: 0.3
    }
    RotationAnimation {
        target: workGlyph
        property: "rotation"
        running: workStatus.animating && workStatus.variant === 0
        loops: Animation.Infinite
        from: 0
        to: 360
        duration: 1600
        easing.type: Easing.Linear
    }
}
