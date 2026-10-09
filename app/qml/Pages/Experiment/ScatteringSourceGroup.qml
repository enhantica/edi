// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Elements as EaElements

import edi.app

// `scattering_source` (edi ADR-0014): one selector per item of the experiment's
// probe — neutron: the scattering-length table; X-ray: the form factor and the dispersion — over its
// known values, an absent item showing its default.
EaElements.GroupRow {
    id: row

    property ExperimentViewModel experiment: null

    Repeater {
        model: row.experiment ? row.experiment.scatteringSource : null
        delegate: Item {
            id: item

            required property var model

            width: (EaStyle.Sizes.sideBarContentWidth - (row.experiment.scatteringSource.count - 1) * AppSizes.fieldSpacing) / row.experiment.scatteringSource.count
            height: selector.height

            SelectorField {
                id: selector
                objectName: `scatteringSource.${item.model.name}`
                width: item.width
                label: item.model.isDeclared ? item.model.name : qsTr("%1 (default)").arg(item.model.name)
                options: item.model.options
                token: item.model.effectiveToken
                onSelected: token => row.experiment.scatteringSource.select(item.model.name, token)
            }
        }
    }
}
