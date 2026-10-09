// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Logic as EaLogic
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

    readonly property bool editable: experiment !== null && experiment.calculationOnly
    property ExperimentViewModel experiment: null
    readonly property RangeViewModel range: experiment ? experiment.measuredRange : null
    readonly property bool timeOfFlight: experiment !== null && experiment.beamMode === ExperimentViewModel.TimeOfFlight
    readonly property string units: timeOfFlight ? "µs" : "°"

    // "inc": the steps at the base's default precision, as ValueField shows a number.
    function increment(summary) {
        if (!summary)
            return "";
        const smallest = EaLogic.Utils.toDefaultPrecision(summary.stepMinimum);
        const largest = EaLogic.Utils.toDefaultPrecision(summary.stepMaximum);
        return smallest === largest ? summary.step : `${smallest}–${largest}`;
    }
    function intensity(value) {
        return value === undefined || isNaN(value) ? "" : NumberText.plain(Number(value.toFixed(3)), 10);
    }

    // The axis by the app's one rule for numbers (NumberText); an intensity first rounded to three decimals,
    // so a calculated value that is effectively zero (1e-46 at a pattern's tail, its digits floating-point
    // noise that differs by platform) reads 0. The table shows the data, it does not edit it.
    function shown(value) {
        return value === undefined || isNaN(value) ? "" : NumberText.plain(value, 10);
    }

    spacing: AppSizes.groupContentSpacing

    EaElements.GroupRow {
        ValueField {
            accepts: "number"
            editable: group.editable
            fieldValue: group.range ? group.range.minimum : ""
            label: qsTr("min")
            objectName: "range.minimum"
            unit: group.units

            onCommitted: text => group.experiment.setRange(Number(text), group.range.maximum, group.range.step)
        }
        ValueField {
            accepts: "number"
            editable: group.editable
            fieldValue: group.range ? group.range.maximum : ""
            label: qsTr("max")
            objectName: "range.maximum"
            unit: group.units

            onCommitted: text => group.experiment.setRange(group.range.minimum, Number(text), group.range.step)
        }
        ValueField {
            accepts: "number"
            editable: group.editable
            fieldValue: group.increment(group.range)
            label: qsTr("inc")
            objectName: "range.step"
            unit: group.units

            onCommitted: text => group.experiment.setRange(group.range.minimum, group.range.maximum, Number(text))
        }
        ValueField {
            accepts: "integer"
            editable: false
            fieldValue: group.range ? group.range.points : ""
            label: qsTr("points")
            objectName: "range.points"
        }
    }
    DataTable {
        id: table

        columnWidths: [numberColumnWidth, -1, -1, -1, -1, -1, -1, -1, -1]
        defaultInfoText: qsTr("No measured points")
        model: visible ? group.experiment.pattern : null
        objectName: "data.list"
        visible: group.experiment !== null && !group.experiment.calculationOnly

        delegate: EaComponents.ListViewDelegate {
            id: row

            required property int index
            // The roles by the model (its `x` role would shadow the delegate's own x).
            required property var model

            EaComponents.TableViewLabel {
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            EaComponents.TableViewLabel {
                text: group.shown(row.model.x)
            }
            EaComponents.TableViewLabel {
                text: group.intensity(row.model.intensityMeas)
            }
            EaComponents.TableViewLabel {
                text: group.intensity(row.model.intensityMeasSu)
            }
            EaComponents.TableViewLabel {
                text: group.intensity(row.model.intensityCalc)
            }
            EaComponents.TableViewLabel {
                text: group.shown(row.model.dSpacing)
            }
            EaComponents.TableViewLabel {
                text: group.intensity(row.model.intensityBkg)
            }
            EaComponents.TableViewLabel {
                text: group.intensity(row.model.residual)
            }
            EaComponents.TableViewLabel {
                text: table.model.stale ? qsTr("pending") : table.model.calculationError ? qsTr("failed") : row.model.calcStatus ?? ""
            }
        }
        header: EaComponents.ListViewHeader {
            EaComponents.TableViewLabel {
                text: qsTr("id")
            }
            EaComponents.TableViewLabel {
                text: group.timeOfFlight ? qsTr("TOF (µs)") : qsTr("2θ (°)")
            }
            EaComponents.TableViewLabel {
                text: qsTr("I meas")
            }
            EaComponents.TableViewLabel {
                text: qsTr("σ(I meas)")
            }
            EaComponents.TableViewLabel {
                text: qsTr("I calc")
            }
            EaComponents.TableViewLabel {
                text: qsTr("d (Å)")
            }
            EaComponents.TableViewLabel {
                text: qsTr("I bkg")
            }
            EaComponents.TableViewLabel {
                text: qsTr("meas − calc")
            }
            EaComponents.TableViewLabel {
                text: qsTr("status")
            }
        }
    }
}
