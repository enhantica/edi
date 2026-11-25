// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents
import edi.app

// The app's curated example catalogue (ADR-0031). Filtering never changes an example's identity.
SideBarGroup {
    id: group
    // The tab's last shown group draws no bottom border (edi ADR-0017 section 3).
    last: SideBarGroups.isLast(group)
    objectName: "group.examples"
    title: qsTr("Examples")
    icon: "database"

    Column {
        // Hidden while collapsed, so each row's accessible box is placed when it shows: the web platform does
        // not move an accessible box when only an ancestor moves.
        visible: !group.collapsed || group.implicitHeight > group.topPadding
        spacing: AppSizes.groupContentSpacing
        ExampleFilters {
            catalogue: Session.examples
        }
        TagRowsWidth {
            id: tagWidths
            model: Session.examples
        }
        // Why no example can be opened: every online source holding the projects failed (ADR-0068).
        EaElements.Label {
            objectName: "examples.notice"
            visible: Session.examplesNotice !== ""
            width: parent.width
            wrapMode: Text.WordWrap
            text: Session.examplesNotice
        }
        DataTable {
            id: table
            objectName: "examples.list"
            // One line more when the widest tag row does not fit the sidebar's cell: the tags wrap, never cut short. The
            // cell is the row less its number, the column margin, the row's padding and borders, and the cell's own insets.
            readonly property bool tagsWrap: tagWidths.widest > table.width - table.numberColumnWidth - table.autoColumnPadding - table.rowPadding * 2 - EaStyle.Sizes.borderThickness * 2 - EaStyle.Sizes.fontPixelSize * 2
            // The rows' least height; a row whose tags wrap grows to its own lines (the delegate's height).
            tableRowHeight: Math.ceil(EaStyle.Sizes.fontPixelSize * (table.tagsWrap ? 7.4 : 5.5))
            // Every row kept once made, so scrolling up and down again makes none anew (the owner, 2026-11-21: "not
            // smooth when scrolling - even if scroll up and down multiple times"). The list is short and shows before
            // any project, so the rows made ahead hold no page's layout back. In the browser the rows in view only, as each
            // row made there also makes its accessible elements, all of them at once when the group opens.
            cacheBuffer: Qt.platform.os === "wasm" ? 0 : Math.max(0, table.count * table.tableRowHeight)
            defaultInfoText: qsTr("No matching examples")
            sourceModel: Session.examples
            // Its columns by kind (the shared column model, DataTable.columnKinds; ADR-0103 decision 4).
            columnKinds: ["index", "name"]
            // Widths from column types, not rows (ADR-0103 rule 4): the name and description.
            header: EaComponents.ListViewHeader {
                visible: false
                implicitHeight: 0
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Name / description")
                }
            }
            delegate: TableRow {
                id: row
                required property string exampleId
                required property string sample
                required property string origin
                required property string detail
                required property list<string> tagLabels
                required property list<string> tagIcons
                required property list<string> tagColors
                required property list<string> tagDarkColors
                objectName: `examples.open.${exampleId}`
                // As tall as its own lines, at least the table's row: a row whose tags wrap to a second line overlapped
                // the next one when every row took the first row's height (the owner, 2026-11-22).
                height: Math.max(table.tableRowHeight, Math.ceil(exampleCell.implicitHeight + EaStyle.Sizes.fontPixelSize))
                onHeightChanged: table.noteRowHeight(index, height)
                onIndexChanged: table.noteRowHeight(index, height)
                // Screen readers and browser checks find a row by its id and title, which the three lines show
                // only in part. The row itself carries them, as the list moves the row.
                Accessible.role: Accessible.Button
                Accessible.name: `${row.exampleId}: ${row.sample} · ${row.origin}`
                Accessible.description: row.detail
                Accessible.onPressAction: ApplicationInfo.openProjectRow(false, false)
                MouseArea {
                    parent: row
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: ApplicationInfo.openProjectRow(false, true)
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                ExampleCell {
                    id: exampleCell
                    height: row.height
                    title: row.sample + " · " + row.origin
                    tagLabels: row.tagLabels
                    tagIcons: row.tagIcons
                    tagColors: row.tagColors
                    tagDarkColors: row.tagDarkColors
                    detail: row.detail
                }
            }
        }
    }
}
