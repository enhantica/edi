// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A running tutorial's Stop, Back and Next (edi ADR-0064; the owner, 2026-11-02): one row for the callout and the
// status bar's strip, in that order with equal gaps, Next shown but off on the last step. In the status bar they are the
// bar's light round buttons, as the assistant's (StatusBarButton); in the callout plain icons. Both rows act on the same
// tutorial.
Row {
    id: controls

    required property TutorialPanel tutorial
    // The start of the buttons' names: `<prefix>.stop`, `<prefix>.back` and `<prefix>.next`.
    property string namePrefix: "tutorial"
    // Stop, unless the last step's own choices stand in for it (the callout's Keep and Discard).
    property bool stopShown: true
    // The status bar's round buttons; plain icons otherwise.
    property bool round: false

    // The assistant's round status buttons: a circle three quarters of a tool button tall, its icon a little under the
    // font size.
    readonly property real roundExtent: Math.round(EaStyle.Sizes.toolButtonHeight * 0.75)
    readonly property real roundIconSize: AppSizes.unit * 0.9375
    readonly property bool canGoBack: tutorial !== null && tutorial.step > 0
    // On the last step Next stays where it is, off, so nothing moves under the pointer; Stop ends the tutorial there.
    readonly property bool canGoOn: tutorial !== null && !tutorial.atEnd
    readonly property string stopTip: tutorial && tutorial.atEnd ? qsTr("Finish the tutorial (Esc)") : qsTr("Stop the tutorial (Esc)")

    spacing: Math.round(EaStyle.Sizes.fontPixelSize * 0.5)

    // How far an icon's ink sits from its advance's middle, to centre a plain icon by what it draws.
    function inkShift(metrics) {
        return metrics.advanceWidth / 2 - (metrics.tightBoundingRect.x + metrics.tightBoundingRect.width / 2);
    }
    readonly property font plainIconFont: Qt.font({
        "family": EaStyle.Fonts.iconsFamily,
        "pixelSize": EaStyle.Sizes.fontPixelSize * 1.25
    })
    // How far below the plain icons' lowest ink the row ends: each icon sits in its taller button, so the callout
    // measures its bottom padding from the glyphs, not from the buttons (the owner, 2026-11-02). Read from the icons'
    // text as laid out, its baseline and the glyph's ink below it, once the buttons are made and when the row changes.
    property real inkBottomInset: 0
    function measureInk() {
        const row = buttons.item as Row;
        if (controls.round || row === null)
            return;
        const inkOf = {
            "times": stopInk,
            "chevron-left": backInk
        };
        let lowest = -1;
        for (const button of row.children) {
            // Laid out whether shown or not: a closed callout's buttons read as hidden.
            if (!button.contentItem)
                continue;
            const ink = inkOf[button.fontIcon] ?? nextInk;
            for (const text of button.contentItem.children) {
                if (text.baselineOffset === undefined || text.text === undefined || text.text === "")
                    continue;
                const bottom = text.mapToItem(controls, 0, text.baselineOffset).y + ink.tightBoundingRect.y + ink.tightBoundingRect.height;
                lowest = Math.max(lowest, bottom);
            }
        }
        if (lowest >= 0)
            controls.inkBottomInset = controls.height - lowest;
    }
    onHeightChanged: Qt.callLater(controls.measureInk)
    TextMetrics {
        id: stopInk
        font: controls.plainIconFont
        text: "times"
    }
    TextMetrics {
        id: backInk
        font: controls.plainIconFont
        text: "chevron-left"
    }
    TextMetrics {
        id: nextInk
        font: controls.plainIconFont
        text: "chevron-right"
    }

    // One kind of buttons is made, so each name is held by one control.
    Loader {
        id: buttons

        anchors.verticalCenter: parent.verticalCenter
        sourceComponent: controls.round ? roundButtons : plainButtons
        onLoaded: Qt.callLater(controls.measureInk)
    }

    Component {
        id: roundButtons

        Row {
            spacing: controls.spacing

            StatusBarButton {
                anchors.verticalCenter: parent.verticalCenter
                frameHeight: controls.roundExtent
                iconPixelSize: controls.roundIconSize
                dropsWord: true
                showWord: false
                objectName: `${controls.namePrefix}.stop`
                shown: controls.stopShown
                clickable: true
                keyIcon: "times"
                ToolTip.text: controls.stopTip
                Accessible.name: qsTr("Stop")
                onClicked: controls.tutorial.stop()
            }
            StatusBarButton {
                anchors.verticalCenter: parent.verticalCenter
                frameHeight: controls.roundExtent
                iconPixelSize: controls.roundIconSize
                dropsWord: true
                showWord: false
                objectName: `${controls.namePrefix}.back`
                shown: true
                clickable: controls.canGoBack
                keyIcon: "chevron-left"
                ToolTip.text: qsTr("Previous step (Left arrow)")
                Accessible.name: qsTr("Back")
                onClicked: controls.tutorial.back()
            }
            StatusBarButton {
                anchors.verticalCenter: parent.verticalCenter
                frameHeight: controls.roundExtent
                iconPixelSize: controls.roundIconSize
                dropsWord: true
                showWord: false
                objectName: `${controls.namePrefix}.next`
                shown: true
                clickable: controls.canGoOn
                keyIcon: "chevron-right"
                ToolTip.text: qsTr("Next step (Right arrow)")
                Accessible.name: qsTr("Next")
                onClicked: controls.tutorial.forward()
            }
        }
    }

    Component {
        id: plainButtons

        Row {
            spacing: controls.spacing

            EaElements.ToolButton {
                objectName: `${controls.namePrefix}.stop`
                transform: Translate {
                    x: controls.inkShift(stopInk)
                }
                visible: controls.stopShown
                showBackground: false
                fontIcon: "times"
                ToolTip.text: controls.stopTip
                Accessible.name: qsTr("Stop")
                onClicked: controls.tutorial.stop()
            }
            EaElements.ToolButton {
                objectName: `${controls.namePrefix}.back`
                transform: Translate {
                    x: controls.inkShift(backInk)
                }
                showBackground: false
                enabled: controls.canGoBack
                fontIcon: "chevron-left"
                ToolTip.text: qsTr("Previous step (Left arrow)")
                Accessible.name: qsTr("Back")
                onClicked: controls.tutorial.back()
            }
            EaElements.ToolButton {
                objectName: `${controls.namePrefix}.next`
                transform: Translate {
                    x: controls.inkShift(nextInk)
                }
                showBackground: false
                enabled: controls.canGoOn
                fontIcon: "chevron-right"
                ToolTip.text: qsTr("Next step (Right arrow)")
                Accessible.name: qsTr("Next")
                onClicked: controls.tutorial.forward()
            }
        }
    }
}
