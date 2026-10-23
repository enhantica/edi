// SPDX-License-Identifier: BSD-3-Clause
import QtQuick

import edi.app

// `extinction`: a single crystal's Becker-Coppens extinction, the crystal's radius and its mosaicity.
Column {
    id: group

    property ExperimentViewModel experiment: null
    // The mosaicity is Becker-Coppens' g, an inverse width with no angle unit (edi ADR-0049); its hint gives the mosaic
    // spread it means. CrysPy reads g as the value times π/10800 beside the radius in μm and λ in Å, so g per radian is
    // that times 10⁴; a Gaussian spread's FWHM is √(2 ln 2/π)/g, a Lorentzian's 1/(πg).
    readonly property ParameterItem mosaicity: grid.fields && grid.fields.count >= 0 ? grid.fields.parameterNamed("mosaicity") : null

    function spreadHint(value, lorentzian) {
        if (!(value > 0))
            return qsTr("Mosaicity g, an inverse width of the mosaic spread; 0 turns the secondary extinction off");
        const g = value * Math.PI / 10800 * 1e4;
        const fwhm = (lorentzian ? 1 / (Math.PI * g) : Math.sqrt(2 * Math.LN2 / Math.PI) / g) * 180 / Math.PI * 3600;
        const text = Number(fwhm.toPrecision(2)).toString();
        return lorentzian ? qsTr("Mosaicity g, an inverse width: a Lorentzian mosaic spread of FWHM %1″").arg(text) : qsTr("Mosaicity g, an inverse width: a Gaussian mosaic spread of FWHM %1″").arg(text);
    }

    spacing: AppSizes.groupContentSpacing

    ParameterGrid {
        id: grid

        fields: group.experiment ? group.experiment.extinction : null
        prefix: "extinction"
        fillRows: true
        hints: group.mosaicity !== null ? {
            "mosaicity": group.spreadHint(group.mosaicity.value, group.experiment.lorentzianExtinction)
        } : ({})
    }
}
