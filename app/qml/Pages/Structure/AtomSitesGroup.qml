// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `atom_site` (easydiffractionbeta Pages/Model/SideBarBasic/AtomSite.qml and AtomSiteAdp.qml, merged:
// the ADP columns belong to the category, packet §15.6): label, type, coordinates, Wyckoff letter,
// occupancy, ADP type and Biso; append, duplicate and remove as the library's AtomSites do.
Column {
    id: group

    property StructureViewModel structure: null
    readonly property AtomSiteListModel sites: structure ? structure.atomSites : null
    readonly property real coordinateWidth: EaStyle.Sizes.fontPixelSize * 3.5

    spacing: AppSizes.groupContentSpacing

    EaComponents.TableView {
        id: table
        objectName: "atomSites.list"
        defaultInfoText: qsTr("No atom sites defined")
        model: group.sites

        header: EaComponents.TableViewHeader {
            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
                text: qsTr("No.")
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.tableRowHeight
            }
            EaComponents.TableViewLabel {
                flexibleWidth: true
                text: qsTr("label")
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 2.5
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
                width: EaStyle.Sizes.fontPixelSize * 2
                text: qsTr("WP")
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 3
                text: qsTr("occ")
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 2.75
                text: qsTr("ADP")
            }
            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 3
                text: qsTr("iso")
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
            required property string adpType
            required property ParameterItem fractX
            required property ParameterItem fractY
            required property ParameterItem fractZ
            required property ParameterItem occupancy
            required property ParameterItem adpIso

            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            // The site's atom icon in its element's colour, as the Analysis page's parameter names carry it (the owner,
            // 2026-10-03): the category icon its parameters hold, the element colour of its type.
            IconCell {
                objectName: `atomSite.icon.${row.index}`
                icon: row.fractX ? row.fractX.categoryIcon : ""
                iconColor: AppColors.element(row.typeSymbol)
                toolTip: row.typeSymbol
            }
            TextCell {
                objectName: `atomSite.label.${row.index}`
                width: table.headerLabelItems.length > 2 ? table.headerLabelItems[2].width : 0
                value: row.label
                onCommitted: text => group.sites.setText(row.index, "label", text)
            }
            TextCell {
                objectName: `atomSite.typeSymbol.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 2.5
                value: row.typeSymbol
                onCommitted: text => group.sites.setText(row.index, "typeSymbol", text)
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
                width: EaStyle.Sizes.fontPixelSize * 2
                value: row.wyckoffLetter
                onCommitted: text => group.sites.setText(row.index, "wyckoffLetter", text)
            }
            ParameterCell {
                objectName: `atomSite.occupancy.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 3
                item: row.occupancy
            }
            TextCell {
                objectName: `atomSite.adpType.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 2.75
                value: row.adpType
                onCommitted: text => group.sites.setText(row.index, "adpType", text)
            }
            ParameterCell {
                objectName: `atomSite.adpIso.${row.index}`
                width: EaStyle.Sizes.fontPixelSize * 3
                item: row.adpIso
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
