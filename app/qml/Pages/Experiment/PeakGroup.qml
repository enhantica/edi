// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick

import EasyApplication.Gui.Elements as EaElements

import edi.app

// `peak`:
// the profile selector over the beam mode's profiles, the profile's fields a row per family, then its
// asymmetry fields when the profile declares asymmetry, with no subheadings for now (owner, 2026-09-29;
// edi ADR-0017 §5). The peak window `cutoff_fwhm` is in Extras (PeakExtrasGroup).
Column {
    id: group

    property ExperimentViewModel experiment: null

    spacing: AppSizes.groupContentSpacing

    EaElements.GroupRow {
        SelectorField {
            objectName: "peak.type"
            label: qsTr("profile")
            options: group.experiment ? group.experiment.peakTypeOptions : null
            token: group.experiment ? group.experiment.peakType : ""
            onSelected: token => group.experiment.peakType = token
        }
    }

    // One row per family, each five fields wide so the columns line up and a shorter row leaves its last
    // cells empty (edi ADR-0017 §5): the back-to-back exponentials (α, β), the Gaussian broadening (σ, U V W,
    // size, strain), the Lorentzian (γ, X Y, size, strain), then any other field.
    Repeater {
        model: group.experiment ? [group.experiment.peakBackToBack, group.experiment.peakGaussian, group.experiment.peakLorentzian, group.experiment.peakOther] : []
        delegate: ParameterGrid {
            required property ParameterListModel modelData

            visible: modelData.usedCount > 0
            fields: modelData
            prefix: "peak"
        }
    }

    ParameterGrid {
        visible: group.experiment !== null && group.experiment.peakAsymmetry.usedCount > 0
        fields: group.experiment ? group.experiment.peakAsymmetry : null
        prefix: "peak"
    }
}
