// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import EasyApplication.Gui.Style as EaStyle

// edi's own layout values, in one place: each is taken from easydiffractionbeta's QML and expressed in
// the base's font size, so the pages carry no bare numbers. Fonts come only from the base's EaStyle
// tokens, colours from those and AppColors.
QtObject {
    readonly property real unit: EaStyle.Sizes.fontPixelSize

    // The wordmark's mark (Components/Wordmark.qml; its name is 0.4309 of it): easydiffractionbeta's 5 units,
    // the same on Home and in About (WordmarkWithVersion, edi ADR-0017 §1).
    readonly property real homeMarkDiameter: unit * 5

    // Home page (easydiffractionbeta Pages/Home/Page.qml)
    readonly property real homeBlockSpacer: unit * 2.5
    readonly property real homeLinkColumnsSpacing: unit * 3
    readonly property real homeLinkSpacing: unit
    readonly property real homeBranchTopPadding: unit * 0.5

    // Workflow pages (easydiffractionbeta Pages/*)
    readonly property real fieldSpacing: unit * 0.5           // between fields of one GroupRow
    readonly property real groupContentSpacing: unit          // between rows inside a group
    readonly property real indexColumnWidth: unit * 2.5       // a table's row-number column
    readonly property real iconColumnWidth: EaStyle.Sizes.tableRowHeight        // a table's action-button column
    readonly property real dataIndexColumnWidth: unit * 3.5   // a data table's row number (up to 5 digits)
    readonly property real dataColumnWidth: unit * 6          // a data table's value column
    readonly property real fileColumnWidth: unit * 7          // an explorer table's file column
    readonly property real datasetFileColumnWidth: unit * 11  // a scan's data file name (01_101_101p9130.dat)
    readonly property real descriptionNameColumnWidth: unit * 10
    readonly property real descriptionInnerSpacing: unit * 0.85
    readonly property real descriptionOuterSpacing: unit * 1.5
    readonly property real descriptionTitleFontPixelSize: unit * 3
    readonly property real textViewPadding: unit
    // A Text tab's text view fills the tab down to the sidebar's bottom, under the Continue pill, which floats
    // over it (edi ADR-0017 §7), never below the minimum. Its last lines can scroll clear of the pill: the
    // pill, one unit above the sidebar's bottom (the text's own padding), and half a unit's gap above it.
    readonly property real textViewMinimumHeight: unit * 5
    readonly property real textViewContinueClearance: EaStyle.Sizes.sideBarButtonHeight + unit * 0.5
    readonly property real reportPadding: unit * 2.5
    // A chart toolbar's controls (ChartToolButton, ToolbarComboBox) are this tall, and this far apart within a
    // group; the block selector row and the structure legend take the same values (edi ADR-0017 §7, §15, §16).
    readonly property real toolbarControlSize: Math.round(unit * 2.5)
    // The main area's side margin (the owner, 2026-10-05): the pattern chart's room right of its plot areas, which
    // is also where the selector row and the chart toolbars start on the left, the structure view's toolbar
    // inset on the right, and the pattern chart's gap from its toolbar down to the main plot area.
    readonly property real mainAreaMargin: unit * 2
    readonly property real toolbarSpacing: unit * 0.25
    // The messages dialog's fixed width (edi ADR-0017 §14): about the Preferences dialog's.
    readonly property real messagesDialogContentWidth: unit * 38
    // The About dialog's component table, as wide as the messages dialog and about ten rows high, and the
    // licence-text viewer it opens.
    readonly property real aboutComponentsWidth: unit * 38
    readonly property real aboutComponentsHeight: unit * 16
    readonly property real aboutLicenceColumnWidth: unit * 16
    readonly property real licenceTextWidth: unit * 52
    readonly property real licenceTextHeight: unit * 32
}
