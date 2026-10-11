// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// The "free" column title's menu, in the parameter menu's style: whether the rows the filters show are all free, all
// fixed or mixed, and Free or Fixed to make them so at once, one Undo step (the owner, 2026-10-11). Mixed is a state,
// never a choice. Rows that can never be fitted (a fixed setting, a coordinate the symmetry fixes) are not counted.
EaElements.Menu {
    id: menu

    property ProjectViewModel project: null
    property ParameterFilterModel filter: null

    // The shown rows that can be fitted, and how many of them are free. Reading each row's `free` keeps it live.
    readonly property var shown: {
        const rows = [];
        if (menu.filter === null || menu.project === null)
            return rows;
        // The filters and the project's counts change when rows come and go.
        void menu.filter.nameFilter;
        void menu.filter.categoryFilter;
        void menu.filter.variability;
        void menu.project.parameters.freeCount;
        for (let i = 0; i < menu.filter.rowCount(); ++i) {
            const parameter = menu.filter.parameterAt(i);
            if (parameter !== null && parameter.fittable && parameter.refinable)
                rows.push(parameter);
        }
        return rows;
    }
    readonly property int freeCount: shown.filter(parameter => parameter.free).length
    readonly property int fixedCount: shown.length - freeCount

    function apply(free) {
        if (menu.project !== null)
            menu.project.setParametersFree(menu.shown, free);
        menu.close();
    }

    width: layout.implicitWidth

    // Three rows, each an Analysis-table row high, a count right after its label (the owner, 2026-10-11).
    component StateRow: Row {
        id: stateRow

        property string buttonName: ""
        property string label: ""
        property string count: ""
        property bool choosable: true
        property bool selected: false
        property bool active: true
        signal chosen

        height: EaStyle.Sizes.tableRowHeight
        spacing: 0.5 * EaStyle.Sizes.fontPixelSize

        EaElements.RadioButton {
            objectName: stateRow.buttonName
            anchors.verticalCenter: parent.verticalCenter
            verticalPadding: 0
            text: stateRow.label
            autoExclusive: false
            checkable: stateRow.choosable
            enabled: stateRow.active
            checked: stateRow.selected
            onClicked: stateRow.chosen()
        }
        EaElements.Label {
            anchors.verticalCenter: parent.verticalCenter
            color: EaStyle.Colors.themeForegroundMinor
            text: stateRow.count
        }
    }

    Column {
        id: layout

        leftPadding: 0.75 * EaStyle.Sizes.fontPixelSize
        rightPadding: 1.25 * EaStyle.Sizes.fontPixelSize

        StateRow {
            buttonName: "parameters.freeHeader.free"
            label: qsTr("Free")
            count: qsTr("all %1").arg(menu.shown.length)
            active: menu.shown.length > 0
            selected: menu.shown.length > 0 && menu.fixedCount === 0
            onChosen: menu.apply(true)
        }
        StateRow {
            buttonName: "parameters.freeHeader.fixed"
            label: qsTr("Fixed")
            count: qsTr("all %1").arg(menu.shown.length)
            active: menu.shown.length > 0
            selected: menu.shown.length > 0 && menu.freeCount === 0
            onChosen: menu.apply(false)
        }
        StateRow {
            buttonName: "parameters.freeHeader.mixed"
            label: qsTr("Mixed")
            count: qsTr("%1 free · %2 fixed").arg(menu.freeCount).arg(menu.fixedCount)
            choosable: false
            active: menu.freeCount > 0 && menu.fixedCount > 0
            selected: active
        }
    }
}
