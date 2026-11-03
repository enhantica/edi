// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// `data` / `data_range` (easydiffractionbeta's Measured range): the
// axis summary — minimum, maximum, the increment and the number of points — read-only for measured data and
// editable for an experiment without it (a simulation), whose grid it sets. The increment is one
// value when every step between neighbouring points reads the same at the field's display precision, and
// otherwise the smallest and largest step, "min–max" (TOF data, merged scans; ADR-0017 §6). `data` is a loop
// in `.edi`, so its points follow as a table ("loop in .edi — table in gui"): the axis, the measured intensity
// and its uncertainty, and the calculated intensity, read-only. The declared grid of a calculation-only
// experiment (`data_range`) is not a loop and has no table.
Column {
    id: group

    property ExperimentViewModel experiment: null
    readonly property RangeViewModel range: experiment ? experiment.measuredRange : null
    readonly property bool timeOfFlight: experiment !== null && experiment.beamMode === ExperimentViewModel.TimeOfFlight
    // The range's items: the `_data_range` of the experiment's beam mode.
    readonly property string rangeItem: timeOfFlight ? "data_range.time_of_flight" : "data_range.two_theta"
    readonly property string axisItem: timeOfFlight ? "data.time_of_flight" : "data.two_theta"
    readonly property bool editable: experiment !== null && experiment.calculationOnly

    // Each column, measured or calculated, in its item's display format; the table shows the data, it does not edit it.
    function shown(uid, value) {
        return ApplicationInfo.formShownValue(uid, value, true);
    }
    // The step, or the smallest and largest steps of an uneven pattern, in the step's display format.
    function increment(summary) {
        return ApplicationInfo.measuredRangeIncrement(summary);
    }

    spacing: AppSizes.groupContentSpacing

    EaElements.GroupRow {
        spacing: AppSizes.inputSpacing
        ValueField {
            objectName: "range.minimum"
            editable: group.editable
            onCommitted: text => group.experiment.setRange(Number(text), group.range.maximum, group.range.step)
            accepts: "number"
            uid: group.rangeItem + "_min"
            fieldValue: group.range ? group.range.minimum : ""
        }
        ValueField {
            objectName: "range.maximum"
            editable: group.editable
            onCommitted: text => group.experiment.setRange(group.range.minimum, Number(text), group.range.step)
            accepts: "number"
            uid: group.rangeItem + "_max"
            fieldValue: group.range ? group.range.maximum : ""
        }
        ValueField {
            objectName: "range.step"
            editable: group.editable
            onCommitted: text => group.experiment.setRange(group.range.minimum, group.range.maximum, Number(text))
            accepts: "number"
            uid: group.rangeItem + "_step"
            fieldValue: group.increment(group.range)
        }
        ValueField {
            objectName: "range.points"
            editable: false
            accepts: "integer"
            label: qsTr("points")
            fieldValue: group.range ? group.range.points : ""
        }
    }

    DataTable {
        id: table
        objectName: "data.list"
        visible: group.experiment !== null && !group.experiment.calculationOnly
        defaultInfoText: qsTr("No measured points")
        sourceModel: visible ? group.experiment.pattern : null

        // Each structure's curve, one column per structure at the end of the row. A Repeater places its cells before
        // itself, so the Repeater, declared last, takes the last width, kept narrow.
        readonly property var componentNames: group.experiment ? group.experiment.pattern.componentNames : []
        columns: ApplicationInfo.nativeListProjection(1)
        // A layout of its own (the owner, 2026-10-27): the count, the status and the structures' columns fit their
        // content, and the other numeric columns share the rest equally after their own widths.
        spreadColumns: [1, 2, 3, 4, 5, 6, 7]

        header: EaComponents.ListViewHeader {
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
            }
            HeaderLabel {
                uid: group.axisItem
                withUnits: true
            }
            HeaderLabel {
                uid: "data.intensity_meas"
            }
            HeaderLabel {
                uid: "data.intensity_meas_su"
            }
            HeaderLabel {
                uid: "data.intensity_calc"
            }
            HeaderLabel {
                uid: "data.d_spacing"
                withUnits: true
            }
            HeaderLabel {
                uid: "data.intensity_bkg"
            }
            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("resid")
            }
            HeaderLabel {
                uid: "data.calc_status"
            }
            Repeater {
                model: table.componentNames
                delegate: EaComponents.ListViewLabel {
                    required property string modelData
                    objectName: "data.header.component." + modelData
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData
                }
            }
        }

        delegate: TableRow {
            id: row

            // The roles by the model (its `x` role would shadow the delegate's own x).
            required property var model

            EaComponents.ListViewLabel {
                horizontalAlignment: Text.AlignHCenter
                marksCurrentRow: true
                text: row.index + 1
            }
            NumberLabel {
                horizontalAlignment: Text.AlignHCenter
                number: group.shown(group.axisItem, row.model.x)
                full: NumberText.plainFull(row.model.x)
            }
            NumberLabel {
                horizontalAlignment: Text.AlignHCenter
                number: group.shown("data.intensity_meas", row.model.intensityMeas)
                full: NumberText.plainFull(row.model.intensityMeas)
            }
            NumberLabel {
                horizontalAlignment: Text.AlignHCenter
                number: group.shown("data.intensity_meas_su", row.model.intensityMeasSu)
                full: NumberText.plainFull(row.model.intensityMeasSu)
            }
            NumberLabel {
                horizontalAlignment: Text.AlignHCenter
                number: group.shown("data.intensity_calc", row.model.intensityCalc)
                full: NumberText.plainFull(row.model.intensityCalc)
            }
            NumberLabel {
                horizontalAlignment: Text.AlignHCenter
                number: group.shown("data.d_spacing", row.model.dSpacing)
                full: NumberText.plainFull(row.model.dSpacing)
            }
            NumberLabel {
                horizontalAlignment: Text.AlignHCenter
                number: group.shown("data.intensity_bkg", row.model.intensityBkg)
                full: NumberText.plainFull(row.model.intensityBkg)
            }
            NumberLabel {
                horizontalAlignment: Text.AlignHCenter
                // The residual, meas − calc, on the measured intensity's scale and in its format.
                number: group.shown("data.intensity_meas", row.model.residual)
                full: NumberText.plainFull(row.model.residual)
            }
            // The point's calculation status as an icon, the word in its tooltip, as the experiments' fit column.
            IconCell {
                readonly property string status: !table.model ? "" : table.model.stale ? "pending" : table.model.calculationError ? "failed" : row.model.calcStatus ?? ""

                horizontalAlignment: Text.AlignHCenter
                objectName: `data.status.${row.index}`
                icon: status === "incl" ? FitOutcomes.icon("success") : status === "excl" ? "minus-circle" : status === "failed" ? FitOutcomes.icon("failed") : ""
                iconColor: String(status === "incl" ? EaStyle.Colors.green : status === "failed" ? EaStyle.Colors.red : EaStyle.Colors.themeForegroundMinor)
                ring: status === "pending"
                toolTip: status === "incl" ? Session.optionLabel("data.calc_status", "incl") : status === "excl" ? Session.optionLabel("data.calc_status", "excl") : status === "pending" ? qsTr("Pending") : status === "failed" ? qsTr("Failed") : ""
            }
            // One cell per structure on every row, an empty one where the point has no curve (an excluded point, or
            // before a calculation): the base centres a row's cells, so a row with fewer would sit apart from the
            // header.
            Repeater {
                model: ApplicationInfo.nativeListProjection(2)
                delegate: EaComponents.ListViewLabel {
                    required property var modelData
                    horizontalAlignment: Text.AlignHCenter
                    text: group.shown("pd_calc.component_intensities_net", modelData)
                }
            }
        }
    }
}
