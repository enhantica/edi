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

    property Settings settings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "Edi.Preferences"
        property alias toolTips: preferences.toolTips
        property alias autoCollapse: preferences.autoCollapse
        property alias sideBarSide: preferences.sideBarSide
    }

    property Settings developSettings: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "develop"
        property alias engineThreads: preferences.engineThreads
    }

    onToolTipsChanged: EaGlobals.Vars.showToolTips = toolTips
    onAutoCollapseChanged: EaGlobals.Vars.autoCollapseSideBarGroups = autoCollapse
    onEngineThreadsChanged: ApplicationInfo.setEngineThreads(engineThreads)

    function apply() {
        EaGlobals.Vars.showToolTips = preferences.toolTips;
        EaGlobals.Vars.autoCollapseSideBarGroups = preferences.autoCollapse;
        ApplicationInfo.setEngineThreads(preferences.engineThreads);
        EaGlobals.Vars.checkUpdateOnAppStart = false;
        EaStyle.Sizes.defaultScale = 100;
    }
}
