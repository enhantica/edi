// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtTest
import QtGraphs
import edi.app
import ReportAcceptance 1.0
import EdiAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import EasyApplication.Gui.Style as Style
import "ApprovedPalette.js" as Approved
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui
import "../../fixtures/scan_views/input.js" as Input
import "../../fixtures/scan_views/oklab.js" as Oklab

Rectangle {
    id: surface
    width: Math.min(1200, Screen.desktopAvailableWidth)
    height: Math.min(850, Screen.desktopAvailableHeight)
    color: "white"
    Component {
        id: factory
        ScanViewChart {
            width: Math.min(1100, surface.Window.window.width)
            height: Math.min(760, surface.Window.window.height)
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
        property var applicationWindow
        property var preferencesDialog
        property var preferencesSelector
        Component {
            id: preferencesFactory
            AppPreferencesDialog {}
        }
        property var samples: JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/viridis.json")).samples
        function test_private_copy_required() {
            for (const root of ["", "experiments", "file://relative", "https://example.invalid/project"])
                for (const generator of [Input.prepare, Input.joint, Input.dense, Input.edgeBanks, Input.gap, Input.coincident]) {
                    let writes = 0, refused = false;
                    const proof = {
                        write: () => {
                            ++writes;
                            return true;
                        }
                    };
                    try {
                        generator(proof, root);
                    } catch (error) {
                        refused = String(error).includes("nonempty absolute private project URL");
                    }
                    verify(refused, "Every scan fixture generator refuses an absent or relative private-copy URL before using it");
                    compare(writes, 0, "A failed private project copy cannot write fixture data into the caller's working tree");
                }
        }
        function logicalImage(item, image = grabImage(item)) {
            verify(image.width > 0 && image.height > 0 && item.width > 0 && item.height > 0, "The rendered observer requires a nonempty image and logical item");
            const sx = image.width / item.width, sy = image.height / item.height;
            return {
                width: item.width,
                height: item.height,
                pixel: (x, y) => image.pixel(Math.floor((x + 0.5) * sx), Math.floor((y + 0.5) * sy))
            };
        }
        function cleanup() {
            if (preferencesDialog) {
                preferencesDialog.close();
                if (!applicationWindow)
                    preferencesDialog.destroy();
            }
            preferencesDialog = null;
            preferencesSelector = null;
            if (chart && !applicationWindow)
                chart.destroy();
            if (applicationWindow) {
                applicationWindow.close();
                applicationWindow.destroy();
            }
            applicationWindow = null;
            chart = null;
            Session.closeProject();
        }
        function open(mode, kind = "bands") {
            Style.Colors.theme = Style.Colors.LightTheme;
            Preferences.resetToDefaults();
            Preferences.patternYScale = "linear";
            Preferences.chartHighlightSelected = false;
            if (typeof Preferences.scanMapColours === "string")
                Preferences.scanMapColours = "viridis";
            if (typeof Preferences.scanStackedPalette === "string")
                Preferences.scanStackedPalette = "ediNatural";
            const location = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/scan_template/project"));
            Input.prepare(SettingsProof, location, mode === "stacked" && kind === "rows" ? "bounded-rows" : kind);
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
            Preferences.chartHighlightSelected = false;
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
        function exposeStack() {
            if (chart.mode === "stacked") {
                chart.zoomY = [-.05, 1.05];
                chart.Window.window.update();
                verify(waitForPolish(chart) && waitForRendering(chart), "The colour witness gives boundary Stacked lines clear space from the plot frame");
            }
        }
        function stackedAt(index, count, fraction) {
            const offset = Preferences.scanStackedOffset / 100;
            const height = Preferences.scanStackedSize === 0 ? 1 / (1 + (count - 1) * offset) : Preferences.scanStackedSize / 100;
            return height * (index * offset + fraction);
        }
        function selectionLabel(index) {
            const axes = named("axes"), coordinate = chart.mode === "stacked" ? stackedAt(index, chart.scan.count, 0) : chart.scan.rowOf(index);
            if (coordinate < axes.axisY.min || coordinate > axes.axisY.max)
                return null;
            surface.Window.window.update();
            verify(waitForPolish(chart) && waitForRendering(chart), "The selected row label reaches its actual rendered layout");
            const matches = Render.descendants(chart).filter(item => item.objectName === "scanView." + chart.mode + ".rowLabel." + index && item.visible && item.opacity > 0);
            compare(matches.length, 1, "Highlight off identifies exactly one shown label for the selected dataset");
            const label = matches[0];
            verify(label.segments.some(segment => segment.text && segment.bold === true), "The shown dataset's actual IconLine text segment is bold");
            compare(String(label.textColor), String(Style.Colors.themeAccent), "The shown dataset's actual label uses the theme accent");
            const text = Render.texts(label).find(item => item.font.family === Style.Fonts.ptSansBold.name && item.font.styleName === "Bold" && item.opacity > 0);
            verify(text !== undefined && Ui.rendered(text), "The selected label loads the real bold face in the visible plot");
            const root = Ui.windowRoot(chart.Window.window), at = text.mapToItem(root, 0, 0);
            const opacity = label.opacity;
            label.opacity = 0;
            chart.Window.window.update();
            verify(waitForRendering(chart), "The label ink reference captures the real underlay without its text");
            const underlay = logicalImage(root);
            label.opacity = opacity;
            chart.Window.window.update();
            verify(waitForRendering(chart), "The selected label is restored before its actual ink is compared");
            const frame = logicalImage(root);
            let drawn = false;
            for (let y = 0; y < text.height && !drawn; ++y)
                for (let x = 0; x < text.width && !drawn; ++x)
                    drawn = ink(frame.pixel(Math.floor(at.x + x), Math.floor(at.y + y)), Style.Colors.themeAccent, underlay.pixel(Math.floor(at.x + x), Math.floor(at.y + y)));
            verify(drawn, "The selected label has actual accent ink inside its rendered text bounds");
            compare(findChild(chart, "scanView." + chart.mode + ".current"), null, "The retired selection rectangle is absent from the actual scan chart");
            return label;
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
            compare(scan.loaded, 0, "The marker is observed before background reading starts");
            compare(scan.rowOf(1), 1, "The selected dataset begins at its independent file-index position");
            ready(scan);
            compare(Session.project.currentExperimentIndex, 1, "The selected dataset remains unchanged throughout asynchronous placement");
            compare(scan.rowOf(1), 250, "The second independent TEMP field becomes the scan coordinate");
            selectionLabel(1);
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
            Preferences.chartHighlightSelected = false;
            ready(scan);
            const layer = named("layer"), image = logicalImage(chart);
            compare(scan.xMin, 10, "The analytic map reads its declared x minimum");
            fuzzyCompare(scan.xMax, 112.4, 1e-9, "The analytic map reads its declared x maximum");
            compare(layer.displayMin, 0, "The map normalization starts at the independent zero-intensity band");
            compare(layer.displayMax, 255, "The map normalization ends at the independent maximum-intensity band");
            verify(image.width > 300 && image.height > 100, "The colormap witness captures actual nonempty Map pixels");
            const bar = named("colourBar.colours");
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
            // Owner amendment 2026-10-22 replaces centre-to-centre interpolation.
            checkEdgePixels([25, 175, 475, 775], [0, 128, 255], [[10, 112.4], [10, 112.4], [10, 112.4]], [50], true);
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
            for (const [scale, x, y] of [[1, 3, 2], [1.5, 5, 3], [2, 7, 5]]) {
                const image = logicalImage({
                    width: 8,
                    height: 6
                }, {
                    width: 8 * scale,
                    height: 6 * scale,
                    pixel: (px, py) => Qt.rgba(px / 255, py / 255, 0, 1)
                });
                compare(image.width, 8, "The capture exposes the logical width at each device scale");
                compare(image.height, 6, "The capture exposes the logical height at each device scale");
                compare(image.pixel(3, 2), Qt.rgba(x / 255, y / 255, 0, 1), "The observer samples the physical centre of a logical pixel at integral and fractional device scales");
            }
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
            exposeStack();
            const layer = named("layer"), axes = named("axes");
            const colours = data.mode === "stacked" ? Approved.colours(SettingsProof, "ediNatural", "measured", 3, false) : ["#440154", "#21918c", "#fde725"];
            for (let index = 0; index < 3; ++index) {
                if (data.mode === "map") {
                    Session.project.currentExperimentIndex = (index + 1) % 3;
                    verify(waitForRendering(chart), "The selected-row overlay moves away from each independent map-row sample");
                }
                const frame = logicalImage(chart);
                const coordinate = data.mode === "stacked" ? stackedAt(index, 3, [0, 128, 255][index] / 255) : [100, 250, 700][index];
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
        function test_selected_map_label_is_always_drawn() {
            const scan = open("map");
            ready(scan);
            for (const index of [0, 2, 1]) {
                Session.project.currentExperimentIndex = index;
                verify(waitForRendering(chart), "The newly selected Map dataset reaches a completed real frame");
                selectionLabel(index);
            }
        }
        function axisControl(axis) {
            const controls = Render.descendants(chart).filter(item => item.visible && item.count >= 1 && typeof item.currentIndex === "number");
            const expression = new RegExp("(?:[. _-]|^)" + axis + "(?:axis|scale|type|[. _-])|" + axis + "[ -]axis", "i");
            const found = controls.find(item => expression.test(String(item.objectName) + " " + item.toolTip + " " + (item.closedTexts || []).join(" ")));
            verify(found !== undefined, "The real scan toolbar has an independent " + axis + " axis-type control");
            return found;
        }
        function openPreferences() {
            if (!preferencesDialog)
                preferencesDialog = applicationWindow ? findChild(applicationWindow, "preferences") : preferencesFactory.createObject(surface);
            verify(preferencesDialog !== null, "The palette witness opens the actual application Preferences dialog");
            if (applicationWindow && !Preferences.dialogShown)
                Ui.click(test, Probe, applicationWindow, "appBar.button.preferences");
            else
                Preferences.dialogShown = true;
            tryCompare(preferencesDialog, "opened", true, 1000, "The actual Preferences dialog finishes opening before colour input");
            const tab = findChild(preferencesDialog.contentItem, "preferences.tab.appearance");
            verify(tab !== null && tab.enabled, "The actual Preferences Appearance tab is available");
            if (!tab.checked)
                mouseClick(tab, tab.width / 2, tab.height / 2);
            tryCompare(tab, "checked", true, 1000, "Actual input chooses the Preferences Appearance page");
            tryVerify(() => !Ui.moving(preferencesDialog.contentItem), 2000, "The actual Preferences page finishes moving before colour input");
            verify(waitForPolish(preferencesDialog.contentItem), "Preferences colour controls finish layout before input");
        }
        function preferenceColour(label) {
            openPreferences();
            const row = Render.descendants(preferencesDialog.contentItem).find(item => item.rowLabel === true && String(item.text).replace(/:$/, " ").trim() === label);
            verify(row !== undefined, "Preferences contains its actual independently named " + label + " colour choice");
            const siblings = row.parent.children, index = siblings.indexOf(row);
            const box = siblings.slice(index + 1).find(item => item.rowBox === true);
            verify(box !== undefined && box.count > 1, "The " + label + " colour choice has its actual populated Preferences selector");
            return box;
        }
        function paletteSelector(mode) {
            if (mode === "map")
                return named("toolbar.colourMap");
            preferencesSelector = preferenceColour("Stacked");
            return preferencesSelector;
        }
        function choose(control, index) {
            if (control === preferencesSelector)
                openPreferences();
            Ui.scrollIntoView(control);
            verify(waitForPolish(control.Window.window.contentItem), "The selector is laid out after scrolling its real viewport" + "; step=polish selector=" + control.objectName + " targetIndex=" + index);
            control.Window.window.update();
            verify(waitForRendering(control.Window.window.contentItem), "The actual selector window has rendered before input" + "; step=render selector=" + control.objectName + " targetIndex=" + index);
            let at;
            tryVerify(() => {
                at = Ui.clickPoint(control);
                return at !== null;
            }, 2000, "The real selector finishes its tab transition inside the input viewport" + "; step=exposure selector=" + control.objectName + " targetIndex=" + index + " observedAtPollStart=" + JSON.stringify({
                point: Ui.clickPoint(control),
                visible: control.visible,
                enabled: control.enabled,
                width: control.width,
                height: control.height
            }));
            mouseClick(control, at.x, at.y);
            tryCompare(control.popup, "opened", true, 1000, "Real input opens the requested scan selector" + "; step=open selector=" + control.objectName + " targetIndex=" + index + " click=" + JSON.stringify(at));
            const windowRoot = control.Window.window.contentItem;
            mouseMove(windowRoot, windowRoot.width - 1, windowRoot.height - 1);
            verify(SettingsProof.key(control, Qt.Key_Home), "Home reaches the actual scan selector window" + "; step=Home selector=" + control.objectName + " targetIndex=" + index + " readIndex=" + control.currentIndex + " highlightedIndex=" + control.highlightedIndex);
            for (let step = 0; step < index; ++step)
                verify(SettingsProof.key(control, Qt.Key_Down), "Down reaches the actual scan selector window" + "; step=Down ordinal=" + (step + 1) + " selector=" + control.objectName + " targetIndex=" + index + " readIndex=" + control.currentIndex + " highlightedIndex=" + control.highlightedIndex);
            verify(SettingsProof.key(control, Qt.Key_Return), "Return commits the actual scan selector choice" + "; step=Return selector=" + control.objectName + " targetIndex=" + index + " readIndex=" + control.currentIndex + " highlightedIndex=" + control.highlightedIndex);
            tryCompare(control, "currentIndex", index, 1000, "Real input chooses the requested scan axis or palette type" + "; step=commit selector=" + control.objectName + " expectedIndex=" + index + " expectedText=" + control.textAt(index) + " readTextAtPollStart=" + control.displayText + " popupOpened=" + control.popup.opened + " highlightedIndex=" + control.highlightedIndex);
            tryCompare(control.popup, "visible", false, 1000, "The real popup finishes closing before another scan input" + "; step=close selector=" + control.objectName + " targetIndex=" + index);
            if (control === preferencesSelector) {
                verify(SettingsProof.key(control, Qt.Key_Escape), "Actual Escape input closes Preferences after the colour choice");
                tryCompare(preferencesDialog, "visible", false, 1000, "The Preferences overlay closes before observing actual scan pixels");
            }
            chart.Window.window.update();
            verify(waitForRendering(chart), "The selected scan setting reaches an actual frame");
        }
        function plotDigest() {
            const layer = named("layer"), frame = logicalImage(chart), colours = [];
            for (let x = 1; x < 16; ++x)
                for (let y = 1; y < Math.floor(layer.height); ++y) {
                    const at = layer.mapToItem(chart, layer.width * x / 16, y);
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
            if (data.mode === "stacked" && data.axis === "y") {
                compare(plotDigest(), before, "Switching from monotonic scientific values to file order preserves the new rank-based Stacked placement");
                verify(rowLabels().some(item => /all594/.test(item.text)), "The Stacked row-order choice changes the actual row labels to file names");
            } else
                tryVerify(() => plotDigest() !== before, 1000, "Changing the " + data.axis + " type changes actual scan plot pixels, beyond the button's label; selector=" + control.objectName + " originalIndex=" + original + " expectedIndex=" + ((original + 1) % control.count) + " readIndex=" + control.currentIndex + " displayText=" + control.displayText);
            choose(control, original);
            tryVerify(() => plotDigest() === before, 1000, "Restoring the axis type restores the same actual analytic scan drawing");
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
            return [
                {
                    tag: "map-light",
                    mode: "map",
                    dark: false
                },
                {
                    tag: "map-dark",
                    mode: "map",
                    dark: true
                }
            ];
        }
        function test_background_to_experiment_ramp(data) {
            const scan = open("map", "bands");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            const choices = chart.mapChoices, selector = paletteSelector("map");
            const schemes = Approved.reference(SettingsProof).schemes;
            compare(choices.slice(0, 5).join(","), schemes.map(scheme => "ramp:" + scheme.id).join(","), "The Map toolbar offers all five Edi shades before every published colour map");
            const preferences = preferenceColour("Map");
            compare(Array.from({
                length: 5
            }, (_, index) => preferences.textAt(index)).join(","), Array.from({
                length: 5
            }, (_, index) => selector.textAt(index)).join(","), "The Preferences Map list has the same first five Edi shades in the same order");
            keyClick(Qt.Key_Escape);
            tryCompare(preferencesDialog, "visible", false, 1000, "Actual Escape closes the Preferences observer before Map input");
            const pattern = createTemporaryObject(patternReferenceFactory, surface, {
                experiment: Session.project.currentExperiment
            });
            verify(pattern !== null, "The Map ramp reference is the actual Pattern plot background in the current theme");
            for (let choice = 0; choice < 5; ++choice) {
                choose(selector, choice);
                const expected = [String(pattern.colors.chartBackground), schemes[choice].palette[data.dark ? "dark" : "light"].measured[0]];
                const layer = named("layer"), frame = logicalImage(chart);
                for (const index of [0, 1]) {
                    const point = layer.mapToItem(chart, layer.width * (index ? 6.5 : .5) / 7, layer.height * .2);
                    compare(String(frame.pixel(Math.round(point.x), Math.round(point.y))).toLowerCase(), expected[index].toLowerCase(), "Every Map shade ramp starts at the Pattern plot background and ends at its independently approved main experiment colour");
                }
            }
        }
        function test_stacked_schemes_and_line_width_data() {
            return [
                {
                    tag: "light",
                    dark: false
                },
                {
                    tag: "dark",
                    dark: true
                }
            ];
        }
        function test_stacked_schemes_and_line_width(data) {
            const scan = open("stacked", "rows");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            exposeStack();
            const choices = chart.stackedChoices, schemes = Approved.reference(SettingsProof).schemes;
            verify(choices.every(name => !String(name).startsWith("ramp:")), "Stacked offers no background-to-colour shades after the owner's removal decision");
            const selector = paletteSelector("stacked");
            const pattern = createTemporaryObject(patternReferenceFactory, surface, {
                experiment: Session.project.currentExperiment
            });
            verify(pattern !== null, "The Stacked width witness reaches the prior Pattern chart's actual measured series");
            const measured = Render.series(pattern).find(item => item.objectName === "chart.series.meas");
            verify(measured !== undefined, "The width comparison observes an actual Pattern measured line");
            compare(measured.width, 2, "The Pattern measured-line width is the owner's independently declared two logical pixels");
            for (const scheme of schemes) {
                const index = choices.indexOf(scheme.id);
                verify(index >= 0, "Every approved categorical Edi scheme remains offered for Stacked");
                choose(selector, index);
                const layer = named("layer"), axes = named("axes"), frame = logicalImage(chart);
                const colours = Approved.colours(SettingsProof, scheme.id, "measured", 3, data.dark);
                for (let row = 0; row < 3; ++row) {
                    const coordinate = stackedAt(row, 3, [0, 128, 255][row] / 255);
                    const py = Math.round((axes.axisY.max - coordinate) / (axes.axisY.max - axes.axisY.min) * layer.height), px = Math.round(layer.width * .4), expected = rgb(colours[row]);
                    let coverage = 0;
                    for (let dy = -6; dy <= 6; ++dy) {
                        const at = layer.mapToItem(chart, px, py + dy), pixel = frame.pixel(Math.round(at.x), Math.round(at.y));
                        const bg = chart.colors.chartBackground;
                        const channel = ["r", "g", "b"].sort((a, b) => Math.abs(expected[b] - bg[b]) - Math.abs(expected[a] - bg[a]))[0];
                        const alpha = (pixel[channel] - bg[channel]) / (expected[channel] - bg[channel]);
                        verify(["r", "g", "b"].every(c => Math.abs(pixel[c] - (bg[c] + alpha * (expected[c] - bg[c]))) <= 3 / 255), "Every width sample is a composite of the independent scheme colour over the plot background");
                        coverage += Math.max(0, Math.min(1, alpha));
                    }
                    verify(Math.abs(coverage - measured.width) <= .15 * measured.width, "Every widely separated Stacked row has drawable independent scheme ink as wide as the Pattern measured line, including the selected dataset; coverage=" + coverage + " scheme=" + scheme.id + " row=" + row + " expectedWidth=" + measured.width + " sampledBand=" + JSON.stringify({
                        x: px,
                        yMin: py - 6,
                        yMax: py + 6,
                        coordinate: coordinate,
                        rowValue: [100, 250, 700][row],
                        level: [0, 128, 255][row],
                        patternHeight: layer.patternHeight,
                        domain: [axes.axisY.min, axes.axisY.max],
                        layerSize: [layer.width, layer.height]
                    }) + " expectedColour=" + expected + " pixels=" + JSON.stringify(Array.from({
                        length: 13
                    }, (_, i) => ({
                                x: px,
                                y: py + i - 6,
                                colour: String(frame.pixel(Math.round(layer.mapToItem(chart, px, py + i - 6).x), Math.round(layer.mapToItem(chart, px, py + i - 6).y)))
                            }))));
                }
            }
        }
        function test_offered_maps_are_readable_in_both_themes_data() {
            const rows = [];
            const count = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/offered.json")).maps.length;
            for (const mode of ["stacked", "map"])
                for (const dark of [false, true])
                    for (let first = 0; first < count; first += 7)
                        rows.push({
                            tag: mode + (dark ? "-dark" : "-light") + "-part" + Math.floor(first / 7),
                            mode,
                            dark,
                            first,
                            last: Math.min(first + 7, count),
                            count
                        });
            return rows;
        }
        function test_offered_maps_are_readable_in_both_themes(data) {
            const scan = open(data.mode, data.mode === "stacked" ? "rows" : "bands");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            exposeStack();
            const references = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/maps.json"));
            const choices = data.mode === "map" ? chart.mapChoices : chart.stackedChoices;
            verify(choices !== undefined && choices.length > 1, "The real view exposes its offered palette choices for independent source matching");
            const selector = paletteSelector(data.mode);
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
                if (offered <= data.first || offered > data.last)
                    continue;
                choose(selector, index);
                const layer = named("layer"), axes = named("axes");
                if (data.mode === "map") {
                    const frame = logicalImage(chart);
                    for (const [band, place] of [[1, 32], [3, 96], [5, 192]]) {
                        const point = layer.mapToItem(chart, layer.width * (band + 0.5) / 7, layer.height * 0.2);
                        const pixel = frame.pixel(Math.round(point.x), Math.round(point.y));
                        const expected = reference.colours[place];
                        for (const [channel, offset] of [["r", 1], ["g", 3], ["b", 5]])
                            verify(Math.abs(Math.round(pixel[channel] * 255) - parseInt(expected.slice(offset, offset + 2), 16)) <= 1, "The actual Map retains a published interior intensity colour in both themes: " + name);
                    }
                } else {
                    for (let row = 0; row < 3; ++row) {
                        Session.project.currentExperimentIndex = (row + 1) % 3;
                        surface.Window.window.update();
                        verify(waitForRendering(chart), "The dataset choice settles before observing each published Stacked curve colour");
                        const frame = logicalImage(chart);
                        const coordinate = stackedAt(row, 3, [0, 128, 255][row] / 255);
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
            compare(offered, data.count, "Separate map actors cover the entire independent map inventory");
        }
        function test_map_reverse_and_key_data() {
            const cases = [];
            const count = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/offered.json")).maps.length + Approved.reference(SettingsProof).schemes.length;
            for (const reverse of [false, true])
                for (const dark of [false, true])
                    for (let first = 0; first < count; first += 12)
                        cases.push({
                            tag: (reverse ? "reversed" : "forward") + (dark ? "-dark" : "-light") + "-part" + Math.floor(first / 12),
                            reverse,
                            dark,
                            first,
                            last: Math.min(first + 12, count),
                            count
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
            compare(choices.length, data.count, "Every reversal part retains the complete independently recorded roster of maps and approved ramps");
            const reference = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/maps.json"));
            const selector = findChild(chart, "scanView.map.toolbar.colourMap");
            verify(selector !== null && choices !== undefined, "Reversal operates the real offered Map palette selector");
            const pattern = createTemporaryObject(patternReferenceFactory, surface, {
                experiment: Session.project.currentExperiment
            });
            verify(pattern !== null, "Reversed ramps use the actual Pattern plot background as their relational input");
            const schemes = Approved.reference(SettingsProof).schemes;
            const layer = named("layer");
            const bar = named("colourBar.colours");
            verify(bar !== undefined, "The reverse witness reaches the actual drawn quantitative colour key");
            for (const requested of [!data.reverse, data.reverse]) {
                if (toggle.checked !== requested)
                    mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                tryCompare(toggle, "checked", requested, 1000, "Real pointer input changes the reverse choice in both directions");
                for (let choice = data.first; choice < data.last; ++choice) {
                    const name = choices[choice];
                    const ramp = String(name).startsWith("ramp:");
                    const scheme = ramp ? schemes.find(row => row.id === String(name).slice(5)) : null;
                    verify(ramp ? scheme !== undefined : reference[name] !== undefined && reference[name].license, "Every offered reversible map has an independent published table/licence or approved ramp operands");
                    choose(selector, choice);
                    const frame = logicalImage(chart);
                    for (const [band, index] of [[1, 32], [3, 96], [5, 192]]) {
                        const place = requested ? 255 - index : index;
                        const expected = ramp ? Oklab.gradient(String(pattern.colors.chartBackground), scheme.palette[data.dark ? "dark" : "light"].measured[0], place / 255) : reference[name].colours[place];
                        for (const [item, x, y] of [[layer, layer.width * (band + 0.5) / 7, layer.height * 0.2], [bar, bar.width / 2, (bar.height - 1) * (1 - index / 255)]]) {
                            const at = item.mapToItem(chart, x, y), pixel = frame.pixel(Math.round(at.x), Math.round(at.y));
                            for (const [channel, offset] of [["r", 1], ["g", 3], ["b", 5]])
                                verify(Math.abs(Math.round(pixel[channel] * 255) - parseInt(expected.slice(offset, offset + 2), 16)) <= 1, "Forward and reversed image and key use the same independent interior table sample: " + name);
                        }
                    }
                }
            }
            const restored = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property bool checked:Preferences.scanMapReversed }');
            verify(!restored.error, "A fresh production engine restores the reverse setting exercised by the actual Map control");
            compare(restored.checked, data.reverse, "The reverse choice survives a fresh settings engine in both directions");
        }
        function interpolationToggle(root) {
            return Render.descendants(root).find(item => typeof item.checked === "boolean" && /smooth|stepp|interpol/i.test(String(item.objectName) + " " + item.toolTip));
        }
        function mapStrip() {
            const layer = named("layer"), axes = named("axes");
            verify(waitForRendering(chart), "Map interpolation samples exclude only the unrelated selection overlay");
            const frame = logicalImage(chart), strip = [];
            for (let py = 2; py < layer.height - 2; ++py) {
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
        // Closed-form owner oracle: band boundaries are neighbour midpoints;
        // each blend extends one quarter of each adjacent band's own height.
        function edgeValue(y, x, bounds, levels, supports, smooth) {
            let own = -1;
            for (let i = 0; i < levels.length; ++i)
                if (y >= bounds[i] && y <= bounds[i + 1]) {
                    own = i;
                    break;
                }
            if (own < 0 || x < supports[own][0] || x > supports[own][1])
                return NaN;
            if (smooth)
                for (let i = 0; i < levels.length - 1; ++i) {
                    const lower = bounds[i + 1] - (bounds[i + 1] - bounds[i]) / 4;
                    const upper = bounds[i + 1] + (bounds[i + 2] - bounds[i + 1]) / 4;
                    if (y >= lower && y <= upper && x >= supports[i][0] && x <= supports[i][1] && x >= supports[i + 1][0] && x <= supports[i + 1][1])
                        return levels[i] + (levels[i + 1] - levels[i]) * (y - lower) / (upper - lower);
                }
            return levels[own];
        }
        function checkEdgePixels(bounds, levels, supports, columns, smooth) {
            verify(waitForRendering(chart), "The independent band-colour observation has a completed frame without its selection overlay");
            const layer = named("layer"), axes = named("axes"), frame = logicalImage(chart);
            const table = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/maps.json")).viridis.colours;
            const dy = (axes.axisY.max - axes.axisY.min) / layer.height;
            for (let row = 0; row < levels.length; ++row)
                for (const fraction of [.1, .2, .4, .6, .8, .9])
                    for (const x of columns) {
                        const y = bounds[row] + fraction * (bounds[row + 1] - bounds[row]);
                        if (y <= axes.axisY.min + dy * 2 || y >= axes.axisY.max - dy * 2)
                            continue;
                        const point = layer.mapToItem(chart, (x - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width, (axes.axisY.max - y) / dy);
                        const pixel = frame.pixel(Math.round(point.x), Math.round(point.y));
                        const value = edgeValue(y, x, bounds, levels, supports, smooth);
                        if (!Number.isFinite(value)) {
                            compare(String(pixel), String(chart.colors.chartBackground), "A dataset's unsupported column stays empty through its whole band in both modes; row=" + row + " fraction=" + fraction + " x=" + x);
                        } else {
                            // At most two logical pixels of raster sampling uncertainty, never a data tolerance.
                            const candidates = [-2, -1, 0, 1, 2].map(delta => edgeValue(y + delta * dy, x, bounds, levels, supports, smooth)).filter(Number.isFinite).map(v => rgb(table[Math.max(0, Math.min(255, Math.round(v)))]));
                            verify(candidates.some(c => ["r", "g", "b"].every(k => Math.abs(c[k] - pixel[k]) <= 2 / 255)), "Map pixels retain their own dataset except inside the quarter-band edge zone; row=" + row + " fraction=" + fraction + " x=" + x + " smooth=" + smooth + " actual=" + pixel + " analytic intensity=" + value);
                        }
                    }
        }
        function test_map_edge_bands_data() {
            const rows = [];
            for (const kind of ["value", "file", "datablock"])
                for (const smooth of [false, true])
                    for (const dark of [false, true])
                        rows.push({
                            tag: kind + "-" + (smooth ? "smooth" : "stepped") + "-" + (dark ? "dark" : "light"),
                            kind,
                            smooth,
                            dark
                        });
            return rows;
        }
        function test_map_edge_bands(data) {
            let scan;
            if (data.kind === "datablock") {
                Preferences.resetToDefaults();
                Preferences.scanMapColours = "viridis";
                const root = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project"));
                Input.edgeBanks(SettingsProof, root);
                verify(Session.openProject(root), "The edge-blend witness opens independently written unequal-support datablocks");
                chart = factory.createObject(surface, {
                    project: Session.project,
                    mode: "map"
                });
                scan = Session.project.scanViews;
            } else
                scan = open("map", "edges");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            const rows = axisControl("y");
            if (data.kind === "file")
                choose(rows, 1);
            const toggle = interpolationToggle(chart);
            verify(toggle !== undefined && toggle.enabled && toggle.visible, "Every row kind exposes the enabled hard-edge/edge-blend control");
            compare(toggle.checked, true, "Every row kind begins with the remembered default edge blending");
            if (!data.smooth) {
                mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                tryCompare(toggle, "checked", false, 1000, "Real toolbar input selects hard band edges");
            }
            verify(waitForRendering(chart), "The selected edge mode reaches the actual Map pixels");
            const bounds = data.kind === "value" ? [25, 175, 475, 775] : data.kind === "file" ? [-.5, .5, 1.5, 2.5] : [-.5, .5, 1.5];
            checkEdgePixels(bounds, data.kind === "datablock" ? [0, 255] : [0, 128, 255], data.kind === "datablock" ? [[10000, 50000], [30000, 90000]] : [[10, 50], [30, 90], [20, 80]], data.kind === "datablock" ? [40000, 20000, 70000] : [40, 20, 85], data.smooth);
        }
        function test_map_centre_crossing_data() {
            const rows = [];
            for (const near of [true, false])
                for (const smooth of [false, true])
                    for (const dark of [false, true])
                        rows.push({
                            tag: (near ? "near" : "far") + (smooth ? "-smooth" : "-stepped") + (dark ? "-dark" : "-light"),
                            near,
                            smooth,
                            dark
                        });
            return rows;
        }
        function test_map_centre_crossing(data) {
            const coordinates = data.near ? [100, 110, 1000] : [100, 990, 1000];
            const scan = open("map", data.near ? "uneven-near" : "uneven-far");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            compare([scan.rowOf(0), scan.rowOf(1), scan.rowOf(2)], coordinates, "The unequal-band witness uses the independently specified row coordinates");
            const toggle = interpolationToggle(chart);
            if (toggle.checked !== data.smooth)
                mouseClick(toggle, toggle.width / 2, toggle.height / 2);
            const bounds = data.near ? [95, 105, 555, 1005] : [-345, 545, 995, 1005];
            chart.setZoom([30, 60], data.near ? [95, 235] : [860, 1005]);
            verify(waitForRendering(chart), "The highly uneven Map draws its zoomed edge without selection ink");
            const layer = named("layer"), axes = named("axes"), frame = logicalImage(chart);
            const dy = (axes.axisY.max - axes.axisY.min) / layer.height;
            const colours = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/maps.json")).viridis.colours;
            const witnesses = data.near ? [100, 103, 107, 109, 110, 111, 130, 170, 210, 217.5, 225] : [870, 882.5, 900, 950, 989, 990, 991, 993, 997, 1000];
            for (const y of witnesses) {
                const point = layer.mapToItem(chart, layer.width / 2, (axes.axisY.max - y) / dy);
                const actual = frame.pixel(Math.round(point.x), Math.round(point.y));
                const candidates = [-2, -1, 0, 1, 2].map(offset => edgeValue(y + offset * dy, 45, bounds, [0, 128, 255], [[10, 112.4], [10, 112.4], [10, 112.4]], data.smooth)).map(value => rgb(colours[Math.max(0, Math.min(255, Math.round(value)))]));
                verify(candidates.some(value => ["r", "g", "b"].every(channel => Math.abs(value[channel] - actual[channel]) <= 2 / 255)), "Actual Map blending follows edge-zone ownership through the middle row centre to its quarter-band endpoint; y=" + y + " smooth=" + data.smooth + " actual=" + actual);
            }
        }
        function test_map_intensity_labels_data() {
            const cases = [];
            for (const scale of ["linear", "sqrt", "log"])
                for (const range of ["large", "plain"])
                    for (const dark of [false, true])
                        cases.push({
                            tag: scale + "-" + range + (dark ? "-dark" : "-light"),
                            scale,
                            range,
                            dark
                        });
            return cases;
        }
        function test_map_intensity_labels(data) {
            const low = data.range === "large" ? 437233 : 1;
            const high = data.range === "large" ? 9853782 : 437233;
            const expected = data.range === "large" ? (data.scale === "log" ? ["437233", "9.854e6"] : ["0.437e6", "9.854e6"]) : ["1", "437233"];
            const root = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/scan_template/project"));
            for (const [index, file] of ["all594687.dat", "all594791.dat", "all594842.dat"].entries()) {
                const text = "XYDATA independent intensity endpoints\nTEMP " + [100, 250, 700][index] + "\n10 " + low + " 1\n40 " + high + " 1\n80 " + low + " 1\n";
                verify(SettingsProof.write(root, "experiments/d20_scan/" + file, text), "The label fixture writes its declared original-count endpoints");
            }
            Preferences.resetToDefaults();
            Preferences.patternYScale = data.scale;
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            verify(Session.openProject(root), "The intensity-label actor opens the independent scan");
            const component = Qt.createComponent(Qt.resolvedUrl("../../../app/qml/Components/ScanViewChart.qml"));
            compare(component.status, Component.Ready, "The label actor loads the actual production scan QML: " + component.errorString());
            chart = component.createObject(surface, {
                project: Session.project,
                mode: "map",
                shown: false,
                width: 1100,
                height: 760
            });
            verify(chart !== null, "The actual scan chart is created with the native production model");
            ready(Session.project.scanViews);
            const layer = named("layer");
            const scale = data.scale === "log" ? PatternChartController.Log10 : data.scale === "sqrt" ? PatternChartController.Sqrt : PatternChartController.Linear;
            const reference = patternReferenceFactory.createObject(surface);
            verify(reference !== null, "The formatter comparison reaches the actual Pattern chart");
            const axis = Qt.createQmlObject('import QtGraphs; ValueAxis {}', surface);
            axis.min = layer.displayMin;
            axis.max = layer.displayMax;
            axis.tickAnchor = layer.displayMin;
            axis.tickInterval = layer.displayMax - layer.displayMin;
            const values = reference.yValues(axis, scale);
            compare(values.length, 2, "The Pattern reference has exactly the same two intensity ticks as the colour bar");
            fuzzyCompare(values[0], low, Math.abs(low) * 1e-10, "The lower rendered endpoint is the fixture's original count, including inverse scale conversion");
            fuzzyCompare(values[1], high, high * 1e-10, "The upper rendered endpoint is the fixture's original count, including inverse scale conversion");
            const format = NumberText.axisFormat(values, data.scale !== "log");
            for (let index = 0; index < 2; ++index)
                compare(reference.yLabelText(String(index ? axis.max : axis.min), axis, scale, format), expected[index], "The actual Pattern intensity formatter agrees with the independently written expected string");
            reference.destroy();
            axis.destroy();
            const mismatches = [];
            for (const width of [480, 1100]) {
                chart.width = width;
                verify(waitForPolish(chart) && waitForRendering(chart), "Each narrow and wide Map layout has a completed rendered frame");
                for (const [index, end] of ["min", "max"].entries()) {
                    const label = named("colourBar." + end);
                    verify(label.visible && label.text.length > 0 && label.width > 0 && label.height > 0, "Both intensity endpoints have actual visible text");
                    if (label.text !== expected[index])
                        mismatches.push(end + " at " + width + ": " + label.text + " instead of " + expected[index]);
                    const at = label.mapToItem(chart, 0, 0);
                    verify(at.x >= 0 && at.y >= 0 && at.x + label.width <= chart.width && at.y + label.height <= chart.height, "Each complete colour-bar label remains inside the chart at both widths and themes");
                    verify(label.contentWidth <= label.width + 0.5, "The colour-bar text is fully laid out inside its label without truncation");
                }
            }
            compare(mismatches, [], "Colour-bar endpoints format the same original value exactly as the Pattern intensity axis");
        }
        function test_map_default_and_saved_choice() {
            const location = Globals.Vars.settingsFile;
            SettingsProof.erase(location, "ScanViews", "mapColours");
            compare(SettingsProof.settingFacts(location, "ScanViews", "mapColours").type, "invalid", "The default witness removes the actual saved Map choice before a fresh engine reads it");
            const code = 'import QtQuick; import edi.app; QtObject { property string preference:Preferences.scanMapColours }';
            const fresh = SettingsProof.restart(code);
            verify(!fresh.error, "The absent-choice witness starts a fresh production Map engine");
            compare(fresh.preference, "ramp:ediNatural", "The absent Map preference uses the same Edi Natural shades default");
            const scan = open("map");
            Preferences.scanMapColours = fresh.preference;
            ready(scan);
            compare(chart.mapChoices[paletteSelector("map").currentIndex], "ramp:ediNatural", "The actual Map selector displays the independently reloaded absent-key default");
            const selector = paletteSelector("map"), choice = chart.mapChoices.indexOf("plasma");
            verify(choice >= 0, "A distinct published colour map provides the saved-choice witness");
            choose(selector, choice);
            tryCompare(Preferences, "scanMapColours", "plasma", 1000, "Real Map selector input updates the saved choice");
            tryVerify(() => SettingsProof.value(location, "ScanViews", "mapColours") === "plasma", 2000, "The selected Map choice reaches the actual settings file before restart");
            const saved = SettingsProof.restart(code);
            verify(!saved.error, "The saved-choice witness starts another fresh production engine");
            compare(saved.preference, "plasma", "The remembered Map preference remains bound to its toolbar selector");
        }
        function test_map_interpolation_default() {
            Preferences.resetToDefaults();
            const scan = open("map", "rows");
            ready(scan);
            verify(interpolationToggle(chart) !== undefined, "The Map toolbar exposes its actual stepped/smooth toggle");
            verify(smoothStrip(mapStrip()), "A new profile defaults to smooth blending across the analytic band edges");
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
            checkEdgePixels([25, 175, 475, 775], [0, 128, 255], [[10, 112.4], [10, 112.4], [10, 112.4]], [50], data.smooth);
            const checked = toggle.checked;
            tryVerify(() => SettingsProof.value(Globals.Vars.settingsFile, "ScanViews", "mapSmooth") === checked, 2000, "The real edge-mode preference reaches its settings file before the fresh-engine memory check");
            const fresh = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property bool saved:Preferences.scanMapSmooth }');
            verify(!fresh.error, "A fresh production engine reloads the interpolation setting exercised by the actual control");
            compare(fresh.saved, checked, "Both actual stepped and smooth choices are remembered in a fresh engine");
        }
        function test_scan_toolbar_and_top_margin_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_scan_toolbar_and_top_margin(data) {
            const scan = open(data.mode);
            ready(scan);
            const controls = Render.descendants(chart).filter(item => item.visible && typeof item.count === "number" && typeof item.currentIndex === "number" && typeof item.textAt === "function");
            const toolbarColour = controls.filter(item => /palette|colourMap/.test(item.objectName));
            compare(toolbarColour.length, data.mode === "map" ? 1 : 0, "Only the Map retains a toolbar colour selector after colour choices move to Preferences");
            const layer = named("layer"), plot = layer.mapToItem(chart, 0, 0), axis = axisControl("x"), at = axis.mapToItem(chart, 0, 0);
            verify(at.y >= 0 && at.y + axis.height <= plot.y && at.y > 0, "The scan toolbar keeps its actual axis line and positive plot margin after palette relocation");
            for (const text of Render.texts(chart)) {
                const point = text.mapToItem(chart, 0, 0);
                verify(point.y >= 0 && point.y + text.height <= chart.height + .5, "Every scan axis and key label stays inside the chart after palette relocation");
            }
            const before = grabImage(layer), palette = paletteSelector(data.mode), previous = palette.currentIndex;
            choose(palette, (previous + 1) % palette.count);
            verify(!before.equals(grabImage(layer)), "Real colour-choice input in Preferences or the Map shortcut changes actual scan pixels");
        }

        function test_owner_axis_name_data() {
            return ["pattern", "stacked", "map"].map(mode => ({
                        tag: mode,
                        mode
                    }));
        }
        function test_owner_axis_name(data) {
            const scan = open(data.mode === "pattern" ? "stacked" : data.mode);
            ready(scan);
            if (data.mode === "pattern") {
                chart.destroy();
                chart = patternReferenceFactory.createObject(surface, {
                    experiment: Session.project.currentExperiment,
                    shown: true,
                    visible: true
                });
            }
            const selector = data.mode === "pattern" ? findChild(chart, "chart.toolbar.xaxis") : axisControl("x");
            verify(selector !== null, "Each actual chart exposes its x selector before caption input");
            tryVerify(() => selector.enabled, 8000, "Calculated data make the real d-spacing entry selectable");
            let dSeen = false;
            for (let index = 0; index < selector.count; ++index) {
                choose(selector, index);
                const entry = selector.textAt(index);
                if (/^(x:\s*)?d(?:-spacing)?$/.test(entry)) {
                    dSeen = true;
                    compare(selector.displayText, "x: d-spacing", "The selected d-axis caption is the owner's full quantity name on every chart");
                    compare(entry, "x: d-spacing", "The d-axis list entry uses the same full x: d-spacing caption as its selection");
                } else
                    compare(selector.displayText.replace(/^x:\s*/, ""), entry.replace(/^x:\s*/, ""), "Every other opened x-axis entry and selected quantity retain the same name");
            }
            verify(dSeen && selector.count > 1, "The name witness exercises both native and d quantities");
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
            // The chart uses the core point column, whose CW angle is raw (ADR-0041).
            const expected = [10, 112.4].map(x => 1.87 / (2 * Math.sin(x * Math.PI / 360))).sort((a, b) => a - b);
            tryVerify(() => Math.abs(axes.axisX.min - expected[0]) < 1e-5 && Math.abs(axes.axisX.max - expected[1]) < 1e-5, 2000, "Selecting newly available d uses the declared raw-angle Bragg point column at both nontrivial domain ends" + "; expected=" + JSON.stringify(expected) + " observedAtPollStart=" + JSON.stringify([axes.axisX.min, axes.axisX.max]) + " selector=" + selector.displayText + " nativeEndpoints=[10,112.4] wavelength=1.87 zero=0.29 convention=raw-angle");
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
            const layer = named("layer"), centre = chart.width / 2;
            verify(Math.abs((left + right) / 2 - centre) <= 1, "The wrapped button line shares the chart and dataset selector's horizontal centre" + "; expectedSelectorCentre=" + centre + " readLineCentre=" + ((left + right) / 2) + " readExtents=" + JSON.stringify([left, right]) + " plot=" + JSON.stringify({
                left: layer.mapToItem(chart, 0, 0).x,
                width: layer.width
            }) + " tools=" + JSON.stringify(tools.map(item => ({
                        name: item.objectName,
                        left: item.mapToItem(chart, 0, 0).x,
                        right: item.mapToItem(chart, item.width, 0).x
                    }))));
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
            const coarse = logicalImage(chart);
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
                        const y = (axes.axisY.max - (stackedAt(1, 3, intensity / 255))) / (axes.axisY.max - axes.axisY.min) * layer.height;
                        const at = layer.mapToItem(chart, column + .5, y);
                        let hit = false;
                        for (let dx = -1; dx <= 1; ++dx)
                            for (let dy = -2; dy <= 2; ++dy)
                                hit = hit || ink(coarse.pixel(Math.round(at.x) + dx, Math.round(at.y) + dy), expected, chart.colors.chartBackground);
                        verify(hit, "A zoomed Stacked pixel column retains the true independently enumerated visible minimum and maximum");
                    }
                    for (const outside of [low - 40, high + 40].filter(value => value > 0 && value < 255)) {
                        const y = (axes.axisY.max - (stackedAt(1, 3, outside / 255))) / (axes.axisY.max - axes.axisY.min) * layer.height;
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
            const frame = logicalImage(chart);
            let checked = 0;
            for (let i = 1600; i <= 1616; ++i) {
                const x = 10 + i / 40;
                if (x < axes.axisX.min || x > axes.axisX.max)
                    continue;
                const px = (x - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width;
                const intensity = values[i % 8];
                if (data.mode === "stacked") {
                    const at = layer.mapToItem(chart, px, (axes.axisY.max - (stackedAt(1, 3, intensity / 255))) / (axes.axisY.max - axes.axisY.min) * layer.height);
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
            if (data.mode !== "evolution") {
                const scan = open(data.mode, "rows");
                Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
                ready(scan);
                for (const row of [0, 2, 1]) {
                    Session.project.currentExperimentIndex = row;
                    selectionLabel(row);
                }
                return;
            }
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
            }
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            verify(layer !== null && axes !== null && pointer !== null && marker !== null, "Each scan chart supplies a real selected-pattern indicator and plot for pixel inspection");
            Session.project.currentExperimentIndex = 0;
            verify(waitForRendering(chart), "The initial indicator is rendered away from the next selected row");
            const opacity = marker.opacity;
            marker.opacity = 0;
            verify(waitForRendering(chart), "The indicator pixel observer captures the actual data underlay with only the prior indicator transparent");
            const background = logicalImage(chart);
            marker.opacity = opacity;
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
                verify(["r", "g", "b"].every(c => Math.abs(strip.color[c] - colour) < 1e-9) && Math.abs(strip.color.a - (core ? 1 : .5)) <= 1 / 65535, "The actual core and half-transparent border use the exact owner colours for this theme" + "; strip=" + index + " expectedRGB=" + colour + " expectedAlpha=" + (core ? 1 : .5) + " readColour=" + strip.color + " readAlpha=" + strip.color.a);
                for (const along of [.25, .5, .75]) {
                    const at = strip.mapToItem(chart, vertical ? strip.width / 2 : strip.width * along, vertical ? strip.height * along : strip.height / 2);
                    const actual = logicalImage(chart).pixel(Math.floor(at.x), Math.floor(at.y)), before = background.pixel(Math.floor(at.x), Math.floor(at.y));
                    verify(["r", "g", "b"].every(c => Math.abs(actual[c] - (core ? colour : (colour + before[c]) / 2)) <= 1 / 255), "Rendered indicator core and border pixels equal the exact themed alpha composite over the independent pre-selection frame" + "; strip=" + index + " x=" + Math.floor(at.x) + " y=" + Math.floor(at.y) + " expectedRGB=" + JSON.stringify(["r", "g", "b"].map(c => core ? colour : (colour + before[c]) / 2)) + " read=" + actual + " readAlpha=" + actual.a + " underlay=" + before);
                }
            }
            const actualCentre = marker.mapToItem(layer, marker.width / 2, marker.height / 2);
            verify(Math.abs((vertical ? actualCentre.x : actualCentre.y) - position) <= 1, "The indicator centre follows the selected physical coordinate, rather than its top or left edge" + "; expected=" + position + " read=" + (vertical ? actualCentre.x : actualCentre.y));
        }
        function excludedButton(root) {
            return Render.descendants(root).find(item => item.visible && typeof item.checked === "boolean" && /exclud.*region|region.*exclud|Show only the included range/i.test(String(item.objectName) + " " + item.toolTip));
        }
        function test_owner_excluded_regions_data() {
            const rows = [];
            for (const mode of ["stacked", "map"]) {
                rows.push({
                    tag: mode,
                    mode,
                    scanOnly: false
                });
                rows.push({
                    tag: mode + "-scan",
                    mode,
                    scanOnly: true
                });
            }
            return rows;
        }
        function test_owner_excluded_regions(data) {
            const scan = open(data.mode, "excluded");
            ready(scan);
            const pattern = createTemporaryObject(patternReferenceFactory, surface, {
                experiment: Session.project.currentExperiment,
                visible: !data.scanOnly,
                shown: true
            });
            const other = createTemporaryObject(factory, surface, {
                project: Session.project,
                mode: data.mode === "map" ? "stacked" : "map",
                shown: true
            });
            verify(pattern !== null && other !== null, "The excluded-range actor reaches all three actual chart implementations");
            const roots = data.scanOnly ? [chart, other] : [pattern, chart, other], buttons = roots.map(excludedButton);
            const active = data.scanOnly ? 0 : 1;
            verify(buttons.every(item => item !== undefined), "Pattern, Stacked and Map expose the same included-range toggle");
            for (let index = 0; index < roots.length; ++index) {
                const control = buttons[index];
                const isPattern = roots[index] === pattern;
                const peer = Render.descendants(roots[index]).find(item => isPattern ? /toolbar.legend$/.test(item.objectName) : /toolbar.zoom$/.test(item.objectName));
                compare(control.fontIcon, "eraser", "Every included-range toggle uses the sidebar's eraser icon");
                compare(control.toolTip, "Show only the included range", "All three charts use the owner's exact included-range tooltip");
                verify(peer !== undefined && control.parent === peer.parent && Math.abs(control.mapToItem(roots[index], 0, 0).y - peer.mapToItem(roots[index], 0, 0).y) < 1, "The included-range toggle shares the actual Pattern legend/tooltip group or scan zoom/reset group");
            }
            const original = SettingsProof.text(Qt.resolvedUrl("file:" + Session.project.path), "experiments/d20.edi");
            function activate(index, wanted) {
                roots.forEach((root, at) => root.visible = at === index);
                const control = buttons[index];
                if (control.checked !== wanted)
                    mouseClick(control, control.width / 2, control.height / 2);
                tryVerify(() => buttons.every(button => button.checked === wanted), 1000, "Real input on each chart updates the one shared included-range choice on all three charts");
                verify(waitForRendering(roots[index]), "The shared included-range choice reaches an actual chart frame");
            }
            for (let index = 0; index < roots.length; ++index) {
                activate(index, true);
                const fresh = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property bool allOn:Preferences.chartIncludedOnly }');
                verify(!fresh.error && fresh.allOn, "The single included-range setting exercised by all three actual chart controls survives a fresh production engine");
                activate(index, false);
            }
            activate(active, false);
            verify(waitForRendering(chart), "The excluded-data observer captures the real plot with equal dataset colours");
            const layer = named("layer"), axes = named("axes");
            const x = value => Math.round((value - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * (layer.width - 1));
            const traceY = stackedAt(0, 3, 64 / 255);
            const y = Math.round((axes.axisY.max - (data.mode === "map" ? 175 : traceY)) / (axes.axisY.max - axes.axisY.min) * (layer.height - 1));
            function sample(image, x, y) {
                const at = layer.mapToItem(chart, x, y);
                return image.pixel(Math.floor(at.x), Math.floor(at.y));
            }
            const full = logicalImage(chart), expected = rgb(Approved.colours(SettingsProof, "ediNatural", "measured", 3, false)[0]);
            if (data.mode === "map")
                verify(String(sample(full, x(36), y)) !== String(sample(full, x(43), y)), "Off retains the independently different 32- and 64-count Map bands inside the excluded range");
            activate(active, true);
            const gap = logicalImage(chart), blank = sample(gap, x(41), y - 6);
            verify(blank.a > 0, "On draws a visible tint in the otherwise empty excluded gap");
            if (data.mode === "stacked")
                verify([-2, -1, 0, 1, 2].some(dy => ink(sample(full, x(42), y + dy), expected, blank)), "Off draws the independently coloured measured trace over the same excluded-region tint retained by On; expected=" + expected + "; blank=" + blank + "; geometry=" + [x(42), y, layer.patternHeight, axes.axisY.min, axes.axisY.max] + "; samples=" + [-3, -2, -1, 0, 1, 2, 3].map(dy => String(sample(full, x(42), y + dy))));
            for (let px = x(40); px <= x(44); ++px)
                for (let dy = -2; dy <= 2; ++dy)
                    compare(String(sample(gap, px, y + dy)), String(sample(gap, px, Math.floor(layer.height * .15))), "On removes all measured ink inside the independently specified excluded interval, leaving an empty uniformly tinted gap" + "; x=" + px + " y=" + (y + dy) + " read=" + sample(gap, px, y + dy) + " expected=" + sample(gap, px, Math.floor(layer.height * .15)) + " referenceY=" + Math.floor(layer.height * .15));
            const outside = Math.round(layer.height * .8);
            verify(String(sample(gap, x(30), outside)) === String(sample(full, x(30), outside)), "The included-range toggle preserves drawable data outside the independent excluded interval");
            compare(SettingsProof.text(Qt.resolvedUrl("file:" + Session.project.path), "experiments/d20.edi"), original, "A display toggle preserves the independently specified excluded scientific ranges");
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
            applicationWindow = applicationFactory.createObject(null);
            verify(applicationWindow !== null && waitForRendering(applicationWindow.contentItem), "The mode witness also renders the actual status bar");
            const follow = findChild(applicationWindow, "statusBar.fit.follow");
            verify(data.kind !== "scan" || follow !== null, "The scan status bar supplies its Follow control");
            verify(data.kind === "scan" ? follow.visible : follow === null || !follow.visible && !follow.clickable && !follow.checked, "Follow is usable only for scans and cannot be activated for single or joint fits");
        }
        function test_joint_labels_outside_axis_data() {
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
        function test_joint_labels_outside_axis(data) {
            openJoint();
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            chart = factory.createObject(surface, {
                project: Session.project,
                mode: data.mode
            });
            const scan = Session.project.scanViews;
            ready(scan);
            const layer = named("layer"), axes = named("axes"), origin = layer.mapToItem(chart, 0, 0);
            compare(axes.axisY.visible, false, "Joint experiment names replace the entire numeric y axis on both views");
            const expected = Approved.colours(SettingsProof, "ediNatural", "measured", 2, data.dark);
            for (let row = 0; row < 2; ++row) {
                const name = ["expt_n2", "expt_s2"][row];
                const labels = Render.texts(chart).filter(item => item.text === name);
                compare(labels.length, 1, "Each joint experiment has exactly one actual visible name, without a duplicate inside the plot");
                const label = labels[0], left = label.mapToItem(chart, 0, 0), right = label.mapToItem(chart, label.width, label.height);
                verify(left.x >= 0 && right.x < origin.x, "Every complete joint experiment name lies outside the plot to the left of its y axis");
                const centre = label.mapToItem(chart, label.width / 2, data.mode === "stacked" ? label.height : label.height / 2).y;
                const coordinate = data.mode === "stacked" ? stackedAt(row, 2, 0) : row;
                const wanted = origin.y + (axes.axisY.max - coordinate) / (axes.axisY.max - axes.axisY.min) * layer.height;
                verify(Math.abs(centre - wanted) <= 1, "Each joint label ends at its Stacked baseline or is centred on its Map row");
                tryCompare(label, "color", row === Session.project.currentExperimentIndex ? Style.Colors.themeAccent : rgb(expected[row]), 2000, "Each joint dataset name settles to its dataset colour or the selected bold accent in both themes");
                let parent = label.parent;
                while (parent && parent.segments === undefined)
                    parent = parent.parent;
                verify(parent !== null && parent.segments !== undefined, "The joint name belongs to an actual icon-and-name row");
                const icons = Render.texts(parent).filter(item => item !== label && String(item.font.family).includes("Awesome"));
                compare(icons.length, 1, "Every outside joint row label has exactly one real experiment icon");
                verify(parent.segments.some(piece => piece.icon === "microscope"), "The joint row uses the prior experiment list's microscope icon");
                compare(String(icons[0].color).toLowerCase(), row === Session.project.currentExperimentIndex ? String(Style.Colors.themeAccent).toLowerCase() : expected[row], "The experiment icon and its name share the independent dataset colour");
                verify(icons[0].mapToItem(chart, icons[0].width, 0).x <= left.x, "The experiment icon precedes its name outside the axis");
                const frame = logicalImage(chart), inkColour = row === Session.project.currentExperimentIndex ? Style.Colors.themeAccent : rgb(expected[row]);
                for (const item of [label, icons[0]]) {
                    const at = item.mapToItem(chart, 0, 0);
                    let painted = false;
                    for (let x = Math.ceil(at.x); x < Math.floor(at.x + item.width) && !painted; ++x)
                        for (let y = Math.ceil(at.y); y < Math.floor(at.y + item.height) && !painted; ++y)
                            painted = ink(frame.pixel(x, y), inkColour, chart.colors.chartBackground);
                    verify(painted, "Both the outside joint icon and name have actual drawable ink in the dataset colour");
                }
            }
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
            exposeStack();
            compare(scan.count, 2, "Joint chart rows cover every project experiment exactly once");
            compare(scan.rowOf(0), 0, "The first joint experiment occupies index zero rather than a scan coordinate");
            compare(scan.rowOf(1), 1, "The second joint experiment follows the first in project order");
            fuzzyCompare(scan.xMin, 813, 1e-6, "The native joint range starts at the first bank's own offset plus calibrated d minimum");
            fuzzyCompare(scan.xMax, 6981, 1e-6, "The native joint range covers the second bank's distinct calibrated maximum");
            const names = Probe.rows(Session.project.experiments).map(row => String(row.name));
            compare(names.join(","), "expt_n2,expt_s2", "The independent joint fixture retains its declared experiment names in project order");
            const texts = Render.texts(chart).map(item => item.text).join(" ");
            verify(names.length === 2 && names.every(name => name !== "" && texts.includes(name)), "Joint rows are visibly labelled by their real experiment names in project order");
            const selector = axisControl("x");
            tryVerify(() => selector.enabled, 8000, "Real calculated bank d coordinates become selectable");
            choose(selector, 1);
            const axes = named("axes"), layer = named("layer");
            tryVerify(() => Math.abs(axes.axisX.min - .8) < 1e-5 && Math.abs(axes.axisX.max - 2.8) < 1e-5, 2000, "Both nontrivial TOF calibrations share the independently known physical d range" + "; expected=[0.8,2.8] observedAtPollStart=" + JSON.stringify([axes.axisX.min, axes.axisX.max]) + " selector=" + selector.displayText);
            Session.project.currentExperimentIndex = 0;
            verify(waitForRendering(chart), "The joint d view has a completed actual frame");
            const frame = logicalImage(chart), measured = Approved.colours(SettingsProof, "ediNatural", "measured", 2, false);
            for (let row = 0; row < 2; ++row) {
                const x = (1.8 - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width;
                const y = data.mode === "stacked" ? stackedAt(row, 2, 1) : row;
                const at = layer.mapToItem(chart, x, (axes.axisY.max - y) / (axes.axisY.max - axes.axisY.min) * layer.height + (data.mode === "map" ? (row === 0 ? -5 : 5) : 0));
                const expected = data.mode === "stacked" ? rgb(measured[row]) : rgb(Approved.colours(SettingsProof, "ediNatural", "measured", 1, false)[0]);
                let hit = false;
                for (let dx = -2; dx <= 2; ++dx)
                    for (let dy = -2; dy <= 2; ++dy)
                        hit = hit || ink(frame.pixel(Math.round(at.x) + dx, Math.round(at.y) + dy), expected, chart.colors.chartBackground);
                verify(hit, "Each bank's independently placed peak aligns at physical d=1.8 on the same actual chart scale" + "; row=" + row + " expectedPeakD=1.8 readDomain=" + JSON.stringify([axes.axisX.min, axes.axisX.max, axes.axisY.min, axes.axisY.max]) + " centre=" + JSON.stringify(at) + " expectedColour=" + expected + " sampleWindow=" + JSON.stringify(Array.from({
                    length: 25
                }, (_, i) => ({
                            x: Math.round(at.x) + i % 5 - 2,
                            y: Math.round(at.y) + Math.floor(i / 5) - 2,
                            colour: String(frame.pixel(Math.round(at.x) + i % 5 - 2, Math.round(at.y) + Math.floor(i / 5) - 2))
                        }))));
            }
            const pointer = named("pointer");
            const py = (axes.axisY.max - 1) / (axes.axisY.max - axes.axisY.min) * pointer.height;
            mouseClick(pointer, pointer.width * .4, Math.max(2, py));
            tryCompare(Session.project, "currentExperimentIndex", 1, 1000, "Actual joint-chart input selects the second real experiment");
            selectionLabel(1);
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
                verify(Math.abs(control.width - (maximum + clearance)) <= 1, "Every toolbar combobox fits its own longest entry and normal arrow/padding, with at most one pixel of rounding room; selector=" + control.objectName + " width=" + control.width + " expected=" + (maximum + clearance) + " entries=" + JSON.stringify(entries) + " font=" + JSON.stringify(control.font) + " measuredFont=" + JSON.stringify(metrics.font) + " cachedLongest=" + control.widestEntry + " maximumTextWidth=" + maximum + " clearanceSum=" + clearance + " paddings=" + JSON.stringify({
                    labelLeft: label.leftPadding,
                    labelRight: label.rightPadding,
                    controlLeft: control.leftPadding,
                    controlRight: control.rightPadding
                }));
                widths.push(control.width);
            }
            verify(Math.max(...widths) - Math.min(...widths) > 1, "Unequal longest texts produce individual selector widths rather than one shared width");
        }
        function test_joint_user_chosen_axes_data() {
            const rows = [];
            for (const mode of ["stacked", "map"])
                for (const axes of ["tof", "cwl", "mixed"])
                    rows.push({
                        tag: mode + "-" + axes,
                        mode,
                        axes
                    });
            return rows;
        }
        function test_joint_user_chosen_axes(data) {
            const root = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project"));
            Input.joint(SettingsProof, root, false, data.axes);
            verify(Session.openProject(root), "Every native-axis witness opens independently calibrated real joint experiments: " + Session.lastError);
            const page = createTemporaryObject(analysisFactory, surface, {
                visible: false,
                current: false
            });
            verify(page !== null, "The any-joint gate reaches the actual Analysis tab declarations");
            for (const mode of ["stacked", "map"])
                compare(page.mainTabs.find(item => item.objectName === "mainArea.analysis.tab." + mode).enabled, true, "Both scan-view tabs are enabled for TOF, constant-wavelength and mixed-axis joint fits");
            chart = factory.createObject(surface, {
                project: Session.project,
                mode: data.mode
            });
            const scan = Session.project.scanViews;
            ready(scan);
            compare(scan.count, 2, "Every real joint-fit axis witness draws both measured experiments");
            const selector = axisControl("x");
            const entries = [];
            for (let i = 0; i < selector.count; ++i)
                entries.push(selector.textAt(i));
            const dIndex = entries.findIndex(text => /^(?:x:\s*)?d(?:$|[ -])/.test(text));
            verify(dIndex >= 0, "Every joint fit offers physical d as a user-selectable common quantity");
            if (data.axes === "mixed") {
                compare(entries.length, 1, "Unlike native quantities are not offered as one mixed 2theta/TOF axis");
                verify(!entries.some(text => /TOF|2θ|two.theta/i.test(text)), "A mixed joint fit exposes d only, never one bank's native quantity for all banks");
                const axes = named("axes");
                tryVerify(() => Math.abs(axes.axisX.min - .8) < 1e-5 && Math.abs(axes.axisX.max - 3.2) < 1e-5, 8000, "A mixed native-axis fit actually draws the independently computed common d union" + "; expected=[0.8,3.2] observedAtPollStart=" + JSON.stringify([axes.axisX.min, axes.axisX.max]) + " entries=" + JSON.stringify(entries) + " readIndex=" + selector.currentIndex);
            } else {
                const nativeIndex = entries.findIndex(text => data.axes === "tof" ? /TOF/i.test(text) : /2θ|two.theta/i.test(text));
                verify(nativeIndex >= 0 && nativeIndex !== dIndex, "A shared native quantity remains available beside d, regardless of how well the banks align visually");
                tryVerify(() => selector.enabled, 8000, "A real joint calculation makes both physical/native choices usable");
                const native = data.axes === "tof" ? [813, 6981] : [Math.asin(1.54 / 6.4) * 360 / Math.PI, Math.asin(1.87 / 2.4) * 360 / Math.PI];
                for (const index of [nativeIndex, dIndex, nativeIndex]) {
                    choose(selector, index);
                    const axes = named("axes"), expected = index === nativeIndex ? native : data.axes === "tof" ? [.8, 2.8] : [1.2, 3.2];
                    tryVerify(() => Math.abs(axes.axisX.min - expected[0]) < 1e-5 && Math.abs(axes.axisX.max - expected[1]) < 1e-5, 2000, "Actual joint-axis input uses every bank's own native or independently calibrated d coordinates in both directions" + "; expected=" + JSON.stringify(expected) + " observedAtPollStart=" + JSON.stringify([axes.axisX.min, axes.axisX.max]) + " selectedIndex=" + index + " readIndex=" + selector.currentIndex + " readText=" + selector.displayText);
                }
            }
        }
        function choosePreference(label, wanted) {
            const box = preferenceColour(label);
            let index = -1;
            for (let i = 0; i < box.count; ++i)
                if (String(box.textAt(i)).toLowerCase() === wanted.toLowerCase())
                    index = i;
            verify(index >= 0, "The actual " + label + " preference offers the independently named choice " + wanted);
            preferencesSelector = box;
            choose(box, index);
            return box.currentText;
        }
        function currentPreference(label) {
            const box = preferenceColour(label), result = box.currentText;
            preferencesSelector = box;
            verify(SettingsProof.key(box, Qt.Key_Escape), "Actual Escape input closes the observed Preferences dialog");
            tryCompare(preferencesDialog, "visible", false, 1000, "Preferences closes before colour rendering observations");
            return result;
        }
        function test_preferences_four_colour_choices_data() {
            return [
                {
                    tag: "light",
                    dark: false
                },
                {
                    tag: "dark",
                    dark: true
                }
            ];
        }
        function test_preferences_four_colour_choices(data) {
            const scan = open("stacked", "rows");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            exposeStack();
            const pattern = createTemporaryObject(patternReferenceFactory, surface, {
                experiment: Session.project.currentExperiment,
                visible: false,
                shown: true
            });
            verify(pattern !== null, "Independent structure/pattern choices are observed through the actual Pattern drawing");
            const refs = Approved.reference(SettingsProof).schemes;
            function check(structures, patterns) {
                pattern.visible = true;
                verify(waitForRendering(pattern), "The palette witness shows its paused Pattern chart before observing uploaded series colours");
                const series = Render.series(pattern), measured = series.find(item => item.objectName === "chart.series.meas"), bragg = series.find(item => item.objectName === "chart.series.bragg.0");
                verify(measured !== undefined && bragg !== undefined, "The colour-split witness reaches real measured and structure drawing series");
                const expectedMeasured = Approved.colours(SettingsProof, patterns, "measured", 3, data.dark)[1], expectedStructure = Approved.colours(SettingsProof, structures, "structures", 1, data.dark)[0];
                tryVerify(() => String(measured.color).toLowerCase() === expectedMeasured && String(bragg.color).toLowerCase() === expectedStructure, 2000, "Patterns and Structures independently follow their own approved colour choices" + "; chosen=" + JSON.stringify({
                    patterns: patterns,
                    structures: structures
                }) + " expected=" + JSON.stringify({
                    measured: expectedMeasured,
                    bragg: expectedStructure
                }) + " observedAtPollStart=" + JSON.stringify({
                    measured: String(measured.color),
                    bragg: String(bragg.color)
                }));
                Session.project.report.active = true;
                tryVerify(() => Session.project.report.model.pattern_styles !== undefined, 3000, "The colour split reaches the actual report style model");
                const reportMeas = Approved.colours(SettingsProof, patterns, "measured", 3, false)[1], reportStructure = Approved.colours(SettingsProof, structures, "structures", 1, false)[0];
                tryVerify(() => {
                    const styles = Session.project.report.model.pattern_styles;
                    return styles.some(row => row.key === "meas.1" && String(row.light).toLowerCase() === reportMeas) && styles.some(row => row.key === "bragg.0" && String(row.light).toLowerCase() === reportStructure);
                }, 3000, "The report follows the same independent structure/pattern choices after its deferred model update" + "; chosen=" + JSON.stringify({
                    patterns: patterns,
                    structures: structures
                }) + " expected=" + JSON.stringify({
                    "meas.1": reportMeas,
                    "bragg.0": reportStructure
                }) + " observedAtPollStart=" + JSON.stringify(Session.project.report.model.pattern_styles));
                pattern.visible = false;
            }
            choosePreference("Structures", refs[1].label);
            choosePreference("Patterns", refs[3].label);
            check(refs[1].id, refs[3].id);
            choosePreference("Structures", refs[2].label);
            check(refs[2].id, refs[3].id);
            choosePreference("Patterns", refs[4].label);
            check(refs[2].id, refs[4].id);
            choosePreference("Stacked", refs[1].label);
            choosePreference("Map", "Plasma");
            compare(String(chart.stackedPalette), refs[1].id, "The Stacked colour preference controls its own lines independently of Structures and Patterns");
            const layer = named("layer"), axes = named("axes"), frame = logicalImage(chart);
            const colours = Approved.colours(SettingsProof, refs[1].id, "measured", 3, data.dark);
            for (let row = 0; row < 3; ++row) {
                const y = stackedAt(row, 3, [0, 128, 255][row] / 255);
                const at = layer.mapToItem(chart, layer.width * .4, (axes.axisY.max - y) / (axes.axisY.max - axes.axisY.min) * layer.height);
                let hit = false;
                for (let dy = -2; dy <= 2; ++dy)
                    hit = hit || ink(frame.pixel(Math.round(at.x), Math.round(at.y) + dy), rgb(colours[row]), chart.colors.chartBackground);
                verify(hit, "Every Stacked line draws its independently approved preference colour in both themes");
            }
            const map = createTemporaryObject(factory, surface, {
                project: Session.project,
                mode: "map",
                shown: true
            });
            verify(map !== null && waitForRendering(map), "The independent Map preference reaches an actual completed image");
            compare(map.mapColours, "plasma", "The separate Map preference controls the map without changing the other three choices");
            const expected = [refs[2].label, refs[4].label, refs[1].label, "Plasma"];
            for (let i = 0; i < 4; ++i)
                compare(currentPreference(["Structures", "Patterns", "Stacked", "Map"][i]), expected[i], "Changing one of the four colour preferences preserves the other independently chosen values");
        }
        function test_preferences_map_shortcut_and_roster() {
            const scan = open("map");
            ready(scan);
            const roster = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/offered.json")).maps;
            compare(roster.length, 28, "The keep-all witness uses the owner's complete pinned candidate roster");
            const toolbar = named("toolbar.colourMap"), preference = preferenceColour("Map");
            const expectedTitles = roster.map(name => ApplicationInfo.scanColourTitle(name)).sort();
            for (const control of [toolbar, preference]) {
                const offered = [];
                for (let i = 0; i < control.count; ++i)
                    offered.push(control.textAt(i));
                verify(expectedTitles.every(title => offered.includes(title)), "All 28 independently frozen candidate identities are offered in both Map preference and shortcut");
            }
            choosePreference("Map", "Plasma");
            compare(toolbar.currentText, "Plasma", "The actual Preferences Map choice immediately updates the toolbar shortcut");
            let viridis = -1;
            for (let i = 0; i < toolbar.count; ++i)
                if (toolbar.textAt(i).toLowerCase() === "viridis")
                    viridis = i;
            verify(viridis >= 0, "The shortcut retains the independent viridis map witness");
            choose(toolbar, viridis);
            compare(currentPreference("Map").toLowerCase(), "viridis", "Actual Map-toolbar input updates the very same preference in the reverse direction");
            verify(interpolationToggle(chart) !== undefined && Render.descendants(chart).some(item => typeof item.checked === "boolean" && /reverse/i.test(String(item.objectName) + " " + item.toolTip)), "Reverse and stepped/smooth remain actual Map-toolbar controls beside the shared shortcut");
        }
        function test_preferences_four_choices_remembered() {
            const scan = open("stacked");
            ready(scan);
            const refs = Approved.reference(SettingsProof).schemes, labels = ["Structures", "Patterns", "Stacked", "Map"], expected = [refs[1].label, refs[3].label, refs[2].label, "Plasma"];
            for (let i = 0; i < 4; ++i)
                choosePreference(labels[i], expected[i]);
            const fresh = SettingsProof.restart('import QtQuick; import edi.app; Item { AppPreferencesDialog { id: dialog } Component.onCompleted: Preferences.dialogShown=true; function walk(item) {let out=[item];for(const child of item.children||[])out=out.concat(walk(child));return out;} readonly property var labels:["Structures","Patterns","Stacked","Map"]; readonly property var rows:walk(dialog.contentItem).filter(item=>item.rowLabel===true); function selected(label) {const row=rows.find(item=>String(item.text).replace(/:$/," ").trim()===label);if(!row)return "";const siblings=row.parent.children;const box=siblings.slice(siblings.indexOf(row)+1).find(item=>item.rowBox===true);return box?box.currentText:"";} property bool acceptanceReady:labels.every(label=>selected(label)!==""); property string saved:JSON.stringify(labels.map(label=>selected(label))) }');
            verify(!fresh.error && fresh.acceptanceReady, "A fresh actual Preferences engine restores all four real colour selectors");
            compare(fresh.saved, JSON.stringify(expected), "Four distinct colour choices are remembered independently across a fresh production settings engine");
        }
        Component {
            id: applicationFactory
            Main {
                width: 1500
                height: 1000
                visible: true
            }
        }
        function fullyExposed(item) {
            for (let parent = item.parent; parent; parent = parent.parent) {
                if (!parent.clip)
                    continue;
                const bounds = item.mapToItem(parent, 0, 0, item.width, item.height);
                if (bounds.x < -1 || bounds.y < -1 || bounds.x + bounds.width > parent.width + 1 || bounds.y + bounds.height > parent.height + 1)
                    return false;
            }
            return true;
        }
        function showSharedScan(pageName, mode) {
            Ui.click(test, Probe, applicationWindow, "appBar.tab." + pageName);
            let page;
            tryVerify(() => {
                page = Render.descendants(applicationWindow.contentItem).find(item => item.pageName === pageName && item.current);
                return page !== undefined;
            }, 2000, "Actual application input opens the requested scan-view page");
            tryVerify(() => !Ui.moving(applicationWindow.contentItem), 2000, "The scan page finishes moving before tab input");
            verify(waitForPolish(applicationWindow), "The actual application lays out its scan-view tabs");
            applicationWindow.update();
            verify(waitForRendering(applicationWindow.contentItem), "The actual page has a completed frame before scan-tab input");
            const tab = Array.from(page.mainTabs).find(item => item.text === (mode === "map" ? "Map" : "Stacked"));
            verify(tab !== undefined && tab.enabled, "Experiment and Analysis both offer enabled Stacked/Map tabs for scans and every joint fit");
            if (!tab.checked)
                mouseClick(tab, tab.width / 2, tab.height / 2);
            tryCompare(tab, "checked", true, 1000, "Actual pointer input chooses the requested Stacked or Map tab");
            tryVerify(() => !Ui.moving(applicationWindow.contentItem), 2000, "The requested shared scan chart finishes its transition");
            const found = Render.descendants(page).filter(item => item.objectName === "scanView." + mode && item.visible && item.shown);
            compare(found.length, 1, "The shown page contains exactly one eligible actual scan chart");
            chart = found[0];
            tryVerify(() => fullyExposed(named("pointer")), 2000, "The shown scan plot finishes its SwipeView transition inside every actual clip before capture");
            tryCompare(Session.project.scanViews, "loaded", Session.project.scanViews.count, 8000, "Shared measured views finish their real asynchronous data reads");
            if (!Session.project.scanViews.nativeShared) {
                tryCompare(Session.project.scanViews, "dAvailable", true, 8000, "Unlike native quantities wait for every calculated bank d column before observing a shared physical plot; observedAtPollStart=" + JSON.stringify({
                    loaded: Session.project.scanViews.loaded,
                    count: Session.project.scanViews.count,
                    dAvailable: Session.project.scanViews.dAvailable,
                    dShown: Session.project.scanViews.dShown,
                    calculating: Session.project.calculating,
                    lastError: Session.project.lastError
                }));
                tryCompare(Session.project.scanViews, "dShown", true, 1000, "Mixed native axes are actually placed on their only common d quantity");
            }
            applicationWindow.update();
            verify(waitForRendering(chart), "The shown shared scan drawing reaches a completed actual frame");
            return chart;
        }
        function test_experiment_analysis_scan_sharing_data() {
            const rows = [];
            for (const project of ["scan", "tof", "cwl", "mixed"])
                for (const origin of ["experiment", "analysis"])
                    for (const mode of ["stacked", "map"])
                        rows.push({
                            tag: project + "-" + origin + "-" + mode,
                            project,
                            origin,
                            mode
                        });
            return rows;
        }
        function test_experiment_analysis_scan_sharing(data) {
            Preferences.resetToDefaults();
            Style.Colors.theme = Style.Colors.LightTheme;
            Preferences.patternYScale = "linear";
            Preferences.chartHighlightSelected = false;
            Preferences.scanMapColours = "viridis";
            const root = SettingsProof.copyProject(Probe.repoUrl(data.project === "scan" ? "tests/fixtures/scan_template/project" : "docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project"));
            if (data.project === "scan")
                Input.prepare(SettingsProof, root, "bands");
            else
                Input.joint(SettingsProof, root, false, data.project);
            verify(Session.openProject(root), "Shared scan charts open real independently specified measured data before fitting: " + Session.lastError);
            verify(!Session.project.fit.running && Session.project.fit.scanFitted === 0, "The Experiment scan-view witness has performed no fit");
            applicationWindow = applicationFactory.createObject(null);
            verify(applicationWindow !== null && applicationWindow.visible, "The shared scan actor opens the actual application");
            applicationWindow.requestActivate();
            tryCompare(applicationWindow, "active", true, 2000, "Shared scan input reaches the active actual application window");
            const first = showSharedScan(data.origin, data.mode), scan = Session.project.scanViews;
            compare(scan.count, data.project === "scan" ? 3 : 2, "Before any fit the shared chart reads every independent measured dataset");
            const captureLayer = named("layer"), capture = Ui.windowRoot(applicationWindow), firstPixels = logicalImage(capture);
            function firstPixel(x, y) {
                const at = captureLayer.mapToItem(capture, x, y);
                return firstPixels.pixel(Math.round(at.x), Math.round(at.y));
            }
            verify(captureLayer.width > 100 && captureLayer.height > 100, "Before any fit the shared measured view has actual nonempty plot pixels");
            const colours = new Set();
            for (let x = 5; x < captureLayer.width - 5; x += 5)
                for (let y = 5; y < captureLayer.height - 5; y += 5)
                    colours.add(String(firstPixel(x, y)));
            verify(colours.size > 3, "Before any fit the actual plot contains measured map/curve ink rather than only an empty canvas");
            const expectedLine = rgb(Approved.colours(SettingsProof, "ediNatural", "measured", scan.count, false)[1]);
            const frozenMap = JSON.parse(SettingsProof.repoText("tests/fixtures/scan_views/maps.json")).viridis.colours;
            const mapReferences = new Set([32, 96, 128, 192, 255].map(index => frozenMap[index].toLowerCase()));
            let measuredInk = false;
            for (let x = 2; x < captureLayer.width - 2 && !measuredInk; ++x)
                for (let y = 2; y < captureLayer.height - 2 && !measuredInk; ++y) {
                    const pixel = firstPixel(x, y);
                    measuredInk = data.mode === "stacked" ? ink(pixel, expectedLine, chart.colors.chartBackground) : mapReferences.has(String(pixel).toLowerCase());
                }
            verify(measuredInk, "Before any fit the actual scan view contains independently identified measured-data ink, beyond its grid and selected marker");
            for (const quantity of ["x", "y", "z"]) {
                const control = axisControl(quantity);
                if (control.enabled && control.count > 1)
                    choose(control, (control.currentIndex + 1) % control.count);
            }
            const palette = paletteSelector(data.mode);
            choose(palette, (palette.currentIndex + 1) % palette.count);
            const selectionPointer = named("pointer"), selectionAxes = named("axes");
            const selectCoordinate = data.mode === "stacked" ? stackedAt(1, scan.count, 0) : scan.rowOf(1);
            const selectY = (selectionAxes.axisY.max - selectCoordinate) / (selectionAxes.axisY.max - selectionAxes.axisY.min) * selectionPointer.height;
            mouseClick(selectionPointer, selectionPointer.width * (data.mode === "stacked" ? (data.project === "scan" ? (scan.dShown ? .995 : .005) : (1.3 - selectionAxes.axisX.min) / (selectionAxes.axisX.max - selectionAxes.axisX.min)) : .4), Math.max(2, Math.min(selectionPointer.height - 2, selectY)));
            tryCompare(Session.project, "currentExperimentIndex", 1, 1000, "Real scan-view input selects a non-default measured dataset before changing pages; coordinate=" + selectCoordinate + " readIndex=" + Session.project.currentExperimentIndex);
            const pointer = named("pointer"), axes = named("axes");
            mouseDrag(pointer, pointer.width * .2, pointer.height * .2, pointer.width * .6, pointer.height * .6, Qt.LeftButton);
            let ranges = [axes.axisX.min, axes.axisX.max, axes.axisY.min, axes.axisY.max];
            const controls = Render.descendants(chart).filter(item => item.visible && typeof item.currentIndex === "number" && String(item.objectName).includes("toolbar"));
            const types = controls.map(item => [item.objectName, item.currentIndex]);
            const row = Session.project.currentExperimentIndex;
            selectionLabel(row);
            const next = data.origin === "experiment" ? "analysis" : "experiment";
            for (const pageName of [next, data.origin, next]) {
                const shown = showSharedScan(pageName, data.mode), actual = named("axes");
                verify([actual.axisX.min, actual.axisX.max, actual.axisY.min, actual.axisY.max].every((x, i) => Math.abs(x - ranges[i]) < 1e-9), "User zoom ranges remain identical through actual Experiment/Analysis navigation in both directions" + "; origin=" + data.origin + " page=" + pageName + " expectedOriginRanges=" + JSON.stringify(ranges) + " readPageRanges=" + JSON.stringify([actual.axisX.min, actual.axisX.max, actual.axisY.min, actual.axisY.max]));
                for (const [name, index] of types)
                    compare(findChild(shown, name).currentIndex, index, "Every shared scan axis/palette control follows the same user state across pages");
                compare(Session.project.currentExperimentIndex, row, "The same selected measured dataset remains current across both scan-view pages");
                const retained = Render.descendants(applicationWindow.contentItem).filter(item => item.objectName === "scanView." + data.mode);
                compare(retained.filter(item => item.visible && item.shown).length, 1, "The shared-object or authorized retained-chart fallback has exactly one eligible shown view");
                selectionLabel(row);
                const p = named("pointer");
                mouseClick(p, p.width * .5, p.height * .5, Qt.RightButton);
                verify(waitForPolish(chart) && waitForRendering(chart), "Reset finishes the native-axis label layout before the next pixel drag");
                const native = [actual.axisX.min, actual.axisX.max, actual.axisY.min, actual.axisY.max];
                const origin = p.mapToItem(p.Window.window.contentItem, 0, 0);
                const start = [Math.round(origin.x + p.width * .2) - origin.x, Math.round(origin.y + p.height * .2) - origin.y];
                const end = [Math.round(origin.x + p.width * .8) - origin.x, Math.round(origin.y + p.height * .8) - origin.y];
                const wanted = [native[0] + start[0] / p.width * (native[1] - native[0]), native[0] + end[0] / p.width * (native[1] - native[0]), native[3] - end[1] / p.height * (native[3] - native[2]), native[3] - start[1] / p.height * (native[3] - native[2])];
                mouseDrag(p, start[0], start[1], end[0] - start[0], end[1] - start[1], Qt.LeftButton);
                verify([actual.axisX.min, actual.axisX.max, actual.axisY.min, actual.axisY.max].every((x, i) => Math.abs(x - wanted[i]) <= Math.abs(native[i % 2 ? 1 : 0]) * 1e-10 + 1e-9), "Both pages accept real reset and re-zoom input while retaining the same shared visible ranges" + "; origin=" + data.origin + " page=" + pageName + " expectedOriginRanges=" + JSON.stringify(ranges) + " readResetRanges=" + JSON.stringify(native) + " expectedPixelDragRanges=" + JSON.stringify(wanted) + " readRezoomRanges=" + JSON.stringify([actual.axisX.min, actual.axisX.max, actual.axisY.min, actual.axisY.max]));
                ranges = [actual.axisX.min, actual.axisX.max, actual.axisY.min, actual.axisY.max];
            }
        }
        function test_chart_colour_selector_location() {
            const scan = open("stacked");
            ready(scan);
            chart.destroy();
            chart = null;
            applicationWindow = applicationFactory.createObject(null);
            verify(applicationWindow !== null, "Colour-control placement is checked in the actual application");
            applicationWindow.requestActivate();
            tryCompare(applicationWindow, "active", true, 2000, "The actual application receives colour-control placement navigation");
            for (const pageName of ["structure", "experiment", "analysis"]) {
                Ui.click(test, Probe, applicationWindow, "appBar.tab." + pageName);
                tryVerify(() => !Ui.moving(applicationWindow.contentItem), 2000, "Actual page navigation finishes before observing its colour controls");
                const page = Render.descendants(applicationWindow.contentItem).find(item => item.pageName === pageName && item.current);
                verify(page !== undefined, "Every colour-consuming page is reached in the actual application");
                for (const text of (pageName === "structure" ? ["Structure", "Pattern"] : ["Pattern"])) {
                    const tab = Array.from(page.mainTabs).find(item => item.text === text);
                    verify(tab !== undefined && tab.enabled, "Colour placement reaches the actual Structure and Pattern tabs, rather than a retained scan tab");
                    tryVerify(() => fullyExposed(tab) && Ui.clickPoint(tab) !== null, 2000, "The intended colour-view tab finishes its page transition inside every actual input clip");
                    if (!tab.checked)
                        Ui.click(test, Probe, applicationWindow, tab.objectName);
                    tryCompare(tab, "checked", true, 1000, "Real input opens the intended colour-consuming view");
                    tryVerify(() => !Ui.moving(page), 2000, "The intended colour view finishes moving before its toolbar census");
                    const controls = Render.descendants(page).filter(item => Ui.rendered(item) && typeof item.textAt === "function" && String(item.objectName).includes("toolbar"));
                    const colours = controls.filter(item => item.objectName !== "structure.toolbar.colors" && /colour|color|palette/i.test(String(item.objectName) + " " + item.toolTip));
                    compare(colours.length, 0, "Categorical palette choices leave the Pattern and Structure toolbars while the independent element scheme stays");
                }
            }
            for (const pageName of ["experiment", "analysis"])
                for (const mode of ["stacked", "map"]) {
                    const target = showSharedScan(pageName, mode);
                    const controls = Render.descendants(target).filter(item => item.visible && typeof item.textAt === "function" && /colour|color|palette/i.test(String(item.objectName) + " " + item.toolTip));
                    compare(controls.length, mode === "map" ? 1 : 0, "Only the Map toolbar retains its one shared colour-map shortcut on both pages");
                }
        }
        function test_stacked_tick_labels_cover_rows_only_data() {
            const rows = [];
            for (const byIndex of [false, true])
                for (const dark of [false, true])
                    rows.push({
                        tag: (byIndex ? "index" : "value") + (dark ? "-dark" : "-light"),
                        byIndex,
                        dark
                    });
            return rows;
        }
        function rowLabels() {
            return Render.texts(chart).filter(item => {
                let parent = item.parent;
                while (parent && parent.segments === undefined)
                    parent = parent.parent;
                return parent && parent.segments.some(piece => piece.icon === "microscope") && !String(item.font.family).includes("Awesome") && Ui.rendered(item);
            });
        }
        function labelFor(labels, expected) {
            return labels.filter(item => typeof expected === "number" ? /^[-+0-9.]+\s*K$/.test(item.text.trim()) && Math.abs(parseFloat(item.text) - expected) < 1e-9 : item.text === expected);
        }
        function checkRows(expected, coordinates, dark) {
            const axes = named("axes"), layer = named("layer"), labels = rowLabels(), origin = layer.mapToItem(chart, 0, 0);
            compare(axes.axisY.visible, false, "Labelled rows hide the whole y axis so it reserves no numeric-scale gutter");
            compare(labels.length, expected.length, "Sparse rows show exactly one icon-and-name label for each independent dataset");
            const colours = Approved.colours(SettingsProof, "ediNatural", "measured", expected.length, dark);
            for (let i = 0; i < expected.length; ++i) {
                const matches = labelFor(labels, expected[i]);
                compare(matches.length, 1, "Every row uses its independent file, datablock or scan value with unit");
                const label = matches[0], right = label.mapToItem(chart, label.width, chart.mode === "stacked" ? label.height : label.height / 2);
                verify(right.x < origin.x && label.mapToItem(chart, 0, 0).x >= 0, "The complete row label lies left of the plot and inside the chart");
                const coordinate = chart.mode === "stacked" ? stackedAt(i, expected.length, 0) : coordinates[i];
                const wanted = origin.y + (axes.axisY.max - coordinate) / (axes.axisY.max - axes.axisY.min) * layer.height;
                verify(Math.abs(right.y - wanted) <= 1, "A Stacked label's bottom sits on its independent baseline; a Map label stays centred on its row");
                tryCompare(label, "color", i === Session.project.currentExperimentIndex && !Preferences.chartHighlightSelected ? Style.Colors.themeAccent : rgb(colours[i]), 2000, "Every row label settles to its independently approved dataset colour or selected accent");
                let parent = label.parent;
                while (parent && parent.segments === undefined)
                    parent = parent.parent;
                const icons = Render.texts(parent).filter(item => String(item.font.family).includes("Awesome"));
                compare(icons.length, 1, "Every labelled row draws its experiment icon");
                compare(String(icons[0].color).toLowerCase(), i === Session.project.currentExperimentIndex && !Preferences.chartHighlightSelected ? String(Style.Colors.themeAccent).toLowerCase() : colours[i], "The experiment icon uses the same independent dataset colour as its row label");
                verify(icons[0].mapToItem(chart, icons[0].width, 0).x <= label.mapToItem(chart, 0, 0).x, "The experiment icon precedes the name outside the y axis");
            }
        }
        function test_stacked_tick_labels_cover_rows_only(data) {
            const scan = open("stacked");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            const selector = axisControl("y"), expected = data.byIndex ? ["all594687.dat", "all594791.dat", "all594842.dat"] : [100, 250, 700];
            choose(selector, data.byIndex ? 1 : 0);
            compare(selector.displayText, data.byIndex ? "y: file" : "y: temperature (K)", "The order selector names files or the extracted quantity, never a file-index scale");
            checkRows(expected, data.byIndex ? [0, 1, 2] : [100, 250, 700], data.dark);
        }
        function test_row_order_and_map_bands_data() {
            const cases = [];
            for (const mode of ["stacked", "map"])
                for (const kind of ["file", "datablock"])
                    for (const dark of [false, true])
                        cases.push({
                            tag: mode + "-" + kind + (dark ? "-dark" : "-light"),
                            mode,
                            kind,
                            dark
                        });
            return cases;
        }
        function test_row_order_and_map_bands(data) {
            let scan;
            if (data.kind === "datablock") {
                openJoint();
                chart = factory.createObject(surface, {
                    project: Session.project,
                    mode: data.mode
                });
                scan = Session.project.scanViews;
            } else
                scan = open(data.mode);
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            const selector = axisControl("y"), expected = data.kind === "file" ? ["all594687.dat", "all594791.dat", "all594842.dat"] : ["expt_n2", "expt_s2"];
            let index = -1;
            for (let i = 0; i < selector.count; ++i)
                if (selector.textAt(i) === data.kind)
                    index = i;
            verify(index >= 0, "The actual row selector offers file or datablock according to the independent datasets' names");
            if (selector.count > 1)
                choose(selector, index);
            else
                compare(selector.currentIndex, index, "A joint fit displays its sole datablock ordering without requiring a disabled selector to open");
            compare(selector.displayText, "y: " + data.kind, "The selected row ordering uses its short owner-requested caption");
            checkRows(expected, expected.map((_, i) => i), data.dark);
            if (data.mode === "map") {
                const bounds = expected.map((_, i) => [scan.rowLowEdge(i), scan.rowHighEdge(i)]);
                for (let i = 0; i < bounds.length; ++i) {
                    fuzzyCompare(bounds[i][0], i - .5, 1e-9, "Each named Map band begins at the independent half-index edge");
                    fuzzyCompare(bounds[i][1], i + .5, 1e-9, "Each named Map band has equal unit height irrespective of temperature spacing");
                }
            }
        }
        function test_scan_axis_fonts_data() {
            return test_owner_indicator_data();
        }
        function test_scan_axis_fonts(data) {
            if (data.mode === "evolution") {
                const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/report_evolution/project"));
                verify(Session.openProject(root), "Evolution font comparison uses a real saved fitted scan");
                chart = evolutionFactory.createObject(surface, {
                    project: Session.project
                });
                tryVerify(() => chart.fitted, 3000, "Evolution has real numeric axis content before its font comparison");
            } else {
                const scan = open(data.mode);
                ready(scan);
            }
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            const pattern = createTemporaryObject(patternReferenceFactory, surface, {
                experiment: Session.project.currentExperiment,
                shown: true
            });
            verify(pattern !== null && waitForRendering(chart), "Actual Pattern and scan chart font objects are ready");
            const reference = findChild(pattern, "chart.view.main"), title = findChild(pattern, "chart.title.x"), axes = findChild(chart, data.mode === "evolution" ? "evolution.view" : "scanView." + data.mode + ".axes");
            verify(reference !== null && title !== null && axes !== null, "Font equality compares the actual chart axes and title, not hardcoded point sizes");
            function equal(actual, wanted) {
                compare(actual.family, wanted.family, "Every scan axis uses the Pattern axis font family");
                fuzzyCompare(actual.pixelSize, wanted.pixelSize, .01, "Every scan tick, title and key uses the Pattern axis font size");
                compare(actual.weight, wanted.weight, "Every scan axis uses the Pattern axis font weight");
            }
            equal(axes.theme.labelFont, reference.theme.labelFont);
            const prefix = data.mode === "evolution" ? "evolution" : "scanView." + data.mode;
            for (const axis of ["x", "y"]) {
                const item = findChild(chart, prefix + ".title." + axis);
                verify(item !== null, "Each actual scan axis has its rendered title for comparison");
                equal(item.font, title.font);
            }
            for (const item of Render.texts(axes))
                equal(item.font, reference.theme.labelFont);
            if (data.mode === "map")
                for (const end of ["min", "max"])
                    equal(named("colourBar." + end).font, reference.theme.labelFont);
        }
        function test_map_numeric_dataset_ticks_data() {
            return [
                {
                    tag: "light",
                    dark: false
                },
                {
                    tag: "dark",
                    dark: true
                }
            ];
        }
        function test_map_numeric_dataset_ticks(data) {
            const scan = open("map");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            choose(axisControl("y"), 0);
            const axes = named("axes");
            verify(axes.axisY.visible && axes.axisY.labelsVisible, "The Map retains a numeric axis when rows use physical scan values");
            checkDatasetTicks([100, 250, 700], Approved.colours(SettingsProof, "ediNatural", "measured", 3, data.dark));
        }
        function checkDatasetTicks(rows, colours) {
            const layer = named("layer"), axes = named("axes"), ticks = named("rowTicks"), origin = layer.mapToItem(chart, 0, 0);
            verify(ticks.visible && ticks.scanLayer === layer, "The named combined tick item draws the shown scan layer's dataset ticks");
            const at = ticks.mapToItem(chart, 0, 0);
            fuzzyCompare(at.x - origin.x - layer.width, 1, .01, "Dataset ticks stay one logical pixel right of the plot");
            fuzzyCompare(at.y, origin.y, .01, "The combined tick strip starts at the actual plot top");
            fuzzyCompare(ticks.height, layer.height, .01, "The combined tick strip spans the actual plot height");
            const expected = rows.map((value, i) => ({
                        value: chart.mode === "stacked" ? stackedAt(i, rows.length, 0) : value,
                        i
                    })).filter(row => row.value >= axes.axisY.min && row.value <= axes.axisY.max);
            const frame = logicalImage(chart), expectedPixels = new Map();
            for (const row of expected) {
                const y = Math.max(0, Math.min(Math.floor(layer.height) - 1, Math.floor((axes.axisY.max - row.value) / (axes.axisY.max - axes.axisY.min) * layer.height)));
                // At subpixel spacing later rows legitimately paint over earlier ticks.
                expectedPixels.set(y, row.i);
            }
            for (const [y, index] of expectedPixels) {
                const pixel = frame.pixel(Math.floor(at.x + ticks.width / 2), Math.floor(at.y + y));
                verify(["r", "g", "b"].every(c => Math.abs(pixel[c] - rgb(colours[index])[c]) <= 2 / 255), "Each visible tick has actual independent dataset colour at its closed-form baseline; row=" + index + " y=" + y + " pixel=" + pixel + " expected=" + colours[index]);
            }
            for (let y = 0; y < Math.floor(layer.height); ++y)
                if (![...expectedPixels.keys()].some(at => Math.abs(at - y) <= 1)) {
                    const pixel = frame.pixel(Math.floor(at.x + ticks.width / 2), Math.floor(at.y + y));
                    compare(String(pixel), String(chart.colors.chartBackground), "The tick strip contains no extra row ticks outside independently expected raster positions");
                }
        }
        function test_dataset_ticks_all_y_modes_data() {
            const cases = [];
            for (const mode of ["stacked", "map"])
                for (const kind of ["value", "file", "datablock"])
                    for (const dark of [false, true])
                        cases.push({
                            tag: mode + "-" + kind + (dark ? "-dark" : "-light"),
                            mode,
                            kind,
                            dark
                        });
            return cases;
        }
        function test_dataset_ticks_all_y_modes(data) {
            let scan;
            if (data.kind === "datablock") {
                openJoint();
                chart = factory.createObject(surface, {
                    project: Session.project,
                    mode: data.mode
                });
                scan = Session.project.scanViews;
            } else
                scan = open(data.mode);
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            Preferences.scanStackedPalette = "ediNatural";
            ready(scan);
            const selector = axisControl("y");
            if (selector.count > 1)
                choose(selector, data.kind === "value" ? 0 : selector.count - 1);
            else
                compare(selector.currentIndex, 0, "A joint fit starts in its sole datablock ordering");
            const rows = data.kind === "value" ? [100, 250, 700] : data.kind === "file" ? [0, 1, 2] : [0, 1];
            compare(named("axes").axisY.visible, data.mode === "map" && data.kind === "value", "Only a Map ordered by physical values keeps the numeric y axis");
            for (const palette of ["ediNatural", "ediCoast"]) {
                Preferences.scanStackedPalette = palette;
                surface.Window.window.update();
                verify(waitForRendering(chart), "A changed Stacked colour choice redraws ticks on both scan views");
                checkDatasetTicks(rows, Approved.colours(SettingsProof, palette, "measured", rows.length, data.dark));
            }
            const pointer = named("pointer");
            mouseDrag(pointer, pointer.width * .2, pointer.height * .15, pointer.width * .6, pointer.height * .7, Qt.LeftButton);
            verify(waitForRendering(chart), "Actual zoom redraws dataset ticks at their new row coordinates");
            checkDatasetTicks(rows, Approved.colours(SettingsProof, "ediCoast", "measured", rows.length, data.dark));
            // Put the first and last rows exactly at the viewport boundaries.
            chart.zoomY = [rows[0], rows[rows.length - 1]];
            surface.Window.window.update();
            verify(waitForRendering(chart), "The boundary viewport has a completed frame");
            checkDatasetTicks(rows, Approved.colours(SettingsProof, "ediCoast", "measured", rows.length, data.dark));
        }
        function test_dataset_ticks_survive_label_thinning_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_dataset_ticks_survive_label_thinning(data) {
            const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/scan_template/project"));
            const count = Input.dense(SettingsProof, root, false);
            verify(Session.openProject(root), "Dense dataset ticks use independently generated measured files");
            Preferences.resetToDefaults();
            Preferences.scanStackedPalette = "ediNatural";
            Style.Colors.theme = Style.Colors.LightTheme;
            chart = factory.createObject(surface, {
                project: Session.project,
                mode: data.mode,
                height: 500
            });
            ready(Session.project.scanViews);
            const selector = axisControl("y");
            choose(selector, selector.count - 1);
            chart.zoomY = [-.5, count - .5];
            surface.Window.window.update();
            verify(waitForRendering(chart), "Dense tick rows have a completed frame in their full row viewport");
            verify(rowLabels().length < count, "The dense tick witness reaches actual label thinning");
            const endpoints = Approved.colours(SettingsProof, "ediNatural", "measured", 2, false);
            checkDatasetTicks(Array.from({
                length: count
            }, (_, i) => i), Array.from({
                length: count
            }, (_, i) => Oklab.gradient(endpoints[0], endpoints[1], i / (count - 1))));
        }
        function heightSelector() {
            const control = named("toolbar.height");
            verify(control.visible && typeof control.textAt === "function", "The Stacked height gate reaches the named actual height combobox");
            return control;
        }
        function test_stacked_height_default_and_memory() {
            const location = Globals.Vars.settingsFile, code = 'import QtQuick; import edi.app; QtObject { property int saved:Preferences.scanStackedSize }';
            SettingsProof.erase(location, "ScanViews", "stackedSize");
            const fresh = SettingsProof.restart(code);
            verify(!fresh.error, "The absent height key is read by an actual fresh preferences engine");
            compare(fresh.saved, 0, "An absent Stacked size setting defaults to Fit");
            const scan = open("stacked", "rows");
            ready(scan);
            const selector = heightSelector();
            compare(selector.count, 11, "The height selector offers Fit and ten percentage choices");
            for (let i = 0; i < selector.count; ++i) {
                const expected = i === 0 ? "Fit" : (i * 10) + "%";
                compare(selector.textAt(i).replace(/\s/g, ""), expected, "Every height choice has its independently specified percentage or Fit label");
            }
            for (const choice of [10, 1, 0]) {
                choose(selector, choice);
                const expected = choice * 10;
                compare(Preferences.scanStackedSize, expected, "Actual height input commits the selected plot-height percentage");
                tryVerify(() => SettingsProof.value(location, "ScanViews", "stackedSize") === expected, 2000, "The height percentage reaches the actual preferences file before restart");
                const restored = SettingsProof.restart(code);
                verify(!restored.error, "The saved percentage loads in another real preferences engine");
                compare(restored.saved, expected, "Fixed height and Fit both persist across an engine restart");
            }
            chart.mode = "map";
            verify(waitForRendering(chart), "The chart switches to Map after height selection");
            verify(!Ui.rendered(selector), "The pattern-height selector is exposed only for Stacked");
        }

        function test_stacked_height_changes_rise_not_rows_data() {
            return [
                {
                    tag: "value",
                    byIndex: false
                },
                {
                    tag: "file",
                    byIndex: true
                }
            ];
        }
        function test_stacked_height_changes_rise_not_rows(data) {
            const scan = open("stacked", "height");
            ready(scan);
            choose(axisControl("y"), data.byIndex ? 1 : 0);
            const rows = data.byIndex ? [0, 1, 2] : [100, 250, 400], selector = heightSelector();
            for (const choice of [1, 5, 10, 0]) {
                choose(selector, choice);
                const layer = named("layer");
                compare(rows.map((_, i) => scan.rowOf(i)), rows, "Height changes preserve the actual scientific dataset coordinates");
                for (let i = 0; i < rows.length; ++i)
                    fuzzyCompare(layer.rowOf(i), stackedAt(i, rows.length, 0), 1e-9, "A changed height places each Stacked baseline at rank times height times offset");
                fuzzyCompare(layer.patternHeight, choice === 0 ? 1 / 1.2 : choice / 10, 1e-9, "The actual height equals the fixed plot share or the closed-form Fit height");
                checkDatasetTicks(rows, Approved.colours(SettingsProof, "ediNatural", "measured", 3, false));
            }
        }

        function test_reverse_colour_group_and_memory_data() {
            return test_joint_labels_outside_axis_data();
        }
        function test_reverse_colour_group_and_memory(data) {
            const scan = open(data.mode, "rows");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            ready(scan);
            exposeStack();
            const toggle = Render.descendants(chart).find(item => item.visible && typeof item.checked === "boolean" && /reverse/i.test(String(item.objectName) + " " + item.toolTip));
            verify(toggle !== undefined && toggle.enabled, "Both Stacked and Map expose a real reverse-colours button");
            const colours = Approved.colours(SettingsProof, "ediNatural", "measured", 3, data.dark), location = Globals.Vars.settingsFile;
            const ownKey = data.mode === "map" ? "mapReversed" : "stackedReversed";
            for (const reversed of [true, false, true]) {
                if (toggle.checked !== reversed)
                    mouseClick(toggle, toggle.width / 2, toggle.height / 2);
                tryCompare(toggle, "checked", reversed, 1000, "Actual pointer input reverses either scan view in both directions");
                tryVerify(() => SettingsProof.value(location, "ScanViews", ownKey) === reversed, 2000, "The view's reverse choice reaches its own saved settings key");
                const fresh = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property bool map:Preferences.scanMapReversed; property bool stacked:Preferences.scanStackedReversed }');
                verify(!fresh.error, "A fresh production settings engine reads the separately remembered reversal choices");
                compare(fresh[data.mode], reversed, "The chosen view remembers its own reversal after restart");
                compare(fresh[data.mode === "map" ? "stacked" : "map"], false, "Reversing one view leaves the other view's remembered colours unchanged");
                surface.Window.window.update();
                verify(waitForRendering(chart), "The reverse input reaches actual pattern and dataset-tick pixels");
                const expected = data.mode === "stacked" && reversed ? colours.slice().reverse() : colours;
                checkDatasetTicks([100, 250, 700], expected);
                const layer = named("layer"), axes = named("axes"), frame = logicalImage(chart);
                const y = data.mode === "stacked" ? stackedAt(2, 3, 1) : 700;
                const at = layer.mapToItem(chart, layer.width * .4, (axes.axisY.max - y) / (axes.axisY.max - axes.axisY.min) * layer.height);
                const colour = data.mode === "stacked" ? expected[2] : reversed ? "#440154" : "#fde725";
                let drawn = false;
                for (let dy = -2; dy <= 2; ++dy)
                    drawn = drawn || ink(frame.pixel(Math.round(at.x), Math.round(at.y) + dy), rgb(colour), chart.colors.chartBackground);
                verify(drawn, "Reversal changes the actual independent dataset colour or frozen viridis endpoint in the drawn view");
            }
        }
        function test_tof_x_labels_never_touch_data() {
            return test_current_row_tracks_async_coordinates_data();
        }
        function test_tof_x_labels_never_touch(data) {
            const root = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project"));
            Input.joint(SettingsProof, root, false, "tof-wide");
            verify(Session.openProject(root), "TOF label spacing opens independently authored six-digit native coordinates");
            Preferences.resetToDefaults();
            chart = factory.createObject(surface, {
                project: Session.project,
                mode: data.mode
            });
            ready(Session.project.scanViews);
            for (const width of [1100, 640, 420]) {
                chart.width = width;
                chart.zoomX = [];
                for (const zoom of [false, true]) {
                    if (zoom) {
                        const pointer = named("pointer");
                        mouseDrag(pointer, pointer.width * .23, pointer.height * .2, pointer.width * .47, pointer.height * .6, Qt.LeftButton);
                    }
                    surface.Window.window.update();
                    verify(waitForRendering(chart), "The TOF axis redraws its tick labels after resizing and real zoom input");
                    const layer = named("layer"), axes = named("axes"), origin = layer.mapToItem(chart, 0, 0);
                    const labels = Render.texts(axes).filter(item => item.visible && /^[-−+0-9.,eE ]+$/.test(item.text)).map(item => {
                        const p = item.mapToItem(chart, 0, 0);
                        return {
                            item,
                            left: p.x,
                            right: p.x + item.width,
                            top: p.y
                        };
                    }).filter(box => box.top >= origin.y + layer.height - 1 && box.left + box.item.width / 2 >= origin.x - 1 && box.left + box.item.width / 2 <= origin.x + layer.width + 1).sort((a, b) => a.left - b.left);
                    verify(labels.length >= 2, "A nonempty TOF axis retains at least two actual readable numeric ticks");
                    for (let i = 1; i < labels.length; ++i)
                        verify(labels[i].left - labels[i - 1].right >= 1, "Every adjacent pair of rendered TOF x tick labels keeps visible space at each chart width and zoom");
                }
            }
        }
        function test_row_label_thinning_data() {
            const cases = [];
            for (const mode of ["stacked", "map"])
                for (const kind of (mode === "stacked" ? ["file", "datablock", "value"] : ["file", "datablock"]))
                    cases.push({
                        tag: mode + "-" + kind,
                        mode,
                        kind
                    });
            return cases;
        }
        function test_row_label_thinning(data) {
            const joint = data.kind === "datablock", root = SettingsProof.copyProject(Probe.repoUrl(joint ? "docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project" : "tests/fixtures/scan_template/project"));
            const count = Input.dense(SettingsProof, root, joint);
            verify(Session.openProject(root), "Dense row-label acceptance opens independently generated files or datablocks");
            chart = factory.createObject(surface, {
                project: Session.project,
                mode: data.mode,
                height: 500
            });
            const scan = Session.project.scanViews;
            ready(scan);
            compare(scan.count, count, "The dense actor has every independently generated dataset");
            const selector = axisControl("y");
            let choice = -1;
            for (let i = 0; i < selector.count; ++i)
                if (data.kind === "value" ? /temperature/i.test(selector.textAt(i)) : selector.textAt(i) === data.kind)
                    choice = i;
            verify(choice >= 0, "Dense row-label input reaches the real file, datablock or scan-value choice");
            choose(selector, choice);
            function name(i) {
                return data.kind === "value" ? 100 + i * 7 + .345 : "row_" + String(i).padStart(3, "0") + (joint ? "" : ".dat");
            }
            function visibleIndices() {
                const labels = rowLabels();
                return Array.from({
                    length: count
                }, (_, i) => i).filter(i => labelFor(labels, name(i)).length === 1);
            }
            let shown = visibleIndices();
            verify(shown.length > 2 && shown.length < count, "Crowded rows thin their labels while retaining a readable spread across the plot");
            const selected = Array.from({
                length: count - 8
            }, (_, i) => i + 4).find(i => !shown.includes(i));
            verify(selected !== undefined, "The dense witness chooses a dataset whose label was thinned out");
            const axes = named("axes"), pointer = named("pointer"), row = data.mode === "stacked" ? stackedAt(selected, count, 0) : data.kind === "value" ? 100 + selected * 7 + .345 : selected;
            mouseClick(pointer, pointer.width * (data.mode === "stacked" ? .001 : .5), (axes.axisY.max - row - (data.mode === "stacked" ? 0 : data.kind === "value" ? .7 : .1)) / (axes.axisY.max - axes.axisY.min) * pointer.height);
            tryCompare(Session.project, "currentExperimentIndex", selected, 1000, "Real plot input selects the independently chosen hidden-label dataset");
            verify(waitForRendering(chart), "The selected dense row has a completed frame");
            shown = visibleIndices();
            verify(shown.includes(selected), "Thinning always retains the selected dataset's label");
            selectionLabel(selected);
            const regular = shown.filter(i => i !== selected), gaps = regular.slice(1).map((i, n) => i - regular[n]);
            verify(gaps.length > 0 && Math.max(...gaps) <= 2 * Math.min(...gaps), "Thinned row labels remain evenly spread, allowing the selected-row insertion");
            const labels = rowLabels().map(item => ({
                        top: item.mapToItem(chart, 0, 0).y,
                        bottom: item.mapToItem(chart, 0, item.height).y
                    })).sort((a, b) => a.top - b.top);
            verify(labels.slice(1).every((box, i) => box.top >= labels[i].bottom), "Visible thinned labels do not collide, including the always-kept selected row" + "; expected=each top >= previous bottom; readBoxes=" + JSON.stringify(labels) + " collidingPairs=" + JSON.stringify(labels.slice(1).map((box, i) => ({
                        previous: labels[i],
                        current: box
                    })).filter(pair => pair.current.top < pair.previous.bottom)) + " labelRectangles=" + JSON.stringify(rowLabels().map(item => ({
                        text: item.text,
                        x: item.mapToItem(chart, 0, 0).x,
                        y: item.mapToItem(chart, 0, 0).y,
                        width: item.width,
                        height: item.height
                    }))));
            const step = data.mode === "stacked" ? stackedAt(1, count, 0) : data.kind === "value" ? 7 : 1, top = (axes.axisY.max - (row + 3 * step)) / (axes.axisY.max - axes.axisY.min) * pointer.height, bottom = (axes.axisY.max - (row - 3 * step)) / (axes.axisY.max - axes.axisY.min) * pointer.height;
            mouseDrag(pointer, pointer.width * .2, top, pointer.width * .6, bottom - top, Qt.LeftButton);
            verify(waitForRendering(chart), "Actual drag zoom gives the formerly crowded rows room to reappear");
            shown = visibleIndices();
            for (let i = selected - 2; i <= selected + 2; ++i)
                verify(shown.includes(i), "Every independently in-range row label reappears once zoom makes its spacing readable");
        }

        function test_coincident_dataset_identity_data() {
            const cases = [];
            for (const shape of ["all", "interior", "file"])
                for (const style of ["stepped", "smooth", "stacked"])
                    for (const subject of ["pixels", "selection"])
                        cases.push({
                            tag: shape + "-" + style + "-" + subject,
                            shape,
                            style,
                            subject
                        });
            return cases;
        }
        function test_coincident_dataset_identity(data) {
            Style.Colors.theme = Style.Colors.LightTheme;
            Preferences.resetToDefaults();
            Preferences.patternYScale = "linear";
            Preferences.chartHighlightSelected = false;
            Preferences.scanMapColours = "viridis";
            Preferences.scanStackedPalette = "ediNatural";
            const root = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/scan_template/project"));
            const fixture = Input.coincident(SettingsProof, root, data.shape === "all");
            verify(Session.openProject(root), "Coincident datasets open through the ordinary project and scan reader");
            const scan = Session.project.scanViews;
            chart = factory.createObject(surface, {
                project: Session.project,
                mode: data.style === "stacked" ? "stacked" : "map"
            });
            ready(scan);
            compare(scan.count, fixture.intensities.length, "Every independently authored coincident dataset is retained");
            compare(scan.failed, 0, "Repeated finite scientific values are valid readable inputs");
            compare(scan.error, "", "Equal extracted values do not conceal a file-read refusal");
            if (data.shape === "file") {
                const selector = axisControl("y");
                let index = -1;
                for (let i = 0; i < selector.count; ++i)
                    if (selector.textAt(i) === "file")
                        index = i;
                verify(index >= 0, "The control reaches explicit file ordering through the real row selector");
                choose(selector, index);
            }
            if (chart.mode === "map") {
                const toggle = interpolationToggle(chart);
                if (toggle.checked !== (data.style === "smooth"))
                    mouseClick(toggle, toggle.width / 2, toggle.height / 2);
            }
            exposeStack();
            const layer = named("layer"), pointer = named("pointer");
            verify(waitForRendering(chart), "The independent identity observer captures completed data pixels without the selection border");
            const frame = logicalImage(chart);
            const colours = chart.mode === "stacked" ? Approved.colours(SettingsProof, "ediNatural", "measured", fixture.intensities.length, false).map(rgb) : fixture.intensities.map(level => {
                const sample = samples.find(value => value.index === level);
                return {
                    r: Math.round(sample.rgb[0] * 255) / 255,
                    g: Math.round(sample.rgb[1] * 255) / 255,
                    b: Math.round(sample.rgb[2] * 255) / 255
                };
            });
            function matches(row, y) {
                return [.31, .57, .79].every(fraction => {
                    const at = layer.mapToItem(chart, Math.round(layer.width * fraction), y);
                    const pixel = frame.pixel(Math.round(at.x), Math.round(at.y));
                    return chart.mode === "stacked" ? ink(pixel, colours[row], chart.colors.chartBackground) : ["r", "g", "b"].every(c => Math.abs(pixel[c] - colours[row][c]) <= 1 / 255);
                });
            }
            const locations = colours.map((_, row) => {
                const ys = [];
                for (let y = 4; y < layer.height - 4; ++y)
                    if (matches(row, y))
                        ys.push(y);
                return ys;
            });
            if (data.subject === "pixels") {
                for (let row = 0; row < colours.length; ++row)
                    verify(locations[row].length > 0, "Every dataset has its own independent constant-intensity Map pixels or approved Stacked ink, irrespective of coincident-coordinate layout; row=" + row + " level=" + fixture.intensities[row] + " temperatures=" + JSON.stringify(fixture.temperatures) + " pixelRows=" + JSON.stringify(locations));
                return;
            }
            for (let row = 0; row < colours.length; ++row) {
                Session.project.currentExperimentIndex = row;
                selectionLabel(row);
                const own = locations[row];
                verify(own.length > 0, "The selected dataset retains independently identified data pixels beside its bold label");
                Session.project.currentExperimentIndex = (row + 1) % colours.length;
                verify(waitForRendering(chart), "The real-input witness starts with a different selected dataset");
                const y = own[Math.floor(own.length / 2)];
                const point = layer.mapToItem(pointer, layer.width * .57, y);
                mouseClick(pointer, point.x, point.y);
                tryCompare(Session.project, "currentExperimentIndex", row, 1000, "Clicking each dataset's Map pixels or Stacked row selects that exact dataset; row=" + row + " level=" + fixture.intensities[row] + " click=" + JSON.stringify([point.x, point.y]));
            }
        }
        function test_failed_middle_map_band_data() {
            return [
                {
                    tag: "stepped",
                    smooth: false
                },
                {
                    tag: "smooth",
                    smooth: true
                }
            ];
        }
        function test_failed_middle_map_band(data) {
            const scan = open("map", "broken");
            ready(scan);
            compare(scan.failed, 1, "Exactly the independently malformed middle dataset is refused");
            compare([scan.rowOf(0), scan.rowOf(1), scan.rowOf(2)], [0, 1, 2], "An unreadable extracted value retains its reserved file-index band");
            const toggle = interpolationToggle(chart);
            if (toggle.checked !== data.smooth)
                mouseClick(toggle, toggle.width / 2, toggle.height / 2);
            verify(waitForRendering(chart), "The failed-middle ownership witness captures the real Map without a selection overlay");
            const layer = named("layer"), axes = named("axes"), frame = logicalImage(chart);
            function pixel(x, y) {
                const at = layer.mapToItem(chart, (x - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width, (axes.axisY.max - y) / (axes.axisY.max - axes.axisY.min) * layer.height);
                return frame.pixel(Math.floor(at.x), Math.floor(at.y));
            }
            for (const y of [.55, .75, 1, 1.25, 1.45])
                for (const x of [25, 55, 85])
                    compare(String(pixel(x, y)), String(chart.colors.chartBackground), "Every interior column of a failed middle dataset's band stays empty in stepped and smooth Map modes");
            for (const y of [0, 2])
                verify(String(pixel(55, y)) !== String(chart.colors.chartBackground), "Both healthy neighbours retain actual Map data beside the refused middle band");
            const texts = Render.texts(chart).map(item => item.text).join(" ");
            verify(texts.includes("all594791.dat"), "Empty-band ownership retains the failed dataset's visible read diagnostic");
        }
        function test_unsampled_and_reduced_excluded_gaps_data() {
            const rows = [];
            for (const mode of ["map", "stacked"])
                for (const kind of ["sparse", "reduced", "subpixel"])
                    for (const falling of [false, true])
                        rows.push({
                            tag: mode + "-" + kind + (falling ? "-d" : ""),
                            mode,
                            kind,
                            falling
                        });
            return rows;
        }
        function test_unsampled_and_reduced_excluded_gaps(data) {
            Preferences.resetToDefaults();
            Preferences.patternYScale = "linear";
            Preferences.scanMapColours = "viridis";
            const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/scan_template/project"));
            Input.gap(SettingsProof, root, data.kind !== "sparse", data.kind === "subpixel");
            verify(Session.openProject(root), "The gap actor opens independently authored endpoints and excluded intervals");
            chart = factory.createObject(surface, {
                project: Session.project,
                mode: data.mode
            });
            const scan = Session.project.scanViews;
            ready(scan);
            const button = excludedButton(chart);
            verify(button !== undefined, "Each scan view exposes its ordinary included-only control");
            const layer = named("layer"), axes = named("axes");
            function shown(x) {
                // Exclusion locations follow the same raw-angle point column (ADR-0041).
                return data.falling ? 1.87 / (2 * Math.sin(x * Math.PI / 360)) : x;
            }
            if (data.falling) {
                const selector = axisControl("x");
                tryVerify(() => selector.enabled, 8000, "The actual calculated nontrivial Bragg conversion enables the falling d grid");
                choose(selector, 1);
                tryCompare(scan, "dShown", true, 1000, "Real x-axis input selects the measured pattern's falling d coordinates");
            }
            function setIncluded(on) {
                if (button.checked !== on)
                    mouseClick(button, button.width / 2, button.height / 2);
                tryCompare(button, "checked", on, 1000, "Real toolbar input changes the included-only drawing choice");
                if (data.kind === "sparse")
                    chart.setZoom([shown(12), shown(18)].sort((a, b) => a - b), []);
                verify(waitForPolish(chart) && waitForRendering(chart), "Each included-range choice and fine zoom reach the completed production frame");
            }
            function pixel(image, x, y) {
                const at = layer.mapToItem(chart, x, y);
                return image.pixel(Math.floor(at.x), Math.floor(at.y));
            }
            setIncluded(false);
            const full = logicalImage(chart);
            const gapX = shown(data.kind === "subpixel" ? 14.125 : 15);
            const x = Math.floor((gapX - axes.axisX.min) / (axes.axisX.max - axes.axisX.min) * layer.width);
            setIncluded(true);
            const included = logicalImage(chart);
            // Capture the chart and map the plot origin explicitly: a Qt item grab
            // uses the requested size but can retain the window's pixel origin.
            const blank = pixel(included, x, Math.floor(layer.height * .1));
            let offInk = false;
            for (let y = Math.floor(layer.height * .12); y < layer.height * .88; ++y) {
                offInk = offInk || String(pixel(full, x, y)) !== String(blank);
                compare(String(pixel(included, x, y)), String(blank), "Included-only leaves no Stacked segment, reduced-bin stroke or Map interpolation across an excluded interval; y=" + y + " x=" + x + " read=" + pixel(included, x, y) + " expected=" + blank + " referenceY=" + Math.floor(layer.height * .1));
            }
            verify(offInk, "Full-range control retains real measured ink at the same excluded x column");
            setIncluded(false);
            const restored = logicalImage(chart);
            for (const y of [.2, .4, .6, .8])
                compare(String(pixel(restored, x, Math.floor(layer.height * y))), String(pixel(full, x, Math.floor(layer.height * y))), "Switching back to full range restores the same measured drawing");
        }
    }
}
