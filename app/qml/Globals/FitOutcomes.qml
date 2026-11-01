// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import edi.app

import EasyApplication.Gui.Style as EaStyle

// How a fit ended, drawn one way everywhere (edi ADR-0017 §17): the status bar's summary, the results window's
// Overall status row and the Fit column of the experiment lists all take the icon, word and colour of an
// outcome key (FitViewModel.outcome, recorded_outcome) from here. A scan's outcome is its worst file's. An
// experiment the last fit did not take part in (an empty key) is "Not fitted": a hollow circle in the minor colour,
// drawn rather than taken from the icon font, whose solid face has no hollow circle (`ring`).
QtObject {
    // The separator between the fit area's items, inside and beside the progress bar.
    readonly property string separator: " · "

    function icon(key) {
        return ApplicationInfo.fitOutcomePresentation(ApplicationInfo.FitIcon, key, undefined);
    }

    // Whether the outcome is drawn as the hollow "Not fitted" circle.
    function ring(key) {
        return ApplicationInfo.fitOutcomePresentation(ApplicationInfo.FitRing, key, undefined);
    }

    function word(key) {
        return ApplicationInfo.fitOutcomePresentation(ApplicationInfo.FitWord, key, undefined);
    }

    // What the outcome means, for a tooltip.
    function meaning(key) {
        return ApplicationInfo.fitOutcomePresentation(ApplicationInfo.FitMeaning, key, undefined);
    }

    // An outcome's colour for its icon. Stopped, Superseded and Skipped have none of their own: their icon takes
    // `neutral`, the grey of the icons around it (the minor colour unless given), and their word the text colour
    // (`textColor`), so they never look disabled (the owner, 2026-10-26).
    function color(key, neutral) {
        return ApplicationInfo.fitOutcomePresentation(ApplicationInfo.FitColor, key, neutral);
    }

    // An outcome's colour for its word: its own colour, or the text colour for one that has none.
    function textColor(key) {
        return ApplicationInfo.fitOutcomePresentation(ApplicationInfo.FitTextColor, key, undefined);
    }
}
