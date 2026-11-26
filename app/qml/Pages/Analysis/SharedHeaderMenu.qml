// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The "Shared" column title's menu (edi ADR-0107), a copy of the Free title's (FreeHeaderMenu): whether the rows the
// filters show are all shared, none shared or mixed, and Shared or Not shared to make them so at once, one Undo step.
// Mixed is a state, never a choice. A parameter set by a relation or by symmetry is not counted.
EaElements.Menu {
    id: menu
    objectName: "parameters.sharedHeader.menu"

    property ProjectViewModel project: null
    property ParameterFilterModel filter: null

    // The shown rows that can be shared, as the filter model has them when the menu is open.
    function shownRows() {
        const rows = [];
        if (!menu.filter)
            return rows;
        for (let i = 0; i < menu.filter.rowCount(); ++i) {
            const item = menu.filter.parameterAt(i);
            if (item && item.refinable)
                rows.push(item);
        }
        return rows;
    }

    readonly property var shown: menu.visible ? menu.shownRows() : []
    readonly property int sharedCount: menu.shown.filter(item => item.shared).length
    readonly property int notSharedCount: shown.length - sharedCount

    // Shared or Not shared acts on the rows shown when it is chosen.
    function apply(shared) {
        if (menu.project)
            menu.project.setParametersShared(menu.shownRows(), shared);
        menu.close();
    }

    // Centred in the app window, as the Free menu is.
    parent: Overlay.overlay
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    anchors.centerIn: Overlay.overlay
    width: layout.implicitWidth
    verticalPadding: 0

    component StateRow: EaElements.RadioButton {
        property bool choosable: true
        property bool selected: false
        property bool active: true
        signal chosen

        implicitHeight: AppSizes.legendRowHeight
        padding: 0
        autoExclusive: false
        checkable: choosable
        enabled: active
        checked: selected
        onClicked: chosen()
    }

    Column {
        id: layout

        padding: AppSizes.listItemPadding
        spacing: EaStyle.Sizes.comboBoxHeight - AppSizes.legendRowHeight

        StateRow {
            objectName: "parameters.sharedHeader.shared"
            text: qsTr("Shared · all %1").arg(menu.shown.length)
            active: menu.shown.length > 0
            selected: menu.shown.length > 0 && menu.notSharedCount === 0
            onChosen: menu.apply(true)
        }
        StateRow {
            objectName: "parameters.sharedHeader.notShared"
            text: qsTr("Not shared · all %1").arg(menu.shown.length)
            active: menu.shown.length > 0
            selected: menu.shown.length > 0 && menu.sharedCount === 0
            onChosen: menu.apply(false)
        }
        StateRow {
            objectName: "parameters.sharedHeader.mixed"
            text: qsTr("Mixed · %1 shared · %2 not shared").arg(menu.sharedCount).arg(menu.notSharedCount)
            choosable: false
            active: menu.sharedCount > 0 && menu.notSharedCount > 0
            selected: active
        }
    }
}
