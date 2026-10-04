// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// One `.edi` category of a block as a sidebar group: the base's GroupBox, named `group.<category
// id>`, its title and icon from the category model (a loop's row count in the title), and the
// category's own content — a component per category id — inside. Used as the delegate of a Repeater
// over a CategoryListModel, so a group exists exactly when the core returns its category.
EaElements.GroupBox {
    id: group

    required property var model
    // Which sidebar tab this group is in, and each category's content by id.
    property string shownTier: "Basic"
    property var contents: ({})
    property Component fallback: null

    readonly property string categoryId: model.categoryId

    // A Basic category with an Extras part has a group in each tab; `contents` is the tab's own.
    readonly property bool shown: model.tier === shownTier || (shownTier === "Extras" && model.extrasPart)

    objectName: `group.${categoryId}`
    visible: shown
    // Folded by default, as every foldable group (the base's default); the tab's last shown one has no bottom
    // border (edi ADR-0017 §3; SideBarGroups).
    last: SideBarGroups.isLast(group)
    title: model.isLoop ? `${model.title} (${model.itemCount})` : model.title
    icon: model.icon

    Loader {
        sourceComponent: group.contents[group.categoryId] ?? group.fallback
    }
}
