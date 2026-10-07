// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// A workflow page's frame (easydiffractionbeta Pages/*/PageStructure.qml): the main view with its tabs
// on the left, the Main / Extra / Text sidebar on the right, and Continue at the bottom. A page with a
// block list (Structure, Experiment, Analysis) shows one compact block selector as a row at the top of the main
// area, under its tab bar (MainAreaBlockSelector; edi ADR-0017 §7), while the project holds a block of its kind.
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
    // Continue and its fade, while AppState shows the Continue area at all.
    readonly property bool continueShown: continueVisible && AppState.continueAreaShown
    signal continueClicked
    // The block selector: shown when set; the page's blocks, the shown one, and the user's choice.
    property bool blockSelectorShown: false
    property var blocks: null
    property string blocksTextRole: ""
    property string blockKind: ""
    property int blockIndex: 0
    // Where the selector row ends, from the main area's right edge: the right edge of the chart toolbar below.
    property real blockSelectorRightInset: EaStyle.Sizes.fontPixelSize
    // The blocks' fit-outcome role and the shown block's outcome (experiments; BlockSelector).
    property string blockOutcomeRole: ""
    property string blockCurrentOutcome: ""
    // Every entry in the first block's colour (a scan's datasets).
    property bool blockOneColour: false
    // The role marking the template dataset, and whether the shown block is it (BlockSelector).
    property string blockTemplateRole: ""
    property bool blockCurrentTemplate: false
    signal blockActivated(int index)

    // Shows one of the main area's tabs (the base's tab bar is the main content's first child).
    function showMainTab(index) {
        mainContent.children[0].currentIndex = index;
    }

    // The base's fade above Continue, in the sidebar's colour, reads as a shadow over the Text tab's text view,
    // which runs under the Continue pill (edi ADR-0017 §7): hidden on that tab. The base
    // names it nowhere, so it is found as the SideBar's child with a gradient.
    Component.onCompleted: {
        for (let i = 0; i < sideBar.children.length; ++i) {
            const child = sideBar.children[i];
            if (child.gradient)
                child.visible = Qt.binding(() => page.continueShown && !textLoader.SwipeView.isCurrentItem);
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

        MainAreaBlockSelector {
            id: blockSelector
            visible: page.blockSelectorShown && page.blocks !== null && page.blocks.count > 0
            areaWidth: mainContent.width
            rightInset: page.blockSelectorRightInset
            blocks: page.blocks
            blocksTextRole: page.blocksTextRole
            blockKind: page.blockKind
            blockIndex: page.blockIndex
            outcomeRole: page.blockOutcomeRole
            currentOutcome: page.blockCurrentOutcome
            oneColour: page.blockOneColour
            templateRole: page.blockTemplateRole
            currentTemplate: page.blockCurrentTemplate
            onBlockActivated: index => page.blockActivated(index)
        }

        // The tabs' view (the base's SwipeView, the main area's second child, anchored under the tab bar)
        // starts below the selector.
        Binding {
            target: mainContent.children.length > 1 ? mainContent.children[1].anchors : null
            property: "topMargin"
            value: blockSelector.reservedHeight
        }
    }

    sideBar: EaComponents.SideBar {
        id: sideBar

        tabs: [
            EaElements.TabButton {
                objectName: "sideBar.tab.basic"
                text: qsTr("Main")
            },
            EaElements.TabButton {
                objectName: "sideBar.tab.extras"
                text: qsTr("Extra")
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
        continueButton.visible: page.continueShown
        continueButton.onClicked: page.continueClicked()
        // Continue as a pill (the owner, 2026-09-29; edi ADR-0017 §7): the base button's own background and
        // border shown, fully rounded ends, as wide as its icon and text plus a font unit each side (the base
        // lays them out in an unnamed row, read here), raised half a font unit above the base's place
        // (onCompleted).
        continueButton.showBackground: true
        continueButton.radius: sideBar.continueButton.height / 2
        continueButton.width: (sideBar.continueButton.contentItem && sideBar.continueButton.contentItem.children.length > 0 ? sideBar.continueButton.contentItem.children[0].width : 0) + 2 * EaStyle.Sizes.fontPixelSize

        // On the Text tab the tabs' view reaches the bottom of the sidebar, so the text view can run down to it
        // with Continue kept in its place, drawn over the text with the base's fade (edi ADR-0017 §7). The base
        // anchors the view's bottom a font unit above Continue's top, or above the sidebar's bottom without
        // Continue; the other tabs keep that.
        Binding {
            target: basicLoader.SwipeView.view ? basicLoader.SwipeView.view.anchors : null
            property: "bottomMargin"
            when: textLoader.SwipeView.isCurrentItem
            value: page.continueShown ? -(sideBar.continueButton.height + sideBar.continueButton.anchors.bottomMargin) : 0
        }
    }
}
