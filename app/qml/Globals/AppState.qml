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
    // The Meas vs calc view's axes scale (0 linear, 1 square root, 2 log) and zoom, and each single-crystal view's zoom
    // ({comparison, stacked, axis}), one per view and shared by the pages that show it: a change on one page's copy
    // shows on every other's.
    property int measCalcScale: 0
    property list<real> measCalcZoom: []
    property var singleCrystalZoom: ({})
    // A project opened, reset or closed starts with its full view (no range set, as a chart writes it, the comparison
    // and single-crystal zooms included); the toolbar's choices stay.
    property Connections patternViewReset: Connections {
        target: Session
        function onProjectChanged() {
            ApplicationInfo.resetPatternProjectView();
            AppState.measCalcZoom = [];
            AppState.singleCrystalZoom = {};
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
    // Save as with the format already chosen from Get started's Save menu: the EasyDiffraction folder or a .zip, and
    // whether to write a copy and keep working where the project is.
    signal saveAsFormatRequested(bool zip, bool copy)
    // Open project (a folder, or a .zip with `zip`) and Import, asked for from Get started's Load menu. The window
    // answers them: dealing with unsaved changes can close the project and rebuild that page, so the page cannot.
    signal openProjectRequested(bool zip)
    signal importProjectRequested(var importer)
    // That Save as ended: saved at the place chosen, or cancelled or refused.
    signal saveAsFinished(bool saved)
    // Run `action` (opening, creating or closing a project, quitting) once the open project's unsaved changes are
    // dealt with: at once when there are none, else after the window asks to save or discard them.
    signal changesQuestion(var action, var abandoned)
    // The assistant's `action` closes the open project, saved or not: the user answers first. `closing` says why: "create"
    // (its new project) or "conversation" (a chosen conversation's own project).
    signal closeQuestion(var action, var abandoned, string closing)
    // The same question about the user's own project while a tutorial holds it aside (edi ADR-0064).
    signal setAsideChangesQuestion(var action)
    // An action that replaces the project runs on the next turn of the event loop, never inside the handler that asked
    // for it: replacing the project rebuilds the pages, and the page holding that handler with them.
    // `creating`: the action is Create a new project, which in a tutorial without a project of its own yet makes the
    // tutorial's project; it never touches the user's project held aside, so it asks nothing about it.
    // Opening, closing and quitting still do.
    // `closing`: the assistant's action, which asks even when nothing is unsaved (closeQuestion).
    function afterChanges(action, abandoned, creating, closing) {
        ApplicationInfo.afterProjectChanges(action, abandoned, creating === true, closing ?? "");
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
    // The window's one main view of the Structure, Experiment and Analysis pages (MainView), set by the window.
    property var mainView: null
    // Help and feedback, asked for from Home, About or the crash popup: the window's form opens on `kind` ("feedback",
    // "question", "problem" or "idea"), with `log` attached instead of this run's when it is not empty (Main.qml).
    signal feedbackRequested(string kind, string log)
    // An error popup's Send to developers (edi ADR-0062): the form opens as a problem with `message`, this run's log and
    // `file`, the file edi could not read, attached when not empty.
    signal problemReported(string message, string file)
    // The post-crash popup's Send to developers: the form opens as a problem with the crashed run's `log` and `text`
    // (what went wrong, RunLog.crashedDiagnostic) filled in.
    signal crashReported(string log, string text)
    // Home's "Enjoying EasyDiffraction?": the likes bar now, whatever its timing rule (owner, 2026-11-17).
    signal likesRequested
    // Home's Update available link: the update dialog the status bar opens on the other pages.
    signal updateDialogRequested
    // What's new, asked for from Home (Main.qml).
    signal whatsNewRequested
    // A built-in tutorial to run (its manifest entry), asked for from Home's Tutorials; the window's panel runs it.
    signal tutorialRequested(var tutorial)
    // A tutorial is running (TutorialPanel); while it is, no other starts.
    // A fit's results window: open now, and how often it has opened (a tutorial waits for it to open and close).
    property bool fitResultsOpen: false
    property int fitResultsShown: 0
    // The results window closed as its OK closes it, asked for by a tutorial step's Next.
    signal fitResultsCloseRequested
    // An entry of an online collection loaded into the project: its kind and its id (the tutorial checks which).
    signal onlineEntryLoaded(string kind, string id)
    property bool tutorialRunning: false
    // A replacement or a quit brought the user's set-aside project back, which ends the running tutorial.
    signal tutorialEnded

    function open(page) {
        ApplicationInfo.openWorkflowPage(page);
    }

    // The untitled project's first Save (the owner, 2026-11-19): the Project page opens and its Create project dialog
    // names the project and saves it. `id`: the untitled operation that asked (a guard Save), which the dialog answers;
    // without one the dialog opens its own.
    signal untitledSaveRequested(real id)
    function requestUntitledSave(id = 0) {
        open(AppState.Page.Project);
        untitledSaveRequested(id > 0 ? id : 0);
    }

    // Clear returns to Home without a project; opening Project starts untitled work (edi ADR-0017 §13).
    function reset() {
        ApplicationInfo.resetWorkflow();
    }

    // Closes a popup of the project being replaced before the next project shows (edi ADR-0052). `close` is what
    // closes it, when more than its close() is needed. Both run with no exit transition, so Qt hides the popup within
    // this call; every other close still animates.
    function retirePopup(popup, close = null) {
        const exit = popup.exit;
        popup.exit = null;
        if (close !== null)
            close();
        popup.close();
        popup.exit = exit;
        // An exit that started earlier (an Escape just before) is still running, and Qt starts no second one: it is
        // ended here too, and the overlay forgets the focus target the popup left (PopupRetirement).
        PopupRetirement.retire(popup);
    }
}
