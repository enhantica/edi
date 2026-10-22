// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import "ApprovedPalette.js" as Approved
import QtQuick.Controls
import QtTest
import edi.app
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

Rectangle {
    width: 1400
    height: 1000
    Component {
        id: reportFactory
        ReportPage {}
    }
    Component {
        id: preferencesFactory
        AppPreferencesDialog {}
    }
    TestCase {
        name: "PublishedPaletteContrast"
        when: windowShown
        property int oldTheme
        property string oldScheme
        property var page
        property var reference: Approved.reference(SettingsProof)
        function initTestCase() {
            oldTheme = Style.Colors.theme;
            oldScheme = Preferences.colourScheme;
        }
        function cleanup() {
            if (page)
                page.destroy();
            page = null;
            Session.closeProject();
            Style.Colors.theme = oldTheme;
            Preferences.colourScheme = oldScheme;
        }
        // W3C WCAG 2.2, relative luminance: the sRGB transfer function, then
        // the fixed 0.2126/0.7152/0.0722 weights. No product colour arithmetic.
        function luminance(colour) {
            if (colour === undefined || colour === null)
                return NaN;
            let channels;
            const css = /^rgba?\(([^)]+)\)$/.exec(String(colour));
            if (css)
                channels = css[1].split(",").slice(0, 3).map(value => Number(value.trim()) / 255);
            else if (colour.r !== undefined)
                channels = [colour.r, colour.g, colour.b];
            else {
                let hex = String(colour).replace("#", "");
                if (hex.length === 3)
                    hex = hex.split("").map(value => value + value).join("");
                channels = [0, 2, 4].map(index => parseInt(hex.slice(index, index + 2), 16) / 255);
            }
            const linear = channels.map(value => value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4));
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
        }
        function contrast(a, b) {
            const x = luminance(a), y = luminance(b);
            return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
        }
        function oklab(colour) {
            const hex = String(colour).replace("#", "");
            const rgb = [0, 2, 4].map(index => parseInt(hex.slice(index, index + 2), 16) / 255).map(value => value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4));
            const lms = [[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566], [0.0883024619, 0.2817188376, 0.6299787005]].map(row => Math.cbrt(row.reduce((sum, value, index) => sum + value * rgb[index], 0)));
            return [[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099], [0.0259040371, 0.7827717662, -0.8086757660]].map(row => row.reduce((sum, value, index) => sum + value * lms[index], 0));
        }
        function oklabDistance(first, second) {
            const a = oklab(first), b = oklab(second);
            return Math.sqrt(a.reduce((sum, value, index) => sum + Math.pow(value - b[index], 2), 0));
        }
        function test_independent_wcag_formula_controls() {
            fuzzyCompare(oklabDistance("#000000", "#ffffff"), 1, 1e-7, "The independent Oklab observer reaches the unit neutral black/white distance");
            compare(contrast("#000000", "#ffffff"), 21, "The independent WCAG observer reaches the published black/white 21:1 endpoint");
            compare(contrast("#333333", "#333333"), 1, "Equal encoded colours have exactly unit contrast");
            verify(contrast("#949494", "#ffffff") > 3 && contrast("#959595", "#ffffff") < 3, "Adjacent independent RGB grey values straddle the strict 3:1 boundary");
            fuzzyCompare(luminance("#0a0a0a"), 0.003035269835488375, 1e-12, "Encoded sRGB 10 uses the W3C lower linear branch");
            fuzzyCompare(luminance("#0b0b0b"), 0.003346535763899161, 1e-12, "Encoded sRGB 11 uses the W3C power branch");
        }
        function test_preferences_lists_all_five_named_schemes() {
            const dialog = createTemporaryObject(preferencesFactory, parent);
            verify(dialog !== null, "The five-palette gate creates the actual Preferences dialog");
            const box = findChild(dialog, "preferences.colourScheme");
            verify(box !== null, "Appearance exposes its actual preferences.colourScheme selector");
            const actual = Array.from({
                length: box.count
            }, (_, index) => box.textAt(index));
            compare(JSON.stringify(actual), JSON.stringify(reference.schemes.map(scheme => scheme.label)), "Preferences lists the five approved palettes in the owner's order; actual=" + JSON.stringify(actual));
            for (let index = 0; index < reference.schemes.length; ++index) {
                box.currentIndex = index;
                box.activated(index);
                compare(Preferences.colourScheme, reference.schemes[index].id, "Selecting each actual published scheme stores its corresponding token: " + actual[index]);
            }
        }
        function test_approved_palette_assignment_data() {
            const rows = [];
            for (const scheme of reference.schemes)
                for (const dark of [false, true])
                    rows.push({
                        tag: scheme.id + (dark ? "-dark" : "-light"),
                        scheme: scheme.id,
                        dark
                    });
            return rows;
        }
        function test_approved_palette_assignment(data) {
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            for (const count of [1, 2, 5, 6, 17, 1001]) {
                const expected = Approved.colours(SettingsProof, data.scheme, "measured", count, data.dark);
                const structures = Approved.colours(SettingsProof, data.scheme, "structures", count, data.dark);
                for (let place = 0; place < count; ++place) {
                    compare(String(ApplicationInfo.patternColour(data.scheme, place, count, data.dark)).toLowerCase(), expected[place], "The measured API equals the independently approved categorical or Oklab assignment at every place");
                    compare(String(ApplicationInfo.structureColour(data.scheme, place, count, data.dark)).toLowerCase(), structures[place], "The count-aware structure API equals the independently approved whole-group gradient at every place");
                }
            }
        }
        function hue(colour) {
            const coordinates = oklab(colour);
            return Math.atan2(coordinates[2], coordinates[1]) * 180 / Math.PI;
        }
        function hueDistance(a, b) {
            return Math.abs(((a - b + 540) % 360) - 180);
        }
        function quantisationBounds(colour) {
            const channels = [1, 3, 5].map(i => parseInt(String(colour).slice(i, i + 2), 16));
            const level = oklab(colour)[0], originalHue = hue(colour);
            const original = oklab(colour);
            let lightness = 0, angle = 0, chroma = 0, radius = 0;
            for (const r of [-0.5, 0.5])
                for (const g of [-0.5, 0.5])
                    for (const b of [-0.5, 0.5]) {
                        const values = [r, g, b].map((delta, i) => Math.max(0, Math.min(255, channels[i] + delta)) / 255);
                        const linear = values.map(v => v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
                        const cone = [[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566], [0.0883024619, 0.2817188376, 0.6299787005]].map(row => Math.cbrt(row.reduce((sum, v, i) => sum + v * linear[i], 0)));
                        const lab = [[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099], [0.0259040371, 0.7827717662, -0.8086757660]].map(row => row.reduce((sum, v, i) => sum + v * cone[i], 0));
                        radius = Math.max(radius, Math.sqrt(lab.reduce((sum, value, i) => sum + Math.pow(value - original[i], 2), 0)));
                        chroma = Math.max(chroma, Math.abs(Math.hypot(lab[1], lab[2]) - Math.hypot(...oklab(colour).slice(1))));
                        lightness = Math.max(lightness, Math.abs(lab[0] - level));
                        angle = Math.max(angle, hueDistance(Math.atan2(lab[2], lab[1]) * 180 / Math.PI, originalHue));
                    }
            return {
                lightness: lightness + 1e-7,
                hue: angle + 1e-5,
                chroma: chroma + 1e-7,
                radius: radius + 1e-7
            };
        }
        function calcHue(colour) {
            const lab = oklab(colour);
            if (Math.hypot(lab[1], lab[2]) <= quantisationBounds(colour).chroma)
                return false;
            const limits = [hue("#f44336"), hue("#ef9a9a")].sort((a, b) => a - b);
            const margin = Math.max(quantisationBounds("#f44336").hue, quantisationBounds("#ef9a9a").hue);
            return hue(colour) >= limits[0] - margin && hue(colour) <= limits[1] + margin;
        }
        function test_independent_hue_observer_reaches_calc_and_safe_controls() {
            verify(calcHue("#f44336") && calcHue("#ef9a9a"), "Both independent light/dark calculated colours lie in the calculated hue range");
            verify(!calcHue("#0055a0") && !calcHue("#808080"), "An independently blue hue and hue-less neutral stay outside the calculated hue range");
        }
        function test_natural_is_the_reversible_default() {
            Preferences.resetToDefaults();
            compare(Preferences.colourScheme, reference.default, "The owner-selected new default is Edi Natural after a real Preferences reset");
            Preferences.colourScheme = reference.schemes[1].id;
            Preferences.resetToDefaults();
            compare(Preferences.colourScheme, reference.default, "Reset reversibly restores Edi Natural after selecting another named scheme");
        }
        function test_pdf_colour_observer_reaches_an_independent_qt_image() {
            const witness = SettingsProof.pdfWitness();
            verify(!witness.error && witness.url !== undefined, "The palette observer consumes the independent Qt-written PDF image");
            const facts = SettingsProof.pdfImageColours(witness.url, ["#0000ff", "#00ff00"]);
            verify(!facts.error && facts.images > 0, "The PDF colour observer decodes an actual independent image stream: " + facts.error);
            verify(facts.counts["#0000ff"] > 0 && facts.counts["#00ff00"] === 0, "The PDF colour observer finds the independently blue image and rejects absent green; actual=" + JSON.stringify(facts));
        }
        function test_report_preview_html_and_pdf_use_light_palettes_data() {
            return reference.schemes.map(scheme => ({
                        tag: scheme.id,
                        scheme: scheme.id
                    }));
        }
        function test_report_preview_html_and_pdf_use_light_palettes(data) {
            Style.Colors.theme = Style.Colors.DarkTheme;
            Preferences.colourScheme = data.scheme;
            const expected = reference.schemes.find(row => row.id === data.scheme).palette;
            verify(expected !== undefined, "The report colour gate reaches its independently approved palette");
            const folder = SettingsProof.copyProject(Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project"));
            verify(Session.openProject(folder), "The light-report colour gate opens the real lbco project in the dark app theme");
            tryCompare(Session.project, "calculating", false, 15000, "The report colour input finishes its actual pattern and reflection calculation");
            page = reportFactory.createObject(parent, {
                width: 1400,
                height: 1000,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Report page creates its real pattern chart");
            const preview = findChild(page, "report.preview");
            function colourSeries(name) {
                const items = Render.descendants(preview);
                for (const item of items) {
                    if (item.objectName === name)
                        return item;
                    if (item.seriesList !== undefined)
                        for (let index = 0; index < item.seriesList.length; ++index)
                            if (item.seriesList[index].objectName === name)
                                return item.seriesList[index];
                }
                return findChild(preview, name);
            }
            tryVerify(() => colourSeries("chart.series.meas") !== null && colourSeries("chart.series.bragg.0") !== null, 5000, "The native report gate reads actual GraphsView seriesList consumers after lazy figure loading; actual chart items=" + JSON.stringify(Render.descendants(preview).filter(item => String(item.objectName).startsWith("chart.")).map(item => item.objectName)));
            const measured = colourSeries("chart.series.meas"), bragg = colourSeries("chart.series.bragg.0");
            const lightMeasured = expected.light.measured[0].toLowerCase(), lightStructure = expected.light.structures[0].toLowerCase();
            const failures = [];
            if (String(measured.color) !== lightMeasured || String(bragg.color) !== lightStructure)
                failures.push("preview measured=" + measured.color + " Bragg=" + bragg.color + "; light expected=" + lightMeasured + "/" + lightStructure);
            const exportGroup = findChild(page, "group.reportExport");
            verify(exportGroup !== null, "The palette gate reaches the actual Export writer action");
            Session.project.report.embedLibraries = true;
            Session.project.report.writesPdf = true;
            exportGroup.saveReport();
            const base = "reports/" + Session.project.name;
            tryVerify(() => SettingsProof.fileFacts(folder, base + ".html").bytes > 100 && SettingsProof.fileFacts(folder, base + ".pdf").bytes > 100, 15000, "The palette gate consumes actual saved HTML and PDF reports");
            const html = SettingsProof.htmlEvolutionFacts(SettingsProof.childUrl(folder, base + ".html"));
            verify(!html.error, "The actual saved HTML renderer loads in an independent browser: " + html.error);
            for (const view of ["wide", "narrow"]) {
                verify(html[view].ready, "The independent browser must reach initialized plot data and actual SVG or canvas drawing in the " + view + " report");
                const patterns = html[view].patterns;
                if (!patterns || patterns.length !== 1) {
                    failures.push(view + " actual HTML patterns=" + JSON.stringify(patterns));
                    continue;
                }
                const traces = patterns[0].traces;
                const meas = traces.find(trace => /measured/i.test(String(trace.name).replace(/<[^>]+>/g, "")));
                const ticks = traces.find(trace => /Bragg peaks/i.test(String(trace.name).replace(/<[^>]+>/g, "")));
                if (!meas || String(meas.line.color).toLowerCase() !== lightMeasured || !ticks || String(ticks.line.color).toLowerCase() !== lightStructure)
                    failures.push(view + " actual drawn HTML colours=" + JSON.stringify(traces.map(trace => ({
                                name: trace.name,
                                colour: trace.line ? trace.line.color : null
                            }))));
                if (contrast(patterns[0].background, "#ffffff") !== 1)
                    failures.push(view + " actual HTML plot background=" + patterns[0].background);
            }
            const pixels = SettingsProof.pdfImageColours(SettingsProof.childUrl(folder, base + ".pdf"), [lightMeasured, lightStructure]);
            verify(!pixels.error && pixels.images > 0, "The saved-PDF palette gate decodes actual figure images: " + pixels.error);
            if (!(pixels.counts[lightMeasured] >= 5 && pixels.counts[lightStructure] >= 5))
                failures.push("actual saved PDF light-colour pixels=" + JSON.stringify(pixels));
            compare(failures.length, 0, "Report preview, actual rendered HTML and actual saved PDF use the selected scheme's light pattern and structure colours while the app is dark; scheme=" + data.scheme + " actual=" + failures.join("; "));
        }
    }
}
