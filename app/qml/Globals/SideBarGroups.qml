// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import edi.app

// Where a sidebar group stands among the groups its tab shows (edi ADR-0017 §3): the last shown draws no
// bottom border. The base's GroupBox takes its `last` from its parent's
// last child, which in a column with a Repeater is the last delegate whether or not it is shown
// (gui-components#55), so edi's groups set `last` from here. A group is a sibling with the base GroupBox's
// `collapsible`. A category group says whether its tab shows it in `shown` (CategoryGroup); a group without
// one is always shown. `shown`, not `visible`: an item's `visible` is also false while its page is hidden, and
// the order must not change with that.
QtObject {
    // Each category group's open or closed state, by its tab and category id. Showing another block rebuilds
    // the page's groups, and each new group opens or stays closed as its predecessor was left. Another project
    // starts with every group closed again.
    property var openStates: ({})
    readonly property var project: Session.project
    onProjectChanged: openStates = {}

    function isOpen(key) {
        return openStates[key] === true;
    }

    function setOpen(key, open) {
        openStates[key] = open;
    }

    function shownGroups(group) {
        const siblings = group && group.parent ? group.parent.children : [];
        const shown = [];
        for (let i = 0; i < siblings.length; ++i) {
            const sibling = siblings[i];
            if (typeof sibling.collapsible !== "undefined" && (typeof sibling.shown === "undefined" || sibling.shown))
                shown.push(sibling);
        }
        return shown;
    }

    function isLast(group) {
        const shown = shownGroups(group);
        return shown.length > 0 && shown[shown.length - 1] === group;
    }
}
