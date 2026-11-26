// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The "Shared" column title's menu (edi ADR-0107), in the Free menu's style: share or unshare every row the filters show,
// or only the peak profile and instrument rows, each one Undo step.
EaElements.Menu {
    id: menu
    objectName: "parameters.sharedHeader.menu"

    property ProjectViewModel project: null
    property ParameterFilterModel filter: null

    // The shown rows, read when the menu opens and when a choice is made.
    function shownRows(profileOnly) {
        const rows = [];
        if (!menu.filter) return rows;
        for (let i = 0; i < menu.filter.rowCount(); ++i) {
            const item = menu.filter.parameterAt(i);
            if (!item || !item.refinable) continue;
            if (profileOnly && item.category !== "peak" && item.category !== "instrument") continue;
            rows.push(item);
        }
        return rows;
    }
    function apply(rows, shared) {
        if (menu.project) menu.project.setParametersShared(rows, shared);
        menu.close();
    }

    property var shown: []
    property int sharedCount: 0
    property int profileCount: 0
    onAboutToShow: {
        shown = shownRows(false);
        sharedCount = shown.filter(item => item.shared).length;
        profileCount = shownRows(true).length;
    }

    parent: Overlay.overlay
    anchors.centerIn: Overlay.overlay
    width: layout.implicitWidth
    verticalPadding: 0

    component ChoiceRow: EaElements.RadioButton {
        property bool selected: false
        signal chosen

        implicitHeight: AppSizes.legendRowHeight
        padding: 0
        autoExclusive: false
        checked: selected
        onClicked: chosen()
    }

    Column {
        id: layout

        padding: AppSizes.listItemPadding
        spacing: EaStyle.Sizes.comboBoxHeight - AppSizes.legendRowHeight

        ChoiceRow {
            objectName: "parameters.sharedHeader.shared"
            text: qsTr("Shared · all %1").arg(menu.shown.length)
            enabled: menu.shown.length > 0
            selected: menu.shown.length > 0 && menu.sharedCount === menu.shown.length
            onChosen: menu.apply(menu.shownRows(false), true)
        }
        ChoiceRow {
            objectName: "parameters.sharedHeader.notShared"
            text: qsTr("Not shared · all %1").arg(menu.shown.length)
            enabled: menu.shown.length > 0
            selected: menu.shown.length > 0 && menu.sharedCount === 0
            onChosen: menu.apply(menu.shownRows(false), false)
        }
        ChoiceRow {
            objectName: "parameters.sharedHeader.profile"
            text: qsTr("Profile and instrument → shared · %1").arg(menu.profileCount)
            enabled: menu.profileCount > 0
            onChosen: menu.apply(menu.shownRows(true), true)
        }
    }
}
