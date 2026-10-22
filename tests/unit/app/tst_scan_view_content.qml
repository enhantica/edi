// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtTest
import edi.app
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "ApprovedPalette.js" as Approved
import "RenderedTable.js" as Render
import "../../fixtures/scan_views/input.js" as Input

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
            verify(marker.visible && Math.abs(marker.y - expected) <= 1, "The drawn marker lies at the selected physical scan coordinate");
            compare(marker.width, layer.width, "The current pattern is marked by a full-width horizontal line");
            verify(marker.height >= 1 && marker.color.a > 0, "The selected Map pattern has visible line ink even with no fit running");
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
            const strongest = channels.reduce((best, c) => Math.abs(background[c] - expected[c]) > Math.abs(background[best] - expected[best]) ? c : best, "r");
            const alpha = (background[strongest] - pixel[strongest]) / (background[strongest] - expected[strongest]);
            return alpha > 0 && alpha <= 1 + 1 / 255 && channels.every(c => Math.abs(pixel[c] - (background[c] * (1 - alpha) + alpha * expected[c])) <= 1 / 255);
        }
        function test_antialiased_ink_observer() {
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
            const layer = named("layer"), axes = named("axes"), frame = grabImage(chart);
            const colours = data.mode === "stacked" ? Approved.colours(SettingsProof, "ediNatural", "measured", 3, false) : ["#440154", "#21918c", "#fde725"];
            for (let index = 0; index < 3; ++index) {
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
                verify(Math.abs(marker.y - expectedY) <= 1, "Selecting a pattern places its drawn marker at the independent temperature");
                verify(marker.visible && marker.width === layer.width && marker.color.a > 0, "The Map keeps a visible full-width current-pattern line outside a running fit");
                surface.Window.window.update();
                verify(waitForRendering(chart), "The selected Map line reaches an actual completed frame");
                const frame = grabImage(chart), at = marker.mapToItem(chart, marker.width / 2, marker.height / 2);
                const pixel = frame.pixel(Math.floor(at.x), Math.floor(at.y));
                verify(["r", "g", "b"].every(channel => Math.abs(pixel[channel] - marker.color[channel]) <= 1 / 255), "The selected pattern's horizontal line is present in actual Map pixels");
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
            const steps = (index - control.currentIndex + control.count) % control.count;
            for (let step = 0; step < steps; ++step)
                keyClick(Qt.Key_Down);
            keyClick(Qt.Key_Return);
            tryCompare(control, "currentIndex", index, 1000, "Real input chooses the requested scan axis or palette type");
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
                for (const axis of mode === "map" ? ["x", "y", "z"] : ["x", "y"])
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
            return ["stacked", "map"].flatMap(mode => [false, true].map(dark => ({
                            tag: mode + (dark ? "-dark" : "-light"),
                            mode,
                            dark
                        })));
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
                for (const index of [0, 1]) {
                    if (data.mode === "map") {
                        const point = layer.mapToItem(chart, layer.width * (index ? 6.5 : 0.5) / 7, layer.height * 0.2);
                        compare(String(frame.pixel(Math.round(point.x), Math.round(point.y))).toLowerCase(), expected[index].toLowerCase(), "Every Map ramp starts at the Pattern plot background and ends at its main experiment colour");
                    } else {
                        const coordinate = index ? 700 + scan.stackHeight : 100;
                        const py = (axes.axisY.max - coordinate) / (axes.axisY.max - axes.axisY.min) * layer.height;
                        const point = layer.mapToItem(chart, layer.width * 0.4, py);
                        const colour = expected[index];
                        const rgb = {
                            r: parseInt(colour.slice(1, 3), 16) / 255,
                            g: parseInt(colour.slice(3, 5), 16) / 255,
                            b: parseInt(colour.slice(5, 7), 16) / 255
                        };
                        let present = false;
                        for (let dy = -2; dy <= 2; ++dy) {
                            const pixel = frame.pixel(Math.round(point.x), Math.round(point.y) + dy);
                            present = present || (index ? ink(pixel, rgb, chart.colors.chartBackground) : ["r", "g", "b"].every(channel => Math.abs(pixel[channel] - rgb[channel]) <= 1 / 255));
                        }
                        verify(present, "Every Stacked ramp uses the Pattern plot background and its main experiment colour at the end patterns");
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
                        const colour = reference.colours[[0, 128, 255][row]];
                        const expected = {
                            r: parseInt(colour.slice(1, 3), 16) / 255,
                            g: parseInt(colour.slice(3, 5), 16) / 255,
                            b: parseInt(colour.slice(5, 7), 16) / 255
                        };
                        const bg = chart.colors.chartBackground;
                        let present = false;
                        for (let dy = -2; dy <= 2; ++dy)
                            present = present || ink(frame.pixel(Math.round(point.x), Math.round(point.y) + dy), expected, bg);
                        verify(present, "Each stacked pattern has real published-map ink against the current theme background: " + name);
                    }
                }
                verify(chart.colors.chartLabels !== chart.colors.chartBackground, "The map's axis and key labels remain visible against the theme background");
            }
            verify(offered > 1, "Both views offer multiple sourced maps beside the background ramps");
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
    }
}
