// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import EasyApplication.Gui.Style as EaStyle

import edi.app

// A parameter's iconified name on the Analysis page, as easydiffractionbeta's shortest name with icons and
// pretty labels (Globals/Proxies.qml paramName; ADR-0017 §8), as the pieces of one
// IconLine (§10): the block's icon in the block's colour; the category's icon, for an atom site in its element's
// colour; the row (an atom's label, a loop row's number) in the category icon's colour; the parameter's icon;
// then its short name in bold.
QtObject {
    id: names

    // A block kind's icon, as the block tables show it.
    function blockIcon(kind) {
        return kind === "structure" ? "layer-group" : kind === "experiment" ? "microscope" : "";
    }

    // easydiffractionbeta's parameter icons (Logic/Calculators.py), by `.edi` item name or its prefix; none
    // for a parameter the original had no icon for.
    function parameterIcon(name) {
        const icons = [["length_", "ruler"], ["angle_", "ruler"], ["fract_", "map-marker-alt"], ["occupancy", "fill"], ["adp_", "arrows-alt"], ["scale", "weight"], ["setup_wavelength", "radiation"], ["setup_twotheta_bank", "hashtag"], ["calib_d_to_tof_offset", "arrows-alt-h"], ["calib_d_to_tof_", "radiation"], ["calib_", "arrows-alt-h"], ["broad_", "shapes"], ["rise_", "shapes"], ["decay_", "shapes"], ["asym_", "balance-scale-left"], ["intensity", "mountain"]];
        for (let i = 0; i < icons.length; ++i) {
            if (name.startsWith(icons[i][0]))
                return icons[i][1];
        }
        return "";
    }

    // A ParameterItem's name as IconLine pieces (§10).
    function segments(item) {
        if (!item)
            return [];
        const minor = EaStyle.Colors.themeForegroundMinor;
        const categoryColor = item.elementSymbol !== "" ? AppColors.element(item.elementSymbol) : item.phaseIndex >= 0 ? AppColors.structure(item.phaseIndex) : minor;
        const pieces = [
            {
                "icon": names.blockIcon(item.blockKind),
                "color": AppColors.block(item.blockKind, item.blockIndex)
            }
        ];
        if (item.categoryIcon !== "")
            pieces.push({
                "icon": item.categoryIcon,
                "color": categoryColor
            });
        if (item.rowLabel !== "")
            pieces.push({
                "text": /^[0-9]+$/.test(item.rowLabel) ? String(Number(item.rowLabel) + 1) : item.rowLabel,
                "color": categoryColor
            });
        const parameterIcon = names.parameterIcon(item.name);
        if (parameterIcon !== "")
            pieces.push({
                "icon": parameterIcon,
                "color": minor
            });
        pieces.push({
            "text": item.shortName,
            "bold": true
        });
        return pieces;
    }
}
