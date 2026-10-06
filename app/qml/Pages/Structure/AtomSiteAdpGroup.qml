// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `atom_site_aniso` (easydiffractionbeta Pages/Model/SideBarBasic/AtomSiteAdp.qml; the owner, 2026-10-06): one row
// per atom site, its label as in Atom sites, read only; its ADP type; the isotropic value; the six anisotropic
// components. An isotropic type edits `iso` and leaves the six empty; an anisotropic type edits the six and shows
// the equivalent isotropic value. Only Biso is calculated yet: the other types are a draft, kept in the app.
Column {
    id: group

    property StructureViewModel structure: null
    readonly property AtomSiteAdpListModel adps: structure ? structure.atomSiteAdps : null
    readonly property real valueWidth: EaStyle.Sizes.fontPixelSize * 3.7
    readonly property real typeWidth: EaStyle.Sizes.fontPixelSize * 4.5

    spacing: AppSizes.groupContentSpacing

    EaComponents.TableView {
        id: table
        objectName: "atomSiteAdps.list"
        defaultInfoText: qsTr("No atom sites defined")
        model: group.adps

        header: EaComponents.TableViewHeader {
            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
            }
            EaComponents.TableViewLabel {
                flexibleWidth: true
                text: qsTr("label")
            }
            EaComponents.TableViewLabel {
                width: group.typeWidth
                text: qsTr("type")
            }
            EaComponents.TableViewLabel {
                width: group.valueWidth
                text: qsTr("iso")
            }
            EaComponents.TableViewLabel {
                width: group.valueWidth
                text: "ani11"
            }
            EaComponents.TableViewLabel {
                width: group.valueWidth
                text: "ani22"
            }
            EaComponents.TableViewLabel {
                width: group.valueWidth
                text: "ani33"
            }
            EaComponents.TableViewLabel {
                width: group.valueWidth
                text: "ani12"
            }
            EaComponents.TableViewLabel {
                width: group.valueWidth
                text: "ani13"
            }
            EaComponents.TableViewLabel {
                width: group.valueWidth
                text: "ani23"
            }
        }

        delegate: EaComponents.TableViewDelegate {
            id: row

            required property int index
            required property string label
            required property string adpType
            required property bool active
            required property ParameterItem adpIso
            required property var iso
            required property var ani11
            required property var ani22
            required property var ani33
            required property var ani12
            required property var ani13
            required property var ani23
            readonly property bool anisotropic: adpType === "Bani" || adpType === "Uani" || adpType === "beta"

            EaComponents.TableViewLabel {
                width: AppSizes.indexColumnWidth
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                objectName: `atomSiteAdp.label.${row.index}`
                width: table.headerLabelItems.length > 1 ? table.headerLabelItems[1].width : 0
                enabled: false
                value: row.label
            }
            SearchableComboBox {
                objectName: `atomSiteAdp.type.${row.index}`
                width: group.typeWidth
                inTable: true
                anchors.verticalCenter: parent.verticalCenter
                model: group.adps ? group.adps.types : []
                currentIndex: group.adps ? group.adps.types.indexOf(row.adpType) : -1
                onActivated: index => {
                    group.adps.setType(row.index, textAt(index));
                    currentIndex = Qt.binding(() => group.adps ? group.adps.types.indexOf(row.adpType) : -1);
                }
            }
            // Biso is the stored parameter itself, with its vary toggle; any other type's value is the draft's. One
            // column, so the table's columns stay one per header label.
            Item {
                width: group.valueWidth
                height: EaStyle.Sizes.tableRowHeight

                ParameterCell {
                    objectName: `atomSiteAdp.iso.${row.index}`
                    anchors.fill: parent
                    visible: row.adpType === "Biso"
                    item: row.adpIso
                }
                TextCell {
                    objectName: `atomSiteAdp.isoPreview.${row.index}`
                    anchors.fill: parent
                    visible: row.adpType !== "Biso"
                    enabled: !row.anisotropic
                    accepts: "number"
                    value: row.iso
                    onCommitted: text => group.adps.setIso(row.index, Number(text))
                }
            }
            TextCell {
                objectName: `atomSiteAdp.ani11.${row.index}`
                width: group.valueWidth
                enabled: row.anisotropic
                accepts: "number"
                value: row.anisotropic ? row.ani11 : ""
                onCommitted: text => group.adps.setComponent(row.index, 0, Number(text))
            }
            TextCell {
                objectName: `atomSiteAdp.ani22.${row.index}`
                width: group.valueWidth
                enabled: row.anisotropic
                accepts: "number"
                value: row.anisotropic ? row.ani22 : ""
                onCommitted: text => group.adps.setComponent(row.index, 1, Number(text))
            }
            TextCell {
                objectName: `atomSiteAdp.ani33.${row.index}`
                width: group.valueWidth
                enabled: row.anisotropic
                accepts: "number"
                value: row.anisotropic ? row.ani33 : ""
                onCommitted: text => group.adps.setComponent(row.index, 2, Number(text))
            }
            TextCell {
                objectName: `atomSiteAdp.ani12.${row.index}`
                width: group.valueWidth
                enabled: row.anisotropic
                accepts: "number"
                value: row.anisotropic ? row.ani12 : ""
                onCommitted: text => group.adps.setComponent(row.index, 3, Number(text))
            }
            TextCell {
                objectName: `atomSiteAdp.ani13.${row.index}`
                width: group.valueWidth
                enabled: row.anisotropic
                accepts: "number"
                value: row.anisotropic ? row.ani13 : ""
                onCommitted: text => group.adps.setComponent(row.index, 4, Number(text))
            }
            TextCell {
                objectName: `atomSiteAdp.ani23.${row.index}`
                width: group.valueWidth
                enabled: row.anisotropic
                accepts: "number"
                value: row.anisotropic ? row.ani23 : ""
                onCommitted: text => group.adps.setComponent(row.index, 5, Number(text))
            }
        }
    }

    EaElements.Label {
        objectName: "atomSiteAdps.draft"
        visible: group.adps !== null && group.adps.hasPreview
        width: EaStyle.Sizes.sideBarContentWidth
        wrapMode: Text.WordWrap
        color: EaStyle.Colors.themeForegroundMinor
        text: qsTr("Draft: only Biso is calculated yet. Uiso, Bani, Uani and beta are shown to try the table; the calculation uses each site's Biso, and these types are not saved.")
    }
}
