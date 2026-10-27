// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// One `.edi` category of a block as a sidebar group: the base's GroupBox, named `group.<category
// id>`, its title, icon and title tooltip (the `.edi` category it shows) from the category model (a loop's row count
// in the title), and the category's own content — a component per category id — inside. Used as the delegate of a Repeater
// over a CategoryListModel, so a group exists exactly when the core returns its category.
EaElements.GroupBox {
    id: group

    required property var model
    // Which sidebar tab this group is in, and each category's content by id.
    property string shownTier: "Basic"
    property var contents: ({})
    // A category with no content of its own gets the group the app makes from the dictionary and the block's text.
    property BlockText textSource: null
    property Component fallback: generatedContent
    // Whether the block holds measured data: a category only of use with it is hidden without (the owner, 2026-10-27).
    property bool measured: true

    readonly property string categoryId: model.categoryId
    // The key its open or closed state is kept by, across the blocks the page shows.
    readonly property string openKey: `${shownTier}:${categoryId}`

    // A Basic category with an Extras part has a group in each tab; `contents` is the tab's own.
    readonly property bool extrasPart: shownTier === "Extras" && model.tier !== "Extras" && model.extrasPart
    readonly property bool shown: (model.tier === shownTier || extrasPart) && (measured || !(extrasPart ? model.extrasNeedsData : model.needsData))
    // Among the groups its tab lists (SideBarGroups).
    readonly property bool listed: shown

    objectName: `group.${categoryId}`
    visible: shown
    // Folded at first, as every foldable group (the base's default), then as the user left it, also when the
    // page shows another block; the tab's last shown one has no bottom border (edi ADR-0017 §3; SideBarGroups).
    collapsed: !SideBarGroups.isOpen(openKey, group)
    onCollapsedChanged: SideBarGroups.setOpen(openKey, !collapsed, group)
    last: SideBarGroups.isLast(group)
    title: extrasPart && model.extrasTitle !== "" ? model.extrasTitle : model.isLoop ? `${model.title} (${model.itemCount})` : model.title
    icon: model.icon

    EaElements.ToolTip {
        parent: group.titleArea
        text: group.model.toolTip
        visible: text !== "" && group.titleArea.hovered && EaGlobals.Vars.showToolTips
    }

    Loader {
        sourceComponent: group.contents[group.categoryId] ?? group.fallback
    }
    Component {
        id: generatedContent
        GeneratedGroup {
            // Read only while open: the text is a save of the project.
            source: group.collapsed ? null : group.textSource
            categoryId: group.categoryId
        }
    }
}
