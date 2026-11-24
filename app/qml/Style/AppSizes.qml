// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton

import QtQuick

import EasyApplication.Gui.Style as EaStyle

// edi's own layout values, in one place: each is taken from easydiffractionbeta's QML and expressed in
// the base's font size, so the pages carry no bare numbers. Fonts come only from the base's EaStyle
// tokens, colours from those and AppColors.
QtObject {
    readonly property real unit: EaStyle.Sizes.fontPixelSize
    readonly property real assistantDefaultWidth: unit * 30
    readonly property real assistantMinimumWidth: unit * 23
    readonly property real assistantMaximumWidth: unit * 48
    readonly property real assistantMainMinimumWidth: unit * 40
    // The original composer's Stop circle, shared by the status controls.
    readonly property real assistantIconExtent: EaStyle.Sizes.toolButtonHeight * 0.75
    readonly property real assistantControlBorderWidth: 1 // The existing status eye/Success outline.
    // Borderless working glyphs match the eye circle's inner diameter.
    readonly property real assistantIndicatorExtent: Math.max(0, assistantIconExtent - 2 * assistantControlBorderWidth)
    // The original composer Stop/eye font size, shared by their status-bar copies.
    readonly property real assistantControlIconSize: unit * 0.75 * 1.25
    // Stop square only: keep the existing eye, circle paint and full hit target.
    readonly property real assistantStopIconSize: assistantControlIconSize * 0.85

    // The wordmark's mark (Components/Wordmark.qml; its name is 0.4309 of it): easydiffractionbeta's 5 units,
    // the same on Home and in About (WordmarkWithVersion, edi ADR-0017 §1).
    readonly property real homeMarkDiameter: unit * 5

    // The smallest app area every page is made for (ADR-0103 decision 3): the desktop window cannot be made smaller,
    // and the browser's page shows only a request to make it larger below it (Main.qml). In logical pixels. Below
    // sideBarBelowWidth the sidebar sits under the main view, which needs a taller window.
    readonly property int minimumAppWidth: 360
    // The window's width (Main.qml binds it) and its range, the one width test every layout reads (ADR-0103
    // decision 1): compact below 600, medium to 1024, expanded to 1600, large above; a boundary belongs to the upper.
    property real appWidth: 1280
    readonly property string range: appWidth < 600 ? "compact" : appWidth < 1024 ? "medium" : appWidth < 1600 ? "expanded" : "large"
    readonly property bool compact: range === "compact"
    // Below this width the sidebar moves under the main view: the narrowest window whose main view, beside the sidebar,
    // still holds the widest main-view tab bar (the Analysis page's seven tabs) on one line, so no tabs overlap and no
    // chart gets narrower than its tabs (the owner, 2026-11-21). 800 until the pages report their tab bars.
    property var mainTabsWidths: ({})
    readonly property real mainTabsWidth: Math.max(0, ...Object.values(mainTabsWidths))
    // Each page's widest bar so far: the bold name of the selected tab moves it by a fraction of a pixel, which must
    // not move the switch back and forth.
    function noteMainTabs(page: string, width: real) {
        if ((mainTabsWidths[page] ?? 0) >= width)
            return;
        const next = Object.assign({}, mainTabsWidths);
        next[page] = width;
        mainTabsWidths = next;
    }
    // The least heights of a pattern's main pane and of its residual in the bottom-sidebar layout, where the window
    // holds them (the owner, 2026-11-24).
    readonly property real paneMinimum: 120
    readonly property real residualMinimum: 40
    // What the main view needs there for them: its tab bar, the block selector's row, the chart toolbar's with its gaps,
    // the x labels and title, and the panes with the project's most Bragg rows (PatternChart's own lengths).
    function bottomMainNeed(braggRows: int): real {
        const em = EaStyle.Sizes.fontPixelSize;
        const around = EaStyle.Sizes.tabBarHeight + em + EaStyle.Sizes.comboBoxHeight + em + toolbarControlSize + mainAreaMargin + 5 * em;
        const between = braggRows > 0 ? Math.round((0.5 + 1.5 * braggRows) * em) + 2 * em : em;
        return around + paneMinimum + between + residualMinimum;
    }
    // The sidebar's height at the bottom: half the window, at most 70 % of the page, less what the chart needs. Where
    // that leaves it under 14 em it keeps the half. From the window and the project's Bragg rows alone, the same on every
    // page and after a fit.
    function bottomSideBarHeight(pageHeight: real, windowHeight: real, braggRows: int): real {
        const half = Math.min(pageHeight * 0.7, windowHeight * 0.5);
        const left = pageHeight - bottomMainNeed(braggRows);
        return Math.round(left >= EaStyle.Sizes.fontPixelSize * 14 ? Math.min(half, left) : half);
    }
    // The shown chart's toolbar width with every control in it (ToolbarLines.naturalWidth).
    property real toolbarNaturalWidth: 0
    // How far the current page's block selector reaches from its left edge, gap included, when it shares the chart
    // toolbar's row (the bottom-sidebar layout), so the toolbar starts after it; 0 when the selector has its own row.
    property real selectorRowReserve: 0
    // A lone control in a sidebar group (a combo box alone on its row): the sidebar's width, at most about 30 em, so a
    // wide window does not stretch a short choice across the whole sidebar (the owner, 2026-11-21).
    readonly property real loneControlWidth: Math.min(EaStyle.Sizes.sideBarContentWidth, Math.round(EaStyle.Sizes.fontPixelSize * 30))
    readonly property int sideBarBelowWidth: {
        if (!(mainTabsWidth > 0))
            return 800;
        // The main view's own margin on each side, and the sidebar's border.
        const needed = mainTabsWidth + EaStyle.Sizes.fontPixelSize * 2 + EaStyle.Sizes.borderThickness;
        // And the sidebar, half the window there, holds the parameter table's base columns (Name, Value, s.u., Free):
        // the smallest landscape window shows them (ADR-0103 decision 3).
        // The fixed base, as the fixed full width: the switch is the same for every project.
        const base = sideBarBaseWidth;
        for (let width = 600; width < 2560; ++width) {
            // Two pixels over the base: its widths are fractional and the steps rounded, so at exactly the base the row
            // could reach a pixel past the table.
            // The widest the sidebar may be there, not the shown page's width: a page of narrow tables keeps the
            // switch where the parameter table puts it.
            if (width - sideBarMaximumFor(width) >= needed && sideBarMaximumFor(width) >= base + 2)
                return width;
        }
        return 2560;
    }
    function minimumAppHeight(width: real): int {
        return width < sideBarBelowWidth ? 640 : 600;
    }
    // Auto's full width: one value from the fonts and the parameter table's column model alone, the same on every page
    // and for every project, never moved by a page switch, a project, a fit or a table measuring (the owner,
    // 2026-11-23, "Auto is one fixed width per window size"). It is the parameter table's width before a fit: the row
    // number, a name at its typical budget, Start, Value and s.u. as a fitted value reads, the unit, Change, Min, Max
    // and Free, with the column spacings, the table's padding and the sidebar's insets. A page with narrower tables
    // shows the spare as its tables' rules place it.
    readonly property real sideBarDefaultFull: Math.round(EaStyle.Sizes.fontPixelSize * 52)
    readonly property FontMetrics autoBold: FontMetrics {
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        font.bold: true
    }
    readonly property FontMetrics autoPlain: FontMetrics {
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }
    // A parameter field's least readable width: a value at four significant digits with its sign, the row's widest
    // unit, the field's paddings. A row of fields keeps every field at least this wide, wrapping into even rows (six
    // as three and three) rather than cropping a number (the owner, 2026-11-23, "field rows reduce precision, then wrap").
    function fieldMinimumFor(unit: string): real {
        return Math.ceil(autoPlain.advanceWidth("-0.000") + autoPlain.advanceWidth(" " + unit) + EaStyle.Sizes.fontPixelSize * 1.5);
    }
    // The columns a row of `count` fields takes: `most` where each is still at least fieldMinimumFor(unit) wide, else the most
    // even rows that are (one field a row at the narrowest).
    function fieldColumns(count: int, most: int, width: real, spacing: real, unit: string): int {
        const least = fieldMinimumFor(unit);
        const fits = columns => (width - (columns - 1) * spacing) / columns >= least;
        if (fits(most))
            return most;
        for (let columns = Math.min(most - 1, count); columns > 1; --columns) {
            const even = Math.ceil(count / Math.ceil(count / columns));
            if (fits(even))
                return even;
        }
        return 1;
    }
    readonly property real autoValueColumn: Math.ceil(autoBold.advanceWidth("-0.00000")) + 2 * tableCellMargin
    readonly property real autoUncertaintyColumn: Math.ceil(autoPlain.advanceWidth("0.00000")) + 2 * tableCellMargin
    readonly property real autoChangeColumn: Math.ceil(autoPlain.advanceWidth("100.0% \u2191")) + 2 * tableCellMargin
    // As the parameter table sizes them: the bounds at their title or an infinite bound, the unit at deg² less the pull
    // that draws it one space after its value, the row number at two digits in bold, the Free column at its title and
    // arrow with its paddings (ParametersGroup.freeColumnWidth).
    readonly property real autoBoundColumn: Math.ceil(Math.max(autoPlain.advanceWidth("Max"), autoPlain.advanceWidth("-inf"))) + 2 * tableCellMargin
    readonly property real autoIndexColumn: Math.ceil(autoBold.advanceWidth("99")) + tableCellMargin * 2
    readonly property real autoFreeColumn: Math.ceil(unit * 1.35 + tableCellMargin + autoPlain.advanceWidth("Free"))
    readonly property real autoUnitColumn: Math.ceil(autoPlain.advanceWidth("deg\u00b2") - Math.max(0, tableCellMargin + EaStyle.Sizes.tableColumnSpacing - autoPlain.advanceWidth(" "))) + tableCellMargin
    // The table's padding and border, and the sidebar's own insets around it.
    readonly property real autoChrome: EaStyle.Sizes.groupBoxSpacing + EaStyle.Sizes.sideBarPadding + 2 * EaStyle.Sizes.tableColumnSpacing + 2 * EaStyle.Sizes.borderThickness
    // The name column's budget at the Auto stop: the widest name, icons included, of the bundled examples (W5):
    // 156 px, 11.14 em at the 14 px font, over 23 of them (the scan and synthetic series, which download, left out;
    // the e58-names check, 2026-11-23), with the cell's margins (T1).
    readonly property real nameBudget: Math.ceil(unit * 11.15) + 2 * tableCellMargin
    // Every column; and the base the narrowest window keeps (the row number, Name, Value, its unit, s.u. and Free).
    readonly property real sideBarFullWidth: Math.ceil(autoIndexColumn + nameBudget + 2 * autoValueColumn + autoUncertaintyColumn + autoUnitColumn + autoChangeColumn + 2 * autoBoundColumn + autoFreeColumn + 9 * EaStyle.Sizes.tableColumnSpacing + autoChrome)
    readonly property real sideBarBaseWidth: Math.ceil(autoIndexColumn + nameBudget + autoValueColumn + autoUncertaintyColumn + autoUnitColumn + autoFreeColumn + 5 * EaStyle.Sizes.tableColumnSpacing + autoChrome)
    // The narrower widths the sidebar's width button names (SideBarWidthButton), each the full width less the columns
    // it leaves out of the Parameters table (noteSideBarSteps): {bounds, values, compact}.
    // When a sidebar group last began to fold or unfold, and how long that takes (the base's 500 ms and a margin):
    // tables keep their room until it ends (DataTable.placeRoom).
    property double sideBarFoldedAt: 0
    readonly property int sideBarFoldMs: 550
    property var sideBarSteps: ({})
    function noteSideBarSteps(steps: var) {
        if (sideBarSteps.bounds !== steps.bounds || sideBarSteps.values !== steps.values || sideBarSteps.compact !== steps.compact)
            sideBarSteps = steps;
    }
    // The widest the sidebar can be at a window width: the main view keeps its widest tab bar (as the switch does).
    // and never more than half the window (ADR-0103 decision 3): every width mode is a step inside this envelope.
    function sideBarMaximumFor(width: real): int {
        return Math.round(Math.min(width * 0.5, width - mainTabsWidth - EaStyle.Sizes.fontPixelSize * 2 - EaStyle.Sizes.borderThickness));
    }
    // The sidebar's width at the side for the chosen mode (Preferences.sideBarWidthMode): Auto the rule below; Full, a
    // named width or Manual that width, at most what leaves the main view its tabs and at least the rule's narrowest.
    // Full: one fixed width from the window alone, as on edi main (the sidebar reaches from the window's edge to the
    // Experiment button's centre in the top bar; Main.qml binds it): the same on every page, never moved by a fit, a
    // project or a table measuring (the owner, 2026-11-22 and 2026-11-23). The content stop is Auto's.
    property real sideBarMainWidth: 0
    function sideBarWidthChosen(width: real, mode: string, manual: int): int {
        let chosen = -1;
        if (mode === "full")
            chosen = sideBarMainWidth > 0 ? sideBarMainWidth : sideBarDefaultFull;
        else if (mode === "manual" && manual > 0)
            chosen = manual;
        else if (sideBarSteps[mode] > 0)
            chosen = sideBarSteps[mode];
        if (!(chosen > 0))
            return sideBarWidthFor(width);
        // Full is edi main's rule itself, never clamped to the other modes' envelope (W2).
        if (mode === "full")
            return Math.round(chosen);
        return Math.round(Math.min(chosen, sideBarMaximumFor(width)));
    }
    // Why a mode cannot give its width at a window width ("" when it does): no width shows exactly its columns, or the
    // window is too narrow for it; the width button says so beside the mode.
    function sideBarModeProblem(width: real, mode: string): string {
        if (mode === "auto" || mode === "manual" || mode === "full")
            return "";
        const wanted = sideBarSteps[mode] ?? -1;
        // Not measured yet (no table laid out, nothing cached): the mode is offered, it takes its width once measured.
        if (!(wanted > 0))
            return "";
        if (wanted > sideBarMaximumFor(width))
            return qsTr("needs a wider window");
        return "";
    }
    // The sidebar's width at the side in Auto, from the window's width (ADR-0103 decision 3): half the window, so at
    // the smallest landscape window it holds Name, Value, s.u. and Free, and it widens smoothly with the window while
    // the parameter table adds its columns one at a time as each fits (ParametersGroup.droppedAt); once every column
    // fits, at the content width of every column, it widens by at most one column spacing, then stops (the owner,
    // 2026-11-23). It always leaves the main view its tab bar.
    readonly property real sideBarBreathing: EaStyle.Sizes.tableColumnSpacing
    function sideBarWidthFor(width: real): int {
        return Math.round(Math.max(0, Math.min(sideBarFullWidth + sideBarBreathing, sideBarMaximumFor(width))));
    }

    // Home page (easydiffractionbeta Pages/Home/Page.qml)
    readonly property real homeBlockSpacer: unit * 2.5
    readonly property real homeLinkColumnsSpacing: unit * 3
    readonly property real homeLinkSpacing: unit
    readonly property real homeBranchTopPadding: unit * 0.5

    // Workflow pages (easydiffractionbeta Pages/*)
    readonly property real fieldSpacing: unit * 0.5           // a tag's padding
    // A table cell's margin on each side: with the column spacing, two neighbouring columns' contents are one em apart
    // whatever their alignment (T1).
    readonly property real tableCellMargin: (EaStyle.Sizes.fontPixelSize - EaStyle.Sizes.tableColumnSpacing) / 2
    readonly property real groupContentSpacing: unit          // between rows inside a group
    readonly property real indexColumnWidth: unit * 2.5       // a table's row-number column
    // A table's trailing row button: its glyph with a cell margin on both sides (T1, T3).
    readonly property real tableControlWidth: Math.round(unit + 2 * tableCellMargin)
    readonly property real iconColumnWidth: EaStyle.Sizes.tableRowHeight        // a table's action-button column
    readonly property real iconOnlyColumnWidth: unit * 2      // an icon-only display column: the icon and a margin (note 19)
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
    // One row of a legend (the pattern chart's, the structure view's): one text line's height, the pattern
    // legend's spacing (the owner, 2026-10-11).
    readonly property real legendRowHeight: Math.round(unit * 1.3)
    // The widest a datablock's name is drawn in a chart (a Bragg row's label, a legend entry, a Stacked or Map row):
    // a longer one is cut in its middle, the full name in a tooltip, so a long name never squeezes the plot (the
    // owner, 2026-11-22).
    readonly property real chartNameMaximum: unit * 10
    // The structure view's legend rows: halfway between a legend row and a combo box list entry (the owner,
    // 2026-10-11).
    readonly property real structureLegendRowHeight: Math.round((legendRowHeight + EaStyle.Sizes.comboBoxHeight) / 2)
    // A combo box list entry's side padding: the base MenuItem's (a literal 16 there).
    readonly property real listItemPadding: 16
    // Between the input boxes of one group, as between a chart toolbar's buttons (the owner's note 23).
    readonly property real inputSpacing: toolbarSpacing
    // The messages dialog's fixed width (edi ADR-0017 §14): about the Preferences dialog's.
    readonly property real messagesDialogContentWidth: unit * 38
    // The padding of a dialog's choice rows that read as one group (Save project as: Folder, Zip archive), closer
    // together than the usual rows (owner, 2026-10-25).
    readonly property real choiceRowPadding: Math.round(unit * 0.35)
    // The About window's content: room for the third-party table's columns and a licence text below it.
    readonly property real aboutWidth: unit * 52
    readonly property real aboutHeight: unit * 32
}
