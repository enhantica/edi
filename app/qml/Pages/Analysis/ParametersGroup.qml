// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Components as EaComponents

import edi.app

// The parameter table (easydiffractionbeta Pages/Analysis/SideBarBasic/Fittables.qml): every parameter
// the Structure and Experiment pages show, in page order, each named by icons as there (ParameterNames),
// filtered by name and variability; a value or vary change here is the same ParameterItem the pages bind.
// Minimum and maximum are the admissible range (edi has no user fit bounds), shown "-inf"/"inf" when
// unbounded. Untitled and fixed open, as the original's group (SideBarBasic.qml): the status bar carries
// the counts; `last`, as there, keeps the untitled group's border out of its content (note 7).
SideBarGroup {
    id: group

    property ProjectViewModel project: null
    property ParameterItem selected: null
    // Some experiment holds measured data: without any, nothing can be fitted (edi ADR-0046), so the free column, its
    // header menu and the free or fixed choice are shown disabled, keeping the layout when data arrive; the other filters stay
    // (the owner, 2026-11-02), and values stay editable. The disabled choice goes back to all parameters: one left from
    // a project with data showed one row under "Atomic displacement (4)" (the owner, 2026-10-27).
    readonly property bool measured: project !== null && project.fit.measured
    onMeasuredChanged: ApplicationInfo.parameterMeasuredChanged(false)
    // The selected parameter's row, kept as the filters and the rows change; -1 when it is not shown.
    // The pickers' row with each picker wide enough for its default text whole ("All categories (58)", W6), with the
    // project's own count, as the boxes draw it: the text 0.75 em in with 1 em after it, and the box's own room for its arrow.
    // Its paddings are not read: they count the arrow only while it is shown.
    readonly property real pickerRowNeed: {
        // Two digits at least, so the width is the same before the parameters are listed.
        const count = Math.max(10, parameterFilter.datablockGroups.length > 0 ? parameterFilter.datablockGroups[0].count : 0);
        const widest = Math.max(...[qsTr("All datablocks (%1)"), qsTr("All categories (%1)"), qsTr("All parameters (%1)")].map(text => filterMetrics.advanceWidth(text.arg(count))));
        return 3 * Math.ceil(widest + EaStyle.Sizes.fontPixelSize * 1.75 + 2 * categoryPicker.padding + categoryPicker.spacing + categoryPicker.indicator.width) + 2 * AppSizes.inputSpacing + (filters.below ? AppSizes.inputSpacing + filters.resetWidth : 0);
    }
    property int selectedRow: -1
    property real tableViewportHeight: 0
    // The free column fits its title and the arrow after it, with a table column's padding (the owner, 2026-10-11). Its
    // title and check boxes stand at the table's right edge, and the gap before it is the table's spacing between any two
    // columns, as between Change and Max (the owner, 2026-11-17).
    readonly property real freeGap: 0.25 * EaStyle.Sizes.fontPixelSize
    // The arrow ends where the right-aligned check boxes do: a check box's own padding before the column's edge, the
    // last column adding no spacing after it (DataTable.padForFiller; the owner, 2026-11-21).
    readonly property real freeInset: 0.5 * EaStyle.Sizes.fontPixelSize
    // The free title's word and arrow share one colour, each with the labels' own colour transition.
    property bool freeTitleHovered: false
    readonly property color freeTitleColor: !measured ? EaStyle.Colors.themeForegroundMinor : freeTitleHovered ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
    // A cell's margin on the left, so "Max" and "Free" are an em apart (T1).
    readonly property real freeColumnWidth: Math.ceil(AppSizes.tableCellMargin + freeTitleText.advanceWidth + freeGap + freeArrowText.advanceWidth + freeInset)
    // "Same for all" (edi ADR-0087 point 3): a switch on each experiment parameter tying it in every other experiment of
    // its set to the template's, through alias and constraint rows. Not shown for now: the parametric fit will offer it
    // through the Free box (ADR-0087, amended 2026-11-17).
    readonly property bool sameShown: false
    readonly property real sameColumnWidth: sameShown ? Math.ceil(sameTitleText.advanceWidth) + AppSizes.tableCellMargin * 2 + EaStyle.Sizes.fontPixelSize : 0
    // Read again whenever the relation rows change.
    readonly property int relationRows: project && project.analysis ? project.analysis.constraints.count + project.analysis.aliases.count : 0

    TextMetrics {
        id: sameTitleText
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        text: qsTr("Same for all")
    }

    TextMetrics {
        id: freeTitleText
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        text: qsTr("Free")
    }
    // The arrow is measured in the font it is drawn in: the hidden label's in the column below (the group box sizes
    // itself by one content item), which the arrow takes too. A metrics font built from the family alone can
    // resolve a face without the glyph and send Qt to the platform's fonts (FreeType warnings on macOS).
    TextMetrics {
        id: freeArrowText
        font: freeArrowProbe.font
        text: freeArrowProbe.text
    }

    objectName: "group.parameters"
    collapsible: false
    last: SideBarGroups.isLast(group)

    // A row is always selected while the table shows any (the owner, 2026-09-29; edi ADR-0017 §11): the first
    // shown row, when a project opens, when the experiment changes or when the filters hide the selected row;
    // a row the user selected stays selected while it is shown.
    function ensureSelection() {
        ApplicationInfo.ensureParameterSelection();
    }
    onSelectedChanged: ApplicationInfo.parameterSelectionChanged(false)

    onProjectChanged: ApplicationInfo.parameterSelectionChanged(true)
    Component.onCompleted: ApplicationInfo.parameterMeasuredChanged(true)

    Connections {
        target: parameterFilter
        function onRowsInserted() {
            group.ensureSelection();
        }
        function onRowsRemoved() {
            group.ensureSelection();
        }
        function onModelReset() {
            group.ensureSelection();
        }
        function onLayoutChanged() {
            group.ensureSelection();
        }
    }
    Connections {
        target: group.project
        function onCurrentExperimentIndexChanged() {
            group.ensureSelection();
        }
    }
    // Whatever changed the shown rows (a filter, a free or fixed edit, a fit, an Undo), the selection follows them.
    Connections {
        target: table
        function onCountChanged() {
            group.ensureSelection();
        }
    }

    // A picker entry's line: a datablock's icon in its colour, a category's icon in the minor colour, a kind heading in
    // bold, and the title with its parameter count.
    function datablockSegments(entry) {
        return ApplicationInfo.parameterSegments(entry, false);
    }
    function categorySegments(entry) {
        return ApplicationInfo.parameterSegments(entry, true);
    }
    // A picker's closed line where its whole one does not fit: without its icon, then in its short form: one word with the
    // count, which a cut would lose first (the owner, 2026-11-22), then the word alone. "All datablocks (259)" has the
    // given word, "Atomic displacement (12)" its last one; a name the user gave stays as it is.
    function shortLine(segments, room, word, named) {
        const last = segments && segments.length > 0 ? segments[segments.length - 1] : null;
        if (!last || last.text === undefined)
            return segments ?? [];
        const advance = text => Math.ceil(filterMetrics.advanceWidth(text));
        const whole = String(last.text);
        if (advance(whole) + (segments.length - 1) * EaStyle.Sizes.fontPixelSize * 1.75 <= room)
            return segments;
        const match = whole.match(/^(.*) (\(\d+\))$/);
        const title = match ? match[1] : whole;
        const ending = title.slice(title.lastIndexOf(" ") + 1);
        const short = word !== "" ? word : named ? title : ending.charAt(0).toUpperCase() + ending.slice(1);
        const forms = [whole, match ? `${short} ${match[2]}` : short, short];
        return [Object.assign({}, last, {
                "text": forms.find(text => advance(text) <= room) ?? short
            })];
    }
    function shortened(segments, whole) {
        return segments.length > 0 && segments[segments.length - 1].text !== whole;
    }
    FontMetrics {
        id: filterMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }

    // A datablock's colour, as its icon has it elsewhere: a structure's or an experiment's by its place in the
    // project's list.
    function datablockColor(kind, name) {
        return ApplicationInfo.parameterDatablockColor(kind, name);
    }

    function bound(value) {
        return ApplicationInfo.parameterBound(value);
    }

    Column {
        spacing: AppSizes.groupContentSpacing

        EaElements.Label {
            id: freeArrowProbe
            visible: false
            font.family: EaStyle.Fonts.iconsFamily
            font.pixelSize: EaStyle.Sizes.fontPixelSize
            text: "\uf0d7"
        }
        // The filters (edi ADR-0046): datablocks, categories and parameters on the top line, each narrowing the next,
        // then the name filter and a button clearing all four. Every count is a number of parameters.
        Column {
            id: filters

            // Shown with or without measured data: a calculation-only project filters its parameters too.
            // In the bottom layout there is no name filter, and the reset sits at the end of the pickers' row (the
            // owner, 2026-11-23).
            readonly property bool below: EaStyle.Sizes.sideBarBelow
            readonly property real resetWidth: below ? datablockPicker.height : 0
            readonly property real third: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.inputSpacing - (below ? AppSizes.inputSpacing + resetWidth : 0)) / 3

            spacing: AppSizes.groupContentSpacing

            Row {
                spacing: AppSizes.inputSpacing

                // Each picker shows the filter the table applies: its index, its closed text with the icon and the
                // parameter count, all read from the filter model. A rebuilt list resets a combo box's index, so the
                // index follows the filter again after every rebuild and every choice (the owner, 2026-10-21).
                SearchableComboBox {
                    id: datablockPicker
                    readonly property int selectedIndex: Math.max(0, parameterFilter.datablocks.indexOf(parameterFilter.datablockFilter))
                    readonly property var selected: parameterFilter.datablockGroups[selectedIndex] ?? null
                    function follow() {
                        currentIndex = Qt.binding(() => datablockPicker.selectedIndex);
                    }
                    objectName: "parameters.datablock"
                    // Shown disabled until an experiment has measured data, as the free/fixed picker and the Free
                    // column are (the owner, 2026-11-15).
                    enabled: group.measured
                    ToolTip.text: !enabled ? qsTr("The parameter pickers apply once an experiment has measured data") : group.shortened(datablockClosed.segments, displayText) ? displayText : ""
                    width: filters.third
                    model: parameterFilter.datablockGroups
                    textRole: "title"
                    searchThreshold: 1000
                    popup.width: Math.max(width, optionWidth + 3 * font.pixelSize)
                    currentIndex: selectedIndex
                    displayText: selected ? selected.title : ""
                    onModelChanged: ApplicationInfo.parameterPickerChanged(0, false, undefined)
                    onActivated: index => ApplicationInfo.parameterPickerChanged(0, true, index)
                    contentItem: Item {
                        clip: true
                        IconLine {
                            id: datablockClosed
                            x: EaStyle.Sizes.fontPixelSize * 0.75
                            anchors.verticalCenter: parent.verticalCenter
                            maximumWidth: Math.max(1, parent.width - x - EaStyle.Sizes.fontPixelSize)  // a gap before the arrow
                            elide: Text.ElideMiddle
                            textColor: EaStyle.Colors.themeForeground
                            segments: group.shortLine(group.datablockSegments(datablockPicker.selected), maximumWidth, datablockPicker.selectedIndex === 0 ? qsTr("Blocks") : "", true)
                        }
                    }
                    delegate: EaElements.MenuItem {
                        id: datablockEntry
                        required property int index
                        required property var modelData
                        width: datablockPicker.popup.width
                        height: EaStyle.Sizes.comboBoxHeight
                        text: modelData.title
                        highlighted: datablockPicker.highlightedIndex === index
                        contentItem: Item {
                            implicitHeight: datablockLine.implicitHeight
                            IconLine {
                                id: datablockLine
                                anchors.verticalCenter: parent.verticalCenter
                                maximumWidth: parent.width
                                textColor: EaStyle.Colors.themeForeground
                                segments: group.datablockSegments(datablockEntry.modelData)
                            }
                        }
                    }
                }
                SearchableComboBox {
                    id: categoryPicker
                    readonly property int selectedIndex: Math.max(0, parameterFilter.categories.indexOf(parameterFilter.categoryFilter))
                    readonly property var selected: parameterFilter.categoryGroups[selectedIndex] ?? null
                    function follow() {
                        currentIndex = Qt.binding(() => categoryPicker.selectedIndex);
                    }
                    objectName: "parameters.category"
                    enabled: group.measured
                    ToolTip.text: !enabled ? qsTr("The parameter pickers apply once an experiment has measured data") : group.shortened(categoryClosed.segments, displayText) ? displayText : ""
                    width: filters.third
                    model: parameterFilter.categoryGroups
                    textRole: "title"
                    searchThreshold: 1000
                    popup.width: Math.max(width, optionWidth + 3 * font.pixelSize)
                    currentIndex: selectedIndex
                    displayText: selected ? selected.title : ""
                    onModelChanged: ApplicationInfo.parameterPickerChanged(1, false, undefined)
                    onActivated: index => ApplicationInfo.parameterPickerChanged(1, true, index)
                    contentItem: Item {
                        clip: true
                        IconLine {
                            id: categoryClosed
                            x: EaStyle.Sizes.fontPixelSize * 0.75
                            anchors.verticalCenter: parent.verticalCenter
                            maximumWidth: Math.max(1, parent.width - x - EaStyle.Sizes.fontPixelSize)  // a gap before the arrow
                            textColor: EaStyle.Colors.themeForeground
                            segments: group.shortLine(group.categorySegments(categoryPicker.selected), maximumWidth, categoryPicker.selectedIndex === 0 ? qsTr("Categories") : "", false)
                        }
                    }
                    delegate: EaElements.MenuItem {
                        id: categoryEntry
                        required property int index
                        required property var modelData
                        width: categoryPicker.popup.width
                        height: EaStyle.Sizes.comboBoxHeight
                        text: modelData.title
                        highlighted: categoryPicker.highlightedIndex === index
                        contentItem: Item {
                            implicitHeight: categoryLine.implicitHeight
                            IconLine {
                                id: categoryLine
                                anchors.verticalCenter: parent.verticalCenter
                                maximumWidth: parent.width
                                textColor: EaStyle.Colors.themeForeground
                                segments: group.categorySegments(categoryEntry.modelData)
                            }
                        }
                    }
                }
                // A disabled control takes no hover, so the reason it is disabled comes from here.
                Item {
                    width: variabilityPicker.width
                    height: variabilityPicker.height

                    SearchableComboBox {
                        id: variabilityPicker
                        readonly property var titles: [qsTr("All parameters (%1)").arg(parameterFilter.variabilityCounts[0]), qsTr("Free parameters (%1)").arg(parameterFilter.variabilityCounts[1]), qsTr("Fixed parameters (%1)").arg(parameterFilter.variabilityCounts[2]), qsTr("Not fittable (%1)").arg(parameterFilter.variabilityCounts[3])]
                        function follow() {
                            currentIndex = Qt.binding(() => parameterFilter.variability);
                        }
                        objectName: "parameters.variability"
                        // Free and fixed mean nothing before there are measured data to fit (edi ADR-0046). The reason is
                        // the picker's own tooltip text, which the combo box shows disabled too.
                        enabled: group.measured
                        ToolTip.text: !enabled ? qsTr("Free and fixed parameters apply once an experiment has measured data") : variabilityText.text !== displayText ? displayText : ""
                        width: filters.third
                        model: titles
                        currentIndex: parameterFilter.variability
                        displayText: titles[parameterFilter.variability]
                        // The same choices without the word "parameters", for a box too narrow for the full title: the
                        // count is what a cut would lose first (the owner's sweep, 2026-11-22).
                        // And then the word alone.
                        readonly property var words: [qsTr("Params"), qsTr("Free"), qsTr("Fixed"), qsTr("Not fittable")]
                        readonly property var forms: {
                            const at = parameterFilter.variability;
                            return [displayText, `${words[at]} (${parameterFilter.variabilityCounts[at]})`, words[at]];
                        }
                        // As the other two pickers: the text cut a gap before the arrow, not under it.
                        contentItem: Item {
                            clip: true
                            EaElements.Label {
                                id: variabilityText
                                x: EaStyle.Sizes.fontPixelSize * 0.75
                                anchors.verticalCenter: parent.verticalCenter
                                width: Math.max(1, parent.width - x - EaStyle.Sizes.fontPixelSize)
                                elide: Text.ElideRight
                                color: variabilityPicker.enabled ? EaStyle.Colors.themeForeground : EaStyle.Colors.themeForegroundDisabled
                                text: variabilityPicker.forms.find(form => Math.ceil(variabilityMetrics.advanceWidth(form)) <= width) ?? variabilityPicker.forms[2]
                            }
                            FontMetrics {
                                id: variabilityMetrics
                                font: variabilityText.font
                            }
                        }
                        onModelChanged: ApplicationInfo.parameterPickerChanged(2, false, undefined)
                        onActivated: index => ApplicationInfo.parameterPickerChanged(2, true, index)
                    }
                }
                EaElements.SideBarButton {
                    objectName: "parameters.clearFiltersBelow"
                    visible: filters.below
                    width: filters.resetWidth
                    height: datablockPicker.height
                    fontIcon: "eraser"
                    text: ""
                    ToolTip.text: qsTr("Clear all filters")
                    onClicked: parameterFilter.clearFilters()
                }
            }
            Row {
                visible: !filters.below
                spacing: AppSizes.inputSpacing

                EaElements.TextField {
                    id: nameField
                    objectName: "parameters.nameFilter"
                    width: EaStyle.Sizes.sideBarContentWidth - AppSizes.inputSpacing - clearButton.width
                    placeholderText: qsTr("Filter by name")
                    text: parameterFilter.nameFilter
                    // Applied once typing pauses: filtering the table at every key took 131 ms a key (R3: at most 16).
                    onTextEdited: nameApply.restart()
                    Timer {
                        id: nameApply
                        interval: 200
                        onTriggered: parameterFilter.nameFilter = nameField.text
                    }
                }
                EaElements.SideBarButton {
                    id: clearButton
                    objectName: "parameters.clearFilters"
                    width: height
                    height: nameField.height
                    property string toolTip: qsTr("Clear all filters")
                    fontIcon: "eraser"
                    text: ""
                    ToolTip.text: toolTip
                    onClicked: parameterFilter.clearFilters()
                }
            }
        }

        DataTable {
            id: table
            objectName: "parameters.list"
            kindFloors: false
            defaultInfoText: qsTr("No parameters")
            sourceModel: ParameterFilterModel {
                id: parameterFilter
                sourceModel: group.project ? group.project.parameters : null
                // The Settings tab's show-filters, by ParameterItem.FitGroup from NotMeasured (edi ADR-0053).
                readonly property var wanted: [Preferences.analysisShowNotMeasured, Preferences.analysisShowBySymmetry, Preferences.analysisShowByConstraint, Preferences.analysisShowFixedSettings]
                function follow() {
                    ApplicationInfo.parameterShownGroupsFollow();
                }
                onWantedChanged: follow()
                Component.onCompleted: follow()
            }
            marksCurrentRow: true
            currentRow: group.selectedRow
            // Widths from column types, not rows (ADR-0103 rule 4): the name, start, value, units, s.u., change, and the
            // bounds, which are short (0, 1, inf). A fitted run changes values, never a column, so a fit measures no row.
            // Its columns by kind, measured from their content (DataTable.columnKinds); the widths are this table's
            // own rule below, which drops columns in a narrow sidebar.
            columnKinds: ["index", "name", "value", "value", "unit", "uncertainty", "change", "number", "number"].concat(group.measured ? ["control", "control"] : []).concat(group.sameShown ? ["control"] : [])
            onRowActivated: row => group.selected = parameterFilter.parameterAt(row)

            // A layout of its own (the owner, 2026-10-27): every column as wide as its type (ADR-0103 decision 4), the
            // name taking what is left, free at the right with a wider gap before it. Start and change are the report's
            // fit table columns, empty before a fit (owner record 2026-11-10). In a narrow sidebar the margins go
            // first, then whole columns by priority, so the name keeps its minimum width.
            readonly property var fittedColumns: [2, 3, 4, 5, 6, 7, 8]
            // Set by its own rule (applyColumns), never by the kind model's default.
            columns: []
            // Columns drop one at a time while the rest do not fit beside the name's minimum width (ADR-0103 decision 3):
            // Change, Max, Min, Start, then the unit (a width mode narrower than the base). The row number, Name, Value,
            // s.u. and Free stay at every width (the owner, 2026-11-22 and 2026-11-23, "Compact with s.u."). The header
            // and the rows show the same columns.
            readonly property var dropOrder: [[6], [8], [7], [2], [4]]
            readonly property real freeWidth: group.freeColumnWidth
            // The name's room before a column drops: its icons (about 5 em) and an ordinary label (Na1 B iso, about
            // 7 em). At the full sidebar width every column shows and only a longer name is cut, in its middle (the
            // owner, 2026-11-22).
            // Never more than the widest name: a short-named project keeps its columns at a narrower width.
            // The name budget, never the measured names: which columns fit is known before any row is measured (T6;
            // a minimum read from the names moved the columns once the names were measured).
            readonly property real nameMinimum: AppSizes.nameBudget
            // The name's content width: the widest name (its minimum until measured).
            // Before the names are measured, the name budget (AppSizes.nameBudget, the widest bundled name): measured,
            // a name that fits it changes nothing (T6).
            readonly property real nameContent: widestName > 0 ? Math.max(nameMinimum, widestName) : Math.max(nameMinimum, AppSizes.nameBudget)
            // Each column's measured content (its header or widest value): the table's raw measure, as this table sets
            // its columns itself and the combined widths keep a set column's own width.
            // Each column's width by its kind alone, the reserve the Auto width is made of (AppSizes), never the values
            // shown: a longer value or a fit moves no column (T5, T6); a value wider than its column shows fewer digits.
            function contentOf(column: int): real {
                if (column === 2 || column === 3)
                    return AppSizes.autoValueColumn;
                if (column === 5)
                    return AppSizes.autoUncertaintyColumn;
                if (column === 6)
                    return AppSizes.autoChangeColumn;
                if (column === 7 || column === 8)
                    return AppSizes.autoBoundColumn;
                return Math.max(contentWidths[column] ?? 0, fittedWidths[column] ?? 0);
            }
            // With a cell's standard padding, never one read from the cells: those come and go as columns drop, and a
            // width that followed them moved the sidebar back and forth (the owner's sweep, 2026-11-23).
            readonly property real typicalValue: Math.ceil(boldMetrics.advanceWidth("-0.00000")) + 2 * AppSizes.tableCellMargin
            readonly property real typicalUncertainty: Math.ceil(unitMetrics.advanceWidth("0.00000")) + 2 * AppSizes.tableCellMargin
            readonly property real typicalChange: Math.ceil(unitMetrics.advanceWidth("100.0% \u2191")) + 2 * AppSizes.tableCellMargin
            FontMetrics {
                id: boldMetrics
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
                font.bold: true
            }
            readonly property real fittedSum: fittedColumns.reduce((sum, column) => sum + contentOf(column), 0)
            // The one rule for which columns a table width drops: the table shown and the sidebar widths named below
            // both ask it, so a named width shows what its name says.
            // The room left for the fitted columns beside the name's minimum at a table width.
            // A dropped column takes no width and no spacing: only the shown columns' gaps are counted, so their
            // width goes to the name rather than to empty space (the owner, 2026-11-22).
            function roomAt(tableWidth: real, dropped: var): real {
                const shown = (dropped.includes(0) ? 0 : 1) + 1 + fittedColumns.filter(column => !dropped.includes(column)).length + (group.measured ? 1 : 0) + (group.sameShown ? 1 : 0);
                return tableWidth - rowPadding * 2 - EaStyle.Sizes.borderThickness * 2 - EaStyle.Sizes.tableColumnSpacing * (shown - 1) - (dropped.includes(0) ? 0 : numberColumnWidth) - freeWidth - group.sameColumnWidth - nameMinimum;
            }
            readonly property real fittedRoom: roomAt(width, droppedColumns)
            function droppedAt(tableWidth: real): var {

                // Every column shows while there is room, empty or not (the owner, 2026-11-22). The columns' widths are
                // their kinds' (T5), known before any row is measured, so the first frame already shows them (T6: the
                // base alone, then every column, moved the table on its first show).
                let dropped = [];
                for (let step = 0; step < dropOrder.length; ++step) {
                    const kept = fittedColumns.filter(column => !dropped.includes(column));
                    // The name never gives way below its minimum: columns drop first, so no name is cut to dots.
                    const room = roomAt(tableWidth, dropped);
                    // Every column at its fixed content width; a column that does not fit drops, never narrows.
                    if (kept.reduce((total, column) => total + columnWidth(column), 0) <= room)
                        break;
                    dropped = dropped.concat(dropOrder[step].filter(column => !dropped.includes(column)));
                }
                return dropped;
            }
            // A named width mode shows exactly its columns, whatever room is left (W6: Compact is Name, Value, s.u. and
            // Free; the owner, 2026-11-23); Auto, Full and Manual drop by the room.
            readonly property var modeDrops: ({
                    "bounds": [6],
                    "values": [6, 8, 7],
                    "compact": [6, 8, 7, 2, 4]
                })
            readonly property var droppedColumns: !EaStyle.Sizes.sideBarBelow && modeDrops[Preferences.sideBarWidthMode] !== undefined ? modeDrops[Preferences.sideBarWidthMode] : droppedAt(width)
            // Each data column at a minimal estimate from its content type plus one cell padding, the same for every
            // project; a value wider than that is written to fit (fewer digits, then ×10ⁿ; ADR-0051), and the name takes
            // everything left (the owner, 2026-11-22). The estimates are logged once (sweep reports).
            // Value at its own estimate; the units column as wide as the widest unit the shown rows have, less the pull
            // that draws it one space after the value (unitPull).
            function columnWidth(column: int): real {
                // The unit at its widest, deg², whatever the rows show (T5).
                if (column === 4)
                    return AppSizes.autoUnitColumn;
                return contentOf(column);
            }
            readonly property real unitGap: Math.ceil(unitMetrics.advanceWidth(" "))
            // How far the unit is drawn left of its column: the value's right padding and the column spacing, less one
            // space.
            // The value cells' right padding, as they report it (one value for every row).
            property real valuePadding: 0
            readonly property real unitPull: Math.max(0, valuePadding + EaStyle.Sizes.tableColumnSpacing - unitGap)
            // The widest unit among the shown rows, measured as the rows change (a short, known set; never in a width
            // binding).
            property real widestUnit: 0
            function measureUnits(): void {
                let widest = 0;
                for (let row = 0; row < parameterFilter.rowCount(); ++row) {
                    const p = parameterFilter.parameterAt(row);
                    if (p && p.displayUnits !== "")
                        widest = Math.max(widest, unitMetrics.advanceWidth(p.displayUnits));
                }
                widestUnit = Math.ceil(widest);
            }
            // The widest name among the shown rows, icons included: the name column's measured content (the owner,
            // 2026-11-23).
            readonly property real widestName: contentOf(1)
            Connections {
                target: parameterFilter
                function onModelReset() {
                    Qt.callLater(table.measureUnits);
                }
                function onRowsInserted() {
                    Qt.callLater(table.measureUnits);
                }
                function onRowsRemoved() {
                    Qt.callLater(table.measureUnits);
                }
                function onLayoutChanged() {
                    Qt.callLater(table.measureUnits);
                }
            }
            FontMetrics {
                id: unitMetrics
                font.family: EaStyle.Fonts.fontFamily
                font.pixelSize: EaStyle.Sizes.fontPixelSize
            }
            property string columnReport: ""
            function reportColumns(): void {
                const titles = ["", "Name", "Start", "Value", "units", "s.u.", "Change", "Min", "Max"];
                const report = fittedColumns.map(column => `${titles[column]} ${Math.round(columnWidth(column))}`).join(", ");
                if (report !== columnReport) {
                    columnReport = report;
                    console.info("parameters column estimates (px, padding included): " + report);
                }
            }
            onFittedWidthsChanged: Qt.callLater(reportColumns)
            // Start, Value, s.u. and Change: the columns that narrow when the row is too wide.
            readonly property var numberColumns: [2, 3, 5, 6]
            function shows(column: int): bool {
                return !droppedColumns.includes(column);
            }
            // Every column after a fit at its type's width with the columns' spacing between them, the name whole: the width
            // the sidebar takes from about 1280 px up (AppSizes.sideBarFullWidth; the owner, 2026-11-22), noted with the
            // sidebar's own insets. (With the table's full margin on every column it came to about 950 px, leaving the
            // main view less than its tab bar at 1280.)
            readonly property real allColumnsWidth: rowPadding * 2 + EaStyle.Sizes.borderThickness * 2 + EaStyle.Sizes.tableColumnSpacing * (9 + (group.sameShown ? 1 : 0)) + numberColumnWidth + freeWidth + group.sameColumnWidth + nameContent + fittedColumns.reduce((sum, column) => sum + contentOf(column), 0)
            // The sidebar's own insets around this table.
            readonly property real sideBarInsets: EaStyle.Sizes.groupBoxSpacing + EaStyle.Sizes.sideBarPadding
            // The table width that shows exactly the columns left after `dropped` (each at its fixed width, the name at
            // its minimum): each step of the rule, from all columns to the base and narrower.
            // With every column shown, the name at its content width: the full width stops there (the owner,
            // 2026-11-23); narrower steps keep the name's minimum.
            function needFor(dropped: var): real {
                const all = dropped;
                return -roomAt(0, all) + fittedColumns.filter(column => !all.includes(column)).reduce((sum, column) => sum + columnWidth(column), 0) + (all.length === 0 ? nameContent - nameMinimum : 0);
            }
            // The steps, noted for the sidebar (AppSizes.noteSideBarSteps): all columns ("full"), one less each time to
            // the base (Name, Value, s.u., Free); the width modes are steps of the rule: No change, Fit values, Compact.
            function noteWidths(): void {
                // From the columns' kinds alone (T5), so neither its page shown nor its rows measured: a measure that a
                // page switch broke off left every named mode at Auto's width. A project's rows set the row number's width.
                if (!(count > 0))
                    return;
                const steps = [];
                let dropped = [];
                steps.push(Math.ceil(needFor(dropped) + sideBarInsets));
                for (let step = 0; step < dropOrder.length - 1; ++step) {
                    dropped = dropped.concat(dropOrder[step]);
                    steps.push(Math.ceil(needFor(dropped) + sideBarInsets));
                }
                console.info(`sidebar steps (px, all columns to the base): ${steps.join(", ")}; insets ${Math.round(sideBarInsets)}; ${widestName > 0 ? `widest name ${Math.ceil(widestName)} px (${(widestName / EaStyle.Sizes.fontPixelSize).toFixed(2)} em)` : "names not measured yet"}`);
                AppSizes.noteSideBarSteps({
                    "steps": steps,
                    "bounds": Math.ceil(needFor([6]) + sideBarInsets),
                    "values": Math.ceil(needFor([6, 8, 7]) + sideBarInsets),
                    // Never narrower than the pickers' row with each picker showing its text whole (W6).
                    "compact": Math.ceil(Math.max(needFor([6, 8, 7, 2, 4]) + sideBarInsets, group.pickerRowNeed + EaStyle.Sizes.sideBarWidth - EaStyle.Sizes.sideBarContentWidth))
                });
            }
            // What the named widths are made of.
            readonly property var stepInputs: [needFor([6, 8, 7, 2, 4]), needFor([]), group.pickerRowNeed, count > 0]
            onStepInputsChanged: Qt.callLater(noteWidths)
            readonly property var shownColumns: fittedColumns.filter(column => shows(column))
            readonly property real shownSum: shownColumns.reduce((sum, column) => sum + columnWidth(column), 0)
            function fittedColumn(column: int): real {
                return shownColumns.includes(column) ? Math.ceil(columnWidth(column)) : 0;
            }
            // The name takes the rest, set here rather than by the table's rule, so it follows only the table's width
            // and the measured texts, never the rows in view.
            // At least its minimum where the columns allow it (they drop first); below that, when nothing else can give
            // (a narrow width mode), the name is cut in its middle rather than the row overrunning the table: the
            // columns add up to the table's width.
            // The name at its content width; what is left past it is empty space before Free (the owner, 2026-11-23),
            // or the name's when that is less than one column spacing.
            readonly property real nameRoom: Math.max(EaStyle.Sizes.fontPixelSize * 4, Math.floor(fittedRoom + nameMinimum - shownColumns.reduce((sum, column) => sum + fittedColumn(column), 0)))
            // Past one column spacing the spare is an empty column before Free (or the row's right end without it);
            // up to one spacing the name holds it (the owner, 2026-11-23: at most one spacing past the widest name).
            // The row without the spare: the name at the smaller of its content and its room.
            readonly property var baseColumns: [shows(0) ? numberColumnWidth : 0, Math.min(nameRoom, Math.ceil(nameContent))].concat(fittedColumns.map(column => fittedColumn(column))).concat(group.measured ? [freeWidth] : []).concat(group.sameShown ? [group.sameColumnWidth] : [])
            // What the row leaves of the table's inner width, its spacings counted between the columns that take width.
            readonly property real leftOver: {
                const taking = baseColumns.filter(column => column > 0.5);
                const used = taking.reduce((sum, column) => sum + column, 0) + EaStyle.Sizes.tableColumnSpacing * Math.max(0, taking.length - 1);
                return Math.floor(width - rowPadding * 2 - EaStyle.Sizes.borderThickness * 2 - used);
            }
            // Nothing shared out before the columns are measured: a leftover of columns of nothing overran the row.
            readonly property bool measuredColumns: (contentWidths[3] ?? 0) > 0
            // The name takes what is left up to the name budget (the widest bundled example's name), so at the Auto stop
            // the space before Free is at most one column gap for every example (W5); more is spare before Free (T4).
            readonly property real nameGrow: Math.min(Math.max(0, leftOver), Math.max(0, AppSizes.nameBudget - baseColumns[1]))
            readonly property real afterName: leftOver - nameGrow
            readonly property bool spares: afterName > EaStyle.Sizes.tableColumnSpacing + 1
            readonly property real spareWidth: group.measured && spares ? afterName - EaStyle.Sizes.tableColumnSpacing : 0
            readonly property real nameWidth: baseColumns[1] + nameGrow + (spares ? 0 : Math.max(0, afterName))
            readonly property var wantedColumns: [shows(0) ? numberColumnWidth : 0, nameWidth].concat(fittedColumns.map(column => fittedColumn(column))).concat(group.measured ? [spareWidth, freeWidth] : []).concat(group.sameShown ? [group.sameColumnWidth] : [])
            // Applied a moment later: new widths remake rows and measure them again, which would otherwise feed back
            // into the widths while they are being worked out.
            function applyColumns() {
                if (ApplicationInfo.sameColumnWidths(columns, wantedColumns))
                    return;
                const recount = columns.length !== wantedColumns.length;
                columns = wantedColumns;
                // A new set of columns is measured afresh: a measure made before them had nothing to fill.
                if (recount)
                    Qt.callLater(refit);
            }
            onWantedColumnsChanged: Qt.callLater(applyColumns)
            Component.onCompleted: {
                columns = wantedColumns;
                Qt.callLater(measureUnits);
                Qt.callLater(refit);
            }

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    visible: table.shows(0)
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Name")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    visible: table.shows(2)
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("Start")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("Value")
                }
                // Pulled left with its cells, so the header and the cells keep one geometry.
                EaComponents.ListViewLabel {
                    readonly property bool keepsAlignment: true
                    visible: table.shows(4)
                    horizontalAlignment: Text.AlignLeft
                    text: ""
                    transform: Translate {
                        x: -table.unitPull
                    }
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    visible: table.shows(5)
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("s.u.")
                }
                // Right-aligned on the arrows' right edge, a cell margin before the column's, as the change cells end.
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    readonly property bool keepsAlignment: true
                    visible: table.shows(6)
                    horizontalAlignment: Text.AlignRight
                    rightPadding: AppSizes.tableCellMargin
                    text: qsTr("Change")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    visible: table.shows(7)
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("Min")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    visible: table.shows(8)
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("Max")
                }
                // The spare width, empty, before Free.
                Item {
                    visible: group.measured && table.spareWidth > 0
                    height: 1
                }
                // The title is a button, marked by the combo boxes' arrow: a click frees or fixes every row the
                // filters show, as one Undo step (the owner, 2026-10-11). The arrow ends where the right-aligned check
                // boxes do; its menu opens centred, so the title is as wide as itself.
                EaComponents.ListViewLabel {
                    id: freeTitle
                    elide: Text.ElideRight
                    // Laid out here, not by the table's alignment rule.
                    readonly property bool keepsAlignment: true
                    objectName: "parameters.freeHeader"
                    horizontalAlignment: Text.AlignRight
                    rightPadding: freeArrow.width + group.freeGap + group.freeInset
                    color: group.freeTitleColor
                    text: qsTr("Free")

                    // Whether the click area that takes the header's input is enabled: it is reparented over the
                    // header, so the title's own `enabled` does not follow it.
                    readonly property bool interactionEnabled: freeArea.enabled
                    // The item a press on the header lands on.
                    readonly property Item pressArea: freeArea
                    // Its menu, whose Free and Fixed a tutorial's Next chooses as the user would (edi ADR-0064).
                    readonly property FreeHeaderMenu menu: freeMenu

                    EaElements.Label {
                        id: freeArrow
                        x: freeTitle.width - freeTitle.rightPadding + group.freeGap
                        anchors.verticalCenter: parent.verticalCenter
                        font: freeArrowProbe.font
                        color: group.freeTitleColor
                        text: freeArrowProbe.text
                    }

                    // On the header itself, over this cell: the header's own click area covers its cells.
                    MouseArea {
                        id: freeArea
                        parent: freeTitle.parent ? freeTitle.parent.parent : freeTitle
                        z: 1
                        x: freeTitle.parent ? freeTitle.parent.x + freeTitle.x : 0
                        y: freeTitle.y
                        width: freeTitle.width
                        height: freeTitle.height
                        enabled: group.measured
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onContainsMouseChanged: group.freeTitleHovered = containsMouse
                        onClicked: freeMenu.open()
                    }
                    FreeHeaderMenu {
                        id: freeMenu
                        project: group.project
                        filter: parameterFilter
                    }
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    objectName: "parameters.sameHeader"
                    visible: group.sameShown
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("Same for all")
                }
            }

            delegate: TableRow {
                id: row

                required property ParameterItem parameter
                required property string path
                required property string units
                required property real minimum
                required property real maximum
                // A Pawley structure's intensities in one experiment, one row for all of them (edi ADR-0109): no value
                // of its own, only the name with their count and one Free box for every intensity.
                readonly property bool grouped: parameter !== null && parameter.groupSize > 0

                objectName: `parameters.row.${index}`
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    visible: table.shows(0)
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                // The iconified name on one centre line (edi ADR-0017 §8, §10), with the path in a tooltip on
                // hover.
                Item {
                    property int horizontalAlignment: Text.AlignLeft
                    objectName: `parameters.name.${row.index}`
                    // As wide as its icons and text with the cell's margins, which the table fits the column to; a narrower
                    // column ends the name with an ellipsis, its full name in the tooltip.
                    readonly property real cellMargin: AppSizes.tableCellMargin
                    implicitWidth: nameLine.fullWidth + 2 * cellMargin
                    height: parent.height
                    clip: true

                    IconLine {
                        id: nameLine
                        x: AppSizes.tableCellMargin
                        anchors.verticalCenter: parent.verticalCenter
                        maximumWidth: Math.max(1, parent.width - 2 * AppSizes.tableCellMargin)
                        // Every row keeps its icons, so their columns line up: a name too long for the column is cut in
                        // its middle (the owner, 2026-11-17, 2026-11-22), so both its ends show.
                        minimumTextWidth: 0
                        elide: Text.ElideMiddle
                        segments: ParameterNames.segments(row.parameter)
                    }
                    TapHandler {
                        acceptedButtons: Qt.RightButton
                        enabled: !row.grouped
                        onTapped: valueCell.openContextMenu(valueCell)
                    }
                    HoverHandler {
                        id: nameHover
                    }
                    EaElements.ToolTip {
                        text: ParameterNames.fullName(row.parameter)
                        requested: nameHover.hovered
                    }
                }
                NumberLabel {
                    objectName: `parameters.start.${row.index}`
                    visible: table.shows(2)
                    horizontalAlignment: Text.AlignRight
                    color: EaStyle.Colors.themeForegroundMinor
                    number: row.parameter && !row.grouped ? row.parameter.startText : ""
                }
                ParameterCell {
                    id: valueCell
                    columnAlignment: Text.AlignRight
                    objectName: `parameters.value.${row.index}`
                    onRightPaddingChanged: table.valuePadding = rightPadding
                    Component.onCompleted: table.valuePadding = rightPadding
                    item: row.grouped ? null : row.parameter
                    enabled: !row.grouped && refinable
                    // An auto-mode background's values are the estimate's, as in the Experiment page's table.
                    locked: row.parameter ? row.parameter.estimated : false
                    onActiveFocusChanged: ApplicationInfo.finishUiEvent(11, undefined)
                }
                // The unit in its own column right after Value, drawn one space after the value (the owner, 2026-11-22):
                // shifted left over the value's padding and the column spacing, its column as much narrower.
                EaComponents.ListViewLabel {
                    objectName: `parameters.units.${row.index}`
                    visible: table.shows(4)
                    color: EaStyle.Colors.themeForegroundMinor
                    // The value's family and size, one space after it, but never bold, whatever the value's weight (the
                    // owner, 2026-11-23).
                    font.family: EaStyle.Fonts.fontFamily
                    font.pixelSize: valueCell.font.pixelSize
                    font.bold: false
                    horizontalAlignment: Text.AlignLeft
                    readonly property bool keepsAlignment: true
                    leftPadding: 0
                    rightPadding: 0
                    // The column is narrower than the unit by the pull: the text runs on into the spacing it was pulled
                    // across, never cut.
                    elide: Text.ElideNone
                    transform: Translate {
                        x: -table.unitPull
                    }
                    text: row.grouped ? "" : row.units
                }
                NumberLabel {
                    objectName: `parameters.su.${row.index}`
                    visible: table.shows(5)
                    horizontalAlignment: Text.AlignRight
                    number: row.parameter && !row.grouped ? (row.parameter.fileValue !== "" ? row.parameter.fileSu : row.parameter.hasUncertainty ? NumberText.error(row.parameter.uncertainty, 0, row.parameter.value) : "") : ""
                    narrow: row.parameter && row.parameter.hasUncertainty ? NumberText.ownUncertainty(row.parameter.uncertainty, row.parameter.value) : ""
                    full: row.parameter && row.parameter.hasUncertainty ? NumberText.plainFull(row.parameter.uncertainty) : ""
                    // Red after a fit for a poorly determined or strongly correlated parameter, its reasons on hover
                    // (edi ADR-0085).
                    color: row.parameter && row.parameter.suFlagged ? EaStyle.Colors.red : EaStyle.Colors.themeForeground

                    HoverHandler {
                        id: suHover
                    }
                    EaElements.ToolTip {
                        text: row.parameter ? row.parameter.suReason : ""
                        requested: suHover.hovered && text !== ""
                    }
                }
                // The change in % right-aligned on its last digit, then its direction as an arrow icon of a fixed
                // width, as the report and notebook tables draw it.
                Item {
                    objectName: `parameters.change.${row.index}`
                    visible: table.shows(6)
                    property int horizontalAlignment: Text.AlignRight
                    readonly property bool keepsAlignment: true
                    readonly property real gap: EaStyle.Sizes.fontPixelSize * 0.25
                    implicitWidth: changePercent.implicitWidth + gap + changeArrow.width + AppSizes.tableCellMargin
                    height: parent.height
                    clip: true

                    EaElements.Label {
                        id: changeArrow
                        anchors.right: parent.right
                        anchors.rightMargin: AppSizes.tableCellMargin
                        anchors.verticalCenter: parent.verticalCenter
                        width: EaStyle.Sizes.fontPixelSize * 0.75
                        horizontalAlignment: Text.AlignHCenter
                        font.family: EaStyle.Fonts.iconsFamily
                        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
                        text: !row.parameter || row.parameter.changeDirection === 0 ? "" : row.parameter.changeDirection > 0 ? "arrow-up" : "arrow-down"
                    }
                    // The room left of the arrow, so a change too long for the column is fitted, in full on hover.
                    NumberLabel {
                        id: changePercent
                        anchors.right: changeArrow.left
                        anchors.rightMargin: parent.gap
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - AppSizes.tableCellMargin - parent.gap - changeArrow.width)
                        horizontalAlignment: Text.AlignRight
                        number: row.parameter && !row.grouped ? row.parameter.changeText : ""
                    }
                }
                // Right-aligned like its header, an infinite bound included.
                NumberLabel {
                    visible: table.shows(7)
                    horizontalAlignment: Text.AlignRight
                    color: EaStyle.Colors.themeForegroundMinor
                    number: row.grouped ? "" : group.bound(row.minimum)
                    full: NumberText.plainFull(row.minimum)
                }
                // Right-aligned like its header, an infinite bound included.
                NumberLabel {
                    visible: table.shows(8)
                    horizontalAlignment: Text.AlignRight
                    color: EaStyle.Colors.themeForegroundMinor
                    number: row.grouped ? "" : group.bound(row.maximum)
                    full: NumberText.plainFull(row.maximum)
                }
                Item {
                    visible: group.measured && table.spareWidth > 0
                    height: 1
                }
                // Enabled where a fit can vary the value, or while it is free so a flag set before a change can be
                // cleared; otherwise disabled, its tooltip naming why (edi ADR-0053). Without measured data every box
                // is disabled. A Pawley row's box is partly checked while only some of its intensities are free; a
                // click frees or fixes them all.
                Item {
                    // At the table's right edge, under the title's arrow (the owner, 2026-11-17).
                    property int horizontalAlignment: Text.AlignRight
                    visible: group.measured
                    height: parent.height

                    EaComponents.ListViewCheckBox {
                        id: freeBox
                        anchors.right: parent.right
                        horizontalAlignment: Text.AlignRight
                        objectName: `parameters.free.${row.index}`
                        enabled: group.measured && row.parameter !== null && (row.parameter.fittable || row.parameter.free || row.parameter.partiallyFree)
                        tristate: row.grouped
                        checkState: !row.parameter ? Qt.Unchecked : row.parameter.partiallyFree ? Qt.PartiallyChecked : row.parameter.free ? Qt.Checked : Qt.Unchecked
                        // Never partly checked by a click: that state only reports a mix.
                        nextCheckState: () => freeBox.checkState === Qt.Checked ? Qt.Unchecked : Qt.Checked
                        onToggled: row.parameter.free = checked
                        ToolTip.text: row.parameter && !row.parameter.fittable ? qsTr("Cannot be fitted: %1").arg(row.parameter.fitReason) : ""
                    }
                }
                Item {
                    property int horizontalAlignment: Text.AlignHCenter
                    visible: group.sameShown
                    height: parent.height

                    EaComponents.ListViewCheckBox {
                        id: sameBox
                        anchors.fill: parent
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `parameters.same.${row.index}`
                        readonly property bool applies: group.sameShown && group.relationRows >= 0 && group.project.sameForAllApplies(row.parameter)
                        visible: applies
                        checked: applies && group.relationRows >= 0 && group.project.sameForAll(row.parameter)
                        onToggled: {
                            group.project.setSameForAll(row.parameter, checked);
                            checked = Qt.binding(() => sameBox.applies && group.relationRows >= 0 && group.project.sameForAll(row.parameter));
                        }
                        ToolTip.text: qsTr("The same value in every experiment of the set, through a constraint each")
                    }
                }
            }
        }

        // The slider of the selected row with its limits in a read-only box on each side (the original's
        // Fittables.qml slider row). The limits are set when a row is selected, when the value changes other
        // than by the slider, and when the slider is released, as there: a drag moves the value within them, by one
        // unit of the last digit the item's display format shows. The limits show in that format, the value as the
        // file spells it.
        Row {
            id: sliderRow

            // The current row's parameter, and none while the table shows no row (the owner, 2026-10-21): the slider
            // and its limits are then disabled and empty, and come back for the parameter that becomes current. The row
            // comes from the filter model, which changes at once; the table's own count follows a frame later.
            // A Pawley row has no single value, so it moves nothing here.
            readonly property bool groupSelected: group.selectedRow >= 0 && group.selected !== null && group.selected.groupSize > 0
            readonly property ParameterItem selected: group.selectedRow >= 0 && !groupSelected ? group.selected : null
            property real lower: 0
            property real upper: 1

            function updateLimits() {
                ApplicationInfo.updateParameterSliderLimits();
            }

            spacing: EaStyle.Sizes.fontPixelSize
            onSelectedChanged: updateLimits()

            Connections {
                target: sliderRow.selected
                function onValueChanged() {
                    ApplicationInfo.finishUiEvent(6, undefined);
                }
            }

            EaElements.TextField {
                objectName: "parameters.slider.from"
                width: EaStyle.Sizes.fontPixelSize * 6
                readOnly: true
                enabled: sliderRow.selected !== null
                text: sliderRow.selected ? sliderRow.selected.displayText(slider.from) : ""
                ToolTip.text: enabled ? "" : qsTr("Select a parameter in the table first")
            }
            EaElements.Slider {
                id: slider
                objectName: "parameters.slider"
                width: EaStyle.Sizes.sideBarContentWidth - EaStyle.Sizes.fontPixelSize * 14
                anchors.verticalCenter: parent.verticalCenter
                // A value symmetry holds and a descriptor row's value are not moved here (edi ADR-0019, ADR-0053).
                enabled: sliderRow.selected !== null && !sliderRow.selected.estimated && sliderRow.selected.refinable
                ToolTip.text: enabled ? "" : sliderRow.groupSelected ? qsTr("Pawley intensities have no single value to move") : sliderRow.selected === null ? qsTr("Select a parameter in the table first") : sliderRow.selected.estimated ? qsTr("Set by the automatic background: choose Manual to change it") : qsTr("Fixed by the structure's symmetry or a constraint")
                from: sliderRow.lower
                to: sliderRow.upper
                // Clamped here to the limits, so the value is read again when they move: the slider clamps to the
                // range it has at the time, and a value read before a newly current parameter's limits would stay
                // clamped to the old ones.
                value: sliderRow.selected ? Math.min(Math.max(sliderRow.selected.value, sliderRow.lower), sliderRow.upper) : 0
                // No thumb while no parameter is current, so the empty slider shows no value.
                handle.visible: sliderRow.selected !== null
                stepSize: sliderRow.selected ? sliderRow.selected.sliderStep : 0
                toolTipText: sliderRow.selected ? sliderRow.selected.fileValue : ""
                onMoved: sliderRow.selected.value = value
                // Held, the pattern charts keep their y range; let go, they fit it again (ProjectViewModel.adjusting).
                onPressedChanged: ApplicationInfo.parameterSliderPressed(false)
                // A slider gone while held (the page left) holds nothing.
                Component.onDestruction: ApplicationInfo.parameterSliderPressed(true)
            }
            EaElements.TextField {
                objectName: "parameters.slider.to"
                width: EaStyle.Sizes.fontPixelSize * 6
                readOnly: true
                enabled: sliderRow.selected !== null
                text: sliderRow.selected ? sliderRow.selected.displayText(slider.to) : ""
                ToolTip.text: enabled ? "" : qsTr("Select a parameter in the table first")
            }
        }
    }
}
