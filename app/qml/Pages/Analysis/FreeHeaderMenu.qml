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

    // Counts every change of the rows the filters show (a filter, rows that come or go, a scan experiment switch), as
    // the table's selection follows them (ParametersGroup): reading a row of the filter model does not follow them.
    property int membership: 0

    // The shown rows that can be fitted, as the filter model has them now.
    function fittableRows() {
        const rows = [];
        if (menu.filter === null || menu.project === null)
            return rows;
        for (let i = 0; i < menu.filter.rowCount(); ++i) {
            const parameter = menu.filter.parameterAt(i);
            if (parameter !== null && parameter.fittable && parameter.refinable)
                rows.push(parameter);
        }
        return rows;
    }

    // The shown rows that can be fitted, and how many of them are free. Reading each row's `free` keeps it live. The
    // count is used, not only read: the compiled binding drops a read whose value is unused (`void x`), and with it
    // the dependency.
    readonly property var shown: menu.membership >= 0 ? menu.fittableRows() : []
    readonly property int freeCount: shown.filter(parameter => parameter.free).length
    readonly property int fixedCount: shown.length - freeCount

    // Free or Fixed acts on the rows shown when it is chosen.
    function apply(free) {
        if (menu.project !== null)
            menu.project.setParametersFree(menu.fittableRows(), free);
        menu.close();
    }

    Connections {
        target: menu.filter
        function onRowsInserted() {
            ++menu.membership;
        }
        function onRowsRemoved() {
            ++menu.membership;
        }
        function onModelReset() {
            ++menu.membership;
        }
        function onLayoutChanged() {
            ++menu.membership;
        }
    }
    Connections {
        target: menu.project
        function onCurrentExperimentIndexChanged() {
            ++menu.membership;
        }
    }

    width: layout.implicitWidth
    verticalPadding: 0

    // Three rows, each one text ("Free · all 48"), a filter combo box's list entry apart; the same margin on every
    // side, the list entries' side padding (the owner, 2026-10-11 and 2026-10-12).
    component StateRow: EaElements.RadioButton {
        property bool choosable: true
        property bool selected: false
        property bool active: true
        signal chosen

        // One text line high: the button's own height counts its touch area, which would widen the top and bottom
        // margins past the sides'.
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
            objectName: "parameters.freeHeader.free"
            text: qsTr("Free · all %1").arg(menu.shown.length)
            active: menu.shown.length > 0
            selected: menu.shown.length > 0 && menu.fixedCount === 0
            onChosen: menu.apply(true)
        }
        StateRow {
            objectName: "parameters.freeHeader.fixed"
            text: qsTr("Fixed · all %1").arg(menu.shown.length)
            active: menu.shown.length > 0
            selected: menu.shown.length > 0 && menu.freeCount === 0
            onChosen: menu.apply(false)
        }
        StateRow {
            objectName: "parameters.freeHeader.mixed"
            text: qsTr("Mixed · %1 free · %2 fixed").arg(menu.freeCount).arg(menu.fixedCount)
            choosable: false
            active: menu.freeCount > 0 && menu.fixedCount > 0
            selected: active
        }
    }
}
