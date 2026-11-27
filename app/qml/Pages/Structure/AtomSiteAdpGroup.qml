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
    // Advances on every change of the rows, so the columns are measured again: a type or a value can change the
    // widest text while no text column's width does. Held as a property, not a child of the column.
    property int adpRevision: 0
    readonly property Connections adpWatcher: Connections {
        target: group.adps
        ignoreUnknownSignals: true
        function onDataChanged() {
            group.adpRevision++;
        }
    }

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "atomSiteAdps.list"
        defaultInfoText: qsTr("No atom sites yet")
        sourceModel: group.adps

        // Equal-width numeric columns (the owner, 2026-10-24), each as wide as its number type (ADR-0103 rule 4), in
        // their natural order ID, type, iso, 11, 22, 33, 12, 13, 23; the six components show whenever there is room, an
        // all-isotropic structure included (the owner, 2026-11-22). Spare width goes to the number columns. A beta
        // component shows five significant digits, in smaller text where it would not fit.
        // Each number column at the displacement type's minimal estimate plus one cell padding; a value wider than
        // that is written to fit (ADR-0051), the owner, 2026-11-22.
        readonly property real isoWidth: typeColumnWidth("displacement", Session.label("atom_site.adp_iso"))
        readonly property real componentWidth: typeColumnWidth("displacement", Session.label("atom_site_aniso.adp_11"))
        // Widths from column types, not rows (ADR-0103 rule 4): short label and type, then numbers.
        // Its columns by kind (the shared column model, DataTable.columnKinds; ADR-0103 decision 4).
        // The type column as wide as its widest option and the arrow, so changing a site's type never moves a column
        // (the owner, 2026-11-23).
        readonly property real typeWidth: Math.ceil(Math.max(0, ...(group.adps ? group.adps.types : []).map(type => typeMetrics.advanceWidth(type)))) + EaStyle.Sizes.fontPixelSize * 2.5
        FontMetrics {
            id: typeMetrics
            font.family: EaStyle.Fonts.fontFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
        }
        columnTexts: ["", "label"]
        columnKinds: ["index", "name", typeWidth, "displacement", "displacement", "displacement", "displacement", "displacement", "displacement", "displacement"]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "atom_site.id"
            }
            // "Type": the group's title says what kind (the owner, 2026-11-23).
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site.adp_type"
                longText: qsTr("Type")
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                // B iso or U iso, editable, or a tensor's read-only equivalent B eq or U eq (owner, 2026-10-12).
                uid: "atom_site.adp_iso"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site_aniso.adp_11"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site_aniso.adp_22"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site_aniso.adp_33"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site_aniso.adp_12"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site_aniso.adp_13"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site_aniso.adp_23"
            }
        }

        delegate: TableRow {
            id: row

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

            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            // An atom's id is edited in the Atom sites table only (the owner, 2026-10-23).
            TextCell {
                editMember: row
                editModel: group.adps
                editIndex: row.index
                objectName: `atomSiteAdp.label.${row.index}`
                horizontalAlignment: Text.AlignLeft
                readOnly: true
                value: row.label
            }
            ComboCell {
                SearchableComboBox {
                    horizontalAlignment: Text.AlignLeft
                    objectName: `atomSiteAdp.type.${row.index}`
                    inTable: true
                    anchors.verticalCenter: parent.verticalCenter
                    model: group.adps ? group.adps.types : []
                    currentIndex: group.adps ? group.adps.types.indexOf(row.adpType) : -1
                    // The type change can add or remove a tensor row, which rebuilds this table: it runs after the
                    // popup has closed.
                    onActivated: index => ApplicationInfo.scientificSelectorChanged(index, 5, () => {
                            currentIndex = Qt.binding(() => group.adps ? group.adps.types.indexOf(row.adpType) : -1);
                        })
                }
            }
            // The isotropic value in the site's type; an anisotropic site's equivalent value, which follows its
            // tensor, and a value a constraint sets are shown disabled.
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteAdp.iso.${row.index}`
                item: row.adpIso
                enabled: !row.anisotropic && refinable
                ToolTip.text: row.adpIso ? (row.anisotropic ? qsTr("Equivalent isotropic displacement %1, %2 (%3)") : qsTr("Isotropic displacement %1, %2 (%3)")).arg(row.adpIso.shortName).arg(row.adpIso.displayUnits).arg("_atom_site.adp_iso") : ""
                // Help, hidden while the cell shows why its value is red.
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteAdp.ani11.${row.index}`
                enabled: row.anisotropic && !!row.ani11 && refinable
                item: row.ani11 ? row.ani11 : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1, %2 (%3)").arg(item.shortName).arg(item.displayUnits !== "" ? item.displayUnits : qsTr("dimensionless")).arg("_atom_site_aniso.adp_11") : ""
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteAdp.ani22.${row.index}`
                enabled: row.anisotropic && !!row.ani22 && refinable
                item: row.ani22 ? row.ani22 : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1, %2 (%3)").arg(item.shortName).arg(item.displayUnits !== "" ? item.displayUnits : qsTr("dimensionless")).arg("_atom_site_aniso.adp_22") : ""
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteAdp.ani33.${row.index}`
                enabled: row.anisotropic && !!row.ani33 && refinable
                item: row.ani33 ? row.ani33 : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1, %2 (%3)").arg(item.shortName).arg(item.displayUnits !== "" ? item.displayUnits : qsTr("dimensionless")).arg("_atom_site_aniso.adp_33") : ""
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteAdp.ani12.${row.index}`
                enabled: row.anisotropic && !!row.ani12 && refinable
                item: row.ani12 ? row.ani12 : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1, %2 (%3)").arg(item.shortName).arg(item.displayUnits !== "" ? item.displayUnits : qsTr("dimensionless")).arg("_atom_site_aniso.adp_12") : ""
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteAdp.ani13.${row.index}`
                enabled: row.anisotropic && !!row.ani13 && refinable
                item: row.ani13 ? row.ani13 : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1, %2 (%3)").arg(item.shortName).arg(item.displayUnits !== "" ? item.displayUnits : qsTr("dimensionless")).arg("_atom_site_aniso.adp_13") : ""
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteAdp.ani23.${row.index}`
                enabled: row.anisotropic && !!row.ani23 && refinable
                item: row.ani23 ? row.ani23 : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1, %2 (%3)").arg(item.shortName).arg(item.displayUnits !== "" ? item.displayUnits : qsTr("dimensionless")).arg("_atom_site_aniso.adp_23") : ""
                helpToolTip: true
            }
        }
    }
}
