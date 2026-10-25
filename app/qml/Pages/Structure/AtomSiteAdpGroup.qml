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
        defaultInfoText: qsTr("No atom sites defined")
        sourceModel: group.adps

        // A beta component is small (about 1e-4 to 1e-2) and so has more characters than a U or B: with a beta row
        // present iso/eq is only as wide as its header and values, and the six component columns share the rest,
        // each showing five significant digits, in smaller text where they would not fit. Measured again on every
        // change of the rows.
        readonly property real isoWidth: {
            const revision = modelRevision + group.adpRevision;
            let beta = false;
            for (let row = 0; group.adps && row < count && !beta; ++row)
                beta = group.adps.text(row, "adpType") === "beta";
            if (!beta)
                return -1;  // without a beta row no value is measured
            let widest = advance(qsTr("iso/eq"));
            for (let row = 0; row < count; ++row) {
                const item = group.adps.item(row, "adpIso") as ParameterItem;
                if (item)
                    widest = Math.max(widest, advance(NumberText.parameter(item.value, item.hasUncertainty ? item.uncertainty : 0, 5)));
            }
            return Math.ceil(widest) + AppSizes.fieldSpacing * 2;
        }
        columnWidths: [numberColumnWidth, textColumnWidth("label", qsTr("id")), group.typeWidth, isoWidth, -1, -1, -1, -1, -1, -1]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignLeft
                text: qsTr("id")
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("type")
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                // B iso or U iso, editable, or a tensor's read-only equivalent B eq or U eq (owner, 2026-10-12).
                text: qsTr("iso/eq")
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "11"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "22"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "33"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "12"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "13"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "23"
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
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            // An atom's id is edited in the Atom sites table only (the owner, 2026-10-23).
            TextCell {
                objectName: `atomSiteAdp.label.${row.index}`
                horizontalAlignment: Text.AlignLeft
                readOnly: true
                value: row.label
            }
            Item {
                property int horizontalAlignment: Text.AlignHCenter
                height: parent.height
                SearchableComboBox {
                    width: Math.min(parent.width, implicitWidth)
                    x: parent.horizontalAlignment === Text.AlignRight ? parent.width - width : parent.horizontalAlignment === Text.AlignLeft ? 0 : (parent.width - width) / 2
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
            }
            // The isotropic value in the site's type; an anisotropic site's equivalent value, which follows its
            // tensor, is shown disabled.
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteAdp.iso.${row.index}`
                item: row.adpIso
                enabled: !row.anisotropic
                ToolTip.text: row.adpIso ? (row.anisotropic ? qsTr("Equivalent isotropic displacement %1, %2 (%3)") : qsTr("Isotropic displacement %1, %2 (%3)")).arg(row.adpIso.shortName).arg(row.adpIso.displayUnits).arg("_atom_site.adp_iso") : ""
                // Help, hidden while the cell shows why its value is red.
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                fitDigits: true
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
                fitDigits: true
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
                fitDigits: true
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
                fitDigits: true
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
                fitDigits: true
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
                fitDigits: true
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
