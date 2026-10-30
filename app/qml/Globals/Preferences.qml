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
    property bool assistantShown: false
    property bool assistantCopyTechnicalDetails: false
    property real assistantWidth: AppSizes.assistantDefaultWidth

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
    // The figure palette of experiments and structures (data/palettes, edi ADR-0038): a palette's token, "earth" (the
    // default) or another of ApplicationInfo.colourSchemes; a stored earlier palette reads as its nearest new one
    // (ApplicationInfo.colourSchemeOrDefault). Every chart, legend, icon and report the app draws follows it, a report
    // in its light colours. The Stacked and Map colours are scanStackedPalette and scanMapColours.
    property string colourScheme: "earth"
    // The patterns' palette stored before the one palette (the owner, 2026-10-22, until 2026-10-26): read once into
    // colourScheme, then cleared, so a choice made there carries over.
    property string patternColourScheme: ""
    // Whether a new project's HTML reports load their chart libraries ("online", the default) or embed them
    // ("embedded"): its `_report.html_offline` (edi ADR-0036 §7). A project keeps its own; this only starts a new one.
    property string newReportLibraries: "online"

    // ADR-0031 §5: every preference back to its default, as Preferences' Reset does; the open project is untouched.
    function resetToDefaults() {
        ApplicationInfo.resetPreferences();
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
        // After colourScheme: the settings load in this order, so the earlier patterns' choice wins once.
        property alias patternColourScheme: preferences.patternColourScheme
    }

    property Settings assistantSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Assistant"
        property alias width: preferences.assistantWidth
        property alias copyTechnicalDetails: preferences.assistantCopyTechnicalDetails
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
    // A scan's Stacked and Map views (edi ADR-0041): the palette or colour map the stacked patterns take their colours
    // from (one of ApplicationInfo.colourSchemes or ApplicationInfo.scanColourMaps; empty follows colourScheme) and the
    // map's colour map (one of ApplicationInfo.scanColourMaps; Blue-Red by default, the owner, 2026-10-26). The Map's
    // direction is the project's (ScanViewModel.mapDirection).
    property string scanStackedPalette: ""
    property string scanMapColours: "blue-red"
    // The Map's colour between datasets' rows: smooth, or stepped in bands (the owner, 2026-10-22).
    property bool scanMapSmooth: true
    // The Stacked colours reversed, last dataset first (the owner, 2026-10-22).
    property bool scanStackedReversed: false
    // The Stacked legend shown (its toolbar button; off by default, the owner, 2026-10-26).
    property bool scanStackedLegendShown: false
    // Every pattern chart shows only the included range (the toolbar's eraser button; edi ADR-0044).
    property bool chartIncludedOnly: false
    // Pattern, Stacked and the Map draw every curve with its background subtracted; off by default (the owner,
    // 2026-10-26).
    property bool chartSubtractBackground: false
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

    // What every page's Text tab shows (the owner, 2026-10-27): "editable", the categories the user sets, or
    // "everything", the measured data and the program's output too, read-only. One setting for every Text tab.
    property string textShow: "editable"

    property Settings textSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "TextTab"
        property alias show: preferences.textShow
    }

    property Settings chartSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Charts"
        property alias includedOnly: preferences.chartIncludedOnly
        property alias subtractBackground: preferences.chartSubtractBackground
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
        property alias stackedReversed: preferences.scanStackedReversed
        property alias stackedLegend: preferences.scanStackedLegendShown
        property alias renderer: preferences.scanRenderer
    }

    property Binding fitPatternUpdates: Binding {
        target: Session.project ? Session.project.fit : null
        property: "patternUpdates"
        value: preferences.scanPatternUpdates
        when: Session.project !== null
    }
    // The open project's blocks take their positions in the palette, and the report's charts its colours, bound here
    // with the open project, not on the Report page, which loads only once reached.
    property Binding projectColours: Binding {
        target: Session.project
        property: "colourScheme"
        value: preferences.colourScheme
        when: Session.project !== null
    }
    property Binding reportColours: Binding {
        target: Session.project ? Session.project.report : null
        property: "colourScheme"
        value: preferences.colourScheme
        when: Session.project !== null
    }

    onToolTipsChanged: EaGlobals.Vars.showToolTips = toolTips
    // A stored palette no longer offered becomes the one it reads as, so the chosen palette and the one drawn agree
    // and the settings file keeps the one shown.
    onColourSchemeChanged: ApplicationInfo.preferencesColourChanged()
    // A stored Stacked choice no longer offered (an earlier palette's token) follows the palette again, so the Stacked
    // lines and the choice Preferences shows agree (the owner's report, 2026-10-27).
    onScanStackedPaletteChanged: ApplicationInfo.preferencesStackedPaletteChanged()
    onPatternColourSchemeChanged: ApplicationInfo.preferencesLegacyPaletteChanged()
    onAutoCollapseChanged: EaGlobals.Vars.autoCollapseSideBarGroups = autoCollapse
    onEngineThreadsChanged: ApplicationInfo.persistPreference(0)
    // Saved at once too: a restart or a new window soon after the toggle must find it, and no write is left pending
    // for the settings' own schedule when the window closes.
    onChartIncludedOnlyChanged: ApplicationInfo.persistPreference(1)

    // Saved at once too: the renderer choice is read by the next start, which may follow at once.
    onScanRendererChanged: ApplicationInfo.persistPreference(2)

    // Saved at once too: no write of an earlier choice is left pending to land over what is read next.
    onScanPatternUpdatesChanged: ApplicationInfo.persistPreference(3)

    function apply() {
        ApplicationInfo.applyPreferences();
    }
}
