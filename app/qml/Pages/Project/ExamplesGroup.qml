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
            // One line more when the widest tag row does not fit the sidebar's cell: the tags wrap, never cut short.
            readonly property bool tagsWrap: tagWidths.widest > table.width - table.numberColumnWidth - EaStyle.Sizes.fontPixelSize * 2
            tableRowHeight: Math.ceil(EaStyle.Sizes.fontPixelSize * (table.tagsWrap ? 7.4 : 5.5))
            maxRowCountShow: 6
            defaultInfoText: qsTr("No matching examples")
            sourceModel: Session.examples
            columns: [numberColumnWidth, -1]
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
