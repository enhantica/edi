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
    // The main area's place in the page: the Structure, Experiment and Analysis pages leave it to the window's one
    // main view, drawn over it (MainView).
    readonly property Item mainArea: mainContent.parent
    // The page's own main view (MainView), over its main area and moving with the page (edi ADR-0017 §2; the owner,
    // 2026-11-14 item 5); null keeps the area's own tabs.
    property Component pageView: null
    readonly property var pageViewItem: pageViewLoader.item
    Loader {
        id: pageViewLoader
        parent: page.mainArea
        anchors.fill: parent
        z: 2
        active: page.pageView !== null
        sourceComponent: page.pageView
    }
    property alias mainTabs: mainContent.tabs
    property alias mainItems: mainContent.items
    property alias basicItem: basicLoader.sourceComponent
    // The page and its Main sidebar tab are both current: what that tab's groups show is on screen.
    readonly property bool basicShown: current && basicLoader.SwipeView.isCurrentItem
    property Component extrasItem: null
    property Component textItem: null
    // Tools (owner, 2026-11-28, sidebar tabs by role): groups that act on the project but edit no `.edi` category, such
    // as the k-vector search or the magnetic symmetry analysis. Main and Extra hold only category groups, Settings only
    // the page's own settings.
    property Component toolsItem: null
    // The page's Settings tab (edi ADR-0031 §2): its view options, kept in the app's settings under the page's name,
    // never in the project.
    property Component settingsItem: null
    property bool extrasEnabled: false
    property bool textEnabled: false
    // Every page shows all five tabs (the owner, 2026-11-10; Tools 2026-11-28). A tab whose content waits for the page's first block
    // says so; a tab the page has no groups for yet asks for ideas, with a link to the feedback form (TabNote below).
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

    function showSidebarTab(extra) {
        ApplicationInfo.showWorkflowSidebarTab(extra);
    }

    // Shows one of the main area's tabs (the base's tab bar is the main content's first child).
    // The main area's shown tab.
    readonly property int mainTabIndex: mainContent.children.length > 0 ? mainContent.children[0].currentIndex : 0

    function showMainTab(index) {
        ApplicationInfo.showWorkflowMainTab(index);
    }
    // The run log's line for a main-view tab chosen on the shown page (edi ADR-0062).
    onMainTabIndexChanged: {
        if (page.current)
            RunLog.note(`${page.pageName} main tab: ${page.mainTabs[page.mainTabIndex]?.objectName ?? page.mainTabIndex}`);
    }

    // The base's fade above Continue, in the sidebar's colour, reads as a shadow over the Text tab's text view,
    // which runs under the Continue pill (edi ADR-0017 §7): hidden on that tab. The base
    // names it nowhere, so it is found as the SideBar's child with a gradient.
    Component.onCompleted: ApplicationInfo.workflowCompleted(child => {
        child.visible = Qt.binding(() => page.continueShown && !textLoader.SwipeView.isCurrentItem);
    }, () => {
        sideBar.continueButton.anchors.bottomMargin = Qt.binding(() => EaStyle.Sizes.fontPixelSize);
    })

    // The sidebar on the side the preferences set (Preferences.sideBarSide; edi ADR-0017 §12), live. The base's
    // ContentPage anchors its sidebar container to the right and the main area to its left, with the sidebar's
    // border on its left edge, and names none of them; they are reached as the parents of the main content and
    // the sidebar, and only their anchors change — nothing is mirrored, so text, icons and number order stay.
    function placeSideBar() {
        ApplicationInfo.placeWorkflowSidebar();
        followOwnBorder();
        placeBelow();
    }
    // In a narrow window the sidebar is under the main view, full width, above the status bar, taking what the main
    // view's minimum leaves (ADR-0103 decision 3).
    // Both layouts set every anchor they use from the page itself, so switching back needs nothing remembered; the side
    // layout's left and right anchors are the base's placement (placeWorkflowSidebar).
    property bool sideBarBelow: false
    function placeBelow() {
        const main = mainContent.parent, side = sideBar.parent;
        if (!main || !side)
            return;
        const below = EaStyle.Sizes.sideBarBelow;
        if (below) {
            side.anchors.left = undefined;
            side.anchors.right = undefined;
            side.anchors.top = undefined;
            side.anchors.left = page.left;
            side.anchors.right = page.right;
            side.anchors.bottom = page.bottom;
            // Half the window's height (the owner, 2026-11-23), less what the project's pattern needs (2026-11-24).
            side.height = Qt.binding(() => AppSizes.bottomSideBarHeight(page.height, page.Window.height > 0 ? page.Window.height : page.height, Session.project ? Session.project.patternBraggRows : 0));
            main.anchors.left = undefined;
            main.anchors.right = undefined;
            main.anchors.bottom = undefined;
            main.anchors.left = page.left;
            main.anchors.right = page.right;
            main.anchors.top = page.top;
            main.anchors.bottom = side.top;
        } else if (sideBarBelow) {
            side.anchors.top = undefined;
            side.anchors.bottom = undefined;
            side.anchors.left = undefined;
            side.anchors.right = undefined;
            main.anchors.top = undefined;
            main.anchors.bottom = undefined;
            main.anchors.left = undefined;
            main.anchors.right = undefined;
            side.anchors.top = page.top;
            side.anchors.bottom = page.bottom;
            main.anchors.top = page.top;
            main.anchors.bottom = page.bottom;
            // Anchoring both edges below replaced the base's width binding; it is given back.
            side.width = Qt.binding(() => EaStyle.Sizes.sideBarWidth);
            if (Preferences.sideBarOnLeft) {
                side.anchors.left = page.left;
                main.anchors.left = side.right;
                main.anchors.right = page.right;
            } else {
                side.anchors.right = page.right;
                main.anchors.left = page.left;
                main.anchors.right = side.left;
            }
            ApplicationInfo.placeWorkflowSidebar();
            followOwnBorder();
        }
        sideBarBelow = below;
    }
    Connections {
        target: EaStyle.Sizes
        // Later, once the width and every other binding of the switch have settled.
        function onSideBarBelowChanged() {
            Qt.callLater(page.placeSideBar);
        }
    }
    // Hides the sidebar's own border, the base's thin child beside it, while the one main view draws a fixed one: the
    // page's border would slide with the page and pass under the main view.
    property bool ownBorderHidden: false
    // The side border's colour, read from the base's border, for the one drawn above the sidebar when it is below.
    property color borderColour: "transparent"
    function followOwnBorder() {
        const host = sideBar.parent;
        for (let index = 0; host && index < host.children.length; ++index) {
            const child = host.children[index];
            if (child !== sideBar && child !== belowBorder && child.width === EaStyle.Sizes.borderThickness) {
                child.visible = Qt.binding(() => !page.ownBorderHidden && !page.sideBarBelow);
                if (child.color !== undefined)
                    page.borderColour = Qt.binding(() => child.color);
            }
        }
    }
    // Below the main view the sidebar is parted from it by the same border, run along its top, full width, above its
    // tab bar (the owner, 2026-11-23).
    Rectangle {
        id: belowBorder
        objectName: "workflow." + page.pageName + ".belowBorder"
        parent: sideBar.parent
        visible: page.sideBarBelow
        z: 10
        anchors.left: parent ? parent.left : undefined
        anchors.right: parent ? parent.right : undefined
        anchors.top: parent ? parent.top : undefined
        height: EaStyle.Sizes.borderThickness
        color: page.borderColour
    }

    Connections {
        target: Preferences
        function onSideBarSideChanged() {
            page.placeSideBar();
        }
    }

    // The sidebar's width as asked and as drawn, in the log at start and after each resize of the shown page: a
    // platform where the two differ shows it there (the owner, 2026-11-21: narrow on macOS, right on Linux).
    function logSideBar() {
        if (page.current && sideBar.parent)
            console.info(`sidebar: page ${page.pageName} window ${page.Window.width} appWidth ${AppSizes.appWidth} sideBarWidth ${EaStyle.Sizes.sideBarWidth} side ${sideBar.parent.width} below ${EaStyle.Sizes.sideBarBelow} switch ${AppSizes.sideBarBelowWidth} tabs ${AppSizes.mainTabsWidth}`);
    }
    Connections {
        target: sideBar.parent
        function onWidthChanged() {
            Qt.callLater(page.logSideBar);
        }
    }
    Connections {
        target: AppSizes
        function onAppWidthChanged() {
            Qt.callLater(page.logSideBar);
        }
    }

    // The Text tab knows whether it is shown and which block the page shows, so leaving an edit not yet applied asks
    // first; kept, the page, the tab and the block come back (edi ADR-0017 §7).
    property int pageIndex: -1
    // The Text tab's edit is not yet applied: its loader stays active until the user discards it. Set from the tab's
    // signal, so the loader's `active` never reads its own item.
    property bool textDirty: false
    onCurrentChanged: {
        ApplicationInfo.workflowCurrentChanged();
        Qt.callLater(page.logSideBar);
    }
    Binding {
        target: textLoader.item
        property: "shown"
        value: page.current && textLoader.SwipeView.isCurrentItem
        when: textLoader.item !== null && page.textItem !== null && page.textEnabled
    }
    Binding {
        target: textLoader.item
        property: "blockIndex"
        value: page.blockIndex
        when: textLoader.item !== null && page.textItem !== null && page.textEnabled
    }
    // The run log's line for a sidebar tab chosen on the shown page.
    Connections {
        target: textTabButton.TabBar.tabBar
        function onCurrentIndexChanged() {
            if (page.current)
                RunLog.note(`${page.pageName} sidebar tab: ${["basic", "extras", "text", "settings"][textTabButton.TabBar.tabBar.currentIndex] ?? textTabButton.TabBar.tabBar.currentIndex}`);
        }
    }
    Connections {
        target: textLoader.item
        ignoreUnknownSignals: true
        function onDirtyChanged() {
            ApplicationInfo.workflowDirtyChanged();
        }
        function onStayRequested() {
            ApplicationInfo.workflowStayRequested();
        }
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
            current: page.current
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

    // The sidebar's width choice at the right end of its tab bar, its right edge where the groups' pins end (the owner,
    // 2026-11-22), and in Manual the sidebar's left edge to drag.
    SideBarWidthButton {
        parent: sideBar
        z: 2
        visible: !EaStyle.Sizes.sideBarBelow
        anchors.right: parent ? parent.right : undefined
        // The groups' pins end at the content's right padding; the icon, as wide as a pin, ends there too.
        anchors.rightMargin: EaStyle.Sizes.sideBarPadding
        y: Math.round((EaStyle.Sizes.tabBarHeight - height) / 2)
    }
    MouseArea {
        parent: sideBar
        z: 2
        visible: Preferences.sideBarWidthMode === "manual" && !EaStyle.Sizes.sideBarBelow
        x: -Math.round(EaStyle.Sizes.fontPixelSize * 0.3)
        width: Math.round(EaStyle.Sizes.fontPixelSize * 0.6)
        height: parent ? parent.height : 0
        cursorShape: Qt.SplitHCursor
        property real startX: 0
        property int startWidth: 0
        onPressed: mouse => {
            startX = mapToItem(null, mouse.x, 0).x;
            startWidth = EaStyle.Sizes.sideBarWidth;
        }
        onPositionChanged: mouse => {
            if (pressed)
                Preferences.sideBarManualWidth = Math.round(Math.max(EaStyle.Sizes.fontPixelSize * 20, Math.min(AppSizes.sideBarMaximumFor(AppSizes.appWidth), startWidth - (mapToItem(null, mouse.x, 0).x - startX))));
        }
    }

    sideBar: EaComponents.SideBar {
        id: sideBar
        objectName: "workflow." + page.pageName + ".manualSidebar"
        // Laid out only on the shown page: the sidebar's width is one for every page, and a change of it on a page
        // switch laid every page's sidebar out again (ADR-0102; the owner, 2026-11-23).
        visible: page.current
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
            },
            EaElements.TabButton {
                id: textTabButton
                objectName: "sideBar.tab.text"
                text: qsTr("Text")
            },
            EaElements.TabButton {
                objectName: "sideBar.tab.tools"
                text: qsTr("Tools")
            },
            EaElements.TabButton {
                objectName: "sideBar.tab.settings"
                text: qsTr("Settings")
            }
        ]

        // As the main area's pages (MainView): a tab that is not the current one draws nothing, while staying loaded and
        // visible for everything that reads it.
        items: [
            Loader {
                id: basicLoader
                opacity: SwipeView.isCurrentItem ? 1 : 0
            },
            Loader {
                id: extrasLoader
                opacity: SwipeView.isCurrentItem ? 1 : 0
                sourceComponent: page.extrasItem === null ? inviteNote : page.extrasEnabled ? page.extrasItem : waitingNote
            },
            // Text is loaded only while its tab is shown, a block's text can be the whole data loop, or while it
            // holds an edit not yet applied, until the user discards it.
            Loader {
                id: textLoader
                opacity: SwipeView.isCurrentItem ? 1 : 0
                active: SwipeView.isCurrentItem || page.textDirty
                sourceComponent: page.textItem === null ? inviteNote : page.textEnabled ? page.textItem : waitingNote
                onItemChanged: ApplicationInfo.workflowTextItemChanged()
            },
            Loader {
                id: toolsLoader
                opacity: SwipeView.isCurrentItem ? 1 : 0
                sourceComponent: page.toolsItem ?? inviteNote
            },
            Loader {
                id: settingsLoader
                opacity: SwipeView.isCurrentItem ? 1 : 0
                sourceComponent: page.settingsItem ?? inviteNote
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
        // Continue; with Continue the other tabs keep that, and without it every tab reaches the bottom, so a table can
        // use that strip (T7).
        Binding {
            target: basicLoader.SwipeView.view ? basicLoader.SwipeView.view.anchors : null
            property: "bottomMargin"
            when: textLoader.SwipeView.isCurrentItem || !page.continueShown
            value: page.continueShown ? -(sideBar.continueButton.height + sideBar.continueButton.anchors.bottomMargin) : 0
        }
    }

    // An empty tab's line, where a group's content starts, in the minor text colour.
    component TabNote: Text {
        x: EaStyle.Sizes.fontPixelSize
        topPadding: EaStyle.Sizes.fontPixelSize
        width: EaStyle.Sizes.sideBarContentWidth
        wrapMode: Text.WordWrap
        textFormat: Text.StyledText
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        color: EaStyle.Colors.themeForegroundMinor
        linkColor: EaStyle.Colors.themeAccent

        HoverHandler {
            cursorShape: parent.hoveredLink !== "" ? Qt.PointingHandCursor : Qt.ArrowCursor
        }
    }
    Component {
        id: waitingNote
        TabNote {
            objectName: "sideBar.note.waiting"
            text: qsTr("Nothing to show yet: start in the Main tab")
        }
    }
    Component {
        id: inviteNote
        TabNote {
            objectName: "sideBar.note.invite"
            text: qsTr("Nothing here yet. What would you like this tab to hold? <a href=\"idea\">Share your idea</a>")
            onLinkActivated: AppState.feedbackRequested("idea", "")
        }
    }
}
