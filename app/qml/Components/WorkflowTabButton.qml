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

    width: Math.max(boldName.implicitWidth + tab.font.pixelSize * 1.5 + tab.leftInset + tab.rightInset, tab.implicitContentWidth + tab.leftPadding + tab.rightPadding)

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
