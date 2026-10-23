// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `extinction`: a single crystal's extinction type, then that type's fields (edi ADR-0049): none, the mosaic
// distribution and spread for type I, the domain radius for type II, all three for mixed.
Column {
    id: group

    property ExperimentViewModel experiment: null

    spacing: AppSizes.groupContentSpacing

    EaElements.GroupRow {
        spacing: AppSizes.inputSpacing
        SelectorField {
            objectName: "extinction.type"
            label: qsTr("type")
            options: group.experiment ? group.experiment.extinctionTypeOptions : null
            token: group.experiment ? group.experiment.extinctionType : ""
            onSelected: token => group.experiment.extinctionType = token
        }
        SelectorField {
            objectName: "extinction.mosaicDistribution"
            visible: group.experiment !== null && group.experiment.mosaicDistribution !== ""
            label: qsTr("mosaic distribution")
            options: group.experiment ? group.experiment.mosaicDistributionOptions : null
            token: group.experiment ? group.experiment.mosaicDistribution : ""
            onSelected: token => group.experiment.mosaicDistribution = token
        }
    }

    ParameterGrid {
        fields: group.experiment ? group.experiment.extinction : null
        prefix: "extinction"
        // Two columns, as the selectors above: a lone field keeps the width of the type selector.
        maxColumns: 2
    }
}
