// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtTest
import edi.app
import ReportAcceptance 1.0
import EdiAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "ApprovedPalette.js" as Approved
import "RenderedTable.js" as Render
import "../../fixtures/scan_views/input.js" as Input
import "../../fixtures/scan_views/oklab.js" as Oklab

Rectangle {
    id: surface
    width: 1200
    height: 850
    color: "white"
    Component {
        id: factory
        ScanViewChart {
            width: 1100
            height: 760
            shown: false
        }
    }
    Component {
        id: patternReferenceFactory
        PatternChart {
            visible: false
            shown: false
            width: 800
            height: 500
        }
    }
    TestCase {
        id: test
        name: "ScanViewContent"
        when: windowShown
        property var chart
        property var samples: JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/viridis.json")).samples
        function cleanup() {
            if (chart)
                chart.destroy();
            chart = null;
            Session.closeProject();
        }
        function open(mode, kind = "bands") {
            Style.Colors.theme = Style.Colors.LightTheme;
            Preferences.colourScheme = "ediNatural";
            Preferences.patternYScale = "linear";
            if (typeof Preferences.scanMapColours === "string")
                Preferences.scanMapColours = "viridis";
            if (typeof Preferences.scanStackedPalette === "string")
                Preferences.scanStackedPalette = "ediNatural";
            const location = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/scan_template/project"));
            Input.prepare(SettingsProof, location, kind);
            verify(Session.openProject(location), "The scan actor opens a private real project with independent analytic datasets");
            compare(Session.project.experiments.count, 3, "Every analytic dataset appears in the real scan selector");
            Session.project.currentExperimentIndex = 1;
            chart = factory.createObject(surface, {
                project: Session.project,
                mode
            });
            verify(chart !== null, "The actor creates the production scan view, initially without reading");
            return Session.project.scanViews;
        }
        function ready(scan) {
            chart.shown = true;
            tryCompare(scan, "loaded", scan.count, 8000, "Every listed dataset finishes its asynchronous read");
            surface.Window.window.update();
            verify(waitForPolish(chart) && waitForRendering(chart), "The actual scan drawing has a completed frame");
            const reverse = Render.descendants(chart).find(item => item.visible && typeof item.checked === "boolean" && /reverse/i.test(String(item.objectName) + " " + item.toolTip));
            if (reverse && reverse.checked) {
                mouseClick(reverse, reverse.width / 2, reverse.height / 2);
                tryCompare(reverse, "checked", false, 1000, "Each independent scan witness explicitly starts with forward colours");
                verify(waitForRendering(chart), "The forward palette setup reaches a completed frame");
            }
        }
        function named(suffix) {
            const item = findChild(chart, "scanView." + chart.mode + "." + suffix);
            verify(item !== null, "The scan actor reaches its actual " + suffix + " item");
            return item;
        }
        function test_current_row_tracks_async_coordinates_data() {
            return [
                {
                    tag: "stacked",
                    mode: "stacked"
                },
                {
                    tag: "map",
                    mode: "map"
                }
            ];
        }
        function test_current_row_tracks_async_coordinates(data) {
            const scan = open(data.mode);
            const marker = named("current");
            compare(scan.loaded, 0, "The marker is observed before background reading starts");
            compare(scan.rowOf(1), 1, "The selected dataset begins at its independent file-index position");
            ready(scan);
            compare(Session.project.currentExperimentIndex, 1, "The selected dataset remains unchanged throughout asynchronous placement");
            compare(scan.rowOf(1), 250, "The second independent TEMP field becomes the scan coordinate");
            const axes = named("axes"), layer = named("layer");
            const expected = (axes.axisY.max - 250) / (axes.axisY.max - axes.axisY.min) * layer.height;
            verify(marker.visible && Math.abs(marker.mapToItem(layer, 0, marker.height / 2).y - expected) <= 1, "The drawn marker centre lies at the selected physical scan coordinate");
            compare(marker.width, layer.width, "The current pattern is marked by a full-width horizontal line");
            verify(marker.height >= 1 && marker.visible, "The selected Map pattern has visible line ink even with no fit running");
        }
        function test_unreadable_pattern_is_visibly_refused_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_unreadable_pattern_is_visibly_refused(data) {
            const scan = open(data.mode, "broken");
            ready(scan);
            verify(scan.error.length > 0, "The deliberately malformed pattern produces a real read refusal");
            const texts = Render.texts(chart).map(item => item.text).join(" ");
            verify(texts.includes("all594791.dat") && /error|fail|read|invalid|refus/i.test(texts), "Both real scan views visibly identify and explain the unreadable dataset");
        }
        function test_map_key_and_image_use_frozen_interior_samples() {
            const scan = open("map");
            Preferences.patternYScale = "linear";
            ready(scan);
            const layer = named("layer"), image = grabImage(chart);
            compare(scan.xMin, 10, "The analytic map reads its declared x minimum");
            fuzzyCompare(scan.xMax, 112.4, 1e-9, "The analytic map reads its declared x maximum");
            compare(layer.displayMin, 0, "The map normalization starts at the independent zero-intensity band");
            compare(layer.displayMax, 255, "The map normalization ends at the independent maximum-intensity band");
            verify(image.width > 300 && image.height > 100, "The colormap witness captures actual nonempty Map pixels");
            const bars = Render.descendants(chart).filter(item => item !== chart && item.width > 2 && item.width < 40 && item.height > layer.height * 0.8 && item.x > 0);
            const bar = bars.find(item => item.mapToItem(chart, 0, 0).x > layer.mapToItem(chart, layer.width, 0).x);
            verify(bar !== undefined, "The quantitative colour key is a real drawn item beside the image");
            function pixel(item, x, y) {
                const point = item.mapToItem(chart, x, y);
                return image.pixel(Math.round(point.x), Math.round(point.y));
            }
            for (let i = 1; i < samples.length - 1; ++i) {
                const sample = samples[i];
                const expected = sample.rgb.map(value => Math.floor(value * 255 + 0.5));
                const imagePixel = pixel(layer, (i + 0.5) / 7 * layer.width, layer.height * 0.2);
                const keyPixel = pixel(bar, bar.width / 2, (1 - sample.index / 255) * (bar.height - 1));
                for (const [pixel, name] of [[imagePixel, "image"], [keyPixel, "key"]])
                    for (const [channel, index] of [["r", 0], ["g", 1], ["b", 2]])
                        verify(Math.abs(Math.round(pixel[channel] * 255) - expected[index]) <= 1, "The real " + name + " pixel equals the independently frozen viridis interior sample " + sample.index + " channel " + channel + "; actual=" + pixel + "; expected=" + expected);
            }
        }
        function test_map_interpolates_between_neighboring_patterns() {
            const scan = open("map", "rows");
            ready(scan);
            const layer = named("layer"), image = grabImage(chart), axes = named("axes");
            const x = Math.floor(layer.width * 0.4);
            const y = value => Math.round((axes.axisY.max - value) / (axes.axisY.max - axes.axisY.min) * (layer.height - 1));
            function pixel(py) {
                const point = layer.mapToItem(chart, x, py);
                return image.pixel(Math.round(point.x), Math.round(point.y));
            }
            const first = pixel(y(100)), second = pixel(y(250));
            verify(String(first) !== String(second), "Independent constant-intensity datasets establish distinct neighboring row colours");
            const colours = new Set();
            for (let py = y(250) + 2; py < y(100) - 2; ++py) {
                const current = pixel(py);
                colours.add(String(current));
                if (py > y(250) + 3) {
                    const previous = pixel(py - 1);
                    verify(Math.max(...["r", "g", "b"].map(c => Math.abs(current[c] - previous[c]))) < 0.04, "Adjacent Map pixels change smoothly without a row boundary jump");
                }
            }
            verify(colours.size > 8, "Between neighboring datasets the actual Map draws many interior colours rather than constant row bands");
        }
        function ink(pixel, expected, background = ({
                r: 1,
                g: 1,
                b: 1
            })) {
            const channels = ["r", "g", "b"];
            let lower = 0, upper = 1;
            for (const channel of channels) {
                const span = expected[channel] - background[channel];
                if (span === 0) {
                    if (Math.abs(pixel[channel] - background[channel]) > 1 / 255)
                        return false;
                    continue;
                }
                const a = (pixel[channel] - background[channel] - 1 / 255) / span;
                const b = (pixel[channel] - background[channel] + 1 / 255) / span;
                lower = Math.max(lower, Math.min(a, b));
                upper = Math.min(upper, Math.max(a, b));
            }
            return lower > 0 && lower <= upper && upper <= 1;
        }
        function test_antialiased_ink_observer() {
            const olive = {
                r: 189 / 255,
                g: 223 / 255,
                b: 38 / 255
            };
            verify(ink({
                r: 223 / 255,
                g: 238 / 255,
                b: 147 / 255
            }, olive), "The ink observer accepts a common half-coverage alpha with independent one-byte channel quantization");
            verify(!ink({
                r: 225 / 255,
                g: 238 / 255,
                b: 147 / 255
            }, olive), "The ink observer rejects channels outside a common alpha interval at the same one-byte bound");
            const blue = {
                r: 0,
                g: 0,
                b: 1
            };
            verify(ink({
                r: 0.5,
                g: 0.5,
                b: 1
            }, blue), "The independent observer admits half-coverage blue antialiasing over white");
            verify(!ink({
                r: 1,
                g: 1,
                b: 1
            }, blue), "The independent observer rejects an undrawn white pattern");
            verify(!ink({
                r: 1,
                g: 0,
                b: 0
            }, blue), "The independent observer rejects ink of an unrelated colour");
        }
        function test_every_pattern_is_drawn_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_every_pattern_is_drawn(data) {
            const scan = open(data.mode, "rows");
            ready(scan);
            const layer = named("layer"), axes = named("axes");
            const colours = data.mode === "stacked" ? Approved.colours(SettingsProof, "ediNatural", "measured", 3, false) : ["#440154", "#21918c", "#fde725"];
            for (let index = 0; index < 3; ++index) {
                if (data.mode === "map") {
                    Session.project.currentExperimentIndex = (index + 1) % 3;
                    verify(waitForRendering(chart), "The selected-row overlay moves away from each independent map-row sample");
                }
                const frame = grabImage(chart);
                const coordinate = [100, 250, 700][index] + (data.mode === "stacked" ? [0, 128, 255][index] / 255 * scan.stackHeight : 0);
                const py = (axes.axisY.max - coordinate) / (axes.axisY.max - axes.axisY.min) * layer.height;
                const at = layer.mapToItem(chart, layer.width * 0.4, py);
                let present = false;
                for (let dy = -2; dy <= 2; ++dy) {
                    const pixel = frame.pixel(Math.round(at.x), Math.round(at.y) + dy);
                    const expected = {
                        r: parseInt(colours[index].slice(1, 3), 16) / 255,
                        g: parseInt(colours[index].slice(3, 5), 16) / 255,
                        b: parseInt(colours[index].slice(5, 7), 16) / 255
                    };
                    present = present || ink(pixel, expected);
                }
                verify(present, "The actual " + data.mode + " view draws independently specified pattern " + index + " at its physical scan coordinate");
            }
        }
        function test_scan_top_margin_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_scan_top_margin(data) {
            const scan = open(data.mode);
            ready(scan);
            const plot = named("layer").mapToItem(chart, 0, 0);
            verify(plot.y > 0, "The scan plot keeps a positive top margin for its labels");
            for (const text of Render.texts(chart)) {
                const point = text.mapToItem(chart, 0, 0);
                verify(point.y >= 0 && point.y + text.height <= chart.height + 0.5, "Every scan label, including the Map maximum, fits inside the view");
            }
        }
        function test_selected_map_line_is_always_drawn() {
            const scan = open("map");
            ready(scan);
            const marker = named("current"), layer = named("layer");
            for (const index of [0, 2, 1]) {
                Session.project.currentExperimentIndex = index;
                const axes = named("axes");
                const expectedY = (axes.axisY.max - [100, 250, 700][index]) / (axes.axisY.max - axes.axisY.min) * layer.height;
                const inside = Math.max(marker.height / 2, Math.min(layer.height - marker.height / 2, expectedY));
                verify(Math.abs(marker.mapToItem(layer, 0, marker.height / 2).y - inside) <= 1, "Selecting a pattern centres its line at the independent temperature, clamped inside the plot at its edges");
                verify(marker.visible && marker.width === layer.width, "The Map keeps a visible full-width current-pattern line outside a running fit");
                surface.Window.window.update();
                verify(waitForRendering(chart), "The selected Map line reaches an actual completed frame");
            }
        }
        function axisControl(axis) {
            const controls = Render.descendants(chart).filter(item => item.visible && item.count > 1 && typeof item.currentIndex === "number");
            const expression = new RegExp("(?:[. _-]|^)" + axis + "(?:axis|scale|type|[. _-])|" + axis + "[ -]axis", "i");
            const found = controls.find(item => expression.test(String(item.objectName) + " " + item.toolTip + " " + (item.closedTexts || []).join(" ")));
            verify(found !== undefined, "The real scan toolbar has an independent " + axis + " axis-type control");
            return found;
        }
        function choose(control, index) {
            mouseClick(control, control.width / 2, control.height / 2);
            tryCompare(control.popup, "opened", true, 1000, "Real input opens the requested scan selector");
            verify(SettingsProof.key(control, Qt.Key_Home), "Home reaches the actual scan selector window");
            for (let step = 0; step < index; ++step)
                verify(SettingsProof.key(control, Qt.Key_Down), "Down reaches the actual scan selector window");
            verify(SettingsProof.key(control, Qt.Key_Return), "Return commits the actual scan selector choice");
            tryCompare(control, "currentIndex", index, 1000, "Real input chooses the requested scan axis or palette type");
            tryCompare(control.popup, "visible", false, 1000, "The real popup finishes closing before another scan input");
            surface.Window.window.update();
            verify(waitForRendering(chart), "The selected scan setting reaches an actual frame");
        }
        function plotDigest() {
            const layer = named("layer"), frame = grabImage(chart), colours = [];
            for (let x = 1; x < 16; ++x)
                for (let y = 1; y < 16; ++y) {
                    const at = layer.mapToItem(chart, layer.width * x / 16, layer.height * y / 16);
                    colours.push(String(frame.pixel(Math.round(at.x), Math.round(at.y))));
                }
            return colours.join(",");
        }
        function test_independent_axis_type_buttons_data() {
            const rows = [];
            for (const mode of ["stacked", "map"])
                for (const axis of ["x", "y", "z"])
                    rows.push({
                        tag: mode + "-" + axis,
                        mode,
                        axis
                    });
            return rows;
        }
        function test_independent_axis_type_buttons(data) {
            const scan = open(data.mode);
            ready(scan);
            const control = axisControl(data.axis), original = control.currentIndex, before = plotDigest();
            choose(control, (original + 1) % control.count);
            verify(plotDigest() !== before, "Changing the " + data.axis + " type changes actual scan plot pixels, beyond the button's label");
            choose(control, original);
            compare(plotDigest(), before, "Restoring the axis type restores the same actual analytic scan drawing");
        }
        function test_zoom_stays_on_and_reset_restores_axes_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_zoom_stays_on_and_reset_restores_axes(data) {
            const scan = open(data.mode);
            ready(scan);
            const items = Render.descendants(chart);
            const zoom = items.find(item => item.visible && typeof item.checked === "boolean" && /zoom/i.test(String(item.objectName) + " " + item.toolTip));
            const reset = items.find(item => item.visible && /reset.*ax|ax.*reset/i.test(String(item.objectName) + " " + item.toolTip));
            verify(zoom !== undefined && reset !== undefined, "Both scan toolbars carry the actual box-zoom toggle and reset-axes action");
            compare(zoom.checked, true, "Scan box zoom starts on");
            if (zoom.enabled)
                mouseClick(zoom, zoom.width / 2, zoom.height / 2);
            compare(zoom.checked, true, "A user cannot turn scan zoom off");
            const axes = named("axes"), pointer = named("pointer");
            const full = [axes.axisX.min, axes.axisX.max, axes.axisY.min, axes.axisY.max];
            mouseDrag(pointer, pointer.width * 0.2, pointer.height * 0.2, pointer.width * 0.5, pointer.height * 0.5);
            tryVerify(() => axes.axisX.max - axes.axisX.min < full[1] - full[0] && axes.axisY.max - axes.axisY.min < full[3] - full[2], 1000, "Real box input zooms both scan axes");
            mouseClick(reset, reset.width / 2, reset.height / 2);
            tryVerify(() => [axes.axisX.min, axes.axisX.max, axes.axisY.min, axes.axisY.max].every((value, index) => Math.abs(value - full[index]) <= Math.max(1, Math.abs(full[index])) * 1e-9), 1000, "The real reset action restores both complete analytic scan ranges");
            compare(zoom.checked, true, "Zoom remains on after reset");
        }
        function test_background_to_experiment_ramp_data() {
            const cases = [];
            for (const mode of ["stacked", "map"])
                for (const dark of [false, true])
                    cases.push({
                        tag: mode + (dark ? "-dark" : "-light"),
                        mode,
                        dark
                    });
            return cases;
        }
        function test_background_to_experiment_ramp(data) {
            const scan = open(data.mode, data.mode === "stacked" ? "rows" : "bands");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            const choices = data.mode === "map" ? chart.mapChoices : chart.stackedChoices;
            verify(choices !== undefined, "The actual scan menu exposes the offered ramp choices");
            const selector = findChild(chart, "scanView." + data.mode + ".toolbar." + (data.mode === "map" ? "colourMap" : "palette"));
            verify(selector !== null, "The ramp observer operates the actual palette selector");
            const schemes = Approved.reference(SettingsProof).schemes;
            const pattern = createTemporaryObject(patternReferenceFactory, surface, {
                experiment: Session.project.currentExperiment
            });
            verify(pattern !== null, "The ramp reference is the actual single-pattern chart in the current theme");
            let offered = 0;
            for (let choice = 0; choice < choices.length; ++choice) {
                if (!String(choices[choice]).startsWith("ramp:"))
                    continue;
                ++offered;
                const scheme = schemes.find(row => row.id === choices[choice].slice(5));
                verify(scheme !== undefined, "Every offered ramp ends at an independently approved experiment colour");
                choose(selector, choice);
                const expected = [String(pattern.colors.chartBackground), scheme.palette[data.dark ? "dark" : "light"].measured[0]];
                const layer = named("layer"), axes = named("axes"), frame = grabImage(chart);
                if (data.mode === "map") {
                    for (const index of [0, 1]) {
                        const point = layer.mapToItem(chart, layer.width * (index ? 6.5 : 0.5) / 7, layer.height * 0.2);
                        compare(String(frame.pixel(Math.round(point.x), Math.round(point.y))).toLowerCase(), expected[index].toLowerCase(), "Every Map ramp starts at the Pattern plot background and ends at its main experiment colour");
                    }
                } else {
                    for (let row = 0; row < 3; ++row) {
                        const coordinate = [100, 250, 700][row] + [0, 128, 255][row] / 255 * scan.stackHeight;
                        const py = (axes.axisY.max - coordinate) / (axes.axisY.max - axes.axisY.min) * layer.height;
                        const point = layer.mapToItem(chart, layer.width * 0.4, py);
                        const place = Math.round((0.25 + 0.75 * row / 2) * 255) / 255;
                        const colour = Oklab.gradient(expected[0], expected[1], place);
                        const rgb = {
                            r: parseInt(colour.slice(1, 3), 16) / 255,
                            g: parseInt(colour.slice(3, 5), 16) / 255,
                            b: parseInt(colour.slice(5, 7), 16) / 255
                        };
                        verify(colour !== expected[0].toLowerCase(), "ADR-0041's quarter-ramp start gives every Stacked trace a colour distinct from the Pattern background");
                        let present = false;
                        for (let dy = -2; dy <= 2; ++dy)
                            present = present || ink(frame.pixel(Math.round(point.x), Math.round(point.y) + dy), rgb, chart.colors.chartBackground);
                        verify(present, "Every Stacked ramp pattern has actual drawable ink in its independently mixed inset colour");
                    }
                }
            }
            verify(offered > 0, "Both scan palette selectors offer background-to-experiment ramps in both themes");
        }
        function test_offered_maps_are_readable_in_both_themes_data() {
            const rows = [];
            for (const mode of ["stacked", "map"])
                for (const dark of [false, true])
                    rows.push({
                        tag: mode + (dark ? "-dark" : "-light"),
                        mode,
                        dark
                    });
            return rows;
        }
        function test_offered_maps_are_readable_in_both_themes(data) {
            const scan = open(data.mode, data.mode === "stacked" ? "rows" : "bands");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            const references = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/maps.json"));
            const choices = data.mode === "map" ? chart.mapChoices : chart.stackedChoices;
            verify(choices !== undefined && choices.length > 1, "The real view exposes its offered palette choices for independent source matching");
            const selector = findChild(chart, "scanView." + data.mode + ".toolbar." + (data.mode === "map" ? "colourMap" : "palette"));
            verify(selector !== null, "The published-map observer uses the actual palette selector");
            const categorical = Approved.reference(SettingsProof).schemes.map(row => row.id);
            let offered = 0;
            for (let index = 0; index < choices.length; ++index) {
                const name = choices[index];
                if (String(name).startsWith("ramp:") || categorical.includes(name))
                    continue;
                const reference = references[name];
                verify(reference !== undefined && reference.license && reference.source, "Every offered map has an independent published source and bundling licence, without a fixed whitelist: " + name);
                ++offered;
                choose(selector, index);
                const layer = named("layer"), axes = named("axes"), frame = grabImage(chart);
                if (data.mode === "map") {
                    for (const [band, place] of [[1, 32], [3, 96], [5, 192]]) {
                        const point = layer.mapToItem(chart, layer.width * (band + 0.5) / 7, layer.height * 0.2);
                        const pixel = frame.pixel(Math.round(point.x), Math.round(point.y));
                        const expected = reference.colours[place];
                        for (const [channel, offset] of [["r", 1], ["g", 3], ["b", 5]])
                            verify(Math.abs(Math.round(pixel[channel] * 255) - parseInt(expected.slice(offset, offset + 2), 16)) <= 1, "The actual Map retains a published interior intensity colour in both themes: " + name);
                    }
                } else {
                    for (let row = 0; row < 3; ++row) {
                        const coordinate = [100, 250, 700][row] + [0, 128, 255][row] / 255 * scan.stackHeight;
                        const py = (axes.axisY.max - coordinate) / (axes.axisY.max - axes.axisY.min) * layer.height;
                        const point = layer.mapToItem(chart, layer.width * 0.4, py);
                        const colour = reference.colours[Math.round((0.1 + 0.8 * row / 2) * 255)];
                        const expected = {
                            r: parseInt(colour.slice(1, 3), 16) / 255,
                            g: parseInt(colour.slice(3, 5), 16) / 255,
                            b: parseInt(colour.slice(5, 7), 16) / 255
                        };
                        const bg = chart.colors.chartBackground;
                        let present = false;
                        for (let dy = -2; dy <= 2; ++dy)
                            present = present || ink(frame.pixel(Math.round(point.x), Math.round(point.y) + dy), expected, bg);
                        verify(present, "Each stacked pattern has real published-map ink against the current theme background: " + name + " row=" + row + " expected=" + colour + " background=" + bg + " samples=" + JSON.stringify([-2, -1, 0, 1, 2].map(dy => String(frame.pixel(Math.round(point.x), Math.round(point.y) + dy)))));
                    }
                }
                verify(chart.colors.chartLabels !== chart.colors.chartBackground, "The map's axis and key labels remain visible against the theme background");
            }
            verify(offered > 1, "Both views offer multiple sourced maps beside the background ramps");
        }
        function test_map_reverse_and_key_data() {
            const cases = [];
            for (const reverse of [false, true])
                for (const dark of [false, true])
                    cases.push({
                        tag: (reverse ? "reversed" : "forward") + (dark ? "-dark" : "-light"),
                        reverse,
                        dark
                    });
            return cases;
        }
        function test_map_reverse_and_key(data) {
            const scan = open("map");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            const toggle = Render.descendants(chart).find(item => item.visible && typeof item.checked === "boolean" && /reverse/i.test(String(item.objectName) + " " + item.toolTip));
            verify(toggle !== undefined && toggle.enabled, "The Map toolbar exposes an actual reverse switch");
            const choices = chart.mapChoices;
            const reference = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/maps.json"));
            const selector = findChild(chart, "scanView.map.toolbar.colourMap");
            verify(selector !== null && choices !== undefined, "Reversal operates the real offered Map palette selector");
            const pattern = createTemporaryObject(patternReferenceFactory, surface, {
                experiment: Session.project.currentExperiment
            });
            verify(pattern !== null, "Reversed ramps use the actual Pattern plot background as their relational input");
            const schemes = Approved.reference(SettingsProof).schemes;
            const layer = named("layer");
            const bars = Render.descendants(chart).filter(item => item !== chart && item.width > 2 && item.width < 40 && item.height > layer.height * 0.8 && item.x > 0);
            const bar = bars.find(item => item.mapToItem(chart, 0, 0).x > layer.mapToItem(chart, layer.width, 0).x);
            verify(bar !== undefined, "The reverse witness reaches the actual drawn quantitative colour key");
            for (const requested of [!data.reverse, data.reverse]) {
                if (toggle.checked !== requested)
                    mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                tryCompare(toggle, "checked", requested, 1000, "Real pointer input changes the reverse choice in both directions");
                for (let choice = 0; choice < choices.length; ++choice) {
                    const name = choices[choice];
                    const ramp = String(name).startsWith("ramp:");
                    const scheme = ramp ? schemes.find(row => row.id === String(name).slice(5)) : null;
                    verify(ramp ? scheme !== undefined : reference[name] !== undefined && reference[name].license, "Every offered reversible map has an independent published table/licence or approved ramp operands");
                    choose(selector, choice);
                    const frame = grabImage(chart);
                    for (const [band, index] of [[1, 32], [3, 96], [5, 192]]) {
                        const place = requested ? 255 - index : index;
                        const expected = ramp ? Oklab.gradient(String(pattern.colors.chartBackground), scheme.palette[data.dark ? "dark" : "light"].measured[0], place / 255) : reference[name].colours[place];
                        for (const [item, x, y] of [[layer, layer.width * (band + 0.5) / 7, layer.height * 0.2], [bar, bar.width / 2, bar.height * (1 - index / 255)]]) {
                            const at = item.mapToItem(chart, x, y), pixel = frame.pixel(Math.round(at.x), Math.round(at.y));
                            for (const [channel, offset] of [["r", 1], ["g", 3], ["b", 5]])
                                verify(Math.abs(Math.round(pixel[channel] * 255) - parseInt(expected.slice(offset, offset + 2), 16)) <= 1, "Forward and reversed image and key use the same independent interior table sample: " + name);
                        }
                    }
                }
            }
            const restored = SettingsProof.restart('import QtQuick; import edi.app; Item { ScanViewChart { id: view; mode: "map"; width: 1100; height: 760 } function walk(item) { let all = [item]; for (const child of item.children || []) all = all.concat(walk(child)); return all; } readonly property var toggle: walk(view).find(item => typeof item.checked === "boolean" && /reverse/i.test(String(item.objectName) + " " + item.toolTip)); property bool found: toggle !== undefined; property bool checked: toggle ? toggle.checked : false }');
            verify(!restored.error && restored.found, "A fresh production engine restores the actual Map reverse control");
            compare(restored.checked, data.reverse, "The reverse choice survives a fresh settings engine in both directions");
        }
        function interpolationToggle(root) {
            return Render.descendants(root).find(item => typeof item.checked === "boolean" && /smooth|stepp|interpol/i.test(String(item.objectName) + " " + item.toolTip));
        }
        function mapStrip() {
            const layer = named("layer"), axes = named("axes"), marker = named("current"), frame = grabImage(chart), strip = [];
            for (let py = 2; py < layer.height - 2; ++py) {
                if (Math.abs(py - marker.y) <= marker.height + 1)
                    continue;
                const at = layer.mapToItem(chart, layer.width * 0.4, py);
                const value = axes.axisY.max - py / layer.height * (axes.axisY.max - axes.axisY.min);
                strip.push({
                    pixel: frame.pixel(Math.round(at.x), Math.round(at.y)),
                    value,
                    py
                });
            }
            return strip;
        }
        function smoothStrip(strip) {
            return new Set(strip.map(row => String(row.pixel))).size > 3;
        }
        function test_map_interpolation_default() {
            Preferences.resetToDefaults();
            const scan = open("map", "rows");
            ready(scan);
            verify(interpolationToggle(chart) !== undefined, "The Map toolbar exposes its actual stepped/smooth toggle");
            verify(smoothStrip(mapStrip()), "A new profile defaults to smoothly interpolated colour between the analytic datasets");
        }
        function test_map_interpolation_toggle_data() {
            const rows = [];
            for (const smooth of [false, true])
                for (const dark of [false, true])
                    rows.push({
                        tag: (smooth ? "smooth" : "stepped") + (dark ? "-dark" : "-light"),
                        smooth,
                        dark
                    });
            return rows;
        }
        function test_map_interpolation_toggle(data) {
            const scan = open("map", "rows");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            const toggle = interpolationToggle(chart);
            verify(toggle !== undefined && toggle.visible && toggle.enabled, "A real Map toolbar toggle chooses stepped or smooth colour");
            if (smoothStrip(mapStrip()) !== data.smooth) {
                mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                surface.Window.window.update();
                verify(waitForRendering(chart), "The actual interpolation toggle reaches a completed Map frame");
            }
            const strip = mapStrip(), background = String(chart.colors.chartBackground);
            compare(smoothStrip(strip), data.smooth, "Real input selects the requested interpolation rather than only changing its icon");
            verify(strip.length > 20 && strip.every(row => String(row.pixel) !== background), "Neither interpolation mode exposes background seams between any neighboring datasets");
            const table = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/maps.json")).viridis.colours;
            if (!data.smooth) {
                for (const row of strip) {
                    // Exact bands meet at the independently known neighbour midpoints.
                    if (Math.abs(row.value - 175) < (chart.yMax - chart.yMin) / named("layer").height || Math.abs(row.value - 475) < (chart.yMax - chart.yMin) / named("layer").height)
                        continue;
                    const expected = table[row.value < 175 ? 0 : row.value < 475 ? 128 : 255];
                    compare(String(row.pixel).toLowerCase(), expected.toLowerCase(), "Each stepped dataset band keeps its independent published intensity colour, without a gradient inside the band");
                }
            } else {
                let maximumStep = 0;
                for (let index = 1; index < table.length; ++index)
                    for (const offset of [1, 3, 5])
                        maximumStep = Math.max(maximumStep, Math.abs(parseInt(table[index].slice(offset, offset + 2), 16) - parseInt(table[index - 1].slice(offset, offset + 2), 16)));
                const minimumPixels = named("layer").height * 150 / (chart.yMax - chart.yMin);
                const bound = (Math.ceil(128 / minimumPixels) + 1) * maximumStep + 1;
                for (let index = 1; index < strip.length; ++index) {
                    if (strip[index].py !== strip[index - 1].py + 1)
                        continue;
                    verify(["r", "g", "b"].every(channel => Math.abs(strip[index].pixel[channel] - strip[index - 1].pixel[channel]) * 255 <= bound), "Smooth colour has no band jump beyond the independently derived table and pixel-step bound");
                }
            }
            const checked = toggle.checked;
            const fresh = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property Item view: ScanViewChart { mode: "map" }; function walk(item) { let all = [item]; for (const child of item.children || []) all = all.concat(walk(child)); return all; } property var toggles: walk(view).filter(item => typeof item.checked === "boolean" && /smooth|stepp|interpol/i.test(String(item.objectName) + " " + item.toolTip)); property bool acceptanceReady: toggles.length === 1; property bool saved: toggles.length === 1 ? toggles[0].checked : false }');
            verify(!fresh.error && fresh.acceptanceReady, "A fresh production QML engine reloads the real interpolation control");
            compare(fresh.saved, checked, "Both actual stepped and smooth choices are remembered in a fresh engine");
        }
        function test_scan_toolbar_and_top_margin_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_scan_toolbar_and_top_margin(data) {
            const scan = open(data.mode);
            ready(scan);
            const controls = Render.descendants(chart).filter(item => item.visible && typeof item.count === "number" && typeof item.currentIndex === "number" && typeof item.textAt === "function");
            const palette = controls.find(item => /palette|colour|color|viridis/i.test(item.objectName + " " + item.toolTip + " " + Array.from({
                    length: item.count
                }, (_, i) => item.textAt(i)).join(" ")));
            verify(palette !== undefined && palette.count > 1, "Both scan views provide an actual palette selector in a second chart-toolbar line");
            const layer = named("layer"), at = palette.mapToItem(chart, 0, 0), plot = layer.mapToItem(chart, 0, 0);
            verify(at.y >= 0 && at.y + palette.height <= plot.y && at.y > 0, "The second toolbar line fits above the scan plot with a positive top margin");
            for (const text of Render.texts(chart)) {
                const point = text.mapToItem(chart, 0, 0);
                verify(point.y >= 0 && point.y + text.height <= chart.height + 0.5, "Every scan axis and colour-key label fits vertically inside the view");
            }
            if (palette.count > 1) {
                const before = grabImage(layer);
                const previous = palette.currentIndex;
                mouseClick(palette, palette.width / 2, palette.height / 2);
                keyClick(Qt.Key_Down);
                keyClick(Qt.Key_Return);
                tryVerify(() => palette.currentIndex !== previous, 1000, "Real input changes the view's palette selector");
                verify(waitForRendering(chart), "The selected palette reaches a real scan frame");
                verify(!before.equals(grabImage(layer)), "Changing the scan palette changes its actual rendered colours");
            }
        }
        function test_owner_axis_name_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_owner_axis_name(data) {
            const scan = open(data.mode);
            ready(scan);
            const selector = axisControl("x");
            for (let index = 0; index < selector.count; ++index) {
                if (!selector.enabled)
                    continue;
                choose(selector, index);
                compare(selector.displayText.replace(/^x:\s*/, ""), selector.textAt(index), "An opened x-axis entry and its selected quantity have exactly the same name");
            }
            verify(selector.count > 1, "The name witness exercises both native and d quantities");
        }
        function test_owner_d_availability_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_owner_d_availability(data) {
            const scan = open(data.mode);
            chart.project = null;
            const selector = axisControl("x");
            compare(selector.currentIndex, 0, "A view with no calculated dataset names its native axis");
            verify(!selector.enabled, "Without calculated data the actual d selector cannot be operated");
            mouseClick(selector, selector.width / 2, selector.height / 2);
            compare(selector.currentIndex, 0, "Actual input cannot select d before a dataset calculation exists");
            chart.project = Session.project;
            ready(scan);
            tryVerify(() => selector.enabled, 8000, "The first real nonzero-wavelength calculation makes d selectable without recreating the chart");
            choose(selector, 1);
            const axes = named("axes");
            const expected = [10, 112.4].map(x => 1.87 / (2 * Math.sin((x - .29) * Math.PI / 360))).sort((a, b) => a - b);
            tryVerify(() => Math.abs(axes.axisX.min - expected[0]) < 1e-5 && Math.abs(axes.axisX.max - expected[1]) < 1e-5, 2000, "Selecting newly available d actually uses the independent nontrivial Bragg conversion at both domain ends");
        }
        function test_owner_toolbar_centred_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_owner_toolbar_centred(data) {
            const scan = open(data.mode);
            ready(scan);
            chart.width = 640;
            verify(waitForPolish(chart) && waitForRendering(chart), "The owner witness lays out the real narrow chart with a second button line");
            const reset = findChild(chart, "scanView." + data.mode + ".toolbar.reset");
            verify(reset !== null && reset.visible, "The second toolbar line contains the real reset control");
            const row = reset.parent;
            const tools = row.children.filter(item => item.visible && item.width > 0);
            const left = Math.min(...tools.map(item => item.mapToItem(chart, 0, 0).x));
            const right = Math.max(...tools.map(item => item.mapToItem(chart, item.width, 0).x));
            const layer = named("layer"), centre = layer.mapToItem(chart, layer.width / 2, 0).x;
            verify(Math.abs((left + right) / 2 - centre) <= 1, "The second toolbar line is horizontally centred above its plot like the Pattern toolbar");
        }
        function test_owner_secondary_click_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_owner_secondary_click(data) {
            const scan = open(data.mode);
            ready(scan);
            const pointer = named("pointer"), axes = named("axes");
            const full = [axes.axisX.min, axes.axisX.max, axes.axisY.min, axes.axisY.max];
            mouseDrag(pointer, pointer.width * .2, pointer.height * .2, pointer.width * .6, pointer.height * .6, Qt.LeftButton);
            tryVerify(() => axes.axisX.max - axes.axisX.min < full[1] - full[0], 1000, "Actual drag creates a non-default scan zoom before resetting it");
            mouseClick(pointer, pointer.width * .45, pointer.height * .45, Qt.RightButton);
            tryVerify(() => [axes.axisX.min, axes.axisX.max, axes.axisY.min, axes.axisY.max].every((x, i) => Math.abs(x - full[i]) < 1e-9), 1000, "An actual secondary click restores both full scan axis ranges");
        }
        function test_owner_zoom_samples_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_owner_zoom_samples(data) {
            const scan = open(data.mode, "zoom");
            ready(scan);
            Session.project.currentExperimentIndex = 0;
            const pointer = named("pointer"), axes = named("axes"), layer = named("layer");
            const values = [0, 17, 230, 41, 180, 64, 255, 11];
            function zoom(left, right) {
                const xmin = axes.axisX.min, xmax = axes.axisX.max;
                const start = (left - xmin) / (xmax - xmin) * pointer.width;
                const end = (right - xmin) / (xmax - xmin) * pointer.width;
                mouseDrag(pointer, start, pointer.height * .01, end - start, pointer.height * .98, Qt.LeftButton);
                tryVerify(() => Math.abs(axes.axisX.min - left) < (xmax - xmin) / pointer.width && Math.abs(axes.axisX.max - right) < (xmax - xmin) / pointer.width, 1000, "Real pointer zoom selects a known interior measured-data interval");
                verify(waitForRendering(chart), "The viewport change reaches the actual scan drawing");
            }
            zoom(30, 90);
            const coarse = grabImage(chart);
            const columns = Math.round(layer.width);
            for (let column = 3; column < columns - 3; column += 17) {
                const left = axes.axisX.min + column / columns * (axes.axisX.max - axes.axisX.min);
                const right = axes.axisX.min + (column + 1) / columns * (axes.axisX.max - axes.axisX.min);
                const visible = [];
                for (let i = Math.ceil((left - 10) * 40); i <= Math.floor((right - 10) * 40 - 1e-8); ++i)
                    visible.push(values[((i % 8) + 8) % 8]);
                if (!visible.length)
                    continue;
                const low = Math.min(...visible), high = Math.max(...visible);
                if (data.mode === "stacked") {
                    const colour = Approved.colours(SettingsProof, "ediNatural", "measured", 3, false)[1];
                    const expected = rgb(colour);
                    for (const intensity of [low, high]) {
                        const y = (axes.axisY.max - (250 + intensity / 255 * scan.stackHeight)) / (axes.axisY.max - axes.axisY.min) * layer.height;
                        const at = layer.mapToItem(chart, column + .5, y);
                        let hit = false;
                        for (let dx = -1; dx <= 1; ++dx)
                            for (let dy = -2; dy <= 2; ++dy)
                                hit = hit || ink(coarse.pixel(Math.round(at.x) + dx, Math.round(at.y) + dy), expected, chart.colors.chartBackground);
                        verify(hit, "A zoomed Stacked pixel column retains the true independently enumerated visible minimum and maximum");
                    }
                    for (const outside of [low - 40, high + 40].filter(value => value > 0 && value < 255)) {
                        const y = (axes.axisY.max - (250 + outside / 255 * scan.stackHeight)) / (axes.axisY.max - axes.axisY.min) * layer.height;
                        const at = layer.mapToItem(chart, column + .5, y);
                        verify(!ink(coarse.pixel(Math.round(at.x), Math.round(at.y)), expected, chart.colors.chartBackground), "A visible-range Stacked column has no spurious ink from extrema outside its actual visible samples");
                    }
                } else {
                    const table = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/maps.json")).viridis.colours;
                    const at = layer.mapToItem(chart, column + .5, layer.height * .2);
                    compare(String(coarse.pixel(Math.round(at.x), Math.round(at.y))).toLowerCase(), table[high].toLowerCase(), "A zoomed Map column uses the true maximum of its visible raw samples rather than a stretched full-range envelope");
                }
            }
            zoom(50, 50.4);
            const frame = grabImage(chart);
            let checked = 0;
            for (let i = 1600; i <= 1616; ++i) {
                const x = 10 + i / 40;
                if (x < axes.axisX.min || x > axes.axisX.max)
                    continue;
                const px = (x - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width;
                const intensity = values[i % 8];
                if (data.mode === "stacked") {
                    const at = layer.mapToItem(chart, px, (axes.axisY.max - (250 + intensity / 255 * scan.stackHeight)) / (axes.axisY.max - axes.axisY.min) * layer.height);
                    const expected = rgb(Approved.colours(SettingsProof, "ediNatural", "measured", 3, false)[1]);
                    let hit = false;
                    for (let dx = -1; dx <= 1; ++dx)
                        for (let dy = -2; dy <= 2; ++dy)
                            hit = hit || ink(frame.pixel(Math.round(at.x) + dx, Math.round(at.y) + dy), expected, chart.colors.chartBackground);
                    verify(hit, "Below pixel resolution the actual zoomed Stacked line passes through each independently specified measured point");
                } else {
                    const at = layer.mapToItem(chart, px, layer.height * .2);
                    const table = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/maps.json")).viridis.colours;
                    const pixel = frame.pixel(Math.round(at.x), Math.round(at.y)), expected = rgb(table[intensity]);
                    verify(["r", "g", "b"].every(c => Math.abs(pixel[c] - expected[c]) <= 3 / 255), "Below pixel resolution the Map retains each real sample intensity without stretching the prior envelope");
                }
                ++checked;
            }
            verify(checked >= 15, "The fine zoom checks the independently known interior samples, including valleys lost by the full-range reduction");
        }
        Component {
            id: evolutionFactory
            EvolutionChart {
                width: 1100
                height: 760
                shown: true
            }
        }
        function test_owner_indicator_data() {
            const cases = [];
            for (const mode of ["stacked", "map", "evolution"])
                for (const dark of [false, true])
                    cases.push({
                        tag: mode + (dark ? "-dark" : "-light"),
                        mode,
                        dark
                    });
            return cases;
        }
        function test_owner_indicator(data) {
            let layer, axes, pointer, marker, value;
            if (data.mode === "evolution") {
                const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/report_evolution/project"));
                verify(Session.openProject(root), "The Evolution indicator uses independently authored three-row saved fit results");
                chart = evolutionFactory.createObject(surface, {
                    project: Session.project
                });
                tryVerify(() => chart.fitted, 3000, "The real Evolution chart loads its saved independent parameter series");
                layer = findChild(chart, "evolution.points");
                axes = findChild(chart, "evolution.view");
                pointer = findChild(chart, "evolution.pointer");
                marker = findChild(chart, "evolution.current");
                value = 311.75;
            } else {
                const scan = open(data.mode, "rows");
                ready(scan);
                layer = named("layer");
                axes = named("axes");
                pointer = named("pointer");
                marker = named("current");
                value = 250;
            }
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            verify(layer !== null && axes !== null && pointer !== null && marker !== null, "Each scan chart supplies a real selected-pattern indicator and plot for pixel inspection");
            Session.project.currentExperimentIndex = 0;
            verify(waitForRendering(chart), "The initial indicator is rendered away from the next selected row");
            const background = grabImage(chart);
            const vertical = data.mode === "evolution";
            const position = vertical ? (value - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width : (axes.axisY.max - value) / (axes.axisY.max - axes.axisY.min) * layer.height;
            mouseClick(pointer, vertical ? position : pointer.width * .6, vertical ? pointer.height * .5 : position);
            tryCompare(Session.project, "currentExperimentIndex", 1, 1000, "Real chart input selects the middle independent dataset on every scan chart");
            verify(waitForRendering(chart), "The newly selected indicator has a completed actual frame");
            compare(vertical ? marker.width : marker.height, 4, "Every selected-pattern indicator occupies exactly four logical pixels");
            const children = marker.children.filter(item => item.visible && item.color !== undefined);
            compare(children.length, 3, "The unified indicator draws one core and two border strips");
            const sorted = children.sort((a, b) => (vertical ? a.x : a.y) - (vertical ? b.x : b.y));
            for (let index = 0; index < 3; ++index) {
                const strip = sorted[index], core = index === 1;
                compare(vertical ? strip.width : strip.height, core ? 2 : 1, "The selected indicator uses a two-pixel core and one-pixel borders");
                const colour = core ? (data.dark ? 1 : 0) : (data.dark ? 0 : 1);
                verify(["r", "g", "b"].every(c => Math.abs(strip.color[c] - colour) < 1e-9) && Math.abs(strip.color.a - (core ? 1 : .5)) < 1e-9, "The actual core and half-transparent border use the exact owner colours for this theme");
                for (const along of [.25, .5, .75]) {
                    const at = strip.mapToItem(chart, vertical ? strip.width / 2 : strip.width * along, vertical ? strip.height * along : strip.height / 2);
                    const actual = grabImage(chart).pixel(Math.floor(at.x), Math.floor(at.y)), before = background.pixel(Math.floor(at.x), Math.floor(at.y));
                    verify(["r", "g", "b"].every(c => Math.abs(actual[c] - (core ? colour : (colour + before[c]) / 2)) <= 1 / 255), "Rendered indicator core and border pixels equal the exact themed alpha composite over the independent pre-selection frame");
                }
            }
            const actualCentre = marker.mapToItem(layer, marker.width / 2, marker.height / 2);
            verify(Math.abs((vertical ? actualCentre.x : actualCentre.y) - position) <= 1, "The indicator centre follows the selected physical coordinate, rather than its top or left edge");
        }
        function excludedButton(root) {
            return Render.descendants(root).find(item => item.visible && typeof item.checked === "boolean" && /exclud.*region|region.*exclud/i.test(String(item.objectName) + " " + item.toolTip));
        }
        function test_owner_excluded_regions_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_owner_excluded_regions(data) {
            const scan = open(data.mode, "excluded");
            ready(scan);
            const pattern = createTemporaryObject(patternReferenceFactory, surface, {
                experiment: Session.project.currentExperiment,
                visible: true,
                shown: true
            });
            verify(pattern !== null, "Excluded-region behaviour is checked against the actual prior Pattern chart");
            const prior = excludedButton(pattern), control = excludedButton(chart);
            verify(prior !== undefined && control !== undefined, "Pattern and both scan toolbars expose the same excluded-regions control");
            const original = SettingsProof.text(Qt.resolvedUrl("file:" + Session.project.path), "experiments/d20.edi");
            for (const root of [pattern, chart]) {
                const button = excludedButton(root), before = grabImage(root), initial = button.checked;
                mouseClick(button, button.width / 2, button.height / 2);
                tryCompare(button, "checked", !initial, 1000, "Real input toggles excluded-region visibility on Pattern, Stacked and Map");
                verify(waitForRendering(root), "The excluded-region setting reaches an actual chart frame");
                verify(!before.equals(grabImage(root)), "The real excluded-region control changes drawable chart content");
                mouseClick(button, button.width / 2, button.height / 2);
                tryCompare(button, "checked", initial, 1000, "The same excluded-region input restores its original state");
            }
            compare(SettingsProof.text(Qt.resolvedUrl("file:" + Session.project.path), "experiments/d20.edi"), original, "A visibility control preserves the independently specified excluded scientific ranges");
        }
        Component {
            id: analysisFactory
            AnalysisPage {
                width: 1100
                height: 760
                current: true
            }
        }
        function openJoint(independent = false) {
            const root = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project"));
            Input.joint(SettingsProof, root, independent);
            verify(Session.openProject(root), "The joint actor opens two independently specified nontrivial TOF banks");
            compare(Session.project.experiments.count, 2, "Both analytic joint banks retain project order");
            return root;
        }
        function test_joint_tab_availability_data() {
            return [
                {
                    tag: "scan",
                    kind: "scan",
                    enabled: true
                },
                {
                    tag: "joint",
                    kind: "joint",
                    enabled: true
                },
                {
                    tag: "single-multi",
                    kind: "single-multi",
                    enabled: false
                },
                {
                    tag: "single",
                    kind: "single",
                    enabled: false
                }
            ];
        }
        function test_joint_tab_availability(data) {
            if (data.kind === "joint" || data.kind === "single-multi")
                openJoint(data.kind === "single-multi");
            else {
                const root = SettingsProof.copyProject(Probe.repoUrl(data.kind === "scan" ? "tests/fixtures/scan_template/project" : "tests/fixtures/loop_parameter_ids/line-segment"));
                verify(Session.openProject(root), "The tab-availability control opens its real fitting-mode project");
            }
            chart = analysisFactory.createObject(surface);
            verify(chart !== null && waitForPolish(chart), "The real Analysis page lays out its mode-dependent tabs");
            for (const name of ["stacked", "map"]) {
                const tab = chart.mainTabs.find(item => item.objectName === "mainArea.analysis.tab." + name);
                verify(tab !== undefined, "Analysis has the actual " + name + " tab");
                compare(tab.enabled, data.enabled, "Stacked and Map are enabled exactly for scans and joint fits");
                if (data.enabled) {
                    mouseClick(tab, tab.width / 2, tab.height / 2);
                    verify(waitForRendering(chart), "Actual input opens each enabled scan or joint chart tab");
                }
            }
            const evolution = chart.mainTabs.find(item => item.objectName === "mainArea.analysis.tab.evolution");
            verify(evolution !== undefined, "The availability witness reaches the actual Evolution tab");
            compare(evolution.enabled, data.kind === "scan", "Evolution remains scan-only after joint Stacked and Map are added");
            const follow = findChild(chart, "fitting.follow");
            verify(follow !== null, "The actual fitting sidebar supplies its Follow control");
            verify(data.kind === "scan" ? follow.visible : !follow.enabled && !follow.checked, "Follow is usable only for scans and cannot be activated for single or joint fits");
        }
        function test_joint_rows_and_common_d_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_joint_rows_and_common_d(data) {
            openJoint();
            chart = factory.createObject(surface, {
                project: Session.project,
                mode: data.mode
            });
            const scan = Session.project.scanViews;
            ready(scan);
            compare(scan.count, 2, "Joint chart rows cover every project experiment exactly once");
            compare(scan.rowOf(0), 0, "The first joint experiment occupies index zero rather than a scan coordinate");
            compare(scan.rowOf(1), 1, "The second joint experiment follows the first in project order");
            fuzzyCompare(scan.xMin, 813, 1e-6, "The native joint range starts at the first bank's own offset plus calibrated d minimum");
            fuzzyCompare(scan.xMax, 6981, 1e-6, "The native joint range covers the second bank's distinct calibrated maximum");
            const names = Probe.rows(Session.project.experiments).map(row => String(row.label));
            const texts = Render.texts(chart).map(item => item.text).join(" ");
            verify(names.length === 2 && names.every(name => name !== "" && texts.includes(name)), "Joint rows are visibly labelled by their real experiment names in project order");
            const selector = axisControl("x");
            tryVerify(() => selector.enabled, 8000, "Real calculated bank d coordinates become selectable");
            choose(selector, 1);
            const axes = named("axes"), layer = named("layer");
            tryVerify(() => Math.abs(axes.axisX.min - .8) < 1e-5 && Math.abs(axes.axisX.max - 2.8) < 1e-5, 2000, "Both nontrivial TOF calibrations share the independently known physical d range");
            Session.project.currentExperimentIndex = 0;
            verify(waitForRendering(chart), "The joint d view has a completed actual frame");
            const frame = grabImage(chart), measured = Approved.colours(SettingsProof, "ediNatural", "measured", 2, false);
            for (let row = 0; row < 2; ++row) {
                const x = (1.8 - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width;
                const y = data.mode === "stacked" ? row + scan.stackHeight : row;
                const at = layer.mapToItem(chart, x, (axes.axisY.max - y) / (axes.axisY.max - axes.axisY.min) * layer.height + (data.mode === "map" ? (row === 0 ? -5 : 5) : 0));
                const expected = data.mode === "stacked" ? rgb(measured[row]) : rgb("#fde725");
                let hit = false;
                for (let dx = -2; dx <= 2; ++dx)
                    for (let dy = -2; dy <= 2; ++dy)
                        hit = hit || ink(frame.pixel(Math.round(at.x) + dx, Math.round(at.y) + dy), expected, chart.colors.chartBackground);
                verify(hit, "Each bank's independently placed peak aligns at physical d=1.8 on the same actual chart scale");
            }
            const pointer = named("pointer"), marker = named("current");
            const py = (axes.axisY.max - 1) / (axes.axisY.max - axes.axisY.min) * pointer.height;
            mouseClick(pointer, pointer.width * .4, Math.max(2, py));
            tryCompare(Session.project, "currentExperimentIndex", 1, 1000, "Actual joint-chart input selects the second real experiment");
            verify(Math.abs(marker.mapToItem(layer, 0, marker.height / 2).y - Math.max(marker.height / 2, py)) <= 1, "The joint indicator follows the selected experiment's index row");
        }
        function rgb(hex) {
            return Qt.rgba(parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255, 1);
        }
        Component {
            id: metricsFactory
            FontMetrics {}
        }
        function test_owner_selector_widths_data() {
            return [
                {
                    tag: "pattern",
                    mode: "pattern"
                },
                {
                    tag: "stacked",
                    mode: "stacked"
                },
                {
                    tag: "map",
                    mode: "map"
                }
            ];
        }
        function test_owner_selector_widths(data) {
            const scan = open(data.mode === "pattern" ? "stacked" : data.mode);
            ready(scan);
            if (data.mode === "pattern") {
                chart.destroy();
                chart = patternReferenceFactory.createObject(surface, {
                    experiment: Session.project.currentExperiment,
                    visible: true,
                    shown: true
                });
                verify(chart !== null && waitForPolish(chart) && waitForRendering(chart), "The width witness lays out the actual Pattern toolbar");
            }
            const controls = Render.descendants(chart).filter(item => item.visible && item.count > 1 && typeof item.textAt === "function" && String(item.objectName).includes("toolbar"));
            verify(controls.length >= 2, "Each chart has distinct real toolbar selectors for the independent width witness");
            const widths = [];
            for (const control of controls) {
                const metrics = createTemporaryObject(metricsFactory, surface, {
                    font: control.font
                });
                verify(metrics !== null, "The selector width witness measures its actual Qt font independently");
                const entries = [];
                for (let i = 0; i < control.count; ++i)
                    entries.push(control.textAt(i));
                for (const text of control.closedTexts || [])
                    entries.push(text);
                const maximum = Math.ceil(Math.max(...entries.map(text => metrics.advanceWidth(String(text)))));
                const label = control.contentItemLabel;
                verify(label !== undefined, "The actual selector exposes its rendered text padding and arrow clearance");
                const clearance = label.leftPadding + label.rightPadding + control.leftPadding + control.rightPadding;
                verify(Math.abs(control.width - (maximum + clearance)) <= 1, "Every toolbar combobox fits its own longest entry and normal arrow/padding, with at most one pixel of rounding room; selector=" + control.objectName + " width=" + control.width + " expected=" + (maximum + clearance));
                widths.push(control.width);
            }
            verify(Math.max(...widths) - Math.min(...widths) > 1, "Unequal longest texts produce individual selector widths rather than one shared width");
        }
    }
}
