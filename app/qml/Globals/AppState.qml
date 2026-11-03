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
    // and every one follows these ranges (PatternChartController.viewRanges) and the toolbar's choices, which are app
    // settings (Preferences.patternLegendShown, patternHoverShown, patternPointerMode, structureCurves).
    // [x min, x max, y min, y max], NaN for the data's own range, and the x axis they are on.
    property list<real> patternViewRanges: [NaN, NaN, NaN, NaN]
    property string patternViewAxis: ""
    // The Stacked and Map views' zoom, one per view and shared by the pages that show them (edi ADR-0041):
    // {stacked: {x, y}, map: {x, y}}, each [min, max] or empty for the whole range.
    property var scanZoom: ({})
    // A project opened, reset or closed starts with its full view (no range set, as a chart writes it); the toolbar's
    // choices stay.
    property Connections patternViewReset: Connections {
        target: Session
        function onProjectChanged() {
            ApplicationInfo.resetPatternProjectView();
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
    // That Save as ended: saved at the place chosen, or cancelled or refused.
    signal saveAsFinished(bool saved)
    // Run `action` (opening, creating or closing a project, quitting) once the open project's unsaved changes are
    // dealt with: at once when there are none, else after the window asks to save or discard them.
    signal changesQuestion(var action, var abandoned)
    // The same question about the user's own project while a tutorial holds it aside (edi ADR-0064).
    signal setAsideChangesQuestion(var action)
    // An action that replaces the project runs on the next turn of the event loop, never inside the handler that asked
    // for it: replacing the project rebuilds the pages, and the page holding that handler with them.
    // `creating`: the action is Create a new project, which in a tutorial without a project of its own yet makes the
    // tutorial's project; it never touches the user's project held aside, so it asks nothing about it.
    // Opening, closing and quitting still do.
    function afterChanges(action, abandoned, creating) {
        ApplicationInfo.afterProjectChanges(action, abandoned, creating === true);
    }
    // The Text tab holding an edit not yet applied, or null. What would replace what it shows (another project,
    // closing the window, another Show choice) settles the edit first, as leaving the tab does (TextTab.settleEdit).
    property var textEdit: null
    // Every Text tab shows `choice` ("editable" or "everything") once an unapplied edit is settled.
    function setTextShow(choice) {
        ApplicationInfo.setTextShow(choice);
    }
    // A created project that could not be saved at its location stays open, unsaved: the window says why.
    signal createFailed
    // The Analysis page's Evolution tab, asked for from the results window after a scan (edi ADR-0017 §19).
    signal evolutionRequested
    // Help and feedback, asked for from Home, About or the crash popup: the window's form opens on `kind` ("feedback",
    // "question", "problem" or "idea"), with `log` attached instead of this run's when it is not empty (Main.qml).
    signal feedbackRequested(string kind, string log)
    // What's new, asked for from Home (Main.qml).
    signal whatsNewRequested
    // A built-in tutorial to run (its manifest entry), asked for from Home's Tutorials; the window's panel runs it.
    signal tutorialRequested(var tutorial)
    // A tutorial is running (TutorialPanel); while it is, no other starts.
    // A fit's results window: open now, and how often it has opened (a tutorial waits for it to open and close).
    property bool fitResultsOpen: false
    property int fitResultsShown: 0
    property bool tutorialRunning: false
    // A replacement or a quit brought the user's set-aside project back, which ends the running tutorial.
    signal tutorialEnded

    function open(page) {
        ApplicationInfo.openWorkflowPage(page);
    }

    // The app bar's reset: close the project and open the Project page, where a new project starts (the owner,
    // 2026-10-11).
    function reset() {
        ApplicationInfo.resetWorkflow();
    }
}
