// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// The untitled experiment selector heading the original's Analysis sidebar: which experiment's
// pattern the chart shows. `last`, as in the original (SideBarBasic.qml): an untitled group's bottom
// border is drawn inside its content, across the selector.
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null

    objectName: "analysis.experimentSelector"
    collapsible: false
    last: true

    // The same selector as the Experiment and Structure pages' (BlockSelector: number, coloured icon, name),
    // over the one current experiment the project holds, so choosing here or there is one choice (edi
    // ADR-0017 §7).
    BlockSelector {
        objectName: "analysis.experiment"
        blocks: group.project ? group.project.experiments : null
        blocksTextRole: "label"
        blockKind: "experiment"
        blockIndex: group.project ? group.project.currentExperimentIndex : -1
        onBlockActivated: index => group.project.currentExperimentIndex = index
    }
}
