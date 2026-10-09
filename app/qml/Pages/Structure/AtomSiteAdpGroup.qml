// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `atom_site_aniso` (easydiffractionbeta Pages/Model/SideBarBasic/AtomSiteAdp.qml; the owner, 2026-10-06): one row
// per atom site, its label as in Atom sites, read only; its ADP type; the isotropic value; the six anisotropic
// components. An isotropic type edits its value and leaves the six empty and disabled; an anisotropic type edits the six, those
// its site symmetry leaves free, and shows the equivalent isotropic value read only. Changing the type converts the
// site's values.
Column {
    id: group

    property StructureViewModel structure: null
    readonly property AtomSiteAdpListModel adps: structure ? structure.atomSiteAdps : null
    readonly property real typeWidth: EaStyle.Sizes.fontPixelSize * 4.5

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "atomSiteAdps.list"
        defaultInfoText: qsTr("No atom sites defined")
        sourceModel: group.adps

        readonly property string isoHeading: {
            const revision = modelRevision;
            const names = [];
            for (let index = 0; group.adps && index < count; ++index) {
                const type = group.adps.text(index, "adpType");
                const name = type === "Uani" ? "U eq" : type === "Bani" || type === "beta" ? "B eq" : type;
                if (!names.includes(name))
                    names.push(name);
            }
            return names.length === 1 ? names[0] : qsTr("iso / eq");
        }

        columnWidths: [numberColumnWidth, textColumnWidth("label", qsTr("id")), group.typeWidth, -1, -1, -1, -1, -1, -1, -1]

        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("id")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("type")
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: table.isoHeading
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "ani11"
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "ani22"
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "ani33"
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "ani12"
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "ani13"
            }
            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "ani23"
            }
        }

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int index
            required property string label
            required property string adpType
            required property ParameterItem adpIso
            required property var ani11
            required property var ani22
            required property var ani33
            required property var ani12
            required property var ani13
            required property var ani23
            readonly property bool anisotropic: adpType === "Bani" || adpType === "Uani" || adpType === "beta"

            EaComponents.TableViewLabel {
                horizontalAlignment: Text.AlignHCenter
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            TextCell {
                objectName: `atomSiteAdp.label.${row.index}`
                horizontalAlignment: Text.AlignLeft
                value: row.label
                onCommitted: text => group.structure.atomSites.setText(row.index, "label", text)
            }
            SearchableComboBox {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSiteAdp.type.${row.index}`
                inTable: true
                anchors.verticalCenter: parent.verticalCenter
                model: group.adps ? group.adps.types : []
                currentIndex: group.adps ? group.adps.types.indexOf(row.adpType) : -1
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
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSiteAdp.iso.${row.index}`
                item: row.adpIso
                enabled: !row.anisotropic
                ToolTip.text: row.anisotropic ? qsTr("Equivalent isotropic displacement %1 (Å²)").arg(row.adpType === "Uani" ? "U eq" : "B eq") : qsTr("Isotropic displacement %1 (Å²)").arg(row.adpType)
                ToolTip.visible: hovered && EaGlobals.Vars.showToolTips
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSiteAdp.ani11.${row.index}`
                enabled: row.anisotropic && !!row.ani11 && refinable
                item: row.ani11 ? row.ani11 : null
                text: item !== null ? value : ""
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSiteAdp.ani22.${row.index}`
                enabled: row.anisotropic && !!row.ani22 && refinable
                item: row.ani22 ? row.ani22 : null
                text: item !== null ? value : ""
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSiteAdp.ani33.${row.index}`
                enabled: row.anisotropic && !!row.ani33 && refinable
                item: row.ani33 ? row.ani33 : null
                text: item !== null ? value : ""
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSiteAdp.ani12.${row.index}`
                enabled: row.anisotropic && !!row.ani12 && refinable
                item: row.ani12 ? row.ani12 : null
                text: item !== null ? value : ""
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSiteAdp.ani13.${row.index}`
                enabled: row.anisotropic && !!row.ani13 && refinable
                item: row.ani13 ? row.ani13 : null
                text: item !== null ? value : ""
            }
            ParameterCell {
                horizontalAlignment: Text.AlignHCenter
                objectName: `atomSiteAdp.ani23.${row.index}`
                enabled: row.anisotropic && !!row.ani23 && refinable
                item: row.ani23 ? row.ani23 : null
                text: item !== null ? value : ""
            }
        }
    }
}
