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

    property StructureViewModel structure: null
    readonly property AtomSiteListModel sites: structure ? structure.atomSites : null
    readonly property real typeWidth: EaStyle.Sizes.fontPixelSize * 4.5
    readonly property real wyckoffWidth: EaStyle.Sizes.fontPixelSize * 2.5

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "atomSites.list"
        defaultInfoText: qsTr("No atom sites defined")
        sourceModel: group.sites

        columnWidths: [numberColumnWidth, textColumnWidth("label", qsTr("id")), group.typeWidth, -1, -1, -1, group.wyckoffWidth, -1, AppSizes.iconColumnWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("id")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("type")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "x"
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "y"
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "z"
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("WL")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("occ")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
        }

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int index
            required property string label
            required property string typeSymbol
            required property string wyckoffLetter
            required property ParameterItem fractX
            required property ParameterItem fractY
            required property ParameterItem fractZ
            required property ParameterItem occupancy

            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                objectName: `atomSite.label.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.label
                onCommitted: text => group.sites.setText(row.index, "label", text)
            }
            // The type picked from the element table or typed into the list's search field (the owner,
            // 2026-10-06); a type outside the table, as a file may declare it ("Co2+", "157Gd"), is shown as it is.
            SearchableComboBox {
                horizontalAlignment: Text.AlignLeft
                objectName: `atomSite.typeSymbol.${row.index}`
                inTable: true
                anchors.verticalCenter: parent.verticalCenter
                searchThreshold: 0
                model: ApplicationInfo.elementSymbols
                currentIndex: ApplicationInfo.elementSymbols.indexOf(row.typeSymbol)
                displayText: row.typeSymbol
                popup.width: Math.max(width, EaStyle.Sizes.fontPixelSize * 8)
                // The site's atom icon in its element's colour just before the type, as the Analysis page's parameter
                // names carry it (the owner, 2026-10-03 and 2026-10-06).
                contentItem: Item {
                    clip: true

                    IconLine {
                        objectName: `atomSite.icon.${row.index}`
                        x: EaStyle.Sizes.fontPixelSize * 0.5
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
                onActivated: index => {
                    group.sites.setText(row.index, "typeSymbol", textAt(index));
                    currentIndex = Qt.binding(() => ApplicationInfo.elementSymbols.indexOf(row.typeSymbol));
                }
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSite.fractX.${row.index}`
                item: row.fractX
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSite.fractY.${row.index}`
                item: row.fractY
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSite.fractZ.${row.index}`
                item: row.fractZ
            }
            TextCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSite.wyckoffLetter.${row.index}`
                value: row.wyckoffLetter
                onCommitted: text => group.sites.setText(row.index, "wyckoffLetter", text)
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSite.occupancy.${row.index}`
                item: row.occupancy
            }
            EaComponents.TableViewButton {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSite.remove.${row.index}`
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this atom site")
                onClicked: group.sites.remove(row.index)
            }
        }
    }

    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            objectName: "atomSites.append"
            fontIcon: "plus-circle"
            text: qsTr("Append new atom site")
            onClicked: group.sites.append()
        }
        EaElements.SideBarButton {
            objectName: "atomSites.duplicate"
            enabled: table.currentIndex >= 0 || (group.sites && group.sites.count > 0)
            fontIcon: "clone"
            text: qsTr("Duplicate selected atom site")
            onClicked: group.sites.duplicate(Math.max(table.currentIndex, 0))
        }
    }
}
