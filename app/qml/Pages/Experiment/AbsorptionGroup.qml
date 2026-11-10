// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `absorption`: the family selector over the beam mode's families, then the
// family's field — CW μR, TOF ABSCOR1, none nothing.
Column {
    id: group

    property ExperimentViewModel experiment: null

    spacing: AppSizes.groupContentSpacing

    EaElements.GroupRow {
        spacing: AppSizes.inputSpacing
        SelectorField {
            objectName: "absorption.type"
            uid: "absorption.type"
            options: group.experiment ? group.experiment.absorptionTypeOptions : null
            token: group.experiment ? group.experiment.absorptionType : ""
            onSelected: token => group.experiment.absorptionType = token
        }
    }

    // The family's one field takes the full width, as the instrument's (edi ADR-0017 §5): μR or ABSCOR1.
    ParameterGrid {
        fields: group.experiment ? group.experiment.absorption : null
        prefix: "absorption"
        fillRows: true
    }
}
