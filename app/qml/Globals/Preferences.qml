// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick
import QtCore

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals

import edi.app

// edi's application preferences (edi ADR-0017 §12), shown by edi's own dialog (AppPreferencesDialog) in
// place of the base's: the base's dialog offers no way to hide or add a row, and edi changes several. The
// values persist in the app's settings file (the base's Settings mechanism, `EaGlobals.Vars.settingsFile`;
// a demo or test run has its own fresh file) under edi's own category, and `apply` hands them to the base
// once the window is complete — after the base's hidden dialog has loaded its own, older keys, so edi's win.
// What is not available yet is forced off whatever a settings file says: no update check at start, the
// default zoom, English.
QtObject {
    id: preferences

    property bool dialogShown: false

    property bool toolTips: true
    property bool autoCollapse: true
    // Where the workflow pages show their sidebar: "Right" (the default) or "Left" (WorkflowPage).
    property string sideBarSide: "Right"
    readonly property bool sideBarOnLeft: sideBarSide === "Left"
    // The engine's thread count for every fill (Develop): 0 is Auto, the engine's own policy.
    property int engineThreads: 0
    // How a followed scan redraws the pattern (Analysis, Extras; edi ADR-0029): FitViewModel.patternUpdates, 2 is
    // adaptive. The open project's fit takes it, whichever project is open.
    property int scanPatternUpdates: 2
    // How a new project writes values with a standard uncertainty: "iucr_19" or "iucr_99". A project keeps its
    // own; this only starts a new one.
    property string newProjectSuRule: "iucr_19"
    // The experiments' and structures' colours (data/palettes): a scheme's token, "coast" (the default) or another of
    // AppPreferencesDialog's list; an unknown one reads as the default. Every chart, icon and report the app draws
    // follows it, a report in the scheme's light colours.
    property string colourScheme: "coast"
    // Whether a new project's HTML reports load their chart libraries ("online", the default) or embed them
    // ("embedded"): its `_report.html_offline` (edi ADR-0036 §7). A project keeps its own; this only starts a new one.
    property string newReportLibraries: "online"

    // ADR-0031 §5: every preference back to its default, as Preferences' Reset does; the open project is untouched.
    function resetToDefaults() {
        preferences.toolTips = true;
        preferences.autoCollapse = true;
        preferences.sideBarSide = "Right";
        preferences.engineThreads = 0;
        preferences.scanPatternUpdates = 2;
        preferences.newProjectSuRule = "iucr_19";
        preferences.newReportLibraries = "online";
        preferences.colourScheme = "coast";
        preferences.analysisYScale = "linear";
        preferences.experimentYScale = "linear";
        preferences.experimentXAxis = "native";
        preferences.chartIncludedOnly = false;
        preferences.singleCrystalQuantity = "f_squared";
        preferences.chartHoverShown = true;
        preferences.chartPointerMode = "zoom";
    }

    property Settings settings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Edi.Preferences"
        property alias toolTips: preferences.toolTips
        property alias autoCollapse: preferences.autoCollapse
        property alias sideBarSide: preferences.sideBarSide
    }

    // ADR-0031: the Appearance tab's colour scheme, and the Projects tab's defaults for new projects.
    property Settings appearanceSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Appearance"
        property alias colourScheme: preferences.colourScheme
    }

    property Settings projectsSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Projects"
        property alias newProjectSuRule: preferences.newProjectSuRule
        property alias newReportLibraries: preferences.newReportLibraries
    }

    property Settings developSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "develop"
        property alias engineThreads: preferences.engineThreads
    }

    // ADR-0031 §2: the pages' settings, each kept under its page's name: the pattern charts' y scale ("linear",
    // "sqrt" or "log") and the Experiment chart's x axis ("native" or "d_spacing"; the Analysis chart's is the
    // project's), both chosen on the chart, and how a followed scan redraws.
    property string analysisYScale: "linear"
    property string experimentYScale: "linear"
    property string experimentXAxis: "native"
    // Every pattern chart shows only the included range (the toolbar's eraser button; edi ADR-0044).
    property bool chartIncludedOnly: false
    // A single crystal's chart plots F² (calc against meas) or F ("f_squared" or "f").
    property string singleCrystalQuantity: "f_squared"
    // Every chart's hover read-out (the toolbar's tooltip button).
    property bool chartHoverShown: true
    // Every chart's left drag: "zoom" (a box) or "pan" (the toolbar's zoom and move buttons).
    property string chartPointerMode: "zoom"

    property Settings chartSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Charts"
        property alias includedOnly: preferences.chartIncludedOnly
        property alias singleCrystalQuantity: preferences.singleCrystalQuantity
        property alias hoverShown: preferences.chartHoverShown
        property alias pointerMode: preferences.chartPointerMode
    }

    property Settings analysisSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Analysis"
        property alias scanPatternUpdates: preferences.scanPatternUpdates
        property alias yScale: preferences.analysisYScale
    }

    property Settings experimentSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Experiment"
        property alias yScale: preferences.experimentYScale
        property alias xAxis: preferences.experimentXAxis
    }

    property Binding fitPatternUpdates: Binding {
        target: Session.project ? Session.project.fit : null
        property: "patternUpdates"
        value: preferences.scanPatternUpdates
        when: Session.project !== null
    }

    onToolTipsChanged: EaGlobals.Vars.showToolTips = toolTips
    onAutoCollapseChanged: EaGlobals.Vars.autoCollapseSideBarGroups = autoCollapse
    onEngineThreadsChanged: {
        ApplicationInfo.setEngineThreads(engineThreads);
        // Saved at once rather than on the Settings' own schedule: a browser reload or a restart soon after the
        // change must find it.
        developSettings.setValue("engineThreads", engineThreads);
        developSettings.sync();
        ApplicationInfo.storeSettings();
    }
    // Saved at once too: a restart or a new window soon after the toggle must find it, and no write is left pending
    // for the settings' own schedule when the window closes.
    onChartIncludedOnlyChanged: {
        chartSettings.setValue("includedOnly", chartIncludedOnly);
        chartSettings.sync();
        ApplicationInfo.storeSettings();
    }

    function apply() {
        EaGlobals.Vars.showToolTips = preferences.toolTips;
        EaGlobals.Vars.autoCollapseSideBarGroups = preferences.autoCollapse;
        ApplicationInfo.setEngineThreads(preferences.engineThreads);
        EaGlobals.Vars.checkUpdateOnAppStart = false;
        EaStyle.Sizes.defaultScale = 100;
    }
}
