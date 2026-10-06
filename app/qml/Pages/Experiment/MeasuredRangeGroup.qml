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

    property ExperimentViewModel experiment: null
    readonly property RangeViewModel range: experiment ? experiment.measuredRange : null
    readonly property bool timeOfFlight: experiment !== null && experiment.beamMode === ExperimentViewModel.TimeOfFlight
    readonly property string units: timeOfFlight ? "µs" : "°"
    readonly property bool editable: experiment !== null && experiment.calculationOnly

    // The axis at six significant digits; an intensity at three decimals, so a calculated value that is
    // effectively zero (1e-46 at a pattern's tail, its digits floating-point noise that differs by platform)
    // reads 0. The table shows the data, it does not edit it.
    function shown(value) {
        return value === undefined || isNaN(value) ? "" : String(Number(value.toPrecision(6)));
    }
    function intensity(value) {
        return value === undefined || isNaN(value) ? "" : String(Number(value.toFixed(3)));
    }
    // "inc": the steps at the base's default precision, as ValueField shows a number.
    function increment(summary) {
        if (!summary)
            return "";
        const smallest = EaLogic.Utils.toDefaultPrecision(summary.stepMinimum);
        const largest = EaLogic.Utils.toDefaultPrecision(summary.stepMaximum);
        return smallest === largest ? summary.step : `${smallest}–${largest}`;
    }

    spacing: AppSizes.groupContentSpacing

    EaElements.GroupRow {
        ValueField {
            objectName: "range.minimum"
            editable: group.editable
            onCommitted: text => group.experiment.setRange(Number(text), group.range.maximum, group.range.step)
            accepts: "number"
            label: qsTr("min")
            unit: group.units
            fieldValue: group.range ? group.range.minimum : ""
        }
        ValueField {
            objectName: "range.maximum"
            editable: group.editable
            onCommitted: text => group.experiment.setRange(group.range.minimum, Number(text), group.range.step)
            accepts: "number"
            label: qsTr("max")
            unit: group.units
            fieldValue: group.range ? group.range.maximum : ""
        }
        ValueField {
            objectName: "range.step"
            editable: group.editable
            onCommitted: text => group.experiment.setRange(group.range.minimum, group.range.maximum, Number(text))
            accepts: "number"
            label: qsTr("inc")
            unit: group.units
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

    EaComponents.TableView {
        id: table
        objectName: "data.list"
        visible: group.experiment !== null && !group.experiment.calculationOnly
        defaultInfoText: qsTr("No measured points")
        model: visible ? group.experiment.pattern : null

        header: EaComponents.TableViewHeader {
            EaComponents.TableViewLabel {
                width: AppSizes.dataIndexColumnWidth
            }
            EaComponents.TableViewLabel {
                flexibleWidth: true
                text: group.timeOfFlight ? qsTr("TOF (µs)") : qsTr("2θ (°)")
            }
            EaComponents.TableViewLabel {
                width: AppSizes.dataColumnWidth
                text: qsTr("I meas")
            }
            EaComponents.TableViewLabel {
                width: AppSizes.dataColumnWidth
                text: qsTr("σ(I meas)")
            }
            EaComponents.TableViewLabel {
                width: AppSizes.dataColumnWidth
                text: qsTr("I calc")
            }
        }

        delegate: EaComponents.TableViewDelegate {
            id: row

            required property int index
            // The roles by the model (its `x` role would shadow the delegate's own x).
            required property var model

            EaComponents.TableViewLabel {
                width: AppSizes.dataIndexColumnWidth
                color: EaStyle.Colors.themeForegroundMinor
                text: row.index + 1
            }
            EaComponents.TableViewLabel {
                width: table.headerLabelItems.length > 1 ? table.headerLabelItems[1].width : 0
                text: group.shown(row.model.x)
            }
            EaComponents.TableViewLabel {
                width: AppSizes.dataColumnWidth
                text: group.intensity(row.model.intensityMeas)
            }
            EaComponents.TableViewLabel {
                width: AppSizes.dataColumnWidth
                text: group.intensity(row.model.intensityMeasSu)
            }
            EaComponents.TableViewLabel {
                width: AppSizes.dataColumnWidth
                text: group.intensity(row.model.intensityCalc)
            }
        }
    }
}
