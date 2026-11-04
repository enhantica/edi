// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `magnetic_form_factor` (the owner, 2026-11-03): one row per magnetic atom type. The type and its ion are read only;
// the ion is chosen in the Magnetic moments table. The approximation picks which radial integrals the form factor
// sums, and the coefficients it uses are edited and fitted like any other value: C2 in the dipole approximation, C2,
// C4 and C6 beyond it. A coefficient the approximation does not use, or whose term the ion's table lacks, is greyed
// out. C2's tooltip gives the Landé g it stands for, C2 = 2/g - 1.
Column {
    id: group

    property StructureViewModel structure: null
    readonly property MagneticFormFactorListModel formFactors: structure ? structure.magneticFormFactors : null
    readonly property real typeWidth: EaStyle.Sizes.fontPixelSize * 4
    readonly property real coefficientWidth: EaStyle.Sizes.fontPixelSize * 5.5

    // The Landé g a C2 stands for, g = 2 / (1 + C2); a dash where it has none.
    function landeText(value) {
        if (typeof value !== "number" || !isFinite(value) || value === -1)
            return "—";
        return Number((2 / (1 + value)).toPrecision(4)).toString();
    }

    spacing: AppSizes.groupContentSpacing

    DataTable {
        id: table
        objectName: "magneticFormFactors.list"
        defaultInfoText: qsTr("No magnetic atom types")
        sourceModel: group.formFactors

        columns: [numberColumnWidth, group.typeWidth, group.typeWidth, -1, group.coefficientWidth, group.coefficientWidth, group.coefficientWidth]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "magnetic_form_factor.type_symbol"
                text: qsTr("Type")
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "magnetic_form_factor.ion"
                text: qsTr("Ion")
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignLeft
                uid: "magnetic_form_factor.approximation"
                text: qsTr("Approximation")
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "magnetic_form_factor.j2_coefficient"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "magnetic_form_factor.j4_coefficient"
            }
            HeaderLabel {
                horizontalAlignment: Text.AlignHCenter
                uid: "magnetic_form_factor.j6_coefficient"
            }
        }

        delegate: TableRow {
            id: row

            required property string type
            required property string ion
            required property string approximation
            required property var c2
            required property var c4
            required property var c6
            readonly property int used: row.approximation === "dipole" ? 1 : row.approximation === "beyond_dipole" ? 3 : 0

            // Whether coefficient n (0: C2, 1: C4, 2: C6) is one the row's approximation uses and its ion's table
            // carries.
            function takes(n) {
                return n < row.used && row.ion !== "" && !!group.formFactors && group.formFactors.hasTerm(row.index, n);
            }

            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            TextCell {
                objectName: `magneticFormFactor.type.${row.index}`
                horizontalAlignment: Text.AlignLeft
                readOnly: true
                value: row.type
            }
            TextCell {
                objectName: `magneticFormFactor.ion.${row.index}`
                horizontalAlignment: Text.AlignLeft
                readOnly: true
                value: row.ion
            }
            ComboCell {
                SearchableComboBox {
                    readonly property var tokens: group.formFactors ? group.formFactors.approximations : []

                    horizontalAlignment: Text.AlignLeft
                    objectName: `magneticFormFactor.approximation.${row.index}`
                    inTable: true
                    anchors.verticalCenter: parent.verticalCenter
                    model: tokens.map(token => Session.optionLabel("magnetic_form_factor.approximation", token))
                    currentIndex: tokens.indexOf(row.approximation)
                    // A form-factor row may come or go, which rebuilds this table: it runs after the popup has closed.
                    onActivated: index => {
                        const at = row.index;
                        const token = tokens[index];
                        const formFactors = group.formFactors;
                        currentIndex = Qt.binding(() => tokens.indexOf(row.approximation));
                        Qt.callLater(() => formFactors.setApproximation(at, token));
                    }
                    ToolTip.text: Session.optionTooltip("magnetic_form_factor.approximation", row.approximation)
                }
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `magneticFormFactor.c2.${row.index}`
                enabled: row.takes(0) && !!row.c2 && refinable
                item: row.c2 ? row.c2 : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1, Landé g = %2 (C₂ = 2/g − 1; %3)").arg(item.shortName).arg(group.landeText(item.value)).arg("_magnetic_form_factor.j2_coefficient") : ""
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `magneticFormFactor.c4.${row.index}`
                enabled: row.takes(1) && !!row.c4 && refinable
                item: row.c4 ? row.c4 : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1 (%2)").arg(item.shortName).arg("_magnetic_form_factor.j4_coefficient") : ""
                helpToolTip: true
            }
            ParameterCell {
                columnAlignment: Text.AlignHCenter
                significantDigits: 5
                objectName: `magneticFormFactor.c6.${row.index}`
                enabled: row.takes(2) && !!row.c6 && refinable
                item: row.c6 ? row.c6 : null
                text: item !== null ? value : ""
                ToolTip.text: item !== null ? qsTr("%1 (%2)").arg(item.shortName).arg("_magnetic_form_factor.j6_coefficient") : ""
                helpToolTip: true
            }
        }
    }
}
