// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `atom_site` (easydiffractionbeta Pages/Model/SideBarBasic/AtomSite.qml): label, the type with its atom icon,
// coordinates, Wyckoff position and occupancy; append, duplicate and remove as the library's AtomSites do. The ADP
// columns are the Atomic displacement group's (the owner, 2026-10-06).
Column {
    id: group

    property StructureViewModel structure: null
    readonly property AtomSiteListModel sites: structure ? structure.atomSites : null

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "atomSites.list"
        defaultInfoText: qsTr("No atom sites yet")
        sourceModel: group.sites

        // The type's combo box as wide as its widest type, its icon and arrow (the owner, 2026-10-27).
        // Widths from column types, not rows (ADR-0103 rule 4): the label and type are short texts, the
        // coordinates, occupancy and B numbers.
        // Its columns by kind (the shared column model, DataTable.columnKinds; ADR-0103 decision 4).
        columnKinds: ["index", "short", "short", "value", "value", "value", "short", "value", "control"]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
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
                elide: Text.ElideRight
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

            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            TextCell {
                editMember: row
                editModel: group.sites
                editIndex: row.index
                objectName: `atomSite.label.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.label
                onCommitted: text => group.sites.setText(row.index, "label", text)
            }
            // The type picked from the types the linked experiments' scattering tables hold (isotopes for neutrons,
            // ions for X-rays), or typed into the list's search field (the owner, 2026-10-06); a type outside the list
            // is shown as it is. A typed type the list does not hold but the structure computes with (13C with
            // X-rays) is taken with Enter, as the Text tab takes it (the owner, 2026-11-25). Each entry carries its
            // element-coloured atom icon.
            ComboCell {
                SearchableComboBox {
                    id: typeBox
                    horizontalAlignment: Text.AlignLeft
                    objectName: `atomSite.typeSymbol.${row.index}`
                    inTable: true
                    anchors.verticalCenter: parent.verticalCenter
                    searchThreshold: 0
                    readonly property var types: group.structure ? group.structure.atomTypes : ApplicationInfo.elementSymbols
                    model: types
                    typedEntry: group.structure ? group.structure.typedAtomType(searchText, types) : ""
                    onTypedAccepted: text => group.sites.setText(row.index, "typeSymbol", text)
                    currentIndex: types.indexOf(row.typeSymbol)
                    displayText: row.typeSymbol
                    popup.width: Math.max(width, EaStyle.Sizes.fontPixelSize * 8)
                    // The site's atom icon in its element's colour just before the type, as the Analysis page's parameter
                    // names carry it (the owner, 2026-10-03 and 2026-10-06).
                    contentItem: Item {
                        implicitWidth: typeLine.implicitWidth
                        clip: true

                        IconLine {
                            id: typeLine
                            objectName: `atomSite.icon.${row.index}`
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
                    delegate: EaElements.MenuItem {
                        id: typeEntry

                        required property int index
                        required property string modelData
                        readonly property bool matching: typeBox.matches(modelData)

                        objectName: `atomSite.typeSymbol.${row.index}.entry.${index}`
                        width: typeEntry.parent !== null ? typeEntry.parent.width : 0
                        height: matching ? EaStyle.Sizes.comboBoxHeight : 0
                        opacity: matching ? 1 : 0
                        highlighted: typeBox.highlightedIndex === index
                        hoverEnabled: typeBox.hoverEnabled
                        text: modelData
                        contentItem: IconLine {
                            segments: [
                                {
                                    "icon": row.fractX ? row.fractX.categoryIcon : "",
                                    "color": AppColors.element(typeEntry.modelData)
                                },
                                {
                                    "text": typeEntry.modelData
                                }
                            ]
                        }
                    }
                    onActivated: index => ApplicationInfo.scientificSelectorChanged(index, 0, () => {
                            currentIndex = Qt.binding(() => typeBox.types.indexOf(row.typeSymbol));
                        })
                }
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `atomSite.fractX.${row.index}`
                item: row.fractX
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `atomSite.fractY.${row.index}`
                item: row.fractY
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `atomSite.fractZ.${row.index}`
                item: row.fractZ
            }
            // The Wyckoff position, chosen among the space group's: its multiplicity, letter and coordinates
            // (the owner, 2026-10-08). A letter the group does not know is shown as it is.
            ComboCell {
                // The column is as wide as the position name shown; the list's longer coordinates open in a popup.
                // The box is as wide as its value and arrow, the arrow right after the value, as every table's combo box
                // (the owner, 2026-11-22).
                SearchableComboBox {
                    readonly property int letterIndex: group.sites ? group.sites.wyckoffLetters.indexOf(row.wyckoffLetter) : -1

                    horizontalAlignment: Text.AlignLeft
                    objectName: `atomSite.wyckoffLetter.${row.index}`
                    inTable: true
                    anchors.verticalCenter: parent.verticalCenter
                    model: group.sites ? group.sites.wyckoffLabels : []
                    // PT Sans lacks the thirds, sixths and eighths in the coordinates; Noto Sans has them.
                    listFontFamily: "Noto Sans"
                    currentIndex: letterIndex
                    displayText: letterIndex >= 0 ? group.sites.wyckoffNames[letterIndex] : row.wyckoffLetter
                    onActivated: index => ApplicationInfo.scientificSelectorChanged(index, 1, () => {
                            currentIndex = Qt.binding(() => letterIndex);
                        })
                }
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                objectName: `atomSite.occupancy.${row.index}`
                item: row.occupancy
            }
            EaComponents.ListViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSite.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this atom site")
                onClicked: group.sites.remove(row.index)
            }
        }
    }

    Row {
        id: buttons

        // Whole labels where the longer fits beside its icon, else the short ones, the same on both buttons (no label
        // runs out of its button).
        readonly property bool wholeLabels: labelMetrics.advanceWidth + EaStyle.Sizes.fontPixelSize * 4 <= appendButton.width
        TextMetrics {
            id: labelMetrics
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            text: qsTr("Duplicate selected atom site")
        }

        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            id: appendButton
            objectName: "atomSites.append"
            fontIcon: "plus-circle"
            text: buttons.wholeLabels ? qsTr("Append new atom site") : qsTr("Append")
            onClicked: group.sites.append()
        }
        EaElements.SideBarButton {
            objectName: "atomSites.duplicate"
            enabled: table.currentIndex >= 0 || (group.sites && group.sites.count > 0)
            fontIcon: "clone"
            text: buttons.wholeLabels ? qsTr("Duplicate selected atom site") : qsTr("Duplicate")
            ToolTip.text: enabled ? "" : qsTr("Nothing to duplicate: add an atom site first")
            onClicked: group.sites.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
