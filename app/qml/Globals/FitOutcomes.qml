// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

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
        switch (key) {
        case "success":
            return "check-circle";
        case "maxIterations":
        case "noStep":
        case "notConverged":
            return "exclamation-circle";
        case "stopped":
            return "stop-circle";
        case "superseded":
        case "skipped":
            return "minus-circle";
        case "failed":
        case "refused":
            return "times-circle";
        }
        return "";
    }

    // Whether the outcome is drawn as the hollow "Not fitted" circle.
    function ring(key) {
        return key === "";
    }

    function word(key) {
        switch (key) {
        case "":
            return qsTr("Not fitted");
        case "success":
            return qsTr("Success");
        case "maxIterations":
            return qsTr("Max iterations");
        case "noStep":
            return qsTr("No step");
        case "notConverged":
            return qsTr("Not converged");
        case "stopped":
            return qsTr("Stopped");
        case "superseded":
            return qsTr("Superseded");
        case "skipped":
            return qsTr("Skipped");
        case "refused":
            return qsTr("Refused");
        case "failed":
            return qsTr("Failed");
        }
        return "";
    }

    // What the outcome means, for a tooltip.
    function meaning(key) {
        switch (key) {
        case "":
            return qsTr("Not fitted yet");
        case "success":
            return qsTr("The fit converged");
        case "maxIterations":
            return qsTr("The iteration limit was reached; the result is kept");
        case "noStep":
            return qsTr("No further improving step was found; the result is kept");
        case "notConverged":
            return qsTr("The fit did not converge; why was not recorded with the result, which is kept");
        case "stopped":
            return qsTr("Stop fitting was pressed; the result is kept");
        case "superseded":
            return qsTr("An input changed during the fit; nothing was written");
        case "skipped":
            return qsTr("The file has no intensity above zero, so it was not fitted");
        case "refused":
            return qsTr("The fit refused this file (analysis/scan-notes.csv says why); the scan went on");
        case "failed":
            return qsTr("The fit was refused or failed; nothing was written");
        }
        return "";
    }

    function color(key) {
        switch (key) {
        case "success":
            return EaStyle.Colors.green;
        case "maxIterations":
        case "noStep":
        case "notConverged":
            return EaStyle.Colors.orange;
        case "failed":
        case "refused":
            return EaStyle.Colors.red;
        }
        return EaStyle.Colors.themeForegroundMinor;
    }
}
