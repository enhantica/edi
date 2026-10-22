// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import edi.app

// `extinction`: a single crystal's Becker-Coppens extinction, the crystal's radius and its mosaicity.
Column {
    id: group

    property ExperimentViewModel experiment: null

    spacing: AppSizes.groupContentSpacing

    ParameterGrid {
        fields: group.experiment ? group.experiment.extinction : null
        prefix: "extinction"
        fillRows: true
    }
}
