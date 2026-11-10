// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements

// A text field of several lines, in the one-line text fields' look (the owner, 2026-10-27): three lines at first,
// growing with its text to ten, then scrolling. A line break is typed with Return.
ScrollView {
    id: field

    property alias text: area.text
    property alias editorObjectName: area.objectName
    property alias placeholderText: area.placeholderText
    // The text area's own name, for the controls that find it by name.
    property alias areaObjectName: area.objectName
    // Shown, not typed: a preview.
    property alias readOnly: area.readOnly
    // A read-only field's text is greyed unless it is the thing to read, as a preview is.
    property bool dimsWhenReadOnly: true
    property alias fontFamily: area.font.family
    property int minimumLines: 3
    property int maximumLines: 10
    // Its scroll bar stays shown while its text is taller than the field, not only while scrolling.
    property bool scrollBarShown: false

    readonly property real lineHeight: metrics.lineSpacing

    // The field's height when it shows `lines` lines.
    function heightFor(lines) {
        // Rounded once, for the whole field: a line rounded up on its own adds a pixel a line.
        return Math.ceil(lines * lineHeight + area.topPadding + area.bottomPadding);
    }
    function focusText() {
        area.forceActiveFocus();
    }

    // As tall as its lines, between the two counts; all of them, as laid out, when they fit under the most.
    implicitHeight: area.lineCount > maximumLines ? heightFor(maximumLines) : Math.max(heightFor(minimumLines), Math.ceil(area.implicitHeight))
    clip: true

    // A field whose text fits does not scroll, so the wheel over it scrolls what holds it (a form's body).
    wheelEnabled: field.contentHeight > field.height + 1
    Binding {
        target: field.contentItem
        property: "interactive"
        value: field.wheelEnabled
    }
    // Text wraps, so it never scrolls sideways: no horizontal bar, not even one shown for a moment.
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    // The app's scroll bar, not the style's.
    ScrollBar.vertical: EaElements.ScrollBar {
        parent: field
        x: field.mirrored ? 0 : field.width - width
        y: field.topPadding
        height: field.availableHeight
        // None at all while the text fits, so a field never adds a second scroll bar to its form.
        policy: field.contentHeight <= field.height + 1 ? ScrollBar.AlwaysOff : field.scrollBarShown ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
    }

    EaElements.TextArea {
        id: area

        padding: EaStyle.Sizes.fontPixelSize * 0.5 + 1
        wrapMode: TextEdit.Wrap
        // Tab moves on through the form, as from a one-line field, rather than typing a tab.
        Keys.onTabPressed: event => {
            nextItemInFocusChain(true).forceActiveFocus(Qt.TabFocusReason);
            event.accepted = true;
        }
        Keys.onBacktabPressed: event => {
            nextItemInFocusChain(false).forceActiveFocus(Qt.BacktabFocusReason);
            event.accepted = true;
        }
        color: !enabled ? EaStyle.Colors.themeForegroundDisabled : readOnly && field.dimsWhenReadOnly ? EaStyle.Colors.themeForegroundMinor : hovered || activeFocus ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.themeForeground
        background: Rectangle {
            color: area.enabled && !area.readOnly && (area.activeFocus || area.hovered) ? EaStyle.Colors.appBarComboBoxBackgroundHovered : EaStyle.Colors.appBarComboBoxBackground
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
            border.color: area.enabled && !area.readOnly && (area.activeFocus || area.hovered) ? EaStyle.Colors.themeForegroundHovered : EaStyle.Colors.appBarComboBoxBorder
            Behavior on border.color {
                EaAnimations.ThemeChange {}
            }
        }
    }
    FontMetrics {
        id: metrics
        font: area.font
    }
}
