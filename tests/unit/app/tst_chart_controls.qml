// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtTest
import edi.app
import ReportAcceptance 1.0
import EdiAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render
import "../../fixtures/scan_views/input.js" as Input

Rectangle {
    id: surface
    width: 1200
    height: 850
    color: "white"
    Component {
        id: scanFactory
        ScanViewChart {
            width: 1100
            height: 760
            shown: false
        }
    }
    Component {
        id: preferencesFactory
        AppPreferencesDialog {}
    }
    Component {
        id: figureFactory
        FigureColors {
            light: true
        }
    }
    Component {
        id: patternFactory
        PatternChart {
            width: 1100
            height: 760
        }
    }
    Component {
        id: reportFactory
        ReportPage {
            width: 1200
            height: 850
            current: true
        }
    }
    Component {
        id: structureFactory
        StructureView {
            width: 600
            height: 500
            shown: false
        }
    }
    TestCase {
        id: test
        name: "ChartControls"
        when: windowShown
        property var chart
        property var dialog
        property var reportPage
        property var location
        property int originalTheme
        property var owner: JSON.parse(SettingsProof.repoText("tests/fixtures/chart_controls/owner.json"))
        function initTestCase() {
            originalTheme = Style.Colors.theme;
        }
        function cleanup() {
            if (chart)
                chart.destroy();
            if (dialog) {
                dialog.close();
                dialog.destroy();
            }
            if (reportPage)
                reportPage.destroy();
            reportPage = null;
            chart = null;
            dialog = null;
            Session.closeProject();
            Preferences.resetToDefaults();
            Style.Colors.theme = originalTheme;
        }
        function items(root) {
            return Render.descendants(root);
        }
        function combo(root, labels) {
            const found = items(root).find(item => typeof item.textAt === "function" && item.count === labels.length && labels.every((text, i) => item.textAt(i) === text));
            verify(found !== undefined, "The real selector offers exactly the owner's labels in order: " + labels.join(", "));
            return found;
        }
        function choose(box, index) {
            box.currentIndex = index;
            box.activated(index);
        }
        function ready() {
            chart.shown = true;
            tryCompare(Session.project.scanViews, "loaded", Session.project.scanViews.count, 8000, "Every independently written scan row completes its real read");
            verify(waitForPolish(chart) && waitForRendering(chart), "The production chart completes an actual rendering frame");
        }
        function openScan(mode, count = 3, noBackground = false) {
            Style.Colors.theme = Style.Colors.LightTheme;
            Preferences.resetToDefaults();
            Preferences.chartHighlightSelected = false;
            Preferences.patternYScale = "linear";
            location = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/scan_template/project"));
            verify(/^file:\/\/\//.test(String(location)), "Every actor writes only a private absolute project copy");
            Input.prepare(SettingsProof, location, "rows");
            if (count !== 3)
                Input.dense(SettingsProof, location, false, count);
            let text = SettingsProof.text(location, "experiments/d20.edi");
            text = text.replace(/_background.type[^\n]+[\s\S]*?(?=\n(?:loop_\n_(?!background\.)|_(?!background\.)[a-z])|$)/, noBackground ? "" : "_background.type line-segment\n\nloop_\n_background.id\n_background.position\n_background.intensity\n1 0 17\n2 180 17\n");
            verify(SettingsProof.write(location, "experiments/d20.edi", text), "The background witness is the project's explicit constant line segment, never an estimate");
            verify(Session.openProject(location), "The production session opens the independent scan project");
            chart = scanFactory.createObject(surface, {
                project: Session.project,
                mode
            });
            verify(chart !== null, "The actor creates the real scan chart");
            ready();
            const layer = items(chart).find(item => String(item.objectName) === "scanView." + mode + ".layer");
            verify(layer !== undefined, "The numerical observer reads the production layer shared by both renderers");
            return layer;
        }
        function test_preferences_strip_uses_shared_project_colours() {
            openScan("stacked");
            dialog = preferencesFactory.createObject(surface);
            verify(dialog !== null, "The strip gate creates the production Preferences dialog");
            dialog.open();
            tryCompare(dialog, "visible", true, 1000, "The strip witness opens Preferences before observing its rendered pixels");
            verify(waitForPolish(dialog.contentItem) && waitForRendering(dialog.contentItem), "The opened Preferences strip completes layout and a frame");
            const appearance = findChild(dialog.contentItem, "preferences.tab.appearance");
            verify(appearance !== null, "Preferences exposes its real Appearance tab");
            mouseClick(appearance, appearance.width / 2, appearance.height / 2);
            tryCompare(appearance, "checked", true, 1000, "The strip witness selects the actual Appearance tab before capture");
            const explanation = items(dialog.contentItem).find(item => item.text === "Each new experiment or structure takes the next free colour.");
            verify(explanation !== undefined, "Preferences displays the owner's exact one-line colour-order explanation");
            const calc = items(dialog.contentItem).find(item => item.text === "calc");
            verify(calc !== undefined, "The common calculation colour is labelled calc beside its separate calculator icon");
            const calculator = items(dialog.contentItem).find(item => item.objectName === "preferences.paletteStrip.calc");
            verify(calculator !== undefined && calculator.text === "calculator", "The calculation marker uses the approved calculator glyph");
            compare(calculator.font.family, Style.Fonts.iconsFamily, "The calculator glyph is drawn with the application's icon font");
            compare(String(calculator.color).toUpperCase(), owner.calc.light, "The separate calculator uses the independently recorded light calculation colour");
            const strip = explanation.parent;
            const colours = [];
            for (const item of items(strip))
                for (const colour of [item.color, item.textColor])
                    colours.push(String(colour).toUpperCase());
            verify(owner.palettes[0].light.every(colour => colours.includes(colour)), "The live strip displays all eleven independently recorded palette positions");
            tryCompare(dialog, "opened", true, 2000, "The Preferences opening transition finishes before its pixel baseline");
            function stripSnapshot() {
                const root = surface.Window.window.contentItem;
                surface.Window.window.update();
                verify(waitForRendering(root), "Each palette snapshot follows an explicitly requested whole-window frame");
                const image = grabImage(root);
                const at = strip.mapToItem(root, 0, 0);
                const sx = image.width / root.width, sy = image.height / root.height;
                const left = Math.floor(at.x * sx), top = Math.floor(at.y * sy);
                const right = Math.ceil((at.x + strip.width) * sx), bottom = Math.ceil((at.y + strip.height) * sy);
                verify(left >= 0 && top >= 0 && right <= image.width && bottom <= image.height, "The whole-window capture contains the visible palette strip");
                const pixels = [];
                for (let y = top; y < bottom; ++y)
                    for (let x = left; x < right; ++x)
                        pixels.push(String(image.pixel(x, y)));
                return {
                    width: right - left,
                    height: bottom - top,
                    pixels
                };
            }
            function sameStrip(expected, actual) {
                return expected.width === actual.width && expected.height === actual.height && expected.pixels.every((pixel, index) => pixel === actual.pixels[index]);
            }
            tryCompare(Session.project, "calculating", false, 8000, "The baseline project's calculation finishes before its palette is captured");
            let before = stripSnapshot();
            tryVerify(() => {
                const next = stripSnapshot();
                const settled = sameStrip(before, next);
                before = next;
                return settled;
            }, 2000, "The visible palette reaches a stable baseline before comparing project edits");
            verify(before.width > 0 && before.pixels.some(pixel => pixel.toUpperCase() === owner.palettes[0].light[3]), "The capture contains the recorded colour of the actual free palette square");
            verify(Session.project.createStructure(), "Adding a real project structure exercises the live assignment consumer");
            tryCompare(Session.project, "calculating", false, 8000, "The added structure's calculation finishes before its palette frame is compared");
            verify(waitForPolish(strip), "A project edit reaches the order strip's layout");
            tryVerify(() => !sameStrip(before, stripSnapshot()), 2000, "Adding an item changes a free square into that item's coloured icon");
            Session.project.removeStructure(Session.project.structures.count - 1);
            tryCompare(Session.project, "calculating", false, 8000, "The removed structure's calculation finishes before its palette frame is compared");
            verify(waitForPolish(strip), "Removing an item reaches the order strip's layout");
            tryVerify(() => sameStrip(before, stripSnapshot()), 2000, "Removing the new item restores its free square and original assignments");
        }
        function test_saved_html_and_pdf_are_light_data() {
            return owner.palettes.map((palette, index) => ({
                        tag: palette.name,
                        palette,
                        index
                    }));
        }
        function test_saved_html_and_pdf_are_light(data) {
            Style.Colors.theme = Style.Colors.DarkTheme;
            Preferences.colourScheme = ApplicationInfo.colourSchemes[data.index];
            location = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project"));
            verify(Session.openProject(location), "The actual export witness opens an independent saved project in a dark app");
            tryCompare(Session.project, "calculating", false, 15000, "The real input finishes calculating before export");
            reportPage = reportFactory.createObject(surface);
            verify(reportPage !== null && waitForPolish(reportPage), "The real Report page creates its export figures");
            const group = findChild(reportPage, "group.reportExport");
            verify(group !== null, "The light export witness invokes the actual report writer");
            Session.project.report.embedLibraries = true;
            Session.project.report.writesPdf = true;
            group.saveReport();
            const base = "reports/" + Session.project.name;
            tryVerify(() => [".html", ".pdf"].every(extension => SettingsProof.fileFacts(location, base + extension).bytes > 100), 15000, "Both actual saved report formats exist before their colours are observed");
            const expected = data.palette.light[0].toLowerCase();
            const html = SettingsProof.htmlEvolutionFacts(SettingsProof.childUrl(location, base + ".html"));
            verify(!html.error, "An independent browser renders the saved HTML: " + html.error);
            for (const width of ["wide", "narrow"]) {
                verify(html[width].ready && html[width].patterns.length > 0, "The saved HTML actually draws its pattern at each width");
                const pattern = html[width].patterns[0];
                const measured = pattern.traces.find(trace => /measured/i.test(String(trace.name).replace(/<[^>]+>/g, "")));
                verify(measured !== undefined, "The independent browser locates the measured trace in the saved report");
                compare(String(measured.line.color).toLowerCase(), expected, "The saved HTML uses the recorded light measured colour while the app is dark");
                verify(["#fff", "#ffffff", "rgb(255, 255, 255)"].includes(String(pattern.background).toLowerCase()), "The saved HTML's actual plot background is white");
            }
            const pixels = SettingsProof.pdfImageColours(SettingsProof.childUrl(location, base + ".pdf"), [expected]);
            verify(!pixels.error && pixels.images > 0, "The independent PDF observer decodes actual saved figure images");
            verify(pixels.counts[expected] >= 5, "The actual saved PDF contains the light curve colour from the owner record");
        }
        function test_element_scheme_names() {
            openScan("stacked");
            const view = createTemporaryObject(structureFactory, surface, {
                structure: Session.project.currentStructure,
                options: Session.project.structureViewOptions
            });
            verify(view !== null, "The element-name witness creates the real structure view toolbar");
            combo(view, ["Jmol", "VESTA"]);
        }
        function test_common_pool_and_earth_reservation_data() {
            return owner.palettes.map((palette, index) => ({
                        tag: palette.name,
                        palette,
                        index
                    }));
        }
        function test_common_pool_and_earth_reservation(data) {
            Style.Colors.theme = Style.Colors.LightTheme;
            verify(Session.createProject("colour_pool", "Interleaved experiment and structure colours"), "The shared-pool witness uses a regular project that admits experiment additions");
            verify(Session.project.createExperiment(), "The shared-pool witness starts with a real experiment");
            verify(Session.project.createStructure(), "The shared-pool witness starts with a real structure");
            const tokens = Array.from(ApplicationInfo.colourSchemes);
            compare(tokens.length, 5, "The actual assignment sees exactly five figure palettes");
            Preferences.colourScheme = tokens[data.index];
            const firstStructure = String(AppColors.structure(0)).toUpperCase();
            const firstExperiment = String(AppColors.experiment(0)).toUpperCase();
            verify(firstStructure !== firstExperiment, "Structures and experiments never consume the same occupied palette position");
            const palette = data.palette.light;
            if (data.index === 0) {
                compare(firstExperiment, palette[0], "Earth starts experiments at reserved position one");
                compare(firstStructure, palette[2], "Earth starts structures after its two experiment reservations");
            } else {
                verify(palette.includes(firstStructure) && palette.includes(firstExperiment), "Both kinds draw from the same eleven-colour pool");
            }
            const original = String(AppColors.structure(0));
            verify(Session.project.createExperiment(), "The shared pool receives a real experiment after the existing items");
            compare(String(AppColors.structure(0)), original, "Adding an experiment preserves an existing structure's occupied position");
            const e = String(AppColors.experiment(Session.project.experiments.count - 1)).toUpperCase();
            verify(Session.project.createStructure(), "The shared pool receives a structure after an experiment");
            const s = String(AppColors.structure(Session.project.structures.count - 1)).toUpperCase();
            verify(e !== s, "Interleaved additions take distinct next free positions across item kinds");
        }
        function test_light_figure_is_independent_of_app_theme() {
            Style.Colors.theme = Style.Colors.DarkTheme;
            const figure = createTemporaryObject(figureFactory, surface);
            verify(figure !== null, "The export observer creates the actual light figure colour provider");
            compare(figure.isDarkPalette, false, "An export's figure never inherits the dark app theme");
            compare(String(figure.chartBackground), "#ffffff", "PDF, HTML and picture figures use the same white paper");
            const before = String(figure.chartBackground);
            Style.Colors.theme = Style.Colors.LightTheme;
            compare(String(figure.chartBackground), before, "Export paper stays constant through an app theme switch");
        }
        function test_element_two_to_one_and_scheme_titles() {
            for (const scheme of ["jmol", "vesta"]) {
                const source = ApplicationInfo.elementColor("H", "#000000", scheme);
                const actual = ApplicationInfo.readableColour(source, ["#ffffff"]);
                const carbon = ApplicationInfo.readableColour(ApplicationInfo.elementColor("C", "#000000", scheme), ["#ffffff"]);
                verify(String(actual) !== String(carbon), "The common element function distinguishes hydrogen and carbon for both schemes");
            }
            compare(String(ApplicationInfo.readableColour("#aaaaaa", ["#ffffff"])), "#aaaaaa", "An element above 2:1 but below 3:1 remains byte-identical through the app adapter");
        }
        function test_map_direction_default_and_theme_following() {
            const layer = openScan("map");
            const direction = combo(chart, ["Auto", "Normal", "Inverted"]);
            compare(direction.currentText, "Auto", "A new project starts with automatic map direction");
            const map = combo(chart, owner.maps);
            compare(map.currentIndex, 0, "The new default map is Blue-Red");
            for (const theme of [Style.Colors.LightTheme, Style.Colors.DarkTheme]) {
                Style.Colors.theme = theme;
                choose(map, 0);
                choose(direction, 0);
                verify(waitForPolish(chart), "The Blue-Red map follows the current theme");
                compare(String(layer.mapColour(0)).toUpperCase(), owner.blue_red[theme === Style.Colors.LightTheme ? "light" : "dark"][0], "Automatic Blue-Red starts at its independently recorded background stop in each theme");
                choose(map, owner.maps.indexOf("Viridis"));
                choose(direction, 0);
                verify(waitForPolish(chart), "The map's automatic direction processes the theme switch");
                compare(layer.reversed, theme === Style.Colors.LightTheme, "Viridis puts its light endpoint low on white and its dark endpoint low on dark paper");
                choose(direction, 1);
                compare(layer.reversed, false, "Normal is stable in both themes");
                choose(direction, 2);
                compare(layer.reversed, true, "Inverted is stable in both themes");
            }
            choose(direction, 0);
            verify(Session.save(), "The project saves its automatic choice through the real persistence path");
            chart.destroy();
            chart = null;
            Session.closeProject();
            verify(Session.openProject(location), "The direction actor reopens its saved project");
            chart = scanFactory.createObject(surface, {
                project: Session.project,
                mode: "map"
            });
            ready();
            compare(combo(chart, ["Auto", "Normal", "Inverted"]).currentText, "Auto", "Save and reopen preserve Auto itself rather than its resolved Boolean");
        }
        function test_spacing_geometry_data() {
            const rows = [];
            for (const count of [1, 3, 162])
                for (let step = 0; step < 5; ++step)
                    rows.push({
                        tag: count + "-" + step,
                        count,
                        step
                    });
            return rows;
        }
        function test_spacing_geometry(data) {
            const layer = openScan("stacked", data.count);
            const spacing = combo(chart, ["Overlay", "Close", "Medium", "Wide", "Separate"]);
            compare(spacing.currentText, "Wide", "Every new scan uses Wide regardless of pattern count");
            choose(spacing, data.step);
            verify(waitForPolish(chart), "The spacing selector updates the one production placement function");
            const s = data.step / 4, height = 1 - s + s / data.count;
            fuzzyCompare(layer.patternHeight, height, 1e-10, "Pattern height equals H(1-s)+(H/N)s independently of the renderer");
            for (let row = 0; row < data.count; ++row)
                fuzzyCompare(layer.rowOf(row), data.count === 1 ? 0 : row * (1 - height) / (data.count - 1), 1e-10, "Every baseline follows the closed-form evenly spaced placement");
            if (data.step === 4) {
                for (let row = 1; row < data.count; ++row)
                    verify(layer.rowOf(row) + 1e-10 >= layer.peakOf(row - 1), "Separate leaves every independently measured pattern below its next baseline");
            }
            if (data.step === 4) {
                for (const range of [[10, 80], [25, 30]]) {
                    chart.zoomX = range;
                    verify(waitForPolish(chart), "Separate recomputes placement for each visible x range");
                    for (let row = 1; row < data.count; ++row)
                        verify(layer.rowOf(row) + 1e-10 >= layer.peakOf(row - 1), "Separate remains non-overlapping after the large peaks leave the view");
                }
            }
            const image = grabImage(chart);
            verify(image.width > 0 && image.height > 0, "The geometry actor also renders the real chart");
        }
        function test_spacing_survives_project_reopen() {
            openScan("stacked");
            choose(combo(chart, ["Overlay", "Close", "Medium", "Wide", "Separate"]), 1);
            verify(Session.save(), "The spacing choice saves in the project's real store");
            chart.destroy();
            chart = null;
            Session.closeProject();
            verify(Session.openProject(location), "The spacing actor reopens the real saved project");
            chart = scanFactory.createObject(surface, {
                project: Session.project,
                mode: "stacked"
            });
            ready();
            compare(combo(chart, ["Overlay", "Close", "Medium", "Wide", "Separate"]).currentText, "Close", "The non-default spacing step survives a save and reopen");
        }
        function subtractButton() {
            const button = items(chart).find(item => /subtract.*background/i.test(String(item.toolTip)));
            verify(button !== undefined, "The scan toolbar exposes a subtract-background button");
            return button;
        }
        function test_subtraction_uses_set_unfitted_background_data() {
            return [
                {
                    tag: "Stacked",
                    mode: "stacked"
                },
                {
                    tag: "Map",
                    mode: "map"
                }
            ];
        }
        function test_subtraction_uses_set_unfitted_background(data) {
            const layer = openScan(data.mode);
            const button = subtractButton();
            compare(button.checked, false, "Background subtraction is off on every new view");
            verify(button.enabled, "An explicit background enables subtraction before any fit");
            const low = layer.displayMin, high = layer.displayMax;
            mouseClick(button, button.width / 2, button.height / 2);
            verify(waitForPolish(chart), "The subtraction toggle reaches the actual measured-data layer");
            fuzzyCompare(layer.displayMin, low - 17, 1e-6, "The shown lower intensity subtracts the project's own constant background");
            fuzzyCompare(layer.displayMax, high - 17, 1e-6, "The shown upper intensity subtracts the same unfitted background");
            mouseClick(button, button.width / 2, button.height / 2);
            verify(waitForPolish(chart), "Turning subtraction off restores the real measured samples");
            fuzzyCompare(layer.displayMin, low, 1e-6, "Subtraction is a reversible display transformation");
        }
        function test_pattern_subtracts_each_measured_point() {
            openScan("stacked");
            Session.project.currentExperimentIndex = 1;
            Preferences.patternMeasuredStyle = "linePoints";
            tryCompare(Session.project, "calculating", false, 8000, "The selected scan row finishes loading before the Pattern observer is attached");
            chart.destroy();
            chart = patternFactory.createObject(surface, {
                experiment: Session.project.currentExperiment
            });
            verify(chart !== null && waitForPolish(chart), "The Pattern witness draws the same explicit-background project");
            const button = subtractButton();
            compare(button.checked, false, "Pattern also starts with subtraction off");
            const measured = Render.series(chart).find(series => series.objectName === "chart.series.meas");
            verify(measured !== undefined && measured.count > 0, "The independent point observer reaches the actual measured Graphs series");
            tryVerify(() => Array.from({
                    length: measured.count
                }, (_, i) => measured.at(i).y).some(value => isFinite(value)), 5000, "The Pattern actor waits for finite measured samples from the selected scan row");
            function checkPoints(expected) {
                let finitePoints = 0;
                for (let i = 0; i < measured.count; ++i) {
                    const point = measured.at(i);
                    if (isNaN(point.x) || isNaN(point.y)) {
                        verify(isNaN(point.x) && isNaN(point.y), "An excluded-range gap uses a complete NaN point");
                        continue;
                    }
                    const sample = (point.x - 10) * 40;
                    verify(sample >= -1e-6 && sample <= 4096 + 1e-6, "Every drawn x coordinate lies in the independently written scan range");
                    fuzzyCompare(sample, Math.round(sample), 1e-6, "Every drawn x coordinate remains on the independent measured grid");
                    fuzzyCompare(point.y, expected, 1e-6, "Every drawn Pattern point equals the independently written row intensity minus its set background");
                    ++finitePoints;
                }
                verify(finitePoints > 0, "The subtraction witness checks finite measured intensities as well as gap markers");
            }
            checkPoints(128);
            mouseClick(button, button.width / 2, button.height / 2);
            verify(waitForPolish(chart), "Pattern applies subtraction to its real measured series");
            checkPoints(128 - 17);
            mouseClick(button, button.width / 2, button.height / 2);
            verify(waitForPolish(chart), "Pattern restores the measured samples when subtraction is turned off");
            checkPoints(128);
        }
        function test_no_background_disables_subtraction() {
            openScan("map", 3, true);
            const button = subtractButton();
            compare(button.available, false, "No shown pattern with a defined background makes subtraction unavailable");
            compare(button.active, false, "Unavailable subtraction has the actual disabled appearance");
            const before = button.checked;
            mouseClick(button, button.width / 2, button.height / 2);
            compare(button.checked, before, "A real click on unavailable subtraction cannot change its state");
            verify(/background/i.test(String(button.toolTip)) && /no|not|set|defined/i.test(String(button.toolTip)), "The disabled button explains that no background is defined");
        }
        function test_short_legend_and_selection() {
            openScan("stacked", 162);
            const toggle = items(chart).find(item => /legend/i.test(String(item.toolTip)) && typeof item.checked === "boolean");
            verify(toggle !== undefined, "Stacked has the same real show/hide legend control as Pattern");
            if (!toggle.checked)
                mouseClick(toggle, toggle.width / 2, toggle.height / 2);
            const legend = items(chart).find(item => item.visible && item.entries !== undefined && String(item.objectName).toLowerCase().includes("legend"));
            verify(legend !== undefined, "Showing Stacked's legend exposes a real legend model");
            verify(legend.entries.count <= 4, "A large scan has a short legend with a count instead of all pattern names");
            Session.project.currentExperimentIndex = 78;
            Preferences.chartHighlightSelected = true;
            verify(waitForPolish(chart), "Changing the selected pattern updates the legend");
            const selectedName = "row_078.dat";
            const plain = item => String(item.text).replace(/<[^>]*>/g, "");
            const selected = Render.texts(legend).filter(item => plain(item).includes(selectedName) || /646[.,]345/.test(plain(item)));
            verify(selected.length > 0, "The short legend always includes a selected middle pattern");
            const axis = findChild(chart, "scanView.stacked.rowLabel.78");
            verify(axis !== null && axis.visible, "Highlight selected retains the selected row name on the Stacked axis");
            verify(items(legend).some(item => item.key === "78" && String(item.color) === String(axis.textColor)), "The selected legend name keeps its dataset colour, matching the retained axis name");
            Preferences.chartHighlightSelected = false;
            verify(waitForPolish(chart), "All-colour mode updates the selected label and short legend");
            verify(axis.segments.some(segment => segment.bold === true), "The selected axis name is bold in all-colour mode");
            verify(items(legend).some(item => item.key === "78" && item.selected === true), "The selected legend name is bold in all-colour mode");
            mouseClick(toggle, toggle.width / 2, toggle.height / 2);
            compare(legend.visible, false, "The legend button hides the Stacked legend");
        }
    }
}
