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
    // The experiments' and structures' colours (data/palettes, edi ADR-0038): a scheme's token, "ediNatural" (the
    // default) or another of ApplicationInfo.colourSchemes; a stored token no longer offered reads as the default.
    // Every chart, icon and report the app draws follows it, a report in the scheme's light colours.
    property string colourScheme: "ediNatural"
    // The colours split by what they colour (the owner, 2026-10-22): the structures' and the patterns' schemes, each
    // empty until chosen and then following colourScheme, the one choice before the split, so a stored choice carries
    // over. The Stacked and Map colours are scanStackedPalette and scanMapColours.
    property string structureColourScheme: ""
    property string patternColourScheme: ""
    readonly property string structureColours: structureColourScheme !== "" ? structureColourScheme : colourScheme
    readonly property string patternColours: patternColourScheme !== "" ? patternColourScheme : colourScheme
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
        preferences.colourScheme = "ediNatural";
        preferences.structureColourScheme = "";
        preferences.patternColourScheme = "";
        preferences.patternYScale = "linear";
        preferences.structureCurves = true;
        preferences.patternLegendShown = false;
        preferences.patternHoverShown = true;
        preferences.patternMeasuredStyle = "band";
        preferences.patternPointerMode = "zoom";
        preferences.scanStackedPalette = "";
        preferences.scanMapColours = "ramp:ediNatural";
        preferences.scanMapSmooth = true;
        preferences.scanMapReversed = false;
        preferences.scanStackedHeight = 2;
        preferences.scanStackedReversed = false;
        preferences.chartIncludedOnly = false;
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
        property alias structureColourScheme: preferences.structureColourScheme
        property alias patternColourScheme: preferences.patternColourScheme
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

    // ADR-0031 §2: the one pattern chart's settings (every page shows the same chart): its y scale ("linear", "sqrt"
    // or "log"; the x axis is the project's), whether it draws each structure's curve over the background (the chart
    // toolbar's switch; on by default, the owner, 2026-10-21), the toolbar's legend and hover-coordinate switches and
    // its pointer mode ("zoom" or "pan"), and how a followed scan redraws.
    property string patternYScale: "linear"
    // The two pages' former names of the one y scale.
    property alias analysisYScale: preferences.patternYScale
    property alias experimentYScale: preferences.patternYScale
    property bool structureCurves: true
    property bool patternLegendShown: false
    property bool patternHoverShown: true
    // How the pattern charts draw the measured data: "band" (measured ± s.u., the default), "line", "points" or
    // "linePoints" (the owner, 2026-10-22).
    property string patternMeasuredStyle: "band"
    property string patternPointerMode: "zoom"
    // A scan's Stacked and Map views (edi ADR-0041): the palette the stacked patterns take their colours from (one of
    // ApplicationInfo.colourSchemes; empty follows colourScheme) and the map's colour map (one of
    // ApplicationInfo.scanColourMaps).
    property string scanStackedPalette: ""
    // The Map's default, for now, is Edi Natural's shades (the owner, 2026-10-22).
    property string scanMapColours: "ramp:ediNatural"
    // The Map's colour between datasets' rows: smooth, or stepped in bands (the owner, 2026-10-22).
    property bool scanMapSmooth: true
    // The Map's colours reversed, from the map's high end at the lowest intensity (the owner, 2026-10-22).
    property bool scanMapReversed: false
    // How high a Stacked pattern rises, in multiples of four rows, 1 to 5 (the owner, 2026-10-22).
    property int scanStackedHeight: 2
    // The Stacked colours reversed, last dataset first (the owner, 2026-10-22).
    property bool scanStackedReversed: false
    // Every pattern chart shows only the included range (the toolbar's eraser button; edi ADR-0044).
    property bool chartIncludedOnly: false

    property Settings chartSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Charts"
        property alias includedOnly: preferences.chartIncludedOnly
    }

    property Settings analysisSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Analysis"
        property alias scanPatternUpdates: preferences.scanPatternUpdates
    }

    property Settings patternChartSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "PatternChart"
        property alias yScale: preferences.patternYScale
        property alias structureCurves: preferences.structureCurves
        property alias legendShown: preferences.patternLegendShown
        property alias hoverShown: preferences.patternHoverShown
        property alias measuredStyle: preferences.patternMeasuredStyle
        property alias pointerMode: preferences.patternPointerMode
    }

    property Settings scanViewSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "ScanViews"
        property alias stackedPalette: preferences.scanStackedPalette
        property alias mapColours: preferences.scanMapColours
        property alias mapSmooth: preferences.scanMapSmooth
        property alias mapReversed: preferences.scanMapReversed
        property alias stackedHeight: preferences.scanStackedHeight
        property alias stackedReversed: preferences.scanStackedReversed
    }

    property Binding fitPatternUpdates: Binding {
        target: Session.project ? Session.project.fit : null
        property: "patternUpdates"
        value: preferences.scanPatternUpdates
        when: Session.project !== null
    }
    // The report's charts take the Patterns and Structures colours, bound here with the open project, not on the Report
    // page, which loads only once reached.
    property Binding reportPatternColours: Binding {
        target: Session.project ? Session.project.report : null
        property: "colourScheme"
        value: preferences.patternColours
        when: Session.project !== null
    }
    property Binding reportStructureColours: Binding {
        target: Session.project ? Session.project.report : null
        property: "structureColourScheme"
        value: preferences.structureColours
        when: Session.project !== null
    }

    onToolTipsChanged: EaGlobals.Vars.showToolTips = toolTips
    // A stored scheme no longer offered (one of the eighteen before the Edi palettes) becomes the default, so the
    // chosen scheme and the one drawn agree and the settings file keeps the one shown.
    onColourSchemeChanged: {
        const offered = ApplicationInfo.colourSchemeOrDefault(colourScheme);
        if (offered !== colourScheme) {
            colourScheme = offered;
        }
    }
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
