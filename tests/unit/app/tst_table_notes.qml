// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import ReportAcceptance 1.0
import "ExampleProjects.js" as Examples
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents
import edi.app
import "UiInteraction.js" as Ui
import "TableBoundary.js" as Boundary

Item {
    id: surface
    width: 1100
    height: 900
    TextMetrics {
        id: numberInk
    }
    FontMetrics {
        id: fittedMetrics
        font.family: EaStyle.Fonts.fontFamily
        font.pixelSize: EaStyle.Sizes.fontPixelSize
    }
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
                required property int index
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
        id: test
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
            verify(Examples.bundled(this, Session, "pd-neut-cwl_cosio-d20"), "The supplied experiment opens for its fit status column");
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
            Boundary.check(test, table, next, surface);
        }
        function test_template_marker_follows_its_filename() {
            const root = SettingsProof.copyProject(Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project"));
            const file = "all594791.dat";
            verify(SettingsProof.fileFacts(root, "experiments/d20_scan/" + file).bytes > 0, "The positive template names an actual independently supplied scan dataset");
            const analysis = SettingsProof.text(root, "analysis/analysis.edi");
            verify(analysis.length > 0 && !analysis.includes("_sequential_fit.template_file"), "The original disposable scan source has no designated template");
            verify(SettingsProof.write(root, "analysis/analysis.edi", analysis + "\n_sequential_fit.template_file " + file + "\n"), "The positive source explicitly designates its actual template file before loading");
            verify(Session.openProject(root), Session.lastError);
            verify(Session.project.scan && Session.project.templateIndex >= 0, "The real loaded scan resolves its designated template index");
            compare(Session.project.currentExperimentIndex, Session.project.templateIndex, "The actual designated dataset is shown before querying its marker");
            const group = createTemporaryObject(experimentsComponent, surface, {
                project: Session.project
            });
            verify(group !== null, "The declared scan opens its actual experiment table");
            verify(surface.Window.window !== null && waitForPolish(surface.Window.window), "The scan table completes layout");
            const marker = Ui.find(group, "experiments.template." + Session.project.templateIndex);
            verify(marker !== null, "The template dataset has its visible marker");
            const siblings = marker.parent.children;
            let filename = null;
            for (const child of siblings) {
                if (child !== marker && typeof child.text === "string" && child.text !== "" && child.visible && typeof child.contentWidth === "number")
                    filename = child;
            }
            verify(filename !== null, "The marker shares a row with the actual filename text");
            compare(filename.text, file, "The marker belongs to the exact source-designated dataset filename");
            tryCompare(marker, "color", EaStyle.Colors.themeAccent, 2000, "The actual designated template marker settles to the declared accent");
            const gap = marker.x - filename.x - filename.contentWidth;
            verify(gap >= 0 && gap <= 2 * AppSizes.fieldSpacing, "The template marker immediately follows the filename instead of preceding it or drifting to the edge");
        }
        function test_scan_without_a_designated_template_has_no_template_marker() {
            verify(Examples.fixture(Session, "pd-neut-cwl_cosio-d20_scan-3f"), Session.lastError);
            compare(Session.project.templateIndex, -1, "Opening the first dataset does not designate it as a template");
            const group = createTemporaryObject(experimentsComponent, surface, {
                project: Session.project
            });
            verify(group !== null && waitForPolish(group), "The original unmarked scan reaches its real table");
            const table = Ui.find(group, "experiments.list");
            verify(table !== null && table.count === 3, "All original scan dataset rows remain in the negative fixture");
            for (let row = 0; row < table.count; ++row)
                compare(Ui.find(group, "experiments.template." + row), null, "No dataset falsely advertises an undeclared template marker");
        }
        function test_number_thresholds_data() {
            return [
                {
                    tag: "below-large",
                    value: 999999,
                    text: "999999",
                    capped: "1000000"
                },
                {
                    tag: "at-large",
                    value: 1000000,
                    text: "1.000e6",
                    capped: "1.000e6"
                },
                {
                    tag: "at-small",
                    value: 0.0001,
                    text: "0.0001",
                    capped: "0.0001"
                },
                {
                    tag: "below-small",
                    value: 0.00009999,
                    text: "9.999e-5",
                    capped: "9.999e-5"
                },
                {
                    tag: "zero",
                    value: 0,
                    text: "0",
                    capped: "0"
                },
                {
                    tag: "negative-large",
                    value: -1000000,
                    text: "-1.000e6",
                    capped: "-1.000e6"
                },
                {
                    tag: "negative-small",
                    value: -0.00001,
                    text: "-1.000e-5",
                    capped: "-1.000e-5"
                },
                {
                    tag: "owner-intensity",
                    value: 22900000,
                    text: "2.290e7",
                    capped: "2.290e7"
                }
            ];
        }
        function test_number_thresholds(data) {
            compare(NumberText.parameter(data.value, 0, 64), data.text, "Scientific display uses the owner's magnitude thresholds and four significant digits");
            compare(NumberText.parameter(data.value, 0, 3), data.capped, "The third argument is a significant-digit cap, independently of viewport fitting");
        }
        function test_explicit_digit_caps_data() {
            return [
                {tag: "positive-three", value: 12345.6, digits: 3, text: "12300"},
                {tag: "negative-three", value: -12345.6, digits: 3, text: "-12300"},
                {tag: "positive-five", value: 12345.6, digits: 5, text: "12346"},
                {tag: "small-three", value: 0.00123456, digits: 3, text: "0.00123"},
                {tag: "zero", value: 0, digits: 3, text: "0"},
                {tag: "carry-one", value: 999999, digits: 1, text: "1000000"}
            ];
        }
        function test_explicit_digit_caps(data) {
            compare(NumberText.parameter(data.value, 0, data.digits), data.text, "The original no-SU decimal cap rounds the authored sign, scale and carry cases");
        }
        function test_pixel_room_preserves_all_literal_digits_through_the_actual_fitted_seam() {
            const text = "999999", narrow = "9.99999e5";
            const advance = fittedMetrics.advanceWidth(text);
            verify(advance > 1, "The actual font ink overflows the strictly positive narrow room");
            compare(NumberText.fitted(text, Math.ceil(advance) + 1, fittedMetrics, narrow), text, "A roomy fitted display preserves the complete original literal");
            compare(NumberText.fitted(text, 1, fittedMetrics, narrow), narrow, "Positive-room fitting changes notation while preserving every literal significant digit");
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
            compare(cell.item.fileValue, "22900000", "The supplied pair has its independently specified written value");
            compare(cell.item.fileSu, "100000", "The supplied IUCr99 uncertainty has its independent written value");
            compare(cell.error, cell.item.fileSu, "The editable cell's menu retains the canonical written uncertainty");
            numberInk.font = cell.font;
            numberInk.text = "22900000";
            const fits = numberInk.advanceWidth <= cell.width - cell.leftPadding - cell.rightPadding;
            compare(cell.text, fits ? "22900000" : "2.290e7", "The actual table text follows independent ink fit while retaining the written pair's meaningful last digit");
            cell.forceActiveFocus();
            tryCompare(cell, "text", "22900000", 2000, "Editing exposes the complete numerical value");
            cell.focus = false;
            tryCompare(cell, "cursorPosition", 0, 2000, "An unfocused number is visible from its start");
        }
        function test_analysis_filter_units_heading_and_free_colour() {
            verify(Examples.bundled(this, Session, "pd-neut-cwl_cosio-d20"), Session.lastError);
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
            const owner = Session.project, held = freeCell.item;
            console.info("TableNotes free-colour precondition", JSON.stringify({
                calculating: owner.calculating, free: held.free, fittable: held.fittable,
                refinable: held.refinable, enabled: freeCell.enabled, readOnly: freeCell.readOnly,
                bold: freeCell.font.bold, color: String(freeCell.color)
            }));
            verify(held.free && held.fittable && held.refinable && freeCell.enabled && !freeCell.readOnly, "The same live free/fittable control reaches its enabled editable colour rule");
            tryCompare(freeCell, "color", EaStyle.Colors.green, 2000, "A free parameter settles through its normal colour Behavior to the declared base green");
            verify(Session.project === owner && group.project === owner && freeCell.item === held && held.free && held.fittable && held.refinable, "Colour settlement observes the same current model and live free/fittable parameter item");
            verify(freeCell.font.bold, "A free parameter remains bold as well as green");
        }
    }
}
