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
//
// A selector above the table shows and edits the moments in crystal axes, Cartesian (x along a, z along c*) or
// spherical form (modulus, polar and azimuthal angles in degrees), each with a read-only |M| (the owner, 2026-11-03).
// The moments are stored, saved and fitted in crystal axes whatever the form; the choice is saved with the
// structure's view.
Column {
    id: group

    property StructureViewModel structure: null
    property StructureViewOptions options: null
    readonly property AtomSiteMomentListModel moments: structure ? structure.atomSiteMoments : null
    readonly property real ionWidth: EaStyle.Sizes.fontPixelSize * 5
    readonly property string form: options ? options.momentForm : "crystal_axes"
    readonly property bool crystalAxes: form === "crystal_axes"
    // The |M| column's text: the modulus rounded by its s.u. under the project's rule.
    function modulusText(parts) {
        if (!parts || parts.length < 8)
            return "";
        const text = NumberText.ruled(parts[6], parts[7]);
        return text ? text.bracket : Session.display("atom_site_moment.crystalaxis_x", parts[6]);
    }

    spacing: AppSizes.groupContentSpacing

    SelectorField {
        objectName: "atomSiteMoments.form"
        width: (EaStyle.Sizes.sideBarContentWidth - AppSizes.inputSpacing) / 2
        uid: "structure_view.moment_form"
        options: group.options ? group.options.momentFormOptions : null
        token: group.form
        onSelected: token => group.options.momentForm = token
    }

    DataTable {
        id: table
        objectName: "atomSiteMoments.list"
        visible: group.crystalAxes
        defaultInfoText: qsTr("No atom sites defined")
        sourceModel: group.moments

        equalColumns: true
        // The symmetry form wider than its text and right-aligned like the components, so it stands clear of Mz
        // (the owner, 2026-11-03).
        columns: [numberColumnWidth, textColumnWidth("label", Session.label("atom_site.id")), Math.max(group.ionWidth, (fittedWidths[2] ?? 0) + autoColumnPadding / 2), -1, -1, -1, -1, textColumnWidth("symmform", Session.label("atom_site_moment.symmform")) + EaStyle.Sizes.fontPixelSize * 4]

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
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "|M|"
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
            // The moment's modulus, read only.
            TextCell {
                objectName: `atomSiteMoment.modulus.${row.index}`
                horizontalAlignment: Text.AlignHCenter
                readOnly: true
                // Read again whenever a component's value or s.u. changes.
                value: {
                    const changes = [row.mx, row.my, row.mz].map(item => item ? [item.value, item.uncertainty] : null);
                    return row.magnetic && group.moments && changes && group.moments.revision >= 0 ? group.modulusText(group.moments.components(row.index, "crystal_axes")) : "";
                }
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

    // The moments in Cartesian or spherical form: each component converted from the crystal axes, its s.u. in its
    // tooltip, and an edit converted back (AtomSiteMomentListModel.setComponent).
    DataTable {
        id: converted
        objectName: "atomSiteMoments.converted"
        visible: !group.crystalAxes
        defaultInfoText: qsTr("No atom sites defined")
        sourceModel: group.moments

        readonly property bool spherical: group.form === "spherical"
        readonly property var titles: spherical ? [qsTr("|M|"), qsTr("θ (deg)"), qsTr("φ (deg)")] : [qsTr("Mx (x ∥ a)"), qsTr("My"), qsTr("Mz (z ∥ c*)")]

        equalColumns: true
        columns: [numberColumnWidth, textColumnWidth("label", Session.label("atom_site.id")), group.ionWidth, -1, -1, -1, -1]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "atom_site.id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "magnetic_form_factor.ion"
                text: qsTr("magnetic")
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: converted.titles[0]
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: converted.titles[1]
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: converted.titles[2]
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: "|M|"
            }
        }

        delegate: TableRow {
            id: formRow

            required property string label
            required property string ion
            required property var mx
            required property var my
            required property var mz
            readonly property bool magnetic: ion !== "none"
            // The moment in the chosen form, read again whenever a crystal-axis value or s.u. changes.
            readonly property var parts: {
                const changes = [mx, my, mz].map(item => item ? [item.value, item.uncertainty] : null);
                return magnetic && group.moments && changes && group.moments.revision >= 0 ? group.moments.components(index, group.form) : [];
            }

            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: formRow.index + 1
            }
            TextCell {
                horizontalAlignment: Text.AlignLeft
                readOnly: true
                value: formRow.label
            }
            TextCell {
                horizontalAlignment: Text.AlignLeft
                readOnly: true
                value: formRow.ion
            }
            TextCell {
                readonly property bool number: true

                objectName: `atomSiteMoment.form.0.${formRow.index}`
                horizontalAlignment: Text.AlignHCenter
                accepts: "number"
                uid: "atom_site_moment.crystalaxis_x"
                readOnly: !formRow.magnetic
                value: formRow.parts.length > 0 ? formRow.parts[0] : ""
                ToolTip.text: formRow.parts.length > 3 && isFinite(formRow.parts[3]) ? qsTr("s.u. %1").arg(Session.display("atom_site_moment.crystalaxis_x", formRow.parts[3])) : ""
                onCommitted: text => group.moments.setComponent(formRow.index, group.form, 0, Number(text))
            }
            TextCell {
                readonly property bool number: true

                objectName: `atomSiteMoment.form.1.${formRow.index}`
                horizontalAlignment: Text.AlignHCenter
                accepts: "number"
                uid: "atom_site_moment.crystalaxis_x"
                readOnly: !formRow.magnetic
                value: formRow.parts.length > 1 ? formRow.parts[1] : ""
                ToolTip.text: formRow.parts.length > 4 && isFinite(formRow.parts[4]) ? qsTr("s.u. %1").arg(Session.display("atom_site_moment.crystalaxis_x", formRow.parts[4])) : ""
                onCommitted: text => group.moments.setComponent(formRow.index, group.form, 1, Number(text))
            }
            TextCell {
                readonly property bool number: true

                objectName: `atomSiteMoment.form.2.${formRow.index}`
                horizontalAlignment: Text.AlignHCenter
                accepts: "number"
                uid: "atom_site_moment.crystalaxis_x"
                readOnly: !formRow.magnetic
                value: formRow.parts.length > 2 ? formRow.parts[2] : ""
                ToolTip.text: formRow.parts.length > 5 && isFinite(formRow.parts[5]) ? qsTr("s.u. %1").arg(Session.display("atom_site_moment.crystalaxis_x", formRow.parts[5])) : ""
                onCommitted: text => group.moments.setComponent(formRow.index, group.form, 2, Number(text))
            }
            TextCell {
                objectName: `atomSiteMoment.formModulus.${formRow.index}`
                horizontalAlignment: Text.AlignHCenter
                readOnly: true
                value: group.modulusText(formRow.parts)
            }
        }
    }
}
