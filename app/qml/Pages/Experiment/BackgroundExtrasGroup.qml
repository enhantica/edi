// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `background` in Extras: the settings of the background estimate (`_background_estimate`, edi ADR-0040) that
// Estimate and the auto mode use, for every background type. Two columns, as the minimizer's (the owner,
// 2026-10-20): first the calculated peaks and the type's own count (points for a line-segment background, the most
// terms for a polynomial or Chebyshev one), then the method and the numbers that go with it. A blank field stays
// empty and shows, in grey until something is typed, the value the estimate derives from the data (for the points
// and terms, how many it places; for the tolerance, its default); emptying a field makes it blank again. The
// smoothing applies to arpls and fabc only, so it is disabled for snip. Each box set to auto shows, in grey after it,
// what auto resolves to; why auto subtracted or ignored the calculated peaks goes to the messages when an estimate
// runs (the owner, 2026-10-20).
Column {
    id: group

    property ExperimentViewModel experiment: null
    readonly property bool snip: experiment !== null && experiment.estimateMethod === "snip"
    readonly property bool lineSegment: experiment === null || experiment.backgroundType === "line-segment"
    // The method in force, named in full with its reference: what it does and which fields it reads.
    readonly property var methodTips: ({
            "arpls": qsTr("arPLS (Baek et al. 2015): a smooth curve fitted with less and less weight on the points above it, so the peaks drop out; uses the curve smoothness."),
            "snip": qsTr("SNIP (Ryan et al. 1988): clips the peaks away, lowering each point to the mean of its neighbours up to a peak width apart; uses the peak width."),
            "fabc": qsTr("FABC (Cobas et al. 2006): finds the baseline points by a wavelet transform at the peak width, then draws a smooth curve through them; uses the peak width and the curve smoothness.")
        })

    // A blank field stays empty, so nothing it shows is ever saved as a setting; the value the estimate derives is
    // its placeholder, a whole number as the estimate's summary writes the width.
    function derived(value: real): string { return ApplicationInfo.derivedBackgroundValue(value); }

    spacing: AppSizes.groupContentSpacing

    Grid {
        id: fields

        readonly property real fieldWidth: (EaStyle.Sizes.sideBarContentWidth - fields.columnSpacing) / 2

        columns: 2
        columnSpacing: AppSizes.inputSpacing
        rowSpacing: AppSizes.groupContentSpacing

        SelectorField {
            objectName: "background_estimate.use_model"
            width: fields.fieldWidth
            uid: "background_estimate.use_model"
            options: group.experiment ? group.experiment.backgroundEstimateModels : null
            token: group.experiment ? group.experiment.backgroundEstimateUseModel : "auto"
            resolved: group.experiment ? group.experiment.estimateModelChoice : ""
            onSelected: token => group.experiment.backgroundEstimateUseModel = token
            helpToolTip: true
            ToolTip.text: qsTr("What Estimate and the automatic mode do with the peaks of the calculated pattern. Subtract removes them from the measured data before the background is estimated and keeps the background away from them, which helps where peaks overlap and the data never come down to the background. Ignore estimates from the measured data alone. Auto subtracts them only when the calculated pattern matches the data: subtracting them leaves at most 1% of the points below the noise, which peaks in the wrong place or too strong do.")
        }
        ValueField {
            objectName: "background_estimate.n_points"
            visible: group.lineSegment
            width: fields.fieldWidth
            label: qsTr("anchor points")
            // Blank: as many as the tolerance needs, which the placeholder counts.
            fieldValue: group.experiment && group.experiment.backgroundEstimatePoints > 0 ? group.experiment.backgroundEstimatePoints : ""
            placeholderText: group.derived(group.experiment ? group.experiment.estimatePoints : NaN)
            accepts: "integer"
            clearable: true
            onCommitted: text => group.experiment.backgroundEstimatePoints = text === "" ? 0 : Number(text)
        }
        ValueField {
            objectName: "background_estimate.max_terms"
            visible: !group.lineSegment
            width: fields.fieldWidth
            uid: "background_estimate.max_terms"
            // Blank: at most 12, as many as the tolerance needs, which the placeholder counts.
            fieldValue: group.experiment && group.experiment.backgroundEstimateMaxTerms > 0 ? group.experiment.backgroundEstimateMaxTerms : ""
            placeholderText: group.derived(group.experiment ? group.experiment.estimateTerms : NaN)
            accepts: "integer"
            clearable: true
            onCommitted: text => group.experiment.backgroundEstimateMaxTerms = text === "" ? 0 : Number(text)
        }
        SelectorField {
            objectName: "background_estimate.method"
            width: fields.fieldWidth
            label: qsTr("baseline method")
            options: group.experiment ? group.experiment.backgroundEstimateMethods : null
            token: group.experiment ? group.experiment.backgroundEstimateMethod : ""
            resolved: group.experiment ? group.experiment.estimateMethod : ""
            onSelected: token => group.experiment.backgroundEstimateMethod = token
            helpToolTip: true
            ToolTip.text: group.methodTips[group.experiment ? group.experiment.estimateMethod : ""] ?? ""
        }
        ValueField {
            objectName: "background_estimate.width"
            width: fields.fieldWidth
            label: qsTr("peak width (points)")
            fieldValue: group.experiment && !isNaN(group.experiment.backgroundEstimateWidth) ? group.experiment.backgroundEstimateWidth : ""
            placeholderText: group.derived(group.experiment ? group.experiment.estimateWidth : NaN)
            accepts: "number"
            clearable: true
            onCommitted: text => group.experiment.backgroundEstimateWidth = text === "" ? NaN : Number(text)
        }
        ValueField {
            objectName: "background_estimate.smoothness"
            width: fields.fieldWidth
            label: qsTr("curve smoothness")
            enabled: !group.snip
            editable: !group.snip
            fieldValue: group.experiment && !group.snip && !isNaN(group.experiment.backgroundEstimateSmoothness) ? group.experiment.backgroundEstimateSmoothness : ""
            placeholderText: group.snip ? "" : group.derived(group.experiment ? group.experiment.estimateSmoothness : NaN)
            accepts: "number"
            clearable: true
            onCommitted: text => group.experiment.backgroundEstimateSmoothness = text === "" ? NaN : Number(text)
        }
        ValueField {
            objectName: "background_estimate.tolerance"
            width: fields.fieldWidth
            label: qsTr("noise tolerance")
            fieldValue: group.experiment && !isNaN(group.experiment.backgroundEstimateTolerance) ? group.experiment.backgroundEstimateTolerance : ""
            placeholderText: group.experiment ? String(group.experiment.estimateTolerance) : ""
            accepts: "number"
            clearable: true
            onCommitted: text => group.experiment.backgroundEstimateTolerance = text === "" ? NaN : Number(text)
        }
    }
    EaElements.Label {
        objectName: "background_estimate.note"
        width: EaStyle.Sizes.sideBarContentWidth
        wrapMode: Text.Wrap
        visible: text !== ""
        text: group.experiment ? group.experiment.estimateNote : ""
    }
}
