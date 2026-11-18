import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import PatternPolishAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import "ApprovedPalette.js" as Approved
import "../../fixtures/pattern_styles/input.js" as PowderInput

Item {
    id: surface
    width: 1200
    height: 900
    Component {
        id: chartFactory
        SingleCrystalChart {
            width: 1100
            height: 800
            shown: true
        }
    }
    Component {
        id: pageFactory
        ExperimentPage {
            current: true
            visible: true
            width: 1200
            height: 900
        }
    }
    TestCase {
        id: test
        name: "SingleCrystalPattern"
        when: windowShown
        visible: true
        property var scene
        property var pattern
        property var page
        property var root
        property var mainView
        readonly property var reference: JSON.parse(SettingsProof.repoText("tests/fixtures/single_crystal_pattern/reference.json"))
        function cleanup() {
            if (page)
                page.destroy();
            if (scene && !mainView)
                scene.destroy();
            if (mainView)
                mainView.destroy();
            mainView = null;
            page = scene = pattern = null;
            Session.closeProject();
        }
        function click(control) {
            verify(control !== null && control.visible && control.enabled, "The single-crystal action uses a real visible enabled control");
            Ui.scrollIntoView(Ui.target(control));
            verify(waitForPolish(surface), "Single-crystal input follows a finished real layout");
            const at = Ui.clickPoint(Ui.target(control));
            verify(at !== null, "The single-crystal control has an exposed pointer target");
            mouseClick(Ui.target(control), at.x, at.y);
            verify(waitForRendering(surface), "The actual single-crystal control renders after input");
        }
        function choose(control, predicate) {
            verify(control !== null && control.enabled && control.count > 0, "The requested single-crystal choice is a real populated selector");
            const index = Array.from({
                length: control.count
            }, (_, i) => control.textAt(i)).findIndex(predicate);
            verify(index >= 0, "The real single-crystal selector offers the required quantity or style");
            // Existing defaults need no popup round-trip; changed choices still use real input.
            if (control.currentIndex === index)
                return;
            click(control);
            tryCompare(control.popup, "opened", true, 1000, "Actual input opens the single-crystal choices");
            const list = control.popup.contentItem;
            list.positionViewAtIndex(index, ListView.Contain);
            tryVerify(() => list.itemAtIndex(index) && Ui.exposed(list.itemAtIndex(index)), 1000, "The requested single-crystal choice is visible in its actual popup");
            const entry = list.itemAtIndex(index);
            mouseClick(entry, entry.width / 2, entry.height / 2);
            tryCompare(control.popup, "visible", false, 1000, "The real single-crystal choice closes its popup");
        }
        function open(magnetic, simulation = false, relations = "") {
            Preferences.resetToDefaults();
            root = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/legacy_structure_project/compact-project"));
            verify(SettingsProof.write(root, "structures/cosio.edi", SettingsProof.repoText("tests/fixtures/single_crystal_pattern/" + (magnetic ? "magnetic" : "nuclear") + ".edi")), "The actor supplies its independently declared single-atom structure");
            verify(SettingsProof.write(root, "experiments/d20.edi", SettingsProof.repoText("tests/fixtures/single_crystal_pattern/" + (simulation ? "simulation" : "measured") + ".edi")), "The actor supplies its independently declared single-crystal input");
            verify(SettingsProof.write(root, "analysis/analysis.edi", "_edi.schema_version 3\n_fitting_mode.type single\n" + relations), "The single-atom input declares only its intended current moment relations");
            verify(Session.openProject(root), "The real project loader opens the independent single-crystal input");
            tryCompare(Session.project, "calculating", false, 10000, "The actual single-crystal calculation finishes before plotting");
            scene = chartFactory.createObject(surface, {
                experiment: Session.project.currentExperiment,
                project: Session.project
            });
            verify(scene !== null && waitForPolish(scene) && waitForRendering(scene), "The production single-crystal chart renders its actual project");
        }
        function axis(name) {
            const selectors = Render.descendants(scene).filter(item => item.visible && /(?:singleCrystal\.toolbar\.xaxis|chart\.toolbar\.singleCrystalXAxis)$/.test(item.objectName));
            verify(selectors.length > 0, "Single-crystal plotting exposes a real physical-x selector");
            choose(selectors[selectors.length - 1], text => name === "q" ? /\bQ\b/.test(text) : /sin/.test(text));
            tryVerify(() => {
                pattern = Render.descendants(scene).find(item => item.objectName === "chart" && item.visible && item.singleCrystal === true);
                return pattern !== undefined;
            }, 2000, "The selected reciprocal quantity renders through the production Pattern chart");
        }
        function style(squared) {
            choose(findChild(pattern, "chart.toolbar.singleCrystalQuantity"), text => squared ? text === "F²" : text === "F");
            choose(findChild(pattern, "chart.toolbar.measuredStyle"), text => text === "Bars");
        }
        function vertices(series) {
            return Array.from({
                length: series.count
            }, (_, i) => series.at(i)).filter(point => Number.isFinite(point.x) && Number.isFinite(point.y));
        }
        function near(points, x, axis) {
            const half = axis === "q" ? 0.05 : 0.05 / (4 * Math.PI);
            return points.filter(point => Math.abs(point.x - x) < half);
        }
        function extent(series, x, axis) {
            const points = near(vertices(series), x, axis);
            return points.length ? {
                low: Math.min(...points.map(p => p.y)),
                high: Math.max(...points.map(p => p.y)),
                width: Math.max(...points.map(p => p.x)) - Math.min(...points.map(p => p.x))
            } : null;
        }
        function contribution(rows, magnetic, squared, axis) {
            // Bars are vertical thick LineSeries strokes: inspect the actual renderer
            // input rather than the deliberately empty Qt Graphs area edges.
            return Render.series(pattern).filter(series => series.visible && (/^chart\.series\.structure\.outline\./.test(series.objectName) || (!magnetic && series.objectName === "chart.series.calc.bars.fill")) && series.color.a > 0).find(series => rows.every(row => {
                    if (magnetic && row.magnetic < 1e-12)
                        return true;
                    const bounds = extent(series, row[axis], axis);
                    const low = magnetic ? (squared ? row.nuclear : Math.sqrt(row.nuclear)) : 0;
                    const high = magnetic ? (squared ? row.total : Math.sqrt(row.total)) : (squared ? row.nuclear : Math.sqrt(row.nuclear));
                    return bounds && Math.abs(bounds.high - high) < 1e-7 && Math.abs(bounds.low - low) < 1e-7;
                }));
        }
        function cases() {
            const rows = [];
            for (const magnetic of [false, true])
                for (const axis of ["q", "sine"])
                    for (const squared of [true, false])
                        rows.push({
                            tag: (magnetic ? "magnetic" : "nuclear") + "-" + axis + "-" + (squared ? "f2" : "f"),
                            magnetic,
                            axis,
                            squared
                        });
            return rows;
        }
        function test_constrained_moment_nuclear_counterfactual_data() {
            const rows = [];
            for (const mode of ["fixed", "expression", "alias"])
                for (const axis of ["q", "sine"])
                    for (const squared of [true, false])
                        rows.push({
                            tag: mode + "-" + axis + "-" + (squared ? "f2" : "f"),
                            mode,
                            axis,
                            squared
                        });
            return rows;
        }
        function test_constrained_moment_nuclear_counterfactual(data) {
            const aliases = "loop_\n_alias.id\n_alias.parameter_unique_name\nmz cosio.atom_site_moment.Co1.crystalaxis_z\n";
            const expression = data.mode === "expression" ? "mz = 1 + 1" : "mz = 2";
            const relations = aliases + (data.mode === "alias" ? "" : 'loop_\n_constraint.id\n_constraint.expression\nmz "' + expression + '"\n');
            open(true, false, relations);
            const before = SettingsProof.momentRelationFacts(Session.project);
            compare(before.moments, [[0, 0, 2]], "The declared nonzero constrained or aliased moment is present before plotting");
            compare(before.aliases, [["mz", "cosio.atom_site_moment.Co1.crystalaxis_z"]], "The real model retains the declared moment alias");
            compare(before.constraints, data.mode === "alias" ? [] : [["mz", expression]], "The real model retains the declared fixed or expression constraint");
            axis(data.axis);
            style(data.squared);
            verify(contribution(reference.rows, false, data.squared, data.axis) !== undefined, "The nuclear counterfactual remains the independent nonmagnetic structure factor despite nonzero moment relations");
            verify(contribution(reference.rows, true, data.squared, data.axis) !== undefined, "The constrained magnetic fill remains nonzero and stacks to the independent unpolarised total in either reciprocal axis and quantity");
            compare(SettingsProof.momentRelationFacts(Session.project), before, "Calculating the nuclear counterfactual preserves original moments, alias paths and constraint expressions");
        }
        function test_independent_reflections_and_stacked_contributions_data() {
            return cases();
        }
        function test_independent_reflections_and_stacked_contributions(data) {
            open(data.magnetic);
            axis(data.axis);
            style(data.squared);
            const rows = reference.rows.map(row => Object.assign({}, row, {
                    sine: row.sine,
                    total: data.magnetic ? row.total : row.nuclear
                }));
            const measured = PatternProof.measured(pattern).slice().sort((a, b) => a.x - b.x);
            const expected = rows.slice().sort((a, b) => a[data.axis] - b[data.axis]);
            compare(measured.length, rows.length, "Measured single-crystal values remain points in calculated Bars style");
            for (let i = 0; i < expected.length; ++i) {
                verify(Math.abs(measured[i].x - expected[i][data.axis]) < 1e-9, "Every measured reflection follows the independent reciprocal-cell metric");
                const y = data.squared ? expected[i].measured : Math.sqrt(expected[i].measured);
                verify(Math.abs(measured[i].y - y) < 1e-9, "The independent measured F² or square-root F stays paired with its own hkl");
            }
            const outline = Render.series(pattern).find(item => item.objectName === "chart.series.calc.bars.top");
            verify(outline !== undefined && outline.count > 0, "The actual calculated reflection bars expose their rendered total outline");
            for (const row of rows) {
                const bounds = extent(outline, row[data.axis], data.axis);
                const total = data.squared ? row.total : Math.sqrt(row.total);
                verify(bounds !== null && Math.abs(bounds.high - total) < 1e-7, "Calculated bar totals match the independent unpolarised single-atom structure factors");
            }
            const nuclearArea = contribution(rows, false, data.squared, data.axis);
            const theme = pattern.colors.isDarkPalette ? "dark" : "light";
            const published = JSON.parse(SettingsProof.repoText("tests/fixtures/single_crystal_pattern/powder-colours.json"));
            const token = Preferences.colourScheme;
            const oldIndex = published.tokens.indexOf(token);
            const oldPalette = oldIndex >= 0 ? published.palettes[oldIndex] : null;
            const totalColour = oldPalette ? oldPalette.roles.total_calculation[theme] : Approved.owner(SettingsProof).calc[theme];
            const colours = oldPalette ? oldPalette[theme].slice(2, 4) : Approved.colours(SettingsProof, token, "structures", 2, theme === "dark", {
                experiments: 1,
                structures: 1
            });
            verify(Qt.colorEqual(outline.color, totalColour), "The actual total bar outline uses the independently approved powder calculation red");
            verify(nuclearArea !== undefined, "Each calculated bar has a nuclear fill from zero to the independent nuclear contribution");
            const nuclearInk = Qt.tint("transparent", colours[0]);
            verify(Math.abs(nuclearArea.color.r - nuclearInk.r) + Math.abs(nuclearArea.color.g - nuclearInk.g) + Math.abs(nuclearArea.color.b - nuclearInk.b) < 1e-6, "The nuclear fill follows the independent approved powder structure colour");
            if (data.magnetic) {
                const magneticArea = contribution(rows, true, data.squared, data.axis);
                verify(magneticArea !== undefined, "The magnetic fill stacks above nuclear and reaches the independent total; F uses cumulative square roots");
                const magneticInk = Qt.tint("transparent", colours[1]);
                verify(Math.abs(magneticArea.color.r - magneticInk.r) + Math.abs(magneticArea.color.g - magneticInk.g) + Math.abs(magneticArea.color.b - magneticInk.b) < 1e-6, "The magnetic fill follows the independent approved powder magnetic contribution colour");
            }
            const labels = Render.descendants(pattern).filter(item => item.objectName === "chart.bragg.label" && item.visible);
            compare(labels.length, data.magnetic ? 2 : 1, "The actual Bragg strip has nuclear and magnetic rows only when the structure is magnetic");
            const icons = [];
            for (const label of labels) {
                compare(label.segments.filter(part => part.text !== undefined).map(part => part.text).join(""), "cosio", "Every Bragg row uses the structure name without a contribution suffix");
                const icon = label.segments.find(part => part.icon !== undefined);
                verify(icon !== undefined, "Each actual Bragg label exposes its powder structure or magnetic icon");
                icons.push(icon.icon);
                verify(Qt.colorEqual(icon.color, colours[icon.icon === "magnet" ? 1 : 0]), "The actual Bragg tick label uses its independently approved powder contribution colour");
            }
            verify(icons.includes("layer-group") && (!data.magnetic || icons.includes("magnet")), "Actual Bragg rows distinguish nuclear and magnetic by the powder icons");
            verify(findChild(pattern, "chart.view.residual").visible, "Measured minus calculated has its own residual pane");
            const residual = Render.series(pattern).find(item => item.objectName === "chart.series.residual.bars.top" || item.objectName === "chart.series.resid.band.top");
            verify(residual !== undefined && residual.count > 0, "The residual is rendered as bars, including in calculated line mode");
            const residualColour = oldPalette ? oldPalette.roles.difference[theme] : Approved.reference(SettingsProof).schemes.find(row => row.id === token).palette[theme].difference;
            verify(Qt.colorEqual(residual.color, residualColour), "Residual bars use the independently approved powder grey");
            for (const row of rows) {
                const value = data.squared ? row.measured - row.total : Math.sqrt(row.measured) - Math.sqrt(row.total);
                const bounds = extent(residual, row[data.axis], data.axis);
                verify(bounds !== null && Math.abs(bounds.low - Math.min(0, value)) < 1e-7 && Math.abs(bounds.high - Math.max(0, value)) < 1e-7, "Residual bars run from zero to the independently computed measured-minus-calculated value");
            }
            const tickSeries = Render.series(findChild(pattern, "chart.view.bragg")).filter(series => /^chart\.series\.bragg\./.test(series.objectName) && vertices(series).length > 0);
            compare(tickSeries.length, data.magnetic ? 2 : 1, "Each actual nuclear or magnetic Bragg row has its own tick series");
            for (const series of tickSeries) {
                const xs = vertices(series).map(point => point.x);
                verify(xs.length > 0 && xs.every(x => rows.some(row => Math.abs(row[data.axis] - x) < 1e-9)), "Every drawn Bragg tick lies at an independently calculated reflection position");
            }
            click(findChild(pattern, "chart.toolbar.thinBars"));
            const lines = Render.series(pattern).filter(series => !series.upperSeries && series.visible && series.count > 0);
            const matches = (series, magnetic) => rows.every(row => {
                    if (magnetic && row.magnetic < 1e-12)
                        return true;
                    const bounds = extent(series, row[data.axis], data.axis);
                    const low = magnetic ? (data.squared ? row.nuclear : Math.sqrt(row.nuclear)) : 0;
                    const high = magnetic ? (data.squared ? row.total : Math.sqrt(row.total)) : (data.squared ? row.nuclear : Math.sqrt(row.nuclear));
                    return bounds && Math.abs(bounds.low - low) < 1e-7 && Math.abs(bounds.high - high) < 1e-7;
                });
            verify(lines.some(line => matches(line, false) && Qt.colorEqual(line.color, colours[0])), "Thin mode renders the independently calculated nuclear line in its powder colour");
            if (data.magnetic)
                verify(lines.some(line => matches(line, true) && Qt.colorEqual(line.color, colours[1])), "Thin mode renders the magnetic line stacked over nuclear in its powder colour");
        }
        function test_legend_hides_real_contributions_data() {
            return [
                {
                    tag: "nuclear",
                    magnetic: false
                },
                {
                    tag: "magnetic",
                    magnetic: true
                }
            ];
        }
        function test_legend_hides_real_contributions(data) {
            open(data.magnetic);
            axis("q");
            style(true);
            click(findChild(pattern, "chart.toolbar.legend"));
            const legend = findChild(pattern, "chart.legend");
            tryCompare(legend, "visible", true, 1000, "The actual legend opens from its toolbar button");
            let entries;
            tryVerify(() => {
                entries = Render.descendants(legend).filter(item => item.objectName === "chart.legend.entry" && item.visible && item.bragg && item.label === "cosio");
                return entries.length === (data.magnetic ? 2 : 1);
            }, 1000, "The actual legend finishes drawing each named contribution row before input");
            compare(entries.length, data.magnetic ? 2 : 1, "Each calculated contribution has a real legend row named only by its structure");
            const keys = entries.map(entry => entry.key);
            const rowFor = key => Render.descendants(legend).find(item => item.objectName === "chart.legend.entry" && item.visible && item.key === key);
            for (const key of keys) {
                const entry = rowFor(key);
                verify(entry.segments.some(part => part.icon === (entry.magnetic ? "magnet" : "layer-group")), "Each actual contribution legend row uses the powder structure or magnetic icon");
                const area = contribution(reference.rows, entry.magnetic, true, "q");
                verify(area !== undefined, "A contribution legend row has actual drawn contribution strokes before it is hidden");
                click(entry);
                tryVerify(() => rowFor(key) && rowFor(key).hidden && (!area.visible || area.color.a === 0 || vertices(area).length === 0), 1000, "Clicking the actual legend row hides its contribution in the real graph");
                click(rowFor(key));
                tryVerify(() => rowFor(key) && !rowFor(key).hidden && area.visible && area.color.a > 0 && vertices(area).length > 0, 1000, "Clicking the refreshed actual legend row restores its plotted contribution");
            }
        }
        function test_simulation_has_calculated_bars_and_ticks_without_measurements_data() {
            return [
                {
                    tag: "nuclear",
                    magnetic: false
                },
                {
                    tag: "magnetic",
                    magnetic: true
                }
            ];
        }
        function test_simulation_has_calculated_bars_and_ticks_without_measurements(data) {
            open(data.magnetic, true);
            tryVerify(() => Session.project.currentExperiment.singleCrystalReflections.simulated, 3000, "An experiment without measured data publishes real simulated reflections");
            axis("q");
            const line = Render.series(pattern).find(item => item.objectName === "chart.series.calc.bars.top");
            verify(line !== undefined && vertices(line).length > 0, "An empty single-crystal experiment renders its calculated reflection bars");
            compare(PatternProof.measured(pattern).length, 0, "A simulation invents no measured points");
            verify(!findChild(pattern, "chart.view.residual").visible, "A simulation has no residual pane without measurements");
            const labels = Render.descendants(pattern).filter(item => item.objectName === "chart.bragg.label" && item.visible);
            compare(labels.length, data.magnetic ? 2 : 1, "Simulated Bragg strips retain the structure's nuclear and magnetic row count");
        }
        function assertMeasuredPixels(squared, axisName) {
            const layer = findChild(pattern, "chart.measured");
            verify(layer !== null && layer.count === reference.rows.length && layer.visible, "Measured points stay visible in either calculated bar style");
            verify(layer.fillColor.a > 0 && layer.fillColor.a < 1 && layer.fillColor.b > layer.fillColor.r, "Measured circles have a light blue fill and a blue outline");
            verify(waitForPolish(layer) && waitForRendering(layer), "The actual measured layer completes a frame before pixel inspection");
            const pointer = findChild(pattern, "chart.pointer"), initialRange = layer.xMax - layer.xMin;
            mouseWheel(pointer, pointer.width / 2, pointer.height / 2, 0, -240);
            tryVerify(() => layer.xMax - layer.xMin > initialRange, 1000, "Real zoom-out input places boundary reflections inside the pixel viewport");
            const image = grabImage(layer);
            function ink(x, y) {
                for (let dx = -1; dx <= 1; ++dx)
                    for (let dy = -1; dy <= 1; ++dy) {
                        const px = Math.round(x) + dx, py = Math.round(y) + dy;
                        if (px < 0 || py < 0 || px >= image.width || py >= image.height)
                            continue;
                        const pixel = image.pixel(px, py);
                        if (pixel.a > 0.6 && Math.abs(pixel.r - layer.color.r) + Math.abs(pixel.g - layer.color.g) + Math.abs(pixel.b - layer.color.b) < 0.25)
                            return true;
                    }
                return false;
            }
            for (const row of reference.rows.slice(0, 3)) {
                const y = squared ? row.measured : Math.sqrt(row.measured);
                const su = squared ? row.su : row.su / (2 * Math.sqrt(row.measured));
                const xPixel = (row[axisName] - layer.xMin) / (layer.xMax - layer.xMin) * layer.width;
                for (const end of [y - su, y + su]) {
                    const yPixel = (layer.yMax - end) / (layer.yMax - layer.yMin) * layer.height;
                    verify(ink(xPixel, yPixel), "Actual blue error-bar ink reaches the independently converted uncertainty endpoint");
                }
            }
        }
        function test_measured_points_and_uncertainties_in_both_modes_data() {
            const rows = [];
            for (const axis of ["q", "sine"])
                for (const squared of [true, false])
                    for (const thin of [false, true])
                        rows.push({
                            tag: axis + "-" + (squared ? "f2" : "f") + "-" + (thin ? "lines" : "bars"),
                            axis,
                            squared,
                            thin
                        });
            return rows;
        }
        function test_measured_points_and_uncertainties_in_both_modes(data) {
            open(false);
            axis(data.axis);
            style(data.squared);
            if (data.thin)
                click(findChild(pattern, "chart.toolbar.thinBars"));
            assertMeasuredPixels(data.squared, data.axis);
        }
        function test_bar_width_and_thin_line_zoom_invariants_data() {
            return [
                {
                    tag: "q",
                    axis: "q"
                },
                {
                    tag: "sine",
                    axis: "sine"
                }
            ];
        }
        function test_bar_width_and_thin_line_zoom_invariants(data) {
            open(false);
            axis(data.axis);
            style(true);
            const outline = Render.series(pattern).find(item => item.objectName === "chart.series.calc.bars.top");
            const layer = findChild(pattern, "chart.measured"), pointer = findChild(pattern, "chart.pointer");
            verify(outline !== undefined && pointer !== null && pointer.enabled, "Bar width is observed on real Qt series under the actual chart pointer");
            const x = reference.rows[0][data.axis];
            const before = extent(outline, x, data.axis);
            verify(before !== null && before.width > 0, "The calculated bar has a positive physical x width");
            const widthPixels = () => extent(outline, x, data.axis).width / (layer.xMax - layer.xMin) * layer.width;
            const initialPixels = widthPixels(), initialRange = layer.xMax - layer.xMin;
            mouseWheel(pointer, (x - layer.xMin) / initialRange * pointer.width, pointer.height / 2, 0, 240);
            tryVerify(() => layer.xMax - layer.xMin < initialRange, 1500, "A real wheel event zooms the single-crystal x range");
            verify(Math.abs(extent(outline, x, data.axis).width - before.width) < 1e-9, "Bars retain their physical Q width when the actual chart is zoomed");
            verify(widthPixels() > initialPixels, "A fixed-width bar occupies more pixels after real zoom input");
            click(findChild(pattern, "chart.toolbar.thinBars"));
            tryVerify(() => widthPixels() <= 1.1, 1000, "Thin-line mode has a single-pixel horizontal footprint");
            const ticks = Render.series(findChild(pattern, "chart.view.bragg")).filter(series => series.count > 0);
            verify(ticks.length > 0 && ticks.every(series => Math.abs(series.width - outline.width) < 1e-9), "The thin calculated lines match the actual Bragg tick stroke width");
            const range = layer.xMax - layer.xMin, thinPixels = widthPixels();
            mouseWheel(pointer, (x - layer.xMin) / range * pointer.width, pointer.height / 2, 0, 120);
            tryVerify(() => layer.xMax - layer.xMin < range, 1500, "Thin-line mode still accepts the actual zoom gesture");
            verify(Math.abs(widthPixels() - thinPixels) < 0.1, "Calculated thin lines retain their pixel width at another zoom");
        }
        function test_comparison_quantities_remain_separate_from_pattern_data() {
            return [
                {
                    tag: "nuclear",
                    magnetic: false
                },
                {
                    tag: "magnetic",
                    magnetic: true
                }
            ];
        }
        function test_comparison_quantities_remain_separate_from_pattern(data) {
            open(data.magnetic);
            axis("q");
            style(true);
            scene.destroy();
            scene = null;
            pattern = null;
            mainView = Qt.createQmlObject('import edi.app; MainView { width: 1100; height: 800; shown: true; tabKeys: ["pattern", "meascalc"]; defaultKey: "pattern"; pageKey: "comparison-acceptance" }', surface);
            verify(mainView !== null && waitForPolish(mainView), "The comparison actor uses the real main-view tab host");
            click(findChild(mainView, "mainArea.tab.measCalc"));
            tryCompare(mainView, "currentKey", "meascalc", 1500, "Actual comparison-tab input selects the supported independent view");
            scene = findChild(mainView, "singleCrystal.measCalc");
            verify(scene !== null && waitForRendering(scene), "The comparison tab renders its actual single-crystal chart");
            const box = findChild(scene, "singleCrystal.toolbar.quantity");
            choose(box, text => text === "F");
            const layer = findChild(scene, "singleCrystal.points");
            verify(layer !== null && layer.count === reference.rows.length, "The comparison has one actual measured point per reflection");
            const actual = PatternProof.layerPoints(layer);
            for (const row of reference.rows) {
                const x = Math.sqrt(data.magnetic ? row.total : row.nuclear), y = Math.sqrt(row.measured);
                verify(actual.some(point => Math.abs(point.x - x) < 1e-7 && Math.abs(point.y - y) < 1e-9), "Meas vs calc plots independent calculated and measured F for each reflection");
            }
            const diagonal = Render.series(scene).find(series => series.count === 2 && vertices(series).length === 2 && vertices(series).every(point => point.x === point.y));
            verify(diagonal !== undefined && vertices(diagonal)[0].x !== vertices(diagonal)[1].x, "The comparison draws its actual nondegenerate y equals x line");
            click(findChild(mainView, "mainArea.tab.pattern"));
            tryCompare(mainView, "currentKey", "pattern", 1500, "Actual tab input returns to the independent Pattern view");
            pattern = Render.descendants(mainView).find(item => item.objectName === "chart" && item.visible && item.singleCrystal === true);
            verify(pattern !== undefined, "Returning to Pattern restores its real reciprocal-axis chart");
            compare(findChild(pattern, "chart.toolbar.singleCrystalQuantity").currentText, "F²", "Changing comparison to F preserves the Pattern tab's independent F² setting");
        }
        function test_powder_comparison_has_one_point_per_data_row_and_identity_line() {
            Preferences.resetToDefaults();
            root = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/loop_parameter_ids/line-segment"));
            PowderInput.prepare(SettingsProof, root);
            verify(Session.openProject(root), "The powder comparison opens independently declared measured counts and a six-count background");
            tryCompare(Session.project, "calculating", false, 10000, "The real powder calculation finishes before comparison");
            try {
                scene = Qt.createQmlObject('import edi.app; MeasCalcChart { width: 1100; height: 800; shown: true; experiment: Session.project.currentExperiment }', surface);
            } catch (error) {
                verify(false, "The production powder Meas vs calc chart can be instantiated");
            }
            verify(scene !== null && waitForPolish(scene) && waitForRendering(scene), "The actual powder comparison chart renders its current experiment");
            const layer = findChild(scene, "measCalc.points");
            verify(layer !== null && layer.count === 3, "Powder comparison has one actual point per measured data row");
            const points = PatternProof.layerPoints(layer), measured = [20, 33, 25];
            for (let i = 0; i < measured.length; ++i)
                verify(Math.abs(points[i].x - 6) < 1e-10 && Math.abs(points[i].y - measured[i]) < 1e-10, "Powder comparison pairs each independent measured count with its flat-background calculation");
            const diagonal = Render.series(scene).find(series => series.count === 2 && vertices(series).every(point => point.x === point.y));
            verify(diagonal !== undefined && Math.min(...vertices(diagonal).map(point => point.x)) <= 6 && Math.max(...vertices(diagonal).map(point => point.x)) >= 33, "The actual powder y equals x line spans the measured and calculated data");
        }
        function test_creating_single_crystal_experiment_immediately_draws_simulated_bars() {
            open(false);
            scene.destroy();
            scene = null;
            page = pageFactory.createObject(test);
            verify(page !== null && waitForPolish(page) && waitForRendering(page), "The simulation creation witness renders the production Experiment page");
            click(findChild(page, "sideBar.tab.basic"));
            const group = findChild(page, "group.experiments");
            verify(group !== null, "The actual Experiment page exposes its experiment group");
            if (group.collapsed)
                click(group);
            tryVerify(() => !group.collapsed && Math.abs(group.height - group.implicitHeight) < 1, 1500, "The actual experiment group finishes expanding before Create input");
            const before = Session.project.experiments.count;
            click(findChild(page, "experiments.create"));
            tryCompare(Session.project.experiments, "count", before + 1, 2000, "The real Create control adds one experiment");
            choose(findChild(page, "experimentType.sampleForm"), text => /single.*crystal/i.test(text));
            tryCompare(Session.project.currentExperiment, "sampleFormToken", "single crystal", 2000, "Real type input makes the new experiment single-crystal before loading data");
            tryVerify(() => Session.project.currentExperiment.singleCrystalReflections.simulated, 5000, "The newly created single-crystal experiment immediately calculates its simulated reflections");
            page.destroy();
            page = null;
            scene = chartFactory.createObject(surface, {
                experiment: Session.project.currentExperiment,
                project: Session.project
            });
            verify(scene !== null && waitForPolish(scene) && waitForRendering(scene), "The real chart displays the newly created single-crystal experiment");
            axis("q");
            const bars = Render.series(pattern).find(series => series.objectName === "chart.series.calc.bars.top");
            verify(bars !== undefined && bars.count > 0, "Creating a single-crystal experiment without data displays real simulated calculated bars");
            compare(PatternProof.measured(pattern).length, 0, "The newly created simulation invents no measured data");
            verify(!findChild(pattern, "chart.view.residual").visible, "The newly created simulation has no residual without measured data");
        }
    }
}
