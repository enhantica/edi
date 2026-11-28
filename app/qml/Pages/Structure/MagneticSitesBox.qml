// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The magnetic analysis toolbar's "sites" box (owner, 2026-11-28, header design B): closed, the chosen sites; open, the
// Atom sites group's table, its columns, icons and styling, read-only here, after a check box column that chooses the
// magnetic sites. At least one stays chosen. The chosen sites get the moment rows of each new structure, where their
// ions are set.
ToolbarComboBox {
    id: box

    property StructureViewModel structure: null
    // The parent's sites ({id, type}) and the chosen ids.
    property var sites: []
    property var chosen: []
    signal toggled(string id, bool on)

    readonly property AtomSiteListModel rows: structure ? structure.atomSites : null
    readonly property string shownText: qsTr("sites: %1").arg(chosen.join(", "))

    toolTip: qsTr("The magnetic sites: the sites each new structure gives a moment")
    model: [shownText]
    closedTexts: [shownText]
    fitShown: true

    // The combo box's own popup, its frame, shadow and opening as every combo list's, with the Atom sites table
    // inside instead of the list (owner, 2026-11-28). The table at its natural width, every column as wide as its
    // content, wider than the box when it needs to be: no value is cut. Until the table has measured itself, a width
    // that holds it.
    popup.objectName: "magnetic.sites.popup"
    popup.width: Math.max(table.naturalWidth > 0 ? table.naturalWidth : EaStyle.Sizes.fontPixelSize * 44, box.width)
    popup.height: Math.min(table.contentHeight, EaStyle.Sizes.tableRowHeight * 12)
    popup.padding: 0
    popup.contentItem: DataTable {
        id: table
        objectName: "magnetic.sites.list"
        clip: true
        defaultInfoText: qsTr("No atom sites")
        sourceModel: box.rows
        // The Atom sites group's columns, the row number first, and the choice last, where the app's tables keep
        // their row action (owner, 2026-11-28).
        columnKinds: ["index", "name", "short", "value", "value", "value", "short", "value", "control"]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "atom_site.id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "atom_site.type_symbol"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.fract_x"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.fract_y"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.fract_z"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.wyckoff_letter"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.occupancy"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: TableRow {
            id: row

            required property string label
            required property string typeSymbol
            required property string wyckoffLetter
            required property ParameterItem fractX
            required property ParameterItem fractY
            required property ParameterItem fractZ
            required property ParameterItem occupancy
            readonly property bool isChosen: box.chosen.indexOf(row.label) >= 0

            // The row number in the app's grey row-number style, as the Atom sites table has it.
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignLeft
                elide: Text.ElideRight
                text: row.label
            }
            // The type with its atom icon in its element's colour, as the Atom sites table shows it.
            Item {
                property int horizontalAlignment: Text.AlignLeft
                height: parent.height
                implicitWidth: typeLine.implicitWidth
                IconLine {
                    id: typeLine
                    anchors.verticalCenter: parent.verticalCenter
                    segments: [
                        {
                            "icon": row.fractX ? row.fractX.categoryIcon : "",
                            "color": AppColors.element(row.typeSymbol)
                        },
                        {
                            "text": row.typeSymbol
                        }
                    ]
                }
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                locked: true
                item: row.fractX
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                locked: true
                item: row.fractY
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                locked: true
                item: row.fractZ
            }
            EaComponents.ListViewLabel {
                readonly property int letterIndex: box.rows ? box.rows.wyckoffLetters.indexOf(row.wyckoffLetter) : -1
                horizontalAlignment: Text.AlignHCenter
                text: letterIndex >= 0 ? box.rows.wyckoffNames[letterIndex] : row.wyckoffLetter
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                locked: true
                item: row.occupancy
            }
            Item {
                property int horizontalAlignment: Text.AlignHCenter
                height: parent.height
                EaComponents.ListViewCheckBox {
                    anchors.fill: parent
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `magnetic.site.${row.index}`
                    checked: row.isChosen
                    // The last chosen site stays chosen.
                    enabled: !(row.isChosen && box.chosen.length === 1)
                    onToggled: box.toggled(row.label, checked)
                }
            }
        }
    }
}
