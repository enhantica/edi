// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals

import edi.app

// Which workflow pages are open and which one is shown — the original's page-unlocking flow
// (easydiffractionbeta Globals/Vars.qml): Home opens Project; each page's Continue opens the next.
QtObject {
    enum Page {
        Home,
        Project,
        Structure,
        Experiment,
        Analysis,
        Report
    }

    // The Continue area at the bottom of every page's sidebar, hidden for now (the owner, 2026-10-06), so the
    // sidebar's content runs down to its bottom. The one switch: true brings Continue back as it was.
    readonly property bool continueAreaShown: false

    // The platform's appearance, which the base's "System" theme follows: Qt's own colour scheme, live
    // (macOS switches it with System Settings → Appearance). Writable, as the test and demo seam: a
    // headless Linux runner reports Unknown, so they set Light or Dark here instead.
    property int platformColorScheme: Application.styleHints.colorScheme
    property Binding systemColorScheme: Binding {
        target: EaStyle.Colors
        property: "systemColorScheme"
        value: AppState.platformColorScheme
    }

    // The pattern charts' one view (edi ADR-0017 §15): the Structure, Experiment and Analysis pages each show a chart,
    // and every one follows these: the view's ranges (PatternChartController.viewRanges) and the toolbar's choices.
    property var patternViewRanges: []
    property bool patternLegendShown: false
    property bool patternHoverShown: true
    property string patternPointerMode: "zoom"
    // A project opened, reset or closed starts with its full view; the toolbar's choices stay.
    property Connections patternViewReset: Connections {
        target: Session
        function onProjectChanged() {
            AppState.patternViewRanges = [];
        }
    }

    // The furthest page the user has opened with Start or Continue; an open project opens every page
    // (easydiffractionbeta: loading a project enables the workflow pages together).
    property int reached: AppState.Page.Home

    readonly property bool projectPageEnabled: reached >= AppState.Page.Project || Session.hasProject
    readonly property bool structurePageEnabled: reached >= AppState.Page.Structure || Session.hasProject
    // A page is made once it is reached; its tab is enabled while the project allows it: Experiment, Analysis and
    // Summary (Report) need a structure, Analysis and Summary an experiment too, and removing the last one disables
    // them again (the owner, 2026-10-08). A page stays made while its tab is disabled, so it keeps its state.
    readonly property bool experimentPageReached: reached >= AppState.Page.Experiment || Session.hasProject
    readonly property bool analysisPageReached: reached >= AppState.Page.Analysis || Session.hasProject
    readonly property bool reportPageReached: reached >= AppState.Page.Report || Session.hasProject
    readonly property bool hasStructure: Session.project !== null && Session.project.structures.count > 0
    readonly property bool hasExperiment: Session.project !== null && Session.project.experiments.count > 0
    readonly property bool experimentPageEnabled: experimentPageReached && hasStructure
    readonly property bool analysisPageEnabled: analysisPageReached && hasStructure && hasExperiment
    readonly property bool reportPageEnabled: reportPageReached && hasStructure && hasExperiment

    // Save as, asked for from a page (Get started); the window's folder dialog answers (Main.qml; edi
    // ADR-0017 §13).
    signal saveAsRequested
    // The Analysis page's Evolution tab, asked for from the results window after a scan (edi ADR-0017 §19).
    signal evolutionRequested

    function open(page) {
        reached = Math.max(reached, page);
        EaGlobals.Vars.appBarCurrentIndex = page;
    }

    // The app bar's reset: close the project and open the Project page, where a new project starts (the owner,
    // 2026-10-11).
    function reset() {
        Session.closeProject();
        reached = AppState.Page.Project;
        EaGlobals.Vars.appBarCurrentIndex = AppState.Page.Project;
    }
}
