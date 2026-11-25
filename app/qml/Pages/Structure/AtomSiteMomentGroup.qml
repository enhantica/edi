// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `atom_site_moment` (edi ADR-0078; the owner, 2026-11-03): one row per atom site, as Atomic displacement — its id,
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
    readonly property string form: options ? options.momentForm : "crystal_axes"
    readonly property bool crystalAxes: form === "crystal_axes"
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
        // Outside 0.001 to 1000 the rule for numbers writes it with a power of ten, its s.u. on hover.
        if (value !== 0 && (Math.abs(value) < 0.001 || Math.abs(value) >= 1000))
            return NumberText.parameter(value, su);
        // The value alone, rounded by its s.u.; the s.u. shows in its popup (DerivedCell; the owner, 2026-11-23).
        const text = NumberText.ruled(value, su);
        if (text)
            return text.value;
        const decimals = Math.max(0, ...(crystal ?? []).slice(0, 3).map(group.decimalsOf));
        return value.toFixed(decimals);
    }
    // An angle with its unit, a dash as it is.
    function degrees(text) {
        return text === "" || text === "\u2014" ? text : `${text}\u00b0`;
    }
    // The |M| column's text, from the row's components in any form (index 6, its s.u. 7) and its crystal-axis ones.
    function modulusText(parts, crystal) {
        if (!parts || parts.length < 8)
            return "";
        return group.derivedText(parts[6], parts[7], crystal);
    }
    // Value k of a form (0-2): a dash where the moment does not fix it (index 9 marks them, bit k), else the value
    // with its s.u.
    function formText(parts, k, crystal) {
        if (!parts || parts.length < 6)
            return "";
        if (group.undetermined(parts, k))
            return "\u2014";
        return group.derivedText(parts[k], parts[k + 3], crystal);
    }
    function undetermined(parts, k) {
        return parts.length > 9 && (parts[9] & (1 << k)) !== 0;
    }
    // Why an undetermined angle has no value: a zero moment fixes neither angle, one along z no azimuth.
    function undeterminedTip(parts) {
        return group.undetermined(parts, 1) ? qsTr("Undetermined: the moment is zero") : qsTr("Undetermined: the moment is along z");
    }
    // The value an edit starts from, as it shows but always plain digits.
    function editText(parts, k) {
        if (!parts || parts.length < 6 || group.undetermined(parts, k) || !isFinite(parts[k]))
            return "";
        const text = NumberText.ruled(parts[k], parts[k + 3]);
        return text ? text.value : NumberText.plain(parts[k], 10);
    }
    // A value's s.u. as its popup shows it: none without one, or where the moment does not fix the value.
    function suText(value, su) {
        return typeof su === "number" && su > 0 ? NumberText.error(su, 0, value) : "";
    }
    // The spherical form's items; the Cartesian one has none. An item's full name, as its crystal-axis component's.
    readonly property var sphericalItems: ["spherical_modulus", "spherical_polar", "spherical_azimuthal"]
    function itemName(component, item) {
        return component ? component.fullName.slice(0, component.fullName.lastIndexOf(".") + 1) + item : "";
    }
    // A derived value's tooltip: its s.u. and how it was found, from the fit's covariance (index 8) or propagated
    // from the components' own s.u. as if they were uncorrelated (edi ADR-0078).
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
        // Greyed until a site has a moment: every site starts with none (the owner, 2026-11-14).
        writable: group.structure !== null && group.structure.magnetic
        disabledReason: qsTr("Choose a magnetic ion for a site to give it a moment")
        onSelected: token => group.options.momentForm = token
    }

    DataTable {
        id: table
        objectName: "atomSiteMoments.list"
        visible: group.crystalAxes
        defaultInfoText: qsTr("No atom sites yet")
        sourceModel: group.moments

        // The symmetry form takes what the equal component columns leave, right-aligned like the components, so it
        // stands clear of |M| (the owner, 2026-11-03).
        // |M| and its two angles beside the components, read only (edi ADR-0089 point 6).
        // Its columns by kind (the shared column model, DataTable.columnKinds; ADR-0103 decision 4).
        columnKinds: ["index", "short", "short", "value", "value", "value", "value", "value", "value", "text"]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
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
                // "Ion": the group's title already says magnetic (no title repeats its group's, N10).
                text: qsTr("Ion")
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
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignRight
                text: Session.label("atom_site_moment.spherical_modulus")
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignRight
                // The angle alone, its unit in the cells, so the title is never cut (the owner, 2026-11-23).
                text: qsTr("θ")
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignRight
                text: qsTr("φ")
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignRight
                uid: "atom_site_moment.symmform"
                text: qsTr("Symmetry")
            }
        }

        delegate: TableRow {
            id: row

            // The moment in spherical form, for the read-only angles; read again whenever a component changes.
            readonly property var sphericalParts: {
                const changes = [row.mx, row.my, row.mz].map(item => item ? [item.value, item.uncertainty] : null);
                if (!row.magnetic || !group.moments || !changes || group.moments.revision < 0)
                    return [];
                return group.moments.components(row.index, "spherical");
            }

            required property string label
            required property string ion
            required property var mx
            required property var my
            required property var mz
            required property string symmform
            // The site's element: the ion choices follow it.
            required property string type
            readonly property bool magnetic: ion !== "none"

            EaComponents.ListViewLabel {
                elide: Text.ElideRight
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
                    model: group.moments ? group.moments.ions(row.index, row.type) : []
                    currentIndex: group.moments ? group.moments.ions(row.index, row.type).indexOf(row.ion) : -1
                    // A moment row comes or goes, which rebuilds this table: it runs after the popup has closed.
                    onActivated: index => {
                        const site = row.index;
                        const ion = textAt(index);
                        const moments = group.moments;
                        currentIndex = Qt.binding(() => group.moments ? group.moments.ions(row.index, row.type).indexOf(row.ion) : -1);
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
            DerivedCell {
                objectName: `atomSiteMoment.modulus.${row.index}`
                // Read again whenever a component's value or s.u. changes.
                readonly property var parts: {
                    const changes = [row.mx, row.my, row.mz].map(item => item ? [item.value, item.uncertainty] : null);
                    if (!row.magnetic || !group.moments || !changes || group.moments.revision < 0)
                        return [];
                    return group.moments.components(row.index, "crystal_axes");
                }
                shownValue: group.modulusText(parts, parts)
                fullValue: parts.length > 7 ? NumberText.plainFull(parts[6]) : ""
                uncertainty: parts.length > 7 ? group.suText(parts[6], parts[7]) : ""
                uid: "atom_site_moment.spherical_modulus"
                derivedName: group.itemName(row.mx, "spherical_modulus")
                derivedUnits: row.mx ? row.mx.displayUnits : ""
            }
            // The polar and azimuthal angles, read only: the spherical form's own, a dash where the moment fixes none.
            DerivedCell {
                objectName: `atomSiteMoment.angle1.${row.index}`
                readonly property var parts: row.sphericalParts
                shownValue: parts.length > 5 ? group.degrees(group.formText(parts, 1, parts)) : ""
                fullValue: parts.length > 5 && !group.undetermined(parts, 1) ? NumberText.plainFull(parts[1]) : ""
                uncertainty: parts.length > 5 && !group.undetermined(parts, 1) ? group.suText(parts[1], parts[4]) : ""
                uid: "atom_site_moment.spherical_polar"
                derivedName: group.itemName(row.mx, "spherical_polar")
                derivedUnits: "\u00b0"
            }
            DerivedCell {
                objectName: `atomSiteMoment.angle2.${row.index}`
                readonly property var parts: row.sphericalParts
                shownValue: parts.length > 5 ? group.degrees(group.formText(parts, 2, parts)) : ""
                fullValue: parts.length > 5 && !group.undetermined(parts, 2) ? NumberText.plainFull(parts[2]) : ""
                uncertainty: parts.length > 5 && !group.undetermined(parts, 2) ? group.suText(parts[2], parts[5]) : ""
                uid: "atom_site_moment.spherical_azimuthal"
                derivedName: group.itemName(row.mx, "spherical_azimuthal")
                derivedUnits: "\u00b0"
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
        defaultInfoText: qsTr("No atom sites yet")
        sourceModel: group.moments

        readonly property bool spherical: group.form === "spherical"
        readonly property var titles: spherical ? [Session.label("atom_site_moment.spherical_modulus"), qsTr("θ (deg)"), qsTr("φ (deg)")] : [qsTr("Mx (x ‖ a)"), qsTr("My"), qsTr("Mz (z ‖ c*)")]

        // In spherical form the modulus is the first component, so the |M| column takes no width and is hidden.
        // Its columns by kind (the shared column model, DataTable.columnKinds; ADR-0103 decision 4).
        columnKinds: ["index", "short", "short", "value", "value", "value", spherical ? 0.001 : "value", "text"]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "atom_site.id"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "magnetic_form_factor.ion"
                // "Ion": the group's title already says magnetic (no title repeats its group's, N10).
                text: qsTr("Ion")
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                text: converted.titles[0]
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                text: converted.titles[1]
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                text: converted.titles[2]
            }
            EaComponents.ListViewLabel {
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignRight
                visible: !converted.spherical
                text: Session.label("atom_site_moment.spherical_modulus")
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignRight
                uid: "atom_site_moment.symmform"
                text: qsTr("Symmetry")
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
            // The site's element: the ion choices follow it.
            required property string type
            readonly property bool magnetic: ion !== "none"
            // The crystal-axis components, whose decimals a derived value without an s.u. shows.
            readonly property var crystal: parts.length > 0 && group.moments ? group.moments.components(index, "crystal_axes") : []
            // The moment in the chosen form, read again whenever a crystal-axis value or s.u. changes.
            readonly property var parts: {
                const changes = [mx, my, mz].map(item => item ? [item.value, item.uncertainty] : null);
                return magnetic && group.moments && changes && group.moments.revision >= 0 ? group.moments.components(index, group.form) : [];
            }
            // Component k's popup: its value in full, its s.u., its item, its name, its unit and its cell's tooltip.
            function determined(k): bool {
                return parts.length > 5 && !group.undetermined(parts, k);
            }
            function full(k): string {
                return determined(k) ? NumberText.plainFull(parts[k]) : "";
            }
            function su(k): string {
                return determined(k) ? group.suText(parts[k], parts[k + 3]) : "";
            }
            function uid(k): string {
                return converted.spherical ? "atom_site_moment." + group.sphericalItems[k] : "";
            }
            function name(k): string {
                return converted.spherical ? group.itemName(mx, group.sphericalItems[k]) : qsTr("%1 of %2").arg(["Mx", "My", "Mz"][k]).arg(label);
            }
            function unit(k): string {
                return converted.spherical && k > 0 ? "\u00b0" : mx ? mx.displayUnits : "";
            }
            function tip(k): string {
                return group.undetermined(parts, k) ? group.undeterminedTip(parts) : parts.length > 5 ? group.suTip(parts, parts[k + 3]) : "";
            }

            EaComponents.ListViewLabel {
                elide: Text.ElideRight
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
            // Each component opens its popup, as every value's cell does: typed there, converted back to the crystal axes.
            DerivedCell {
                objectName: `atomSiteMoment.form.0.${formRow.index}`
                shownValue: group.formText(formRow.parts, 0, formRow.crystal)
                fullValue: formRow.full(0)
                uncertainty: formRow.su(0)
                uid: formRow.uid(0)
                derivedName: formRow.name(0)
                derivedUnits: formRow.unit(0)
                editable: formRow.magnetic
                editText: group.editText(formRow.parts, 0)
                ToolTip.text: formRow.tip(0)
                onCommitted: number => group.moments.setComponent(formRow.index, group.form, 0, number)
            }
            DerivedCell {
                objectName: `atomSiteMoment.form.1.${formRow.index}`
                shownValue: group.formText(formRow.parts, 1, formRow.crystal)
                fullValue: formRow.full(1)
                uncertainty: formRow.su(1)
                uid: formRow.uid(1)
                derivedName: formRow.name(1)
                derivedUnits: formRow.unit(1)
                editable: formRow.magnetic
                editText: group.editText(formRow.parts, 1)
                ToolTip.text: formRow.tip(1)
                onCommitted: number => group.moments.setComponent(formRow.index, group.form, 1, number)
            }
            DerivedCell {
                objectName: `atomSiteMoment.form.2.${formRow.index}`
                shownValue: group.formText(formRow.parts, 2, formRow.crystal)
                fullValue: formRow.full(2)
                uncertainty: formRow.su(2)
                uid: formRow.uid(2)
                derivedName: formRow.name(2)
                derivedUnits: formRow.unit(2)
                editable: formRow.magnetic
                editText: group.editText(formRow.parts, 2)
                ToolTip.text: formRow.tip(2)
                onCommitted: number => group.moments.setComponent(formRow.index, group.form, 2, number)
            }
            // Derived, as |M| in the crystal-axes table: its value alone, its s.u. in the popup a click opens (F3a).
            DerivedCell {
                objectName: `atomSiteMoment.formModulus.${formRow.index}`
                visible: !converted.spherical
                shownValue: group.modulusText(formRow.parts, formRow.crystal)
                fullValue: formRow.parts.length > 7 ? NumberText.plainFull(formRow.parts[6]) : ""
                uncertainty: formRow.parts.length > 7 ? group.suText(formRow.parts[6], formRow.parts[7]) : ""
                uid: "atom_site_moment.spherical_modulus"
                derivedName: group.itemName(formRow.mx, "spherical_modulus")
                derivedUnits: formRow.mx ? formRow.mx.displayUnits : ""
            }
            TextCell {
                property int columnAlignment: Text.AlignRight

                horizontalAlignment: columnAlignment
                readOnly: true
                value: formRow.symmform
            }
        }
    }

    // An edit the site symmetry does not allow is not made: the reason shows in the app's error popup and the Messages
    // center (the owner, 2026-11-19).
    Connections {
        target: group.moments
        function onRefusalChanged() {
            if (group.moments && group.moments.refusal !== "") {
                Session.reportRefusal(group.moments.refusal);
                group.moments.clearRefusal();
            }
        }
    }
}
