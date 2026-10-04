// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// A main-area tab whose title is an icon and a name (edi ADR-0017 §2): the base's TabButton, its content drawn
// as one IconLine so the icon sits on the name's centre line (§10). The icon takes
// `iconColor`, or the tab's own text colour when that is empty; the name is bold while the tab is checked, as
// the base's.
EaElements.TabButton {
    id: tab

    function titleSegments() {
        const name = {
            "text": tab.text,
            "bold": tab.checked
        };
        if (tab.fontIcon === "")
            return [name];
        const icon = {
            "icon": tab.fontIcon,
            "color": tab.iconColor !== "" ? tab.iconColor : tab.foregroundColor()
        };
        return [icon, name];
    }

    contentItem: Item {
        implicitWidth: title.implicitWidth
        implicitHeight: title.implicitHeight

        IconLine {
            id: title
            anchors.centerIn: parent
            spacing: tab.spacing
            textColor: tab.foregroundColor()
            segments: tab.titleSegments()
        }
    }
}
