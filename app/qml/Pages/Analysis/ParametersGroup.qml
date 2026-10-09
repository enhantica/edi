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
    property real tableViewportHeight: 0

    objectName: "group.parameters"
    collapsible: false
    last: true

    // A row is always selected while the table shows any (the owner, 2026-09-29; edi ADR-0017 §11): the first
    // shown row, when a project opens, when the experiment changes or when the filters hide the selected row;
    // a row the user selected stays selected while it is shown.
    function ensureSelection() {
        if (group.selected !== null && filter.shows(group.selected))
            return;
        group.selected = filter.parameterAt(0);
    }

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

    function bound(value) {
        return value === Infinity ? "inf" : value === -Infinity ? "-inf" : String(value);
    }

    Column {
        spacing: AppSizes.groupContentSpacing

        EaElements.GroupRow {
            id: filters
            EaElements.TextField {
                objectName: "parameters.nameFilter"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.fieldSpacing) / 3
                placeholderText: qsTr("Filter by name")
                onTextChanged: filter.nameFilter = text
            }
            EaElements.ComboBox {
                objectName: "parameters.variability"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.fieldSpacing) / 3
                model: [qsTr("All parameters"), qsTr("Free parameters"), qsTr("Fixed parameters")]
                onActivated: index => filter.variability = index
            }
            EaElements.ComboBox {
                objectName: "parameters.category"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.fieldSpacing) / 3
                model: filter.categories
                currentIndex: Math.max(0, filter.categories.indexOf(filter.categoryFilter))
                displayText: currentIndex === 0 ? qsTr("All categories") : currentText.replace(/_/g, " ")
                onActivated: index => filter.categoryFilter = filter.categories[index]
            }
        }

        DataTable {
            id: table
            objectName: "parameters.list"
            // Reserve the controls below and half a row as a scroll cue (ADR-0028).
            maxRowCountShow: Math.max(1, Math.floor((group.tableViewportHeight - group.topPadding - group.bottomPadding - filters.height - sliderRow.height - 2 * AppSizes.groupContentSpacing) / tableRowHeight - 1.5))
            defaultInfoText: qsTr("No parameters")
            model: ParameterFilterModel {
                id: filter
                sourceModel: group.project ? group.project.parameters : null
            }

            columnWidths: [numberColumnWidth, -1, EaStyle.Sizes.fontPixelSize * 5, textColumnWidth("units", ""), EaStyle.Sizes.fontPixelSize * 3.5, EaStyle.Sizes.fontPixelSize * 3, EaStyle.Sizes.fontPixelSize * 3, AppSizes.iconColumnWidth]

            header: EaComponents.ListViewHeader {
                EaComponents.TableViewLabel {}
                EaComponents.TableViewLabel {
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("name")
                }
                EaComponents.TableViewLabel {
                    text: qsTr("value")
                }
                EaComponents.TableViewLabel {
                    text: ""
                }
                EaComponents.TableViewLabel {
                    text: qsTr("error")
                }
                EaComponents.TableViewLabel {
                    text: qsTr("min")
                }
                EaComponents.TableViewLabel {
                    text: qsTr("max")
                }
                EaComponents.TableViewLabel {
                    text: qsTr("vary")
                }
            }

            delegate: EaComponents.ListViewDelegate {
                id: row

                required property int index
                required property ParameterItem parameter
                required property string path
                required property string units
                required property real minimum
                required property real maximum

                objectName: `parameters.row.${index}`
                // The selected row is highlighted, as the block tables' current row.
                color: group.selected === row.parameter ? EaStyle.Colors.tableHighlight : (index % 2 ? EaStyle.Colors.themeBackgroundHovered2 : EaStyle.Colors.themeBackgroundHovered1)
                TapHandler {
                    onTapped: group.selected = row.parameter
                }

                EaComponents.TableViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                // The iconified name on one centre line (edi ADR-0017 §8, §10), with the path in a tooltip on
                // hover.
                Item {
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
                    objectName: `parameters.value.${row.index}`
                    item: row.parameter
                    onActiveFocusChanged: if (activeFocus)
                        group.selected = row.parameter
                }
                EaComponents.TableViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    horizontalAlignment: Text.AlignLeft
                    text: row.units
                }
                EaComponents.TableViewLabel {
                    text: row.parameter && row.parameter.hasUncertainty ? NumberText.error(row.parameter.uncertainty) : ""
                }
                EaComponents.TableViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    text: group.bound(row.minimum)
                }
                EaComponents.TableViewLabel {
                    color: EaStyle.Colors.themeForegroundMinor
                    text: group.bound(row.maximum)
                }
                EaComponents.TableViewCheckBox {
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
                enabled: sliderRow.selected !== null
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
