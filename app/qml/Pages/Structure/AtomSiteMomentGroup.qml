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
    // Mx, My, Mz and |M| share one width; the symmetry column takes the rest (the owner, 2026-11-03).
    readonly property real componentWidth: EaStyle.Sizes.fontPixelSize * 5.5
    // That shared width: the widest value a table's cells have shown, with its s.u., so no value is cut short. Each
    // value cell reports its whole text's width as it changes (a fit's new values change no model row, so the
    // table's own fit is not redone); the width only grows.
    function componentsWidth(table, widest) {
        return Math.max(group.componentWidth, Math.ceil(widest) + table.autoColumnPadding / 2);
    }
    // The decimals a value shows as its cell writes it (up to six significant digits).
    function decimalsOf(value) {
        if (typeof value !== "number" || !isFinite(value))
            return 0;
        const text = String(Number(value.toPrecision(6)));
        const point = text.indexOf(".");
        return point < 0 || text.indexOf("e") >= 0 ? 0 : text.length - point - 1;
    }
    // A value derived from the moment (|M|, a Cartesian or spherical component): rounded by its s.u. under the
    // project's rule, or without one to the most decimals the crystal-axis components show (the owner, 2026-11-03).
    function derivedText(value, su, crystal) {
        if (typeof value !== "number" || !isFinite(value))
            return "";
        const text = NumberText.ruled(value, su);
        if (text)
            return `${text.value}(${text.bracket})`;
        const decimals = Math.max(0, ...(crystal ?? []).slice(0, 3).map(group.decimalsOf));
        return value.toFixed(decimals);
    }
    // The |M| column's text, from the row's components in any form (index 6, its s.u. 7) and its crystal-axis ones.
    function modulusText(parts, crystal) {
        if (!parts || parts.length < 8)
            return "";
        return group.derivedText(parts[6], parts[7], crystal);
    }
    // Value k of a form (0-2): "undetermined" where the moment does not fix it (index 9 marks them, bit k), else
    // the value with its s.u.
    function formText(parts, k, crystal) {
        if (!parts || parts.length < 6)
            return "";
        if (parts.length > 9 && (parts[9] & (1 << k)) !== 0)
            return qsTr("undetermined");
        return group.derivedText(parts[k], parts[k + 3], crystal);
    }
    // A derived value's tooltip: its s.u. and how it was found, from the fit's covariance (index 8) or propagated
    // from the components' own s.u. as if they were uncorrelated (relay decision 2026-11-03).
    function suTip(parts, su) {
        if (typeof su !== "number" || !isFinite(su))
            return "";
        const how = parts.length > 8 && parts[8] ? qsTr("from the fit's covariance") : qsTr("propagated as uncorrelated");
        return qsTr("s.u. %1, %2").arg(Session.display("atom_site_moment.crystalaxis_x", su)).arg(how);
    }

    spacing: AppSizes.groupContentSpacing

    SelectorField {
        objectName: "atomSiteMoments.form"
        width: EaStyle.Sizes.sideBarContentWidth
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
        // The symmetry form takes what the equal component columns leave, right-aligned like the components, so it
        // stands clear of |M| (the owner, 2026-11-03).
        columns: [numberColumnWidth, textColumnWidth("label", Session.label("atom_site.id")), Math.max(group.ionWidth, (fittedWidths[2] ?? 0) + autoColumnPadding / 2), components, components, components, components, -1]
        readonly property real components: group.componentsWidth(table, widestValue)
        property real widestValue: 0

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
                horizontalAlignment: Text.AlignRight
                text: "|M|"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignRight
                uid: "atom_site_moment.symmform"
                text: qsTr("symmetry")
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
                onImplicitWidthChanged: table.widestValue = Math.max(table.widestValue, implicitWidth)
                Component.onCompleted: table.widestValue = Math.max(table.widestValue, implicitWidth)
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
                onImplicitWidthChanged: table.widestValue = Math.max(table.widestValue, implicitWidth)
                Component.onCompleted: table.widestValue = Math.max(table.widestValue, implicitWidth)
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
                onImplicitWidthChanged: table.widestValue = Math.max(table.widestValue, implicitWidth)
                Component.onCompleted: table.widestValue = Math.max(table.widestValue, implicitWidth)
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
                property int columnAlignment: Text.AlignRight
                onImplicitWidthChanged: table.widestValue = Math.max(table.widestValue, implicitWidth)
                Component.onCompleted: table.widestValue = Math.max(table.widestValue, implicitWidth)

                objectName: `atomSiteMoment.modulus.${row.index}`
                horizontalAlignment: columnAlignment
                readOnly: true
                // Read again whenever a component's value or s.u. changes.
                readonly property var parts: {
                    const changes = [row.mx, row.my, row.mz].map(item => item ? [item.value, item.uncertainty] : null);
                    if (!row.magnetic || !group.moments || !changes || group.moments.revision < 0)
                        return [];
                    return group.moments.components(row.index, "crystal_axes");
                }
                value: group.modulusText(parts, parts)
                ToolTip.text: parts.length > 7 ? group.suTip(parts, parts[7]) : ""
            }
            // Derived from the site and the magnetic group: read only. Aligned as the components are, so the table
            // treats it as a number column (DataTable.kindOf).
            TextCell {
                property int columnAlignment: Text.AlignRight

                objectName: `atomSiteMoment.symmform.${row.index}`
                horizontalAlignment: columnAlignment
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
        // In spherical form the modulus is the first component, so the |M| column takes no width and is hidden.
        columns: [numberColumnWidth, textColumnWidth("label", Session.label("atom_site.id")), group.ionWidth, components, components, components, spherical ? 0 : components, -1]
        readonly property real components: group.componentsWidth(converted, widestValue)
        property real widestValue: 0

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
                horizontalAlignment: Text.AlignRight
                visible: !converted.spherical
                text: "|M|"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignRight
                uid: "atom_site_moment.symmform"
                text: qsTr("symmetry")
            }
        }

        delegate: TableRow {
            id: formRow

            required property string label
            required property string ion
            required property var mx
            required property var my
            required property var mz
            required property string symmform
            readonly property bool magnetic: ion !== "none"
            // The crystal-axis components, whose decimals a derived value without an s.u. shows.
            readonly property var crystal: parts.length > 0 && group.moments ? group.moments.components(index, "crystal_axes") : []
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
                property int columnAlignment: Text.AlignRight
                onImplicitWidthChanged: converted.widestValue = Math.max(converted.widestValue, implicitWidth)
                Component.onCompleted: converted.widestValue = Math.max(converted.widestValue, implicitWidth)

                objectName: `atomSiteMoment.form.0.${formRow.index}`
                horizontalAlignment: columnAlignment
                accepts: "number"
                uid: "atom_site_moment.crystalaxis_x"
                readOnly: !formRow.magnetic
                value: group.formText(formRow.parts, 0, formRow.crystal)
                ToolTip.text: formRow.parts.length > 3 ? group.suTip(formRow.parts, formRow.parts[3]) : ""
                onCommitted: text => group.moments.setComponent(formRow.index, group.form, 0, Number(text))
            }
            TextCell {
                property int columnAlignment: Text.AlignRight
                onImplicitWidthChanged: converted.widestValue = Math.max(converted.widestValue, implicitWidth)
                Component.onCompleted: converted.widestValue = Math.max(converted.widestValue, implicitWidth)

                objectName: `atomSiteMoment.form.1.${formRow.index}`
                horizontalAlignment: columnAlignment
                accepts: "number"
                uid: "atom_site_moment.crystalaxis_x"
                readOnly: !formRow.magnetic
                value: group.formText(formRow.parts, 1, formRow.crystal)
                ToolTip.text: formRow.parts.length > 4 ? group.suTip(formRow.parts, formRow.parts[4]) : ""
                onCommitted: text => group.moments.setComponent(formRow.index, group.form, 1, Number(text))
            }
            TextCell {
                property int columnAlignment: Text.AlignRight
                onImplicitWidthChanged: converted.widestValue = Math.max(converted.widestValue, implicitWidth)
                Component.onCompleted: converted.widestValue = Math.max(converted.widestValue, implicitWidth)

                objectName: `atomSiteMoment.form.2.${formRow.index}`
                horizontalAlignment: columnAlignment
                accepts: "number"
                uid: "atom_site_moment.crystalaxis_x"
                readOnly: !formRow.magnetic
                value: group.formText(formRow.parts, 2, formRow.crystal)
                ToolTip.text: formRow.parts.length > 5 ? group.suTip(formRow.parts, formRow.parts[5]) : ""
                onCommitted: text => group.moments.setComponent(formRow.index, group.form, 2, Number(text))
            }
            TextCell {
                property int columnAlignment: Text.AlignRight
                onImplicitWidthChanged: converted.widestValue = Math.max(converted.widestValue, implicitWidth)
                Component.onCompleted: converted.widestValue = Math.max(converted.widestValue, implicitWidth)

                objectName: `atomSiteMoment.formModulus.${formRow.index}`
                horizontalAlignment: columnAlignment
                visible: !converted.spherical
                readOnly: true
                value: group.modulusText(formRow.parts, formRow.crystal)
                ToolTip.text: formRow.parts.length > 7 ? group.suTip(formRow.parts, formRow.parts[7]) : ""
            }
            TextCell {
                property int columnAlignment: Text.AlignRight

                horizontalAlignment: columnAlignment
                readOnly: true
                value: formRow.symmform
            }
        }
    }
}
