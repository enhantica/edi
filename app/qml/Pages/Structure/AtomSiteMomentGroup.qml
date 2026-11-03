// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `atom_site_moment` (edi ADR-0068; the owner, 2026-11-03): one row per atom site, as Atomic displacement — its id,
// read only; the magnetic ion its moment takes, "none" for a site without a moment, so choosing an ion marks the site
// magnetic; the three components along the cell axes, those the site symmetry leaves free editable; and the symmetry
// form crysta derives, read only. The ion belongs to the atom type, so sites of one type share it.
Column {
    id: group

    property StructureViewModel structure: null
    readonly property AtomSiteMomentListModel moments: structure ? structure.atomSiteMoments : null
    readonly property real ionWidth: EaStyle.Sizes.fontPixelSize * 5

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "atomSiteMoments.list"
        defaultInfoText: qsTr("No atom sites defined")
        sourceModel: group.moments

        equalColumns: true
        // The symmetry form wider than its text and right-aligned like the components, so it stands clear of Mz
        // (the owner, 2026-11-03).
        columns: [numberColumnWidth, textColumnWidth("label", Session.label("atom_site.id")), Math.max(group.ionWidth, (fittedWidths[2] ?? 0) + autoColumnPadding / 2), -1, -1, -1, textColumnWidth("symmform", Session.label("atom_site_moment.symmform")) + EaStyle.Sizes.fontPixelSize * 4]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "atom_site.id"
            }
            // The magnetic form factor, by its ion (the owner, 2026-11-03).
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "magnetic_form_factor.ion"
                text: qsTr("magnetic")
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site_moment.crystalaxis_x"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site_moment.crystalaxis_y"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "atom_site_moment.crystalaxis_z"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignRight
                uid: "atom_site_moment.symmform"
            }
        }

        delegate: TableRow {
            id: row

            required property string label
            required property string ion
            required property var mx
            required property var my
            required property var mz
            required property string symmform
            readonly property bool magnetic: ion !== "none"

            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            // An atom's id is edited in the Atom sites table only.
            TextCell {
                objectName: `atomSiteMoment.label.${row.index}`
                horizontalAlignment: Text.AlignLeft
                readOnly: true
                value: row.label
            }
            ComboCell {
                SearchableComboBox {
                    horizontalAlignment: Text.AlignLeft
                    objectName: `atomSiteMoment.ion.${row.index}`
                    inTable: true
                    anchors.verticalCenter: parent.verticalCenter
                    model: group.moments ? group.moments.ions(row.index) : []
                    currentIndex: group.moments ? group.moments.ions(row.index).indexOf(row.ion) : -1
                    // A moment row comes or goes, which rebuilds this table: it runs after the popup has closed.
                    onActivated: index => {
                        const site = row.index;
                        const ion = textAt(index);
                        const moments = group.moments;
                        currentIndex = Qt.binding(() => group.moments ? group.moments.ions(row.index).indexOf(row.ion) : -1);
                        Qt.callLater(() => moments.setIon(site, ion));
                    }
                    ToolTip.text: qsTr("The magnetic ion whose form factor the moment takes, shared by every site of the atom type; none: the site has no moment")
                }
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteMoment.mx.${row.index}`
                enabled: row.magnetic && !!row.mx && refinable
                item: row.mx ? row.mx : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1, %2 (%3)").arg(item.shortName).arg(item.displayUnits).arg("_atom_site_moment.crystalaxis_x") : ""
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteMoment.my.${row.index}`
                enabled: row.magnetic && !!row.my && refinable
                item: row.my ? row.my : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1, %2 (%3)").arg(item.shortName).arg(item.displayUnits).arg("_atom_site_moment.crystalaxis_y") : ""
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `atomSiteMoment.mz.${row.index}`
                enabled: row.magnetic && !!row.mz && refinable
                item: row.mz ? row.mz : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1, %2 (%3)").arg(item.shortName).arg(item.displayUnits).arg("_atom_site_moment.crystalaxis_z") : ""
                helpToolTip: true
            }
            // Derived from the site and the magnetic group: read only. Aligned as the components are, so the table
            // treats it as a number column (DataTable.kindOf).
            TextCell {
                readonly property bool number: true

                objectName: `atomSiteMoment.symmform.${row.index}`
                horizontalAlignment: Text.AlignRight
                readOnly: true
                value: row.symmform
            }
        }
    }
}
