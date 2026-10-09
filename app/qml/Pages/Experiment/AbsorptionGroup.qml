// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `absorption`: the family selector over the beam mode's families, then the
// family's fields — CW μR, TOF the ABSCOR pair, none nothing.
Column {
    id: group

    property ExperimentViewModel experiment: null

    spacing: AppSizes.groupContentSpacing

    EaElements.GroupRow {
        SelectorField {
            label: qsTr("type")
            objectName: "absorption.type"
            options: group.experiment ? group.experiment.absorptionTypeOptions : null
            token: group.experiment ? group.experiment.absorptionType : ""

            onSelected: token => group.experiment.absorptionType = token
        }
    }

    // The family's fields share the full width, as the instrument's (edi ADR-0017 §5): μR alone, ABSCOR1 and
    // ABSCOR2 half each.
    ParameterGrid {
        fields: group.experiment ? group.experiment.absorption : null
        fillRows: true
        prefix: "absorption"
    }
}
