// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Animations as EaAnimations
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A workflow page's frame (easydiffractionbeta Pages/*/PageStructure.qml): the main view with its tabs
// on the left, the Basic / Extras / Text sidebar on the right, and Continue at the bottom. A page with a
// block list (Structure, Experiment) shows one compact block selector under the sidebar's tabs, above every
// tab's content, never folded (edi ADR-0017 §7): the base's SideBar has no place for it, so it is a child of
// the SideBar placed under the tab bar, and the tabs' view starts below it.
EaComponents.ContentPage {
    id: page

    property string pageName: ""
    // The page is the one the window shows (Main.qml binds it to the window's page view). A page that is not
    // shown stays loaded, laid out and visible beside the shown one, clipped out of the view, so `visible`
    // does not say it: what the page draws only for the eye (its chart) follows this instead.
    property bool current: false
    property alias mainTabs: mainContent.tabs
    property alias mainItems: mainContent.items
    property alias basicItem: basicLoader.sourceComponent
    property alias extrasItem: extrasLoader.sourceComponent
    property alias textItem: textLoader.sourceComponent
    property bool extrasEnabled: false
    property bool textEnabled: false
    property alias continueText: sideBar.continueButton.text
    property bool continueVisible: true
    signal continueClicked
    // The block selector: shown when set; the page's blocks, the shown one, and the user's choice.
    property bool blockSelectorShown: false
    property var blocks: null
    property string blocksTextRole: ""
    property string blockKind: ""
    property int blockIndex: 0
    signal blockActivated(int index)

    // The base's fade above Continue, in the sidebar's colour, reads as a shadow over the Text tab's text view,
    // which runs under the Continue pill (edi ADR-0017 §7): hidden on that tab. The base
    // names it nowhere, so it is found as the SideBar's child with a gradient.
    Component.onCompleted: {
        for (let i = 0; i < sideBar.children.length; ++i) {
            const child = sideBar.children[i];
            if (child.gradient)
                child.visible = Qt.binding(() => !textLoader.SwipeView.isCurrentItem);
        }
        page.placeSideBar();
        sideBar.continueButton.anchors.bottomMargin = Qt.binding(() => EaStyle.Sizes.fontPixelSize);
    }

    // The sidebar on the side the preferences set (Preferences.sideBarSide; edi ADR-0017 §12), live. The base's
    // ContentPage anchors its sidebar container to the right and the main area to its left, with the sidebar's
    // border on its left edge, and names none of them; they are reached as the parents of the main content and
    // the sidebar, and only their anchors change — nothing is mirrored, so text, icons and number order stay.
    function placeSideBar() {
        const main = mainContent.parent;
        const side = sideBar.parent;
        if (!main || !side)
            return;
        const left = Preferences.sideBarOnLeft;
        side.anchors.left = undefined;
        side.anchors.right = undefined;
        main.anchors.left = undefined;
        main.anchors.right = undefined;
        if (left) {
            side.anchors.left = page.left;
            main.anchors.left = side.right;
            main.anchors.right = page.right;
        } else {
            side.anchors.right = page.right;
            main.anchors.left = page.left;
            main.anchors.right = side.left;
        }
        // The sidebar's border stays on its edge towards the main area.
        for (let i = 0; i < side.children.length; ++i) {
            const border = side.children[i];
            if (border !== sideBar && border.width === EaStyle.Sizes.borderThickness) {
                border.anchors.left = undefined;
                border.anchors.right = undefined;
                if (left)
                    border.anchors.right = side.right;
                else
                    border.anchors.left = side.left;
            }
        }
    }

    Connections {
        target: Preferences
        function onSideBarSideChanged() {
            page.placeSideBar();
        }
    }

    mainView: EaComponents.MainContent {
        id: mainContent
    }

    sideBar: EaComponents.SideBar {
        id: sideBar

        tabs: [
            EaElements.TabButton {
                id: basicTab
                objectName: "sideBar.tab.basic"
                text: qsTr("Basic")
            },
            EaElements.TabButton {
                objectName: "sideBar.tab.extras"
                text: qsTr("Extras")
                enabled: page.extrasEnabled
            },
            EaElements.TabButton {
                objectName: "sideBar.tab.text"
                text: qsTr("Text")
                enabled: page.textEnabled
            }
        ]

        items: [
            Loader {
                id: basicLoader
            },
            Loader {
                id: extrasLoader
            },
            // Text is loaded only while its tab is shown: a block's text can be the whole data loop.
            Loader {
                id: textLoader
                active: SwipeView.isCurrentItem
            }
        ]

        continueButton.objectName: "sideBar.continue"
        continueButton.visible: page.continueVisible
        continueButton.onClicked: page.continueClicked()
        // Continue as a pill (the owner, 2026-09-29; edi ADR-0017 §7): the base button's own background and
        // border shown, fully rounded ends, as wide as its icon and text plus a font unit each side (the base
        // lays them out in an unnamed row, read here), raised half a font unit above the base's place
        // (onCompleted).
        continueButton.showBackground: true
        continueButton.radius: sideBar.continueButton.height / 2
        continueButton.width: (sideBar.continueButton.contentItem && sideBar.continueButton.contentItem.children.length > 0 ? sideBar.continueButton.contentItem.children[0].width : 0) + 2 * EaStyle.Sizes.fontPixelSize

        BlockSelector {
            id: blockSelector
            objectName: "sideBar.blocks"
            visible: page.blockSelectorShown
            x: EaStyle.Sizes.sideBarPadding
            // As the Text tab's selector sat: one font unit under the tab bar.
            y: (basicTab.TabBar.tabBar ? basicTab.TabBar.tabBar.height : 0) + EaStyle.Sizes.fontPixelSize
            blocks: page.blocks
            blocksTextRole: page.blocksTextRole
            blockKind: page.blockKind
            blockIndex: page.blockIndex
            onBlockActivated: index => page.blockActivated(index)
        }

        // On every tab the selector closes with the bottom border a group draws (the base GroupBox's: a line of
        // the border colour, a font unit under its content, across the sidebar); the tabs' view starts right
        // under it (edi ADR-0017 §7).
        Rectangle {
            objectName: "sideBar.blocks.border"
            visible: page.blockSelectorShown
            y: blockSelector.y + blockSelector.height + EaStyle.Sizes.fontPixelSize - height
            width: parent.width
            height: EaStyle.Sizes.borderThickness
            color: EaStyle.Colors.appBorder
            Behavior on color {
                EaAnimations.ThemeChange {}
            }
        }

        // The tabs' view (the base's SwipeView, anchored under the tab bar) starts a font unit under the
        // selector on every tab, right under its border.
        Binding {
            target: basicLoader.SwipeView.view ? basicLoader.SwipeView.view.anchors : null
            property: "topMargin"
            value: !page.blockSelectorShown ? 0 : 2 * EaStyle.Sizes.fontPixelSize + blockSelector.height
        }

        // On the Text tab the tabs' view reaches the bottom of the sidebar, so the text view can run down to it
        // with Continue kept in its place, drawn over the text with the base's fade (edi ADR-0017 §7). The base
        // anchors the view's bottom a font unit above Continue's top, or above the sidebar's bottom without
        // Continue; the other tabs keep that.
        Binding {
            target: basicLoader.SwipeView.view ? basicLoader.SwipeView.view.anchors : null
            property: "bottomMargin"
            when: textLoader.SwipeView.isCurrentItem
            value: page.continueVisible ? -(sideBar.continueButton.height + sideBar.continueButton.anchors.bottomMargin) : 0
        }
    }
}
