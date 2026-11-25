// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) 2021-2026 EasyScience contributors.
// App-owned pinned ListViewParameter overlay: its menu shows the parameter's full name with the link icon.
pragma ComponentBehavior: Bound
import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// A parameter cell of a ListViewDelegate row: the value, bold when it is
// fitted, with a context menu (right click or press and hold) showing its
// name, value, units, uncertainty and fit toggle. The menu is made the first
// time it opens, as a list can hold many parameters.
EaElements.TextInput {
    id: control

    property bool flexibleWidth: false

    property var parameter: {
        'value': 0.0,
        'idx': 0,
        'error': 0.0,
        'enabled': true,
        'fittable': false,
        'fit': false,
        'category': '',
        'fullName': '',
        'name': 'default',
        'prettyName': '',
        'title': '',
        'units': '',
        'url': '',
        'cifDict': ''
    }

    // The callers pass the value and its s.u. as text the display bridge has rounded.
    property var value: typeof parameter.value === 'undefined' ? 0 : parameter.value
    property var error: typeof parameter.error === 'undefined' ? '' : parameter.error

    property int idx: parameter.idx ?? 0
    property bool fittable: parameter.fittable ?? false
    property bool fit: parameter.fit ?? false
    property string category: parameter.category ?? ''
    // The datablock-qualified name, when the cell's parameter has one.
    property string fullName: parameter.fullName ?? ''
    property string name: parameter.name ?? 'default'
    property string prettyName: parameter.prettyName ?? ''
    property string title: parameter.title ?? ''
    property string units: parameter.units ?? ''
    property string url: parameter.url ?? ''
    property string cifDict: parameter.cifDict ?? ''

    // The menu's column titles for the uncertainty and the fit toggle.
    property string errorTitle: 'error'
    property string fitTitle: 'vary'

    // Optional, for a table that edits in its menu: the editor shown in place of the read-only value, full width;
    // the range shown beside it; and whether a left click (and Enter) opens the menu, at the cell.
    property Component editorComponent: null
    property string minimumText: ''
    property string maximumText: ''
    property bool clickOpensMenu: false
    // The value the popup shows: the cell's own, unless a cell shows a shortened form (a derived value in full).
    property string menuValue: value
    // The menu's number columns (s.u., Min, Max), header and value aligned as in a table: one width, enough for a whole
    // s.u. in either of the forms it is written in (0.00021, 1.9×10⁻⁸⁸; the owner, 2026-11-24). A number longer than
    // that is fitted as a cell's is, in full on hover.
    readonly property real menuNumberWidth: Math.ceil(Math.max(...[NumberText.ownUncertainty(1.9e-88), "0.00021"].map(text => numberMetrics.advanceWidth(text)))) + 2 * EaStyle.Sizes.fontPixelSize
    readonly property real menuNumberRoom: menuNumberWidth - 2 * (EaStyle.Sizes.fontPixelSize * 0.5 + 1)
    function menuNumber(text: string): string {
        return text === "" ? "" : NumberText.fitted(text, menuNumberRoom, numberMetrics);
    }
    FontMetrics {
        id: numberMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }

    property EaElements.Menu contextMenu: null
    // The menu's fit toggle, once the menu is made.
    property EaElements.CheckBox fitCheckBox: null
    signal fitToggled(bool checked)

    // `anchorItem`: where a menu that edits opens, under it; the cell itself unless a field row's field asks.
    function openContextMenu(parentItem, anchorItem) {
        if (contextMenu === null)
            contextMenu = contextMenuComponent.createObject(parentItem);
        const anchor = anchorItem ?? control;
        // A menu that edits opens at the cell, under it; the plain menu where the pointer is.
        if (editorComponent !== null)
            contextMenu.popup(anchor, 0, anchor.height);
        else
            contextMenu.popup();
    }

    minored: !parameter.enabled ?? false

    // The row's height; with no row yet, its own implicit height. Binding the height to
    // implicitHeight would make the text lay out in that height, which on macOS's
    // fractional line heights changed implicitHeight again: a binding loop.
    height: parent ? parent.height : undefined

    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter

    text: control.value
    font.bold: control.fit && enabled

    onAccepted: focus = false

    // Mouse area
    MouseArea {
        id: menuArea
        anchors.fill: parent
        cursorShape: undefined //Qt.PointingHandCursor
        acceptedButtons: control.clickOpensMenu ? Qt.LeftButton | Qt.RightButton : Qt.RightButton
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton || control.clickOpensMenu) {
                control.openContextMenu(menuArea);
            }
            mouse.accepted = false;
        }
        onDoubleClicked: mouse => {
            if (control.clickOpensMenu)
                control.openContextMenu(menuArea);
        }
        onPressAndHold: mouse => {
            if (mouse.source === Qt.MouseEventNotSynthesized) {
                control.openContextMenu(menuArea);
            }
            mouse.accepted = false;
        }
        // Menu
        Component {
            id: contextMenuComponent

            EaElements.Menu {
                id: parameterMenu
                objectName: control.objectName + ".popup"
                width: layout.implicitWidth
                // Inside the sidebar, a cell margin from its edges; one wider than that gives up the side the main view is on.
                readonly property bool fitsSideBar: width <= EaStyle.Sizes.sideBarWidth - 2 * AppSizes.tableCellMargin + 0.5
                readonly property real beside: fitsSideBar && !EaStyle.Sizes.sideBarBelow ? Math.max(0, AppSizes.appWidth - EaStyle.Sizes.sideBarWidth) : 0
                leftMargin: AppSizes.tableCellMargin + (Preferences.sideBarOnLeft ? 0 : beside)
                rightMargin: AppSizes.tableCellMargin + (Preferences.sideBarOnLeft ? beside : 0)
                // Typing goes to the editor as the menu opens; Escape closes it, from the editor too, which handles
                // Escape itself.
                // As it starts to show, not after its 220 ms opening animation: typing right after the click lands.
                onAboutToShow: if (editorLoader.item)
                    (editorLoader.item as Item).forceActiveFocus()
                onOpened: if (editorLoader.item && !(editorLoader.item as Item).activeFocus)
                    (editorLoader.item as Item).forceActiveFocus()
                Shortcut {
                    sequences: [StandardKey.Cancel]
                    enabled: parameterMenu.opened
                    onActivated: parameterMenu.close()
                }

                // Layout
                Grid {
                    id: layout

                    leftPadding: 1.25 * EaStyle.Sizes.fontPixelSize
                    rightPadding: 1.25 * EaStyle.Sizes.fontPixelSize
                    topPadding: 0.5 * EaStyle.Sizes.fontPixelSize
                    bottomPadding: 0.75 * EaStyle.Sizes.fontPixelSize
                    rowSpacing: 0.75 * EaStyle.Sizes.fontPixelSize
                    // Every gap between neighbouring inputs one em (the owner, 2026-11-24).
                    columnSpacing: EaStyle.Sizes.fontPixelSize

                    rows: 2
                    // Every cell of the row on one centre line: the name and s.u. sat at the top of the taller inputs
                    // (the owner, 2026-11-23).
                    verticalItemAlignment: Grid.AlignVCenter

                    // Header
                    EaElements.Label {
                        color: EaStyle.Colors.themeForegroundMinor
                        text: qsTr('Full name')
                    }
                    // With an editor (the edited value, its unit inside it) the value column has no header, and there
                    // is no units column (the owner, 2026-11-22). The empty header keeps the editor's width: the grid
                    // skips an item without width, which moved every later header a column left.
                    EaElements.Label {
                        width: control.editorComponent !== null ? editorLoader.width : implicitWidth
                        color: EaStyle.Colors.themeForegroundMinor
                        text: control.editorComponent !== null ? qsTr('Value') : 'value'
                    }
                    EaElements.Label {
                        visible: control.units !== '' && control.editorComponent === null
                        color: EaStyle.Colors.themeForegroundMinor
                        text: 'units'
                    }
                    // With an editor the s.u. is a disabled input of a fixed width, there before a fit too, so the popup's
                    // layout and width do not change with a fit (the owner, 2026-11-23, "a Value header and a fixed-width
                    // s.u. field").
                    EaElements.Label {
                        id: errorHeader
                        visible: control.editorComponent !== null || ((control.fittable || control.readOnly) && control.error !== '')
                        width: control.editorComponent !== null ? control.menuNumberWidth : implicitWidth
                        horizontalAlignment: control.editorComponent !== null ? Text.AlignRight : Text.AlignLeft
                        color: EaStyle.Colors.themeForegroundMinor
                        text: control.errorTitle
                    }
                    EaElements.Label {
                        visible: control.editorComponent !== null
                        width: control.menuNumberWidth
                        horizontalAlignment: Text.AlignRight
                        color: EaStyle.Colors.themeForegroundMinor
                        text: qsTr('Min')
                    }
                    EaElements.Label {
                        visible: control.editorComponent !== null
                        width: control.menuNumberWidth
                        horizontalAlignment: Text.AlignRight
                        color: EaStyle.Colors.themeForegroundMinor
                        text: qsTr('Max')
                    }
                    EaElements.Label {
                        visible: control.fittable && (!control.readOnly || control.editorComponent !== null)
                        color: EaStyle.Colors.themeForegroundMinor
                        text: control.fitTitle
                    }

                    // Content
                    EaElements.Button {
                        objectName: control.objectName + ".popup.docs"
                        enabled: control.url !== ''
                        fontIcon: "external-link-alt"  // opens the parameter's documentation
                        text: control.fullName !== '' ? control.fullName : `${control.category}.${control.name}`
                        checked: true
                        onClicked: Qt.openUrlExternally(control.url)
                    }
                    EaElements.Label {
                        visible: control.editorComponent === null
                        text: control.menuValue
                        font.bold: control.fit
                    }
                    Loader {
                        id: editorLoader
                        active: control.editorComponent !== null
                        visible: active
                        width: 7 * EaStyle.Sizes.fontPixelSize
                        sourceComponent: control.editorComponent
                    }
                    EaElements.Label {
                        visible: control.units !== '' && control.editorComponent === null
                        text: control.units
                        color: EaStyle.Colors.themeForegroundMinor
                    }
                    EaElements.Label {
                        visible: control.editorComponent === null && (control.fittable || control.readOnly) && control.error !== ''
                        text: control.error
                    }
                    EaElements.TextField {
                        objectName: control.objectName + ".popup.su"
                        visible: control.editorComponent !== null
                        enabled: false
                        width: control.menuNumberWidth
                        horizontalAlignment: Text.AlignRight
                        text: control.menuNumber(control.error)
                        fullText: control.error
                        shortened: text !== fullText
                    }
                    // The range as text inputs, not editable yet (the owner, 2026-11-22).
                    EaElements.TextField {
                        visible: control.editorComponent !== null
                        enabled: false
                        width: control.menuNumberWidth
                        horizontalAlignment: Text.AlignRight
                        text: control.menuNumber(control.minimumText)
                        fullText: control.minimumText
                        shortened: text !== fullText
                    }
                    EaElements.TextField {
                        visible: control.editorComponent !== null
                        enabled: false
                        width: control.menuNumberWidth
                        horizontalAlignment: Text.AlignRight
                        text: control.menuNumber(control.maximumText)
                        fullText: control.maximumText
                        shortened: text !== fullText
                    }
                    EaElements.CheckBox {
                        id: fitBox
                        objectName: control.objectName + ".popup.free"
                        visible: control.fittable && (!control.readOnly || control.editorComponent !== null)
                        padding: 0
                        checked: control.fit
                        onToggled: control.fitToggled(checked)
                        Component.onCompleted: control.fitCheckBox = fitBox
                    }
                    // Content
                }
                // Layout
            }
        }
        // Menu
    }
    // Mouse area

    // HoverHandler to react on hover events
    HoverHandler {
        id: mouseHoverHandler
        acceptedDevices: PointerDevice.AllDevices
        blocking: false
    }
}
