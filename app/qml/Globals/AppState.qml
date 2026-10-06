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

    // The furthest page the user has opened with Start or Continue; an open project opens every page
    // (easydiffractionbeta: loading a project enables the workflow pages together).
    property int reached: AppState.Page.Home

    readonly property bool projectPageEnabled: reached >= AppState.Page.Project || Session.hasProject
    readonly property bool structurePageEnabled: reached >= AppState.Page.Structure || Session.hasProject
    readonly property bool experimentPageEnabled: reached >= AppState.Page.Experiment || Session.hasProject
    readonly property bool analysisPageEnabled: reached >= AppState.Page.Analysis || Session.hasProject
    readonly property bool reportPageEnabled: reached >= AppState.Page.Report || Session.hasProject

    // Save as, asked for from a page (Get started); the window's folder dialog answers (Main.qml; edi
    // ADR-0017 §13).
    signal saveAsRequested

    function open(page) {
        reached = Math.max(reached, page);
        EaGlobals.Vars.appBarCurrentIndex = page;
    }

    // The app bar's reset: close the project and return Home with only Home open.
    function reset() {
        Session.closeProject();
        reached = AppState.Page.Home;
        EaGlobals.Vars.appBarCurrentIndex = AppState.Page.Home;
    }
}
