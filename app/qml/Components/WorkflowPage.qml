// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
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
    // Popup visibility includes its exit; manual controls resume only after the sheet closes.
    property bool assistantCovered: false
    // Retained offscreen pages keep their tree/state but cannot acquire input focus.
    enabled: current
    readonly property Item assistantOverlayHost: sideBar.parent
    property alias mainTabs: mainContent.tabs
    property alias mainItems: mainContent.items
    property alias basicItem: basicLoader.sourceComponent
    property alias extrasItem: extrasLoader.sourceComponent
    property alias textItem: textLoader.sourceComponent
    // The page's Settings tab (edi ADR-0031 §2): its view options, kept in the app's settings under the page's name,
    // never in the project. A page with none has the tab disabled, as an empty Extra tab is.
    property Component settingsItem: null
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
    // The role marking the template dataset, and whether the shown block is it (BlockSelector).
    property string blockTemplateRole: ""
    property bool blockCurrentTemplate: false
    signal blockActivated(int index)

    function showSidebarTab(extra) { ApplicationInfo.showWorkflowSidebarTab(extra); }

    // Shows one of the main area's tabs (the base's tab bar is the main content's first child).
    // The main area's shown tab.
    readonly property int mainTabIndex: mainContent.children.length > 0 ? mainContent.children[0].currentIndex : 0

    function showMainTab(index) { ApplicationInfo.showWorkflowMainTab(index); }

    // The base's fade above Continue, in the sidebar's colour, reads as a shadow over the Text tab's text view,
    // which runs under the Continue pill (edi ADR-0017 §7): hidden on that tab. The base
    // names it nowhere, so it is found as the SideBar's child with a gradient.
    Component.onCompleted: ApplicationInfo.workflowCompleted(child => { child.visible = Qt.binding(() => page.continueShown && !textLoader.SwipeView.isCurrentItem); }, () => { sideBar.continueButton.anchors.bottomMargin = Qt.binding(() => EaStyle.Sizes.fontPixelSize); })

    // The sidebar on the side the preferences set (Preferences.sideBarSide; edi ADR-0017 §12), live. The base's
    // ContentPage anchors its sidebar container to the right and the main area to its left, with the sidebar's
    // border on its left edge, and names none of them; they are reached as the parents of the main content and
    // the sidebar, and only their anchors change — nothing is mirrored, so text, icons and number order stay.
    function placeSideBar() { ApplicationInfo.placeWorkflowSidebar(); }

    Connections {
        target: Preferences
        function onSideBarSideChanged() {
            page.placeSideBar();
        }
    }

    // The Text tab knows whether it is shown and which block the page shows, so leaving an edit not yet applied asks
    // first; kept, the page, the tab and the block come back (edi ADR-0017 §7).
    property int pageIndex: -1
    // The Text tab's edit is not yet applied: its loader stays active until the user discards it. Set from the tab's
    // signal, so the loader's `active` never reads its own item.
    property bool textDirty: false
    onCurrentChanged: ApplicationInfo.workflowCurrentChanged()
    Binding {
        target: textLoader.item
        property: "shown"
        value: page.current && textLoader.SwipeView.isCurrentItem
        when: textLoader.item !== null
    }
    Binding {
        target: textLoader.item
        property: "blockIndex"
        value: page.blockIndex
        when: textLoader.item !== null
    }
    Connections {
        target: textLoader.item
        ignoreUnknownSignals: true
        function onDirtyChanged() { ApplicationInfo.workflowDirtyChanged(); }
        function onStayRequested() { ApplicationInfo.workflowStayRequested(); }
        function onBlockRequested(index) {
            page.blockActivated(index);
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
        objectName: "workflow." + page.pageName + ".manualSidebar"
        // Remain painted at full theme colors under the sliding sheet. Popup's
        // local input shield and actual strip focus guard own covered input.

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
                id: textTabButton
                objectName: "sideBar.tab.text"
                text: qsTr("Text")
                enabled: page.textEnabled
            },
            EaElements.TabButton {
                objectName: "sideBar.tab.settings"
                text: qsTr("Settings")
                enabled: page.settingsItem !== null
            }
        ]

        items: [
            Loader {
                id: basicLoader
            },
            Loader {
                id: extrasLoader
            },
            // Text is loaded only while its tab is shown, a block's text can be the whole data loop, or while it
            // holds an edit not yet applied, until the user discards it.
            Loader {
                id: textLoader
                active: SwipeView.isCurrentItem || page.textDirty
                onItemChanged: page.textDirty = item !== null && item.dirty === true
            },
            Loader {
                id: settingsLoader
                sourceComponent: page.settingsItem
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
