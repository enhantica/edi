// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `atom_site` (easydiffractionbeta Pages/Model/SideBarBasic/AtomSite.qml): label, the type with its atom icon,
// coordinates, Wyckoff letter and occupancy; append, duplicate and remove as the library's AtomSites do. The ADP
// columns are the Atomic displacement group's (the owner, 2026-10-06).
Column {
    id: group

    // easydiffractionbeta's widths (AtomSite.qml): the label takes what the others leave.
    readonly property real coordinateWidth: EaStyle.Sizes.fontPixelSize * 4.8
    readonly property AtomSiteListModel sites: structure ? structure.atomSites : null
    property StructureViewModel structure: null
    readonly property real typeWidth: EaStyle.Sizes.fontPixelSize * 4.5
    readonly property real wyckoffWidth: EaStyle.Sizes.fontPixelSize * 2.5

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table

        columnWidths: [numberColumnWidth, textColumnWidth("label", qsTr("label")), group.typeWidth, -1, -1, -1, group.wyckoffWidth, -1, AppSizes.iconColumnWidth]
        defaultInfoText: qsTr("No atom sites defined")
        model: group.sites
        objectName: "atomSites.list"

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property ParameterItem fractX
            required property ParameterItem fractY
            required property ParameterItem fractZ
            required property int index
            required property string label
            required property ParameterItem occupancy
            required property string typeSymbol
            required property string wyckoffLetter

            EaComponents.TableViewLabel {
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                horizontalAlignment: Text.AlignLeft
                objectName: `atomSite.label.${row.index}`
                value: row.label

                onCommitted: text => group.sites.setText(row.index, "label", text)
            }
            // The type picked from the element table or typed into the list's search field (the owner,
            // 2026-10-06); a type outside the table, as a file may declare it ("Co2+", "157Gd"), is shown as it is.
            SearchableComboBox {
                anchors.verticalCenter: parent.verticalCenter
                currentIndex: ApplicationInfo.elementSymbols.indexOf(row.typeSymbol)
                displayText: row.typeSymbol
                inTable: true
                model: ApplicationInfo.elementSymbols
                objectName: `atomSite.typeSymbol.${row.index}`
                popup.width: Math.max(width, EaStyle.Sizes.fontPixelSize * 8)
                searchThreshold: 0

                // The site's atom icon in its element's colour just before the type, as the Analysis page's parameter
                // names carry it (the owner, 2026-10-03 and 2026-10-06).
                contentItem: Item {
                    clip: true

                    IconLine {
                        anchors.verticalCenter: parent.verticalCenter
                        objectName: `atomSite.icon.${row.index}`
                        segments: [
                            {
                                "icon": row.fractX ? row.fractX.categoryIcon : "",
                                "color": AppColors.element(row.typeSymbol)
                            },
                            {
                                "text": row.typeSymbol
                            }
                        ]
                        x: EaStyle.Sizes.fontPixelSize * 0.5
                    }
                }

                onActivated: index => {
                    group.sites.setText(row.index, "typeSymbol", textAt(index));
                    currentIndex = Qt.binding(() => ApplicationInfo.elementSymbols.indexOf(row.typeSymbol));
                }
            }
            ParameterCell {
                item: row.fractX
                objectName: `atomSite.fractX.${row.index}`
            }
            ParameterCell {
                item: row.fractY
                objectName: `atomSite.fractY.${row.index}`
            }
            ParameterCell {
                item: row.fractZ
                objectName: `atomSite.fractZ.${row.index}`
            }
            TextCell {
                objectName: `atomSite.wyckoffLetter.${row.index}`
                value: row.wyckoffLetter

                onCommitted: text => group.sites.setText(row.index, "wyckoffLetter", text)
            }
            ParameterCell {
                item: row.occupancy
                objectName: `atomSite.occupancy.${row.index}`
            }
            EaComponents.TableViewButton {
                ToolTip.text: qsTr("Remove this atom site")
                fontIcon: "minus-circle"
                objectName: `atomSite.remove.${row.index}`

                onClicked: group.sites.remove(row.index)
            }
        }
        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("label")
            }
            EaComponents.TableViewLabel {
                text: qsTr("type")
            }
            EaComponents.TableViewLabel {
                text: "x"
            }
            EaComponents.TableViewLabel {
                text: "y"
            }
            EaComponents.TableViewLabel {
                text: "z"
            }
            EaComponents.TableViewLabel {
                text: qsTr("WL")
            }
            EaComponents.TableViewLabel {
                text: qsTr("occ")
            }
            EaComponents.TableViewLabel {
            }
        }
    }
    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            fontIcon: "plus-circle"
            objectName: "atomSites.append"
            text: qsTr("Append new atom site")

            onClicked: group.sites.append()
        }
        EaElements.SideBarButton {
            enabled: table.currentIndex >= 0 || (group.sites && group.sites.count > 0)
            fontIcon: "clone"
            objectName: "atomSites.duplicate"
            text: qsTr("Duplicate selected atom site")

            onClicked: group.sites.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
