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
    // Some experiment holds measured data: without any, nothing can be fitted (edi ADR-0046), so the free column and its
    // header menu are hidden (the owner, 2026-10-27) and the free or fixed choice is disabled; the other filters stay
    // (the owner, 2026-11-02), and values stay editable. The disabled choice goes back to all parameters: one left from
    // a project with data showed one row under "Atomic displacement (4)" (the owner, 2026-10-27).
    readonly property bool measured: project !== null && project.fit.measured
    onMeasuredChanged: ApplicationInfo.parameterMeasuredChanged(false)
    // The selected parameter's row, kept as the filters and the rows change; -1 when it is not shown.
    property int selectedRow: -1
    property real tableViewportHeight: 0
    // The free column fits its title and the arrow after it, with a table column's padding (the owner, 2026-10-11),
    // and a font size more before the title, so it keeps clear of "max" (the owner, 2026-10-27).
    readonly property real freeGap: 0.25 * EaStyle.Sizes.fontPixelSize
    // The arrow ends where the right-aligned check boxes do: a check box's own padding and the table's spacing before
    // the column's edge (DataTable.padForFiller).
    readonly property real freeInset: 0.5 * EaStyle.Sizes.fontPixelSize + EaStyle.Sizes.tableColumnSpacing
    // The free title's word and arrow share one colour, each with the labels' own colour transition.
    property bool freeTitleHovered: false
    readonly property color freeTitleColor: !measured ? EaStyle.Colors.themeForegroundMinor : freeTitleHovered ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
    readonly property real freeColumnWidth: Math.ceil(freeTitleText.advanceWidth + freeGap + freeArrowText.advanceWidth + freeInset) + AppSizes.fieldSpacing * 2 + EaStyle.Sizes.fontPixelSize

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
            readonly property real third: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.inputSpacing) / 3

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
                            x: EaStyle.Sizes.fontPixelSize * 0.75
                            anchors.verticalCenter: parent.verticalCenter
                            maximumWidth: Math.max(1, parent.width - x)
                            textColor: EaStyle.Colors.themeForeground
                            segments: group.datablockSegments(datablockPicker.selected)
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
                            x: EaStyle.Sizes.fontPixelSize * 0.75
                            anchors.verticalCenter: parent.verticalCenter
                            maximumWidth: Math.max(1, parent.width - x)
                            textColor: EaStyle.Colors.themeForeground
                            segments: group.categorySegments(categoryPicker.selected)
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
                        ToolTip.text: enabled ? "" : qsTr("Free and fixed parameters apply once an experiment has measured data")
                        width: filters.third
                        model: titles
                        currentIndex: parameterFilter.variability
                        displayText: titles[parameterFilter.variability]
                        onModelChanged: ApplicationInfo.parameterPickerChanged(2, false, undefined)
                        onActivated: index => ApplicationInfo.parameterPickerChanged(2, true, index)
                    }
                }
            }
            Row {
                spacing: AppSizes.inputSpacing

                EaElements.TextField {
                    id: nameField
                    objectName: "parameters.nameFilter"
                    width: EaStyle.Sizes.sideBarContentWidth - AppSizes.inputSpacing - clearButton.width
                    placeholderText: qsTr("Filter by name")
                    text: parameterFilter.nameFilter
                    onTextEdited: parameterFilter.nameFilter = text
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
            // Reserve the controls below and half a row as a scroll cue (ADR-0029).
            maxRowCountShow: Math.max(1, Math.floor((group.tableViewportHeight - group.topPadding - group.bottomPadding - (filters.visible ? filters.height + AppSizes.groupContentSpacing : 0) - sliderRow.height - AppSizes.groupContentSpacing) / tableRowHeight - 1.5))
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
            onRowActivated: row => group.selected = parameterFilter.parameterAt(row)

            // A layout of its own (the owner, 2026-10-27): the name a little wider than its longest shown name, icons
            // and text; the units, min and max as their text; start, value, s.u. and change each fit their widest
            // text and share what is left; free at the right with a wider gap before it. Start and change are the
            // report's fit table columns, empty before a fit (owner record 2026-11-10).
            // Every number column is as wide as its widest text and its header, so no number loses digits or its
            // exponent; the name takes what is left. In a narrow sidebar the margins go first, then the min and max
            // columns, then the name down to a few characters; a row still too wide scrolls sideways (DataTable).
            readonly property var fittedColumns: [2, 3, 4, 5, 6, 7, 8]
            readonly property var rangeColumns: [7, 8]
            readonly property real freeWidth: group.measured ? group.freeColumnWidth : 0
            readonly property real nameMinimum: Math.min((fittedWidths[1] ?? 0) + EaStyle.Sizes.fontPixelSize, EaStyle.Sizes.fontPixelSize * 8)
            readonly property real fittedRoom: width - rowPadding * 2 - EaStyle.Sizes.borderThickness * 2 - EaStyle.Sizes.tableColumnSpacing * (group.measured ? 9 : 8) - numberColumnWidth - freeWidth - nameMinimum
            readonly property real fittedSum: fittedColumns.reduce((sum, column) => sum + (fittedWidths[column] ?? 0), 0)
            readonly property bool rangeShown: fittedRoom >= fittedSum
            readonly property var shownColumns: rangeShown ? fittedColumns : fittedColumns.filter(column => !rangeColumns.includes(column))
            readonly property real shownSum: shownColumns.reduce((sum, column) => sum + (fittedWidths[column] ?? 0), 0)
            readonly property real columnMargin: Math.max(0, Math.min(autoColumnPadding, Math.floor((fittedRoom - shownSum) / shownColumns.length)))
            function fittedColumn(column: int): real {
                return shownColumns.includes(column) ? Math.floor((fittedWidths[column] ?? 0) + columnMargin) : 0;
            }
            // The name takes the rest, set here rather than by the table's rule, so it follows only the table's width
            // and the measured texts, never the rows in view.
            readonly property real nameWidth: Math.max(EaStyle.Sizes.fontPixelSize * 4, Math.floor(fittedRoom + nameMinimum - shownColumns.reduce((sum, column) => sum + fittedColumn(column), 0)))
            readonly property var wantedColumns: [numberColumnWidth, nameWidth].concat(fittedColumns.map(column => fittedColumn(column))).concat(group.measured ? [freeWidth] : [])
            // Applied a moment later: new widths remake rows and measure them again, which would otherwise feed back
            // into the widths while they are being worked out.
            function applyColumns() {
                if (!ApplicationInfo.sameColumnWidths(columns, wantedColumns))
                    columns = wantedColumns;
            }
            onWantedColumnsChanged: Qt.callLater(applyColumns)
            Component.onCompleted: columns = wantedColumns

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("Name")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("Start")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("Value")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignLeft
                    text: ""
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("s.u.")
                }
                // Right-aligned on the arrows' right edge, as the change cells end there without the table's padding.
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    readonly property bool keepsAlignment: true
                    horizontalAlignment: Text.AlignRight
                    rightPadding: 0
                    text: qsTr("Change")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    visible: table.rangeShown
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("Min")
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    visible: table.rangeShown
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("Max")
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
                    visible: group.measured
                    horizontalAlignment: Text.AlignRight
                    rightPadding: freeArrow.width + group.freeGap + group.freeInset
                    color: group.freeTitleColor
                    text: qsTr("Free")

                    // Whether the click area that takes the header's input is enabled: it is reparented over the
                    // header, so the title's own `enabled` does not follow it.
                    readonly property bool interactionEnabled: freeArea.enabled
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
            }

            delegate: TableRow {
                id: row

                required property ParameterItem parameter
                required property string path
                required property string units
                required property real minimum
                required property real maximum

                objectName: `parameters.row.${index}`
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                // The iconified name on one centre line (edi ADR-0017 §8, §10), with the path in a tooltip on
                // hover.
                Item {
                    property int horizontalAlignment: Text.AlignLeft
                    objectName: `parameters.name.${row.index}`
                    // As wide as its icons and text, which the table fits the column to; a narrower column ends the name
                    // with an ellipsis, its full name in the tooltip.
                    implicitWidth: nameLine.fullWidth
                    height: parent.height
                    clip: true

                    IconLine {
                        id: nameLine
                        anchors.verticalCenter: parent.verticalCenter
                        maximumWidth: Math.max(1, parent.width)
                        minimumTextWidth: EaStyle.Sizes.fontPixelSize * 3
                        segments: ParameterNames.segments(row.parameter)
                    }
                    TapHandler {
                        acceptedButtons: Qt.RightButton
                        onTapped: valueCell.openContextMenu(valueCell)
                    }
                    HoverHandler {
                        id: nameHover
                    }
                    EaElements.ToolTip {
                        text: row.path
                        requested: nameHover.hovered
                    }
                }
                NumberLabel {
                    objectName: `parameters.start.${row.index}`
                    horizontalAlignment: Text.AlignRight
                    color: EaStyle.Colors.themeForegroundMinor
                    number: row.parameter ? row.parameter.startText : ""
                }
                ParameterCell {
                    id: valueCell
                    columnAlignment: Text.AlignRight
                    objectName: `parameters.value.${row.index}`
                    item: row.parameter
                    // An auto-mode background's values are the estimate's, as in the Experiment page's table.
                    locked: row.parameter ? row.parameter.estimated : false
                    onActiveFocusChanged: ApplicationInfo.finishUiEvent(11, undefined)
                }
                EaComponents.ListViewLabel {
                    elide: Text.ElideRight
                    color: EaStyle.Colors.themeForegroundMinor
                    horizontalAlignment: Text.AlignLeft
                    text: row.units
                }
                NumberLabel {
                    objectName: `parameters.su.${row.index}`
                    horizontalAlignment: Text.AlignRight
                    number: row.parameter ? (row.parameter.fileValue !== "" ? row.parameter.fileSu : row.parameter.hasUncertainty ? NumberText.error(row.parameter.uncertainty, 0, row.parameter.value) : "") : ""
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
                    property int horizontalAlignment: Text.AlignRight
                    readonly property bool keepsAlignment: true
                    readonly property real gap: EaStyle.Sizes.fontPixelSize * 0.25
                    implicitWidth: changePercent.implicitWidth + gap + changeArrow.width
                    height: parent.height
                    clip: true

                    EaElements.Label {
                        id: changeArrow
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        width: EaStyle.Sizes.fontPixelSize * 0.75
                        horizontalAlignment: Text.AlignHCenter
                        font.family: EaStyle.Fonts.iconsFamily
                        font.pixelSize: EaStyle.Sizes.fontPixelSize * 0.85
                        text: !row.parameter || row.parameter.changeDirection === 0 ? "" : row.parameter.changeDirection > 0 ? "arrow-up" : "arrow-down"
                    }
                    EaElements.Label {
                        id: changePercent
                        anchors.right: changeArrow.left
                        anchors.rightMargin: parent.gap
                        anchors.verticalCenter: parent.verticalCenter
                        text: row.parameter ? row.parameter.changeText : ""
                    }
                }
                NumberLabel {
                    visible: table.rangeShown
                    horizontalAlignment: Text.AlignRight
                    color: EaStyle.Colors.themeForegroundMinor
                    number: group.bound(row.minimum)
                    full: NumberText.plainFull(row.minimum)
                }
                NumberLabel {
                    visible: table.rangeShown
                    horizontalAlignment: Text.AlignRight
                    color: EaStyle.Colors.themeForegroundMinor
                    number: group.bound(row.maximum)
                    full: NumberText.plainFull(row.maximum)
                }
                // Enabled where a fit can vary the value, or while it is free so a flag set before a change can be
                // cleared; otherwise disabled, its tooltip naming why (edi ADR-0053).
                Item {
                    property int horizontalAlignment: Text.AlignHCenter
                    visible: group.measured
                    height: parent.height

                    EaComponents.ListViewCheckBox {
                        id: freeBox
                        anchors.fill: parent
                        horizontalAlignment: Text.AlignHCenter
                        objectName: `parameters.free.${row.index}`
                        enabled: row.parameter !== null && (row.parameter.fittable || row.parameter.free)
                        checked: row.parameter ? row.parameter.free : false
                        onToggled: row.parameter.free = checked
                        ToolTip.text: row.parameter && !row.parameter.fittable ? qsTr("Cannot be fitted: %1").arg(row.parameter.fitReason) : ""
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
            readonly property ParameterItem selected: group.selectedRow >= 0 ? group.selected : null
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
                ToolTip.text: enabled ? "" : sliderRow.selected === null ? qsTr("Select a parameter in the table first") : sliderRow.selected.estimated ? qsTr("Set by the automatic background: choose Manual to change it") : qsTr("Fixed by the structure's symmetry or a constraint")
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
