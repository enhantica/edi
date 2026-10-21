// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Logic as EaLogic
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
    // The selected parameter's row, kept as the filters and the rows change; -1 when it is not shown.
    property int selectedRow: -1
    property real tableViewportHeight: 0
    // The free column fits its title and the arrow after it, with a table column's padding (the owner, 2026-10-11).
    readonly property real freeGap: 0.25 * EaStyle.Sizes.fontPixelSize
    // The free title's word and arrow share one colour, each with the labels' own colour transition.
    property bool freeTitleHovered: false
    readonly property color freeTitleColor: freeTitleHovered ? EaStyle.Colors.themeAccent : EaStyle.Colors.themeForeground
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
        if (group.selected === null || !filter.shows(group.selected))
            group.selected = filter.parameterAt(0);
        group.selectedRow = filter.rowOf(group.selected);
    }
    onSelectedChanged: selectedRow = filter.rowOf(selected)

    onProjectChanged: {
        group.selected = null;
        group.ensureSelection();
    }
    Component.onCompleted: group.ensureSelection()

    Connections {
        target: filter
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

                SearchableComboBox {
                    id: datablockPicker
                    objectName: "parameters.datablock"
                    width: filters.third
                    model: filter.datablockGroups
                    textRole: "title"
                    searchThreshold: 1000
                    popup.width: Math.max(width, optionWidth + 3 * font.pixelSize)
                    currentIndex: Math.max(0, filter.datablocks.indexOf(filter.datablockFilter))
                    // The box follows the filter again after a choice, so a reset or a datablock that goes away shows.
                    onActivated: index => {
                        filter.datablockFilter = filter.datablocks[index];
                        currentIndex = Qt.binding(() => Math.max(0, filter.datablocks.indexOf(filter.datablockFilter)));
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
                                segments: datablockEntry.modelData.icon === "" ? [
                                    {
                                        text: datablockEntry.modelData.title
                                    }
                                ] : [
                                    {
                                        icon: datablockEntry.modelData.icon,
                                        color: group.datablockColor(datablockEntry.modelData.blockKind, datablockEntry.modelData.blockName)
                                    },
                                    {
                                        text: datablockEntry.modelData.title
                                    }
                                ]
                            }
                        }
                    }
                }
                SearchableComboBox {
                    id: categoryPicker
                    objectName: "parameters.category"
                    width: filters.third
                    model: filter.categoryGroups
                    textRole: "title"
                    searchThreshold: 1000
                    popup.width: Math.max(width, optionWidth + 3 * font.pixelSize)
                    currentIndex: Math.max(0, filter.categories.indexOf(filter.categoryFilter))
                    onActivated: index => {
                        filter.categoryFilter = filter.categories[index];
                        currentIndex = Qt.binding(() => Math.max(0, filter.categories.indexOf(filter.categoryFilter)));
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
                                segments: categoryEntry.modelData.icon === "" ? [
                                    {
                                        text: categoryEntry.modelData.title,
                                        bold: categoryEntry.modelData.datablock
                                    }
                                ] : [
                                    {
                                        icon: categoryEntry.modelData.icon,
                                        color: EaStyle.Colors.themeForegroundMinor
                                    },
                                    {
                                        text: categoryEntry.modelData.title,
                                        bold: categoryEntry.modelData.datablock
                                    }
                                ]
                            }
                        }
                    }
                }
                SearchableComboBox {
                    objectName: "parameters.variability"
                    width: filters.third
                    model: [qsTr("All parameters (%1)").arg(filter.variabilityCounts[0]), qsTr("Free parameters (%1)").arg(filter.variabilityCounts[1]), qsTr("Fixed parameters (%1)").arg(filter.variabilityCounts[2])]
                    currentIndex: filter.variability
                    onActivated: index => {
                        filter.variability = index;
                        currentIndex = Qt.binding(() => filter.variability);
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
                    text: filter.nameFilter
                    onTextEdited: filter.nameFilter = text
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
                    onClicked: filter.clearFilters()
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
                id: filter
                sourceModel: group.project ? group.project.parameters : null
            }
            marksCurrentRow: true
            currentRow: group.selectedRow

            columnWidths: [numberColumnWidth, -1, EaStyle.Sizes.fontPixelSize * 5, textColumnWidth("units", ""), EaStyle.Sizes.fontPixelSize * 3.5, EaStyle.Sizes.fontPixelSize * 3, EaStyle.Sizes.fontPixelSize * 3, group.freeColumnWidth]

            header: EaComponents.ListViewHeader {
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("name")
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("value")
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: ""
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("s.u.")
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("min")
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignRight
                    text: qsTr("max")
                }
                // The title is a button, marked by the combo boxes' arrow: a click frees or fixes every row the
                // filters show, as one Undo step (the owner, 2026-10-11). The word and the arrow are centred together
                // over the checkboxes.
                EaComponents.TableViewLabel {
                    id: freeTitle
                    objectName: "parameters.freeHeader"
                    horizontalAlignment: Text.AlignHCenter
                    rightPadding: freeArrow.width + group.freeGap
                    color: group.freeTitleColor
                    text: qsTr("free")

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
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onContainsMouseChanged: group.freeTitleHovered = containsMouse
                        onClicked: freeMenu.popup()
                    }
                    FreeHeaderMenu {
                        id: freeMenu
                        project: group.project
                        filter: filter
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
                TapHandler {
                    onTapped: group.selected = row.parameter
                }

                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                // The iconified name on one centre line (edi ADR-0017 §8, §10), with the path in a tooltip on
                // hover.
                Item {
                    property int horizontalAlignment: Text.AlignLeft
                    objectName: `parameters.name.${row.index}`
                    height: parent.height
                    clip: true

                    IconLine {
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
                EaComponents.TableViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    horizontalAlignment: Text.AlignLeft
                    text: row.units
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignRight
                    text: row.parameter && row.parameter.hasUncertainty ? NumberText.error(row.parameter.uncertainty, 0, row.parameter.value) : ""
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignRight
                    color: EaStyle.Colors.themeForegroundMinor
                    text: group.bound(row.minimum)
                }
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignRight
                    color: EaStyle.Colors.themeForegroundMinor
                    text: group.bound(row.maximum)
                }
                EaComponents.TableViewCheckBox {
                    horizontalAlignment: Text.AlignHCenter
                    objectName: `parameters.free.${row.index}`
                    checked: row.parameter ? row.parameter.free : false
                    onToggled: row.parameter.free = checked
                }
            }
        }

        // The slider of the selected row with its limits in a read-only box on each side (the original's
        // Fittables.qml slider row). The limits are set when a row is selected, when the value changes other
        // than by the slider, and when the slider is released, as there: a drag moves the value within them.
        // Shown at the base's default precision; the value keeps its full precision.
        Row {
            id: sliderRow

            readonly property ParameterItem selected: group.selected
            property real lower: 0
            property real upper: 1

            function updateLimits() {
                if (!selected)
                    return;
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
                text: sliderRow.selected ? EaLogic.Utils.toDefaultPrecision(slider.from) : ""
            }
            EaElements.Slider {
                id: slider
                objectName: "parameters.slider"
                width: EaStyle.Sizes.sideBarContentWidth - EaStyle.Sizes.fontPixelSize * 14
                anchors.verticalCenter: parent.verticalCenter
                enabled: sliderRow.selected !== null && !sliderRow.selected.estimated
                from: sliderRow.lower
                to: sliderRow.upper
                value: sliderRow.selected ? sliderRow.selected.value : 0
                toolTipText: EaLogic.Utils.toDefaultPrecision(value)
                onMoved: sliderRow.selected.value = value
                onPressedChanged: if (!pressed)
                    sliderRow.updateLimits()
            }
            EaElements.TextField {
                objectName: "parameters.slider.to"
                width: EaStyle.Sizes.fontPixelSize * 6
                readOnly: true
                enabled: sliderRow.selected !== null
                text: sliderRow.selected ? EaLogic.Utils.toDefaultPrecision(slider.to) : ""
            }
        }
    }
}
