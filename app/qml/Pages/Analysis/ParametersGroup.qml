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
            EaElements.TextField {
                objectName: "parameters.nameFilter"
                width: (EaStyle.Sizes.sideBarContentWidth - AppSizes.fieldSpacing) / 2
                placeholderText: qsTr("Filter by name")
                onTextChanged: filter.nameFilter = text
            }
            EaElements.ComboBox {
                objectName: "parameters.variability"
                width: (EaStyle.Sizes.sideBarContentWidth - AppSizes.fieldSpacing) / 2
                model: [qsTr("All parameters"), qsTr("Free parameters"), qsTr("Fixed parameters")]
                onActivated: index => filter.variability = index
            }
        }

        EaComponents.TableView {
            id: table
            objectName: "parameters.list"
            // The original's (Fittables.qml): seven rows at the minimum window height, one more per row
            // of height the window adds, so the slider and Start fitting stay in view.
            maxRowCountShow: 7 + Math.max(0, Math.trunc((Window.height - EaStyle.Sizes.appWindowMinimumHeight) / EaStyle.Sizes.tableRowHeight))
            defaultInfoText: qsTr("No parameters")
            model: ParameterFilterModel {
                id: filter
                sourceModel: group.project ? group.project.parameters : null
            }

            header: EaComponents.TableViewHeader {
                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                    text: qsTr("No.")
                }
                EaComponents.TableViewLabel {
                    flexibleWidth: true
                    horizontalAlignment: Text.AlignLeft
                    text: qsTr("name")
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 5
                    text: qsTr("value")
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 2.5
                    text: qsTr("units")
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 3.5
                    text: qsTr("error")
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 3
                    text: qsTr("min")
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 3
                    text: qsTr("max")
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 2.5
                    text: qsTr("vary")
                }
            }

            delegate: EaComponents.TableViewDelegate {
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
                mouseArea.onPressed: group.selected = row.parameter

                EaComponents.TableViewLabel {
                    width: AppSizes.indexColumnWidth
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.index + 1
                }
                // The iconified name on one centre line (edi ADR-0017 §8, §10), with the path in a tooltip on
                // hover.
                Item {
                    objectName: `parameters.name.${row.index}`
                    width: table.headerLabelItems.length > 1 ? table.headerLabelItems[1].width : 0
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
                    width: EaStyle.Sizes.fontPixelSize * 5
                    item: row.parameter
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 2.5
                    color: EaStyle.Colors.themeForegroundMinor
                    text: row.units
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 3.5
                    text: row.parameter && row.parameter.hasUncertainty ? NumberText.error(row.parameter.uncertainty) : ""
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 3
                    color: EaStyle.Colors.themeForegroundMinor
                    text: group.bound(row.minimum)
                }
                EaComponents.TableViewLabel {
                    width: EaStyle.Sizes.fontPixelSize * 3
                    color: EaStyle.Colors.themeForegroundMinor
                    text: group.bound(row.maximum)
                }
                EaComponents.TableViewCheckBox {
                    objectName: `parameters.free.${row.index}`
                    width: EaStyle.Sizes.fontPixelSize * 2.5
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
