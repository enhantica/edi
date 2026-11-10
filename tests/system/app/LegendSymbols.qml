// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiChartReference 1.0
import ReportAcceptance 1.0
import "../../unit/app/RenderedTable.js" as Render
import "../../unit/app/UiInteraction.js" as Ui

Item {
    Component { id: application; Main { visible: true; width: 1500; height: 900 } }
    TestCase {
        id: test
        name: "LegendSymbols"
        when: windowShown
        property var app: null
        property var chart: null
        property var box: null
        function cleanup() {
            Session.closeProject();
            if (app) { app.close(); app.destroy(); }
            app = null; chart = null; box = null;
            Preferences.resetToDefaults();
        }
        function frame() {
            app.update();
            verify(waitForPolish(app.contentItem) && waitForRendering(app.contentItem), "Legend symbol observations use the actual rendered application frame");
        }
        function open(data) {
            Preferences.resetToDefaults();
            Preferences.patternLegendShown = true;
            Preferences.structureCurves = true;
            Preferences.patternMeasuredStyle = "line";
            Preferences.toolTips = false;
            const project = data.single ? "sc-neut-cwl_pr2nio4-5c2_fit" : data.many ? "pd-neut-cwl_yalo3-al2o3-spodi" : "pd-neut-cwl_lbco-hrpt";
            const location = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/" + project + "/project"));
            verify(String(location).startsWith("file:") && Session.openProject(location), "Symbol preservation uses a private copy of an independently saved catalogue project");
            app = application.createObject(null);
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "Legend symbol clicks reach the active real application");
            Ui.click(test, Probe, app, "appBar.tab." + data.page);
            const tab = Array.from(Ui.page(app).mainTabs || []).find(item => item.text === "Pattern");
            if (tab && !tab.checked) Ui.click(test, Probe, app, tab.objectName);
            tryVerify(() => {
                chart = Render.descendants(Ui.page(app)).find(item => item.objectName === (data.single ? "singleCrystal.chart" : "chart") && item.visible && item.shown);
                return chart && !Session.project.calculating && Probe.datasetReady(Session.project) && Math.abs(Ui.page(app).mapToItem(app.contentItem, 0, 0).x) < 1;
            }, 15000, "Every symbol witness reaches its populated selected Pattern chart");
            box = findChild(chart, data.single ? "singleCrystal.legend" : "chart.legend");
            verify(box !== null && box.visible, "The symbol witness reaches the actual chart legend");
            frame();
        }
        function entries() { return Render.descendants(box).filter(item => item.objectName === "chart.legend.entry"); }
        function target(data) {
            const rows = entries(), bragg = rows.filter(item => item.key.startsWith("bragg/"));
            if (!data.single) {
                compare(bragg.length, data.many ? 2 : 1, "The independent one- or two-structure project supplies every structure legend entry");
                verify(["meas", "calc", "bkg", "resid"].every(key => rows.some(item => item.key === key)), "The witness contains measured, calculated, background and residual entries");
                compare(new Set(bragg.map(item => item.label)).size, bragg.length, "Several structures have independently identifiable names rather than duplicate entries");
            }
            const row = data.single ? rows[0] : data.kind.startsWith("bragg") ? bragg[Number(data.kind.slice(-1))] : rows.find(item => item.key === data.kind);
            verify(row !== undefined, "Every requested legend entry type is actually present");
            return row;
        }
        function pieces(line) {
            return Render.descendants(line).filter(item => typeof item.isIcon === "boolean" && item.modelData !== undefined && typeof item.index === "number").sort((a, b) => a.index - b.index);
        }
        function symbols(line) { return pieces(line).filter(item => item.isIcon || item.mark !== ""); }
        function words(line) {
            return pieces(line).filter(item => !item.isIcon && item.mark === "").map(item => String(item.text).replace(/<[^>]*>/g, "").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&")).join(" ").replace(/\s+/g, " ").trim();
        }
        function signature(line) {
            return symbols(line).map(item => ({icon: item.isIcon ? item.modelData.icon : "", mark: item.mark, width: item.modelData.width || 0, font: item.isIcon ? item.font.family : ""}));
        }
        function click(row) {
            let previous = "", stable = 0;
            tryVerify(() => {
                const at = row.mapToItem(app.contentItem, 0, 0), now = JSON.stringify([at.x, at.y, row.width, row.height]);
                stable = now === previous ? stable + 1 : 0; previous = now;
                return stable >= 3;
            }, 2500, "The legend entry settles before ordinary pointer input");
            mouseClick(row, row.width - 3, row.height / 2, Qt.LeftButton, Qt.NoModifier, 500);
            mouseMove(app.contentItem, 2, 2);
            frame();
        }
        // Enabled ink is a round-trip geometry reference, not a correctness golden.
        // Compare each piece with its own real underlay so metadata-only icons cannot pass.
        function ink(piece, expected) {
            verify(piece.visible && piece.opacity > 0 && piece.width > 0 && piece.height > 0, "Every retained name or symbol has visible positive-area drawing geometry");
            frame();
            const opacity = piece.opacity;
            piece.opacity = 0; frame();
            const underlay = grabImage(app.contentItem);
            piece.opacity = opacity; frame();
            const image = grabImage(app.contentItem), at = piece.mapToItem(app.contentItem, 0, 0);
            const sx = image.width / app.contentItem.width, sy = image.height / app.contentItem.height;
            const x0 = Math.floor(at.x * sx), y0 = Math.floor(at.y * sy), width = Math.ceil(piece.width * sx), height = Math.ceil(piece.height * sy);
            let mask = [], mass = 0, painted = 0, wrong = 0, core = 0;
            for (let y = 0; y < height; ++y) for (let x = 0; x < width; ++x) {
                const bg = underlay.pixel(x0 + x, y0 + y), pixel = image.pixel(x0 + x, y0 + y);
                const delta = [pixel.r - bg.r, pixel.g - bg.g, pixel.b - bg.b];
                const colour = [expected.r - bg.r, expected.g - bg.g, expected.b - bg.b];
                const length = colour.reduce((sum, value) => sum + value * value, 0);
                const alpha = length > 1e-8 ? delta.reduce((sum, value, i) => sum + value * colour[i], 0) / length : 0;
                const changed = delta.some(value => Math.abs(value) > 2 / 255);
                mask.push(changed);
                if (changed) {
                    ++painted; mass += Math.max(0, Math.min(1, alpha));
                    // Qt's LCD text antialiasing covers R/G/B independently.
                    // Each channel must lie between its actual underlay and ink.
                    if (delta.some((value, i) => value < Math.min(0, colour[i]) - 0.025 || value > Math.max(0, colour[i]) + 0.025)) ++wrong;
                    if ([pixel.r - expected.r, pixel.g - expected.g, pixel.b - expected.b].every(value => Math.abs(value) < 0.08)) ++core;
                }
            }
            verify(painted >= 2 && mass > 1, "Every retained legend name and symbol contributes actual visible ink over its own underlay");
            console.log("LEGEND_INK " + JSON.stringify({text: piece.text, mark: piece.mark, foreground: String(expected), at: [x0, y0], size: [width, height], painted, wrong, core, mass}));
            verify(wrong <= painted * 0.05 && core > 0, "The actual name or symbol ink uses its declared enabled or disabled foreground, including independent RGB antialiasing");
            return {width, height, mask, mass};
        }
        function preserved(before, after) {
            verify(Math.abs(before.width - after.width) <= 1 && Math.abs(before.height - after.height) <= 1, "Disabling a symbol preserves its physical drawing dimensions within one antialiasing pixel");
            verify(Math.abs(after.mass / before.mass - 1) <= 0.15, "Disabling a symbol preserves its normalised ink area within fifteen percent across subpixel placement");
            function covered(source, destination) {
                let count = 0, found = 0;
                for (let y = 0; y < source.height; ++y) for (let x = 0; x < source.width; ++x) if (source.mask[y * source.width + x]) {
                    ++count; let hit = false;
                    for (let dy = -1; dy <= 1; ++dy) for (let dx = -1; dx <= 1; ++dx) {
                        const px = x + dx, py = y + dy;
                        if (px >= 0 && py >= 0 && px < destination.width && py < destination.height && destination.mask[py * destination.width + px]) hit = true;
                    }
                    if (hit) ++found;
                }
                return found / Math.max(1, count);
            }
            verify(covered(before, after) >= 0.95 && covered(after, before) >= 0.95, "The disabled symbol preserves its own enabled raster shape with one-pixel edge tolerance and ninety-five-percent coverage");
        }
        function test_symbol_data() {
            let rows = [];
            for (const page of ["experiment", "analysis"]) {
                for (const many of [false, true]) for (const kind of ["meas", "calc", "bkg", "resid", "bragg0"].concat(many ? ["bragg1"] : []))
                    rows.push({tag: page + "-" + (many ? "many" : "one") + "-" + kind, page, many, kind, single: false});
                rows.push({tag: page + "-single", page, many: false, kind: "points", single: true});
            }
            return rows;
        }
        function test_symbol(data) {
            open(data);
            let row = target(data);
            const key = row.key, original = signature(row), name = words(row);
            verify(original.length > 0 && name.length > 0, "Every entry starts with its own drawn symbol and nonempty name");
            if (row.key.startsWith("bragg/")) verify(original.some(piece => piece.icon === "layer-group") && original.some(piece => piece.mark === "tick"), "Every Bragg entry includes both its structure icon and geometric tick");
            const reference = symbols(row).map(piece => ink(piece, piece.color));
            click(row);
            tryVerify(() => { row = entries().find(item => item.key === key); return row && row.hidden; }, 2000, "A real legend name click hides the requested curve");
            compare(JSON.stringify(signature(row)), JSON.stringify(original), "A hidden entry retains every one of its own symbols, including each Bragg structure icon");
            compare(words(row), name, "A hidden legend entry retains its complete original displayed name");
            const disabled = box.colors.themeForegroundDisabled;
            for (const piece of pieces(row)) {
                compare(piece.color, disabled, "Every hidden legend name and symbol uses the shared disabled foreground");
                const raster = ink(piece, disabled), index = symbols(row).indexOf(piece);
                if (index >= 0) preserved(reference[index], raster);
            }
            click(row);
            tryVerify(() => { row = entries().find(item => item.key === key); return row && !row.hidden; }, 2000, "A second real legend click restores the curve and enabled entry");
            compare(JSON.stringify(signature(row)), JSON.stringify(original), "Showing the curve restores its original symbol identity");
            symbols(row).forEach((piece, index) => preserved(reference[index], ink(piece, piece.color)));
        }
        function test_strip_data() { return test_symbol_data().filter(row => row.kind.startsWith("bragg")); }
        function test_strip(data) {
            open(data);
            let row = target(data);
            const key = row.key, structure = row.label;
            function labels() { return Render.descendants(chart).filter(item => item.objectName === "chart.bragg.label"); }
            compare(labels().length, data.many ? 2 : 1, "Every independently supplied structure retains its own Bragg tick-strip label");
            let label = labels().find(item => item.modelData.text === structure);
            verify(label !== undefined && label.visible, "The Bragg strip label is associated with the clicked structure name");
            const original = signature(label), name = words(label), reference = symbols(label).map(piece => ink(piece, piece.color));
            click(row);
            tryVerify(() => { row = entries().find(item => item.key === key); return row && row.hidden; }, 2000, "The requested structure is hidden through its real legend entry");
            label = labels().find(item => item.modelData.text === structure);
            verify(label !== undefined, "The hidden structure retains an actual tick-strip label object");
            verify(label.visible && words(label) === name, "A hidden Bragg tick strip keeps its structure label shown with the same name");
            compare(JSON.stringify(signature(label)), JSON.stringify(original), "The hidden Bragg strip keeps its original structure icon");
            for (const piece of pieces(label)) {
                compare(piece.color, box.colors.themeForegroundDisabled, "The hidden Bragg strip structure name and icon are drawn in the disabled style");
                const raster = ink(piece, box.colors.themeForegroundDisabled), index = symbols(label).indexOf(piece);
                if (index >= 0) preserved(reference[index], raster);
            }
            labels().filter(item => item !== label).forEach(item => compare(item.modelData.hidden, false, "Hiding one structure leaves the other Bragg strip labels enabled"));
            click(row);
            tryVerify(() => { row = entries().find(item => item.key === key); return row && !row.hidden; }, 2000, "Showing the structure restores its real legend entry");
            label = labels().find(item => item.modelData.text === structure);
            verify(label !== undefined && label.visible && words(label) === name, "Showing a structure retains its original Bragg strip name");
            symbols(label).forEach((piece, index) => preserved(reference[index], ink(piece, piece.color)));
        }
    }
}
