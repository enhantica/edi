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

    // The column's children in the order it lays them out. A Repeater's delegates are added at the end of the
    // children and only then moved behind the Repeater, with no change signal, so a group after a Repeater would
    // stay "not last". The delegates are taken from their Repeater, in its place.
    function orderedChildren(parent) {
        const children = [];
        for (let i = 0; parent && i < parent.children.length; ++i)
            children.push(parent.children[i]);
        const repeaters = children.filter(child => typeof child.itemAt === "function" && typeof child.count === "number");
        const repeated = [];
        for (const repeater of repeaters) {
            for (let i = 0; i < repeater.count; ++i)
                repeated.push(repeater.itemAt(i));
        }
        const ordered = [];
        for (const child of children) {
            if (repeaters.includes(child)) {
                for (let i = 0; i < child.count; ++i) {
                    if (child.itemAt(i) !== null)
                        ordered.push(child.itemAt(i));
                }
            } else if (!repeated.includes(child)) {
                ordered.push(child);
            }
        }
        return ordered;
    }

    function shownGroups(group) {
        const siblings = orderedChildren(group ? group.parent : null);
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
