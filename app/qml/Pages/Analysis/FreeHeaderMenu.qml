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

    Grid {
        id: layout

        leftPadding: 1.25 * EaStyle.Sizes.fontPixelSize
        rightPadding: 1.25 * EaStyle.Sizes.fontPixelSize
        topPadding: 0.5 * EaStyle.Sizes.fontPixelSize
        bottomPadding: 0.75 * EaStyle.Sizes.fontPixelSize
        rowSpacing: 0.25 * EaStyle.Sizes.fontPixelSize
        columnSpacing: 1.5 * EaStyle.Sizes.fontPixelSize
        columns: 2
        verticalItemAlignment: Grid.AlignVCenter

        EaElements.Label {
            color: EaStyle.Colors.themeForegroundMinor
            text: menu.shown.length === 1 ? qsTr("Free · 1 shown parameter") : qsTr("Free · %1 shown parameters").arg(menu.shown.length)
        }
        Item {
            width: 1
            height: 1
        }

        EaElements.RadioButton {
            objectName: "parameters.freeHeader.free"
            text: qsTr("Free")
            autoExclusive: false
            enabled: menu.shown.length > 0
            checked: menu.shown.length > 0 && menu.fixedCount === 0
            onClicked: menu.apply(true)
        }
        EaElements.Label {
            color: EaStyle.Colors.themeForegroundMinor
            text: qsTr("all %1").arg(menu.shown.length)
        }

        EaElements.RadioButton {
            objectName: "parameters.freeHeader.fixed"
            text: qsTr("Fixed")
            autoExclusive: false
            enabled: menu.shown.length > 0
            checked: menu.shown.length > 0 && menu.freeCount === 0
            onClicked: menu.apply(false)
        }
        EaElements.Label {
            color: EaStyle.Colors.themeForegroundMinor
            text: qsTr("all %1").arg(menu.shown.length)
        }

        EaElements.RadioButton {
            objectName: "parameters.freeHeader.mixed"
            text: qsTr("Mixed")
            autoExclusive: false
            checkable: false
            enabled: menu.freeCount > 0 && menu.fixedCount > 0
            checked: enabled
        }
        EaElements.Label {
            color: EaStyle.Colors.themeForegroundMinor
            text: qsTr("%1 free · %2 fixed").arg(menu.freeCount).arg(menu.fixedCount)
        }

        EaElements.Label {
            topPadding: 0.5 * EaStyle.Sizes.fontPixelSize
            color: EaStyle.Colors.themeForegroundMinor
            text: qsTr("Applies to the rows the filters show. Undo with Ctrl+Z.")
        }
    }
}
