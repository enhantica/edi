// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import edi.app

// Where a sidebar group stands among the groups its tab shows (edi ADR-0017 §3): the first shown starts unfolded,
// and the last shown draws no bottom border. The base's GroupBox takes its `last` from its parent's
// last child, which in a column with a Repeater is the last delegate whether or not it is shown
// (gui-components#55), so edi's groups set `last` from here. A group is a sibling with the base GroupBox's
// `collapsible`. A category group says whether its tab lists it in `listed` (CategoryGroup); a group without one
// is always listed. Neither `visible` nor a group's own `shown` (the Report page's mean "the page is on screen"):
// both change as the page is shown, one group before another, and the order must not change with that.
QtObject {
    // Each group's open or closed state, by its tab and key, once the user has opened or closed it. Showing another
    // block rebuilds the page's groups, and each new group opens or stays closed as its predecessor was left.
    // Another project starts with nothing remembered again.
    property var openStates: ({})
    readonly property var project: Session.project
    onProjectChanged: openStates = {}

    // Open as the user left it; with nothing remembered, open when it is the first group its tab shows and closed
    // otherwise: the first group of every tab of every page starts unfolded (the owner, 2026-10-25).
    function isOpen(key, group) {
        return ApplicationInfo.sidebarIsOpen(key, group);
    }

    // Remembered once it differs from what the group would show by default: a group the user opened or folded.
    function setOpen(key, open, group) {
        ApplicationInfo.sidebarSetOpen(key, open, group);
    }

    function defaultOpen(group) {
        return ApplicationInfo.sidebarEdge(group, false);
    }

    // The column's children in the order it lays them out. A Repeater's delegates are added at the end of the
    // children and only then moved behind the Repeater, with no change signal, so a group after a Repeater would
    // stay "not last". The delegates are taken from their Repeater, in its place.
    function orderedChildren(parent) {
        return ApplicationInfo.sidebarOrderedChildren(parent);
    }

    function shownGroups(group) {
        return ApplicationInfo.sidebarShownGroups(group);
    }

    function isLast(group) {
        return ApplicationInfo.sidebarEdge(group, true);
    }
}
