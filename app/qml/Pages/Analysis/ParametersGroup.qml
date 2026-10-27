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
EaElements.GroupBox {
    id: group

    property ProjectViewModel project: null
    property ParameterItem selected: null
    // Some experiment holds measured data: without any, nothing can be fitted (edi ADR-0046), so the free column, its
    // header menu and the free or fixed filter are hidden (the owner, 2026-10-27); values stay editable.
    readonly property bool measured: project !== null && project.fit.measured
    // The selected parameter's row, kept as the filters and the rows change; -1 when it is not shown.
    property int selectedRow: -1
    property real tableViewportHeight: 0
    // The free column fits its title and the arrow after it, with a table column's padding (the owner, 2026-10-11).
    readonly property real freeGap: 0.25 * EaStyle.Sizes.fontPixelSize
    // The free title's word and arrow share one colour, each with the labels' own colour transition.
    property bool freeTitleHovered: false
    readonly property color freeTitleColor: !measured ? EaStyle.Colors.themeForegroundMinor : freeTitleHovered ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
    readonly property real freeColumnWidth: Math.ceil(freeTitleText.advanceWidth + freeGap + freeArrowText.advanceWidth) + AppSizes.fieldSpacing * 2

    TextMetrics {
        id: freeTitleText
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
        text: qsTr("free")
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
    last: true

    // A row is always selected while the table shows any (the owner, 2026-09-29; edi ADR-0017 §11): the first
    // shown row, when a project opens, when the experiment changes or when the filters hide the selected row;
    // a row the user selected stays selected while it is shown.
    function ensureSelection() {
        if (group.selected === null || !parameterFilter.shows(group.selected))
            group.selected = parameterFilter.parameterAt(0);
        group.selectedRow = parameterFilter.rowOf(group.selected);
    }
    onSelectedChanged: selectedRow = parameterFilter.rowOf(selected)

    onProjectChanged: {
        group.selected = null;
        group.ensureSelection();
    }
    Component.onCompleted: group.ensureSelection()

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
        if (!entry)
            return [];
        const title = {
            "text": entry.title,
            "elides": true
        };
        return entry.icon === "" ? [title] : [
            {
                "icon": entry.icon,
                "color": group.datablockColor(entry.blockKind, entry.blockName)
            },
            title];
    }
    function categorySegments(entry) {
        if (!entry)
            return [];
        const title = {
            "text": entry.title,
            "bold": entry.datablock,
            "elides": true
        };
        return entry.icon === "" ? [title] : [
            {
                "icon": entry.icon,
                "color": EaStyle.Colors.themeForegroundMinor
            },
            title];
    }

    // A datablock's colour, as its icon has it elsewhere: a structure's or an experiment's by its place in the
    // project's list.
    function datablockColor(kind, name) {
        const blocks = group.project ? (kind === "structure" ? group.project.structures : group.project.experiments) : null;
        let place = 0;
        for (let row = 0; blocks && row < blocks.count; ++row) {
            if (blocks.text(row, "name") === name) {
                place = row;
                break;
            }
        }
        return kind === "structure" ? AppColors.structure(place) : AppColors.experiment(place);
    }

    function bound(value) {
        return value === Infinity ? "inf" : value === -Infinity ? "-inf" : String(value);
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
                    onModelChanged: {
                        datablockPicker.follow();
                        Qt.callLater(datablockPicker.follow);
                    }
                    onActivated: index => {
                        parameterFilter.datablockFilter = parameterFilter.datablocks[index];
                        datablockPicker.follow();
                    }
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
                    onModelChanged: {
                        categoryPicker.follow();
                        Qt.callLater(categoryPicker.follow);
                    }
                    onActivated: index => {
                        parameterFilter.categoryFilter = parameterFilter.categories[index];
                        categoryPicker.follow();
                    }
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
                SearchableComboBox {
                    id: variabilityPicker
                    readonly property var titles: [qsTr("All parameters (%1)").arg(parameterFilter.variabilityCounts[0]), qsTr("Free parameters (%1)").arg(parameterFilter.variabilityCounts[1]), qsTr("Fixed parameters (%1)").arg(parameterFilter.variabilityCounts[2])]
                    function follow() {
                        currentIndex = Qt.binding(() => parameterFilter.variability);
                    }
                    objectName: "parameters.variability"
                    visible: group.measured
                    width: filters.third
                    model: titles
                    currentIndex: parameterFilter.variability
                    displayText: titles[parameterFilter.variability]
                    onModelChanged: {
                        variabilityPicker.follow();
                        Qt.callLater(variabilityPicker.follow);
                    }
                    onActivated: index => {
                        parameterFilter.variability = index;
                        variabilityPicker.follow();
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
            maxRowCountShow: Math.max(1, Math.floor((group.tableViewportHeight - group.topPadding - group.bottomPadding - filters.height - sliderRow.height - 2 * AppSizes.groupContentSpacing) / tableRowHeight - 1.5))
            defaultInfoText: qsTr("No parameters")
            sourceModel: ParameterFilterModel {
                id: parameterFilter
                sourceModel: group.project ? group.project.parameters : null
            }
            marksCurrentRow: true
            currentRow: group.selectedRow
            onRowActivated: row => group.selected = parameterFilter.parameterAt(row)

            // A layout of its own (the owner, 2026-10-27): the name as wide as its longest shown name, icons and text,
            // the units as their text, and value, s.u., min and max sharing the rest equally; free at the right.
            equalColumns: true
            columns: [numberColumnWidth, (fittedWidths[1] ?? 0) + autoColumnPadding, -1, (fittedWidths[3] ?? 0) + autoColumnPadding, -1, -1, -1].concat(group.measured ? [group.freeColumnWidth] : [])

            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("name")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("value")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: ""
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("s.u.")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("min")
                }
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("max")
                }
                // The title is a button, marked by the combo boxes' arrow: a click frees or fixes every row the
                // filters show, as one Undo step (the owner, 2026-10-11). The word and the arrow are centred together
                // over the checkboxes.
                EaComponents.ListViewLabel {
                    id: freeTitle
                    objectName: "parameters.freeHeader"
                    visible: group.measured
                    horizontalAlignment: Text.AlignHCenter
                    rightPadding: freeArrow.width + group.freeGap
                    color: group.freeTitleColor
                    text: qsTr("free")

                    // Whether the click area that takes the header's input is enabled: it is reparented over the
                    // header, so the title's own `enabled` does not follow it.
                    readonly property bool interactionEnabled: freeArea.enabled

                    EaElements.Label {
                        id: freeArrow
                        x: (freeTitle.width - freeTitle.rightPadding + freeTitle.contentWidth) / 2 + group.freeGap
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
                        onClicked: freeMenu.popup()
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
                    horizontalAlignment: Text.AlignHCenter
                    marksCurrentRow: true
                    text: row.index + 1
                }
                // The iconified name on one centre line (edi ADR-0017 §8, §10), with the path in a tooltip on
                // hover.
                Item {
                    property int horizontalAlignment: Text.AlignLeft
                    objectName: `parameters.name.${row.index}`
                    // As wide as its icons and text, which the table fits the column to.
                    implicitWidth: nameLine.implicitWidth
                    height: parent.height
                    clip: true

                    IconLine {
                        id: nameLine
                        anchors.verticalCenter: parent.verticalCenter
                        segments: ParameterNames.segments(row.parameter)
                    }
                    HoverHandler {
                        id: nameHover
                    }
                    EaElements.ToolTip {
                        text: row.path
                        visible: nameHover.hovered && EaGlobals.Vars.showToolTips
                    }
                }
                ParameterCell {
                    columnAlignment: Text.AlignRight
                    objectName: `parameters.value.${row.index}`
                    item: row.parameter
                    // An auto-mode background's values are the estimate's, as in the Experiment page's table.
                    locked: row.parameter ? row.parameter.estimated : false
                    onActiveFocusChanged: if (activeFocus)
                        group.selected = row.parameter
                }
                EaComponents.ListViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    horizontalAlignment: Text.AlignLeft
                    text: row.units
                }
                NumberLabel {
                    horizontalAlignment: Text.AlignRight
                    number: row.parameter ? (row.parameter.fileValue !== "" ? row.parameter.fileSu : row.parameter.hasUncertainty ? NumberText.error(row.parameter.uncertainty, 0, row.parameter.value) : "") : ""
                    narrow: row.parameter && row.parameter.hasUncertainty ? NumberText.ownUncertainty(row.parameter.uncertainty, row.parameter.value) : ""
                    full: row.parameter && row.parameter.hasUncertainty ? NumberText.plainFull(row.parameter.uncertainty) : ""
                }
                NumberLabel {
                    horizontalAlignment: Text.AlignRight
                    color: EaStyle.Colors.themeForegroundMinor
                    number: group.bound(row.minimum)
                    full: NumberText.plainFull(row.minimum)
                }
                NumberLabel {
                    horizontalAlignment: Text.AlignRight
                    color: EaStyle.Colors.themeForegroundMinor
                    number: group.bound(row.maximum)
                    full: NumberText.plainFull(row.maximum)
                }
                EaComponents.ListViewCheckBox {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `parameters.free.${row.index}`
                    visible: group.measured
                    checked: row.parameter ? row.parameter.free : false
                    onToggled: row.parameter.free = checked
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
                if (!selected) {
                    lower = 0;
                    upper = 1;
                    return;
                }
                const span = selected.sliderHalfWidth();
                lower = selected.value - span;
                upper = selected.value + span;
            }

            spacing: EaStyle.Sizes.fontPixelSize
            onSelectedChanged: updateLimits()

            Connections {
                target: sliderRow.selected
                function onValueChanged() {
                    if (!slider.pressed)
                        sliderRow.updateLimits();
                }
            }

            EaElements.TextField {
                objectName: "parameters.slider.from"
                width: EaStyle.Sizes.fontPixelSize * 6
                readOnly: true
                enabled: sliderRow.selected !== null
                text: sliderRow.selected ? sliderRow.selected.displayText(slider.from) : ""
            }
            EaElements.Slider {
                id: slider
                objectName: "parameters.slider"
                width: EaStyle.Sizes.sideBarContentWidth - EaStyle.Sizes.fontPixelSize * 14
                anchors.verticalCenter: parent.verticalCenter
                enabled: sliderRow.selected !== null && !sliderRow.selected.estimated
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
                onPressedChanged: {
                    if (group.project)
                        group.project.adjusting = pressed;
                    if (!pressed)
                        sliderRow.updateLimits();
                }
                // A slider gone while held (the page left) holds nothing.
                Component.onDestruction: {
                    if (pressed && group.project)
                        group.project.adjusting = false;
                }
            }
            EaElements.TextField {
                objectName: "parameters.slider.to"
                width: EaStyle.Sizes.fontPixelSize * 6
                readOnly: true
                enabled: sliderRow.selected !== null
                text: sliderRow.selected ? sliderRow.selected.displayText(slider.to) : ""
            }
        }
    }
}
