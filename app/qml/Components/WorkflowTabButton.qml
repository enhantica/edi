// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// A workflow tab in the top bar: the base's AppBarTabButton, always as wide as it is when selected. The base widens
// only the selected tab, for its bold name, so the centred tabs shifted whenever the page changed, and the sidebar's
// edge, read from the Experiment button, moved with them (edi ADR-0017 §12).
EaElements.AppBarTabButton {
    id: tab

    // The tab's page: while it is being built in the background the tab stays disabled and says so (edi ADR-0052).
    property Loader page: null
    property bool pageWanted: false
    readonly property bool preparing: page !== null && pageWanted && Session.hasProject && page.status !== Loader.Ready

    // Icons only in a window narrower than 600 px (ADR-0103 decision 2), each as wide as the six can be between the two
    // buttons at either side of the app bar (about 6 em a side), and never wider than 2.8 em.
    readonly property bool iconOnly: AppSizes.compact
    // The base draws the name as the second child of its content column; it is hidden, never cleared, so the button
    // keeps its text (its accessible name and every reader of it) whatever the window's width.
    Component.onCompleted: {
        const column = contentItem && contentItem.children.length > 0 ? contentItem.children[0] : null;
        if (column && column.children.length > 1)
            column.children[1].visible = Qt.binding(() => !tab.iconOnly);
    }
    width: iconOnly ? Math.min(Math.round(tab.font.pixelSize * 2.8), Math.floor((AppSizes.appWidth - tab.font.pixelSize * 12.5) / 6)) : Math.max(boldName.implicitWidth + tab.font.pixelSize * 1.5 + tab.leftInset + tab.rightInset, tab.implicitContentWidth + tab.leftPadding + tab.rightPadding)

    // The base's name label as the selected tab draws it, never shown.
    EaElements.Label {
        id: boldName

        visible: false
        font.family: tab.font.family
        font.pixelSize: tab.font.pixelSize * 0.95
        font.bold: true
        text: tab.text
    }
}
