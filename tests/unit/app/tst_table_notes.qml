// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents
import edi.app
import "UiInteraction.js" as Ui

Item {
    id: surface
    width: 1100
    height: 900
    ListModel {
        id: scrollRows
    }
    Component {
        id: scrollComponent
        DataTable {
            width: 800
            maxRowCountShow: 4
            sourceModel: scrollRows
            columnWidths: [-1]
            header: EaComponents.ListViewHeader {
                TextCell {
                    text: "Value"
                }
            }
            delegate: EaComponents.ListViewDelegate {
                required property string label
                TextCell {
                    text: label
                }
            }
        }
    }
    Component {
        id: experimentsComponent
        ExperimentsGroup {
            width: 800
        }
    }
    Component {
        id: backgroundComponent
        BackgroundGroup {
            width: 800
        }
    }
    Component {
        id: atomsComponent
        AtomSitesGroup {
            width: 800
        }
    }
    Component {
        id: parametersComponent
        ParametersGroup {
            width: 800
        }
    }
    TestCase {
        name: "TableNotes"
        when: windowShown
        function init() {
            failOnWarning(/.*/);
            Session.closeProject();
        }
        function cleanup() {
            Session.closeProject();
        }
        function test_experiment_fit_column_retains_icon_and_word_tooltip() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), "The supplied experiment opens for its fit status column");
            const group = createTemporaryObject(experimentsComponent, surface, {
                project: Session.project
            });
            verify(group !== null && waitForPolish(group), "The experiment fit column completes actual layout");
            const cell = Ui.find(group, "experiments.fit.0");
            verify(cell !== null, "The actual experiment row exposes its fit status cell");
            compare(cell.toolTip, "Not fitted", "The unfitted experiment names its state in the tooltip");
            compare(cell.ring, true, "An unfitted experiment retains the fit-family hollow circle");
            verify(!Ui.text(cell).includes("Not fitted"), "The Fit column keeps the status word in the tooltip");
        }
        function test_scrollable_tables_expose_half_of_the_next_live_row() {
            scrollRows.clear();
            for (let i = 0; i < 12; ++i)
                scrollRows.append({
                    label: "row " + i
                });
            const table = createTemporaryObject(scrollComponent, surface);
            verify(table !== null, "The actual scrollable table is instantiated");
            verify(waitForPolish(table), "The scrollable table completes layout");
            let next = null;
            tryVerify(() => {
                next = table.itemAtIndex(4);
                return next !== null;
            }, 2000, "The next delegate exists in the actual viewport");
            const top = next.mapToItem(table, 0, 0).y;
            const visibleFraction = (table.height - top) / next.height;
            verify(Math.abs(visibleFraction - 0.5) < 0.06, "The real clipped delegate shows about half its height as the scrolling cue");
        }
        function test_template_marker_follows_its_filename() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_scan-3f"), Session.lastError);
            const group = createTemporaryObject(experimentsComponent, surface, {
                project: Session.project
            });
            verify(group !== null, "The declared scan opens its actual experiment table");
            verify(waitForPolish(group), "The scan table completes layout");
            const marker = Ui.find(group, "experiments.template." + Session.project.templateIndex);
            verify(marker !== null, "The template dataset has its visible marker");
            const siblings = marker.parent.children;
            let filename = null;
            for (const child of siblings) {
                if (child !== marker && typeof child.text === "string" && child.text !== "" && child.visible && typeof child.contentWidth === "number")
                    filename = child;
            }
            verify(filename !== null, "The marker shares a row with the actual filename text");
            const gap = marker.x - filename.x - filename.contentWidth;
            verify(gap >= 0 && gap <= 2 * AppSizes.fieldSpacing, "The template marker immediately follows the filename instead of preceding it or drifting to the edge");
        }
        function test_number_thresholds_data() {
            return [
                {
                    tag: "below-large",
                    value: 999999,
                    text: "999999"
                },
                {
                    tag: "at-large",
                    value: 1000000,
                    text: "1.000e6"
                },
                {
                    tag: "at-small",
                    value: 0.0001,
                    text: "0.0001"
                },
                {
                    tag: "below-small",
                    value: 0.00009999,
                    text: "9.999e-5"
                },
                {
                    tag: "zero",
                    value: 0,
                    text: "0"
                },
                {
                    tag: "negative-large",
                    value: -1000000,
                    text: "-1.000e6"
                },
                {
                    tag: "negative-small",
                    value: -0.00001,
                    text: "-1.000e-5"
                },
                {
                    tag: "owner-intensity",
                    value: 22900000,
                    text: "2.290e7"
                }
            ];
        }
        function test_number_thresholds(data) {
            compare(NumberText.parameter(data.value, 0, 64), data.text, "Scientific display uses the owner's magnitude thresholds and four significant digits");
            compare(NumberText.parameter(data.value, 0, 3), data.text, "The displayed precision remains the same when the cell clips at its edge");
        }
        function test_scientific_uncertainty_editing_and_clipping() {
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/table_display")), Session.lastError);
            const group = createTemporaryObject(backgroundComponent, surface, {
                experiment: Session.project.currentExperiment
            });
            verify(group !== null, "The declared scientific-number fixture opens its actual background table");
            verify(waitForPolish(group), "The scientific-number table completes layout");
            const cell = Ui.find(group, "background.intensity.0");
            verify(cell !== null && cell.item.hasUncertainty, "The independent fixture supplies both a value and its s.u.");
            compare(cell.value, "2.290e7", "The value uses four significant digits in scientific notation");
            compare(cell.error, "0.010e7", "The s.u. uses the same exponent as its value");
            cell.forceActiveFocus();
            tryCompare(cell, "text", "22900000", 2000, "Editing exposes the complete numerical value");
            cell.focus = false;
            tryCompare(cell, "cursorPosition", 0, 2000, "An unfocused number is visible from its start");
            compare(cell.horizontalAlignment, Text.AlignLeft, "A long number clips its end while retaining its beginning");
        }
        function test_atom_columns_use_content_width_and_equal_numeric_space() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), Session.lastError);
            const group = createTemporaryObject(atomsComponent, surface, {
                structure: Session.project.currentStructure
            });
            verify(group !== null, "The actual atom table is instantiated");
            verify(waitForPolish(group), "The actual atom table completes layout");
            const table = Ui.find(group, "atomSites.list");
            verify(table !== null, "The actual atom table remains exposed");
            const widths = table.resolvedColumnWidths;
            compare(widths.length, 9, "The atom table retains every scientific and action column");
            compare(widths[0], table.numberColumnWidth, "Numbering takes its measured content width");
            for (const column of [4, 5, 7])
                compare(widths[column], widths[3], "Coordinates and occupancy share the remaining width equally");
            verify(widths[0] < widths[3], "Numbering leaves room for scientific values");
            group.width = 1000;
            verify(waitForPolish(group), "The wider sidebar completes layout");
            compare(table.resolvedColumnWidths[0], widths[0], "Numbering stays fixed as the sidebar widens");
            verify(table.resolvedColumnWidths[3] > widths[3], "Main columns receive the added sidebar width");
        }
        function test_analysis_filter_units_heading_and_free_colour() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), Session.lastError);
            const group = createTemporaryObject(parametersComponent, surface, {
                project: Session.project
            });
            verify(group !== null, "The actual analysis sidebar is instantiated");
            verify(waitForPolish(group), "The actual analysis sidebar completes layout");
            const picker = Ui.find(group, "parameters.category");
            verify(picker !== null && picker.count > 1, "The category picker exposes several scientific categories");
            const table = Ui.find(group, "parameters.list");
            verify(table !== null && table.count > 0, "Analysis retains a populated table after adding the category filter");
            verify(!Ui.text(table.headerItem).split(/\s+/).includes("Units"), "The analysis units column has no Units heading");
            let freeCell = null;
            for (let i = 0; i < Math.min(table.count, 12); ++i) {
                const cell = Ui.find(group, "parameters.value." + i);
                if (cell && cell.item && cell.item.refinable && cell.item.fittable) {
                    cell.item.free = true;
                    freeCell = cell;
                    break;
                }
            }
            verify(freeCell !== null, "The fixture exposes a fittable parameter cell");
            compare(freeCell.color, EaStyle.Colors.chartForegroundsExtra[1], "A free parameter uses the residual green");
            verify(freeCell.font.bold, "A free parameter remains bold as well as green");
        }
    }
}
