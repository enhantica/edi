// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `atom_site_aniso` (easydiffractionbeta Pages/Model/SideBarBasic/AtomSiteAdp.qml; the owner, 2026-10-06): one row
// per atom site, its label as in Atom sites, read only; its ADP type; the isotropic value; the six anisotropic
// components. An isotropic type edits its value and leaves the six empty and disabled; an anisotropic type edits the six, those
// its site symmetry leaves free, and shows the equivalent isotropic value read only. Changing the type converts the
// site's values.
Column {
    id: group

    readonly property AtomSiteAdpListModel adps: structure ? structure.atomSiteAdps : null
    property StructureViewModel structure: null
    readonly property real typeWidth: EaStyle.Sizes.fontPixelSize * 4.5
    readonly property real valueWidth: EaStyle.Sizes.fontPixelSize * 3.7

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table

        columnWidths: [numberColumnWidth, textColumnWidth("label", qsTr("label")), group.typeWidth, -1, -1, -1, -1, -1, -1, -1]
        defaultInfoText: qsTr("No atom sites defined")
        model: group.adps
        objectName: "atomSiteAdps.list"

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property ParameterItem adpIso
            required property string adpType
            required property var ani11
            required property var ani12
            required property var ani13
            required property var ani22
            required property var ani23
            required property var ani33
            readonly property bool anisotropic: adpType === "Bani" || adpType === "Uani" || adpType === "beta"
            required property int index
            required property string label

            EaComponents.TableViewLabel {
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                enabled: false
                horizontalAlignment: Text.AlignLeft
                objectName: `atomSiteAdp.label.${row.index}`
                value: row.label
            }
            SearchableComboBox {
                anchors.verticalCenter: parent.verticalCenter
                currentIndex: group.adps ? group.adps.types.indexOf(row.adpType) : -1
                inTable: true
                model: group.adps ? group.adps.types : []
                objectName: `atomSiteAdp.type.${row.index}`

                // The type change can add or remove a tensor row, which rebuilds this table: it runs after the
                // popup has closed.
                onActivated: index => {
                    const site = row.index;
                    const type = textAt(index);
                    const adps = group.adps;
                    currentIndex = Qt.binding(() => group.adps ? group.adps.types.indexOf(row.adpType) : -1);
                    Qt.callLater(() => adps.setType(site, type));
                }
            }
            // The isotropic value in the site's type; an anisotropic site's equivalent value, which follows its
            // tensor, is shown disabled.
            ParameterCell {
                enabled: !row.anisotropic
                item: row.adpIso
                objectName: `atomSiteAdp.iso.${row.index}`
            }
            ParameterCell {
                enabled: row.anisotropic && !!row.ani11 && refinable
                item: row.ani11 ? row.ani11 : null
                objectName: `atomSiteAdp.ani11.${row.index}`
                text: item !== null ? value : ""
            }
            ParameterCell {
                enabled: row.anisotropic && !!row.ani22 && refinable
                item: row.ani22 ? row.ani22 : null
                objectName: `atomSiteAdp.ani22.${row.index}`
                text: item !== null ? value : ""
            }
            ParameterCell {
                enabled: row.anisotropic && !!row.ani33 && refinable
                item: row.ani33 ? row.ani33 : null
                objectName: `atomSiteAdp.ani33.${row.index}`
                text: item !== null ? value : ""
            }
            ParameterCell {
                enabled: row.anisotropic && !!row.ani12 && refinable
                item: row.ani12 ? row.ani12 : null
                objectName: `atomSiteAdp.ani12.${row.index}`
                text: item !== null ? value : ""
            }
            ParameterCell {
                enabled: row.anisotropic && !!row.ani13 && refinable
                item: row.ani13 ? row.ani13 : null
                objectName: `atomSiteAdp.ani13.${row.index}`
                text: item !== null ? value : ""
            }
            ParameterCell {
                enabled: row.anisotropic && !!row.ani23 && refinable
                item: row.ani23 ? row.ani23 : null
                objectName: `atomSiteAdp.ani23.${row.index}`
                text: item !== null ? value : ""
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
                text: qsTr("iso")
            }
            EaComponents.TableViewLabel {
                text: "ani11"
            }
            EaComponents.TableViewLabel {
                text: "ani22"
            }
            EaComponents.TableViewLabel {
                text: "ani33"
            }
            EaComponents.TableViewLabel {
                text: "ani12"
            }
            EaComponents.TableViewLabel {
                text: "ani13"
            }
            EaComponents.TableViewLabel {
                text: "ani23"
            }
        }
    }
}
