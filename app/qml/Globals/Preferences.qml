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
    // How a followed scan redraws the pattern (Analysis, Settings; edi ADR-0029): FitViewModel.patternUpdates, 2 is
    // adaptive. The open project's fit takes it, whichever project is open.
    property int scanPatternUpdates: 2
    // Which rows the Analysis table adds on top of what a fit can free (Analysis, Settings; the owner, 2026-10-26): the
    // values this fit cannot determine by default, the setup values and those symmetry or a constraint sets on request
    // (the owner, 2026-10-27).
    property bool analysisShowNotMeasured: true
    property bool analysisShowBySymmetry: false
    property bool analysisShowByConstraint: false
    property bool analysisShowFixedSettings: false
    // Whether a finished fit opens its results window (Prompts; the owner, 2026-10-26). Off, the status bar's fit status
    // still opens it.
    property bool showFitResults: true
    // How the Stacked view draws its lines (Develop; edi ADR-0041): "auto" (the default) on the GPU when Qt draws with
    // one and painted without (RenderingInfo), "gpu" or "software" whatever was detected.
    property string scanRenderer: "auto"
    // How a new project writes values with a standard uncertainty: "iucr_19" or "iucr_99". A project keeps its
    // own; this only starts a new one.
    property string newProjectSuRule: "iucr_99"
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
        preferences.analysisShowNotMeasured = true;
        preferences.analysisShowBySymmetry = false;
        preferences.analysisShowByConstraint = false;
        preferences.analysisShowFixedSettings = false;
        preferences.showFitResults = true;
        preferences.scanRenderer = "auto";
        preferences.newProjectSuRule = "iucr_99";
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
        preferences.scanStackedOffset = 10;
        preferences.scanStackedSize = 0;
        preferences.scanStackedReversed = false;
        preferences.chartIncludedOnly = false;
        preferences.singleCrystalQuantity = "f_squared";
        preferences.chartHighlightSelected = true;
        preferences.chartHiddenRange = "keep";
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
    // The Stacked patterns' placing (edi ADR-0041 §4; the owner, 2026-10-24): each baseline's offset above the one
    // below it, in percent of a pattern's own height (0 to 100 by 10), and each pattern's height, in percent of the
    // plot's (10 to 100 by 10), 0 for Fit, which fills the plot with the whole stack.
    property int scanStackedOffset: 10
    property int scanStackedSize: 0
    // The Stacked colours reversed, last dataset first (the owner, 2026-10-22).
    property bool scanStackedReversed: false
    // Every pattern chart shows only the included range (the toolbar's eraser button; edi ADR-0044).
    property bool chartIncludedOnly: false
    // A single crystal's chart plots F² (calc against meas) or F ("f_squared" or "f").
    property string singleCrystalQuantity: "f_squared"
    // Every chart of several datasets (Stacked, single-crystal Stacked and the Map) draws the selected one on top and
    // fades the others to chartFadedOpacity; off, all are drawn alike and only the selection's label marks it (the
    // owner, 2026-10-24).
    property bool chartHighlightSelected: true
    readonly property real chartFadedOpacity: 0.3
    // A curve hidden by a click on a pattern chart's legend (the owner, 2026-10-25): "keep" the y range as it is, every
    // fit counting the hidden curve, or "fit" it once to the curves still shown, later fits counting only those.
    property string chartHiddenRange: "keep"

    property Settings chartSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Charts"
        property alias includedOnly: preferences.chartIncludedOnly
        property alias singleCrystalQuantity: preferences.singleCrystalQuantity
        property alias highlightSelected: preferences.chartHighlightSelected
        property alias hiddenRange: preferences.chartHiddenRange
    }

    property Settings analysisSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Analysis"
        property alias scanPatternUpdates: preferences.scanPatternUpdates
        property alias showNotMeasured: preferences.analysisShowNotMeasured
        property alias showBySymmetry: preferences.analysisShowBySymmetry
        property alias showByConstraint: preferences.analysisShowByConstraint
        property alias showFixedSettings: preferences.analysisShowFixedSettings
        property alias showFitResults: preferences.showFitResults
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
        property alias stackedOffset: preferences.scanStackedOffset
        property alias stackedSize: preferences.scanStackedSize
        property alias stackedReversed: preferences.scanStackedReversed
        property alias renderer: preferences.scanRenderer
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

    // Saved at once too: the renderer choice is read by the next start, which may follow at once.
    onScanRendererChanged: {
        scanViewSettings.setValue("renderer", scanRenderer);
        scanViewSettings.sync();
        ApplicationInfo.storeSettings();
    }

    // Saved at once too: no write of an earlier choice is left pending to land over what is read next.
    onScanPatternUpdatesChanged: {
        analysisSettings.setValue("scanPatternUpdates", scanPatternUpdates);
        analysisSettings.sync();
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
