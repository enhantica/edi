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

    property real availableHeight: 0
    property ProjectViewModel project: null
    property ParameterItem selected: null

    function bound(value) {
        return value === Infinity ? "inf" : value === -Infinity ? "-inf" : String(value);
    }

    // A row is always selected while the table shows any (the owner, 2026-09-29; edi ADR-0017 §11): the first
    // shown row, when a project opens, when the experiment changes or when the filters hide the selected row;
    // a row the user selected stays selected while it is shown.
    function ensureSelection() {
        if (group.selected !== null && filter.shows(group.selected))
            return;
        group.selected = filter.parameterAt(0);
    }

    collapsible: false
    last: true
    objectName: "group.parameters"

    Component.onCompleted: group.ensureSelection()
    onProjectChanged: {
        group.selected = null;
        group.ensureSelection();
    }

    Connections {
        function onLayoutChanged() {
            group.ensureSelection();
        }
        function onModelReset() {
            group.ensureSelection();
        }
        function onRowsInserted() {
            group.ensureSelection();
        }
        function onRowsRemoved() {
            group.ensureSelection();
        }

        target: filter
    }
    Connections {
        function onCurrentExperimentIndexChanged() {
            group.ensureSelection();
        }

        target: group.project
    }
    Column {
        spacing: AppSizes.groupContentSpacing

        EaElements.GroupRow {
            id: filters

            EaElements.TextField {
                objectName: "parameters.nameFilter"
                placeholderText: qsTr("Filter by name")
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.fieldSpacing) / 3

                onTextChanged: filter.nameFilter = text
            }
            EaElements.ComboBox {
                model: [qsTr("All parameters"), qsTr("Free parameters"), qsTr("Fixed parameters")]
                objectName: "parameters.variability"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.fieldSpacing) / 3

                onActivated: index => filter.variability = index
            }
            EaElements.ComboBox {
                currentIndex: Math.max(0, filter.categories.indexOf(filter.categoryFilter))
                displayText: currentIndex === 0 ? qsTr("All categories") : currentText.replace(/_/g, " ")
                model: filter.categories
                objectName: "parameters.category"
                width: (EaStyle.Sizes.sideBarContentWidth - 2 * AppSizes.fieldSpacing) / 3

                onActivated: index => filter.categoryFilter = filter.categories[index]
            }
        }
        DataTable {
            id: table

            columnWidths: [numberColumnWidth, -1, EaStyle.Sizes.fontPixelSize * 5, textColumnWidth("units", ""), EaStyle.Sizes.fontPixelSize * 3.5, EaStyle.Sizes.fontPixelSize * 3, EaStyle.Sizes.fontPixelSize * 3, AppSizes.iconColumnWidth]
            defaultInfoText: qsTr("No parameters")
            // The original's (Fittables.qml): seven rows at the minimum window height, one more per row
            // of height the window adds, so the slider and Start fitting stay in view.
            maxRowCountShow: Math.max(1, Math.floor((group.availableHeight - group.topPadding - group.bottomPadding - filters.height - sliderRow.height - 2 * AppSizes.groupContentSpacing) / tableRowHeight - 1.5))
            objectName: "parameters.list"

            delegate: EaComponents.ListViewDelegate {
                id: row

                required property int index
                required property real maximum
                required property real minimum
                required property ParameterItem parameter
                required property string path
                required property string units

                // The selected row is highlighted, as the block tables' current row.
                color: group.selected === row.parameter ? EaStyle.Colors.tableHighlight : (index % 2 ? EaStyle.Colors.themeBackgroundHovered2 : EaStyle.Colors.themeBackgroundHovered1)
                objectName: `parameters.row.${index}`

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
                    clip: true
                    height: parent.height
                    objectName: `parameters.name.${row.index}`

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
                    item: row.parameter
                    objectName: `parameters.value.${row.index}`
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
                    checked: row.parameter ? row.parameter.free : false
                    objectName: `parameters.free.${row.index}`

                    onToggled: row.parameter.free = checked
                }
            }
            header: EaComponents.ListViewHeader {
                EaComponents.TableViewLabel {
                }
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
            model: ParameterFilterModel {
                id: filter

                sourceModel: group.project ? group.project.parameters : null
            }
        }

        // The slider of the selected row with its limits in a read-only box on each side (the original's
        // Fittables.qml slider row). The limits are set when a row is selected, when the value changes other
        // than by the slider, and when the slider is released, as there: a drag moves the value within them.
        // Shown at the base's default precision; the value keeps its full precision.
        Row {
            id: sliderRow

            property real lower: 0
            readonly property ParameterItem selected: group.selected
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
                function onValueChanged() {
                    if (!slider.pressed)
                        sliderRow.updateLimits();
                }

                target: sliderRow.selected
            }
            EaElements.TextField {
                enabled: sliderRow.selected !== null
                objectName: "parameters.slider.from"
                readOnly: true
                text: sliderRow.selected ? EaLogic.Utils.toDefaultPrecision(slider.from) : ""
                width: EaStyle.Sizes.fontPixelSize * 6
            }
            EaElements.Slider {
                id: slider

                anchors.verticalCenter: parent.verticalCenter
                enabled: sliderRow.selected !== null
                from: sliderRow.lower
                objectName: "parameters.slider"
                to: sliderRow.upper
                toolTipText: EaLogic.Utils.toDefaultPrecision(value)
                value: sliderRow.selected ? sliderRow.selected.value : 0
                width: EaStyle.Sizes.sideBarContentWidth - EaStyle.Sizes.fontPixelSize * 14

                onMoved: sliderRow.selected.value = value
                onPressedChanged: if (!pressed)
                    sliderRow.updateLimits()
            }
            EaElements.TextField {
                enabled: sliderRow.selected !== null
                objectName: "parameters.slider.to"
                readOnly: true
                text: sliderRow.selected ? EaLogic.Utils.toDefaultPrecision(slider.to) : ""
                width: EaStyle.Sizes.fontPixelSize * 6
            }
        }
    }
}
