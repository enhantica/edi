// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A page's Text tab (easydiffractionbeta Pages/*/SideBarText.qml): the block's text view, filling the tab
// (SideBarText/TextView.qml, edi ADR-0017 §7). The text is the `.edi` text a save writes for the block,
// read-only in PT Mono, or the writer's refusal when it cannot be written. The tab has no block selector of its
// own (edi ADR-0017 §7): on Structure and Experiment the sidebar's selector serves every tab, and Project,
// Analysis and Report have one block each — the app opens one project at a time, so there is nothing to choose.
EaComponents.SideBarColumn {
    id: tab

    required property BlockText source
    // False on a page without Continue (Report), or while the Continue area is hidden: nothing is drawn over the
    // text view's bottom.
    property bool underContinue: AppState.continueAreaShown

    // The text view fills the tab edge to edge (the owner, 2026-09-29; edi ADR-0017 §7): the sidebar's full
    // width, from the top of the tab's view — under the tab bar, or under the shared block selector — down to
    // the sidebar's bottom, with no border of its own. Continue, a pill with its own background, floats over
    // it, and the text scrolls clear of it.
    Rectangle {
        id: container

        width: tab.width
        height: Math.max(AppSizes.textViewMinimumHeight, tab.height)
        color: EaStyle.Colors.textViewBackground
        Behavior on color {
            EaAnimations.ThemeChange {}
        }

        Flickable {
            anchors.fill: parent
            anchors.topMargin: AppSizes.textViewPadding
            anchors.bottomMargin: AppSizes.textViewPadding
            anchors.leftMargin: AppSizes.textViewPadding
            contentWidth: textEdit.contentWidth
            contentHeight: textEdit.contentHeight
            bottomMargin: tab.underContinue ? AppSizes.textViewContinueClearance : 0
            clip: true
            ScrollBar.vertical: EaElements.ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: false
            }
            ScrollBar.horizontal: EaElements.ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: false
            }

            TextEdit {
                id: textEdit
                objectName: "text.view"
                readOnly: true
                selectByMouse: true
                font.family: tab.source && tab.source.error !== "" ? EaStyle.Fonts.fontFamily : EaStyle.Fonts.monoFontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
                color: tab.source && tab.source.error !== "" ? EaStyle.Colors.themeForegroundMinor : EaStyle.Colors.themeForeground
                selectionColor: EaStyle.Colors.themeAccent
                selectedTextColor: EaStyle.Colors.themeBackground
                text: !tab.source ? "" : tab.source.error !== "" ? tab.source.error : tab.source.text
            }
        }
    }
}
