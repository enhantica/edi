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
    // easydiffractionbeta's widths (AtomSite.qml): the label takes what the others leave.
    readonly property real coordinateWidth: EaStyle.Sizes.fontPixelSize * 4.8
    readonly property real typeWidth: EaStyle.Sizes.fontPixelSize * 4.5
    readonly property real wyckoffWidth: EaStyle.Sizes.fontPixelSize * 2.5

    spacing: AppSizes.groupContentSpacing

    EaComponents.TableView {
        id: table
        objectName: "atomSites.list"
        defaultInfoText: qsTr("No atom sites defined")
        model: group.sites

        header: EaComponents.TableViewHeader {
            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
            }
            EaComponents.TableViewLabel {
                flexibleWidth: true
                text: qsTr("label")
            }
            EaComponents.TableViewLabel {
                width: AppSizes.atomIconColumnWidth
            }
            EaComponents.TableViewLabel {
                width: group.typeWidth
                text: qsTr("type")
            }
            EaComponents.TableViewLabel {
                width: group.coordinateWidth
                text: "x"
            }
            EaComponents.TableViewLabel {
                width: group.coordinateWidth
                text: "y"
            }
            EaComponents.TableViewLabel {
                width: group.coordinateWidth
                text: "z"
            }
            EaComponents.TableViewLabel {
                width: group.wyckoffWidth
                text: qsTr("WL")
            }
            EaComponents.TableViewLabel {
                width: group.coordinateWidth
                text: qsTr("occ")
            }
            EaComponents.TableViewLabel {
                width: AppSizes.iconColumnWidth
            }
        }

        delegate: EaComponents.TableViewDelegate {
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
                width: AppSizes.indexColumnWidth
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                objectName: `atomSite.label.${row.index}`
                width: table.headerLabelItems.length > 1 ? table.headerLabelItems[1].width : 0
                value: row.label
                onCommitted: text => group.sites.setText(row.index, "label", text)
            }
            // The site's atom icon in its element's colour, next to its type, as the Analysis page's parameter
            // names carry it (the owner, 2026-10-03 and 2026-10-06).
            IconCell {
                objectName: `atomSite.icon.${row.index}`
                width: AppSizes.atomIconColumnWidth
                icon: row.fractX ? row.fractX.categoryIcon : ""
                iconColor: AppColors.element(row.typeSymbol)
                toolTip: row.typeSymbol
            }
            // The type picked from the element table or typed into the list's search field (the owner,
            // 2026-10-06); a type outside the table, as a file may declare it ("Co2+", "157Gd"), is shown as it is.
            SearchableComboBox {
                objectName: `atomSite.typeSymbol.${row.index}`
                width: group.typeWidth
                height: EaStyle.Sizes.tableRowHeight
                topInset: 0
                bottomInset: 0
                searchThreshold: 0
                model: ApplicationInfo.elementSymbols
                currentIndex: ApplicationInfo.elementSymbols.indexOf(row.typeSymbol)
                displayText: row.typeSymbol
                popup.width: Math.max(width, EaStyle.Sizes.fontPixelSize * 8)
                onActivated: index => {
                    group.sites.setText(row.index, "typeSymbol", textAt(index));
                    currentIndex = Qt.binding(() => ApplicationInfo.elementSymbols.indexOf(row.typeSymbol));
                }
            }
            ParameterCell {
                objectName: `atomSite.fractX.${row.index}`
                width: group.coordinateWidth
                item: row.fractX
            }
            ParameterCell {
                objectName: `atomSite.fractY.${row.index}`
                width: group.coordinateWidth
                item: row.fractY
            }
            ParameterCell {
                objectName: `atomSite.fractZ.${row.index}`
                width: group.coordinateWidth
                item: row.fractZ
            }
            TextCell {
                objectName: `atomSite.wyckoffLetter.${row.index}`
                width: group.wyckoffWidth
                value: row.wyckoffLetter
                onCommitted: text => group.sites.setText(row.index, "wyckoffLetter", text)
            }
            ParameterCell {
                objectName: `atomSite.occupancy.${row.index}`
                width: group.coordinateWidth
                item: row.occupancy
            }
            EaComponents.TableViewButton {
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
